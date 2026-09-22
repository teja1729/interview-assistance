"""Interview state machine and transactional persistence.

Lifecycle: lobby -> active -> complete -> finishing -> finished.
Finishing failures become report_failed and may be retried. Empty sessions may be abandoned.
A compare-and-swap version plus a fenced 150-second lease protects turns across processes.
No database write transaction is held while waiting on a model. Completed request IDs replay
exact results; reusing an ID with different content is rejected.
"""

import hashlib
import time

from fastapi import HTTPException
from sqlalchemy import update
from sqlmodel import Session, select

from ..agents.context import CLOSINGS, agent_context, brief_for, live_context, preference_flags, requested_language
from ..agents.runtime import execute
from ..agents.specs import snapshot as execution_snapshot
from ..auth import Context
from ..config import settings
from ..models import AgentJob, Interview, Operation, Resume, Turn, uid
from ..personas import interview_persona, persona_definition, public_persona
from ..providers.base import agent_profiles
from ..schemas import InterviewBrief, InterviewDecision, Plan, TurnDecision
from .company_research import research
from .interview_policy import question_bounds, remaining_topics, update_memory, validate_decision, validate_plan
from .usage import consume, rate_limit


def get_interview(session, ctx, interview_id, mutate=False):
    iv = session.get(Interview, interview_id)
    if not iv or iv.workspace_id != ctx.workspace.id:
        raise HTTPException(404, "Interview not found")
    if iv.user_id != ctx.user.id:
        raise HTTPException(404, "Interview not found")
    return iv


def turns_for(session, iv):
    return list(
        session.exec(
            select(Turn).where(Turn.interview_id == iv.id, Turn.workspace_id == iv.workspace_id).order_by(Turn.position)
        ).all()
    )


def remaining(iv):
    end = iv.ended_at or time.time()
    return max(0, int(iv.duration_minutes * 60 - (end - iv.started_at))) if iv.started_at else iv.duration_minutes * 60


def public(session, iv):
    turns = turns_for(session, iv)
    data = iv.model_dump(exclude={"resume_snapshot", "lock_token", "lock_until", "ai_profiles", "workspace_id"})
    data["plan"] = {"focus_areas": iv.plan.get("focus_areas", [])}
    data["persona_profile"] = public_persona(interview_persona(iv))
    brief = brief_for(iv)
    data["language"] = brief.language
    data["preference_notice"] = (
        "Requests to change grading were excluded from interview preferences."
        if preference_flags(iv.custom_instructions)
        else None
    )
    data["company_context"] = brief.company_context.model_dump()
    job = session.exec(select(AgentJob).where(AgentJob.interview_id == iv.id)).first()
    stage = (job.artifacts or {}).get("active_stage", "") if job else ""
    data["report_progress"] = (
        None
        if not job
        else {
            "completed_steps": len((job.artifacts or {}).get("steps", {})),
            "label": "Report ready"
            if job.status == "succeeded"
            else "Building your practice plan"
            if stage == "coaching"
            else "Writing your report summary"
            if stage == "report_summary"
            else "Reviewing your answers",
            "error": job.error if job.status == "failed" else None,
        }
    )
    data["turns"] = [t.model_dump(exclude={"assessment", "workspace_id", "interview_id"}) for t in turns]
    data["current_question"] = turns[-1].question if turns and turns[-1].answer is None else None
    data["remaining_seconds"] = remaining(iv)
    data["demo"] = iv.ai_profiles.get("evaluator", settings.default_profile) == "demo"
    return data


