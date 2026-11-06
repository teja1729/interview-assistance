"""Retrieve a bounded, version-pinned company intelligence snapshot for interviews."""

import re

from sqlmodel import Session, select

from ..models import CompanyIntelligenceImport, CompanyIntelligenceRecord
from ..schemas import CompanyIntelligence, CompanyIntelligenceEvidence

ALIASES = {
    "amazon": "amazonaws",
    "aws": "amazonaws",
    "amazonaws": "amazonaws",
    "walmart": "walmartglobaltech",
    "walmartglobaltech": "walmartglobaltech",
    "suri": "suri",
}
EVIDENCE_SHEETS = {
    "06 Role-Interview Profiles",
    "07 Interview Stages",
    "09 Interview Experiences",
    "10 Questions-Conv Patterns",
    "11 Evaluation Signals",
}


def normalize(value):
    return re.sub(r"[^a-z0-9]+", "", str(value or "").casefold())


def company_key(value):
    normalized = normalize(value)
    return ALIASES.get(normalized, normalized)


def _clean(value, limit=1200):
    value = re.sub(r"[\x00-\x08\x0b\x0c\x0e-\x1f]", "", str(value or ""))
    return re.sub(r"\s+", " ", value).strip()[:limit]


def _split_values(value):
    return [item.strip() for item in re.split(r"[;,|/\n]+", str(value or "")) if item.strip()]


def _resolve_role(records, job_title):
    target = normalize(job_title)
    for record in records:
        if record.sheet_name != "05 Role Profiles":
            continue
        row = record.payload
        role_id = str(row.get("role_family_id", ""))
        role_name = str(row.get("role_family", ""))
        aliases = [role_name, *_split_values(row.get("original_titles_preserved_separately", ""))]
        if any(
            normalize(alias)
            and (normalize(alias) == target or normalize(alias) in target or target in normalize(alias))
            for alias in aliases
        ):
            return role_id, role_name, _split_values(row.get("core_competencies", ""))
    # Accept an explicit family identifier if a caller supplies one as the job title.
    for record in records:
        if record.sheet_name == "05 Role Profiles" and normalize(record.payload.get("role_family_id")) == target:
            return (
                record.payload.get("role_family_id", ""),
                record.payload.get("role_family", ""),
                _split_values(record.payload.get("core_competencies", "")),
            )
    return "", "", []


def _role_match(record, role_id, job_title):
    row = record.payload
    value = str(row.get("role_family", "") or row.get("normalized_role_family", "") or "").strip()
    direct = str(row.get("role_match", "") or row.get("title_match", "") or "").casefold()
    if value and role_id:
        if value.casefold() == role_id.casefold():
            return "exact_role"
        if direct in {"adjacent_role", "related", "adjacent"}:
            return "adjacent_role"
        if direct in {"general_process", "company_wide", "company-wide"}:
            return "general_process"
        return "unknown"
    if direct in {"exact_role", "exact", "exact role"}:
        return "exact_role"
    if direct in {"adjacent_role", "related", "adjacent"}:
        return "adjacent_role"
    if direct in {"general_process", "company_wide", "company-wide"}:
        return "general_process"
    title = normalize(job_title)
    record_title = normalize(row.get("original_role_title", ""))
    if title and record_title and (title in record_title or record_title in title):
        return "exact_role"
    return "unknown"


def _experience_band(years):
    if years <= 0:
        return "unknown"
    if years <= 2:
        return "early"
    if years <= 6:
        return "mid"
    return "senior"


def _level_relevance(level, years):
    level = str(level or "").casefold()
    if not level or any(value in level for value in ("unknown", "mixed", "all")):
        return "unknown"
    if any(value in level for value in ("campus", "entry", "junior", "graduate", "sde-1", "early")):
        observed = "early"
    elif any(value in level for value in ("mid", "sde-2", "l4", "experienced")):
        observed = "mid"
    elif any(value in level for value in ("senior", "staff", "principal", "lead", "l5", "l6")):
        observed = "senior"
    else:
        return "unknown"
    target = _experience_band(years)
    if target == "unknown":
        return "unknown"
    return "matching" if observed == target else "adjacent"


