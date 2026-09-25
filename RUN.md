# Run commands

Copy commands from this file; no source-code reading is needed. Unless a section says otherwise,
start in the **repository root**. Parenthesized commands change directory only for that command.
Use a separate terminal for each long-running service. Existing secrets in `backend/.env` are
preserved by the setup commands below.

## 1. Fastest start

Requirements: **Python 3.12+, uv, Node.js 22+, npm**. Docker is optional.

```bash
# Check installed tools.
python3 --version
uv --version
node --version
npm --version

# Start web + API + report worker. Installs missing dependencies and applies migrations.
./dev.sh
```

Open **http://localhost:3000**. Press **Ctrl-C** in that terminal to stop all three services.
The API is at **http://127.0.0.1:8000**; API documentation is at **http://localhost:3000/api/docs**.
Reports need the worker; `dev.sh` starts it automatically.

The default database is `backend/data/saas.db`. The old `backend/data/interviews.db` is preserved.
Google sign-in and AI require configured credentials. The normal app uses real model calls;
synthetic fixtures are available only through the isolated automated-testing recipe in section 8.

## 2. Install or refresh dependencies

```bash
# Create local configuration only when it is missing. Never overwrite an existing .env.
test -f backend/.env || cp backend/.env.example backend/.env

# Install the exact Python dependencies, including development tools.
(cd backend && uv sync --locked)

# Install the exact frontend dependencies. Run again after package-lock.json changes.
(cd frontend && npm ci)

# Confirm the Python lock agrees with the dependency manifest.
(cd backend && uv lock --check)
```

`dev.sh` runs Python dependency sync each time; it runs `npm ci` only if `node_modules` is missing.

## 3. Credentials, Google login and model selection

```bash
# Edit server configuration in your terminal editor; save, then restart the API and worker.
${EDITOR:-vi} backend/.env

# Edit [agents] role assignments, named model profiles, model IDs and fallback routing.
${EDITOR:-vi} backend/config/models.toml

# Confirm local environment files are excluded from Git.
git check-ignore backend/.env
```

Set these **names** in `backend/.env`; use your actual credentials only in that ignored file:

| Setting | Purpose |
| --- | --- |
| `GOOGLE_CLIENT_ID`, `GOOGLE_CLIENT_SECRET` | Google web OAuth credentials |
| `LINKEDIN_CLIENT_ID`, `LINKEDIN_CLIENT_SECRET` | LinkedIn OpenID Connect sign-in |
| `FRONTEND_ORIGIN=http://localhost:3000` | Browser origin and OAuth callback base |
| `SARVAM_API_KEY` | Enables Sarvam profiles |
| `GEMINI_API_KEY` | Enables Gemini profiles and optional cloud speech |
| `OPENAI_API_KEY` | Enables OpenAI Responses profiles |
| `COMPATIBLE_API_KEY`, `COMPATIBLE_BASE_URL`, `COMPATIBLE_MODEL` | Enables another compatible endpoint |
| `AI_DEFAULT_PROFILE` | Fallback for roles omitted from TOML `[agents]`; explicit assignments take precedence |
| `AUDIO_PROVIDER` | `sarvam` (default): voice-to-voice using SARVAM_API_KEY; `gemini`: alternative cloud speech; `browser`: typed input/local voice only |
| `SARVAM_STT_MODEL`, `SARVAM_TTS_MODEL` | `saaras:v3` transcription and `bulbul:v3` speech |
| `SARVAM_TTS_VOICE`, `SPEECH_LANGUAGE` | `ritu` and `en-IN` by default; edit here to change the interviewer voice |

Register these exact **authorized redirect URIs**:

```text
http://localhost:3000/api/auth/google/callback
http://localhost:3000/api/auth/linkedin/callback
```

For port 3100, register the same paths on `http://localhost:3100` too. For a deployment,
register `https://YOUR_DOMAIN/api/auth/google/callback` and
`https://YOUR_DOMAIN/api/auth/linkedin/callback`. The origin must match `FRONTEND_ORIGIN`.
The Google consent screen must allow your account. Completing consent requires a browser login.

