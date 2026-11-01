"""Weather must share the same deterministic layer for worlds and footage."""
import json
from pathlib import Path
import shutil
import subprocess
import pytest
from phrasync.footage import prepare_footage, effects_enabled
from phrasync.webgl_renderer import _fallback_reason

ROOT=Path(__file__).resolve().parents[1]


@pytest.mark.parametrize('weather',['rain','snow','fog','storm','leaves'])
def test_weather_alone_preserves_direct_gpu_world_export(weather):
    p={'background':{'type':'dynamic','visual':'scene3d','weather':weather}}
    assert _fallback_reason(p,None) is None
    p['background']['effectClips']=[dict(kind=weather,start=0,end=2,amount=100)]
    assert _fallback_reason(p,None) is None
    p['background']['effects']={'particles':20}
    assert 'composition' in _fallback_reason(p,None)


@pytest.mark.parametrize('weather',['rain','snow','fog','storm','leaves'])
def test_weather_routes_flat_backgrounds_through_shared_compositor(weather):
    p={'background':{'type':'dynamic','visual':'aurora','textSpace':'flat','weather':weather}}
    assert effects_enabled(prepare_footage(p))
    p['background']['weatherIntensity']=0
    assert not effects_enabled(prepare_footage(p))
    p['background']['effectClips']=[dict(id='weather',kind=weather,start=2,end=4,amount=100,attack=0,release=0)]
    assert effects_enabled(prepare_footage(p))


@pytest.mark.parametrize('key,value',[('weatherIntensity',float('nan')),('weatherIntensity',2),('weatherWind',-2),('weatherSpeed',-1),('weatherLightning','yes')])
def test_invalid_weather_cannot_reach_export(key,value):
    with pytest.raises(ValueError):prepare_footage({'background':{key:value}})


