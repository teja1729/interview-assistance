"""Offline case validation or deliberately paid, reproducible model judgment regressions.

No private application database or candidate data is read. The disposable trace database is
owned by this run. Expected scores are provisional until a human reviews the reference cases.
"""

import argparse
import hashlib
import json
import logging
import statistics
import tempfile
import time
from pathlib import Path
from types import SimpleNamespace

from sqlmodel import Session, SQLModel, select

from app import db
from app.agents import specs
from app.agents.runtime import execute
from app.models import AgentRun, User, Workspace
from app.personas import persona_definition, public_persona
from app.providers.base import agent_profiles
from app.schemas import InterviewDecision, TopicAssessment, TopicEvaluation, TurnDecision
from app.services.assessment import topic_score, validate_assessment
from app.services.interview_policy import validate_decision
from app.services.reports import validate_topic

ROOT = Path(__file__).resolve().parents[1]


def load_cases(path):
    dataset = json.loads(Path(path).read_text())
    ids = set()
    for case in dataset["cases"]:
        if case["id"] in ids or not case["answer"].strip() or not case["question"].strip():
            raise ValueError("Case IDs must be unique and question/answer must be nonempty")
        ids.add(case["id"])
        low, high = case["score_range"]
        if not 0 <= low <= high <= 100 or not set(case["actions"]) <= {"follow_up", "advance", "finish"}:
            raise ValueError("Invalid score range or expected action")
        if not case["anchors"] or not all(anchor in case["answer"] for anchor in case["anchors"]):
            raise ValueError("Expected evidence anchors must occur in the identified answer")
        if case.get("human_reviewed") and not case.get("reviewer"):
            raise ValueError("Reviewed cases must identify their reviewer")
    return dataset


def summarize(rows):
    scored = [r for r in rows if r.get("score") is not None]
    return {
        "runs": len(rows),
        "scored_runs": len(scored),
        "action_runs": sum("action" in r for r in rows),
        "quote_rejections": sum(r.get("quote_rejections", 0) for r in rows),
        "failed_runs": sum(bool(r.get("error")) for r in rows),
        "within_expected_range": sum(r.get("score_in_range", False) for r in rows),
        "acceptable_followups": sum(r.get("action_correct", False) for r in rows),
        "quote_checks_passed": sum(r.get("quotes_valid", False) for r in rows),
        "anchor_coverage": sum(r.get("anchor_covered", False) for r in rows),
        "mean_score": round(statistics.mean(r["score"] for r in scored), 2) if scored else None,
        "repairs": sum(r.get("repairs", 0) for r in rows),
        "mean_latency_ms": round(statistics.mean(r["latency_ms"] for r in rows)) if rows else None,
        "human_reviewed_runs": sum(r["human_reviewed"] for r in rows),
    }


def score_drift(rows, previous):
    """Compare per-case means so --repeat does not make the last baseline run authoritative."""

    def means(values):
        grouped = {}
        for row in values:
            if row.get("score") is not None:
                grouped.setdefault(row["id"], []).append(row["score"])
        return {key: statistics.mean(scores) for key, scores in grouped.items()}

    current, baseline = means(rows), means(previous)
    return [
        {"id": key, "score_delta": round(current[key] - baseline[key], 2)}
        for key in sorted(current.keys() & baseline.keys())
    ]


