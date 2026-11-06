"""Validate and version a Suri company-intelligence XLSX workbook.

Dry-run is the default. --stage stores an immutable, inactive snapshot in PostgreSQL;
--activate stores it and makes that import the active runtime release. Activation is
explicit because the current pilot contains provisional material and no human-approved rows.
The parser reads cached cell values only and never evaluates workbook formulas or macros.
"""

import argparse
import hashlib
import json
import re
import sys
import time
import zipfile
from pathlib import Path
from xml.etree import ElementTree

NS = {
    "m": "http://schemas.openxmlformats.org/spreadsheetml/2006/main",
    "r": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
    "p": "http://schemas.openxmlformats.org/package/2006/relationships",
}
EXPECTED_SHEETS = {
    "01 Company Profiles": "company_id",
    "02 Company Archetypes": "archetype_id",
    "03 Universal Traits": "trait_id",
    "04 Archetype-Trait Map": "archetype_id",
    "05 Role Profiles": "role_family_id",
    "06 Role-Interview Profiles": "profile_id",
    "07 Interview Stages": "stage_id",
    "08 Evidence Sources": "source_id",
    "09 Interview Experiences": "experience_id",
    "10 Questions-Conv Patterns": "pattern_id",
    "11 Evaluation Signals": "signal_id",
    "12 Runtime Configs": "config_id",
}
MAX_COMPRESSED_BYTES = 40 * 1024 * 1024
MAX_UNCOMPRESSED_BYTES = 160 * 1024 * 1024
MAX_ROWS = 100_000
MAX_COLUMNS = 100
VALID_PUBLICATION_STATES = {"approved", "provisional", "restricted", "rejected"}


class WorkbookError(ValueError):
    pass


def column_number(cell_ref):
    letters = "".join(char for char in cell_ref if char.isalpha())
    number = 0
    for char in letters.upper():
        number = number * 26 + ord(char) - 64
    return number


