"""Exercise lazy speech imports before NeMo can mask their original error."""

from .errors import SpeechError


def check_speech_dependencies():
    # Importing librosa alone does not load filters/core.intervals. Construct the
    # same kind of mel filter used by NeMo, without loading weights or audio.
    try:
        import librosa

        librosa.filters.mel(sr=16000, n_fft=512, n_mels=80)
    except ModuleNotFoundError as exc:
        if exc.name == "pkg_resources":
            raise SpeechError(
                "Speech dependencies need pkg_resources. In the active virtual environment run: "
                "python3 -m pip install 'setuptools>=68,<82'. "
                "Then run python3 -m cowingman.speech_dependencies; see RUN_ON_JETSON.md."
            ) from None
        raise SpeechError(
            "Speech dependency missing. Install the documented NeMo/audio environment; "
            "see RUN_ON_JETSON.md."
        ) from None
    except Exception:
        raise SpeechError(
            "Speech preprocessing check failed. Check the Librosa/NumPy environment; "
            "see RUN_ON_JETSON.md."
        ) from None


def main():
    try:
        check_speech_dependencies()
    except SpeechError as exc:
        print(str(exc))
        return 2
    print("Speech preprocessing passed (synthetic mel filter; no model or CUDA test).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
