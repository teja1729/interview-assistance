# Follow-up architecture assessment and implementation

Reviewed 2026-09-20 against the actual repository. The earlier review in
AGENT_ARCHITECTURE_REVIEW.md records the previous baseline. This document covers the subsequent
15 findings and two smaller notes. Keep the service-owned state machine and strict agent contracts.

| Finding | Assessment and decision | Current implementation / limit |
| --- | --- | --- |
| 1. Discarded interviewer advance / finish | Worth correcting without granting control of state to the model. | Revision 3 accepts a short transition and a validated unvisited bank index. Finish is honoured with at most three minutes left; hard wrap remains two minutes. |
| 2. No cross-topic memory | Worth correcting; full transcript replay would grow latency/cost. | Up to ten exact candidate claims, with source answer IDs, retained across topics. New claims must quote the current answer; evaluators do not treat the memory as independent evidence. |
| 3. Bank too small for duration | Real missing validation. | Server checks ceil(duration/5), minimum two, at most two extra and unique topics. This ensures topic coverage, not a minimum wall-clock duration for terse answers. |
| 4. Unused live assessment | Generating it adds cost with no current product value. | Removed from revision 3 decisions. Historical decisions retain the old contract; independent scoring never consumes those assessments. |
| 5. Second-hand communication ratings | Real evidence gap. Word count alone would not establish good communication. | Summary receives bounded verbatim samples and needs dimension-specific exact quotes. Clarity/structure can abstain. Unsupported confidence scoring is removed from new reports. |
| 6. One rubric for all rounds | Real mismatch between roles, but new weights need calibration. | Persona-owned versioned criteria/weights, snapshotted per session. Server applies weights; N/A criteria are excluded with reasons. Weights and thresholds are explicitly provisional. |
| 7. Sequential topic evaluation | Independent stages can run concurrently. Sixfold speedup is not guaranteed. | Default two concurrent stages, configurable up to four. One coordinator owns quota/checkpoints; successful siblings survive a failure. Provider bounds and summary/coach latency still matter. |
| 8. Duplicate drills | Worth improving with stable keys before semantic deduplication. | Fixed skill/exercise vocabularies; unfinished goals merge by candidate/account, normalized role, skill and exercise. Source interview edges preserve provenance; completed history remains. Different role titles are not semantically merged. |
| 9. Search bypasses runtime | Real routing/observability inconsistency. | Seventh company_research role, search capability check, shared deadlines/traces and code-only TOML routing. Gemini implements the sourced search adapter. |
| 10. Schema repair switches model | Real retry-policy problem. | Invalid output retries the same model with safe field/code feedback. Transport, quota and configuration failures may select a configured fallback. Two total calls remain the cap. |
| 11. Byte token estimates / assumed windows | Real capacity problem; heuristic estimates are still approximate. | Verified per-profile context sizes, Unicode-aware offline estimate with headroom, conservative override option and profile-aware report batching. Compatible limits must be explicitly configured. |
| 12. Repeated full prompt snapshots | Real duplication. | Prompt bundles stored once by hash and referenced from interviews. Hash integrity checked. Revision 2 inline bundles remain readable; no destructive rewrite of history. |
| 13. Dead prompt / duplicated boilerplate | Worth simplifying while preserving old sessions. | Unreachable generic evaluator removed; shared preamble composed into revision 3 bundles. Legacy variants are deliberately retained for supported old contracts. |
| 14. No streaming | Worth a separate measured voice change; the claimed latency reduction is unproven. | Deferred. Speech remains STT -> validated/committed decision -> full TTS playback. Current microphone/playback regressions pass. Streaming needs adapter, cancellation, partial-failure, playback-order and latency tests; do not speak unvalidated model proposals. |
| 15. No evaluation loop | Highest-priority quality gap. A deterministic provider cannot certify judgment. | Twenty synthetic reference cases; opt-in paid runner records prompt/model bundles, score drift, evidence rejection, action accuracy, repairs, latency and variance. Reference ranges still need independent human review and a held-out set. Live failures are reported, never filled with synthetic scores. |
| 16. Eleven language locales | A product/speech capability boundary, not an accidental promise of worldwide voice support. | Explicitly retained for the default Sarvam voice integration (English plus ten Indian languages). This does not restrict account geography. Expanding locales requires tested STT/TTS and model contracts. |
| 17. Custom grading instructions | Worth hardening; no regex fully solves prompt injection. | Obvious manipulation is flagged/excluded from live preferences. Evaluator inputs omit all raw preferences/resume/company research, with a strict allowlist. Exact evidence checks and service-owned scores remain independent controls. |

