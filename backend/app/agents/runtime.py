"""Bounded inference with immutable specs, classified retries and optional diagnostic traces.

Authoritative quota reservation stays in services. Semantic validators run inside the attempt,
so rejected artifacts are never traced as successful or passed to the next workflow stage.
"""

import json
import logging
import threading
import time
from dataclasses import replace

import httpx
from pydantic import ValidationError
from sqlmodel import Session

from .. import db
from ..models import AgentRun
from ..providers import PROVIDERS
from ..providers.base import AGENT_ROLES, InvalidOutput, ProviderError, agent_profiles, profiles
from . import specs
from .tokens import input_estimate  # estimate_tokens is also used by operator tooling

log = logging.getLogger(__name__)
ROLES = AGENT_ROLES
PROMPTS = specs.PROMPTS
PROMPT_VARIANTS = specs.VARIANTS


_semaphores = {}
_semaphore_lock = threading.Lock()


def provider_semaphore(profile):
    # Per-process bound shared by reports and request threads. Multiple worker processes must
    # divide their provider quota accordingly; this is not a distributed rate limiter.
    key = (profile.provider, profile.model, profile.concurrency)
    with _semaphore_lock:
        return _semaphores.setdefault(key, threading.BoundedSemaphore(max(1, profile.concurrency)))


def classify(exc):
    if isinstance(exc, ProviderError):
        return exc
    if isinstance(exc, (ValidationError, json.JSONDecodeError)):
        return ProviderError("The AI response did not meet its contract.", category="invalid_output")
    if isinstance(exc, (TimeoutError, httpx.TimeoutException)):
        return ProviderError("The AI service timed out. Please retry.", category="transient")
    status = getattr(exc, "status_code", None) or getattr(exc, "code", None)
    response = getattr(exc, "response", None)
    if isinstance(exc, httpx.HTTPStatusError):
        status = exc.response.status_code
    if status == 429:
        try:
            delay = float(response.headers.get("retry-after", "1")) if response is not None else 1
        except (ValueError, TypeError):
            delay = 1
        return ProviderError(
            "The AI service is busy. Please retry shortly.", category="rate_limited", retry_after=max(0, min(60, delay))
        )
    if status in {401, 403, 404}:
        return ProviderError("The AI service configuration needs operator attention.", category="configuration")
    if isinstance(status, int) and 400 <= status < 500 and status not in {408, 409}:
        return ProviderError("The AI service rejected this request.", category="permanent")
    if isinstance(exc, httpx.TransportError) or status in {408, 409, 500, 502, 503, 504}:
        return ProviderError("The AI service is temporarily unavailable.", category="transient")
    return ProviderError("The AI step failed. Contact the application operator.", category="internal")


def trace(engine=None, **metadata):
    """Best-effort diagnostics. These are not the authoritative usage or security audit ledger."""
    try:
        with Session(engine or db.engine) as session:
            session.add(AgentRun(**metadata))
            session.commit()
    except Exception as exc:  # noqa: BLE001 - diagnostics must not mask valid inference
        log.error("agent_trace_failed error=%s", type(exc).__name__)


