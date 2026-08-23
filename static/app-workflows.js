"use strict";

async function handleAudioFile(file) {
  if (!file) return;
  setAssetStatus(`Uploading ${file.name}…`);
  try {
    const video = project.mode === "subtitles" && isVideoUpload(file);
    if (video) await assertBrowserPreviewableVideo(file);
    const kind = video ? "video" : "audio";
    const asset = await uploadAsset(kind, file);
    project.audioAssetId = asset.id;
    project.audio = asset;
    project.sourceAssetId = asset.id;
    project.sourceKind = kind;
    if (video) {
      project.background.type = "video";
      project.background.videoAsset = asset;
      project.background.assetId = asset.id;
      project.background.url = asset.url;
      project.background.name = asset.name;
    }
    analysis = null;
    if (asset.duration) project.duration = asset.duration;
    els.audioName.textContent = asset.name;
    applyAudioPreview(); applyBackgroundPreview(); updateDurationUI(); scheduleSave();
    const mediaLabel = video ? "Video" : (project.mode === "subtitles" ? "Audio" : "Song");
    setAssetStatus(`${mediaLabel} ready · ${asset.duration ? formatTime(asset.duration) : "loading duration"}`, "success");
    toast(`${mediaLabel} loaded.`, "success");
    timeline?.fitAll();
    ensureAnalysis(true);
  } catch (error) {
    setAssetStatus(error.message, "error");
    toast(error.message, "error");
  }
}
async function handleBackgroundFile(file) {
  if (!file || project.background.type === "dynamic") return;
  const kind = project.background.type;
  setAssetStatus(`Uploading ${file.name}…`);
  try {
    if (project.background.type === "video") await assertBrowserPreviewableVideo(file);
    const asset = await uploadAsset(kind, file);
    if (kind === "image") project.background.imageAsset = asset;
    else project.background.videoAsset = asset;
    project.background.assetId = asset.id;
    project.background.url = asset.url;
    project.background.name = asset.name;
    applyBackgroundPreview(); scheduleSave();
    setAssetStatus(`${kind[0].toUpperCase() + kind.slice(1)} background ready.`, "success");
  } catch (error) {
    setAssetStatus(error.message, "error");
    toast(error.message, "error");
  }
}
async function handleOCRFile(file) {
  if (!file) return;
  els.ocrPick.disabled = true;
  setAssetStatus(`Reading ${file.name} with local OCR…`);
  try {
    const asset = await uploadAsset("image", file);
    const result = await api("/api/ocr", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ assetId: asset.id, language: "auto" })
    });
    els.bulkLyrics.value = result.text || "";
    setAssetStatus(`${result.engine} extracted ${result.lines?.length || 0} text line(s). Review them, then auto-time.`, "success");
    toast("OCR text added to the lyric box.", "success");
  } catch (error) {
    setAssetStatus(error.message, "error");
    toast(error.message, "error");
  } finally {
    els.ocrPick.disabled = false;
    els.ocrInput.value = "";
  }
}

async function handleLyricsFile(file) {
  if (!file) return;
  setAssetStatus(`Importing ${file.name}…`);
  try {
    const asset = await uploadAsset("lyrics", file);
    const result = await api("/api/lyrics/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ assetId: asset.id, duration: projectDuration() })
    });
    project.cues = result.cues;
    selectedCueId = project.cues[0]?.id || null;
    renderCueList(); updateDurationUI(); seekTo(0); scheduleSave();
    setAssetStatus(`Imported ${project.cues.length} ${project.mode === "subtitles" ? "subtitle" : "lyric"} cues.`, "success");
    // Imported files carry phrase times at best, never word times. Align them
    // against the song straight away so the result is usable without the user
    // having to know the Auto-align button exists.
    await runAutoAlign({ auto: true });
  } catch (error) {
    setAssetStatus(error.message, "error");
    toast(error.message, "error");
  } finally {
    els.lyricsInput.value = "";
  }
}

async function handleFontFile(file) {
  if (!file) return;
  setAssetStatus(`Uploading ${file.name}…`);
  try {
    const asset = await uploadAsset("font", file);
    project.style.fontAssetId = asset.id;
    project.style.fontName = asset.name;
    els.fontPick.textContent = asset.name;
    scheduleSave();
    setAssetStatus("Custom font stored for final export. Browser preview uses the closest local font.", "success");
  } catch (error) {
    setAssetStatus(error.message, "error");
    toast(error.message, "error");
  } finally {
    els.fontInput.value = "";
  }
}

function updateTranscriptionProgress(job) {
  const percent = Math.max(0, Math.min(100, Math.round(Number(job.progress || 0) * 100)));
  els.transcriptionProgress.hidden = false;
  els.transcriptionMessage.textContent = job.message || "Transcribing…";
  els.transcriptionPercent.value = `${percent}%`;
  els.transcriptionProgressBar.style.width = `${percent}%`;
  els.transcriptionTrack.setAttribute("aria-valuenow", String(percent));
}

