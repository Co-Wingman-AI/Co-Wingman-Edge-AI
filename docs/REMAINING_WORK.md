# Verified loose ends and implementation milestones

Audit date: 2026-10-22. Application code reviewed at `766ad48`; reconciled website updates through
`b592753` before publication. Includes model assistance
from `8c2c8d7`. Original classifier revision: `03288414382def0356e44ae1c4aca4d0fd6ad35d`.
These milestones were requested for development planning. Operating instructions
remain in the README, RUN_ON_JETSON.md and MODEL_ASSIST.md. This audit does not
implement the changes below or claim new hardware/model-quality results.

## What is verified

- Pulled the latest website commits before review and reconciled three further
  website-only commits before publication, preserving unrelated local work.
- Reran 141 tests successfully on macOS arm64 / Python 3.14.7. Offline end-to-end
  and typed-input cue flows passed with output suppressed. Ruff 0.14.1 lint and
  formatting passed for 39 Python files.
- Reviewed configuration, request bounds, audio/ASR supervision, automatic trigger,
  summary/portfolio options, timing reports, and the original training notebook.
- Inspected the pinned Keras archive's model configuration without running inference.
  A synthetic index-layout check reproduced the temporal reshape issue below.
- GitHub reports successful offline CI and website deployment for `766ad48`.
  The served website could not be retrieved through this audit's web tool, so this
  is deployment-workflow evidence, not a fresh browser verification.
- Prior handoffs contain operator-reported Jetson and NaviGator successes. Those
  are useful evidence but do not establish repeatability of the latest combined
  ASR/classifier path. No real API call, microphone or Jetson execution occurred
  in this audit. No model was retrained or accuracy measurement repeated.

## Confirmed gaps and scope differences

| Finding | Evidence in the current repository | Consequence / next action |
| --- | --- | --- |
| Original strict text budget applies only to default mode | `cowingman/context.py`, `provider.py`, `memory.py`: rolling permits 15 fragments / 3,600 characters, plus up to 1,200 summary characters; portfolio adds up to 1,200 fact characters | Later handoffs record explicit requests for these extensions. They are documented opt-ins, not a discovered secret upload. They nevertheless differ from the pasted original 4/240/800 specification. Make operating profiles and outbound budgets unambiguous; do not silently remove later features. |
| Rolling capture also enables remote summaries | `__main__.py` constructs `ConversationMemory` whenever rolling is enabled | Continuous capture, remote summary requests and wider disclosure are coupled. Separate these controls if continuous listening with the original boundary is desired. Model-assist alone already retains the original bounds. |
| UI commands wait during network work | `app.py` calls cue generation and summary flush synchronously; `provider.py` waits for its request child | `:pause`, `:assist off`, `:quit` and display-expiry ticks are not processed while calls block. Deadlines and Ctrl-C cleanup exist, but immediate command cancellation does not. |
| Default capture has gaps and reload cost | `speech.py` closes capture during ASR in noncontinuous mode; `app.py` stops the worker for cues | Words can be missed at boundaries; `:listen` reloads ASR. Continuous modes use a bounded queue but are not proof of gap-free operation. Measure before optimizing. |
| No enrolled-speaker identification | ASR fragments are intentionally `unknown`; no enrollment/verification module | Another nearby speaker can influence context and triggers. Personal-microphone guidance is a mitigation, not identification. |
| Trigger performance is unknown | `ModelPauseGate` uses two scores >=0.5, three-second silence via `PauseDetector`, freshness checks and cooldown | Short freezes, ordinary pauses, overlapping speech and queued events require event-level tests. The first capture only primes a tail; two eligible scored windows cannot arrive until about 12 seconds of continuous capture, before processing delay. |
| Existing reports are timing tools, not accuracy evaluators | `scripts/timing_report.py` reports score counts, stage durations and review markers | There is no automated event matcher, false-cues/minute metric, speaker-held-out evaluation or useful-cue rating report. |
| Optional features are implemented but incompletely verified live | Sequential NVIDIA TTS, S3 summary/portfolio, shortening and profile retrieval have code and mocked coverage | Test the exact configurations intended for presentation. Visual/manual/typed fallback remains usable without all optional services. |
| Public descriptions need consolidation | Website describes shadow mode without the newer assist option; historical HANDOFF entries describe superseded behavior | Add a current capability summary without rewriting historical evidence. Video/poster links are still pending. |

Schema/keyword/echo checks constrain outputs; they do not prove factual accuracy,
semantic safety, useful timing, or fidelity after shortening. The original hard
rule that audio never goes to NaviGator remains implemented. Local RAM cleanup
cannot determine UF retention or erase OS/terminal captures.

## Milestone 1 — Responsive controls and explicit privacy profiles

**Implement:** separate continuous listening from summaries and outbound budget
selection; retain a clearly named/default strict profile with four fragments,
240 characters each and 800 total. Keep existing expanded-memory/portfolio
features explicitly selectable and disclose their separate budgets/persistence.
Move cue/summary work behind a small cancellable operation interface so the main
loop continues processing stop/clear/quit and cue expiry. Reject late results
from cancelled operations; never automatically retry private context.

