# Presentation runbook

## Before presenting

Use synthetic conversation content and a consenting operator. Open a terminal,
activate the prepared Jetson environment, and export the key and ASR archive path
as described in [RUN_ON_JETSON.md](../RUN_ON_JETSON.md). Confirm:

```sh
python3 -m unittest discover -s tests -q
python3 -m cowingman --offline --demo
python3 -m cowingman --health-check
python3 -m cowingman --list-audio
free -h
```

Use visual output, a USB headset microphone, and the manual cue trigger for the
most predictable presentation. Ensure no local LLM server is consuming RAM.
Keep the typed and offline commands below ready in a second terminal. Each shell
needs its own exported key; never paste the key into a command or a screen share.

## Normal live demonstration

```sh
python3 -m cowingman
```

1. Explain that microphone audio is processed locally and only a bounded excerpt
   can leave the device after a cue request.
2. Wait for `[listening]`, then say: “I would like to explain how our project
   protects conversation privacy.” Allow a capture window and transcription.
3. Press Enter or type `:cue`. Show `[requesting a cue]` and the short cue.
4. Explain that the microphone is now paused and the request context discarded.
   Enter `:listen` to capture a fresh example.
5. Enter `:quit` or press Ctrl-C. Show the clean shutdown message.

Input text is hidden; it is normal not to see typed commands. Do not redirect
stdout when demonstrating the cue: redirected output intentionally suppresses it.
Use `:clear` to remove context/display and stop microphone processing immediately.

## Typed live fallback

```sh
python3 -m cowingman --typed
```

Type a short synthetic fragment, Enter to accept, then `:cue`. This uses the real
NaviGator provider but no microphone or speech models. For a self-contained live
synthetic example: `python3 -m cowingman --typed --demo`.

## Offline fallback

```sh
python3 -m cowingman --offline --demo
python3 -m cowingman --typed --offline
```

The first runs one complete synthetic example; the second accepts interactive
hidden input. Clearly state that the response is deterministic and mocked. It
exercises context selection, request construction, schema validation, display,
and cleanup, but it does not demonstrate model quality or live connectivity.

## Recover from failures

- **Network/API error:** no automatic retries; failed context is discarded. Check
  the key/model permission or wait after a rate limit. Add fresh context before
  retrying. If service remains unavailable, exit and use the offline fallback.
- **Microphone error:** type a fragment in the same application and request a cue,
  or restart with `--typed`. Reconnect the headset, check `--list-audio`, and use
  `:listen` to resume capture.
- **Low RAM/model error:** keep visual output and switch to typed input. Inspect
  `free -h` and `tegrastats`. Do not start a local LLM or force new dependencies
  onto the Jetson during the presentation.
- **TTS error:** use the visual cue. TTS is optional and is not a prerequisite.
- **Unexpected automatic cue:** enter `:assist off`. Use Enter or `:cue` instead.
- **Interrupted session:** Ctrl-C or `:quit` releases the child processes; relaunch
  the application. Context is not restored across sessions.

## Accurate claims

Audio is local; there are no application-created recordings or transcript files.
The API input contains at most four recent fragments, 240 characters each and
800 characters total. The store expires and is cleared on request or exit; the
application does not log prompts, transcripts, credentials, or generated cues.
UF still receives the bounded text; its server-side retention is not controlled
by this application. Visible/audible cues and OS-level capture remain observable.

Do not claim medical diagnosis, anxiety/stress recognition, biometric enrollment,
speaker verification, uninterrupted streaming ASR, or measured Jetson performance
unless separately demonstrated. Optional pause assistance is only an energy and
silence heuristic. A short conversation can fit inside a selected excerpt; the
bound is a maximum disclosure limit, not a guarantee that every input omits words.
