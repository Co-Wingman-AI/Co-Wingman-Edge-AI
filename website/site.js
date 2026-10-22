"use strict";

// This is a scripted public illustration. No recording, API calls, or storage.
const scenarios = {
  project: [
    {
      question: "What did you build for your project?",
      fragment: "I built a notes app using…",
      cue: "Python and SQLite to keep notes organized.",
      source: "Example reference: a fictional notes-app portfolio passage.",
    },
    {
      question: "How did you make your app easier to use?",
      fragment: "After testing it with classmates, I decided to…",
      cue: "simplify the navigation and make the buttons easier to find.",
      source: "Fictional example: a student app usability project.",
    },
    {
      question: "Why did you choose to process audio locally?",
      fragment: "Keeping the audio on the device helps us…",
      cue: "avoid sending recordings to a remote service.",
      source: "Fictional example: an explanation of an edge AI project.",
    },
    {
      question: "What was the hardest part of building the robot?",
      fragment: "The camera worked in the lab, but we needed to…",
      cue: "test it under different lighting conditions.",
      source: "Fictional example: a robotics camera experiment.",
    },
    {
      question: "What would you improve in your next version?",
      fragment: "For the next version, I want to focus on…",
      cue: "faster responses and clearer feedback when something goes wrong.",
      source: "Fictional example: a software project roadmap.",
    },
  ],
  interview: [
    {
      question: "What did you learn from working with your team?",
      fragment: "I learned that good teamwork means…",
      cue: "Listening carefully and making space for different ideas.",
      source: "Example reference: a fictional reflection on a team project.",
    },
    {
      question: "How do you approach a problem you haven't seen before?",
      fragment: "When a problem is unfamiliar, I usually start by…",
      cue: "breaking it into smaller questions and testing one assumption.",
      source: "Fictional example: an interview about problem solving.",
    },
    {
      question: "Tell me about a time you received feedback.",
      fragment: "My teammate suggested a simpler design, so I…",
      cue: "built a quick prototype and compared both approaches.",
      source: "Fictional example: a discussion about design feedback.",
    },
    {
      question: "How did you handle a disagreement on your team?",
      fragment: "We had different ideas, and what helped was…",
      cue: "agreeing on the goal before comparing our solutions.",
      source: "Fictional example: a team collaboration interview.",
    },
    {
      question: "What do you enjoy about working on AI projects?",
      fragment: "What I enjoy most is the chance to…",
      cue: "turn a technical idea into something useful for people.",
      source: "Fictional example: an interview about project interests.",
    },
  ],
  idea: [
    {
      question: "How would you make the app easier to use?",
      fragment: "I think we could start by…",
      cue: "Simplifying the first screen and testing it with users.",
      source: "Example reference: a fictional conversation about app design.",
    },
    {
      question: "How could we find out whether people need this feature?",
      fragment: "Before we build the whole thing, we could…",
      cue: "show a simple prototype and ask people to try it.",
      source: "Fictional example: a product discovery conversation.",
    },
    {
      question: "What if the system offers help at the wrong moment?",
      fragment: "We could give people more control by…",
      cue: "letting them pause assistance or request a cue themselves.",
      source: "Fictional example: a discussion about user control.",
    },
    {
      question: "How would you explain the idea to someone new?",
      fragment: "I would describe it as a small assistant that…",
      cue: "suggests a next phrase when you lose your train of thought.",
      source: "Fictional example: a project introduction.",
    },
    {
      question: "What should we test before our demonstration?",
      fragment: "Before the demo, let's make sure we can…",
      cue: "capture clear speech and recover when the network is unavailable.",
      source: "Fictional example: planning a prototype demonstration.",
    },
  ],
};

const stages = {
  edge: {
    badge: "THE EDGE",
    title: "Your audio takes the short route.",
    copy: "The Jetson captures audio in four-second windows and runs NVIDIA NeMo speech recognition locally. Rolling mode keeps a bounded minute of recent text while capture continues during decoding.",
    emphasis: "Raw audio",
    note: "stays on the device",
  },
  cloud: {
    badge: "THE CLOUD",
    title: "A little context. A focused request.",
    copy: "When a cue is requested, bounded text and optional relevant portfolio passages go through UF NaviGator to NVIDIA Nemotron. The model is asked for a short next phrase; local checks validate the response before display.",
    emphasis: "Selected text",
    note: "leaves the device",
  },
  you: {
    badge: "YOUR MOMENT",
    title: "The suggestion is small. The choice is yours.",
    copy: "A validated cue appears in the terminal for up to 20 seconds. You can use it, adapt it, or ignore it. The model may decline to offer a cue, and the prototype does not guarantee a useful answer every time.",
    emphasis: "Up to 12 words",
    note: "and 160 characters",
  },
};

