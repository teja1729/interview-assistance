"""Executable contracts for tenant boundaries, state transitions and durable agent work."""

import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

from fastapi.testclient import TestClient
from sqlmodel import Session, select

from app import schemas
from app.api.auth import provision
from app.config import settings
from app.main import app
from app.models import AgentJob, AgentRun, Interview, PracticeTask
from app.providers import PROVIDERS
from app.providers.base import Completion
from app.services.reports import process_one


def create_join(client):
    response = client.post("/api/interviews", json={"job_title": "Backend Engineer"})
    assert response.status_code == 201, response.text
    created = response.json()
    assert created["started_at"] is None and created["status"] == "lobby"
    joined = client.post(f"/api/interviews/{created['id']}/join")
    assert joined.status_code == 200, joined.text
    return joined.json()


def answer(client, iv, text="I used various tools.", request_id=None):
    return client.post(
        f"/api/interviews/{iv['id']}/turn-text",
        json={"text": text, "version": iv["version"], "request_id": request_id or f"request-{time.time_ns()}"},
    )


def test_auth_csrf_and_origin(clients):
    client = clients()
    assert TestClient(app).get("/api/interviews").status_code == 401
    assert client.get("/api/auth/me").status_code == 200
    assert (
        client.post("/api/interviews", json={"job_title": "Engineer"}, headers={"X-CSRF-Token": "wrong"}).status_code
        == 403
    )
    assert (
        client.post(
            "/api/interviews", json={"job_title": "Engineer"}, headers={"Origin": "https://evil.example"}
        ).status_code
        == 403
    )
    identity = client.get("/api/auth/me").json()
    assert identity["account"]["id"] == client.workspace_id
    assert not {"workspace", "workspaces", "ai_profiles"} & identity.keys()


def test_full_interview_and_followup_cap(clients, engine):
    client = clients(plan="team")
    iv = create_join(client)
    assert client.post(f"/api/interviews/{iv['id']}/join").json()["version"] == iv["version"]
    for index in range(3):
        response = answer(client, iv)
        assert response.status_code == 200, response.text
        assert response.json()["transcript"] == "I used various tools."
        iv = client.get(f"/api/interviews/{iv['id']}").json()
        assert iv["turns"][-1]["topic"] == (1 if index == 2 else 0)
    result = client.post(f"/api/interviews/{iv['id']}/finish")
    assert result.json()["status"] == "finishing"
    assert client.post(f"/api/interviews/{iv['id']}/finish").json()["status"] == "finishing"
    assert process_one(engine)
    report = client.get(f"/api/interviews/{iv['id']}").json()
    assert report["status"] == "finished"
    schemas.PracticeReport.model_validate(report["report"])
    assert len(report["report"]["questions"]) == 1
    assert len(client.get("/api/practice").json()) == 2
    assert not process_one(engine)
    assert client.post(f"/api/interviews/{iv['id']}/finish").json()["report"] == report["report"]
    with Session(engine) as session:
        assert len(session.exec(select(AgentJob)).all()) == 1
        assert len(session.exec(select(AgentRun)).all()) == 8


def test_tenant_isolation(clients):
    owner, stranger = clients(), clients("other@example.test")
    iv = create_join(owner)
    for path in (f"/api/interviews/{iv['id']}",):
        assert stranger.get(path).status_code == 404
    assert stranger.post(f"/api/interviews/{iv['id']}/finish").status_code == 404
    assert stranger.get("/api/interviews").json() == []
    assert stranger.get("/api/agent-runs").json() == []
    assert stranger.post(f"/api/auth/workspace/{owner.workspace_id}").status_code == 404
    uploaded = owner.post(
        "/api/resumes",
        files={
            "file": (
                "resume.txt",
                b"Alex Example\nBackend engineer with database and API design experience.",
                "text/plain",
            )
        },
    ).json()
    assert stranger.get(f"/api/resumes/{uploaded['id']}").status_code == 404
    assert stranger.delete(f"/api/resumes/{uploaded['id']}").status_code == 404


def test_duplicate_and_stale_answers(clients):
    client = clients()
    iv = create_join(client)
    first = answer(client, iv, request_id="same-request-123456")
    assert first.status_code == 200
    assert answer(client, iv, request_id="same-request-123456").json() == first.json()
    assert answer(client, iv, text="different", request_id="same-request-123456").status_code == 409
    assert answer(client, iv).status_code == 409
    assert len(client.get(f"/api/interviews/{iv['id']}").json()["turns"]) == 2


def test_concurrent_answers_are_fenced(clients, monkeypatch):
    client = clients()
    iv = create_join(client)
    entered, release = threading.Event(), threading.Event()
    original = PROVIDERS["demo"].generate

    def blocking(*args):
        if args[-1] is schemas.InterviewDecision:
            entered.set()
            assert release.wait(10)
        return original(*args)

    monkeypatch.setattr(PROVIDERS["demo"], "generate", blocking)
    with ThreadPoolExecutor(2) as pool:
        first = pool.submit(answer, client, iv)
        assert entered.wait(10)
        try:
            second = answer(client, iv)
            assert second.status_code == 409, second.text
        finally:
            release.set()
        assert first.result().status_code == 200
    saved = client.get(f"/api/interviews/{iv['id']}").json()
    assert sum(t["answer"] is not None for t in saved["turns"]) == 1


