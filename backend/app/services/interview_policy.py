"""Deterministic coverage and memory validation for revision 3 interview proposals."""

import math
import re

from ..providers.base import InvalidOutput
from .assessment import validate_quotes


def question_bounds(minutes):
    minimum = max(2, math.ceil(minutes / 5))
    return minimum, min(15, minimum + 2)


def validate_plan(plan, minutes):
    low, high = question_bounds(minutes)
    if not low <= len(plan.question_bank) <= high:
        raise InvalidOutput(f"question_bank_requires_{low}_to_{high}_questions")
    names = [re.sub(r"\s+", " ", q.topic.strip().casefold()) for q in plan.question_bank]
    if len(set(names)) != len(names):
        raise InvalidOutput("question_bank_topics_must_be_distinct")


def remaining_topics(iv):
    visited = set(iv.plan.get("_visited_topics", list(range(iv.current_topic + 1))))
    return [i for i in range(len(iv.plan["question_bank"])) if i not in visited]


def validate_decision(output, iv, turns, answer):
    if output.action == "follow_up" and (not output.reply.strip() or output.next_topic is not None):
        raise InvalidOutput("follow_up_requires_reply_and_null_next_topic")
    if output.next_topic is not None and output.next_topic not in remaining_topics(iv):
        raise InvalidOutput("next_topic_must_be_an_unvisited_bank_index")
    if any(mark in output.transition for mark in ("?", "？")):
        raise InvalidOutput("transition_must_be_a_statement_not_another_question")
    # Memory additions may quote only this answer. Old claims remain independently sourced.
    validate_quotes(output.memory_updates, [{"answer_id": turns[-1].id, "answer": answer}])


def update_memory(plan, decision):
    claims = plan.get("_memory", []) + [m.model_dump() for m in decision.memory_updates]
    unique = {(claim["answer_id"], claim["quote"]): claim for claim in claims}
    return list(unique.values())[-10:]