def execute(
    agent,
    payload,
    schema,
    *,
    workspace_id,
    user_id,
    ai_profiles=None,
    interview_id=None,
    engine=None,
    execution=None,
    operation_id=None,
    stage="inference",
    validate=None,
):
    if agent not in ROLES:
        raise ValueError("Unknown agent")
    common = {
        "workspace_id": workspace_id,
        "user_id": user_id,
        "interview_id": interview_id,
        "agent": agent,
        "operation_id": operation_id,
        "stage": stage,
    }
    try:
        if execution:
            candidates, policy, prompt, version = specs.resolve(execution, agent, schema, engine)
        else:
            registry = profiles()
            profile = registry.get((ai_profiles or agent_profiles()).get(agent))
            if profile is None:
                raise ProviderError("The assigned AI profile is missing.", category="configuration")
            candidates = [profile]
            if profile.fallback:
                if profile.fallback not in registry:
                    raise ProviderError("The fallback profile is missing.", category="configuration")
                candidates.append(registry[profile.fallback])
            policy = specs.POLICIES[agent]
            prompt = specs.load_prompt(specs.prompt_name(agent, schema))
            version = specs.digest(prompt)[:12]
        if candidates[0].provider != "demo" and any(p.provider == "demo" for p in candidates):
            raise ProviderError("Live providers cannot fall back to fixtures.", category="configuration")
    except Exception as exc:
        failure = classify(exc)
        trace(
            engine,
            **common,
            prompt_version="unresolved",
            provider="unresolved",
            model="unresolved",
            status="failed",
            duration_ms=0,
            error_code=failure.category,
            attempt=0,
        )
        raise failure from exc
    deadline = time.monotonic() + policy.deadline
    request = dict(payload)
    last_error = None
    candidate_index = 0
    for attempt in range(2):
        candidate = candidates[candidate_index]
        started = time.monotonic()
        response, error = None, None
        try:
            if not candidate.available or candidate.provider not in PROVIDERS:
                raise ProviderError("This AI service is not configured.", category="configuration")
            remaining = deadline - started
            if remaining <= 0:
                raise ProviderError("The AI step exceeded its deadline.", category="deadline")
            candidate = replace(
                candidate,
                timeout_seconds=min(policy.attempt_timeout, remaining),
                max_output_tokens=policy.output_tokens,
            )
            # Include instructions/schema/output budget, with a further framing allowance.
            if (
                input_estimate(request, prompt, schema, candidate.tokenizer) + policy.output_tokens
                > candidate.context_tokens
            ):
                raise ProviderError(
                    "This input exceeds the selected model's context budget. Shorten the supplied material.",
                    category="context_limit",
                )
            capability = "search" if agent == "company_research" else "structured_output"
            adapter = PROVIDERS[candidate.provider]
            if capability not in candidate.capabilities or (capability == "search" and not hasattr(adapter, "search")):
                raise ProviderError("The assigned model does not support this capability.", category="configuration")
            semaphore = provider_semaphore(candidate)
            if not semaphore.acquire(timeout=max(0, deadline - time.monotonic())):
                raise ProviderError("The AI step exceeded its deadline.", category="deadline")
            try:
                candidate = replace(
                    candidate, timeout_seconds=min(policy.attempt_timeout, max(0.01, deadline - time.monotonic()))
                )
                response = (
                    adapter.search(candidate, prompt, request, schema)
                    if capability == "search"
                    else adapter.generate(candidate, prompt, request, schema)
                )
            finally:
                semaphore.release()
            if time.monotonic() > deadline:
                raise ProviderError("The AI step exceeded its deadline.", category="deadline")
            output = schema.model_validate(response.data)
            if validate:
                validate(output)
            return output
        except Exception as exc:
            error = classify(exc)
            last_error = error
            log.warning("agent=%s stage=%s attempt=%s category=%s", agent, stage, attempt + 1, error.category)
            repair = []
            if isinstance(exc, ValidationError):
                repair = [
                    {"field": ".".join(map(str, e["loc"])), "code": e["type"]}
                    for e in exc.errors(include_input=False, include_url=False)[:8]
                ]
            elif isinstance(exc, InvalidOutput):
                repair = [{"field": "output", "code": exc.code}]
            elif error.category == "invalid_output":
                repair = [{"field": "output", "code": "return_complete_valid_json"}]
            if repair:
                log.info("agent=%s repair=%s", agent, repair)
                request = {**payload, "validation_feedback": repair}
            # Permanent errors may switch to an explicitly configured different provider once.
            may_fallback = attempt == 0 and len(candidates) > 1 and error.category in {"configuration", "permanent"}
            retryable = error.category in {"transient", "rate_limited", "invalid_output"}
            if attempt == 1 or not (retryable or may_fallback):
                raise error from exc
            # Repair malformed output with the model that produced it. Only service/configuration
            # failures select an explicitly configured fallback. Two calls remain the hard cap.
            if error.category != "invalid_output" and len(candidates) > 1:
                candidate_index = 1
        finally:
            trace(
                engine,
                **common,
                prompt_version=version,
                provider=candidate.provider,
                model=candidate.model,
                status="failed" if error else "succeeded",
                duration_ms=int((time.monotonic() - started) * 1000),
                error_code=error.category if error else None,
                attempt=attempt + 1,
                input_tokens=response.input_tokens if response else 0,
                output_tokens=response.output_tokens if response else 0,
            )
        delay = error.retry_after if error and error.category == "rate_limited" else 0
        if delay:
            if time.monotonic() + delay + 1 >= deadline:
                raise error
            time.sleep(delay)
    raise last_error or ProviderError("No configured AI provider is available.", category="configuration")
