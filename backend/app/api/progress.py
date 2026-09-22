"""Candidate-owned progress, computed from persisted sessions rather than seeded charts."""

from fastapi import APIRouter, Depends
from sqlalchemy import func
from sqlmodel import Session, select

from ..auth import Context, current_context
from ..db import get_session
from ..models import Interview, PracticeTask
from ..personas import persona_definition

router = APIRouter(prefix="/api/progress", tags=["progress"])


@router.get("")
def progress(ctx: Context = Depends(current_context), session: Session = Depends(get_session)):
    owned = (
        Interview.user_id == ctx.user.id,
        Interview.workspace_id == ctx.workspace.id,
        Interview.status == "finished",
    )
    count, scored, average = session.exec(
        select(func.count(Interview.id), func.count(Interview.score), func.avg(Interview.score)).where(*owned)
    ).one()
    recent = session.exec(
        select(Interview).where(*owned).order_by(Interview.ended_at.desc(), Interview.created_at.desc()).limit(100)
    ).all()
    by_round = session.exec(
        select(Interview.persona, func.count(Interview.id), func.avg(Interview.score))
        .where(*owned)
        .group_by(Interview.persona)
    ).all()
    tasks, completed = session.exec(
        select(func.count(PracticeTask.id), func.count(PracticeTask.completed_at)).where(
            PracticeTask.user_id == ctx.user.id, PracticeTask.workspace_id == ctx.workspace.id
        )
    ).one()
    return {
        "completed_interviews": count,
        "scored_interviews": scored,
        "average_score": round(average, 1) if average is not None else None,
        "practice_tasks": tasks,
        "completed_tasks": completed,
        "rounds": [
            {
                "id": name,
                "name": persona_definition(name)["round"],
                "count": n,
                "average_score": round(avg, 1) if avg is not None else None,
            }
            for name, n, avg in by_round
        ],
        "recent": [
            {"id": i.id, "score": i.score, "at": i.ended_at or i.created_at, "label": i.job_title, "persona": i.persona}
            for i in recent
        ],
    }
