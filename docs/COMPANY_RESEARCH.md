# Company research

New company web research is currently unavailable because the application has no search provider.
When a candidate starts an interview, the supplied job description remains the source of role context.
The UI reports research as unavailable rather than inventing company facts.

Previously saved, candidate-owned research snapshots remain readable and may be reused. Cached IDs
are still checked against account ownership and the company, role and URL. An interview copies any
reused brief into its private snapshot so later changes to the cache do not alter that interview.
A forced refresh reports unavailable and does not replace a previously successful cached result.

The `CompanyBrief` and API contracts remain for stored data compatibility. No live web search or
provider call occurs on a cache miss, and unavailable results do not consume model quota.

## Curated interview intelligence

The workbook-backed intelligence corpus is separate from this candidate-owned web-research cache.
`scripts/import_company_intelligence.py` validates the XLSX package, sheet headers, stable row keys,
publication states and selected cross-sheet references. Dry-run is the default. `--stage` stores an
immutable inactive snapshot; `--activate` explicitly makes that snapshot the runtime release. Imports
are identified by workbook SHA-256, so uploading identical bytes is idempotent and a changed workbook
creates a new version. A signal with a broken source reference is stored as rejected and excluded from retrieval.

Runtime retrieval filters the active release by company and role, excludes restricted/rejected rows,
and snapshots a bounded set of provenance-labelled evidence into the interview's private `_brief`.
The planner and live interviewer may use it to choose practice emphasis. They must not present reported
questions or provisional patterns as guaranteed employer behavior. Company-role evidence can be absent;
in that case the runtime receives generic role competencies and continues using the job description.
Evaluator context deliberately excludes this company intelligence.

To validate a workbook without database writes:

```bash
cd backend
uv run python scripts/import_company_intelligence.py \
  "/path/to/Suri - Company Interview Intelligence.xlsx" \
  --report ../research/interview_intelligence/import_report.json
```

The XLSX can be converted into a readable manifest plus one JSON file per sheet:

```bash
cd backend
uv run python scripts/import_company_intelligence.py \
  "/path/to/Suri - Company Interview Intelligence.xlsx" \
  --convert-json-dir ../research/interview_intelligence/workbook_v4
```

The JSON manifest is a portable import source. It includes the source workbook hash and a canonical
content hash; the importer rejects modified sheet data when it no longer matches the manifest.
After reviewing the report and applying migrations, stage or activate the JSON release explicitly:

```bash
cd backend
uv run alembic upgrade head
uv run python scripts/import_company_intelligence.py ../research/interview_intelligence/workbook_v4/manifest.json --stage
# After operator review, make the staged version available to new interviews:
uv run python scripts/import_company_intelligence.py ../research/interview_intelligence/workbook_v4/manifest.json --activate
```

Activation permits provisional records because the pilot methodology allows cautious pattern synthesis.
The import report and original row publication state are retained for audit. Review the report before
activation; workbook content is never treated as executable instructions or prompt templates.
