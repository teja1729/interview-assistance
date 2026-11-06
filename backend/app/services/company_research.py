"""Candidate-owned cache of saved company sources; no live research provider is configured."""

import hashlib
import json
import time

from fastapi import HTTPException
from sqlmodel import select

from ..models import CompanyResearch
from ..schemas import CompanyBrief


def unavailable(company, note):
    return CompanyBrief(company=company, status="unavailable", note=note)


def cache_key(company, job_title, company_url=""):
    return hashlib.sha256(
        json.dumps([company.strip().casefold(), job_title.strip().casefold(), company_url.strip()]).encode()
    ).hexdigest()


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
        # Successful saved research remains reusable. A refresh failure never destroys it.
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
    brief = unavailable(company, "Company web research is unavailable. Your job description will guide the interview.")
    # Unavailable results use a short backoff; old successful source snapshots remain durable.
    row = CompanyResearch(
        workspace_id=ctx.workspace.id,
        user_id=ctx.user.id,
        cache_key=key,
        data=brief.model_dump(),
        expires_at=time.time() + 60,
    )
    session.add(row)
    session.commit()
    return row.id, brief
