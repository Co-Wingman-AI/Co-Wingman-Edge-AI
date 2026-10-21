# Co-Wingman handoff

Updated October 20, 2026. Start with the root README and RUN_ON_JETSON.md.
This repository is the source of truth for continuing work in another chat/account.
Do not rely on credentials, chat history, or generated files from a previous session.

## Current product

`python3 -m cowingman` launches the application. It connects local NVIDIA ASR,
bounded expiring context, an explicit Enter / `:cue` trigger, UF NaviGator Nemotron,
strict structured response checks, terminal display, and optional sequential local
NVIDIA TTS. Typed/live and typed/offline paths share the application orchestration.
Optional pause assistance detects speech energy followed by silence; it makes no
anxiety/stress or speaker-identity claim and is disabled by default.

The main runtime requires only `NAVIGATOR_TOOLKIT_API_KEY` for remote inference,
uses `https://api.ai.it.ufl.edu/v1/chat/completions`, and allows only
`nemotron-3-nano-30b-a3b`. Never fall back to an unapproved model, Nebius,
remote audio transcription, or local Nemotron.

## Validation performed in this implementation session

- macOS arm64, Python 3.14.7: complete unittest suite passed.
- Offline end-to-end demo and interactive typed/offline subprocess flow passed.
- Real pseudo-terminal test verified hidden input, visible cue, Ctrl-C exit, and
  terminal echo restoration. Partial pipe input no longer blocks the event loop.
- Provider mocks verified endpoint/model restrictions, correct auth, bounded text,
  audio rejection, malformed/unsafe output rejection, network errors, rate limits,
  response bounds, deadlines, and content-free reporting.
- Local speech interfaces were tested with mocks, including device failures,
  direct tensor decoding return shapes, model integrity, process termination,
  memory-independent fallback, and TTS failure handling.
- Python 3.10 grammar, Ruff lint/format checks, whitespace checks, and tracked/new
  source credential/artifact pattern scan passed. Complete changes were reviewed.
- CI configuration runs the same offline checks on Linux Python 3.10/3.12/3.14.
  A configured workflow is not itself evidence that a remote run succeeded.

No real NaviGator key was available. No physical Jetson, microphone, downloaded
speech model, CUDA inference, or local speech playback was exercised here. The
historical Jetson local-LLM evidence is distinct from current application testing.

## Continue with real-device verification

The continuation session validated Linux x86_64 with Python 3.12.14: all 52
unittests passed, including typed/offline subprocess and real pseudo-terminal
flows. The offline demo, Ruff 0.14.1 lint/format, repository hygiene/syntax scan,
dependency consistency, and diff whitespace checks also passed. Unsupported ASR
text now stops audio and discards context while preserving the typed fallback;
regression coverage verifies pending speech cannot leak into the next request.
The README and Jetson clone commands now use Co-Wingman-AI/Co-Wingman-Edge-AI.
No real UF key, Jetson, CUDA, microphone, or speech weights were available in this
cloud continuation. Those remaining live-device checks still require an operator.

A subsequent Jetson health-check attempt reported the old generic invalid-cue
error. Its exact cause is unconfirmed without a new request. The client now asks
for non-reasoning output using NVIDIA's documented Nano vLLM option, allows 256
output tokens, and reports content-free error categories for truncation, empty
content, refusal/tool calls, malformed envelopes, and invalid cue validation.
All 54 offline tests passed, including request-option and diagnostic privacy
coverage. The operator subsequently reported a successful live health check;
see the device results below. The original failure's exact cause is unconfirmed.

### Operator-reported Jetson results

The operator supplied terminal output from the physical device confirming:

- JetPack 6.2.1+b38, L4T 36.4.7, Python 3.10.12, CUDA toolkit 12.6.
- Live NaviGator health check returned a valid approved-model cue in 0.86 seconds.
- Bluetooth handsfree microphone exposed a 16 kHz mono input through PulseAudio.
  Two three-second in-memory capture tests measured RMS levels 0.0607 and 0.0108,
  with no audio overflow. These establish a signal, not ASR accuracy.
- An isolated `.venv` installed torch 2.8.0 and torchaudio 2.8.0 from the Jetson
  community CUDA 12.6 index. CUDA was available, the GPU identified as Orin, and
  an actual CUDA tensor calculation passed.