def workbook_sheets(path):
    """Read a bounded XLSX package or a generated JSON manifest."""
    path = Path(path)
    if path.stat().st_size > MAX_COMPRESSED_BYTES:
        raise WorkbookError("Input must be smaller than 40 MiB")
    if path.suffix.lower() == ".json":
        try:
            manifest = json.loads(path.read_text(encoding="utf-8"))
            if manifest.get("format") != "suri-company-intelligence" or manifest.get("format_version") != 1:
                raise WorkbookError("Unsupported company-intelligence JSON manifest")
            sheet_files = manifest.get("sheets")
            if not isinstance(sheet_files, dict):
                raise WorkbookError("JSON manifest is missing its sheet file map")
            total_bytes = 0
            sheets = {}
            for title, filename in sheet_files.items():
                if not isinstance(filename, str) or Path(filename).name != filename:
                    raise WorkbookError("JSON manifest sheet files must be plain filenames")
                sheet_path = path.parent / filename
                total_bytes += sheet_path.stat().st_size
                if total_bytes > MAX_UNCOMPRESSED_BYTES:
                    raise WorkbookError("JSON sheet files exceed the 160 MiB safety limit")
                content = json.loads(sheet_path.read_text(encoding="utf-8"))
                columns = content.get("columns")
                rows = content.get("records")
                if content.get("sheet") != title or not isinstance(columns, list) or not isinstance(rows, list):
                    raise WorkbookError(f"Malformed JSON data for sheet {title!r}")
                if len(rows) > MAX_ROWS or len(columns) > MAX_COLUMNS:
                    raise WorkbookError(f"Sheet {title!r} exceeds the import limits")
                sheets[title] = [columns] + [[row.get(key, "") for key in columns] for row in rows]
            sheets["_source_metadata"] = {
                "workbook": manifest.get("source_workbook", {}).get("name", path.name),
                "workbook_sha256": manifest.get("source_workbook", {}).get("sha256", ""),
                "workbook_version": manifest.get("source_workbook", {}).get("version", ""),
                "expected_content_sha256": manifest.get("content_sha256", ""),
            }
            return sheets
        except WorkbookError:
            raise
        except (OSError, json.JSONDecodeError, AttributeError, TypeError) as exc:
            raise WorkbookError("JSON manifest or referenced sheet data is malformed") from exc
    if path.suffix.lower() != ".xlsx":
        raise WorkbookError("Input must be an .xlsx workbook or a Suri JSON manifest")
    try:
        archive = zipfile.ZipFile(path)
    except (OSError, zipfile.BadZipFile) as exc:
        raise WorkbookError("The workbook is not a valid XLSX package") from exc
    with archive:
        entries = archive.infolist()
        if sum(item.file_size for item in entries) > MAX_UNCOMPRESSED_BYTES:
            raise WorkbookError("Workbook expands beyond the 160 MiB safety limit")
        names = set(archive.namelist())
        if "xl/vbaProject.bin" in names or any(item.filename.startswith("xl/externalLinks/") for item in entries):
            raise WorkbookError("Macro-enabled or externally linked workbooks are not accepted")
        required = {"xl/workbook.xml", "xl/_rels/workbook.xml.rels"}
        if not required <= names:
            raise WorkbookError("Workbook is missing its workbook manifest")
        try:
            shared = []
            if "xl/sharedStrings.xml" in names:
                root = ElementTree.fromstring(archive.read("xl/sharedStrings.xml"))
                for item in root.findall("m:si", NS):
                    shared.append("".join(node.text or "" for node in item.findall(".//m:t", NS)))
            workbook = ElementTree.fromstring(archive.read("xl/workbook.xml"))
            relationships = ElementTree.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
            relation_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in relationships}
            sheets = {}
            for sheet in workbook.findall("m:sheets/m:sheet", NS):
                title = sheet.attrib["name"]
                target = relation_map[sheet.attrib[f"{{{NS['r']}}}id"]]
                if target.startswith("/"):
                    sheet_path = target.lstrip("/")
                elif target.startswith("xl/"):
                    sheet_path = target
                else:
                    sheet_path = f"xl/{target}"
                root = ElementTree.fromstring(archive.read(sheet_path))
                xml_rows = root.findall("m:sheetData/m:row", NS)
                if len(xml_rows) > MAX_ROWS:
                    raise WorkbookError(f"Sheet {title!r} exceeds the 100,000 row limit")
                matrix = []
                for xml_row in xml_rows:
                    values = {}
                    for cell in xml_row.findall("m:c", NS):
                        index = column_number(cell.attrib["r"])
                        if index > MAX_COLUMNS:
                            raise WorkbookError(f"Sheet {title!r} exceeds the 100-column limit")
                        value = cell.find("m:v", NS)
                        inline = cell.find("m:is", NS)
                        if value is not None:
                            raw = value.text or ""
                            if cell.attrib.get("t") == "s":
                                raw = shared[int(raw)]
                            elif cell.attrib.get("t") == "b":
                                raw = raw == "1"
                            else:
                                formula = cell.find("m:f", NS)
                                if formula is not None and raw == "":
                                    raw = ""
                        elif inline is not None:
                            raw = "".join(node.text or "" for node in inline.findall(".//m:t", NS))
                        else:
                            raw = ""
                        values[index] = raw
                    matrix.append([values.get(index, "") for index in range(1, max(values, default=0) + 1)])
                sheets[title] = matrix
        except (KeyError, ValueError, ElementTree.ParseError, zipfile.BadZipFile) as exc:
            if isinstance(exc, WorkbookError):
                raise
            raise WorkbookError("Workbook contents are malformed or inconsistent") from exc
    sheets["_source_metadata"] = {
        "workbook": path.name,
        "workbook_sha256": hashlib.sha256(path.read_bytes()).hexdigest(),
        "workbook_version": str((sheets.get("README") or [[""]])[0][0] or "unknown workbook version"),
    }
    return sheets


def normalize_cell(value):
    if value is None:
        return ""
    if isinstance(value, str):
        return value.strip()
    return value


def normalize_name(value):
    return re.sub(r"[^a-z0-9]+", "", str(value).casefold())


def record_key(sheet, row):
    if sheet == "04 Archetype-Trait Map":
        return f"{row.get('archetype_id', '')}|{row.get('trait', '')}"
    return str(row.get(EXPECTED_SHEETS[sheet], "")).strip()


