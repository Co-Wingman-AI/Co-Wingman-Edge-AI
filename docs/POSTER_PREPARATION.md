# Co-Wingman: poster presentation and rehearsal pack

Prepared against repository revision `774bb74`. This is a speaking and study guide,
not a new evaluation report. Runtime claims were checked against the README,
implementation, and linked technical notes. Timing examples below come from one
operator-supplied Jetson report; original classifier metrics are reported research
results, not a fresh reproduction. Verify the actual device configuration before
presenting. Use “we” for team contributions and describe your personal contribution
only as you actually performed it.

## 1. The sentence to remember

**Co-Wingman gives you a short, context-aware starting point when you get stuck in
conversation, while keeping microphone audio on the Jetson.**

Three ideas carry the presentation: **local speech, bounded cloud context, optional
recovery cue**. The person remains in control of what they say.

## 2. Thirty-second pitch

“Have you ever known what you wanted to say, but lost the next sentence?
Co-Wingman is a conversational support prototype that offers a short phrase to
help you continue. An NVIDIA Jetson processes speech locally, and UF NaviGator
provides hosted NVIDIA Nemotron inference using a limited text excerpt. The
result is a brief cue you can use in your own words. We have demonstrated the
end-to-end path and are now studying cue usefulness, timing, and more reliable
automatic assistance.”

## 3. Two-minute pitch

“Imagine someone asks about a project you know well. You begin answering, then
lose your train of thought. What might help is a small starting point that lets
you continue yourself.

That is the idea behind Co-Wingman, our hybrid edge–cloud assistant for
conversational recovery cues.

On the edge, an NVIDIA Jetson Orin Nano captures microphone audio and runs local
speech recognition with NVIDIA NeMo. The application keeps a limited recent text
context. The user can request assistance directly, or enable an experimental
pause-based trigger.

For a cue, the application sends selected text to NVIDIA Nemotron through the
University of Florida’s NaviGator AI Toolkit. Raw microphone audio stays local.
If the user enables portfolio retrieval, a few relevant reference passages can
help the cue reflect their actual projects or experience.

The response must pass local checks before it is displayed. A cue is limited to
12 words and 160 characters. For example, after ‘Our project protects privacy
because…,’ a useful cue could be ‘Raw audio stays on the device.’ That example
illustrates the intended behavior; real model wording varies.

Our rolling mode continues listening while maintaining up to a minute of recent
context. Optional summaries can be stored in S3 for later reuse, with separate
disclosure and persistence from the default local mode.

We have demonstrated microphone capture, local transcription, hosted cue requests,
and portfolio-supported cues on the Jetson. We are still evaluating real-world
cue quality and automatic triggers. The system does not identify speakers or
diagnose anxiety. Our experimental disfluency model is a research component.

The goal is to offer timely support so a person can pick up the conversation in
their own voice.”

## 4. Walk around the poster in five minutes

| Time | Point to | Say |
| --- | --- | --- |
| 0:00–0:40 | Motivation | “The problem is the moment when someone loses their train of thought. We are exploring whether a short optional cue helps them continue.” |
| 0:40–1:15 | Conversation illustration | “The partner asks a question, the user starts an answer, and assistance is requested during a pause. The display offers a starting phrase, and the person takes over.” |
| 1:15–2:15 | Edge–cloud architecture | “Audio capture and speech recognition happen on the Jetson. A bounded text excerpt goes to Nemotron through NaviGator. We validate the returned cue locally.” |
| 2:15–2:55 | Privacy | “Raw audio stays local. Selected text does leave the device for inference. Optional S3 summaries are persistent, so that mode has a different storage boundary.” |
| 2:55–3:40 | Prototype capabilities | “Manual requests, pause assistance, portfolio retrieval and rolling context are implemented. Speaker identification and dependable detection of help-needed moments remain research goals.” |
| 3:40–4:20 | Demo/results | Show a short controlled interaction. Explain the limited timing sample and separate technical operation from cue usefulness. |
| 4:20–5:00 | Future work | “We will evaluate false triggers and useful cues on held-out speakers, improve the disfluency model, and study speaker-aware support and lower latency.” |

If interrupted, answer the question, then return with: “That connects to this
part of our architecture.” Point to the corresponding box. Avoid reading every
poster bullet aloud.

## 5. Understand the architecture

