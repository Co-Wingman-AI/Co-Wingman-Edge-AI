# Personal portfolio cues

The optional portfolio index supplies personal facts to the live cue request.
It works with typed input, microphone input, and pause assistance. It does not add
speaker identification or change the microphone/pause detector.

## Set up on the Jetson

From the repository root, with your existing virtual environment active:

```sh
git pull --ff-only
python3 -m cowingman.portfolio
python3 -m cowingman --typed --portfolio private/portfolio.json
```

The import command downloads four fixed public HTML pages from the GitHub source
of [Honey's portfolio](https://honeyreddydaram.github.io/Portfolio/index.html):
About, Projects, Experience, and Certifications. It uses source commit
`2cc372613dde6c7a5dfb5bed24cc9bf5cdeedc26` for reproducibility. This is a snapshot,
not an automatically updating mirror. It does not execute JavaScript, follow
links, or fetch the resume PDF, images, videos, or external project repositories.
The live website may change independently of this pinned snapshot.

The generated JSON includes source URLs and an import timestamp. Review/edit it
locally with a text editor if facts are outdated or you want fewer passages. The
importer keeps complete text blocks up to 600 characters, with section/project/
role labels; oversized blocks and contact email lines are omitted. It preserves
qualifications within a block, such as results measured in simulated scenarios.
This is selected portfolio text, not a complete factual biography.

The file stays in the ignored `private/` directory, with owner-only permissions.
Importing again refuses to overwrite it. Use `--output private/portfolio-new.json`
for another copy. To disable portfolio use, launch without `--portfolio`.
Delete the local JSON when it is no longer wanted. Never commit personal profiles.

## Controlled test

Type each line separately, pressing Enter after each. Input remains hidden:

```text
:partner Tell me about OrderFlow. What did you build?
I built OrderFlow using
:cue
```

A supported cue might be: "I built six Spring Boot microservices coordinated through Kafka."
The exact wording varies. It should refer to the portfolio facts rather than ask
for generic clarification.

The status `Portfolio: 2 reference passages supplied.` reports how many local
passages were included in the request, without printing them. If retrieval finds
zero matches, portfolio mode stops before the API request and displays an explicit
no-match message. Add fresh context naming the project or topic before retrying.
A multiword verbatim echo of a user/microphone
fragment is withheld with an explicit error, rather than displayed as a useful cue.
Context is discarded as with other rejected responses; there is no automatic retry.
The check ignores case and punctuation but is not a general relevance evaluator.
For an explicit Enter/`:cue` request, portfolio mode can use a local reference
phrase when the model returns a valid `should_offer: false` response or when its
only validation failure is word/character length. The UI explicitly identifies
this as a local fallback. It is a new phrase extracted from selected portfolio
facts, not the model's declined text. No second API request is made.

The fallback prefers complete short statements in retrieval order and can add
"I" before a source action verb. It can omit an appended achievement clause from
a long action sentence, but skips shortening if recognized qualifications such
as "only", "not", or "simulated" occur. It does not select trailing comma/list
fragments. Every candidate passes the normal schema, safety, 12-word, 160-character,
and echo checks. These rules are conservative heuristics, not proof of semantic
accuracy. If no suitable phrase exists, a valid decline stays a decline and an
invalid response stays an error. Other validation failures and explicit API
refusals do not trigger fallback. Automatic pause requests never use this fallback
and preserve the model's decision not to offer a cue.

Test another topic using fresh context:

```text
:partner What did you do during your robotics internship?
I worked on
:cue
```

The relevant passages describe Python machine-vision work at IIITDM. To use the
same profile with your microphone:

```sh
python3 -m cowingman --portfolio private/portfolio.json --pause-assist
```

After each cue, `:listen` resumes audio. Pause assistance still uses speech energy
and silence, cannot recognize your identity, and can mistake normal turn-taking
for a hesitation. Typed tests isolate retrieval from microphone/ASR quality.

For a controlled microphone test, use `:pause` first, then type the `:partner`
question and press Enter. Use `:check` to verify one typed partner fragment and
two matching passages. Then use `:listen`, speak one short unfinished answer,
wait for the accepted-fragment message, and request a cue. `:check` reports only
counts: no conversation text is printed, no API request is made, and the context
is neither consumed nor kept beyond its original expiry. It cannot verify ASR
accuracy. A long exchange or the 60-second TTL can still remove the typed question.

## Retrieval, limits, and verification

Retrieval uses local keyword ranking with a few question aliases (for example,
"study" maps to education). It loads no embedding model and uses no additional
GPU memory. Only matches are selected; no match stops the request before any API
call. This applies to all requests while `--portfolio` is enabled. Launch without
that flag for general conversation cues that do not require portfolio matches. It may
miss paraphrases or select an irrelevant passage. Selected facts stay separate
from conversation roles: portfolio text is reference data, never a spoken turn.

Each live request can contain up to **two passages, 600 characters each**, in
addition to the existing **800-character** conversation window. Thus the new
maximum source-text content is **2,000 characters**, plus JSON and the fixed system
prompt. Selection is validated again before transmission. No full profile or
source URLs are sent, and the application does not browse during conversations.
UF receives those selected facts as well as the bounded conversation excerpt.

Health checks and synthetic/offline demos reject `--portfolio`; they cannot send
profile text accidentally. Imported facts persist locally until deleted, unlike
ephemeral conversation fragments. Runtime references are released at shutdown;
conversation TTL does not delete the imported file.

Tests cover topic selection, no-match behavior, malformed files, import boundaries,
payload bounds, and a typed application run with a mocked service. Live cue factual
accuracy still requires operator review: prompt instructions and schema validation
do not prove the model's answer is supported by the selected facts.
