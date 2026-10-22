# Experimental model-assisted recovery

The original project's CNN+LSTM model can now participate in recovery requests
with `--disfluency-assist`. It runs locally in the existing speech worker, using
Keras's PyTorch backend on CPU. NeMo still transcribes locally; only selected text
is sent to NVIDIA Nemotron through NaviGator.

This is the custom research model from
[Co-Wingman-AIS-Project-Original](https://github.com/Co-Wingman-AI/Co-Wingman-AIS-Project-Original),
pinned to revision `03288414382def0356e44ae1c4aca4d0fd6ad35d` and a SHA-256 digest.
It is not an NVIDIA model; this explicit experimental option is separate from the
default NVIDIA model path. Its training labels are stuttering/control. The older
app calls outputs “Anxious” and “Calm”, but those labels do not establish anxiety
recognition. The integration therefore labels its output as speech disfluency.
The existing evaluation and limitations are in [PROFILING_AND_SHADOW.md](PROFILING_AND_SHADOW.md).

## Install and launch on the Jetson

First complete the standard NeMo/microphone setup in [RUN_ON_JETSON.md](../RUN_ON_JETSON.md)
and configure `NAVIGATOR_TOOLKIT_API_KEY`. Keep the working Jetson CUDA PyTorch.
In that same virtual environment, from the repository root:

```bash
python3 -m pip install -e '.[shadow]'
python3 scripts/prepare_disfluency_model.py
python3 -m cowingman --disfluency-assist
```

The flag defaults to `models/disfluency.keras`; an explicit model path is accepted
only if the file matches the pinned checksum. Downloads happen only in the setup
command. No timing file, rolling summary, or AWS storage is enabled by this flag.

## Behavior and controls

- The model scores five seconds of local audio every four seconds, using a
  one-second tail from the previous capture. The initial window is not scored.
- Two consecutive scored windows at or above 0.5 provide eligibility. This fixed
  threshold is experimental and is not an anxiety probability.
- A detected pause must follow within eight seconds of eligible speech. Pause
  detection uses at least one second of speech followed by three seconds of
  sustained low energy. A high score alone never requests a cue.
- Low scores, gaps, invalid values, and expired evidence clear eligibility.
  Results processed more than eight seconds after capture ends are rejected.
- Requests share the existing 30-second cooldown with manual and pause requests.
  Scores and raw audio are not included in the remote payload.
- Enter/`:cue` always remains available. `:assist off` disables automatic requests;
  `:assist on` re-enables the selected model-plus-pause mode. It does not switch to
  silence-only assistance. `--pause-assist` and `--disfluency-shadow` cannot be
  combined with `--disfluency-assist`.
- Normal model-assisted mode keeps the four-fragment/240-character-per-fragment/
  800-character-total text boundary. Capture continues during ASR, but stops for
  a cue; request context is discarded. Use `:listen` to resume afterwards.
- Adding `--rolling` explicitly selects its larger text budget, continued listening
  after cues, and minute summary calls. It is optional and visual-output only.
- If the model cannot load or fails, automatic model assistance stops. ASR and
  manual requests continue; there is no fallback to silence-only auto requests.
  Install/repair the optional dependencies or model, then use `:listen` to retry.

Optional numeric diagnostics use `--timings private/model-assist-01.jsonl` with a
new filename. `scripts/timing_report.py` reports `model_assist_trigger` requests
alongside scores. Reports contain no speech, prompt, or cue text, but do reveal
session activity. Without `--timings`, no score report is written.

## Verification limits and demo fallback

Mocked tests cover score gating, capture-to-cue routing, stale events, model
failures, cooldown, default text bounds, no audio/score payload, and clean closure.
Real Jetson throughput, false triggers, missed triggers, cue usefulness and the
combination of live ASR plus classifier still require supervised device testing.
The microphone can capture either participant. This model cannot identify the
user, diagnose anxiety, or establish that someone needs help. Use the manual cue
control for a dependable presentation.

Network fallback: `python3 -m cowingman --typed --offline`.
Microphone/model fallback with real NaviGator: `python3 -m cowingman --typed`.
Exit with `:quit` or Ctrl-C. Local speech processes and their buffers are released.
