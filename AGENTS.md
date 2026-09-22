# Interview Studio: coding-agent entry point

Read `docs/ARCHITECTURE.md` before changing boundaries. Read the nearest module README before
editing its internals. `docs/DEVELOPMENT.md` has exact setup and verification commands.
`RUN.md` is the operator command reference; update it when commands, ports or setup requirements change.

## Repository map
- `backend/app/api/`: authentication and HTTP adapters. Keep domain rules out of routes.
- `backend/app/services/`: tenant-aware business rules, interview state machine, quotas, durable reports.
- `backend/app/agents/`: bounded orchestration and versioned prompts; outputs are Pydantic contracts.
- `backend/app/agents/specs.py` / `context.py`: immutable execution bundles and shared interview briefs.
- `backend/app/services/company_research.py`: bounded web search, source attribution and private caches.
- `backend/app/providers/`: vendor SDK adapters only. `backend/config/models.toml` selects models.
- `backend/app/models.py`: relational persistence. `schemas.py`: API/agent validation contracts.
- `backend/migrations/`: Alembic history. Never replace migrations with `create_all` at startup.
- `frontend/src/lib/api.ts`: browser API boundary (credentials, CSRF, typed contracts).
- `frontend/src/components/`: application shell and shared presentation.
- `frontend/src/features/interview/`: session/device orchestration and reusable call controls.
- `docs/`: architecture, workflows, extension recipes, operations and deployment.

## Invariants
1. Every private read/write checks the session and internal account membership. All candidate
   resources, interviews and traces also check creator ownership. Never authorize by opaque ID alone.
   Workspace/team management is retired; existing tables are retained for data compatibility.
   Explicit candidate consent in services/discovery.py permits only the selected resume text and email
   to the approved recruiter. Directory publication never grants interview or trace access.
   Model routing belongs only in backend/config/models.toml, never in user settings.
2. Never expose API keys, Google subjects, session tokens or provider exception bodies to the browser.
3. Agents propose; services enforce. A prompt is not authorization or a state machine.
4. Validate model output before persistence. Keep candidate transcripts verbatim.
5. Use version checks, idempotency keys and fenced leases for interview writes. Never hold a DB
   write transaction across a model call. Reports and practice tasks commit atomically.
6. Schema changes require a migration and contract tests. Use PostgreSQL in production; SQLite is
   a development/test convenience. Never assign legacy private records to new users automatically.
7. Do not call paid model APIs in routine tests. Use the deterministic provider and injected fixtures.
8. Keep docs current when routes, env variables, prompts, defaults or operational behavior change.
9. Google/Stripe credentials require operator setup; do not fake a successful external integration.

## Definition of done
Run backend `ruff check`, `pytest`, migration checks; frontend `npm run lint`, `npm run typecheck`,
`npm run build`. For user-facing flows run `npm run test:e2e` with the demo API and worker.
For speech/device changes also run `npm run test:voice`; its APIs and microphone are isolated fixtures.
Add tests for authorization, persistence, concurrency or agent behavior when those contracts change.
Document meaningful assumptions and external prerequisites. Use the recipes in `docs/EXTENDING.md`.
