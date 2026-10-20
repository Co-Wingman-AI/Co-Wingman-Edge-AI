"""One small NVIDIA CTC model; direct tensor inference avoids audio manifests."""

from .errors import SpeechError


class NemoASR:
    def __init__(self, path):
        try:
            import torch
            from nemo.collections.asr.models import ASRModel

            if not torch.cuda.is_available():
                raise SpeechError(
                    "CUDA unavailable. Install NVIDIA PyTorch for your JetPack; use --typed meanwhile."
                )
            self.torch = torch
            self.model = ASRModel.restore_from(path, map_location="cpu").eval().to("cuda")
            if not hasattr(self.model, "ctc_decoder_predictions_tensor") and not hasattr(
                self.model, "decoding"
            ):
                raise SpeechError(
                    "Unsupported ASR archive. Run scripts/prepare_speech_models.py --asr."
                )
        except SpeechError:
            raise
        except Exception:
            raise SpeechError(
                "NeMo ASR could not load. Check JetPack/PyTorch compatibility and the model setup guide."
            ) from None

    def transcribe(self, samples):
        torch = self.torch
        signal = lengths = logits = encoded_lengths = _predictions = decoded = None
        try:
            with torch.inference_mode():
                signal = torch.as_tensor(samples, dtype=torch.float32, device="cuda").unsqueeze(0)
                lengths = torch.tensor([samples.shape[0]], dtype=torch.long, device="cuda")
                logits, encoded_lengths, _predictions = self.model(
                    input_signal=signal, input_signal_length=lengths
                )
                decoded = self.model.decoding.ctc_decoder_predictions_tensor(
                    logits,
                    decoder_lengths=encoded_lengths,
                    return_hypotheses=False,
                )
                # NeMo versions return list[str], list[Hypothesis], or (best, all).
                if isinstance(decoded, tuple):
                    decoded = decoded[0]
                text = decoded[0]
                if hasattr(text, "text"):
                    text = text.text
                if type(text) is not str:
                    raise ValueError
                return " ".join(text[-2048:].split())[-240:]
        except Exception:
            raise SpeechError(
                "Local transcription failed. Check available RAM and NeMo; use --typed if needed."
            ) from None
        finally:
            signal = lengths = logits = encoded_lengths = _predictions = decoded = None
