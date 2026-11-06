# Company interview intelligence workbook export

This directory is a readable JSON export of workbook `(3)`, dated 2026-11-06. It expands the previous
export from 514 to 956 rows, adding 28 company profiles and additional role families, profiles, stages,
sources, experiences, questions, signals, and runtime drafts. `manifest.json` maps each original workbook
tab to its JSON file. Each tab file contains the original column names and an array of row objects.

To import and activate it in an application database, run from `backend/`:

```bash
uv run alembic upgrade head
uv run python scripts/import_company_intelligence.py \
  ../research/interview_intelligence/workbook_v4/manifest.json --activate
```

The importer validates cross-sheet references and verifies the canonical content hash. The workbook
contains no human-approved records yet; provisional evidence is labeled as such. Signal `ES004` has an
unresolved source reference and is quarantined during import. Restricted and rejected source/question
rows remain in the export but cannot be selected at runtime.
