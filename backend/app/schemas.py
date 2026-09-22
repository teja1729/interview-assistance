"""Strict API and agent contracts. Never persist unvalidated model output."""

import ipaddress
from typing import Annotated, Literal
from urllib.parse import urlsplit

from pydantic import BaseModel, ConfigDict, Field, field_validator

from .personas import DEFAULT_PERSONA, PersonaId, normalize_persona


class Contract(BaseModel):
    model_config = ConfigDict(extra="forbid", strict=True)


Language = Literal["en-IN", "hi-IN", "bn-IN", "ta-IN", "te-IN", "gu-IN", "kn-IN", "ml-IN", "mr-IN", "pa-IN", "od-IN"]
Nonempty = Annotated[str, Field(min_length=1, max_length=1200, pattern=r"\S")]


class Source(Contract):
    id: str
    title: str = Field(max_length=300)
    url: str = Field(max_length=3000)


class CompanyFact(Contract):
    text: str = Field(min_length=1, max_length=1200)
    source_ids: list[str] = Field(min_length=1, max_length=8)


class CompanyBrief(Contract):
    company: str
    status: Literal["researched", "unavailable", "not_requested"]
    facts: list[CompanyFact] = Field(default_factory=list, max_length=8)
    sources: list[Source] = Field(default_factory=list, max_length=8)
    researched_at: float | None = None
    note: str = ""
    cached: bool = False
    search_suggestions: str = Field(default="", max_length=50000)


def public_company_url(value):
    if not value:
        return ""
    parsed = urlsplit(value)
    host = parsed.hostname or ""
    if parsed.scheme != "https" or not host or parsed.username or parsed.password or parsed.port not in {None, 443}:
        raise ValueError("Use a public HTTPS company or job URL")
    if "." not in host or host.endswith((".local", ".internal", ".localhost")):
        raise ValueError("Use a public company domain")
    try:
        address = ipaddress.ip_address(host)
    except ValueError:
        address = None
    if address is not None:
        raise ValueError("Use a company domain, not an IP address")
    return value


class CompanyResearchInput(BaseModel):
    company: str = Field(min_length=2, max_length=150)
    job_title: str = Field(min_length=2, max_length=150)
    company_url: str = Field(default="", max_length=2000)
    force_refresh: bool = False
    _url = field_validator("company_url")(public_company_url)


class InterviewBrief(Contract):
    job_title: str
    company: str
    experience_years: int
    job_description: str
    resume: str
    custom_instructions: str
    language: Language
    company_context: CompanyBrief


class Question(Contract):
    topic: str = Field(min_length=1, max_length=120)
    question: str = Field(min_length=5, max_length=1500)
    why: str = Field(min_length=1, max_length=1000)


class Plan(Contract):
    focus_areas: list[str] = Field(min_length=1, max_length=12)
    question_bank: list[Question] = Field(min_length=2, max_length=15)
    opening: str = Field(min_length=5, max_length=1500)


class TurnDecision(Contract):
    assessment: str = Field(min_length=1, max_length=2000)
    action: Literal["follow_up", "advance", "finish"]
    reply: str = Field(min_length=1, max_length=1500)


class Rubric(Contract):
    correctness: int = Field(ge=0, le=3)
    ownership: int = Field(ge=0, le=3)
    reasoning: int = Field(ge=0, le=2)
    outcomes: int = Field(ge=0, le=2)


class EvidenceQuote(Contract):
    answer_id: str = Field(min_length=1, max_length=80)
    quote: Nonempty


class MemoryQuote(EvidenceQuote):
    """A candidate claim, never a verified external fact or an evaluator judgment."""

    quote: str = Field(min_length=1, max_length=280, pattern=r"\S")


class InterviewDecision(Contract):
    """Revision 3 live proposal. The service validates coverage, memory and completion."""

    action: Literal["follow_up", "advance", "finish"]
    reply: str = Field(max_length=1000)
    transition: str = Field(max_length=180)
    next_topic: int | None = Field(ge=0, le=14)
    memory_updates: list[MemoryQuote] = Field(max_length=3)


class CriterionRating(Contract):
    criterion: str = Field(min_length=1, max_length=40)
    score: int | None = Field(ge=0, le=4)
    reason: str = Field(min_length=1, max_length=420, pattern=r"\S")
    evidence_indices: list[Annotated[int, Field(ge=0, le=4)]] = Field(max_length=2)


class TopicAssessment(Contract):
    """Scores are normalized ratings; the server owns weights and applicability checks."""

    topic: int = Field(ge=0, le=14)
    answer_summary: Nonempty
    feedback: Nonempty
    ideal_answer: str = Field(min_length=1, max_length=1800)
    # Generate evidence first so ratings reference an already constructed list.
    evidence: list[EvidenceQuote] = Field(min_length=1, max_length=5)
    ratings: list[CriterionRating] = Field(min_length=1, max_length=6)


class CommunicationEvidence(EvidenceQuote):
    dimension: Literal["clarity", "structure"]


class CommunicationAssessment(Contract):
    clarity: int | None = Field(ge=0, le=10)
    structure: int | None = Field(ge=0, le=10)
    notes: Nonempty
    evidence: list[CommunicationEvidence] = Field(max_length=6)


class EvidenceReportSummary(Contract):
    summary: Nonempty
    strengths: list[Nonempty] = Field(max_length=5)
    gaps: list[Nonempty] = Field(max_length=5)
    communication: CommunicationAssessment
    drill_next: list[Nonempty] = Field(min_length=1, max_length=5)


