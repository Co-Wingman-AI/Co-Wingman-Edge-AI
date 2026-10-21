"""Bounded, expiring RAM-only fragments; no conversation archive."""

from __future__ import annotations

import time
from dataclasses import dataclass, field
from typing import Callable, Sequence

from .errors import PrivacyBoundaryError

MAX_CONTEXT_TURNS = 4
MAX_TURN_CHARACTERS = 240
MAX_CONTEXT_CHARACTERS = 800


@dataclass(frozen=True, repr=False)
class ContextTurn:
    speaker: str
    text: str


@dataclass(frozen=True, repr=False)
class BoundedContext:
    turns: tuple[ContextTurn, ...]

    @classmethod
    def from_turns(cls, turns: Sequence[ContextTurn]) -> BoundedContext:
        if not isinstance(turns, (tuple, list)) or not 1 <= len(turns) <= MAX_CONTEXT_TURNS:
            raise PrivacyBoundaryError("Use one to four recent text fragments.")
        checked = []
        for turn in turns:
            if not isinstance(turn, ContextTurn) or turn.speaker not in {
                "user",
                "partner",
                "unknown",
            }:
                raise PrivacyBoundaryError("Invalid text fragment.")
            if type(turn.text) is not str:
                raise PrivacyBoundaryError("Only decoded text is permitted.")
            # Control characters are never useful conversational context.
            if any(ord(c) < 32 and c not in "\n\r\t" for c in turn.text):
                raise PrivacyBoundaryError("Text contains unsupported control characters.")
            text = " ".join(turn.text.split())
            if not 1 <= len(text) <= MAX_TURN_CHARACTERS:
                raise PrivacyBoundaryError("Each fragment must contain 1–240 characters.")
            checked.append(ContextTurn(turn.speaker, text))
        if sum(len(t.text) for t in checked) > MAX_CONTEXT_CHARACTERS:
            raise PrivacyBoundaryError("Selected context exceeds 800 characters.")
        return cls(tuple(checked))

    @property
    def character_count(self) -> int:
        return sum(len(turn.text) for turn in self.turns)

    def as_prompt(self) -> str:
        import json

        return json.dumps(
            {"recent_fragments": [{"speaker": t.speaker, "text": t.text} for t in self.turns]},
            ensure_ascii=True,
        )


@dataclass(repr=False)
class RollingContext:
    ttl_seconds: float = 60.0
    clock: Callable[[], float] = time.monotonic
    _items: list[tuple[float, ContextTurn]] = field(default_factory=list, init=False)

    def expire(self) -> None:
        cutoff = self.clock() - self.ttl_seconds
        self._items[:] = [(at, t) for at, t in self._items if at > cutoff]

    def add(self, text: str, speaker: str = "user", *, merge=False) -> None:
        if type(text) is not str:
            raise PrivacyBoundaryError("Only decoded text is permitted.")
        # Discard older words locally before they enter the rolling store.
        fragment = " ".join(text[-2048:].split())[-MAX_TURN_CHARACTERS:]
        if not fragment:
            return
        turn = BoundedContext.from_turns([ContextTurn(speaker, fragment)]).turns[0]
        self.expire()
        if merge and self._items and self._items[-1][1].speaker == speaker:
            first_seen, previous = self._items[-1]
            combined = f"{previous.text} {turn.text}"
            if len(combined) <= MAX_TURN_CHARACTERS:
                # Preserve the oldest window's timestamp. Continued conversation
                # must never refresh and retain older speech beyond the TTL.
                self._items[-1] = (first_seen, ContextTurn(speaker, combined))
                return
        self._items.append((self.clock(), turn))
        while (
            len(self._items) > MAX_CONTEXT_TURNS
            or sum(len(t.text) for _, t in self._items) > MAX_CONTEXT_CHARACTERS
        ):
            self._items.pop(0)

    def take(self) -> BoundedContext:
        self.expire()
        try:
            return BoundedContext.from_turns([t for _, t in self._items])
        finally:
            self.clear()

    def clear(self) -> None:
        self._items.clear()

    def __len__(self) -> int:
        self.expire()
        return len(self._items)
