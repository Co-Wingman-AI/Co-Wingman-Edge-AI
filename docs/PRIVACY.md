# Data lifecycle and trust boundary

Default conversation mode has no persistence layer. Optional rolling/S3 mode
persists summaries as described below. A local worker captures four-second
windows of mono float32 audio in RAM, runs direct NVIDIA CTC tensor inference,
returns at most 240 text characters through local IPC, zeros its audio arrays,
and drops intermediate tensors. It does not use a file-based transcription API.
Speech workers suppress third-party stdout/stderr, disable IP socket creation,
and remove credential environment variables before loading models. This guards
against accidental library requests; it is not a hostile-code security sandbox.

Default mode retains at most four timestamped fragments / 800 characters.
Consecutive local-ASR windows may be combined only while the resulting fragment
remains at most 240 characters. Microphone fragments carry an `unknown` speaker
label because the application performs no diarization or identity inference.
Expired entries are removed in the event loop (normally within 0.1 seconds).
In default mode, a cue request stops the speech worker, takes and clears the store, and
submits only validated bounded text. A failed request also consumes the context.
The request subprocess enforces a wall-clock deadline, exits after the response,
and never follows redirects or environment proxies. The main process drops the
request context before display or TTS; it retains no response history. Only
content-free timing/count/schema metrics may enter optional benchmark reports.

With `--rolling`, capture runs in a separate local thread during inference. At
most one four-second window is being captured, one awaits inference, and one is
being processed (up to 12 seconds of raw samples in RAM). Older queued windows
are zeroed and discarded if processing falls behind, with an explicit gap notice.
Capture continues during cue requests; this mode does not permit TTS.
Recent text is capped at 15 fragments / 3,600 characters over 60 seconds and is
retained across cue requests. Network/model calls can delay main-loop cleanup;
timestamps are checked before reusing buffered speech.

Every active minute, a separate NaviGator request summarizes only the latest
rolling minute into at most 1,200 characters. The source text stays bounded at
3,600 characters. Summary quality is model-dependent; no complete transcript or
perfect recall is promised. The summary stays in RAM unless `--summary-s3` is
supplied. With that option, the configured private S3 prefix receives a summary
record with UTC window start/end, creation time, and a random session ID. A minute
object and latest pointer are written with SSE-S3 encryption. AWS credentials
use the normal local SDK chain, separately from the NaviGator key.

S3 records persist across exits until deleted through AWS or a bucket lifecycle
rule. `:forget` clears RAM only. `:save`, `:summary`, `:pause`, and normal `:quit`
can summarize/save a partial window; interruption does not make a final network
call. One failed upload is held in RAM for retry, not in a durable outbox. Outages
can produce missing intervals. `--resume-summary` explicitly reads a selected or
latest S3 record. Historical summary text is untrusted, fallible context; up to
1,200 characters accompany new cue requests. Combined rolling budgets are 3,600
recent + 1,200 summary + 1,200 optional portfolio characters per cue (6,000 total).
See [AWS setup and retrieval](AWS_SUMMARIES.md) for controls and verification.

An offered model response that fails only the word/character length limit can
receive one shortening request to the same approved endpoint and model. The
draft comes from a response JSON string capped at 1,024 characters and must pass
all other cue checks first. Only this bounded generated draft and its intent are
sent back; conversation fragments and portfolio passages are not resent. Both
calls share the configured timeout. No shortening occurs for refusals, unsafe or
malformed responses, or a false offer decision. Shortening output is fully checked
and never recursively repaired. Drafts are kept in memory for this operation,
dropped afterward, and excluded from logs and metrics; counts and a shortening
flag are permitted. These checks cannot guarantee preservation of meaning.

The optional portfolio feature explicitly imports public reference text into an
ignored local JSON file. This file persists until the operator deletes it; it is
not conversation history and is not subject to the conversation TTL. Using
`--portfolio` loads it locally and selects at most two 600-character passages for
each cue. The outbound boundary revalidates this 1,200-character fact budget in
addition to the selected conversation-mode budget (2,000 source-text characters
in default mode, excluding serialization and the fixed prompt). The full profile and its
source URLs are not sent. The importer is a separate setup command; conversational
retrieval has no website access. Facts are untrusted reference data, not system
instructions. Health checks and synthetic modes reject the portfolio option.
See [portfolio setup](PORTFOLIO.md) for the snapshot source and deletion controls.

“Full transcripts are not sent” means the application never builds or uploads a
transcript archive. A very short input may fit entirely into the bounded excerpt.
The system does not anonymize names within an excerpt. Use synthetic content for
presentations and obtain participants' consent for real use. Local TTL and deletion
do not establish deletion from UF infrastructure; consult institutional policy.

Typed input is capped at 2,048 characters before local suffix selection. `--typed`
shows input by default, including partner commands. `--hide-input` disables echo;
`--show-input` enables it in microphone mode. Visible text can remain in scrollback.
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

## Optional profiling, shadow scores and AWS portfolio storage

`--timings` explicitly persists local numeric measurements, UTC/monotonic timestamps
and fixed review markers in a new permission-0600 file. It records no transcripts,
cues, portfolio facts, credentials or exception bodies. Reports may reveal session
activity and are not automatically deleted or uploaded. Use ignored `private/` paths.

`--disfluency-shadow` keeps the pinned research model in the local speech worker,
with network access disabled. It uses CPU inference, stores only numeric scores
in the timing report, and never triggers cues, identifies speakers or infers anxiety.
Five-second classifier windows reuse four-second ASR captures plus a one-second
RAM tail. Temporary raw buffers are cleared after use; no recordings are written.
`:mark fluent/stuck/partner/quiet` records a fixed self-reported review marker only.

The explicit `cowingman.portfolio_cloud upload` command sends the whole validated
portfolio snapshot to your chosen private S3 prefix. It persists as a timestamped
archive and `portfolio.json` with SSE-S3 encryption. `--portfolio-s3` loads this
snapshot once at startup into RAM, validates the existing profile limits, and keeps
per-cue retrieval local with the same two-passage/1,200-character outbound limit.
S3 portfolio storage is independent of minute summaries; neither contains raw audio.
Saved objects remain until deleted or expired by your bucket's lifecycle policy.
