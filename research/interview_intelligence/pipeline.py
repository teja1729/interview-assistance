"""Parameterized public-web interview intelligence pipeline.

Usage is intentionally local and JSON-only. The pipeline performs two bounded model calls:
1. search and normalize public evidence;
2. synthesize evidence into company knowledge and a mock-interview rubric.

It never writes application tables and never accepts candidate transcripts or secrets as model input.
"""

from __future__ import annotations

import argparse
import calendar
import hashlib
import json
import os
import re
import tempfile
from datetime import UTC, date, datetime
from pathlib import Path
from typing import Literal
from urllib.parse import urlparse

import httpx
from dotenv import load_dotenv
from openai import APIError, OpenAI
from pydantic import BaseModel, ConfigDict, Field, ValidationError, field_validator

ROOT = Path(__file__).resolve().parents[2]
OUTPUT_DIR = Path(__file__).resolve().parent
ROLE_ALIASES = {
    "software developer": "software engineer",
    "sde": "software engineer",
    "ml engineer": "machine learning engineer",
}
LEVEL_ALIASES = {
    "sde2": "sde-2",
    "sde ii": "sde-2",
    "sde 2": "sde-2",
    "sde1": "sde-1",
    "sde i": "sde-1",
    "sde 1": "sde-1",
}
LOCATION_ALIASES = {"bangalore": "bengaluru", "bombay": "mumbai", "new delhi": "delhi"}
LOCATION_PARENTS = {
    "bengaluru": "india",
    "delhi": "india",
    "hyderabad": "india",
    "mumbai": "india",
    "pune": "india",
    "chennai": "india",
    "kolkata": "india",
}


class Evidence(BaseModel):
    model_config = ConfigDict(extra="forbid")

    evidence_id: str = Field(min_length=1, max_length=120)
    source_id: str = Field(min_length=1, max_length=120)
    source_url: str
    source_title: str
    source_type: Literal[
        "official_role",
        "official_engineering",
        "first_hand_report",
        "secondary_aggregation",
        "community_context",
    ]
    published_date: str
    published_date_basis: Literal["page_publication", "explicit_source", "unknown"]
    interview_date: str
    interview_date_basis: Literal["explicit_interview", "unknown"]
    company: str
    role: str
    level: str
    location: str
    round: str
    claim: str
    observed_questions_or_tasks: list[str]
    follow_ups_or_probes: list[str]
    extraction_basis: Literal["explicit_source_text", "source_summary", "inferred", "unknown"]
    supporting_excerpt: str
    evaluation_signals: list[str]
    candidate_outcome: str
    confidence: Literal["high", "medium", "low"]
    independence_key: str = Field(min_length=1, max_length=120)
    evidence_limitations: list[str]

    @field_validator("source_url")
    @classmethod
    def valid_source_url(cls, value: str) -> str:
        parsed = urlparse(value)
        if parsed.scheme not in {"http", "https"} or not parsed.netloc or any(char.isspace() for char in value):
            raise ValueError("source_url must be an absolute HTTP(S) URL")
        return value

    @field_validator("published_date", "interview_date")
    @classmethod
    def valid_optional_date(cls, value: str) -> str:
        if value:
            date.fromisoformat(value)
        return value


class FocusCoverage(BaseModel):
    model_config = ConfigDict(extra="forbid")

    focus: str
    status: Literal["covered", "unsupported", "not_found"]
    evidence_ids: list[str]


