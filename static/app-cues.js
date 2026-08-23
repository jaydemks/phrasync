"use strict";

function renderCueList() {
  normalizeCues();
  els.cueList.textContent = "";
  const fragment = document.createDocumentFragment();
  project.cues.forEach((cue, index) => {
    const card = document.createElement("article");
    card.className = `cue-card${cue.id === currentCueId ? " active" : ""}`
      + (cue.id === selectedCueId ? " selected" : "");
    card.dataset.id = cue.id;
    const number = document.createElement("button");
    number.type = "button";
    number.className = "cue-index";
    number.textContent = String(index + 1).padStart(2, "0");
    number.title = "Seek to cue";
    const content = document.createElement("div");
    content.className = "cue-content";
    const times = document.createElement("div");
    times.className = "cue-times";
    const start = document.createElement("input");
    start.type = "number"; start.min = "0"; start.step = ".01"; start.value = cue.start.toFixed(2); start.setAttribute("aria-label", "Cue start");
    const dash = document.createElement("span"); dash.textContent = "→";
    const end = document.createElement("input");
    end.type = "number"; end.min = "0"; end.step = ".01"; end.value = cue.end.toFixed(2); end.setAttribute("aria-label", "Cue end");
    times.append(start, dash, end);
    const text = document.createElement("textarea");
    text.className = "cue-text"; text.value = cue.text; text.rows = 2; text.setAttribute("aria-label", `Cue ${index + 1} lyric`);
    content.append(times, text);
    const remove = document.createElement("button");
    remove.type = "button"; remove.className = "cue-delete"; remove.textContent = "×"; remove.title = "Delete cue";
    card.append(number, content, remove);

    const select = () => {
      selectedCueId = cue.id;
      selectedWordIndex = 0;
      tapQueue = [];
      seekTo(cue.start + (project.timing.offset || 0));
      timeline?.focusTime(cue.start);
      updateWordLabel();
      $$(".cue-card", els.cueList).forEach(item => item.classList.toggle("selected", item.dataset.id === cue.id));
    };
    number.addEventListener("click", select);
    card.addEventListener("click", event => { if (!event.target.matches("input,textarea,button")) select(); selectedCueId = cue.id; });
    start.addEventListener("change", () => {
      cue.start = Math.max(0, Number(start.value) || 0);
      if (cue.end <= cue.start) cue.end = cue.start + .5;
      normalizeCues(); updateDurationUI(); renderCueList(); scheduleSave();
    });
    end.addEventListener("change", () => {
      cue.end = Math.max(cue.start + .05, Number(end.value) || cue.start + 2);
      updateDurationUI(); scheduleSave();
    });
    text.addEventListener("input", () => {
      cue.text = text.value;
      if (cue.id === currentCueId) renderLyric(cue, true);
      scheduleSave();
    });
    remove.addEventListener("click", () => {
      project.cues = project.cues.filter(item => item.id !== cue.id);
      if (selectedCueId === cue.id) selectedCueId = project.cues[0]?.id || null;
      renderCueList(); updateDurationUI(); scheduleSave();
    });
    fragment.append(card);
  });
  els.cueList.append(fragment);
  els.cueCount.textContent = `${project.cues.length} cue${project.cues.length === 1 ? "" : "s"}`;
}
async function createCuesFromLines(lines, replace) {
  lines = lines.map(line => line.trim()).filter(Boolean);
  if (!lines.length) return;
  let startAt = replace ? 0 : Math.max(0, ...project.cues.map(cue => cue.end));
  const availableDuration = replace ? projectDuration() : Math.max(lines.length * 3, 3);
  const slot = replace ? Math.max(.45, availableDuration / lines.length) : 3;
  const newCues = lines.map((text, index) => ({
    id: `cue-${Date.now()}-${index}`,
    start: startAt + index * slot,
    end: startAt + (index + 1) * slot - .03,
    text,
    words: []
  }));
  project.cues = replace ? newCues : [...project.cues, ...newCues];
  normalizeCues();
  selectedCueId = newCues[0]?.id || selectedCueId;
  renderCueList(); updateDurationUI(); restartLyricAnimation(); scheduleSave();
  // Pasted and OCR'd text arrives with nothing but an even split across the
  // song. Snapping it to the detected vocal attacks is the whole point of the
  // tool, so it happens here rather than waiting to be asked.
  await runAutoAlign({ auto: true });
}
function nudgeSelected(delta) {
  const cue = project.cues.find(item => item.id === selectedCueId);
  if (!cue) return toast("Select a cue first.");
  const duration = cue.end - cue.start;
  cue.start = Math.max(0, cue.start + delta);
  cue.end = cue.start + duration;
  renderCueList(); seekTo(cue.start); scheduleSave();
}
