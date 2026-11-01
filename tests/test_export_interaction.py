import shutil
import subprocess
from pathlib import Path
import pytest

ROOT=Path(__file__).resolve().parents[1]


def test_export_modal_lock_cancel_and_failure_recovery():
    if not shutil.which('node'):pytest.skip('Node required')
    script=r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const element=()=>({hidden:false,disabled:false,value:'/renders',style:{},textContent:'',open:true,close(){this.open=false},removeAttribute(){}});
const els=new Proxy({}, {get(obj,key){return obj[key]||=(element())}}),elements={};
let create,jobState='running',failStart=false,failCancel=false,cancels=0;
const c={els,ITALIAN:{},document:{getElementById:id=>elements[id]||=(element())},window:{location:{origin:'http://127.0.0.1:5571'}},
 project:{title:'Preserve me',cues:[{text:'Original'}]},currentRenderJob:null,IS_DESKTOP_HOST:false,renderPollTimer:null,
 clone:structuredClone,t:x=>x,toast(){},clearTimeout(){},setTimeout:()=>1,
 api:async(path,options)=>{
  if(path==='/api/render'){if(failStart)throw Error('Start failed');return await new Promise(r=>create=r)}
  if(path.endsWith('/cancel')){cancels++;if(failCancel)throw Error('Cancel failed');return {ok:true}}
  return {id:'job',state:jobState,progress:.4,result:{width:640,height:360,fps:30,duration:1,elapsed:1,path:'/renders/video.mp4'}};
 }};
vm.createContext(c);vm.runInContext(fs.readFileSync('static/app-render.js','utf8'),c);
(async()=>{
 const before=JSON.stringify(c.project),start=c.startRender();
 assert(els.renderClose.disabled&&els.renderDirectoryInput.disabled);assert(!elements.renderBusyNotice.hidden);
 c.closeRenderDialog();assert(els.renderDialog.open);
 let prevented=false;c.cancelRenderDialog({preventDefault(){prevented=true}});assert(prevented);
 await c.cancelRender();assert(els.cancelRender.disabled); // Cancel while request is being created.
 create({id:'job'});await start;await Promise.resolve();assert.equal(cancels,1);
 assert(els.renderClose.disabled,'Unlocking before cancellation was confirmed');
 jobState='cancelled';await c.pollRender();assert(!els.renderClose.disabled&&!els.renderDirectoryInput.disabled);
 assert(elements.renderBusyNotice.hidden);assert.equal(JSON.stringify(c.project),before);
 c.closeRenderDialog();assert(!els.renderDialog.open);
 els.renderDialog.open=true;failStart=true;await c.startRender();assert(!els.renderClose.disabled&&elements.renderBusyNotice.hidden);
 failStart=false;jobState='running';const next=c.startRender();create({id:'job'});await next;
 failCancel=true;await c.cancelRender();assert(!els.cancelRender.disabled&&els.renderClose.disabled);
 jobState='failed';await c.pollRender();assert(!els.renderClose.disabled&&elements.renderBusyNotice.hidden);
 c.currentRenderJob='job';c.setRenderBusy(true);jobState='complete';await c.pollRender();
 assert(!els.renderClose.disabled&&elements.renderBusyNotice.hidden);assert(!els.renderResult.hidden);
 c.currentRenderJob='lost-job';c.setRenderBusy(true);c.api=async()=>{const e=Error('Not found');e.status=404;throw e};
 await c.pollRender();assert.equal(c.currentRenderJob,null);assert(!els.renderClose.disabled&&elements.renderBusyNotice.hidden);
 console.log('Export lock, Escape/X, queued cancel, failure and completion recovery passed');
})().catch(e=>{console.error(e);process.exitCode=1});
'''
    result=subprocess.run(['node','-e',script],cwd=ROOT,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr


def test_custom_font_swapping_keeps_controls_usable_after_failure():
    if not shutil.which('node'):pytest.skip('Node required')
    script=r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const controls={},element=()=>({textContent:'',disabled:false,listeners:{},addEventListener(k,f){this.listeners[k]=f}});
const c={ITALIAN:{},document:{getElementById:id=>controls[id]||=element(),fonts:{add(){}}},
 project:{style:{fontPreset:'impact'}},fontStacks:{impact:'Impact, sans-serif'},els:{fontPick:element()},
 applyStageStyle(){},restartLyricAnimation(){},scheduleSave(){},setAssetStatus(){},toast(){},t:x=>x,
 FontFace:class {constructor(name){this.name=name}async load(){if(this.name.includes('broken'))throw Error('Invalid font');return this}},
 fetch:async()=>({ok:true,arrayBuffer:async()=>new ArrayBuffer(16)})};
vm.createContext(c);vm.runInContext(fs.readFileSync('static/app-project-tasks.js','utf8'),c);vm.runInContext(fs.readFileSync('static/app-fonts.js','utf8'),c);
(async()=>{
 for(const id of ['sans-ttf','serif-ttf','display-otf','variable-ttf','cjk-ttc']){
  await c.useCustomFont({id,name:id});assert(c.lyricFontStack().includes(id));assert(!c.els.fontPick.disabled);
 }
 await c.useCustomFont({id:'broken',name:'broken.ttf'});assert.equal(c.lyricFontStack(),'Impact, sans-serif');
 assert(!controls.resetCustomFont.disabled);controls.resetCustomFont.listeners.click();assert.equal(c.project.style.fontAssetId,null);
 await c.useCustomFont({id:'working-after-error',name:'valid.otf'});assert(c.lyricFontStack().includes('working-after-error'));
 assert(!c.els.fontPick.disabled);console.log('Font swaps, fallback/reset and recovery leave controls usable');
 let attempts=0;c.fetch=async()=>{if(++attempts===1)throw Error('Temporary font request failure');return{ok:true,arrayBuffer:async()=>new ArrayBuffer(16)}};
 await c.useCustomFont({id:'retry-font',name:'Retry.ttf'});assert.equal(c.lyricFontStack(),'Impact, sans-serif');
 await c.useCustomFont({id:'retry-font',name:'Retry.ttf'});assert(c.lyricFontStack().includes('retry-font'));assert.equal(attempts,2);
})().catch(e=>{console.error(e);process.exitCode=1});
'''
    result=subprocess.run(['node','-e',script],cwd=ROOT,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr
