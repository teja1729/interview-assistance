"""Checkpointed topic evaluation -> report summary -> coaching, with atomic publication.

Each checkpoint renews a fenced lease. Validated artifacts survive worker restarts and coach
failures, but remain private until the whole report/practice transaction is ready to publish.
"""

import hashlib
import json
import logging
import time
import tomllib
from copy import deepcopy

from fastapi import HTTPException
from sqlalchemy import or_, update
from sqlmodel import Session, select

from .. import db
from ..agents import specs
from ..agents.context import agent_context
from ..agents.runtime import classify, trace
from ..agents.specs import snapshot
from ..agents.tokens import input_estimate
from ..config import settings
from ..models import AgentJob, Interview, PracticeTask, Workspace, uid
from ..personas import persona_definition
from ..providers.base import InvalidOutput, ProviderError
from ..schemas import (
    CoachingPlan,
    EvidenceReportSummary,
    PracticeReport,
    ReportSummary,
    SkillCoachingPlan,
    TopicAssessment,
    TopicEvaluation,
)
from . import practice
from .assessment import communication_samples, topic_score, validate_assessment, validate_summary
from .interviews import turns_for
from .report_stages import Stage, StageRunner

log = logging.getLogger(__name__)


class LostLease(Exception):
    pass


def fingerprint(value):
    return hashlib.sha256(json.dumps(value, sort_keys=True, ensure_ascii=False).encode()).hexdigest()


def evidence_turns(turns):
    # Never pass the interviewer's private assessment into an independent evaluation.
    return [
        {"answer_id": t.id, "question": t.question, "answer": t.answer, "topic": t.topic} for t in turns if t.answer
    ]


def topic_batches(turns, limit=48000):
    """Keep every answer byte; split only large topic inputs, retaining original answer IDs."""
    batches, batch, size = [], [], 0
    for turn in turns:
        remaining = turn["answer"]
        while remaining:
            # A Unicode code point uses at most four UTF-8 bytes. Binary search avoids splitting it.
            lo, hi = 1, len(remaining)
            while lo < hi:
                mid = (lo + hi + 1) // 2
                if len(remaining[:mid].encode()) <= limit:
                    lo = mid
                else:
                    hi = mid - 1
            part, remaining = remaining[:lo], remaining[lo:]
            amount = len(part.encode())
            if batch and size + amount > limit:
                batches.append(batch)
                batch, size = [], 0
            batch.append({**turn, "answer": part})
            size += amount
    if batch:
        batches.append(batch)
    return batches


def validate_topic(output, topic, turns):
    if output.topic != topic:
        raise InvalidOutput("topic_must_match_requested_id")
    for evidence in output.evidence:
        if not evidence.quote.strip() or not any(
            t["answer_id"] == evidence.answer_id and evidence.quote in t["answer"] for t in turns
        ):
            raise InvalidOutput("evidence_must_quote_the_identified_answer_exactly")


def checkpoint(session, job, lease, artifacts):
    changed = session.execute(
        update(AgentJob)
        .where(AgentJob.id == job.id, AgentJob.lease_token == lease, AgentJob.status == "running")
        .values(artifacts=deepcopy(artifacts), lease_until=time.time() + 240)
    )
    if changed.rowcount != 1:
        session.rollback()
        raise LostLease()
    session.commit()


