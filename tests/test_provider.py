import copy
import json
import re
import unittest
from unittest.mock import patch
import urllib.error

from cowingman.config import Config, DEFAULT_BASE_URL, DEFAULT_MODEL, validate_cloud_configuration
from cowingman.context import BoundedContext, ContextTurn, RollingContext
from cowingman.cue import cue_response_format, parse_cue
from cowingman.errors import ConfigurationError, CloudRequestError, PrivacyBoundaryError
from cowingman.provider import NavigatorClient, NoRedirect, urllib_transport


def response(cue="Could you repeat that?", **extra):
    return {
        "choices": [
            {
                "message": {
                    "content": json.dumps(
                        dict(cue=cue, intent="clarify", should_offer=True, **extra)
                    )
                },
                "finish_reason": "stop",
            }
        ]
    }


class ConfigurationTests(unittest.TestCase):
    def test_defaults_and_key_selection(self):
        config = Config.load(
            environ={"NAVIGATOR_TOOLKIT_API_KEY": "correct", "NEBIUS_API_KEY": "wrong"}
        )
        self.assertEqual(config.api_key, "correct")
        self.assertNotIn("correct", repr(config))
        self.assertEqual(config.model, DEFAULT_MODEL)
        with self.assertRaises(ConfigurationError):
            Config.load(environ={"NEBIUS_API_KEY": "wrong"})
        self.assertEqual(Config.load(offline=True, environ={}).api_key, "")

    def test_host_and_path_allowlist(self):
        for url in [
            "http://api.ai.it.ufl.edu/v1",
            "https://api.ai.it.ufl.edu.evil.test/v1",
            "https://evilapi.ai.it.ufl.edu/v1",
            "https://api.ai.it.ufl.edu@evil.test/v1",
            "https://user@api.ai.it.ufl.edu/v1",
            "https://api.ai.it.ufl.edu:444/v1",
            "https://api.ai.it.ufl.edu/v1?",
            "https://api.ai.it.ufl.edu/v1#",
            "https://api.ai.it.ufl.edu/v1/../other",
            "https://api.ai.it.ufl.edu./v1",
            "https://api.ai.it.ufl.edu/v1\n",
            "https://[invalid/v1",
            "https://example.com/v1",
        ]:
            with self.subTest(url=url), self.assertRaises(ConfigurationError):
                validate_cloud_configuration(url, DEFAULT_MODEL)
        self.assertEqual(
            validate_cloud_configuration(DEFAULT_BASE_URL + "/", DEFAULT_MODEL)[0], DEFAULT_BASE_URL
        )

    def test_model_and_numeric_validation(self):
        for model in ["nvidia/nemotron-unknown", "gpt-4", "nemotron-3-nano-30b-a3b ", ""]:
            with self.assertRaises(ConfigurationError):
                validate_cloud_configuration(DEFAULT_BASE_URL, model)
        for name, value in [
            ("COWINGMAN_TIMEOUT", "nan"),
            ("COWINGMAN_TIMEOUT", "31"),
            ("COWINGMAN_CONTEXT_TTL", "inf"),
            ("COWINGMAN_AUDIO_DEVICE", "-1"),
        ]:
            with self.assertRaises(ConfigurationError):
                Config.load(offline=True, environ={name: value})


class BoundaryTests(unittest.TestCase):
    def test_constructor_cannot_bypass_network_boundary(self):
        called = []
        client = NavigatorClient("key", transport=lambda *a: called.append(a))
        for turns in [
            (ContextTurn("user", b"audio"),),
            (ContextTurn("user", "x" * 241),),
            tuple(ContextTurn("user", "a") for _ in range(5)),
            tuple(ContextTurn("user", "x" * 240) for _ in range(4)),
        ]:
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

    def test_unknown_audio_fragments_merge_within_privacy_bounds(self):
        now = [0.0]
        context = RollingContext(clock=lambda: now[0])
        context.add("partner asks about the project", "unknown", merge=True)
        now[0] = 30.0
        context.add("user begins explaining local privacy", "unknown", merge=True)
        window = context.take()
        self.assertEqual(len(window.turns), 1)
        self.assertEqual(window.turns[0].speaker, "unknown")
        self.assertIn("partner asks", window.turns[0].text)
        self.assertIn("local privacy", window.turns[0].text)
        self.assertLessEqual(window.character_count, 800)

        now[0] = 40.0
        context.add("a" * 200, "unknown", merge=True)
        context.add("b" * 100, "unknown", merge=True)
        window = context.take()
        self.assertEqual(len(window.turns), 2)
        self.assertTrue(all(len(turn.text) <= 240 for turn in window.turns))

        now[0] = 50.0
        context.add("older speech", "unknown", merge=True)
        now[0] = 109.0
        context.add("newer speech", "unknown", merge=True)
        now[0] = 110.0
        context.expire()
        self.assertEqual(len(context), 0)

    def test_strict_schema_and_unsafe_results(self):
        for content in [
            "{}",
            "[]",
            "null",
            '{"cue":"a","cue":"b","intent":"resume","should_offer":true}',
            json.dumps({"cue": "a", "intent": [], "should_offer": True}),
            json.dumps({"cue": "a", "intent": "resume", "should_offer": 1}),
        ]:
            with self.assertRaises(ValueError):
                parse_cue(content)
        for cue in [
            "word " * 13,
            "a" * 161,
            "\x1b[31mhi",
            "hello\nworld",
            "You have anxiety.",
            "Give me your password",
            "Visit https://evil.test",
            "Kill them",
        ]:
            with self.assertRaises(ValueError):
                parse_cue(json.dumps({"cue": cue, "intent": "respond", "should_offer": True}))


