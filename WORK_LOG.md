# Shared development handoff

This is the short, Git-tracked project change log for handoffs between devices and
Codex sessions. It records code changes and verification only. It is not a runtime
or user-data log. Read the latest entry before starting; append an entry before
committing each completed unit. Detailed product instructions remain in README,
`docs/HANDOFF.md`, and `docs/PRESENTATION.md`.

## 2026-10-20 — Co-Wingman application foundation

- **Session:** Codex workspace, macOS arm64, Python 3.14.7.
- **Source commits:** `4009af7` (NaviGator client and archive cleanup),
  `1d98d5b` (application, local speech path, fallbacks, docs, and CI).
- **Changes:** one `python3 -m cowingman` entry point; NaviGator-only bounded-text
  Nemotron client; strict cue checks; explicit terminal trigger; typed and synthetic
  offline paths; isolated NVIDIA ASR and optional sequential TTS; consent-conscious
  pause heuristic; setup, privacy, Jetson, and presentation documentation.
- **Validation:** 51 local tests, offline end-to-end and typed fallback runs, Ruff,
  repository hygiene scan, and GitHub Actions on Python 3.10, 3.12, and 3.14 passed.
- **Still unverified in that session:** physical Jetson audio/model execution and a
  live NaviGator key. See later operator notes below; do not infer device results
  from the macOS checks.

## 2026-10-21 — Astra handoff on organization main

- **Session/device:** Astra/Codex session; physical device identity not recorded.
- **Source:** 14 commits from `1d98d5b` through `fc928cd` on the organization
  repository. GitHub author: Honeydaram.
- **Changes:** optional local portfolio import and retrieval, better two-person
  context handling without claiming speaker identity, strict structured cue
  requests and echo checks, safer handling of invalid/declined responses, stronger
  typed fallback, and expanded operator handoff notes.
- **Operator evidence:** upstream notes report a Jetson microphone-to-cue run and
  a live NaviGator check. These are operator-reported results, not measurements
  independently repeated in the current Codex workspace. Read `docs/HANDOFF.md`
  and `docs/PORTFOLIO.md` for the detailed sequence and limitations.
- **CI:** the prior organization run passed. At the time of syncing `fc928cd`, its
  new workflow was still running; check GitHub Actions before relying on that run.

## 2026-10-21 — Organization sync and cross-device log

- **Session/device:** Codex workspace; macOS arm64, Python 3.14.7.
- **Source:** fast-forwarded this checkout to organization `main` at `fc928cd`;
  local `origin` now points to `Co-Wingman-AI/Co-Wingman-Edge-AI`.
- **Reconciled local edits:** ASR capture timestamps now survive speech-worker IPC.
  Old recognition results cannot refresh the 60-second context TTL. Adjacent
  windows merge only within the existing fragment bound and retain their oldest
  capture time. Microphone text stays marked `unknown` because there is no speaker
  verification. Empty ASR windows retain Astra's clear user-facing status.
- **Validation:** 80 local tests passed after the reconciliation; Ruff lint and
  formatting checks passed; offline end-to-end demo completed; repository scan
  checked 46 source files for syntax, whitespace, and credential/artifact patterns.
  GitHub Actions run 39613916563 has green test jobs on Python 3.10, 3.12, and
  3.14; GitHub still reports the overall run as in progress while settling.
- **Next:** check the GitHub Actions run for the shared-log commit, then continue
  real-device checks from `docs/HANDOFF.md`. Do not repeat the operator-reported
  Jetson/NaviGator test as if it were independently verified here.

## 2026-10-21 — Poster architecture diagram

- **Session/device:** Codex workspace; macOS arm64.
- **Source:** organization `main` through merge commit `00f82e6`; the diagram files
  were added in `db6e515` after syncing the shared handoff commit `0526cb3`.
- **Changes:** added a poster-ready editable SVG and a 3600×2500 PNG describing the
  Jetson and UF cloud trust zones, exact NVIDIA ASR/LLM/TTS models, local
  process boundaries, NaviGator request settings, validation, cleanup, privacy,
  and memory safeguards. Added a SHA-256 allowlist entry so the reviewed PNG is
  accepted by the repository hygiene check while replacements remain detectable.
