from contextlib import nullcontext, redirect_stderr
import io
import json
from pathlib import Path
import tempfile
import unittest
from unittest.mock import Mock, MagicMock, patch

from cowingman.__main__ import main
from cowingman.app import Application
from cowingman.config import Config
from cowingman.context import BoundedContext, ContextTurn
from cowingman.disfluency import ShadowDetector, verify_shadow_model
from cowingman.errors import CloudRequestError, ConfigurationError, SpeechError
from cowingman.portfolio import Portfolio, MAX_FILE_BYTES
from cowingman.portfolio_cloud import S3PortfolioStore
from cowingman.provider import NavigatorClient, urllib_transport
from cowingman.timing import Timing, NO_TIMING
from scripts.timing_report import summarize
from scripts.token_benchmark import run
from scripts.setup_s3_bucket import create
from test_application import FakeUI


def response():
    return {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "content": json.dumps(
                        {
                            "cue": "Here is a useful next step.",
                            "intent": "resume",
                            "should_offer": True,
                        }
                    )
                },
            }
        ]
    }


class TimingTests(unittest.TestCase):
    def test_private_numeric_trace_failure_and_summary(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "timing.jsonl"
            trace = Timing.create(path)
            with self.assertRaises(RuntimeError):
                with trace.measure("asr_inference", window_start=1):
                    raise RuntimeError("private transcript sentinel")
            trace.event("audio_drop", count=2)
            trace.event("disfluency_score", score=0.6, window_start=1)
            raw = path.read_text()
            self.assertNotIn("sentinel", raw)
            self.assertEqual(path.stat().st_mode & 0o777, 0o600)
            report = summarize(path)
            self.assertEqual(report["stages"]["asr_inference"]["failures"], 1)
            self.assertEqual(report["dropped_windows"], 2)
            self.assertEqual(report["shadow"]["at_or_above_0_5"], 1)
            self.assertFalse(report["shadow"]["automatic_cue_trigger"])
            with self.assertRaises(ConfigurationError):
                Timing.create(path)
            for kwargs in ({"transcript": "secret"}, {"score": float("nan")}, {"score": "secret"}):
                with self.assertRaises(ValueError):
                    trace.event("disfluency_score", **kwargs)

    def test_disabled_measurement_does_not_touch_clock_or_disk(self):
        with patch("cowingman.timing.time.monotonic", side_effect=AssertionError):
            with NO_TIMING.measure("asr_load"):
                pass
            NO_TIMING.event("asr_load")

    def test_provider_and_application_timings_never_include_content(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "run.jsonl"
            trace = Timing.create(path)
            client = NavigatorClient(
                "private-key-sentinel", transport=lambda *a: response(), timing=trace
            )
            app = Application(Config(), client, FakeUI(), timing=trace, tts=True, speaker=Mock())
            app.add("private conversation sentinel")
            app.request_cue()
            stages = {row["stage"] for row in map(json.loads, path.read_text().splitlines())}
            self.assertTrue({"transport", "validation", "cue_total", "tts"} <= stages)
            self.assertNotIn("sentinel", path.read_text())
            self.assertNotIn("Here is", path.read_text())
            app.close()

    def test_network_handler_measures_connect_and_response_separately(self):
        trace = Mock()
        trace.measure.side_effect = lambda *a, **kw: nullcontext()
        captured = []

        def build(*handlers):
            captured.extend(handlers)
            opener = MagicMock()
            opener.open.return_value.__enter__.return_value.read.return_value = b"{}"
            return opener

        with patch("cowingman.provider.urllib.request.build_opener", side_effect=build):
            urllib_transport("https://api.ai.it.ufl.edu/v1/chat/completions", {}, {}, 1, trace)
        handler = captured[-1]

        def open_connection(cls, request, **kw):
            connection = cls("api.ai.it.ufl.edu")
            with (
                patch("http.client.HTTPSConnection.connect"),
                patch("http.client.HTTPSConnection.getresponse"),
            ):
                connection.connect()
                connection.getresponse()

        handler.do_open = open_connection
        handler.https_open(Mock())
        stages = [call.args[0] for call in trace.measure.call_args_list]
        self.assertIn("network_setup", stages)
        self.assertIn("server_response", stages)
        self.assertIn("response_read", stages)


class PortfolioCloudTests(unittest.TestCase):
    def test_bucket_setup_has_region_specific_creation_and_private_controls(self):
        for region in ("us-east-1", "us-west-2"):
            client = Mock()
            missing = RuntimeError()
            missing.response = {"ResponseMetadata": {"HTTPStatusCode": 404}}
            client.head_bucket.side_effect = missing
            create(client, "example-bucket", region)
            args = client.create_bucket.call_args.kwargs
            self.assertEqual(args["ObjectOwnership"], "BucketOwnerEnforced")
            if region == "us-east-1":
                self.assertNotIn("CreateBucketConfiguration", args)
            else:
                self.assertEqual(args["CreateBucketConfiguration"], {"LocationConstraint": region})
            self.assertTrue(
                all(
                    client.put_public_access_block.call_args.kwargs[
                        "PublicAccessBlockConfiguration"
                    ].values()
                )
            )
            self.assertIn("AES256", json.dumps(client.put_bucket_encryption.call_args.kwargs))

    def test_bucket_creation_failure_never_changes_an_existing_bucket(self):
        client = Mock()
        with self.assertRaises(ConfigurationError):
            create(client, "example-bucket", "us-west-2")
        client.create_bucket.assert_not_called()
        client.put_public_access_block.assert_not_called()

    def test_upload_and_reload_keeps_retrieval_bounds(self):
        s3 = Mock()
        store = S3PortfolioStore("s3://example-bucket/device", "us-east-1", client=s3)
        portfolio = Portfolio(("Demo project: I built a synthetic test using Python.",))
        archived = store.upload(portfolio)
        self.assertTrue(archived.startswith("portfolios/"))
        self.assertEqual(s3.put_object.call_count, 2)
        written = s3.put_object.call_args.kwargs
        self.assertEqual(written["Key"], "device/portfolio.json")
        self.assertEqual(written["ServerSideEncryption"], "AES256")
        self.assertNotIn("ACL", written)
        self.assertIn("created_at", json.loads(written["Body"]))
        body = io.BytesIO(written["Body"])
        s3.get_object.return_value = {"Body": body}
        loaded = store.load()
        self.assertEqual(loaded, portfolio)
        self.assertTrue(body.closed)
        context = BoundedContext.from_turns([ContextTurn("partner", "Explain the demo project")])
        self.assertEqual(loaded.select(context), portfolio.select(context))
        self.assertLessEqual(sum(map(len, loaded.select(context))), 1200)

    def test_load_rejects_invalid_or_unbounded_data_and_closes_body(self):
        s3 = Mock()
        store = S3PortfolioStore("s3://example-bucket/device", "us-east-1", client=s3)
        for content in (
            b"x" * (MAX_FILE_BYTES + 1),
            b"private sentinel",
            b'{"version":1,"passages":[]}',
        ):
            body = io.BytesIO(content)
            s3.get_object.return_value = {"Body": body}
            with self.assertRaises(ConfigurationError) as caught:
                store.load()
            self.assertNotIn("sentinel", str(caught.exception))
            self.assertTrue(body.closed)
        with self.assertRaises(ConfigurationError):
            store.load("../another/portfolio.json")

    def test_invalid_portfolio_never_uploads_and_aws_errors_are_sanitized(self):
        s3 = Mock()
        store = S3PortfolioStore("s3://example-bucket/device", "us-east-1", client=s3)
        with self.assertRaises(ConfigurationError):
            store.upload(Portfolio(("x" * 601,)))
        s3.put_object.assert_not_called()
        s3.put_object.side_effect = RuntimeError("private sentinel credentials")
        with self.assertRaises(CloudRequestError) as caught:
            store.upload(Portfolio(("synthetic fact",)))
        self.assertNotIn("sentinel", str(caught.exception))

    def test_cli_refuses_conflicting_portfolio_and_unconfigured_shadow(self):
        for argv in (
            ["--portfolio", "file", "--portfolio-s3", "s3://example-bucket/device"],
            ["--portfolio-s3", "s3://example-bucket/device"],
            ["--disfluency-shadow", "file"],
            ["--rolling", "--typed", "--timings", "file", "--disfluency-shadow", "model"],
        ):
            with redirect_stderr(io.StringIO()), self.assertRaises(SystemExit) as caught:
                main(argv)
            self.assertEqual(caught.exception.code, 2)


class ShadowTests(unittest.TestCase):
    def test_failed_shadow_load_does_not_stop_asr(self):
        from cowingman.speech import _speech_worker

        connection = Mock()
        capture = Mock(dropped=0)
        samples = Mock()
        capture.read.side_effect = [(0, samples, True, False), SpeechError("test end")]
        model = Mock()
        model.transcribe.return_value = "synthetic fragment"
        with (
            patch("cowingman.speech.prepare_worker"),
            patch("cowingman.speech.available_memory", return_value=3 * 1024**3),
            patch.dict("sys.modules", numpy=Mock()),
            patch("cowingman.asr.NemoASR", return_value=model),
            patch("cowingman.audio.ContinuousMicrophone") as microphone,
            patch(
                "cowingman.disfluency.ShadowDetector", side_effect=RuntimeError("private sentinel")
            ),
        ):
            microphone.return_value.open.return_value = capture
            _speech_worker(connection, "model", None, 0.015, True, disfluency_path="shadow")
        sent = [call.args[0] for call in connection.send.call_args_list]
        self.assertIn(("fragment", (0, "synthetic fragment")), sent)
        self.assertTrue(any(kind == "notice" for kind, _ in sent))
        self.assertNotIn("sentinel", repr(sent))
        capture.close.assert_called_once()

    def test_review_markers_are_fixed_local_metadata_only(self):
        with tempfile.TemporaryDirectory() as root:
            path = Path(root) / "markers.jsonl"
            trace = Timing.create(path)
            client = Mock()
            app = Application(Config(), client, FakeUI(), timing=trace)
            for label in ("quiet", "fluent", "stuck", "partner"):
                app.command(":mark " + label)
            app.command(":mark private sentinel")
            report = summarize(path, windows=True)
            self.assertEqual(len(report["review_timeline"]), 4)
            self.assertNotIn("sentinel", path.read_text())
            client.request_cue.assert_not_called()
            app.close()

    def test_model_must_match_pinned_digest(self):
        with tempfile.TemporaryDirectory() as root:
            file = Path(root) / "model.keras"
            file.write_bytes(b"untrusted model sentinel")
            with self.assertRaises(SpeechError) as caught:
                verify_shadow_model(file)
            self.assertNotIn("sentinel", str(caught.exception))

    def test_shadow_windows_reset_across_gaps_and_never_mutate_asr_input(self):
        detector = ShadowDetector.__new__(ShadowDetector)
        detector.tail = detector.last_start = None
        detector.timing = Mock()
        detector.timing.measure.side_effect = lambda *a, **kw: nullcontext()
        detector.keras = Mock()
        detector.keras.device.return_value = nullcontext()
        detector.model = Mock()
        output = detector.model.return_value.detach.return_value.cpu.return_value.numpy.return_value
        output.__getitem__ = Mock(return_value=0.8)
        samples = Mock(shape=(64000,))
        samples.__getitem__ = Mock(return_value=Mock())
        np = Mock()
        np.isfinite.return_value.all.return_value = True
        torch = Mock()
        torch.inference_mode.return_value = nullcontext()
        data = Mock()
        with (
            patch.dict("sys.modules", numpy=np, torch=torch),
            patch("cowingman.disfluency.features", return_value=data),
        ):
            detector.observe(samples, 0, True)
            detector.model.assert_not_called()
            self.assertEqual(detector.observe(samples, 4, True), 0.8)
            self.assertEqual(detector.model.call_count, 1)
            detector.timing.event.assert_called_once_with(
                "disfluency_score", window_start=3, score=0.8
            )
            detector.observe(samples, 16, True)
            detector.observe(samples, 20, False)
            self.assertEqual(detector.model.call_count, 1)
        samples.fill.assert_not_called()
        data.fill.assert_called_with(0)
        tail = detector.tail
        detector.close()
        tail.fill.assert_called_with(0)
        self.assertIsNone(detector.model)

    def test_shadow_event_cannot_request_cue(self):
        client = Mock()
        audio = Mock(process=object())
        audio.poll.return_value = [("fragment", "synthetic input"), ("disfluency_score", 0.99)]
        app = Application(Config(), client, FakeUI(), audio=audio, rolling=True, pause_assist=True)
        app.tick()
        client.request_cue.assert_not_called()
        app.close()


class TokenBenchmarkTests(unittest.TestCase):
    def test_balanced_interleaved_synthetic_budgets_with_no_content_report(self):
        budgets = []

        def transport(url, headers, payload, timeout):
            budgets.append(payload["max_tokens"])
            if payload["max_tokens"] == 96:
                return {
                    "choices": [
                        {"finish_reason": "length", "message": {"content": "private sentinel"}}
                    ]
                }
            return response()

        report = run(Config(api_key="synthetic-key"), 1, transport=transport)
        self.assertEqual(len(report["trials"]), 12)
        for budget in (96, 128, 192, 256):
            self.assertEqual(budgets.count(budget), 3)
        self.assertNotEqual(budgets, sorted(budgets))
        self.assertEqual(sum(row["truncated"] for row in report["trials"]), 3)
        self.assertNotIn("sentinel", json.dumps(report))
        self.assertNotIn("useful next step", json.dumps(report))
        self.assertTrue(report["quality_review_required"])
