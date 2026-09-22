# Extension recipes for coding agents

Use the smallest module boundary that owns the behavior. Read the root AGENTS.md and the relevant
module README, implement a vertical slice, then run the listed contracts. Do not add abstractions
that only rename the existing service layer.

## Add a model/provider

See `ADDING_A_PROVIDER.md`. For an existing vendor, usually only add a profile to models.toml and
an environment credential, then assign its ID to the relevant role in TOML `[agents]`. Model
configuration is operator-owned and has no settings screen or browser mutation endpoint.

## Add an agent

1. Define a strict Pydantic output in `backend/app/schemas.py`. Set bounds and disallow extra fields.
2. Write one role prompt in `agents/prompts/<role>.md`. Explicitly treat supplied user text as data.
3. Register the role in `providers/base.py` (`AGENT_ROLES`) and add a deterministic fixture to tests/fixtures/demo_provider.py.
4. Invoke it from a domain service with workspace/user scope and a bounded input snapshot.
5. Validate semantic invariants (e.g., exact evidence quotes) after structural validation.
6. Assign its default profile in TOML `[agents]`. Preserve interview snapshots for later jobs.
7. Write tests for malformed output, retries, tenant scope and duplicate delivery. Update the
   handoff table in AGENT_WORKFLOWS.md. No model is allowed to directly commit business state.

## Add an endpoint or product feature

1. Keep candidate data private to its owning user. Internal account containers are not shared product workspaces.
2. Define input schema. Use current_context; use require_owner for administrative operations.
3. Put behavior in services, HTTP adaptation in api. Query by tenant and owner, not just ID.
4. Use the existing API client for cookies/CSRF. Add typed response contracts there.
5. Add a route/page, loading/error/empty states, keyboard labels and the relevant navigation link.
6. Test cross-tenant access and the user-visible happy/recovery path. Update API.md.

## Add a database field

1. Edit models.py; consider nullability/backfill/default semantics for existing records.
2. Run `uv run alembic revision --autogenerate -m '...'` from backend.
3. Review the generated migration. Do not import current models into migration history.
4. Apply against disposable SQLite and PostgreSQL; run `alembic check` and contract tests.
5. Update schemas.py, serialization helpers and frontend types if the field is public.
6. Document its ownership and retention in DATABASE.md.

## Modify interview policy

The state machine is `services/interviews.py`. The prompt can propose a follow-up; only this
service chooses whether it is allowed. Preserve version checks, idempotency and fenced leases.
Changing inference timeouts also requires reviewing lease duration. Modify the tests that assert
follow-up caps, timeout closure, duplicate response replay, and concurrent write rejection.

Role budgets and immutable execution bundles now live in `agents/specs.py`; shared session fields and
context selection live in `agents/context.py`. See AGENT_RUNTIME.md before modifying contracts.
Report stages checkpoint privately in `AgentJob.artifacts`. Preserve lease fencing at every checkpoint
and the final atomic report/task commit; a coach failure must not repeat completed evaluation.

## Extend company research

The trusted search boundary is `services/company_research.py`, separate from the live interviewer.
Keep resume/answer data out of search queries. CompanyBrief facts must refer to actual grounding
source IDs; never accept model-written URLs without provider source metadata. Cache and research IDs
must remain candidate-scoped. Render citations through CompanyContext.tsx and isolate Search Suggestions
HTML in a script-free iframe. See COMPANY_RESEARCH.md and its mocked transport/ownership tests.

## Customize interviewer personas

1. Edit `backend/app/personas.py`: public card metadata and private behavioral instructions live
   together. For a new role, also extend `PersonaId` in that file. Keep historical aliases readable.
2. Reuse existing names from `frontend/src/components/Icon.tsx`, or add an icon there. Setup, the
   lobby, the call and reports consume server metadata; do not add another frontend persona map.
3. Preserve the private plan snapshot and `public_persona` filtering. Never accept arbitrary persona
   instructions from the browser. Existing snapshots keep their original definition.
4. For changes to shared behavior, edit planner.md, interviewer.md or evaluator.md. Spoken question
   length and role-specific tone are prompt guidance; validate live quality separately from fixtures.
5. Run `pytest tests/test_personas.py -q` from backend and the browser E2E flow. Restart the API and
   report worker to load code changes; normal API development reloads Python files automatically.

## Modify billing

Plans/limits live in services/usage.py. Payment routes and signature verification live in
api/billing.py; versioned subscription reconciliation lives in services/billing.py.
Never derive entitlements from browser query parameters or unchecked webhook JSON.
Keep signature verification, unique event IDs, server-owned price mapping and out-of-order tests.
Change public pricing copy and plan contracts alongside backend policy.

## Quality of handoff

In your final change note, list what behavior changed, which checks ran, and which external
integrations remain unverified. Keep credentials out of examples. Include a migration/runbook
step whenever operators need to do something beyond deploying code.
