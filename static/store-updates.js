"use strict";

(() => {
  const $ = id => document.getElementById(id);
  const translate = value => typeof window.t === "function" ? window.t(value) : value;
  let packaged = false;
  let available = false;

  function message(value) { $("storeUpdateMessage").textContent = translate(value); }
  function showInstall(value) {
    available = value;
    $("storeUpdateInstall").hidden = !value;
  }
  async function request(path) {
    const response = await fetch(path, { method: path.endsWith("/status") ? "GET" : "POST", cache: "no-store" });
    const data = await response.json();
    if (!response.ok) throw new Error(data.detail || "Microsoft Store could not be reached.");
    return data;
  }

  async function status() {
    showInstall(false);
    try {
      const data = await request("/api/store-updates/status");
      packaged = Boolean(data.packaged);
      $("storeUpdateVersion").textContent = `Phrasync ${data.version}`;
      message(packaged
        ? "Ready to check Microsoft Store for updates."
        : "This is a local preview. Update checks work after installing Phrasync from Microsoft Store.");
      $("storeUpdateCheck").disabled = !packaged;
    } catch (error) {
      message(error.message);
      $("storeUpdateCheck").disabled = true;
    }
  }

  async function check() {
    if (!packaged) return;
    const button = $("storeUpdateCheck");
    button.disabled = true;
    showInstall(false);
    message("Checking Microsoft Store…");
    try {
      const data = await request("/api/store-updates/check");
      showInstall(Boolean(data.available));
      message(data.available ? "A Phrasync update is available." : "Phrasync is up to date.");
    } catch (error) {
      message(error.message);
    } finally {
      button.disabled = false;
    }
  }

  async function install() {
    if (!packaged || !available) return;
    if (!confirm(translate("Install this Phrasync update now? Save your project first; the app may close during installation."))) return;
    const button = $("storeUpdateInstall");
    button.disabled = true;
    message("Microsoft Store is downloading and installing the update. The app may close.");
    try {
      const data = await request("/api/store-updates/install");
      if (data.state === "completed") message("Update installed. Restart Phrasync to use the new version.");
      else if (data.state === "up-to-date") { showInstall(false); message("Phrasync is up to date."); }
      else message(`Microsoft Store update status: ${data.state}.`);
    } catch (error) {
      message(error.message);
    } finally {
      button.disabled = false;
    }
  }

  document.addEventListener("DOMContentLoaded", () => {
    $("settingsButton").addEventListener("click", status);
    $("storeUpdateCheck").addEventListener("click", check);
    $("storeUpdateInstall").addEventListener("click", install);
  });
})();
