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
`backend/config/models.toml`. Apply Alembic migrations to the target database before deploying
backend code that expects the new schema. Keep preview and production databases separate.

The durable report worker in `backend/app/worker.py` is a persistent polling process. It claims
database jobs and loops until it receives a shutdown signal; it cannot be deployed as a normal
Vercel request service without redesigning job dispatch. Run it as a separate long-lived service
(for example on Railway) with the same `DATABASE_URL`, `APP_ENV`, `SESSION_SECRET`, OAuth settings,
and provider configuration as the backend. Keep `INLINE_WORKER=false` on Vercel. The worker and
backend communicate through the PostgreSQL job table, not HTTP, so there is no Vercel service
binding between them.

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
[configuration reference](https://vercel.com/docs/services/config-reference).
