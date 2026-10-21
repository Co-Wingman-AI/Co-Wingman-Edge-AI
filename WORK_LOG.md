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

## 2026-10-21 — Automatic cue length recovery

- **Session/device:** Codex cloud workspace; Linux x86_64, Python 3.12.14.
- **Source:** continued `fc928cd`, reconciled with organization main `00f82e6`,
  preserving the context-expiry changes and architecture documentation.
- **Changes:** automatic portfolio requests can recover word/character-limit-only
  failures using the existing validated local phrase extraction, but only when
  the otherwise-validated response explicitly offers a cue. Automatic declines,
  malformed fields, and unsafe responses cannot enable this fallback. No retry
  or additional cloud request; the UI still identifies the local phrase.
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
- **Remaining:** live hosted-model and Jetson test of shortening quality, semantic
  fidelity, and latency. Mocked responses do not establish live model compliance.
