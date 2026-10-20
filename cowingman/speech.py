"""Isolated local speech lifecycle; termination frees CUDA and microphone resources."""

from __future__ import annotations

import hashlib
import json
import multiprocessing
import os
from pathlib import Path
import time

from .config import ASR_MODEL
from .errors import SpeechError

FASTPITCH_MODEL = "tts_en_fastpitch"
HIFIGAN_MODEL = "tts_en_hifigan"


def verify_model(path, model_id):
    try:
        archive = Path(path)
        if not path or archive.suffix != ".nemo" or not archive.is_file():
            raise ValueError
        manifest = json.loads(archive.with_suffix(".json").read_text())
        if manifest["model_id"] != model_id:
            raise ValueError
        digest = hashlib.sha256()
        with archive.open("rb") as stream:
            for block in iter(lambda: stream.read(1024 * 1024), b""):
                digest.update(block)
        if digest.hexdigest() != manifest["sha256"]:
            raise ValueError
    except (OSError, ValueError, KeyError, TypeError):
        raise SpeechError(
            "Missing or unverified NVIDIA model. Run scripts/prepare_speech_models.py; see RUN_ON_JETSON.md."
        ) from None


def available_memory():
    try:
        for line in Path("/proc/meminfo").read_text().splitlines():
            if line.startswith("MemAvailable:"):
                return int(line.split()[1]) * 1024
    except (OSError, ValueError):
        pass
    return 0


def prepare_worker():
    # Never let third-party libraries print transcripts, tokens, or cue text.
    with open(os.devnull, "w") as sink:
        os.dup2(sink.fileno(), 1)
        os.dup2(sink.fileno(), 2)
    for name in list(os.environ):
        if "KEY" in name or "TOKEN" in name or "SECRET" in name:
            os.environ.pop(name, None)
    os.environ.update(HF_HUB_OFFLINE="1", TRANSFORMERS_OFFLINE="1", WANDB_MODE="disabled")
    try:
        import resource

        resource.setrlimit(resource.RLIMIT_CORE, (0, 0))
    except (ImportError, ValueError, OSError):
        pass
    # Offline speech dependencies may use local sockets, but never IP sockets.
    import socket

    original = socket.socket

    class LocalSocket(original):
        def __init__(self, family=socket.AF_INET, *args, **kwargs):
            if family in {socket.AF_INET, socket.AF_INET6}:
                raise OSError("Network disabled in local speech worker.")
            super().__init__(family, *args, **kwargs)

    socket.socket = LocalSocket


def _speech_worker(connection, asr_path, device, threshold):
    prepare_worker()
    microphone = None
    samples = None
    try:
        import numpy as np
        from .asr import NemoASR
        from .audio import BLOCK_FRAMES, CHUNK_BLOCKS, Microphone
        from .pause import PauseDetector

        if available_memory() < 2 * 1024**3:
            raise SpeechError("Less than 2 GiB RAM available. Close GPU workloads or use --typed.")
        model = NemoASR(asr_path)
        detector = PauseDetector(threshold=threshold)
        connection.send(("status", "listening"))
        while True:
            if available_memory() < 1024**3:
                raise SpeechError(
                    "Memory is low. Audio stopped; close other workloads or use --typed."
                )
            microphone = Microphone(device).open()
            samples = np.zeros(BLOCK_FRAMES * CHUNK_BLOCKS, dtype=np.float32)
            voiced = False
            pause = False
            try:
                for index in range(CHUNK_BLOCKS):
                    block = microphone.read()
                    rms = float(np.sqrt(np.mean(block * block)))
                    voiced = voiced or rms >= threshold
                    pause = detector.observe(rms, 0.25) or pause
                    samples[index * BLOCK_FRAMES : (index + 1) * BLOCK_FRAMES] = block
                    block.fill(0)
            finally:
                microphone.close()
                microphone = None
            if voiced:
                connection.send(("status", "transcribing"))
                text = model.transcribe(samples)
                if text:
                    connection.send(("fragment", text))
                text = None
            samples.fill(0)
            samples = None
            if pause:
                connection.send(("pause", None))
            connection.send(("status", "listening"))
    except SpeechError as exc:
        connection.send(("error", str(exc)))
    except Exception:
        connection.send(
            (
                "error",
                "Local speech unavailable. Check NeMo, CUDA and microphone setup; use --typed.",
            )
        )
    finally:
        if microphone is not None:
            microphone.close()
        if samples is not None:
            samples.fill(0)
        connection.close()


def _tts_worker(connection, cue, fastpitch_path, hifigan_path):
    prepare_worker()
    try:
        from .tts import speak_local

        if available_memory() < 2 * 1024**3:
            raise SpeechError("TTS skipped: less than 2 GiB RAM available. Use the visual cue.")
        speak_local(cue, fastpitch_path, hifigan_path)
        connection.send(("done", None))
    except SpeechError as exc:
        connection.send(("error", str(exc)))
    except Exception:
        connection.send(("error", "Local TTS unavailable. Use the visual cue."))
    finally:
        connection.close()


class SpeechSession:
    def __init__(self, config, threshold=0.015):
        self.config = config
        self.threshold = threshold
        self.process = None
        self.connection = None
        self.last_event = 0.0

    def start(self):
        self.close()
        verify_model(self.config.asr_path, ASR_MODEL)
        ctx = multiprocessing.get_context("spawn")
        self.connection, child = ctx.Pipe(duplex=False)
        self.process = ctx.Process(
            target=_speech_worker,
            args=(
                child,
                self.config.asr_path,
                self.config.audio_device,
                self.threshold,
            ),
            daemon=True,
        )
        self.process.start()
        child.close()
        self.last_event = time.monotonic()

    def poll(self):
        if self.process is None:
            return []
        events = []
        try:
            while len(events) < 32 and self.connection.poll():
                events.append(self.connection.recv())
                self.last_event = time.monotonic()
        except EOFError:
            pass
        if not self.process.is_alive() and not any(kind == "error" for kind, _ in events):
            events.append(
                ("error", "Audio worker stopped. Use :listen to retry or restart with --typed.")
            )
        elif time.monotonic() - self.last_event > 90:
            events.append(("error", "Local speech timed out. Check available RAM or use --typed."))
        if any(kind == "error" for kind, _ in events):
            self.close()
        return events

    def close(self):
        if self.process is not None:
            if self.process.is_alive():
                self.process.terminate()
            self.process.join(timeout=2)
            if self.process.is_alive():
                self.process.kill()
                self.process.join(timeout=2)
            self.process.close()
            self.process = None
        if self.connection is not None:
            self.connection.close()
            self.connection = None


def speak(cue, config):
    verify_model(config.fastpitch_path, FASTPITCH_MODEL)
    verify_model(config.hifigan_path, HIFIGAN_MODEL)
    ctx = multiprocessing.get_context("spawn")
    parent, child = ctx.Pipe(duplex=False)
    process = ctx.Process(
        target=_tts_worker,
        args=(child, cue, config.fastpitch_path, config.hifigan_path),
        daemon=True,
    )
    try:
        process.start()
        child.close()
        if not parent.poll(45):
            raise SpeechError("Local TTS timed out. Use the visual cue.")
        try:
            kind, message = parent.recv()
        except EOFError:
            raise SpeechError("Local TTS stopped. Use the visual cue.") from None
        if kind == "error":
            raise SpeechError(message)
    finally:
        if process.pid is not None:
            if process.is_alive():
                process.terminate()
            process.join(timeout=2)
            if process.is_alive():
                process.kill()
                process.join(timeout=2)
            process.close()
        parent.close()
        child.close()
