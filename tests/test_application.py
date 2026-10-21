import io
import subprocess
import sys
import unittest
from unittest.mock import Mock, patch

from cowingman.app import Application
from cowingman.config import Config
from cowingman.cue import Cue
from cowingman.errors import CloudRequestError, SpeechError
from cowingman.pause import PauseDetector
from cowingman.provider import OfflineClient
from cowingman.ui import TerminalUI


class FakeUI:
    def __init__(self, commands=()):
        self.commands = iter(commands)
        self.messages = []
        self.cues = []

    def message(self, value):
        self.messages.append(value)

    def status(self, value):
        self.messages.append(value)

    def show_cue(self, cue):
        self.cues.append(cue)

    def clear_cue(self):
        pass

    def tick(self):
        pass

    def read_command(self):
        return next(self.commands, ":quit")


class ApplicationTests(unittest.TestCase):
    def make_app(self, **kwargs):
        ui = kwargs.pop("ui", FakeUI())
        client = kwargs.pop("client", OfflineClient())
        return Application(Config.load(offline=True, environ={}), client, ui, **kwargs)

    def test_offline_end_to_end_and_clean_shutdown(self):
        ui = FakeUI(["private fragment", ":cue", ":quit"])
        app = self.make_app(ui=ui)
        app.run()
        self.assertEqual(len(ui.cues), 1)
        self.assertEqual(len(app.context), 0)
        self.assertTrue(app.closed)
        self.assertNotIn("private fragment", repr(ui.messages))
        app.close()  # idempotent

    def test_failure_drops_context_and_does_not_present(self):
        client = Mock()
        client.request_cue.side_effect = CloudRequestError("Network unavailable.")
        app = self.make_app(client=client)
        app.add("private fragment")
        app.request_cue()
        self.assertEqual(len(app.context), 0)
        self.assertEqual(app.ui.cues, [])
        self.assertNotIn("private fragment", repr(app.ui.messages))

    def test_no_context_and_expiration(self):
        now = [0.0]
        app = self.make_app(clock=lambda: now[0])
        app.add("private fragment")
        now[0] = 61
        app.tick()
        self.assertEqual(app.context._items, [])
        app.request_cue()
        self.assertFalse(app.ui.cues)

    def test_audio_shutdown_before_tts(self):
        audio = Mock(process=object())
        events = []
        audio.close.side_effect = lambda: events.append("close")

        def speaker(cue, config):
            events.append("speak")

        app = self.make_app(audio=audio, tts=True, speaker=speaker)
        app.add("hello")
        app.request_cue()
        self.assertEqual(events, ["close", "speak"])
        self.assertTrue(app.pending_resume)
        app.close()
        self.assertEqual(events[-1], "close")

    def test_tts_failure_preserves_visual_cue(self):
        speaker = Mock(side_effect=SpeechError("TTS unavailable."))
        app = self.make_app(tts=True, speaker=speaker)
        app.add("hello")
        app.request_cue()
        self.assertTrue(app.ui.cues)
        self.assertEqual(len(app.context), 0)

    def test_missing_audio_still_allows_typed_flow(self):
        audio = Mock(process=None)
        audio.start.side_effect = SpeechError("Microphone unavailable.")
        audio.poll.return_value = []
        app = self.make_app(audio=audio, ui=FakeUI(["hello", ":cue", ":quit"]))
        app.run()
        self.assertEqual(len(app.ui.cues), 1)
        audio.close.assert_called()

    def test_audio_feedback_distinguishes_empty_and_accepted_text_privately(self):
        audio = Mock(process=object())
        audio.poll.side_effect = [
            [("empty_fragment", None), ("status", "listening")],
            [("fragment", "private speech sentinel"), ("status", "listening")],
        ]
        app = self.make_app(audio=audio)
        app.tick()
        self.assertEqual(len(app.context), 0)
        self.assertIn("No words recognized", " ".join(app.ui.messages))
        self.assertNotIn("Speech fragment accepted", " ".join(app.ui.messages))
        app.tick()
        self.assertEqual(len(app.context), 1)
        self.assertIn("Speech fragment accepted privately", " ".join(app.ui.messages))
        self.assertNotIn("private speech sentinel", " ".join(app.ui.messages))
        app.request_cue()
        self.assertEqual(len(app.ui.cues), 1)
        self.assertEqual(len(app.context), 0)
        # No resume message may clear a successful visual cue.
        self.assertNotIn("Microphone paused", " ".join(app.ui.messages))

    def test_failed_or_empty_audio_request_explains_how_to_resume(self):
        for has_context in (False, True):
            with self.subTest(has_context=has_context):
                audio = Mock(process=object())
                client = Mock()
                client.request_cue.side_effect = CloudRequestError("Cue rejected.")
                app = self.make_app(audio=audio, client=client)
                if has_context:
                    app.add("private fragment")
                app.request_cue()
                self.assertTrue(app.pending_resume)
                self.assertIn("Use :listen before speaking again", " ".join(app.ui.messages))
                self.assertEqual(len(app.context), 0)
                self.assertEqual(client.request_cue.call_count, int(has_context))

    def test_pause_opt_in_and_cooldown(self):
        audio = Mock(process=object())
        audio.poll.return_value = [("fragment", "hello"), ("pause", None)]
        now = [50.0]
        app = self.make_app(audio=audio, clock=lambda: now[0])
        app.tick()
        self.assertEqual(len(app.ui.cues), 0)
        app.command(":assist on")
        app.tick()
        self.assertEqual(len(app.ui.cues), 1)
        now[0] = 55
        app.tick()
        self.assertEqual(len(app.ui.cues), 1)
        app.command(":assist off")
        now[0] = 90
        app.tick()
        self.assertEqual(len(app.ui.cues), 1)

    def test_rejected_speech_discards_context_and_preserves_typed_fallback(self):
        for rejected in ("private\x00speech", b"private audio bytes"):
            with self.subTest(kind=type(rejected).__name__):
                audio = Mock(process=object())
                audio.poll.side_effect = [
                    [("fragment", rejected), ("fragment", "stale pending speech")],
                    [],
                    [],
                ]
                ui = FakeUI(["fresh typed fragment", ":cue", ":quit"])
                client = Mock(wraps=OfflineClient())
                app = self.make_app(audio=audio, ui=ui, client=client)
                app.add("earlier private fragment")
                app.run()
                self.assertTrue(app.closed)
                audio.close.assert_called()
                context = client.request_cue.call_args.args[0]
                self.assertEqual([turn.text for turn in context.turns], ["fresh typed fragment"])
                self.assertEqual(len(ui.cues), 1)
                self.assertEqual(len(app.context), 0)
                self.assertIn("Local speech returned unsupported text", " ".join(ui.messages))
                self.assertNotIn("private", " ".join(ui.messages).replace("privately", ""))
                self.assertNotIn("stale pending speech", " ".join(ui.messages))

    def test_clear_stops_in_flight_audio(self):
        audio = Mock(process=object())
        app = self.make_app(audio=audio)
        app.add("private")
        app.command(":clear")
        self.assertEqual(len(app.context), 0)
        audio.close.assert_called_once()

    def test_no_offer_is_never_spoken(self):
        client = Mock()
        client.request_cue.return_value = (Cue("Could you clarify?", "clarify", False), {})
        speaker = Mock()
        app = self.make_app(client=client, tts=True, speaker=speaker)
        app.add("hello")
        app.request_cue()
        speaker.assert_not_called()

    def test_interrupt_closes_resources(self):
        ui = FakeUI()
        ui.read_command = Mock(side_effect=KeyboardInterrupt)
        audio = Mock(process=None)
        audio.poll.return_value = []
        app = self.make_app(ui=ui, audio=audio)
        with self.assertRaises(KeyboardInterrupt):
            app.run()
        self.assertTrue(app.closed)
        audio.close.assert_called()


