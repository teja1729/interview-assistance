"""Recovery, grounding and execution contracts. Every provider is a fixture."""

from copy import deepcopy

import pytest
from sqlmodel import Session, select

from app.agents import runtime, specs
from app.agents.context import live_context
from app.models import AgentJob, AgentRun, Interview, Turn
from app.providers import PROVIDERS
from app.providers.base import Profile, ProviderError
from app.schemas import ResumeDigest, Titles
from app.services import reports
from app.services.reports import process_one


def prepare(client, **body):
    response = client.post("/api/interviews", json={"job_title": "Engineer", **body})
    assert response.status_code == 201
    iv = response.json()
    joined = client.post(f"/api/interviews/{iv['id']}/join").json()
    result = client.post(
        f"/api/interviews/{iv['id']}/turn-text",
        json={
            "text": "I designed the API and measured its latency.",
            "version": joined["version"],
            "request_id": "workflow-regression-answer",
        },
    )
    assert result.status_code == 200
    return iv


def test_coach_retry_resumes_without_reevaluating(clients, engine, monkeypatch):
    client = clients()
    iv = prepare(client)
    generate = PROVIDERS["demo"].generate
    calls, fail = [], True

    def capture(profile, prompt, payload, schema):
        calls.append(schema.__name__)
        if fail and schema.__name__ == "SkillCoachingPlan":
            raise ProviderError("Fixture transient outage")
        return generate(profile, prompt, payload, schema)

    monkeypatch.setattr(PROVIDERS["demo"], "generate", capture)
    client.post(f"/api/interviews/{iv['id']}/finish")
    assert process_one(engine)
    interim = client.get(f"/api/interviews/{iv['id']}").json()
    assert interim["status"] == "finishing" and interim["report"] is None
    with Session(engine) as session:
        job = session.exec(select(AgentJob)).one()
        assert {"topic:0:part:0", "report_summary"} <= job.artifacts["steps"].keys()
        job.available_at = 0
        session.add(job)
        session.commit()
    fail = False
    assert process_one(engine)
    assert calls.count("TopicAssessment") == calls.count("EvidenceReportSummary") == 1
    assert client.get(f"/api/interviews/{iv['id']}").json()["status"] == "finished"
    assert len(client.get("/api/practice").json()) == 2 and not process_one(engine)


@pytest.mark.parametrize("invalid", ["empty", "whitespace", "wrong_answer", "fabricated"])
def test_invalid_evidence_never_publishes(clients, engine, monkeypatch, invalid):
    client = clients()
    iv = prepare(client)
    generate = PROVIDERS["demo"].generate
    seen = []

    def corrupt(profile, prompt, payload, schema):
        result = generate(profile, prompt, payload, schema)
        if schema.__name__ == "TopicAssessment":
            seen.append(deepcopy(payload))
            if invalid == "empty":
                result.data["evidence"] = []
            elif invalid == "wrong_answer":
                result.data["evidence"][0]["answer_id"] = "unrelated-answer"
            else:
                result.data["evidence"][0]["quote"] = "  " if invalid == "whitespace" else "fabricated private text"
        return result

    monkeypatch.setattr(PROVIDERS["demo"], "generate", corrupt)
    client.post(f"/api/interviews/{iv['id']}/finish")
    process_one(engine)
    assert len(seen) == 2 and seen[1]["validation_feedback"]
    assert "fabricated private text" not in str(seen[1]["validation_feedback"])
    saved = client.get(f"/api/interviews/{iv['id']}").json()
    assert saved["status"] == "report_failed" and saved["report"] is None
    assert not process_one(engine)


