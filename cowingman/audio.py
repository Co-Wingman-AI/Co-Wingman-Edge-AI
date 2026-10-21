"""Local microphone capture only; fixed-size RAM buffers, no recordings."""

from .errors import SpeechError
import queue
import threading
import time
from .timing import NO_TIMING

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


class ContinuousMicrophone:
    """One capture thread and one queued window; discard older backlog explicitly."""

    def __init__(self, device, threshold, timing=NO_TIMING):
        self.microphone = Microphone(device)
        self.threshold = threshold
        self.windows = queue.Queue(maxsize=1)
        self.stopped = threading.Event()
        self.ready = threading.Event()
        self.error = None
        self.dropped = 0
        self.thread = None
        self.timing = timing

    def open(self):
        self.thread = threading.Thread(target=self._capture, daemon=True)
        self.thread.start()
        if not self.ready.wait(5) or self.error:
            self.close()
            raise SpeechError("Continuous microphone failed to start. Check the audio device.")
        return self

    def _offer(self, window):
        try:
            self.windows.put_nowait(window)
        except queue.Full:
            try:
                old = self.windows.get_nowait()
                old[1].fill(0)
                self.dropped += 1
                self.timing.event("audio_drop", count=1)
            except queue.Empty:
                pass
            self.windows.put_nowait(window)

    def _capture(self):
        samples = None
        try:
            import numpy as np
            from .pause import PauseDetector

            detector = PauseDetector(threshold=self.threshold)
            with self.timing.measure("microphone_open"):
                self.microphone.open()
            self.ready.set()
            while not self.stopped.is_set():
                captured_at = time.monotonic()
                samples = np.zeros(BLOCK_FRAMES * CHUNK_BLOCKS, dtype=np.float32)
                voiced = pause = False
                for index in range(CHUNK_BLOCKS):
                    if self.stopped.is_set():
                        return
                    block = self.microphone.read()
                    rms = float(np.sqrt(np.mean(block * block)))
                    voiced = voiced or rms >= self.threshold
                    pause = detector.observe(rms, 0.25) or pause
                    samples[index * BLOCK_FRAMES : (index + 1) * BLOCK_FRAMES] = block
                    block.fill(0)
                self.timing.event("capture", captured_at, window_start=captured_at)
                self._offer((captured_at, samples, voiced, pause))
                samples = None
        except Exception:
            self.error = SpeechError(
                "Continuous microphone stopped. Check the device and use :listen."
            )
            self.ready.set()
        finally:
            if samples is not None:
                samples.fill(0)
            self.microphone.close()

    def read(self):
        while not self.stopped.is_set():
            if self.error:
                raise self.error
            try:
                return self.windows.get(timeout=0.25)
            except queue.Empty:
                pass
        raise SpeechError("Continuous microphone stopped.")

    def close(self):
        self.stopped.set()
        self.microphone.close()
        if self.thread:
            self.thread.join(timeout=1)
        while True:
            try:
                self.windows.get_nowait()[1].fill(0)
            except queue.Empty:
                break