def process_one(engine=None):
    engine = engine or db.engine
    with Session(engine, expire_on_commit=False) as session:
        now = time.time()
        candidates = session.exec(
            select(AgentJob)
            .where(
                AgentJob.available_at <= now,
                or_(AgentJob.status == "pending", (AgentJob.status == "running") & (AgentJob.lease_until < now)),
            )
            .order_by(AgentJob.created_at)
            .limit(10)
        ).all()
        job = None
        for candidate in candidates:
            lease = uid()
            changed = session.execute(
                update(AgentJob)
                .where(
                    AgentJob.id == candidate.id,
                    or_(AgentJob.status == "pending", (AgentJob.status == "running") & (AgentJob.lease_until < now)),
                )
                .values(status="running", lease_token=lease, lease_until=now + 240, attempts=AgentJob.attempts + 1)
            )
            session.commit()
            if changed.rowcount == 1:
                session.refresh(candidate)
                job = candidate
                break
        if not job:
            return False
        try:
            if job.attempts > 3:
                raise ProviderError("Report retry budget exhausted.", category="permanent")
            iv = session.get(Interview, job.interview_id)
            workspace = session.get(Workspace, job.workspace_id)
            turns = evidence_turns(turns_for(session, iv))
            if not turns:
                raise ProviderError("No answered questions to evaluate.", category="permanent")
            artifacts = deepcopy(job.artifacts or {})
            input_hash = fingerprint({"turns": turns, "interview": iv.id})
            if artifacts and artifacts.get("input_hash") != input_hash:
                raise ProviderError("Report input changed after it was frozen.", category="permanent")
            if not artifacts:
                artifacts = {
                    "input_hash": input_hash,
                    "steps": {},
                    "execution": iv.plan.get("_execution")
                    or snapshot(
                        {
                            k: v
                            for k, v in iv.ai_profiles.items()
                            if k in {"planner", "interviewer", "evaluator", "coach"}
                        },
                        engine,
                    ),
                    "context": agent_context(iv, iv.job_title, evaluator=True),
                    "rubric": iv.plan.get("_rubric") or persona_definition(iv.persona)["rubric"],
                    "unfinished_practice": practice.unfinished(session, iv),
                }
                checkpoint(session, job, lease, artifacts)
            # Old checkpoints may contain raw custom preferences. Do not forward them to scoring.
            context = {
                k: v
                for k, v in artifacts["context"].items()
                if k in {"job_title", "experience_years", "language", "interview_profile"}
            }
            modern = artifacts["execution"].get("contract_revision", 2) >= 3
            rubric = artifacts.get("rubric") or persona_definition(iv.persona)["rubric"]
            if modern:
                context["rubric"] = rubric
            kwargs = {
                "workspace_id": job.workspace_id,
                "user_id": job.user_id,
                "interview_id": iv.id,
                "ai_profiles": iv.ai_profiles,
                "execution": artifacts["execution"],
                "engine": engine,
                "operation_id": job.id,
            }

            runner = StageRunner(
                session, workspace, artifacts, lambda: checkpoint(session, job, lease, artifacts), kwargs
            )
            run_stage = runner.run
            schema = TopicAssessment if modern else TopicEvaluation
            validator = (
                (lambda output, tp, ts: validate_assessment(output, tp, ts, rubric)) if modern else validate_topic
            )
            candidates, policy, prompt, _ = specs.resolve(artifacts["execution"], "evaluator", schema, engine)
            # Leave room for question text, wrappers and merge metadata, using the smallest fallback.
            spare = (
                min(
                    p.context_tokens - input_estimate(context, prompt, schema, p.tokenizer) - policy.output_tokens
                    for p in candidates
                )
                - 6000
            )
            batch_limit = max(512, min(48000, int(spare / 1.5)))
            with settings.models_file.open("rb") as config:
                concurrency = max(1, min(4, tomllib.load(config).get("execution", {}).get("report_concurrency", 2)))
            by_topic = {
                topic: [t for t in turns if t["topic"] == topic] for topic in sorted({t["topic"] for t in turns})
            }
            batches_by_topic = {
                topic: topic_batches(topic_turns, batch_limit) for topic, topic_turns in by_topic.items()
            }
            stages = [
                Stage(
                    f"topic:{topic}:part:{index}",
                    "evaluator",
                    {**context, "topic": topic, "turns": batch, "part": index + 1, "parts": len(batches)},
                    schema,
                    lambda output, ts=batch, tp=topic: validator(output, tp, ts),
                )
                for topic, batches in batches_by_topic.items()
                for index, batch in enumerate(batches)
            ]
            completed = runner.parallel(stages, concurrency)
            questions = []
            for topic, topic_turns in by_topic.items():
                pieces = [completed[f"topic:{topic}:part:{index}"] for index in range(len(batches_by_topic[topic]))]
                value = pieces[0]
                if len(pieces) > 1:
                    # Merge bounded validated assessments, with exact original evidence snippets.
                    quoted = [
                        {
                            "answer_id": e.answer_id,
                            "answer": e.quote,
                            "topic": topic,
                            "question": topic_turns[0]["question"],
                        }
                        for part in pieces
                        for e in part.evidence
                    ]
                    value = run_stage(
                        f"topic:{topic}:merge",
                        "evaluator",
                        {
                            **context,
                            "topic": topic,
                            "turns": quoted,
                            "validated_parts": [p.model_dump() for p in pieces],
                        },
                        schema,
                        lambda output, ts=quoted, tp=topic: validator(output, tp, ts),
                    )
                questions.append(
                    {
                        "topic": topic,
                        "question": topic_turns[0]["question"],
                        "answer_summary": value.answer_summary,
                        "score": topic_score(value, rubric) if modern else sum(value.rubric.model_dump().values()),
                        "feedback": value.feedback,
                        "ideal_answer": value.ideal_answer,
                        "evidence": [e.quote for e in value.evidence],
                        "evidence_refs": [e.model_dump() for e in value.evidence],
                        "rubric": {r.criterion: r.score for r in value.ratings}
                        if modern
                        else value.rubric.model_dump(),
                        "ratings": [r.model_dump() for r in value.ratings] if modern else [],
                    }
                )
            scored = [q["score"] for q in questions if q["score"] is not None]
            score = round(sum(scored) / len(scored) * 10) if scored else None
            verdict = (
                "insufficient_evidence"
                if score is None
                else "strong_hire"
                if score >= 85
                else "hire"
                if score >= 70
                else "lean_hire"
                if score >= 55
                else "no_hire"
            )
            # Communication gets separate verbatim samples, never inferred from topic scores.
            assessments = [
                {k: v for k, v in q.items() if k not in {"ideal_answer", "evidence_refs"}} for q in questions
            ]
            samples = communication_samples(turns)
            summary = run_stage(
                "report_summary",
                "evaluator",
                {
                    **context,
                    "assessments": assessments,
                    "overall_score": score,
                    "verdict": verdict,
                    **({"communication_samples": samples} if modern else {}),
                },
                EvidenceReportSummary if modern else ReportSummary,
                (lambda output: validate_summary(output, samples)) if modern else None,
            )
            report = {
                **summary.model_dump(),
                "questions": questions,
                "rubric_definition": rubric if modern else None,
                "assessment_version": 3 if modern else 2,
                "overall_score": score,
                "verdict": verdict,
                "verdict_reason": (
                    f"Practice score: {score}/100, calculated from {len(scored)} assessed topics. Rubric weights are provisional; this is not a hiring prediction."
                    if score is not None
                    else "There is insufficient applicable evidence to calculate a practice score."
                ),
            }
            if modern:
                report = PracticeReport.model_validate(report).model_dump()
            coaching = run_stage(
                "coaching",
                "coach",
                {
                    "report": {**report, "questions": assessments},
                    "language": context["language"],
                    "job_title": iv.job_title,
                    "interview_profile": context["interview_profile"],
                    "skill_catalog": practice.SKILLS,
                    "unfinished_goals": artifacts.get("unfinished_practice", []),
                },
                SkillCoachingPlan if modern else CoachingPlan,
            )
            changed = session.execute(
                update(AgentJob)
                .where(AgentJob.id == job.id, AgentJob.lease_token == lease)
                .values(status="succeeded", error=None, lease_token=None, lease_until=0)
            )
            if changed.rowcount != 1:
                session.rollback()
                raise LostLease()
            iv.report, iv.score, iv.status = report, score, "finished"
            session.add(iv)
            if modern:
                practice.publish(session, iv, coaching.tasks)
            else:
                for task in coaching.tasks:
                    session.add(
                        PracticeTask(
                            **task.model_dump(), workspace_id=iv.workspace_id, user_id=iv.user_id, interview_id=iv.id
                        )
                    )
            session.commit()
            trace(
                engine,
                workspace_id=job.workspace_id,
                user_id=job.user_id,
                interview_id=iv.id,
                agent="report_workflow",
                prompt_version="v3" if modern else "v2",
                provider="application",
                model="validated-artifacts",
                operation_id=job.id,
                stage="publication",
                status="succeeded",
                duration_ms=0,
            )
        except LostLease:
            session.rollback()
        except Exception as exc:  # noqa: BLE001 - durable boundary persists a sanitized failure category
            session.rollback()
            failure = classify(exc)
            if isinstance(exc, HTTPException) and exc.status_code == 429:
                failure = ProviderError(
                    "Account AI usage limit reached. Check Billing before retrying.", category="budget"
                )
            terminal = job.attempts >= 3 or failure.category not in {"transient", "rate_limited"}
            log.warning("report job=%s category=%s", job.id, failure.category)
            changed = session.execute(
                update(AgentJob)
                .where(AgentJob.id == job.id, AgentJob.lease_token == lease)
                .values(
                    status="failed" if terminal else "pending",
                    lease_token=None,
                    lease_until=0,
                    error=str(failure),
                    available_at=time.time() + max(5 * job.attempts, failure.retry_after),
                )
            )
            if changed.rowcount == 1 and terminal:
                session.execute(
                    update(Interview).where(Interview.id == job.interview_id).values(status="report_failed")
                )
            session.commit()
        return True
