import hashlib
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from cowingman.audio import Microphone
from cowingman.config import ASR_MODEL, Config
from cowingman.errors import SpeechError
from cowingman.speech import SpeechSession, verify_model


class SpeechTests(unittest.TestCase):
    def test_missing_microphone_actionable(self):
        sd = Mock()
        sd.check_input_settings.side_effect = RuntimeError("sensitive library internals")
        with patch.dict("sys.modules", sounddevice=sd):
            with self.assertRaisesRegex(SpeechError, "Microphone unavailable") as caught:
                Microphone().open()
        self.assertNotIn("sensitive", str(caught.exception))

    def test_microphone_closes_after_failed_start(self):
        sd = Mock()
        sd.InputStream.return_value.start.side_effect = RuntimeError()
        with patch.dict("sys.modules", sounddevice=sd):
            with self.assertRaises(SpeechError):
                Microphone().open()
        sd.InputStream.return_value.close.assert_called_once()

    def test_verified_model_and_tampering(self):
        with tempfile.TemporaryDirectory() as directory:
            model = Path(directory) / "test.nemo"
            model.write_bytes(b"synthetic model")
            manifest = {
                "model_id": ASR_MODEL,
                "sha256": hashlib.sha256(model.read_bytes()).hexdigest(),
            }
            model.with_suffix(".json").write_text(json.dumps(manifest))
            verify_model(str(model), ASR_MODEL)
            model.write_bytes(b"different")
            with self.assertRaises(SpeechError):
                verify_model(str(model), ASR_MODEL)
        with self.assertRaises(SpeechError):
            verify_model("", ASR_MODEL)

    def test_session_missing_model_no_child(self):
        session = SpeechSession(Config())
        with self.assertRaises(SpeechError):
            session.start()
        self.assertIsNone(session.process)
        session.close()

    def test_hung_worker_is_killed_on_shutdown(self):
        session = SpeechSession(Config())
        process = Mock()
        process.is_alive.side_effect = [True, True]
        session.process = process
        connection = session.connection = Mock()
        session.close()
        process.terminate.assert_called_once()
        process.kill.assert_called_once()
        connection.close.assert_called_once()
        self.assertIsNone(session.process)

    def test_worker_failure_is_sanitized(self):
        session = SpeechSession(Config())
        session.process = Mock()
        session.process.is_alive.return_value = False
        session.connection = Mock()
        session.connection.poll.return_value = False
        events = session.poll()
        self.assertEqual(events[0][0], "error")
        self.assertIsNone(session.process)


class ASRAdapterTests(unittest.TestCase):
    def test_direct_tensor_decoding_handles_nemo_return_shapes(self):
        from cowingman.asr import NemoASR
        from contextlib import nullcontext

        adapter = NemoASR.__new__(NemoASR)
        adapter.torch = Mock()
        adapter.torch.inference_mode.return_value = nullcontext()
        adapter.model = Mock()
        adapter.model.return_value = ("logits", "lengths", "predictions")
        for result in [
            ["private fragment"],
            (["private fragment"], []),
            [Mock(text="private fragment")],
        ]:
            adapter.model.decoding.ctc_decoder_predictions_tensor.return_value = result
            text = adapter.transcribe(Mock(shape=[64000]))
            self.assertEqual(text, "private fragment")
            adapter.model.decoding.ctc_decoder_predictions_tensor.assert_called_with(
                "logits",
                decoder_lengths="lengths",
                return_hypotheses=False,
            )
        adapter.model.decoding.ctc_decoder_predictions_tensor.return_value = ["x" * 1000]
        self.assertEqual(len(adapter.transcribe(Mock(shape=[64000]))), 240)

    def test_no_devices_is_actionable(self):
        from cowingman.__main__ import main
        import contextlib
        import io

        sd = Mock()
        sd.query_devices.return_value = []
        output = io.StringIO()
        with patch.dict("sys.modules", sounddevice=sd), contextlib.redirect_stderr(output):
            self.assertEqual(main(["--list-audio"]), 2)
        self.assertIn("microphone", output.getvalue())
