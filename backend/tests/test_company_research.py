"""Search grounding, ownership, caching and snapshots; never calls Google in CI."""

from dataclasses import replace
from types import SimpleNamespace as N

import pytest
from sqlmodel import Session, select

from app.agents import runtime
from app.models import CompanyResearch, Interview
from app.providers import PROVIDERS
from app.providers.base import Completion, Profile
from app.providers.grounding import parse_grounding
from app.services import company_research as research


def grounded():
    return N(
        text="Example builds developer tools.",
        usage_metadata=None,
        candidates=[
            N(
                grounding_metadata=N(
                    web_search_queries=["Example company developer tools"],
                    grounding_chunks=[N(web=N(uri="https://example.com/about", title="Example official site"))],
                    grounding_supports=[
                        N(segment=N(text="Example builds developer tools."), grounding_chunk_indices=[0])
                    ],
                    search_entry_point=N(rendered_content="<div>Search suggestions</div>"),
                )
            )
        ],
    )


@pytest.fixture
def search(monkeypatch):
    monkeypatch.setattr(
        research,
        "settings",
        replace(research.settings, demo_login=False, company_research_enabled=True, gemini_api_key="fixture-key"),
    )
    calls = []

    def run(profile, system, payload, schema):
        calls.append(payload)
        return Completion(parse_grounding(payload["company"], grounded(), payload.get("official_url", "")).model_dump())

    registry = runtime.profiles()
    registry["search-fixture"] = Profile(
        "search-fixture", "Fixture", "gemini", "fixture-model", api_key="fixture-key", capabilities=("search",)
    )
    monkeypatch.setattr(runtime, "profiles", lambda: registry)
    monkeypatch.setattr(runtime, "agent_profiles", lambda: {"company_research": "search-fixture"})
    monkeypatch.setattr(PROVIDERS["gemini"], "search", run)
    return calls


def test_research_is_cited_cached_and_candidate_private(clients, engine, search):
    client, stranger = clients(), clients("other@example.test")
    payload = {"company": "Example", "job_title": "Engineer", "company_url": "https://example.com"}
    result = client.post("/api/company-research", json=payload)
    assert result.status_code == 200
    brief = result.json()
    assert brief["status"] == "researched" and brief["facts"][0]["source_ids"] == ["s0"]
    assert client.post("/api/company-research", json=payload).json()["id"] == brief["id"]
    assert len(search) == 1 and set(search[0]) == {"company", "role", "official_url"}
    iv = client.post("/api/interviews", json={**payload, "company_research_id": brief["id"]}).json()
    assert iv["company_context"]["facts"] == brief["facts"] and len(search) == 1
    assert stranger.post("/api/interviews", json={**payload, "company_research_id": brief["id"]}).status_code == 404
    assert (
        client.post(
            "/api/interviews", json={**payload, "job_title": "Designer", "company_research_id": brief["id"]}
        ).status_code
        == 409
    )
    with Session(engine) as session:
        cached = session.get(CompanyResearch, brief["id"])
        cached.data = {**cached.data, "facts": []}
        session.add(cached)
        session.commit()
        assert session.get(Interview, iv["id"]).plan["_brief"]["company_context"]["facts"] == brief["facts"]


@pytest.mark.parametrize("kind", ["no_search", "no_citations", "unsafe_url", "ambiguous"])
def test_unsourced_or_ambiguous_results_never_become_company_facts(kind):
    response = grounded()
    metadata = response.candidates[0].grounding_metadata
    if kind == "no_search":
        metadata.web_search_queries = []
    elif kind == "no_citations":
        metadata.grounding_supports = []
    elif kind == "unsafe_url":
        metadata.grounding_chunks[0].web.uri = "javascript:alert(1)"
    else:
        response.text = "This name is ambiguous."
    brief = parse_grounding("Example", response)
    assert brief.status == "unavailable" and brief.facts == []


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


def test_failed_search_stays_explicitly_unavailable_and_never_leaks_error(clients, engine, search, monkeypatch):
    def fail(*args):
        raise RuntimeError("private-vendor-token-body")

    monkeypatch.setattr(PROVIDERS["gemini"], "search", fail)
    client = clients()
    payload = {"company": "Example", "job_title": "Engineer"}
    result = client.post("/api/company-research", json=payload)
    assert result.status_code == 200 and result.json()["status"] == "unavailable"
    assert "private-vendor" not in result.text
    iv = client.post("/api/interviews", json=payload)
    assert iv.status_code == 201 and iv.json()["company_context"]["status"] == "unavailable"
    with Session(engine) as session:
        assert len(session.exec(select(CompanyResearch)).all()) == 1


def test_official_url_filters_unrelated_search_sources():
    response = grounded()
    metadata = response.candidates[0].grounding_metadata
    metadata.grounding_chunks[0].web.uri = "https://vertexaisearch.cloud.google.com/redirect"
    metadata.grounding_chunks[0].web.title = "unrelated.example"
    assert parse_grounding("Example", response, "https://example.com").status == "unavailable"
    metadata.grounding_chunks[0].web.title = "example.com"
    assert parse_grounding("Example", response, "https://example.com").status == "researched"
