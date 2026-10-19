"""Privacy-bounded text cue generation through Nebius Token Factory.

This module deliberately has no audio input and no persistence layer. Local
speech components must select a short, ephemeral text window before calling
``BoundedContext.from_turns``. The cloud request and reports never contain raw
audio or a complete transcript.
"""

from __future__ import annotations

import json
import time
import urllib.error
import urllib.parse
import urllib.request
from dataclasses import dataclass
from typing import Any, Callable, Mapping, Sequence


DEFAULT_BASE_URL = "https://api.tokenfactory.us-central1.nebius.com/v1"
DEFAULT_MODEL = "nvidia/nvidia-nemotron-3-nano-30b-a3b"
MAX_CONTEXT_TURNS = 4
MAX_TURN_CHARACTERS = 240
MAX_CONTEXT_CHARACTERS = 800
MAX_CUE_WORDS = 12

SYSTEM_PROMPT = """You generate one discreet conversational recovery cue.
Use only the bounded, recent text fragments supplied by the edge device.
Do not diagnose emotion, anxiety, disability, or a medical condition.
Return one JSON object and no other text:
{"cue":"at most 12 words","intent":"resume|clarify|respond","should_offer":true}"""


class ConfigurationError(ValueError):
    """Raised when cloud configuration violates an architecture boundary."""


class PrivacyBoundaryError(ValueError):
    """Raised before a request that exceeds the bounded-text contract."""


class CloudRequestError(RuntimeError):
    """A deliberately content-free cloud request failure."""


@dataclass(frozen=True)
class ContextTurn:
    speaker: str
    text: str


@dataclass(frozen=True)
class BoundedContext:
    """A short-lived excerpt selected locally; never a transcript container."""

    turns: tuple[ContextTurn, ...]

    @classmethod
    def from_turns(cls, turns: Sequence[ContextTurn]) -> "BoundedContext":
        if not isinstance(turns, Sequence) or isinstance(turns, (str, bytes, bytearray)):
            raise PrivacyBoundaryError("context must be a sequence of text turns")
        if not turns:
            raise PrivacyBoundaryError("at least one context turn is required")
        if len(turns) > MAX_CONTEXT_TURNS:
            raise PrivacyBoundaryError(f"context is limited to {MAX_CONTEXT_TURNS} turns")

        checked: list[ContextTurn] = []
        total = 0
        for turn in turns:
            if not isinstance(turn, ContextTurn):
                raise PrivacyBoundaryError("every context item must be a ContextTurn")
            if turn.speaker not in {"user", "partner"}:
                raise PrivacyBoundaryError("speaker must be 'user' or 'partner'")
            if not isinstance(turn.text, str):
                raise PrivacyBoundaryError("only decoded text may cross the cloud boundary")
            text = " ".join(turn.text.split())
            if not text:
                raise PrivacyBoundaryError("empty context turns are not allowed")
            if len(text) > MAX_TURN_CHARACTERS:
                raise PrivacyBoundaryError(
                    f"one turn exceeds the {MAX_TURN_CHARACTERS}-character limit"
                )
            total += len(text)
            if total > MAX_CONTEXT_CHARACTERS:
                raise PrivacyBoundaryError(
                    f"context exceeds the {MAX_CONTEXT_CHARACTERS}-character limit"
                )
            checked.append(ContextTurn(turn.speaker, text))
        return cls(tuple(checked))

    @property
    def character_count(self) -> int:
        return sum(len(turn.text) for turn in self.turns)

    def as_prompt(self) -> str:
        lines = [f"{turn.speaker}: {turn.text}" for turn in self.turns]
        return "Recent fragments:\n" + "\n".join(lines) + "\nA cue was requested locally."


@dataclass(frozen=True)
class Cue:
    cue: str
    intent: str
    should_offer: bool


def validate_cloud_configuration(base_url: str, model: str) -> tuple[str, str]:
    parsed = urllib.parse.urlparse(base_url.rstrip("/"))
    hostname = (parsed.hostname or "").lower()
    if parsed.scheme != "https" or not hostname.endswith(".nebius.com"):
        raise ConfigurationError("base URL must use HTTPS on a nebius.com host")
    if parsed.username or parsed.password or parsed.query or parsed.fragment:
        raise ConfigurationError("base URL must not contain credentials, query, or fragment")
    normalized_model = model.strip().lower()
    if not normalized_model.startswith("nvidia/") or "nemotron" not in normalized_model:
        raise ConfigurationError("model must be an NVIDIA Nemotron model ID")
    return base_url.rstrip("/"), model.strip()