def create(session: Session, ctx: Context, body):
    rate_limit(session, ctx.workspace)
    snapshot = ""
    if body.resume_id:
        resume = session.get(Resume, body.resume_id)
        if not resume or resume.workspace_id != ctx.workspace.id or resume.user_id != ctx.user.id:
            raise HTTPException(404, "Resume not found")
        snapshot = f"Candidate: {resume.candidate_name}\n{resume.digest}"
    # Reject exhausted interview allowances before any paid company lookup.
    consume(session, ctx.workspace, "interviews")
    _, company_context = research(
        session, ctx, body.company, body.job_title, body.company_url, body.company_research_id
    )
    consume(session, ctx.workspace)
    iv = Interview(
        **body.model_dump(exclude={"language", "company_url", "company_research_id"}),
        workspace_id=ctx.workspace.id,
        user_id=ctx.user.id,
        resume_snapshot=snapshot,
        ai_profiles=agent_profiles(),
    )
    # Read-only context copied before model call; no open write transaction.
    session.commit()
    selected_persona = persona_definition(iv.persona)
    brief = InterviewBrief(
        job_title=iv.job_title,
        company=iv.company,
        experience_years=iv.experience_years,
        job_description=iv.job_description,
        resume=snapshot,
        custom_instructions=iv.custom_instructions,
        language=requested_language(body),
        company_context=company_context,
    )
    iv.plan = {
        "_brief": brief.model_dump(),
        "_persona": selected_persona,
        "_execution": execution_snapshot(
            {k: v for k, v in iv.ai_profiles.items() if k in {"planner", "interviewer", "evaluator", "coach"}},
            session.bind,
        ),
        "_visited_topics": [0],
        "_memory": [],
        "_rubric": selected_persona["rubric"],
    }
    plan = execute(
        "planner",
        {
            **agent_context(iv, iv.job_title),
            "duration_minutes": iv.duration_minutes,
            "question_count": dict(zip(("minimum", "maximum"), question_bounds(iv.duration_minutes), strict=True)),
        },
        Plan,
        workspace_id=ctx.workspace.id,
        user_id=ctx.user.id,
        ai_profiles=iv.ai_profiles,
        execution=iv.plan["_execution"],
        operation_id=iv.id,
        stage="planning",
        interview_id=iv.id,
        engine=session.bind,
        validate=lambda output: validate_plan(output, iv.duration_minutes),
    )
    iv.plan = {**plan.model_dump(), **iv.plan}
    session.add(iv)
    session.flush()
    session.add(Turn(workspace_id=iv.workspace_id, interview_id=iv.id, position=0, question=plan.opening))
    session.commit()
    return public(session, iv)


def join(session, ctx, interview_id):
    iv = get_interview(session, ctx, interview_id, mutate=True)
    if iv.status == "lobby":
        session.execute(
            update(Interview)
            .where(Interview.id == iv.id, Interview.status == "lobby")
            .values(status="active", started_at=time.time(), version=Interview.version + 1)
        )
        session.commit()
        session.refresh(iv)
    return public(session, iv)


def apply_turn(session, ctx, interview_id, version, request_id, answer=None, audio=None):
    from .speech import transcribe

    iv = get_interview(session, ctx, interview_id, mutate=True)
    fingerprint = hashlib.sha256(audio if audio is not None else (answer or "").encode()).hexdigest()
    operation = session.exec(
        select(Operation).where(Operation.interview_id == iv.id, Operation.request_id == request_id)
    ).first()
    if operation:
        if operation.fingerprint != fingerprint:
            raise HTTPException(409, "This request ID was already used for a different answer")
        return operation.response
    if iv.status != "active":
        raise HTTPException(409, "This interview is not accepting answers")
    if time.time() > iv.started_at + iv.duration_minutes * 60 + 120:
        raise HTTPException(409, "The interview has expired. Finish it to see your report.")
    rate_limit(session, ctx.workspace)
    lease = uid()
    acquired = session.execute(
        update(Interview)
        .where(
            Interview.id == iv.id,
            Interview.workspace_id == ctx.workspace.id,
            Interview.version == version,
            Interview.status == "active",
            Interview.lock_until < time.time(),
        )
        .values(lock_token=lease, lock_until=time.time() + 150)
    )
    if acquired.rowcount != 1:
        session.rollback()
        raise HTTPException(409, "Another answer is being processed or this question changed. Reload the interview.")
    session.commit()
    try:
        consume(session, ctx.workspace)
        session.refresh(iv)
        turns = turns_for(session, iv)
        if not turns or turns[-1].answer is not None:
            raise HTTPException(409, "There is no open question")
        session.commit()
        text = transcribe(audio) if audio is not None else (answer or "").strip()
        if not text:
            response = {
                "transcript": "",
                "reply": "I couldn't hear speech. Please try again or type your answer.",
                "done": False,
                "repeat": True,
                "remaining_seconds": remaining(iv),
                "version": version,
            }
            # No answer is consumed; a fresh recording gets a fresh request ID.
            session.execute(
                update(Interview)
                .where(Interview.id == iv.id, Interview.lock_token == lease)
                .values(lock_token=None, lock_until=0)
            )
            session.commit()
            return response
        modern = iv.plan.get("_execution", {}).get("contract_revision", 2) >= 3
        decision = execute(
            "interviewer",
            live_context(iv, turns, text, remaining(iv)),
            InterviewDecision if modern else TurnDecision,
            workspace_id=iv.workspace_id,
            user_id=iv.user_id,
            interview_id=iv.id,
            ai_profiles=iv.ai_profiles,
            execution=iv.plan.get("_execution"),
            operation_id=request_id,
            stage="interview_turn",
            engine=session.bind,
            validate=(lambda output: validate_decision(output, iv, turns, text)) if modern else None,
        )
        topic, count = iv.current_topic, iv.followup_count
        bank = iv.plan["question_bank"]
        closing = CLOSINGS[brief_for(iv).language]
        done = remaining(iv) <= 120
        plan = dict(iv.plan)
        if modern:
            plan["_memory"] = update_memory(plan, decision)
            done = done or (decision.action == "finish" and remaining(iv) <= 180)
        if done:
            reply = closing
        elif decision.action == "follow_up" and count < 2:
            reply, count = decision.reply, count + 1
        else:
            # The model cannot skip coverage or exceed the follow-up cap.
            if modern:
                available = remaining_topics(iv)
                done = not available
                topic = (
                    (decision.next_topic if decision.next_topic is not None else available[0]) if available else topic
                )
                count = 0
                reply = (
                    closing if done else " ".join(filter(None, [decision.transition.strip(), bank[topic]["question"]]))
                )
                if not done:
                    plan["_visited_topics"] = list(dict.fromkeys([*plan.get("_visited_topics", [0]), topic]))
            else:
                topic, count = topic + 1, 0
                done = topic >= len(bank)
                reply = closing if done else bank[topic]["question"]
        result = session.execute(
            update(Interview)
            .where(Interview.id == iv.id, Interview.lock_token == lease, Interview.version == version)
            .values(
                version=version + 1,
                lock_token=None,
                lock_until=0,
                current_topic=topic,
                followup_count=count,
                status="complete" if done else "active",
                closing_remark=reply if done else None,
                ended_at=time.time() if done else None,
                plan=plan,
            )
        )
        if result.rowcount != 1:
            session.rollback()
            raise HTTPException(409, "The session changed while processing. Reload to recover its current state.")
        last = turns[-1]
        last.answer, last.assessment = text, None if modern else decision.assessment
        session.add(last)
        if not done:
            session.add(
                Turn(
                    workspace_id=iv.workspace_id,
                    interview_id=iv.id,
                    position=last.position + 1,
                    topic=topic,
                    question=reply,
                )
            )
        response = {
            "transcript": text,
            "reply": reply,
            "done": done,
            "repeat": False,
            "remaining_seconds": remaining(iv),
            "version": version + 1,
        }
        session.add(
            Operation(
                workspace_id=iv.workspace_id,
                interview_id=iv.id,
                request_id=request_id,
                fingerprint=fingerprint,
                response=response,
            )
        )
        session.commit()
        return response
    except Exception:
        session.rollback()
        session.execute(
            update(Interview)
            .where(Interview.id == iv.id, Interview.lock_token == lease)
            .values(lock_token=None, lock_until=0)
        )
        session.commit()
        raise


