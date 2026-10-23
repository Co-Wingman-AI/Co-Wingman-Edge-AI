#!/usr/bin/env python3
"""Offline syntax, whitespace, and tracked-content hygiene checks; no values printed."""

import ast
import hashlib
from pathlib import Path
import re
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
FORBIDDEN_SUFFIXES = {
    ".keras",
    ".wav",
    ".mp3",
    ".pcm",
    ".flac",
    ".ogg",
    ".m4a",
    ".nemo",
    ".pt",
    ".pth",
    ".gguf",
    ".safetensors",
    ".key",
    ".pem",
}
REVIEWED_BINARY_FILES = {
    "website/assets/yasasvi-kaipa.jpg": (
        "3df3affa82b2514e173aae84ba0c6e641aa3c83b6af43f118805210a9c9f5d62"
    ),
    "website/assets/shrimayee-deshpande.jpg": (
        "89155f59339f159eae81e5d3f8bd5936ab54ca0ca4d8ddc4edfb4b7e43d9b544"
    ),
    "website/assets/honey-reddy-daram.jpg": (
        "cdf666f6d5153f37dc85a7704e602080be9d0f00f6643d159533cf77b35e9e02"
    ),
    "docs/co-wingman-architecture-current.png": (
        "ac77b02e30a68a1e99fdbba2272de1f7f32f0b258948c03dcfbf9fe23265c637"
    ),
    "docs/co-wingman-architecture.png": (
        "d06367f12cd4b3566ab8fec86f963837473ecc8f9774392d65f5cb02034cad4a"
    ),
}
SECRET_PATTERNS = (
    re.compile(r"-----BEGIN (?:RSA |EC |OPENSSH )?PRIVATE KEY-----"),
    re.compile(
        r"\b(?:sk-[A-Za-z0-9_-]{24,}|gh[pousr]_[A-Za-z0-9]{30,}|github_pat_[A-Za-z0-9_]{30,})\b"
    ),
    re.compile(r"\bAKIA[0-9A-Z]{16}\b"),
    re.compile(
        r"(?m)^[ \t]*(?:NAVIGATOR_TOOLKIT_API_KEY|NEBIUS_API_KEY)[ \t]*=[ \t]*[^\s#\n][^\n]{15,}$"
    ),
)


def check():
    # Include new non-ignored source during development, without touching .env/models.
    result = subprocess.run(
        ["git", "ls-files", "--cached", "--others", "--exclude-standard", "-z"],
        cwd=ROOT,
        check=True,
        capture_output=True,
    )
    names = sorted(set(result.stdout.decode().split("\0")) - {""})
    errors = []
    count = 0
    for name in names:
        path = ROOT / name
        if not path.is_file():
            continue
        if path.name == ".env" or (path.name.startswith(".env.") and path.name != ".env.example"):
            errors.append(f"{name}: private environment file")
        if path.suffix in FORBIDDEN_SUFFIXES or name.startswith(
            ("recordings/", "transcripts/", "models/", "private/")
        ):
            errors.append(f"{name}: private/model artifact")
        if name.startswith("reports/") and path.name != ".gitkeep":
            errors.append(f"{name}: generated report")
        try:
            content = path.read_text(encoding="utf-8")
        except UnicodeError:
            digest = hashlib.sha256(path.read_bytes()).hexdigest()
            if REVIEWED_BINARY_FILES.get(name) != digest:
                errors.append(f"{name}: unreviewed binary")
            continue
        count += 1
        if any(pattern.search(content) for pattern in SECRET_PATTERNS):
            errors.append(f"{name}: possible credential (value suppressed)")
        if any(line.rstrip() != line for line in content.splitlines()):
            errors.append(f"{name}: trailing whitespace")
        if content and not content.endswith("\n"):
            errors.append(f"{name}: missing final newline")
        if path.suffix == ".py":
            try:
                ast.parse(content, filename=name, feature_version=(3, 10))
            except SyntaxError:
                errors.append(f"{name}: Python 3.10 syntax error (content suppressed)")
    for error in errors:
        print(error)
    if errors:
        return 1
    print(
        f"Checked {count} source files: syntax, whitespace, and credential/artifact patterns passed."
    )
    print("Pattern scanning is not proof that all sensitive data is absent; review the diff too.")
    return 0


if __name__ == "__main__":
    sys.exit(check())