Model routing is in code only: edit `[agents]` in `backend/config/models.toml`. For example,
change `evaluator = "sarvam"` to `evaluator = "gemini"` after configuring `GEMINI_API_KEY`.
The seven keys are `planner`, `interviewer`, `evaluator`, `coach`, `resume`, `assistant`, and `company_research`.
The research profile requires `search` capability; its default is `gemini_search`.
Saved workspace preferences are ignored. New interviews snapshot resolved models, prompts and policies;
existing interviews keep their snapshot. Preserve legacy profile IDs for sessions created before
execution snapshots were introduced. Deploy the same TOML to API and worker.
Speech configuration stays independent. The UI offers personal Account settings only.

For voice-to-voice interviews, set `AUDIO_PROVIDER=sarvam` and `SARVAM_TTS_VOICE=ritu` in
`backend/.env`, with `SARVAM_API_KEY` configured. Restart the API and refresh the interview page.
Join, allow microphone permission, and speak after the interviewer finishes. A three-second pause
submits your answer automatically; **Send answer** submits sooner. **Hands-free off** switches to
manual recording controls. No typing is required. See [voice behavior](docs/VOICE.md).

```bash
# Start with role assignments from backend/config/models.toml (six reasoning roles use Sarvam; company research uses Gemini Search).
# Requires SARVAM_API_KEY in backend/.env; this makes live, billable provider calls.
./dev.sh
```

Stop the current stack before running another command on the same ports. Keep AUTH_DEMO_ENABLED=false
for normal use. Test fixtures live under backend/tests/ and are excluded from the production image.

## 4. Start services separately

Useful for debugging one service or watching separate logs. Run the migration command first.

```bash
# Apply pending database migrations.
(cd backend && uv run alembic upgrade head)
```

**Terminal A — API with code reload:**

```bash
(cd backend && uv run uvicorn app.main:app --reload --host 127.0.0.1 --port 8000)
```

**Terminal B — durable report worker:**

```bash
(cd backend && uv run python -m app.worker)
```

**Terminal C — frontend with code reload:**

```bash
(cd frontend && npm run dev)
```

Restart the worker after backend or environment changes; it does not reload automatically.
Restart the API after `.env` changes. To run an embedded worker for a small local/test setup:

```bash
# Use instead of terminals A and B; do not also start a separate worker for this recipe.
(cd backend && INLINE_WORKER=true uv run uvicorn app.main:app --reload --port 8000)
```

## 5. Use different ports

Keep the browser origin and proxy destination aligned with the chosen ports:

```bash
API_PORT=8100 WEB_PORT=3100 \
FRONTEND_ORIGIN=http://localhost:3100 \
BACKEND_URL=http://127.0.0.1:8100 \
NEXT_DIST_DIR=.next-e2e \
./dev.sh
```

Open **http://localhost:3100**. `NEXT_DIST_DIR` keeps this frontend's generated files separate
from the default build. Use the isolated database recipe below if another stack is already running.

## 6. Backend tests and code checks

```bash
# Run contract tests against automatically created, temporary SQLite databases.
(cd backend && uv run pytest -q)

# Run a focused suite or a single matching test.
(cd backend && uv run pytest tests/test_billing.py -q)
(cd backend && uv run pytest tests/test_providers.py -q)
(cd backend && uv run pytest tests/test_personas.py -q)
(cd backend && uv run pytest tests/test_agent_workflows.py tests/test_company_research.py -q)
(cd backend && uv run pytest -q -k concurrent)

# Check Python style and formatting without changing files.
(cd backend && uv run ruff check .)
(cd backend && uv run ruff format --check .)

# Apply Python formatting when editing code.
(cd backend && uv run ruff format .)
```

Tests inject demo/mocked providers; they do not make paid model calls.

