"""Opt-in local portfolio passages and bounded keyword retrieval; no runtime network."""

from __future__ import annotations

import argparse
from dataclasses import dataclass
from datetime import datetime, timezone
from html.parser import HTMLParser
import json
import math
from pathlib import Path
import re
import urllib.request

from .errors import ConfigurationError, PrivacyBoundaryError

MAX_FILE_BYTES = 256_000
MAX_PASSAGES = 256
MAX_PASSAGE_CHARACTERS = 600
MAX_SELECTED_PASSAGES = 2
MAX_SELECTED_CHARACTERS = 1200
SOURCE_REVISION = "2cc372613dde6c7a5dfb5bed24cc9bf5cdeedc26"
SOURCE_BASE = "https://honeyreddydaram.github.io/Portfolio/"
PAGES = ("index.html", "projects.html", "experience.html", "certifications.html")
STOP_WORDS = frozenset(
    "a an the i me my you your we our it its is are was were be been am "
    "and or of to for in on at by with from as that this those these have has had "
    "do did does can could would will should what which how why when where "
    "tell about explain please some more because so then just something "
    "worked work working used use using built build building".split()
)
QUERY_ALIASES = {
    "study": {"education", "university"},
    "studying": {"education", "university"},
    "school": {"education", "university"},
    "college": {"education", "college"},
    "internship": {"intern"},
    "yourself": {"introduction"},
    "background": {"education", "experience"},
}


def tokens(text):
    # Small lexical index: no additional model or GPU memory required.
    result = set()
    for word in re.findall(r"[a-z0-9]+", text.lower()):
        if word in STOP_WORDS or len(word) < 2:
            continue
        if word.endswith("s") and len(word) > 4 and not word.endswith("ss"):
            word = word[:-1]
        result.add(word)
    return result


def checked_selection(passages):
    """Recheck the entire selection at the outbound boundary, before serialization."""
    if type(passages) not in (list, tuple) or len(passages) > MAX_SELECTED_PASSAGES:
        raise PrivacyBoundaryError("Portfolio selection exceeds its bounds.")
    if any(
        type(text) is not str
        or not 1 <= len(text) <= MAX_PASSAGE_CHARACTERS
        or not text.isprintable()
        for text in passages
    ):
        raise PrivacyBoundaryError("Invalid portfolio passage.")
    if sum(map(len, passages)) > MAX_SELECTED_CHARACTERS:
        raise PrivacyBoundaryError("Portfolio selection exceeds its bounds.")
    return tuple(passages)


@dataclass(frozen=True, repr=False)
class Portfolio:
    passages: tuple[str, ...]

    @classmethod
    def load(cls, path):
        try:
            with Path(path).open("rb") as stream:
                data = stream.read(MAX_FILE_BYTES + 1)
            if len(data) > MAX_FILE_BYTES:
                raise ValueError
            value = json.loads(data)
            if type(value) is not dict or value.get("version") != 1:
                raise ValueError
            records = value["passages"]
            if type(records) is not list or not 1 <= len(records) <= MAX_PASSAGES:
                raise ValueError
            texts = []
            for record in records:
                if type(record) is not dict:
                    raise ValueError
                text = record["text"]
                checked_selection([text])
                texts.append(text)
            return cls(tuple(dict.fromkeys(texts)))
        except (OSError, ValueError, KeyError, TypeError, RecursionError):
            raise ConfigurationError(
                "Portfolio unavailable or invalid. Import it with python3 -m cowingman.portfolio."
            ) from None

    def select(self, context):
        query = tokens(" ".join(turn.text for turn in context.turns))
        query = set().union(*(QUERY_ALIASES.get(word, {word}) for word in query))
        if not query:
            return ()
        indexed = [
            tokens(passage) | ({"introduction"} if passage.startswith("About Me:") else set())
            for passage in self.passages
        ]
        weights = {
            word: math.log(1 + len(indexed) / (1 + sum(word in words for words in indexed)))
            for word in query
        }
        ranked = []
        for index, (passage, words) in enumerate(zip(self.passages, indexed)):
            matched = words & query
            if not matched:
                continue
            # Favor a named project/role over a passing mention in another passage.
            title = tokens(passage.split(":", 1)[0])
            score = sum(weights[word] * (2 if word in title else 1) for word in matched)
            ranked.append((-score, index, passage))
        ranked.sort()
        return checked_selection([item[2] for item in ranked[:MAX_SELECTED_PASSAGES]])


