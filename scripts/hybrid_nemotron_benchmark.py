#!/usr/bin/env python3
"""Validate the bounded-text Jetson-to-Nebius Nemotron architecture gate."""

from __future__ import annotations

import argparse
import datetime as dt
import json
import os
import platform
import sys
from pathlib import Path
from typing import Any, Sequence

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from cowingman.hybrid_nemotron import (  # noqa: E402
    DEFAULT_BASE_URL,
    DEFAULT_MODEL,
    BoundedContext,
    CloudRequestError,
    ContextTurn,
    NebiusNemotronClient,
    validate_cloud_configuration,
)

REPORTS_DIR = PROJECT_ROOT / "reports"
SYNTHETIC_CONTEXTS = (
    (
        ContextTurn("partner", "Which part of the project should we test first?"),
        ContextTurn("user", "I think the first thing is... I lost the phrase."),
    ),
    (
        ContextTurn("partner", "Why must audio processing stay on the edge?"),
        ContextTurn("user", "Because the private signal should never leave the device."),
    ),
    (
        ContextTurn("partner", "Should the result be JSON or Markdown?"),
        ContextTurn("user", "Both, but I am trying to explain how they differ."),
    ),
)


def parse_args(argv: Sequence[str] | None = None) -> argparse.Namespace:
    parser = argparse.ArgumentParser(description=__doc__)
    mode = parser.add_mutually_exclusive_group(required=True)
    mode.add_argument("--dry-run", action="store_true", help="validate locally without networking")
    mode.add_argument("--live", action="store_true", help="send synthetic bounded text to Nebius")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument("--timeout", type=float, default=20.0)
    parser.add_argument("--max-latency", type=float, default=5.0)
    parser.add_argument("--base-url", default=os.environ.get("NEBIUS_BASE_URL", DEFAULT_BASE_URL))
    parser.add_argument("--model", default=os.environ.get("NEBIUS_MODEL", DEFAULT_MODEL))
    parser.add_argument("--reports-dir", type=Path, default=REPORTS_DIR, help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.trials < 1:
        parser.error("--trials must be at least 1")
    if args.max_latency <= 0:
        parser.error("--max-latency must be positive")
    return args


def environment_summary() -> dict[str, Any]:
    model_path = Path("/proc/device-tree/model")
    try:
        board = model_path.read_text(encoding="utf-8", errors="replace").strip("\x00\n ")
    except OSError:
        board = "not detected"
    return {
        "is_jetson": "jetson" in board.lower(),
        "board_model": board,
        "architecture": platform.machine(),
        "system": platform.system(),
        "python": platform.python_version(),
    }


def run_benchmark(args: argparse.Namespace) -> dict[str, Any]:
    base_url, model = validate_cloud_configuration(args.base_url, args.model)
    environment = environment_summary()
    contexts = [BoundedContext.from_turns(turns) for turns in SYNTHETIC_CONTEXTS]
    trials: list[dict[str, Any]] = []
    failure: str | None = None
    if args.live:
        key = os.environ.get("NEBIUS_API_KEY", "")
        client = NebiusNemotronClient(
            key,
            base_url=base_url,
            model=model,
            timeout_seconds=args.timeout,
        )
        for number in range(args.trials):
            context = contexts[number % len(contexts)]
            try:
                _cue, metrics = client.request_cue(context)
                trials.append({"trial": number + 1, "success": True, **metrics})
            except CloudRequestError as exc:
                trials.append({"trial": number + 1, "success": False, "error_type": type(exc).__name__})
                failure = str(exc)
    durations = [trial["duration_seconds"] for trial in trials if trial.get("success")]
    all_success = len(trials) == args.trials and all(t["success"] for t in trials)
    latency_passed = bool(durations) and max(durations) <= args.max_latency
    gate_passed = args.live and environment["is_jetson"] and all_success and latency_passed
    return {
        "report_schema_version": 1,
        "generated_at": dt.datetime.now().astimezone().isoformat(timespec="seconds"),
        "milestone": "1.3-hybrid-nebius-nemotron-gate",
        "mode": "live" if args.live else "dry-run",
        "environment": environment,
        "architecture": {
            "local": "NVIDIA speech/audio models on Jetson (not exercised by this milestone)",
            "cloud": "NVIDIA Nemotron through Nebius Token Factory",
            "raw_audio_sent_to_cloud": False,
            "full_transcript_sent_to_cloud": False,
            "request_content_recorded_in_report": False,
        },
        "configuration": {
            "base_url": base_url,
            "model": model,
            "trials_requested": args.trials,
            "timeout_seconds": args.timeout,
            "max_latency_seconds": args.max_latency,
            "synthetic_bounded_text_only": True,
        },
        "trials": trials,
        "failure": failure,
        "assessment": {
            "status": "passed" if gate_passed else ("not_run" if args.dry_run else "failed"),
            "jetson_verified": environment["is_jetson"],
            "all_requests_succeeded": all_success,
            "all_responses_schema_valid": all_success,
            "latency_gate_passed": latency_passed,
            "maximum_duration_seconds": max(durations) if durations else None,
            "ready_for_next_milestone": gate_passed,
            "next_gate": (
                "Return the timestamp-matched Jetson reports for review."
                if args.live
                else "Run the live synthetic benchmark on the Jetson and return both reports."
            ),
        },
    }


def markdown_report(report: dict[str, Any]) -> str:
    config = report["configuration"]
    assessment = report["assessment"]
    rows = []
    for trial in report["trials"]:
        rows.append(
            f"| {trial['trial']} | {'yes' if trial['success'] else 'no'} | "
            f"{trial.get('duration_seconds', 'n/a')} | {trial.get('request_characters', 'n/a')} |"
        )
    failure = report.get("failure") or "none"
    return f"""# Hybrid Nebius/NVIDIA Nemotron benchmark

Generated: {report['generated_at']}

- Mode: **{report['mode']}**
- Jetson verified: **{'yes' if report['environment']['is_jetson'] else 'no'}**
- Model: `{config['model']}`
- Endpoint: `{config['base_url']}`
- Synthetic bounded text only: **yes**
- Raw audio sent to cloud: **no**
- Full transcript sent to cloud: **no**
- Prompts, cues, and credentials recorded: **no**
- Gate status: **{assessment['status']}**

## Trials

| Trial | Success | Duration (s) | Request characters |
|---:|:---:|---:|---:|
{chr(10).join(rows)}

## Assessment

```json
{json.dumps(assessment, indent=2, sort_keys=True)}
```

Failure summary: `{failure}`

This report intentionally excludes request text, response cue text, full
transcripts, raw audio, authorization headers, and API keys.
"""


def write_reports(report: dict[str, Any], reports_dir: Path) -> tuple[Path, Path]:
    reports_dir.mkdir(parents=True, exist_ok=True)
    stamp = dt.datetime.now().astimezone().strftime("%Y%m%d_%H%M%S")
    stem = f"hybrid_nemotron_{stamp}"
    json_path = reports_dir / f"{stem}.json"
    md_path = reports_dir / f"{stem}.md"
    json_path.write_text(json.dumps(report, indent=2, sort_keys=True) + "\n", encoding="utf-8")
    md_path.write_text(markdown_report(report), encoding="utf-8")
    return json_path, md_path


def main(argv: Sequence[str] | None = None) -> int:
    args = parse_args(argv)
    try:
        report = run_benchmark(args)
    except (ValueError, RuntimeError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 2
    json_path, md_path = write_reports(report, args.reports_dir)
    print(f"JSON report: {json_path}")
    print(f"Markdown report: {md_path}")
    return 0 if report["assessment"]["status"] != "failed" else 1


if __name__ == "__main__":
    raise SystemExit(main())
