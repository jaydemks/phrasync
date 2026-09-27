"use strict";

let completedRenderJob = null;

function desktopExportApi() {
  return window.pywebview?.api || null;
}

async function openRenderDialog() {
  if (currentRenderJob) {
    if (!els.renderDialog.open) els.renderDialog.showModal();
    return;
  }
  resetRenderModal();
  completedRenderJob = null;
  if (!els.renderDialog.open) els.renderDialog.showModal();
  els.chooseRenderDirectory.hidden = !IS_DESKTOP_HOST;
  els.openRenderDirectory.hidden = !IS_DESKTOP_HOST;
  els.openDefaultRenderDirectory.hidden = !IS_DESKTOP_HOST;
  if (IS_DESKTOP_HOST) {
    try {
      els.renderDirectory.textContent = await desktopExportApi().get_render_directory();
    } catch (error) {
      els.renderDirectory.textContent = t("Export folder unavailable");
      toast(error.message, "error");
    }
  } else {
    els.renderDirectory.textContent = t("Browser Downloads folder");
  }
}

async function chooseRenderDirectory() {
  try {
    const directory = await desktopExportApi().choose_render_directory();
    if (directory) els.renderDirectory.textContent = directory;
  } catch (error) {
    toast(error.message, "error");
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
  if (!IS_DESKTOP_HOST) return;
  event.preventDefault();
  if (!completedRenderJob) return;
  try {
    const saved = await desktopExportApi().save_render_as(completedRenderJob);
    if (saved) toast(`${t("MP4 saved to")} ${saved}`, "success");
  } catch (error) {
    toast(error.message, "error");
  }
}

function resetRenderModal() {
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
  if (currentRenderJob) return;
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
      body: JSON.stringify({ title: project.title, project: exportProject })
    });
    currentRenderJob = response.id;
    pollRender();
  } catch (error) {
    els.confirmRender.hidden = false;
    els.cancelRender.hidden = true;
    els.chooseRenderDirectory.disabled = false;
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
      completedRenderJob = job.id;
      currentRenderJob = null;
      els.cancelRender.hidden = true;
      els.chooseRenderDirectory.disabled = false;
      els.renderResult.hidden = false;
      els.downloadRender.href = job.result.downloadUrl;
      els.downloadRender.download = job.result.filename;
      if (job.result.path) els.renderDirectory.textContent = job.result.path.replace(/[\\/][^\\/]+$/, "");
      els.renderMeta.textContent = `${job.result.width} × ${job.result.height} · ${job.result.fps} fps · ${job.result.duration.toFixed(2)}s · rendered in ${job.result.elapsed.toFixed(1)}s`;
      if (job.postflight && !job.postflight.ok) showReport(job.postflight, "Post-render critic");
      toast("MP4 render complete.", "success");
      return;
    }
    if (job.state === "failed" || job.state === "cancelled") {
      currentRenderJob = null;
      els.cancelRender.hidden = true;
      els.confirmRender.hidden = false;
      els.chooseRenderDirectory.disabled = false;
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
