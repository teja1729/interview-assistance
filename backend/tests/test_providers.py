"""Adapter wire contracts and agent failure boundaries, without paid API calls."""

import json

import httpx
import pytest
from pydantic import ValidationError
from sqlmodel import Session, select

from app.agents import runtime
from app.models import AgentRun
from app.providers.base import Profile, ProviderError
from app.providers.sarvam import SarvamProvider
from app.schemas import Titles

PROFILE = Profile(id="sarvam-test", label="Test", provider="sarvam", model="sarvam-105b", api_key="fixture-key")


def mock_sarvam(monkeypatch, handler):
    original = httpx.AsyncClient
    monkeypatch.setattr(
        "app.providers.sarvam.httpx.AsyncClient",
        lambda **kwargs: original(transport=httpx.MockTransport(handler), **kwargs),
    )


def completion(content, reason="stop"):
    return {
        "choices": [{"finish_reason": reason, "message": {"content": content}}],
        "usage": {"prompt_tokens": 20, "completion_tokens": 8},
    }


def test_sarvam_structured_request_and_usage(monkeypatch):
    def handler(request):
        assert str(request.url) == "https://api.sarvam.ai/v1/chat/completions"
        assert request.headers["api-subscription-key"] == "fixture-key"
        body = json.loads(request.content)
        assert body["model"] == PROFILE.model
        assert body["reasoning_effort"] is None
        assert body["response_format"]["json_schema"]["schema"] == Titles.model_json_schema()
        assert body["messages"][1]["content"] == json.dumps({"job_title": "Engineer"})
        return httpx.Response(200, json=completion('{"titles":["Backend Engineer"]}'))

    mock_sarvam(monkeypatch, handler)
    result = SarvamProvider().generate(PROFILE, "Return titles", {"job_title": "Engineer"}, Titles)
    assert Titles.model_validate(result.data).titles == ["Backend Engineer"]
    assert (result.input_tokens, result.output_tokens) == (20, 8)


@pytest.mark.parametrize(
    "body,status,error",
    [
        (completion("", "length"), 200, ProviderError),
        (completion(None), 200, ProviderError),
        (completion("invalid JSON"), 200, ProviderError),
        (completion('{"titles":[]}'), 200, ValidationError),
        ({"error": "vendor-private-body"}, 403, httpx.HTTPStatusError),
    ],
)
def test_sarvam_rejects_failed_or_invalid_output(monkeypatch, body, status, error):
    mock_sarvam(monkeypatch, lambda request: httpx.Response(status, json=body))
    with pytest.raises(error):
        result = SarvamProvider().generate(PROFILE, "Return titles", {}, Titles)
        Titles.model_validate(result.data)


def test_runtime_bounds_invalid_provider_retries_and_redacts_error(clients, engine, monkeypatch):
    client = clients()
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(403, json={"error": "vendor-private-body"})

    mock_sarvam(monkeypatch, handler)
    monkeypatch.setattr(runtime, "profiles", lambda: {PROFILE.id: PROFILE})
    with pytest.raises(ProviderError) as error:
        runtime.execute(
            "assistant",
            {"job_title": "Engineer"},
            Titles,
            workspace_id=client.workspace_id,
            user_id=client.user_id,
            ai_profiles={"assistant": PROFILE.id},
            engine=engine,
        )
    assert "vendor-private-body" not in str(error.value)
    assert len(calls) == 1
    with Session(engine) as session:
        runs = session.exec(select(AgentRun)).all()
        assert len(runs) == 1
        assert all(run.status == "failed" and run.error_code == "configuration" for run in runs)


def test_sarvam_timeout_is_not_retried_inside_adapter(monkeypatch):
    calls = []

    def handler(request):
        calls.append(request)
        raise httpx.ReadTimeout("fixture timeout", request=request)

    mock_sarvam(monkeypatch, handler)
    with pytest.raises(httpx.ReadTimeout):
        SarvamProvider().generate(PROFILE, "Return titles", {}, Titles)
    assert len(calls) == 1


def test_sarvam_attempt_deadline_cancels_transport(monkeypatch):
    import asyncio
    from dataclasses import replace

    cancelled = []

    async def slow(request):
        try:
            await asyncio.sleep(1)
        finally:
            cancelled.append(True)
        return httpx.Response(200, json=completion('{"titles":["Engineer"]}'))

    mock_sarvam(monkeypatch, slow)
    with pytest.raises(TimeoutError):
        SarvamProvider().generate(replace(PROFILE, timeout_seconds=0.01), "Return titles", {}, Titles)
    assert cancelled == [True]


@pytest.mark.parametrize("adapter", ["OpenAIProvider", "CompatibleProvider"])
def test_openai_connection_errors_remain_retryable(monkeypatch, adapter):
    from openai import APIConnectionError

    from app.providers import openai as adapters

    provider = getattr(adapters, adapter)()

    async def disconnected(*args):
        raise APIConnectionError(request=httpx.Request("POST", "https://example.com"))

    monkeypatch.setattr(provider, "_generate", disconnected)
    with pytest.raises(ProviderError) as error:
        provider.generate(PROFILE, "Prompt", {}, Titles)
    assert error.value.category == "transient"


def test_sarvam_pattern_is_local_but_still_enforced(monkeypatch, clients, engine):
    from app.providers.sarvam import wire_schema
    from app.schemas import EvidenceQuote

    client = clients()
    calls = []

    def handler(request):
        body = json.loads(request.content)
        assert '"pattern"' not in json.dumps(body["response_format"]["json_schema"]["schema"])
        calls.append(body)
        return httpx.Response(200, json=completion('{"answer_id":"a","quote":"   "}'))

    mock_sarvam(monkeypatch, handler)
    monkeypatch.setattr(runtime, "profiles", lambda: {PROFILE.id: PROFILE})
    with pytest.raises(ProviderError) as error:
        runtime.execute(
            "assistant",
            {},
            EvidenceQuote,
            workspace_id=client.workspace_id,
            user_id=client.user_id,
            ai_profiles={"assistant": PROFILE.id},
            engine=engine,
        )
    assert error.value.category == "invalid_output" and len(calls) == 2
    full = EvidenceQuote.model_json_schema()
    assert "pattern" not in wire_schema(full)["properties"]["quote"]
    assert full["properties"]["quote"]["pattern"] == r"\S"
    assert wire_schema({"properties": {"pattern": {"type": "string"}}}) == {
        "properties": {"pattern": {"type": "string"}}
    }
