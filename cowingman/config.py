"""Explicit environment configuration; .env files are never loaded."""

from __future__ import annotations

import math
import os
from dataclasses import dataclass, field
from urllib.parse import urlsplit

from .errors import ConfigurationError

DEFAULT_BASE_URL = "https://api.ai.it.ufl.edu/v1"
DEFAULT_MODEL = "nemotron-3-nano-30b-a3b"
APPROVED_MODELS = frozenset({DEFAULT_MODEL})
ASR_MODEL = "nvidia/stt_en_conformer_ctc_small"


def validate_cloud_configuration(base_url: str, model: str) -> tuple[str, str]:
    try:
        parsed = urlsplit(base_url)
        valid = (
            parsed.scheme == "https"
            and parsed.netloc in {"api.ai.it.ufl.edu", "api.ai.it.ufl.edu:443"}
            and parsed.hostname == "api.ai.it.ufl.edu"
            and parsed.port in {None, 443}
            and parsed.path in {"/v1", "/v1/"}
            and not parsed.query
            and not parsed.fragment
            and not any(c.isspace() for c in base_url)
            and "?" not in base_url
            and "#" not in base_url
        )
    except (ValueError, TypeError, AttributeError):
        valid = False
    if not valid:
        raise ConfigurationError("NaviGator URL must be https://api.ai.it.ufl.edu/v1.")
    if type(model) is not str or model not in APPROVED_MODELS:
        raise ConfigurationError("Use the approved model: nemotron-3-nano-30b-a3b.")
    return DEFAULT_BASE_URL, model


def number(value, name, low, high):
    try:
        result = float(value)
    except (ValueError, TypeError):
        raise ConfigurationError(f"{name} must be a number.") from None
    if not math.isfinite(result) or not low <= result <= high:
        raise ConfigurationError(f"{name} must be between {low} and {high}.")
    return result


@dataclass(frozen=True)
class Config:
    api_key: str = field(default="", repr=False)
    base_url: str = DEFAULT_BASE_URL
    model: str = DEFAULT_MODEL
    timeout_seconds: float = 15.0
    context_ttl: float = 60.0
    asr_path: str = ""
    fastpitch_path: str = ""
    hifigan_path: str = ""
    audio_device: int | None = None

    @classmethod
    def load(cls, *, offline=False, environ=None):
        env = os.environ if environ is None else environ
        base_url, model = validate_cloud_configuration(
            env.get("NAVIGATOR_BASE_URL", DEFAULT_BASE_URL), env.get("NAVIGATOR_MODEL", DEFAULT_MODEL)
        )
        key = "" if offline else env.get("NAVIGATOR_TOOLKIT_API_KEY", "")
        if not offline and (not key or any(c.isspace() for c in key) or not key.isascii()):
            raise ConfigurationError("Set NAVIGATOR_TOOLKIT_API_KEY to your UF Toolkit key.")
        try:
            device = int(env["COWINGMAN_AUDIO_DEVICE"]) if env.get("COWINGMAN_AUDIO_DEVICE") else None
            if device is not None and device < 0:
                raise ValueError
        except ValueError:
            raise ConfigurationError("COWINGMAN_AUDIO_DEVICE must be a nonnegative device index.") from None
        return cls(
            key, base_url, model,
            number(env.get("COWINGMAN_TIMEOUT", "15"), "COWINGMAN_TIMEOUT", 1, 30),
            number(env.get("COWINGMAN_CONTEXT_TTL", "60"), "COWINGMAN_CONTEXT_TTL", 5, 120),
            env.get("COWINGMAN_ASR_MODEL_PATH", ""),
            env.get("COWINGMAN_FASTPITCH_PATH", ""),
            env.get("COWINGMAN_HIFIGAN_PATH", ""),
            device,
        )
