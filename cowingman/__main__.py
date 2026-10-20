"""One application entry point: python3 -m cowingman."""

import argparse
import signal
import sys

from .app import Application
from .config import Config, number
from .context import BoundedContext, ContextTurn
from .errors import CloudRequestError, ConfigurationError, SpeechError
from .provider import NavigatorClient, OfflineClient
from .speech import SpeechSession
from .ui import TerminalUI


def parser():
    result = argparse.ArgumentParser(description="Co-Wingman conversational recovery assistant")
    result.add_argument(
        "--typed", action="store_true", help="hidden typed input; no audio dependencies"
    )
    result.add_argument(
        "--offline", action="store_true", help="synthetic cue provider; no API or microphone"
    )
    result.add_argument(
        "--demo", action="store_true", help="run a synthetic end-to-end example and exit"
    )
    result.add_argument(
        "--health-check",
        action="store_true",
        help="real synthetic NaviGator request; no private text",
    )
    result.add_argument("--list-audio", action="store_true", help="list local input-device indices")
    result.add_argument("--tts", action="store_true", help="optional sequential local NVIDIA TTS")
    result.add_argument(
        "--pause-assist",
        action="store_true",
        help="opt in to pause-triggered cues on a personal microphone",
    )
    result.add_argument(
        "--speech-threshold", default="0.015", help="local speech energy threshold, 0.001–0.2"
    )
    return result


def main(argv=None):
    args = parser().parse_args(argv)
    if args.demo and not (args.offline or args.typed):
        parser().error("--demo requires --offline or --typed")
    if args.health_check and (args.offline or args.demo):
        parser().error("--health-check requires the real NaviGator provider")
    if args.pause_assist and (args.typed or args.offline):
        parser().error("--pause-assist requires a personal microphone in live mode")
    if args.offline and args.tts:
        parser().error("--offline uses visual output and no model dependencies")
    try:
        if args.list_audio:
            try:
                import sounddevice as sd

                found = False
                for index, device in enumerate(sd.query_devices()):
                    if device["max_input_channels"] > 0:
                        found = True
                        print(f"Input {index}: {device['name']}")
                if not found:
                    raise SpeechError("No microphone found. Connect a USB input or use --typed.")
            except SpeechError:
                raise
            except Exception:
                raise SpeechError(
                    "Audio devices unavailable. Install sounddevice/PortAudio and connect a USB microphone."
                ) from None
            return 0
        config = Config.load(offline=args.offline)
        threshold = number(args.speech_threshold, "Speech threshold", 0.001, 0.2)
        client = (
            OfflineClient()
            if args.offline
            else NavigatorClient(
                config.api_key,
                base_url=config.base_url,
                model=config.model,
                timeout_seconds=config.timeout_seconds,
            )
        )
        if args.health_check:
            context = BoundedContext.from_turns(
                [ContextTurn("partner", "Can you clarify the demonstration?")]
            )
            try:
                _cue, metrics = client.request_cue(context)
                _cue = None
                print(
                    f"NaviGator access OK; approved Nemotron returned a valid cue ({metrics['duration_seconds']:.2f}s)."
                )
            finally:
                context = None
                client.close()
            return 0
        audio = None if args.typed or args.offline else SpeechSession(config, threshold)
        with TerminalUI(input_ttl=config.context_ttl) as ui:
            ui.message(
                "Provider: "
                + ("OFFLINE synthetic mock" if args.offline else "UF NaviGator / NVIDIA Nemotron")
            )
            ui.message(
                "Audio: "
                + ("disabled" if audio is None else "local NVIDIA ASR; four-second capture windows")
            )
            ui.message(
                "TTS: "
                + (
                    "sequential local NVIDIA (ASR stopped first)"
                    if args.tts
                    else "visual cues only"
                )
            )
            application = Application(
                config, client, ui, audio=audio, tts=args.tts, pause_assist=args.pause_assist
            )
            application.run(demo=args.demo)
        return 0
    except (ConfigurationError, CloudRequestError, SpeechError) as exc:
        print(f"Error: {exc}", file=sys.stderr)
        return 2
    except (KeyboardInterrupt, EOFError):
        print("Stopped cleanly.")
        return 0
    except Exception:
        # A library exception can contain private text. Never show its repr/traceback.
        print(
            "Error: component unavailable. Check setup or restart with --typed --offline.",
            file=sys.stderr,
        )
        return 1


def _terminate(signum, frame):
    raise KeyboardInterrupt


if __name__ == "__main__":
    signal.signal(signal.SIGTERM, _terminate)
    signal.signal(signal.SIGINT, _terminate)
    raise SystemExit(main())
