# Agent execution and recovery

Read this alongside AGENT_WORKFLOWS.md. Domain services enforce ownership/state; models return
validated proposals. The implementation uses the existing explicit runtime and database queue.

## Execution bundles

`agents/specs.py` snapshots resolved provider/model names, credential **environment names**, context
limits, fallback profiles, role policies and contract revision 3. Full prompts (including the shared
`_preamble.md`) are stored once in immutable `prompt_bundles` by SHA-256; interviews reference their ID. New
interviews retain this private bundle in `plan._execution`, plus a typed `plan._brief` containing role,
resume, JD, language, preferences and source-backed company context. No credential values are stored.
Credentials are resolved from the environment each time, permitting rotation. Prompt integrity and
contract revision are checked. Revision 2 inline bundles and their original output contracts remain supported; historical reports are not rescored.
Portable evaluation manifests include prompt text so a run can be replayed without the application database.

Legacy interviews without a bundle retain ID-based live-turn routing. Their first report job saves
an execution/context bundle in its checkpoint, so later report retries use the same version. Existing
completed reports remain readable; no historical transcripts or scores are rewritten.

## Budgets and retries

| Role | Total reasoning deadline | Per attempt | Output token cap |
| --- | --- | --- | --- |
| Live interviewer | 28s | 14s | 1,200 |
| Planner | 70s | 35s | 3,000 |
| Evaluator stage | 90s | 45s | 4,000 |
| Coach | 50s | 25s | 2,000 |
| Resume analyst | 60s | 30s | 4,000 |
| Setup assistant | 60s | 30s | 3,000 |
| Company research | 35s | 30s | 2,400 |

There are at most two attempts. Invalid output repairs use the same model with bounded feedback.
Transport, quota or configuration failures may use a configured fallback; malformed JSON alone cannot switch models. Configuration/permanent errors are not retried against the identical profile. Rate-limit
Retry-After seconds are honored only within the total deadline. Validation retries receive bounded
field paths/codes without raw input values. Semantic validators execute before recording success.
Adapters enforce cancellable asyncio deadlines and disable nested SDK retries. Safe errors distinguish
transient, rate-limited, invalid-output, configuration, context-limit, deadline and internal failures.

`context_tokens` is explicit per profile. The offline estimate accounts for ASCII words, punctuation,
whitespace and Unicode with safety headroom, plus prompt/schema/framing/output costs. It is an estimate,
not a guarantee or vendor tokenizer; `byte_ceiling` remains available for strict operator policies.
Sarvam has 128,000 tokens and its conversation profile 32,000. Gemini profiles declare 1,048,576;
GPT-4.1 mini declares 1,047,576. Changing a model requires checking its limit. Compatible profiles fail
closed until `COMPATIBLE_CONTEXT_TOKENS` is supplied. A process-wide semaphore bounds each provider/model;
multiple processes must divide provider capacity themselves. This is not a distributed provider limiter.

Limits were checked against [Sarvam](https://docs.sarvam.ai/api/getting-started/models/sarvam-105b),
[Gemini](https://ai.google.dev/gemini-api/docs/models/gemini-2.5-flash), and
[OpenAI](https://developers.openai.com/api/docs/models/gpt-4.1-mini). These are configuration values,
not guarantees of account entitlement.

## Context and reports

Live context includes the current answer, three current-topic turns, relevant setup excerpts and a
running memory of up to ten exact candidate claims. Each memory update must quote the current answer
and carry its answer ID. Claims are candidate statements, not externally verified facts. The service
accepts a short transition and legal unvisited bank index, limits follow-ups to two, and honours finish
within the final three minutes. The final two minutes always close after an accepted answer. Planning
requires ceil(duration/5) questions (minimum two), with at most two extra and distinct topics. This
prevents undersized plans; it cannot guarantee that brief answers fill the entire scheduled duration.

Revision 3 report stages use round-specific criteria/weights snapshotted from personas.py. Models rate
criteria 0–4, provide reasons and link each scored criterion to exact evidence. A genuinely inapplicable
criterion can be null; the server excludes it from the denominator. All-null topics abstain. The server
computes totals/bands. Weights and bands are **provisional**, not human-calibrated hiring predictions.
Communication clarity and structure use bounded verbatim answer samples with dimension-specific exact
quotes. Confidence is no longer inferred from text. Historical confidence fields remain readable.

Evaluator context is an allowlist: role, experience, language and server-owned persona/rubric. It does
not include raw preferences, resume or company research. A deterministic guard flags obvious grading
manipulation in preferences before planning/interviewing; this is supplemental, not a complete semantic
prompt-injection detector. Transcripts remain untrusted data and exact evidence is enforced separately.

Topic stages run concurrently (default two, configured in TOML `[execution].report_concurrency`, maximum
four). One coordinator reserves quota and saves checkpoints; executor threads never share its Session.
Successful siblings survive another topic's failure. No further calls launch after a detected failure.
The coordinator renews leases while waiting. Long-topic batches retain every Unicode character and
answer ID, and their size uses the smallest configured fallback context budget. Consolidation uses
validated parts and exact quotes. Summary/coaching follow the completed assessments.

Coaching uses eleven fixed skill IDs and six exercise types. An unfinished exercise with the same
candidate/account, normalized job title, skill and exercise type is reused, with an additional source
interview link. Completed work is retained and can lead to a new exercise; legacy tasks remain readable.
This is deterministic goal grouping, not semantic equivalence across different job titles.

`AgentJob.artifacts` saves input hash, execution/context bundle and completed steps. Every checkpoint
checks the lease token and renews its 240-second lease. A stale worker cannot checkpoint or publish.
Successful steps are reused across retry/restart; permanent failures terminate after bounded repair.
Transient jobs retry up to three claims, and manual retry preserves valid checkpoints. Report plus
practice tasks publish in one transaction. The API exposes only progress labels and safe errors,
not private checkpoints. A report's total duration varies with topic count; stage deadlines fit leases.

## Observability and accounting

AgentRun correlates operation/job ID, stage and attempt with safe error categories, model/prompt
revision, latency and token usage. Semantic failures are failed runs; publication is a separate
`report_workflow` event. Diagnostic trace writes are best-effort and cannot discard a valid inference.
Authoritative account quota reservations remain database-backed and fail closed.

Usage currently counts logical reasoning stages, speech actions and search invocations; a reasoning
repair, multiple STT chunks or multiple search queries can involve more provider requests. Token
metadata records reported usage, not a calculated invoice. Price actual workload before promising
cost-based quotas. Search/STT/TTS and end-to-end voice timing require separate monitoring from the
reasoning runs; full streaming/barge-in is unchanged and outside this implementation.

## Extending safely

Add contracts and prompt variants in schemas.py/specs.py; add fixtures for every new contract. Preserve
semantic quote checks, frozen inputs, ownership and fenced checkpoint writes. Test failures between
stages, restart recovery, credential rotation, model/prompt edits, long multilingual inputs and stale
leases. Provider tests must enforce the supplied timeout/output budget. See EXTENDING.md and RUN.md.
The 20-case synthetic evaluation CLI in `backend/evaluations/` records prompt/model snapshots, drift,
quote rejection, action accuracy, variance and latency. It is offline by default and needs explicit paid
flags for model calls. Reference ranges remain provisional. Live quality still requires human review: fixture success proves workflow correctness,
not calibrated hiring judgment or universal factual accuracy.
