"""Strict structured cue contract and conservative output checks."""

import json
import re
import unicodedata
from dataclasses import dataclass

MAX_CUE_WORDS = 12
MAX_CUE_CHARACTERS = 160


class CueValidationError(ValueError):
    """Fixed diagnostic messages only; never include response content."""

    MESSAGES = {
        "size": "response size or type is invalid.",
        "duplicate": "JSON contains duplicate fields.",
        "json": "response is not a single valid JSON object.",
        "schema": "JSON fields do not match cue, intent, and should_offer.",
        "type": "cue must be a JSON string, not null, a list, or an object.",
        "empty": "cue is empty or whitespace-only.",
        "length": "cue exceeds the 160-character limit.",
        "words": "cue exceeds the 12-word limit.",
        "characters": "cue contains unsupported control characters.",
        "intent": "intent must be exactly resume, clarify, or respond.",
        "offer": "should_offer must be a JSON boolean.",
        "safety": "cue failed the safety check.",
    }

    def __init__(self, code):
        super().__init__(self.MESSAGES[code])


@dataclass(frozen=True, repr=False)
class Cue:
    cue: str
    intent: str
    should_offer: bool


def _unique_object(pairs):
    value = {}
    for key, item in pairs:
        if key in value:
            raise CueValidationError("duplicate")
        value[key] = item
    return value


def parse_cue(content: str) -> Cue:
    if type(content) is not str or len(content) > 1024:
        raise CueValidationError("size")
    try:
        value = json.loads(content, object_pairs_hook=_unique_object)
    except (json.JSONDecodeError, RecursionError):
        raise CueValidationError("json") from None
    if type(value) is not dict or set(value) != {"cue", "intent", "should_offer"}:
        raise CueValidationError("schema")
    cue = value["cue"]
    if type(cue) is not str:
        raise CueValidationError("type")
    if not cue.strip():
        raise CueValidationError("empty")
    if len(cue.strip()) > MAX_CUE_CHARACTERS:
        raise CueValidationError("length")
    if len(cue.split()) > MAX_CUE_WORDS:
        raise CueValidationError("words")
    if not cue.isprintable() or any(unicodedata.category(c).startswith("C") for c in cue):
        raise CueValidationError("characters")
    if type(value["intent"]) is not str or value["intent"] not in {"resume", "clarify", "respond"}:
        raise CueValidationError("intent")
    if type(value["should_offer"]) is not bool:
        raise CueValidationError("offer")
    # Defense in depth, not a claim of comprehensive semantic moderation.
    if re.search(
        r"https?://|www\.|[<>`]|\b(?:suicid\w*|kill|murder|weapon\w*|bomb\w*|"
        r"diagnos\w*|disorder\w*|anxiety|medicat\w*|password\w*|api.?key|"
        r"ignore.{0,30}instructions)\b",
        cue,
        re.IGNORECASE,
    ):
        raise CueValidationError("safety")
    return Cue(cue.strip(), value["intent"], value["should_offer"])
