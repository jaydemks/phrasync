"use strict";

let lastInteractiveFrame = 0;
let lastPlaybackPaint = -1;

function animationLoop(now) {
  if (window.__vfExportMode || document.hidden) {
    requestAnimationFrame(animationLoop);
    return;
  }
  const playing = project.audio?.url ? !els.audioPlayer.paused : virtualPlaying;
  // Export retains the selected FPS. Only the interactive preview is capped,
  // keeping controls responsive in a large high-DPI desktop WebView.
  const frameInterval = playing ? (1000 / 60) : (1000 / 12);
  // Half a millisecond tolerance avoids dropping every other refresh because
  // rAF timestamps at 60/120 Hz straddle a floating-point interval boundary.
  if (now - lastInteractiveFrame + .5 < frameInterval) {
    requestAnimationFrame(animationLoop);
    return;
  }
  lastInteractiveFrame = now;
  if (project.audio?.url && !els.audioPlayer.paused && currentPlaybackTime() >= projectDuration()) {
    els.audioPlayer.pause();els.backgroundVideo.pause();seekTo(projectDuration());updatePlayButton();
  }
  if (virtualPlaying && currentPlaybackTime() >= projectDuration()) {
    virtualTime = projectDuration();
    virtualPlaying = false;
    updatePlayButton();
  }
  const time = currentPlaybackTime();
  let glScene = null;
  try {
    glScene = project.background.type === "dynamic" && !VFMedia.enabled()
      ? drawDynamicVisual(now)
      : prepareWebGLOverlay(time);
  } catch (error) {
    // One bad frame must not kill the loop and freeze the whole editor.
    if (!window.__visualErrorShown) {
      window.__visualErrorShown = true;
      console.error("Preview visual failed:", error);
      toast(`Preview visual is unavailable: ${error.message}`, "error");
    }
  }
  // Scene switches replace their text layer, so submit lyrics afterwards.
  if (playing || Math.abs(time - lastPlaybackPaint) > .001) {
    updatePlaybackUI(time);
    lastPlaybackPaint = time;
  } else renderLyric();
  glScene?.render();
  try { VFMedia.preview(time, playing); }
  catch (error) {
    if (!window.__mediaErrorShown) { window.__mediaErrorShown = true; console.error("Footage preview failed:", error); toast(error.message, "error"); }
  }
  if (project.background.type === "video") syncBackgroundVideo(time);
  if (playing || timeline?._lastPaintTime !== lyricTime()) timeline?.tick();
  requestAnimationFrame(animationLoop);
}