- **Validation:** SVG passed `xmllint`; PNG format and 3600×2500 dimensions were
  verified; the rendered poster was visually reviewed. On Python 3.12, all 80
  unittests passed and the offline end-to-end demo completed. The repository scan
  checked 47 source files, Ruff lint/format checks passed, and `git diff --check`
  reported no whitespace errors.
- **Remaining work:** no runtime behavior changed. A physical print proof and any
  poster-specific typography adjustments remain optional.

## 2026-10-21 — Automatic cue length recovery

- **Session/device:** Codex cloud workspace; Linux x86_64, Python 3.12.14.
- **Source:** continued `fc928cd`, reconciled with organization main `00f82e6`,
  preserving the context-expiry changes and architecture documentation.
- **Changes:** automatic portfolio requests can recover word/character-limit-only
  failures using the existing validated local phrase extraction, but only when
  the otherwise-validated response explicitly offers a cue. Automatic declines,
  malformed fields, and unsafe responses cannot enable this fallback. No retry or
  additional cloud request; the UI still identifies the local phrase.
- **Validation:** 82 unittest tests passed, including simulated microphone pause
  routing and oversized automatic responses. Ruff lint/format checks, offline
  demo, and `git diff --check` passed. Repository hygiene scan failed on the
  upstream `docs/co-wingman-architecture.png` as an unreviewed binary; preserved
  that existing artifact without weakening the scanner.
- **Remaining:** live Jetson/NaviGator retest of automatic length recovery;
  upstream architecture binary needs review for the repository hygiene policy.

## 2026-10-21 — Condense oversized model answers before display

- **Session/device:** Codex cloud workspace; Linux x86_64, Python 3.12.14.
- **Source:** organization main `76f758b`.
- **Changes:** replaced oversized-answer local portfolio fallback with one
  shortening call to the same approved model. Only an otherwise-validated offered
  draft is eligible; only that bounded draft and intent are sent back, within the
  original timeout. The final response must pass normal validation and preserve
  intent. No recursive repair, no fallback after a failed shortening response,
  and no override of a shortening decline. Added content-free request counts and
  a visible shortening status. Direct manual declines retain the separate local
  portfolio phrase behavior. Updated privacy and operating documentation.
- **Validation:** 89 unittest tests passed, including automatic pause routing,
  both length limits, deadline sharing, request boundaries, declined/invalid
  repairs, and suppression of content in diagnostics. Ruff lint and formatting,
  offline demo, and `git diff --check` passed. Repository scan still flags the
  pre-existing architecture PNG as an unreviewed binary; it remains unchanged.
- **Remaining:** live hosted-model and Jetson test of shortening quality,
  semantic fidelity, and latency. Mocked responses do not establish live model
  compliance.

## 2026-10-21 — Rolling minute, visible testing, and optional S3 summaries

- **Session/device:** Codex cloud workspace; Linux x86_64, Python 3.12.14.
- **Source:** organization main `b04f69f`.
- **Changes:** opt-in rolling mode retains a 60-second, 15-fragment/3,600-character
  window across cues. Local capture continues in four-second windows during ASR
  and visual cue requests, with a bounded queue and reported drops. Cues remain
  manual/pause-triggered. Typed input is visible by default with explicit show/hide
  flags. A separate minute timer asks the approved model for a bounded summary.
  Optional boto3 integration saves timestamped summary JSON to a selected private
  S3 prefix and supports explicit latest/archived-record reuse. No audio or full
  transcript archive is uploaded. Added bucket/IAM/profile operating instructions
  and documented expanded text budgets and summary persistence.
- **Validation:** 103 unit/integration tests passed, including real terminal echo
  and restoration, capture-window queue bounds, rolling expiry, minute boundaries,
  summary validation, mocked S3 encryption/upload/reload, and failed-upload retry.
  Ruff lint/format checks, offline demo, CLI help, and `git diff --check` passed.
  No Jetson hardware or AWS identity was available for live verification.