class ResearchPacket(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: str
    role: str
    level: str
    location: str
    start_date: str
    end_date: str
    research_questions: list[str]
    focus_coverage: list[FocusCoverage]
    evidence: list[Evidence]
    unresolved_contradictions: list[str]
    coverage_gaps: list[str]

    @field_validator("start_date", "end_date")
    @classmethod
    def valid_date(cls, value: str) -> str:
        date.fromisoformat(value)
        return value


class RoundRubric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    round_name: str
    purpose: str
    dimensions: list[str]
    strong_evidence: list[str]
    weak_evidence: list[str]
    critical_gate: str
    company_specific_probes: list[str]
    likely_question_families: list[str]
    evidence_ids: list[str]
    confidence: Literal["high", "medium", "low"]
    basis_type: Literal["observed", "inferred", "mixed"]


class ScoringLevel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: str
    meaning: str


class CalibrationEntry(BaseModel):
    model_config = ConfigDict(extra="forbid")

    level: str
    expectation: str


class KnowledgeRubric(BaseModel):
    model_config = ConfigDict(extra="forbid")

    company: str
    role: str
    level: str
    location: str
    evidence_summary: str
    company_mindset: list[str]
    role_signals: list[str]
    likely_process_variants: list[str]
    round_rubrics: list[RoundRubric]
    observed_question_families: list[str]
    scoring_scale: list[ScoringLevel]
    hard_gates: list[str]
    preparation_priorities: list[str]
    confidence_and_limits: list[str]
    source_urls: list[str]
    seniority_calibration: list[CalibrationEntry]
    evidence_capture_contract: list[str]
    interviewer_protocol: list[str]
    anti_bias_checks: list[str]


def args() -> argparse.Namespace:
    parser = argparse.ArgumentParser(description="Generate company-specific interview knowledge and rubric JSON.")
    parser.add_argument("--company", required=True)
    parser.add_argument(
        "--role",
        required=True,
        help="For example: software engineer, ML engineer, applied AI engineer",
    )
    parser.add_argument(
        "--level",
        default="unspecified",
        help="For example: intern, SDE-1, SDE-2, senior",
    )
    parser.add_argument("--location", default="India")
    parser.add_argument("--months", type=bounded_int(1, 60), default=24)
    parser.add_argument(
        "--focus",
        action="append",
        default=[],
        help="Repeat for domain priorities such as speech or logistics",
    )
    parser.add_argument("--max-evidence", type=bounded_int(1, 100), default=10)
    parser.add_argument(
        "--provider",
        choices=["openai", "sarvam"],
        default=os.getenv("INTERVIEW_KB_PROVIDER", "openai"),
    )
    parser.add_argument(
        "--model",
        default=None,
        help="Backward-compatible override for both pipeline stages",
    )
    parser.add_argument("--research-model", default=None, help="Model used for web research")
    parser.add_argument("--synthesis-model", default=None, help="Model used for rubric synthesis")
    parser.add_argument("--output", type=Path, default=None)
    parser.add_argument(
        "--research-packet",
        type=Path,
        default=None,
        help="Reuse a previously collected ResearchPacket JSON; required for --provider sarvam",
    )
    parser.add_argument(
        "--max-output-tokens",
        type=bounded_int(1000, 20000),
        default=None,
        help="Backward-compatible token limit",
    )
    parser.add_argument("--research-output-tokens", type=bounded_int(1000, 8000), default=3000)
    parser.add_argument("--synthesis-output-tokens", type=bounded_int(1000, 8000), default=4000)
    parser.add_argument("--search-context-size", choices=["low", "medium", "high"], default="low")
    parser.add_argument(
        "--allow-insufficient-evidence",
        action="store_true",
        help="Permit a rubric when fewer than two independent clusters or no first-hand report exists",
    )
    parser.add_argument(
        "--overwrite",
        action="store_true",
        help="Allow replacing an existing explicit output path",
    )
    parser.add_argument(
        "--dry-run",
        action="store_true",
        help="Print the bounded search plan without calling the API",
    )
    return parser.parse_args()


def bounded_int(minimum: int, maximum: int):
    def parse(value: str) -> int:
        parsed = int(value)
        if not minimum <= parsed <= maximum:
            raise argparse.ArgumentTypeError(f"must be between {minimum} and {maximum}")
        return parsed

    return parse


def window(months: int) -> tuple[str, str]:
    end = datetime.now(UTC).date()
    month_index = end.year * 12 + end.month - 1 - months
    year, month_zero_index = divmod(month_index, 12)
    month = month_zero_index + 1
    start = date(year, month, min(end.day, calendar.monthrange(year, month)[1]))
    return start.isoformat(), end.isoformat()


def search_plan(options: argparse.Namespace, start: str, end: str) -> list[str]:
    focus = ", ".join(options.focus) if options.focus else "role-specific technical skills and company domain"
    base = f'"{options.company}" "{options.role}" {options.level} {options.location}'
    glassdoor_domain = "glassdoor.co.in" if "india" in options.location.casefold() else "glassdoor.com"
    return [
        f"{base} interview experience questions rounds {start}..{end}",
        f"{base} site:reddit.com OR site:leetcode.com OR site:geeksforgeeks.org interview",
        f"{base} site:{glassdoor_domain} interview questions",
        f"{options.company} careers {options.role} {focus}",
        f"{options.company} engineering blog technical architecture {focus}",
    ]


def instructions(start: str, end: str, max_evidence: int) -> str:
    return f"""You are the evidence collector for an interview intelligence dataset.
Use one bounded public-web search pass using the web search tool. Scope: interview evidence published or dated
between {start} and {end}, with priority for India and the requested role/level.

Return at most {max_evidence} evidence records. Separate first-hand candidate reports from official
company material and secondary aggregations. Do not invent a question, round, date, outcome or URL.
Use an empty string or empty list when a field is not visible. Set interview_date to empty and
interview_date_basis to unknown unless the source explicitly states when the interview occurred.
Never copy a page publication date into interview_date. Set extraction_basis to
explicit_source_text only when the source visibly contains the question/task; otherwise use
source_summary, inferred, or unknown and leave observed_questions_or_tasks and follow_ups_or_probes
empty. When extraction_basis is explicit_source_text, copy a short supporting_excerpt from the
source and ensure every observed question or follow-up is contained in that excerpt. Preserve contradictions instead of
forcing one universal process. Copy source URLs from pages actually found by search. Treat duplicated
aggregator wording as one independence_key. Extract follow-ups and evaluation signals, not only the
headline question. Do not include personal contact information or candidate-sensitive data. Generate
a unique evidence_id for each record. Use one stable source_id for every record copied from the same
canonical URL; never assign multiple source_ids to one URL. Never reuse an independence_key for
independent evidence clusters. Copy the requested company, role, level, location and exact date
window into the packet fields. For every requested focus area in the input, add exactly one
focus_coverage entry with status covered, unsupported, or not_found and cite evidence_ids only when
status is covered. Missing focus evidence must appear in coverage_gaps."""


def synthesize_instructions() -> str:
    return """You are a conservative interview-rubric analyst. Use only the supplied evidence packet.
Separate observed interview facts from role/domain inference. Do not claim that an official job
description proves an interview question. Preserve process variants by level, team and location.
Every question family must be traceable to evidence, and source_urls must contain only supplied URLs.
Generate a practical mock-interview rubric with observable evidence, company-specific probes and hard
gates. Low evidence must remain visible as uncertainty; do not fill gaps with generic certainty.
If the packet has no first-hand report or has fewer than two independent clusters, every round must
use confidence low or medium, and inferred or mixed basis; never label a generic question as observed.
Keep the artifact compact: use at most 3 items per list, at most 5 round rubrics, and one concise
sentence per item. Do not repeat the source packet verbatim. Include the requested seniority
calibration, evidence-capture contract, interviewer protocol and anti-bias checks as concise lists.
Return source_urls only by copying exact source_url values from the packet. Every round rubric must
include evidence_ids copied from the packet and mark its basis as observed, inferred or mixed."""


def normalize_scope(value: str) -> str:
    return re.sub(r"\s+", " ", value.casefold().strip())


def canonical_role(value: str) -> str:
    normalized = normalize_scope(value)
    return ROLE_ALIASES.get(normalized, normalized)


def canonical_level(value: str) -> str:
    normalized = normalize_scope(value)
    return LEVEL_ALIASES.get(normalized, normalized)


def canonical_location(value: str) -> str:
    normalized = normalize_scope(value)
    return LOCATION_ALIASES.get(normalized, normalized)


def canonical_url(value: str) -> str:
    parsed = urlparse(value)
    path = parsed.path.rstrip("/") or "/"
    return parsed._replace(
        scheme=parsed.scheme.casefold(),
        netloc=parsed.netloc.casefold(),
        path=path,
        query="",
        fragment="",
    ).geturl()


def location_matches(observed: str, requested: str) -> bool:
    observed = canonical_location(observed)
    requested = canonical_location(requested)
    if observed in {"", "unknown", "global"} or requested in {"", "unknown", "global"}:
        return True
    if observed == requested:
        return True
    return LOCATION_PARENTS.get(observed) == requested or LOCATION_PARENTS.get(requested) == observed


def normalize_packet_source_ids(packet: ResearchPacket) -> ResearchPacket:
    """Normalize identities and conservatively remove likely copied interview dates."""
    normalized = packet.model_copy(deep=True)
    for record in normalized.evidence:
        canonical = canonical_url(record.source_url)
        record.source_id = f"src_{hashlib.sha256(canonical.encode()).hexdigest()[:20]}"
        if record.interview_date and record.interview_date == record.published_date:
            record.interview_date = ""
            record.interview_date_basis = "unknown"
        if record.extraction_basis != "explicit_source_text" or not record.supporting_excerpt.strip():
            record.extraction_basis = "source_summary" if record.claim.strip() else "unknown"
            record.observed_questions_or_tasks = []
            record.follow_ups_or_probes = []
        elif any(
            question.casefold() not in record.supporting_excerpt.casefold()
            for question in [*record.observed_questions_or_tasks, *record.follow_ups_or_probes]
        ):
            record.extraction_basis = "source_summary"
            record.observed_questions_or_tasks = []
            record.follow_ups_or_probes = []
    return normalized


def normalize_focus_coverage(packet: ResearchPacket, focus: list[str]) -> ResearchPacket:
    normalized = packet.model_copy(deep=True)
    evidence_by_id = {record.evidence_id: record for record in normalized.evidence}
    entries = {normalize_scope(entry.focus): entry for entry in normalized.focus_coverage}
    gaps = list(normalized.coverage_gaps)
    for requested in focus:
        entry = entries.get(normalize_scope(requested))
        if entry is None:
            continue
        cited = [evidence_by_id[evidence_id] for evidence_id in entry.evidence_ids if evidence_id in evidence_by_id]
        searchable = " ".join(
            f"{record.claim} {record.supporting_excerpt} {' '.join(record.observed_questions_or_tasks)}"
            for record in cited
        ).casefold()
        if entry.status == "covered" and normalize_scope(requested) not in searchable:
            entry.status = "not_found"
            entry.evidence_ids = []
            gaps.append(f"Requested focus has no directly supported evidence: {requested}")
    if not any(record.source_type == "first_hand_report" for record in normalized.evidence):
        gaps.append("No first-hand interview report was found")
    if any(not record.interview_date for record in normalized.evidence):
        gaps.append("Interview dates are unknown unless explicitly stated by the source")
    normalized.coverage_gaps = list(dict.fromkeys(gaps))
    return normalized


def evidence_sufficiency(packet: ResearchPacket) -> tuple[int, int]:
    clusters = {record.independence_key for record in packet.evidence if record.source_type == "first_hand_report"}
    first_hand_count = sum(record.source_type == "first_hand_report" for record in packet.evidence)
    return len(clusters), first_hand_count


def normalize_rubric_confidence(
    rubric: KnowledgeRubric, packet: ResearchPacket, *, allow_insufficient: bool
) -> KnowledgeRubric:
    """Downgrade unsupported certainty before the rubric is validated or saved."""
    if not allow_insufficient:
        return rubric
    clusters, first_hand_count = evidence_sufficiency(packet)
    if clusters >= 2 and first_hand_count >= 1:
        return rubric
    normalized = rubric.model_copy(deep=True)
    evidence_by_id = {record.evidence_id: record for record in packet.evidence}
    for round_rubric in normalized.round_rubrics:
        if round_rubric.confidence == "high":
            round_rubric.confidence = "medium"
        cited = [
            evidence_by_id[evidence_id] for evidence_id in round_rubric.evidence_ids if evidence_id in evidence_by_id
        ]
        if round_rubric.basis_type == "observed" and not any(
            record.extraction_basis == "explicit_source_text" for record in cited
        ):
            round_rubric.basis_type = "inferred"
    normalized.confidence_and_limits = [
        re.sub(r"(?i)\bhigh confidence\b", "provisional confidence", item) for item in normalized.confidence_and_limits
    ]
    normalized.hard_gates = [f"Practice-only, not established: {item}" for item in normalized.hard_gates]
    return normalized


def validate_packet(
    packet: ResearchPacket,
    *,
    max_evidence: int,
    company: str,
    role: str,
    level: str,
    location: str,
    focus: list[str],
    start: str,
    end: str,
    allow_insufficient: bool,
    strict_window: bool,
) -> None:
    if not packet.evidence:
        raise ValueError("research packet contains no evidence; refusing to generate a rubric")
    if len(packet.evidence) > max_evidence:
        raise ValueError(f"research packet contains {len(packet.evidence)} evidence records; limit is {max_evidence}")
    if normalize_scope(packet.company) != normalize_scope(company) or canonical_role(packet.role) != canonical_role(
        role
    ):
        raise ValueError("research packet company or role does not match the request")
    if (canonical_level(packet.level), canonical_location(packet.location)) != (
        canonical_level(level),
        canonical_location(location),
    ):
        raise ValueError("research packet level or location does not match the request")
    requested_start = date.fromisoformat(start)
    requested_end = date.fromisoformat(end)
    packet_start = date.fromisoformat(packet.start_date)
    packet_end = date.fromisoformat(packet.end_date)
    if strict_window and (packet.start_date, packet.end_date) != (start, end):
        raise ValueError("fresh research packet date window does not match the request")
    if not strict_window and (packet_start > requested_start or packet_end > requested_end):
        raise ValueError("reused research packet extends outside the requested date window")
    if not strict_window and (requested_end - packet_end).days > 31:
        raise ValueError("reused research packet is older than the 31-day freshness allowance")
    if requested_start > requested_end or packet_start > packet_end:
        raise ValueError("research packet date window is reversed")
    requested_location = canonical_location(location)
    requested_level = canonical_level(level)
    for record in packet.evidence:
        if normalize_scope(record.company) != normalize_scope(company) or canonical_role(record.role) != canonical_role(
            role
        ):
            raise ValueError("research evidence company or role does not match the request")
        if canonical_level(record.level) not in {
            requested_level,
            "",
            "unspecified",
            "unknown",
        }:
            raise ValueError("research evidence level does not match the request")
        if not location_matches(record.location, requested_location):
            raise ValueError("research evidence location does not match the request")
        for observed_date in (record.published_date, record.interview_date):
            if observed_date and not packet.start_date <= observed_date <= packet.end_date:
                raise ValueError("research evidence date falls outside the requested window")
        if record.interview_date and record.interview_date_basis != "explicit_interview":
            raise ValueError("interview_date requires an explicit_interview date basis")
        if record.extraction_basis != "explicit_source_text" and (
            record.observed_questions_or_tasks or record.follow_ups_or_probes
        ):
            raise ValueError("observed questions and follow-ups require explicit_source_text extraction basis")
        if record.extraction_basis == "explicit_source_text" and not record.supporting_excerpt.strip():
            raise ValueError("explicit_source_text requires a non-empty supporting_excerpt")
        if not record.claim.strip() or not record.source_title.strip():
            raise ValueError("every research record must contain a source title and claim")
    evidence_ids = [record.evidence_id for record in packet.evidence]
    if len(evidence_ids) != len(set(evidence_ids)):
        raise ValueError("research packet contains duplicate evidence_id values")
    source_urls_by_id: dict[str, str] = {}
    source_ids_by_url: dict[str, str] = {}
    for record in packet.evidence:
        normalized_url = canonical_url(record.source_url)
        previous_url = source_urls_by_id.setdefault(record.source_id, normalized_url)
        if previous_url != normalized_url:
            raise ValueError(f"source_id {record.source_id!r} maps to multiple URLs")
        previous_id = source_ids_by_url.setdefault(normalized_url, record.source_id)
        if previous_id != record.source_id:
            raise ValueError(f"canonical URL maps to multiple source_ids: {normalized_url}")
    source_counts: dict[str, int] = {}
    for record in packet.evidence:
        source_counts[canonical_url(record.source_url)] = source_counts.get(canonical_url(record.source_url), 0) + 1
    if max(source_counts.values(), default=0) > 3:
        raise ValueError("a single source page contributes more than three evidence records")
    focus_entries = {normalize_scope(entry.focus): entry for entry in packet.focus_coverage}
    requested_focus = {normalize_scope(value) for value in focus}
    if set(focus_entries) != requested_focus:
        raise ValueError("focus_coverage must contain exactly one entry for every requested focus")
    known_evidence = set(evidence_ids)
    for entry in focus_entries.values():
        if not set(entry.evidence_ids) <= known_evidence:
            raise ValueError("focus_coverage contains an unknown evidence_id")
        if entry.status == "covered" and not entry.evidence_ids:
            raise ValueError("covered focus areas must cite evidence_ids")
        if entry.status != "covered" and entry.evidence_ids:
            raise ValueError("unsupported or not_found focus areas cannot cite evidence_ids")
    missing_focus = [entry.focus for entry in focus_entries.values() if entry.status != "covered"]
    if missing_focus and not any(
        focus.casefold() in gap.casefold() for gap in missing_focus for focus in packet.coverage_gaps
    ):
        raise ValueError("coverage_gaps must disclose requested focus areas without supporting evidence")
    clusters, first_hand_count = evidence_sufficiency(packet)
    if not allow_insufficient and (clusters < 2 or first_hand_count < 1):
        raise ValueError("insufficient evidence: need two first-hand independent clusters")


def validate_rubric(
    rubric: KnowledgeRubric,
    packet: ResearchPacket,
    *,
    company: str,
    role: str,
    level: str,
    location: str,
    allow_insufficient: bool,
) -> None:
    known_urls = {canonical_url(record.source_url) for record in packet.evidence}
    returned_urls = {canonical_url(url) for url in rubric.source_urls}
    if not returned_urls:
        raise ValueError("rubric contains no source URLs")
    if not returned_urls <= known_urls:
        unknown = sorted(returned_urls - known_urls)
        raise ValueError(f"rubric contains source URLs absent from the research packet: {unknown[:3]}")
    if normalize_scope(rubric.company) != normalize_scope(company) or canonical_role(rubric.role) != canonical_role(
        role
    ):
        raise ValueError("rubric company or role does not match the request")
    if canonical_level(rubric.level) != canonical_level(level) or canonical_location(
        rubric.location
    ) != canonical_location(location):
        raise ValueError("rubric level or location does not match the request")
    if not rubric.round_rubrics or not rubric.hard_gates or not rubric.evidence_capture_contract:
        raise ValueError("rubric is missing required evaluation controls")
    if len(rubric.round_rubrics) > 5 or len(rubric.scoring_scale) > 5 or len(rubric.seniority_calibration) > 5:
        raise ValueError("rubric exceeds bounded section limits")
    clusters, first_hand_count = evidence_sufficiency(packet)
    if (
        allow_insufficient
        and (clusters < 2 or first_hand_count < 1)
        and any(round_rubric.confidence == "high" for round_rubric in rubric.round_rubrics)
    ):
        raise ValueError("insufficient-evidence rubric cannot contain high-confidence rounds")
    for values, label in (
        (rubric.company_mindset, "company_mindset"),
        (rubric.role_signals, "role_signals"),
        (rubric.likely_process_variants, "likely_process_variants"),
        (rubric.observed_question_families, "observed_question_families"),
        (rubric.hard_gates, "hard_gates"),
        (rubric.preparation_priorities, "preparation_priorities"),
        (rubric.confidence_and_limits, "confidence_and_limits"),
        (rubric.evidence_capture_contract, "evidence_capture_contract"),
        (rubric.interviewer_protocol, "interviewer_protocol"),
        (rubric.anti_bias_checks, "anti_bias_checks"),
    ):
        if not values or len(values) > 5:
            raise ValueError(f"rubric field {label} must contain 1 to 5 items")
    for round_rubric in rubric.round_rubrics:
        if not round_rubric.evidence_ids:
            raise ValueError(f"rubric round {round_rubric.round_name!r} has no evidence_ids")
        for values in (
            round_rubric.dimensions,
            round_rubric.strong_evidence,
            round_rubric.weak_evidence,
            round_rubric.company_specific_probes,
            round_rubric.likely_question_families,
            round_rubric.evidence_ids,
        ):
            if len(values) > 3:
                raise ValueError("rubric round contains an unbounded list")
    known_evidence = {record.evidence_id for record in packet.evidence}
    for round_rubric in rubric.round_rubrics:
        if not set(round_rubric.evidence_ids) <= known_evidence:
            raise ValueError("rubric round contains an unknown evidence_id")
        if round_rubric.basis_type == "observed":
            cited = [record for record in packet.evidence if record.evidence_id in round_rubric.evidence_ids]
            if not any(record.extraction_basis == "explicit_source_text" for record in cited):
                raise ValueError(f"rubric round {round_rubric.round_name!r} is observed without explicit source text")


def safe_slug(value: str) -> str:
    slug = re.sub(r"[^a-z0-9]+", "_", value.casefold()).strip("_")
    if not slug:
        raise ValueError("company and role must contain at least one filename-safe character")
    return slug[:80]


def resolve_output(options: argparse.Namespace, request: dict) -> Path:
    if options.output:
        output = options.output.expanduser().resolve()
        root = OUTPUT_DIR.resolve()
        if root not in output.parents:
            raise ValueError(f"output must remain under {root}")
    else:
        request_hash = hashlib.sha256(json.dumps(request, sort_keys=True).encode()).hexdigest()[:10]
        output = OUTPUT_DIR / f"{safe_slug(options.company)}_{safe_slug(options.role)}_{request_hash}.json"
    if output.exists() and not options.overwrite:
        raise FileExistsError(f"output already exists: {output}; use --overwrite to replace it")
    return output


def atomic_write(output: Path, content: str, *, overwrite: bool) -> None:
    output.parent.mkdir(parents=True, exist_ok=True)
    with tempfile.NamedTemporaryFile("w", encoding="utf-8", dir=output.parent, delete=False) as temporary:
        temporary.write(content)
        temporary_path = Path(temporary.name)
    try:
        if overwrite:
            os.replace(temporary_path, output)
        else:
            os.link(temporary_path, output)
            temporary_path.unlink()
    finally:
        temporary_path.unlink(missing_ok=True)


def call_openai(
    client: OpenAI,
    *,
    model: str,
    system: str,
    user: str,
    schema: type[BaseModel],
    max_tokens: int,
    search_context_size: str = "low",
):
    request = {
        "model": model,
        "instructions": system,
        "input": user,
        "text": {
            "format": {
                "type": "json_schema",
                "name": schema.__name__.lower(),
                "description": "Strict structured interview intelligence artifact",
                "schema": schema.model_json_schema(),
                "strict": True,
            }
        },
        "max_output_tokens": max_tokens,
        "store": False,
    }
    if schema is ResearchPacket:
        request["tools"] = [{"type": "web_search", "search_context_size": search_context_size}]
        request["tool_choice"] = "required"
    response = client.responses.create(**request)
    if getattr(response, "status", "completed") != "completed":
        raise ValueError(f"OpenAI response incomplete: {getattr(response, 'status', 'unknown')}")
    if not response.output_text:
        raise ValueError("OpenAI returned no structured output")
    return schema.model_validate_json(response.output_text)


def call_sarvam(
    api_key: str,
    *,
    model: str,
    system: str,
    user: str,
    schema: type[BaseModel],
    max_tokens: int,
):
    response = httpx.post(
        "https://api.sarvam.ai/v1/chat/completions",
        headers={"api-subscription-key": api_key},
        json={
            "model": model,
            "messages": [
                {"role": "system", "content": system},
                {"role": "user", "content": user},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": schema.__name__,
                    "strict": True,
                    "schema": schema.model_json_schema(),
                },
            },
            "max_tokens": max_tokens,
            "temperature": 0.2,
        },
        timeout=180,
    )
    response.raise_for_status()
    body = response.json()
    choice = body["choices"][0]
    if choice.get("finish_reason") != "stop":
        raise ValueError(f"Sarvam response incomplete: {choice.get('finish_reason', 'unknown')}")
    content = choice["message"].get("content")
    if not content:
        raise ValueError("Sarvam returned an empty response")
    return schema.model_validate_json(content)


