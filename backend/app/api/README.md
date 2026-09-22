# HTTP layer

Use `current_context` for every private route. It verifies the database session, active membership
and CSRF token. Owner-only operations additionally call `ctx.require_owner()`.
Business transitions belong in services. Always pass the current session's engine into an agent
invocation, so tests/workers can use isolated databases without changing global state.
See docs/API.md for endpoint contracts and tests/test_saas.py for authorization examples.
