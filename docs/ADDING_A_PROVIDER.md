# Adding or changing an AI provider

The application depends on the `Provider.generate(profile, system, payload, schema)` protocol,
not vendor SDKs. It returns `Completion(data, input_tokens, output_tokens)`. The runtime validates
`data` again even when the vendor supports structured output. Providers must not mutate the DB.

## Same vendor, different model

Add a named profile to `backend/config/models.toml`:

```toml
[profiles.review_model_v2]
label = "Review model v2"
provider = "openai"
model = "your-account-supported-model-id"
api_key_env = "OPENAI_API_KEY"
fallback = "openai"
context_tokens = 128000 # Set the actual limit supported by this model.
```

Assign the new profile in the existing `[agents]` section, for example `evaluator = "review_model_v2"`.
Deploy the same TOML to the API and worker; restart both if credentials changed. No frontend edit
or database preference update is needed.
New interviews retain resolved execution bundles. Preserve legacy profile IDs for historical sessions
that predate execution snapshots; their IDs still resolve dynamically.
The registry checks configured availability without exposing the secret. It does not probe paid
APIs or guarantee account entitlement.

## New vendor

1. Add `providers/vendor.py` implementing generate. Put all vendor SDK imports here.
2. Translate the role prompt, untrusted JSON payload and output schema to that vendor's format.
3. Apply the supplied profile.timeout_seconds as a cancellable total timeout, enforce
   profile.max_output_tokens, and disable SDK retries. Runtime retry/fallback is already bounded. Return usage metadata when available; do not fabricate token counts.
4. Register an instance in `providers/__init__.py`. Add a TOML profile with an environment-key name.
5. Keep base URLs operator-configured; browser users must never select arbitrary destinations.
6. Add adapter tests using mocked SDK responses, including refusal, non-JSON, missing fields,
   timeout and unavailable-model cases. Run the shared agent/state-machine tests.
7. Update CONFIGURATION.md and dependency locks.

The compatible adapter uses Chat Completions JSON mode plus local validation. OpenAI uses the
Responses API's Pydantic structured-output helper with `store=False`. Gemini receives JSON Schema.
Native schema enforcement improves reliability but never replaces application-level checks.
Sarvam uses native V1 JSON Schema output through HTTPX and disables thinking for call latency.

Speech is independent. Changing the reasoning provider must not silently change audio retention,
transcription or TTS behavior. `services/speech.py` validates WAV and dispatches to Gemini or
`services/sarvam_speech.py`. See `VOICE.md` before changing timeouts, chunking or voice behavior.

Official references used for the initial adapters:
- https://developers.openai.com/api/docs/guides/structured-outputs
- https://ai.google.dev/gemini-api/docs/structured-output
- https://docs.sarvam.ai/api/api-guides-tutorials/chat-completion/overview