def run(options: argparse.Namespace) -> Path | None:
    start, end = window(options.months)
    queries = search_plan(options, start, end)
    if options.dry_run:
        print(
            json.dumps(
                {
                    "parameters": vars(options) | {"output": str(options.output) if options.output else None},
                    "queries": queries,
                },
                indent=2,
                default=str,
            )
        )
        return None

    load_dotenv(ROOT / "backend/.env")
    provider = options.provider
    legacy_model = options.model or os.getenv("INTERVIEW_KB_MODEL")
    defaults = {
        "openai": "gpt-4.1-mini",
        "sarvam": "sarvam-105b",
    }
    research_model = (
        options.research_model or os.getenv("INTERVIEW_KB_RESEARCH_MODEL") or legacy_model or defaults[provider]
    )
    synthesis_model = (
        options.synthesis_model
        or os.getenv("INTERVIEW_KB_SYNTHESIS_MODEL")
        or legacy_model
        or ("gpt-4.1-nano" if provider == "openai" else research_model)
    )
    research_tokens = options.max_output_tokens or options.research_output_tokens
    synthesis_tokens = options.max_output_tokens or options.synthesis_output_tokens
    if provider == "openai":
        if not os.getenv("OPENAI_API_KEY"):
            raise SystemExit("OPENAI_API_KEY is not configured in backend/.env or the environment.")
        client = OpenAI(api_key=os.environ["OPENAI_API_KEY"], timeout=180, max_retries=0)
        call = call_openai
    else:
        if not os.getenv("SARVAM_API_KEY"):
            raise SystemExit("SARVAM_API_KEY is not configured in backend/.env or the environment.")
        client = os.environ["SARVAM_API_KEY"]
        call = call_sarvam
    request = {
        "company": options.company,
        "role": options.role,
        "level": options.level,
        "location": options.location,
        "focus": options.focus,
        "date_window": {"start": start, "end": end},
        "search_queries": queries,
    }
    if options.research_packet:
        packet = ResearchPacket.model_validate_json(options.research_packet.read_text())
    elif provider == "sarvam":
        raise SystemExit(
            "--research-packet is required with --provider sarvam; Sarvam is used for synthesis, not web search."
        )
    else:
        research_kwargs = {
            "model": research_model,
            "system": instructions(start, end, options.max_evidence),
            "user": json.dumps(request, ensure_ascii=False),
            "schema": ResearchPacket,
            "max_tokens": research_tokens,
        }
        if provider == "openai":
            research_kwargs["search_context_size"] = options.search_context_size
        packet = call(client, **research_kwargs)
    packet = normalize_packet_source_ids(packet)
    packet = normalize_focus_coverage(packet, options.focus)
    validate_packet(
        packet,
        max_evidence=options.max_evidence,
        company=options.company,
        role=options.role,
        level=options.level,
        location=options.location,
        focus=options.focus,
        start=start,
        end=end,
        allow_insufficient=options.allow_insufficient_evidence,
        strict_window=options.research_packet is None,
    )
    synthesis_kwargs = {
        "model": synthesis_model,
        "system": synthesize_instructions(),
        "user": json.dumps(packet.model_dump(), ensure_ascii=False),
        "schema": KnowledgeRubric,
        "max_tokens": synthesis_tokens,
    }
    if provider == "openai":
        rubric = call_openai(client, **synthesis_kwargs)
    else:
        rubric = call(client, **synthesis_kwargs)
    rubric = normalize_rubric_confidence(rubric, packet, allow_insufficient=options.allow_insufficient_evidence)
    validate_rubric(
        rubric,
        packet,
        company=options.company,
        role=options.role,
        level=options.level,
        location=options.location,
        allow_insufficient=options.allow_insufficient_evidence,
    )
    output = resolve_output(options, request)
    independent_clusters, first_hand_count = evidence_sufficiency(packet)
    evidence_status = "insufficient_evidence" if independent_clusters < 2 or first_hand_count < 1 else "sufficient"
    artifact = {
        "metadata": {
            "pipeline_version": "1.0",
            "generated_at": datetime.now(UTC).date().isoformat(),
            "parameters": {
                "company": options.company,
                "role": options.role,
                "level": options.level,
                "location": options.location,
                "months": options.months,
                "focus": options.focus,
            },
            "provider": provider,
            "research_model": research_model,
            "synthesis_model": synthesis_model,
            "research_output_tokens": research_tokens,
            "synthesis_output_tokens": synthesis_tokens,
            "search_context_size": options.search_context_size,
            "allow_insufficient_evidence": options.allow_insufficient_evidence,
            "artifact_role": (
                "provisional_process_hypothesis" if evidence_status == "insufficient_evidence" else "grounded_rubric"
            ),
            "provenance_mode": "model_reported_unverified",
            "evidence_status": (evidence_status),
            "search_plan": queries,
            "search_execution": "provider_web_search_tool_for_openai; model-reported coverage is not treated as independent proof",
            "storage": "local_json_only",
        },
        "research_packet": packet.model_dump(mode="json"),
        "knowledge_and_rubric": rubric.model_dump(mode="json"),
    }
    atomic_write(
        output,
        json.dumps(artifact, ensure_ascii=False, indent=2) + "\n",
        overwrite=options.overwrite,
    )
    return output


if __name__ == "__main__":
    try:
        run(args())
    except APIError as exc:
        status = getattr(exc, "status_code", None)
        if status == 401:
            raise SystemExit("OpenAI request failed: the configured API key was rejected.") from None
        if status == 429:
            raise SystemExit(
                "OpenAI request failed: API quota or credits are unavailable; no artifact was written."
            ) from None
        raise SystemExit(f"OpenAI request failed with status {status or 'unknown'}; no artifact was written.") from None
    except (ValueError, ValidationError) as exc:
        raise SystemExit(
            f"Structured model output or local validation failed ({type(exc).__name__}): {exc}; no artifact was written."
        ) from None
    except (OSError, httpx.HTTPError) as exc:
        raise SystemExit(f"Pipeline stopped safely ({type(exc).__name__}): {exc}; no artifact was written.") from None