def test_snapshot_survives_configuration_edit(clients, engine, monkeypatch, tmp_path):
    client = clients()
    iv = client.post("/api/interviews", json={"job_title": "Engineer"}).json()
    with Session(engine) as session:
        bundle = session.get(Interview, iv["id"]).plan["_execution"]
    assert "'api_key':" not in str(bundle)
    old_prompt = specs.bundle_prompts(bundle, engine)["interviewer"]["text"]
    monkeypatch.setattr(runtime, "profiles", dict)
    monkeypatch.setattr(runtime, "PROMPTS", tmp_path)
    generate = PROVIDERS["demo"].generate
    seen = []

    def capture(profile, prompt, payload, schema):
        seen.append((profile.model, prompt))
        return generate(profile, prompt, payload, schema)

    monkeypatch.setattr(PROVIDERS["demo"], "generate", capture)
    joined = client.post(f"/api/interviews/{iv['id']}/join").json()
    result = client.post(
        f"/api/interviews/{iv['id']}/turn-text",
        json={"text": "I delivered the API.", "version": joined["version"], "request_id": "snapshot-regression-turn"},
    )
    assert result.status_code == 200 and seen == [("demo-v1", old_prompt)]


def test_credentials_rotate_without_changing_saved_model(monkeypatch, engine):
    profile = Profile("one", "One", "sarvam", "pinned-model", api_key="old-secret", api_key_env="TEST_AGENT_CREDENTIAL")
    monkeypatch.setattr(specs, "profiles", lambda: {"one": profile})
    bundle = specs.snapshot({"assistant": "one"}, engine)
    assert "old-secret" not in str(bundle)
    monkeypatch.setenv("TEST_AGENT_CREDENTIAL", "rotated-secret")
    candidates, _, _, _ = specs.resolve(bundle, "assistant", Titles, engine)
    assert candidates[0].api_key == "rotated-secret" and candidates[0].model == "pinned-model"


def test_trace_failure_does_not_mask_valid_output(clients, engine, monkeypatch):
    client = clients()

    class BrokenSession:
        def __init__(self, *_):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *_):
            return False

        def add(self, *_):
            pass

        def commit(self):
            raise RuntimeError("fixture trace failure")

    monkeypatch.setattr(runtime, "Session", BrokenSession)
    result = runtime.execute(
        "assistant",
        {},
        Titles,
        workspace_id=client.workspace_id,
        user_id=client.user_id,
        ai_profiles={"assistant": "demo"},
        engine=engine,
    )
    assert result.titles


def test_non_latin_resume_budget(clients, engine):
    client = clients()
    result = runtime.execute(
        "resume",
        {"text": "क" * 31000},
        ResumeDigest,
        workspace_id=client.workspace_id,
        user_id=client.user_id,
        ai_profiles={"resume": "demo"},
        engine=engine,
    )
    assert result.digest


def test_language_preferences_reach_followups_and_owned_speech(clients, monkeypatch):
    client, stranger = clients(), clients("other@example.test")
    generate = PROVIDERS["demo"].generate
    seen = []

    def capture(profile, prompt, payload, schema):
        seen.append((schema.__name__, payload))
        return generate(profile, prompt, payload, schema)

    monkeypatch.setattr(PROVIDERS["demo"], "generate", capture)
    iv = prepare(client, custom_instructions="Conduct this interview in Hindi. Focus on API testing.")
    payload = next(p for schema, p in seen if schema == "InterviewDecision")
    assert payload["language"] == "hi-IN" and "API testing" in payload["custom_instructions"]
    from app.services import speech

    spoken = []
    monkeypatch.setattr(speech, "synthesize", lambda text, language: spoken.append(language) or b"fixture-audio")
    assert (
        client.post("/api/tts", json={"text": "Hello", "interview_id": iv["id"], "language": "en-IN"}).status_code
        == 200
    )
    assert spoken == ["hi-IN"]
    assert stranger.post("/api/tts", json={"text": "Hello", "interview_id": iv["id"]}).status_code == 404
    assert spoken == ["hi-IN"]


