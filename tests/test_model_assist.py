"""Offline coverage of model evidence, worker routing, privacy and explicit opt-in."""

from contextlib import redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, patch

from cowingman.__main__ import main, parser
from cowingman.app import Application
from cowingman.config import Config
from cowingman.disfluency import ModelPauseGate
from cowingman.errors import SpeechError
from cowingman.provider import NavigatorClient, OfflineClient
from cowingman.speech import _speech_worker
from test_application import FakeUI
from cowingman.timing import Timing
from scripts.timing_report import summarize


class GateTests(unittest.TestCase):
    def test_repeated_evidence_requires_pause_and_is_consumed(self):
        gate = ModelPauseGate()
        self.assertFalse(gate.observe(0.8, 100, False, 104))
        self.assertFalse(gate.observe(0.7, 104, False, 108))
        self.assertTrue(gate.observe(None, 108, True, 112))
        self.assertFalse(gate.observe(None, 112, True, 116))

    def test_one_score_low_score_or_missing_window_cannot_arm(self):
        for scores in ((None, 0.9), (0.9, 0.49), (0.9, None)):
            gate = ModelPauseGate()
            gate.observe(scores[0], 100, False, 104)
            self.assertFalse(gate.observe(scores[1], 104, True, 108))

    def test_stale_future_invalid_or_discontinuous_evidence_is_rejected(self):
        for score, start, now in (
            (0.9, 120, 124),
            (0.9, 104, 130),
            (0.9, 104, 100),
            (float("nan"), 104, 108),
            (True, 104, 108),
            (1.1, 104, 108),
            ("private sentinel", 104, 108),
            (0.9, float("inf"), 108),
            (0.9, 100, 104),
        ):
            gate = ModelPauseGate()
            gate.observe(0.9, 100, False, 104)
            self.assertFalse(gate.observe(score, start, True, now))

    def test_evidence_expires_and_explicit_reset_discards_it(self):
        gate = ModelPauseGate()
        gate.observe(0.9, 100, False, 104)
        gate.observe(0.9, 104, False, 108)
        gate.observe(None, 108, False, 112)
        gate.observe(None, 112, False, 116)
        self.assertFalse(gate.observe(None, 116, True, 120))
        gate.observe(0.9, 120, False, 124)
        gate.observe(0.9, 124, False, 128)
        gate.reset()
        self.assertFalse(gate.observe(None, 128, True, 132))


def worker_events(*, load_error=False, scores=(None, 0.8, 0.9), assist=True):
    connection, samples = Mock(), Mock()
    capture = Mock(dropped=0)
    capture.read.side_effect = [
        (100, samples, True, False),
        (104, samples, True, False),
        (108, samples, True, True),
        SpeechError("test end"),
    ]
    model = Mock()
    model.transcribe.return_value = "synthetic conversation fragment"
    shadow = Mock()
    shadow.observe.side_effect = scores
    with (
        patch("cowingman.speech.prepare_worker"),
        patch("cowingman.speech.available_memory", return_value=3 * 1024**3),
        patch("cowingman.speech.time.monotonic", return_value=112),
        patch.dict("sys.modules", numpy=Mock()),
        patch("cowingman.asr.NemoASR", return_value=model),
        patch("cowingman.audio.ContinuousMicrophone") as microphone,
        patch("cowingman.disfluency.ShadowDetector") as detector,
    ):
        microphone.return_value.open.return_value = capture
        if load_error:
            detector.side_effect = RuntimeError("private sentinel")
        else:
            detector.return_value = shadow
        _speech_worker(
            connection, "model", None, 0.015, True, disfluency_path="model", model_assist=assist
        )
    capture.close.assert_called_once()
    connection.close.assert_called_once()
    samples.fill.assert_called_with(0)
    if not load_error:
        shadow.close.assert_called_once()
    model.transcribe.assert_called()
    return [call.args[0] for call in connection.send.call_args_list]