def finish(session, ctx, interview_id):
    iv = get_interview(session, ctx, interview_id, mutate=True)
    if iv.status == "finished":
        return public(session, iv)
    if iv.status == "finishing":
        return public(session, iv)
    if iv.status == "abandoned":
        raise HTTPException(409, "This interview was abandoned")
    if not any(t.answer for t in turns_for(session, iv)):
        raise HTTPException(400, "Answer at least one question before requesting a report")
    changed = session.execute(
        update(Interview)
        .where(
            Interview.id == iv.id,
            Interview.version == iv.version,
            Interview.lock_until < time.time(),
            Interview.status.in_(["active", "complete", "report_failed"]),
        )
        .values(status="finishing", ended_at=iv.ended_at or time.time(), version=Interview.version + 1)
    )
    if changed.rowcount != 1:
        session.rollback()
        session.refresh(iv)
        if iv.status in {"finished", "finishing"}:
            return public(session, iv)
        raise HTTPException(409, "An answer is still processing; try again in a moment")
    job = session.exec(select(AgentJob).where(AgentJob.interview_id == iv.id)).first()
    if job:
        job.status, job.attempts, job.error, job.available_at = "pending", 0, None, time.time()
        session.add(job)
    else:
        session.add(AgentJob(workspace_id=iv.workspace_id, user_id=iv.user_id, interview_id=iv.id))
    session.commit()
    session.refresh(iv)
    return public(session, iv)


def abandon(session, ctx, interview_id):
    iv = get_interview(session, ctx, interview_id, mutate=True)
    if iv.status in {"finishing", "finished"} or iv.lock_until > time.time():
        raise HTTPException(409, "This interview cannot be abandoned right now")
    changed = session.execute(
        update(Interview)
        .where(
            Interview.id == iv.id,
            Interview.version == iv.version,
            Interview.lock_until < time.time(),
            Interview.status.not_in(["finishing", "finished"]),
        )
        .values(status="abandoned", ended_at=time.time(), version=Interview.version + 1)
    )
    if changed.rowcount != 1:
        session.rollback()
        raise HTTPException(409, "This session changed; reload before leaving")
    session.commit()
    return {"ok": True}
