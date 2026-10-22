#!/usr/bin/env python3
"""Summarize local timing JSONL without displaying conversation or cue text."""

import argparse
from collections import defaultdict
import json
import math
from pathlib import Path
import statistics
import sys

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cowingman.timing import STAGES


def summarize(path, *, windows=False):
    groups = defaultdict(list)
    failures = defaultdict(int)
    scores = []
    drops = 0
    timeline = []
    origin = None
    with Path(path).open() as file:
        while True:
            line = file.readline(4097)
            if not line:
                break
            if len(line) > 4096:
                raise ValueError
            row = json.loads(line)
            stage, duration = row["stage"], row["duration_ms"]
            if (
                stage not in STAGES
                or type(duration) not in (int, float)
                or not math.isfinite(duration)
                or duration < 0
            ):
                raise ValueError
            groups[stage].append(duration)
            if origin is None:
                origin = row["start_monotonic"]
            failures[stage] += int(not row["ok"])
            if stage == "audio_drop":
                drops += int(row["count"])
            if stage == "disfluency_score":
                score = row["score"]
                if type(score) not in (int, float) or not 0 <= score <= 1:
                    raise ValueError
                scores.append(score)
            if windows and (
                stage in {"disfluency_score", "model_assist_trigger"} or stage.startswith("review_")
            ):
                at = row.get("window_start", row["start_monotonic"])
                if type(at) not in (int, float) or not math.isfinite(at):
                    raise ValueError
                item = {"stage": stage, "elapsed_seconds": round(at - origin, 3)}
                if stage == "disfluency_score":
                    item["window_seconds"] = 5
                    item["score"] = row["score"]
                timeline.append(item)
    report = {"stages": {}, "dropped_windows": drops}
    for stage, values in sorted(groups.items()):
        ordered = sorted(values)
        report["stages"][stage] = {
            "count": len(values),
            "failures": failures[stage],
            "p50_ms": round(statistics.median(values), 3),
            "p95_ms": ordered[max(0, math.ceil(0.95 * len(values)) - 1)],
            "max_ms": max(values),
        }
    if scores:
        report["shadow"] = {
            "scored_windows": len(scores),
            "mean_score": round(statistics.mean(scores), 4),
            "at_or_above_0_5": sum(s >= 0.5 for s in scores),
            "anxiety_inference": False,
            "automatic_cue_trigger": bool(groups.get("model_assist_trigger")),
            "model_assisted_requests": len(groups.get("model_assist_trigger", [])),
        }
    if windows:
        report["review_timeline"] = sorted(timeline, key=lambda item: item["elapsed_seconds"])
    return report


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("report", type=Path)
    parser.add_argument(
        "--windows",
        action="store_true",
        help="include numeric shadow windows and fixed review markers",
    )
    args = parser.parse_args()
    try:
        print(json.dumps(summarize(args.report, windows=args.windows), indent=2))
        return 0
    except (OSError, ValueError, KeyError, TypeError):
        print("Cannot read timing report; check its path and format.")
        return 2


if __name__ == "__main__":
    raise SystemExit(main())