class TerminalAndCLITests(unittest.TestCase):
    def test_redirected_cue_never_printed(self):
        stream = io.StringIO()
        ui = TerminalUI(stdout=stream)
        ui.show_cue(Cue("private cue", "respond", True))
        self.assertNotIn("private cue", stream.getvalue())
        self.assertIn("suppressed", stream.getvalue())

    def test_real_cli_offline_and_typed_flows(self):
        for args, stdin in [
            (["--offline", "--demo"], ""),
            (["--typed", "--offline"], "private sentinel\n:cue\n:quit\n"),
        ]:
            completed = subprocess.run(
                [sys.executable, "-m", "cowingman", *args],
                input=stdin,
                capture_output=True,
                text=True,
                timeout=10,
            )
            self.assertEqual(completed.returncode, 0, completed.stderr)
            self.assertIn("Cue validated", completed.stdout)
            self.assertNotIn("private sentinel", completed.stdout + completed.stderr)
            self.assertNotIn("Could you repeat", completed.stdout + completed.stderr)
            self.assertIn("temporary context discarded", completed.stdout)

    def test_missing_key_message_without_traceback(self):
        import os

        env = dict(os.environ)
        env.pop("NAVIGATOR_TOOLKIT_API_KEY", None)
        completed = subprocess.run(
            [sys.executable, "-m", "cowingman", "--typed"],
            env=env,
            input="",
            capture_output=True,
            text=True,
            timeout=10,
        )
        self.assertEqual(completed.returncode, 2)
        self.assertIn("NAVIGATOR_TOOLKIT_API_KEY", completed.stderr)
        self.assertNotIn("Traceback", completed.stderr)


