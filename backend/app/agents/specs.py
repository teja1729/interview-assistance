"""Immutable, non-secret execution bundles. Credential values are resolved only at execution.

Prompt text is retained with its hash so an in-flight interview survives a deploy. Contract
revisions fail explicitly when unsupported. Add a migration/adapter before retiring a revision.
"""

import hashlib
import json
import os
import time
from dataclasses import asdict, dataclass
from pathlib import Path

from sqlalchemy.dialects.postgresql import insert as pg_insert
from sqlalchemy.dialects.sqlite import insert as sqlite_insert
from sqlmodel import Session

from .. import db
from ..models import PromptBundle
from ..providers.base import Profile, ProviderError, profiles

PROMPTS = Path(__file__).parent / "prompts"
CONTRACT_REVISION = 3
VARIANTS = {
    ("interviewer", "TurnDecision"): "legacy_interviewer",
    ("assistant", "JobDescriptionDraft"): "job_description",
    ("evaluator", "TopicEvaluation"): "topic_evaluation",
    ("evaluator", "ReportSummary"): "report_summary",
    ("evaluator", "TopicAssessment"): "topic_assessment",
    ("evaluator", "EvidenceReportSummary"): "evidence_summary",
    ("coach", "SkillCoachingPlan"): "skill_coach",
}
ROLE_PROMPTS = {
    "planner": ["planner"],
    "interviewer": ["interviewer"],
    "evaluator": ["topic_assessment", "evidence_summary"],
    "coach": ["skill_coach"],
    "assistant": ["assistant", "job_description"],
    "resume": ["resume"],
    "company_research": ["company_research"],
}


@dataclass(frozen=True)
class Policy:
    deadline: float
    attempt_timeout: float
    output_tokens: int


POLICIES = {
    "interviewer": Policy(28, 14, 1200),
    "planner": Policy(70, 35, 3000),
    "evaluator": Policy(90, 45, 4000),
    "coach": Policy(50, 25, 2000),
    "resume": Policy(60, 30, 4000),
    "assistant": Policy(60, 30, 3000),
    "company_research": Policy(35, 30, 2400),
}


def prompt_name(agent, schema):
    return VARIANTS.get((agent, schema.__name__), agent)


def digest(value):
    return hashlib.sha256(value.encode()).hexdigest()


def load_prompt(name):
    return (PROMPTS / "_preamble.md").read_text() + "\n\n" + (PROMPTS / f"{name}.md").read_text()


def bundle_hash(prompts):
    return digest(json.dumps(prompts, sort_keys=True, ensure_ascii=False))


def save_prompts(prompts, engine=None):
    """Insert once by content hash; existing records are never updated."""
    identifier = bundle_hash(prompts)
    with Session(engine or db.engine) as session:
        insert = sqlite_insert if session.bind.dialect.name == "sqlite" else pg_insert
        session.execute(
            insert(PromptBundle).values(id=identifier, prompts=prompts, created_at=time.time()).on_conflict_do_nothing()
        )
        session.commit()
    return identifier


def bundle_prompts(bundle, engine=None):
    if "prompts" in bundle:  # Revision 2 interviews and portable evaluation manifests.
        return bundle["prompts"]
    with Session(engine or db.engine) as session:
        saved = session.get(PromptBundle, bundle.get("prompt_bundle_id"))
        if not saved or bundle_hash(saved.prompts) != saved.id:
            raise ProviderError("The saved prompt bundle is missing or invalid.", category="configuration")
        return saved.prompts


def snapshot(routing, engine=None):
    registry = profiles()
    roles = {}
    for role, profile_id in routing.items():
        primary = registry.get(profile_id)
        if primary is None:
            raise ProviderError("An assigned model profile is missing.", category="configuration")
        candidates = [primary]
        if primary.fallback:
            fallback = registry.get(primary.fallback)
            if fallback is None:
                raise ProviderError("An assigned fallback profile is missing.", category="configuration")
            if primary.provider != "demo" and fallback.provider == "demo":
                raise ProviderError("Live services cannot use test fallbacks.", category="configuration")
            candidates.append(fallback)
        roles[role] = {
            "profiles": [
                {key: value for key, value in asdict(p).items() if key not in {"api_key", "fallback"}}
                for p in candidates
            ],
            "policy": asdict(POLICIES[role]),
        }
    names = sorted({name for role in routing for name in ROLE_PROMPTS[role]})
    prompts = {name: {"text": text, "hash": digest(text)} for name in names if (text := load_prompt(name))}
    return {"contract_revision": CONTRACT_REVISION, "roles": roles, "prompt_bundle_id": save_prompts(prompts, engine)}


def resolve(bundle, agent, schema, engine=None):
    if bundle.get("contract_revision") not in {2, CONTRACT_REVISION}:
        raise ProviderError("This interview requires an unsupported contract revision.", category="configuration")
    try:
        role = bundle["roles"][agent]
        name = (
            "interviewer"
            if bundle.get("contract_revision") == 2 and agent == "interviewer"
            else prompt_name(agent, schema)
        )
        saved = bundle_prompts(bundle, engine)[name]
        if digest(saved["text"]) != saved["hash"]:
            raise ValueError("Prompt integrity")
        candidates = [Profile(**p, api_key=os.getenv(p["api_key_env"], "")) for p in role["profiles"]]
        return candidates, Policy(**role["policy"]), saved["text"], saved["hash"][:12]
    except (KeyError, TypeError, ValueError) as exc:
        raise ProviderError("The saved execution configuration is incomplete.", category="configuration") from exc
