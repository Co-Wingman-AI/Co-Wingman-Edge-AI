# Milestone 1, Step 1 — Jetson inventory

## Scope

This step establishes the target Jetson's factual baseline before any model or
runtime decision. It does not install dependencies, download models, benchmark
compute, capture audio, or change the device configuration.

Run `python3 scripts/jetson_inventory.py` on the Jetson and return the matching
Markdown and JSON reports from `reports/`.

## Decision gate

The report states whether it ran on a detected Jetson and whether enough facts
were gathered to begin a later feasibility test. That status is not a claim
that Nemotron—or any complete concurrent workload—is supported.

After the real inventory is reviewed, Step 2 may select and test an appropriate
local NVIDIA Nemotron checkpoint, quantization, and Jetson-compatible runtime.
All application model checkpoints, including future TTS, must be NVIDIA models.