def parse_workbook(path):
    data = workbook_sheets(path)
    source_metadata = data.pop("_source_metadata", {})
    issues = []
    missing_sheets = sorted(set(EXPECTED_SHEETS) - set(data))
    if missing_sheets:
        issues.append({"severity": "error", "code": "missing_sheets", "details": missing_sheets})
    rows_by_sheet = {}
    id_sets = {}
    for sheet, id_column in EXPECTED_SHEETS.items():
        matrix = data.get(sheet, [])
        if not matrix:
            rows_by_sheet[sheet] = []
            id_sets[sheet] = set()
            continue
        headers = [str(value).strip() for value in matrix[0]]
        if len(headers) != len(set(headers)) or not headers or any(not value for value in headers):
            issues.append({"severity": "error", "code": "invalid_headers", "sheet": sheet})
            rows_by_sheet[sheet] = []
            id_sets[sheet] = set()
            continue
        if id_column not in headers:
            issues.append({"severity": "error", "code": "missing_id_column", "sheet": sheet, "column": id_column})
            rows_by_sheet[sheet] = []
            id_sets[sheet] = set()
            continue
        rows = []
        seen = set()
        for line_number, values in enumerate(matrix[1:], start=2):
            row = {
                header: normalize_cell(values[index] if index < len(values) else "")
                for index, header in enumerate(headers)
            }
            if not any(value != "" for value in row.values()):
                continue
            external_id = record_key(sheet, row)
            if not external_id:
                issues.append({"severity": "error", "code": "missing_record_id", "sheet": sheet, "row": line_number})
            elif external_id in seen:
                issues.append(
                    {
                        "severity": "error",
                        "code": "duplicate_record_id",
                        "sheet": sheet,
                        "row": line_number,
                        "record_id": external_id,
                    }
                )
            else:
                seen.add(external_id)
            state = row.get("publication_state", "")
            if state and state not in VALID_PUBLICATION_STATES:
                issues.append(
                    {
                        "severity": "error",
                        "code": "invalid_publication_state",
                        "sheet": sheet,
                        "row": line_number,
                        "value": state,
                    }
                )
            rows.append(row)
        rows_by_sheet[sheet] = rows
        id_sets[sheet] = seen

    # Validate the workbook's key cross-sheet relationships without guessing at free-text references.
    reference_checks = [
        ("09 Interview Experiences", "source_id", "08 Evidence Sources"),
        ("10 Questions-Conv Patterns", "experience_id", "09 Interview Experiences"),
        ("11 Evaluation Signals", "source_ref", None),  # May refer to a source or experience.
    ]
    links_checked = 0
    rejected_records = []
    for sheet, column, target in reference_checks:
        for row_number, row in enumerate(rows_by_sheet.get(sheet, []), start=2):
            raw = str(row.get(column, "")).strip()
            if not raw:
                continue
            links_checked += 1
            refs = [item for item in re.split(r"[;,|\s]+", raw) if item]
            allowed = (
                id_sets.get(target, set())
                if target
                else id_sets.get("08 Evidence Sources", set()) | id_sets.get("09 Interview Experiences", set())
            )
            for reference in refs:
                if reference not in allowed:
                    if sheet == "11 Evaluation Signals":
                        rejected_records.append(f"{sheet}:{record_key(sheet, row)}")
                        issues.append(
                            {
                                "severity": "warning",
                                "code": "unresolved_signal_source_rejected",
                                "sheet": sheet,
                                "row": row_number,
                                "column": column,
                                "reference": reference,
                            }
                        )
                    else:
                        issues.append(
                            {
                                "severity": "error",
                                "code": "broken_reference",
                                "sheet": sheet,
                                "row": row_number,
                                "column": column,
                                "reference": reference,
                            }
                        )

    companies = {normalize_name(row.get("company", "")) for row in rows_by_sheet.get("01 Company Profiles", [])}
    roles = {row.get("role_family_id", "") for row in rows_by_sheet.get("05 Role Profiles", [])}
    for sheet in (
        "06 Role-Interview Profiles",
        "09 Interview Experiences",
        "10 Questions-Conv Patterns",
        "11 Evaluation Signals",
    ):
        for row_number, row in enumerate(rows_by_sheet.get(sheet, []), start=2):
            role = row.get("role_family", "") or row.get("normalized_role_family", "")
            if (
                role
                and normalize_name(role) not in {"all", ""}
                and role not in roles
                and not re.search(r"RF-[A-Z]+", role)
            ):
                issues.append(
                    {
                        "severity": "warning",
                        "code": "unmapped_role_family",
                        "sheet": sheet,
                        "row": row_number,
                        "value": role,
                    }
                )
            company = row.get("company", "")
            if company and normalize_name(company) not in companies:
                # Company aliases such as Amazon / AWS are common; preserve as a warning for review.
                issues.append(
                    {
                        "severity": "warning",
                        "code": "unmapped_company_name",
                        "sheet": sheet,
                        "row": row_number,
                        "value": company,
                    }
                )
    publication_counts = {}
    for sheet, rows in rows_by_sheet.items():
        for row in rows:
            state = row.get("publication_state", "") or "not_applicable"
            publication_counts[f"{sheet}:{state}"] = publication_counts.get(f"{sheet}:{state}", 0) + 1
    errors = sum(issue["severity"] == "error" for issue in issues)
    warning_count = sum(issue["severity"] == "warning" for issue in issues)
    content_hash = hashlib.sha256(
        json.dumps(rows_by_sheet, ensure_ascii=False, sort_keys=True, separators=(",", ":")).encode()
    ).hexdigest()
    expected_content_hash = source_metadata.get("expected_content_sha256")
    if expected_content_hash and expected_content_hash != content_hash:
        raise WorkbookError("JSON data does not match the content hash in its manifest")
    report = {
        "workbook": source_metadata.get("workbook", Path(path).name),
        "workbook_sha256": source_metadata.get("workbook_sha256")
        or hashlib.sha256(Path(path).read_bytes()).hexdigest(),
        "content_sha256": content_hash,
        "workbook_version": source_metadata.get("workbook_version") or "unknown workbook version",
        "status": "invalid" if errors else "validated_staged_candidate",
        "error_count": errors,
        "warning_count": warning_count,
        "sheets": {
            sheet: {
                "records": len(rows),
                "record_key": "archetype_id + trait" if sheet == "04 Archetype-Trait Map" else EXPECTED_SHEETS[sheet],
            }
            for sheet, rows in rows_by_sheet.items()
        },
        "total_records": sum(map(len, rows_by_sheet.values())),
        "publication_counts": publication_counts,
        "eligible_runtime_rows": sum(
            row.get("publication_state") in {"approved", "provisional"}
            and sheet in {"09 Interview Experiences", "10 Questions-Conv Patterns", "11 Evaluation Signals"}
            for sheet, rows in rows_by_sheet.items()
            for row in rows
        ),
        "importable_records": sum(map(len, rows_by_sheet.values())) - len(rejected_records),
        "human_approved_records": sum(
            row.get("publication_state") == "approved" for rows in rows_by_sheet.values() for row in rows
        ),
        "cross_sheet_links_checked": links_checked,
        "rejected_input_records": rejected_records,
        "issues": issues,
    }
    return report, rows_by_sheet