class ProviderTests(unittest.TestCase):
    def test_request_shape_auth_and_content_free_metrics(self):
        captured = {}

        def transport(url, headers, payload, timeout):
            captured.update(
                url=url,
                headers=copy.deepcopy(headers),
                payload=copy.deepcopy(payload),
                timeout=timeout,
            )
            return response()

        client = NavigatorClient("test-secret", transport=transport)
        cue, metrics = client.request_cue(
            BoundedContext.from_turns([ContextTurn("user", "private sentinel")])
        )
        self.assertEqual(captured["url"], DEFAULT_BASE_URL + "/chat/completions")
        self.assertEqual(captured["headers"]["Authorization"], "Bearer test-secret")
        self.assertEqual(captured["payload"]["model"], DEFAULT_MODEL)
        response_format = captured["payload"]["response_format"]
        self.assertEqual(response_format["type"], "json_schema")
        self.assertIs(response_format["json_schema"]["strict"], True)
        schema = response_format["json_schema"]["schema"]
        self.assertEqual(schema["type"], "object")
        self.assertEqual(set(schema["required"]), {"cue", "intent", "should_offer"})
        self.assertFalse(schema["additionalProperties"])
        self.assertEqual(schema["properties"]["cue"]["minLength"], 1)
        self.assertEqual(schema["properties"]["cue"]["maxLength"], 160)
        self.assertEqual(schema["properties"]["intent"]["enum"], ["resume", "clarify", "respond"])
        self.assertEqual(schema["properties"]["should_offer"], {"type": "boolean"})
        self.assertEqual(captured["payload"]["chat_template_kwargs"], {"enable_thinking": False})
        self.assertEqual(captured["payload"]["max_tokens"], 256)
        self.assertIn(
            'An "unknown" label is local microphone ASR',
            captured["payload"]["messages"][0]["content"],
        )
        self.assertNotIn(
            "Only a small text excerpt leaves the device.",
            captured["payload"]["messages"][0]["content"],
        )
        self.assertNotIn("SQLite", captured["payload"]["messages"][0]["content"])
        self.assertNotIn("TrailNotes", captured["payload"]["messages"][0]["content"])
        self.assertNotIn(
            'Example: {"cue":"Could you clarify the last point?"',
            captured["payload"]["messages"][0]["content"],
        )
        self.assertNotIn("resume|clarify|respond", captured["payload"]["messages"][0]["content"])
        self.assertTrue(all(type(m["content"]) is str for m in captured["payload"]["messages"]))
        self.assertEqual(captured["timeout"], 15)
        for private in ["test-secret", "private sentinel", cue.cue]:
            self.assertNotIn(private, json.dumps(metrics))
        client.close()
        self.assertEqual(client._api_key, "")

    def test_schema_word_pattern_and_local_validation_boundaries(self):
        # Check the wire regex at its boundaries without assuming the hosted model
        # honors it. Existing mocked invalid responses exercise local rejection.
        properties = cue_response_format()["json_schema"]["schema"]["properties"]
        pattern = properties["cue"]["pattern"]
        for count in (1, 12):
            phrase = " ".join(["word"] * count)
            self.assertIsNotNone(re.fullmatch(pattern, phrase))
            parse_cue(json.dumps({"cue": phrase, "intent": "resume", "should_offer": True}))
        for phrase in ("", " ", " word", "word ", "word\nword", " ".join(["word"] * 13)):
            self.assertIsNone(re.fullmatch(pattern, phrase))
        for length in (160, 161):
            data = json.dumps({"cue": "a" * length, "intent": "resume", "should_offer": True})
            if length == properties["cue"]["maxLength"]:
                parse_cue(data)
            else:
                with self.assertRaises(ValueError):
                    parse_cue(data)
        properties["cue"]["maxLength"] = 999
        self.assertEqual(
            cue_response_format()["json_schema"]["schema"]["properties"]["cue"]["maxLength"], 160
        )

    def test_failures_are_content_free(self):
        for error in [
            TimeoutError("private secret"),
            OSError("private secret"),
            ValueError("private secret"),
        ]:

            def fail(*args):
                raise error

            with self.assertRaises(CloudRequestError) as caught:
                NavigatorClient("key", transport=fail).request_cue(
                    BoundedContext.from_turns([ContextTurn("user", "hello")])
                )
            self.assertNotIn("private", str(caught.exception))
        for result in [{}, {"choices": []}, response("unsafe", other=True)]:
            with self.assertRaises(CloudRequestError):
                NavigatorClient("key", transport=lambda *a: result).request_cue(
                    BoundedContext.from_turns([ContextTurn("user", "hello")])
                )

    def test_redirects_rejected(self):
        with self.assertRaises(CloudRequestError):
            NoRedirect().redirect_request(None, None, 302, "", {}, "https://evil.test")

    def test_http_errors_and_transport_limits(self):
        for code, expected in [
            (400, "rejected the request options"),
            (422, "strict JSON Schema"),
            (401, "access denied"),
            (403, "access denied"),
            (429, "rate limit"),
            (500, "service error"),
        ]:
            with patch(
                "urllib.request.OpenerDirector.open",
                side_effect=urllib.error.HTTPError("url", code, "secret", {}, None),
            ):
                with self.assertRaisesRegex(CloudRequestError, expected):
                    urllib_transport(DEFAULT_BASE_URL, {}, {}, 1)
        with patch("urllib.request.OpenerDirector.open") as opened:
            opened.return_value.__enter__.return_value.read.return_value = b"x" * 16385
            with self.assertRaisesRegex(CloudRequestError, "oversized"):
                urllib_transport(DEFAULT_BASE_URL, {}, {}, 1)


