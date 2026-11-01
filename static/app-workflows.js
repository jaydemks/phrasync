"use strict";
let transcriptionStarting=false,transcriptionCancelRequested=false,transcriptionPollErrorShown=false;
async function handleAudioFile(file) {
  if (!file) return;
  const request=beginProjectOperation("audio-import",{source:false});
  setAssetStatus(`Uploading ${file.name}…`);
  try {
    const video = project.mode === "subtitles" && isVideoUpload(file);
    if (video) await assertBrowserPreviewableVideo(file);
    const kind = video ? "video" : "audio";
    const asset = await uploadAsset(kind, file);
    if(!request.valid())return;
    project.audioAssetId = asset.id;
    project.audio = asset;
    project.sourceAssetId = asset.id;
    project.sourceKind = kind;
    if (video) {
      project.background.type = "video";
      project.background.footageEnabled = false;
      project.background.videoAsset = asset;
      project.background.assetId = asset.id;
      project.background.url = asset.url;
      project.background.name = asset.name;
    }
    analysis = null;
    if (asset.duration) project.duration = asset.duration;
    if (video) { attachBackgroundAsset(asset); refreshFootageControls(); }
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
  const request=beginProjectOperation("background-import",{source:false});
  const kind = project.background.type;
  setAssetStatus(`Uploading ${file.name}…`);
  try {
    if (project.background.type === "video") await assertBrowserPreviewableVideo(file);
    const asset = await uploadAsset(kind, file);
    if(!request.valid()||project.background.type!==kind)return;
    attachBackgroundAsset({...asset,kind});
    refreshFootageControls(); applyBackgroundPreview(); footageChanged();
    setAssetStatus(`${kind[0].toUpperCase() + kind.slice(1)} background ready.`, "success");
  } catch (error) {
    setAssetStatus(error.message, "error");
    toast(error.message, "error");
  }
}
async function handleOCRFile(file) {
  if (!file) return;
  const request=beginProjectOperation("ocr-import",{source:false});
  els.ocrPick.disabled = true;
  setAssetStatus(`Reading ${file.name} with local OCR…`);
  try {
    const asset = await uploadAsset("image", file);
    const result = await api("/api/ocr", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ assetId: asset.id, language: "auto" })
    });
    if(!request.valid())return;
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
  const request=beginProjectOperation("lyrics-import",{source:false});
  setAssetStatus(`Importing ${file.name}…`);
  try {
    const asset = await uploadAsset("lyrics", file);
    const result = await api("/api/lyrics/import", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ assetId: asset.id, duration: projectDuration() })
    });
    if(!request.valid())return;
    if (!result.cues?.length) throw new Error("No lyrics were found. Check the file's text and timestamp format.");
    project.cues = result.cues;
    selectedCueId = project.cues[0]?.id || null;
    renderCueList(); updateDurationUI(); seekTo(0); scheduleSave();
    setAssetStatus(`Imported ${project.cues.length} ${project.mode === "subtitles" ? "subtitle" : "lyric"} cues.`, "success");
    // Timed imports are authoritative, including Enhanced LRC word timing.
    // Only plain text needs automatic alignment; timed files can be aligned
    // explicitly by the user without silently changing their supplied times.
    if (/\.txt$/i.test(file.name)) await runAutoAlign({ auto: true });
  } catch (error) {
    setAssetStatus(error.message, "error");
    toast(error.message, "error");
  } finally {
    els.lyricsInput.value = "";
  }
}

async function handleFontFile(file) {
  if (!file) return;
  const request=beginProjectOperation("font-import",{source:false});
  setAssetStatus(`Uploading ${file.name}…`);
  try {
    const asset = await uploadAsset("font", file);
    if(!request.valid())return;
    await useCustomFont(asset);
  } catch (error) {
    setAssetStatus(error.message, "error");
    toast(error.message, "error");
  } finally {
    els.fontInput.value = "";
  }
}

