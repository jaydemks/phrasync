"use strict";

// Stateless evaluation shared by interactive preview and offline export.
window.VFEffects = (() => {
  const limits = {bw:100, pendulum:15, shake:8, flash:60, gradient:80, particles:100,
    spectrum:150, drop:30, pulse:40, lightLeak:100, rain:150, snow:150, fog:150, storm:150, leaves:150};
  const reactive = new Set(["shake", "flash", "drop", "pulse"]);
  const clamp = (v, min=0, max=1) => Math.max(min, Math.min(max, Number(v) || 0));
  function signal(mode, time, amplitude, settings, p) {
    if (mode === "off") return 0;
    if (mode === "constant" || mode === "one-shot") return 1;
    if (mode === "audio") return clamp(amplitude);
    const division = clamp(settings.division ?? 1, .25, 8);
    if (mode === "transient" && p.background.effectOnsets?.length) {
      const hits = p.background.effectOnsets || [];
      let lo=0, hi=hits.length;
      while (lo<hi) { const mid=(lo+hi)>>1; if (hits[mid]<=time) lo=mid+1; else hi=mid; }
      return lo>0 ? Math.exp(-(time-hits[lo-1])*24) : 0;
    }
    const bpm = Number(p.background.effects?.bpm) || Number(p.timing?.bpm);
    if (!(bpm > 0)) return clamp(amplitude);
    const phase = ((time-(Number(p.timing?.beatOffset)||0))*bpm/60/division%1+1)%1;
    return Math.exp(-phase*14);
  }
  function value(key, time, amplitude, p) {
    const bg=p.background, fx=bg.effects || {}, setting=bg.effectSettings?.[key] || {};
    const mode=setting.mode || (reactive.has(key) ? fx.trigger || "beat" : "constant");
    let result=clamp(fx[key],0,limits[key]) * signal(mode,time,amplitude,setting,p);
    for (const clip of bg.effectClips || []) {
      if (clip.kind!==key || clip.enabled===false || time<clip.start || time>=clip.end) continue;
      const duration=clip.end-clip.start, elapsed=time-clip.start, remaining=clip.end-time;
      const attack=clamp(clip.attack ?? .025,0,duration), release=clamp(clip.release ?? duration*.8,0,duration);
      const fade=Math.min(1,attack>0 ? elapsed/attack : 1,release>0 ? remaining/release : 1);
      result=Math.max(result,clamp(clip.amount,0,limits[key])*fade*signal(clip.mode || "one-shot",time,amplitude,clip,p));
    }
    return clamp(result,0,limits[key]);
  }
  return {limits, value, signal};
})();
