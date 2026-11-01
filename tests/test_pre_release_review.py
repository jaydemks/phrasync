from pathlib import Path
import shutil
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[1]


def node(script):
    if not shutil.which('node'):pytest.skip('Node required')
    result=subprocess.run(['node','-e',script],cwd=ROOT,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr


def test_four_crossfades_and_two_prerolls_do_not_evict_live_decoders():
    node(r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');let created=0,released=0;
const c={window:{},project:{background:{}},document:{createElement(){created++;return{addEventListener(){},pause(){released++},removeAttribute(){},load(){}}}}};
vm.runInNewContext(fs.readFileSync('static/media-effects.js','utf8'),c);
const assets=Array.from({length:10},(_,i)=>({id:'clip-'+i,kind:'video',url:'/test-'+i}));
for(let frame=0;frame<5;frame++)for(const asset of assets)c.window.VFMedia.preload(asset);
assert.equal(created,10,'Visible/pre-roll video decoders were repeatedly recreated');assert.equal(released,0);
c.window.VFMedia.preload({id:'new',kind:'video',url:'/new'});assert.equal(released,1);
''')


def test_overlapping_hidden_visuals_do_not_exhaust_webgl_contexts():
    node(r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');let canvases=0,lost=0;
const ctx={clearRect(){},drawImage(){}};
const clips=Array.from({length:20},(_,i)=>({id:'clip-'+i,start:0,end:100,asset:{settings:{visual:'scene3d',sceneKit:'ocean'}}}));
const project={background:{clips}},flat={},gl={};
const c={window:{},project,els:{visualCanvas:flat,glCanvas:gl},particles:[],lastParticleSize:'',currentPlaybackTime:()=>1,
 document:{createElement(){canvases++;return{getContext:type=>type==='2d'?ctx:{getExtension:()=>({loseContext(){lost++}})}}}},
 drawDynamicVisual:()=>({update(){},render(){}}),sceneSpeedFor:()=>1,audioAmplitude:()=>0,atmosphereStateAt:()=>({})};
vm.runInNewContext(fs.readFileSync('static/visual-clips.js','utf8'),c);
for(const clip of clips)c.window.VFVisualClips.render(clip,1,640,360);
assert.equal(lost,12);assert.equal(canvases,60);
for(const clip of clips.slice(-8))c.window.VFVisualClips.render(clip,1,640,360);
assert.equal(canvases,60,'Active crossfade targets were evicted');assert.equal(lost,12);
clips[19].enabled=false;c.window.VFVisualClips.render(clips[18],1,640,360);assert.equal(lost,13);
assert.equal(project.background.clips,clips);assert.equal(c.els.visualCanvas,flat);assert.equal(c.els.glCanvas,gl);
''')


def test_project_roundtrip_preserves_new_timeline_media_and_effect_settings():
    node(r'''
const fs=require('node:fs'),vm=require('node:vm'),assert=require('node:assert/strict');
const c={URLSearchParams,location:{search:''},localStorage:{getItem:()=>null},document:{documentElement:{classList:{toggle(){}}},querySelector:()=>({})}};
vm.createContext(c);vm.runInContext(fs.readFileSync('static/app-state.js','utf8'),c);
const input={title:'Keep 日本語',timelineDuration:37,exportRange:{in:3,out:12},mode:'subtitles',
 cues:[{id:'manual',start:3,end:8,text:'手動 中文',manual:true,words:[{text:'手動',start:3,end:4}]}],
 style:{fontAssetId:'my-font.otf',offset3DX:1.2,offset3DY:-.3},
 background:{footageEnabled:true,tracks:['V1','V2'],clips:[{id:'v',asset:{id:'raw.mp4',kind:'video'},start:1,end:30,loop:true,track:1}],
 mediaLibrary:[{id:'world',kind:'visual',settings:{visual:'scene3d',sceneKit:'ocean',weather:'snow'}}],
 weather:'snow',weatherIntensity:.7,weatherWind:-.3,weatherSpeed:1.3,weatherLightning:false,
 effectSettings:{pulse:{mode:'audio'}},effectClips:[{id:'fx',kind:'rain',start:5,end:9,amount:90,mode:'one-shot'}]}};
c.input=input;vm.runInContext('result=migrateProject(JSON.parse(JSON.stringify(migrateProject(input))))',c);
for(const key of ['title','timelineDuration','exportRange','cues'])assert.equal(JSON.stringify(c.result[key]),JSON.stringify(input[key]));
for(const [key,value]of Object.entries(input.background))assert.equal(JSON.stringify(c.result.background[key]),JSON.stringify(value));
assert.equal(c.result.style.fontAssetId,input.style.fontAssetId);assert.equal(c.result.style.offset3DX,1.2);
''')
