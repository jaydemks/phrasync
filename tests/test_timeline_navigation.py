import json
from pathlib import Path
import shutil
import subprocess
import pytest

ROOT=Path(__file__).resolve().parents[1]


def run_js(script):
    if not shutil.which('node'):pytest.skip('Node required')
    result=subprocess.run([shutil.which('node'),'-'],input=script,text=True,capture_output=True,timeout=15)
    assert result.returncode==0,result.stderr


def test_navigation_keyboard_selection_zoom_and_editing_guards():
    source=(ROOT/'static/app-timeline-navigation.js').read_text(encoding='utf-8')
    script=r"""
const vm=require('node:vm'),assert=require('node:assert/strict');const listeners={},nodes=new Map();let modal=false,clock=60;
const element=id=>{if(!nodes.has(id))nodes.set(id,{value:'0',addEventListener(k,f){this[k]=f}});return nodes.get(id)};
const project={canvas:{fps:60},timing:{offset:.2},exportRange:{in:20,out:30},cues:[{start:4,end:8}]};
const timeline={viewStart:0,viewSpan:100,minSpan:2/60,follow:true,duration:()=>100,
 setView(start,span){this.viewStart=start;this.viewSpan=span},fitAll(){this.setView(0,100)},focusTime(t){this.setView(t-this.viewSpan/2,this.viewSpan)}};
const c={window:{},ITALIAN:{},document:{getElementById:element,querySelector:()=>modal?{}:null,addEventListener:(k,f)=>listeners[k]=f},
 timeline,project,currentPlaybackTime:()=>clock,t:x=>x,toast(){},selectedFootage:()=>({start:10,end:12}),selectedEffect:()=>({start:20,end:21}),selectedCue:()=>project.cues[0]};
vm.runInNewContext(SOURCE,c);const nav=c.window.VFTimelineNavigation;nav.init();const before=JSON.stringify(project);
function press(key,extra={}){let prevented=false;const e={key,code:'',target:{closest:()=>null},preventDefault(){prevented=true},stopImmediatePropagation(){},...extra};listeners.keydown(e);return prevented}
assert(press('+'));assert(timeline.viewSpan<100);assert(Math.abs(timeline.viewStart+timeline.viewSpan/2-59.8)<1e-8);
for(let i=0;i<40;i++)press('+');assert(Math.abs(timeline.viewSpan-2/60)<1e-8);
for(let i=0;i<40;i++)press('-');assert.equal(timeline.viewSpan,100);assert.equal(timeline.viewStart,0);
timeline.viewSpan=10;assert(press('PageDown'));assert.equal(timeline.viewStart,8);assert(press('PageUp'));assert.equal(timeline.viewStart,0);
function scope(name){listeners.pointerdown({target:{closest:s=>s.includes(name)?{}:null}})}
scope('#footageLane');assert(press('f'));assert(timeline.viewStart<9.8&&timeline.viewStart+timeline.viewSpan>11.8);
scope('#effectsLane');assert(press('f'));assert(timeline.viewStart<19.8&&timeline.viewStart+timeline.viewSpan>20.8);
scope('#timelineWrap');press('f');assert(timeline.viewStart<4&&timeline.viewStart+timeline.viewSpan>8);
press('r',{shiftKey:true});assert(timeline.viewStart<19.8&&timeline.viewStart+timeline.viewSpan>29.8);
press('p',{shiftKey:true});assert(Math.abs(timeline.viewStart+timeline.viewSpan/2-59.8)<1e-8);
press('z',{shiftKey:true});assert.equal(timeline.viewSpan,100);assert.equal(timeline.follow,false);
element('timelineZoom').value='100';element('timelineZoom').input({target:element('timelineZoom')});assert(Math.abs(timeline.viewSpan-2/60)<1e-8);
nav.refresh();assert(Number(element('timelineZoom').value)>99.9);
for(const key of ['i','o','s','w','ArrowLeft','ArrowRight',' '])assert(!press(key));
for(const extra of [{ctrlKey:true},{metaKey:true},{altKey:true},{isComposing:true},{target:{isContentEditable:true,closest:()=>null}},{target:{closest:()=>({})}}])assert(!press('+',extra));
modal=true;assert(!press('+'));modal=false;assert.equal(JSON.stringify(project),before);
""".replace('SOURCE',json.dumps(source))
    run_js(script)


def test_real_timeline_uses_content_width_frame_level_zoom_and_shared_view():
    source=(ROOT/'static/timeline.js').read_text(encoding='utf-8')
    script=r"""
const vm=require('node:vm'),assert=require('node:assert/strict');const handlers={};let shared;
const ctx=new Proxy({measureText:()=>({width:12}),createLinearGradient:()=>({addColorStop(){}})},{get:(o,k)=>k in o?o[k]:(()=>{})});
const canvas={style:{},getContext:()=>ctx,addEventListener:(k,f)=>handlers[k]=f,getBoundingClientRect:()=>({left:11,top:0,width:978,height:164})};
const host={getBoundingClientRect:()=>({width:1000,height:164})};const state={duration:120,cues:[],fps:60};
const c={window:{addEventListener(){},devicePixelRatio:1},IS_DESKTOP_HOST:true,document:{documentElement:{}},
 getComputedStyle:()=>({getPropertyValue:()=>'',paddingLeft:'11px',paddingRight:'11px'})};
vm.runInNewContext(SOURCE,c);const t=c.window.VFTimeline.create({canvas,host,getState:()=>state,onView:(start,span)=>shared={start,span}});
assert.equal(t.width,978);t.fitAll();assert.equal(t.timeToX(120),978);assert.equal(t.xToTime(978),120);
t.setView(10,10);const pivot=t.xToTime(400);t.zoomAt(.5,400);assert(Math.abs(t.xToTime(400)-pivot)<1e-10);assert.equal(shared.span,t.viewSpan);
t.setView(10,1e-8);assert(Math.abs(t.viewSpan-2/60)<1e-10);
t.setView(80,80);t.zoomAt(2,900);assert.equal(t.viewStart,0);assert.equal(t.viewSpan,120);assert.equal(t.follow,false);
""".replace('SOURCE',json.dumps(source))
    run_js(script)
