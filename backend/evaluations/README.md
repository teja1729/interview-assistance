# Interview judgment regression suite

`cases.json` contains synthetic reference cases, never production transcripts. Their score ranges,
actions and evidence anchors are provisional automated regression targets, not calibrated hiring
standards. The suite needs no manual review step: offline checks validate the dataset; opt-in live
runs compare model outputs with the synthetic targets, exact quote provenance, evidence anchors and
action expectations. Repeated runs report drift and variance, while saved model/prompt bundles make
comparisons reproducible.

Run the CLI in RUN.md with `--live --accept-cost` to deliberately call a real model. Default
validation is offline and never spends money. Results include case/model/prompt hashes, repeats,
score drift, action accuracy, quote fidelity, anchor coverage, repairs, latency and token usage.
Automated checks detect regressions and contract failures; they cannot prove that a judgment is
correct for every real candidate. Keep a held-out synthetic set when tuning prompts; do not narrow
reference ranges merely to make a new prompt pass.

Never import private candidate transcripts without consent and anonymization. Fixtures and this
suite remain outside product flows. Results are local ignored artifacts; preserve a baseline
before comparing prompt/model changes. Quote fidelity checks provenance, not whether the quote
logically justifies a rating; anchor coverage is only a coarse relevance check.