To customize the Recruiter, Hiring Manager, Technical Interviewer or Leadership Interviewer,
edit `backend/app/personas.py` and restart the API and worker using section 4. New interviews use
the updated definition; existing interviews keep their saved profile. See `docs/EXTENDING.md`.

For PostgreSQL contract tests, create a **disposable test database** first. The fixture drops and
recreates application tables; never supply a development database with data you need or production.

```bash
# Point only at a disposable PostgreSQL database that already exists.
export TEST_DATABASE_URL='postgresql+psycopg://test:test@127.0.0.1:5432/studio_test'

# Verify real migration history, schema agreement and all contracts on PostgreSQL.
(cd backend && DATABASE_URL="$TEST_DATABASE_URL" uv run alembic upgrade head)
(cd backend && DATABASE_URL="$TEST_DATABASE_URL" uv run alembic check)
(cd backend && uv run pytest -q)

# Return to the default temporary SQLite test databases.
unset TEST_DATABASE_URL
```

## 7. Frontend checks and production build

```bash
# Static checks.
(cd frontend && npm run lint)
(cd frontend && npm run typecheck)
(cd frontend && npm run format:check)

# Apply formatting when editing frontend code.
(cd frontend && npm run format)

# Verify login availability, service-error recovery and Google redirect when configured.
# Requires the running frontend/API and installed Playwright Chromium; no account login is performed.
(cd frontend && npm run test:login)

# Build production frontend assets with Webpack; no font download is required.
(cd frontend && npm run build)

# Serve the compiled app on port 3000. Stop the dev frontend first.
# The API and worker still need to be running separately.
(cd frontend && npm run start)
```

The proxy's `BACKEND_URL` is embedded at **build time**. To use a different API for a production build:

```bash
(cd frontend && BACKEND_URL=http://127.0.0.1:8100 npm run build)
(cd frontend && npm run start -- --port 3100)
```

The API in that example must use `FRONTEND_ORIGIN=http://localhost:3100`. Do not build into the
same `.next` directory while a default development frontend is using it.

## 8. Browser tests — isolated, no paid calls

The suite creates a resume and interview, then checks reports, practice tasks, settings, billing,
logout and microphone cleanup. Use this recipe to keep test data separate from your normal app.

```bash
# Install Chromium once. On Linux CI, use: npx playwright install --with-deps chromium
(cd frontend && npx playwright install chromium)
```

**Terminal A — isolated demo stack on ports 8100/3100:**

```bash
DATABASE_URL=sqlite:////tmp/interview-studio-browser-tests.db \
AI_DEFAULT_PROFILE=demo AUTH_DEMO_ENABLED=true AUDIO_PROVIDER=browser \
API_PORT=8100 WEB_PORT=3100 \
FRONTEND_ORIGIN=http://localhost:3100 \
BACKEND_URL=http://127.0.0.1:8100 \
NEXT_DIST_DIR=.next-e2e \
./dev.sh
```

**Terminal B — run the tests after the stack is ready:**

```bash
# Check readiness through the same-origin frontend proxy.
curl --fail http://localhost:3100/api/ready

# Run the browser suite against the isolated stack.
(cd frontend && BASE=http://localhost:3100 npm run test:e2e)

# Verify cloud playback, automatic microphone turns, permission retry and audio-error recovery.
# Uses intercepted APIs and a fake microphone; no paid service calls.
(cd frontend && BASE=http://localhost:3100 npm run test:voice)
```

Screenshots go to `frontend/e2e/shots/` and are ignored by Git. Press Ctrl-C in terminal A afterward.
To start with fresh test data, choose a new filename in `/tmp`; no database deletion is required.
Repeated runs consume the test account's quotas. The default `npm run test:e2e` targets port 3000;
use that only when your normal stack is intentionally configured as a test demo.

## 9. Database migrations

All commands below target the `DATABASE_URL` loaded by the backend.

The current updates add `d20a77b9c431` (shared prompt bundles/practice sources) and
`e54c91d703a2` (saved setup artifacts), following `c91f0326ad10`. Stop the API/worker, apply the migration,
then restart both. `dev.sh` applies it automatically. Existing interviews and reports are preserved.

