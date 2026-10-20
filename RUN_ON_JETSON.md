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

Type one short fragment and press Enter, then enter `:cue`. Input stays hidden;
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

## Launch the live microphone demonstration

Make sure at least 2 GiB RAM is available, other GPU workloads are closed, and the
UF key remains exported in this shell. Then:

```sh
python3 -m cowingman
```

Wait for `[listening]`. Speak a short synthetic phrase, allow a four-second capture
window plus local transcription, then press Enter or enter `:cue`. The cue appears
for up to 20 seconds. The microphone/model stops for the request and stays paused
afterward; enter `:listen` to resume. Use `:quit` or Ctrl-C to release resources.
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
