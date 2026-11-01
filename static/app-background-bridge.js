"use strict";

// The quick background picker creates the same editable clips as the media bin.
function attachBackgroundAsset(asset, { legacy = false } = {}) {
  const bg=project.background, library=bg.mediaLibrary ||= [];
  asset={...asset, kind:asset.kind || bg.type};
  if (!library.some(item=>item.id===asset.id)) library.push(clone(asset));
  const duration=Number(project.timelineDuration) || Number(project.audio?.duration)
    || (project.audioAssetId ? Number(project.duration) : 0) || Number(asset.duration) || projectDuration();
  const clip={id:crypto.randomUUID(),asset:clone(asset),start:0,end:Math.max(.05,duration),in:0,rate:1,
    zoomStart:1,zoomEnd:1,xStart:0,xEnd:0,yStart:0,yEnd:0,track:0,opacity:1,fadeIn:0,fadeOut:0,
    transition:"cut",loop:asset.kind==="video",backgroundPicker:true};
  if(!bg.footageEnabled)for(const previous of bg.clips || []){
    previous.enabled=false;
    if(previous.asset?.id&&!library.some(item=>item.id===previous.asset.id))library.push(clone(previous.asset));
  }
  bg.clips=(bg.clips || []).filter(item=>!item.backgroundPicker);
  bg.clips.unshift(clip); bg.footageEnabled=true; bg.tracks ||= ["V1"];
  if (!bg.tracks.length) bg.tracks=["V1"];
  bg.type="dynamic"; bg.timelineBackgroundMigrated=true;
  for (const key of ["assetId","url","name","videoAsset","imageAsset"]) delete bg[key];
  selectedFootageId=clip.id;
  window.VFTimelineNavigation?.selectLane("footage");
  if (!legacy) document.getElementById("footageSection").open=true;
  return clip;
}

function exposeLegacyBackground() {
  const bg=project.background;
  if (bg.footageEnabled || bg.timelineBackgroundMigrated || !["image","video"].includes(bg.type)) return;
  const asset=bg[`${bg.type}Asset`] || (bg.assetId ? {id:bg.assetId,kind:bg.type,name:bg.name || bg.type,url:bg.url} : null);
  if (asset?.id) attachBackgroundAsset(asset,{legacy:true});
}