- **Remaining:** create the destination bucket and configure the Jetson's AWS
  profile, then verify physical rolling capture, live summary quality, latency,
  and upload/reuse. Summary compression is lossy; failed uploads have a RAM-only
  retry record, not a durable offline archive. The pre-existing architecture PNG
  remains flagged by the repository hygiene scanner as an unreviewed binary.

## 2026-10-21 — Timing, experimental shadow scoring and S3 portfolio

- **Session/device:** Codex cloud workspace; Linux x86_64, Python 3.12.14.
- **Source:** organization main `7046445`; reviewed external research repository
  revision `03288414382def0356e44ae1c4aca4d0fd6ad35d` for its pinned model adapter.
- **Changes:** opt-in content-free UTC/monotonic timing reports cover capture,
  ASR verification/load/inference, request-worker startup, HTTPS connection setup,
  response wait/read, validation, cue handling, TTS, summaries and S3. Added a
  synthetic interleaved comparison of four cue token budgets; production remains
  256. Experimental disfluency scoring uses pinned local weights with Keras's
  PyTorch CPU backend, warms before capture, and never triggers cues or infers
  anxiety/identity. Fixed review markers support local inspection without audio
  recording. Explicit S3 portfolio upload creates an archive and current snapshot;
  startup retrieval validates it and retains bounded local passage selection.
  Added private-bucket setup script and operator commands. No AWS upload occurred.
- **Validation:** 119 offline tests passed; Ruff lint/format, CLI help, offline
  demonstration and diff whitespace checks passed. Real pinned-model download and
  SHA verification passed. A separate temporary PyTorch 2.8 CPU/Keras 3.10 runtime
  loaded the real weights and scored three synthetic windows, including inside the
  network-disabled speech environment. This establishes adapter compatibility,
  not accuracy or Jetson latency. AWS tests use mocks; no live identity was available.
- **Remaining:** configure the bucket and Jetson AWS profile, upload/reload the
  portfolio, and collect baseline/shadow timings on the Jetson. Run the explicit
  live token comparison before lowering limits. No ASR overlap or persistent
  NaviGator transport was enabled. The existing architecture PNG still fails the
  repository scanner's unreviewed-binary check and was preserved.

## 2026-10-21 — Speech preprocessing dependency repair

- **Session/device:** Codex workspace; macOS arm64, Python 3.14.7.
- **Source:** organization main `c568b67`; fetched before editing, no upstream
  divergence or pre-existing working-tree edits.
- **Changes:** audio and shadow extras now require runtime `setuptools>=68,<82`
  for older Librosa's `pkg_resources` import. ASR, TTS, and model setup exercise
  lazy mel-filter imports before NeMo can mask a dependency failure. Missing
  `pkg_resources` produces a bounded repair instruction; other dependency failures
  remain sanitized. Added a standalone preprocessing check and staged Jetson
  CPU restore, CUDA inference, microphone, live cue, and rolling-mode retests.
- **Validation:** `python3 -m unittest discover -s tests -v` passed all 127 tests;
  Ruff 0.14.1 lint and format checks passed; offline demo and `git diff --check`
  passed. A fresh temporary Python 3.14 environment resolved the compatibility
  bound to setuptools 81.0.0, imported `pkg_resources.resource_filename`, and
  passed `pip check`. The standalone check correctly exited 2 with a sanitized
  missing-dependency message in the development environment without Librosa.
  Repository hygiene still fails only on the pre-existing architecture PNG.
- **Remaining:** apply the environment repair on the Jetson and run the staged
  checks in `RUN_ON_JETSON.md`. No physical Jetson, CUDA, NeMo model, live service,
  or full Librosa-stack validation was performed in this workspace. Retire the
  compatibility bound after separately validating a newer speech/shadow stack.

## 2026-10-21 — Resolve repository script imports in populated environments

- **Session/device:** Codex workspace; macOS arm64, Python 3.14.7.
- **Source:** fast-forwarded organization main from `4a1ecf3` to `66f72a4`,
  preserving the upstream architecture and repository-scanner changes.
