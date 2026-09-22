"""Shared session brief and bounded live context. Exact transcript evidence stays in the DB."""

import re

from ..personas import interview_persona, public_persona
from ..schemas import CompanyBrief, InterviewBrief

LANGUAGES = {
    "en-IN": "English",
    "hi-IN": "Hindi",
    "bn-IN": "Bengali",
    "ta-IN": "Tamil",
    "te-IN": "Telugu",
    "gu-IN": "Gujarati",
    "kn-IN": "Kannada",
    "ml-IN": "Malayalam",
    "mr-IN": "Marathi",
    "pa-IN": "Punjabi",
    "od-IN": "Odia",
}


def requested_language(body):
    # Preserve old clients that expressed a supported language in free-text preferences.
    if "language" in body.model_fields_set:
        return body.language
    for code, name in LANGUAGES.items():
        if re.search(r"\b(?:in|speak|use)\s+" + name + r"\b", body.custom_instructions, re.IGNORECASE):
            return code
    return body.language


def brief_for(iv):
    stored = iv.plan.get("_brief")
    if stored:
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
        remaining_seconds=remaining,
        followups=iv.followup_count,
        covered_topics=[q["topic"] for i, q in enumerate(bank) if i in visited and i != iv.current_topic],
        current_topic=iv.current_topic,
        answer_id=current.id,
        candidate_memory=iv.plan.get("_memory", []),
        remaining_topics=available,
        finish_allowed=remaining <= 180,
        target_seconds_per_topic=round(remaining / (len(available) + 1)),
    )
    return data


# Service-owned closing copy keeps the final spoken turn in the saved interview language.
CLOSINGS = {
    "en-IN": "Thank you for your answers. This practice interview is complete. Let's review what to work on next.",
    "hi-IN": "आपके जवाबों के लिए धन्यवाद। यह अभ्यास इंटरव्यू पूरा हो गया है। अब आपकी फीडबैक रिपोर्ट देखते हैं।",
    "bn-IN": "আপনার উত্তরগুলোর জন্য ধন্যবাদ। অনুশীলনমূলক সাক্ষাৎকার শেষ হয়েছে। এবার আপনার মূল্যায়নের প্রতিবেদন দেখুন।",
    "ta-IN": "உங்கள் பதில்களுக்கு நன்றி. பயிற்சி நேர்காணல் முடிந்தது. இப்போது உங்கள் மதிப்பீட்டு அறிக்கையைப் பார்க்கலாம்.",
    "te-IN": "మీ సమాధానాలకు ధన్యవాదాలు. ఈ అభ్యాస ఇంటర్వ్యూ పూర్తయింది. ఇప్పుడు మీ మూల్యాంకన నివేదికను చూద్దాం.",
    "gu-IN": "તમારા જવાબો માટે આભાર. અભ્યાસ માટેનો ઇન્ટરવ્યૂ પૂર્ણ થયો છે. હવે તમારો પ્રતિસાદ અહેવાલ જોઈએ.",
    "kn-IN": "ನಿಮ್ಮ ಉತ್ತರಗಳಿಗೆ ಧನ್ಯವಾದಗಳು. ಅಭ್ಯಾಸ ಸಂದರ್ಶನ ಮುಗಿದಿದೆ. ಈಗ ನಿಮ್ಮ ಮೌಲ್ಯಮಾಪನ ವರದಿಯನ್ನು ನೋಡೋಣ.",
    "ml-IN": "നിങ്ങളുടെ ഉത്തരങ്ങൾക്ക് നന്ദി. പരിശീലന അഭിമുഖം പൂർത്തിയായി. ഇനി നിങ്ങളുടെ വിലയിരുത്തൽ റിപ്പോർട്ട് നോക്കാം.",
    "mr-IN": "तुमच्या उत्तरांसाठी धन्यवाद. सराव मुलाखत पूर्ण झाली आहे. आता तुमचा अभिप्राय अहवाल पाहूया.",
    "pa-IN": "ਤੁਹਾਡੇ ਜਵਾਬਾਂ ਲਈ ਧੰਨਵਾਦ। ਅਭਿਆਸ ਇੰਟਰਵਿਊ ਪੂਰੀ ਹੋ ਗਈ ਹੈ। ਹੁਣ ਤੁਹਾਡੀ ਫੀਡਬੈਕ ਰਿਪੋਰਟ ਵੇਖੀਏ।",
    "od-IN": "ଆପଣଙ୍କ ଉତ୍ତର ପାଇଁ ଧନ୍ୟବାଦ। ଅଭ୍ୟାସ ସାକ୍ଷାତକାର ସମାପ୍ତ ହୋଇଛି। ଏବେ ଆପଣଙ୍କ ମୂଲ୍ୟାଙ୍କନ ରିପୋର୍ଟ ଦେଖିବା।",
}
