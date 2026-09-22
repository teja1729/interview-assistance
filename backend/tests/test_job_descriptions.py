"""Role-brief contracts and the boundary between live AI and opt-in test fixtures."""

from dataclasses import replace

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import auth
from app.agents import runtime
from app.api.auth import provision
from app.auth import issue_session
from app.main import app
from app.models import AgentRun, Workspace
from app.providers import PROVIDERS, base
from app.providers.base import Completion, Profile, ProviderError
from app.schemas import JobDescriptionDraft
from app.services import job_descriptions
from tests.fixtures.demo_provider import DemoProvider


def test_job_description_is_complete_and_explicitly_labels_test_data(clients, engine):
    client = clients()
    response = client.post(
        "/api/suggest/job-description",
        json={
            "job_title": "Agentic AI Engineer",
            "company": "Example",
            "experience_years": 2,
        },
    )
    assert response.status_code == 200
    result = response.json()
    assert result["demo"] is True
    assert result["job_description"].startswith("DEMO SAMPLE")
    for section in ("Role overview", "Responsibilities", "Requirements", "Nice to have", "First 90 days"):
        assert section in result["job_description"]
    with Session(engine) as session:
        run = session.exec(select(AgentRun)).one()
        assert run.agent == "assistant" and run.status == "succeeded"


def test_live_description_uses_server_routing_and_preserves_role_context(clients, engine, monkeypatch):
    client = clients()
    profile = Profile("live-test", "Live test", "sarvam", "test-model", api_key="fixture-key")
    registry = lambda: {profile.id: profile}
    monkeypatch.setattr(runtime, "profiles", registry)
    monkeypatch.setattr(job_descriptions, "profiles", registry)
    monkeypatch.setattr(job_descriptions, "agent_profiles", lambda: {"assistant": profile.id})
    captured = []

    def generate(selected, system, payload, schema):
        captured.append((selected, system, payload, schema))
        return DemoProvider().generate(selected, system, payload, schema)

    monkeypatch.setattr(PROVIDERS["sarvam"], "generate", generate)
    with Session(engine) as session:
        workspace = session.get(Workspace, client.workspace_id)
        workspace.ai_profiles = {"assistant": "demo"}  # A legacy UI preference must have no effect.
        session.add(workspace)
        session.commit()
    payload = {"job_title": "Agentic AI Engineer", "company": "Example", "experience_years": 2}
    response = client.post("/api/suggest/job-description", json=payload)
    assert response.status_code == 200
    assert response.json()["demo"] is False
    assert response.json()["job_description"].startswith("Agentic AI Engineer\n\nRole overview")
    assert len(captured) == 1
    selected, prompt, received, schema = captured[0]
    assert selected.id == profile.id and selected.model == profile.model and schema is JobDescriptionDraft
    assert all(received[key] == value for key, value in payload.items())
    assert "company_context" in received
    assert prompt == runtime.specs.load_prompt("job_description")


def test_incomplete_job_description_is_rejected_instead_of_returning_filler(clients, monkeypatch):
    client = clients()
    monkeypatch.setattr(PROVIDERS["demo"], "generate", lambda *a: Completion({"job_description": "generic filler"}))
    response = client.post("/api/suggest/job-description", json={"job_title": "Engineer"})
    assert response.status_code == 503
    assert "job_description" not in response.json()


def test_disabling_test_mode_hides_fixtures_and_revokes_existing_demo_sessions(clients, engine, monkeypatch):
    clients()  # install the isolated session dependency
    with Session(engine) as session:
        user, workspace = provision(session, "development-demo", "demo@example.test", "Demo", demo=True)
        from fastapi import Response

        response = Response()
        issue_session(response, session, user, workspace)
    disabled = replace(auth.settings, demo_login=False)
    monkeypatch.setattr(auth, "settings", disabled)
    monkeypatch.setattr(base, "settings", disabled)
    with TestClient(app) as client:
        client.headers["cookie"] = response.headers["set-cookie"].split(";", 1)[0]
        assert client.get("/api/auth/me").status_code == 401
    assert not Profile("demo", "Demo", "demo", "fixture").available
    assert not base.profiles()["demo"].available


def test_live_provider_failure_cannot_fall_back_to_fixtures(clients, engine, monkeypatch):
    import pytest

    client = clients()
    live = Profile("live-test", "Live", "sarvam", "test-model", api_key="fixture", fallback="demo")
    demo = Profile("demo", "Demo", "demo", "fixture")
    monkeypatch.setattr(runtime, "profiles", lambda: {live.id: live, demo.id: demo})
    calls = []

    def fail(*args):
        calls.append("live")
        raise RuntimeError("provider unavailable")

    monkeypatch.setattr(PROVIDERS["sarvam"], "generate", fail)
    with pytest.raises(ProviderError, match="cannot fall back"):
        runtime.execute(
            "assistant",
            {"job_title": "Engineer"},
            JobDescriptionDraft,
            workspace_id=client.workspace_id,
            user_id=client.user_id,
            ai_profiles={"assistant": live.id},
            engine=engine,
        )
    assert calls == []  # Reject an invalid live-to-fixture configuration before making a paid call.
