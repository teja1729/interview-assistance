"""Follow-through on the coach's drills and observable agent execution history."""

import time

from fastapi import APIRouter, Depends, HTTPException
from pydantic import BaseModel
from sqlalchemy.exc import IntegrityError
from sqlmodel import Session, select

from ..auth import Context, current_context
from ..db import get_session
from ..models import AgentRun, Interview, PracticeTask, PracticeTaskSource
from ..services.practice import active_key

router = APIRouter(prefix="/api", tags=["practice"])


class CompleteInput(BaseModel):
    completed: bool


@router.get("/practice")
def tasks(ctx: Context = Depends(current_context), session: Session = Depends(get_session)):
    tasks = session.exec(
        select(PracticeTask)
        .where(PracticeTask.workspace_id == ctx.workspace.id, PracticeTask.user_id == ctx.user.id)
        .order_by(PracticeTask.created_at.desc())
        .limit(200)
    ).all()
    if not tasks:
        return []
    sources = session.exec(
        select(PracticeTaskSource).where(PracticeTaskSource.task_id.in_([t.id for t in tasks]))
    ).all()
    return [
        {
            **task.model_dump(exclude={"active_key", "workspace_id", "user_id"}),
            "source_interview_ids": list(
                dict.fromkeys([task.interview_id, *[s.interview_id for s in sources if s.task_id == task.id]])
            ),
        }
        for task in tasks
    ]


@router.patch("/practice/{task_id}")
def complete(
    task_id: str, body: CompleteInput, ctx: Context = Depends(current_context), session: Session = Depends(get_session)
):
    task = session.get(PracticeTask, task_id)
    if not task or task.workspace_id != ctx.workspace.id or task.user_id != ctx.user.id:
        raise HTTPException(404, "Practice task not found")
    task.completed_at = time.time() if body.completed else None
    if task.skill_id:
        interview = session.get(Interview, task.interview_id)
        task.active_key = (
            None
            if body.completed
            else active_key(task.workspace_id, task.user_id, interview.job_title, task.skill_id, task.exercise_type)
        )
    session.add(task)
    try:
        session.commit()
    except IntegrityError as exc:
        session.rollback()
        raise HTTPException(409, "An equivalent exercise is already active in your practice plan.") from exc
    return task.model_dump(exclude={"active_key", "workspace_id", "user_id"})


@router.get("/agent-runs")
def runs(ctx: Context = Depends(current_context), session: Session = Depends(get_session)):
    query = select(AgentRun).where(AgentRun.workspace_id == ctx.workspace.id, AgentRun.user_id == ctx.user.id)
    return session.exec(query.order_by(AgentRun.created_at.desc()).limit(100)).all()