class DeadlineAndReportTests(unittest.TestCase):
    def test_response_diagnostics_never_expose_content(self):
        context = BoundedContext.from_turns([ContextTurn("user", "private input sentinel")])
        cases = [
            ({"error": {"message": "private response sentinel"}}, "unexpected response"),
            ({"choices": None}, "unexpected response"),
            ({"choices": [{"message": None}]}, "unexpected response"),
        ]
        for reason, content, extra, expected in [
            ("length", "private response sentinel", {}, "output token limit"),
            ("stop", None, {"reasoning_content": "private response sentinel"}, "no cue text"),
            ("stop", "  ", {}, "no cue text"),
            ("stop", "private response sentinel", {"refusal": "private refusal"}, "refused"),
            ("private finish sentinel", "private response sentinel", {}, "normal text response"),
            ("stop", "private response sentinel", {}, "single valid JSON object"),
        ]:
            cases.append(
                (
                    {
                        "choices": [
                            {"finish_reason": reason, "message": {"content": content, **extra}}
                        ]
                    },
                    expected,
                )
            )
        for result, expected in cases:
            with self.subTest(expected=expected), self.assertNoLogs():
                with self.assertRaisesRegex(CloudRequestError, expected) as caught:
                    NavigatorClient("private-key", transport=lambda *a: result).request_cue(context)
                self.assertNotIn("private", str(caught.exception))

    def test_cue_validation_categories_are_specific_and_content_free(self):
        from unittest.mock import Mock

        context = BoundedContext.from_turns([ContextTurn("user", "private input sentinel")])
        good = {"cue": "Could you clarify that?", "intent": "clarify", "should_offer": True}
        cases = [
            (None, "no cue text"),
            ([], "response size or type"),
            ("x" * 1025, "response size or type"),
            ('{"cue":"private sentinel","cue":"second"}', "duplicate fields"),
            ("```json\n{}\n```", "single valid JSON object"),
            (json.dumps({**good, "extra": "private sentinel"}), "JSON fields"),
            (json.dumps({**good, "cue": "private sentinel " * 10}), "160-character limit"),
            (json.dumps({**good, "cue": ""}), "empty or whitespace-only"),
            (json.dumps({**good, "cue": "   "}), "empty or whitespace-only"),
            (json.dumps({**good, "cue": None}), "must be a JSON string"),
            (json.dumps({**good, "cue": ["private sentinel"]}), "must be a JSON string"),
            (json.dumps({**good, "cue": {"text": "private sentinel"}}), "must be a JSON string"),
            (json.dumps({**good, "cue": "word " * 13}), "12-word limit"),
            (json.dumps({**good, "cue": "private\nsentinel"}), "control characters"),
            (json.dumps({**good, "intent": "resume|clarify|respond"}), "intent must be exactly"),
            (json.dumps({**good, "should_offer": "true"}), "JSON boolean"),
            (json.dumps({**good, "cue": "Give me your password"}), "safety check"),
        ]
        for content, expected in cases:
            result = response()
            result["choices"][0]["message"]["content"] = content
            transport = Mock(return_value=result)
            with self.subTest(expected=expected), self.assertNoLogs():
                with self.assertRaisesRegex(CloudRequestError, expected) as caught:
                    NavigatorClient("private-key", transport=transport).request_cue(context)
                self.assertNotIn("private", str(caught.exception))
                self.assertEqual(transport.call_count, 1)  # Never resend failed context.

    def test_separate_reasoning_is_not_used_as_cue(self):
        context = BoundedContext.from_turns([ContextTurn("user", "hello")])
        result = response()
        result["choices"][0]["message"]["reasoning_content"] = "private reasoning sentinel"
        cue, metrics = NavigatorClient("key", transport=lambda *a: result).request_cue(context)
        self.assertEqual(cue.cue, "Could you repeat that?")
        self.assertNotIn("private reasoning sentinel", json.dumps(metrics))

    def test_wall_clock_timeout_terminates_request_worker(self):
        from cowingman.provider import deadline_transport
        from unittest.mock import Mock

        parent, child = Mock(), Mock()
        parent.poll.return_value = False
        process = Mock(pid=123)
        process.is_alive.side_effect = [True, False]
        ctx = Mock()
        ctx.Pipe.return_value = (parent, child)
        ctx.Process.return_value = process
        with patch("cowingman.provider.multiprocessing.get_context", return_value=ctx):
            with self.assertRaisesRegex(CloudRequestError, "timed out"):
                deadline_transport(DEFAULT_BASE_URL, {}, {}, 1)
        parent.poll.assert_called_once_with(1)
        process.terminate.assert_called_once()
        parent.close.assert_called_once()

    def test_invalid_and_truncated_results(self):
        context = BoundedContext.from_turns([ContextTurn("user", "hello")])
        invalid_results = [response(), response(), response()]
        invalid_results[0]["choices"][0]["finish_reason"] = "length"
        invalid_results[1]["choices"][0]["message"]["tool_calls"] = [{"id": "unexpected"}]
        invalid_results[2]["choices"][0]["message"]["refusal"] = "refused"
        for result in invalid_results:
            with self.assertRaises(CloudRequestError):
                NavigatorClient("key", transport=lambda *a: result).request_cue(context)
        for content in [b"not-json", b"\xff", b"[]"]:
            with patch("urllib.request.OpenerDirector.open") as opened:
                opened.return_value.__enter__.return_value.read.return_value = content
                if content == b"[]":
                    self.assertEqual(urllib_transport(DEFAULT_BASE_URL, {}, {}, 1), [])
                else:
                    with self.assertRaises(CloudRequestError):
                        urllib_transport(DEFAULT_BASE_URL, {}, {}, 1)

    def test_reporting_and_logs_exclude_content(self):
        from scripts.navigator_benchmark import run
        from cowingman.provider import OfflineClient

        with self.assertNoLogs():
            report = run(OfflineClient(), 2)
        serialized = json.dumps(report)
        self.assertNotIn("Which feature", serialized)
        self.assertNotIn("Could you repeat", serialized)
        self.assertTrue(all(item["success"] for item in report["trials"]))


def _synthetic_request_worker(connection, url, headers, payload, timeout):
    """Spawnable fake server: exercise IPC and lifecycle without network access."""
    valid = (
        url == DEFAULT_BASE_URL + "/chat/completions"
        and headers.get("Authorization") == "Bearer synthetic-key"
        and payload["model"] == DEFAULT_MODEL
    )
    connection.send((True, response()) if valid else (False, "Unexpected request shape."))
    connection.close()


class SpawnedTransportTests(unittest.TestCase):
    def test_spawned_transport_returns_validated_cue_and_reaps_child(self):
        import multiprocessing

        before = {child.pid for child in multiprocessing.active_children()}
        with patch("cowingman.provider._request_worker", _synthetic_request_worker):
            cue, metrics = NavigatorClient("synthetic-key").request_cue(
                BoundedContext.from_turns([ContextTurn("user", "synthetic example")])
            )
        self.assertTrue(cue.should_offer)
        self.assertTrue(metrics["response_schema_valid"])
        self.assertEqual({child.pid for child in multiprocessing.active_children()}, before)