def test_clock_wrap_and_resume_snapshot(clients, engine):
    client = clients()
    uploaded = client.post(
        "/api/resumes",
        files={
            "file": (
                "resume.txt",
                b"Alex Example\nReduced API latency by optimizing database access patterns.",
                "text/plain",
            )
        },
    )
    assert uploaded.status_code == 201
    resume_id = uploaded.json()["id"]
    iv = client.post("/api/interviews", json={"job_title": "Engineer", "resume_id": resume_id}).json()
    client.delete(f"/api/resumes/{resume_id}")
    iv = client.post(f"/api/interviews/{iv['id']}/join").json()
    with Session(engine) as session:
        row = session.get(Interview, iv["id"])
        assert "latency" in row.resume_snapshot
        row.started_at = time.time() - row.duration_minutes * 60 + 30
        session.add(row)
        session.commit()
    response = answer(client, iv)
    assert response.json()["done"] is True
    assert "?" not in response.json()["reply"]
    assert answer(client, iv).status_code == 409


def test_bad_model_output_never_finishes_report(clients, engine, monkeypatch):
    client = clients()
    iv = create_join(client)
    assert answer(client, iv).status_code == 200
    client.post(f"/api/interviews/{iv['id']}/finish")
    original = PROVIDERS["demo"].generate

    def malformed(*args):
        return Completion({}) if args[-1] is schemas.TopicAssessment else original(*args)

    monkeypatch.setattr(PROVIDERS["demo"], "generate", malformed)
    for _ in range(1):
        with Session(engine) as session:
            job = session.exec(select(AgentJob)).one()
            job.available_at = 0
            session.add(job)
            session.commit()
        assert process_one(engine)
    result = client.get(f"/api/interviews/{iv['id']}").json()
    assert result["status"] == "report_failed" and result["report"] is None
    assert len([t for t in result["turns"] if t["answer"]]) == 1
    assert client.get("/api/practice").json() == []


def test_expired_worker_lease_recovers(clients, engine):
    client = clients()
    iv = create_join(client)
    answer(client, iv)
    client.post(f"/api/interviews/{iv['id']}/finish")
    with Session(engine) as session:
        job = session.exec(select(AgentJob)).one()
        job.status, job.lease_until, job.lease_token, job.attempts = "running", 0, "crashed-worker", 1
        session.add(job)
        session.commit()
    assert process_one(engine)
    assert client.get(f"/api/interviews/{iv['id']}").json()["status"] == "finished"
    with Session(engine) as session:
        assert len(session.exec(select(PracticeTask)).all()) == 2


def test_quota_and_owner_permissions(clients):
    client = clients()
    for _ in range(3):
        assert client.post("/api/interviews", json={"job_title": "Engineer"}).status_code == 201
    assert client.post("/api/interviews", json={"job_title": "Engineer"}).status_code == 429
    member = clients("member@example.test", role="member")
    assert member.put("/api/workspace/profiles", json={"profiles": {"planner": "demo"}}).status_code == 404
    assert member.post("/api/billing/checkout", json={"plan": "pro"}).status_code == 403
    assert client.put("/api/workspace/profiles", json={"profiles": {"planner": "attacker"}}).status_code == 404


def test_workspace_management_is_retired(clients):
    client = clients()
    for method, path in (
        ("GET", "/api/workspace"),
        ("POST", "/api/workspace"),
        ("PATCH", "/api/workspace"),
        ("PUT", "/api/workspace/profiles"),
        ("POST", "/api/workspace/invitations"),
        ("POST", "/api/workspace/invitations/accept"),
        ("DELETE", "/api/workspace/members/someone"),
        ("GET", "/api/workspace/audit"),
        ("POST", f"/api/auth/workspace/{client.workspace_id}"),
    ):
        assert client.request(method, path, json={}).status_code == 404
    assert {plan["id"] for plan in client.get("/api/billing").json()["plans"]} == {"free", "pro"}
    assert client.post("/api/billing/checkout", json={"plan": "team"}).status_code == 400


def test_legacy_owner_cannot_read_another_candidates_interview_or_traces(clients, engine):
    owner, other = clients(), clients("other@example.test")
    iv = create_join(other)
    # Historical shared-container data must remain candidate-private, even to its owner.
    with Session(engine) as session:
        record = session.get(Interview, iv["id"])
        record.workspace_id = owner.workspace_id
        session.add(record)
        trace = session.exec(select(AgentRun).where(AgentRun.interview_id == iv["id"])).one()
        trace.workspace_id = owner.workspace_id
        session.add(trace)
        session.commit()
    assert owner.get(f"/api/interviews/{iv['id']}").status_code == 404
    assert owner.post(f"/api/interviews/{iv['id']}/finish").status_code == 404
    assert owner.get("/api/interviews").json() == []
    assert owner.get("/api/agent-runs").json() == []


def test_google_subject_not_email_is_identity(engine):
    with Session(engine) as session:
        first, _ = provision(session, "google-sub-1", "same@example.test", "First")
        second, _ = provision(session, "google-sub-2", "same@example.test", "Second")
        assert first.id != second.id
        repeated, _ = provision(session, "google-sub-1", "changed@example.test", "First")
        assert repeated.id == first.id


def test_production_refuses_demo_and_weak_configuration():
    import pytest

    with pytest.raises(RuntimeError):
        replace(settings, environment="production").validate()