```bash
# Show the currently applied revision and available history.
(cd backend && uv run alembic current)
(cd backend && uv run alembic history)

# Apply all pending migrations.
(cd backend && uv run alembic upgrade head)

# Detect model/schema drift; does not generate or apply changes.
(cd backend && uv run alembic check)

# After changing app/models.py, generate a migration for review.
(cd backend && uv run alembic revision --autogenerate -m 'describe the change')
```

Inspect generated migrations before applying them. Back up persistent data first. On a disposable
database, this command tests a rollback; it can remove columns/data and is not a routine reset:

```bash
(cd backend && uv run alembic downgrade -1)
```

Always restore the intended revision with `alembic upgrade head` before restarting current code.

## 10. PostgreSQL + all services with Docker

Requires Docker Engine/Desktop and Compose v2. This uses a separate PostgreSQL volume, not SQLite.

```bash
# Create environment configuration only if it is missing.
test -f backend/.env || cp backend/.env.example backend/.env

# Build and start database, migration gate, API, worker and frontend.
docker compose up --build -d

# Check service status and follow API/worker/frontend logs.
docker compose ps
docker compose logs --tail=100 -f api worker web

# Apply migrations explicitly during maintenance; normal startup already runs the gate.
docker compose run --rm migrate

# Restart the report worker after deploying its code.
docker compose restart worker

# Stop services. Named PostgreSQL data remains intact.
docker compose down
```

Open **http://localhost:3000**. Stop any non-Docker frontend already using that port.
Use `docker compose up --build -d` after image/code changes. After `.env` changes, recreate services
with `docker compose up -d --force-recreate`; a plain restart does not load changed container env.

## 11. Production deployment

Complete [deployment prerequisites](docs/DEPLOYMENT.md): domain, HTTPS, Google consent/callback,
live model credentials, PostgreSQL backups and operating policies. Docker images still need a
smoke test in your deployment environment.

```bash
# Create root Compose settings without overwriting an existing file.
test -f .env || cp .env.production.example .env

# Set PUBLIC_HOST, PUBLIC_URL, POSTGRES_PASSWORD and SESSION_SECRET; configure TOML [agents].
${EDITOR:-vi} .env

# Generate a random session secret; copy its output into your secret store/root .env.
(cd backend && uv run python -c 'import secrets; print(secrets.token_urlsafe(48))')

# Build and start the HTTPS deployment with production configuration checks.
docker compose -f compose.yaml -f compose.production.yaml up --build -d

# Inspect service status and follow API/worker/edge logs.
docker compose -f compose.yaml -f compose.production.yaml ps
docker compose -f compose.yaml -f compose.production.yaml logs --tail=100 -f api worker edge

# Verify the deployed API through HTTPS; replace YOUR_DOMAIN.
curl --fail https://YOUR_DOMAIN/api/health
curl --fail https://YOUR_DOMAIN/api/ready

# Stop this deployment while preserving named volumes.
docker compose -f compose.yaml -f compose.production.yaml down
```

Keep app/vendor credentials in `backend/.env` or your deployment secret manager. Use a URI-safe
PostgreSQL password (for example, a long random hex value) in this Compose URL recipe. Changing
POSTGRES_PASSWORD in `.env` does not rotate an existing PostgreSQL volume's database password.

## 12. Stripe test-mode billing

Requires a Stripe account, CLI and a recurring Pro test price. Set `STRIPE_SECRET_KEY`,
`STRIPE_PRO_PRICE_ID`, and `STRIPE_TEAM_PRICE_ID` in `backend/.env`.

```bash
# Authenticate the local Stripe CLI.
stripe login

# Forward subscription notifications to your running local API.
stripe listen --events customer.subscription.created,customer.subscription.updated,customer.subscription.deleted \
  --forward-to http://localhost:8000/api/billing/webhook
```

