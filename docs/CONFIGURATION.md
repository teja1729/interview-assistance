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
| LINKEDIN_CLIENT_ID / LINKEDIN_CLIENT_SECRET | empty | LinkedIn OIDC credentials; optional alongside Google |
| OPENAI_API_KEY | empty | Reasoning-provider credentials for OpenAI profiles |
| LOCAL_USAGE_OVERRIDES | false | Enables operator allowances only when APP_ENV=development |
| LOCAL_INTERVIEW_LIMIT / LOCAL_AI_CALL_LIMIT | 100 / 5000 | Monthly local allowances when the override is enabled; production ignores them |
| COMPATIBLE_CONTEXT_TOKENS | 0 | Verified context window required for compatible endpoints |
| SARVAM_API_KEY / SARVAM_MODEL | empty / sarvam-105b | Sarvam V1 structured chat; separate conversation profile also available |
| COMPATIBLE_API_KEY / BASE_URL / MODEL | empty | OpenAI-compatible endpoint; use full COMPATIBLE_ prefix for each |
| AUDIO_PROVIDER | sarvam | Sarvam voice-to-voice; browser disables cloud speech |
| SARVAM_STT_MODEL / SARVAM_TTS_MODEL | saaras:v3 / bulbul:v3 | Speech models, independent of reasoning profiles |
| SARVAM_TTS_VOICE | ritu | Operator-selected natural English voice |
| STRIPE_SECRET_KEY / STRIPE_WEBHOOK_SECRET | empty | Required together to enable billing |
| STRIPE_PRO_PRICE_ID | empty | Recurring personal Pro price managed in Stripe |
| STRIPE_TEAM_PRICE_ID | empty | Legacy subscription reconciliation only; no new team checkout |
| RAZORPAY_KEY_ID / RAZORPAY_KEY_SECRET | empty | Server-side Razorpay Standard Checkout credentials |
| RAZORPAY_STARTER_MONTHLY_AMOUNT_PAISE / YEARLY | 99900 / 999900 | One-time Starter prices for 30 / 365 days, in paise |
| RAZORPAY_PRO_MONTHLY_AMOUNT_PAISE / YEARLY | 299900 / 2999900 | One-time Pro prices for 30 / 365 days, in paise |
| RAZORPAY_SENIOR_MONTHLY_AMOUNT_PAISE / YEARLY | 499900 / 4999900 | One-time Senior prices for 30 / 365 days, in paise |
| BACKEND_URL (frontend only) | http://127.0.0.1:8000 | Server-only proxy destination; supplied at build time for containers |

Generate a secret with `python -c 'import secrets; print(secrets.token_urlsafe(48))'` and place it in
your secret store. Model routing comes from `config/models.toml`; legacy model environment overrides are ignored.

## Google sign-up/sign-in

1. Create a Google Cloud OAuth consent screen and a **Web application** OAuth client.
2. Register `http://localhost:3000/api/auth/google/callback` for local development.
3. Register `https://YOUR_DOMAIN/api/auth/google/callback` for production.
4. Set GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET and FRONTEND_ORIGIN. Restart the API.
5. Test with an allowed consent-screen user, then publish/verify the OAuth app as required by Google.

Authlib performs OIDC state/nonce/token validation. The provider subject is the identity key;
email alone never links accounts. A Google login and a LinkedIn login with the same address stay
separate. Only verified email identities are provisioned. First login creates a user and personal
Starter account. OAuth tokens are discarded after sign-in.

Reference: https://developers.google.com/identity/openid-connect/openid-connect
Library: https://docs.authlib.org/en/latest/oauth2/client/web/starlette.html

## LinkedIn sign-up/sign-in

1. Create a LinkedIn app and add the product **Sign In with LinkedIn using OpenID Connect**.
2. Register `http://localhost:3000/api/auth/linkedin/callback` for local development.
3. Register `https://YOUR_DOMAIN/api/auth/linkedin/callback` for production.
4. Set LINKEDIN_CLIENT_ID, LINKEDIN_CLIENT_SECRET and FRONTEND_ORIGIN. Restart the API.
5. Confirm `/api/auth/config` returns `linkedin_enabled: true`, then use **Continue with LinkedIn**.

