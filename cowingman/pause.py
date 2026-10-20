"""Opt-in speech/pause heuristic. It does not detect anxiety or stress."""

from dataclasses import dataclass
import math


@dataclass
class PauseDetector:
    threshold: float = 0.015
    silence_seconds: float = 3.0
    minimum_speech_seconds: float = 1.0
    cooldown_seconds: float = 30.0
    _speech: float = 0.0
    _silence: float = 0.0
    _elapsed: float = 0.0
    _last_offer: float = -30.0

    def observe(self, rms: float, seconds: float) -> bool:
        if not math.isfinite(rms) or not math.isfinite(seconds) or seconds <= 0:
            return False
        self._elapsed += seconds
        if rms >= self.threshold:
            self._speech += seconds
            self._silence = 0.0
            return False
        self._silence += seconds
        if self._silence < self.silence_seconds:
            return False
        eligible = (
            self._speech >= self.minimum_speech_seconds
            and self._elapsed - self._last_offer >= self.cooldown_seconds
        )
        self._speech = 0.0
        if eligible:
            self._last_offer = self._elapsed
        return eligible