```text
Microphone → local RAM audio → local NeMo ASR → bounded recent text
                                                 ↓
Manual request / enabled automatic trigger + optional portfolio passages
                                                 ↓
               HTTPS → UF NaviGator → NVIDIA Nemotron
                                                 ↓
             Local response checks → short visual cue

Optional rolling mode: recent text → generated summary → RAM
Optional S3 mode: timestamped summary / explicitly uploaded portfolio → S3
```

**Jetson** is the edge computer. Keeping speech processing there reduces exposure
of raw recordings and lets the microphone/ASR path operate locally. It does not
make hosted cue generation work without internet.

**NeMo** is NVIDIA's speech framework. The selected English ASR model is Conformer
CTC Small, about 13 million parameters. Conformer combines convolution for local
acoustic patterns with attention for broader sequence context. CTC maps acoustic
frames to text using blanks and repeat collapsing, without requiring a manually
aligned word label for each frame. ASR is transcription, not speaker identification.
ASR may also normalize repetitions, so clean text alone is not a reliable measure
of disfluency.

**NaviGator** is UF's API service; **Nemotron** is the hosted model requested through
that service. The configured model identifier is `nemotron-3-nano-30b-a3b`. It is
not loaded on the Jetson. An OpenAI-compatible API format does not mean the model
is an OpenAI model.

**Portfolio retrieval** selects up to two locally stored relevant passages. This
is retrieval-augmented prompting, not fine-tuning. The model receives facts at
request time; its weights are not updated. The current retrieval is lightweight
text matching, not a claimed vector-database or semantic-search system. A portfolio
snapshot needs explicit refreshing when the source changes.

**Validation** checks response structure and local constraints, including length
and certain unsafe/echo patterns. An oversized offered cue may get one request
to the same model to shorten its bounded draft. Shortening is not arbitrary
character clipping. Structure and length checks cannot prove truth or usefulness.

**Rolling mode** keeps the microphone stream and ASR worker running, using a
separate capture thread while decoding completed four-second windows. It is
windowed ASR, not a fully streaming decoder. Its bounded queue may drop old windows
if processing falls behind. The default non-rolling mode has a different lifecycle:
capture and transcription are sequential, and requesting a cue releases the
speech worker. Do not describe all modes as having identical latency or memory use.

**S3** is optional object storage for summaries and portfolio records. It does not
generate cues, transcribe speech, or provide NaviGator connection reuse. In rolling
mode, minute-summary requests also use NaviGator; cloud requests are not limited
to moments when a cue appears. Network work can still block command handling while
the separate rolling speech process continues.

## 6. Numbers worth knowing

| Item | Current value and interpretation |
| --- | --- |
| Target device | NVIDIA Jetson Orin Nano, 8 GB shared system memory |
| Operator-reported stack | JetPack 6.2.1; L4T 36.4.7; Python 3.10; PyTorch 2.8.0 built for CUDA 12.6. This is one working setup, not a compatibility promise. |
| Audio | 16 kHz mono; four-second ASR windows |
| Default text context | Up to four fragments; 240 characters per fragment; 800 characters total; 60-second TTL |
| Rolling recent text | Up to 15 fragments / 3,600 characters over 60 seconds |
| Historical summary | Up to 1,200 additional characters in rolling cue requests |
| Portfolio reference | Up to two passages / 1,200 additional characters when enabled |
| Cue | At most 12 words AND 160 characters; display target is 20 seconds |
| Cue model output budget | 256 tokens; includes structured output and is not the displayed word limit |
| Pause heuristic | At least one second accumulated above the energy threshold, then three seconds sustained low energy; 30-second cooldown |
| Default RMS threshold | 0.015; microphone-dependent, not a universal speech threshold |
| Experimental classifier | Five-second audio windows every four seconds; first window not scored |
| Model-assist trigger | Two consecutive scores ≥0.5, then a qualifying pause within the implemented eight-second evidence interval; still experimental |

The 60-second TTL limits recent fragments. An updated historical summary can
represent information older than a minute. Do not say all conversational information
disappears after 60 seconds when summary memory is enabled.

### How to discuss the supplied timing report

| Stage | Sample | Median | Largest observed value |
| --- | --- | --- | --- |
| ASR initial load | 1 | 13.19 s | 13.19 s |
| Audio capture | 18 windows | 4.07 s | 4.23 s |
| ASR inference | 8 windows | 0.130 s | 0.752 s |
| Cue request handling | 2 | 1.14 s | 1.31 s |
| S3 upload | 1 | 0.563 s | 0.563 s |

