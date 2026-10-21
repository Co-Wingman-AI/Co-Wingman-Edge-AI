"""Opt-in one-minute summary memory, with timestamped S3 persistence."""

from datetime import datetime, timedelta, timezone
import json
import re
import time
from urllib.parse import urlsplit
from uuid import uuid4

from .context import RollingContext
from .errors import CloudRequestError, ConfigurationError, PrivacyBoundaryError

MAX_SUMMARY_CHARACTERS = 1200


def checked_summary(value):
    if type(value) is not str or len(value) > MAX_SUMMARY_CHARACTERS:
        raise PrivacyBoundaryError("Conversation summary must be at most 1200 characters.")
    if value and not value.isprintable():
        raise PrivacyBoundaryError("Conversation summary contains unsupported characters.")
    return value.strip()


def utc_now():
    return datetime.now(timezone.utc)


def stamp(value):
    return value.astimezone(timezone.utc).isoformat(timespec="milliseconds").replace("+00:00", "Z")


def checked_record(value):
    keys = {"version", "session_id", "window_start", "window_end", "created_at", "summary"}
    if (
        type(value) is not dict
        or set(value) != keys
        or type(value["version"]) is not int
        or value["version"] != 1
    ):
        raise ValueError
    if type(value["session_id"]) is not str or not re.fullmatch(
        r"[0-9a-f]{32}", value["session_id"]
    ):
        raise ValueError
    dates = []
    for key in ("window_start", "window_end", "created_at"):
        item = value[key]
        if type(item) is not str or not item.endswith("Z"):
            raise ValueError
        dates.append(datetime.fromisoformat(item.replace("Z", "+00:00")))
    if not 0 <= (dates[1] - dates[0]).total_seconds() <= 60.01 or dates[2] < dates[1]:
        raise ValueError
    summary = checked_summary(value["summary"])
    if not summary:
        raise ValueError
    return {**value, "summary": summary}


class S3SummaryStore:
    def __init__(self, uri, region, *, client=None):
        parsed = urlsplit(uri)
        if (
            parsed.scheme != "s3"
            or not re.fullmatch(r"[a-z0-9][a-z0-9.-]{1,61}[a-z0-9]", parsed.netloc)
            or parsed.query
            or parsed.fragment
        ):
            raise ConfigurationError("Use an S3 destination such as s3://bucket/conversations.")
        self.bucket = parsed.netloc
        self.prefix = parsed.path.strip("/") or "cowingman"
        if not re.fullmatch(r"[A-Za-z0-9/_-]+", self.prefix):
            raise ConfigurationError(
                "S3 prefix must use letters, digits, slash, underscore or hyphen."
            )
        if not region or not re.fullmatch(r"[a-z]{2}(?:-[a-z]+)+-\d", region):
            raise ConfigurationError("Set --aws-region to the bucket's AWS region.")
        if client is not None:
            self.client = client
        else:
            try:
                import boto3
                from botocore.config import Config

                self.client = boto3.client(
                    "s3",
                    region_name=region,
                    config=Config(
                        connect_timeout=5, read_timeout=10, retries={"total_max_attempts": 1}
                    ),
                )
            except Exception:
                raise ConfigurationError(
                    "S3 unavailable. Install the cloud extra and configure AWS credentials on this device."
                ) from None

    def upload(self, record):
        record = checked_record(record)
        key = record["window_end"].replace(":", "-") + "-" + record["session_id"] + ".json"
        body = json.dumps(record, ensure_ascii=True).encode("utf-8")
        try:
            for name in ("windows/" + key, "latest.json"):
                self.client.put_object(
                    Bucket=self.bucket,
                    Key=self.prefix + "/" + name,
                    Body=body,
                    ContentType="application/json",
                    ServerSideEncryption="AES256",
                )
        except Exception:
            raise CloudRequestError(
                "S3 summary upload failed. Check AWS credentials, bucket permissions, region and network."
            ) from None

    def load(self, key="latest.json"):
        if not re.fullmatch(r"latest\.json|windows/[A-Za-z0-9_.-]+\.json", key):
            raise ConfigurationError("Use latest.json or a windows/ summary key from this prefix.")
        body = None
        try:
            response = self.client.get_object(Bucket=self.bucket, Key=self.prefix + "/" + key)
            body = response["Body"]
            data = body.read(16385)
            if len(data) > 16384:
                raise ValueError
            return checked_record(json.loads(data))
        except Exception:
            raise ConfigurationError(
                "Cannot load the latest S3 summary. Check access, or start without --resume-summary."
            ) from None
        finally:
            if body is not None:
                body.close()


class ConversationMemory:
    def __init__(
        self, client, store=None, *, resume=False, clock=time.monotonic, utc_clock=utc_now
    ):
        self.client = client
        self.store = store
        self.clock = clock
        self.utc_clock = utc_clock
        self.recent = RollingContext(60, clock, rolling=True)
        self.text = ""
        self.revision = self.saved_revision = 0
        self.next_update = clock() + 60
        self.session_id = uuid4().hex
        self.pending_upload = None
        self.last_upload_end = None
        if resume:
            if store is None:
                raise ConfigurationError("--resume-summary requires an S3 destination.")
            record = store.load(resume if type(resume) is str else "latest.json")
            self.text = checked_summary(record["summary"])

    def add(self, text, speaker, *, captured_at=None):
        if captured_at is not None and speaker == "unknown":
            # A capture spans four seconds. Archive by its end so the first
            # window is still eligible at the first one-minute summary boundary.
            captured_at = min(self.clock(), captured_at + 4)
        self.recent.add(text, speaker, captured_at=captured_at)
        self.revision += 1

    def due(self):
        return self.clock() >= self.next_update

    def flush(self):
        now = self.clock()
        self.next_update = now + 60
        uploaded = False
        if self.pending_upload is not None:
            self.store.upload(self.pending_upload)
            self.last_upload_end = self.pending_upload["window_end"]
            self.pending_upload = None
            uploaded = True
        if self.revision == self.saved_revision or not len(self.recent):
            return uploaded
        window = self.recent.snapshot()
        end = self.utc_clock()
        first_at, first_turn = self.recent._items[0]
        if first_turn.speaker == "unknown":
            first_at -= 4
        start = end - timedelta(seconds=min(60, max(0, now - first_at)))
        # A minute record summarizes only this window, never accumulated history.
        summary = checked_summary(self.client.summarize("", window))
        if not summary:
            raise CloudRequestError("The model returned an empty conversation summary.")
        record = checked_record(
            {
                "version": 1,
                "session_id": self.session_id,
                "window_start": stamp(start),
                "window_end": stamp(end),
                "created_at": stamp(max(end, self.utc_clock())),
                "summary": summary,
            }
        )
        self.text = summary
        self.saved_revision = self.revision
        if self.store:
            self.pending_upload = record
            self.store.upload(record)
            self.last_upload_end = record["window_end"]
            self.pending_upload = None
        return True

    def clear_recent(self):
        self.recent.clear()
        self.saved_revision = self.revision

    def forget(self):
        self.text = ""
        self.clear_recent()
        self.pending_upload = None

    def close(self):
        self.forget()
        self.client = None