Copy the listener's signing secret into `STRIPE_WEBHOOK_SECRET`, then restart the API. Enable
Customer Portal in Stripe and use **Plans & usage** to exercise a real test-mode checkout.
Synthetic CLI events without a matching application customer do not upgrade an account.
For port 8100, change the forwarding URL accordingly. Live billing uses separate live credentials.

## 13. Health, troubleshooting and quick reference

```bash
# API liveness; database/migration-table readiness; browser auth feature availability.
curl --fail http://localhost:8000/api/health
curl --fail http://localhost:8000/api/ready
curl --fail http://localhost:8000/api/auth/config

# Check the browser-facing proxy as well.
curl --fail http://localhost:3000/api/ready

# Identify occupied ports on macOS/Linux before stopping the relevant terminal/process.
lsof -nP -iTCP:3000 -sTCP:LISTEN
lsof -nP -iTCP:8000 -sTCP:LISTEN

# Inspect changes before sharing them. Actual secrets remain ignored.
git status --short
```

| Symptom | Action |
| --- | --- |
| Port already in use | Stop the previous stack with Ctrl-C or use section 5 |
| Proxy fails / cannot reach API | Start the API; check BACKEND_URL; rebuild if using production assets |
| Table/column missing | Stop services, run `alembic upgrade head`, restart |
| Google redirect mismatch | Register the exact callback and match FRONTEND_ORIGIN |
| Google login returns an error | Check consent-screen test users and restart after credential edits |
| Login has no sign-in options / auth config returns 404 | An older backend may still occupy port 8000. Stop it, then restart the current stack with `./dev.sh`; consent settings cannot fix a missing API route |
| 403 on a mutation | Use the same browser origin; reload to refresh the session/CSRF token |
| 409 after answering | Retry the pending request or reload; do not manually duplicate saved turns |
| Report stays pending | Start/restart `uv run python -m app.worker`; inspect its terminal output |
| Report failed | Check provider credentials/quota in Agent activity, then use the report Retry button |
| 429 quota reached | Check Plans & usage; use a fresh disposable DB for repeated test runs |
| Sarvam/Gemini/OpenAI unavailable | Set its server key and restart API + worker; assign a configured profile in TOML [agents] |
| Microphone answer unavailable | Set AUDIO_PROVIDER=sarvam and SARVAM_API_KEY; restart API and reload. Allow microphone access in browser site settings, then Retry microphone |
| Robotic interviewer voice | Use AUDIO_PROVIDER=sarvam, SARVAM_TTS_MODEL=bulbul:v3, SARVAM_TTS_VOICE=ritu; restart API and refresh. Cloud audio failures show Retry question audio |
| Old sample response in a saved session | Start a new interview with a live profile; saved sessions retain their original model snapshot |

Architecture and extension recipes: [AGENTS.md](AGENTS.md), [docs/EXTENDING.md](docs/EXTENDING.md).
Complete setting descriptions: [docs/CONFIGURATION.md](docs/CONFIGURATION.md).

## Company web research and agent recovery

Company research uses the shared runtime and the seventh role in models.toml.
Set `GEMINI_API_KEY` and `COMPANY_RESEARCH_ENABLED=true` in `backend/.env`, then assign
`company_research = "gemini_search"` in TOML. The Google AI project needs search/model
quota; Google sign-in credentials do not provide that access. No separate search API key is needed.

```bash
# Edit search credentials/model, then restart the API and worker using section 4.
${EDITOR:-vi} backend/.env

# Check company source handling and report recovery without any paid API calls.
(cd backend && uv run pytest tests/test_company_research.py tests/test_agent_workflows.py -q)

# OPTIONAL LIVE CHECK: performs a real, billable Google Search-grounded request.
# Uses configured credentials; prints status and public source links, never API keys.
(cd backend && uv run python -m scripts.check_company_research \
  --company 'Sarvam AI' --role 'Agentic AI Engineer' --url https://www.sarvam.ai)

# Apply the additive checkpoint/search migration before starting updated services.
(cd backend && uv run alembic upgrade head)
(cd backend && uv run alembic check)

# Start the durable worker; required for topic evaluation, report summary and coaching.
(cd backend && uv run python -m app.worker)
```