function finishTranscriptionControls() {
  if (transcriptionPollTimer) clearTimeout(transcriptionPollTimer);
  transcriptionPollTimer = null;
  currentTranscriptionJob = null;
  els.transcribeButton.disabled = false;
  els.transcribeButton.textContent = MODE_COPY[project.mode]?.transcribe || "Transcribe locally";
  els.cancelTranscription.disabled = false;
  els.cancelTranscription.hidden = true;
}

function applyTranscriptionResult(result) {
  project.cues = result.cues;
  selectedCueId = project.cues[0]?.id || null;
  selectedWordIndex = 0;
  renderCueList(); updateDurationUI(); seekTo(0); scheduleSave();
  timeline?.fitAll();
  if (result.alignmentStats) updateSyncSummary(result.alignmentStats);
  const drift = result.alignment && typeof result.alignment.offset === "number"
    ? ` · corrected latency ${Math.round(result.alignment.offset * 1000)} ms`
    : "";
  const gauntlet = result.transcriptionGauntlet || {};
  const retries = gauntlet.adaptiveFallbackSegments?.length || 0;
  const unstable = gauntlet.unstableSegments?.length || 0;
  const review = unstable
    ? ` · review ${unstable} unstable segment${unstable === 1 ? "" : "s"}`
    : (retries ? ` · gauntlet recovered ${retries} segment${retries === 1 ? "" : "s"}` : "");
  setAssetStatus(`Transcribed ${project.cues.length} phrases in ${result.languageMode || result.language || "auto language"} on ${result.device}${drift}${review}.`, "success");
  const languages = result.languages || [];
  toast(languages.length > 1
    ? `Transcribed across ${languages.length} languages: ${languages.join(" → ")}.`
    : "Transcription and alignment completed.", "success");
}

async function pollTranscription() {
  if (!currentTranscriptionJob) return;
  try {
    const job = await api(`/api/transcriptions/${currentTranscriptionJob}`);
    updateTranscriptionProgress(job);
    if (job.state === "complete") {
      applyTranscriptionResult(job.result);
      finishTranscriptionControls();
      return;
    }
    if (job.state === "cancelled") {
      setAssetStatus("Transcription stopped. No phrases were replaced.");
      toast("Transcription stopped.");
      finishTranscriptionControls();
      return;
    }
    if (job.state === "failed") {
      const message = job.error || "Transcription failed";
      setAssetStatus(message, "error");
      toast(message, "error");
      finishTranscriptionControls();
      return;
    }
    transcriptionPollTimer = setTimeout(pollTranscription, 600);
  } catch (error) {
    setAssetStatus(error.message, "error");
    toast(error.message, "error");
    finishTranscriptionControls();
  }
}

async function transcribeSong() {
  if (!project.audioAssetId) {
    return toast(project.mode === "subtitles"
      ? "Add a video or audio file before transcription."
      : "Add a song before transcription.", "error");
  }
  if (currentTranscriptionJob) return;
  els.transcribeButton.disabled = true;
  els.transcribeButton.textContent = "Transcribing locally…";
  els.cancelTranscription.hidden = false;
  els.transcriptionProgress.hidden = false;
  updateTranscriptionProgress({ progress: 0, message: "Creating transcription job" });
  setAssetStatus(`Whisper is transcribing the ${project.sourceKind === "video" ? "video" : "audio"} and timing cues. The first model download can take a while.`);
  try {
    const job = await api("/api/transcriptions", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({
        assetId: project.audioAssetId,
        model: els.whisperModel.value,
        language: els.whisperLanguage.value.trim() || "auto",
        vadFilter: els.vadFilter.checked,
        align: true
      })
    });
    currentTranscriptionJob = job.id;
    updateTranscriptionProgress(job);
    pollTranscription();
  } catch (error) {
    setAssetStatus(error.message, "error");
    toast(error.message, "error");
    finishTranscriptionControls();
  }
}

async function stopTranscription() {
  if (!currentTranscriptionJob) return;
  els.cancelTranscription.disabled = true;
  els.transcriptionMessage.textContent = "Stopping after the current audio segment…";
  try {
    await api(`/api/transcriptions/${currentTranscriptionJob}/cancel`, { method: "POST" });
  } catch (error) {
    els.cancelTranscription.disabled = false;
    toast(`Could not stop transcription: ${error.message}`, "error");
  }
}

