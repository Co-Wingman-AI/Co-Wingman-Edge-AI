# Run Milestone 1 Step 3 on the Jetson

This gate sends three short **synthetic text** requests to NVIDIA Nemotron
through Nebius Token Factory. It does not open a microphone, read a recording,
run a local model, install packages, or send raw audio/full transcripts. It
does require Internet access and may incur a small Token Factory charge.

## 1. Validate on the Mac before moving the drive

```sh
cd "/Volumes/Projects/Cowingman-jetson"
python3 -m unittest discover -s tests -v
python3 scripts/hybrid_nemotron_benchmark.py --dry-run --trials 3
```

The test run must finish with `OK`. The dry-run report must say `not_run`; it
validates configuration and report generation without calling Nebius.

Close files and terminals using the project. In Finder, eject the USB drive
and wait for it to disappear before disconnecting it.

## 2. Locate the project on Jetson Linux

Connect the drive and identify its actual mount path:

```sh
lsblk -f
findmnt
```

Replace `/path/to/Co-Wingman-jetson` below with that path. Do not copy the
placeholder literally.

## 3. Run local tests on the Jetson

```sh
cd "/path/to/Co-Wingman-jetson"
python3 -m unittest discover -s tests -v
```

This project step uses only the Python standard library; do not create a
virtual environment or install packages for it.

## 4. Supply the API key without saving it

Create the API key in Nebius Token Factory. Enter it silently into the current
shell and verify only that a value exists—never print the value:

```sh
read -rsp "Nebius API key: " NEBIUS_API_KEY && printf '\n'
export NEBIUS_API_KEY
test -n "$NEBIUS_API_KEY" && echo "NEBIUS_API_KEY is set"
```

Do not put the key in `.env`, shell history, source files, reports, or Git.

## 5. Run the live synthetic benchmark

```sh
python3 scripts/hybrid_nemotron_benchmark.py --live --trials 3
unset NEBIUS_API_KEY
```

The defaults are:

- endpoint: `https://api.tokenfactory.us-central1.nebius.com/v1`
- model: `nvidia/nvidia-nemotron-3-nano-30b-a3b`
- request timeout: 20 seconds
- acceptance latency: every request at or below 5 seconds

The script exits `0` on a pass and `1` on a completed failed gate. A missing
key or invalid configuration exits `2`. Regardless of success or failure after
requests begin, inspect the timestamp-matched report pair printed by the
script.

## 6. Inspect and return the reports

```sh
ls -lh reports/hybrid_nemotron_*.md reports/hybrid_nemotron_*.json
python3 -m json.tool reports/hybrid_nemotron_YYYYMMDD_HHMMSS.json >/dev/null
sed -n '1,220p' reports/hybrid_nemotron_YYYYMMDD_HHMMSS.md
```

Replace the timestamp placeholder with the exact timestamp printed by the
benchmark. Return both matching files:

- `reports/hybrid_nemotron_YYYYMMDD_HHMMSS.json`
- `reports/hybrid_nemotron_YYYYMMDD_HHMMSS.md`

The report intentionally excludes prompts, responses, credentials, raw audio,
and transcripts. Still review it before sharing or committing it.

## 7. Safely remove the drive and stop

```sh
cd /
sync
udisksctl unmount -b /dev/<usb-partition>
udisksctl power-off -b /dev/<usb-device>
```

Resolve both device placeholders with `lsblk -f`; never guess. If
`udisksctl` is unavailable, use the desktop file manager's eject control.
Wait for confirmation before disconnecting the drive.

**Milestone gate:** stop here and return the two reports. Do not install or run
Jetson speech/audio models yet.