- With those versions constrained and NumPy below 2, `nemo_toolkit[asr]==2.4.0`
  installed. Importing `ASRModel` and repeating the CUDA calculation passed.
- `python3 scripts/prepare_speech_models.py --asr` downloaded the NVIDIA Conformer
  CTC Small archive (49.1 MB) and reported the archive and integrity manifest ready.
- After the speaker battery ran out, CMF Buds were paired, trusted, and connected
  in handsfree mode. The PulseAudio input was index 25. A quiet/speaking capture
  test measured RMS 0.0/0.0446 with no overflow; no audio files were created.
- After launching the microphone application and following the spoken test and
  explicit Enter-trigger instructions, the operator reported that a cue appeared.
  This is the first operator-reported live microphone-to-cue success. No actual
  transcript or returned cue text was supplied or saved in this handoff.

These results come from operator-provided console output and confirmation, not
agent access to the Jetson. Launch `python3 -m cowingman` in that `.venv`, with the key
exported and `COWINGMAN_ASR_MODEL_PATH` set to the absolute `models/asr.nemo` path.
Recheck audio indices after device reconnection; the tested PulseAudio input was
index 25 and the Bluetooth microphone was selected as the default PulseAudio source.
Next, test another cue after `:listen`, then clean shutdown with `:quit`.
Repeated requests/resource cleanup, measured ASR accuracy/performance, microphone
disconnect recovery, and optional TTS still need device validation.

The next operator log showed multiple transcription windows, an empty-context
request, typed fragment acceptance, clean-stop status, and a later generic cue
validation failure. It does not establish repeatable speech-only cue generation
or measured resource cleanup. To diagnose it, the client prompt's ambiguous
`resume|clarify|respond` example was replaced with a valid single-intent example.
Validation now reports fixed, specific categories without any response content;
all original rejection rules and limits remain. The speech UI now distinguishes
accepted fragments from empty ASR output and explains `:listen` after an empty or
failed request. All 57 cloud tests, lint/format checks, offline demo, repository
scan, and diff whitespace checks passed. The operator must pull and repeat a
fresh spoken request, waiting for “Speech fragment accepted privately” first.
The precise cause of the previous rejected response remains unknown.

Follow RUN_ON_JETSON.md. Confirm the actual JetPack version and compatible NVIDIA
torch/torchaudio before installing NeMo. Test `--health-check` with the operator's
own UF key; never send it to a chat. Then exercise real microphone capture, ASR
accuracy/latency, repeated cue requests, fresh-context retry, disconnect recovery,
memory headroom, and Ctrl-C cleanup. Verify optional TTS separately. Record only
content-free measurements locally; generated reports remain ignored.

The small NVIDIA ASR and NeMo 2.4.0 setup has passed the operator's installation,
import checks, and reported first live cue run; no ASR accuracy or performance
measurements were collected. If a dependency
cannot be resolved safely on ARM, use `--typed` with NaviGator for the presentation.
The offline fallback needs neither key, network, microphone, nor model files.

Known limitations: four-second windowed capture pauses during ASR; requesting a
cue discards an unfinished window; ASR reloads on `:listen` after each cue; no
biometric enrollment/diarization; optional energy/silence assistance has false
positives; schema checks are not complete semantic moderation; deletion releases
application references, not forensic erasure or UF server-side deletion.

## Safe development continuation

The user explicitly authorized committing and pushing tested changes during this
session. Read current instructions in a new session rather than assuming that
permission extends to unrelated work. Preserve local changes. Keep the one
application entry point, NVIDIA-only production model choices, bounded context,
manual trigger, and working offline fallback. Do not revive archived setup steps.
Never commit `.env`, keys, model weights, audio, transcripts, or generated reports.

```sh
git status --short
python3 -m unittest discover -s tests -v
python3 -m cowingman --offline --demo
python3 scripts/check_repository.py
ruff check .
ruff format --check .
```

The operating docs describe exact commands and recovery actions; archive/ only
contains prior research. The historical local-LLM script is intentionally disabled
as an executable, while its parsing/resource regression tests remain.