def run_case(case, bundle, engine, identity, repeat):
    answer_id = f"{case['id']}-answer"
    turns = [{"answer_id": answer_id, "question": case["question"], "answer": case["answer"], "topic": 0}]
    persona = persona_definition(case["persona"])
    context = {
        "job_title": case["role"],
        "company": "",
        "experience_years": 4,
        "job_description": "",
        "resume": "",
        "custom_instructions": "",
        "language": case["language"],
        "interview_profile": public_persona(persona),
        "company_context": {"status": "not_requested", "facts": [], "sources": []},
    }
    modern = bundle.get("contract_revision", 2) >= 3
    if modern:
        context = {key: context[key] for key in ("job_title", "experience_years", "language", "interview_profile")}
        context["rubric"] = persona["rubric"]
    else:
        persona.pop("rubric", None)
        context["interview_profile"].pop("rubric", None)
    op = f"{case['id']}:{repeat}"
    kwargs = {
        "workspace_id": identity[0],
        "user_id": identity[1],
        "execution": bundle,
        "engine": engine,
        "operation_id": op,
    }
    started = time.monotonic()
    row = {"id": case["id"], "repeat": repeat, "human_reviewed": bool(case.get("human_reviewed", False))}
    row["quote_rejections"] = 0

    def check_topic(output):
        try:
            if modern:
                validate_assessment(output, 0, turns, persona["rubric"])
            else:
                validate_topic(output, 0, turns)
        except Exception as exc:
            if getattr(exc, "code", "").startswith("evidence_"):
                row["quote_rejections"] += 1
            raise

    try:
        value = execute(
            "evaluator",
            {**context, "topic": 0, "turns": turns, "part": 1, "parts": 1},
            TopicAssessment if modern else TopicEvaluation,
            validate=check_topic,
            **kwargs,
        )
        row["assessment"] = value.model_dump()
        score = topic_score(value, persona["rubric"]) if modern else sum(value.rubric.model_dump().values())
        row["score"] = round(score * 10) if score is not None else None
        row["quotes_valid"] = True
        row["evidence"] = [e.model_dump() for e in value.evidence]
        row["anchor_covered"] = any(
            anchor in e.quote or e.quote in anchor for anchor in case["anchors"] for e in value.evidence
        )
        row["score_in_range"] = (
            row["score"] is not None and case["score_range"][0] <= row["score"] <= case["score_range"][1]
        )
    except Exception as exc:  # noqa: BLE001 - store safe category, not provider bodies
        row["error"] = getattr(exc, "category", type(exc).__name__)
    try:
        iv = SimpleNamespace(
            current_topic=0, plan={"_visited_topics": [0], "question_bank": [{"topic": "Current"}, {"topic": "Next"}]}
        )
        decision = execute(
            "interviewer",
            {
                **context,
                "interview_profile": persona,
                "history": turns,
                "answer": case["answer"],
                "answer_id": answer_id,
                "remaining_seconds": 900,
                "followups": 0,
                "covered_topics": [],
                "current_topic": 0,
                "candidate_memory": [],
                "remaining_topics": [{"index": 1, "topic": "Next", "question": "Describe another relevant decision."}],
                "finish_allowed": False,
                "target_seconds_per_topic": 300,
            },
            InterviewDecision if modern else TurnDecision,
            validate=(lambda output: validate_decision(output, iv, [SimpleNamespace(id=answer_id)], case["answer"]))
            if modern
            else None,
            **kwargs,
        )
        row["action"] = decision.action
        row["action_correct"] = decision.action in case["actions"]
    except Exception as exc:  # noqa: BLE001 - preserve evaluation result if interviewing fails
        row["action_error"] = getattr(exc, "category", type(exc).__name__)
        row["error"] = row.get("error") or row["action_error"]
    row["latency_ms"] = round((time.monotonic() - started) * 1000)
    with Session(engine) as session:
        traces = session.exec(select(AgentRun).where(AgentRun.operation_id == op)).all()
        row["repairs"] = sum(t.error_code == "invalid_output" for t in traces)
        row["trace"] = [
            t.model_dump(
                include={
                    "agent",
                    "model",
                    "provider",
                    "prompt_version",
                    "status",
                    "error_code",
                    "input_tokens",
                    "output_tokens",
                    "duration_ms",
                }
            )
            for t in traces
        ]
    return row