**Files:** `__main__.py`, `app.py`, `context.py`, `provider.py`, `memory.py`,
`ui.py`, relevant tests and privacy/launch docs.

**Completion evidence:** boundary tests for every supported flag combination;
mocked slow-request tests showing pause/clear/quit and display expiry remain
responsive, context is discarded as configured, and a late result is never shown.
Proposed command-handling target: within 250 ms of command submission, excluding
OS scheduling and final process cleanup. Test cancellation of cue, shortening,
summary and upload separately. Preserve the explicit cue trigger and offline path.

## Milestone 2 — Repeatable Jetson and NaviGator operation

**Implement/verify:** a content-free operator checklist and reproducible dependency
constraints for the actually working JetPack environment. Exercise startup,
manual cues, model-assist load/failure, microphone reconnect, timeout/rate-limit
recovery, low memory, repeated resume and shutdown. Prefer visual output first;
verify sequential TTS independently. Use existing numeric timing hooks rather
than adding transcript/audio logging.

**Completion evidence:** proposed minimum rehearsal of 30 minutes and 20
cue/resume cycles, with no crashes or orphan workers and documented memory/swap
behavior. Report capture-to-display latency as well as ASR/classifier/network
p50/p95, dropped windows, failed/declined/shortened requests, and restart time.
Measure combined processing against the four-second capture cadence; do not call
it sustained real time if backlog/drops accumulate. Test real NaviGator using
synthetic context and the operator's locally configured key. Record failures too.
These sample sizes are a rehearsal, not statistical proof of reliability.

**Dependency:** can begin with the present code; repeat affected cases after M1.
Live device/key are required. No claimed completion from mocks alone.

## Milestone 3 — Reproducible detector and cue-quality evaluation

**Implement:** a separate offline evaluation tool that takes an explicitly
provided local evaluation manifest and produces aggregate numeric results. Keep
training/evaluation audio outside Git and outside default runtime capture. Add
speaker/session-separated splits, event annotations, and one-to-one matching of
triggers to eligible help-needed events. Review markers alone are not clinical or
objective ground truth. Distinguish speech-event labels from user-rated desire
for help. A frozen test set must not tune thresholds.

**Compare:** manual control, pause-only, current model-plus-pause and candidate
model-plus-pause on the same held-out scenarios. Include natural thinking pauses,
fluent speech, repetitions, blocks, quiet speech, microphone noise, partner-only
speech and overlap. Acted freezes are an initial UI test, not a substitute for
consented representative evaluation data.

**Completion evidence:** confusion matrix, per-class precision/recall/F1, PR-AUC,
calibration, false cues per minute, missed events, trigger delay and cue usefulness
ratings, with denominators and uncertainty grouped by speaker/session. Publish
only nonidentifying aggregate conclusions; generated reports remain ignored.
Choose the acceptable false-cue budget on development data before final testing;
a replacement should improve event recall at that fixed budget without worsening
latency/memory beyond the declared device budget. Do not set a promised accuracy
percentage before obtaining independent data.

## Milestone 4 — Correct and retrain the disfluency model

**Implement:** reproducible training/configuration in the research repository,
with a model card and preprocessing manifest. Correct label filtering, speaker
splits, feature consistency and the temporal-axis layout described below before
spending on a larger network. Train/evaluate off-device; deploy inference only.
Keep the pinned current checkpoint as the reproducible baseline.

**Completion evidence:** at least a baseline and corrected candidate evaluated
under M3's same frozen protocol; feature-parity fixtures between training and
runtime; threshold selected on validation data; new checksum/version; Jetson
memory and timing comparison; explicit rollback to manual/shadow mode. No weights
or participant data committed to the product repository. Never alter the reshape
under the old checkpoint and assume the old weights remain valid.

**Dependency:** M3's evaluation protocol; M2 for deployment acceptance.

## Milestone 5 — User-specific assistance and speaker handling

**Implement:** first add opt-in session calibration, sensitivity controls and
simple useful/not-useful feedback without saving speech. Calibrate on development
sessions and evaluate on separate sessions. If enrolled-speaker behavior remains
a product requirement, prototype local NVIDIA speaker verification with explicit
enrollment/deletion, an unknown-speaker state and overlap rejection. Diarization
labels alone do not establish enrolled identity. Benchmark any extra model beside
ASR before enabling it on the 8 GB device.

**Completion evidence:** held-out user/partner/unknown/overlap tests, false-accept
and false-reject rates, consent/deletion checks, and acceptable device memory.
Uncertain identity must not produce an automatic user-specific inference. Preserve
manual assistance. Until this exists, describe the product as personal-microphone
assistance, not enrolled-user recognition.

**Dependency:** M2/M3. Speaker verification is additional work, not necessary to
keep the manual presentation path operational.

## Milestone 6 — Release rehearsal and optional integrations

**Implement/verify:** run the presentation script on a fresh Jetson checkout;
confirm key setup, health check, live manual cue, typed fallback, offline fallback
and clean shutdown. Reconcile README/HANDOFF/website/diagrams with measured current
behavior. Publish the supplied video/poster links when available. Check live S3
save/reload/deletion/lifecycle and sequential TTS only if included in the demo;
otherwise explicitly label them unverified/optional.

