# Launch Co-Wingman on the Jetson

Use a terminal on the Jetson and a consenting operator's USB headset microphone.
The main command is `python3 -m cowingman`. No Nebius account, Slurm job, direct
HiPerGator allocation, or local LLM server is needed.

## Get the application and verify the fallback

```sh
git clone https://github.com/Co-Wingman-AI/Co-Wingman-Edge-AI.git
cd Co-Wingman-Edge-AI
python3 -m unittest discover -s tests -v
python3 -m cowingman --offline --demo
```

If already cloned, run `git pull --ff-only` from the repository instead. Preserve
local edits; do not reset the checkout. Use the Jetson's internal Linux filesystem
for the virtual environment and model files, not an exFAT removable drive.

## Set up UF access

In [NaviGator Toolkit](https://api.ai.it.ufl.edu/ui), create a key that can use
`nemotron-3-nano-30b-a3b`. Enter it silently, then test the actual approved model:

```sh
export NAVIGATOR_TOOLKIT_API_KEY="$(python3 -c 'import getpass; print(getpass.getpass("UF NaviGator key: "))')"
python3 -m cowingman --health-check
python3 -m cowingman --typed
```

Type one short fragment and press Enter, then enter `:cue`. Typed input is visible
unless you add `--hide-input`;
only the cue is displayed. Enter `:quit` before setting up speech. This is also
the live presentation fallback if audio installation cannot be completed.

## Prepare the local NVIDIA speech environment

The stored hardware report identifies L4T 36.4.7 / Orin Nano 8 GB. Check the actual
machine; do not assume every Jetson has the same software:

```sh
cat /etc/nv_tegra_release
python3 --version
free -h
```

Use Python 3.10 on the recorded JetPack 6 family system. Install a CUDA-enabled
NVIDIA PyTorch build and matching torchaudio for the **actual** JetPack release
using [NVIDIA's Jetson instructions](https://docs.nvidia.com/deeplearning/frameworks/install-pytorch-jetson-platform/index.html)
and [compatibility table](https://docs.nvidia.com/deeplearning/frameworks/install-pytorch-jetson-platform-release-notes/pytorch-jetson-rel.html).
A generic PyPI CPU-only torch wheel will not work. A universal wheel command would
be misleading across JetPack versions; this is the hardware-specific prerequisite.
Do not upgrade JetPack just to run this demo.

After NVIDIA torch and matching torchaudio are installed and importable:

```sh
sudo apt-get update
sudo apt-get install -y python3-venv python3-dev libportaudio2 portaudio19-dev libsndfile1 ffmpeg build-essential
python3 -m venv --system-site-packages .venv
. .venv/bin/activate
python3 -c 'import torch, torchaudio; assert torch.cuda.is_available(); print("CUDA and torchaudio ready")'
python3 -m pip install --upgrade pip
python3 -m pip freeze | sed -n '/^torch==/p; /^torchaudio==/p; /^torchvision==/p' > /tmp/cowingman-torch-constraints.txt
python3 -m pip install -c /tmp/cowingman-torch-constraints.txt -e '.[audio]' 'nemo_toolkit[asr,tts]==2.4.0'
python3 -m cowingman.speech_dependencies
python3 -c 'import torch; import nemo.collections.asr; assert torch.cuda.is_available(); print("NeMo ASR imports ready")'
python3 scripts/prepare_speech_models.py --asr
export COWINGMAN_ASR_MODEL_PATH="$PWD/models/asr.nemo"
python3 -m cowingman --list-audio
```

The NeMo version is a reproducible starting point, **not a verified Jetson build**.
If pip reports incompatible constraints, CUDA disappears, or an ARM dependency
cannot build, preserve the NVIDIA torch installation and use the typed live path.
Do not remove constraints merely to force installation. See [speech notes](docs/SPEECH.md).
Model setup downloads only the selected official NVIDIA checkpoint, saves it
under ignored `models/`, and records an integrity manifest. Runtime requires both.

If the default input is wrong, set the index from `--list-audio`, for example:

```sh
export COWINGMAN_AUDIO_DEVICE=1
```

Use the actual index; `1` is only an example. The input must support 16 kHz mono.

## Repair missing `pkg_resources` during model restoration

If the first error is `ModuleNotFoundError: No module named 'pkg_resources'`
inside Librosa's `core/intervals.py`, repair the active speech virtual environment:

```sh
git pull --ff-only
. .venv/bin/activate
python3 -m pip install 'setuptools>=68,<82'
python3 -m pip check
python3 -m cowingman.speech_dependencies
```

This only installs the compatibility package; it does not replace NVIDIA torch,
torchaudio, NeMo, or your verified model. Do not install a package named
`pkg_resources`. It is supplied by setuptools, and was
[removed in setuptools 82](https://setuptools.pypa.io/en/stable/history.html#v82-0-0).
The pinned shadow Librosa 0.10.1 still imports it. Both `audio` and `shadow` extras
now declare `setuptools>=68,<82` as a runtime dependency. A build-system dependency
alone is insufficient because pip can install it in an isolated build environment.
Keep this temporary compatibility bound until the speech/shadow stack is retested
with a newer Librosa. Do not broadly upgrade the Jetson's working speech stack.

NeMo may subsequently report `Can't instantiate abstract class ASRModel` after
the concrete model failed to instantiate. In this traceback it is a secondary
error: fix the earlier missing import first. Training/validation manifest warnings
from the saved model configuration do not require downloading training datasets.
The failure happens on CPU, before `.to("cuda")`; it does not establish a CUDA or
out-of-memory problem. If `pip check` finds other conflicts, resolve those against
the documented JetPack stack before continuing; do not remove torch constraints.

The preprocessing check exercises a synthetic mel filter, which catches lazy
imports that `import librosa` or `import nemo.collections.asr` alone can miss.
Next test the verified local archive and GPU inference, without microphone input
or a hosted-model request:

```sh
KERAS_BACKEND=torch HF_HUB_OFFLINE=1 TRANSFORMERS_OFFLINE=1 python3 - <<'PY'
import os
import numpy as np
import torch
from cowingman.config import ASR_MODEL
from cowingman.speech import verify_model
from cowingman.speech_dependencies import check_speech_dependencies

check_speech_dependencies()
from nemo.collections.asr.models import ASRModel

path = os.environ.get("COWINGMAN_ASR_MODEL_PATH") or "models/asr.nemo"
print("STEP 1: Verify archive", flush=True)
verify_model(path, ASR_MODEL)
print("STEP 2: Restore on CPU", flush=True)
model = ASRModel.restore_from(path, map_location="cpu").eval()
print("STEP 3: Move to CUDA", flush=True)
assert torch.cuda.is_available(), "CUDA unavailable"
model = model.to("cuda")
torch.cuda.synchronize()
print("STEP 4: Synthetic four-second inference", flush=True)
from cowingman.asr import NemoASR

adapter = NemoASR.__new__(NemoASR)
adapter.torch, adapter.model = torch, model
samples = np.zeros(64000, dtype=np.float32)
try:
    adapter.transcribe(samples)  # Exercise decoding; do not print recognized text.
    torch.cuda.synchronize()
finally:
    samples.fill(0)
print("ASR CPU RESTORE / CUDA / SYNTHETIC INFERENCE PASSED", flush=True)
PY
```

Silence checks execution, not recognition accuracy. After it passes:

1. Run `python3 -m unittest discover -s tests -v` and
   `python3 -m cowingman --offline --demo`.
2. Run `python3 -m cowingman --list-audio`, then
   `python3 -m cowingman --show-input` with the existing UF key. Speak a synthetic
   phrase, wait for “Speech fragment accepted privately,” then use `:check` and
   `:pause`/`:listen` to check capture without requesting a cue. `--offline`
   disables the microphone, so it cannot test this stage.
3. Run `python3 -m cowingman --health-check`, then repeat the microphone test
   and request `:cue`, followed by `:listen`. Repeat three times; verify `:quit`
   releases the microphone and GPU memory.
4. Run `python3 -m cowingman --rolling --show-input --timings private/asr-retest-01.jsonl`
   for at least two minutes. Check multiple cues, `:pause`/`:listen`, and summary
   updates. Review `python3 scripts/timing_report.py private/asr-retest-01.jsonl`
   for inference duration, capture age, and audio drops. Use `free -h` and
   `tegrastats` in another terminal to observe memory across repeated cycles.
5. Only after the baseline passes, add pause assistance, shadow scoring, S3, or
   TTS one at a time using their respective guides. For shadow scoring compare
   dropped windows and inference time against the baseline. TTS is tested outside
   rolling mode. Also verify microphone unplug handling and Ctrl-C cleanup.

Use a fresh timing filename for each run. Keep only content-free measurements;
do not save terminal transcripts or microphone recordings. Local mocked tests
cannot establish Jetson throughput, recognition quality, or live service success.

## Launch the live microphone demonstration

Make sure at least 2 GiB RAM is available, other GPU workloads are closed, and the
UF key remains exported in this shell. Then:

```sh
python3 -m cowingman
```

Wait for `[listening]`. Speak a short synthetic phrase, allow a four-second capture
window plus local transcription, and wait for “Speech fragment accepted privately.”
The notice also says the speaker was not identified; this is expected when one
microphone captures two people. Keep a test exchange brief and request the cue
soon after the user gets stuck so the relevant question remains in bounded context.
Then press Enter or enter `:cue`. A “No words recognized” notice means that window
produced no usable text; try again or use a typed fragment. The cue appears
for up to 20 seconds. The microphone/model stops for the request and stays paused
afterward; enter `:listen` to resume. Use `:quit` or Ctrl-C to release resources.
Requests also pause the microphone when context is empty or the provider fails;
use `:listen` before trying a fresh spoken example after those errors.
Typed fragments remain available in this same terminal if the microphone fails.

Optional pause assistance: `python3 -m cowingman --pause-assist`. It detects an
energy/silence pattern, not anxiety, stress, or speaker identity. It can send a
bounded request automatically. Use a personal close-talk microphone and keep
`:assist off` available. Prefer the manual trigger in the presentation.

## Optional spoken cues

Use visual output unless TTS has been tested on this Jetson beforehand:

```sh
python3 scripts/prepare_speech_models.py --tts
export COWINGMAN_FASTPITCH_PATH="$PWD/models/fastpitch.nemo"
export COWINGMAN_HIFIGAN_PATH="$PWD/models/hifigan.nemo"
python3 -m cowingman --tts
```

ASR exits before TTS starts. FastPitch unloads before HiFi-GAN. Model reloads can
be slow, TTS has a 45-second deadline, and model/GPU buffers are released with the
worker process. Use a headset. If TTS fails, the visual cue remains available.

## Exit and keep secrets private

```sh
unset NAVIGATOR_TOOLKIT_API_KEY
```

Never commit `.env`, keys, models, recordings, transcripts, logs, or generated
reports. No report is necessary to operate the product. The complete presentation
sequence and recovery actions are in [docs/PRESENTATION.md](docs/PRESENTATION.md).

## Optional research model integration

After the ordinary microphone/NeMo path works, install and verify the original
CNN+LSTM model in the same Jetson environment:

```bash
python3 -m pip install -e '.[shadow]'
python3 scripts/prepare_disfluency_model.py
python3 -m cowingman --disfluency-assist
```

This opts into experimental disfluency-plus-pause requests with default bounded
text, local-only audio, and no timing files by default. Wait for “Experimental
speech model ready”; after a cue, use `:listen` to resume. `:assist off` disables
automatic assistance while Enter/`:cue` remains available. Model failures leave
manual assistance available. See [MODEL_ASSIST.md](docs/MODEL_ASSIST.md) for the
exact trigger, dependency recovery, optional rolling mode and evaluation limits.
The original model's “anxiety” labeling is not supported by its training labels;
no anxiety or speaker-identity conclusion is displayed.