The report counted zero dropped windows during that run. These are small-sample
observations, not a sustained benchmark. Several stages are nested: do not add all
reported durations. `cue_total` excludes waiting to finish capture and waiting
for a pause; it is not “hesitation to useful cue” latency. A two-request p95 is
not a reliable tail-latency estimate. Timing successes also do not establish that
both outputs were useful, or even that both offered a cue.

Say: “An initial run showed local ASR around 130 ms median and cue request handling
around 1.14 seconds median, but only eight ASR windows and two cue requests were
measured. We still need sustained end-to-end evaluation.”

## 7. Privacy explanation you can defend

| Configuration | Local | Sent or stored remotely |
| --- | --- | --- |
| Default live cues | RAM audio and expiring recent text | Selected bounded text goes to UF for a cue |
| Portfolio enabled | Imported reference JSON; local passage selection | Selected reference passages accompany the request |
| Rolling enabled | Recent text plus in-memory summary; continued capture | Cue requests and periodic text-summary requests go to UF |
| Summary S3 enabled | Local rolling processing | Timestamped summaries persist in S3 for later retrieval |
| Portfolio S3 enabled | Downloaded once; passages selected locally | Explicit portfolio uploads persist in S3 |

Use this wording: “We minimize what leaves the device. Raw microphone audio is
not sent to NaviGator. Selected text does leave for inference, and optional
summaries can be stored in S3.”

The application does not create audio recordings or a full transcript archive.
That is not a claim that every mode saves nothing: portfolio files and opt-in
summaries have separate persistence. `:forget` clears local memory; it does not
delete existing S3 objects. UF retention, OS swap, screen capture, and terminal
recording are outside the application's deletion guarantee. Speak about privacy
boundaries, not absolute anonymity, guaranteed confidentiality, or certified
compliance.

## 8. Demonstration script

Use fictional/project-general content, a consenting partner, and the existing
working environment. Do not install or upgrade the speech stack at the poster.
Keep visual output; optional TTS adds another unverified dependency path.

### Before visitors arrive

From the repository, in the prepared virtual environment and shell with the key:

```sh
python3 -m cowingman --health-check
python3 -m cowingman --list-audio
```

Check the actual microphone connection and input. Warm the speech model before
starting your explanation. Keep a second terminal ready for typed mode. Health
check verifies a synthetic request, not all conversational conditions.

### Reliable first demonstration: typed input, live model

```sh
python3 -m cowingman --typed
```

Type each line separately and press Enter after each:

```text
:partner How does Co-Wingman protect conversation privacy?
We process microphone audio locally on the Jetson, so
:cue
```

Say: “This removes microphone variability while still using the real hosted model.
The returned wording varies. We want a short relevant continuation.”

An illustrative acceptable continuation is “Raw audio stays on the device.” Do
not promise that exact response. Finish the thought in your own words. If a cue
is irrelevant, acknowledge it as a cue-quality failure rather than calling it a
success because the request completed.

### Then demonstrate speech

```sh
python3 -m cowingman --show-input
```

Wait for listening. Say: “Our project protects privacy because we process the
microphone audio locally on the Jetson.” Wait for an accepted-fragment message,
then request `:cue`. The manual trigger makes the live demonstration predictable.
Afterward, `:listen` resumes default-mode audio. Keep the exchange short so it
fits the recent context.

For portfolio demonstration, use your reviewed local JSON with
`--portfolio private/portfolio.json`. Choose a topic that you verified is present,
enter the partner's topic, and run `:check` before requesting a cue. Do not improvise
an unverified resume claim solely because the model offers it.

### Optional automatic demonstration

```sh
python3 -m cowingman --rolling --pause-assist --show-input
```

Explain that rolling mode also makes periodic summary requests. Speak a short
unfinished answer, then both participants stay quiet. Allow for the three-second
silence rule, window processing and network delay; do not promise an exact trigger
time. Wait for the automatic-request status. The 30-second cooldown can suppress
another quick attempt. Use `:cue` if the automatic condition is not detected and
explain that pause sensitivity remains experimental. Do not enable model-assisted
mode for the first time in front of visitors.

### Controls and recovery

| Input | Purpose |
| --- | --- |
| `:cue` | Request assistance |
| `:check` | Inspect local context/matches without an API call |
| `:assist off` | Disable automatic triggering |
| `:pause` / `:listen` | Stop / resume microphone processing |
| `:clear` | Clear recent context/display and stop microphone |
| `:forget` | Clear local summary/recent memory in rolling mode; S3 remains |
| `:quit` | End the session |

