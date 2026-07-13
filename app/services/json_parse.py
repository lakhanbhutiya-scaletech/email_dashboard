"""Defensive extraction of the JSON object from a free-text agent reply (spec §6.3).

Strip markdown fences, take the first `{` … last `}`, then json.loads. Returns
(payload, error). On failure payload is None and error explains why — the caller
stores raw_text and marks the snapshot parse_failed.
"""

from __future__ import annotations

import json
import re


def parse_analysis(text: str | None) -> tuple[dict | None, str | None]:
    if not text or not text.strip():
        return None, "empty response"

    cleaned = text.strip()

    # Remove ```json … ``` or ``` … ``` fences if present.
    fence = re.match(r"^```(?:json)?\s*(.*?)\s*```$", cleaned, re.DOTALL)
    if fence:
        cleaned = fence.group(1).strip()

    # Fall back to the first '{' … last '}' span.
    start = cleaned.find("{")
    end = cleaned.rfind("}")
    if start == -1 or end == -1 or end < start:
        return None, "no JSON object found in response"

    candidate = cleaned[start : end + 1]
    try:
        data = json.loads(candidate)
    except json.JSONDecodeError as e:
        return None, f"json decode error: {e}"

    if not isinstance(data, dict):
        return None, "parsed JSON is not an object"
    return data, None