def test_bounded_history_and_lossless_report_batches(clients, engine):
    client = clients()
    iv = prepare(client)
    with Session(engine) as session:
        saved = session.get(Interview, iv["id"])
        turns = [
            Turn(
                id=f"t{i}",
                workspace_id=saved.workspace_id,
                interview_id=saved.id,
                position=i,
                topic=i // 3,
                question="Describe your work?",
                answer="क" * 16000,
            )
            for i in range(36)
        ]
        turns[-1].answer = None
        payload = live_context(saved, turns, "Exact current answer", 500)
        assert len(payload["history"]) == 3 and payload["answer"] == "Exact current answer"
        assert all(len(t["answer"] or "") < 2600 for t in payload["history"])
        evidence = reports.evidence_turns(turns)
        batches = reports.topic_batches(evidence)
        for original in evidence:
            assert (
                "".join(t["answer"] for batch in batches for t in batch if t["answer_id"] == original["answer_id"])
                == original["answer"]
            )
        assert all(sum(len(t["answer"].encode()) for t in batch) <= 48000 for batch in batches)


def test_stale_worker_cannot_checkpoint_or_publish(clients, engine, monkeypatch):
    client = clients()
    iv = prepare(client)
    generate = PROVIDERS["demo"].generate

    def steal(profile, prompt, payload, schema):
        if schema.__name__ == "EvidenceReportSummary":
            with Session(engine) as session:
                job = session.exec(select(AgentJob)).one()
                job.lease_token = "replacement-worker"
                session.add(job)
                session.commit()
        return generate(profile, prompt, payload, schema)

    monkeypatch.setattr(PROVIDERS["demo"], "generate", steal)
    client.post(f"/api/interviews/{iv['id']}/finish")
    assert process_one(engine)
    assert client.get(f"/api/interviews/{iv['id']}").json()["report"] is None
    assert client.get("/api/practice").json() == []
    with Session(engine) as session:
        job = session.exec(select(AgentJob)).one()
        assert "report_summary" not in job.artifacts["steps"] and job.lease_token == "replacement-worker"


def test_retry_after_exceeding_deadline_does_not_retry(clients, engine, monkeypatch):
    client = clients()
    calls = []

    def fail(*args):
        calls.append(True)
        raise ProviderError("Busy", category="rate_limited", retry_after=60)

    monkeypatch.setattr(PROVIDERS["demo"], "generate", fail)
    with pytest.raises(ProviderError):
        runtime.execute(
            "interviewer",
            {},
            Titles,
            workspace_id=client.workspace_id,
            user_id=client.user_id,
            ai_profiles={"interviewer": "demo"},
            engine=engine,
        )
    assert len(calls) == 1


def test_successful_repair_and_server_computed_rubric(clients, engine, monkeypatch):
    client = clients()
    iv = prepare(client)
    generate = PROVIDERS["demo"].generate
    seen = []

    def repair(profile, prompt, payload, schema):
        result = generate(profile, prompt, payload, schema)
        if schema.__name__ == "TopicAssessment":
            seen.append(payload)
            if len(seen) == 1:
                result.data["evidence"][0]["quote"] = "not in answer"
        return result

    monkeypatch.setattr(PROVIDERS["demo"], "generate", repair)
    client.post(f"/api/interviews/{iv['id']}/finish")
    process_one(engine)
    report = client.get(f"/api/interviews/{iv['id']}").json()["report"]
    assert len(seen) == 2 and seen[1]["validation_feedback"][0]["code"].startswith("evidence_")
    assert report["questions"][0]["score"] == 2.5  # All fixture criterion ratings are 1/4; weights normalize to 10.
    assert report["overall_score"] == report["questions"][0]["score"] * 10
    with Session(engine) as session:
        runs = session.exec(select(AgentRun).where(AgentRun.stage == "topic:0:part:0")).all()
        assert [r.status for r in runs] == ["failed", "succeeded"]


def test_final_spoken_turn_keeps_session_language(clients, engine):
    import time

    client = clients()
    iv = prepare(client, language="hi-IN")
    with Session(engine) as session:
        saved = session.get(Interview, iv["id"])
        saved.started_at = time.time() - saved.duration_minutes * 60 + 30
        version = saved.version
        session.add(saved)
        session.commit()
    result = client.post(
        f"/api/interviews/{iv['id']}/turn-text",
        json={"text": "मैंने परीक्षण किया।", "version": version, "request_id": "closing-language-regression"},
    )
    assert result.status_code == 200 and result.json()["done"] is True
    assert "धन्यवाद" in result.json()["reply"]