let currentScenario = "project";
let currentExample = null;
const exampleBags = new Map();
let cueVisible = false;
let pendingTimer;
const cueBox = document.getElementById("demo-cue");
const cueText = document.getElementById("demo-cue-text");
const sourceText = document.getElementById("demo-source");
const trigger = document.getElementById("demo-trigger");
const demoStatus = document.getElementById("demo-status");

function triggerLabel(label) {
  trigger.firstChild.textContent = label + " ";
}

// Shuffle each topic's bank, exhausting it before refilling. Never immediately
// repeat the visible example when a bag is refilled.
function drawExample(key) {
  let bag = exampleBags.get(key);
  if (!bag || bag.length === 0) {
    bag = [...scenarios[key]];
    for (let i = bag.length - 1; i > 0; i -= 1) {
      const j = Math.floor(Math.random() * (i + 1));
      [bag[i], bag[j]] = [bag[j], bag[i]];
    }
    if (bag[0] === currentExample && bag.length > 1) {
      [bag[0], bag[1]] = [bag[1], bag[0]];
    }
    exampleBags.set(key, bag);
  }
  return bag.shift();
}

function resetDemo(key, example = currentExample) {
  clearTimeout(pendingTimer);
  currentScenario = key;
  currentExample = example;
  cueVisible = false;
  trigger.disabled = false;
  document.getElementById("demo-question").textContent = example.question;
  document.getElementById("demo-fragment").textContent = example.fragment;
  cueText.textContent = "A small phrase. Room for your own voice.";
  sourceText.textContent = "Ready when you are.";
  cueBox.classList.remove("revealed", "pending");
  cueBox.setAttribute("aria-busy", "false");
  triggerLabel("Help me find the next words");
  demoStatus.textContent =
    "You’re in control. Request a cue to continue the example.";
  document.querySelectorAll(".scenario").forEach((button) => {
    const selected = button.dataset.scenario === key;
    button.classList.toggle("active", selected);
    button.setAttribute("aria-pressed", String(selected));
  });
}

document.querySelectorAll(".scenario").forEach((button) => {
  button.addEventListener("click", () => {
    const key = button.dataset.scenario;
    resetDemo(key, drawExample(key));
  });
});

document.getElementById("demo-shuffle").addEventListener("click", () => {
  const keys = Object.keys(scenarios);
  const key = keys[Math.floor(Math.random() * keys.length)];
  resetDemo(key, drawExample(key));
  demoStatus.textContent =
    "A new fictional conversation is ready. Request its matching cue.";
});
resetDemo("project", drawExample("project"));

trigger.addEventListener("click", () => {
  if (cueVisible) {
    resetDemo(currentScenario, drawExample(currentScenario));
    return;
  }
  trigger.disabled = true;
  cueBox.classList.add("pending");
  cueBox.setAttribute("aria-busy", "true");
  cueText.textContent = "Finding the next words…";
  sourceText.textContent = "Playing a scripted response.";
  triggerLabel("Thinking through this moment…");
  demoStatus.textContent =
    "Illustrating how relevant context becomes a short cue…";
  const reduce = window.matchMedia("(prefers-reduced-motion: reduce)").matches;
  const delay = reduce ? 0 : 800 + Math.floor(Math.random() * 500);
  const example = currentExample;
  pendingTimer = setTimeout(() => {
    cueBox.classList.remove("pending");
    cueBox.classList.add("revealed");
    const words = example.cue.split(/\s+/u);
    let count = reduce ? words.length : 1;
    const reveal = () => {
      cueText.textContent = words.slice(0, count).join(" ");
      if (count < words.length) {
        count += 1;
        pendingTimer = setTimeout(reveal, 65);
        return;
      }
      sourceText.textContent = example.source;
      cueBox.setAttribute("aria-busy", "false");
      trigger.disabled = false;
      triggerLabel("Try another moment");
      demoStatus.textContent =
        "A scripted cue, shown as a simulated response. Try another moment to explore more.";
      cueVisible = true;
    };
    reveal();
  }, delay);
});

