"use strict";

// This is a scripted public illustration. No recording, API calls, or storage.
const scenarios = {
  project: {
    question: "What did you build for your project?",
    fragment: "I built a notes app using…",
    cue: "Python and SQLite to keep notes organized.",
    source: "Example reference: a fictional notes-app portfolio passage.",
  },
  interview: {
    question: "What did you learn from working with your team?",
    fragment: "I learned that good teamwork means…",
    cue: "Listening carefully and making space for different ideas.",
    source: "Example reference: a fictional reflection on a team project.",
  },
  idea: {
    question: "How would you make the app easier to use?",
    fragment: "I think we could start by…",
    cue: "Simplifying the first screen and testing it with users.",
    source: "Example reference: a fictional conversation about app design.",
  },
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

function resetDemo(key) {
  clearTimeout(pendingTimer);
  currentScenario = key;
  cueVisible = false;
  trigger.disabled = false;
  const example = scenarios[key];
  document.getElementById("demo-question").textContent = example.question;
  document.getElementById("demo-fragment").textContent = example.fragment;
  cueText.textContent = "A small phrase. Room for your own voice.";
  sourceText.textContent = "Ready when you are.";
  cueBox.classList.remove("revealed", "pending");
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
  button.addEventListener("click", () => resetDemo(button.dataset.scenario));
});

trigger.addEventListener("click", () => {
  if (cueVisible) {
    resetDemo(currentScenario);
    return;
  }
  trigger.disabled = true;
  cueBox.classList.add("pending");
  triggerLabel("Finding a way back in…");
  demoStatus.textContent =
    "Illustrating how relevant context becomes a short cue…";
  const delay = window.matchMedia("(prefers-reduced-motion: reduce)").matches
    ? 0
    : 650;
  pendingTimer = setTimeout(() => {
    cueText.textContent = scenarios[currentScenario].cue;
    sourceText.textContent = scenarios[currentScenario].source;
    cueBox.classList.remove("pending");
    cueBox.classList.add("revealed");
    trigger.disabled = false;
    triggerLabel("Replay this moment");
    demoStatus.textContent =
      "An optional starting point. Take it from here, in your own words.";
    cueVisible = true;
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

// This editable lab is a deterministic simulation, never a model endpoint.
const labForm = document.getElementById("lab-form");
const labRun = document.getElementById("lab-run");
const labStatus = document.getElementById("lab-status");
const labFields = ["lab-question", "lab-fragment", "lab-fact"].map((id) =>
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
  const [question, fragment, fact] = labFields.map((field) =>
    field.value.trim(),
  );
  const words = fact ? fact.split(/\s+/u).length : 0;
  const characters = Array.from(fact).length;
  if (!question || !fragment || !fact) {
    labStatus.textContent = "Fill in all three fields to build the example.";
    labFields.find((field) => !field.value.trim()).focus();
    return;
  }
  if (words > 12 || characters > 160) {
    labStatus.textContent = `Your continuation has ${words} words and ${characters} characters. Keep it within 12 words and 160 characters; this simulator will not cut off your thought.`;
    labFields[2].focus();
    return;
  }
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
    document.getElementById("terminal-output").textContent = fact;
    document.getElementById("terminal-count").textContent =
      `${words} words · ${characters} characters · supplied by you`;
    terminalCue.hidden = false;
    labRun.disabled = false;
    labStatus.textContent =
      "Your supplied continuation is displayed. The real prototype requests a generated cue from Nemotron; this browser example does not.";
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
      "Example edited. Play it again to see your new continuation.";
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
