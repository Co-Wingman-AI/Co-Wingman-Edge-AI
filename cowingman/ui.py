"""Terminal presentation with explicit input visibility and private redirected output."""

from __future__ import annotations

import os
import select
import textwrap
import sys
import time


class TerminalUI:
    def __init__(self, stdin=None, stdout=None, input_ttl=60.0, visible_input=False):
        self.input = sys.stdin if stdin is None else stdin
        self.output = sys.stdout if stdout is None else stdout
        self._terminal = self.output.isatty()
        self._saved = None
        self._cue_until = 0.0
        self._status = None
        self._input_buffer = bytearray()
        self._discard_line = False
        self._eof = False
        self._cue_lines = 0
        self._cue_input_lines = 0
        self._input_ttl = input_ttl
        self._input_until = 0.0
        self.visible_input = visible_input

    def __enter__(self):
        if self.input.isatty():
            import termios

            self._saved = termios.tcgetattr(self.input.fileno())
            hidden = termios.tcgetattr(self.input.fileno())
            if self.visible_input:
                hidden[3] |= termios.ECHO
            else:
                hidden[3] &= ~(termios.ECHO | termios.ECHONL)
            termios.tcsetattr(self.input.fileno(), termios.TCSANOW, hidden)
        return self

    def __exit__(self, *args):
        self.clear_cue()
        self._input_buffer.clear()
        if self._saved is not None:
            import termios

            termios.tcsetattr(self.input.fileno(), termios.TCSANOW, self._saved)

    def message(self, message):
        self.clear_cue()
        print(message, file=self.output, flush=True)

    def show_summary(self, summary):
        self.message(
            "Summary: " + (summary or "No summary yet.")
            if self._terminal
            else "Summary display suppressed on redirected output."
        )

    def status(self, state):
        if state != self._status:
            self._status = state
            self.message(f"[{state}]")

    def show_cue(self, cue):
        self.clear_cue()
        if not cue.should_offer:
            self.message("No cue offered. Add recent context and try again.")
        elif self._terminal:
            try:
                columns = os.get_terminal_size(self.output.fileno()).columns
            except (OSError, ValueError):
                columns = 80
            # Leave room for the label and for wide Unicode characters. Explicit
            # newlines let us erase every rendered line, including on small screens.
            lines = textwrap.wrap(cue.cue, width=max(5, (columns - 9) // 2))
            self._cue_lines = len(lines)
            self.output.write("\r\033[2K  CUE: " + "\n       ".join(lines))
            if self.visible_input:
                self.output.write("\n")
                self._cue_input_lines = 0
            self.output.flush()
            self._cue_until = time.monotonic() + 20
        else:
            self.message("Cue validated (private display suppressed on redirected output).")

    def clear_cue(self):
        if self._cue_until:
            if self.visible_input:
                # Keep an in-progress visible input line intact when a cue expires.
                self.output.write("\0337")
                if self._cue_input_lines:
                    self.output.write(f"\033[{self._cue_input_lines}A")
                for _ in range(self._cue_lines):
                    self.output.write("\033[1A\r\033[2K")
                self.output.write("\0338")
            else:
                self.output.write("\r\033[2K")
                for _ in range(self._cue_lines - 1):
                    self.output.write("\033[1A\r\033[2K")
            self.output.flush()
            self._cue_until = 0.0
            self._cue_lines = 0

    def tick(self):
        if self._input_buffer and time.monotonic() >= self._input_until:
            self._input_buffer.clear()
            self._discard_line = True
        if self._cue_until and time.monotonic() >= self._cue_until:
            self.clear_cue()

    def read_command(self, timeout=0.1):
        # Read bounded bytes, never blocking on readline after select: a pipe may
        # contain an unfinished line, and idle context must still expire.
        if b"\n" not in self._input_buffer and not self._eof:
            if not select.select([self.input], [], [], timeout)[0]:
                return None
            data = os.read(self.input.fileno(), 4096)
            self._eof = not data
            self._input_buffer.extend(data)
            if data:
                self._input_until = time.monotonic() + self._input_ttl
        if b"\n" in self._input_buffer:
            end = self._input_buffer.index(b"\n")
            value = bytes(self._input_buffer[:end])
            del self._input_buffer[: end + 1]
        elif self._eof:
            if not self._input_buffer:
                return ":quit"
            value = bytes(self._input_buffer)
            self._input_buffer.clear()
        else:
            if len(self._input_buffer) > 8192 or self._discard_line:
                self._input_buffer.clear()
                self._discard_line = True
            return None
        if self._discard_line:
            self._discard_line = False
            self.message("Input too long. Enter a short recent fragment.")
            return None
        try:
            text = value.decode("utf-8")
        except UnicodeError:
            self.message("Input must be text in UTF-8.")
            return None
        if self.visible_input and self._cue_until:
            try:
                columns = os.get_terminal_size(self.output.fileno()).columns
            except (OSError, ValueError):
                columns = 80
            self._cue_input_lines += 1 + len(text) // max(1, columns)
        if len(text) > 2048:
            self.message("Input too long. Enter a short recent fragment.")
            return None
        return text.strip()
