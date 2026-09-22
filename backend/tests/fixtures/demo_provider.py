"""Deterministic fixtures for automated tests only. Never an interview assessment."""

from app.providers.base import Completion


class DemoProvider:
    def generate(self, profile, system, payload, schema):
        name = schema.__name__
        if name == "Plan":
            role = payload.get("job_title", "engineer")
            data = {
                "focus_areas": ["Project depth", "System design", "Collaboration"],
                "question_bank": [
                    {
                        "topic": "Project depth",
                        "question": f"Tell me about a project that prepared you for this {role} role. What did you own?",
                        "why": "Understand individual contribution.",
                    },
                    {
                        "topic": "System design",
                        "question": "Describe a technical trade-off you made. How did you measure whether it worked?",
                        "why": "Evaluate reasoning and evidence.",
                    },
                    {
                        "topic": "Collaboration",
                        "question": "Tell me about a disagreement with a teammate and how you resolved it.",
                        "why": "Explore collaboration.",
                    },
                ],
                "opening": f"Welcome. Let's practice for your {role} interview. Tell me about a recent project and what you personally owned.",
            }
            target = payload.get("question_count", {}).get("minimum", 3)
            while len(data["question_bank"]) < target:
                index = len(data["question_bank"])
                data["question_bank"].append(
                    {
                        "topic": f"Practice area {index + 1}",
                        "question": f"Describe a different decision about reliability in area {index + 1}.",
                        "why": "Exercise distinct coverage in test fixtures.",
                    }
                )
        elif name == "InterviewDecision":
            specific = len(payload.get("answer", "").split()) >= 25
            data = {
                "action": "advance" if specific else "follow_up",
                "reply": "What specifically did you decide, and how did you check the outcome?" if not specific else "",
                "transition": "Let's explore another part of your experience." if specific else "",
                "next_topic": payload.get("remaining_topics", [{}])[0].get("index")
                if specific and payload.get("remaining_topics")
                else None,
                "memory_updates": [{"answer_id": payload["answer_id"], "quote": payload["answer"][:180]}],
            }
        elif name == "TopicAssessment":
            turns = payload["turns"]
            specific = sum(len(t["answer"].split()) for t in turns) >= 25
            data = {
                "topic": payload["topic"],
                "answer_summary": " ".join(t["answer"] for t in turns)[:800],
                "feedback": "Explain your decision, an alternative, and how you checked the outcome.",
                "ideal_answer": "Describe the situation, your choice, a trade-off and the observed or proposed validation.",
                "ratings": [
                    {
                        "criterion": c["id"],
                        "score": 3 if specific else 1,
                        "reason": "Synthetic fixture rating for workflow verification.",
                        "evidence_indices": [0],
                    }
                    for c in payload["rubric"]["criteria"]
                ],
                "evidence": [{"answer_id": turns[0]["answer_id"], "quote": turns[0]["answer"][:150]}],
            }
        elif name == "EvidenceReportSummary":
            samples = payload["communication_samples"]
            sufficient = sum(len(t["answer"].strip()) for t in samples) >= 80
            data = {
                "summary": "Synthetic test report; use live providers for actual practice feedback.",
                "strengths": ["You provided an answer."],
                "gaps": ["Explain a concrete decision and validation."],
                "communication": {
                    "clarity": 6 if sufficient else None,
                    "structure": 6 if sufficient else None,
                    "notes": "Fixture values based on bounded wording samples; voice delivery is not measured.",
                    "evidence": [
                        {
                            "dimension": dimension,
                            "answer_id": samples[0]["answer_id"],
                            "quote": samples[0]["answer"][:150],
                        }
                        for dimension in ("clarity", "structure")
                    ]
                    if sufficient
                    else [],
                },
                "drill_next": ["Practice a decision and its validation."],
            }
        elif name == "SkillCoachingPlan":
            data = {
                "tasks": [
                    {
                        "title": "Explain a technical trade-off",
                        "skill_id": "trade_offs",
                        "exercise_type": "compare_options",
                        "instructions": "Compare two approaches to a past problem. Explain your constraints and how to check the result.",
                        "minutes": 15,
                    },
                    {
                        "title": "Practice an ownership story",
                        "skill_id": "ownership",
                        "exercise_type": "timed_story",
                        "instructions": "Tell a two-minute story about one decision you owned. Identify your action and supporting evidence.",
                        "minutes": 10,
                    },
                ]
            }
        elif name == "TurnDecision":
            specific = len(payload.get("answer", "").split()) >= 25
            data = {
                "assessment": "Demo assessment: add your actions, a trade-off, and measurable evidence.",
                "action": "advance" if specific else "follow_up",
                "reply": "What specifically did you do, and how did you measure the outcome?",
            }
        elif name == "TopicEvaluation":
            turns = payload["turns"]
            specific = sum(len(t["answer"].split()) for t in turns) >= 25
            data = {
                "topic": payload["topic"],
                "answer_summary": " ".join(t["answer"] for t in turns)[:800],
                "feedback": "Name your decision, an alternative, and the observed result.",
                "ideal_answer": "Explain the context, your individual action, a trade-off and the observed outcome.",
                "rubric": {
                    "correctness": 2,
                    "ownership": 2 if specific else 1,
                    "reasoning": 2 if specific else 1,
                    "outcomes": 1 if specific else 0,
                },
                "evidence": [{"answer_id": turns[0]["answer_id"], "quote": turns[0]["answer"][:150]}],
            }
        elif name == "ReportSummary":
            data = {
                "summary": "Demo fixture: practice explaining your decisions and evidence clearly.",
                "strengths": ["You completed a deliberate practice session."],
                "gaps": ["Make your individual contribution and results specific."],
                "communication": {
                    "clarity": 6,
                    "structure": 6,
                    "confidence": 6,
                    "notes": "Demo values describe wording. Voice, accent, body language and hiring probability are not assessed.",
                },
                "drill_next": ["Practice a two-minute project story with a concrete trade-off and outcome."],
            }
        elif name == "Report":
            grouped = {}
            for turn in payload["turns"]:
                grouped.setdefault(turn["topic"], []).append(turn)
            questions = []
            for topic, turns in grouped.items():
                words = sum(len((t.get("answer") or "").split()) for t in turns)
                questions.append(
                    {
                        "topic": topic,
                        "question": turns[0]["question"],
                        "answer_summary": " ".join(t["answer"] for t in turns)[:800],
                        "score": 7 if words >= 25 else 4,
                        "feedback": "Name your decision, the alternative you rejected, and the observed result.",
                        "ideal_answer": "Explain the context, your individual action, a trade-off, and a measurable outcome.",
                        "evidence": [turns[0]["answer"][:150]],
                    }
                )
            data = {
                "overall_score": 60,
                "verdict": "lean_hire",
                "verdict_reason": "Demo fixture, not a real hiring prediction.",
                "summary": "This is a sample report from the deterministic demo provider. Select a configured AI provider for personalized feedback.",
                "strengths": ["You completed a deliberate practice session."],
                "gaps": ["Make your individual contribution and results specific."],
                "questions": questions,
                "communication": {
                    "clarity": 6,
                    "structure": 6,
                    "confidence": 6,
                    "notes": "Demo values. Delivery and vocal confidence are not measured.",
                },
                "drill_next": ["Practice a two-minute project story with a concrete trade-off and outcome."],
            }
        elif name == "CoachingPlan":
            data = {
                "tasks": [
                    {
                        "title": "Make your project story specific",
                        "instructions": "Record a two-minute answer: situation, your action, an alternative, and a measurable result. Repeat once without notes.",
                        "skill": "Project depth",
                        "minutes": 15,
                    },
                    {
                        "title": "Explain one engineering trade-off",
                        "instructions": "Choose two designs from a recent project. Compare latency, cost, and operational complexity, then defend your choice.",
                        "skill": "System design",
                        "minutes": 20,
                    },
                ]
            }
        elif name == "ResumeDigest":
            text = payload.get("text", "")
            data = {
                "candidate_name": text.splitlines()[0][:100] if text else "Candidate",
                "summary": "Demo resume digest. Switch provider for a semantic analysis.",
                "digest": text[:10000] or "No readable content.",
            }
        elif name == "Titles":
            title = payload.get("job_title", "Software Engineer")
            data = {"titles": [f"Senior {title}", "Backend Engineer", "AI Engineer"][:3]}
        elif name == "JobDescriptionDraft":
            data = {
                "role_summary": "This is a deterministic sample for testing the setup workflow. It does not describe the target employer or provide a role-specific hiring assessment.",
                "responsibilities": [
                    "Define a scoped deliverable and agree on acceptance criteria with the relevant stakeholders.",
                    "Investigate an ambiguous problem and document the assumptions behind the proposed approach.",
                    "Produce and review the work artifacts needed to deliver the agreed scope reliably.",
                    "Identify likely failure cases and explain how they will be detected and addressed.",
                    "Document decisions and hand over completed work with clear operational guidance.",
                ],
                "requirements": [
                    "Explain a relevant project and distinguish your contribution from the team's work.",
                    "Compare alternative approaches using evidence appropriate to the role.",
                    "Communicate assumptions, limitations and open questions clearly.",
                    "Show how you review the quality of your work and incorporate feedback.",
                ],
                "preferred": [
                    "Experience presenting a completed project to stakeholders outside your immediate team.",
                    "Examples of improving a repeated process and explaining the observed impact.",
                ],
                "early_outcomes": [
                    "Deliver a scoped improvement and review it against agreed acceptance criteria.",
                    "Document one recurring failure mode and propose an evidence-based improvement.",
                ],
            }
        else:
            raise ValueError(f"No demo fixture for {name}")
        return Completion(data)
