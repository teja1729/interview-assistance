"""Native Sarvam chat with a cancellable wall-clock deadline and role output budget."""

import asyncio
import json

import httpx

from .base import Completion, InvalidOutput


def wire_schema(value):
    r"""Keep regex checks local: Sarvam's decoder produced invalid quotes with \S patterns.

    Reproduced with synthetic English/Hindi evidence. The full Pydantic schema still validates
    every response in the runtime. This changes provider decoding constraints, never acceptance.
    """
    if isinstance(value, dict):
        return {
            key: wire_schema(item) for key, item in value.items() if not (key == "pattern" and isinstance(item, str))
        }
    if isinstance(value, list):
        return [wire_schema(item) for item in value]
    return value


class SarvamProvider:
    def generate(self, profile, system, payload, schema):
        return asyncio.run(self._generate(profile, system, payload, schema))

    async def _generate(self, profile, system, payload, schema):
        async with (
            asyncio.timeout(profile.timeout_seconds),
            httpx.AsyncClient(timeout=profile.timeout_seconds) as client,
        ):
            response = await client.post(
                "https://api.sarvam.ai/v1/chat/completions",
                headers={"api-subscription-key": profile.api_key},
                json={
                    "model": profile.model,
                    "messages": [
                        {"role": "system", "content": system},
                        {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                    ],
                    "response_format": {
                        "type": "json_schema",
                        "json_schema": {
                            "name": schema.__name__,
                            "strict": True,
                            "schema": wire_schema(schema.model_json_schema()),
                        },
                    },
                    "reasoning_effort": None,
                    "max_tokens": profile.max_output_tokens,
                    "temperature": 0.2,
                },
            )
            response.raise_for_status()
            body = response.json()
        choice = body["choices"][0]
        if choice.get("finish_reason") != "stop":
            raise InvalidOutput(
                "response_truncated" if choice.get("finish_reason") == "length" else "response_incomplete"
            )
        if not choice["message"].get("content"):
            raise InvalidOutput("response_empty")
        usage = body.get("usage") or {}
        try:
            data = json.loads(choice["message"]["content"])
        except json.JSONDecodeError as exc:
            code = "response_json_syntax"
            if exc.msg.startswith("Invalid \\escape"):
                code = "response_json_invalid_escape"
            elif exc.msg.startswith("Invalid control character"):
                code = "response_json_unescaped_control_character"
            elif exc.msg.startswith("Expecting value"):
                code = "response_json_expected_value"
            raise InvalidOutput(code) from exc
        return Completion(data, usage.get("prompt_tokens", 0), usage.get("completion_tokens", 0))
