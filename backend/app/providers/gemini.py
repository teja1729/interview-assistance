"""Google adapter with one cancellable attempt; the agent runtime owns retries."""

import asyncio
import json

from google import genai
from google.genai import types

from .base import Completion
from .grounding import parse_grounding


class GeminiProvider:
    def search(self, profile, system, payload, schema):
        return asyncio.run(self._search(profile, system, payload))

    async def _search(self, profile, system, payload):
        client = genai.Client(
            api_key=profile.api_key,
            http_options=types.HttpOptions(
                timeout=int(profile.timeout_seconds * 1000), retry_options=types.HttpRetryOptions(attempts=1)
            ),
        )
        async with asyncio.timeout(profile.timeout_seconds), client.aio as aio:
            response = await aio.models.generate_content(
                model=profile.model,
                contents=json.dumps(payload, ensure_ascii=False),
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    tools=[types.Tool(google_search=types.GoogleSearch())],
                    max_output_tokens=profile.max_output_tokens,
                    automatic_function_calling=types.AutomaticFunctionCallingConfig(disable=True),
                ),
            )
        brief = parse_grounding(payload["company"], response, payload.get("official_url", ""))
        usage = response.usage_metadata
        return Completion(
            brief.model_dump(),
            (usage.prompt_token_count or 0) if usage else 0,
            (usage.candidates_token_count or 0) if usage else 0,
        )

    def generate(self, profile, system, payload, schema):
        return asyncio.run(self._generate(profile, system, payload, schema))

    async def _generate(self, profile, system, payload, schema):
        client = genai.Client(
            api_key=profile.api_key,
            http_options=types.HttpOptions(
                timeout=int(profile.timeout_seconds * 1000), retry_options=types.HttpRetryOptions(attempts=1)
            ),
        )
        async with asyncio.timeout(profile.timeout_seconds), client.aio as aio:
            response = await aio.models.generate_content(
                model=profile.model,
                contents=json.dumps(payload, ensure_ascii=False),
                config=types.GenerateContentConfig(
                    system_instruction=system,
                    response_mime_type="application/json",
                    response_json_schema=schema.model_json_schema(),
                    max_output_tokens=profile.max_output_tokens,
                ),
            )
        usage = response.usage_metadata
        return Completion(
            json.loads(response.text or "{}"),
            (usage.prompt_token_count or 0) if usage else 0,
            (usage.candidates_token_count or 0) if usage else 0,
        )
