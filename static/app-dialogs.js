"use strict";

Object.assign(ITALIAN, {
  "Confirm action": "Conferma operazione", "Continue": "Continua",
  "Save and stop Phrasync": "Salva e arresta Phrasync",
  "Keep the current session on this computer and stop Phrasync? This does not create a separate project file.": "Conservare la sessione attuale su questo computer e arrestare Phrasync? Non viene creato un file di progetto separato.",
  "Stop the running export or transcription before closing Phrasync.": "Interrompi l'esportazione o la trascrizione in corso prima di chiudere Phrasync.",
  "Phrasync stopped.": "Phrasync arrestato.",
  "Your session is saved on this computer. You can close this window.": "La sessione è salvata su questo computer. Puoi chiudere questa finestra.",
  "Your session is saved on this computer. You can close this tab.": "La sessione è salvata su questo computer. Puoi chiudere questa scheda.",
  "Remove the saved Hugging Face token from this computer?": "Rimuovere il token Hugging Face salvato su questo computer?"
});

let appConfirmationOpen = false;

function confirmAction(message, { title = "Confirm action", action = "Continue" } = {}) {
  if (appConfirmationOpen) return Promise.resolve(false);
  appConfirmationOpen = true;
  return new Promise(resolve => {
    const opener = document.activeElement;
    const dialog = document.createElement("dialog");
    dialog.id = "appConfirmDialog"; dialog.className = "modal app-confirm-modal";
    dialog.setAttribute("aria-labelledby", "appConfirmTitle");
    dialog.setAttribute("aria-describedby", "appConfirmMessage");
    const form = document.createElement("form"); form.method = "dialog"; form.className = "modal-card";
    const header = document.createElement("header"), heading = document.createElement("h2");
    heading.id = "appConfirmTitle"; heading.textContent = t(title); header.append(heading);
    const text = document.createElement("p"); text.id = "appConfirmMessage"; text.textContent = t(message);
    const footer = document.createElement("footer");
    const cancel = document.createElement("button"); cancel.type = "submit"; cancel.value = "cancel";
    cancel.className = "button secondary"; cancel.textContent = t("Cancel"); cancel.autofocus = true;
    const accept = document.createElement("button"); accept.type = "submit"; accept.value = "confirm";
    accept.className = "button primary"; accept.textContent = t(action);
    footer.append(cancel, accept); form.append(header, text, footer); dialog.append(form);
    const finish = accepted => {
      dialog.remove(); appConfirmationOpen = false;
      if (opener?.isConnected) opener.focus({ preventScroll: true });
      resolve(accepted);
    };
    dialog.addEventListener("close", () => finish(dialog.returnValue === "confirm"), { once: true });
    dialog.addEventListener("cancel", () => { dialog.returnValue = "cancel"; });
    document.body.append(dialog);
    try { dialog.showModal(); cancel.focus(); }
    catch (_) { finish(false); }
  });
}

async function shutdownServer() {
  const busy=()=>currentRenderJob||currentTranscriptionJob||(typeof renderStarting!=="undefined"&&renderStarting)||(typeof transcriptionStarting!=="undefined"&&transcriptionStarting);
  if (busy()) return toast(t("Stop the running export or transcription before closing Phrasync."), "error");
  if (!await confirmAction("Keep the current session on this computer and stop Phrasync? This does not create a separate project file.", { title: "Save and stop Phrasync", action: "Save and stop Phrasync" })) return;
  if (busy()) return toast(t("Stop the running export or transcription before closing Phrasync."), "error");
  try {
    localStorage.setItem(STORAGE_KEY, JSON.stringify(project));
    const response = await fetch("/api/shutdown", { method: "POST" });
    if (!response.ok) throw new Error(await response.text());
    document.body.replaceChildren(Object.assign(document.createElement("main"), { className: "shutdown-screen" }));
    const heading = document.createElement("h1"); heading.textContent = t("Phrasync stopped.");
    const note = document.createElement("p"); note.textContent = t(IS_DESKTOP_HOST ? "Your session is saved on this computer. You can close this window." : "Your session is saved on this computer. You can close this tab.");
    document.body.firstChild.append(heading, note);
  } catch (error) {
    toast(`Could not stop Phrasync: ${error.message}`, "error");
  }
}