def main():
    logging.basicConfig(level=logging.WARNING)
    logging.getLogger("app.agents.runtime").setLevel(logging.INFO)
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--cases", type=Path, default=ROOT / "evaluations/cases.json")
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--accept-cost", action="store_true")
    parser.add_argument("--bundle", type=Path)
    parser.add_argument("--profile")
    parser.add_argument("--limit", type=int, default=20)
    parser.add_argument("--case-id", action="append", default=[])
    parser.add_argument("--repeat", type=int, default=1)
    parser.add_argument("--output", type=Path, default=ROOT / "evaluations/results/latest.json")
    parser.add_argument("--baseline", type=Path)
    args = parser.parse_args()
    dataset = load_cases(args.cases)
    if set(args.case_id) - {case["id"] for case in dataset["cases"]}:
        parser.error("Unknown --case-id; choose an ID in the reference dataset")
    if not args.live:
        print(
            f"Validated {len(dataset['cases'])} synthetic reference cases offline; no model calls. Human review remains required."
        )
        return
    if not args.accept_cost or not 1 <= args.limit <= 100 or not 1 <= args.repeat <= 10:
        parser.error("Live runs require --accept-cost, --limit 1..100 and --repeat 1..10")
    routing = {role: profile for role, profile in agent_profiles().items() if role in {"interviewer", "evaluator"}}
    if args.profile:
        routing = {role: args.profile for role in ("interviewer", "evaluator")}
    with tempfile.TemporaryDirectory(prefix="interview-eval-") as directory:
        engine = db.make_engine(f"sqlite:///{directory}/traces.db")
        SQLModel.metadata.create_all(engine)
        with Session(engine) as session:
            user, account = (
                User(google_sub="evaluation-only", email="evaluation@example.invalid", name="Synthetic evaluation"),
                Workspace(name="Evaluation"),
            )
            session.add(user)
            session.add(account)
            session.commit()
            identity = (account.id, user.id)
        bundle = json.loads(args.bundle.read_text()) if args.bundle else specs.snapshot(routing, engine)
        bundle = bundle.get("execution", bundle)
        bundle = {**bundle, "prompts": specs.bundle_prompts(bundle, engine)}
        if any(p["provider"] == "demo" for role in bundle["roles"].values() for p in role["profiles"]):
            parser.error("Live evaluations require a real provider")
        result = {
            "dataset_hash": hashlib.sha256(args.cases.read_bytes()).hexdigest(),
            "execution": bundle,
            "created_at": time.time(),
            "rubrics": {case["persona"]: persona_definition(case["persona"])["rubric"] for case in dataset["cases"]},
            "rows": [],
        }
        args.output.parent.mkdir(parents=True, exist_ok=True)
        for repeat in range(args.repeat):
            for case in [c for c in dataset["cases"] if not args.case_id or c["id"] in args.case_id][: args.limit]:
                row = run_case(case, bundle, engine, identity, repeat)
                result["rows"].append(row)
                result["summary"] = summarize(result["rows"])
                args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
                print(
                    f"{case['id']}: score={row.get('score')} action={row.get('action')} error={row.get('error', 'none')}",
                    flush=True,
                )
        if args.baseline:
            baseline = json.loads(args.baseline.read_text())
            result["drift"] = score_drift(result["rows"], baseline["rows"])
            result["same_dataset"] = baseline["dataset_hash"] == result["dataset_hash"]
            args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
        engine.dispose()
    grouped = {}
    for row in result["rows"]:
        if row.get("score") is not None:
            grouped.setdefault(row["id"], []).append(row["score"])
    result["score_variance"] = {
        key: {"min": min(values), "max": max(values), "stdev": statistics.pstdev(values)}
        for key, values in grouped.items()
    }
    args.output.write_text(json.dumps(result, ensure_ascii=False, indent=2))
    lines = [
        "# Live judgment regression",
        "",
        "Synthetic provisional references; human review is required. Scores are practice feedback.",
        "",
        "| Case | Score | In reference range | Action | Accepted action | Rejected quote attempts | Error |",
        "| --- | --- | --- | --- | --- | --- | --- |",
    ]
    for row in result["rows"]:
        lines.append(
            f"| {row['id']} | {row.get('score', '—')} | {row.get('score_in_range', False)} | {row.get('action', '—')} | {row.get('action_correct', False)} | {row.get('quote_rejections', 0)} | {row.get('error', '')} |"
        )
    args.output.with_suffix(".md").write_text("\n".join(lines) + "\n")
    print(json.dumps(result["summary"]))


if __name__ == "__main__":
    main()
