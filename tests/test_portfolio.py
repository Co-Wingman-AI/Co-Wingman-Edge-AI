import contextlib
import copy
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import MagicMock, Mock, patch

from cowingman.__main__ import main
from cowingman.app import Application
from cowingman.config import Config
from cowingman.context import BoundedContext, ContextTurn
from cowingman.errors import CloudRequestError, ConfigurationError, PrivacyBoundaryError
from cowingman.portfolio import (
    MAX_FILE_BYTES,
    Portfolio,
    PortfolioHTML,
    import_honey,
)
from cowingman.provider import NavigatorClient
from test_application import FakeUI


PASSAGES = (
    "Featured Projects / ParcelFlow: Six Java microservices coordinate orders through Kafka.",
    "Featured Projects / ParcelFlow: Idempotent consumers and retries handle failures.",
    "Featured Projects / GestureTutor: An ASL platform with computer vision and gamified learning.",
    "Work Experience / Robotics Intern / Example Institute: Developed Python vision pipelines.",
    "Education / Master of Science / Example University: Artificial Intelligence Systems.",
    "About Me: I build software and study artificial intelligence.",
)


def context(question):
    return BoundedContext.from_turns([ContextTurn("partner", question)])


def write_profile(path, passages=PASSAGES):
    path.write_text(json.dumps({"version": 1, "passages": [{"text": p} for p in passages]}))


