"""Stable skill vocabulary and candidate-scoped merging of unfinished practice goals."""

import hashlib

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import select

from ..models import PracticeTask, PracticeTaskSource, uid

SKILLS = {
    "technical_reasoning": "Domain reasoning",
    "trade_offs": "Trade-offs",
    "validation": "Validation",
    "debugging": "Problem diagnosis",
    "ownership": "Individual ownership",
    "outcomes": "Evidence of outcomes",
    "communication": "Clear explanations",
    "role_alignment": "Role alignment",
    "collaboration": "Collaboration",
    "leadership": "Leadership and influence",
    "reflection": "Reflection and learning",
}


def active_key(workspace_id, user_id, role, skill_id, exercise_type):
    parts = (workspace_id, user_id, " ".join(role.lower().split()), skill_id, exercise_type)
    return hashlib.sha256("\0".join(parts).encode()).hexdigest()


def unfinished(session, iv):
    return [
        {"skill_id": task.skill_id, "exercise_type": task.exercise_type, "title": task.title}
        for task in session.exec(
            select(PracticeTask)
            .where(
                PracticeTask.workspace_id == iv.workspace_id,
                PracticeTask.user_id == iv.user_id,
                PracticeTask.completed_at.is_(None),
                PracticeTask.skill_id.is_not(None),
            )
            .limit(30)
        ).all()
    ]


def publish(session, iv, drills):
    """Part of the report publication transaction; caller alone may commit."""
    insert = sqlite_insert if session.bind.dialect.name == "sqlite" else pg_insert
    for drill in drills:
        key = active_key(iv.workspace_id, iv.user_id, iv.job_title, drill.skill_id, drill.exercise_type)
        values = PracticeTask(
            id=uid(),
            workspace_id=iv.workspace_id,
            user_id=iv.user_id,
            interview_id=iv.id,
            title=drill.title,
            instructions=drill.instructions,
            skill=SKILLS[drill.skill_id],
            skill_id=drill.skill_id,
            exercise_type=drill.exercise_type,
            minutes=drill.minutes,
            active_key=key,
        ).model_dump()
        session.execute(insert(PracticeTask).values(**values).on_conflict_do_nothing(index_elements=["active_key"]))
        task = session.exec(
            select(PracticeTask).where(
                PracticeTask.active_key == key,
                PracticeTask.workspace_id == iv.workspace_id,
                PracticeTask.user_id == iv.user_id,
            )
        ).one()
        session.execute(insert(PracticeTaskSource).values(task_id=task.id, interview_id=iv.id).on_conflict_do_nothing())