- **Changes:** added `scripts/__init__.py` so an installed regular package named
  `scripts` cannot shadow repository tools during tests run from the project root.
  Added a subprocess regression with a competing package later on the import path,
  checking all four tool modules imported by the test suite.
- **Validation:** regression failed before the package marker and passed after it;
  `python3 -m unittest discover -s tests -v` passed all 128 tests. Offline demo,
  Ruff 0.14.1 lint/format checks, and `git diff --check` passed. Repository hygiene
  passed for 65 source files using the upstream reviewed-image policy.
- **Remaining:** pull on the Jetson and rerun discovery; expected count is now 128.
  The package collision is locally reproduced, but the exact installed package on
  the Jetson was not inspected. Physical ASR/CUDA and microphone checks remain
  separate from these offline tests.

## 2026-10-21 — Interactive public project website

- **Session/device:** managed Linux cloud workspace; desktop Chromium browser.
- **Source:** fast-forwarded clean working branch from `c568b67` to organization
  main `172b7aa`, preserving upstream speech dependency, scanner, and prompt edits.
- **Changes:** added an illustrated static showcase with three fictional cue
  examples, an interactive architecture diagram, team attribution, prototype
  boundaries, and privacy information. Added responsive layouts, keyboard tabs,
  reduced-motion support, a content security policy, and deployment documentation.
  The Pages workflow publishes only `website/`, never runtime data or credentials.
- **Validation:** browser checks passed for three scenarios, replay, pending-cue
  cancellation, keyboard tabs, FAQ interaction, five viewport widths (320–1440),
  reduced motion, no-JavaScript fallback, and internal navigation. No external
  requests or browser errors occurred. Axe WCAG A/AA checks reported zero
  violations at desktop and mobile widths with the cue and cloud panel visible.
  JavaScript syntax, repository hygiene (72 source files), Ruff lint/format, and
  whitespace checks passed. Python discovery ran 128 tests: 127 passed and one
  pre-existing provider test failed because it expects wording replaced by the
  upstream system-prompt edit. Application code and that test were preserved.
- **Remaining:** verify the GitHub Pages deployment and live URL. Git transport
  works, but this workspace cannot use GitHub's API under its current network
  policy. A narrowly scoped network configuration draft was saved for review;
  it is not applied automatically. Pages may also need its source set to GitHub
  Actions in repository settings. The website's simulated examples are not live
  Jetson/ASR or model-quality validation.

## 2026-10-22 — Expanded research showcase and conversation simulator

- **Session/device:** managed Linux cloud workspace; Chromium browser.
- **Source:** clean organization main `46d2b36`; fetched before editing and
  rechecked before commit, with no upstream divergence.
- **Changes:** expanded the website with the full project title, UF-inspired
  colors, an animated recovery flow, editable terminal simulation, edge/cloud
  specifications, research provenance, setup/command guide, roadmap, resources,
  and acknowledgments. Adapted React Bits spotlight treatment for the static
  site and preserved its license and source attribution. The simulator displays
  visitor-supplied continuations with explicit local-only labeling and bounds;
  no live model credential, network call, microphone, or persistence was added.
  Published descriptions distinguish expiring recent context from optional S3
  persistence and shadow disfluency scoring from anxiety/speaker inference.
- **Validation:** browser regression passed for all three existing examples,
  replay/cancellation, keyboard architecture tabs, FAQs, five widths, reduced
  motion, and no-JavaScript fallback. New lab checks passed for simulated pause,
  reset/edit cancellation, literal text rendering, word/character limits,
  whitespace rejection, roadmap controls, navigation anchors, and mobile output.
  No storage, external requests, or JavaScript errors were observed. Axe WCAG
  A/AA checks found zero violations at 1440px and 390px with the lab result and
  roadmap open. JavaScript syntax, whitespace, and repository hygiene passed
  (74 source files). Application code was unchanged; the previously recorded
  upstream prompt-wording test failure remains outside this website change.
- **Remaining:** project owner must provide the demo-video and Google Drive
  poster URLs; resource cards explicitly show their pending status. Live model
  testing in a browser would need a separately hosted backend. GitHub API/Pages
  access remains blocked by the workspace network policy, so deployment status
  and the served website cannot be confirmed here. The existing workflow will
  request deployment on this website push if repository Pages is configured.

