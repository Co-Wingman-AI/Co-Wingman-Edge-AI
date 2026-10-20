import copy
import json
import unittest
from unittest.mock import patch
import urllib.error

from cowingman.config import Config, DEFAULT_BASE_URL, DEFAULT_MODEL, validate_cloud_configuration
from cowingman.context import BoundedContext, ContextTurn, RollingContext
from cowingman.cue import parse_cue
from cowingman.errors import ConfigurationError, CloudRequestError, PrivacyBoundaryError
from cowingman.provider import NavigatorClient, NoRedirect, urllib_transport


def response(cue="Could you repeat that?", **extra):
    return {"choices": [{"message": {"content": json.dumps(dict(
        cue=cue, intent="clarify", should_offer=True, **extra
    ))}, "finish_reason": "stop"}]}


class ConfigurationTests(unittest.TestCase):
    def test_defaults_and_key_selection(self):
        config = Config.load(environ={"NAVIGATOR_TOOLKIT_API_KEY": "correct", "NEBIUS_API_KEY": "wrong"})
        self.assertEqual(config.api_key, "correct")
        self.assertNotIn("correct", repr(config))
        self.assertEqual(config.model, DEFAULT_MODEL)
        with self.assertRaises(ConfigurationError):
            Config.load(environ={"NEBIUS_API_KEY": "wrong"})
        self.assertEqual(Config.load(offline=True, environ={}).api_key, "")

    def test_host_and_path_allowlist(self):
        for url in ["http://api.ai.it.ufl.edu/v1", "https://api.ai.it.ufl.edu.evil.test/v1",
                    "https://evilapi.ai.it.ufl.edu/v1", "https://api.ai.it.ufl.edu@evil.test/v1",
                    "https://user@api.ai.it.ufl.edu/v1", "https://api.ai.it.ufl.edu:444/v1",
                    "https://api.ai.it.ufl.edu/v1?", "https://api.ai.it.ufl.edu/v1#",
                    "https://api.ai.it.ufl.edu/v1/../other", "https://api.ai.it.ufl.edu./v1",
                    "https://api.ai.it.ufl.edu/v1\n", "https://[invalid/v1", "https://example.com/v1"]:
            with self.subTest(url=url), self.assertRaises(ConfigurationError):
                validate_cloud_configuration(url, DEFAULT_MODEL)
        self.assertEqual(validate_cloud_configuration(DEFAULT_BASE_URL + "/", DEFAULT_MODEL)[0], DEFAULT_BASE_URL)

    def test_model_and_numeric_validation(self):
        for model in ["nvidia/nemotron-unknown", "gpt-4", "nemotron-3-nano-30b-a3b ", ""]:
            with self.assertRaises(ConfigurationError):
                validate_cloud_configuration(DEFAULT_BASE_URL, model)
        for name, value in [("COWINGMAN_TIMEOUT", "nan"), ("COWINGMAN_TIMEOUT", "31"),
                            ("COWINGMAN_CONTEXT_TTL", "inf"), ("COWINGMAN_AUDIO_DEVICE", "-1")]:
            with self.assertRaises(ConfigurationError):
                Config.load(offline=True, environ={name: value})


