# Measure rolling mode and review experimental disfluency scores

These additions measure the existing design. Four-second ASR windows, manual/pause
cue triggers and the 256-token production cue budget are unchanged. Overlapping
ASR, persistent NaviGator connections and shorter capture windows have not been
enabled without device measurements. S3 already uses boto3's reusable client;
creating a bucket does not change NaviGator HTTPS connections.

## Baseline on the Jetson

Run from the repository in the working Jetson virtual environment, with the
existing API key and verified local ASR model configured:

```bash
git pull --ff-only
python3 -m cowingman --rolling --pause-assist --show-input \
  --portfolio private/portfolio.json --timings private/baseline-01.jsonl
```

Have a two-minute conversation, request at least two manual cues and allow a pause
cue. Type `:quit` and press Enter. Each new run needs a new report filename; an
existing file is never overwritten. Then inspect:

```bash
python3 scripts/timing_report.py private/baseline-01.jsonl
```

Events have UTC timestamps, monotonic start/end times, duration, success status
and numeric metadata only. They contain no audio, transcript, portfolio passage,
prompt, cue, key or exception body. Reports are local, permission 0600, opt-in;
use `private/` to keep them out of Git. They are not sent to AWS. Delete them when
review is complete. If disk writes fail, assistance continues but the report may
be incomplete. Worker termination can leave an unfinished stage unrecorded.

| Stage | Meaning |
| --- | --- |
| `asr_verify`, `asr_load` | Archive hashing, then ASR initialization/loading |
| `microphone_open`, `capture` | Stream opening and a completed audio window |
| `capture_age` | Age of a window when the worker receives it, including its four-second capture duration |
| `asr_inference` | Local recognition for one voiced window |
| `audio_drop` | An older queued window was discarded; sum of `count` |
| `network_worker_start` | Process startup until the request worker begins |
| `network_setup` | DNS, TCP and TLS connection setup combined |
| `server_response` | Waiting for HTTP status/headers after sending the request |
| `response_read` | Reading the bounded response body |
| `transport`, `validation`, `cue_total` | Entire HTTP call, cue parsing, and application request handling |
| `summary_total`, `s3_upload`, `s3_load` | Summary work and explicit AWS operations |
| `tts` | Optional sequential TTS, including its worker/model setup and playback |

Several stages are nested; do not add all durations together. `server_response`
includes network wait; it cannot separate server queueing from model inference.
`cue_total` is not latency from the instant you hesitate. TTS is unavailable in
rolling mode, so measure it separately with `--tts --timings ...` if needed.
The summary and cue calls still block the application command loop while they run;
the rolling speech process continues capture/decoding, subject to its bounded queue.

Compare median and p95, not a single run. Slow ASR plus drops suggests recognition
workload pressure; long capture age suggests backlog; long server-response time
suggests remote/network wait. Faster hardware timings do not establish better cues.

## Experimental shadow detector

Source: [Co-Wingman-AI/Co-Wingman-AIS-Project-Original](https://github.com/Co-Wingman-AI/Co-Wingman-AIS-Project-Original),
revision `03288414382def0356e44ae1c4aca4d0fd6ad35d`. The explicit setup script downloads
the included model and checks its pinned SHA-256 before loading it. Weights are
not redistributed in this repository. Downloads never occur inside a conversation.

The training labels are stuttering/control, not anxiety. Reported test accuracy is
59.27% and stuttering recall about 53% at threshold 0.5. The original app's 0.35
threshold does not have that evaluation. The training split is per clip, not
explicitly grouped by speaker. Generalization to your voice, microphone and setting
is unverified. The score is not a calibrated probability of anxiety or a diagnosis.

Keep your existing Jetson CUDA PyTorch. Install only the optional adapter dependencies:

```bash
python3 -m pip install -e '.[shadow]'
python3 -m cowingman.speech_dependencies
python3 scripts/prepare_disfluency_model.py
python3 -m cowingman --rolling --show-input --portfolio private/portfolio.json \
  --timings private/shadow-01.jsonl --disfluency-shadow models/disfluency.keras
```

This run omits `--pause-assist` so only Enter/`:cue` requests cues. You can add it
later to compare existing pause assistance; shadow scores never cause cue requests.
The extra includes a setuptools compatibility bound for Librosa 0.10.1's
`pkg_resources` import. For an existing broken environment, follow the
[repair and staged retest](../RUN_ON_JETSON.md#repair-missing-pkg_resources-during-model-restoration).
The adapter uses Keras 3.10's PyTorch backend on CPU in the local speech process.
It reuses the Jetson's PyTorch rather than installing TensorFlow. Initialization
warms feature extraction and inference before opening the microphone. A dependency,
model or scoring failure disables the detector with a notice; ordinary ASR continues.

ASR still receives four-second windows. The classifier receives five-second windows
every four seconds by retaining one extra second of local audio. The first window,
unvoiced windows and discontinuities are not scored. It reproduces upstream MFCC +
delta features (80 by 200) at our fixed 16 kHz rate. Window duration, sample rate and
microphone differences need real-data validation; this is not equivalence to the
training distribution. Audio stays RAM-only and is cleared after use. This adds a
one-second retained tail and a temporary five-second classifier buffer. Classification
is sequential with ASR in its worker; it may increase processing time and dropped
windows, while the separate capture thread continues. No speaker identity is inferred.

For a first review, take turns with your friend. At the start of each segment type
one of these commands and press Enter, then continue that condition for 10–15 seconds:

1. `:mark quiet` — both stay quiet.
2. `:mark fluent` — you speak normally.
3. `:mark stuck` — act an unfinished answer, repetition or hesitation.
4. `:mark partner` — only your friend speaks.

These are self-reported review markers, not ground-truth diagnoses. They do not
change microphone capture, cue behavior or model input. Repeat with ordinary
conversation, then `:quit`. Review numeric scores against the marked intervals:

```bash
python3 scripts/timing_report.py private/shadow-01.jsonl --windows
```

The timeline reports each five-second scoring interval's start relative to the
report and the marker times. A score crossing 0.5 is only a review count; it does
not mean a cue was needed. Windows spanning two conditions need manual judgment.
Repeated words can occur without anxiety, and a friend's speech can influence the
score. Real validation requires consenting, labeled examples and held-out speakers,
including false alarms, missed events and useful-cue timing. This smoke test does
not validate an automatic trigger. The separately opted-in
[model-assisted mode](MODEL_ASSIST.md) remains experimental and requires supervised
evaluation; shadow mode itself never triggers cues.

## Compare cue token budgets explicitly

```bash
python3 scripts/token_benchmark.py --live --rounds 1 > private/token-budget-01.json
```

This makes 12 synthetic trials per round, up to 24 requests including shortening.
It compares 256, 192, 128 and 96 tokens across three synthetic cases, including a
fictional portfolio. Trial order is deterministically shuffled to reduce order
bias. It does not read your real portfolio or conversation. Reports include valid
responses, original response validity, declines, truncation, shortening, fallback,
cue length and total time. No model output is logged. Summary requests retain their
separate 512-token budget. The production cue limit remains 256.

One round is a smoke test, not evidence of reliability. Repeat across times and
review useful wording in separate controlled interactive tests. Do not choose a
lower budget solely because its failed/truncated requests completed faster.

## Verification scope

Cloud tests cover bounds, timings, failure handling, disabled shadow triggers,
synthetic token comparisons and mocked S3 behavior. A CPU smoke test loads the real
pinned model and scores synthetic audio. Neither test proves Jetson throughput,
disfluency accuracy, live NaviGator compliance, or real AWS upload/retrieval.
