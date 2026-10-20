"""Vercel Queue subscribers for durable application jobs."""

import asyncio
import math
import time

from sqlmodel import Session
from vercel.queue import Message, RetryAfter, subscribe

from . import db
from .models import AgentJob
from .services.reports import process_one


@subscribe(topic="interview-reports", retry_after=30, max_concurrency=2, max_attempts=10)
async def generate_interview_report(message: Message[dict[str, str]]) -> None:
    """Run one durable report job, letting the database lease fence duplicate deliveries."""
    job_id = message.payload.get("job_id")
    if not job_id:
        return

    with Session(db.engine) as session:
        job = session.get(AgentJob, job_id)
        if job is None or job.status in {"succeeded", "failed"}:
            return
        now = time.time()
        if job.status == "running" and job.lease_until > now:
            raise RetryAfter(max(5, math.ceil(job.lease_until - now)), reason="report_job_leased")
        if job.available_at > now:
            raise RetryAfter(max(5, math.ceil(job.available_at - now)), reason="report_job_backoff")

    await asyncio.to_thread(process_one, db.engine, job_id)

    with Session(db.engine) as session:
        job = session.get(AgentJob, job_id)
        if job is None or job.status in {"succeeded", "failed"}:
            return
        now = time.time()
        if job.status == "running" and job.lease_until > now:
            raise RetryAfter(max(5, math.ceil(job.lease_until - now)), reason="report_job_still_running")
        if job.available_at > now:
            raise RetryAfter(max(5, math.ceil(job.available_at - now)), reason="report_job_backoff")
        raise RetryAfter(30, reason="report_job_not_claimed")
