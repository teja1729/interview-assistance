# Company interview intelligence workbook export

This directory is a readable JSON export of the pilot workbook dated 2026-11-06. `manifest.json`
maps each original workbook tab to its JSON file. Each tab file contains its original column names and
an array of row objects. Values and stable source IDs are preserved so the import report can be
reproduced without the original Excel file.

To load the data into an application database, apply migrations and run the operator importer from
`backend/`:

```bash
uv run alembic upgrade head
uv run python scripts/import_company_intelligence.py \
  ../research/interview_intelligence/workbook_v3/manifest.json --activate
```

The importer validates the manifest and cross-sheet references before writing. It recomputes the
canonical data hash and rejects edits that do not match the manifest. Update the workbook and regenerate
the JSON export when changing the authored data. The export contains 514 rows; signal `ES004` has an
unresolved source reference and is quarantined during import. Restricted and rejected source/question
rows are preserved in the export and remain ineligible for runtime retrieval.
