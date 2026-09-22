"""Evidence checks and server-owned scoring. These cannot prove semantic judgment quality.

New rubrics use 0..4 ratings and snapshotted round weights. Historical reports keep their own
3/3/2/2 contract. No custom preferences or live assessments are scoring inputs.
"""

from ..providers.base import InvalidOutput


def validate_quotes(quotes, turns):
    for evidence in quotes:
        if not evidence.quote.strip() or not any(
            t["answer_id"] == evidence.answer_id and evidence.quote in t["answer"] for t in turns
        ):
            raise InvalidOutput("evidence_must_quote_the_identified_answer_exactly")


def validate_assessment(output, topic, turns, rubric):
    if output.topic != topic:
        raise InvalidOutput("topic_must_match_requested_id")
    validate_quotes(output.evidence, turns)
    expected = {c["id"] for c in rubric["criteria"]}
    if {r.criterion for r in output.ratings} != expected or len(output.ratings) != len(expected):
        raise InvalidOutput("ratings_must_use_each_exact_criterion_id_once:" + ",".join(sorted(expected)))
    for rating in output.ratings:
        if any(i < 0 or i >= len(output.evidence) for i in rating.evidence_indices):
            raise InvalidOutput(f"evidence_indices_must_be_zero_based_between_0_and_{len(output.evidence) - 1}")
        if rating.score is not None and not rating.evidence_indices:
            raise InvalidOutput("every_scored_criterion_requires_evidence")
        if rating.score is None and rating.evidence_indices:
            raise InvalidOutput("not_applicable_criteria_require_reason_without_score_or_evidence")


def topic_score(output, rubric):
    weights = {c["id"]: c["weight"] for c in rubric["criteria"]}
    scored = [r for r in output.ratings if r.score is not None]
    total = sum(weights[r.criterion] for r in scored)
    return round(sum(r.score * weights[r.criterion] for r in scored) / (4 * total) * 10, 1) if total else None


def communication_samples(turns, max_chars=10000):
    """Equal bounded excerpts across topic/time coverage, not evaluator-selected success quotes.

    The original answer remains in storage. Excerpts preserve exact wording, carry IDs and are
    labelled incomplete. Communication judgments must acknowledge the sampling limit.
    """
    if not turns:
        return []
    # At most six evenly spaced answers include the beginning and end of the session.
    count = min(6, len(turns))
    indices = sorted({round(i * (len(turns) - 1) / max(1, count - 1)) for i in range(count)})
    size = max_chars // len(indices)
    result = []
    for index in indices:
        turn = turns[index]
        text = turn["answer"]
        # A contiguous excerpt is verifiable; avoid manufacturing joined quotations.
        result.append({**turn, "question": turn["question"][:1000], "answer": text[:size], "excerpt": len(text) > size})
    return result


def validate_summary(output, samples):
    validate_quotes(output.communication.evidence, samples)
    for name in ("clarity", "structure"):
        if getattr(output.communication, name) is not None and not any(
            e.dimension == name for e in output.communication.evidence
        ):
            raise InvalidOutput("communication_scores_require_dimension_specific_answer_evidence")
    # With virtually no answer there is no defensible communication sample. Longer answers can
    # also be insufficient; the model may abstain. Length never determines the actual score.
    if sum(len(t["answer"].strip()) for t in samples) < 80 and any(
        getattr(output.communication, name) is not None for name in ("clarity", "structure")
    ):
        raise InvalidOutput("communication_sample_too_short_use_null_scores")
