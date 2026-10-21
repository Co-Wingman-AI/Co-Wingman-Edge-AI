# Data lifecycle and trust boundary

Conversation data has no persistence layer. A local worker captures up to four
seconds of mono float32 audio in RAM, runs direct NVIDIA CTC tensor inference,
returns at most 240 text characters through local IPC, zeros its audio arrays,
and drops intermediate tensors. It does not use a file-based transcription API.
Speech workers suppress third-party stdout/stderr, disable IP socket creation,
and remove credential environment variables before loading models. This guards
against accidental library requests; it is not a hostile-code security sandbox.

The main process retains at most four timestamped fragments / 800 characters.
Consecutive local-ASR windows may be combined only while the resulting fragment
remains at most 240 characters. Microphone fragments carry an `unknown` speaker
label because the application performs no diarization or identity inference.
Expired entries are removed in the event loop (normally within 0.1 seconds).
A cue request stops the speech worker, atomically takes and clears the store, and
submits only validated bounded text. A failed request also consumes the context.
The request subprocess enforces a wall-clock deadline, exits after the response,
and never follows redirects or environment proxies. The main process drops the
request context before display or TTS; it retains no response history. Only
content-free timing/count/schema metrics may enter optional benchmark reports.

The optional portfolio feature explicitly imports public reference text into an
ignored local JSON file. This file persists until the operator deletes it; it is
not conversation history and is not subject to the conversation TTL. Using
`--portfolio` loads it locally and selects at most two 600-character passages for
each cue. The outbound boundary revalidates this 1,200-character fact budget in
addition to the 800-character conversation budget (2,000 source-text characters
total, excluding serialization and the fixed prompt). The full profile and its
source URLs are not sent. The importer is a separate setup command; conversational
retrieval has no website access. Facts are untrusted reference data, not system
instructions. Health checks and synthetic modes reject the portfolio option.
See [portfolio setup](PORTFOLIO.md) for the snapshot source and deletion controls.

“Full transcripts are not sent” means the application never builds or uploads a
transcript archive. A very short input may fit entirely into the bounded excerpt.
The system does not anonymize names within an excerpt. Use synthetic content for
presentations and obtain participants' consent for real use. Local TTL and deletion
do not establish deletion from UF infrastructure; consult institutional policy.

Typed input is hidden and capped at 2,048 characters before local suffix selection.
Cue text is terminal UI output, not a log: it is suppressed when redirected and
cleared from the active line after 20 seconds. Screen recording, terminal session
recorders, scrollback capture, and audible TTS can preserve the cue. Never use
shell tracing (`set -x`) when setting keys. Environment secrets remain in the
operator's shell until unset; a running process necessarily holds its credentials.

Python string/reference deletion and process exit do not guarantee forensic
zeroization. OS swap, system crash dumps, and external tracing are outside the
application's control. Production confidentiality depends on a trusted device
and an appropriate OS/storage policy. Model checkpoints and their extraction
artifacts are setup data; only official NVIDIA archives produced by the setup
script should be used. SHA-256 manifests detect accidental changes, not malicious
replacement of both archive and manifest by someone who controls the device.

The schema rejects excess fields, duplicate keys, long text, controls, URLs,
markup, and several unsafe patterns. This is conservative validation, not proof
of semantic safety or correctness. Cues can be unhelpful; the user decides whether
to use them. The app never treats pauses, word choice, or disfluency as a diagnosis.
