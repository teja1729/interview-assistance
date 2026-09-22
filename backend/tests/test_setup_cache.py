"""Saved setup artifacts remain private, durable and readable after paid quota exhaustion."""

import time
from dataclasses import replace

from sqlmodel import Session, select

from app.models import CompanyResearch, SetupArtifact, UsageBucket
from app.providers import PROVIDERS
from app.services import usage
from tests.test_company_research import search as search  # noqa: PLC0414 - shared pytest fixture


def test_jd_reuses_saved_output_without_spending_after_limit(clients, engine, monkeypatch):
    client = clients()
    body = {"job_title": "Backend Engineer", "company": "Example", "experience_years": 2}
    first = client.post("/api/suggest/job-description", json=body)
    assert first.status_code == 200 and first.json()["cached"] is False
    original = first.json()
    with Session(engine) as session:
        used = session.get(UsageBucket, (client.workspace_id, usage.period(), "ai_calls"))
        used.used = 150
        session.add(used)
        session.commit()

    def forbidden(*_):
        raise AssertionError("A cache hit must not call a model")

    monkeypatch.setattr(PROVIDERS["demo"], "generate", forbidden)
    cached = client.post("/api/suggest/job-description", json={**body, "job_title": "  backend engineer  "})
    assert cached.status_code == 200 and cached.json()["cached"] is True
    assert cached.json()["id"] == original["id"] and cached.json()["job_description"] == original["job_description"]
    assert client.post("/api/suggest/job-description", json={**body, "force_refresh": True}).status_code == 429
    assert (
        client.get(f"/api/setup/job-descriptions/{original['id']}").json()["job_description"]
        == original["job_description"]
    )


def test_jd_refresh_creates_revision_and_private_history(clients, engine):
    client, stranger = clients(), clients("stranger@example.test")
    body = {"job_title": "Engineer", "experience_years": 2}
    first = client.post("/api/suggest/job-description", json=body).json()
    refreshed = client.post("/api/suggest/job-description", json={**body, "force_refresh": True}).json()
    assert first["id"] != refreshed["id"] and not refreshed["cached"]
    assert client.post("/api/suggest/job-description", json=body).json()["id"] == refreshed["id"]
    assert len(client.get("/api/setup/job-descriptions").json()) == 2
    assert stranger.get("/api/setup/job-descriptions").json() == []
    assert stranger.get(f"/api/setup/job-descriptions/{first['id']}").status_code == 404
    changed = client.post("/api/suggest/job-description", json={**body, "experience_years": 5}).json()
    assert changed["id"] != refreshed["id"] and not changed["cached"]
    with Session(engine) as session:
        assert len(session.exec(select(SetupArtifact)).all()) == 3


def test_company_research_survives_old_ttl_and_refresh_is_explicit(clients, engine, search):
    client = clients()
    body = {"company": "Example", "job_title": "Engineer", "company_url": "https://example.com"}
    first = client.post("/api/company-research", json=body).json()
    with Session(engine) as session:
        row = session.get(CompanyResearch, first["id"])
        row.expires_at = time.time() - 365 * 86400
        session.add(row)
        session.commit()
    cached = client.post("/api/company-research", json=body).json()
    assert len(search) == 1 and cached["id"] == first["id"] and cached["cached"]
    refreshed = client.post("/api/company-research", json={**body, "force_refresh": True}).json()
    assert len(search) == 2 and refreshed["id"] != first["id"]
    assert client.post("/api/company-research", json=body).json()["id"] == refreshed["id"]


def test_title_suggestions_are_saved_without_repeat_model_calls(clients, monkeypatch):
    client = clients()
    first = client.post("/api/suggest/titles", json={"job_title": "Engineer"}).json()

    def forbidden(*_):
        raise AssertionError("Cached titles must not invoke a model")

    monkeypatch.setattr(PROVIDERS["demo"], "generate", forbidden)
    assert client.post("/api/suggest/titles", json={"job_title": " engineer "}).json() == first


def test_usage_error_identifies_resource_and_local_override_never_applies_in_production(clients, engine, monkeypatch):
    client = clients()
    with Session(engine) as session:
        session.add(UsageBucket(workspace_id=client.workspace_id, resource="interviews", period=usage.period(), used=3))
        session.commit()
    result = client.post("/api/interviews", json={"job_title": "Engineer"})
    assert (
        result.status_code == 429
        and "interview allowance" in result.json()["detail"]
        and "3/3" in result.json()["detail"]
    )
    monkeypatch.setattr(
        usage, "settings", replace(usage.settings, local_usage_overrides=True, environment="production")
    )
    assert client.get("/api/billing").json()["resources"]["interviews"]["limit"] == 3
    monkeypatch.setattr(
        usage, "settings", replace(usage.settings, environment="development", local_interview_limit=100)
    )
    assert client.get("/api/billing").json()["resources"]["interviews"]["limit"] == 100
    assert client.post("/api/interviews", json={"job_title": "Engineer"}).status_code == 201
