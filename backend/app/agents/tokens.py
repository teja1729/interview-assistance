"""Cheap multilingual context estimates without a network call or tokenizer downloads.

Heuristics are deliberately conservative, not a claimed exact vendor count. ASCII runs use
roughly 3 characters/token, Unicode uses 2 tokens/code point, plus 20% headroom. Punctuation
is counted separately, so code/JSON is not treated as English prose. Unknown deployments may
choose byte_ceiling in TOML; actual limits must always be explicit in the profile.
"""

import json
import math
import re

PIECES = re.compile(r"[A-Za-z0-9_]+|\s+|[^\x00-\x7f]|[^\w\s]", re.UNICODE)


def estimate_tokens(value, method="heuristic"):
    text = value if isinstance(value, str) else json.dumps(value, ensure_ascii=False)
    if method == "byte_ceiling":
        return len(text.encode())
    if method != "heuristic":
        raise ValueError("Unknown token estimator")
    amount = 0.0
    for part in PIECES.findall(text):
        if part.isspace():
            amount += max(1, len(part) / 4)
        elif not part.isascii():
            amount += 2
        elif part[0].isalnum() or part[0] == "_":
            amount += max(1, len(part) / 3)
        else:
            amount += 1
    return math.ceil(amount * 1.2)


def input_estimate(payload, prompt, schema, method="heuristic"):
    return sum(estimate_tokens(v, method) for v in (payload, prompt, schema.model_json_schema())) + 2048