## Additional setup and usage fixes

Generated descriptions/title suggestions are saved privately in setup_artifacts. Matching requests
load saved outputs before consuming paid quota. Explicit regeneration creates a new revision. Successful
company research is retained indefinitely, dated and reused until explicit refresh; failure backoff is
60 seconds and failed refreshes do not destroy earlier successful results. Concurrent first misses can
still make separate calls. See COMPANY_RESEARCH.md for ownership, matching and historical-data limits.

The local account had reached 3 of 3 Starter interviews, while AI usage was 30 of 150. Those counters
are separate. Errors now identify the exhausted resource. The approved development override is 100
interviews / 5,000 AI calls monthly, without resetting counters or changing Stripe subscription state.
Production ignores the override. Provider charges and rate limits remain independent.

## Verification and boundaries

Backend contract tests cover both SQLite and PostgreSQL: semantic evidence, legal topic selection,
memory provenance, old-contract compatibility, parallel checkpoints/retry, merged practice provenance,
cache ownership and cache reads after quota exhaustion. Browser checks cover saved brief restoration,
zero-usage reuse, interview/report/practice flows and microphone cleanup. Voice fixtures exercise automatic
turn-taking, permission retry and cloud-audio failure handling. Migrations are additive and schema drift
checks pass. RUN.md contains repeatable commands and explicit paid evaluation opt-ins.

Synthetic live testing exposed malformed JSON when Sarvam's constrained decoder received the nonblank
regex. Its adapter now omits regex constraints from the wire schema while keeping the full local Pydantic
checks. Invalid quotes are never silently rewritten. Evidence is generated before criterion ratings so
references point to an already constructed list, with explicit zero-based repair feedback.

An exact quote establishes provenance, not whether it justifies the score. Criterion applicability and
semantic quality still require human review. No result here certifies hiring predictions or guarantees
that every future model response will meet the contract. Interrupted/invalid calls fail visibly and the
checkpointed report can be retried; completed valid stages are retained.

## Recorded live verification (2026-09-20)

Real Sarvam calls on the same twenty synthetic cases, one run per case:

| Measure | Earlier revision 2 baseline | Final revision 3 |
| --- | --- | --- |
| Valid topic assessments | 17/20 | 20/20 |
| Scores in provisional reference range | 14/20 | 19/20 |
| Follow-up decisions matching reference | 11/17 attempted | 13/20 attempted |
| Invalid-output attempts requiring repair | 7 | 1 |
| Mean per-case evaluator + interviewer time | 4,213 ms | 8,378 ms |

The final run rejected and repaired one non-verbatim quote. All published evaluation artifacts passed
exact-quote validation. A separate real-model complete-report smoke check reached finished with three
checkpointed stages and two persisted coaching tasks. The baseline skipped interviewer calls when
scoring failed; the final runner attempts both independently, so action denominators differ. Adapter,
contract and prompt changes were combined: this is not an isolated prompt experiment. Timing is one
sample per case, includes network variance, and does not measure end-to-end speech latency.

Follow-up agreement is only 65% against provisional references; do not claim calibrated interviewing
judgment. The remaining work is human review, repeated and held-out evaluation, applicability checks,
and targeted dialogue improvements. Scores/weights remain practice feedback. Local ignored manifests
are evaluations/results/baseline-v2.json and evaluations/results/final-v3.json, each retaining the exact
prompt/profile/policy bundle. No private user transcript was used.
