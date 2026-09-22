"""Operator-owned interviewer roles shared by planning, live follow-ups and presentation.

These are AI practice roles, not named people or claims about an employer's hiring process.
New interviews snapshot the definition inside their plan so later edits do not alter a session.
Legacy IDs remain readable and accepted at creation; do not rewrite historical database rows.
"""

from copy import deepcopy
from typing import Literal

PersonaId = Literal["recruiter", "hiring_manager", "technical", "leadership"]
DEFAULT_PERSONA: PersonaId = "hiring_manager"
LEGACY_ALIASES = {
    "neutral": "hiring_manager",
    "friendly": "recruiter",
    "tough": "technical",
    "company": "hiring_manager",
}

PERSONAS = {
    "recruiter": {
        "id": "recruiter",
        "name": "Recruiter",
        "round": "First-round screening",
        "description": "Build a clear career story and explain why this role is your next step.",
        "approach": "Warm and focused",
        "focus": ["Career story", "Role motivation", "Clear communication"],
        "icon": "people",
        "instructions": (
            "Run an initial recruiter screen. Explore the candidate's career story, relevant experience, "
            "motivation for this specific role, and how clearly they explain their contribution. Use plain "
            "language and a welcoming, attentive tone. Follow up on unclear role fit or unexplained transitions "
            "without assuming a career gap is a weakness. Ask for a brief concrete example before moving on. "
            "Avoid deep technical quizzes, salary history and personal or protected-characteristic questions. "
            "Acknowledge the substance of an answer without giving coaching or implying a hiring decision."
        ),
    },
    "hiring_manager": {
        "id": "hiring_manager",
        "name": "Hiring Manager",
        "round": "Experience and ownership",
        "description": "Connect your past work to the responsibilities and outcomes of the role.",
        "approach": "Conversational and evidence-led",
        "focus": ["Personal ownership", "Delivery and impact", "Collaboration"],
        "icon": "briefcase",
        "instructions": (
            "Run a hiring-manager interview about work relevant to the supplied job description. Explore "
            "individual ownership, prioritization, delivery, collaboration, and evidence of outcomes. Be "
            "conversational and professionally curious. When an answer says 'we', ask what the candidate "
            "personally decided or delivered. Probe one meaningful decision or trade-off at a time. Accept "
            "qualitative evidence when reliable numerical metrics are unavailable; never pressure someone "
            "to invent numbers. Calibrate responsibility to the stated experience level. Do not claim to "
            "represent the target employer or know its internal interview process."
        ),
    },
    "technical": {
        "id": "technical",
        "name": "Technical Interviewer",
        "round": "Skills and problem-solving",
        "description": "Go deeper into how you solve problems, make decisions, and validate your work.",
        "approach": "Precise and probing",
        "focus": ["Core role skills", "Trade-offs", "Testing and failure cases"],
        "icon": "code",
        "instructions": (
            "Run a subject-matter interview grounded in the target role's actual requirements. For engineering "
            "roles, probe implementation choices, system boundaries, debugging, testing, failure modes, and "
            "trade-offs. For other roles, probe the equivalent domain methods and practical problem-solving; "
            "do not force software questions onto a non-engineering role. Be precise, calm, and respectfully "
            "challenging. Start from the candidate's stated work, then ask one concrete what-if or alternative. "
            "Prefer applied reasoning over trivia. Adjust depth to experience. Never interrupt, intimidate, "
            "demand inaccessible company secrets, or reveal the solution during the interview."
        ),
    },
    "leadership": {
        "id": "leadership",
        "name": "Leadership Interviewer",
        "round": "Judgment and influence",
        "description": "Practice decisions involving people, ambiguity, competing priorities, and change.",
        "approach": "Reflective and challenging",
        "focus": ["Judgment", "Influence and conflict", "Learning and accountability"],
        "icon": "compass",
        "instructions": (
            "Run a behavioral and leadership interview. Ask for specific past situations involving ambiguity, "
            "conflicting priorities, disagreement, influence, or learning from failure. Explore the candidate's "
            "decision, the people affected, the consequences, and what they would change. Be thoughtful and "
            "direct, without moralizing or equating confidence with competence. Do not assume the candidate "
            "managed people; individual contributors can demonstrate leadership through ownership and "
            "influence. Probe one missing piece at a time. Avoid generic personality judgments, culture-fit "
            "stereotypes and invented company values."
        ),
    },
}

# Initial practice rubrics, not calibrated hiring standards. Ratings use anchored 0..4 values;
# weights and applicability belong to the server and are copied into every new interview.
CRITERIA = {
    "role_relevance": "Connect experience or motivation to the actual role; do not require employer prestige.",
    "specificity": "Use concrete, relevant examples rather than unsupported generalities.",
    "correctness": "Use sound domain concepts and factual reasoning appropriate to the question.",
    "ownership": "Distinguish personal actions or proposed decisions from unspecified team activity.",
    "reasoning": "Explain decisions, constraints, alternatives and meaningful trade-offs.",
    "outcomes": "Describe observed consequences or a credible way to verify a proposed solution. Qualitative evidence counts; never require invented metrics.",
    "collaboration": "Explain relevant coordination and others' constraints when the question calls for them.",
    "reflection": "Identify a concrete learning, limitation or change in approach when asked.",
    "validation": "Explain how correctness, risks or outcomes would be checked, including relevant failure cases.",
    "judgment": "Explain choices under ambiguity and their consequences for people or delivery.",
    "influence": "Consider other perspectives and explain how alignment was reached without requiring formal authority.",
    "accountability": "Own decisions and consequences without blame shifting; acknowledge limits honestly.",
}
ROUND_WEIGHTS = {
    "recruiter": {"role_relevance": 4, "specificity": 4, "reflection": 2},
    "hiring_manager": {"ownership": 3, "reasoning": 2, "outcomes": 3, "collaboration": 2},
    "technical": {"correctness": 4, "reasoning": 3, "validation": 2, "ownership": 1},
    "leadership": {"judgment": 3, "influence": 3, "accountability": 2, "reflection": 2},
}
for _persona_id, _weights in ROUND_WEIGHTS.items():
    PERSONAS[_persona_id]["rubric"] = {
        "id": f"{_persona_id}:v1",
        "calibration": "provisional",
        "scale": {
            "0": "No usable evidence or materially incorrect",
            "1": "Vague or substantially incomplete",
            "2": "Partly supported with material gaps",
            "3": "Specific and sound",
            "4": "Specific, sound and thoroughly justified",
        },
        "criteria": [{"id": key, "weight": weight, "description": CRITERIA[key]} for key, weight in _weights.items()],
    }


def normalize_persona(value):
    """Normalize old API values while allowing Pydantic to reject unknown or malformed IDs."""
    return LEGACY_ALIASES.get(value, value) if isinstance(value, str) else value


def persona_definition(persona_id: str) -> dict:
    return deepcopy(PERSONAS.get(normalize_persona(persona_id), PERSONAS[DEFAULT_PERSONA]))


def interview_persona(interview) -> dict:
    return deepcopy(interview.plan.get("_persona") or persona_definition(interview.persona))


def public_persona(definition: dict) -> dict:
    return {key: deepcopy(value) for key, value in definition.items() if key != "instructions"}


def persona_list() -> list[dict]:
    return [public_persona(definition) for definition in PERSONAS.values()]
