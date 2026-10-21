import copy
from datetime import datetime, timedelta, timezone
import io
import json
import unittest
from unittest.mock import Mock, MagicMock, patch

from cowingman.app import Application
from cowingman.audio import ContinuousMicrophone
from cowingman.config import Config
from cowingman.context import BoundedContext, ContextTurn, RollingContext
from cowingman.cue import Cue
from cowingman.errors import CloudRequestError, ConfigurationError, PrivacyBoundaryError
from cowingman.memory import ConversationMemory, S3SummaryStore, checked_record
from cowingman.provider import NavigatorClient
from test_application import FakeUI


def record():
    return {
        "version": 1,
        "session_id": "a" * 32,
        "window_start": "2026-01-01T00:00:00.000Z",
        "window_end": "2026-01-01T00:01:00.000Z",
        "created_at": "2026-01-01T00:01:02.000Z",
        "summary": "A project was discussed; speaker identity was not established.",
    }


class RollingMemoryTests(unittest.TestCase):
    def test_minute_summary_includes_fifteen_windows_and_only_saves_summary(self):
        now = [0.0]
        base = datetime(2026, 1, 1, tzinfo=timezone.utc)
        client = Mock()
        client.summarize.return_value = "The participants discussed a project."
        store = Mock()
        memory = ConversationMemory(
            client, store, clock=lambda: now[0], utc_clock=lambda: base + timedelta(seconds=now[0])
        )
        for index in range(15):
            now[0] = (index + 1) * 4
            memory.add(f"private speech {index}", "unknown", captured_at=index * 4)
        self.assertTrue(memory.due())
        self.assertTrue(memory.flush())
        previous, window = client.summarize.call_args.args
        self.assertEqual(previous, "")
        self.assertEqual(len(window.turns), 15)
        self.assertTrue(window.rolling)
        saved = store.upload.call_args.args[0]
        self.assertEqual(saved["window_start"], "2026-01-01T00:00:00.000Z")
        self.assertEqual(saved["window_end"], "2026-01-01T00:01:00.000Z")
        self.assertNotIn("private speech", json.dumps(saved))
        self.assertEqual(checked_record(saved), saved)
        self.assertFalse(memory.flush())
        now[0] = 124
        memory.add("new topic", "unknown", captured_at=120)
        memory.flush()
        self.assertEqual(len(client.summarize.call_args.args[1].turns), 1)
        self.assertEqual(client.summarize.call_args.args[0], "")

    def test_idle_memory_does_not_call_cloud(self):
        now = [0]
        client = Mock()
        memory = ConversationMemory(client, clock=lambda: now[0])
        now[0] = 60
        self.assertFalse(memory.flush())
        client.summarize.assert_not_called()
        self.assertFalse(memory.due())

    def test_failed_upload_is_retried_without_resummarizing(self):
        client = Mock()
        client.summarize.return_value = "A question remains open."
        store = Mock()
        store.upload.side_effect = [CloudRequestError("S3 failed."), None]
        memory = ConversationMemory(client, store)
        memory.add("private question", "partner")
        with self.assertRaises(CloudRequestError):
            memory.flush()
        self.assertIsNotNone(memory.pending_upload)
        self.assertTrue(memory.flush())
        self.assertIsNone(memory.pending_upload)
        self.assertEqual(client.summarize.call_count, 1)
        self.assertEqual(store.upload.call_count, 2)

    def test_resume_and_forget_do_not_delete_s3_records(self):
        store = Mock()
        store.load.return_value = record()
        memory = ConversationMemory(Mock(), store, resume="windows/saved.json")
        store.load.assert_called_once_with("windows/saved.json")
        self.assertEqual(memory.text, record()["summary"])
        memory.forget()
        self.assertEqual(memory.text, "")
        store.delete.assert_not_called()

    def test_rolling_boundary_and_expiry_remain_enforced(self):
        turns = [ContextTurn("unknown", "x" * 240) for _ in range(15)]
        window = BoundedContext.from_turns(turns, rolling=True)
        self.assertEqual(window.character_count, 3600)
        for values, rolling in ((turns, False), (turns + turns[:1], True), (turns, "yes")):
            with self.assertRaises(PrivacyBoundaryError):
                BoundedContext.from_turns(values, rolling=rolling)
        now = [0]
        context = RollingContext(clock=lambda: now[0], rolling=True)
        context.add("old", captured_at=0)
        now[0] = 59
        context.add("new", captured_at=59)
        now[0] = 60
        self.assertEqual([t.text for t in context.snapshot().turns], ["new"])


class S3SummaryTests(unittest.TestCase):
    def test_private_encrypted_objects_and_bounded_reload(self):
        s3 = Mock()
        store = S3SummaryStore("s3://example-bucket/device-one", "us-east-1", client=s3)
        store.upload(record())
        self.assertEqual(s3.put_object.call_count, 2)
        for call in s3.put_object.call_args_list:
            args = call.kwargs
            self.assertEqual(args["Bucket"], "example-bucket")
            self.assertTrue(args["Key"].startswith("device-one/"))
            self.assertEqual(args["ServerSideEncryption"], "AES256")
            self.assertNotIn("ACL", args)
            self.assertEqual(json.loads(args["Body"]), record())
        body = io.BytesIO(json.dumps(record()).encode())
        s3.get_object.return_value = {"Body": body}
        self.assertEqual(store.load(), record())
        self.assertTrue(body.closed)
        s3.get_object.assert_called_once_with(Bucket="example-bucket", Key="device-one/latest.json")

    def test_bad_records_and_aws_errors_are_content_free(self):
        s3 = Mock()
        store = S3SummaryStore("s3://example-bucket/device-one", "us-east-1", client=s3)
        for data in (
            b"x" * 16385,
            b"private invalid sentinel",
            json.dumps({**record(), "summary": "x" * 1201}).encode(),
        ):
            body = io.BytesIO(data)
            s3.get_object.return_value = {"Body": body}
            with self.assertRaises(ConfigurationError) as caught:
                store.load()
            self.assertNotIn("sentinel", str(caught.exception))
            self.assertTrue(body.closed)
        with self.assertRaises(ConfigurationError):
            store.load("../another-prefix/latest.json")
        s3.put_object.side_effect = RuntimeError("private credentials sentinel")
        with self.assertRaises(CloudRequestError) as caught:
            store.upload(record())
        self.assertNotIn("sentinel", str(caught.exception))


