"use strict";

Object.assign(ITALIAN, {
  "Add current visual to bin":"Aggiungi visual corrente alla libreria", "Add background track":"Aggiungi traccia di sfondo",
  "Select an integrated visual above, add it to the bin, then drag it onto a track. Higher tracks appear over lower ones; adjust opacity and transitions to mix them.":"Scegli un visual integrato sopra, aggiungilo alla libreria e trascinalo su una traccia. Le tracce superiori coprono quelle inferiori; regola opacità e transizioni per combinarle.",
  "Track":"Traccia", "Transition":"Transizione", "Cut":"Taglio", "Crossfade":"Dissolvenza", "Wipe":"Tendina", "Slide":"Scorrimento",
  "Clip opacity":"Opacità clip", "Transition in (s)":"Transizione in entrata (s)", "Transition out (s)":"Transizione in uscita (s)",
  "Beat drop zoom (%)":"Drop zoom a tempo (%)", "Beat light pulse (%)":"Impulso luminoso a tempo (%)",
  "Don't show this again":"Non mostrare più", "Maximum four background tracks.":"Massimo quattro tracce di sfondo.",
  "Effect trigger":"Attivazione effetti", "Beat grid":"Griglia dei beat", "Detected audio transients":"Transienti audio rilevati",
  "Remove track":"Rimuovi traccia", "Remove this track and its clips? Original media stays in the bin.":"Rimuovere questa traccia e i suoi clip? I media originali restano nella libreria."
});
async function removeBackgroundTrack(index) {
  const bg = project.background, tracks = bg.tracks || ["V1"];
  if (!Number.isInteger(index) || index < 0 || index >= tracks.length) return;
  const used = (bg.clips || []).some(clip => (clip.track || 0) === index);
  if (used && !await confirmAction("Remove this track and its clips? Original media stays in the bin.")) return;
  if (project.background !== bg) return;
  bg.clips = (bg.clips || []).filter(clip => (clip.track || 0) !== index);
  for (const clip of bg.clips) if ((clip.track || 0) > index) clip.track -= 1;
  bg.tracks = tracks.filter((_,i) => i !== index).map((_,i) => `V${i+1}`);
  if (!bg.tracks.length) bg.footageEnabled = false;
  refreshFootageControls(); footageChanged();
}
// Track indices retain their saved compositing order; screen rows run top-down.
function backgroundTrackRow(track, count=project.background.tracks?.length || 1) {
  return Math.max(1,count)-1-Math.max(0,Math.min(Math.max(1,count)-1,Math.floor(Number(track)||0)));
}
function backgroundTrackAtY(y, count=project.background.tracks?.length || 1) {
  return backgroundTrackRow(Math.floor(Math.max(0,y)/38),count);
}
function refreshVisualTrackControls(clip) {
  const select = document.getElementById("clipTrack"); if (!select) return;
  const tracks = project.background.tracks ||= ["V1"];
  select.replaceChildren();
  [...tracks.keys()].reverse().forEach(i => { const option = document.createElement("option"); option.value=i; option.textContent = `${tracks[i]} · ${t("Track")} ${i+1}`; select.append(option); });
  const manager = document.getElementById("backgroundTrackManager"); manager.replaceChildren();
  [...tracks.keys()].reverse().forEach(i => {
    const name=tracks[i];
    const row = document.createElement("div"), label = document.createElement("span"), remove = document.createElement("button");
    label.textContent = `${name} · ${(project.background.clips || []).filter(c => (c.track||0)===i).length} clips`;
    remove.type="button"; remove.textContent="×"; remove.title=t("Remove track"); remove.setAttribute("aria-label",`${t("Remove track")} ${name}`);
    remove.onclick=()=>removeBackgroundTrack(i); row.append(label,remove); manager.append(row);
  });
  if (clip) { select.value = clip.track || 0; document.getElementById("clipTransition").value = clip.transition || "cut"; }
  document.getElementById("fxTrigger").value = project.background.effects?.trigger || "beat";
}
function initVisualTracks() {
  document.getElementById("fxTrigger").onchange = async event => {
    (project.background.effects ||= {}).trigger = event.target.value;
    if (event.target.value === "transient" && project.audioAssetId) await ensureAnalysis();
    scheduleSave();
  };
  document.getElementById("addVisualTrack").onclick = () => {
    const tracks = project.background.tracks ||= ["V1"];
    if (tracks.length >= 4) return toast(t("Maximum four background tracks."));
    tracks.push(`V${tracks.length+1}`); refreshFootageControls(); footageChanged();
  };
  document.getElementById("addVisualClip").onclick = () => {
    const bg = project.background;
    const label = document.querySelector("#visualSelect option:checked")?.textContent || bg.visual;
    const settings = clone(bg);
    for (const key of ["clips","mediaLibrary","tracks","effects","effectClips","effectSettings","effectOnsets","assetId","url","name","imageAsset","videoAsset"]) delete settings[key];
    const asset = {id:`visual-${crypto.randomUUID()}`,kind:"visual",name:`${label} · ${bg.sceneKit || ""}`,duration:5,size:0,settings};
    (bg.mediaLibrary ||= []).push(asset); refreshFootageControls(); scheduleSave();
  };
  document.getElementById("clipTrack").onchange = event => {
    const clip = selectedFootage(); if (!clip) return;
    clip.track = Number(event.target.value); refreshFootageControls(); footageChanged();
  };
  document.getElementById("clipTransition").onchange = event => {
    const clip = selectedFootage(); if (!clip) return;
    clip.transition = event.target.value;
    if (clip.transition !== "cut" && !(clip.fadeIn > 0)) clip.fadeIn = .35;
    refreshFootageControls(); footageChanged();
  };
}
