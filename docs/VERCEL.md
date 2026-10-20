# Vercel Services deployment

The repository root `vercel.json` defines two Vercel Services: `backend` (FastAPI) and
`frontend` (Next.js). Public requests under `/api/` are routed to FastAPI; all other paths go to
Next.js. Vercel preserves the original path, so the backend receives `/api/...` and keeps its
existing API routes. Vercel Services is currently a beta feature; confirm it is enabled for the
Vercel account before importing this project.

## Required external services

The FastAPI service needs PostgreSQL and application credentials through environment variables.
Set `DATABASE_URL`, `APP_ENV=production`, `AUTH_DEMO_ENABLED=false`, a random `SESSION_SECRET`,
`FRONTEND_ORIGIN`, Google OAuth credentials, and provider keys required by
`backend/config/models.toml`. `DATABASE_URL` may use a provider's `postgres://` or
`postgresql://` scheme; the backend selects its installed psycopg 3 driver automatically. Apply Alembic migrations to the target database before deploying
backend code that expects the new schema. Keep preview and production databases separate.

Report jobs are stored durably in PostgreSQL, then dispatched to Vercel Queues from the interview
finish endpoint. The Python subscriber in `backend/app/queue_subscribers.py` claims the same
fenced database lease used by the existing worker, writes checkpoints, and publishes the report
and practice tasks atomically. No separate worker service or extra queue secret is needed in a
Vercel deployment; the Vercel Queue SDK uses the deployment's OIDC identity. Keep
`INLINE_WORKER=false` on Vercel. Enable Vercel Queues for the project if the dashboard requests it.

The report page re-dispatches an interview that is already `finishing` once when opened. This
recovers jobs created before queue dispatch was deployed. Queue delivery is at least once, so the
database lease and job status remain the source of truth. Locally, the existing
`backend/app/worker.py` polling command remains available for development.

## Routing and bindings

The browser already calls `/api/...` on its own origin. Vercel's top-level rewrite sends those
requests directly to `backend`; there is no server-side frontend-to-backend request that needs a
binding. The `frontend` service's existing Next.js rewrite is disabled on Vercel and retained for
local development. No service bindings are configured because neither Vercel service calls the
other privately. Adding a binding would not be useful for browser requests, which enter through
the public routing table.

For local development, the existing `BACKEND_URL` variable still controls the Next.js `/api`
rewrite. On Vercel, set the backend's `FRONTEND_ORIGIN` to the deployment's HTTPS domain; Vercel's
service routing keeps browser requests same-origin for cookies and CSRF checks.

Google OAuth must include `https://YOUR_DOMAIN/api/auth/google/callback` as an authorized redirect
URI. Add Stripe webhook URLs and any other external callback URLs using the same public domain.

See [Vercel Services documentation](https://vercel.com/docs/services) and the
[configuration reference](https://vercel.com/docs/services/config-reference), plus
[Vercel Queues](https://vercel.com/docs/queues) and the
[Python SDK deployment instructions](https://vercel.com/docs/queues/python-sdk).
