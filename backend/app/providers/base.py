"""Provider boundary: adapters return JSON and usage, never mutate application state."""

import os
import tomllib
from dataclasses import dataclass
from typing import Any, Protocol

from pydantic import BaseModel

from ..config import settings

AGENT_ROLES = ("planner", "interviewer", "evaluator", "coach", "resume", "assistant", "company_research")


class ProviderError(RuntimeError):
    """Safe error surfaced to clients; provider response bodies can contain sensitive inputs."""

    def __init__(self, message, *, category="transient", retry_after=0):
        super().__init__(message)
        self.category = category
        self.retry_after = retry_after


class InvalidOutput(ProviderError):
    """Safe semantic repair hint, containing field names/codes but never candidate values."""

    def __init__(self, code):
        super().__init__("The model output needs correction.", category="invalid_output")
        self.code = code


@dataclass(frozen=True)
class Profile:
    id: str
    label: str
    provider: str
    model: str
    api_key: str = ""
    base_url: str = ""
    fallback: str = ""
    api_key_env: str = ""
    timeout_seconds: float = 45
    max_output_tokens: int = 4096
    context_tokens: int = 128000
    capabilities: tuple[str, ...] = ("structured_output",)
    tokenizer: str = "heuristic"
    concurrency: int = 4

    @property
    def available(self) -> bool:
        if self.provider == "demo":
            return settings.demo_login and not settings.production
        return bool(self.api_key and self.model and (self.provider != "compatible" or self.base_url))


@dataclass
class Completion:
    data: Any
    input_tokens: int = 0
    output_tokens: int = 0


class Provider(Protocol):
    def generate(self, profile: Profile, system: str, payload: dict, schema: type[BaseModel]) -> Completion: ...


def profiles() -> dict[str, Profile]:
    with settings.models_file.open("rb") as handle:
        config = tomllib.load(handle)
    return {
        key: Profile(
            id=key,
            label=value["label"],
            provider=value["provider"],
            model=os.getenv(value.get("model_env", ""), value.get("model", "")),
            api_key=os.getenv(value.get("api_key_env", ""), ""),
            base_url=os.getenv(value.get("base_url_env", ""), ""),
            fallback=value.get("fallback", ""),
            api_key_env=value.get("api_key_env", ""),
            context_tokens=int(os.getenv(value.get("context_tokens_env", ""), value.get("context_tokens", 0))),
            capabilities=tuple(value.get("capabilities", ["structured_output"])),
            tokenizer=value.get("tokenizer", "heuristic"),
            concurrency=value.get("concurrency", 4),
        )
        for key, value in config["profiles"].items()
    }


def agent_profiles() -> dict[str, str]:
    """Resolve server-owned role routing; legacy account preferences are never consulted.

    Explicit local test mode overrides all roles to prevent paid calls in isolated tests.
    Normal operation reads TOML on each invocation, with the environment default used
    only for omitted roles. Interview services persist a snapshot for later turns/jobs.
    """
    if settings.demo_login and not settings.production and settings.default_profile == "demo":
        return dict.fromkeys(AGENT_ROLES, "demo")
    with settings.models_file.open("rb") as handle:
        assignments = tomllib.load(handle).get("agents", {})
    if set(assignments) - set(AGENT_ROLES):
        raise ProviderError("Unknown AI role in server model configuration. Contact the application operator.")
    return {role: assignments.get(role, settings.default_profile) for role in AGENT_ROLES}
