"""Experimental local stuttering score. Never a cue trigger or anxiety inference."""

import hashlib
import math
import os
from pathlib import Path

from .errors import SpeechError

SOURCE_REVISION = "03288414382def0356e44ae1c4aca4d0fd6ad35d"
MODEL_SHA256 = "c3f4e2d568a68dee9c1a280b25e15ad8dd10f71f97604da038d80be48b6ec822"
MODEL_URL = (
    "https://raw.githubusercontent.com/Mrun9/Co-Wingman-AIS-Project/"
    + SOURCE_REVISION
    + "/App/best_cnn_lstm_stutter_model.keras"
)


def verify_shadow_model(path):
    try:
        file = Path(path)
        if file.suffix != ".keras" or not 0 < file.stat().st_size <= 8 * 1024**2:
            raise ValueError
        digest = hashlib.sha256(file.read_bytes()).hexdigest()
        if digest != MODEL_SHA256:
            raise ValueError
    except (OSError, ValueError):
        raise SpeechError(
            "Unverified disfluency model. Run scripts/prepare_disfluency_model.py."
        ) from None


def features(samples):
    import librosa
    import numpy as np

    # Match the upstream MFCC + delta layout, with the application's fixed 16 kHz input.
    mfcc = librosa.feature.mfcc(y=samples, sr=16000, n_mfcc=40)
    result = np.vstack([mfcc, librosa.feature.delta(mfcc)])
    if result.shape[1] < 200:
        result = np.pad(result, ((0, 0), (0, 200 - result.shape[1])))
    return result[:, :200][None, ..., None].astype("float32")


class ShadowDetector:
    def __init__(self, path, timing):
        verify_shadow_model(path)
        # Reuse the installed Jetson PyTorch; do not install a conflicting TensorFlow/CUDA stack.
        os.environ["KERAS_BACKEND"] = "torch"
        import keras

        if keras.backend.backend() != "torch":
            raise SpeechError("Disfluency shadow mode requires the Keras PyTorch backend.")
        self.keras = keras
        self.timing = timing
        self.tail = None
        self.last_start = None
        with keras.device("cpu"):
            self.model = keras.saving.load_model(path, compile=False, safe_mode=True)
        # Librosa/Numba can compile on first use. Pay that cost before opening capture.
        import numpy as np
        import torch

        silence = np.zeros(80000, dtype="float32")
        data = None
        try:
            data = features(silence)
            with torch.inference_mode(), keras.device("cpu"):
                self.model(data, training=False)
        finally:
            silence.fill(0)
            if data is not None:
                data.fill(0)

    def observe(self, samples, captured_at, voiced):
        import numpy as np
        import torch

        # Five-second windows, updated every four seconds. Never join across a dropped window.
        if samples.shape != (64000,) or not np.isfinite(samples).all():
            raise SpeechError("Invalid shadow audio window.")
        previous = self.tail
        contiguous = self.last_start is not None and 3.5 <= captured_at - self.last_start <= 4.5
        self.tail = samples[-16000:].copy()
        self.last_start = captured_at
        window = data = None
        try:
            if previous is None or not contiguous or not voiced:
                return
            window = np.concatenate((previous, samples))
            with self.timing.measure("disfluency_inference", window_start=captured_at - 1):
                data = features(window)
                with torch.inference_mode(), self.keras.device("cpu"):
                    score = float(self.model(data, training=False).detach().cpu().numpy()[0, 0])
                if not math.isfinite(score) or not 0 <= score <= 1:
                    raise SpeechError("Invalid shadow score.")
            self.timing.event("disfluency_score", window_start=captured_at - 1, score=score)
        finally:
            for value in (previous, window, data):
                if value is not None:
                    value.fill(0)

    def close(self):
        if self.tail is not None:
            self.tail.fill(0)
        self.tail = self.model = None