The same verified-email and separate-subject rules apply. Production still requires Google credentials.

Reference: https://learn.microsoft.com/en-us/linkedin/consumer/integrations/self-serve/sign-in-with-linkedin-v2

## Model selection

Set credentials in `backend/.env`, then edit `[agents]` in `backend/config/models.toml`:

```toml
[agents]
planner = "sarvam"
interviewer = "sarvam_conversations"
evaluator = "sarvam"
coach = "sarvam"
resume = "sarvam"
assistant = "sarvam"
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
interactive latency. Set `SARVAM_API_KEY`; assign `sarvam` to roles that need the flagship model.
The interviewer uses `sarvam_conversations` by default, with `sarvam` configured as its fallback.
Speech settings stay independent. Sarvam-M is retired; do not use it in new profiles. Reference:
https://docs.sarvam.ai/api/api-guides-tutorials/chat-completion/overview

## Voice conversation

See [VOICE.md](VOICE.md) for the turn-taking lifecycle and adapter boundaries. Set
`AUDIO_PROVIDER=sarvam` with `SARVAM_API_KEY` to enable both microphone answers and cloud playback.
The browser prioritizes cloud speech whenever configured; old local browser-voice preferences are
ignored. Transcription runs in verbatim mode. Change `SARVAM_TTS_VOICE` in server configuration,
then restart the API. The interview UI has no model/provider selectors.

## Stripe legacy subscriptions

Stripe remains enabled for existing Pro subscriptions and their billing portal; new purchases use
Razorpay Standard Checkout. Configure the existing test/live Stripe secrets and webhook signing
secret to keep renewals and portal management working.

Forward events locally with `stripe listen --forward-to localhost:8000/api/billing/webhook`. Subscribe
to customer.subscription.created, .updated and .deleted. Webhook signatures are checked against the
raw body and subscription state is reconciled with version fencing. `past_due`/inactive subscriptions
use Starter limits.

Reference: https://docs.stripe.com/webhooks

## Razorpay Standard Checkout

New Starter, Pro and Senior purchases use one-time Razorpay orders. Monthly purchases grant 30 days
of access; yearly purchases grant 365 days. Repeat purchases extend from the later of the current
expiry or payment verification time. Existing Stripe subscriptions remain on Stripe management and
are not migrated. Backend monthly usage allowances are 20 interviews for Starter, 40 for Pro and
100 for Senior; AI action allowances are 1,000, 2,000 and 5,000 respectively.

1. Set `RAZORPAY_KEY_ID` and `RAZORPAY_KEY_SECRET` from the same Razorpay test or live mode.
2. Optionally set the six `RAZORPAY_<PLAN>_<PERIOD>_AMOUNT_PAISE` values. Defaults match the current
   displayed prices: Starter ₹999/₹9,999, Pro ₹2,999/₹29,999 and Senior ₹4,999/₹49,999. The browser
   cannot submit the amount.
3. Apply the Alembic migration and restart the API. No Razorpay webhook or plan setup is required.
4. Test checkout with test-mode keys. The API creates the order, verifies the Standard Checkout HMAC
   signature, fetches the payment from Razorpay, and checks order, amount, currency and captured status
   before granting access.

References: [Razorpay Standard Checkout integration](https://razorpay.com/docs/payments/payment-gateway/web-integration/standard/integration-steps/),
[Create an Order](https://razorpay.com/docs/api/orders/create/).

## Company research

New web research is currently unavailable because no search provider is configured. Previously saved,
candidate-owned sources remain reusable. Interviews continue with the supplied job description.

## Usage and saved setup

Starter allows 3 interview reservations and 150 logical AI actions per UTC month. Interview creation,
reasoning stages and speech consume separate counters; failed paid attempts still count. Rate limits
are separate (30 paid requests/minute), with a specific retry message. Errors name the exhausted resource.
Before paid company search, creating an interview checks its interview allowance. Reading a saved JD,
research result, report or history does not consume a new model allowance.

For local development, enable LOCAL_USAGE_OVERRIDES=true and restart the API and worker. Existing usage
counters and the Stripe plan remain unchanged; only the effective development allowance changes. Production
always uses the server-owned subscription limits. These app counters do not change provider billing/quota.