In **New interview**, enter a company and optionally its official website/job URL. **Research company**
previews sourced facts; generating a JD or starting an interview also resolves research automatically.
Select an interview language to apply it to questions, follow-ups and speech. Research failures are
visible and the supplied JD remains usable. See `docs/COMPANY_RESEARCH.md` for cache and source rules.

Report failures retain completed private stages. Use **Retry report** on the report page to resume.
Quota/configuration errors need their stated operator/account fix first. Do not delete agent_jobs
or checkpoint JSON to retry. Runtime policies are in `backend/app/agents/specs.py`; new sessions save
model, prompt and policy versions. See `docs/AGENT_RUNTIME.md` before changing these contracts.

## Saved setup and local usage allowances

Generated JDs and title suggestions are saved in the database. **Generate** reuses matching inputs;
**Regenerate** makes a new paid version. Use the saved-role selector to restore a previous description.
Company research is retained with citations and its original research date; **Research company** reuses
it and **Refresh research** explicitly performs a new search. There is no daily expiry for successful
research. Reading saved output does not spend another AI action, even after reaching the AI allowance.

Starter has 3 interviews and 150 AI actions per month. The error now distinguishes interview, AI and
per-minute limits. For local development, set these values in backend/.env; production ignores them:

```dotenv
LOCAL_USAGE_OVERRIDES=true
LOCAL_INTERVIEW_LIMIT=100
LOCAL_AI_CALL_LIMIT=5000
```

```bash
# Edit only the local usage values above, then restart API and worker (section 4).
${EDITOR:-vi} backend/.env

# Verify the effective local configuration without printing keys or private account data.
(cd backend && uv run python -c 'from app.config import settings; print(settings.environment, settings.local_usage_overrides, settings.local_interview_limit, settings.local_ai_call_limit)')

# Check persistence, ownership, refresh and exhausted-quota cache behavior without live calls.
(cd backend && uv run pytest tests/test_setup_cache.py -q)
```

The existing Stripe plan and usage counters remain unchanged. App allowances do not change provider
billing or vendor rate limits. **Plans & usage** shows the effective allowance and its local status.

## Agent judgment evaluations

```bash
# Validate the twenty synthetic reference cases offline; makes no model calls.
(cd backend && uv run python -m scripts.run_evaluations)

# Run the full suite against the configured real model. Explicit opt-in: billable calls.
# Results include portable prompt/model snapshots and a Markdown report beside the JSON.
(cd backend && uv run python -m scripts.run_evaluations --live --accept-cost \
  --output evaluations/results/baseline.json)

# Compare a subsequent model/prompt change against your baseline and measure run-to-run variance.
(cd backend && uv run python -m scripts.run_evaluations --live --accept-cost --repeat 3 \
  --baseline evaluations/results/baseline.json --output evaluations/results/candidate.json)

# Target a specific case and use another configured profile without editing product routing.
(cd backend && uv run python -m scripts.run_evaluations --live --accept-cost \
  --profile gemini --case-id technical-idempotency-strong --output evaluations/results/focused.json)

# Replay the saved prompt/profile/policy bundle. Uses current adapter code and rotated credentials.
(cd backend && uv run python -m scripts.run_evaluations --live --accept-cost \
  --bundle evaluations/results/baseline.json --output evaluations/results/replay.json)

# Run workflow, evidence, concurrency and evaluation-tool tests with fixture providers only.
(cd backend && uv run pytest tests/test_quality_contracts.py tests/test_evaluation_suite.py -q)
```

Live evaluation uses a disposable trace database and synthetic answers, never production candidate data.
Expected ranges and rubric weights are provisional until independently reviewed. Follow the review
process in backend/evaluations/README.md; passing fixture tests is not a claim of calibrated judgment.
Results are ignored by Git. Keep the relevant JSON manifests privately when comparing releases.
See docs/ARCHITECTURE_REVIEW.md for the individual review findings and implementation boundaries.