def retrieve(session: Session, company: str, job_title: str, experience_years: int = 0) -> CompanyIntelligence:
    if not company.strip():
        return CompanyIntelligence(status="not_requested")
    active = session.exec(
        select(CompanyIntelligenceImport)
        .where(CompanyIntelligenceImport.status == "active")
        .order_by(CompanyIntelligenceImport.activated_at.desc())
        .limit(1)
    ).first()
    if not active:
        return CompanyIntelligence(status="no_company_evidence", company=company)
    records = list(
        session.exec(select(CompanyIntelligenceRecord).where(CompanyIntelligenceRecord.import_id == active.id)).all()
    )
    role_id, role_name, competencies = _resolve_role(records, job_title)
    company_records = [record for record in records if record.company_key == company_key(company)]
    if not company_records:
        return CompanyIntelligence(
            status="no_company_evidence",
            company=company,
            import_id=active.id,
            role_family=role_name,
            role_competencies=competencies,
        )

    experience_rows = {
        record.external_id: record.payload
        for record in company_records
        if record.sheet_name == "09 Interview Experiences" and record.publication_state in {"approved", "provisional"}
    }
    eligible_experience_ids = set()
    eligible_source_ids = set()
    for record in company_records:
        if (
            record.sheet_name == "08 Evidence Sources"
            and record.publication_state in {"approved", "provisional"}
            and record.payload.get("extraction_status") == "extracted"
        ):
            eligible_source_ids.add(record.external_id)
    selected = []
    registered_sources = {
        str(record.payload.get("source_url", "")).rstrip("/"): record.external_id
        for record in company_records
        if record.sheet_name == "08 Evidence Sources"
        and record.publication_state in {"approved", "provisional"}
        and record.payload.get("extraction_status") == "extracted"
    }
    for record in company_records:
        if record.sheet_name == "01 Company Profiles":
            row = record.payload
            profile_source_ids = [
                registered_sources[url.rstrip("/")]
                for url in (row.get("official_careers_url"), row.get("official_about_url"))
                if url and url.rstrip("/") in registered_sources
            ]
            details = []
            for label, column in (
                ("business and products", "business_and_products (official sources only)"),
                ("officially stated values and mission", "values_mission_culture (official sources only)"),
                (
                    "company-wide hiring context",
                    "hiring_process_context (official, company-wide only; role-specific process lives in tabs 06/07)",
                ),
            ):
                value = _clean(row.get(column), 300)
                if value and not value.casefold().startswith("unknown"):
                    details.append(f"{label}: {value}")
            if details and profile_source_ids:
                selected.append(
                    (
                        0,
                        CompanyIntelligenceEvidence(
                            record_type="official_company_profile",
                            record_id=record.external_id,
                            publication_state="provisional",
                            role_match="general_process",
                            summary=_clean(
                                "Official-source profile (context only; not role-specific evidence): "
                                + "; ".join(details),
                                1200,
                            ),
                            source_ids=profile_source_ids[:8],
                        ),
                    )
                )
    for record in company_records:
        if record.publication_state not in {"approved", "provisional"}:
            continue
        row = record.payload
        match = _role_match(record, role_id, job_title)
        if record.sheet_name not in EVIDENCE_SHEETS:
            continue
        if record.sheet_name == "09 Interview Experiences":
            row_role = str(row.get("role_family", "") or row.get("normalized_role_family", "")).strip()
            if role_id and row_role and match == "unknown":
                continue
            if match == "unknown" and row.get("role_relevance") not in {
                "general_process",
                "exact_role",
                "adjacent_role",
            }:
                continue
            eligible_experience_ids.add(record.external_id)
            if row.get("source_id"):
                eligible_source_ids.add(str(row["source_id"]))
            summary = _clean(row.get("process_summary") or row.get("rounds_and_questions_detail"))
            if summary:
                quality = _clean(row.get("record_class", "reported experience"), 100)
                level_relevance = _level_relevance(row.get("reported_level"), experience_years)
                role_rank = 0 if match == "exact_role" else 2
                level_rank = {"matching": 0, "unknown": 1, "adjacent": 2}[level_relevance]
                selected.append(
                    (
                        role_rank + level_rank,
                        CompanyIntelligenceEvidence(
                            record_type=quality,
                            record_id=record.external_id,
                            publication_state=record.publication_state,
                            role_match=match,
                            level_relevance=level_relevance,
                            summary=_clean(
                                f"Candidate-reported process evidence ({quality}; not a guaranteed company process): {summary}",
                                1200,
                            ),
                            source_ids=[str(row["source_id"])] if row.get("source_id") else [],
                        ),
                    )
                )

    for record in company_records:
        if record.publication_state not in {"approved", "provisional"}:
            continue
        row = record.payload
        match = _role_match(record, role_id, job_title)
        if record.sheet_name == "06 Role-Interview Profiles":
            profile_refs = set(_split_values(row.get("evidence_record_ids", "")))
            linked = profile_refs.intersection(eligible_experience_ids)
            if not linked or (role_id and match == "unknown"):
                continue
            summary = _clean(row.get("observed_process"), 850)
            if summary:
                selected.append(
                    (
                        2,
                        CompanyIntelligenceEvidence(
                            record_type="evidence_linked_role_profile",
                            record_id=record.external_id,
                            publication_state="provisional",
                            role_match=match,
                            summary=_clean(
                                f"Evidence-linked process synthesis; check its stated role, level, and geography gaps: {summary}",
                                1200,
                            ),
                            source_ids=sorted(linked)[:8],
                        ),
                    )
                )
        elif record.sheet_name == "07 Interview Stages":
            stage_refs = set(_split_values(row.get("linked_records", "")))
            linked = stage_refs.intersection(eligible_experience_ids | eligible_source_ids)
            if not linked:
                continue
            stage_role = str(row.get("role_family", "")).strip()
            if role_id and stage_role and stage_role.casefold() != role_id.casefold():
                continue
            detail = _clean(row.get("stage_detail"), 800)
            if detail:
                process_class = _clean(row.get("process_class", ""), 80)
                selected.append(
                    (
                        3,
                        CompanyIntelligenceEvidence(
                            record_type="interview_stage_evidence",
                            record_id=record.external_id,
                            publication_state="provisional",
                            role_match="exact_role" if stage_role == role_id else "general_process",
                            summary=_clean(
                                f"Source-linked {process_class} stage detail (not necessarily a universal process): {detail}",
                                1200,
                            ),
                            source_ids=sorted(linked)[:8],
                        ),
                    )
                )
        elif record.sheet_name == "10 Questions-Conv Patterns":
            if row.get("experience_id") not in eligible_experience_ids:
                continue
            if match == "unknown":
                experience = experience_rows.get(row.get("experience_id"), {})
                match = "exact_role" if experience.get("role_relevance") == "exact_role" else "adjacent_role"
            experience = experience_rows.get(row.get("experience_id"), {})
            level_relevance = _level_relevance(experience.get("reported_level"), experience_years)
            question = _clean(row.get("reported_question"), 700)
            theme = _clean(row.get("conversation_theme"), 160)
            if question:
                label = "Reported example question (not a standard or guaranteed question)"
                summary = f"{label}: {question}"
                if theme:
                    summary += f" Theme: {theme}."
                source_id = experience_rows.get(row.get("experience_id"), {}).get("source_id")
                role_rank = 1 if match == "exact_role" else 3
                level_rank = {"matching": 0, "unknown": 1, "adjacent": 2}[level_relevance]
                selected.append(
                    (
                        role_rank + level_rank,
                        CompanyIntelligenceEvidence(
                            record_type="reported_question",
                            record_id=record.external_id,
                            publication_state=record.publication_state,
                            role_match=match,
                            level_relevance=level_relevance,
                            summary=_clean(summary, 1200),
                            source_ids=[str(source_id)] if source_id else [],
                        ),
                    )
                )
        elif record.sheet_name == "11 Evaluation Signals":
            source_ref = str(row.get("source_ref", ""))
            if source_ref not in eligible_source_ids and source_ref not in eligible_experience_ids:
                continue
            signal_scope = _clean(row.get("signal_scope"), 100)
            if signal_scope.startswith("company_specific"):
                summary = _clean(row.get("signal"))
                if summary:
                    selected.append(
                        (
                            2 if match == "exact_role" else 4,
                            CompanyIntelligenceEvidence(
                                record_type="evaluation_signal",
                                record_id=record.external_id,
                                publication_state=record.publication_state,
                                role_match=match,
                                summary=_clean(
                                    f"Reported evaluation signal ({_clean(row.get('evidence_basis'), 100)}): {summary}",
                                    1200,
                                ),
                                source_ids=[source_ref],
                            ),
                        )
                    )

    for archetype in (record for record in records if record.sheet_name == "02 Company Archetypes"):
        examples = _split_values(archetype.payload.get("example_companies_in_pilot", ""))
        if not any(company_key(example) == company_key(company) for example in examples):
            continue
        emphasized = [
            str(mapping.payload.get("trait", ""))
            for mapping in records
            if mapping.sheet_name == "04 Archetype-Trait Map"
            and mapping.payload.get("archetype_id") == archetype.external_id
            and str(mapping.payload.get("relationship", "")).casefold() == "emphasized"
        ]
        emphasis = _clean(archetype.payload.get("additional_emphasis", ""), 400)
        if emphasized or emphasis:
            summary = (
                f"Archetype emphasis hypothesis ({_clean(archetype.payload.get('mapping_confidence', 'unknown'), 40)} mapping): "
                f"{', '.join(emphasized)}. {emphasis} Use as a tentative practice emphasis only, not a company hiring claim."
            )
            selected.append(
                (
                    5,
                    CompanyIntelligenceEvidence(
                        record_type="archetype_hypothesis",
                        record_id=archetype.external_id,
                        publication_state="provisional",
                        role_match="general_process",
                        summary=_clean(summary, 1200),
                    ),
                )
            )

    selected.sort(key=lambda item: (item[0], item[1].record_id))
    evidence = [item[1] for item in selected[:12]]
    return CompanyIntelligence(
        status="available" if evidence else "no_company_evidence",
        company=company,
        import_id=active.id,
        role_family=role_name,
        role_competencies=competencies,
        evidence=evidence,
    )
