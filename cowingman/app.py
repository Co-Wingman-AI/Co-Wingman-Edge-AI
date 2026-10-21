"""Application orchestration, explicit triggers, and ephemeral cue lifecycle."""

from __future__ import annotations

import time

from .context import RollingContext
from .errors import CloudRequestError, PrivacyBoundaryError, SpeechError
from .speech import speak


class Application:
    def __init__(
        self,
        config,
        client,
        ui,
        *,
        audio=None,
        tts=False,
        pause_assist=False,
        speaker=speak,
        clock=time.monotonic,
    ):
        self.config = config
        self.client = client
        self.ui = ui
        self.audio = audio
        self.tts = tts
        self.pause_assist = pause_assist
        self.speaker = speaker
        self.clock = clock
        self.context = RollingContext(config.context_ttl, clock)
        self.last_request = -30.0
        self.closed = False
        self.pending_resume = False

    def start_audio(self):
        if self.audio is None:
            self.ui.message("Audio is disabled in typed mode.")
            return
        try:
            self.ui.status("loading local ASR")
            self.audio.start()
        except SpeechError as exc:
            self.ui.status("error")
            self.ui.message(str(exc))
            self.ui.message("You can still type a short fragment and press Enter, then :cue.")

    def add(self, text, speaker="user"):
        try:
            self.context.add(text, speaker)
            self.ui.status("ready")
            self.ui.message("Recent fragment accepted privately. Enter or :cue requests a cue.")
        except PrivacyBoundaryError as exc:
            self.ui.message(str(exc))

    def request_cue(self):
        self.pending_resume = False
        had_audio = self.audio is not None and self.audio.process is not None
        # Free all audio/model state, even on a network failure; no stale chunks.
        if self.audio is not None:
            self.audio.close()
        context = cue = None
        presented = False
        try:
            context = self.context.take()
            self.last_request = self.clock()
            self.ui.status("requesting a cue")
            cue, _metrics = self.client.request_cue(context)
            context = None  # Drop request text before presenting or synthesizing.
            if "portfolio_passages" in _metrics:
                self.ui.message(
                    f"Portfolio: {_metrics['portfolio_passages']} reference passages supplied."
                )
            self.ui.status("ready")
            self.ui.show_cue(cue)
            presented = True
            if self.tts and cue.should_offer:
                try:
                    self.speaker(cue.cue, self.config)
                except SpeechError as exc:
                    self.ui.message(str(exc))
                    self.ui.show_cue(cue)
        except PrivacyBoundaryError:
            self.ui.message("No recent context. Speak or type a short fragment first.")
        except CloudRequestError as exc:
            self.ui.status("error")
            self.ui.message(str(exc))
            self.ui.message("Context discarded. Add new context before retrying.")
        finally:
            self.context.clear()
            context = cue = None
        if had_audio:
            # Wait for explicit resume so the display remains visible and a speaker
            # cannot feed the generated cue back into the microphone.
            self.pending_resume = True
            if not presented:
                self.ui.message("Microphone paused. Use :listen before speaking again.")
            # Do not print over the visual cue; commands are in the startup help.

    def tick(self):
        self.context.expire()
        self.ui.tick()
        if self.audio is None:
            return
        for kind, value in self.audio.poll():
            if kind == "fragment":
                try:
                    # A personal microphone may capture either participant. NeMo
                    # does not identify speakers, so never label ASR as the user.
                    # Merge adjacent windows when bounded space allows so a
                    # question is less likely to fall out of the four-turn store.
                    self.context.add(value, "unknown", merge=True)
                    if len(self.context):
                        self.ui.message(
                            "Speech fragment accepted privately (speaker not identified). "
                            "Press Enter or :cue for a cue."
                        )
                except PrivacyBoundaryError:
                    self.context.clear()
                    self.audio.close()
                    self.ui.status("error")
                    self.ui.message(
                        "Local speech returned unsupported text. Audio stopped; "
                        "type a fresh fragment or use :listen to retry."
                    )
                    break
            elif kind == "empty_fragment":
                self.ui.message(
                    "No words recognized in this window. "
                    "Try a short clear phrase or type a fragment."
                )
            elif kind == "status":
                self.ui.status(value)
            elif kind == "error":
                self.context.clear()
                self.ui.status("error")
                self.ui.message(value)
            elif kind == "pause" and self.pause_assist and len(self.context):
                if self.clock() - self.last_request >= 30:
                    self.ui.message("Possible conversational pause. Requesting an optional cue.")
                    self.request_cue()
                    break
        value = None

    def command(self, line):
        if line == ":quit":
            return False
        if line in {"", ":cue"}:
            self.request_cue()
        elif line == ":clear":
            if self.audio:
                self.audio.close()
            self.context.clear()
            self.ui.clear_cue()
            self.ui.message("Context cleared; microphone stopped. Use :listen to resume.")
        elif line == ":listen":
            self.pending_resume = False
            self.start_audio()
        elif line == ":pause":
            if self.audio:
                self.audio.close()
            self.context.clear()
            self.ui.status("paused")
        elif line in {":assist on", ":assist off"}:
            self.pause_assist = line.endswith(" on")
            self.ui.message(
                "Pause assistance "
                + ("on (personal microphone only)." if self.pause_assist else "off.")
            )
        elif line.startswith(":partner "):
            self.add(line[len(":partner ") :], "partner")
        elif line == ":check":
            self.check_context()
        elif line.startswith(":"):
            self.ui.message(
                "Commands: :cue, :check, :listen, :pause, :clear, :assist on/off, :quit."
            )
        else:
            self.add(line)
        return True

    def check_context(self):
        """Local count-only check; never print text, call the API, or refresh TTL."""
        window = None
        try:
            window = self.context.snapshot()
            counts = {
                role: sum(t.speaker == role for t in window.turns)
                for role in ("partner", "user", "unknown")
            }
            self.ui.message(
                f"Context: {counts['partner']} typed partner, {counts['user']} typed user, "
                f"{counts['unknown']} microphone fragments."
            )
            portfolio = getattr(self.client, "portfolio", None)
            if portfolio is not None:
                self.ui.message(f"Portfolio: {len(portfolio.select(window))} matching passages.")
            self.ui.message("Local check only; no API request made. Context expiry unchanged.")
        except PrivacyBoundaryError:
            self.ui.message("No recent context. Add a short fragment before :check.")
        finally:
            window = None

    def run(self, *, demo=False):
        try:
            self.ui.message("Co-Wingman | local audio · bounded text · explicit recovery cues")
            self.ui.message("Input is hidden. Type a short fragment, Enter; then Enter or :cue.")
            self.ui.message(
                ":check shows local context counts and portfolio matches without an API call."
            )
            self.ui.message(
                ":listen resumes audio after a cue; :pause stops it; :clear erases context; :quit exits."
            )
            self.ui.message(
                "Cue display expires after 20 seconds. Pause assistance is not a stress detector."
            )
            self.ui.status("ready")
            if demo:
                self.add("Which part of the project should we demonstrate?", "partner")
                self.add("I would like to explain the privacy design.")
                self.request_cue()
                # Keep a real terminal's synthetic cue visible briefly.
                if getattr(self.ui, "_terminal", False):
                    end = self.clock() + 5
                    while self.clock() < end:
                        self.ui.tick()
                        time.sleep(0.1)
                return
            if self.audio is not None:
                self.start_audio()
            while True:
                self.tick()
                line = self.ui.read_command()
                if line is not None:
                    keep_running = self.command(line)
                    line = None
                    if not keep_running:
                        break
        finally:
            self.close()

    def close(self):
        if self.closed:
            return
        self.closed = True
        try:
            if self.audio is not None:
                self.audio.close()
        finally:
            self.context.clear()
            self.client.close()
            self.ui.clear_cue()
            self.ui.status("stopped; temporary context discarded")
