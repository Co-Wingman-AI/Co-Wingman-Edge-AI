"""Local microphone capture only; fixed-size RAM buffers, no recordings."""

from .errors import SpeechError

SAMPLE_RATE = 16000
BLOCK_FRAMES = 4000
CHUNK_BLOCKS = 16  # Four seconds, bounded regardless of conversation duration.


class Microphone:
    def __init__(self, device=None):
        self.device = device
        self.stream = None

    def open(self):
        try:
            import sounddevice as sd

            sd.check_input_settings(
                device=self.device, channels=1, dtype="float32", samplerate=SAMPLE_RATE
            )
            self.stream = sd.InputStream(
                device=self.device,
                channels=1,
                dtype="float32",
                samplerate=SAMPLE_RATE,
                blocksize=BLOCK_FRAMES,
            )
            self.stream.start()
        except Exception:
            self.close()
            raise SpeechError(
                "Microphone unavailable. Check USB input and --list-audio; use --typed if needed."
            ) from None
        return self

    def read(self):
        try:
            samples, overflowed = self.stream.read(BLOCK_FRAMES)
            if overflowed:
                samples.fill(0)
                raise SpeechError("Audio overrun. Close other workloads or use --typed.")
            return samples[:, 0]
        except SpeechError:
            raise
        except Exception:
            raise SpeechError(
                "Microphone disconnected. Reconnect and use :listen, or switch to --typed."
            ) from None

    def close(self):
        if self.stream is not None:
            try:
                self.stream.abort()
            except Exception:
                pass
            try:
                self.stream.close()
            except Exception:
                pass
            self.stream = None