## 2026-10-22 — Opt-in local model-assisted recovery

- **Session/device:** Codex workspace; macOS arm64, Python 3.14.7.
- **Source:** pulled organization main `dc3c434` before integration; fetched again
  before committing, with no upstream divergence. Preserved unrelated local work.
- **Changes:** connected the pinned original CNN+LSTM classifier to explicit
  `--disfluency-assist` mode: two elevated local scores followed by a fresh pause,
  shared cooldown, readiness checks and manual fallback. Model failures stop
  automatic assistance while ASR continues. Default text bounds remain four
  fragments, 240 characters each and 800 total; no audio or scores go to NaviGator.
  The custom non-NVIDIA classifier stays an opt-in research path, separate from
  the default NVIDIA path. It is not validated anxiety or speaker detection.
  Updated the download to the organization repository, added operating docs and
  numeric trigger diagnostics, and aligned the obsolete provider-test wording
  with the existing upstream prompt without changing that prompt.
- **Validation:** all 141 unit tests passed; Ruff 0.14.1 lint and format checks
  passed (39 Python files); offline end-to-end and typed-input cue demos passed,
  with output suppressed. Whitespace checks passed.
  Reviewed-source snapshot passed syntax/credential/artifact checks for 76 source
  files; unrelated local poster artifacts were excluded from the snapshot/commit.
  Explicit model download verified the pinned SHA-256. Mocked integration covers
  worker-to-cue flow, failures, stale events, opt-in, cooldown, privacy and cleanup.
- **Remaining:** physical Jetson ASR-plus-classifier memory/latency and real
  microphone triggers need testing, as do real NaviGator calls. No model accuracy,
  clinical validity or live hardware result is inferred from these checks.
  Next device: pull, follow `docs/MODEL_ASSIST.md`, and use the manual cue control
  for dependable presentation recovery while evaluating automatic assistance.

## 2026-10-22 — Website team roster update

- **Session/device:** managed Linux cloud workspace.
- **Source:** fast-forwarded to organization main `8c2c8d7`, preserving the
  upstream model-assistance implementation and documentation.
- **Changes:** added the requested contributor to the website team section and
  adjusted the grid for five members, with three tablet and two mobile columns.
- **Validation:** Chromium confirmed five team entries and no horizontal overflow
  at 1440, 768, 390, and 320 pixels. Repository hygiene passed for 76 source files;
  whitespace checks passed. No application behavior changed.
- **Remaining:** live Pages deployment verification remains unavailable under the
  workspace network policy; the existing workflow deploys website pushes.

## 2026-10-22 — Randomized scripted conversation examples

- **Session/device:** managed Linux cloud workspace; Chromium browser.
- **Source:** clean organization main `ac35f89`, fetched before editing.
- **Changes:** expanded the website's conversation card to 15 fictional examples
  across three topics. Added shuffled topic cycles, a random-example control,
  and simulated thinking/word reveal with cancellation and reduced-motion support.
  The public interface identifies the simulation; no model calls, recording,
  credentials, or storage were introduced. Updated website maintenance notes.
- **Validation:** browser checks passed for all 15 prompt/cue pairings and length
  limits, topic cycles, no immediate repeats, random selection, cancellation
  during thinking and reveal, reduced motion, and four widths from 320 to 1440px.
  Axe WCAG A/AA checks reported zero violations at desktop and mobile widths.
  No external requests, browser errors, or storage were observed. JavaScript
  syntax, whitespace, and repository hygiene checks passed (76 source files).
- **Remaining:** GitHub Pages deployment is handled by the existing workflow;
  live deployment status cannot be inspected under this workspace's network policy.

## 2026-10-22 — Equal-position team rotation

- **Session/device:** managed Linux cloud workspace; Chromium browser.
- **Source:** clean organization main `766ad48`, fetched before editing.
- **Changes:** placed the four team cards on a clockwise orbit with equal dwell
  times, an initially randomized position, and upright labels. The advisor has a
  separate fixed, centered card below. Added pause/resume and manual advancement;
  reduced motion disables autoplay. Hidden/offscreen playback stops, accessible
  reading order is stable, and no-JavaScript visitors receive a static grid.
