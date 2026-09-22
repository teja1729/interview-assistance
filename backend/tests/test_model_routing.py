"""Operator routing and persisted interview choices are independent of browser preferences."""

from dataclasses import replace

import pytest
from sqlmodel import Session

from app.models import Interview, Workspace
from app.providers import base
from app.providers.base import ProviderError
from app.services import interviews


def test_toml_routes_roles_and_environment_only_fills_omitted_roles(tmp_path, monkeypatch):
    config = tmp_path / "models.toml"
    config.write_text('[agents]\nplanner = "gemini"\nevaluator = "sarvam"\n')
    monkeypatch.setattr(
        base, "settings", replace(base.settings, models_file=config, demo_login=False, default_profile="openai")
    )
    routing = base.agent_profiles()
    assert routing["planner"] == "gemini" and routing["evaluator"] == "sarvam"
    assert routing["assistant"] == "openai" and set(routing) == set(base.AGENT_ROLES)
    config.write_text('[agents]\nplaner = "gemini"\n')
    with pytest.raises(ProviderError, match="Unknown AI role"):
        base.agent_profiles()


def test_new_interviews_snapshot_server_routing_without_legacy_preferences(clients, engine, monkeypatch):
    client = clients()
    with Session(engine) as session:
        account = session.get(Workspace, client.workspace_id)
        account.ai_profiles = {"planner": "unconfigured-legacy-choice"}
        session.add(account)
        session.commit()
    routing = dict.fromkeys(base.AGENT_ROLES, "demo")
    monkeypatch.setattr(interviews, "agent_profiles", lambda: dict(routing))
    response = client.post("/api/interviews", json={"job_title": "Engineer"})
    assert response.status_code == 201
    interview_id = response.json()["id"]
    assert "ai_profiles" not in response.json()
    routing["interviewer"] = "new-server-choice"
    with Session(engine) as session:
        assert session.get(Interview, interview_id).ai_profiles["interviewer"] == "demo"
    joined = client.post(f"/api/interviews/{interview_id}/join").json()
    answer = client.post(
        f"/api/interviews/{interview_id}/turn-text",
        json={
            "version": joined["version"],
            "request_id": "routing-snapshot-test",
            "text": "I built an API and tested its database queries.",
        },
    )
    assert answer.status_code == 200  # The in-progress interview still uses its saved profile.