class PortfolioHTML(HTMLParser):
    """Extract text blocks in main only, with their section, project, and role labels."""

    def __init__(self):
        super().__init__(convert_charrefs=True)
        self.in_main = False
        self.stack = []
        self.capture = None
        self.section = self.heading = self.organization = self.date = ""
        self.records = []

    def handle_starttag(self, tag, attrs):
        if tag in {
            "area",
            "base",
            "br",
            "col",
            "embed",
            "hr",
            "img",
            "input",
            "link",
            "meta",
            "param",
            "source",
            "track",
            "wbr",
        }:
            return
        self.stack.append(tag)
        if tag == "main":
            self.in_main = True
        if not self.in_main or self.capture:
            return
        attrs = dict(attrs)
        classes = set(attrs.get("class", "").split())
        kind = None
        if "section-heading" in classes:
            kind = "section"
        elif tag in {"h3", "h4"}:
            kind = "heading"
        elif "exp-org" in classes:
            kind = "organization"
        elif "exp-date" in classes:
            kind = "date"
        elif tag in {"p", "li"} or classes & {"exp-detail", "tags"}:
            kind = "text"
        if kind:
            self.capture = (len(self.stack), kind, [])

    def handle_data(self, data):
        if self.capture and not set(self.stack) & {"script", "style", "svg"}:
            self.capture[2].append(data)

    def handle_endtag(self, tag):
        if self.capture and len(self.stack) == self.capture[0]:
            _, kind, parts = self.capture
            text = " ".join(" ".join(parts).split())
            self.capture = None
            if kind == "section":
                self.section = text
                self.heading = self.organization = self.date = ""
            elif kind == "heading":
                self.heading = text
                self.organization = self.date = ""
            else:
                if kind in {"organization", "date"}:
                    setattr(self, kind, text)
                    # Role paragraphs already include employer and dates. Avoid
                    # spending both retrieval slots on redundant header fragments.
                prefix = " / ".join(
                    filter(None, (self.section, self.heading, self.organization, self.date))
                )
                passage = f"{prefix}: {text}"
                # Keep complete blocks and qualifications; never silently truncate a claim.
                # Contact lines are not needed for conversational recovery.
                keep = kind == "text" or (kind == "date" and self.section == "Education")
                if (
                    keep
                    and text
                    and len(passage) <= MAX_PASSAGE_CHARACTERS
                    and passage.isprintable()
                    and "@" not in text
                ):
                    self.records.append(passage)
        if tag == "main":
            self.in_main = False
        if self.stack and self.stack[-1] == tag:
            self.stack.pop()


class _NoRedirect(urllib.request.HTTPRedirectHandler):
    def redirect_request(self, *args, **kwargs):
        raise ValueError("Portfolio download redirected.")


def import_honey(output):
    """Explicit setup only; fetch four fixed public HTML files, never follow links."""
    records = []
    opener = urllib.request.build_opener(_NoRedirect())
    for page in PAGES:
        url = (
            f"https://raw.githubusercontent.com/honeyreddydaram/Portfolio/{SOURCE_REVISION}/{page}"
        )
        with opener.open(url, timeout=20) as response:
            data = response.read(MAX_FILE_BYTES + 1)
        if len(data) > MAX_FILE_BYTES:
            raise ValueError("Portfolio page exceeds the import limit.")
        parser = PortfolioHTML()
        parser.feed(data.decode("utf-8"))
        parser.close()
        records.extend({"text": text, "source": SOURCE_BASE + page} for text in parser.records)
    value = {
        "version": 1,
        "source_revision": SOURCE_REVISION,
        "imported_at": datetime.now(timezone.utc).isoformat(),
        "passages": records,
    }
    encoded = (json.dumps(value, ensure_ascii=True, indent=2) + "\n").encode()
    if not 1 <= len(records) <= MAX_PASSAGES or len(encoded) > MAX_FILE_BYTES:
        raise ValueError("Portfolio import exceeds its limits.")
    target = Path(output)
    target.parent.mkdir(parents=True, exist_ok=True)
    # Exclusive create prevents accidental overwriting of a reviewed/customized profile.
    with target.open("xb") as stream:
        target.chmod(0o600)
        stream.write(encoded)
    return len(records)


def main(argv=None):
    parser = argparse.ArgumentParser(description="Import Honey's public portfolio for local cues")
    parser.add_argument("--output", default="private/portfolio.json")
    args = parser.parse_args(argv)
    try:
        count = import_honey(args.output)
        print(f"Imported {count} portfolio passages locally. No NaviGator request was made.")
        print("Review the JSON locally, then launch with --portfolio followed by its path.")
        return 0
    except FileExistsError:
        print("Portfolio file already exists. Use a new --output path to import again.")
    except (OSError, ValueError):
        print("Portfolio import failed. Check network access and the output directory.")
    return 2


if __name__ == "__main__":
    raise SystemExit(main())
