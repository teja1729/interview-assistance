"""Reference data integrity and regression statistics; no paid model calls."""

import json

import pytest

from scripts.run_evaluations import ROOT, load_cases, score_drift, summarize


def test_reference_cases_are_valid_and_explicitly_provisional():
    dataset = load_cases(ROOT / "evaluations/cases.json")
    cases = dataset["cases"]
    assert len(cases) >= 20
    assert {c["persona"] for c in cases} == {"recruiter", "hiring_manager", "technical", "leadership"}
    assert "synthetic" in dataset["provenance"].lower()


def test_invalid_regression_anchors_are_rejected(tmp_path):
    dataset = load_cases(ROOT / "evaluations/cases.json")
    path = tmp_path / "cases.json"
    dataset["cases"][0]["anchors"] = ["Fabricated quote not present in this answer"]
    path.write_text(json.dumps(dataset))
    with pytest.raises(ValueError, match="anchors"):
        load_cases(path)


def test_drift_uses_repeated_case_means_and_excludes_abstentions():
    before = [{"id": "one", "score": 20}, {"id": "one", "score": 40}, {"id": "two", "score": None}]
    after = [{"id": "one", "score": 30}, {"id": "one", "score": 50}, {"id": "two", "score": 30}]
    assert score_drift(after, before) == [{"id": "one", "score_delta": 10}]
    summary = summarize(
        [{"id": "one", "score": None, "error": "invalid_output", "latency_ms": 1}]
    )
    assert summary["failed_runs"] == 1 and summary["scored_runs"] == 0
