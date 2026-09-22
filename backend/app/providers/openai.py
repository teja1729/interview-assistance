"""Responses and Chat compatibility adapters; all attempts have hard cancellation deadlines."""

import asyncio
import json

from openai import APIConnectionError, AsyncOpenAI

from .base import Completion, ProviderError


class OpenAIProvider:
    def generate(self, profile, system, payload, schema):
        try:
            return asyncio.run(self._generate(profile, system, payload, schema))
        except APIConnectionError as exc:
            raise ProviderError("The AI service connection failed.", category="transient") from exc

    async def _generate(self, profile, system, payload, schema):
        async with (
            asyncio.timeout(profile.timeout_seconds),
            AsyncOpenAI(api_key=profile.api_key, timeout=profile.timeout_seconds, max_retries=0) as client,
        ):
            response = await client.responses.parse(
                model=profile.model,
                instructions=system,
                input=json.dumps(payload, ensure_ascii=False),
                text_format=schema,
                max_output_tokens=profile.max_output_tokens,
                store=False,
            )
        if response.output_parsed is None:
            raise ProviderError("The model did not produce a valid response.", category="invalid_output")
        usage = response.usage
        return Completion(
            response.output_parsed.model_dump(), usage.input_tokens if usage else 0, usage.output_tokens if usage else 0
        )


class CompatibleProvider:
    def generate(self, profile, system, payload, schema):
        try:
            return asyncio.run(self._generate(profile, system, payload, schema))
        except APIConnectionError as exc:
            raise ProviderError("The AI service connection failed.", category="transient") from exc

    async def _generate(self, profile, system, payload, schema):
        async with (
            asyncio.timeout(profile.timeout_seconds),
            AsyncOpenAI(
                api_key=profile.api_key, base_url=profile.base_url, timeout=profile.timeout_seconds, max_retries=0
            ) as client,
        ):
            response = await client.chat.completions.create(
                model=profile.model,
                messages=[
                    {
                        "role": "system",
                        "content": system
                        + "\nReturn JSON matching this schema: "
                        + json.dumps(schema.model_json_schema()),
                    },
                    {"role": "user", "content": json.dumps(payload, ensure_ascii=False)},
                ],
                response_format={"type": "json_object"},
                max_tokens=profile.max_output_tokens,
            )
        choice = response.choices[0]
        if choice.finish_reason != "stop":
            raise ProviderError("The model response was incomplete.", category="invalid_output")
        usage = response.usage
        return Completion(
            json.loads(choice.message.content or "{}"),
            usage.prompt_tokens if usage else 0,
            usage.completion_tokens if usage else 0,
        )
