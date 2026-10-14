# Co-Wingman

Co-Wingman is an independent research project for a privacy-conscious,
real-time conversational recovery assistant running locally on an NVIDIA
Jetson Orin Nano 8 GB. It is intended to help an enrolled user request a short,
context-aware conversational cue when they get stuck. It is not a medical
diagnostic system, and it does not equate speech disfluency with anxiety.

## Architecture direction

All live conversation data and inference remain on the Jetson. The planned
pipeline uses only NVIDIA models:

- NVIDIA MarbleNet for voice activity detection
- NVIDIA TitaNet for speaker enrollment and attribution
- a Jetson-compatible NVIDIA NeMo/Riva ASR model for transcription
- a locally deployed NVIDIA Nemotron model for bounded, event-driven context
  maintenance and cue generation
- an NVIDIA NeMo TTS model, with the exact acoustic model and vocoder selected
  only after hardware measurements

No cloud model or external inference API is part of the runtime architecture.
Specific model checkpoints and runtimes remain decisions to be validated on
the target device; listing a model here is not a compatibility claim.

## Current status

Only **Milestone 1, Step 1 — Jetson inventory** is implemented. The inventory
script collects a read-only hardware, software, storage, Python, audio, and
monitoring baseline and writes local Markdown and JSON reports. Audio capture,
VAD, speaker recognition, ASR, Nemotron, hesitation detection, cue caching,
and TTS are planned but not implemented.

## Hardware and workflow

The target is an NVIDIA Jetson Orin Nano with 8 GB RAM. Development follows:

`Mac -> USB project drive -> Jetson -> USB project drive -> Mac`

Architecture-specific environments, packages, and model weights should live
on the Jetson's native Linux filesystem rather than on the portable drive.
See [RUN_ON_JETSON.md](RUN_ON_JETSON.md) for safe execution instructions.

## Repository privacy

The intended GitHub repository is `Co-Wingman-Edge-AI`, private by design.
Generated reports are ignored by default so that each can be reviewed for
sensitive data before it is deliberately committed.
