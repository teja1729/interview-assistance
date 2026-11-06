# Migrations

Alembic owns the schema. The application never calls `create_all`; `backend/tests/conftest.py` uses
it only for isolated, disposable test databases.

- `env.py` reads `DATABASE_URL` through `app.config`, so both SQLite and PostgreSQL share one history.
- Each revision must be self-contained. Never import current application models into migration history.
- Use additive migrations for rolling deployments; split backfills and constraint tightening into
  separate deployments when needed.
- PostgreSQL is production. SQLite is a development/test convenience, and CI applies the full history
  against PostgreSQL 16.
- Application code must tolerate the previous revision while a rolling deployment is in progress.

```bash
cd backend
uv run alembic current
uv run alembic upgrade head
uv run alembic check          # model/schema drift; does not write
uv run alembic revision --autogenerate -m 'describe the change'
```

Review the generated `upgrade` and `downgrade`, indexes, foreign keys and backfill semantics before
committing. Document ownership, retention or compatibility changes in `docs/DATABASE.md`.