class IntegrationTests(unittest.TestCase):
    def test_worker_to_application_to_bounded_text_cue(self):
        sent = worker_events()
        self.assertIn(("model_status", True), sent)
        self.assertIn(("model_pause", 112), sent)
        self.assertNotIn(("pause", None), sent)
        requests = []

        def transport(url, headers, payload, timeout):
            requests.append(json.loads(json.dumps(payload)))
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "cue": "Let me explain the next step.",
                                    "intent": "resume",
                                    "should_offer": True,
                                }
                            )
                        }
                    }
                ]
            }

        audio, ui = Mock(process=object()), FakeUI()
        audio.poll.return_value = [event for event in sent if event[0] != "error"]
        client = NavigatorClient("synthetic-key", transport=transport)
        app = Application(
            Config(),
            client,
            ui,
            audio=audio,
            pause_assist=True,
            model_assist=True,
            clock=lambda: 112,
        )
        app.tick()
        self.assertEqual(len(ui.cues), 1)
        self.assertEqual(len(requests), 1)
        body = json.loads(requests[0]["messages"][1]["content"])
        self.assertLessEqual(len(body["recent_fragments"]), 4)
        self.assertLessEqual(sum(len(t["text"]) for t in body["recent_fragments"]), 800)
        self.assertNotIn("score", json.dumps(requests))
        self.assertNotIn("model_pause", json.dumps(requests))
        self.assertNotIn("synthetic conversation fragment", repr(ui.messages))
        self.assertEqual(len(app.context), 0)
        audio.close.assert_called()
        app.close()
        self.assertEqual(client._api_key, "")

    def test_shadow_stays_observation_only_and_failures_never_fall_back_to_pause(self):
        shadow = worker_events(assist=False)
        self.assertNotIn(("model_pause", 112), shadow)
        self.assertIn(("pause", None), shadow)  # only the separately opted-in pause path
        for kwargs in (
            {"load_error": True},
            {"scores": (None, 0.8, RuntimeError("private sentinel"))},
        ):
            sent = worker_events(**kwargs)
            self.assertIn(("model_status", False), sent)
            self.assertFalse(any(kind in {"model_pause", "pause"} for kind, _ in sent))
            self.assertNotIn("private sentinel", repr(sent))
            self.assertTrue(any(kind == "fragment" for kind, _ in sent))

    def make_app(self, **kwargs):
        audio = Mock(process=object())
        audio.poll.return_value = []
        app = Application(
            Config(),
            Mock(wraps=OfflineClient()),
            FakeUI(),
            audio=audio,
            model_assist=True,
            pause_assist=True,
            clock=lambda: 112,
            **kwargs,
        )
        app.add("synthetic fragment")
        return app

    def test_only_fresh_model_pause_when_ready_and_enabled_can_trigger(self):
        for event in (
            ("pause", None),
            ("disfluency_score", 0.99),
            ("model_pause", 99),
            ("model_pause", 113),
            ("model_pause", float("nan")),
            ("model_pause", "text"),
        ):
            app = self.make_app()
            app.audio.poll.return_value = [("model_status", True), event]
            app.tick()
            app.client.request_cue.assert_not_called()
            app.close()
        for ready, enabled in ((False, True), (True, False)):
            app = self.make_app()
            if not enabled:
                app.command(":assist off")
            app.audio.poll.return_value = [("model_status", ready), ("model_pause", 112)]
            app.tick()
            app.client.request_cue.assert_not_called()
            app.command(":cue")
            self.assertEqual(len(app.ui.cues), 1)  # manual remains usable
            app.close()

    def test_model_events_cannot_enable_unselected_mode(self):
        app = Application(
            Config(),
            Mock(wraps=OfflineClient()),
            FakeUI(),
            clock=lambda: 112,
            audio=Mock(process=object()),
            pause_assist=True,
        )
        app.audio.poll.return_value = [
            ("model_status", True),
            ("fragment", "test"),
            ("model_pause", 112),
        ]
        app.tick()
        app.client.request_cue.assert_not_called()
        app.close()

    def test_shared_cooldown_after_manual_cue_and_toggle(self):
        app = self.make_app(rolling=True)
        app.command(":cue")
        app.audio.poll.return_value = [("model_status", True), ("model_pause", 112)]
        app.tick()
        self.assertEqual(app.client.request_cue.call_count, 1)
        app.command(":assist off")
        app.command(":assist on")
        app.tick()
        self.assertEqual(app.client.request_cue.call_count, 1)
        app.close()

    def test_slow_summary_cannot_revive_queued_model_trigger(self):
        app = self.make_app(rolling=True, memory=Mock())
        now = [112]
        app.clock = lambda: now[0]
        app.audio.poll.return_value = [("model_status", True), ("model_pause", 112)]
        app.memory.flush.side_effect = lambda: now.__setitem__(0, 130)
        app.tick()
        app.client.request_cue.assert_not_called()
        app.close()

    def test_opt_in_numeric_report_distinguishes_model_assisted_requests(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "timings.jsonl"
            trace = Timing.create(path)
            trace.event("disfluency_score", score=0.8)
            app = self.make_app(timing=trace)
            app.audio.poll.return_value = [("model_status", True), ("model_pause", 112)]
            app.tick()
            report = summarize(path)
            self.assertTrue(report["shadow"]["automatic_cue_trigger"])
            self.assertEqual(report["shadow"]["model_assisted_requests"], 1)
            self.assertNotIn("synthetic fragment", path.read_text())
            self.assertFalse(report["shadow"]["anxiety_inference"])
            app.close()

    def test_cli_opt_in_and_conflicting_modes(self):
        self.assertIsNone(parser().parse_args([]).disfluency_assist)
        self.assertEqual(
            parser().parse_args(["--disfluency-assist"]).disfluency_assist,
            "models/disfluency.keras",
        )
        for other in (
            "--typed",
            "--offline",
            "--demo",
            "--health-check",
            "--list-audio",
            "--pause-assist",
        ):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main(["--disfluency-assist", "model", other])
        with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
            main(["--disfluency-assist", "model", "--disfluency-shadow", "model"])

    def test_cli_wires_model_to_continuous_audio_without_rolling_or_recording(self):
        with (
            patch("cowingman.__main__.Config.load", return_value=Config(api_key="test")),
            patch("cowingman.__main__.SpeechSession") as audio,
            patch("cowingman.__main__.Application") as app,
            patch("cowingman.__main__.TerminalUI"),
        ):
            self.assertEqual(main(["--disfluency-assist"]), 0)
        self.assertTrue(audio.call_args.kwargs["continuous"])
        self.assertTrue(audio.call_args.kwargs["model_assist"])
        self.assertEqual(audio.call_args.kwargs["disfluency_path"], "models/disfluency.keras")
        self.assertFalse(app.call_args.kwargs["rolling"])
        self.assertIsNone(app.call_args.kwargs["memory"])
        self.assertIsNone(app.call_args.kwargs["timing"].path)
        self.assertTrue(app.call_args.kwargs["pause_assist"])
        app.return_value.run.assert_called_once_with(demo=False)
