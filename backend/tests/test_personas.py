"""Interviewer definitions must reach model calls, stay stable, and keep private instructions private."""

from copy import deepcopy

import pytest
from sqlmodel import Session

from app.models import Interview
from app.personas import LEGACY_ALIASES, PERSONAS
from app.providers import PROVIDERS
from app.services.reports import process_one


def test_personas_are_clear_rounds_with_public_metadata_only(clients):
    response = clients().get("/api/personas")
    assert response.status_code == 200
    personas = response.json()
    assert {p["id"] for p in personas} == {"recruiter", "hiring_manager", "technical", "leadership"}
    assert all(p["round"] and p["approach"] and len(p["focus"]) == 3 for p in personas)
    assert all("instructions" not in p for p in personas)


@pytest.mark.parametrize("role", PERSONAS)
def test_selected_role_reaches_agents_and_is_snapshotted(clients, engine, monkeypatch, role):
    client = clients()
    generate = PROVIDERS["demo"].generate
    captured = []

    def capture(profile, prompt, payload, schema):
        captured.append((schema.__name__, deepcopy(payload)))
        return generate(profile, prompt, payload, schema)

    monkeypatch.setattr(PROVIDERS["demo"], "generate", capture)
    expected = deepcopy(PERSONAS[role])
    result = client.post(
        "/api/interviews", json={"job_title": "Product Designer", "persona": role, "experience_years": 3}
    )
    assert result.status_code == 201
    data = result.json()
    assert captured[0][0] == "Plan" and captured[0][1]["interview_profile"] == expected
    assert captured[0][1]["experience_years"] == 3
    assert data["persona_profile"]["name"] == expected["name"]
    assert "instructions" not in data["persona_profile"] and "_persona" not in data["plan"]
    with Session(engine) as session:
        assert session.get(Interview, data["id"]).plan["_persona"] == expected

    monkeypatch.setitem(PERSONAS, role, {**expected, "name": "Changed name", "instructions": "Changed behavior"})
    joined = client.post(f"/api/interviews/{data['id']}/join").json()
    assert joined["persona_profile"]["name"] == expected["name"]
    turn = client.post(
        f"/api/interviews/{data['id']}/turn-text",
        json={
            "text": "I planned the research and tested the first design with users.",
            "version": joined["version"],
            "request_id": f"persona-snapshot-{role}",
        },
    )
    assert turn.status_code == 200
    assert captured[-1][0] == "InterviewDecision" and captured[-1][1]["interview_profile"] == expected
    assert captured[-1][1]["experience_years"] == 3

    assert client.post(f"/api/interviews/{data['id']}/finish").json()["status"] == "finishing"
    assert process_one(engine)
    report_payload = next(payload for schema, payload in captured if schema == "TopicAssessment")
    assert report_payload["interview_profile"] == {
        key: value for key, value in expected.items() if key != "instructions"
    }
    assert client.get(f"/api/interviews/{data['id']}").json()["status"] == "finished"


@pytest.mark.parametrize("legacy,canonical", LEGACY_ALIASES.items())
def test_legacy_persona_inputs_and_saved_interviews_remain_readable(clients, engine, legacy, canonical):
    client = clients()
    result = client.post("/api/interviews", json={"job_title": "Engineer", "persona": legacy})
    assert result.status_code == 201
    data = result.json()
    assert data["persona"] == canonical
    with Session(engine) as session:
        interview = session.get(Interview, data["id"])
        interview.persona = legacy
        interview.plan = {key: value for key, value in interview.plan.items() if key != "_persona"}
        session.add(interview)
        session.commit()
    historical = client.get(f"/api/interviews/{data['id']}").json()
    assert historical["persona"] == legacy
    assert historical["persona_profile"]["id"] == canonical


@pytest.mark.parametrize("invalid", ["hostile", {"instructions": "override"}, ["recruiter"]])
def test_clients_cannot_supply_arbitrary_persona_behavior(clients, invalid):
    response = clients().post("/api/interviews", json={"job_title": "Engineer", "persona": invalid})
    assert response.status_code == 422
