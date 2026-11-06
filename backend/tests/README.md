# Backend contracts

Tests are the executable specification for tenancy, state transitions, concurrency, quotas and agent
handoffs. They never call paid model APIs.

- `conftest.py` forces `AI_DEFAULT_PROFILE=demo`, `AUTH_DEMO_ENABLED=true` and an isolated database.
  `clients(...)` creates authenticated, CSRF-enabled clients for one user/account.
- `TEST_DATABASE_URL` runs the same suite against a **disposable** PostgreSQL database. CI does this.
- `fixtures/demo_provider.py` is the contract fixture for every agent schema. Add a branch before
  introducing a new schema, or the suite cannot exercise it.
- Tests are named after invariants (duplicate, concurrent, stale, cross-tenant), not implementation
  details. Preserve that style and add a regression test whenever a boundary is fixed.

| Suite | Contract |
| --- | --- |
| `test_saas.py` | Auth, CSRF/origin, tenancy, lifecycle, idempotency, concurrency, retired routes |
| `test_agent_workflows.py` | Bounded runtime, retries, fallbacks, report recovery |
| `test_quality_contracts.py` | Evidence quoting, rubric coverage, scoring, prompt integrity |
| `test_providers.py` | Adapter wire formats, deadlines, sanitized failures |
| `test_speech.py` | WAV validation, chunking, ordering, sanitization |
| `test_discovery.py` | Publication, consent, revocation, cross-account reads |
| `test_billing.py` | Signatures, idempotency, out-of-order reconciliation |
| `test_personas.py` / `test_model_routing.py` | Role snapshots and TOML routing |
| `test_setup_cache.py` / `test_job_descriptions.py` | Saved setup reuse and rendering |
| `test_company_research.py` | Sourced facts, cache ownership, unavailability |
| `test_progress.py` / `test_evaluation_suite.py` | Progress math and the offline evaluation CLI |

Run `uv run pytest -q`; focus with `uv run pytest tests/test_billing.py -q` or `-k concurrent`.