def row_metadata(sheet, row):
    company = str(row.get("company", "") or "").strip()
    role = str(row.get("role_family", "") or row.get("normalized_role_family", "") or "").strip()
    if not role and sheet == "05 Role Profiles":
        role = str(row.get("role_family_id", "") or "")
    return {
        "company_key": normalize_name(company),
        "role_family": role,
        "publication_state": str(row.get("publication_state", "") or "provisional"),
    }


def persist(path, report, rows_by_sheet, activate=False):
    backend_root = str(Path(__file__).resolve().parents[1])
    if backend_root not in sys.path:
        sys.path.insert(0, backend_root)
    from sqlalchemy import update
    from sqlmodel import Session

    from app.db import engine
    from app.models import CompanyIntelligenceImport, CompanyIntelligenceRecord

    if report["status"] == "invalid":
        raise WorkbookError("Workbook has blocking validation errors; nothing was saved")
    import_id = report["content_sha256"]
    with Session(engine) as session:
        existing = session.get(CompanyIntelligenceImport, import_id)
        if existing is None:
            batch = CompanyIntelligenceImport(
                id=import_id,
                workbook_name=report["workbook"],
                workbook_version=report["workbook_version"],
                report=report,
                created_at=time.time(),
            )
            session.add(batch)
            for sheet, rows in rows_by_sheet.items():
                for row in rows:
                    metadata = row_metadata(sheet, row)
                    external_id = record_key(sheet, row)
                    rejected = f"{sheet}:{external_id}" in report.get("rejected_input_records", [])
                    session.add(
                        CompanyIntelligenceRecord(
                            import_id=import_id,
                            sheet_name=sheet,
                            external_id=external_id,
                            company_key=metadata["company_key"],
                            role_family=metadata["role_family"],
                            publication_state="rejected" if rejected else metadata["publication_state"],
                            payload=row,
                        )
                    )
            session.flush()
        elif existing.report.get("content_sha256") != import_id:
            raise WorkbookError("Import identifier collision; no data was changed")
        if activate:
            session.exec(
                update(CompanyIntelligenceImport)
                .where(CompanyIntelligenceImport.status == "active", CompanyIntelligenceImport.id != import_id)
                .values(status="superseded")
            )
            target = session.get(CompanyIntelligenceImport, import_id)
            target.status = "active"
            target.activated_at = time.time()
            session.add(target)
        else:
            target = session.get(CompanyIntelligenceImport, import_id)
        target.workbook_name = report["workbook"]
        final_status = target.status
        target.report = {**report, "import_id": import_id, "status": final_status}
        session.add(target)
        session.commit()
    return import_id


