"use strict";
const effectNames={drop:"Drop zoom",pulse:"Light pulse",flash:"Flash",lightLeak:"Light leak",shake:"Camera shake",pendulum:"Pendulum",gradient:"Gradient",particles:"Particles",spectrum:"Audio spectrum",bw:"Black & white",rain:"Rain",snow:"Snow",fog:"Fog",storm:"Storm",leaves:"Falling leaves"};
const effectModes={"one-shot":"Single hit",constant:"Continuous",beat:"Beat grid",transient:"Audio transients",audio:"Audio energy",off:"Off"};
let selectedEffectId=null,effectDrag=null,effectLaneKey="";
Object.assign(ITALIAN,{
  "Effects timeline":"Timeline effetti","Add FX at playhead":"Aggiungi FX al cursore","Drop zoom":"Zoom drop","Light pulse":"Impulso luminoso","Light leak":"Bagliore luminoso","Camera shake":"Movimento camera","Pendulum":"Pendolo","Gradient":"Gradiente","Audio spectrum":"Spettro audio",
  "Single hit":"Colpo singolo","Continuous":"Continuo","Audio transients":"Transienti audio","Audio energy":"Energia audio","Default timing":"Tempo predefinito","Effect timing":"Sincronizzazione effetto","Beat spacing":"Intervallo beat",
  "Timeline effect controls":"Controlli effetto in timeline","Select an effect":"Seleziona un effetto","Intensity":"Intensità","Start (s)":"Inizio (s)","End (s)":"Fine (s)","Fade in (s)":"Entrata (s)","Fade out (s)":"Uscita (s)","Duplicate effect":"Duplica effetto","Remove effect":"Rimuovi effetto","Enabled":"Attivo","Loop video":"Ripeti video","Light leak (%)":"Bagliore luminoso (%)",
  "Drag FX to move; drag edges to resize. Alt disables snapping.":"Trascina gli FX per spostarli, i bordi per ridimensionarli. Alt disattiva lo snap.",
  "Timeline effects are independent of global effects. Set a global intensity to 0 for isolated hits.":"Gli effetti in timeline sono indipendenti da quelli globali. Imposta un'intensità globale a 0 per ottenere colpi isolati.",
  "Global effect timing":"Sincronizzazione effetti globali","Maximum 256 timeline effects.":"Massimo 256 effetti in timeline."
});
function selectedEffect(){return(project.background.effectClips||[]).find(c=>c.id===selectedEffectId)}
function effectChanged(){effectLaneKey="";renderEffectsLane();updateDurationUI();scheduleSave()}
function addTimelineEffect(){
  const clips=project.background.effectClips ||= [];if(clips.length>=256)return toast(t("Maximum 256 timeline effects."),"error");
  const kind=document.getElementById("effectKind").value,start=Math.max(0,currentPlaybackTime()),duration=["particles","gradient","spectrum","bw","rain","snow","fog","storm","leaves"].includes(kind)?5:.8;
  const occupied=new Set(clips.filter(c=>c.start<start+duration&&c.end>start).map(c=>c.track||0));
  const clip={id:crypto.randomUUID(),kind,start,end:start+duration,amount:Math.round(window.VFEffects.limits[kind]*.6),mode:"one-shot",division:1,attack:.025,release:duration*.8,track:[0,1,2,3].find(i=>!occupied.has(i))??3,enabled:true};
  clips.push(clip);selectedEffectId=clip.id;document.getElementById("footageSection").open=true;document.getElementById("effectClipControls").open=true;refreshEffectControls();effectChanged();document.getElementById("effectClipControls").scrollIntoView({block:"nearest"});
}
function refreshEffectControls(){
  const select=document.getElementById("effectClipSelect");if(!select)return;
  const clip=selectedEffect(),clips=project.background.effectClips||[];select.replaceChildren(new Option(t("Select an effect"),""));
  for(const item of clips)select.add(new Option(`${item.start.toFixed(2)}s · ${t(effectNames[item.kind])}`,item.id));select.value=clip?.id||"";
  document.getElementById("effectInspector").hidden=!clip;
  for(const id of ["effectDuplicate","effectRemove","effect-enabled"])document.getElementById(id).disabled=!clip;
  if(clip){for(const key of ["start","end","amount","attack","release","mode","division","track"]){
    const el=document.getElementById(`effect-${key}`);el.value=clip[key]??(key==="division"?1:0);
    if(el.type==="number")el.max=key==="amount"?window.VFEffects.limits[clip.kind]:Math.max(projectDuration()+5,clip.end+5);
  }document.getElementById("effect-enabled").checked=clip.enabled!==false;}
  for(const key of Object.keys(effectNames)){document.getElementById(`effectTiming-${key}`).value=project.background.effectSettings?.[key]?.mode||"default";document.getElementById(`effectDivision-${key}`).value=project.background.effectSettings?.[key]?.division||1;}
  syncNumericSliders();effectLaneKey="";renderEffectsLane();
}
function effectPosition(el,clip,lane){
  el.style.left=`${(clip.start-(project.timing.offset||0)-timeline.viewStart)/timeline.viewSpan*lane.clientWidth}px`;
  el.style.width=`${Math.max(6,(clip.end-clip.start)/timeline.viewSpan*lane.clientWidth)}px`;el.style.top=`${3+(clip.track||0)*34}px`;
}
function renderEffectsLane(){
  const lane=document.getElementById("effectsLane");if(!lane||!timeline||(effectDrag&&!effectDrag.pan))return;
  const clips=project.background.effectClips||[],key=JSON.stringify([timeline.viewStart,timeline.viewSpan,project.timing.offset,lane.clientWidth,selectedEffectId,clips]);if(key===effectLaneKey)return;effectLaneKey=key;lane.replaceChildren();
  lane.style.height=`${34*Math.max(1,...clips.map(c=>(c.track||0)+1))}px`;
  if(!clips.length){const hint=document.createElement("span");hint.className="fx-lane-hint";hint.textContent=t("Add FX at playhead");lane.append(hint);}
  for(const clip of clips){
    const offset=project.timing.offset||0;if(clip.end-offset<timeline.viewStart||clip.start-offset>timeline.viewStart+timeline.viewSpan)continue;
    const el=document.createElement("div");el.className=`effect-block${clip.id===selectedEffectId?" selected":""}${clip.enabled===false?" disabled":""}`;el.dataset.id=clip.id;el.tabIndex=0;el.setAttribute("role","button");
    el.title=`${t(effectNames[clip.kind])} · ${clip.start.toFixed(2)}–${clip.end.toFixed(2)}s · ${clip.amount}`;
    const text=document.createElement("span");text.textContent=`FX${(clip.track||0)+1} · ${t(effectNames[clip.kind])}`;
    for(const edge of ["start","end"]){const h=document.createElement("i");h.className=`footage-edge ${edge}`;h.dataset.edge=edge;el.append(h);}el.append(text);effectPosition(el,clip,lane);lane.append(el);
  }
}
function initEffectTracks(){
  const kind=document.getElementById("effectKind");for(const[key,name]of Object.entries(effectNames))kind.add(new Option(t(name),key));
  document.getElementById("effectAdd").onclick=addTimelineEffect;
  document.getElementById("effectClipSelect").onchange=e=>{selectedEffectId=e.target.value;refreshEffectControls()};
  const fields=document.getElementById("effectInspector");
  function selectField(key,label,options){
    const row=document.createElement("label");row.className="field";const span=document.createElement("span");span.textContent=t(label);const input=document.createElement("select");input.id=`effect-${key}`;
    for(const[value,text]of Object.entries(options))input.add(new Option(t(text),value));
    input.onchange=()=>{const clip=selectedEffect();if(!clip)return;clip[key]=key==="mode"?input.value:Number(input.value);if(input.value==="transient"&&project.audioAssetId)ensureAnalysis();effectChanged()};row.append(span,input);fields.append(row);
  }
  selectField("mode","Effect timing",effectModes);selectField("division","Beat spacing",{.25:"1/4 beat",.5:"1/2 beat",1:"1 beat",2:"2 beats",4:"4 beats",8:"8 beats"});selectField("track","Track",{0:"FX1",1:"FX2",2:"FX3",3:"FX4"});
  for(const[key,label]of [["start","Start (s)"],["end","End (s)"],["amount","Intensity"],["attack","Fade in (s)"],["release","Fade out (s)"]]){
    const row=document.createElement("label");row.className="field";const span=document.createElement("span");span.textContent=t(label);const input=document.createElement("input");input.type="number";input.id=`effect-${key}`;input.min=0;input.step=key==="amount"?1:.01;
    input.onchange=()=>{const clip=selectedEffect();if(!clip)return;const value=Math.max(0,Number(input.value)||0);clip[key]=key==="amount"?Math.min(window.VFEffects.limits[clip.kind],value):Math.min(86399,value);if(clip.end<=clip.start+.01)clip.end=clip.start+.05;refreshEffectControls();effectChanged()};row.append(span,input);fields.append(row);
  }
  document.getElementById("effect-enabled").onchange=e=>{const clip=selectedEffect();if(clip){clip.enabled=e.target.checked;effectChanged()}};
  document.getElementById("effectRemove").onclick=()=>{project.background.effectClips=(project.background.effectClips||[]).filter(c=>c.id!==selectedEffectId);selectedEffectId=null;refreshEffectControls();effectChanged()};
  document.getElementById("effectDuplicate").onclick=()=>{const clip=selectedEffect();if(!clip)return;const clips=project.background.effectClips;if(clips.length>=256)return toast(t("Maximum 256 timeline effects."),"error");const copy=clone(clip);copy.id=crypto.randomUUID();copy.start=clip.end;copy.end=copy.start+clip.end-clip.start;clips.push(copy);selectedEffectId=copy.id;refreshEffectControls();effectChanged()};
  const globals=document.getElementById("globalEffectTiming");
  for(const[key,name]of Object.entries(effectNames)){
    const row=document.createElement("label");row.className="field";const span=document.createElement("span");span.textContent=t(name);
    const mode=document.createElement("select");mode.id=`effectTiming-${key}`;mode.setAttribute("aria-label",`${t(name)} · ${t("Effect timing")}`);
    for(const[v,label]of Object.entries({default:"Default timing",constant:"Continuous",beat:"Beat grid",transient:"Audio transients",audio:"Audio energy",off:"Off"}))mode.add(new Option(t(label),v));
    const division=document.createElement("select");division.id=`effectDivision-${key}`;division.setAttribute("aria-label",`${t(name)} · ${t("Beat spacing")}`);for(const v of [.25,.5,1,2,4,8])division.add(new Option(`${v} × beat`,v));
    const commit=async()=>{const settings=project.background.effectSettings ||= {};if(mode.value==="default")delete settings[key];else settings[key]={mode:mode.value,division:Number(division.value)};if(mode.value==="transient"&&project.audioAssetId)await ensureAnalysis();effectChanged()};mode.onchange=commit;division.onchange=commit;row.append(span,mode,division);globals.append(row);
  }
  const lane=document.getElementById("effectsLane");
  lane.onpointerdown=e=>{
    if(e.button===1){e.preventDefault();lane.setPointerCapture(e.pointerId);effectDrag={pan:true,x:e.clientX,start:timeline.viewStart};timeline.follow=false;return;}
    if(e.button!==0)return;const block=e.target.closest(".effect-block");if(!block){seekTo(timeline.xToTime(e.clientX-lane.getBoundingClientRect().left)+(project.timing.offset||0));return;}
    selectedEffectId=block.dataset.id;refreshEffectControls();lane.focus();lane.setPointerCapture(e.pointerId);effectDrag={x:e.clientX,original:clone(selectedEffect()),mode:e.target.dataset.edge||"move"};
  };
  lane.onpointermove=e=>{
    if(!effectDrag)return;const delta=(e.clientX-effectDrag.x)/Math.max(1,lane.clientWidth)*timeline.viewSpan;if(effectDrag.pan){timeline.setView(effectDrag.start-delta,timeline.viewSpan);return;}
    const clip=selectedEffect(),o=effectDrag.original;if(!clip)return;let target=Math.max(0,(effectDrag.mode==="end"?o.end:o.start)+delta);
    if(!e.altKey&&project.timing.snapMode!=="off"){
      const bpm=project.timing.bpm,period=60/bpm,beat=bpm>0?Math.round((target-(project.timing.beatOffset||0))/period)*period+(project.timing.beatOffset||0):target;
      const edges=[beat,...(project.background.clips||[]).flatMap(c=>[c.start,c.end])],closest=edges.reduce((a,b)=>Math.abs(b-target)<Math.abs(a-target)?b:a,target+100);
      if(Math.abs(closest-target)<timeline.viewSpan/lane.clientWidth*8)target=Math.max(0,closest);
    }
    if(effectDrag.mode==="move"){clip.start=target;clip.end=target+o.end-o.start;clip.track=Math.max(0,Math.min(3,Math.floor((e.clientY-lane.getBoundingClientRect().top)/34)));}else if(effectDrag.mode==="start")clip.start=Math.min(o.end-.05,target);else clip.end=Math.max(o.start+.05,target);
    const block=lane.querySelector(`[data-id="${clip.id}"]`);if(block)effectPosition(block,clip,lane);
  };
  const release=()=>{if(!effectDrag)return;effectDrag=null;refreshEffectControls();effectChanged()};lane.onpointerup=release;lane.onpointercancel=release;lane.onlostpointercapture=release;
  lane.onauxclick=e=>{if(e.button===1)e.preventDefault()};lane.onwheel=e=>{e.preventDefault();timeline.follow=false;if(e.ctrlKey||e.metaKey)timeline.zoomAt(e.deltaY>0?1.18:.85,e.clientX-lane.getBoundingClientRect().left);else timeline.setView(timeline.viewStart+(e.deltaX||e.deltaY)/400*timeline.viewSpan,timeline.viewSpan)};
  lane.ondblclick=()=>{document.getElementById("footageSection").open=true;document.getElementById("effectClipControls").open=true;document.getElementById("effectClipControls").scrollIntoView({block:"nearest"})};
  lane.onkeydown=e=>{
    const block=e.target.closest(".effect-block");
    if(["Enter"," "].includes(e.key)&&block){e.preventDefault();e.stopImmediatePropagation();selectedEffectId=block.dataset.id;refreshEffectControls();document.getElementById("effectClipControls").open=true;lane.focus();}
    if(["Delete","Backspace"].includes(e.key)&&selectedEffect()){e.preventDefault();e.stopImmediatePropagation();document.getElementById("effectRemove").click()}
  };
  document.getElementById("clipLoop").onchange=e=>{const clip=selectedFootage();if(clip?.asset.kind==="video"){clip.loop=e.target.checked;constrainFootage(clip);refreshFootageControls();footageChanged()}};
  document.getElementById("clipEnabled").onchange=e=>{const clip=selectedFootage();if(clip){clip.enabled=e.target.checked;refreshFootageControls();footageChanged()}};
  document.addEventListener("phrasync-language-change",()=>{effectLaneKey="";refreshEffectControls()});
}