```bash
# Validate the complete-report smoke case offline (no inference).
(cd backend && uv run python -m scripts.check_report)

# OPTIONAL LIVE CHECK: one synthetic answer through real topic scoring, summary, coaching,
# and atomic publication in a disposable database. Never reads your interview history.
(cd backend && uv run python -m scripts.check_report --live --accept-cost)
```

## Candidate/recruiter login and recruiter access

The application runs from `frontend/` on port **3000**. Only candidate/recruiter login uses the
okkra sign-in design; the rest of the app retains its original interface. The original `B2B-app/` on
port **3100** is a standalone prototype, not the real account or recruiting application.

```bash
# From the repository root: apply all migrations, including recruiter profiles and resume consent.
(cd backend && uv run alembic upgrade head)

# Start the real API, durable report worker and okkra frontend.
./dev.sh

# Confirm the integrated app's backend is ready (no sign-in required).
curl --fail http://localhost:3000/api/ready
```

Open these addresses in your browser:

| Address | What to do |
| --- | --- |
| `http://localhost:3000/recruiter/login` | Sign in with Google, enter company/title, browse published candidates |
| `http://localhost:3000/recruiter` | Search candidates by role/headline/location and minimum experience |
| `http://localhost:3000/recruiter/requests` | Read approved resume text and candidate email |
| `http://localhost:3000/opportunities` | Publish your candidate profile, choose a resume, approve/decline/revoke requests |
| `http://localhost:3000/progress` | View your actual saved interview scores and practice progress |

No new Google OAuth client or callback is required. Both login paths use the existing authorized
redirect `http://localhost:3000/api/auth/google/callback` (or your deployed origin). Directory access
is free of AI calls. Candidates are invisible until they publish; a new directory can be empty.
Older resumes need re-uploading to share original extracted text. PDF binaries are not stored.

### Isolated recruiter browser test

This uses ports **8200/3200**, leaving the real app and the port-3100 prototype available. The
browser test uses a real test database and separate candidate/recruiter identities. It does not
send email, complete Google OAuth or use paid models.

```bash
# Terminal A, repository root: start an isolated database, API, worker and frontend.
DATABASE_URL=sqlite:////tmp/suri-browser-tests-local.db \
AI_DEFAULT_PROFILE=demo AUTH_DEMO_ENABLED=true AUDIO_PROVIDER=browser \
LOCAL_USAGE_OVERRIDES=false \
API_PORT=8200 WEB_PORT=3200 FRONTEND_ORIGIN=http://localhost:3200 \
BACKEND_URL=http://127.0.0.1:8200 NEXT_DIST_DIR=.next-suri-e2e \
./dev.sh

# Terminal B, repository root: ensure the isolated API is ready.
curl --fail http://localhost:3200/api/ready

# Test publication, directory search, request/approval/revocation, privacy and mobile layouts.
# This path MUST match Terminal A; the test identity helper only accepts this /tmp filename prefix.
(cd frontend && BASE=http://localhost:3200 \
  RECRUITER_E2E_DATABASE_URL=sqlite:////tmp/suri-browser-tests-local.db npm run test:recruiter)

# Run existing candidate and voice regressions on the same isolated stack.
(cd frontend && BASE=http://localhost:3200 npm run test:e2e)
(cd frontend && BASE=http://localhost:3200 npm run test:voice)

# Backend authorization, consent concurrency and progress contracts (no paid APIs).
(cd backend && uv run pytest tests/test_discovery.py tests/test_progress.py -q)
```

Press Ctrl-C in Terminal A to stop the isolated stack. Browser captures are ignored files under
`frontend/e2e/shots/recruiter/`. Test identities expire after one hour. Choose another filename with
the same `/tmp/suri-browser-tests-` prefix for a fresh isolated run. See `docs/SURI_INTEGRATION.md`
for the supported feature map and extension boundaries.