- **Validation:** browser checks confirmed every member visits all four positions,
  no card overlaps across 400 sampled layouts at five viewport widths, a fixed
  advisor position, automatic movement, pause/resume, reduced motion, and the
  no-JavaScript layout. Desktop/mobile Axe WCAG A/AA scans found zero violations;
  no browser errors occurred. JavaScript syntax, whitespace, and repository
  hygiene passed for 77 source files. Application code was unchanged.
- **Remaining:** the existing Pages workflow handles deployment; live deployment
  status remains unavailable under the workspace network policy.

## 2026-10-22 — Automatic cue selection in the browser lab

- **Session/device:** managed Linux cloud workspace; Chromium browser.
- **Source:** clean organization main `a2d2814`, fetched before editing.
- **Changes:** removed the visitor-entered cue field. The lab now accepts only
  a partner question and unfinished thought, then selects a bounded scripted cue
  after its simulated pause. Local keyword matching uses 16 fictional examples;
  unfamiliar or unrelated fragments receive a general recovery phrase. Updated
  interface labels and maintenance notes to explain the simulation accurately.
- **Validation:** browser checks passed for two-field input, all 16 cue pairings,
  output bounds, minor edits, unfamiliar/unrelated text, literal text rendering,
  whitespace rejection, timed output, edit/reset cancellation, and four widths.
  Desktop/mobile Axe WCAG A/AA checks found zero violations. No external calls,
  storage, or browser errors occurred. JavaScript syntax, whitespace, and
  repository hygiene checks passed (77 source files).
- **Remaining:** cue selection is scripted matching, not live model inference.
  The existing Pages workflow handles publication; live deployment status remains
  unavailable under this workspace's network policy.

## 2026-10-22 — Simplified team orbit labels

- **Session/device:** managed Linux cloud workspace; Chromium browser.
- **Source:** clean organization main `3394a19`, fetched before editing.
- **Changes:** replaced the center message with the requested team label, removed
  repeated member-role captions, rotation buttons, and the explanatory caption.
  Removed the associated control handlers/styles and updated website notes.
  Automatic rotation, reduced-motion handling, and the fixed advisor remain.
- **Validation:** browser checks passed for the center label, removed elements,
  four member cards, fixed advisor, desktop and two mobile widths, automatic
  movement, reduced motion, and absence of browser errors. JavaScript syntax,
  whitespace, and repository hygiene passed (77 source files).
- **Remaining:** publication uses the existing Pages workflow; live deployment
  verification remains unavailable under this workspace's network policy.

## 2026-10-22 — Verified loose ends and implementation plan

- **Session/device:** Codex workspace; macOS arm64, Python 3.14.7.
- **Source:** pulled organization main from `8c2c8d7` to `766ad48`, preserving
  unrelated local poster work; reconciled concurrent website-only updates through
  `b592753` before publication. Reviewed original classifier revision
  `03288414382def0356e44ae1c4aca4d0fd6ad35d` and its pinned model configuration.
- **Changes:** added `docs/REMAINING_WORK.md` and a README link, with six requested
  implementation milestones, code-backed gaps, completion criteria and dependencies.
  Distinguished later opt-in privacy extensions from the original strict budget,
  implemented features from live verification, and disfluency from anxiety claims.
  Model recommendations cover target labels, speaker-separated evaluation,
  preprocessing consistency, temporal-axis correction, calibration and efficient
  NVIDIA-based candidates. No runtime/model behavior changed.
- **Validation:** all 141 tests passed in 0.507 seconds; offline end-to-end and
  typed-input cue demos passed with output suppressed. Ruff 0.14.1 lint/format
  passed for 39 Python files. Reviewed-source snapshot passed syntax, whitespace
  and credential/artifact checks for 78 source files; unrelated output excluded.
  Documentation links and diff whitespace checked. A synthetic index-layout
  check confirmed that the original flatten/reshape does not preserve time-first
  grouping. Saved notebook metrics were inspected, not independently reproduced.
  GitHub CI and website deployment for `766ad48` report success; served-site
  retrieval was unavailable through the audit web tool.
