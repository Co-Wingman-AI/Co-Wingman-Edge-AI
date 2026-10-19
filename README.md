# Co-Wingman

Co-Wingman is an independent research project for a privacy-conscious,
real-time conversational recovery assistant on an NVIDIA Jetson Orin Nano
8 GB. It helps an enrolled user request a short conversational cue when they
get stuck. It is not a medical diagnostic system and does not infer that
speech disfluency means anxiety.

## Production architecture

The production direction is hybrid and NVIDIA-only:

- Raw audio, voice activity detection, speaker attribution, ASR, and TTS run
  locally on the Jetson with NVIDIA speech/audio models.
- Only a small, locally selected, ephemeral text window may cross the cloud
  boundary.
- NVIDIA Nemotron cue generation runs through Nebius Token Factory.
- Raw audio and full transcripts must never be sent to the cloud.

Candidate local components remain NVIDIA MarbleNet for VAD, NVIDIA TitaNet
for speaker attribution, and Jetson-compatible NVIDIA NeMo/Riva ASR and TTS.
Those components are not installed or exercised by this milestone, and their
listing is not a Jetson compatibility claim.

## Current milestone

**Milestone 1, Step 3 — hybrid Nebius/NVIDIA Nemotron boundary** is implemented
and awaiting its Jetson report. It adds:

- a modular, dependency-free Nebius Token Factory client;
- enforced HTTPS Nebius endpoints and NVIDIA Nemotron model IDs;
- a bounded input contract of at most four text fragments, 240 characters per
  fragment, and 800 characters total;
- synthetic-only live benchmarking with JSON and Markdown reports that omit
  prompts, cue text, credentials, raw audio, and transcripts;
- unit tests and a mocked client integration test.

The returned Step 2 Jetson report did **not** pass its resource gate. During
local Nemotron inference it measured about 294 MiB minimum available RAM,
4.47 GiB maximum server RSS, and 361 MiB swap growth. That experiment is
retained as historical evidence, but local Nemotron is not the production
design. The hybrid Step 3 client does not start that local LLM server.

## Validate on macOS

No API key or network request is needed:

```sh
cd "/Volumes/Projects/Cowingman-jetson"
python3 -m unittest discover -s tests -v
python3 scripts/hybrid_nemotron_benchmark.py --dry-run --trials 3
```

The dry run writes timestamp-matched files under `reports/`. Generated reports
are ignored by Git until deliberately reviewed and force-added.

## Run the gate on Jetson

Create a Nebius Token Factory API key in your account. Export it only in the
current shell; do not write it into this repository or paste it into a report.

### Check the reported 99% RAM use first

Linux normally uses otherwise-idle RAM for reclaimable filesystem cache, so a
"99% used" display does not by itself prove that the Jetson is out of memory.
Jetson CPU and GPU workloads also share physical RAM. Run these read-only
checks while the Jetson is otherwise idle:

```sh
free -h
grep -E 'MemTotal|MemFree|MemAvailable|Buffers|Cached|SwapTotal|SwapFree' /proc/meminfo
ps -eo pid,comm,rss,%mem --sort=-rss | head -15
tegrastats --interval 1000
```

Let `tegrastats` run for about 10 seconds, then press Ctrl-C.

The Step 2 report's near-99% reading occurred while the local Nemotron server
was loaded and was accompanied by low `MemAvailable` and growing swap. That
was real workload pressure, not merely an idle cache reading. Memory used by
that process should be released after the benchmark terminates; the following
idle snapshot checks whether it was released.

- If `MemAvailable` is at least about 1 GiB and swap use is stable, the high
  percentage is probably largely reclaimable cache. The Step 3 cloud client
  itself uses little memory and does not run a local AI model.
- If `MemAvailable` is below 1 GiB while idle, stop and identify the largest
  process before running the gate.
- If swap usage keeps increasing, stop: the device is under real memory
  pressure.
- If one process dominates RSS, identify why it is running before terminating
  or disabling anything. Do not use `drop_caches`, `swapoff`, or disable
  services blindly.
- A reboot can clear temporary processes and cache, but it is not a fix for a
  persistent service or memory leak.

Return the output of these checks along with the two benchmark reports. This
RAM snapshot does not establish that the later concurrent local NVIDIA speech
pipeline will fit; that requires a separate milestone.

### Run the synthetic text gate

```sh
cd "/path/to/Co-Wingman-jetson"
python3 -m unittest discover -s tests -v
read -rsp "Nebius API key: " NEBIUS_API_KEY && printf '\n'
export NEBIUS_API_KEY
python3 scripts/hybrid_nemotron_benchmark.py --live --trials 3
unset NEBIUS_API_KEY
```

Return the matching files printed by the command:

- `reports/hybrid_nemotron_YYYYMMDD_HHMMSS.json`
- `reports/hybrid_nemotron_YYYYMMDD_HHMMSS.md`

Stop at this gate. Do not begin audio capture or install speech models until
the report is reviewed. See [RUN_ON_JETSON.md](RUN_ON_JETSON.md) for the exact
transfer and verification procedure and
[docs/milestones/milestone1_step3.md](docs/milestones/milestone1_step3.md) for
the decision record and acceptance criteria.

## Repository privacy

The intended GitHub repository is private. `.gitignore` excludes credentials,
model weights, recordings, transcripts, logs, and generated reports. Always
review a report before deliberately adding it to version control.
