"""Candidate-owned research cache. Runtime owns routing, deadlines, repair and traces.

Only company, role and optional public URL enter the search capability. Providers normalize their
own grounding metadata. An ordinary text model cannot silently substitute for sourced search.
"""

import hashlib
import json
import logging
import time

from fastapi import HTTPException
from sqlmodel import select

from ..agents.runtime import execute
from ..config import settings
from ..models import CompanyResearch
from ..providers.base import InvalidOutput, ProviderError
from ..providers.grounding import unavailable  # public parser import retained for operators/tests
from ..schemas import CompanyBrief
from .usage import consume, rate_limit

log = logging.getLogger(__name__)


def cache_key(company, job_title, company_url=""):
    return hashlib.sha256(
        json.dumps([company.strip().casefold(), job_title.strip().casefold(), company_url.strip()]).encode()
    ).hexdigest()


def validate_research(brief):
    if brief.status != "researched" or not brief.facts or not brief.sources:
        raise ProviderError(brief.note or "Search did not return sourced company facts.", category="ungrounded")
    identifiers = {source.id for source in brief.sources}
    if any(not set(fact.source_ids) <= identifiers for fact in brief.facts):
        raise InvalidOutput("search_fact_requires_known_source_ids")


def research(session, ctx, company, job_title, company_url="", research_id=None, force_refresh=False):
    if not company.strip():
        return None, CompanyBrief(company="", status="not_requested")
    key = cache_key(company, job_title, company_url)
    if research_id:
        row = session.get(CompanyResearch, research_id)
        if not row or row.user_id != ctx.user.id or row.workspace_id != ctx.workspace.id:
            raise HTTPException(404, "Company research not found")
        if row.cache_key != key:
            raise HTTPException(409, "The company or role changed. Research it again.")
        if not force_refresh and (row.data.get("status") == "researched" or row.expires_at > time.time()):
            return row.id, CompanyBrief.model_validate(row.data).model_copy(update={"cached": True})
    if not force_refresh:
        # Successful research remains reusable until the user explicitly requests an update.
        # A failed refresh must not destroy the last good saved brief.
        query = (
            select(CompanyResearch)
            .where(
                CompanyResearch.user_id == ctx.user.id,
                CompanyResearch.workspace_id == ctx.workspace.id,
                CompanyResearch.cache_key == key,
            )
            .order_by(CompanyResearch.created_at.desc())
            .limit(1)
        )
        reusable = session.exec(query.where(CompanyResearch.data["status"].as_string() == "researched")).first()
        reusable = reusable or session.exec(query.where(CompanyResearch.expires_at > time.time())).first()
        if reusable:
            return reusable.id, CompanyBrief.model_validate(reusable.data).model_copy(update={"cached": True})
    if settings.demo_login and settings.default_profile == "demo":
        return None, unavailable(company, "Web research is disabled in isolated test mode.")
    if not settings.company_research_enabled:
        return None, unavailable(
            company, "Company web research is not configured. Your job description will guide the interview."
        )
    rate_limit(session, ctx.workspace)
    consume(session, ctx.workspace)
    try:
        brief = execute(
            "company_research",
            {"company": company, "role": job_title, "official_url": company_url},
            CompanyBrief,
            workspace_id=ctx.workspace.id,
            user_id=ctx.user.id,
            engine=session.bind,
            stage="company_search",
            validate=validate_research,
        )
    except Exception as exc:  # noqa: BLE001 - optional tool errors become explicit unavailability
        log.warning("company_research category=%s", getattr(exc, "category", "internal"))
        brief = unavailable(
            company,
            str(exc)
            if getattr(exc, "category", None) == "ungrounded"
            else "Company search is temporarily unavailable. Your job description will guide the interview.",
        )
    status = "succeeded" if brief.status == "researched" else "failed"
    # The historical expires_at column now limits only failed-result backoff. Success is durable.
    row = CompanyResearch(
        workspace_id=ctx.workspace.id,
        user_id=ctx.user.id,
        cache_key=key,
        data=brief.model_dump(),
        expires_at=time.time() + (86400 if status == "succeeded" else 60),
    )
    session.add(row)
    session.commit()
    return row.id, brief
