#!/usr/bin/env python3
"""Explicit pinned model download; never run implicitly during a conversation."""

import argparse
import os
from pathlib import Path
import sys
import urllib.request

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cowingman.disfluency import MODEL_URL, verify_shadow_model


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--output", default="models/disfluency.keras")
    args = parser.parse_args()
    target = Path(args.output)
    temporary = target.with_suffix(".download.keras")
    try:
        if target.exists():
            verify_shadow_model(target)
        else:
            target.parent.mkdir(parents=True, exist_ok=True)
            with urllib.request.urlopen(MODEL_URL, timeout=30) as response:
                data = response.read(8 * 1024**2 + 1)
            fd = os.open(temporary, os.O_WRONLY | os.O_CREAT | os.O_EXCL, 0o600)
            with os.fdopen(fd, "wb") as file:
                file.write(data)
            try:
                verify_shadow_model(temporary)
                # Refuse to replace another process's model file.
                os.link(temporary, target)
            finally:
                temporary.unlink(missing_ok=True)
        print("Pinned experimental model verified. It estimates disfluency, not anxiety.")
        return 0
    except Exception:
        print("Model preparation failed. Check access, output path and available disk space.")
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
