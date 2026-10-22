"use strict";

// Keep profiles usable independently of animation and demo initialization.
(() => {
  const profileDialog = document.getElementById("team-profile");
  let profileOpener = null;
  const profilePhoto = document.getElementById("profile-photo");
  const profileInitials = document.getElementById("profile-initials");
  const profileNote = document.getElementById("profile-note");
  function openProfile(button) {
    const profile = teamProfiles[button.dataset.profile];
    if (!profile) return;
    profileOpener = button;
    document.getElementById("profile-name").textContent = profile.name;
    document.getElementById("profile-role").textContent = profile.role;
    profileInitials.textContent = profile.initials;
    profileInitials.hidden = false;
    profilePhoto.hidden = true;
    profilePhoto.onload = null;
    profilePhoto.onerror = null;
    profilePhoto.removeAttribute("src");
    profilePhoto.alt = `Portrait of ${profile.name}`;
    const links = document.getElementById("profile-links");
    links.replaceChildren();
    profile.links.forEach((contact) => {
      const url = new URL(contact.url);
      if (url.protocol !== "https:") return;
      const link = document.createElement("a");
      link.href = url.href;
      link.target = "_blank";
      link.rel = "noopener noreferrer";
      link.textContent = contact.label;
      link.setAttribute(
        "aria-label",
        `${profile.name}: ${contact.label} (opens in a new tab)`,
      );
      links.append(link);
    });
    links.hidden = links.childElementCount === 0;
    profileNote.textContent = links.hidden
      ? "Photo and public contact links coming soon."
      : "Portrait coming soon. Explore the work and connect below.";
    if (profile.photo && profile.photo.startsWith("./assets/")) {
      profilePhoto.onload = () => {
        profilePhoto.hidden = false;
        profileInitials.hidden = true;
        profileNote.textContent = links.hidden
          ? "Public contact links coming soon."
          : "Explore the work and connect below.";
      };
      profilePhoto.onerror = () => {
        profilePhoto.hidden = true;
        profileInitials.hidden = false;
        profileNote.textContent = "The portrait is temporarily unavailable.";
      };
      profilePhoto.src = profile.photo;
    }
    profileDialog.showModal();
    document.body.classList.add("profile-open");
    document.dispatchEvent(new Event("team-profile-change"));
  }
  if (typeof profileDialog.showModal === "function") {
    document.querySelectorAll(".profile-trigger").forEach((button) => {
      button.disabled = false;
      button
        .closest("article")
        .addEventListener("click", () => openProfile(button));
    });
  }
  document
    .getElementById("profile-close")
    .addEventListener("click", () => profileDialog.close());
  profileDialog.addEventListener("keydown", (event) => {
    if (event.key !== "Tab") return;
    const targets = Array.from(
      profileDialog.querySelectorAll("button:not([disabled]), a[href]"),
    );
    const first = targets[0];
    const last = targets[targets.length - 1];
    if (!event.shiftKey && document.activeElement === last) {
      event.preventDefault();
      first.focus();
    } else if (event.shiftKey && document.activeElement === first) {
      event.preventDefault();
      last.focus();
    }
  });
  profileDialog.addEventListener("click", (event) => {
    if (event.target !== profileDialog) return;
    const bounds = profileDialog.getBoundingClientRect();
    if (
      event.clientX < bounds.left ||
      event.clientX > bounds.right ||
      event.clientY < bounds.top ||
      event.clientY > bounds.bottom
    )
      profileDialog.close();
  });
  profileDialog.addEventListener("close", () => {
    document.body.classList.remove("profile-open");
    profilePhoto.onload = null;
    profilePhoto.onerror = null;
    profilePhoto.removeAttribute("src");
    profileOpener?.focus({ preventScroll: true });
    document.dispatchEvent(new Event("team-profile-change"));
  });
})();