class RollingApplicationTests(unittest.TestCase):
    def test_pause_requests_after_ingesting_batch_and_keeps_listening(self):
        client = Mock()
        client.request_cue.return_value = (Cue("Here is the next point.", "resume", True), {})
        audio = Mock(process=object())
        audio.poll.return_value = [("fragment", "first"), ("pause", None), ("fragment", "second")]
        app = Application(Config(), client, FakeUI(), audio=audio, rolling=True, pause_assist=True)
        app.tick()
        self.assertEqual(client.request_cue.call_count, 1)
        sent = client.request_cue.call_args.args[0]
        self.assertIn("second", sent.turns[-1].text)
        self.assertTrue(sent.rolling)
        audio.close.assert_not_called()
        self.assertFalse(app.pending_resume)
        self.assertGreater(len(app.context), 0)
        app.request_cue()
        self.assertEqual(client.request_cue.call_count, 2)
        app.command(":pause")
        audio.close.assert_called_once()
        app.close()

    def test_new_windows_update_context_without_requesting_a_cue(self):
        client = Mock()
        audio = Mock(process=object())
        audio.poll.return_value = [("fragment", "a new topic")]
        app = Application(Config(), client, FakeUI(), audio=audio, rolling=True, pause_assist=True)
        app.tick()
        client.request_cue.assert_not_called()
        self.assertEqual(len(app.context), 1)
        app.close()

    def test_summary_payload_and_cue_history_are_bounded_and_separate(self):
        calls = []

        def transport(url, headers, payload, timeout):
            calls.append(copy.deepcopy(payload))
            if payload["response_format"]["json_schema"]["name"] == "conversation_summary":
                return {
                    "choices": [
                        {
                            "message": {
                                "content": json.dumps({"summary": "A project was discussed."})
                            }
                        }
                    ]
                }
            return {
                "choices": [
                    {
                        "message": {
                            "content": json.dumps(
                                {
                                    "cue": "Let me explain the next part.",
                                    "intent": "resume",
                                    "should_offer": True,
                                }
                            )
                        }
                    }
                ]
            }

        client = NavigatorClient("synthetic", transport=transport)
        window = BoundedContext.from_turns(
            [ContextTurn("unknown", "project") for _ in range(15)], rolling=True
        )
        summary = client.summarize("", window)
        cue, metrics = client.request_cue(window, summary=summary)
        self.assertTrue(cue.should_offer)
        self.assertEqual(metrics["summary_characters"], len(summary))
        self.assertEqual(
            len(json.loads(calls[0]["messages"][1]["content"])["recent_fragments"]), 15
        )
        self.assertEqual(
            json.loads(calls[1]["messages"][1]["content"])["conversation_summary"], summary
        )
        with self.assertRaises(PrivacyBoundaryError):
            client.request_cue(window, summary="x" * 1201)
        self.assertEqual(len(calls), 2)

    def test_invalid_summary_is_not_uploaded_or_used(self):
        for content in (
            '{"summary":"first","summary":"second"}',
            json.dumps({"summary": "x" * 1201}),
            json.dumps({"summary": "private\nsentinel"}),
            json.dumps({"summary": ""}),
            json.dumps({"summary": [], "extra": "private sentinel"}),
        ):
            transport = Mock(return_value={"choices": [{"message": {"content": content}}]})
            client = NavigatorClient("synthetic", transport=transport)
            store = Mock()
            memory = ConversationMemory(client, store)
            memory.add("private question", "partner")
            with self.assertRaises(CloudRequestError) as caught:
                memory.flush()
            self.assertNotIn("private", str(caught.exception))
            self.assertEqual(memory.text, "")
            store.upload.assert_not_called()
            self.assertEqual(transport.call_count, 1)

    def test_capture_queue_discards_and_zeros_old_audio(self):
        capture = ContinuousMicrophone(None, 0.015)
        old, new = Mock(), Mock()
        capture._offer((0, old, True, False))
        capture._offer((4, new, True, False))
        old.fill.assert_called_once_with(0)
        self.assertEqual(capture.dropped, 1)
        self.assertEqual(capture.windows.qsize(), 1)
        capture.close()
        new.fill.assert_called_once_with(0)

    def test_capture_keeps_one_stream_open_across_four_second_windows(self):
        capture = ContinuousMicrophone(None, 0.015)
        capture.microphone = Mock()
        old, new, block = MagicMock(), MagicMock(), MagicMock()
        np = Mock()
        np.zeros.side_effect = [old, new]
        np.sqrt.return_value = 0.02
        reads = [0]

        def read():
            reads[0] += 1
            if reads[0] == 32:
                capture.stopped.set()
            return block

        capture.microphone.read.side_effect = read
        with patch.dict("sys.modules", numpy=np):
            capture._capture()
        self.assertIsNone(capture.error)
        capture.microphone.open.assert_called_once()
        capture.microphone.close.assert_called_once()
        self.assertEqual(reads[0], 32)
        self.assertEqual(capture.dropped, 1)
        old.fill.assert_called_once_with(0)
        self.assertIs(capture.windows.get_nowait()[1], new)