def write_json_package(output_dir, workbook_path, report, rows_by_sheet):
    output_dir = Path(output_dir)
    output_dir.mkdir(parents=True, exist_ok=True)
    manifest_path = output_dir / "manifest.json"
    if any(output_dir.iterdir()):
        raise WorkbookError(f"Refusing to overwrite a non-empty JSON package directory: {output_dir}")
    sheet_files = {}
    for index, (sheet, rows) in enumerate(rows_by_sheet.items(), start=1):
        columns = list(rows[0]) if rows else []
        filename = f"{index:02d}_{re.sub(r'[^a-z0-9]+', '_', sheet.casefold()).strip('_')}.json"
        payload = {"sheet": sheet, "columns": columns, "records": rows}
        (output_dir / filename).write_text(json.dumps(payload, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")
        sheet_files[sheet] = filename
    manifest = {
        "format": "suri-company-intelligence",
        "format_version": 1,
        "source_workbook": {
            "name": report["workbook"],
            "sha256": report["workbook_sha256"],
            "version": report["workbook_version"],
        },
        "content_sha256": report["content_sha256"],
        "validation_summary": {
            "records": report["total_records"],
            "rejected_input_records": report["rejected_input_records"],
        },
        "sheets": sheet_files,
    }
    manifest_path.write_text(json.dumps(manifest, ensure_ascii=False, indent=2) + "\n", encoding="utf-8")


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("workbook", type=Path)
    parser.add_argument("--stage", action="store_true", help="Store a staged import; do not make it active")
    parser.add_argument("--activate", action="store_true", help="Store and activate this import for runtime retrieval")
    parser.add_argument("--report", type=Path, help="Write the validation report to a JSON file")
    parser.add_argument(
        "--convert-json-dir", type=Path, help="Convert an XLSX workbook into readable per-sheet JSON files"
    )
    args = parser.parse_args()
    if args.stage and args.activate:
        parser.error("Choose only one of --stage or --activate")
    try:
        report, rows = parse_workbook(args.workbook)
        if args.convert_json_dir:
            if args.stage or args.activate:
                parser.error("JSON conversion cannot be combined with --stage or --activate")
            if args.workbook.suffix.lower() != ".xlsx":
                parser.error("--convert-json-dir requires an .xlsx source workbook")
            write_json_package(args.convert_json_dir, args.workbook, report, rows)
        if args.stage or args.activate:
            report["import_id"] = persist(args.workbook, report, rows, activate=args.activate)
            report["status"] = "active" if args.activate else "staged"
        rendered = json.dumps(report, ensure_ascii=False, indent=2, default=str)
        if args.report:
            args.report.write_text(rendered + "\n", encoding="utf-8")
        print(rendered)
        return 1 if report["status"] == "invalid" else 0
    except (OSError, WorkbookError) as exc:
        print(json.dumps({"status": "error", "error": str(exc)}, indent=2), file=sys.stderr)
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
