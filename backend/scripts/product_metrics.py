"""Print aggregate, content-free candidate funnel and latency metrics from the configured DB."""

import argparse
import json
import math
import statistics
import time
from collections import defaultdict

from sqlmodel import Session, select

from app import db
from app.models import AgentJob, AgentRun, Interview, PracticeTask


def build_metrics(session, since):
    interviews = session.exec(
        select(Interview.user_id, Interview.status, Interview.started_at).where(Interview.created_at >= since)
    ).all()
    jobs = session.exec(
        select(AgentJob.status, AgentJob.created_at, AgentJob.completed_at).where(AgentJob.created_at >= since)
    ).all()
    tasks = session.exec(
        select(PracticeTask.created_at, PracticeTask.completed_at).where(PracticeTask.created_at >= since)
    ).all()
    runs = session.exec(
        select(AgentRun.agent, AgentRun.provider, AgentRun.prompt_version, AgentRun.status, AgentRun.duration_ms).where(
            AgentRun.created_at >= since
        )
    ).all()

    completed_by_user = defaultdict(int)
    for user_id, status, _ in interviews:
        if status == "finished":
            completed_by_user[user_id] += 1
    started = sum(started_at is not None for _, _, started_at in interviews)
    finished = sum(status == "finished" for _, status, _ in interviews)
    completed_reports = [job for job in jobs if job.status == "succeeded" and job.completed_at is not None]
    report_latencies = [max(0, job.completed_at - job.created_at) * 1000 for job in completed_reports]

    run_groups = defaultdict(list)
    for agent, provider, prompt_version, status, duration_ms in runs:
        run_groups[(agent, provider, prompt_version)].append((status, duration_ms))

    def p95(values):
        return sorted(values)[math.ceil(0.95 * len(values)) - 1] if values else None

    return {
        "window_started_at": since,
        "interviews": {
            "created": len(interviews),
            "started": started,
            "finished": finished,
            "start_to_finish_rate": round(finished / started, 3) if started else None,
            "users_with_multiple_finished": sum(count >= 2 for count in completed_by_user.values()),
            "users_with_finished": len(completed_by_user),
        },
        "reports": {
            "succeeded": sum(job.status == "succeeded" for job in jobs),
            "failed": sum(job.status == "failed" for job in jobs),
            "pending_or_running": sum(job.status in {"pending", "running"} for job in jobs),
            "completed_latency_ms_median": round(statistics.median(report_latencies)) if report_latencies else None,
            "completed_latency_ms_p95": round(p95(report_latencies)) if report_latencies else None,
        },
        "practice": {
            "tasks_created": len(tasks),
            "tasks_completed": sum(completed_at is not None for _, completed_at in tasks),
        },
        "agent_runs": [
            {
                "agent": agent,
                "provider": provider,
                "prompt_version": prompt_version,
                "runs": len(values),
                "mean_latency_ms": round(statistics.mean(duration for _, duration in values)),
                "p95_latency_ms": p95([duration for _, duration in values]),
                "failures": sum(status != "succeeded" for status, _ in values),
            }
            for (agent, provider, prompt_version), values in sorted(run_groups.items())
        ],
        "notes": [
            "Aggregates only; no transcript, resume, email, or candidate identifiers are emitted.",
            "Report latency is available only for jobs completed after the completion timestamp migration.",
            "Repeat practice is a directional count, not a cohort retention rate.",
        ],
    }


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--days", type=int, default=30)
    args = parser.parse_args()
    if not 1 <= args.days <= 365:
        parser.error("--days must be between 1 and 365")
    since = time.time() - args.days * 86400
    with Session(db.engine) as session:
        print(json.dumps(build_metrics(session, since), indent=2))


if __name__ == "__main__":
    main()
