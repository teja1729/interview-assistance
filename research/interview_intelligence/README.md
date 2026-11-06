# Interview intelligence database

Initial public-web-only dataset for India-first AI and software-engineering interview research.

Scope:

- Companies: Meta, Google, Sarvam AI, Swiggy, Locus.sh
- Geography: India-first; India-specific reports are preferred
- Time window: 2024-09-26 through 2026-09-26 where dates are available
- Access: public search results and publicly readable pages only
- No authenticated browsing, private APIs, or restricted scraping

The JSON separates `sources` from `evidence`. A source is an observed public page. Evidence is an
extracted claim linked back to that source, with a confidence value. A claim can be useful without
being authoritative; repeated reports should be aggregated before becoming a planning default.

The datasets are stored as JSON for easy inspection and later import into a database if needed:

- `interview_intelligence.json`: source-linked reports, observed questions and extracted company knowledge.
- `company_knowledge_base.json`: expanded knowledge model with extraction rules, confidence and coverage gaps.
- `company_interview_rubrics.json`: company/role/round scoring rubrics for mock interviews.

## Parameterized pipeline

`pipeline.py` creates a fresh local JSON artifact from public web evidence and an OpenAI synthesis
pass by default. It accepts company, role, level, location, exact month window, domain focus,
evidence limit, provider, model and output path. It does not write the application database.

Dry-run the search plan:

```bash
cd backend
uv run python ../research/interview_intelligence/pipeline.py \
  --company Meta --role "software engineer" --level SDE-2 --location India \
  --focus ranking --focus distributed-systems --dry-run
```

Run it with `OPENAI_API_KEY` in `backend/.env`:

```bash
uv run python ../research/interview_intelligence/pipeline.py \
  --company "Sarvam AI" --role "ML engineer" --level senior \
  --location Bengaluru --focus speech --focus multilingual \
  --output ../research/interview_intelligence/sarvam_ml_pipeline.json
```

The default OpenAI split is `gpt-4.1-mini` for web research and `gpt-4.1-nano` for rubric
synthesis. Override them independently with `--research-model` and `--synthesis-model`, or use
`INTERVIEW_KB_RESEARCH_MODEL` and `INTERVIEW_KB_SYNTHESIS_MODEL`. `--model` remains as a
backward-compatible override for both stages. The default evidence cap is 10, research output is
3000 tokens, synthesis output is 4000 tokens, and OpenAI web search uses low context to control
cost. These can be changed with `--max-evidence`, `--research-output-tokens`,
`--synthesis-output-tokens`, and `--search-context-size`.

The pipeline uses OpenAI for both web research and rubric synthesis by default, keeping the
research and generation schemas consistent. The research stage requires the OpenAI web-search
tool and requests one bounded search pass; the provider may still decide how many underlying
queries are needed, so search coverage remains model-reported rather than independently verified.

Sarvam remains an optional experimental provider. It requires
`--provider sarvam --research-packet <file>` because it does not perform the web-search stage here.

The pipeline uses structured JSON output and `store=false`; it keeps source evidence, uncertainty,
contradictions and the generated rubric together in one artifact.

Before writing, it rejects empty packets, over-limit evidence, duplicate evidence IDs, inconsistent
source IDs/canonical URLs, excessive slicing of one source page, malformed dates/URLs, unsupported
interview dates, unsupported observed questions, company-role mismatches, missing requested-focus
coverage, rubric URLs absent from the packet, unsafe default filenames, and accidental overwrites.
Repeated reports may share an independence cluster and count once. Bounds are enforced for the month
window, evidence count and output-token budget. Reused packets may be up to 31 days stale when they
still cover the requested scope; fresh packets must match the requested date window exactly. Every
rubric round must cite at least one evidence ID, and top-level rubric lists are bounded.

`--allow-insufficient-evidence` is recorded in metadata and marks the artifact
`evidence_status: insufficient_evidence` when the packet lacks two independent clusters or a
first-hand report. Such a rubric cannot contain high-confidence rounds. Publication dates and
interview dates have separate provenance, and question/task observations require explicit source-text
extraction. Identical publication and interview dates are conservatively treated as unverified
interview dates. These are evidence-quality checks, not proof that a public page supports every claim;
provider search citations remain model-reported unless captured by the adapter. Focus coverage is
derived from cited claim/excerpt text, not accepted from the model's status alone. Evidence clusters
are counted only from first-hand reports for sufficiency; secondary pages are tracked as source pages,
not independent interview accounts. Insufficient artifacts are written as provisional process
hypotheses with model-reported, unverified provenance.

The rubric also includes target-level calibration, critical gates, an evidence-capture contract,
standardized hinting/anti-bias rules, and company-role question variants. These are evaluation
controls, not claims that every candidate receives the listed prompt.

The knowledge base now separates official company signals, first-hand interview evidence, secondary
aggregations, and community context. It also records recency, independent evidence clusters,
contradictions, and promotion rules so repeated web copies are not mistaken for independent reports.

## Application import

The workbook is the authoring source; the interviewer consumes a bounded database snapshot. Use
`backend/scripts/import_company_intelligence.py` for a dry-run validation report (default), then
`--stage` to store an immutable inactive batch or `--activate` after review to publish it for new
interviews. See `docs/COMPANY_RESEARCH.md` for the data and runtime boundaries. The processed pilot
workbook contains 514 rows across 12 tabs. One evaluation signal is quarantined
because its `source_ref` (`SRC-NVIDIA-HWH`) does not exist in the source registry; restricted and
rejected source/question rows remain stored but are excluded from runtime retrieval.

The seed is intentionally conservative. It captures the first search pass rather than pretending to
be a complete question bank. Several search-result pages are editorial aggregations; they are marked
as medium or low confidence and should be verified against primary candidate reports where possible.

Important limitations:

- Interview loops vary by role, level, team, location, and hiring campaign.
- Exact question text may be paraphrased or copied between sites.
- Some results contain claims beyond the visible evidence and are not promoted to high confidence.
- LinkedIn, Glassdoor, and other restricted platforms should be added only through permitted public
  pages, official access, or user-provided URLs.