const stageButtons = Array.from(document.querySelectorAll(".path-node"));
function selectStage(button) {
  const details = stages[button.dataset.stage];
  stageButtons.forEach((item) => {
    const selected = item === button;
    item.classList.toggle("active", selected);
    item.setAttribute("aria-selected", String(selected));
    item.tabIndex = selected ? 0 : -1;
  });
  document
    .getElementById("architecture-detail")
    .setAttribute("aria-labelledby", button.id);
  document.getElementById("detail-badge").textContent = details.badge;
  document.getElementById("detail-title").textContent = details.title;
  document.getElementById("detail-copy").textContent = details.copy;
  const note = document.getElementById("detail-note");
  const emphasis = document.createElement("strong");
  emphasis.textContent = details.emphasis;
  note.replaceChildren(emphasis, document.createTextNode(details.note));
}
stageButtons.forEach((button, index) => {
  button.addEventListener("click", () => selectStage(button));
  button.addEventListener("keydown", (event) => {
    let next;
    if (["ArrowRight", "ArrowDown"].includes(event.key))
      next = (index + 1) % stageButtons.length;
    if (["ArrowLeft", "ArrowUp"].includes(event.key))
      next = (index + stageButtons.length - 1) % stageButtons.length;
    if (event.key === "Home") next = 0;
    if (event.key === "End") next = stageButtons.length - 1;
    if (next === undefined) return;
    event.preventDefault();
    selectStage(stageButtons[next]);
    stageButtons[next].focus();
  });
});

