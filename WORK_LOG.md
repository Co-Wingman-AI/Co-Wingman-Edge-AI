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
- **Changes:** added a poster-ready editable SVG and a 3600×2500 PNG describing
  the Jetson and UF cloud trust zones, exact NVIDIA ASR/LLM/TTS models, local
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