If audio fails: `python3 -m cowingman --typed` still uses live NaviGator.
If connectivity fails: `python3 -m cowingman --offline --demo` is a deterministic,
synthetic software demonstration. Announce the distinction. The website is also
a scripted illustration and does not call Nemotron or access the microphone.

## 9. Likely questions and ready answers

### Purpose and contribution

**1. What problem are you solving?**
“We are exploring assistance for the moment when a person loses their train of
thought. A concise cue may help them resume without taking over the conversation.”

**2. Who is it for?**
“Our intended use cases include presentations, interviews, and everyday conversation.
We have not established benefits for any clinical population.”

**3. Why not just use a chatbot?**
“We are designing a conversation-specific workflow: local speech, recent context,
an optional trigger and a tightly bounded cue. The practical research questions
are usefulness, timing and disclosure, not simply whether an LLM can answer.”

**4. What is novel?**
“Our contribution is the integration and evaluation of a constrained recovery-cue
workflow on resource-limited edge hardware. We use existing speech and language
models; we are not claiming a new foundation model or a first-ever system.”

**5. What is actually working?**
“We have operator-observed Jetson capture, local transcription, live NaviGator
requests and displayed cues, including portfolio-supported examples. Rolling and
cloud-memory functions are implemented. Sustained reliability and useful-cue rates
still need structured evaluation.”

**6. How do you know it helps people?**
“We do not yet have a controlled outcome study. We would compare recovery time,
user-rated usefulness and interruption burden against manual support and no support.”

### Architecture and performance

**7. Why hybrid edge–cloud?**
“Local speech keeps recordings on-device, while hosted generation avoids loading
a large language model into the Jetson's limited shared memory. The tradeoff is
network dependence and disclosure of selected text.”

**8. Why Jetson rather than a laptop or phone?**
“It is an accessible embedded GPU platform for local speech research and possible
edge deployment. We have not proven it is better than a phone; that comparison
requires latency, power and usability measurements.”

**9. What runs where?**
“Capture, ASR, context selection, optional disfluency scoring and validation run
locally. Nemotron runs behind NaviGator. S3 is optional storage.”

**10. Is it real time?**
“It is intended for near-real-time assistance, but currently processes four-second
windows. We should judge it by measured capture-to-display delay and sustained
behavior, not just call it instantaneous.”

**11. Does four seconds mean it waits for four seconds of silence?**
“No. Four seconds is the audio window. The default pause rule uses three seconds
of low energy after sufficient speech. Actual delivery also depends on processing.”

**12. Does recording stop while transcribing?**
“In the default path, capture and transcription are sequential. Rolling mode
captures in a separate thread while decoding prior windows. Its queue is bounded,
so it can drop older audio under load.”

**13. What happens without internet?**
“Local speech components can still run, but live hosted cue generation requires
connectivity. Our explicitly labeled offline demo uses deterministic responses.”

**14. Why 12 words and 160 characters?**
“They are design constraints for a glanceable starting point, not a scientifically
optimized threshold. We need user studies to tune cue length and presentation.”

**15. Why allow 256 output tokens for a 12-word cue?**
“The budget applies to structured model output, not just the displayed phrase.
Reducing it can truncate JSON or increase failures. We have a benchmark tool;
we have not established a more reliable smaller production budget.”

**16. What does your latency result prove?**
“It shows the components ran in one short test. Two cue timings do not establish
tail latency or overall usability, and request duration excludes pause/capture wait.”

### Triggers and speech research

**17. Does it detect anxiety?**
“No. Pauses and disfluency are not sufficient evidence of anxiety. We use pause
heuristics and an experimental speech-disfluency model, not an anxiety diagnosis.”

**18. Does it know when I need help?**
“Not reliably. A request explicitly communicates that intention; silence and
model scores are imperfect proxies. Automatic assistance is opt-in and experimental.”

**19. Can it distinguish my voice from my friend's?**
“No. Microphone text is labeled speaker-unknown. A personal microphone helps capture
placement but is not speaker verification. Typed `:partner` labels are supplied
by the operator, not inferred from voices.”

**20. What is the difference between silence, disfluency and anxiety?**
“Silence is an acoustic observation. Disfluency concerns speech flow, such as
repetitions or blocks. Anxiety is a psychological state. They can overlap, but
none establishes the others.”