SkillId = Literal[
    "technical_reasoning",
    "trade_offs",
    "validation",
    "debugging",
    "ownership",
    "outcomes",
    "communication",
    "role_alignment",
    "collaboration",
    "leadership",
    "reflection",
]
ExerciseType = Literal[
    "worked_example", "compare_options", "failure_analysis", "timed_story", "role_pitch", "reflection"
]


class SkillDrill(Contract):
    title: str = Field(min_length=3, max_length=200)
    instructions: str = Field(min_length=10, max_length=2000)
    skill_id: SkillId
    exercise_type: ExerciseType
    minutes: int = Field(ge=5, le=60)


class SkillCoachingPlan(Contract):
    tasks: list[SkillDrill] = Field(min_length=1, max_length=5)


class TopicEvaluation(Contract):
    topic: int = Field(ge=0, le=14)
    answer_summary: Nonempty
    feedback: Nonempty
    ideal_answer: str = Field(min_length=1, max_length=1800)
    rubric: Rubric
    evidence: list[EvidenceQuote] = Field(min_length=1, max_length=3)


class QuestionFeedback(Contract):
    topic: int = Field(ge=0, le=14)
    question: str
    answer_summary: str
    score: int = Field(ge=0, le=10)
    feedback: str
    ideal_answer: str
    evidence: list[str] = Field(max_length=5)
    evidence_refs: list[EvidenceQuote] = Field(default_factory=list, max_length=3)
    rubric: Rubric | None = None


class Communication(Contract):
    clarity: int = Field(ge=0, le=10)
    structure: int = Field(ge=0, le=10)
    confidence: int = Field(ge=0, le=10)
    notes: str = Field(min_length=1, max_length=1200)


class ReportSummary(Contract):
    summary: Nonempty
    strengths: list[Nonempty] = Field(max_length=5)
    gaps: list[Nonempty] = Field(max_length=5)
    communication: Communication
    drill_next: list[Nonempty] = Field(min_length=1, max_length=5)


class Report(Contract):
    overall_score: int = Field(ge=0, le=100)
    verdict: Literal["strong_hire", "hire", "lean_hire", "no_hire"]
    verdict_reason: str
    summary: str
    strengths: list[str] = Field(max_length=10)
    gaps: list[str] = Field(max_length=10)
    questions: list[QuestionFeedback] = Field(min_length=1, max_length=15)
    communication: Communication
    drill_next: list[str] = Field(min_length=1, max_length=5)


class RubricCriterion(Contract):
    id: str
    weight: int = Field(ge=1, le=10)
    description: str


class RoundRubric(Contract):
    id: str
    calibration: Literal["provisional", "validated"]
    scale: dict[str, str]
    criteria: list[RubricCriterion] = Field(min_length=1, max_length=6)


class AssessedQuestion(Contract):
    topic: int = Field(ge=0, le=14)
    question: str
    answer_summary: str
    score: float | None = Field(ge=0, le=10)
    feedback: str
    ideal_answer: str
    evidence: list[str] = Field(max_length=5)
    evidence_refs: list[EvidenceQuote] = Field(max_length=5)
    rubric: dict[str, int | None]
    ratings: list[CriterionRating]


class PracticeReport(EvidenceReportSummary):
    overall_score: int | None = Field(ge=0, le=100)
    verdict: Literal["strong_hire", "hire", "lean_hire", "no_hire", "insufficient_evidence"]
    verdict_reason: str
    questions: list[AssessedQuestion] = Field(min_length=1, max_length=15)
    rubric_definition: RoundRubric
    assessment_version: Literal[3]


class Drill(Contract):
    title: str = Field(min_length=3, max_length=200)
    instructions: str = Field(min_length=10, max_length=2000)
    skill: str = Field(min_length=1, max_length=100)
    minutes: int = Field(ge=5, le=60)


class CoachingPlan(Contract):
    tasks: list[Drill] = Field(min_length=1, max_length=5)


class ResumeDigest(Contract):
    candidate_name: str
    summary: str
    digest: str = Field(min_length=10, max_length=12000)


class Titles(Contract):
    titles: list[str] = Field(min_length=1, max_length=4)


JobDetail = Annotated[str, Field(min_length=20, max_length=360)]


class JobDescriptionDraft(Contract):
    """A complete role brief; the service renders these sections into editable text."""

    role_summary: str = Field(min_length=80, max_length=800)
    responsibilities: list[JobDetail] = Field(min_length=5, max_length=7)
    requirements: list[JobDetail] = Field(min_length=4, max_length=6)
    preferred: list[JobDetail] = Field(min_length=2, max_length=3)
    early_outcomes: list[JobDetail] = Field(min_length=2, max_length=3)


class Transcript(Contract):
    text: str = Field(max_length=16000)


class InterviewCreate(BaseModel):
    job_title: str = Field(min_length=2, max_length=150)
    company: str = Field(default="", max_length=150)
    experience_years: int = Field(default=0, ge=0, le=50)
    job_description: str = Field(default="", max_length=16000)
    custom_instructions: str = Field(default="", max_length=2000)
    duration_minutes: int = Field(default=30, ge=5, le=60)
    persona: PersonaId = DEFAULT_PERSONA
    resume_id: str | None = None
    language: Language = "en-IN"
    company_url: str = Field(default="", max_length=2000)
    company_research_id: str | None = None
    _url = field_validator("company_url")(public_company_url)

    @field_validator("persona", mode="before")
    @classmethod
    def resolve_legacy_persona(cls, value):
        return normalize_persona(value)


class TextTurn(BaseModel):
    text: str = Field(min_length=1, max_length=16000)
    version: int = Field(ge=0)
    request_id: str = Field(min_length=16, max_length=80)
