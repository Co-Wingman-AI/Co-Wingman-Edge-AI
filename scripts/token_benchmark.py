#!/usr/bin/env python3
"""Explicit live synthetic comparison of cue token limits, with no content logs."""

import argparse
import json
from pathlib import Path
import random
import sys
import time

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from cowingman.config import Config
from cowingman.context import BoundedContext, ContextTurn
from cowingman.errors import CloudRequestError, ConfigurationError
from cowingman.portfolio import Portfolio
from cowingman.provider import NavigatorClient, deadline_transport

BUDGETS = (256, 192, 128, 96)
# Synthetic project facts only, never the operator's portfolio or conversation.
CASES = (
    (("partner", "Why keep audio local?"), ("user", "It protects privacy because")),
    (("partner", "What did you build in the fictional demo?"), ("user", "I built a demo using")),
    (("partner", "Which step comes next?"), ("unknown", "We finished the prototype and")),
)


def run(config, rounds, factory=NavigatorClient, transport=deadline_transport):
    schedule = [
        (budget, case) for _ in range(rounds) for case in range(len(CASES)) for budget in BUDGETS
    ]
    random.Random(42).shuffle(schedule)
    results = []
    for budget, case in schedule:
        finishes = []

        def observed_transport(url, headers, payload, timeout):
            response = transport(url, headers, payload, timeout)
            # Only retain an enum, never server/model text.
            try:
                reason = response["choices"][0].get("finish_reason")
            except (KeyError, IndexError, TypeError, AttributeError):
                reason = None
            finishes.append(
                "length" if reason == "length" else "stop" if reason == "stop" else "other"
            )
            return response

        client = factory(
            config.api_key,
            timeout_seconds=config.timeout_seconds,
            base_url=config.base_url,
            model=config.model,
            max_tokens=budget,
            transport=observed_transport,
            portfolio=Portfolio(
                ("Fictional demo: I built a demo using Python and SQLite to store notes locally.",)
            )
            if case == 1
            else None,
        )
        context = BoundedContext.from_turns([ContextTurn(*turn) for turn in CASES[case]])
        row = {"max_tokens": budget, "case": case, "valid": False}
        started = time.monotonic()
        try:
            cue, metrics = client.request_cue(context)
            row.update(
                valid=True,
                offered=cue.should_offer,
                first_response_valid=metrics["response_schema_valid"],
                shortened=metrics["cue_shortened"],
                fallback=bool(metrics.get("portfolio_fallback")),
                cue_characters=len(cue.cue),
                cue_words=len(cue.cue.split()),
            )
        except CloudRequestError:
            pass
        finally:
            row.update(
                duration_ms=round((time.monotonic() - started) * 1000, 3),
                responses=len(finishes),
                truncated="length" in finishes,
            )
            client.close()
            context = cue = None
        results.append(row)
    return {"synthetic_only": True, "quality_review_required": True, "trials": results}


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--live", action="store_true", help="required; sends paid synthetic API requests"
    )
    parser.add_argument(
        "--rounds", type=int, default=1, help="12 trials per round, up to 24 calls with repairs"
    )
    args = parser.parse_args()
    if not args.live or not 1 <= args.rounds <= 5:
        parser.error("Use --live and 1–5 rounds. Each round makes 12 trials, possibly 24 requests.")
    try:
        report = run(Config.load(), args.rounds)
    except ConfigurationError as exc:
        print(str(exc))
        return 2
    print(json.dumps(report, indent=2))
    return 0 if all(row["valid"] for row in report["trials"]) else 1


if __name__ == "__main__":
    raise SystemExit(main())
