"""Shared session brief and bounded live context. Exact transcript evidence stays in the DB."""

import re

from ..personas import interview_persona, public_persona
from ..schemas import CompanyBrief, CompanyIntelligence, InterviewBrief


def requested_language(body):
    # Language selection is retired; legacy request preferences cannot change output language.
    return "en-IN"


def brief_for(iv):
    stored = iv.plan.get("_brief")
    if stored:
        stored = {**stored, "language": "en-IN"}  # Normalize legacy interviews without mutating their plan.
        return InterviewBrief.model_validate(stored)
    return InterviewBrief(
        job_title=iv.job_title,
        company=iv.company,
        experience_years=iv.experience_years,
        job_description=iv.job_description,
        resume=iv.resume_snapshot,
        custom_instructions=iv.custom_instructions,
        language="en-IN",
        company_context=CompanyBrief(company=iv.company, status="not_requested"),
        company_intelligence=CompanyIntelligence(status="not_requested"),
    )


def relevant(text, query, limit):
    """Deterministic excerpt selection, never used for scoring evidence or transcript storage."""
    if len(text) <= limit:
        return text
    words = set(re.findall(r"\w+", query.lower()))
    chunks = [text[i : i + 700] for i in range(0, len(text), 700)]
    ranked = sorted(range(len(chunks)), key=lambda i: (-len(words & set(re.findall(r"\w+", chunks[i].lower()))), i))
    chosen = sorted(ranked[: max(1, (limit - 100) // 700)])
    return "[Selected context excerpts; complete source retained.]\n" + "\n[…]\n".join(chunks[i] for i in chosen)


def agent_context(iv, query="", evaluator=False):
    data = brief_for(iv).model_dump()
    data["resume"] = relevant(data["resume"], query, 3000)
    data["job_description"] = relevant(data["job_description"], query, 4000)
    data["company_context"].pop("search_suggestions", None)
    data["interview_profile"] = public_persona(interview_persona(iv)) if evaluator else interview_persona(iv)
    if evaluator:
        # Scoring receives no candidate preferences, resume claims, company prestige or search text.
        # The question/answer evidence and server-owned round define what can be assessed.
        return {key: data[key] for key in ("job_title", "experience_years", "language", "interview_profile")}
    data["preference_flags"] = preference_flags(data["custom_instructions"])
    if data["preference_flags"]:
        data["custom_instructions"] = ""
    return data


def preference_flags(text):
    """Advisory guard; not an injection firewall. Raw preferences never enter evaluation."""
    manipulation = re.search(
        r"(?:ignore|override|bypass).{0,50}(?:rubric|scor|grad|instruct)|"
        r"(?:give|award|ensure|return|output).{0,35}(?:100|perfect|strong.hire|full.mark)|"
        r"(?:increase|inflate|change|alter).{0,25}(?:score|grade|verdict)|"
        r"(?:पूरे|पूर्ण).{0,10}अंक|100.{0,10}(?:अंक|दो)",
        text,
        re.IGNORECASE,
    )
    return ["grading_manipulation"] if manipulation else []


def live_context(iv, turns, answer, remaining):
    current = turns[-1]
    untimed = iv.plan.get("_mode") == "text"
    data = agent_context(iv, current.question)
    # Current topic is at most two answered follow-ups; older topics only contribute a coverage map.
    recent = [t for t in turns if t.topic == current.topic][-3:]
    history = [
        {
            "question": t.question,
            "answer": relevant(t.answer, current.question, 2400) if t.answer else None,
            "topic": t.topic,
        }
        for t in recent
    ]
    bank = iv.plan["question_bank"]
    visited = set(iv.plan.get("_visited_topics", list(range(iv.current_topic + 1))))
    available = [
        {"index": i, "topic": q["topic"], "question": q["question"]} for i, q in enumerate(bank) if i not in visited
    ]
    data.update(
        history=history,
        answer=answer,
        remaining_seconds=None if untimed else remaining,
        followups=iv.followup_count,
        covered_topics=[q["topic"] for i, q in enumerate(bank) if i in visited and i != iv.current_topic],
        current_topic=iv.current_topic,
        answer_id=current.id,
        candidate_memory=iv.plan.get("_memory", []),
        remaining_topics=available,
        finish_allowed=untimed or remaining <= 180,
        target_seconds_per_topic=None if untimed else round(remaining / (len(available) + 1)),
    )
    return data


# Service-owned English closing copy.
CLOSINGS = {
    "en-IN": "Thank you for your answers. This practice interview is complete. Let's review what to work on next."
}
