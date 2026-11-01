"use strict";

let completedRenderJob = null;
let selectedRenderDirectory = null;
let renderStarting = false;
let choosingRenderDirectory = false;
let renderCancelRequested = false;
const RENDER_BUSY_NOTICE = "Export in progress. Editing is temporarily unavailable. Wait for completion or choose Cancel render to return to the editor.";
Object.assign(ITALIAN,{
  [RENDER_BUSY_NOTICE]:"Esportazione in corso. Le modifiche sono temporaneamente disabilitate. Attendi il completamento oppure scegli Annulla rendering per tornare all’editor.",
  "Cancellation requested…":"Annullamento richiesto…", "Export cancelled. You can edit your project again.":"Esportazione annullata. Puoi modificare nuovamente il progetto.",
  "The export session is no longer available. Your project is unchanged. Start the export again.":"La sessione di esportazione non è più disponibile. Il progetto è rimasto invariato. Avvia di nuovo l’esportazione."
});
function setRenderBusy(busy) {
  const notice=document.getElementById("renderBusyNotice");notice.hidden=!busy;notice.textContent=t(RENDER_BUSY_NOTICE);
  els.renderClose.disabled=busy;els.chooseRenderDirectory.disabled=busy;
  els.renderDirectoryInput.disabled=busy;document.getElementById("manualRenderDirectory").disabled=busy;
}
function closeRenderDialog() {
  if(renderStarting||currentRenderJob){toast(t(RENDER_BUSY_NOTICE));return;}
  els.renderDialog.close();
}
function cancelRenderDialog(event) {
  if(renderStarting||currentRenderJob){event.preventDefault();toast(t(RENDER_BUSY_NOTICE));}
}

function desktopExportApi() {
  return window.pywebview?.api || null;
}

function showManualRenderDirectory() {
  els.renderDirectoryInput.hidden = false; els.renderDirectoryInput.focus();
}

async function openRenderDialog() {
  if (currentRenderJob || renderStarting) {
    if (!els.renderDialog.open) els.renderDialog.showModal();
    return;
  }
  resetRenderModal();
  els.renderMessage.textContent = project.exportRange
    ? `Export: ${formatTime(project.exportRange.in)} → ${formatTime(project.exportRange.out)}`
    : t("Full timeline");
  completedRenderJob = null;
  if (!els.renderDialog.open) els.renderDialog.showModal();
  els.chooseRenderDirectory.hidden = false;
  els.openRenderDirectory.hidden = !IS_DESKTOP_HOST;
  els.openDefaultRenderDirectory.hidden = !IS_DESKTOP_HOST;
  els.renderDirectoryInput.hidden = true;
  document.getElementById("manualRenderDirectory").hidden = IS_DESKTOP_HOST;
  els.downloadRender.textContent = t("Show exported MP4");
  if (IS_DESKTOP_HOST) {
    try {
      selectedRenderDirectory = await desktopExportApi().get_selected_render_directory();
      els.renderDirectory.textContent = selectedRenderDirectory || t("Choose where to save your exports before starting a render.");
    } catch (error) {
      els.renderDirectory.textContent = t("Export folder unavailable");
      toast(error.message, "error");
    }
  } else {
    try {
      const status = await api("/api/export-folder");
      selectedRenderDirectory = els.renderDirectoryInput.value.trim() || status.directory || null;
      els.renderDirectoryInput.value = selectedRenderDirectory || "";
      els.renderDirectory.textContent = selectedRenderDirectory || t("Choose where to save your exports before starting a render.");
      els.chooseRenderDirectory.hidden = !status.available;
      els.renderDirectoryInput.hidden = Boolean(status.available);
    } catch (_) {
      els.chooseRenderDirectory.hidden = true;
      els.renderDirectoryInput.hidden = false;
      els.renderDirectory.textContent = els.renderDirectoryInput.value.trim() || t("Choose where to save your exports before starting a render.");
    }
  }
}

async function chooseRenderDirectory() {
  if (choosingRenderDirectory || currentRenderJob || renderStarting) return;
  choosingRenderDirectory = true;
  els.chooseRenderDirectory.disabled = true;
  els.confirmRender.disabled = true;
  try {
    const directory = IS_DESKTOP_HOST
      ? await desktopExportApi().choose_render_directory()
      : (await api("/api/export-folder/choose", { method: "POST" })).directory;
    if (directory) {
      selectedRenderDirectory = directory; els.renderDirectory.textContent = directory;
      els.renderDirectoryInput.value = directory;
      if (!IS_DESKTOP_HOST) els.renderDirectoryInput.hidden = true;
    }
  } catch (error) {
    if (!IS_DESKTOP_HOST) els.renderDirectoryInput.hidden = false;
    toast(error.message, "error");
  } finally {
    choosingRenderDirectory = false;
    els.chooseRenderDirectory.disabled = false;
    els.confirmRender.disabled = false;
  }
}

async function openRenderDirectory() {
  try {
    await desktopExportApi().open_render_directory(completedRenderJob);
  } catch (error) {
    toast(error.message, "error");
  }
}

async function openDefaultRenderDirectory() {
  try {
    await desktopExportApi().open_default_render_directory();
  } catch (error) {
    toast(error.message, "error");
  }
}

