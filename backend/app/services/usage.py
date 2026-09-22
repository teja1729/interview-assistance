"""Atomic, database-backed usage limits shared by all API/worker processes."""

from datetime import UTC, datetime

from fastapi import HTTPException
from sqlalchemy import update
from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert

from ..config import settings
from ..models import UsageBucket

PLANS = {
    "free": {"name": "Starter", "interviews": 3, "ai_calls": 150, "seats": 1},
    "pro": {"name": "Pro", "interviews": 40, "ai_calls": 2000, "seats": 1},
    # Retained for existing Stripe subscriptions; no new team checkout is offered.
    "team": {"name": "Legacy", "interviews": 200, "ai_calls": 10000, "seats": 10},
}


def period():
    return datetime.now(UTC).strftime("%Y-%m")


def plan_limits(workspace):
    plan = dict(PLANS.get(workspace.plan, PLANS["free"]))
    if settings.environment == "development" and settings.local_usage_overrides:
        plan.update(interviews=max(0, settings.local_interview_limit), ai_calls=max(0, settings.local_ai_call_limit))
    return plan


def consume(session, workspace, resource="ai_calls", limit=None, bucket_period=None):
    """Reserve before paid work. Failed calls count: otherwise failures bypass spend limits."""
    ceiling = limit if limit is not None else plan_limits(workspace)[resource]
    key = {"workspace_id": workspace.id, "period": bucket_period or period(), "resource": resource}
    insert = sqlite_insert if session.bind.dialect.name == "sqlite" else pg_insert
    session.execute(insert(UsageBucket).values(**key, used=0).on_conflict_do_nothing())
    result = session.execute(
        update(UsageBucket)
        .where(
            UsageBucket.workspace_id == key["workspace_id"],
            UsageBucket.period == key["period"],
            UsageBucket.resource == resource,
            UsageBucket.used < ceiling,
        )
        .values(used=UsageBucket.used + 1)
    )
    if result.rowcount != 1:
        session.rollback()
        if resource == "requests":
            raise HTTPException(
                429, "Too many requests in a minute. Wait briefly and try again.", headers={"Retry-After": "60"}
            )
        label = "interview" if resource == "interviews" else "AI call"
        raise HTTPException(
            429, f"Monthly {label} allowance reached ({ceiling}/{ceiling}). Check Plans & usage for your limits."
        )
    session.commit()


def rate_limit(session, workspace):
    consume(session, workspace, "requests", limit=30, bucket_period=datetime.now(UTC).strftime("%Y-%m-%dT%H:%M"))


def summary(session, workspace):
    plan = plan_limits(workspace)
    return {
        "plan": workspace.plan,
        "plan_name": plan["name"],
        "local_development_allowance": settings.environment == "development" and settings.local_usage_overrides,
        "period": period(),
        "resources": {
            key: {
                "used": (bucket.used if (bucket := session.get(UsageBucket, (workspace.id, period(), key))) else 0),
                "limit": plan[key],
            }
            for key in ("interviews", "ai_calls")
        },
        "seats": plan["seats"],
    }
