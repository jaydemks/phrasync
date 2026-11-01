"use strict";

const ATMOSPHERE_KINDS=["rain","snow","fog","storm","leaves"];
Object.assign(ITALIAN,{
  "Atmosphere":"Atmosfera", "Weather intensity":"Intensità meteo", "Weather speed":"Velocità meteo", "Wind":"Vento",
  "Lightning flashes":"Lampi", "Rain":"Pioggia", "Snow":"Neve", "Fog":"Nebbia", "Storm":"Temporale", "Falling leaves":"Foglie cadenti",
  "Weather works with built-in worlds, images and video layers. Daytime and season do not recolour your footage.":"Il meteo funziona con mondi integrati, immagini e livelli video. Ora del giorno e stagione non ricolorano i tuoi filmati.",
  "Storms can include bright flashes. Turn off lightning if needed.":"I temporali possono includere lampi luminosi. Disattiva i lampi se necessario."
});
function atmosphereActive(bg=project.background) {
  return ((bg.weatherIntensity??1)>0&&(bg.environmentMode==="auto"||bg.weather&&bg.weather!=="clear"&&bg.weather!=="cloudy"))
    ||ATMOSPHERE_KINDS.some(key=>Number(bg.effects?.[key])>0)
    ||(bg.effectClips||[]).some(clip=>clip.enabled!==false&&ATMOSPHERE_KINDS.includes(clip.kind));
}
function atmosphereStateAt(time,bg=project.background) {
  const state=resolvedEnvironmentAt(time,bg),levels={},effects={...bg.effects};
  if(ATMOSPHERE_KINDS.includes(state.weather))effects[state.weather]=Math.max(Number(effects[state.weather])||0,100*Math.max(0,Math.min(1.5,bg.weatherIntensity??1)));
  const evaluation={background:{...bg,effects},timing:project.timing};
  for(const key of ATMOSPHERE_KINDS){
    levels[key]=(window.VFEffects?.value(key,currentPlaybackTime(),audioAmplitude(),evaluation)||0)/100;
  }
  return {...state,levels,wind:bg.weatherWind??0,speed:bg.weatherSpeed??1,lightning:bg.weatherLightning!==false};
}
function refreshAtmosphereControls() {
  for(const key of ["weatherIntensity","weatherWind","weatherSpeed"]){
    const input=document.getElementById(key);if(!input)return;
    input.value=(project.background[key]??(key==="weatherWind"?0:1))*100;
    document.getElementById(`${key}Out`).textContent=`${Math.round(input.value)}%`;
  }
  document.getElementById("weatherLightning").checked=project.background.weatherLightning!==false;
}
function initAtmosphereControls() {
  document.getElementById("atmosphereSlot").prepend(els.environmentControls);
  for(const key of ["weatherIntensity","weatherWind","weatherSpeed"]){
    const input=document.getElementById(key);
    input.addEventListener("input",()=>{project.background[key]=Number(input.value)/100;refreshAtmosphereControls();scheduleSave()});
  }
  document.getElementById("weatherLightning").addEventListener("change",event=>{project.background.weatherLightning=event.target.checked;scheduleSave()});
  refreshAtmosphereControls();
}
