#!/usr/bin/env python3
"""Explicit one-time NVIDIA model download; never run during a conversation."""

import argparse
import hashlib
import json
import logging
from pathlib import Path
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cowingman.config import ASR_MODEL
from cowingman.speech import FASTPITCH_MODEL, HIFIGAN_MODEL


def save(model_class, model_id, destination):
    model = model_class.from_pretrained(model_name=model_id, map_location="cpu")
    model.save_to(str(destination))
    digest = hashlib.sha256()
    with destination.open("rb") as stream:
        for block in iter(lambda: stream.read(1024 * 1024), b""):
            digest.update(block)
    destination.with_suffix(".json").write_text(
        json.dumps(
            {
                "model_id": model_id,
                "sha256": digest.hexdigest(),
            },
            indent=2,
        )
        + "\n"
    )
    del model
    import gc

    gc.collect()


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--asr", action="store_true")
    parser.add_argument("--tts", action="store_true")
    parser.add_argument("--output", type=Path, default=Path("models"))
    args = parser.parse_args()
    if not args.asr and not args.tts:
        parser.error("Choose --asr and/or --tts")
    args.output.mkdir(parents=True, exist_ok=True)
    logging.disable(logging.CRITICAL)
    try:
        if args.asr:
            from nemo.collections.asr.models import ASRModel

            save(ASRModel, ASR_MODEL, args.output / "asr.nemo")
            print("NVIDIA ASR archive and integrity manifest ready.")
        if args.tts:
            from nemo.collections.tts.models import FastPitchModel, HifiGanModel

            save(FastPitchModel, FASTPITCH_MODEL, args.output / "fastpitch.nemo")
            save(HifiGanModel, HIFIGAN_MODEL, args.output / "hifigan.nemo")
            print("NVIDIA TTS archives and integrity manifests ready.")
    except Exception:
        print(
            "Model setup failed. Install compatible NeMo/PyTorch and check NVIDIA model-download access.",
            file=sys.stderr,
        )
        return 2
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
