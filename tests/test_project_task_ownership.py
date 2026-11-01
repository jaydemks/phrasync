"""Delayed responses must never overwrite another project or newer edits."""
from pathlib import Path
import shutil
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[1]


def run_case(case):
    if not shutil.which('node'):pytest.skip('Node required')
    prelude=r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const make=()=>({mode:'lyric',audioAssetId:'song-a',timing:{bpm:0},background:{},cues:[{id:'cue',text:'Keep this',start:0,end:2}]});
const el=()=>({textContent:'Original label',value:'base',style:{},classList:{toggle(){}},setAttribute(){},removeAttribute(){},disabled:false});
const els=new Proxy({}, {get:(o,k)=>o[k]||=(el())});
const c={project:make(),els,ITALIAN:{},MODE_COPY:{lyric:{transcribe:'Generate lyrics'}},analysis:null,analysisPending:false,
 currentTranscriptionJob:null,transcriptionPollTimer:null,selectedCueId:'cue',selectedWordIndex:0,timeline:{draw(){},fitAll(){}},
 document:{documentElement:{lang:'en'},getElementById:()=>el()},t:x=>x,toast(){},formatTime:String,
 setAssetStatus(){},formatTranscriptionJob:()=>'',setTimeout:()=>1,clearTimeout(){},scheduleSave(){},
 renderCueList(){},updateDurationUI(){},restartLyricAnimation(){},seekTo(){},
 applyAudioPreview(){},applyBackgroundPreview(){},isVideoUpload:()=>false};
vm.createContext(c);
for(const path of ['static/app-project-tasks.js','static/app-workflows.js','static/app-timeline.js'])if(fs.existsSync(path))vm.runInContext(fs.readFileSync(path,'utf8'),c);
'''
    result=subprocess.run(['node','-e',prelude+case],cwd=ROOT,capture_output=True,text=True,timeout=20)
    assert result.returncode==0,result.stdout+result.stderr


def test_old_analysis_does_not_change_a_new_project():
    run_case(r'''
(async()=>{
 let resolve;c.api=()=>new Promise(r=>resolve=r);const request=c.ensureAnalysis();
 c.project=make();c.project.audioAssetId='song-b';
 resolve({bpm:180,beatOffset:1,onsets:[1]});await request;
 assert.equal(c.project.timing.bpm,0);assert.equal(c.analysis,null);assert(!els.analyzeButton.disabled);
})().catch(e=>{console.error(e);process.exitCode=1});
''')


def test_alignment_does_not_overwrite_manual_edits_made_while_waiting():
    run_case(r'''
(async()=>{
 c.analysis={bpm:120};let resolve;c.api=()=>new Promise(r=>resolve=r);
 const request=c.runAutoAlign();await Promise.resolve();
 c.project.cues[0].text='My newer edit';
 resolve({cues:[{id:'cue',text:'Keep this',start:.1,end:2}],report:{words:2,offset:0},stats:{score:99,meanError:0}});
 await request;assert.equal(c.project.cues[0].text,'My newer edit');assert(!els.autoAlignButton.disabled);
})().catch(e=>{console.error(e);process.exitCode=1});
''')


def test_transcription_for_an_old_source_is_not_applied_to_a_new_project():
    run_case(r'''
(async()=>{
 let resolve;c.api=(path)=>path==='/api/transcriptions'?new Promise(r=>resolve=r):Promise.resolve(path.endsWith('/cancel')?{}:
  {id:'old-job',state:'complete',result:{cues:[{text:'Wrong song'}]}});
 const request=c.transcribeSong();c.project=make();c.project.audioAssetId='song-b';
 resolve({id:'old-job',state:'running'});await request;await Promise.resolve();await Promise.resolve();
 assert.equal(c.project.cues[0].text,'Keep this');
})().catch(e=>{console.error(e);process.exitCode=1});
''')


def test_older_analysis_cannot_unlock_or_replace_a_newer_analysis():
    run_case(r'''
(async()=>{
 const resolvers=[];c.api=()=>new Promise(r=>resolvers.push(r));const first=c.ensureAnalysis();
 c.project=make();c.project.audioAssetId='song-b';c.analysis=null;c.analysisPending=false;
 const second=c.ensureAnalysis();resolvers[0]({bpm:190,onsets:[]});await first;
 assert(els.analyzeButton.disabled);assert.equal(c.analysis,null);
 resolvers[1]({bpm:90,onsets:[]});await second;
 assert.equal(c.project.timing.bpm,90);assert(!els.analyzeButton.disabled);assert.equal(els.analyzeButton.textContent,'Original label');
})().catch(e=>{console.error(e);process.exitCode=1});
''')


def test_alignment_waits_for_an_analysis_already_in_progress():
    run_case(r'''
