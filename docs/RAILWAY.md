# Railway deployment

Railway runs this application as four services: PostgreSQL, API, report worker, and Next.js web.
The web service is the only public app service; it proxies `/api/*` to the private API service.
Keep the API and worker on the same release and database. Do not use SQLite or enable
`INLINE_WORKER` in production.

## Create the services

Create a Railway project from this repository and add a PostgreSQL service. Add three services
from the same repository, each with its own root directory and Dockerfile:

| Service | Root directory | Dockerfile | Start command |
| --- | --- | --- | --- |
| `api` | `/backend` | `Dockerfile` | `/bin/sh -c 'exec uvicorn app.main:app --host 0.0.0.0 --port ${PORT:-8000}'` |
| `worker` | `/backend` | `Dockerfile` | `python -m app.worker` |
| `web` | `/frontend` | `Dockerfile` | Leave the Dockerfile command (`node server.js`) |

For API, set the pre-deploy command to `alembic upgrade head`; this applies migrations before
each new API deployment. Give
the API a healthcheck path of `/api/ready` if you enable Railway healthchecks. The worker should
not have a public domain or HTTP healthcheck. Generate a public domain for `web` only.

Railway root directories are isolated during build. The Dockerfiles already copy the required
files within their respective roots. Set the web service build variable `BACKEND_URL` to
`http://api.railway.internal:8000`; Next.js uses it when building its `/api` rewrite, so rebuild
the web service if the API service name or private address changes.

## Variables

Set these on both `api` and `worker` (Railway can share a variable group). Replace `Postgres` in
the reference expressions with the database service's exact Railway name:

```dotenv
APP_ENV=production
AUTH_DEMO_ENABLED=false
INLINE_WORKER=false
DATABASE_URL=postgresql+psycopg://${{Postgres.PGUSER}}:${{Postgres.PGPASSWORD}}@${{Postgres.PGHOST}}:${{Postgres.PGPORT}}/${{Postgres.PGDATABASE}}
FRONTEND_ORIGIN=https://YOUR-WEB-DOMAIN
SESSION_SECRET=<random value of at least 32 characters>
AI_DEFAULT_PROFILE=gemini
GOOGLE_CLIENT_ID=<Google OAuth web client ID>
GOOGLE_CLIENT_SECRET=<Google OAuth web client secret>
GEMINI_API_KEY=<model key, if using Gemini>
```

`DATABASE_URL` deliberately uses Railway's private Postgres host and the installed `psycopg`
driver. Configure any other provider, speech, research, or Stripe variables needed by your
selected roles; keep `backend/config/models.toml` assignments consistent with those credentials.
Use Railway's secret variable editor for credentials. Do not set `LOCAL_USAGE_OVERRIDES=true`.

On `web`, set:

```dotenv
BACKEND_URL=http://api.railway.internal:8000
```

The Railway web domain is assigned in Settings → Networking. Put its final HTTPS origin in
`FRONTEND_ORIGIN`, then register these exact URLs with Google OAuth:

```text
https://YOUR-WEB-DOMAIN/api/auth/google/callback
https://YOUR-WEB-DOMAIN/api/auth/linkedin/callback
```

Only configure the LinkedIn callback if LinkedIn login is enabled. The frontend service listens
on Railway's injected `PORT` (the Dockerfile sets `PORT=3000` by default; confirm Railway's port
setting is `3000` if needed). The API start command binds the injected `PORT`; its internal
upstream remains port 8000, so set the API service's `PORT=8000` explicitly for this topology.

## Deploy and verify

Deploy Postgres first. Set variables, then deploy API and worker; the API pre-deploy migration
must succeed before serving traffic. Deploy web after the API is available. Visit
`https://YOUR-WEB-DOMAIN/api/ready` and `/api/auth/config`, then sign in and verify a report
completes. A pending report usually means the worker is stopped or cannot reach Postgres/model
credentials. Check Railway deployment logs for each service.

Enable Postgres backups and set an operator data-retention/support process before inviting
users. Railway deploys the checked-in Dockerfiles; redeploy all three app services when shared
backend code or `backend/config/models.toml` changes. The frontend proxy destination is baked into
the Next.js build.