Object.assign(ITALIAN, {
  "Generate lyrics": "Genera il testo", "Generate subtitles": "Genera sottotitoli",
  "Generating lyrics…": "Generazione del testo…", "Generating subtitles…": "Generazione sottotitoli…",
  "Downloading model…": "Download del modello…",
  "AI lyrics": "Testo con AI", "AI subtitles": "Sottotitoli con AI", "AI model": "Modello AI",
  "Runs on your computer. First use downloads the selected model.": "Elaborazione sul tuo computer. Al primo utilizzo viene scaricato il modello scelto.",
  "Tiny · Quick draft": "Tiny · Bozza rapida", "Base · Everyday": "Base · Equilibrato",
  "Small · More detail": "Small · Più dettaglio", "Medium · High accuracy": "Medium · Alta precisione",
  "Large v3 · Highest accuracy": "Large v3 · Massima precisione",
  "Fast drafts with the lowest memory use. Review names and sung words carefully.": "Bozze veloci con un uso minimo di memoria. Ricontrolla nomi e parole cantate.",
  "A balanced starting point. Larger models can improve accuracy but need more time and memory.": "Un punto di partenza equilibrato. I modelli più grandi possono migliorare la precisione, ma richiedono più tempo e memoria.",
  "More detail than Base, with moderate processing time and memory use.": "Più dettaglio di Base, con tempi e memoria intermedi.",
  "Higher accuracy for difficult audio. Needs more memory and processing time.": "Più precisione con audio difficile. Richiede più memoria e tempo di elaborazione.",
  "Our highest-accuracy option. Best with a capable GPU; allow more time on CPU.": "L'opzione più precisa. Consigliata una GPU adeguata; con la CPU serve più tempo."
});

function setTranscriptionButtonState(busy, phase = "") {
  const key = busy ? (phase === "model-download" ? "Downloading model…"
    : project.mode === "subtitles" ? "Generating subtitles…" : "Generating lyrics…")
    : MODE_COPY[project.mode]?.transcribe || "Generate lyrics";
  document.getElementById("transcribeButtonLabel").textContent = t(key);
  els.transcribeButton.classList.toggle("is-generating", Boolean(busy));
  els.transcribeButton.setAttribute("aria-busy", String(Boolean(busy)));
}

function updateModelInsight() {
  const copy = {
    tiny: "Fast drafts with the lowest memory use. Review names and sung words carefully.",
    base: "A balanced starting point. Larger models can improve accuracy but need more time and memory.",
    small: "More detail than Base, with moderate processing time and memory use.",
    medium: "Higher accuracy for difficult audio. Needs more memory and processing time.",
    "large-v3": "Our highest-accuracy option. Best with a capable GPU; allow more time on CPU."
  };
  document.getElementById("modelInsight").textContent = t(copy[els.whisperModel.value] || copy.base);
}

function updateTranscriptionProgress(job) {
  setTranscriptionButtonState(true, job.phase);
  const downloading = job.phase === "model-download";
  const unknown = downloading && !(job.total_bytes > 0);
  const ratio = downloading ? (job.total_bytes > 0 ? job.downloaded_bytes / job.total_bytes : 0) : Number(job.progress || 0);
  const percent = Math.max(0, Math.min(downloading ? 99 : 100, Math.round(ratio * 100)));
  els.transcriptionProgress.hidden = false;
  els.transcriptionMessage.textContent = formatTranscriptionJob(job);
  els.transcriptionPercent.value = unknown ? "…" : `${percent}%`;
  els.transcriptionProgressBar.style.width = `${percent}%`;
  els.transcriptionTrack.setAttribute("aria-valuenow", String(percent));
  els.transcriptionTrack.classList.toggle("indeterminate", unknown);
  if (unknown) els.transcriptionTrack.removeAttribute("aria-valuenow");
}

