"""Durable private setup reuse. Read before reserving paid inference; retain every refresh."""

import hashlib
import json

from fastapi import HTTPException
from sqlmodel import select

from ..models import SetupArtifact


def inputs_for(payload):
    return {
        "job_title": payload["job_title"].strip(),
        "company": payload.get("company", "").strip(),
        "experience_years": payload.get("experience_years", 0),
        "company_url": payload.get("company_url", "").strip(),
    }


def key_for(kind, inputs):
    normalized = {
        k: " ".join(v.casefold().split()) if isinstance(v, str) and k != "company_url" else v for k, v in inputs.items()
    }
    return hashlib.sha256(json.dumps([kind, normalized], sort_keys=True).encode()).hexdigest()


def lookup(session, ctx, kind, inputs):
    return session.exec(
        select(SetupArtifact)
        .where(
            SetupArtifact.workspace_id == ctx.workspace.id,
            SetupArtifact.user_id == ctx.user.id,
            SetupArtifact.kind == kind,
            SetupArtifact.cache_key == key_for(kind, inputs),
        )
        .order_by(SetupArtifact.created_at.desc())
        .limit(1)
    ).first()


def public(row, cached=True):
    return {**row.data, "id": row.id, "cached": cached, "saved_at": row.created_at, "inputs": row.inputs}


def save(session, ctx, kind, inputs, data):
    row = SetupArtifact(
        workspace_id=ctx.workspace.id,
        user_id=ctx.user.id,
        kind=kind,
        cache_key=key_for(kind, inputs),
        inputs=inputs,
        data=data,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return public(row, cached=False)


def get(session, ctx, identifier):
    row = session.get(SetupArtifact, identifier)
    if not row or row.workspace_id != ctx.workspace.id or row.user_id != ctx.user.id or row.kind != "job_description":
        raise HTTPException(404, "Saved role brief not found")
    return public(row)


def list_drafts(session, ctx):
    rows = session.exec(
        select(SetupArtifact)
        .where(
            SetupArtifact.workspace_id == ctx.workspace.id,
            SetupArtifact.user_id == ctx.user.id,
            SetupArtifact.kind == "job_description",
        )
        .order_by(SetupArtifact.created_at.desc())
        .limit(50)
    ).all()
    return [{"id": row.id, "inputs": row.inputs, "saved_at": row.created_at} for row in rows]