def test_actual_three_weather_is_bounded_deterministic_and_world_anchored():
    if not shutil.which('node'):pytest.skip('Node required')
    script=r'''
const fs=require('node:fs'),assert=require('node:assert/strict'),vm=require('node:vm');
(async()=>{
 const load=path=>import('data:text/javascript;base64,'+Buffer.from(fs.readFileSync(path)).toString('base64'));
 const THREE=await load('static/vendor/three.module.min.js');
 const mod=await load('static/scene3d-environment.js');
 global.document={createElement:()=>({getContext:()=>({createRadialGradient:()=>({addColorStop(){}}),fillRect(){}})})};
 const env=mod.createEnvironment(THREE,{}),camera=new THREE.PerspectiveCamera();
 const buffer=env.rain.geometry.attributes.position.array;
 for(const rx of [0,-Math.PI/2,Math.PI/2])for(const ry of [0,Math.PI/2,Math.PI]){
  camera.position.set(300,900,-800);camera.rotation.set(rx,ry,.2);
  const state={levels:{rain:1,snow:1,leaves:1,fog:.5},wind:.5,speed:1,lightning:false};
  const update=t=>mod.updateWeather(THREE,env,{camera,t,state});
  update(20);const before=Array.from(buffer);update(900);update(20);
  assert.deepEqual(Array.from(buffer),before);assert.equal(env.rain.geometry.attributes.position.array,buffer);
  assert(env.group.position.equals(camera.position));assert(env.group.quaternion.equals(new THREE.Quaternion()));
  for(const obj of [env.rain,env.flakes,env.leaves]){
   assert(obj.visible);assert(obj.geometry.drawRange.count<=obj.geometry.attributes.position.count);
   assert(Array.from(obj.geometry.attributes.position.array).every(Number.isFinite));
   assert(obj.geometry.attributes.position.array.some((v,i)=>i%3===2&&v<-3&&v>-110));
  }
 }
 // Holding time fixed and moving/rotating the camera must leave particles at
 // the same world coordinates (except recycled cells at the volume boundary).
 const state={levels:{rain:1,snow:1,leaves:1},wind:0,speed:0};
 camera.position.set(0,4.2,0);camera.rotation.set(0,0,0);
 mod.updateWeather(THREE,env,{camera,t:10,state});
 const positions=[env.rain,env.flakes,env.leaves].map(o=>Array.from(o.geometry.attributes.position.array));
 camera.position.set(1,4.7,-2);camera.rotation.set(.15,.2,.03);
 mod.updateWeather(THREE,env,{camera,t:10,state});
 for(const [index,obj]of [env.rain,env.flakes,env.leaves].entries()){
  const before=positions[index],after=obj.geometry.attributes.position.array;let anchored=0;
  for(let i=0;i<before.length;i+=3){
   const error=Math.abs(after[i]+1-before[i])+Math.abs(after[i+1]+.5-before[i+1])+Math.abs(after[i+2]-2-before[i+2]);
   if(error<.00002)anchored++;
  }
  assert(anchored>before.length/3*.9,'Weather followed the camera instead of its world');
 }
 camera.position.set(0,4.2,0);camera.rotation.set(0,0,0);camera.updateMatrixWorld();
 mod.updateWeather(THREE,env,{camera,t:10,state});
 const a=env.flakes.geometry.attributes.position;
 const i=Array.from({length:a.count},(_,i)=>i).find(i=>a.getZ(i)<-8&&a.getZ(i)>-45&&Math.abs(a.getX(i))>2);
 const world=new THREE.Vector3(a.getX(i),a.getY(i)+4.2,a.getZ(i));
 const initial=world.clone().project(camera);
 const actualProjection=z=>{
  camera.position.z=z;camera.updateMatrixWorld();mod.updateWeather(THREE,env,{camera,t:10,state});
  const point=new THREE.Vector3(a.getX(i),a.getY(i),a.getZ(i)).add(camera.position);
  assert(point.distanceTo(world)<.00001,'Particle was translated with the camera');
  return point.project(camera);
 };
 assert(Math.abs(actualProjection(-2).x)>Math.abs(initial.x),'No forward parallax');
 assert(Math.abs(actualProjection(2).x)<Math.abs(initial.x),'No reverse parallax');
 for(const y of [1,4.2,30]){
  camera.position.set(1234,y,-90000);
  mod.updateWeather(THREE,env,{camera,t:12,state:{levels:{rain:1,snow:1,leaves:1}},surfaceY:0});
  for(const obj of [env.rain,env.flakes,env.leaves]){
   const a=obj.geometry.attributes.position;for(let i=0;i<a.count;i++)assert(a.getY(i)+y>=-.00001,'Weather below ocean surface');
  }
 }
 mod.updateWeather(THREE,env,{camera,t:3,state:{weather:'clear'}});
 assert(!env.rain.visible&&!env.flakes.visible&&!env.leaves.visible&&!env.fog.visible);
 const stopped={levels:{snow:1},speed:0};mod.updateWeather(THREE,env,{camera,t:1,state:stopped});
 const still=Array.from(env.flakes.geometry.attributes.position.array);
 mod.updateWeather(THREE,env,{camera,t:30,state:stopped});assert.deepEqual(Array.from(env.flakes.geometry.attributes.position.array),still);
 mod.updateWeather(THREE,env,{camera,t:0,state:{levels:{storm:1},lightning:false}});assert.equal(env.fogUniforms.flash.value,0);
 const c={window:{},ITALIAN:{},project:{background:{weather:'clear'},timing:{}},currentPlaybackTime:()=>2,audioAmplitude:()=>0,resolvedEnvironmentAt:(t,bg)=>({weather:bg.weather})};
 vm.runInNewContext(fs.readFileSync('static/effect-automation.js','utf8'),c);
 vm.runInNewContext(fs.readFileSync('static/app-atmosphere.js','utf8'),c);
 vm.runInNewContext(fs.readFileSync('static/media-effects.js','utf8'),c);
 c.project.background={type:'dynamic',visual:'scene3d',weather:'snow',effectClips:[{kind:'rain'}]};
 assert(!c.window.VFMedia.usesCanvas());
 c.project.background.effects={particles:20};assert(c.window.VFMedia.usesCanvas());
 for(const type of ['dynamic','video','image']){
  c.project.background={type,weather:'snow',weatherIntensity:.4};assert(c.atmosphereActive());assert.equal(c.atmosphereStateAt(2).levels.snow,.4);
  c.project.background.weatherIntensity=1.5;assert.equal(c.atmosphereStateAt(2).levels.snow,1.5);
  c.project.background.effectSettings={snow:{mode:'off'}};assert.equal(c.atmosphereStateAt(2).levels.snow,0);
  c.project.background={type,weather:'clear',effectClips:[{kind:'rain',start:1,end:3,amount:80,attack:0,release:0},{kind:'snow',start:1,end:3,amount:50,attack:0,release:0}]};
  const state=c.atmosphereStateAt(2);assert.equal(state.levels.rain,.8);assert.equal(state.levels.snow,.5);
 }
 console.log('Weather geometry and state checks passed');
})().catch(e=>{console.error(e);process.exitCode=1});
'''
    result=subprocess.run(['node','-e',script],cwd=ROOT,capture_output=True,text=True,timeout=30)
    assert result.returncode==0,result.stdout+result.stderr[-6000:]
