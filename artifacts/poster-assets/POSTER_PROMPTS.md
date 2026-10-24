# Poster image prompts

Built-in image generation was used for the visual design and conversation illustration. The final print PDF was composed with vector text and diagrams; the original supplied logo and output photo are placed directly, with clipping only. The image-generation preview is not the print master.

## Initial design

Use case: compositing / scientific research poster.
Enhance and redesign the attached Co-Wingman academic poster into a polished, highly readable landscape 4:3 research poster, highest available resolution. This is a finished flat poster image, not a photo of a poster. White background, navy headings, UF-inspired blue and restrained orange, clean consistent typography, spacious grid. All text spelled correctly. Preserve the authors and project identity.
INPUTS in order: 1 original poster (edit target, layout/conversation illustration inspiration); 2 actual Jetson terminal photograph (supporting insert for Results); 3 supplied Herbert Wertheim College of Engineering logo (brand insert). Use the real logo faithfully on white, replace the large UF monogram. Remove the small original AI Days seal if needed for space. Do not invent a new logo.
Header exact title, wrapping beautifully: "Co-Wingman: A Hybrid Edge–Cloud AI Assistant for Real-Time Conversational Recovery Cues"
Authors: "Mrunal Vibhute, Shrimayee Deshpande, Honey Reddy Daram, Dr. Andrea Ramirez-Salgado"
Affiliation: "University of Florida | Master's in AI Systems | AI Days 2026"
Suggested balanced layout: narrow left column with motivation, capabilities and privacy; wide middle column with small human conversation illustration above dominant architecture; wide right column with Results including real photo, metrics and next steps. Adjust layout to make all copy readable, no cramped microtype.
LEFT:
"Motivation" with concise text "Help speakers recover a thought with a short, context-aware cue during a conversational pause."
"Prototype capabilities" with 5 short lines: "Local speech recognition"; "Rolling 60-second context"; "Manual or pause-triggered cues"; "Optional portfolio grounding"; "Minute summaries and S3 continuity".
"Privacy & control": "Raw audio stays on the Jetson." "Only bounded text reaches UF NaviGator." "AWS storage is opt-in." "Pause assistance detects silence, not anxiety or speaker identity."
CENTER illustration title "Speak → Pause → Recover". Two people conversing, Jetson small device between, clean illustration style from original. Small cue bubble "I built them with React and Node." 
CENTER architecture title "Hybrid architecture"
Three clearly distinct trust zones and legible arrows:
Blue zone "NVIDIA Jetson — local processing": Microphone → "4 s audio windows" → "NVIDIA NeMo ASR" → "60 s rolling context". Side branch "Pause heuristic / manual trigger" leads into bounded request construction. "Local portfolio selection" supplies optional context. Text badge "Raw audio remains local".
Green zone "UF hosted inference": "UF NaviGator API" → "NVIDIA Nemotron" with two functions "Short recovery cue" and "Minute summary". Outbound arrow from local context to API labeled "Bounded text over HTTPS". Return arrow from cue to local "Validate response" → "Visual cue on terminal". Validation is local, not AWS. Listening continues during rolling cue requests.
Orange zone "AWS S3 — optional persistence", visually separate and linked through Jetson application: "Timestamped summaries + latest.json"; "Portfolio archive + portfolio.json". Label upload arrow "Validated summary + metadata"; label return arrow "Explicit summary reuse / portfolio load". Footer within zone "boto3 • IAM prefix access • SSE-S3" and "No raw audio or full transcript archive". Avoid implying any raw audio goes to AWS. AWS is storage, not Nemotron hosting.
RIGHT title "Results on Jetson".
Insert actual terminal photograph as a substantial recognizable rectangle; crop surrounding desk/bezel and emphasize visible lower output and program context, retain photo character and literal output text, do not invent terminal output. Caption "Live visual cue demonstrated on Jetson" and small readable pullquote beneath: 'CUE: I built them with React and Node'
Below photo three large stat tiles: "94 audio windows", "13 cue requests", "0 dropped windows".
Compact clean table exact rows:
"Measured stage | Median | p95"
"ASR inference | 110 ms | 127 ms"
"Cue handling | 1.04 s | 2.54 s"
"Summary update | 1.42 s | 1.99 s"
Footnote: "One operator-reported rolling + pause-assist session. 69 voiced windows; 7 summary operations; no recorded stage failures. Cue timing starts at the request and excludes capture wait."
Small separate AWS status note "AWS integration implemented; live upload/reload validation pending." This is not included in the reported timing test.
"Next steps": "Reduce four-second buffering delay"; "Evaluate cue usefulness with users"; "Validate AWS upload and recovery"; "Evaluate experimental disfluency scoring".
Footer takeaway: "Local speech processing • Bounded cloud reasoning • Optional persistent memory"
Replace original vague/inaccurate/gibberish text entirely with supplied clear copy. Do not claim anxiety detection, speaker recognition, proven clinical effectiveness, all cues useful, or streaming ASR. Do not include a fake QR code. Include a small readable repository footer "github.com/Co-Wingman-AI/Co-Wingman-Edge-AI". Keep attractive editorial hierarchy and ample whitespace.

## Architecture refinement

Edit only the bottom-middle "Hybrid architecture" panel of this poster to correct the system boundary and arrow semantics. Preserve every other panel, title, author names, HWCOE logo, illustration, Results photo, metric table, footer, and all external layout unchanged. Maintain same sharp high-resolution poster quality.
Replace the contents of the hybrid architecture panel with a clean legible diagram with BLUE local Jetson zone occupying LEFT 60% width and GREEN hosted UF zone occupying RIGHT 40% width of upper 72% of the panel. Orange AWS zone occupies a full-width bottom 28% strip. Three zones must have non-overlapping borders and clear headings.
BLUE heading "NVIDIA Jetson — local". Use two compact columns in blue zone: first column flows vertically "Microphone" → "4 s audio buffer" → "NVIDIA NeMo ASR" → "60 s rolling context". Second column within blue has "Manual / pause trigger" plus "Local portfolio selection" feeding "Bounded request"; "Validate response" → "Terminal cue" also fully inside blue. Context feeds bounded request. Raw audio lock badge in blue: "Raw audio stays local".
GREEN heading "UF hosted inference". Place "UF NaviGator API" → "NVIDIA Nemotron". Beneath model two output labels "Recovery cue" and "Minute summary". Arrow BLUE "Bounded request" to GREEN "UF NaviGator API" labeled "HTTPS • bounded text". Arrow GREEN recovery cue back to BLUE "Validate response". Minute summary returns to BLUE application too; use a clear left pointing line labeled "Summary". Do not draw arrows from validation back to recovery cue, nor from terminal cue to validation.
ORANGE bottom full-width heading "AWS S3 — optional storage". Two storage icons/labels "Summary history + latest.json" and "Portfolio archive + portfolio.json". Only connect AWS to the BLUE Jetson zone, never directly to green model. Blue-to-AWS arrow label "Upload summary + metadata". AWS-to-blue arrow label "Load portfolio / reuse summary". Small footer in orange: "boto3 • IAM prefix access • SSE-S3 • No audio or full transcript archive". Optional summary upload occurs through app after cloud summarization; explicitly show that.
Keep text short, readable and coherent; orthogonal arrows avoid labels and crossings. No extra zones, no duplicated blocks or fabricated models. Use consistent icon style. Do not modify other poster sections.