class PauseTests(unittest.TestCase):
    def test_silence_alone_never_triggers(self):
        detector = PauseDetector()
        self.assertFalse(any(detector.observe(0, 0.25) for _ in range(500)))

    def test_speech_then_silence_and_cooldown(self):
        detector = PauseDetector()
        for _ in range(4):
            self.assertFalse(detector.observe(0.1, 0.25))
        offers = [detector.observe(0, 0.25) for _ in range(12)]
        self.assertEqual(sum(offers), 1)
        for _ in range(4):
            detector.observe(0.1, 0.25)
        self.assertFalse(any(detector.observe(0, 0.25) for _ in range(12)))

    def test_short_noise_does_not_trigger(self):
        detector = PauseDetector()
        detector.observe(0.1, 0.25)
        self.assertFalse(any(detector.observe(0, 0.25) for _ in range(12)))
        self.assertFalse(detector.observe(float("nan"), 0.25))


class LiveTypedMockTests(unittest.TestCase):
    def test_live_typed_entrypoint_uses_navigator_and_keeps_input_private(self):
        import contextlib
        from cowingman.__main__ import main
        from cowingman.provider import NavigatorClient
        from unittest.mock import MagicMock
        import json

        def transport(url, headers, payload, timeout):
            self.assertEqual(headers["Authorization"], "Bearer synthetic-key")
            self.assertIn("private typed fragment", payload["messages"][1]["content"])
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "cue": "Could you clarify that?",
                                    "intent": "clarify",
                                    "should_offer": True,
                                }
                            )
                        }
                    }
                ]
            }

        client = NavigatorClient("synthetic-key", transport=transport)
        ui = FakeUI(["private typed fragment", ":cue", ":quit"])
        manager = MagicMock()
        manager.__enter__.return_value = ui
        output = io.StringIO()
        with (
            patch.dict("os.environ", {"NAVIGATOR_TOOLKIT_API_KEY": "synthetic-key"}, clear=True),
            patch("cowingman.__main__.NavigatorClient", return_value=client),
            patch("cowingman.__main__.TerminalUI", return_value=manager),
            contextlib.redirect_stdout(output),
        ):
            self.assertEqual(main(["--typed"]), 0)
        self.assertEqual(len(ui.cues), 1)
        self.assertNotIn("private typed fragment", repr(ui.messages) + output.getvalue())
        self.assertEqual(client._api_key, "")
