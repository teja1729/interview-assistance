# Interview judgment regression suite

`cases.json` contains authored synthetic reference cases, not production transcripts. Expected
score ranges and actions are **provisional**, not human-calibrated hiring standards. Every case
records that review status. A human domain reviewer should review the answer, applicable rubric,
acceptable action and range before setting `human_reviewed` to true and adding `reviewer`.

Run the CLI in RUN.md with `--live --accept-cost` to deliberately call a real model. Default
validation is offline and never spends money. Results include case/model/prompt hashes, repeats,
score drift, action accuracy, quote fidelity, anchor coverage, repairs, latency and token usage.
Unreviewed cases are reported separately and cannot certify judgment quality. Keep a held-out set
when tuning prompts; do not narrow reference ranges merely to make a new prompt pass.

Never import private candidate transcripts without consent and anonymization. Fixtures and this
suite remain outside product flows. Results are local ignored artifacts; preserve a baseline
before comparing prompt/model changes. Quote fidelity checks provenance, not whether the quote
logically justifies a rating; anchor coverage is only a coarse relevance check.
