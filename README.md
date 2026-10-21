# Co-Wingman

## Project website

An illustrated, interactive project showcase is in [website/](website/).
It includes scripted conversation examples, the edge–cloud architecture, team,
and prototype boundaries. See [website preview and GitHub Pages setup](docs/WEBSITE.md)
for publishing instructions; the Pages workflow uploads only the public site.

## Continuing work across devices

Before editing, read [WORK_LOG.md](WORK_LOG.md), then inspect `git status` and the
organization remote. Follow [AGENTS.md](AGENTS.md) to preserve work and append a
privacy-safe change/verification entry before pushing. The log contains project
handoff metadata only; Co-Wingman never logs conversation content.

Co-Wingman helps a person who gets stuck in conversation request a short recovery
cue. It is designed for an NVIDIA Jetson Orin Nano 8 GB, with local speech
recognition and bounded text inference through UF NaviGator AI Toolkit.

**Launch: `python3 -m cowingman`.** Press Enter or type `:cue` to request a cue.
The terminal displays component status and a short cue. A Mac can run the same
application with visible typed input, or a fully offline synthetic provider.

The operator has verified Jetson microphone capture, local NeMo ASR, NaviGator
access, and an end-to-end cue. Conversation accuracy, sustained performance, and
optional TTS still need measurement. See the handoff for the recorded setup.

## Install and try it

Python 3.10 or newer is required. Typed/offline modes use only the standard library:

```sh
git clone https://github.com/Co-Wingman-AI/Co-Wingman-Edge-AI.git
cd Co-Wingman-Edge-AI
python3 -m cowingman --offline --demo
python3 -m cowingman --typed --offline
```

The first command runs a synthetic example and exits. In the interactive fallback,
enter a short fragment, press Enter to accept it, then press Enter again or enter
`:cue`. Typed mode shows entered text; add `--hide-input` for hidden entry. The cue
appears only when stdout is a terminal; redirected output contains status only.
Use `:quit`, Ctrl-C, or end-of-input to exit. A cue clears after 20 seconds.

Optional editable install: `python3 -m pip install -e .` inside a virtual environment.
Run from the repository root if you have not installed it.

## Live NaviGator access