class PortfolioTests(unittest.TestCase):
    def test_retrieval_topics_paraphrases_and_no_match(self):
        profile = Portfolio(PASSAGES)
        for question, expected in [
            ("How does ParcelFlow work?", "ParcelFlow"),
            ("Tell me about GestureTutor", "GestureTutor"),
            ("What did you do in your internship?", "Robotics Intern"),
            ("Where do you study?", "Example University"),
            ("Tell me about yourself", "About Me"),
        ]:
            with self.subTest(question=question):
                selected = profile.select(context(question))
                self.assertTrue(selected)
                self.assertIn(expected, selected[0])
                self.assertLessEqual(len(selected), 2)
                self.assertLessEqual(sum(map(len, selected)), 1200)
        self.assertEqual(profile.select(context("How was your weekend?")), ())
        self.assertEqual(profile.select(context("and so")), ())
        self.assertNotIn("ParcelFlow", repr(profile))

    def test_load_rejects_malformed_oversized_and_controls_without_content(self):
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            write_profile(path)
            self.assertEqual(Portfolio.load(path).passages, PASSAGES)
            for passages in [[], ["x" * 601], ["private\x1bfragment"], [b"audio"], ["x"] * 257]:
                with self.subTest(passages_type=type(passages[0]) if passages else None):
                    # Bytes are represented by an invalid JSON value rather than serialized audio.
                    value = [123] if passages == [b"audio"] else passages
                    write_profile(path, value)
                    with self.assertRaises(ConfigurationError) as caught:
                        Portfolio.load(path)
                    self.assertNotIn("private", str(caught.exception))
            path.write_bytes(b"x" * (MAX_FILE_BYTES + 1))
            with self.assertRaises(ConfigurationError):
                Portfolio.load(path)

    def test_html_preserves_role_context_and_excludes_noncontent(self):
        parser = PortfolioHTML()
        parser.feed("""<nav><p>Navigation sentinel</p></nav><main>
          <div class="section-heading"><span>Work Experience</span></div>
          <h3>Robotics Intern</h3><div class="exp-org">Example Institute</div>
          <span class="exp-date">2024</span>
          <ul><li>Built <strong>Python</strong> vision pipelines.</li></ul>
          <script>script sentinel</script><p>contact@example.test</p>
          <div class="section-heading"><span>Projects</span></div>
          <h3>FerryPlanner</h3><p>Reduced unused space by 30% in simulated scenarios.</p>
          </main><footer><p>Footer sentinel</p></footer>""")
        self.assertEqual(len(parser.records), 2)
        self.assertIn("Robotics Intern / Example Institute / 2024", parser.records[0])
        self.assertIn("Python", parser.records[0])
        self.assertIn("in simulated scenarios", parser.records[1])
        self.assertNotIn("Example Institute", parser.records[1])
        self.assertFalse(parser.stack)

    def test_import_downloads_only_fixed_html_and_does_not_overwrite(self):
        opener = Mock()
        response = MagicMock()
        response.__enter__.return_value.read.return_value = (
            b"<main><h3>ParcelFlow</h3><p>Uses Kafka.</p></main>"
        )
        opener.open.return_value = response
        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "private" / "profile.json"
            with patch("cowingman.portfolio.urllib.request.build_opener", return_value=opener):
                self.assertEqual(import_honey(path), 4)
                original = path.read_bytes()
                with self.assertRaises(FileExistsError):
                    import_honey(path)
            self.assertEqual(path.read_bytes(), original)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            self.assertTrue(Portfolio.load(path).passages)
        for call in opener.open.call_args_list:
            self.assertTrue(
                call.args[0].startswith(
                    "https://raw.githubusercontent.com/honeyreddydaram/Portfolio/"
                )
            )
            self.assertTrue(call.args[0].endswith(".html"))

    def test_provider_only_sends_selected_facts_and_bounds_injected_selection(self):
        requests = []

        def transport(url, headers, payload, timeout):
            requests.append(copy.deepcopy(payload))
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "cue": "I used Kafka to coordinate order processing.",
                                    "intent": "respond",
                                    "should_offer": True,
                                }
                            )
                        }
                    }
                ]
            }

        client = NavigatorClient("synthetic", portfolio=Portfolio(PASSAGES), transport=transport)
        _, metrics = client.request_cue(context("Tell me about ParcelFlow"))
        body = json.loads(requests[0]["messages"][1]["content"])
        self.assertEqual(body["portfolio_facts"], list(PASSAGES[:2]))
        self.assertEqual(len(body["recent_fragments"]), 1)
        self.assertNotIn("GestureTutor", json.dumps(requests))
        self.assertNotIn("ParcelFlow", json.dumps(metrics))
        self.assertEqual(metrics["portfolio_characters"], sum(map(len, PASSAGES[:2])))
        with self.assertRaisesRegex(CloudRequestError, "No NaviGator request made"):
            client.request_cue(context("How was your weekend?"))
        for result in [["x"] * 3, ["x" * 601], [b"audio"], ["bad\ntext"]]:
            client.portfolio = Mock(select=Mock(return_value=result))
            with self.assertRaises(PrivacyBoundaryError):
                client.request_cue(context("ParcelFlow"))
        self.assertEqual(len(requests), 1)
        client.close()
        self.assertIsNone(client.portfolio)

    def test_missing_match_never_calls_api_or_displays_invented_cue(self):
        transport = Mock()
        client = NavigatorClient("synthetic", portfolio=Portfolio(PASSAGES), transport=transport)
        ui = FakeUI()
        app = Application(Config.load(offline=True, environ={}), client, ui)
        app.add("I built it using", "unknown")
        app.request_cue()
        transport.assert_not_called()
        self.assertFalse(ui.cues)
        self.assertEqual(len(app.context), 0)
        self.assertIn("0 matching passages", " ".join(ui.messages))
        self.assertNotIn("I built it using", " ".join(ui.messages))
        app.close()

    def test_local_check_counts_without_consuming_refreshing_or_sending(self):
        now = [0.0]
        transport = Mock()
        client = NavigatorClient("synthetic", portfolio=Portfolio(PASSAGES), transport=transport)
        ui = FakeUI()
        app = Application(Config.load(offline=True, environ={}), client, ui, clock=lambda: now[0])
        app.command(":partner Tell me about ParcelFlow")
        app.context.add("I built it using", "unknown")
        now[0] = 59.0
        app.command(":check")
        self.assertIn(
            "Context: 1 typed partner, 0 typed user, 1 microphone fragments.", ui.messages
        )
        self.assertIn("Portfolio: 2 matching passages.", ui.messages)
        self.assertNotIn("ParcelFlow", " ".join(ui.messages))
        self.assertEqual(len(app.context), 2)
        now[0] = 60.0
        app.command(":check")
        self.assertEqual(len(app.context), 0)
        self.assertIn("No recent context. Add a short fragment before :check.", ui.messages)
        transport.assert_not_called()
        app.close()

    def test_live_typed_entrypoint_loads_profile_and_hides_facts(self):
        original = NavigatorClient
        captured = []

        def client_factory(*args, **kwargs):
            def transport(url, headers, payload, timeout):
                captured.append(json.loads(payload["messages"][1]["content"]))
                return {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {
                                        "cue": "I built order services using Kafka.",
                                        "intent": "respond",
                                        "should_offer": True,
                                    }
                                )
                            }
                        }
                    ]
                }

            return original(*args, transport=transport, **kwargs)

        with tempfile.TemporaryDirectory() as directory:
            path = Path(directory) / "profile.json"
            write_profile(path)
            ui = FakeUI([":partner Tell me about ParcelFlow", "I built it using", ":cue", ":quit"])
            manager = MagicMock()
            manager.__enter__.return_value = ui
            with (
                patch.dict("os.environ", {"NAVIGATOR_TOOLKIT_API_KEY": "synthetic"}, clear=True),
                patch("cowingman.__main__.NavigatorClient", side_effect=client_factory),
                patch("cowingman.__main__.TerminalUI", return_value=manager),
            ):
                self.assertEqual(main(["--typed", "--portfolio", str(path)]), 0)
            self.assertEqual(len(ui.cues), 1)
            self.assertIn("portfolio_facts", captured[0])
            self.assertIn("Portfolio: 2 reference passages supplied.", ui.messages)
            self.assertNotIn("ParcelFlow", repr(ui.messages))

    def test_echo_is_withheld_and_context_cleared_without_retry(self):
        for speaker in ("user", "unknown"):
            for echo in ("i built parcelflow using", "I BUILT PARCELFLOW USING..."):
                with self.subTest(speaker=speaker, echo=echo):
                    transport = Mock(
                        return_value={
                            "choices": [
                                {
                                    "message": {
                                        "content": json.dumps(
                                            {"cue": echo, "intent": "resume", "should_offer": True}
                                        )
                                    }
                                }
                            ]
                        }
                    )
                    client = NavigatorClient(
                        "synthetic", portfolio=Portfolio(PASSAGES), transport=transport
                    )
                    ui = FakeUI()
                    app = Application(Config.load(offline=True, environ={}), client, ui)
                    app.add("Tell me about ParcelFlow. What did you build?", "partner")
                    app.add("I built ParcelFlow using", speaker)
                    app.request_cue()
                    self.assertFalse(ui.cues)
                    self.assertEqual(len(app.context), 0)
                    self.assertEqual(transport.call_count, 1)
                    self.assertIn("cue withheld", " ".join(ui.messages))
                    self.assertIn("2 portfolio passages were supplied", " ".join(ui.messages))
                    self.assertNotIn("ParcelFlow", " ".join(ui.messages))
                    app.close()

    def test_completion_may_reuse_input_when_it_adds_information(self):
        window = BoundedContext.from_turns(
            [
                ContextTurn("partner", "Tell me about ParcelFlow"),
                ContextTurn("user", "I built ParcelFlow using"),
            ]
        )
        for phrase in ("Kafka to coordinate orders.", "I built ParcelFlow using Java and Kafka."):

            def transport(url, headers, payload, timeout):
                body = json.loads(payload["messages"][1]["content"])
                self.assertEqual(body["portfolio_facts"], list(PASSAGES[:2]))
                self.assertEqual(body["recent_fragments"][-1]["text"], "I built ParcelFlow using")
                return {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps(
                                    {"cue": phrase, "intent": "resume", "should_offer": True}
                                )
                            }
                        }
                    ]
                }

            client = NavigatorClient(
                "synthetic", portfolio=Portfolio(PASSAGES), transport=transport
            )
            cue, metrics = client.request_cue(window)
            self.assertEqual(cue.cue, phrase)
            self.assertEqual(metrics["portfolio_passages"], 2)
            client.close()

    def test_echo_check_applies_without_portfolio_too(self):
        transport = Mock(
            return_value={
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "cue": "I chose this because...",
                                    "intent": "resume",
                                    "should_offer": True,
                                }
                            )
                        }
                    }
                ]
            }
        )
        client = NavigatorClient("synthetic", transport=transport)
        with self.assertRaisesRegex(CloudRequestError, "repeated the input"):
            client.request_cue(
                BoundedContext.from_turns([ContextTurn("user", "I chose this because")])
            )
        self.assertEqual(transport.call_count, 1)
        client.close()

    def test_synthetic_modes_cannot_include_portfolio(self):
        for option in ["--health-check", "--offline", "--demo", "--list-audio"]:
            with contextlib.redirect_stderr(io.StringIO()), self.assertRaises(SystemExit):
                main(["--typed", option, "--portfolio", "private/profile.json"])