def parse_cue(content: str) -> Cue:
    if not isinstance(content, str):
        raise ValueError("response content is not text")
    try:
        value = json.loads(content)
    except json.JSONDecodeError as exc:
        raise ValueError("response is not one JSON object") from exc
    if not isinstance(value, dict) or set(value) != {"cue", "intent", "should_offer"}:
        raise ValueError("response does not match the cue schema")
    cue = value["cue"]
    if not isinstance(cue, str) or not cue.strip() or len(cue.split()) > MAX_CUE_WORDS:
        raise ValueError(f"cue must contain 1 to {MAX_CUE_WORDS} words")
    if value["intent"] not in {"resume", "clarify", "respond"}:
        raise ValueError("intent is invalid")
    if not isinstance(value["should_offer"], bool):
        raise ValueError("should_offer must be a boolean")
    return Cue(cue.strip(), value["intent"], value["should_offer"])


Transport = Callable[[str, Mapping[str, str], Mapping[str, Any], float], Mapping[str, Any]]


def urllib_transport(
    url: str,
    headers: Mapping[str, str],
    payload: Mapping[str, Any],
    timeout: float,
) -> Mapping[str, Any]:
    request = urllib.request.Request(
        url,
        data=json.dumps(payload, separators=(",", ":")).encode("utf-8"),
        headers=dict(headers),
        method="POST",
    )
    try:
        with urllib.request.urlopen(request, timeout=timeout) as response:
            return json.loads(response.read().decode("utf-8"))
    except urllib.error.HTTPError as exc:
        raise CloudRequestError(f"Token Factory returned HTTP {exc.code}") from None
    except (urllib.error.URLError, TimeoutError, OSError, json.JSONDecodeError) as exc:
        raise CloudRequestError(f"Token Factory request failed ({type(exc).__name__})") from None


class NebiusNemotronClient:
    """Small injectable client whose public input is bounded text, never audio."""

    def __init__(
        self,
        api_key: str,
        *,
        base_url: str = DEFAULT_BASE_URL,
        model: str = DEFAULT_MODEL,
        timeout_seconds: float = 20.0,
        transport: Transport = urllib_transport,
    ) -> None:
        self.base_url, self.model = validate_cloud_configuration(base_url, model)
        if not isinstance(api_key, str) or not api_key.strip():
            raise ConfigurationError("NEBIUS_API_KEY is required")
        if timeout_seconds <= 0:
            raise ConfigurationError("timeout must be positive")
        self._api_key = api_key
        self.timeout_seconds = timeout_seconds
        self._transport = transport

    def request_cue(self, context: BoundedContext) -> tuple[Cue, dict[str, Any]]:
        if not isinstance(context, BoundedContext):
            raise PrivacyBoundaryError("request_cue accepts only BoundedContext")
        payload = {
            "model": self.model,
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": context.as_prompt()},
            ],
            "temperature": 0.0,
            "max_tokens": 64,
            "response_format": {"type": "json_object"},
        }
        started = time.monotonic()
        response = self._transport(
            f"{self.base_url}/chat/completions",
            {"Authorization": f"Bearer {self._api_key}", "Content-Type": "application/json"},
            payload,
            self.timeout_seconds,
        )
        elapsed = time.monotonic() - started
        try:
            content = response["choices"][0]["message"]["content"]
            cue = parse_cue(content)
        except (KeyError, IndexError, TypeError, ValueError) as exc:
            raise CloudRequestError(f"Token Factory response was invalid ({type(exc).__name__})") from None
        usage = response.get("usage") if isinstance(response, Mapping) else None
        if not isinstance(usage, Mapping):
            usage = {}
        safe_usage = {
            key: int(value)
            for key, value in usage.items()
            if key in {"prompt_tokens", "completion_tokens", "total_tokens"}
            and isinstance(value, int)
        }
        return cue, {
            "duration_seconds": round(elapsed, 3),
            "request_turns": len(context.turns),
            "request_characters": context.character_count,
            "response_schema_valid": True,
            "usage": safe_usage,
        }
