# Application core

Read `docs/ARCHITECTURE.md` before moving responsibilities, then the README in the subpackage you
are editing: `api/`, `services/`, `agents/` or `providers/`.

| File | Owns |
| --- | --- |
| `main.py` | Composition only: middleware, origin/size checks, router registration, inline worker, safe `ProviderError` handler |
| `auth.py` | Opaque database sessions, CSRF, `Context` / `current_context`, `require_owner` |
| `config.py` | Environment settings and production startup validation |
| `db.py` | Engine construction and the session dependency; no DDL |
| `models.py` | SQLModel tables, indexes and uniqueness constraints |
| `schemas.py` | Strict API and agent Pydantic contracts |
| `personas.py` | Operator-owned interviewer roles and provisional rubrics |
| `llm.py` | Compatibility shim only; new code imports `agents.runtime.execute` |
| `worker.py` | Polls PostgreSQL for durable report jobs and processes them with fenced leases |

Rules:

- Keep domain rules out of `main.py` and `api/`; services own transitions and authorization checks.
- Every private route starts from `current_context`. Check account membership and, for candidate
  resources, creator ownership. Never authorize by opaque ID alone.
- Schema changes are Alembic revisions in `backend/migrations/`; never call `create_all` at startup.
- Model routing lives only in `backend/config/models.toml`; never in user settings or requests.
- Never expose API keys, Google/LinkedIn subjects, session tokens or provider exception bodies.
- Validate model output before persistence and keep candidate transcripts verbatim.

Verification: `uv run ruff check . && uv run ruff format --check . && uv run pytest -q && uv run alembic check`.
