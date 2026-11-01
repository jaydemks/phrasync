import json
from pathlib import Path
import re
import shutil
import subprocess
import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_app_scripts_never_use_browser_message_boxes():
    for path in (ROOT/'static').glob('*.js'):
        assert not re.search(r'\b(?:confirm|alert|prompt)\s*\(', path.read_text(encoding='utf-8')), path.name


@pytest.mark.skipif(not shutil.which('node'), reason='Node required')
def test_integrated_confirmation_and_shutdown_safety():
    source = (ROOT/'static/app-dialogs.js').read_text(encoding='utf-8')
    probe = r"""
const vm=require('node:vm'), assert=require('node:assert/strict');
let doc,focused=0,events=[],saved,failSave=false,failRequest=false,failDialog=false;
class Element {
 constructor(tag){this.tagName=tag;this.children=[];this.listeners={};this.returnValue='';this.isConnected=true}
 setAttribute(k,v){this[k]=v}
 append(...nodes){for(const node of nodes){node.parent=this;this.children.push(node)}}
 replaceChildren(...nodes){this.children=[];this.append(...nodes)}
 get firstChild(){return this.children[0]}
 addEventListener(k,f){this.listeners[k]=f}
 focus(){doc.activeElement=this;focused++}
 showModal(){if(failDialog)throw Error('not available');this.open=true}
 close(value){if(value!==undefined)this.returnValue=value;this.open=false;this.listeners.close()}
 remove(){this.parent.children=this.parent.children.filter(x=>x!==this);this.isConnected=false}
}
doc={body:new Element('body'),activeElement:new Element('opener'),createElement:tag=>new Element(tag)};
const c={ITALIAN:{},document:doc,t:x=>x,project:{title:'Keep my edits',cues:[{text:'words'}]},
 currentRenderJob:null,currentTranscriptionJob:null,IS_DESKTOP_HOST:true,STORAGE_KEY:'session',
 localStorage:{setItem(k,v){events.push('save');if(failSave)throw Error('Storage full');saved=JSON.parse(v)}},
 fetch:async()=>{events.push('stop');return {ok:!failRequest,text:async()=> 'Server failure'}},
 toast:(msg)=>events.push(msg),confirm:()=>{throw Error('native confirmation forbidden')}};
vm.runInNewContext(SOURCE,c);
(async()=>{
 let p=c.confirmAction('<unsafe text>');let dialog=doc.body.firstChild;
 assert.equal(dialog['aria-labelledby'],'appConfirmTitle');assert.equal(dialog.children[0].children[1].textContent,'<unsafe text>');
 assert.equal(await c.confirmAction('duplicate'),false);assert.equal(doc.body.children.length,1);
 dialog.close('cancel');assert.equal(await p,false);assert.equal(doc.body.children.length,0);
 p=c.confirmAction('Escape');dialog=doc.body.firstChild;dialog.listeners.cancel();dialog.close();assert.equal(await p,false);
 p=c.confirmAction('Accept');doc.body.firstChild.close('confirm');assert.equal(await p,true);assert(focused>2);
 failDialog=true;assert.equal(await c.confirmAction('cannot open'),false);failDialog=false;
 c.confirmAction=async()=>false;await c.shutdownServer();assert.equal(events.length,0);
 c.confirmAction=async()=>true;c.currentRenderJob='active';await c.shutdownServer();assert.equal(events.length,1);assert.equal(saved,undefined);
 c.currentRenderJob=null;c.transcriptionStarting=true;events=[];await c.shutdownServer();assert(!events.includes('save')&&!events.includes('stop'));c.transcriptionStarting=false;
 c.currentRenderJob=null;events=[];failSave=true;await c.shutdownServer();assert(!events.includes('stop'));failSave=false;
 c.confirmAction=async()=>{c.currentTranscriptionJob='started while confirming';return true};events=[];
 await c.shutdownServer();assert(!events.includes('save'));assert(!events.includes('stop'));
 c.currentTranscriptionJob=null;c.confirmAction=async()=>true;
 events=[];failRequest=true;await c.shutdownServer();assert.deepEqual(events.slice(0,2),['save','stop']);assert.equal(saved.title,'Keep my edits');failRequest=false;
 for(const desktop of [true,false]){
  events=[];c.IS_DESKTOP_HOST=desktop;await c.shutdownServer();assert.deepEqual(events,['save','stop']);
  assert.equal(doc.body.firstChild.children[0].textContent,'Phrasync stopped.');
  assert(doc.body.firstChild.children[1].textContent.includes(desktop?'window':'tab'));
 }
})().catch(e=>{console.error(e);process.exitCode=1});
""".replace('SOURCE', json.dumps(source))
    result = subprocess.run([shutil.which('node'), '-'], input=probe, text=True, capture_output=True, timeout=15)
    assert result.returncode == 0, result.stderr
