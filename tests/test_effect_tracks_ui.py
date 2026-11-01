import json
from pathlib import Path
import shutil
import subprocess
import pytest


@pytest.mark.skipif(not shutil.which('node'), reason='Node required')
def test_fx_editor_add_edit_drag_duplicate_remove_and_independent_timing():
    root=Path(__file__).resolve().parents[1]/'static'
    sources={name:(root/name).read_text(encoding='utf-8') for name in ['effect-automation.js','app-effect-tracks.js']}
    script=r"""
const vm=require('node:vm'),assert=require('node:assert/strict');const nodes=new Map();let seq=0,saves=0;
class El {
 constructor(tag){this.tagName=tag;this.children=[];this.dataset={};this.style={};this.className='';this._value='';this.clientWidth=800}
 set id(v){this._id=v;nodes.set(v,this)}get id(){return this._id}
 set value(v){this._value=String(v)}get value(){return this._value}
 append(...items){for(const x of items){x.parent=this;this.children.push(x)}}
 add(x){this.append(x)}replaceChildren(...items){this.children=[];this.append(...items)}
 setAttribute(k,v){this[k]=v}focus(){}setPointerCapture(){}scrollIntoView(){}
 closest(selector){return this.className.split(' ').includes(selector.slice(1))?this:this.parent?.closest(selector)||null}
 querySelector(selector){const id=selector.match(/data-id="([^"]+)"/)?.[1];return this.children.find(x=>x.dataset.id===id)}
 click(){this.onclick?.()}
 getBoundingClientRect(){return {left:0,top:0}}
}
const doc={getElementById(id){if(!nodes.has(id)){const x=new El('div');x.id=id}return nodes.get(id)},createElement:tag=>new El(tag),addEventListener(){}};
const project={background:{effects:{},effectClips:[],clips:[]},timing:{snapMode:'off'}};
const c={window:{},ITALIAN:{},document:doc,project,Option:class extends El{constructor(text,value){super('option');this.textContent=text;this.value=value}},
 t:x=>x,crypto:{randomUUID:()=>String(++seq)},clone:x=>JSON.parse(JSON.stringify(x)),toast(){},
 timeline:{viewStart:0,viewSpan:10,setView(s,v){this.viewStart=s;this.viewSpan=v}},
 currentPlaybackTime:()=>2.5,projectDuration:()=>10,syncNumericSliders(){},updateDurationUI(){},scheduleSave(){saves++},selectedFootage:()=>null,seekTo(){},ensureAnalysis:async()=>{}};
vm.runInNewContext(SOURCES['effect-automation.js'],c);vm.runInNewContext(SOURCES['app-effect-tracks.js'],c);
(async()=>{
 c.initEffectTracks();doc.getElementById('effectKind').value='drop';doc.getElementById('effectAdd').click();
 assert.equal(project.background.effectClips.length,1);let clip=project.background.effectClips[0];assert.equal(clip.start,2.5);assert.equal(clip.mode,'one-shot');
 const amount=doc.getElementById('effect-amount');amount.value=99;amount.onchange();assert.equal(clip.amount,30);
 const mode=doc.getElementById('effect-mode');mode.value='beat';mode.onchange();assert.equal(clip.mode,'beat');
 const timing=doc.getElementById('effectTiming-drop');timing.value='audio';await timing.onchange();assert.equal(project.background.effectSettings.drop.mode,'audio');assert.equal(clip.mode,'beat');
 const lane=doc.getElementById('effectsLane');let block=lane.children.find(x=>x.dataset.id===clip.id);assert(block);
 lane.onpointerdown({button:0,target:block,clientX:100,pointerId:1});lane.onpointermove({clientX:180,clientY:4,altKey:true});lane.onpointerup();assert.equal(clip.start,3.5);
 const enabled=doc.getElementById('effect-enabled');enabled.checked=false;enabled.onchange({target:enabled});assert.equal(clip.enabled,false);
 doc.getElementById('effectDuplicate').click();assert.equal(project.background.effectClips.length,2);assert.equal(project.background.effectClips[1].start,clip.end);
 doc.getElementById('effectRemove').click();assert.equal(project.background.effectClips.length,1);
 doc.getElementById('effectClipSelect').value=clip.id;doc.getElementById('effectClipSelect').onchange({target:doc.getElementById('effectClipSelect')});
 lane.onkeydown({key:'Delete',target:lane,preventDefault(){},stopImmediatePropagation(){}});assert.equal(project.background.effectClips.length,0);assert(saves>5);
})().catch(e=>{console.error(e);process.exitCode=1});
""".replace('SOURCES',json.dumps(sources))
    result=subprocess.run([shutil.which('node'),'-'],input=script,text=True,capture_output=True,timeout=15)
    assert result.returncode==0,result.stderr
