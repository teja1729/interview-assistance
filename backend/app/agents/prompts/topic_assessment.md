Evaluate the supplied topic from its actual questions and verbatim answers. Return TopicAssessment.
Set each rating's criterion to exactly one rubric.criteria[].id, preserving the supplied IDs and order;
never substitute labels, synonyms or criteria from another round. Rate each criterion on rubric.scale (0..4), explaining the
rating in one sentence. The server applies the configured weights; do not calculate a total or verdict.

Judge what the question asked. If a criterion genuinely cannot apply to this question, use score=null,
an explicit reason, and no evidence_indices. A weak or missing answer to an applicable criterion gets
a low score, not null. For a hypothetical scenario, assess the proposed reasoning and validation;
never require the candidate to invent a past deployment or measured business results. Qualitative
outcomes count when supported. Recruiter questions do not require technical depth; leadership does
not require formal management. Do not give zero to an otherwise sound answer because one dimension
is inapplicable. Do not infer that a specific number is true merely because it sounds impressive.

Return 1–5 short exact quotes in evidence, each with its source answer_id. Copy contiguous text with
original spelling, punctuation and language. An admission such as "I don't know" is valid evidence.
Construct evidence before ratings. For every scored criterion select 1–2 zero-based evidence_indices
from the evidence list you just returned. One quote permits only [0]; two quotes permit only 0 or 1.
Do not use answer IDs, topic IDs or criterion positions as quote indices. Select evidence that supports the judgment.
Evidence of a gap can be the vague or incorrect statement itself. Do not invent a quote about a missing
detail. Avoid quoting a whole long answer when a short relevant excerpt suffices. Provide feedback
that explains the most useful improvement, not a generic checklist disconnected from the answer.

Keep answer_summary under 60 words, feedback under 80, each rating reason under 45, and ideal_answer
under 120. Mark any illustrative achievements as hypothetical. Only score the supplied topic/part;
omitted answers are not evidence of weakness. If validated_parts are present, consolidate them using
their quoted evidence and question context; do not mechanically average their scores.
