"""Explicit paid smoke check of topic -> summary -> coaching -> atomic publication.

Runs one synthetic reference answer in a disposable database. Never reads candidate data.
Use the evaluation suite for score/action drift; this verifies the complete worker path.
"""

import argparse
import tempfile

from sqlmodel import Session, SQLModel, select

from app import db
from app.agents.specs import snapshot
from app.models import AgentJob, Interview, PracticeTask, Turn, User, Workspace
from app.personas import persona_definition
from app.providers.base import agent_profiles, profiles
from app.schemas import CompanyBrief, InterviewBrief
from app.services.reports import process_one
from scripts.run_evaluations import ROOT, load_cases


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--accept-cost", action="store_true")
    parser.add_argument("--case-id", default="technical-idempotency-strong")
    args = parser.parse_args()
    cases = load_cases(ROOT / "evaluations/cases.json")["cases"]
    case = next((c for c in cases if c["id"] == args.case_id), None)
    if case is None:
        parser.error("Unknown reference case")
    if not args.live:
        print("Synthetic report case validated offline; use --live --accept-cost to run the worker with real models.")
        return 0
    if not args.accept_cost:
        parser.error("Real model calls require --accept-cost")
    routing = {role: value for role, value in agent_profiles().items() if role in {"evaluator", "coach"}}
    registry = profiles()
    if any(registry[value].provider == "demo" for value in routing.values()):
        parser.error("Live smoke checks require real profiles")
    with tempfile.TemporaryDirectory(prefix="report-smoke-") as directory:
        engine = db.make_engine(f"sqlite:///{directory}/smoke.db")
        try:
            SQLModel.metadata.create_all(engine)
            execution = snapshot(routing, engine)
            with Session(engine, expire_on_commit=False) as session:
                user = User(google_sub="synthetic-smoke", email="smoke@example.invalid", name="Synthetic report")
                account = Workspace(name="Synthetic report")
                session.add(user)
                session.add(account)
                session.commit()
                persona = persona_definition(case["persona"])
                brief = InterviewBrief(
                    job_title=case["role"],
                    company="",
                    experience_years=4,
                    job_description="",
                    resume="",
                    custom_instructions="",
                    language=case["language"],
                    company_context=CompanyBrief(company="", status="not_requested"),
                )
                iv = Interview(
                    workspace_id=account.id,
                    user_id=user.id,
                    job_title=case["role"],
                    persona=case["persona"],
                    status="finishing",
                    ai_profiles=routing,
                    plan={
                        "_execution": execution,
                        "_persona": persona,
                        "_rubric": persona["rubric"],
                        "_brief": brief.model_dump(),
                    },
                )
                session.add(iv)
                session.flush()
                session.add(
                    Turn(
                        workspace_id=account.id,
                        interview_id=iv.id,
                        position=0,
                        topic=0,
                        question=case["question"],
                        answer=case["answer"],
                    )
                )
                session.add(AgentJob(workspace_id=account.id, user_id=user.id, interview_id=iv.id))
                session.commit()
                identifier = iv.id
            process_one(engine)
            with Session(engine) as session:
                iv = session.get(Interview, identifier)
                job = session.exec(select(AgentJob)).one()
                print(
                    f"Status: {iv.status}; completed stages: {len(job.artifacts.get('steps', {}))}; error: {job.error or 'none'}"
                )
                if iv.status != "finished":
                    return 1
                print(
                    f"Practice score: {iv.score}; tasks: {len(session.exec(select(PracticeTask)).all())}; communication dimensions: clarity, structure"
                )
                return 0
        finally:
            engine.dispose()


if __name__ == "__main__":
    raise SystemExit(main())
