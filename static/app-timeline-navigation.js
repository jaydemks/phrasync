"use strict";

Object.assign(ITALIAN, {
  "Timeline navigation":"Navigazione timeline", "Zoom out":"Riduci zoom", "Zoom in":"Aumenta zoom",
  "Timeline zoom":"Zoom timeline", "Visible timeline duration":"Durata visibile sulla timeline",
  "Zoom out (-)":"Riduci zoom (-)", "Zoom in (+)":"Aumenta zoom (+)",
  "Fit all (Backslash / Shift+Z)":"Mostra tutto (barra inversa / Shift+Z)", "Fit selection (F)":"Inquadra selezione (F)",
  "Fit IN/OUT (Shift+R)":"Inquadra IN/OUT (Shift+R)", "Center playhead (Shift+P)":"Centra cursore (Shift+P)",
  "Pan left (Page Up)":"Scorri a sinistra (Pag su)", "Pan right (Page Down)":"Scorri a destra (Pag giù)",
  "Fit all":"Mostra tutto", "Fit selection":"Inquadra selezione", "Fit IN/OUT":"Inquadra IN/OUT",
  "Playhead":"Cursore", "Pan left":"Scorri a sinistra", "Pan right":"Scorri a destra",
  "Select a lyric, footage clip or effect first.":"Seleziona prima un testo, un clip di sfondo o un effetto.",
  "Set an IN/OUT range first.":"Imposta prima un intervallo IN/OUT.",
  "Zoom around the playhead. Ctrl/Cmd + wheel zooms at the pointer on every track.":"Zoom intorno al cursore. Ctrl/Cmd + rotella ingrandisce al puntatore su tutte le tracce."
});

window.VFTimelineNavigation = (() => {
  let selectionLane="lyric";
  const minimum=()=>timeline.minSpan || 2/(project.canvas.fps||30);
  function zoom(factor) {
    if(!timeline)return;
    timeline.follow=false;
    const span=Math.max(minimum(),Math.min(timeline.duration(),timeline.viewSpan*factor));
    if(span>=timeline.duration())return timeline.fitAll();
    const time=currentPlaybackTime()-(project.timing.offset||0);
    timeline.setView(time-span/2,span);
  }
  function pan(direction) {
    if(!timeline)return;timeline.follow=false;
    timeline.setView(timeline.viewStart+direction*timeline.viewSpan*.8,timeline.viewSpan);
  }
  function fitAll() { if(timeline){timeline.follow=false;timeline.fitAll()} }
  function fitInterval(start,end) {
    if(!timeline || !Number.isFinite(start) || !(end>start))return;
    const length=end-start, padding=Math.max(minimum(),length*.12),offset=project.timing.offset||0;
    timeline.follow=false;timeline.setView(start-offset-padding,Math.max(minimum(),length+2*padding));
  }
  function fitSelection() {
    const clip=selectionLane==="footage"?selectedFootage():selectionLane==="effect"?selectedEffect():selectedCue();
    if(!clip)return toast(t("Select a lyric, footage clip or effect first."));
    const offset=selectionLane==="lyric"?(project.timing.offset||0):0;
    fitInterval(Number(clip.start)+offset,Number(clip.end)+offset);
  }
  function fitRange() {
    if(!project.exportRange)return toast(t("Set an IN/OUT range first."));
    fitInterval(project.exportRange.in,project.exportRange.out);
  }
  function center() {
    if(!timeline)return;timeline.follow=false;
    timeline.focusTime(currentPlaybackTime()-(project.timing.offset||0));
  }
  function refresh() {
    const slider=document.getElementById("timelineZoom");if(!slider||!timeline)return;
    const max=timeline.duration(),min=minimum();
    slider.value=max>min?Math.max(0,Math.min(100,100*Math.log(max/timeline.viewSpan)/Math.log(max/min))):0;
    document.getElementById("timelineSpan").textContent=`${timeline.viewSpan.toFixed(2)} s`;
  }
  function init() {
    const actions={navZoomOut:()=>zoom(1.5),navZoomIn:()=>zoom(1/1.5),navFitAll:fitAll,
      navFitSelection:fitSelection,navFitRange:fitRange,navPlayhead:center,navPanLeft:()=>pan(-1),navPanRight:()=>pan(1)};
    for(const[id,action]of Object.entries(actions))document.getElementById(id).addEventListener("click",action);
    document.getElementById("timelineZoom").addEventListener("input",event=>{
      if(!timeline)return;
      const max=timeline.duration(),min=minimum(),span=max*Math.pow(min/max,Number(event.target.value)/100);
      timeline.follow=false;
      if(Number(event.target.value)===0)return timeline.fitAll();
      timeline.setView(currentPlaybackTime()-(project.timing.offset||0)-span/2,span);
    });
    const remember=event=>{
      if(event.target.closest("#effectsLane,#effectClipControls,#effectAdd"))selectionLane="effect";
      else if(event.target.closest("#footageLane,#footageClipEditor,#clipLayerSettings,#footageSelect,#footageTools,#footageBin"))selectionLane="footage";
      else if(event.target.closest("#timelineWrap,#cueList"))selectionLane="lyric";
    };
    document.addEventListener("pointerdown",remember,true);document.addEventListener("focusin",remember);
    document.addEventListener("keydown",event=>{
      if(event.defaultPrevented||event.ctrlKey||event.metaKey||event.altKey||event.isComposing
        ||event.target.isContentEditable||event.target.closest("input,textarea,select,[contenteditable]")||document.querySelector("dialog[open]"))return;
      const key=event.key.toLowerCase();let action;
      if(["+","="].includes(key)||event.code==="NumpadAdd")action=()=>zoom(1/1.5);
      else if(key==="-"||event.code==="NumpadSubtract")action=()=>zoom(1.5);
      else if(key==="\\"||(key==="z"&&event.shiftKey))action=fitAll;
      else if(key==="f"&&!event.shiftKey)action=fitSelection;
      else if(key==="r"&&event.shiftKey)action=fitRange;
      else if(key==="p"&&event.shiftKey)action=center;
      else if(key==="pageup")action=()=>pan(-1);
      else if(key==="pagedown")action=()=>pan(1);
      if(action){event.preventDefault();event.stopImmediatePropagation();action()}
    },true);
    refresh();
  }
  return {init,refresh,zoom,pan,fitAll,fitSelection,fitRange,center,selectLane:lane=>{selectionLane=lane}};
})();
