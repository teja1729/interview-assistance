"""Saved research cache ownership and unavailable behavior without a live search provider."""

import time

import pytest
from sqlmodel import Session, select

from app.models import CompanyResearch, Interview
from app.schemas import CompanyBrief
from app.services.company_research import cache_key


def saved_brief(company="Example"):
    return CompanyBrief(
        company=company,
        status="researched",
        facts=[{"text": "Example builds developer tools.", "source_ids": ["s0"]}],
        sources=[{"id": "s0", "title": "Example official site", "url": "https://example.com/about"}],
        researched_at=time.time(),
    )


def save_research(session, client, brief, job_title="Engineer", company_url="https://example.com"):
    row = CompanyResearch(
        workspace_id=client.workspace_id,
        user_id=client.user_id,
        cache_key=cache_key(brief.company, job_title, company_url),
        data=brief.model_dump(),
        expires_at=time.time() + 86400,
    )
    session.add(row)
    session.commit()
    session.refresh(row)
    return row


def test_new_research_is_unavailable_cached_and_candidate_private(clients, engine):
    client, stranger = clients(), clients("other@example.test")
    payload = {"company": "Example", "job_title": "Engineer", "company_url": "https://example.com"}
    result = client.post("/api/company-research", json=payload)
    assert result.status_code == 200
    brief = result.json()
    assert brief["status"] == "unavailable" and brief["facts"] == []
    assert "job description will guide the interview" in brief["note"]
    assert client.post("/api/company-research", json=payload).json()["id"] == brief["id"]
    iv = client.post("/api/interviews", json={**payload, "company_research_id": brief["id"]}).json()
    assert iv["company_context"]["status"] == "unavailable"
    assert stranger.post("/api/interviews", json={**payload, "company_research_id": brief["id"]}).status_code == 404
    assert (
        client.post(
            "/api/interviews", json={**payload, "job_title": "Designer", "company_research_id": brief["id"]}
        ).status_code
        == 409
    )
    with Session(engine) as session:
        assert len(session.exec(select(CompanyResearch)).all()) == 1
        assert session.get(Interview, iv["id"]).plan["_brief"]["company_context"]["status"] == "unavailable"


def test_saved_sources_are_reused_and_pinned_to_interviews(clients, engine):
    client = clients()
    with Session(engine) as session:
        row = save_research(session, client, saved_brief())
        identifier = row.id
    payload = {
        "company": "Example",
        "job_title": "Engineer",
        "company_url": "https://example.com",
        "company_research_id": identifier,
    }
    result = client.post("/api/company-research", json=payload)
    assert result.status_code == 200
    brief = result.json()
    assert brief["status"] == "researched" and brief["facts"][0]["source_ids"] == ["s0"]
    iv = client.post("/api/interviews", json=payload).json()
    assert iv["company_context"]["facts"] == brief["facts"]
    with Session(engine) as session:
        cached = session.get(CompanyResearch, identifier)
        cached.data = {**cached.data, "facts": []}
        session.add(cached)
        session.commit()
        assert session.get(Interview, iv["id"]).plan["_brief"]["company_context"]["facts"] == brief["facts"]


def test_refresh_without_search_keeps_last_saved_success(clients, engine):
    client = clients()
    with Session(engine) as session:
        row = save_research(session, client, saved_brief())
        identifier = row.id
    payload = {"company": "Example", "job_title": "Engineer", "company_url": "https://example.com"}
    refreshed = client.post("/api/company-research", json={**payload, "force_refresh": True})
    assert refreshed.status_code == 200 and refreshed.json()["status"] == "unavailable"
    cached = client.post("/api/company-research", json=payload)
    assert cached.status_code == 200 and cached.json()["id"] == identifier
    assert cached.json()["status"] == "researched"


@pytest.mark.parametrize(
    "url",
    [
        "http://example.com",
        "https://127.0.0.1",
        "https://localhost",
        "https://user:pass@example.com",
        "https://example.local",
        "https://example.com:8443",
    ],
)
def test_company_urls_are_public_https_without_credentials(clients, url):
    client = clients()
    payload = {"company": "Example", "job_title": "Engineer", "company_url": url}
    assert client.post("/api/company-research", json=payload).status_code == 422
    assert client.post("/api/interviews", json=payload).status_code == 422
    assert client.post("/api/suggest/job-description", json=payload).status_code == 422
