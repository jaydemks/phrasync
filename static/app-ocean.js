"use strict";

const OCEAN_CONTROLS = {
  sunAzimuth: [25, "°"], sunElevation: [12, "°"],
  moonAzimuth: [-25, "°"], moonElevation: [18, "°"],
  oceanWaveStrength: [65, "%"]
};

function initOceanControls() {
  for (const [key, [, suffix]] of Object.entries(OCEAN_CONTROLS)) {
    const input = document.getElementById(key);
    rangeOutputs[key] = [`${key}Out`, value => `${value}${suffix}`];
    input.addEventListener("input", () => {
      project.background[key] = Number(input.value) / (key === "oceanWaveStrength" ? 100 : 1);
      updateRangeUI(input); scheduleSave();
    });
  }
  els.sceneKit.addEventListener("input", () => {
    if (els.sceneKit.value === "ocean") {
      project.background.visual = "scene3d";
      els.visualSelect.value = "scene3d";
    }
    applyBackgroundTypeUI();
  });
}

function applyOceanUI() {
  const ocean = project.background.sceneKit === "ocean" && project.background.visual === "scene3d";
  document.getElementById("oceanControls").hidden = !ocean;
  for (const control of [els.sceneArtStyle, els.sceneDensity, els.sceneBeat, els.sceneWave, els.season]) {
    control.closest("label").hidden = ocean;
  }
  els.sceneReseed.hidden = ocean;
  if (ocean) els.waveControls.hidden = true;
  for (const [key, [fallback]] of Object.entries(OCEAN_CONTROLS)) {
    const input = document.getElementById(key);
    input.value = project.background[key] == null ? fallback : project.background[key] * (key === "oceanWaveStrength" ? 100 : 1);
    updateRangeUI(input);
  }
}
