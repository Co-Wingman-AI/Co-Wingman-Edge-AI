"""Strict structured cue contract and conservative output checks."""

import json
import re
import unicodedata
from dataclasses import dataclass

MAX_CUE_WORDS = 12
MAX_CUE_CHARACTERS = 160


@dataclass(frozen=True, repr=False)
class Cue:
    cue: str
    intent: str
    should_offer: bool


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise ValueError("Duplicate response field.")
        value[key] = item
    return value


def parse_cue(content: str) -> Cue:
    if type(content) is not str or len(content) > 1024:
        raise ValueError("Invalid response size or type.")
    try:
        value = json.loads(content, object_pairs_hook=_unique_object)
    except (json.JSONDecodeError, RecursionError):
        raise ValueError("Response must be one JSON object.") from None
    if type(value) is not dict or set(value) != {"cue", "intent", "should_offer"}:
        raise ValueError("Response does not match the cue schema.")
    cue = value["cue"]
    if type(cue) is not str or not 1 <= len(cue.strip()) <= MAX_CUE_CHARACTERS:
        raise ValueError("Invalid cue length.")
    if len(cue.split()) > MAX_CUE_WORDS:
        raise ValueError("Cue exceeds 12 words.")
    if not cue.isprintable() or any(unicodedata.category(c).startswith("C") for c in cue):
        raise ValueError("Cue contains control characters.")
    if type(value["intent"]) is not str or value["intent"] not in {"resume", "clarify", "respond"}:
        raise ValueError("Invalid cue intent.")
    if type(value["should_offer"]) is not bool:
        raise ValueError("Invalid offer flag.")
    # Defense in depth, not a claim of comprehensive semantic moderation.
    if re.search(
        r"https?://|www\.|[<>`]|\b(?:suicid\w*|kill|murder|weapon\w*|bomb\w*|"
        r"diagnos\w*|disorder\w*|anxiety|medicat\w*|password\w*|api.?key|"
        r"ignore.{0,30}instructions)\b",
        cue,
        re.IGNORECASE,
    ):
        raise ValueError("Cue failed the safety check.")
    return Cue(cue.strip(), value["intent"], value["should_offer"])
