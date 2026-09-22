# Database and migration guide

Production uses PostgreSQL 16+ through psycopg and SQLModel/SQLAlchemy. Development defaults to a
new SQLite `saas.db`; the prototype database is not modified or assigned to a new user.

| Table | Ownership / purpose |
| --- | --- |
| users | Google subject identity and display profile |
| workspaces | Internal personal account container, plan and Stripe references; legacy ai_profiles ignored |
| memberships | Internal account ownership link; legacy shared memberships retained |
| login_sessions | Hashed opaque token, active workspace, expiry, CSRF secret |
| invitations | Legacy records retained; no active invitation endpoints |
| resumes | Candidate-owned AI digest and private extracted text; original PDF binary is not retained |
| interviews | Workspace + candidate, lifecycle/version/lease, resume and profile snapshots |
| turns | Ordered normalized questions/answers, topic and private assessment |
| operations | Unique interview/request ID, content fingerprint, stored successful response |
| agent_runs | Tenant-scoped execution metadata (no prompt/answer content) |
| agent_jobs | One durable report job per interview, retry/lease state and private checkpoint artifacts |
| company_research | Candidate-owned source cache, normalized query key, snapshot JSON and expiry |
| practice_tasks | Candidate-owned exercises produced by the coach |
| usage_buckets | Compound workspace/period/resource counter, atomic bounded increment |
| audit_events | Historical administrative actor/action metadata |
| billing_events | Processed Stripe event IDs for replay protection |

The product uses personal accounts. Historical table/column names remain to preserve existing
data and Stripe references; removing workspace UI and APIs needs no destructive schema migration.
New model routing comes from TOML `[agents]`, while `interviews.ai_profiles` remains the immutable
snapshot for that session. Legacy `workspaces.ai_profiles` never controls new inference.

Interviewer definitions are snapshotted in the existing `interviews.plan` JSON under `_persona`.
This includes server-only instructions; serializers expose only the public `persona_profile`.
Existing rows without a snapshot resolve their legacy ID through `app/personas.py` without a
backfill. Adding this JSON metadata and changing the Python persona default require no DDL change.

## Change the schema

```bash
cd backend
uv run alembic revision --autogenerate -m 'describe the schema change'
# Inspect upgrade/downgrade, indexes, foreign keys and data backfill semantics.
uv run alembic upgrade head
uv run alembic check
uv run pytest -q
```

Never import current application models into a historical migration. The initial migration is
frozen DDL; subsequent revisions must be similarly self-contained. CI tests PostgreSQL as well
as local SQLite contracts. Use additive migrations for rolling deployment; backfill and tighten
constraints in separate deployments when needed.

## Concurrency

There are unique constraints for membership, turn position, idempotency key and report job.
Usage increments use conditional SQL UPDATE rather than read/increment/save. SQLite config enables
foreign keys, WAL and busy timeout; PostgreSQL is required by production settings.

Turn leases expire after 150 seconds. Commit uses the same lease token and version, fencing a
late process. Worker leases expire after 240 seconds and use the same fencing principle.
Never extend a model's retry budget without revisiting lease duration.

Billing reconciliation uses `workspaces.billing_version` to fence concurrent Stripe snapshots.
The subscription list is fetched outside the write transaction. A version conflict requires a new
fetch, and entitlement changes commit with the processed event ID in one transaction.

## Retention and recovery

Resume deletion removes the reusable digest. Existing interviews retain the historical snapshot
used for their questions, which is stated in the delete confirmation. Interview transcripts are
retained until the operator applies the documented retention policy. Production operators must
set a retention schedule appropriate to their offering and provide data export/deletion handling.

Take PostgreSQL backups, encrypt them, and test restores to a separate database. Back up before
migrations. `docs/DEPLOYMENT.md` includes the deployment gate. Automated retention and full account
self-deletion are not implemented; do not imply otherwise in a privacy policy.

## Agent workflow migration

Revision `c91f0326ad10` adds job artifacts, execution correlation fields on agent_runs and company_research.
Apply migrations before starting the updated API/worker. The additive defaults preserve existing rows.
New interview plans retain private `_brief` and `_execution` JSON alongside `_persona`; no credentials
are stored. Report checkpoints retain the frozen input hash and validated stage outputs. Include these
private artifacts in the same export/retention/deletion policy as their parent interview. Company cache
expiry controls reuse; an operator retention task is still needed to physically purge expired rows.

## Candidate discovery migration

`f781c42d930a` follows `e54c91d703a2` and adds:

- `recruiter_profiles`: unique Google user, self-reported company/title.
- `candidate_profiles`: unique candidate, internal account, explicitly published fields, private
  selected resume reference, discoverable=false by default and mutation serialization counter.
- `resume_access_requests`: unique candidate/recruiter pair, pinned resume reference, recruiter
  identity snapshot and pending/approved/denied/revoked state.
- `resumes.extracted_text`: nullable original extracted text. Old records remain NULL; no fabricated
  text backfill. Original PDF binaries are not retained.

Resume references in discovery are historical string IDs. The deletion service revokes linked
requests and withdraws publication before removing the resume, in one transaction. Sharing also
rechecks resume existence/ownership, visibility and active membership. See `SURI_INTEGRATION.md`.
