# Rolling conversation and timestamped AWS summaries

`--rolling` keeps up to 60 seconds of recent text (15 fragments, 240 characters
each, 3,600 total), while the local microphone captures four-second windows.
Cues are requested with Enter/`:cue`, or after a pause with `--pause-assist`.
Four seconds is the capture window, not a required silence or API request interval.
Listening continues after cues. Use `:pause` to stop and `:listen` to resume.
This mode uses visual cues; it cannot be combined with TTS.

Every minute with new recognized text, NaviGator summarizes the latest rolling
window into at most 1,200 characters. Only the summary and metadata are uploaded
to S3. Each JSON record contains version, random session ID, UTC window start/end,
creation time, and summary. It contains no raw audio or transcript field.
The app writes a timestamped `windows/` object and a `latest.json` object.
Use a separate prefix per device/user; `latest.json` is last-writer-wins.

A summary is lossy and model-generated. It cannot retain every detail or establish
speaker identity. Recognition errors and slow processing can cause omissions.
Summary requests add one NaviGator call per active minute. Cue requests and any
length-repair call are separate. Scheduling and recognition/network latency can
delay uploads: this is not an exact real-time or gap-free archive.

## Create the destination

The application does not create AWS accounts, buckets, or credentials.

1. Sign in to your AWS account and open **S3 → Create bucket**.
2. Select a region, for example **US East (N. Virginia), us-east-1**, and a unique
   general-purpose bucket name. Record the name and region.
3. Keep **Block all public access** enabled, ACLs disabled, and default SSE-S3
   encryption. Create the bucket. This application requests SSE-S3 on writes.
4. Give the identity used by the Jetson only `s3:PutObject` and `s3:GetObject` for
   its prefix. For example, attach this policy to a dedicated IAM identity,
   replacing `YOUR_BUCKET` with the actual bucket name:

```json
{
  "Version": "2012-10-17",
  "Statement": [{
    "Effect": "Allow",
    "Action": ["s3:PutObject", "s3:GetObject"],
    "Resource": "arn:aws:s3:::YOUR_BUCKET/cowingman/jetson/*"
  }]
}
```

Configure the identity through AWS CLI on the Jetson. If you already use IAM
Identity Center, use your existing SSO profile and `aws sso login --profile cowingman`.
Otherwise, use a dedicated IAM user's access key and enter it locally with
`aws configure --profile cowingman`. Do not use account-root credentials or put
keys in this repository or chat. Install AWS CLI if needed using its official
Linux ARM installer, or your distribution's package manager.

```bash
aws configure --profile cowingman
export AWS_PROFILE=cowingman
aws sts get-caller-identity
python3 -m pip install -e '.[cloud]'
```

The app uses boto3's normal AWS credential chain. It does not request keys as
conversation input, embed them in summaries, or upload them to NaviGator.

## Run and verify

Replace `YOUR_BUCKET` and the example region before running:

```bash
export AWS_PROFILE=cowingman
python3 -m cowingman --portfolio private/portfolio.json --rolling --pause-assist \
  --show-input --summary-s3 s3://YOUR_BUCKET/cowingman/jetson --aws-region us-east-1
```

For visible manual testing, replace `--pause-assist` with `--typed`.
Without a bucket yet, omit `--summary-s3` and `--aws-region`: rolling conversation
and summary updates work, but summaries stay only in RAM and disappear on exit.
`--typed` now shows entered text by default; `--hide-input` restores hidden entry.
`--show-input` makes typed commands visible during microphone testing as well.
Visible input may remain in terminal scrollback.

| Command | Behavior |
| --- | --- |
| `:check` | Local context/summary counts; no cloud request |
| `:summary` | Update the current summary, save if S3 is configured, and display it on a terminal |
| `:save` | Update/save the current window, including a partial minute |
| `:clear` | Clear recent fragments and stop the microphone; keep the last summary |
| `:forget` | Clear in-memory summary/recent text; S3 records remain |
| `:quit` | Attempt to save the latest partial window, then exit |

After a minute of conversation, inspect `cowingman/jetson/windows/` in S3 or check:

```bash
aws s3api head-object --bucket YOUR_BUCKET --key cowingman/jetson/latest.json --profile cowingman
```

Failures are reported without cloud error bodies or conversation text. One failed
upload is retained in RAM and retried on `:save` or the next minute; it is not a
durable offline queue. An unresolved outage can leave gaps. Ctrl-C/termination
does not make a final network call and can lose unsaved RAM data. Objects already
saved in S3 remain until you delete them or apply your own bucket lifecycle rule.

## Reuse a saved summary

Add `--resume-summary` to the same launch command to load `latest.json`. To load
an older window, copy its relative key from the S3 console:

```text
--resume-summary windows/2026-01-01T00-01-00.000Z-SESSION_ID.json
```

Loaded summaries are historical context, not verified personal facts. Up to
1,200 summary characters can accompany a new cue request to NaviGator alongside
the fresh window and optional portfolio passages. Minute archives themselves
summarize only their own window; earlier summaries are not recursively copied
into every archived record. This is explicit record reuse, not automatic search
across all past conversations. `:summary` displays private text only on a terminal.

The integration has mocked AWS tests. A real bucket, Jetson credentials, and a
live end-to-end upload/reload test are still required for deployment verification.
