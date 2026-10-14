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

**Milestone 1, Step 1 — Jetson inventory** is complete. **Step 2 — isolated
Nemotron feasibility** is ready for Jetson execution. The benchmark runs only
the official NVIDIA Nemotron 3 Nano 4B Q4_K_M model against synthetic prompts;
it does not capture audio or process a real conversation. Audio capture, VAD,
speaker recognition, ASR, hesitation detection, cue caching, and TTS remain
planned rather than implemented.

## Run the Nemotron benchmark on the Jetson

Keep the runtime and downloaded model on the Jetson's native Linux storage.
The following commands install build tools, compile llama.cpp with CUDA, and
run the benchmark. Review each `sudo` command before entering your password.

```sh
sudo apt update
sudo apt install -y build-essential cmake git libcurl4-openssl-dev

mkdir -p "$HOME/cowingman-runtime"
cd "$HOME/cowingman-runtime"
git clone https://github.com/ggml-org/llama.cpp.git
cd llama.cpp
cmake -B build -DGGML_CUDA=ON -DLLAMA_CURL=ON -DCMAKE_BUILD_TYPE=Release
cmake --build build --config Release -j2 --target llama-server
```

Return to the Co-Wingman project on the portable drive, replacing the example
path with the path reported by `findmnt`:

```sh
cd "/path/to/Co-Wingman-jetson"
python3 scripts/nemotron_benchmark.py \
  --server "$HOME/cowingman-runtime/llama.cpp/build/bin/llama-server" \
  --context-size 4096 \
  --trials 3
```

The first run downloads the 2.84 GB official NVIDIA checkpoint to llama.cpp's
model cache on the Jetson's native filesystem. Internet is used only for
installation and model download; all prompts and inference stay local. The
server listens only on `127.0.0.1`. See the
[official NVIDIA model card](https://huggingface.co/nvidia/NVIDIA-Nemotron-3-Nano-4B-GGUF)
for the checkpoint description and license.

Bring back the matching files printed by the command:

- `reports/nemotron_benchmark_YYYYMMDD_HHMMSS.md`
- `reports/nemotron_benchmark_YYYYMMDD_HHMMSS.json`

Do not commit generated reports until they have been reviewed for identifiers.
For methodology and pass criteria, see
[docs/milestones/milestone1_step2.md](docs/milestones/milestone1_step2.md).

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
