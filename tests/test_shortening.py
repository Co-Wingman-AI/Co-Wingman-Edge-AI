import copy
import json
import unittest
from unittest.mock import Mock, patch

from cowingman.config import DEFAULT_BASE_URL, DEFAULT_MODEL
from cowingman.context import BoundedContext, ContextTurn
from cowingman.cue import cue_response_format
from cowingman.errors import CloudRequestError
from cowingman.provider import NavigatorClient


def response(cue, *, intent="resume", should_offer=True):
    return {
        "choices": [
            {
                "finish_reason": "stop",
                "message": {
                    "content": json.dumps(
                        {
                            "cue": cue,
                            "intent": intent,
                            "should_offer": should_offer,
                        }
                    )
                },
            }
        ]
    }


def context():
    return BoundedContext.from_turns([ContextTurn("user", "private context sentinel")])


class ShorteningTests(unittest.TestCase):
    def test_repair_sends_only_draft_to_same_model_with_remaining_deadline(self):
        draft = (
            "I evaluated the prototype on simulated data, and the preliminary results "
            "need validation with real users before I can make claims about performance."
        )
        shortened = "I evaluated a prototype on simulated data; validation remains pending."
        replies = iter([response(draft), response(shortened)])
        calls = []
        references = []

        def transport(url, headers, payload, timeout):
            calls.append((url, copy.deepcopy(headers), copy.deepcopy(payload), timeout))
            references.append((headers, payload))
            return next(replies)

        with patch("cowingman.provider.time.monotonic", side_effect=[10, 12, 13]):
            cue, metrics = NavigatorClient("test-key", transport=transport).request_cue(context())
        self.assertEqual(cue.cue, shortened)
        self.assertEqual(len(calls), 2)
        self.assertEqual(calls[0][3], 15)
        self.assertEqual(calls[1][3], 13)
        url, headers, payload, _ = calls[1]
        self.assertEqual(url, DEFAULT_BASE_URL + "/chat/completions")
        self.assertEqual(headers["Authorization"], "Bearer test-key")
        self.assertEqual(payload["model"], DEFAULT_MODEL)
        self.assertEqual(payload["response_format"], cue_response_format())
        self.assertFalse(payload["chat_template_kwargs"]["enable_thinking"])
        self.assertEqual(
            json.loads(payload["messages"][1]["content"]),
            {
                "draft": draft,
                "intent": "resume",
            },
        )
        self.assertNotIn("private context sentinel", json.dumps(payload))
        self.assertIn("negation", payload["messages"][0]["content"])
        self.assertIn("qualifications", payload["messages"][0]["content"])
        self.assertEqual(metrics["request_count"], 2)
        self.assertTrue(metrics["cue_shortened"])
        self.assertFalse(metrics["response_schema_valid"])
        self.assertEqual(metrics["shortening_characters"], len(draft))
        self.assertNotIn(draft, json.dumps(metrics))
        self.assertNotIn(shortened, json.dumps(metrics))
        self.assertNotIn("portfolio_fallback", metrics)
        self.assertTrue(all(h == {} and p == {} for h, p in references))

    def test_in_limit_response_needs_no_shortening(self):
        transport = Mock(return_value=response("I evaluated a prototype."))
        cue, metrics = NavigatorClient("key", transport=transport).request_cue(context())
        self.assertEqual(cue.cue, "I evaluated a prototype.")
        self.assertEqual(transport.call_count, 1)
        self.assertEqual(metrics["request_count"], 1)
        self.assertEqual(metrics["shortening_characters"], 0)
        self.assertFalse(metrics["cue_shortened"])
        self.assertTrue(metrics["response_schema_valid"])

    def test_failed_shortening_is_never_repeated_or_displayed(self):
        for repair in (
            response("word " * 13),
            response("a" * 161),
            response("Give me your password."),
            response("Changed intent.", intent="respond"),
            response("private context sentinel"),
            {"choices": [{"message": {"content": "private malformed sentinel"}}]},
            CloudRequestError("NaviGator connection failed."),
        ):
            with self.subTest(repair=type(repair).__name__), self.assertNoLogs():
                transport = Mock(side_effect=[response("word " * 40), repair])
                with self.assertRaises(CloudRequestError) as caught:
                    NavigatorClient("key", transport=transport).request_cue(context())
                self.assertEqual(transport.call_count, 2)
                self.assertNotIn("sentinel", str(caught.exception))

    def test_no_repair_when_deadline_exhausted(self):
        transport = Mock(return_value=response("word " * 40))
        with patch("cowingman.provider.time.monotonic", side_effect=[10, 25]):
            with self.assertRaisesRegex(CloudRequestError, "no time to shorten"):
                NavigatorClient("key", transport=transport).request_cue(context())
        self.assertEqual(transport.call_count, 1)

    def test_oversized_echo_is_not_sent_for_shortening(self):
        text = "word " * 40
        transport = Mock(return_value=response(text))
        same = BoundedContext.from_turns([ContextTurn("user", text)])
        with self.assertRaisesRegex(CloudRequestError, "repeated the input"):
            NavigatorClient("key", transport=transport).request_cue(same)
        self.assertEqual(transport.call_count, 1)

    def test_no_shortening_for_refusal_or_incomplete_or_unbounded_output(self):
        refused = response("word " * 40)
        refused["choices"][0]["message"]["refusal"] = "private refusal sentinel"
        truncated = response("word " * 40)
        truncated["choices"][0]["finish_reason"] = "length"
        for original in (refused, truncated, response("word " * 300)):
            transport = Mock(return_value=original)
            with self.assertRaises(CloudRequestError):
                NavigatorClient("key", transport=transport).request_cue(context())
            self.assertEqual(transport.call_count, 1)
