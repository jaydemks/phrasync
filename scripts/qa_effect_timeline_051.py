"""Local rendering checks for editable looped backgrounds and isolated FX."""
import argparse
import copy
import json
from pathlib import Path
import sys
import time
import urllib.request
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
from phrasync.media import run_ffmpeg, decode_test
from phrasync.renderer import render_project
from phrasync.storage import store_path, delete_asset

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--origin',default='http://127.0.0.1:5571');parser.add_argument('--api',action='store_true');parser.add_argument('--label',default='source');parser.add_argument('--4k-only',dest='four_k_only',action='store_true');args=parser.parse_args()
    out=ROOT/'qa_out/effect-timeline-051';out.mkdir(parents=True,exist_ok=True)
    run_ffmpeg(['-y','-f','lavfi','-i','testsrc2=size=640x360:rate=30:duration=2','-c:v','libx264','-pix_fmt','yuv420p',str(out/'loop-source.mp4')])
    run_ffmpeg(['-y','-f','lavfi','-i','sine=frequency=900:sample_rate=48000:duration=6',str(out/'audio.wav')])
    video=store_path('video',out/'loop-source.mp4');audio=store_path('audio',out/'audio.wav')
    base={'title':'FX timeline QA','duration':6,'audioAssetId':audio.id,'__renderOrigin':args.origin,
          'canvas':{'width':1280,'height':720,'fps':30},'timing':{'bpm':120},
          'background':{'type':'dynamic','visual':'aurora','textSpace':'flat','footageEnabled':True,'tracks':['V1'],
              'clips':[{'id':'loop','asset':video.public(),'start':0,'end':6,'in':0,'rate':1,'loop':True}], 'effects':{}},
          'style':{'fontPreset':'impact','fontSize':100,'preset':'focus-word'},'cues':[{'id':'text','start':0,'end':6,'text':'TIMELINE FX'}],
          'export':{'preset':'fast','bitrateMbps':10}}
    def fx(identifier,kind,start,end,amount):return {'id':identifier,'kind':kind,'start':start,'end':end,'amount':amount,'mode':'one-shot','attack':0,'release':0,'track':0}
    cases=[]
    def add(name,scene=False,events=None,ranged=None,world=False):
        p=copy.deepcopy(base);p['background']['textSpace']='scene' if scene else 'flat';p['background']['effectClips']=events or []
        if ranged:p['exportRange']=ranged
        if world:p['background'].update(footageEnabled=False,visual='scene3d',sceneKit='ocean')
        cases.append((name,p))
    events=[fx('flash','flash',1,1.5,40),fx('leak','lightLeak',3,3.6,80)]
    add('loop-baseline');add('isolated-light-events',events=events)
    add('isolated-light-INOUT',events=events,ranged={'in':2.7,'out':3.8})
    add('3d-particles-spectrum',scene=True,events=[fx('drop','drop',1,1.7,18),fx('particles','particles',1,4,40),fx('spectrum','spectrum',1,4,80)])
    add('ocean-3d-one-drop',scene=True,events=[fx('drop','drop',1,1.7,18)],world=True)
    constant=copy.deepcopy(base);constant['background'].update(effects={'drop':10,'pulse':20},effectSettings={'drop':{'mode':'constant'},'pulse':{'mode':'beat','division':2}})
    cases.append(('per-effect-global-timing',constant))
    real=ROOT/'qa_out/real-project-050/I_Still_Wait_real_footage.phrasync.json'
    if real.exists():
        p=json.loads(real.read_text(encoding='utf-8'));p['__renderOrigin']=args.origin
        p['exportRange']={'in':13,'out':17}
        p['background']['effectClips']=[fx('real-drop','drop',14,14.8,20),fx('real-leak','lightLeak',15.5,16.1,60)]
        p['background']['effectSettings']={'drop':{'mode':'off'}}
        cases.append(('real-footage-3d-manual-FX',p))
    def api(path,payload=None):
        req=urllib.request.Request(args.origin+path,data=json.dumps(payload).encode() if payload is not None else None,headers={'Origin':args.origin,'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)
    if args.four_k_only:
        p=copy.deepcopy(base);p['canvas']={'width':3840,'height':2160,'fps':60};p['background']['textSpace']='scene'
        p['background']['effectClips']=[fx('drop','drop',1,1.5,20),fx('leak','lightLeak',1,1.5,60),fx('spectrum','spectrum',1,1.5,80)]
        p['exportRange']={'in':1,'out':1.5};cases=[('4k60-3d-timeline-FX',p)]
    results=[];paths={}
    try:
        for name,p in cases:
            started=time.monotonic()
            if args.api:
                job=api('/api/render',{'project':p,'title':f'{args.label}-{name}','outputDirectory':str(out)})
                deadline=time.monotonic()+180
                while job['state'] not in {'complete','failed','cancelled'} and time.monotonic()<deadline:
                    time.sleep(.3);job=api('/api/render/'+job['id'])
                assert job['state']=='complete',job
                assert job['postflight']['ok'];result=job['result']
            else:result=render_project(p,out/f'{args.label}-{name}.mp4')
            path=Path(result['path']);paths[name]=path;assert decode_test(path)[0]
            import av
            with av.open(str(path)) as container:
                stream=container.streams.video[0];assert float(stream.average_rate)==p['canvas']['fps']
                assert sum(1 for _ in container.decode(stream))==result['frames']
            row={'case':name,'ok':True,'result':result,'wallSeconds':round(time.monotonic()-started,3)};results.append(row)
            (out/f'{args.label}-results.json').write_text(json.dumps(results,indent=2),encoding='utf-8');print(json.dumps(row),flush=True)
        if args.four_k_only:return
        import numpy as np
        def sample(name,t):
            raw=run_ffmpeg(['-ss',str(t),'-i',str(paths[name]),'-frames:v','1','-f','rawvideo','-pix_fmt','rgb24','pipe:1']).stdout
            return np.frombuffer(raw,dtype=np.uint8).astype(float)
        comparisons={}
        for t in [.5,1.2,2.5,3.2,4.5]:
            error=float(np.mean(np.abs(sample('loop-baseline',t)-sample('isolated-light-events',t))))
            comparisons[str(t)]=round(error,4)
            assert error>8 if t in [1.2,3.2] else error<4,(t,error)
        ranged_error=float(np.mean(np.abs(sample('isolated-light-events',3.2)-sample('isolated-light-INOUT',.5))))
        assert ranged_error<5,ranged_error
        report={'outsideAndInsideEffectPixelDifferences':comparisons,'inOutMeanPixelDifference':ranged_error,'ok':True}
        (out/f'{args.label}-comparison.json').write_text(json.dumps(report,indent=2),encoding='utf-8');print(json.dumps(report),flush=True)
    finally:
        delete_asset(video.id);delete_asset(audio.id)


if __name__=='__main__':main()
