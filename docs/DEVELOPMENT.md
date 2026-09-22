# Development and verification

## First run

1. Install Python 3.12+, uv, Node.js 22+.
2. Copy `backend/.env.example` to `backend/.env` if missing. Configure Google OAuth and a live model key.
3. Run `./dev.sh` from the repository root. It installs locked dependencies, migrates, then starts
   API :8000, worker, and Next.js :3000. Stop with Ctrl-C.
4. Sign in with Google. For synthetic automated tests, use RUN.md's separate database/port recipe.

Separate processes:

```bash
cd backend
uv sync --locked
uv run alembic upgrade head
uv run uvicorn app.main:app --reload --port 8000
# another terminal, same directory
uv run python -m app.worker
# another terminal
cd frontend
npm ci
npm run dev
```

`INLINE_WORKER=true` runs a worker task inside the API for E2E tests. Use the separate worker in
normal development and production. Never run tests against your production DATABASE_URL.

## Quality gates

```bash
cd backend
uv run ruff check .
uv run ruff format --check .
uv run pytest -q
uv run alembic check
cd ../frontend
npm run lint
npm run typecheck
npm run format:check
npm run build
npm run test:e2e
```

Backend tests inject isolated databases and authenticated identities. They test tenant isolation,
CSRF/origin checks, OIDC subject mapping, follow-up limits, preserved transcripts, duplicate and
concurrent answers, report failure/recovery, quotas, invitations, Stripe signature verification and
concurrent billing snapshots. Sarvam adapter tests cover structured output, refusal, invalid data,
authentication errors, timeouts and bounded runtime retries without using live credentials.
`TEST_DATABASE_URL` optionally runs the suite against a **disposable PostgreSQL database**; the
fixture drops/recreates application tables. CI does this automatically.

The browser suite uses the running demo API and worker, creates its own session/resume, and checks
setup → interview → report → practice plan → settings/activity/billing → logout. It requires no
paid provider or existing resume. Browser artifacts are ignored by Git.
`npm run test:login` checks the running login page, auth-discovery failure/retry, callback errors
and the Google authorization redirect when credentials are configured. It does not complete Google
consent or create an account. Set `BASE` to test a frontend on a different port.

## Debugging

- `/api/health`: process liveness. `/api/ready`: DB connectivity and migration table presence.
- `/api/docs`: development OpenAPI UI. `/api/openapi.json`: machine-readable schema.
- Response `X-Request-ID` correlates with API logs. Agent activity records provider, model, prompt
  hash, duration, usage and sanitized error class.
- Stuck report: inspect `agent_jobs`. Check the worker is running and model credentials/quotas.
  Expired running leases are recovered automatically. Three failed attempts require explicit retry.
- 409 on a turn: a stale version or concurrent request was rejected. Retry the **same** request ID
  after an uncertain network response; otherwise reload the authoritative state.
- 403 on mutations: check same-origin proxy, FRONTEND_ORIGIN and session CSRF token.
- `/api/auth/config` returns 404: check for a stale prototype backend still bound to the API port.
  Stop that process and restart the current app; Google consent settings do not control route availability.
- No voice input: configure AUDIO_PROVIDER=sarvam and SARVAM_API_KEY, restart the API, then allow
  browser microphone permission. `npm run test:voice` verifies automatic turns without paid calls.

The production build uses Webpack to support environments where Turbopack cannot start its CSS
worker. Fonts use a system stack; building does not fetch Google Fonts.

## Formatting

Python: `uv run ruff format .`. TypeScript/CSS: `npm run format`. Keep generated migration history
readable. Handwritten docs explain behavior; test names explain invariants, not implementation trivia.