**Completion evidence:** CI green, selected live configurations documented with
commit/environment, privacy-safe source scan, confirmed website links, and a
concise next-device handoff. Review dependency pin sustainability separately from
presentation operation; do not upgrade Jetson CUDA/PyTorch blindly.

**Research-repository housekeeping:** its tracked tree includes `App/.env` and
flagged-output paths. Their private contents were not read in this audit and no
credential leak is asserted. Have the owner check whether real secrets/private
artifacts are present, rotate any actual exposed credential and remove accidental
artifacts through a deliberate cleanup. The product integration imports neither.
The source repo exposes no top-level license in the inspected tree; clarify model
and dataset reuse terms before distributing trained artifacts.

## Can the model get better?

There are concrete reasons to expect a better *disfluency detector* is possible,
but improvement is a hypothesis to test. There is no evidence here for a specific
future accuracy or for anxiety inference.

The [original training notebook](https://github.com/Co-Wingman-AI/Co-Wingman-AIS-Project-Original/blob/03288414382def0356e44ae1c4aca4d0fd6ad35d/CNN%2BLSTM%20Model%20training/train.ipynb)
reports 59.27% accuracy on 5,527 test clips; the stuttering class has approximately
0.61 precision, 0.53 recall and 0.57 F1. These are saved notebook results, not a
rerun or Jetson validation. Its target is stuttering/control. The original app's
0.35 threshold and Anxious/Calm labels do not convert that target into anxiety.

Recommended improvement order:

1. **Repair target labels and evaluation first.** The notebook maps
   `NoStutteredWords <= 1` to stuttering without explicitly filtering uncertainty,
   poor quality, no speech or music. Use the actual event annotations and a
   documented exclusion/abstention policy. Preserve difficult valid examples.
   The data uses annotator votes and includes natural-pause and non-speech labels;
   absent fluent votes alone are not reliable evidence of a specific event.
   [Dataset annotation documentation](https://github.com/apple-aiml-research/ml-stuttering-events-dataset).
2. **Split by speaker/session before augmentation.** Current code uses stratified
   random clip splits and Keras validation_split. That does not prevent the same
   speaker or recording appearing in training and testing. Use verified speaker
   IDs; recording groups are only a weaker fallback. Split choice materially
   affects these evaluations. [SEP-28k-E partitioning research](https://arxiv.org/abs/2206.03400).
3. **Match preprocessing.** Training preserves each file's sample rate and uses
   three-second dataset clips; runtime uses five-second windows at 16 kHz. Both
   pad/truncate MFCC+delta features to 80x200, so shape compatibility does not prove
   equivalent inputs. Define a single sample rate, window duration, FFT/hop,
   normalization and padding/masking policy, version it and retrain. Do not simply
   resample or shorten windows under the existing checkpoint without comparison.
4. **Fix the time axis when retraining.** After pooling, the pinned model has
   frequency/time/channel layout 20x50x128, then Flatten and Reshape to 50x2560.
   This does not transpose frequency and time; each LSTM step therefore does not
   represent one time position across all frequency bins. Use a time-first
   permutation before reshaping, or a simpler temporal convolution/pooled model.
   This is an architectural finding; its impact on accuracy is not yet measured.
5. **Improve robustness and calibration.** Use realistic microphone/noise/reverb
   augmentation on training data, preserve temporal patterns of repetitions and
   blocks, and test quiet/overlapping speech. Tune score threshold, smoothing,
   pause timing and cooldown together for fewer unwanted cues. Do not lower 0.5
   to 0.35 merely to make the demo trigger more often. Add an uncertain/abstain
   region and evaluate any per-user calibration on separate sessions.
6. **Compare efficient NVIDIA-based candidates if production requires them.**
   NeMo documents compact MatchboxNet classification and MarbleNet VAD models.
   VAD helps distinguish speech from silence; it does not detect anxiety.
   A fine-tuned NVIDIA-based classifier is a candidate, not an off-the-shelf
   validated detector. Verify runtime/version compatibility and benchmark on Orin;
   using NeMo alone does not turn arbitrary custom weights into an NVIDIA model.
   [NVIDIA speech-classification models](https://docs.nvidia.com/nemo/speech/nightly/asr/speech_classification/models.html).
   Reusing ASR features could reduce duplicate compute, but ASR features may omit
   repetitions; evaluate that hypothesis before integration.

For actual anxiety/stress research, define that target separately with appropriate
self-report/reference measurements and a study designed with qualified domain
expertise. Disfluency, silence and ASR mistakes must not serve as anxiety labels.
The immediately useful product objective is whether the person wants a recovery
cue at that moment. A self-reported help signal can improve that decision without
claiming to diagnose an emotional or medical state. Any new recordings require
explicit consent and a separate data-retention plan; default runtime remains
RAM-only and never sends audio to NaviGator.

Suggested execution order: begin M1 and the M2 baseline; establish M3 before
retraining in M4. M5 follows measured need and resource feasibility. Keep the manual
presentation path usable throughout, then rehearse the selected release in M6.
