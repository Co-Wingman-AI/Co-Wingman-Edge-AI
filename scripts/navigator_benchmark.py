#!/usr/bin/env python3
"""Optional synthetic benchmark. Reports contain numeric metrics only."""

import argparse
import datetime as dt
import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))

from cowingman.config import Config
from cowingman.context import BoundedContext, ContextTurn
from cowingman.errors import CloudRequestError, ConfigurationError
from cowingman.provider import NavigatorClient, OfflineClient


def run(client, trials):
    results = []
    for index in range(trials):
        context = BoundedContext.from_turns(
            [ContextTurn("partner", "Which feature should we demonstrate?")]
        )
        try:
            _cue, metrics = client.request_cue(context)
            results.append({"trial": index + 1, "success": True, **metrics})
            _cue = None
        except CloudRequestError:
            results.append({"trial": index + 1, "success": False})
        finally:
            context = None
    return {"synthetic_only": True, "trials": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--live", action="store_true")
    parser.add_argument("--trials", type=int, default=3)
    parser.add_argument(
        "--output", type=Path, help="Optional report directory; no files by default"
    )
    args = parser.parse_args()
    if not 1 <= args.trials <= 20:
        parser.error("Use 1–20 trials.")
    try:
        config = Config.load(offline=not args.live)
        client = (
            NavigatorClient(config.api_key, timeout_seconds=config.timeout_seconds)
            if args.live
            else OfflineClient()
        )
        try:
            report = run(client, args.trials)
        finally:
            client.close()
    except ConfigurationError as exc:
        print(str(exc))
        return 2
    report["mode"] = "live" if args.live else "offline"
    if args.output:
        args.output.mkdir(parents=True, exist_ok=True)
        stamp = dt.datetime.now(dt.timezone.utc).strftime("%Y%m%d_%H%M%S")
        (args.output / f"navigator_{stamp}.json").write_text(json.dumps(report, indent=2) + "\n")
    print(json.dumps(report, indent=2))
    return 0 if all(r["success"] for r in report["trials"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