function finishTranscriptionControls() {
  transcriptionCancelRequested=false;transcriptionPollErrorShown=false;
  if (transcriptionPollTimer) clearTimeout(transcriptionPollTimer);
  transcriptionPollTimer = null;
  currentTranscriptionJob = null;
  els.transcribeButton.disabled = false;
  setTranscriptionButtonState(false);
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
  const id=currentTranscriptionJob;
  let received=false;
  try {
    const job = await api(`/api/transcriptions/${id}`);
    received=true;
    if(id!==currentTranscriptionJob)return;
    transcriptionPollErrorShown=false;
    updateTranscriptionProgress(job);
    if (job.state === "complete") {
      if(projectOperationMatches("transcription"))applyTranscriptionResult(job.result);
      else toast(t("The source changed. The previous transcription was not applied."));
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
    if(id!==currentTranscriptionJob)return;
    if(received||[404,410].includes(error.status)){toast(error.message,"error");finishTranscriptionControls();return;}
    setAssetStatus(error.message, "error");
    if(!transcriptionPollErrorShown)toast(error.message, "error");transcriptionPollErrorShown=true;
    transcriptionPollTimer=setTimeout(pollTranscription,1400);
  }
}

async function transcribeSong() {
  if (!project.audioAssetId) {
    return toast(project.mode === "subtitles"
      ? "Add a video or audio file before transcription."
      : "Add a song before transcription.", "error");
  }
  if (currentTranscriptionJob || transcriptionStarting) return;
  const request=beginProjectOperation("transcription");transcriptionStarting=true;transcriptionCancelRequested=false;
  els.transcribeButton.disabled = true;
  setTranscriptionButtonState(true);
  els.cancelTranscription.hidden = false;
  els.transcriptionProgress.hidden = false;
  updateTranscriptionProgress({ progress: 0, message: "Creating transcription job" });
  setAssetStatus(document.documentElement.lang === "it"
    ? "Whisper preparerà la trascrizione e i tempi. Al primo utilizzo, il download del modello mostrerà percentuale e tempo rimanente."
    : `Whisper is preparing the ${project.sourceKind === "video" ? "video" : "audio"} transcription and timing. The first model download will show progress and estimated time remaining.`);
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
    if(transcriptionCancelRequested||!request.valid())await stopTranscription();
    updateTranscriptionProgress(job);
    pollTranscription();
  } catch (error) {
    setAssetStatus(error.message, "error");
    toast(error.message, "error");
    finishTranscriptionControls();
  } finally {transcriptionStarting=false;}
}

async function stopTranscription() {
  if(transcriptionStarting&&!currentTranscriptionJob){transcriptionCancelRequested=true;els.cancelTranscription.disabled=true;return;}
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

async function checkHealth() {
  try {
    health = await api("/api/health");
    const coreOk = health.ffmpeg.available;
    els.engineStatus.classList.toggle("ok", coreOk);
    els.engineStatus.classList.toggle("error", !coreOk);
    $("span", els.engineStatus).textContent = t(coreOk ? "Local engine ready" : "FFmpeg missing");
    if (health.transcription.available) {
      const gpuReady = Boolean(health.transcription.cuda);
      els.transcriptionNote.textContent = document.documentElement.lang === "it"
        ? `Whisper locale pronto · ${gpuReady ? "accelerazione NVIDIA CUDA attiva" : "modalità CPU"}. La prima trascrizione scarica il modello mostrando avanzamento e tempo stimato.`
        : `Local Whisper ready · ${gpuReady ? "NVIDIA CUDA acceleration active" : "CPU mode"}. The first transcription downloads the model with progress and estimated time remaining.`;
      els.engineStatus.title = health.transcription.gpu?.reason || t("Local engine status");
    } else {
      els.transcriptionNote.textContent = document.documentElement.lang === "it"
        ? "Componenti AI non installati. Reinstalla Phrasync o esegui lo script install_ai, quindi riavvia."
        : "AI pack not installed. Reinstall Phrasync or run the install_ai script, then restart.";
    }
    if (!health.ocr.available) setAssetStatus("OCR engine not installed. Run the AI installer to enable it.", "error");
  } catch (error) {
    els.engineStatus.classList.add("error");
    $("span", els.engineStatus).textContent = "Backend offline";
    toast(`Backend check failed: ${error.message}`, "error");
  }
}
