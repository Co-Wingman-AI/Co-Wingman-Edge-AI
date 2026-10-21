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
The separate optional setup script below can create a new bucket; normal app startup
never creates or changes bucket configuration.

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

## Command-line setup and portfolio upload

If you prefer commands to the S3 console, run these on the Jetson in your existing
virtual environment. AWS CLI must be installed first; on Ubuntu you can use
`sudo apt-get update` followed by `sudo apt-get install -y awscli`.
Use an IAM identity or SSO profile, not account-root access keys. The setup identity
needs permission to create a bucket and configure ownership, public access blocking
and encryption. A runtime identity needs only the prefix policy shown above.

```bash
python3 -m pip install -e '.[cloud]'
aws configure --profile cowingman
export AWS_PROFILE=cowingman
aws sts get-caller-identity
```

Enter credentials locally when AWS CLI asks. If you already use SSO, skip
`aws configure` and log in with your configured SSO profile instead. Do not paste
credentials or configuration-file contents into chat. Choose an unused bucket name;
the following derives a name from your account and region, without displaying keys:

```bash
export COWINGMAN_AWS_REGION=us-east-1
export COWINGMAN_BUCKET="cowingman-$(aws sts get-caller-identity --query Account --output text)-${COWINGMAN_AWS_REGION}"
python3 scripts/setup_s3_bucket.py --bucket "$COWINGMAN_BUCKET" --region "$COWINGMAN_AWS_REGION"
```

The script refuses an existing bucket, creates a new bucket with ACLs disabled,
blocks public access, and sets SSE-S3 encryption. It prints the restricted runtime
IAM policy for attachment through IAM. It does not create users/access keys or
grant permissions. If the derived name is taken, set `COWINGMAN_BUCKET` to another
unique name and retry. If you already created the bucket, set the two variables to
its name and region and skip the setup script. Select the restricted runtime profile
before ongoing use if setup used a different administrative identity.

Upload the existing local portfolio explicitly, then verify it can be loaded:

```bash
python3 -m cowingman.portfolio_cloud upload --portfolio private/portfolio.json \
  --s3 "s3://$COWINGMAN_BUCKET/cowingman/jetson" --aws-region "$COWINGMAN_AWS_REGION"
python3 -m cowingman.portfolio_cloud check \
  --s3 "s3://$COWINGMAN_BUCKET/cowingman/jetson" --aws-region "$COWINGMAN_AWS_REGION"
```

Each upload stores validated passages, a format version and UTC creation time in a
timestamped `portfolios/` archive and `portfolio.json`. It does not include conversation
text or audio. Both writes request encryption and no public ACL. Archive plus latest
writes are not a transaction; retry an explicitly failed upload. S3 keeps saved files
until you delete them or apply a lifecycle policy.

Reuse the AWS portfolio along with minute summaries:

```bash
python3 -m cowingman --rolling --pause-assist --show-input \
  --portfolio-s3 "s3://$COWINGMAN_BUCKET/cowingman/jetson" \
  --summary-s3 "s3://$COWINGMAN_BUCKET/cowingman/jetson" \
  --aws-region "$COWINGMAN_AWS_REGION" --timings private/aws-run-01.jsonl
```

`--portfolio-s3` replaces `--portfolio`; do not use both. It loads `portfolio.json`
once at startup into RAM, with the same 256 KB / 256-passage validation as local
files. Selection stays local and still supplies at most two passages / 1,200
characters to NaviGator per cue. No S3 request occurs for each portfolio lookup.
A failed startup download stops startup with a clear error rather than silently
using an old portfolio. Re-upload after changing your local portfolio, then restart
to load the updated copy. This is separate from summary history and speaker identity.

The whole validated portfolio snapshot now persists in AWS when you run the upload
command. The default app still uses no AWS portfolio and performs no automatic upload.
Follow [profiling and shadow testing](PROFILING_AND_SHADOW.md) for detector installation
and comparative measurements; those reports remain local.

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