- **Remaining:** execute the documented milestones, starting with responsive
  controls/privacy profiles and a repeatable Jetson baseline, then event-level
  evaluation before retraining. No physical Jetson, live API, microphone or new
  accuracy result was obtained. Keep manual presentation fallback available.

## 2026-10-22 — Clickable website team profiles

- **Session/device:** managed Linux cloud workspace; Chromium browser.
- **Source:** continued website work from `b592753`, reconciled organization main
  through `e4de6bc` before publication.
- **Changes:** added accessible profile dialogs for the team and advisor, a
  separate public profile data file, and supplied/verified public contact links.
  Rotation pauses during selection and while a dialog is open. Added keyboard
  focus handling, mobile layouts, no-JavaScript contact links, maintenance notes,
  and syntax validation for the new data file in the Pages workflow.
- **Validation:** all five dialogs, link destinations, motion pause, Escape and
  close controls, focus return and Tab/Shift-Tab containment passed in Chromium.
  Responsive checks passed at 1440, 390 and 320 pixels; automated WCAG A/AA checks
  reported no violations. Synthetic local-image success/error handling and
  no-JavaScript links passed; no browser errors. JavaScript syntax, diff whitespace
  and repository hygiene checks passed (79 source files).
- **Remaining:** the inline portrait is not available as a downloadable workspace
  asset; portrait placeholders remain until original image files are supplied.
  Additional public profile details are pending. Pages publication uses the
  existing workflow; live deployment verification remains network-restricted.

## 2026-10-22 — Restore reliable profile selection after updates

- **Session/device:** managed Linux cloud workspace; Chromium desktop and mobile
  touch emulation.
- **Source:** organization main `8c9592e`.
- **Finding:** reproduced disabled profile buttons when new markup loads with the
  prior cached main script. The reported live failure could not be inspected
  directly because the Pages host is blocked by workspace network policy.
- **Changes:** versioned profile assets and main script references to bypass old
  cached files; isolated profile initialization from animation/demo scripts;
  enabled selecting initials as well as names. Updated Pages syntax checks and
  maintenance documentation.
- **Validation:** 20 desktop-click/mobile-tap cases passed across all five cards
  and both targets. Link, focus return/containment, motion pause, and automated
  WCAG A/AA checks passed. Verified bypass of old unversioned script requests and
  usable profiles with a simulated main-script failure. JavaScript syntax, diff
  whitespace and repository hygiene checks passed (80 source files).
- **Remaining:** live deployment verification remains unavailable. Original
  portrait files and remaining public contact details are still pending.

## 2026-10-22 — Publish supplied profile portrait

- **Session/device:** managed Linux cloud workspace; Chromium browser.
- **Source:** organization main `92969a8`.
- **Changes:** replaced one profile placeholder with the supplied original image,
  now accessible as an attachment file. Added its reviewed binary hash, refreshed
  the profile-data asset version, and updated maintenance documentation.
- **Validation:** original file copied unchanged; reviewed hash matched. Portrait
  loading, placeholder removal, contact links and absence of horizontal overflow
  passed at 1440, 390 and 320 pixels. Mobile screenshot visually reviewed.
  JavaScript syntax, whitespace and repository hygiene passed (80 source files).
- **Remaining:** other portraits/contact details remain pending. Live Pages
  deployment cannot be verified under this workspace's network restrictions.

## 2026-10-22 — Show portrait in the rotating roster

- **Session/device:** managed Linux cloud workspace; Chromium browser.
- **Source:** organization main `5942694`.
- **Changes:** replaced the corresponding roster initials with the already
  approved portrait, retaining the rounded avatar shape and profile interaction.
  Updated the team stylesheet version for returning visitors.
- **Validation:** image loading, avatar sizing, removal of initials and profile
  opening passed at 1440, 390 and 320 pixels; mobile screenshot reviewed.
  Diff whitespace and repository hygiene passed (80 source files).
- **Remaining:** GitHub Pages deployment remains unverified from this workspace.
