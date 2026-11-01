"use strict";

// Operations keep the project/source they started with. A delayed response
// must not replace another project's media, timing or newer lyric edits.
const projectOperations = new Map();
function beginProjectOperation(kind, options={}) {
  const previous=projectOperations.get(kind), owner=project, asset=project.audioAssetId;
  const cues=options.cues ? JSON.stringify(project.cues) : null;
  const task={active:true,label:previous?.active?previous.label:options.label,
    latest:()=>projectOperations.get(kind)===task,
    valid:()=>task.latest()&&project===owner&&(options.source===false||project.audioAssetId===asset)
      &&(cues===null||JSON.stringify(project.cues)===cues)};
  projectOperations.set(kind,task);return task;
}
function projectOperationMatches(kind) {return projectOperations.get(kind)?.valid() || false;}

Object.assign(ITALIAN,{
  "The project or lyrics changed while aligning. Your current edits were kept.":"Il progetto o il testo sono cambiati durante l’allineamento. Le modifiche attuali sono state conservate.",
  "The source changed. The previous transcription was not applied.":"La sorgente è cambiata. La trascrizione precedente non è stata applicata."
});
