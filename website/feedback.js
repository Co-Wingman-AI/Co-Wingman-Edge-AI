"use strict";

// Opt-in browser dictation for feedback only; no local storage or audio files.
(() => {
  const form = document.getElementById("feedback-form");
  const message = document.getElementById("feedback-message");
  const voice = document.getElementById("feedback-voice");
  const voiceLabel = document.getElementById("feedback-voice-label");
  const send = document.getElementById("feedback-send");
  const status = document.getElementById("feedback-status");
  const emailInstead = document.getElementById("feedback-email-instead");
  const Recognition =
    window.SpeechRecognition || window.webkitSpeechRecognition;
  const canDictate = Boolean(Recognition && window.isSecureContext);
  let recognition = null;
  let stopTimer = null;

  function updateEmailLink() {
    const name = document.getElementById("feedback-name").value.trim();
    const email = document.getElementById("feedback-email").value.trim();
    const body = [
      name && `Name: ${name}`,
      email && `Reply email: ${email}`,
      message.value,
    ]
      .filter(Boolean)
      .join("\n\n");
    emailInstead.href =
      "mailto:honeyreddydara@gmail.com?subject=" +
      encodeURIComponent("Co-Wingman website feedback") +
      "&body=" +
      encodeURIComponent(body);
  }

  function finish(instance, notice) {
    if (recognition !== instance) return;
    recognition = null;
    clearTimeout(stopTimer);
    voice.disabled = !canDictate;
    voice.setAttribute("aria-pressed", "false");
    voiceLabel.textContent = "Speak your feedback";
    send.disabled = false;
    status.textContent = notice;
  }

  function abort(notice) {
    const instance = recognition;
    if (!instance) return;
    finish(instance, notice);
    try {
      instance.abort();
    } catch {
      /* Already stopped. */
    }
  }

  function stop() {
    if (!recognition) return;
    voice.disabled = true;
    status.textContent = "Finishing dictation…";
    try {
      recognition.stop();
    } catch {
      abort("Dictation stopped. Review your message before sending.");
    }
  }

  voice.disabled = !canDictate;
  if (!canDictate) {
    status.textContent =
      "Browser dictation isn't available here. Type your feedback or use your keyboard's microphone.";
  }

  voice.addEventListener("click", () => {
    if (recognition) {
      stop();
      return;
    }
    if (!canDictate) return;
    let instance;
    try {
      instance = new Recognition();
    } catch {
      status.textContent =
        "Voice input could not start. You can still type your feedback.";
      return;
    }
    recognition = instance;
    instance.lang = "en-US";
    instance.continuous = true;
    instance.interimResults = false;
    const accepted = new Set();
    voice.setAttribute("aria-pressed", "true");
    voiceLabel.textContent = "Stop dictation";
    send.disabled = true;
    status.textContent = "Waiting for microphone permission…";
    instance.onstart = () => {
      if (recognition !== instance) return;
      status.textContent =
        "Listening… Speak your feedback. Stops automatically after one minute.";
    };
    instance.onresult = (event) => {
      if (recognition !== instance) return;
      for (
        let index = event.resultIndex;
        index < event.results.length;
        index++
      ) {
        const result = event.results[index];
        if (!result.isFinal || accepted.has(index)) continue;
        accepted.add(index);
        const words = result[0].transcript.trim();
        if (!words) continue;
        const separator =
          message.value && !/\s$/.test(message.value) ? " " : "";
        const combined = message.value + separator + words;
        message.value = combined.slice(0, message.maxLength);
        message.setCustomValidity("");
        updateEmailLink();
        if (combined.length >= message.maxLength) {
          abort(
            "The 2,000-character limit was reached. Dictation stopped; review your message.",
          );
          return;
        }
      }
    };
    instance.onerror = (event) => {
      if (recognition !== instance) return;
      const notices = {
        "not-allowed":
          "Microphone permission was denied. Allow it in your browser settings, or type your feedback.",
        "service-not-allowed":
          "Your browser's speech service is unavailable. You can still type your feedback.",
        "audio-capture":
          "No microphone is available. Check your microphone or type your feedback.",
        network:
          "The speech service could not connect. Your text is still here; try again or keep typing.",
        "no-speech":
          "No speech was recognized. Try again or type your feedback.",
        aborted: "Dictation stopped. Review your message before sending.",
      };
      abort(
        notices[event.error] ||
          "Dictation stopped unexpectedly. Your text is still here; you can keep typing.",
      );
    };
    instance.onend = () =>
      finish(
        instance,
        "Dictation stopped. Review or edit your message, then send it.",
      );
    stopTimer = setTimeout(
      () =>
        abort(
          "Dictation stopped after one minute. Review your text or start again.",
        ),
      60000,
    );
    try {
      instance.start();
    } catch {
      abort("Voice input could not start. You can still type your feedback.");
    }
  });

  form.addEventListener("input", () => {
    message.setCustomValidity("");
    updateEmailLink();
  });
  form.addEventListener("submit", (event) => {
    if (recognition) {
      event.preventDefault();
      stop();
      return;
    }
    if (!message.value.trim()) {
      event.preventDefault();
      message.setCustomValidity("Please enter your feedback before sending.");
      message.reportValidity();
      return;
    }
    status.textContent = "Opening FormSubmit to submit your feedback…";
  });
  emailInstead.addEventListener("click", () => {
    abort(
      "Dictation stopped. Review your message in your email app before sending.",
    );
    updateEmailLink();
  });
  document.addEventListener("visibilitychange", () => {
    if (document.hidden)
      abort(
        "Dictation stopped when you left this page. Your text is still here.",
      );
  });
  window.addEventListener("pagehide", () => abort("Dictation stopped."));
})();