function showReport(report, title = "Quality report") {
  els.reportTitle.textContent = title;
  els.scoreValue.textContent = report.score ?? "—";
  els.scoreRing.style.setProperty("--score-angle", `${Math.max(0, Math.min(100, report.score || 0)) * 3.6}deg`);
  const errors = (report.issues || []).filter(issue => issue.level === "error").length;
  const warnings = (report.issues || []).filter(issue => issue.level === "warning").length;
  els.reportSummary.textContent = report.ok
    ? warnings ? `No blocking faults. ${warnings} warning${warnings === 1 ? "" : "s"} worth reviewing.` : "All logic, timing, asset, typography, and render-workload checks passed."
    : `${errors} blocking issue${errors === 1 ? "" : "s"} must be fixed before export.`;
  els.reportList.textContent = "";
  if (!(report.issues || []).length) {
    const empty = document.createElement("div");
    empty.className = "report-empty";
    empty.textContent = "Clean pass. The critic found no issues.";
    els.reportList.append(empty);
  } else {
    for (const issue of report.issues) {
      const item = document.createElement("div");
      item.className = `report-item ${issue.level}`;
      const dot = document.createElement("i");
      const body = document.createElement("div");
      const label = document.createElement("strong");
      label.textContent = issue.level;
      const message = document.createElement("span");
      message.textContent = `${issue.message}${issue.cueId ? ` · ${issue.cueId}` : ""}`;
      body.append(label, message); item.append(dot, body); els.reportList.append(item);
    }
  }
  els.checksList.textContent = "";
  for (const check of report.checks || []) {
    const li = document.createElement("li"); li.textContent = check; els.checksList.append(li);
  }
  if (!els.reportDialog.open) els.reportDialog.showModal();
}

async function runCritic() {
  try {
    els.criticButton.disabled = true;
    const report = await api("/api/preflight", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ project })
    });
    showReport(report);
    return report;
  } catch (error) {
    toast(error.message, "error");
    return null;
  } finally {
    els.criticButton.disabled = false;
  }
}

function resetRenderModal() {
  els.renderPercent.textContent = "0%";
  els.renderProgress.style.width = "0%";
  els.renderMessage.textContent = "Preparing critic pass…";
  els.renderResult.hidden = true;
  els.renderError.hidden = true;
  els.cancelRender.hidden = false;
  els.renderClose.disabled = false;
}

async function startRender() {
  resetRenderModal();
  if (!els.renderDialog.open) els.renderDialog.showModal();
  try {
    const response = await api("/api/render", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: project.title, project })
    });
    currentRenderJob = response.id;
    pollRender();
  } catch (error) {
    els.renderError.hidden = false;
    els.renderError.textContent = error.message;
    els.renderMessage.textContent = "Could not start render.";
  }
}

async function pollRender() {
  clearTimeout(renderPollTimer);
  if (!currentRenderJob) return;
  try {
    const job = await api(`/api/render/${currentRenderJob}`);
    const percent = Math.round((job.progress || 0) * 100);
    els.renderPercent.textContent = `${percent}%`;
    els.renderProgress.style.width = `${percent}%`;
    els.renderMessage.textContent = job.message || job.state;
    if (job.state === "complete") {
      currentRenderJob = null;
      els.cancelRender.hidden = true;
      els.renderResult.hidden = false;
      els.downloadRender.href = job.result.downloadUrl;
      els.renderMeta.textContent = `${job.result.width} × ${job.result.height} · ${job.result.fps} fps · ${job.result.duration.toFixed(2)}s · rendered in ${job.result.elapsed.toFixed(1)}s`;
      if (job.postflight && !job.postflight.ok) showReport(job.postflight, "Post-render critic");
      toast("MP4 render complete.", "success");
      return;
    }
    if (job.state === "failed" || job.state === "cancelled") {
      currentRenderJob = null;
      els.cancelRender.hidden = true;
      els.renderError.hidden = false;
      els.renderError.textContent = job.error || `Render ${job.state}.`;
      if (job.preflight && !job.preflight.ok) showReport(job.preflight, "Blocking preflight report");
      return;
    }
    renderPollTimer = setTimeout(pollRender, 700);
  } catch (error) {
    els.renderError.hidden = false;
    els.renderError.textContent = error.message;
    renderPollTimer = setTimeout(pollRender, 1400);
  }
}

async function cancelRender() {
  if (!currentRenderJob) return;
  try {
    await api(`/api/render/${currentRenderJob}/cancel`, { method: "POST" });
    els.renderMessage.textContent = "Cancellation requested…";
  } catch (error) {
    toast(error.message, "error");
  }
}

async function checkHealth() {
  try {
    health = await api("/api/health");
    const coreOk = health.ffmpeg.available;
    els.engineStatus.classList.toggle("ok", coreOk);
    els.engineStatus.classList.toggle("error", !coreOk);
    $("span", els.engineStatus).textContent = coreOk ? "Local engine ready" : "FFmpeg missing";
    if (health.transcription.available) {
      els.transcriptionNote.textContent = `Local Whisper ready${health.transcription.cuda ? " · NVIDIA acceleration detected" : " · CPU mode"}. Auto follows a song that changes language, line by line. First use downloads the model.`;
    } else {
      els.transcriptionNote.textContent = "AI pack not installed. Run install_ai script, then restart Phrasync.";
    }
    if (!health.ocr.available) setAssetStatus("OCR engine not installed. Run the AI installer to enable it.", "error");
  } catch (error) {
    els.engineStatus.classList.add("error");
    $("span", els.engineStatus).textContent = "Backend offline";
    toast(`Backend check failed: ${error.message}`, "error");
  }
}
