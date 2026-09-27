import shutil
import subprocess
from pathlib import Path

import pytest

ROOT = Path(__file__).resolve().parents[1]


def test_ocean_uniforms_follow_real_app_controls():
    node = shutil.which('node')
    if not node:
        pytest.skip('Node unavailable')
    script = r'''
const fs=require('fs'),vm=require('vm'),assert=require('assert');
const source=fs.readFileSync('static/scene3d-ocean.js','utf8').replace(/^export /gm,'');
const scope={};vm.runInNewContext(source+';globalThis.update=updateOcean;globalThis.move=updateOceanCamera;',scope);
const T={MathUtils:{clamp:(v,a,b)=>Math.max(a,Math.min(b,v)),lerp:(a,b,t)=>a+(b-a)*t,degToRad:v=>v*Math.PI/180}};
const vector=()=>({set(...v){this.values=v;},setFromMatrixPosition(m){this.values=[m[12],m[13],m[14]];}});
const names=['uTime','uAspect','uTanFov','uNight','uDay','uWaves','uClouds'];
const uniforms=Object.fromEntries(names.map(k=>[k,{value:0}]));
for(const k of ['uOrigin','uSun','uMoon'])uniforms[k]={value:vector()};
uniforms.uRotation={value:{setFromMatrix4(){}}};
const camera={aspect:16/9,fov:62,position:vector(),rotation:vector(),updateMatrixWorld(){
  this.matrixWorld=Array(16).fill(0);this.position.values.forEach((v,i)=>this.matrixWorld[12+i]=v);
}}; camera.position.set(1,3.4,-100);
const ocean={uniforms};
const base={camera,t:3,speed:1,moonElevation:18,sunElevation:12,sunAzimuth:25,motionAmount:1};
scope.update(T,ocean,{...base,environment:{daytime:'day',nextDaytime:'night',dayMix:.5}});
assert.strictEqual(uniforms.uNight.value,.5);assert.strictEqual(uniforms.uDay.value,.5);
assert(Math.abs(uniforms.uSun.value.values[1]-Math.sin(12*Math.PI/180))<1e-8);
assert.deepStrictEqual(uniforms.uOrigin.value.values,[1,3.4,-100]);
scope.move(camera,3,{...base,secondaryMotion:'none'});
scope.update(T,ocean,{...base});const rest=[...uniforms.uOrigin.value.values];
scope.move(camera,3,{...base,secondaryMotion:'rise'});
scope.update(T,ocean,{...base});const rise=[...uniforms.uOrigin.value.values];
assert(rise[1]>rest[1]);assert.strictEqual(rise[0],rest[0]);
scope.move(camera,3,{...base,secondaryMotion:'sway'});
scope.update(T,ocean,{...base});assert.notStrictEqual(uniforms.uOrigin.value.values[0],rest[0]);
scope.move(camera,3,{...base,secondaryMotion:'orbit'});
scope.update(T,ocean,{...base});assert.notStrictEqual(uniforms.uOrigin.value.values[1],rest[1]);
for(const direction of ['forward','left','right','up','down','ascend','dive','drift','bank']) {
  for(const secondaryMotion of ['none','rise','sway','orbit']) {
    scope.move(camera,23,{speed:9,direction,secondaryMotion});
    scope.update(T,ocean,{camera,t:23,direction,secondaryMotion});
    assert.strictEqual(camera.position.values[2],-207);
    assert.deepStrictEqual(uniforms.uOrigin.value.values,camera.position.values);
    assert.strictEqual(camera.rotation.values[0],-Math.atan(.15));
  }
}
assert(!source.includes('vScreen.y*uTanFov-.15'));
'''
    subprocess.run([node, '-e', script], cwd=ROOT, check=True, capture_output=True, text=True)


def test_ocean_and_license_are_bundled_static_assets():
    html = (ROOT / 'static/index.html').read_text(encoding='utf-8')
    assert '<option value="ocean">Lost in the Ocean</option>' in html
    for name in ('sunAzimuth', 'sunElevation', 'moonAzimuth', 'moonElevation', 'oceanWaveStrength'):
        assert f'id="{name}"' in html
    assert (ROOT / 'static/vendor/THREE-LICENSE.txt').is_file()
    shader = (ROOT / 'static/scene3d-ocean.js').read_text(encoding='utf-8')
    assert 'TextureLoader' not in shader and 'fetch(' not in shader
