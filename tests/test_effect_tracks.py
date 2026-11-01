import copy
import json
from pathlib import Path
import shutil
import subprocess
from types import SimpleNamespace
import pytest
from phrasync.footage import prepare_footage, effects_enabled
from phrasync.webgl_renderer import _needs_spectrum

ROOT=Path(__file__).resolve().parents[1]


def event(**changes):
    return dict(id='fx-one',kind='drop',start=1,end=2,amount=20,mode='one-shot',attack=0,release=0,**changes)


def test_timeline_only_effects_route_to_compositor_and_spectrum():
    project={'background':{'type':'dynamic','effectClips':[event()]}}
    assert effects_enabled(prepare_footage(project))
    assert not _needs_spectrum(project)
    project['background']['effectClips'][0]['kind']='spectrum'
    assert _needs_spectrum(project)
    project['background']['effectClips'][0]['enabled']=False
    assert not _needs_spectrum(project)
    assert not effects_enabled(project)


@pytest.mark.parametrize('change',[
    {'amount':999},{'start':float('nan')},{'end':0},{'kind':'unknown'},
    {'mode':'random'},{'track':4},{'division':0},{'enabled':'yes'},{'release':-1}])
def test_invalid_effects_cannot_reach_export(change):
    clip=event();clip.update(change)
    with pytest.raises(ValueError):prepare_footage({'background':{'effectClips':[clip]}})


def test_effect_collection_limits_and_global_modes():
    for value in [[], {'drop':{'mode':'invalid'}}]:
        with pytest.raises(ValueError):prepare_footage({'background':{'effectSettings':value}})
    for value in [{},[event(),event()],[{**event(), 'id':str(i)} for i in range(257)]]:
        with pytest.raises(ValueError):prepare_footage({'background':{'effectClips':value}})
    assert prepare_footage({'background':{'effectSettings':{'drop':{'mode':'constant','division':2}}}})


def test_looped_background_covers_song_without_out_of_source_error(monkeypatch):
    asset=SimpleNamespace(id='video',path='source.mp4',public=lambda:{'id':'video','kind':'video','duration':2})
    monkeypatch.setattr('phrasync.footage.get_asset',lambda *a:asset)
    monkeypatch.setattr('phrasync.footage.probe_duration',lambda *a:2)
    project={'background':{'type':'dynamic','footageEnabled':True,'tracks':['V1'],
        'clips':[{'id':'clip','asset':asset.public(),'start':0,'end':20,'loop':True}]}}
    before=copy.deepcopy(project);assert prepare_footage(project)['background']['clips'][0]['end']==20
    assert project==before
    project['background']['clips'][0]['loop']=False
    with pytest.raises(ValueError,match='beyond'):prepare_footage(project)


@pytest.mark.skipif(not shutil.which('node'),reason='Node required')
def test_effect_envelopes_legacy_compatibility_and_background_migration():
    sources={name:(ROOT/'static'/name).read_text(encoding='utf-8') for name in ['effect-automation.js','app-background-bridge.js','media-effects.js']}
    script=r"""
const vm=require('node:vm'),assert=require('node:assert/strict');
const p={background:{effects:{drop:20,gradient:40,pendulum:5,bpm:120},effectOnsets:[1,2]},timing:{beatOffset:0}};
const c={window:{},project:p,clone:x=>JSON.parse(JSON.stringify(x)),selectedFootageId:null,crypto:{randomUUID:()=> 'id'},document:{getElementById:()=>({})},projectDuration:()=>12};
vm.runInNewContext(SOURCES['effect-automation.js'],c);const fx=c.window.VFEffects;
for(const t of [0,.1,.499,.5,1,13.2]){const phase=((t*2%1)+1)%1;assert(Math.abs(fx.value('drop',t,.3,p)-20*Math.exp(-phase*14))<1e-10);assert.equal(fx.value('gradient',t,.3,p),40);assert.equal(fx.value('pendulum',t,.3,p),5)}
p.background.effectSettings={drop:{mode:'constant'}};assert.equal(fx.value('drop',.25,0,p),20);
p.background.effectSettings.drop.mode='off';assert.equal(fx.value('drop',0,1,p),0);
p.background.effectSettings.drop={mode:'audio'};assert.equal(fx.value('drop',0,.5,p),10);
p.background.effects.drop=0;p.background.effectClips=[{id:'a',kind:'drop',start:1,end:2,amount:18,attack:0,release:0}];
for(const t of [0,.99,2,3])assert.equal(fx.value('drop',t,1,p),0);
assert.equal(fx.value('drop',1.5,0,p),18);assert.equal(fx.value('drop',1,0,p),18);
const before=JSON.stringify(p);assert.equal(fx.value('drop',1.5,0,p),fx.value('drop',1.5,0,p));assert.equal(JSON.stringify(p),before);
p.background.effectClips[0].release=.5;assert(Math.abs(fx.value('drop',1.75,0,p)-9)<1e-8);
p.background.effectClips[0].enabled=false;assert.equal(fx.value('drop',1.5,1,p),0);
p.background={type:'video',videoAsset:{id:'v',kind:'video',duration:3,name:'Background'},assetId:'v'};p.audio={duration:12};
vm.runInNewContext(SOURCES['app-background-bridge.js'],c);c.exposeLegacyBackground();
assert.equal(p.background.clips.length,1);assert.equal(p.background.clips[0].end,12);assert(p.background.clips[0].loop);assert.equal(p.background.type,'dynamic');assert.equal(p.background.assetId,undefined);
c.exposeLegacyBackground();assert.equal(p.background.clips.length,1);
vm.runInNewContext(SOURCES['media-effects.js'],c);
for(const t of [0,2.9,3.1,11.9])assert(Math.abs(c.window.VFMedia.sourceTime(p.background.clips[0],t,{duration:3})-t%3)<1e-8);
p.background.clips=[];c.exposeLegacyBackground();assert.equal(p.background.clips.length,0);assert.equal(p.background.mediaLibrary.length,1);
p.background={type:'video',videoAsset:{id:'v2',kind:'video',duration:3,name:'New background'},footageEnabled:false,clips:[{id:'old',asset:{id:'old-media',kind:'image'},start:0,end:20}]};
c.exposeLegacyBackground();assert.equal(p.background.clips.length,2);assert.equal(p.background.clips[1].enabled,false);assert.equal(p.background.mediaLibrary.length,2);assert.equal(c.window.VFMedia.activeClip(.5).id,p.background.clips[0].id);
""".replace('SOURCES',json.dumps(sources))
    result=subprocess.run([shutil.which('node'),'-'],input=script,text=True,capture_output=True,timeout=15)
    assert result.returncode==0,result.stderr
