# Deployment and operations

## Topology

Caddy terminates HTTPS and routes /api to FastAPI and everything else to Next.js. PostgreSQL
and the worker are private services. API and worker use the same database and model configuration.
A one-shot migration service must complete before API and worker start.

## Local container smoke test

```bash
cp backend/.env.example backend/.env  # only if missing
docker compose up --build
```

Open http://localhost:3000. This uses PostgreSQL, not the local SQLite file. Docker is optional
for local development; `dev.sh` runs the same services without containers.

## Production preparation

1. Provision a host with Docker Compose and a domain pointing to it, or adapt the Dockerfiles to
   your managed platform. Prefer managed PostgreSQL with automated backups for a hosted service.
2. Populate backend/.env with Google client credentials, actual model keys, optional Stripe keys,
   and matching audio configuration. Never commit this file.
3. Copy `.env.production.example` to root `.env`; set PUBLIC_HOST, HTTPS PUBLIC_URL, a strong
   POSTGRES_PASSWORD and random SESSION_SECRET. Configure live role assignments in TOML `[agents]`; AI_DEFAULT_PROFILE fills omitted roles.
4. Register the HTTPS Google callback and Stripe webhook URLs from CONFIGURATION.md.
5. Build and start:

```bash
docker compose -f compose.yaml -f compose.production.yaml up --build -d
```

6. Check `/api/health` and `/api/ready`, Google sign-in, personal account isolation, a real-provider interview,
   report completion, and a Stripe test subscription before switching billing to live mode.
7. Define the data-retention and user-support process in SECURITY.md before public onboarding.

Caddy obtains/renews TLS automatically. The web container's direct port binds loopback only;
PostgreSQL and API ports are not published. Production startup refuses demo login/provider,
weak session secrets, non-HTTPS origin, missing Google credentials and non-PostgreSQL DB URLs.

## Release sequence

Back up → migrate → deploy API/worker/web → verify readiness → run smoke checks. For a rolling
release, use additive compatible migrations first. Do not downgrade schema against newer workers.
Backend dependencies use uv.lock; frontend dependencies use package-lock.json. Images use fixed
major runtime lines and a pinned uv tool version; pin digests in your release pipeline if required.

## Recovery and monitoring

- Report stuck pending: check worker health, DB connectivity and available_at. Restart worker safely.
- Worker crashed mid-report: expired leases are recovered automatically. A late worker is fenced.
- Report failed: inspect sanitized AgentRun metadata, fix provider/quota/config issue, retry from report UI.
- Lost turn response: same request ID safely retrieves the saved result; don't manually append a turn.
- Provider migration: add a new profile ID, test it, then update TOML `[agents]` routing. Keep old
  definitions until their sessions are complete. Provider logs record actual model/prompt versions.
- Monitor request errors/latency, pending job age, failed agent rates, DB capacity and vendor spend.
- Restore backups to a separate instance and validate table counts, session policy and tenant access
  before pointing production at a restored database. Rotate secrets if exposure is suspected.

## Scale boundary

Multiple API and worker processes are supported by DB leases and conditional updates. The initial
worker handles one job at a time per process; add worker replicas to increase report throughput.
The runtime is intentionally bounded, without autonomous tool execution. Before high-volume public
traffic add platform-level rate controls, observability alerts, constrained document extraction and
measured capacity targets. Container build and live credentials must be verified in your deployment environment.
