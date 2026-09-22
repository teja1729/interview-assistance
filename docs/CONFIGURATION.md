# Configuration reference

Never put secrets in `NEXT_PUBLIC_*`, model TOML, database preferences, screenshots, or Git.
The backend reads `backend/.env`; actual environment variables override the file.

## Environment

| Variable | Local default | Purpose |
| --- | --- | --- |
| APP_ENV | development | production enables configuration safety checks and hides Swagger UI |
| DATABASE_URL | SQLite `data/saas.db` | Production: `postgresql+psycopg://user:password@host/database` |
| FRONTEND_ORIGIN | http://localhost:3000 | Exact trusted origin and OAuth redirect origin |
| SESSION_SECRET | development-only value | Random 32+ characters required in production |
| AUTH_DEMO_ENABLED | false | Opt-in automated-test fixtures only; false in normal use and production |
| AI_DEFAULT_PROFILE | sarvam | Fallback for roles omitted from TOML `[agents]`; requires its API key |
| AI_MODELS_FILE | config/models.toml | Optional absolute TOML path |
| INLINE_WORKER | false | Embedded worker for test/simple local runs |
| GOOGLE_CLIENT_ID / GOOGLE_CLIENT_SECRET | empty | Google web OAuth credentials |
| GEMINI_API_KEY / OPENAI_API_KEY | empty | Reasoning-provider credentials; GEMINI_API_KEY also enables company web research |
| COMPANY_RESEARCH_ENABLED | true | Setup research; seventh role and search model selected in models.toml |
| LOCAL_USAGE_OVERRIDES | false | Enables operator allowances only when APP_ENV=development |
| LOCAL_INTERVIEW_LIMIT / LOCAL_AI_CALL_LIMIT | 100 / 5000 | Monthly local allowances when the override is enabled; production ignores them |
| COMPATIBLE_CONTEXT_TOKENS | 0 | Verified context window required for compatible endpoints |
| SARVAM_API_KEY / SARVAM_MODEL | empty / sarvam-105b | Sarvam V1 structured chat; separate conversation profile also available |
| COMPATIBLE_API_KEY / BASE_URL / MODEL | empty | OpenAI-compatible endpoint; use full COMPATIBLE_ prefix for each |
| AUDIO_PROVIDER | sarvam | Sarvam voice-to-voice; gemini for alternative cloud speech; browser for typed input/local voice |
| SARVAM_STT_MODEL / SARVAM_TTS_MODEL | saaras:v3 / bulbul:v3 | Speech models, independent of reasoning profiles |
| SARVAM_TTS_VOICE / SPEECH_LANGUAGE | ritu / en-IN | Operator-selected natural voice; default output language, overridden by the saved interview language |
| TRANSCRIPTION_MODEL | gemini-3.5-flash | Dedicated transcription model |
| GEMINI_TTS_MODEL / GEMINI_TTS_VOICE | example profile / Kore | Cloud speech model and voice |
| STRIPE_SECRET_KEY / STRIPE_WEBHOOK_SECRET | empty | Required together to enable billing |
| STRIPE_PRO_PRICE_ID | empty | Recurring personal Pro price managed in Stripe |
| STRIPE_TEAM_PRICE_ID | empty | Legacy subscription reconciliation only; no new team checkout |
| BACKEND_URL (frontend only) | http://127.0.0.1:8000 | Server-only proxy destination; supplied at build time for containers |

Generate a secret with `python -c 'import secrets; print(secrets.token_urlsafe(48))'` and place it in
your secret store. Existing prototype GEMINI_* values may remain, but model routing now comes
from `config/models.toml`; the old GEMINI_INTERVIEW_MODEL / REPORT_MODEL variables are retired.

## Google sign-up/sign-in

1. Create a Google Cloud OAuth consent screen and a **Web application** OAuth client.
2. Register `http://localhost:3000/api/auth/google/callback` for local development.
3. Register `https://YOUR_DOMAIN/api/auth/google/callback` for production.
4. Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET and FRONTEND_ORIGIN. Restart the API.
5. Test with an allowed consent-screen user, then publish/verify the OAuth app as required by Google.

Authlib performs OIDC state/nonce/token validation. The Google `sub` is the identity key;
email alone never links accounts. Only verified email identities are provisioned. First login
creates a user and personal Starter account. OAuth tokens are discarded after sign-in.

Reference: https://developers.google.com/identity/openid-connect/openid-connect
Library: https://docs.authlib.org/en/latest/oauth2/client/web/starlette.html

## Model selection

Set credentials in `backend/.env`, then edit `[agents]` in `backend/config/models.toml`:

```toml
[agents]
planner = "sarvam"
interviewer = "sarvam"
evaluator = "sarvam"
coach = "sarvam"
resume = "sarvam"
assistant = "sarvam"
company_research = "gemini_search"
```

Use the ID of any configured `[profiles.<id>]` entry for each role. There are no browser controls
or preference APIs. Existing database preferences are ignored. `AI_DEFAULT_PROFILE` fills only
roles omitted from `[agents]`; it does not override explicit assignments. Configuration is read
for new sessions and standalone helper calls. Deploy the same TOML to the API and worker and restart
both after environment changes. New interviews snapshot resolved model settings, prompt text/hashes,
role budgets and credential environment references. Later routing/profile/prompt edits do not change
those sessions; credential values still rotate from the environment. Legacy interviews without the
bundle use their saved IDs until report processing snapshots a bundle. See AGENT_RUNTIME.md.

Credentials are checked for presence; availability and account entitlement are verified only when
called. Model names in the example configuration are editable examples, not a promise of availability.
A fallback must be another configured live profile. The runtime rejects a live-to-fixture fallback.
Test fixture profiles are unavailable unless test mode is explicitly enabled. Only the combination
`AUTH_DEMO_ENABLED=true`, `AI_DEFAULT_PROFILE=demo` and non-production mode overrides all TOML roles
with fixtures, keeping automated tests isolated from paid services. Turning test
mode off also denies previously issued demo-account sessions. Canned provider code lives only under
`tests/fixtures/` and is excluded from production images; failures never become successful sample responses.

Sarvam profiles use V1 JSON Schema output, the subscription-key header and disabled thinking for
interactive latency. Set `SARVAM_API_KEY`, then assign `sarvam` to roles in `[agents]`.
Assign `sarvam_conversations` to the interviewer role to use the conversation model;
it falls back to the flagship profile on failure. Speech settings stay independent. Sarvam-M is
retired; do not use it in new profiles. Reference:
https://docs.sarvam.ai/api/api-guides-tutorials/chat-completion/overview

## Voice conversation

See [VOICE.md](VOICE.md) for the turn-taking lifecycle and adapter boundaries. Set
`AUDIO_PROVIDER=sarvam` with `SARVAM_API_KEY` to enable both microphone answers and cloud playback.
The browser prioritizes cloud speech whenever configured; old local browser-voice preferences are
ignored. Transcription runs in verbatim mode. Change `SARVAM_TTS_VOICE` in server configuration,
then restart the API. The interview UI has no model/provider selectors.

## Stripe

1. Create a recurring Pro price in Stripe’s test mode, then set `STRIPE_PRO_PRICE_ID`.
2. Set the test secret key. Forward events locally:
   `stripe listen --forward-to localhost:8000/api/billing/webhook`.
3. Set the emitted webhook signing secret. For production, register the HTTPS endpoint and use
   the corresponding live credentials and signing secret.
4. Subscribe to customer.subscription.created, .updated and .deleted. Enable Stripe Customer Portal.
5. Exercise checkout, cancellation, failed payments and plan changes with test data.

Webhook signatures are verified against the raw request bytes. Only server-configured price IDs
map to entitlements. Current customer subscriptions are reconciled, so an old cancellation cannot
revoke a newer active plan. A database version fences concurrent snapshots; a losing writer refetches
Stripe before retrying. Customers with more than 100 subscriptions require operator review.
Client checkout success URLs do not grant access. `past_due`/inactive subscriptions use Starter
limits; customize this explicit policy in services/billing.py if offering a grace period.

Reference: https://docs.stripe.com/webhooks

## Company research

See [COMPANY_RESEARCH.md](COMPANY_RESEARCH.md). Configure GEMINI_API_KEY and access/quota for the
search model. Search runs only during setup, preserves dated citations, and never receives candidate
resumes or answers. The app shows unavailable research explicitly and continues with the supplied JD.

## Usage and saved setup

Starter allows 3 interview reservations and 150 logical AI actions per UTC month. Interview creation,
reasoning stages and speech consume separate counters; failed paid attempts still count. Rate limits
are separate (30 paid requests/minute), with a specific retry message. Errors name the exhausted resource.
Before paid company search, creating an interview checks its interview allowance. Reading a saved JD,
research result, report or history does not consume a new model allowance.

For local development, enable LOCAL_USAGE_OVERRIDES=true and restart the API and worker. Existing usage
counters and the Stripe plan remain unchanged; only the effective development allowance changes. Production
always uses the server-owned subscription limits. These app counters do not change provider billing/quota.