// Local scripted matching, never a model endpoint or a claim about a visitor.
const labExamples = [
  {
    question: "Can you tell me about your experience working with AI?",
    fragment: "I've worked on machine learning projects, and one of them was…",
    cue: "an AI assistant that helps people navigate conversations.",
  },
  ...Object.values(scenarios).flat(),
];
const labBridge = "Let me take a moment to explain that clearly.";
const labStopWords = new Set(
  "a an and are as at be been before but by can could did do does for from had has have how i if in into is it its me my of on one or our so some tell that the their them then there these they this to us was we were what when which with would you your ive im ve".split(
    " ",
  ),
);
function labTokens(text) {
  return new Set(
    (
      text
        .toLowerCase()
        .replace(/[’']/g, "")
        .match(/[a-z0-9]+/g) || []
    ).filter((word) => !labStopWords.has(word)),
  );
}
function selectLabCue(question, fragment) {
  const q = labTokens(question);
  const f = labTokens(fragment);
  let best = null;
  let bestScore = 0;
  for (const example of labExamples) {
    const eq = labTokens(example.question);
    const ef = labTokens(example.fragment);
    const sharedQuestion = [...q].filter((word) => eq.has(word)).length;
    const sharedFragment = [...f].filter((word) => ef.has(word)).length;
    // Question overlap alone must not invent a continuation for unrelated speech.
    if (
      sharedFragment < 2 ||
      sharedFragment / Math.max(f.size, ef.size, 1) < 0.4
    )
      continue;
    const score =
      (2 * sharedFragment) / Math.max(f.size, ef.size, 1) +
      sharedQuestion / Math.max(q.size, eq.size, 1);
    if (score > bestScore) {
      best = example;
      bestScore = score;
    }
  }
  return best
    ? { cue: best.cue, matched: true }
    : { cue: labBridge, matched: false };
}
const labForm = document.getElementById("lab-form");
const labRun = document.getElementById("lab-run");
const labStatus = document.getElementById("lab-status");
const labFields = ["lab-question", "lab-fragment"].map((id) =>
  document.getElementById(id),
);
const terminal = document.querySelector(".terminal");
const terminalState = document.getElementById("terminal-state");
const terminalCue = document.getElementById("terminal-cue");
const reducedMotion = window.matchMedia("(prefers-reduced-motion: reduce)");
let labInterval;

function cancelLab() {
  clearInterval(labInterval);
  labRun.disabled = false;
  terminal.classList.remove("running");
  terminalCue.hidden = true;
  document.getElementById("terminal-output").textContent = "";
  document.getElementById("terminal-count").textContent = "";
  terminalState.textContent = "[ready] Play the conversation to begin.";
}

labRun.disabled = false;
labForm.addEventListener("submit", (event) => {
  event.preventDefault();
  cancelLab();
  const [question, fragment] = labFields.map((field) => field.value.trim());
  if (!question || !fragment) {
    labStatus.textContent =
      "Enter your partner’s question and your unfinished thought.";
    labFields.find((field) => !field.value.trim()).focus();
    return;
  }
  const selected = selectLabCue(question, fragment);
  const withinBounds = (text) =>
    text.split(/\s+/u).length <= 12 && Array.from(text).length <= 160;
  const matched = selected.matched && withinBounds(selected.cue);
  const cue = matched ? selected.cue : labBridge;
  const words = cue.split(/\s+/u).length;
  const characters = Array.from(cue).length;
  document.getElementById("terminal-question").textContent = question;
  document.getElementById("terminal-fragment").textContent = fragment;
  labRun.disabled = true;
  terminal.classList.add("running");
  labStatus.textContent =
    "Playing a simulated three-second pause. No audio is being measured.";
  const finish = () => {
    clearInterval(labInterval);
    terminal.classList.remove("running");
    terminalState.textContent = "[pause detected: 3.0s simulated silence]";
    document.getElementById("terminal-output").textContent = cue;
    document.getElementById("terminal-count").textContent =
      `${words} words · ${characters} characters · ${matched ? "scripted example" : "general recovery phrase"}`;
    terminalCue.hidden = false;
    labRun.disabled = false;
    labStatus.textContent = matched
      ? `Suggested cue: ${cue} Selected automatically from fictional examples; no AI call was made.`
      : `Suggested cue: ${cue} No close scripted match was found, so a general recovery phrase is shown.`;
  };
  if (reducedMotion.matches) {
    finish();
    return;
  }
  const start = performance.now();
  terminalState.textContent = "[simulating pause: 0.0 / 3.0s]";
  labInterval = setInterval(() => {
    const elapsed = Math.min(3, (performance.now() - start) / 1000);
    terminalState.textContent = `[simulating pause: ${elapsed.toFixed(1)} / 3.0s]`;
    if (elapsed >= 3) finish();
  }, 100);
});
labFields.forEach((field) =>
  field.addEventListener("input", () => {
    cancelLab();
    labStatus.textContent =
      "Example edited. Play it again to get an automatically selected cue.";
  }),
);
document.getElementById("lab-reset").addEventListener("click", () => {
  labForm.reset();
  cancelLab();
  document.getElementById("terminal-question").textContent = labFields[0].value;
  document.getElementById("terminal-fragment").textContent = labFields[1].value;
  labStatus.textContent =
    "Example reset. Everything you type stays in this page.";
});

const flowSteps = Array.from(document.querySelectorAll(".flow-ribbon>span"));
const flowPlay = document.getElementById("flow-play");
let flowTimer;
flowPlay.addEventListener("click", () => {
  clearInterval(flowTimer);
  flowSteps.forEach((step) => step.classList.remove("flow-active"));
  if (reducedMotion.matches) {
    flowSteps.forEach((step) => step.classList.add("flow-active"));
    return;
  }
  flowPlay.disabled = true;
  let index = 0;
  flowSteps[0].classList.add("flow-active");
  flowTimer = setInterval(() => {
    index += 1;
    if (index < flowSteps.length) flowSteps[index].classList.add("flow-active");
    else {
      clearInterval(flowTimer);
      flowPlay.disabled = false;
    }
  }, 750);
});

// Lightweight adaptation of React Bits SpotlightCard's pointer-relative light.
// Source and complete upstream license: design-credits.txt.
document.querySelectorAll(".spotlight").forEach((card) => {
  let frame = 0;
  card.addEventListener("pointermove", (event) => {
    if (reducedMotion.matches || event.pointerType !== "mouse") return;
    cancelAnimationFrame(frame);
    frame = requestAnimationFrame(() => {
      const bounds = card.getBoundingClientRect();
      card.style.setProperty("--spot-x", `${event.clientX - bounds.left}px`);
      card.style.setProperty("--spot-y", `${event.clientY - bounds.top}px`);
    });
  });
  card.addEventListener("pointerleave", () => cancelAnimationFrame(frame));
});

// Motion is an enhancement: content stays visible if JavaScript is unavailable.
if ("IntersectionObserver" in window) {
  const arrivals = new IntersectionObserver(
    (entries, observer) => {
      entries.forEach((entry) => {
        if (!entry.isIntersecting) return;
        if (!reducedMotion.matches)
          entry.target.classList.add("reveal-arrival");
        observer.unobserve(entry.target);
      });
    },
    { threshold: 0.15 },
  );
  document
    .querySelectorAll(".research-card, .spec-panel, .resource-card")
    .forEach((card) => arrivals.observe(card));
}
window.addEventListener("pagehide", () => {
  cancelLab();
  clearInterval(flowTimer);
  flowPlay.disabled = false;
  clearTimeout(pendingTimer);
  if (!cueVisible) resetDemo(currentScenario);
});

// Equal turns around the team circle. Reading order remains stable for assistive
// technology; only visual positions change. The advisor is outside this orbit.
const teamOrbit = document.getElementById("team-orbit");
const teamMembers = Array.from(
  teamOrbit.querySelectorAll(".team-grid article"),
);
const teamPause = document.getElementById("team-pause");
const teamNext = document.getElementById("team-next");
let teamPhase = Math.floor(Math.random() * teamMembers.length);
let teamPaused = false;
let teamVisible = false;
let teamFrame = 0;
let teamLastTime = null;
let teamGeometry;
teamOrbit.classList.add("is-rotating");
document.querySelector(".team-controls").hidden = false;

function drawTeam() {
  if (!teamGeometry) return;
  const part = teamPhase % 1;
  // Hold each position for 4.3s, then travel clockwise for about 1.7s.
  const travel = Math.max(0, (part - 0.72) / 0.28);
  const eased = travel * travel * (3 - 2 * travel);
  const turn = Math.floor(teamPhase) + eased;
  teamMembers.forEach((card, index) => {
    const { width, height } = teamGeometry.cards[index];
    const angle = (Math.PI * 5) / 4 + ((turn + index) * Math.PI) / 2;
    const x =
      teamGeometry.width / 2 +
      teamGeometry.radiusX * Math.cos(angle) -
      width / 2;
    const y = teamGeometry.height / 2 + 175 * Math.sin(angle) - height / 2;
    card.style.transform = `translate(${x.toFixed(2)}px, ${y.toFixed(2)}px)`;
  });
}

function measureTeam() {
  const cards = teamMembers.map((card) => ({
    width: card.offsetWidth,
    height: card.offsetHeight,
  }));
  teamGeometry = {
    width: teamOrbit.clientWidth,
    height: teamOrbit.clientHeight,
    radiusX: Math.max(
      0,
      (teamOrbit.clientWidth - Math.max(...cards.map((card) => card.width))) /
        2,
    ),
    cards,
  };
  drawTeam();
}

function syncTeamMotion() {
  cancelAnimationFrame(teamFrame);
  teamLastTime = null;
  teamPause.disabled = reducedMotion.matches;
  teamPause.textContent = reducedMotion.matches
    ? "Auto-rotation off"
    : teamPaused
      ? "Resume rotation"
      : "Pause rotation";
  document.getElementById("team-motion-note").textContent =
    reducedMotion.matches
      ? "Reduced motion is on. Use Next position to take turns."
      : "Four equal places. Everyone takes a turn.";
  if (teamPaused || reducedMotion.matches || !teamVisible || document.hidden)
    return;
  const tick = (time) => {
    if (teamLastTime !== null)
      teamPhase =
        (teamPhase + Math.min(time - teamLastTime, 100) / 6000) %
        teamMembers.length;
    teamLastTime = time;
    drawTeam();
    teamFrame = requestAnimationFrame(tick);
  };
  teamFrame = requestAnimationFrame(tick);
}
teamPause.addEventListener("click", () => {
  teamPaused = !teamPaused;
  syncTeamMotion();
});
teamNext.addEventListener("click", () => {
  teamPhase = (Math.floor(teamPhase) + 1) % teamMembers.length;
  drawTeam();
  syncTeamMotion();
});
if ("ResizeObserver" in window)
  new ResizeObserver(measureTeam).observe(teamOrbit);
else window.addEventListener("resize", measureTeam);
if ("IntersectionObserver" in window) {
  new IntersectionObserver((entries) => {
    teamVisible = entries.some((entry) => entry.isIntersecting);
    syncTeamMotion();
  }).observe(teamOrbit);
} else teamVisible = true;
reducedMotion.addEventListener("change", syncTeamMotion);
document.addEventListener("visibilitychange", syncTeamMotion);
window.addEventListener("pagehide", () => cancelAnimationFrame(teamFrame));
window.addEventListener("pageshow", syncTeamMotion);
measureTeam();
syncTeamMotion();
