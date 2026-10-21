# Local NVIDIA speech implementation

## Selection and evidence

The stored Jetson benchmark was read before choosing speech components. It
identified an Orin Nano 8 GB with L4T 36.4.7; local Nemotron consumed roughly
4.47 GiB RSS with only 294 MiB minimum available RAM and 361 MiB swap growth.
Those findings rule out a local LLM in this application's production path.

[NVIDIA Conformer CTC Small](https://huggingface.co/nvidia/stt_en_conformer_ctc_small)
is an English NVIDIA ASR model with approximately 13 million parameters. Its size
makes it a more plausible initial choice than loading a large streaming speech
server alongside other models. This is a resource-based engineering choice,
not a measured Jetson latency or memory claim. The model card notes limitations
with accents, technical terms, and domain mismatch.

Current [Riva quick-start documentation](https://docs.nvidia.com/deeplearning/riva/user-guide/docs/public/quick-start-guide.html)
targets Jetson Thor. Earlier Riva releases list Orin and specific JetPack versions,
but their published memory budgets make a complete concurrent service stack
unattractive here. Co-Wingman therefore uses direct local NeMo inference and no
Riva server. It does not treat generic “Jetson support” as proof of Orin Nano 8 GB
compatibility. The selected software stack still requires physical validation.

## Runtime behavior

The default behavior below remains available. With `--rolling`, a separate capture
thread keeps the microphone open while NeMo transcribes the previous four-second
window. One additional completed window can wait in RAM; older queued audio is
zeroed/discarded with a gap notice when inference cannot keep up. The application
keeps ASR running during and after visual cues. `:pause` stops it; `:listen` restarts
it. This mode excludes TTS. Text context spans at most one minute, and summary/S3
behavior is documented in [AWS_SUMMARIES.md](AWS_SUMMARIES.md). Continuous capture
still needs sustained physical Jetson testing; no gap-free performance is claimed.

- Capture: sounddevice / PortAudio, mono float32, 16,000 Hz, 0.25-second blocks.
- Window: 16 blocks / four seconds in RAM. The microphone closes while each window
  is transcribed. There is no disk audio, resampler, stream queue, or recording file.
- ASR: trusted NVIDIA `.nemo` archive restored on CPU and moved to CUDA, evaluation
  mode, direct forward pass and greedy CTC decoding. No file-based manifest API.
- Selection: only the last 240 characters of a normalized result leave the local
  worker. No automatic speaker attribution. Silent windows skip ASR.
- Supervision: a spawned child isolates dependency output and CUDA allocations.
  No event for 90 seconds triggers termination and an actionable error.
- Memory: require 2 GiB MemAvailable before model loading and stop below 1 GiB
  between windows. Checks are conservative guards, not reserved memory or OOM proof.
- Trigger: Enter or `:cue` immediately stops the speech worker and cancels any
  incomplete window. Recent completed fragments can then be used for a cue.
- Resume: after a cue, use `:listen` to load ASR again. This intentionally avoids
  recapturing a spoken cue and keeps the screen cue stable.

Optional pause assistance uses RMS energy above a configurable threshold for at
least one second, followed by three seconds of silence, and a 30-second request
cooldown. Detection timing follows captured samples; ASR gaps add wall-clock delay.
It can mistake noise or ordinary turn-taking for a pause, and miss quiet speech.
It does not estimate stress, anxiety, confidence, or clinical status. Start disabled;
use a consenting operator's personal microphone. There is no automatic enrollment.

## Optional TTS

The explicit setup script downloads NVIDIA `tts_en_fastpitch` and
`tts_en_hifigan`. [NVIDIA's TTS API](https://docs.nvidia.com/nemo-framework/user-guide/24.07/nemotoolkit/tts/api.html)
provides spectrogram generation and vocoder conversion. ASR exits before a TTS
worker starts. FastPitch generates a CPU spectrogram and unloads; HiFi-GAN then
loads and generates in-memory output. sounddevice plays it locally, without WAV
files. Playback is capped at 20 seconds and the worker deadline is 45 seconds.
Missing archives, output devices, CUDA, text-processing dependencies, and timeouts
produce a short error and leave visual output available. No cloud TTS is used.

The combined dependency installation is heavyweight even though the ASR model is
small. NeMo 2.4.0 is the documented starting version; the NVIDIA CUDA-enabled torch
and matching torchaudio must match the actual JetPack. Do not silently replace them
with CPU wheels. Model restore can extract model assets to temporary storage;
these are model weights/tokenizers, never microphone or transcript files.

## Physical verification still required

On the actual Jetson, verify CUDA imports, model download/restore, 16 kHz device
capture, ASR accuracy and latency, memory headroom over repeated requests, Ctrl-C
cleanup, microphone unplug handling, and optional sequential TTS. Check pause
assistance separately with synthetic speech and long ordinary pauses. Keep the
explicit trigger for the presentation. These tests require hardware and weights;
normal unit tests intentionally require neither.
