"use strict";

// Isolated render targets keep footage-world compositing separate from lyric geometry.
window.VFVisualClips = (() => {
  const targets = new Map();
  function render(clip, time, width, height) {
    const settings = clip.asset.settings || {};
    const key = clip.id;
    let target = targets.get(key);
    if (!target) {
      target = { flat: document.createElement("canvas"), gl: document.createElement("canvas"), snapshot: document.createElement("canvas"), particles: [], size: "" };
      targets.set(key, target);
    }
    const saved = { bg: project.background, flat: els.visualCanvas, gl: els.glCanvas, particles, size: lastParticleSize };
    try {
      project.background = { ...saved.bg, ...settings, type: "dynamic", footageEnabled: false, textSpace: "flat" };
      els.visualCanvas = target.flat; els.glCanvas = target.gl;
      particles = target.particles; lastParticleSize = target.size;
      const scene = drawDynamicVisual(time * 1000);
      if (scene) {
        target.world = true;
        // drawSceneGL normally uses lyric time; drive this clip with its own source clock.
        const bg = project.background;
        scene.update(time, { direction:bg.sceneDirection || "forward", artStyle:bg.artStyle || "cinematic", secondaryMotion:bg.secondaryMotion || "none",
          motionAmount:bg.motionAmount ?? .35, speed:sceneSpeedFor(bg,bg.visualIntensity), density:bg.sceneDensity ?? 1, seed:bg.sceneSeed || 1337,
          sunAzimuth:bg.sunAzimuth ?? 25,sunElevation:bg.sunElevation ?? 12,moonAzimuth:bg.moonAzimuth ?? -25,moonElevation:bg.moonElevation ?? 18,
          waveStrength:bg.oceanWaveStrength ?? .65,pulse:bg.sceneBeat ? audioAmplitude() : 0, environment:resolvedEnvironmentAt(time),
          wave:Boolean(bg.sceneWave),waveColor:bg.waveColor||"#4de2ff",waveIntensity:bg.waveIntensity??1,spectrum:bg.sceneWave?spectrumSnapshot():null });
        scene.render();
      }
      const source = settings.visual === "scene3d" ? target.gl : target.flat;
      if (target.snapshot.width !== width || target.snapshot.height !== height) { target.snapshot.width = width; target.snapshot.height = height; }
      const ctx = target.snapshot.getContext("2d"); ctx.clearRect(0,0,width,height); ctx.drawImage(source,0,0,width,height);
      if (scene && settings.visual !== "scene3d") ctx.drawImage(target.gl,0,0,width,height);
      target.particles = particles; target.size = lastParticleSize;
      // Retain only currently used clip targets, disposing GPU contexts from previous cuts.
      for (const [id, old] of targets) if (id !== key && !(saved.bg.clips || []).some(c => c.id === id && currentPlaybackTime() >= c.start && currentPlaybackTime() < c.end)) {
        if (old.world) { const gl = old.gl.getContext("webgl2"); gl?.getExtension("WEBGL_lose_context")?.loseContext(); }
        targets.delete(id);
      }
      return target.snapshot;
    } finally {
      project.background = saved.bg; els.visualCanvas = saved.flat; els.glCanvas = saved.gl;
      particles = saved.particles; lastParticleSize = saved.size;
    }
  }
  return { render };
})();
