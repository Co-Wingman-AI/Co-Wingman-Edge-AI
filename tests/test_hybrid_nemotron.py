import json
import unittest
from argparse import Namespace
from pathlib import Path
from tempfile import TemporaryDirectory

from cowingman.hybrid_nemotron import (
    BoundedContext,
    ConfigurationError,
    ContextTurn,
    NebiusNemotronClient,
    PrivacyBoundaryError,
    parse_cue,
    validate_cloud_configuration,
)
from scripts import hybrid_nemotron_benchmark as benchmark


class HybridNemotronUnitTests(unittest.TestCase):
    def test_only_nvidia_nemotron_model_is_allowed(self):
        validate_cloud_configuration(
            "https://api.tokenfactory.nebius.com/v1", "nvidia/a-nemotron-model"
        )
        with self.assertRaises(ConfigurationError):
            validate_cloud_configuration(
                "https://api.tokenfactory.nebius.com/v1", "other/vendor-model"
            )

    def test_only_https_nebius_endpoint_is_allowed(self):
        for url in ("http://api.tokenfactory.nebius.com/v1", "https://example.com/v1"):
            with self.assertRaises(ConfigurationError):
                validate_cloud_configuration(url, "nvidia/nemotron")

    def test_context_rejects_audio_and_oversized_turns(self):
        with self.assertRaises(PrivacyBoundaryError):
            BoundedContext.from_turns([ContextTurn("user", b"audio bytes")])  # type: ignore[arg-type]
        with self.assertRaises(PrivacyBoundaryError):
            BoundedContext.from_turns([ContextTurn("user", "x" * 241)])

    def test_cue_schema_is_strict(self):
        cue = parse_cue('{"cue":"Mention the privacy boundary.","intent":"clarify","should_offer":true}')
        self.assertEqual(cue.intent, "clarify")
        with self.assertRaises(ValueError):
            parse_cue('{"cue":"hello","intent":"other","should_offer":true}')


class HybridNemotronMockedIntegrationTests(unittest.TestCase):
    def test_client_builds_bounded_openai_compatible_request(self):
        captured = {}

        def transport(url, headers, payload, timeout):
            captured.update(url=url, headers=headers, payload=payload, timeout=timeout)
            return {
                "choices": [{"message": {"content": json.dumps({
                    "cue": "Explain the local privacy boundary.",
                    "intent": "respond",
                    "should_offer": True,
                })}}],
                "usage": {"prompt_tokens": 44, "completion_tokens": 12, "total_tokens": 56},
            }

        client = NebiusNemotronClient("secret-test-key", transport=transport)
        context = BoundedContext.from_turns([
            ContextTurn("partner", "Why is processing local?"),
            ContextTurn("user", "Because private audio should stay here."),
        ])
        cue, metrics = client.request_cue(context)
        self.assertEqual(cue.intent, "respond")
        self.assertTrue(captured["url"].endswith("/v1/chat/completions"))
        self.assertEqual(captured["payload"]["model"], "nvidia/nvidia-nemotron-3-nano-30b-a3b")
        self.assertNotIn("audio", captured["payload"])
        self.assertEqual(metrics["usage"]["total_tokens"], 56)
        self.assertNotIn("secret-test-key", json.dumps(metrics))

    def test_dry_run_reports_are_machine_readable_and_content_free(self):
        args = Namespace(
            dry_run=True,
            live=False,
            trials=3,
            timeout=20.0,
            max_latency=5.0,
            base_url="https://api.tokenfactory.nebius.com/v1",
            model="nvidia/nemotron-test",
        )
        report = benchmark.run_benchmark(args)
        with TemporaryDirectory() as directory:
            json_path, md_path = benchmark.write_reports(report, Path(directory))
            parsed = json.loads(json_path.read_text(encoding="utf-8"))
            markdown = md_path.read_text(encoding="utf-8")
        self.assertEqual(parsed["assessment"]["status"], "not_run")
        serialized = json.dumps(parsed) + markdown
        for private_content in ("I lost the phrase", "private signal", "secret-test-key"):
            self.assertNotIn(private_content, serialized)


if __name__ == "__main__":
    unittest.main()
