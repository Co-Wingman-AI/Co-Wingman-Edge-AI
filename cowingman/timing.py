"""Opt-in, content-free timings shared by local worker processes."""

from contextlib import contextmanager
from datetime import datetime, timezone
import json
import math
import os
from pathlib import Path
import time
from uuid import uuid4

from .errors import ConfigurationError

STAGES = frozenset(
    "capture microphone_open capture_age audio_drop asr_verify asr_load asr_inference "
    "network_worker_start network_setup server_response response_read transport "
    "validation cue_total tts summary_total s3_upload s3_load "
    "model_assist_trigger disfluency_load disfluency_inference disfluency_score disfluency_disabled "
    "review_fluent review_stuck review_partner review_quiet".split()
)
FIELDS = frozenset("window_start score count offered max_tokens".split())


class Timing:
    def __init__(self, path=None, *, session=None):
        self.path = str(Path(path).absolute()) if path else None
        self.session = session or uuid4().hex

    @classmethod
    def create(cls, path):
        result = cls(path)
        try:
            Path(result.path).parent.mkdir(parents=True, exist_ok=True)
            fd = os.open(result.path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
            os.close(fd)
        except OSError:
            raise ConfigurationError(
                "Cannot create timing report. Choose a new writable path."
            ) from None
        return result

    def event(self, stage, started=None, *, ok=True, **fields):
        if not self.path:
            return
        if stage not in STAGES or not set(fields) <= FIELDS:
            raise ValueError("Unsupported timing field.")
        if any(type(v) not in (float, int, bool) or not math.isfinite(v) for v in fields.values()):
            raise ValueError("Timing fields must be finite numbers.")
        ended = time.monotonic()
        started = ended if started is None else started
        if not math.isfinite(started) or started > ended:
            raise ValueError("Invalid timing interval.")
        record = {
            "version": 1,
            "session": self.session,
            "utc": datetime.now(timezone.utc).isoformat(timespec="milliseconds"),
            "stage": stage,
            "start_monotonic": started,
            "end_monotonic": ended,
            "duration_ms": round((ended - started) * 1000, 3),
            "ok": bool(ok),
            **fields,
        }
        # One small append per event, no transcript, path, model output, or exception text.
        try:
            fd = os.open(self.path, os.O_WRONLY | os.O_APPEND | os.O_NOFOLLOW)
            try:
                os.write(fd, (json.dumps(record) + "\n").encode())
            finally:
                os.close(fd)
        except OSError:
            # Profiling must not stop conversation assistance (e.g. a full disk).
            pass

    @contextmanager
    def measure(self, stage, **fields):
        if not self.path:
            yield
            return
        started = time.monotonic()
        ok = False
        try:
            yield
            ok = True
        finally:
            self.event(stage, started, ok=ok, **fields)


NO_TIMING = Timing()