Create a key in [UF NaviGator AI Toolkit](https://api.ai.it.ufl.edu/ui) with access to
`nemotron-3-nano-30b-a3b`. Follow [UF's key setup instructions](https://docs.ai.it.ufl.edu/docs/navigator_toolkit/getting_started/quickstart/).
Enter the key without putting it in shell history (works on macOS and Linux):

```sh
export NAVIGATOR_TOOLKIT_API_KEY="$(python3 -c 'import getpass; print(getpass.getpass("UF NaviGator key: "))')"
python3 -m cowingman --health-check
python3 -m cowingman --typed
```

The health check sends one **synthetic** bounded request and validates the result;
it does not print the cue. A valid key must also have access to the exact model.
Requests disable Nemotron reasoning using `chat_template_kwargs.enable_thinking`
and allow 256 output tokens. They request strict `json_schema` output with a
nonempty cue string, a 160-character limit, a 12-word pattern, three required
fields, and no extra fields. Local validation still checks every response.
The non-reasoning option follows [NVIDIA's Nano vLLM recipe](https://github.com/NVIDIA-NeMo/Nemotron/blob/main/usage-cookbook/Nemotron-3-Nano/vllm_cookbook.ipynb).
UF's acceptance of the schema and non-reasoning options must be confirmed with
the health check. HTTP 400/422 reports rejected options; there is no automatic
fallback to unconstrained JSON or retry. A valid response alone does not prove
the backend enforces every schema constraint.
To run a scripted live example: `python3 -m cowingman --typed --demo`.
After the demonstration: `unset NAVIGATOR_TOOLKIT_API_KEY`.

NaviGator replaces Nebius in the runtime. It exposes an OpenAI-compatible API
on UF-managed infrastructure, so the operator needs a UF Toolkit key, not a direct
HiPerGator allocation, GPU job, Slurm script, or model server. The only approved
remote model is `nemotron-3-nano-30b-a3b`; there is no automatic model substitution.
Nebius credentials and environment variables are not used.

## Architecture

```text
USB personal microphone → RAM-only 16 kHz mono capture → local NVIDIA NeMo ASR
                                                        ↓
hidden typed fallback ───────────────────────→ rolling recent fragments
                                                        ↓
Enter / :cue (or opt-in local pause assistance) → bounded selection, clear store
                                                        ↓
HTTPS api.ai.it.ufl.edu/v1/chat/completions → NVIDIA Nemotron → strict JSON checks
                                                        ↓
terminal cue → optional sequential local NVIDIA TTS → discard request state
```

The local model is NVIDIA Conformer CTC Small (about 13 million parameters).
Audio is captured in four-second windows; capture pauses during transcription.
Only a short suffix of each result enters the rolling store. This is a simple
windowed prototype, not a continuous streaming transcription service. Partial
words at window boundaries may reduce accuracy. It does not keep a full transcript.
Adjacent microphone windows are combined when they fit within the existing
240-character fragment bound, so a short exchange is less likely to lose its
opening question. Microphone text is labeled `unknown`, because local ASR does
not identify which participant spoke. The cue model is instructed to infer the
direction only from supported wording and produce an exact phrase the user can say.

The recorded Jetson is an Orin Nano on L4T 36.4.7. Earlier local Nemotron inference
left only about 294 MiB available memory and grew swap; the application never
loads a local LLM. Default output is visual. Optional FastPitch then HiFi-GAN TTS
runs in its own process **after ASR exits**, and FastPitch unloads before HiFi-GAN.
Audio remains paused after a cue; `:listen` resumes it. Model reloads trade speed
for predictable memory release. See [speech setup and limitations](docs/SPEECH.md).

## Operating modes and controls

| Task | Command |
| --- | --- |
| Jetson, live microphone + NaviGator | `python3 -m cowingman` |
| Live typed fallback, Mac or Jetson | `python3 -m cowingman --typed` |
| Live synthetic demonstration | `python3 -m cowingman --typed --demo` |
| Interactive offline typed fallback | `python3 -m cowingman --typed --offline` |
| Complete synthetic offline demonstration | `python3 -m cowingman --offline --demo` |
| Verify real API/model access | `python3 -m cowingman --health-check` |
| List microphone indices | `python3 -m cowingman --list-audio` |
| Import Honey's public portfolio snapshot locally | `python3 -m cowingman.portfolio` |
| Personalized typed cues | `python3 -m cowingman --typed --portfolio private/portfolio.json` |
| Optional local spoken cues | `python3 -m cowingman --tts` |
| Opt-in pause-triggered cues | `python3 -m cowingman --pause-assist` |
| Rolling minute, continuous listening and pause cues | `python3 -m cowingman --rolling --pause-assist --show-input` |

| Input while running | Effect |
| --- | --- |
| A short line, then Enter | Accept a local text fragment; visible in typed mode |
| Enter on an empty line, or `:cue` | Request a recovery cue |
| `:check` | Show local fragment counts and portfolio matches without an API call |
| `:partner short text` | Accept a typed partner fragment |
| `:listen` | Start/restart microphone processing, including after a cue |
| `:pause` | Stop microphone; rolling mode keeps recent context until expiry |
| `:clear` | Clear context/display and stop microphone |
| `:assist on` / `:assist off` | Enable/disable automatic pause-triggered requests |
| `:quit` or Ctrl-C | Release resources and exit |

For rolling conversation, add `--rolling`: four-second captures update a
60-second window, and cues no longer stop listening or clear the recent window.
Cues still require a pause (`--pause-assist`) or a manual request. A separate
minute timer summarizes recent text through NaviGator. Without S3, the summary is
RAM-only. To persist timestamped summaries and load them in later sessions, follow
[AWS summary setup](docs/AWS_SUMMARIES.md). `--summary-s3` enables rolling mode;
`--resume-summary` loads the latest record or a selected archived window.
This does not provide speaker identification or a complete transcript archive.

Optional [profiling and shadow testing](docs/PROFILING_AND_SHADOW.md) adds
`--timings private/run-01.jsonl` for numeric stage measurements and
`--disfluency-shadow models/disfluency.keras` for experimental local scores.
Shadow scores never trigger cues or infer anxiety. The model requires explicit
setup and is evaluated independently of pause assistance. Production cue tokens
remain 256; an explicit synthetic benchmark compares smaller budgets.

You can also [upload your portfolio to S3](docs/AWS_SUMMARIES.md) and start with
`--portfolio-s3 s3://YOUR_BUCKET/cowingman/jetson --aws-region us-east-1`.
The profile loads once into RAM; passage retrieval stays local. Uploads are explicit,
timestamped, and separate from conversation summaries.

`--typed` displays entered text by default. `--show-input` also enables visible
commands in microphone mode; `--hide-input` restores hidden testing. In rolling
mode, `:summary` updates/displays the summary, `:save` saves a partial window,
and `:forget` clears local memory without deleting saved S3 objects.

Pause assistance measures audio energy followed by sustained silence, with a
minimum speech duration and a 30-second cooldown. It can send bounded text
without another keypress when enabled. It is **not an anxiety or stress detector**:
quiet speech, noise, ordinary turn-taking, and microphone placement can produce
false or missed triggers. No medical or emotion inference is made. The explicit
trigger is the recommended presentation control.

Use a consenting operator's personal close-talk microphone. This version has no
biometric enrollment, speaker verification, or diarization; it cannot distinguish
the operator from another nearby voice. Do not claim it identifies an enrolled
speaker. See [privacy details](docs/PRIVACY.md).

For the best conversation cue, keep the exchange short and request the cue soon
after getting stuck. A single personal microphone can capture either participant,
but it cannot assign identities. For a controlled demo, `:partner short text`
provides an explicit partner fragment before the user speaks or types a response.

Optional [portfolio retrieval](docs/PORTFOLIO.md) selects up to two local passages
about your projects, experience, or education. With `--portfolio`, each request
can send up to 1,200 additional fact characters alongside the 800-character
conversation excerpt. The profile is explicitly imported into ignored local JSON;
it is not fetched during a conversation. This feature does not identify speakers.
With this option enabled, zero matching passages stops the cue request before
the API call. Add a question naming the topic and use `:check` before retrying.
Oversized model answers go through one shortening request to the same model.
Only its bounded draft is sent back; the result must pass the normal 12-word,
160-character, schema, safety, and echo checks. This works in manual and automatic
mode, with or without a portfolio. It replaces the oversized-answer portfolio
fallback: an invalid shortening result is withheld, never silently replaced.
The UI reports when shortening was used. It can add one API call and latency
within the original request timeout. Meaning preservation still needs live review.
Separately, an explicit Enter/`:cue` request can use a validated local portfolio
phrase if the original model response validly declines; the UI labels that fallback.
Automatic declines and declines during shortening are always respected.

## Privacy contract

- Raw microphone audio stays in the local speech process; it is never an API input.
- No audio recordings or full transcript archive are written. Opt-in S3 mode
  persists timestamped model-generated summaries, up to 1,200 characters each.
- Default context is at most four fragments / 800 characters. `--rolling` uses
  fifteen fragments / 3,600 characters over 60 seconds. Each fragment is at most
  240 characters. Rolling mode can add 1,200 historical summary characters per cue.
- Each request selects only that bounded excerpt. Default mode clears it on request;
  rolling mode retains it until expiry or explicit clearing. In both modes,
  and temporary request references are dropped on success, failure, cancellation,
  and shutdown. Transport failures are not retried. A length-only failure can
  trigger one shortening call containing only the bounded model-generated draft,
  without resending the conversation or retrieving more portfolio passages.
- With `--portfolio`, selected facts add at most 1,200 characters per request.
  The imported profile persists locally until deleted; conversation TTL does not
  apply to this reference file. Without the flag, no profile is loaded or sent.
- Model requests use only the exact approved NaviGator HTTPS host/path. Redirects
  and environment proxies are disabled for that client. Optional S3 requests use
  boto3's AWS endpoints/credential chain. Requests have timeouts and bounded data.
- Keys, authorization headers, transcripts, prompts, and cues are not logged or
  included in benchmark reports. Cue text is intentionally visible on the terminal
  and, with `--tts`, audible; redirected stdout suppresses it.
- UF receives the selected text. Local deletion cannot control UF's retention.
  RAM release is not forensic zeroization; OS swap, crash dumps, terminal capture,
  and screen recording are outside this application's guarantee.

The application reads environment variables only; `.env.example` documents them.
It does not load `.env` or commit secrets. Model downloads happen only in the
explicit setup script, never as a conversation-time fallback.

## Troubleshooting

| Symptom | Action |
| --- | --- |
| Missing/denied API key | Set `NAVIGATOR_TOOLKIT_API_KEY`; grant that key the approved model in UF Toolkit; run `--health-check`. |
| Timeout, rate limit, or service failure | Context is discarded. Wait, add fresh context, and request again; use `--typed --offline` for a network-free demonstration. |
| Output token limit or no cue text | Update with `git pull --ff-only`, then rerun `--health-check`. The service may still be using reasoning mode. Error messages distinguish truncation, empty output, refusal, and invalid cue format without exposing response text. |
| Cue validation failure | Length-only failures on offered cues get one bounded shortening request. If it fails, or another validation check fails, the cue is withheld. Add fresh context to try again. |
| Transcription runs but no context is ready | Wait for “Speech fragment accepted privately” before pressing Enter. “No words recognized” means ASR produced no usable text for that window. After a request, use `:listen` before speaking again. |
| Request options rejected | Confirm UF supports strict JSON Schema with string-length/pattern constraints and `chat_template_kwargs.enable_thinking=false` for the approved model. No automatic fallback or retry is made. |
| Microphone missing or disconnected | Connect a USB input; run `--list-audio`; export `COWINGMAN_AUDIO_DEVICE` to its numeric index. Try `:listen`; typed input remains usable after audio errors. |
| ASR dependency/model/CUDA failure | Follow [RUN_ON_JETSON.md](RUN_ON_JETSON.md); use `--typed` until the NVIDIA stack is verified. |
| Missing `pkg_resources` while restoring ASR; followed by an abstract `ASRModel` error | In the speech venv, run `python3 -m pip install 'setuptools>=68,<82'`, then `python3 -m cowingman.speech_dependencies`. Follow the [staged Jetson retest](RUN_ON_JETSON.md#repair-missing-pkg_resources-during-model-restoration). |
| Low memory | Close other GPU workloads. Check `free -h` and `tegrastats`; keep visual output. Startup needs 2 GiB available, with a 1 GiB runtime guard. These checks cannot guarantee no OOM. |
| No context yet | Wait through a capture/transcription window, or enter a fragment; then `:cue`. A request cancels any unfinished audio window. |
| Cue disappears in a pipe/file | Intentional privacy behavior; launch in a terminal. |
| Pause assistance triggers incorrectly | `:assist off`; use the manual cue trigger. Adjust `--speech-threshold` only with your own microphone. |

## Validation and handoff

```sh
python3 -m unittest discover -s tests -v
python3 -m cowingman --offline --demo
python3 scripts/check_repository.py
```

Optional lint/format checks use `python3 -m pip install -e '.[dev]'`, then
`ruff check .` and `ruff format --check .`. CI runs offline tests and these checks.
The [presentation runbook](docs/PRESENTATION.md), [Jetson launch guide](RUN_ON_JETSON.md),
and [handoff notes](docs/HANDOFF.md) contain the operating procedure and remaining
real-device checks. Earlier research is explicitly archived under `archive/`.
