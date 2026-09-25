# okkra

A multi-user interview-preparation SaaS: Google sign-in, personal accounts, personalized voice-to-voice
interviews, evidence-based reports, practice plans, usage limits, and optional Stripe billing.
Next.js + FastAPI + PostgreSQL, with explicit agent workflows and interchangeable AI providers.

The okkra sign-in design is used only for candidate and recruiter login. The signed-in application retains
its original sidebar and teal theme. Recruiters sign in at `/recruiter/login` to browse
candidate-published profiles and request resume access. Candidates manage publication and consent at
`/opportunities`. See [the integration and feature map](docs/SURI_INTEGRATION.md).

**For coding agents: start with [AGENTS.md](AGENTS.md), then [the architecture](docs/ARCHITECTURE.md).**

**For copyable commands: [RUN.md](RUN.md) covers startup, tests, migrations, providers and deployment.**

## Run locally

Requires Python 3.12+, [uv](https://docs.astral.sh/uv/), and Node.js 22+.

```bash
cp backend/.env.example backend/.env   # skip if you already have one; do not overwrite secrets
./dev.sh
```

Configure Google OAuth and a live AI key in `backend/.env`, then open http://localhost:3000 and
sign in with Google. Normal operation uses Sarvam. Change each role in the `[agents]` section of
`backend/config/models.toml`; model routing is managed in code, with no provider settings in the UI.
Demo authentication and canned responses are disabled. Provider failures surface as errors.
The default development database is `backend/data/saas.db`. The old prototype's `interviews.db`
is left untouched. `dev.sh` runs migrations, the API, a durable report worker, and the web app.

For a PostgreSQL stack instead:

```bash
docker compose up --build
```

To use real Google accounts or AI, follow [configuration](docs/CONFIGURATION.md).

## What is implemented

- Public landing and plans pages; Google OIDC sign-up/sign-in; revocable HTTP-only sessions and CSRF protection.
- Personal account settings and private interview history; no workspaces, invitations or team controls.
- Private PDF/text resume library. New uploads retain extracted text for approved sharing; PDF binaries are discarded.
- Recruiter Google sign-in, company profiles, candidate search and candidate-approved resume/email access.
- Interview planning, natural Sarvam cloud voice, automatic microphone turns with optional typed fallback, countdown starting at join,
  bounded follow-ups, versioned/idempotent submissions and report recovery after reload.
- Planner, interviewer, evaluator, coach, resume analyst and setup assistant with strict output contracts.
- Google Gemini, OpenAI Responses, Sarvam 105B, and OpenAI-compatible provider adapters; per-agent routing in backend configuration.
- Persistent report jobs with retries, lease recovery and atomic report/practice-task writes.
- Feedback tied to exact answer quotes; server-computed practice scores; actionable practice tasks and progress.
- Monthly account quotas, shared database rate limits, Stripe Checkout/portal and verified idempotent webhooks.
- Agent activity metadata, request IDs, migration history, container definitions, CI and deterministic contract tests.

## Documentation map

| Need | Start here |
| --- | --- |
| Product idea, code assessment and validation priorities | [Product review](docs/PRODUCT_REVIEW.md) |
| Understand boundaries and data flow | [Architecture](docs/ARCHITECTURE.md) |
| okkra sign-in, recruiter consent and remaining prototype features | [Sign-in and discovery](docs/SURI_INTEGRATION.md) |
| Set up, test and debug | [Development](docs/DEVELOPMENT.md) |
| Google, models, audio and Stripe | [Configuration](docs/CONFIGURATION.md) |
| Natural voice, automatic microphone turns and speech troubleshooting | [Voice interviews](docs/VOICE.md) |
| Agent decisions, prompts and recovery | [Agent workflows](docs/AGENT_WORKFLOWS.md) |
| Add an agent/provider/field/endpoint | [Extension recipes](docs/EXTENDING.md) |
| Add a model vendor | [Provider guide](docs/ADDING_A_PROVIDER.md) |
| Database, ownership and migrations | [Database](docs/DATABASE.md) |
| Endpoint and error contracts | [API](docs/API.md) |
| Deploy and operate | [Deployment](docs/DEPLOYMENT.md) |
| Security boundaries and known limits | [Security](docs/SECURITY.md) |

## Checks

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
npm run test:e2e  # use RUN.md's isolated test stack, not the live app
```

Production deployment needs your Google OAuth credentials, a real model profile, PostgreSQL,
HTTPS, and Stripe credentials if you offer paid plans. These external accounts are not created
by this repository. Real-provider accuracy, latency and pricing require evaluation for your target roles.
