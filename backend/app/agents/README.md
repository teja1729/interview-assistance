# Agent layer

Start with docs/AGENT_WORKFLOWS.md. Each role has explicit prompt/contract variants. Shared instructions are composed from `_preamble.md`.
`execute` returns a validated Pydantic object, runs optional semantic validation, records metadata
and allows at most two model calls. It classifies errors and provides safe repair hints.
`specs.py` owns role deadlines/output limits and immutable model/prompt/contract bundles.
`context.py` owns shared briefs, language preferences, bounded live memory and an evaluator input allowlist.
`tokens.py` owns the offline token estimate. Revision 3 prompts are stored once by hash; revision 2 inline
bundles and legacy output contracts remain supported.
See `docs/AGENT_RUNTIME.md` for exact budgets, checkpoints and compatibility rules.

Agents do not own sessions, entitlements, persistence or tool authorization. They propose outputs;
services perform semantic validation and commit. Add deterministic fixtures for new contracts under
`tests/fixtures/`. `specs.VARIANTS` selects dedicated prompts for role/contract pairs, such as the
setup assistant's structured job-description draft. Live providers may never fall back to fixtures.
