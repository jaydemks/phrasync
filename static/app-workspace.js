"use strict";

Object.assign(ITALIAN, {
  "Full-width timeline": "Timeline a tutta larghezza",
  "Switch between center and full-width timeline": "Alterna timeline centrale e a tutta larghezza",
  "Resize Studio panel": "Ridimensiona il pannello Studio",
  "Resize lyrics panel": "Ridimensiona il pannello testi",
  "Resize timeline": "Ridimensiona la timeline",
  "Scroll lyrics and editing tools": "Scorri testi e strumenti di modifica",
});

function initWorkspaceLayout() {
  const workspace = document.querySelector(".workspace");
  const toggle = document.getElementById("timelineWidthToggle");
  const compact = matchMedia("(max-height: 800px)");
  const storageKey = "phrasync.workspace.layout";
  let preferences = {};
  try { preferences = JSON.parse(localStorage.getItem(storageKey)) || {}; } catch {}

  function saveLayout() {
    try { localStorage.setItem(storageKey, JSON.stringify(preferences)); } catch {}
  }

  function applyLayout() {
    const layout = preferences.layout || (compact.matches ? "center" : "full");
    workspace.dataset.timelineLayout = layout;
    toggle.setAttribute("aria-pressed", String(layout === "full"));
  }
  applyLayout();
  if (compact.matches) document.getElementById("bulkLyricsTools").open = false;
  compact.addEventListener("change", applyLayout);
  toggle.addEventListener("click", () => {
    preferences.layout = workspace.dataset.timelineLayout === "full" ? "center" : "full";
    applyLayout();
    saveLayout();
  });

  const panels = [
    { grip: "studioGrip", panel: "studioPanel", property: "--studio-width", axis: "X", direction: 1, min: 170, max: 33 },
    { grip: "lyricsGrip", panel: "lyricsPanel", property: "--lyrics-width", axis: "X", direction: -1, min: 182, max: 33 },
    { grip: "dockGrip", panel: "timelineDock", property: "--dock-height", axis: "Y", direction: -1, min: 120, reserve: 186 },
  ];

  for (const config of panels) {
    const grip = document.getElementById(config.grip);
    const panel = document.getElementById(config.panel);
    const vertical = config.axis === "Y";
    const dimension = vertical ? "height" : "width";
    const measure = () => panel.getBoundingClientRect()[dimension];
    const available = () => {
      const style = getComputedStyle(workspace);
      return vertical
        ? workspace.clientHeight - parseFloat(style.paddingTop) - parseFloat(style.paddingBottom)
        : workspace.clientWidth - parseFloat(style.paddingLeft) - parseFloat(style.paddingRight);
    };
    const maximum = size => vertical ? size - config.reserve : size * config.max / 100;
    const refreshAria = () => {
      grip.setAttribute("aria-valuemin", String(config.min));
      grip.setAttribute("aria-valuemax", String(Math.max(config.min, Math.floor(maximum(available())))));
      grip.setAttribute("aria-valuenow", String(Math.round(measure())));
    };
    function resizePanel(pixels) {
      const size = available();
      const clamped = Math.max(config.min, Math.min(maximum(size), pixels));
      const ratio = 100 * clamped / size;
      preferences[config.property] = ratio;
      workspace.style.setProperty(config.property, `${ratio}%`);
      refreshAria();
    }

    const saved = preferences[config.property];
    if (Number.isFinite(saved) && saved > 0 && saved <= 100) workspace.style.setProperty(config.property, `${saved}%`);
    const observer = new ResizeObserver(refreshAria);
    observer.observe(panel);
    let drag = null;
    grip.addEventListener("pointerdown", event => {
      if (event.button !== 0 || drag) return;
      drag = { pointer: event.pointerId, start: event[`client${config.axis}`], pixels: measure() };
      grip.setPointerCapture(event.pointerId);
      grip.dataset.dragging = "";
    });
    grip.addEventListener("pointermove", event => {
      if (drag?.pointer !== event.pointerId) return;
      resizePanel(drag.pixels + (event[`client${config.axis}`] - drag.start) * config.direction);
    });
    grip.addEventListener("lostpointercapture", () => {
      drag = null;
      delete grip.dataset.dragging;
      saveLayout();
    });
    grip.addEventListener("keydown", event => {
      const backward = vertical ? "ArrowUp" : "ArrowLeft";
      const forward = vertical ? "ArrowDown" : "ArrowRight";
      if (event.key === "Home") resizePanel(config.min);
      else if (event.key === "End") resizePanel(maximum(available()));
      else if (event.key === backward || event.key === forward) {
        resizePanel(measure() + (event.key === backward ? -1 : 1) * config.direction * (event.shiftKey ? 48 : 16));
      } else return;
      event.preventDefault();
      event.stopPropagation();
      saveLayout();
    });
  }

  let timelineWidth = 0;
  new ResizeObserver(([entry]) => {
    const width = entry.contentRect.width;
    if (width === timelineWidth) return;
    timelineWidth = width;
    timeline.resize();
  }).observe(els.timelineWrap);
}