class BoundaryTests(unittest.TestCase):
    def test_constructor_cannot_bypass_network_boundary(self):
        called = []
        client = NavigatorClient("key", transport=lambda *a: called.append(a))
        for turns in [(ContextTurn("user", b"audio"),), (ContextTurn("user", "x" * 241),),
                      tuple(ContextTurn("user", "a") for _ in range(5)),
                      tuple(ContextTurn("user", "x" * 240) for _ in range(4))]:
            with self.assertRaises(PrivacyBoundaryError):
                client.request_cue(BoundedContext(turns))
        for audio in [b"raw", {"input_audio": "base64"}, [1, 2, 3]]:
            with self.assertRaises(PrivacyBoundaryError):
                client.request_cue(audio)
        self.assertFalse(called)

    def test_rolling_selection_expiration_and_deletion(self):
        now = [0.0]
        context = RollingContext(clock=lambda: now[0])
        for _ in range(10):
            context.add("x" * 1000)
        window = context.take()
        self.assertLessEqual(window.character_count, 800)
        self.assertLessEqual(len(window.turns), 4)
        self.assertEqual(len(context), 0)
        context.add("private sentinel")
        self.assertNotIn("private sentinel", repr(context))
        now[0] = 60.0
        context.expire()
        self.assertEqual(context._items, [])
        with self.assertRaises(PrivacyBoundaryError):
            context.take()

    def test_strict_schema_and_unsafe_results(self):
        for content in ['{}', '[]', 'null', '{"cue":"a","cue":"b","intent":"resume","should_offer":true}',
                        json.dumps({"cue":"a", "intent":[], "should_offer":True}),
                        json.dumps({"cue":"a", "intent":"resume", "should_offer":1})]:
            with self.assertRaises(ValueError):
                parse_cue(content)
        for cue in ["word " * 13, "a" * 161, "\x1b[31mhi", "hello\nworld", "You have anxiety.",
                    "Give me your password", "Visit https://evil.test", "Kill them"]:
            with self.assertRaises(ValueError):
                parse_cue(json.dumps({"cue":cue, "intent":"respond", "should_offer":True}))


class ProviderTests(unittest.TestCase):
    def test_request_shape_auth_and_content_free_metrics(self):
        captured = {}
        def transport(url, headers, payload, timeout):
            captured.update(url=url, headers=copy.deepcopy(headers), payload=copy.deepcopy(payload), timeout=timeout)
            return response()
        client = NavigatorClient("test-secret", transport=transport)
        cue, metrics = client.request_cue(BoundedContext.from_turns([ContextTurn("user", "private sentinel")]))
        self.assertEqual(captured["url"], DEFAULT_BASE_URL + "/chat/completions")
        self.assertEqual(captured["headers"]["Authorization"], "Bearer test-secret")
        self.assertEqual(captured["payload"]["model"], DEFAULT_MODEL)
        self.assertEqual(captured["payload"]["response_format"], {"type":"json_object"})
        self.assertTrue(all(type(m["content"]) is str for m in captured["payload"]["messages"]))
        self.assertEqual(captured["timeout"], 15)
        for private in ["test-secret", "private sentinel", cue.cue]:
            self.assertNotIn(private, json.dumps(metrics))
        client.close()
        self.assertEqual(client._api_key, "")

    def test_failures_are_content_free(self):
        for error in [TimeoutError("private secret"), OSError("private secret"), ValueError("private secret")]:
            def fail(*args):
                raise error
            with self.assertRaises(CloudRequestError) as caught:
                NavigatorClient("key", transport=fail).request_cue(BoundedContext.from_turns([ContextTurn("user", "hello")]))
            self.assertNotIn("private", str(caught.exception))
        for result in [{}, {"choices": []}, response("unsafe", other=True)]:
            with self.assertRaises(CloudRequestError):
                NavigatorClient("key", transport=lambda *a: result).request_cue(BoundedContext.from_turns([ContextTurn("user", "hello")]))

    def test_redirects_rejected(self):
        with self.assertRaises(CloudRequestError):
            NoRedirect().redirect_request(None, None, 302, "", {}, "https://evil.test")

    def test_http_errors_and_transport_limits(self):
        for code, expected in [(401, "access denied"), (403, "access denied"), (429, "rate limit"), (500, "service error")]:
            with patch("urllib.request.OpenerDirector.open", side_effect=urllib.error.HTTPError("url", code, "secret", {}, None)):
                with self.assertRaisesRegex(CloudRequestError, expected):
                    urllib_transport(DEFAULT_BASE_URL, {}, {}, 1)
        with patch("urllib.request.OpenerDirector.open") as opened:
            opened.return_value.__enter__.return_value.read.return_value = b"x" * 16385
            with self.assertRaisesRegex(CloudRequestError, "oversized"):
                urllib_transport(DEFAULT_BASE_URL, {}, {}, 1)
