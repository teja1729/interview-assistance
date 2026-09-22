"""Explicit paid operator smoke check. Never imported by tests or application startup."""

import argparse
import tempfile

from sqlmodel import Session, SQLModel

from app import db
from app.agents.runtime import classify, execute
from app.models import User, Workspace
from app.schemas import CompanyBrief, CompanyResearchInput
from app.services.company_research import validate_research


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--company", required=True)
    parser.add_argument("--role", required=True)
    parser.add_argument("--url", default="")
    args = parser.parse_args()
    body = CompanyResearchInput(company=args.company, job_title=args.role, company_url=args.url)
    try:
        # Only this temporary operator-owned database uses create_all; application startup uses Alembic.
        with tempfile.TemporaryDirectory(prefix="research-smoke-") as directory:
            engine = db.make_engine(f"sqlite:///{directory}/traces.db")
            try:
                SQLModel.metadata.create_all(engine)
                with Session(engine, expire_on_commit=False) as session:
                    user = User(google_sub="operator-smoke", email="smoke@example.invalid", name="Smoke test")
                    account = Workspace(name="Smoke test")
                    session.add(user)
                    session.add(account)
                    session.commit()
                    identity = account.id, user.id
                brief = execute(
                    "company_research",
                    {"company": body.company, "role": body.job_title, "official_url": body.company_url},
                    CompanyBrief,
                    workspace_id=identity[0],
                    user_id=identity[1],
                    engine=engine,
                    stage="operator_company_search",
                    validate=validate_research,
                )
            finally:
                engine.dispose()
    except Exception as exc:  # noqa: BLE001 - CLI reports only sanitized category
        print(f"Research failed: {classify(exc).category}. Check provider configuration/quota.")
        return 1
    print(f"Status: {brief.status}; {len(brief.facts)} cited facts; {len(brief.sources)} sources")
    for source in brief.sources:
        print(f"- {source.title}: {source.url}")
    if brief.status != "researched":
        print(brief.note)
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
