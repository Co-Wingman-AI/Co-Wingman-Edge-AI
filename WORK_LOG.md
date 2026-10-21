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

