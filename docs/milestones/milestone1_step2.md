# Milestone 1, Step 2 — isolated NVIDIA Nemotron feasibility

## Candidate

- Model: `nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF`
- Quantization: NVIDIA's official `Q4_K_M` GGUF (approximately 2.84 GB)
- Runtime: CUDA-enabled llama.cpp
- Initial context: 4,096 tokens
- Network binding: loopback only (`127.0.0.1`)

The model is developed by NVIDIA. llama.cpp is an inference runtime, not an
application model. No non-NVIDIA model is introduced by this experiment.

## Scope and safety

This step benchmarks Nemotron by itself using synthetic conversations. It does
not install or start ASR, VAD, speaker recognition, TTS, microphone capture,
or the future application. The benchmark script installs nothing and does not
change clocks or power modes. It may download the named public checkpoint when
llama.cpp does not already have it in its native-filesystem cache.

The script starts a local llama.cpp server, waits for readiness, performs one
warm-up and the requested number of measured trials, then terminates the
server. It records:

- server/model load time
- time to first generated content
- request duration and, when reported by the server, output tokens per second
- system available RAM, swap use, and server resident memory
- Jetson temperature, GPU activity, and input power from `tegrastats`
- validity of the requested short JSON cue
- repeat-request success

## Interpretation gate

An isolated pass requires every measured request to complete, valid cue JSON
from every measured trial, no sustained swap growth, no thermal throttling or
process crash, and enough remaining RAM to justify a later concurrency test.
There is deliberately no automatic claim that a numeric result proves the
complete Co-Wingman pipeline feasible. ASR/VAD/TTS concurrency is a separate
later experiment.

Keep the model cache, llama.cpp build, and any architecture-specific virtual
environment on the Jetson's native Linux filesystem. Keep only code and
reviewed, sanitized reports in the portable project repository.
