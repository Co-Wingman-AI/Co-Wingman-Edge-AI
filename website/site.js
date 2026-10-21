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
