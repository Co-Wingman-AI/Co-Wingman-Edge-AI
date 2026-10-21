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

- macOS arm64, Python 3.14.7: complete 52-test unittest suite passed.
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

The operator then supplied screenshots of successful solo, manual-conversation,
and automatic-pause cues. The conversation cues were valid but overly generic,
including requests for the partner to clarify rather than a useful continuation.
The likely cause was confirmed in code: every ASR fragment was labeled `user`,
although one microphone can capture either participant, and a longer exchange
could evict its opening question after four ASR windows. Microphone fragments are
now labeled `unknown`; adjacent ASR windows merge when the combined fragment stays
within 240 characters. The four-fragment, 800-character, and TTL bounds remain.
The system prompt now requests an exact phrase the user can say next, prioritizing
a supported answer or continuation over generic clarification while explaining
that unknown speech may contain either participant. These changes passed all 58
cloud tests; their effect on live cue usefulness still requires operator review.

The operator's controlled typed test still returned "Could you clarify the last
point?" The NaviGator dashboard independently confirmed successful requests. Code
inspection found that exact generic cue in the system prompt's sole JSON example,
which strongly anchored Nemotron's output. The prompt now forbids that fallback
when a topic or unfinished thought is available and uses two context-specific
continuation examples instead. All 58 tests and the offline demo pass; the revised
prompt still requires a live controlled-test result from the Jetson.

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

The operator confirmed the revised typed cue test produced the expected answer.
They then requested continuous personalized conversation assistance, speaker
identification, and accurate hesitation/stutter triggering, and supplied their
public portfolio URL. The portfolio stage is implemented with an explicit local
import (`python3 -m cowingman.portfolio`) and `--portfolio private/portfolio.json`.
The importer reads four pinned public HTML files from the portfolio's GitHub source.
Local keyword retrieval selects at most two 600-character passages; these are
separate from the existing 800-character conversation budget. Generated profiles
live in ignored `private/` and must never be committed. Documentation describes
the new persistence/transmission boundary. No runtime website requests are made.
Mocked integration tests verify payload contents; live personalized cue quality
still needs a Jetson check. Speaker enrollment, uninterrupted audio processing,
and improved disfluency detection remain unimplemented. Do not describe portfolio
retrieval as completing those capabilities.

The first live portfolio test returned the user's unfinished input verbatim
("i built orderflow using"). Reproducing the request locally with the pinned
profile confirmed two OrderFlow passages, including Spring Boot and Kafka, reach
the transport. This does not inspect the operator's actual network payload.
The prompt now requires new continuation content, recognizes "using"/"with" as
unfinished endings, and illustrates completion using an unrelated synthetic
project. The response boundary rejects multiword verbatim user/unknown echoes
after case/punctuation normalization. A content-free passage count now appears
in the UI; echo rejection also reports it when a profile is enabled. Failed
context is cleared with no automatic retry. Live generation quality remains
unverified after this change; mocked tests prove retrieval and echo rejection,
not the behavior of the hosted model.

The subsequent live typed test returned a relevant Kafka cue with two passages.
The microphone test then selected zero passages and copied the synthetic SQLite
example from the system prompt. The log showed no typed-fragment acknowledgement;
it cannot establish whether the intended partner question reached the context or
what ASR recognized. All concrete cue examples have now been removed from the
system prompt. With a profile enabled, zero matches stops before any API call
and reports the missing facts explicitly. General conversation without a profile
continues as before. The new `:check` command reports only current role counts and
matching-passage count, without consuming/refreshing context or making a request.
Use it after a typed partner question and before resuming microphone capture.
This is a retrieval diagnostic, not ASR accuracy or semantic grounding validation.

A subsequent spoken internship test reached the API but failed the combined
empty/type/length cue check. The old error cannot establish which condition failed.
Validation now distinguishes an empty string, a non-string field, and excess length;
response errors also include the selected portfolio-passage count without content.
The prompt explicitly requires a nonempty string even when should_offer is false,
one useful point, and no whole-passage copying. These changes improve diagnosis;
they are not evidence that live schema failures are resolved. Retest with a fresh
typed internship question to isolate generation from ASR before microphone tests.

The new typed internship test confirmed an overlong cue with two portfolio
passages supplied. Request formatting now uses strict `json_schema` instead of
`json_object`: cue is a nonempty string with maxLength 160 and a 1–12-word regex;
intent is an enum, should_offer is boolean, all fields are required, and extras
are forbidden. Local validation remains unchanged and rejects bad responses even
if the backend ignores the schema. UF compatibility is unverified: the next
operator step is `python3 -m cowingman --health-check` without the portfolio.
HTTP 400/422 reports unsupported request options with no fallback or retry.
Offline tests verify request shape and boundaries, not live constrained decoding.

The live endpoint accepted the strict schema yet again produced an overlong cue,
showing that request acceptance does not establish enforcement. Portfolio mode now
has a narrow local fallback for only word-count or character-count failures: it
selects one 4–12-word clause from the highest-ranked already-selected fact, runs
the normal parser and safety checks, makes no retry, and reports fallback use. It
does not repair empty, wrong-type, malformed, unsafe, echo, or unrelated output.
The response-schema-valid metric is false when fallback is used. This behavior is
covered by mocked tests but still needs a live typed portfolio retest.

The operator's next typed request returned a valid `should_offer: false`, so the
length-only fallback was not used. Manual and automatic triggers are now passed
separately to the provider: explicit requests ask for help immediately, while pause
assistance can decline. Manual portfolio requests can extract a local phrase when
the model validly declines; automatic requests do not override declines. The normal
decline text is not displayed or forced to true. The UI labels locally extracted
phrases, and there is still only one API call. Extraction now avoids arbitrary
trailing comma fragments (the old rule selected "and evaluation across 1,500+
images"); the internship candidate is the 12-word first-person CNN/SVM statement.
Length checks follow other schema and safety checks so a length failure cannot
hide another invalid field. Tests cover manual/automatic routing, declines,
unusable facts, qualifier preservation, and validation precedence. Live hosted
generation remains variable; this local recovery path is explicitly reported.

The live Jetson test subsequently confirmed automatic pause detection and a hosted
response, but that response exceeded 160 characters with two portfolio passages
supplied. Automatic requests now use the existing validated local fact fallback
for length-only failures when the model explicitly returned `should_offer: true`.
The parser carries only that validated boolean with the length error; malformed,
unsafe, refused, or false-offer responses cannot enable automatic fallback.
Regression tests cover both length limits, offer decisions, one-request behavior,
and validation precedence. The hardware path still needs the operator's retest.

The next operator request supersedes the oversized-answer fallback above: shorten
the model's own answer instead of replacing it with a portfolio phrase. There is
now one bounded shortening call for otherwise-valid offered responses that fail
only length. It sends only the draft and intent to the same endpoint/model, keeps
the original overall timeout, and validates the second response completely.
Invalid repair output is withheld without another repair or portfolio fallback.
Direct valid declines may still use the existing manual-only local phrase path;
declines returned during shortening are always respected. The UI labels successful
shortening and metrics contain only counts/flags, never the draft. Mocked tests
cover request boundaries, timeout sharing, automatic routing, and rejected repairs.
Live model shortening quality and semantic fidelity remain unverified.

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


## Cross-device development log

The root [WORK_LOG.md](../WORK_LOG.md) is the first-stop summary for another
Codex/device session. Follow [AGENTS.md](../AGENTS.md) to inspect the checkout,
preserve edits, and append a brief verification record before each push. This log
contains project changes only; it must never include user data or runtime content.
