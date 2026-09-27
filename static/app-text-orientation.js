"use strict";

// Saved projects and the WebGL exporter share these orientation values.
const TEXT_ORIENTATION = ["text3DPitch", "text3DYaw", "text3DRoll"];
function initTextOrientation() {
  for (const key of TEXT_ORIENTATION) {
    const input = document.getElementById(key);
    rangeOutputs[key] = [`${key}Out`, value => `${value}°`];
    input.addEventListener("input", () => {
      project.style[key] = Number(input.value);
      updateRangeUI(input); scheduleSave();
    });
  }
  document.getElementById("resetTextOrientation").addEventListener("click", () => {
    for (const key of TEXT_ORIENTATION) project.style[key] = 0;
    applyTextOrientation(); scheduleSave();
  });
}
function applyTextOrientation() {
  document.getElementById("textOrientationControls").hidden = project.background.textSpace !== "scene";
  for (const key of TEXT_ORIENTATION) {
    const input = document.getElementById(key);
    input.value = Number(project.style[key]) || 0;
    updateRangeUI(input);
  }
}