async function downloadRender(event) {
  event.preventDefault();
  if (!completedRenderJob) return;
  try {
    const saved = IS_DESKTOP_HOST ? await desktopExportApi().show_render_file(completedRenderJob)
      : (await api(`/api/render/${completedRenderJob}/show`, { method: "POST" })).path;
    if (saved) toast(`${t("MP4 saved to")} ${saved}`, "success");
  } catch (error) {
    toast(error.message, "error");
  }
}

function resetRenderModal() {
  renderCancelRequested=false;els.cancelRender.disabled=false;setRenderBusy(false);
  els.renderPercent.textContent = "0%";
  els.renderProgress.style.width = "0%";
  els.renderMessage.textContent = t("Choose a folder and start export.");
  els.renderResult.hidden = true;
  els.renderError.hidden = true;
  els.cancelRender.hidden = true;
  els.confirmRender.hidden = false;
  els.chooseRenderDirectory.disabled = false;
  els.renderClose.disabled = false;
}

async function startRender() {
  if (currentRenderJob || renderStarting || choosingRenderDirectory) return;
  const directory = IS_DESKTOP_HOST ? selectedRenderDirectory : els.renderDirectoryInput.value.trim();
  if (!directory) {
    toast(t("Choose where to save your exports before starting a render."), "error"); return;
  }
  renderStarting = true;
  els.renderError.hidden=true;els.renderResult.hidden=true;els.renderPercent.textContent="0%";els.renderProgress.style.width="0%";
  renderCancelRequested=false;els.cancelRender.disabled=false;setRenderBusy(true);
  els.confirmRender.hidden = true;
  els.cancelRender.hidden = false;
  els.chooseRenderDirectory.disabled = true;
  els.renderMessage.textContent = t("Preparing critic pass…");
  try {
    const exportProject = clone(project);
    exportProject.__renderOrigin = window.location.origin;
    const response = await api("/api/render", {
      method: "POST",
      headers: { "Content-Type": "application/json" },
      body: JSON.stringify({ title: project.title, project: exportProject, outputDirectory: directory })
    });
    currentRenderJob = response.id;
    if(renderCancelRequested)await cancelRender();
    pollRender();
  } catch (error) {
    setRenderBusy(false);renderCancelRequested=false;els.cancelRender.disabled=false;
    els.confirmRender.hidden = false;
    els.cancelRender.hidden = true;
    els.chooseRenderDirectory.disabled = false;
    els.renderError.hidden = false;
    els.renderError.textContent = error.message;
    els.renderMessage.textContent = "Could not start render.";
  } finally { renderStarting = false; }
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
      setRenderBusy(false);renderCancelRequested=false;els.cancelRender.disabled=false;
      completedRenderJob = job.id;
      currentRenderJob = null;
      els.cancelRender.hidden = true;
      els.chooseRenderDirectory.disabled = false;
      els.renderResult.hidden = false;
      els.downloadRender.href = "#";
      els.downloadRender.removeAttribute("download");
      if (job.result.path) els.renderDirectory.textContent = job.result.path.replace(/[\\/][^\\/]+$/, "");
      els.renderMeta.textContent = `${job.result.width} × ${job.result.height} · ${job.result.fps} fps · ${job.result.duration.toFixed(2)}s · rendered in ${job.result.elapsed.toFixed(1)}s`;
      if (job.postflight && !job.postflight.ok) showReport(job.postflight, "Post-render critic");
      toast("MP4 render complete.", "success");
      return;
    }
    if (job.state === "failed" || job.state === "cancelled") {
      setRenderBusy(false);renderCancelRequested=false;els.cancelRender.disabled=false;
      currentRenderJob = null;
      els.cancelRender.hidden = true;
      els.confirmRender.hidden = false;
      els.chooseRenderDirectory.disabled = false;
      els.renderError.hidden = false;
      els.renderError.textContent = job.error || `Render ${job.state}.`;
      if(job.state==="cancelled") {els.renderError.hidden=true;els.renderMessage.textContent=t("Export cancelled. You can edit your project again.");}
      if (job.preflight && !job.preflight.ok) showReport(job.preflight, "Blocking preflight report");
      return;
    }
    renderPollTimer = setTimeout(pollRender, 700);
  } catch (error) {
    if([404,410].includes(error.status)){
      currentRenderJob=null;renderCancelRequested=false;setRenderBusy(false);els.cancelRender.hidden=true;els.cancelRender.disabled=false;els.confirmRender.hidden=false;
      els.renderMessage.textContent=t("The export session is no longer available. Your project is unchanged. Start the export again.");
      els.renderError.hidden=true;return;
    }
    els.renderError.hidden = false;
    els.renderError.textContent = error.message;
    renderPollTimer = setTimeout(pollRender, 1400);
  }
}

async function cancelRender() {
  if(renderStarting&&!currentRenderJob){renderCancelRequested=true;els.cancelRender.disabled=true;els.renderMessage.textContent=t("Cancellation requested…");return;}
  if (!currentRenderJob) return;
  els.cancelRender.disabled=true;
  try {
    await api(`/api/render/${currentRenderJob}/cancel`, { method: "POST" });
    els.renderMessage.textContent = t("Cancellation requested…");
  } catch (error) {
    els.cancelRender.disabled=false;
    toast(error.message, "error");
  }
}