(async()=>{
 let resolve,count=0;c.api=path=>{if(path==='/api/analyze'){count++;return new Promise(r=>resolve=r)}
 return Promise.resolve({cues:[{id:'cue',text:'Keep this',start:.2,end:2}],report:{words:2,offset:0},stats:{score:99,meanError:0,tight:1}})};
 const first=c.ensureAnalysis(),align=c.runAutoAlign();resolve({bpm:120,onsets:[]});await Promise.all([first,align]);
 assert.equal(count,1);assert.equal(c.project.cues[0].start,.2);
})().catch(e=>{console.error(e);process.exitCode=1});
''')


def test_uploads_are_discarded_for_a_different_project_and_latest_audio_wins():
    run_case(r'''
(async()=>{
 const resolvers=[];c.uploadAsset=()=>new Promise(r=>resolvers.push(r));c.ensureAnalysis=async()=>null;
 const old=c.handleAudioFile({name:'Old.wav'});c.project=make();c.project.audioAssetId='new-project';
 resolvers[0]({id:'old',name:'Old.wav',duration:2});await old;assert.equal(c.project.audioAssetId,'new-project');
 const first=c.handleAudioFile({name:'First.wav'}),second=c.handleAudioFile({name:'Second.wav'});
 resolvers[2]({id:'second',name:'Second.wav',duration:2});await second;
 resolvers[1]({id:'first',name:'First.wav',duration:2});await first;assert.equal(c.project.audioAssetId,'second');
})().catch(e=>{console.error(e);process.exitCode=1});
''')


def test_transcription_polling_recovers_without_starting_a_duplicate_job():
    run_case(r'''
(async()=>{
 let fail=true,creates=0;c.api=async path=>{
  if(path==='/api/transcriptions'){creates++;return{id:'job',state:'running'}}
  if(fail)throw Error('Temporary disconnect');return{id:'job',state:'complete',result:{cues:[{id:'new',text:'Correct source'}]}};
 };
 await c.transcribeSong();await Promise.resolve();assert.equal(c.currentTranscriptionJob,'job');
 await c.transcribeSong();assert.equal(creates,1);fail=false;await c.pollTranscription();
 assert.equal(c.project.cues[0].text,'Correct source');assert.equal(c.currentTranscriptionJob,null);assert(!els.transcribeButton.disabled);
})().catch(e=>{console.error(e);process.exitCode=1});
''')


def test_transcription_can_be_cancelled_before_job_creation_finishes():
    run_case(r'''
(async()=>{
 let resolve,cancels=0;c.api=path=>{
  if(path==='/api/transcriptions')return new Promise(r=>resolve=r);
  if(path.endsWith('/cancel')){cancels++;return Promise.resolve({})}
  return Promise.resolve({id:'job',state:'cancelled'});
 };
 const request=c.transcribeSong();await c.stopTranscription();resolve({id:'job',state:'running'});
 await request;await Promise.resolve();assert.equal(cancels,1);assert.equal(c.project.cues[0].text,'Keep this');
})().catch(e=>{console.error(e);process.exitCode=1});
''')


def test_a_missing_transcription_session_unlocks_the_controls():
    run_case(r'''
(async()=>{
 c.api=async path=>{if(path==='/api/transcriptions')return{id:'lost-job',state:'running'};const e=Error('Not found');e.status=404;throw e};
 await c.transcribeSong();await Promise.resolve();await Promise.resolve();
 assert.equal(c.currentTranscriptionJob,null);assert(!els.transcribeButton.disabled);
})().catch(e=>{console.error(e);process.exitCode=1});
''')


def test_selecting_or_resetting_a_font_invalidates_an_older_upload():
    run_case(r'''
(async()=>{
 const controls={};c.document.getElementById=id=>controls[id]||=({addEventListener(k,fn){this[k]=fn}});
 vm.runInContext(fs.readFileSync('static/app-fonts.js','utf8'),c);
 c.fetch=async()=>({ok:true,arrayBuffer:async()=>new ArrayBuffer(1)});
 c.FontFace=class {async load(){return this}};c.document.fonts={add(){}};c.applyStageStyle=()=>{};
 c.project.style={fontPreset:'impact'};let resolve;c.uploadAsset=()=>new Promise(r=>resolve=r);
 const upload=c.handleFontFile({name:'slow.ttf'});await c.useCustomFont({id:'new-selection',name:'new.otf'});
 resolve({id:'slow-upload',name:'slow.ttf'});await upload;assert.equal(c.project.style.fontAssetId,'new-selection');
 const next=c.handleFontFile({name:'slow-again.ttf'});controls.resetCustomFont.click();resolve({id:'slow-again',name:'slow-again.ttf'});
 await next;assert.equal(c.project.style.fontAssetId,null);
})().catch(e=>{console.error(e);process.exitCode=1});
''')