**21. What is shadow mode?**
“It computes experimental local scores without allowing those scores to trigger
cues. That lets us examine behavior before giving the model control.”

**22. How does model-assisted mode differ?**
“It requires two elevated scores followed by a qualifying pause, with freshness
checks and cooldown. It is a separate opt-in research mode, not a validated feature.”

**23. What model is used for disfluency?**
“A custom CNN–LSTM baseline from the original research project uses MFCC and delta
features. It is distinct from NVIDIA NeMo ASR and Nemotron. The adapter runs it
locally on CPU using Keras's PyTorch backend.”

**24. How accurate is it?**
“The original saved notebook reports 59.27% clip accuracy and about 53% stuttering
recall at threshold 0.5. Those are not anxiety metrics or our new Jetson evaluation.
They are too limited to support dependable automatic assistance claims.”

**25. What is weak about that evaluation?**
“Clip-level random splits do not establish speaker independence. Training/runtime
preprocessing differs, and the model's temporal reshape needs correction when
retraining. We need a reproducible held-out speaker/session evaluation.”

**26. How would you improve it?**
“First fix labels, splits and preprocessing consistency. Then compare corrected
models, calibrate thresholds and evaluate false cues per minute, missed events
and useful-cue timing. A bigger model alone does not solve the evaluation problem.”

**27. What happens with noise, accents or overlap?**
“ASR and energy thresholds can fail or misfire. We have not measured robust
performance across those conditions. They belong in the evaluation set, with
manual triggering available when automatic behavior is uncertain.”

### Grounding, safety and memory

**28. How do portfolio facts help?**
“Local retrieval supplies relevant reference passages to the model. This can make
the cue specific to the user's known work, but does not guarantee factual fidelity.”

**29. Did you train the model on the portfolio?**
“No. We add selected passages to the request. That is retrieval-augmented prompting,
not training or fine-tuning.”

**30. Can the model hallucinate?**
“Yes. Grounding, bounded prompts, decline behavior and validation reduce some
failure modes but cannot prove every response true. The user decides whether to use it.”

**31. What happens if a response is too long?**
“For a length-only failure, one extra call asks the same model to shorten its own
bounded draft. If that still fails validation, we withhold it. We do not blindly
cut off the text or repeatedly retry.”

**32. Are any cues hardcoded?**
“Live requests use Nemotron. A clearly labeled local portfolio phrase can be used
in a narrow manual-request decline case. The website and offline demonstration
are explicitly scripted and should not be presented as live inference.”

**33. Does raw audio leave the device?**
“It is not sent by this application to NaviGator or S3. Selected text leaves for
inference. Optional summaries and uploaded portfolios can persist in S3.”

**34. Do you store the whole conversation?**
“No full transcript archive is created. Recent fragments are bounded and expire;
rolling summaries can retain selected information, and S3 persistence is opt-in.”

**35. Does clearing memory delete the cloud copy?**
“No. Local clearing and deleting saved S3 objects are separate operations. We also
cannot erase UF-side records by clearing local RAM.”

**36. Is the system secure or compliant?**
“We use restricted destinations, bounded requests, HTTPS and explicit storage
options. We do not claim a security certification, HIPAA compliance or guaranteed
protection against all leaks.”

**37. What if someone else's speech is captured?**
“The current system cannot reliably identify the speaker. We use a consenting
operator and partner for demonstrations, explain capture boundaries, and retain
manual control. Personal-microphone positioning does not solve identity.”

**38. Could assistance become distracting or increase dependence?**
“That is a design risk to evaluate. Cues are optional and short; users can disable
automatic triggering. We need feedback on interruption, agency and longer-term use.”

**39. What is the next milestone?**
“A repeatable Jetson baseline and an evaluation of useful cues and unwanted
triggers across held-out speakers. That evidence should guide model changes and
speaker-aware features.”

**40. What is your personal contribution?**
Prepare a truthful answer: “My main contribution was [actual work]. I implemented
or tested [specific component], observed [specific limitation], and used that
finding to [decision].” Do not claim another teammate's work or equate operating
a demo with training the models.

## 10. What to read, in order

### Essential project reading: about 45–60 minutes

1. [README](../README.md): overview, operating modes, privacy contract. Explain
   the path from microphone to cue without looking at the diagram.
2. [Speech implementation](SPEECH.md): Conformer CTC, default versus rolling
   capture, memory tradeoffs, pause detection. Remember four-second windows versus
   three-second silence.
