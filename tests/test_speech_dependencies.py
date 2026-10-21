import contextlib
import io
import unittest
from unittest.mock import Mock, patch

from cowingman.asr import NemoASR
from cowingman.errors import SpeechError
from cowingman.speech_dependencies import check_speech_dependencies, main
from cowingman.tts import speak_local


class SpeechDependencyTests(unittest.TestCase):
    def test_exercises_lazy_mel_filter(self):
        librosa = Mock()
        with patch.dict("sys.modules", librosa=librosa):
            check_speech_dependencies()
        librosa.filters.mel.assert_called_once_with(sr=16000, n_fft=512, n_mels=80)

    def test_missing_pkg_resources_before_model_restore(self):
        librosa = Mock()
        librosa.filters.mel.side_effect = ModuleNotFoundError(
            "private dependency detail", name="pkg_resources"
        )
        asr_class = Mock()
        with patch.dict(
            "sys.modules",
            {"librosa": librosa, "nemo.collections.asr.models": Mock(ASRModel=asr_class)},
        ):
            with self.assertRaisesRegex(SpeechError, "setuptools>=68,<82") as caught:
                NemoASR("unused.nemo")
        asr_class.restore_from.assert_not_called()
        self.assertNotIn("private", str(caught.exception))

    def test_other_missing_modules_do_not_suggest_setuptools(self):
        librosa = Mock()
        librosa.filters.mel.side_effect = ModuleNotFoundError("private", name="scipy")
        with patch.dict("sys.modules", librosa=librosa):
            with self.assertRaisesRegex(SpeechError, "dependency missing") as caught:
                check_speech_dependencies()
        self.assertNotIn("setuptools", str(caught.exception))
        self.assertNotIn("private", str(caught.exception))

    def test_other_failures_are_sanitized(self):
        librosa = Mock()
        librosa.filters.mel.side_effect = RuntimeError("private")
        with patch.dict("sys.modules", librosa=librosa):
            with self.assertRaisesRegex(SpeechError, "preprocessing check failed") as caught:
                check_speech_dependencies()
        self.assertNotIn("private", str(caught.exception))

    def test_modern_librosa_does_not_require_pkg_resources(self):
        with patch.dict("sys.modules", {"librosa": Mock(), "pkg_resources": None}):
            check_speech_dependencies()

    def test_successful_preflight_keeps_cpu_restore_then_cuda(self):
        torch, asr_class = Mock(), Mock()
        with patch.dict(
            "sys.modules",
            {
                "librosa": Mock(),
                "torch": torch,
                "nemo.collections.asr.models": Mock(ASRModel=asr_class),
            },
        ):
            adapter = NemoASR("verified.nemo")
        asr_class.restore_from.assert_called_once_with("verified.nemo", map_location="cpu")
        asr_class.restore_from.return_value.eval.return_value.to.assert_called_once_with("cuda")
        self.assertIs(adapter.torch, torch)

    def test_tts_preserves_actionable_dependency_error(self):
        with patch(
            "cowingman.tts.check_speech_dependencies", side_effect=SpeechError("repair dependency")
        ):
            with self.assertRaisesRegex(SpeechError, "repair dependency"):
                speak_local("unused", "unused", "unused")

    def test_check_exit_status(self):
        for error, expected in [(None, 0), (SpeechError("repair dependency"), 2)]:
            with (
                patch("cowingman.speech_dependencies.check_speech_dependencies", side_effect=error),
                contextlib.redirect_stdout(io.StringIO()),
            ):
                self.assertEqual(main(), expected)
