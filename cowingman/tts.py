"""Optional NVIDIA FastPitch + HiFi-GAN, in a process after ASR exits."""

from .errors import SpeechError


def speak_local(cue, fastpitch_path, hifigan_path):
    try:
        import sounddevice as sd
        import torch
        from nemo.collections.tts.models import FastPitchModel, HifiGanModel

        if not torch.cuda.is_available():
            raise ValueError
        with torch.inference_mode():
            fastpitch = (
                FastPitchModel.restore_from(fastpitch_path, map_location="cpu").eval().to("cuda")
            )
            tokens = fastpitch.parse(cue)
            spec = fastpitch.generate_spectrogram(tokens=tokens).cpu()
            sample_rate = int(fastpitch.cfg.sample_rate)
            # Unload the text model before loading the vocoder as well.
            del fastpitch, tokens
            import gc

            gc.collect()
            torch.cuda.empty_cache()
            hifigan = HifiGanModel.restore_from(hifigan_path, map_location="cpu").eval().to("cuda")
            samples = hifigan.convert_spectrogram_to_audio(spec=spec.to("cuda"))[0].cpu().numpy()
            try:
                if samples.size > sample_rate * 20:
                    raise ValueError
                sd.play(samples, sample_rate, blocking=True)
            finally:
                sd.stop()
                samples.fill(0)
    except Exception:
        raise SpeechError(
            "Local TTS unavailable. The visual cue remains available; check models and audio output."
        ) from None
