import json
from pathlib import Path
import shutil
import subprocess
import pytest


@pytest.mark.skipif(not shutil.which('node'), reason='Node required')
def test_visual_rows_drag_destinations_and_compositing_order_agree():
    root=Path(__file__).resolve().parents[1]/'static'
    sources={name:(root/name).read_text(encoding='utf-8') for name in ['app-visual-tracks.js','media-effects.js','app-media-bin.js']}
    script=r"""
const vm=require('node:vm'),assert=require('node:assert/strict');const nodes=new Map(),drawn=[];
class Element {constructor(){this.children=[]}replaceChildren(...items){this.children=items}append(...items){this.children.push(...items)}setAttribute(){} }
const document={getElementById(id){if(!nodes.has(id))nodes.set(id,new Element());return nodes.get(id)},createElement:()=>new Element()};
const clips=['bottom','middle','top'].map((id,track)=>({id,track,start:0,end:5,in:0,rate:1,asset:{id,kind:'visual',name:id}}));
const project={background:{type:'dynamic',footageEnabled:true,tracks:['V1','V2','V3'],clips,mediaLibrary:[{id:'new',kind:'visual',name:'new',duration:5}],effects:{}}};
const c={window:{},ITALIAN:{},project,document,t:x=>x,clone:x=>JSON.parse(JSON.stringify(x)),selectedFootageId:null,crypto:{randomUUID:()=> 'inserted'},
 refreshFootageControls(){},footageChanged(){},currentPlaybackTime:()=>0,
 VFVisualClips:{render:clip=>({width:64,height:64,id:clip.id})}};
vm.runInNewContext(SOURCES['app-visual-tracks.js'],c);vm.runInNewContext(SOURCES['media-effects.js'],c);vm.runInNewContext(SOURCES['app-media-bin.js'],c);
(async()=>{
 const before=JSON.stringify(project.background.tracks);
 for(let count=1;count<=4;count++)for(let track=0;track<count;track++){
  const row=c.backgroundTrackRow(track,count);assert.equal(row,count-1-track);assert.equal(c.backgroundTrackAtY(row*38+10,count),track);
 }
 assert.equal(c.backgroundTrackAtY(-20,4),3);assert.equal(c.backgroundTrackAtY(999,4),0);
 c.refreshVisualTrackControls(null);assert.deepEqual(nodes.get('clipTrack').children.map(x=>x.value),[2,1,0]);
 assert.deepEqual(nodes.get('backgroundTrackManager').children.map(x=>x.children[0].textContent.split(' ')[0]),['V3','V2','V1']);
 assert.equal(JSON.stringify(project.background.tracks),before);
 const ctx={canvas:{width:100,height:100},save(){},restore(){},fillRect(){},translate(){},rotate(){},drawImage:s=>drawn.push(s.id)};
 await c.window.VFMedia.exportBase(ctx,1,0);assert.deepEqual(drawn,['bottom','middle','top']);
 c.addMediaClip('new',0);assert.equal(project.background.clips.at(-1).track,2);
 c.addMediaClip('new',0,0);assert.equal(project.background.clips.at(-1).track,0);
 project.background.tracks.push('V4');assert.equal(c.backgroundTrackRow(3),0);assert.equal(c.backgroundTrackRow(0),3);
})().catch(e=>{console.error(e);process.exitCode=1});
""".replace('SOURCES',json.dumps(sources))
    result=subprocess.run([shutil.which('node'),'-'],input=script,text=True,capture_output=True,timeout=15)
    assert result.returncode==0,result.stderr