3. [Portfolio](PORTFOLIO.md) and [privacy](PRIVACY.md): retrieval, no-match behavior,
   shortening, local fallback, what is sent and retained.
4. [Profiling/shadow](PROFILING_AND_SHADOW.md) and [model assistance](MODEL_ASSIST.md):
   distinguish measured stages, shadow scoring, experimental triggering and anxiety.
5. [AWS summaries](AWS_SUMMARIES.md): opt-in summary and portfolio persistence,
   timestamps, later retrieval and local-versus-cloud deletion.
6. [Remaining work](REMAINING_WORK.md): current limitations, evaluation plan and
   original model findings. Read this before answering “how accurate?”
7. [Jetson guide](../RUN_ON_JETSON.md): use the already working launch procedure.
   [Presentation runbook](PRESENTATION.md) is useful operationally, but its default-mode
   descriptions should not be applied to rolling/S3 modes without the newer docs.

### Background references: learn the idea, not every equation

| Reading | What to learn |
| --- | --- |
| [Conformer paper](https://arxiv.org/abs/2005.08100) | Why convolution and attention are combined for speech recognition |
| [NVIDIA Conformer CTC Small model card](https://huggingface.co/nvidia/stt_en_conformer_ctc_small) | Model size, intended language/use, limitations; model-card benchmarks are not your own results |
| [CTC paper](https://www.cs.toronto.edu/~graves/icml_2006.pdf) | Alignment-free sequence training, blank labels and repeat collapsing |
| [UF NaviGator Toolkit quickstart](https://docs.ai.it.ufl.edu/docs/navigator_toolkit/getting_started/quickstart/) | API access, model selection and service boundary |
| [NVIDIA Nemotron repository](https://github.com/NVIDIA-NeMo/Nemotron) | Hosted model family and official inference guidance |
| [Retrieval-Augmented Generation paper](https://arxiv.org/abs/2005.11401) | Retrieval supplies context; your lightweight retriever is not a reproduction of the paper's architecture |
| [SEP-28k dataset](https://github.com/apple-aiml-research/ml-stuttering-events-dataset) | Speech-event labels and annotator votes; stuttering labels are not anxiety labels |
| [SEP-28k-E partitioning research](https://arxiv.org/abs/2206.03400) | Why speaker/session separation changes the credibility of results |
| [Original training notebook](https://github.com/Co-Wingman-AI/Co-Wingman-AIS-Project-Original/blob/03288414382def0356e44ae1c4aca4d0fd6ad35d/CNN%2BLSTM%20Model%20training/train.ipynb) | What the baseline actually trained on and which metrics were reported |
| [AWS S3 overview](https://docs.aws.amazon.com/AmazonS3/latest/userguide/Welcome.html) | Objects, buckets, regions and access control; storage is separate from inference |

### Ten terms to explain in plain language

- **ASR:** audio to text.
- **CTC:** learns text sequences without exact frame-to-letter alignment.
- **MFCC:** compact features describing the short-time spectral envelope of sound.
- **Delta features:** changes in those features over time.
- **CNN:** learns local patterns across an input representation.
- **LSTM:** learns sequence dependencies when the input's time axis is correctly arranged.
- **RMS energy:** a signal-amplitude measure used by our simple speech/silence heuristic.
- **Diarization versus verification:** “which voice spoke when?” versus “is this the enrolled person?” Neither is currently implemented here.
- **Precision versus recall:** of detected positives, how many were correct; of actual positives, how many were found.
- **Calibration:** whether a score corresponds to observed event frequencies; a 0.5 score is not automatically a 50% anxiety probability.

## 11. Final rehearsal

1. Give the thirty-second pitch without notes twice.
2. Walk through the diagram once in two minutes and once in five minutes.
3. Have your friend ask questions 7, 10, 17, 19, 24, 30 and 33–35 in random order.
4. Rehearse one live typed cue and one speech cue. Switch deliberately to the
   offline example once so a failure will not derail the presentation.
5. Practice: “We have not measured that yet. Here is how we would evaluate it.”
6. Keep a compact note with: local audio; selected cloud text; 4-second windows;
   3-second silence; 12 words / 160 characters; optional S3; no anxiety or speaker
   recognition claim.
7. End with: “Our next step is to measure whether the right cue arrives at the
   right moment, with fewer unwanted interruptions.”

You do not need to memorize every hyperparameter. Be fluent in the problem,
architecture, demonstrated evidence, privacy boundary and next experiment.
