# Milestone 1, Step 3 — hybrid Nebius/NVIDIA Nemotron boundary

## Architecture and decisions

Production is a hybrid, NVIDIA-only system:

1. NVIDIA audio and speech models run locally on the Jetson.
2. A future local selector may create only a short, ephemeral text context.
3. That bounded text—not audio and not a full transcript—is sent over HTTPS to
   NVIDIA Nemotron on Nebius Token Factory.
4. The returned short cue is validated locally before any future TTS use.

This milestone implements and tests items 2–4 using synthetic text. It does
not implement audio capture, VAD, speaker enrollment, speaker attribution,
ASR, hesitation detection, TTS, or session storage.

The cloud boundary uses the standard-library HTTP client and an injectable
transport. This keeps the policy and parsing logic independently testable and
avoids adding an SDK dependency. Configuration rejects non-HTTPS endpoints,
hosts outside `nebius.com`, and any model ID that is not both in the `nvidia/`
namespace and named Nemotron.

The default endpoint and model are:

- `https://api.tokenfactory.us-central1.nebius.com/v1`
- `nvidia/nvidia-nemotron-3-nano-30b-a3b`

The bounded context permits at most four turns, 240 characters per turn, and
800 characters total. The client has no bytes/audio input. Benchmark reports
retain only configuration, timing, request sizes, token counts, schema status,
and a content-free failure class. They exclude prompts, cues, response bodies,
authorization headers, API keys, recordings, and transcripts.

The prior local Nemotron benchmark remains for historical reproducibility but
is superseded as the production LLM direction. Its returned Jetson report
failed the resource gate: minimum available RAM was approximately 294 MiB,
maximum server RSS was 4.47 GiB, and swap grew by approximately 361 MiB.

## Files changed

- `cowingman/__init__.py`
- `cowingman/hybrid_nemotron.py`
- `scripts/hybrid_nemotron_benchmark.py`
- `tests/test_hybrid_nemotron.py`
- `.env.example`
- `.gitignore`
- `README.md`
- `RUN_ON_JETSON.md`
- `docs/milestones/milestone1_step3.md`

## Mac validation commands

Run from macOS without an API key:

```sh
cd "/Volumes/Projects/Cowingman-jetson"
python3 -m unittest discover -s tests -v
python3 scripts/hybrid_nemotron_benchmark.py --dry-run --trials 3
```

No live Token Factory call belongs in Mac validation for this gate.

## Jetson validation commands

After resolving the real removable-drive path:

```sh
cd "/path/to/Co-Wingman-jetson"
python3 -m unittest discover -s tests -v
read -rsp "Nebius API key: " NEBIUS_API_KEY && printf '\n'
export NEBIUS_API_KEY
python3 scripts/hybrid_nemotron_benchmark.py --live --trials 3
unset NEBIUS_API_KEY
```

Do not run the obsolete local llama.cpp/Nemotron benchmark for this step.

## Expected report filenames

Return a timestamp-matched pair:

- `reports/hybrid_nemotron_YYYYMMDD_HHMMSS.json`
- `reports/hybrid_nemotron_YYYYMMDD_HHMMSS.md`

Generated reports are ignored by default. Do not commit them until their
metadata has been reviewed.

## Acceptance criteria

The Jetson gate passes only when all of the following are true:

- the full repository test suite passes on the Jetson;
- the report says `mode: live` and `environment.is_jetson: true`;
- the configured endpoint is HTTPS under `nebius.com`;
- the configured model ID is NVIDIA Nemotron;
- exactly three synthetic bounded-text requests succeed;
- all three responses match the strict cue JSON schema;
- every request completes within five seconds;
- the report states that no raw audio, full transcript, prompt/cue content, or
  credential was recorded;
- both report files parse/render and share one timestamp;
- manual report review finds no key, identifier, private recording, or full
  transcript.

A successful Mac dry run is not acceptance. A live report from a non-Jetson
host is also not acceptance, even if requests succeed. Review is required
before advancing.

## Known limitations

- This milestone proves only the bounded cloud request path; it does not prove
  audio quality, speaker attribution, end-to-end latency, or concurrent Jetson
  resource feasibility.
- It cannot determine semantically whether a short text fragment was copied
  from a longer transcript. The future local selector must enforce the same
  policy before constructing `BoundedContext`.
- Nebius service availability, model catalog, account region, rate limits, and
  pricing are external and may change. A permitted NVIDIA Nemotron override
  can be supplied with `NEBIUS_MODEL`; the report records the selected ID.
- The five-second gate measures request/response duration, not complete audio
  capture-to-playback latency.
- Synthetic prompts do not establish quality on private, real conversations.
- No retry is used, deliberately, so the report exposes service/network
  failure rather than hiding it.

## Gate

Stop after the Jetson run. Return both report files for review before any
local audio/speech milestone begins.
