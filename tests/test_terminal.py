"""Real pseudo-terminal exercise without exposing input/cue text in test logs."""

import os
import pty
import select
import signal
import subprocess
import sys
import termios
import time
import unittest


class TerminalIntegrationTests(unittest.TestCase):
    def test_hidden_input_visual_cue_and_interrupt_restores_terminal(self):
        master, slave = pty.openpty()
        original = termios.tcgetattr(slave)
        process = subprocess.Popen(
            [sys.executable, "-m", "cowingman", "--typed", "--offline"],
            stdin=slave,
            stdout=slave,
            stderr=slave,
        )
        captured = bytearray()

        def await_text(needle):
            deadline = time.monotonic() + 5
            while needle not in captured and time.monotonic() < deadline:
                if select.select([master], [], [], 0.1)[0]:
                    captured.extend(os.read(master, 8192))
            self.assertTrue(needle in captured, "Expected terminal state was not observed.")

        try:
            await_text(b"[ready]")
            self.assertFalse(termios.tcgetattr(slave)[3] & termios.ECHO)
            os.write(master, b"private terminal sentinel\n")
            await_text(b"accepted privately")
            os.write(master, b":cue\n")
            await_text(b"CUE:")
            self.assertFalse(b"private terminal sentinel" in captured)
            process.send_signal(signal.SIGINT)
            process.wait(timeout=5)
            self.assertEqual(process.returncode, 0)
            self.assertEqual(termios.tcgetattr(slave), original)
        finally:
            if process.poll() is None:
                process.kill()
                process.wait()
            os.close(master)
            os.close(slave)
            captured.clear()

    def test_partial_pipe_input_does_not_block_event_loop(self):
        from cowingman.ui import TerminalUI
        import io

        read_fd, write_fd = os.pipe()
        stream = os.fdopen(read_fd, "r")
        try:
            ui = TerminalUI(stdin=stream, stdout=io.StringIO())
            os.write(write_fd, b"partial private")
            started = time.monotonic()
            self.assertIsNone(ui.read_command(timeout=0.01))
            self.assertLess(time.monotonic() - started, 0.5)
            os.write(write_fd, b" fragment\n:cue\n")
            self.assertEqual(ui.read_command(), "partial private fragment")
            self.assertEqual(ui.read_command(), ":cue")
        finally:
            stream.close()
            os.close(write_fd)
