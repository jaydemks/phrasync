"""Local weather composition exports; compare visible pixels, not just success."""
import argparse
import copy
import json
from pathlib import Path
import sys
import time
import urllib.request
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import av
import numpy as np
from phrasync.media import run_ffmpeg,decode_test
from phrasync.renderer import render_project
from phrasync.storage import store_path,delete_asset

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--origin',default='http://127.0.0.1:5571');parser.add_argument('--api',action='store_true');parser.add_argument('--label',default='source');parser.add_argument('--compact',action='store_true');parser.add_argument('--contexts',nargs='+');parser.add_argument('--directions-only',action='store_true');parser.add_argument('--stress-only',action='store_true');parser.add_argument('--world-fast-only',action='store_true');args=parser.parse_args()
    out=ROOT/'qa_out/weather-051';out.mkdir(parents=True,exist_ok=True)
    run_ffmpeg(['-y','-f','lavfi','-i','testsrc2=size=640x360:rate=30:duration=2','-c:v','libx264','-pix_fmt','yuv420p',str(out/'source.mp4')])
    run_ffmpeg(['-y','-i',str(out/'source.mp4'),'-frames:v','1',str(out/'source.png')])
    video=store_path('video',out/'source.mp4');image=store_path('image',out/'source.png')
    base={'title':'Weather QA','duration':2,'__renderOrigin':args.origin,'canvas':{'width':640,'height':360,'fps':30},
        'background':{'type':'dynamic','visual':'scene3d','sceneKit':'ocean','visualIntensity':.65,'weather':'clear','daytime':'sunset','season':'summer','textSpace':'flat','shade':0},
        'style':{'fontPreset':'impact','fontSize':64,'preset':'focus-word'},'cues':[{'id':'cue','start':0,'end':2,'text':'RAIN 雪'}],
        'exportRange':{'in':.5,'out':1.1},'export':{'preset':'fast','bitrateMbps':12}}
    if args.world_fast_only:base['export'].pop('bitrateMbps',None)
    results=[];samples={};case_projects={}
    def api(path,payload=None):
        req=urllib.request.Request(args.origin+path,data=json.dumps(payload).encode() if payload is not None else None,headers={'Origin':args.origin,'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
    def render(name,p):
        started=time.monotonic()
        if args.api:
            job=api('/api/render',{'project':p,'title':f'{args.label}-{name}','outputDirectory':str(out)})
            deadline=started+180
            while job['state'] not in {'complete','failed','cancelled'} and time.monotonic()<deadline:
                time.sleep(.3);job=api('/api/render/'+job['id'])
            assert job['state']=='complete',job
            assert job['postflight']['ok'];result=job['result']
        else:result=render_project(p,out/f'{args.label}-{name}.mp4')
        path=Path(result['path']);assert decode_test(path)[0]
        with av.open(str(path)) as container:
            frames=[f.to_ndarray(format='rgb24') for f in container.decode(video=0)]
        expected=round((p['exportRange']['out']-p['exportRange']['in'])*p['canvas']['fps'])
        assert len(frames)==expected,(name,len(frames),expected)
        samples[name]=frames[8].astype(float)
        row={'case':name,'ok':True,'frames':len(frames),'wallSeconds':round(time.monotonic()-started,3),'result':result}
        results.append(row);case_projects[name]=p
        (out/f'{args.label}-results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
        print(json.dumps({k:v for k,v in row.items() if k!='result'}),flush=True)
    try:
        contexts=[] if args.directions_only or args.stress_only else ['ocean'] if args.world_fast_only else args.contexts or (['ocean','video'] if args.compact else ['ocean','japan','flat','image','video','layers'])
        for context in contexts:
            for space in ['flat','scene']:
                p=copy.deepcopy(base);bg=p['background'];bg['textSpace']=space
                if context=='japan':bg['sceneKit']='japan'
                if context=='flat':bg['visual']='aurora'
                if context in ['image','video']:bg.update(type=context,assetId=(image if context=='image' else video).id)
                if context=='layers':
                    bg.update(footageEnabled=True,tracks=['V1','V2'],clips=[
                        {'id':'v','start':0,'end':2,'in':0,'rate':1,'asset':video.public(),'track':0},
                        {'id':'visual','start':0,'end':2,'in':0,'rate':1,'track':1,'opacity':.3,'asset':{'kind':'visual','settings':{'visual':'scene3d','sceneKit':'ocean','weather':'snow'}}}],effects={'particles':30,'spectrum':40,'gradient':20})
                prefix=f'{context}-{space}';render(prefix+'-clear',p)
                if context in ['image','video']:
                    # Catch a missing source even when all effect exports succeed.
                    assert samples[prefix+'-clear'][:100].mean()>30,(prefix,'Missing background footage')
                for weather in (['rain','snow'] if args.compact else ['rain','snow','fog','storm','leaves']):
                    wet=copy.deepcopy(p);wet['background'].update(weather=weather,weatherLightning=False)
                    render(prefix+'-'+weather,wet)
                    difference=float(np.abs(samples[prefix+'-clear']-samples[prefix+'-'+weather]).mean())
                    assert difference>.025,(prefix,weather,difference)
                    results[-1]['weatherPixelDifference']=difference
        # Independent timed layers + unusual camera travel: one interval contains
        # both rain and snow above real footage, with 3D typography and particles.
        p=copy.deepcopy(base);p['background'].update(footageEnabled=True,textSpace='scene',tracks=['V1'],clips=[{'id':'v','start':0,'end':2,'asset':video.public(),'loop':True}],effects={'particles':25},
            effectClips=[{'id':kind,'kind':kind,'start':.5,'end':1.2,'amount':100,'attack':0,'release':0} for kind in ['rain','snow']])
        if args.stress_only:
            p['canvas']={'width':3840,'height':2160,'fps':60};p['exportRange']={'in':.5,'out':1};p['background']['effects'].update(spectrum=60,gradient=20)
        render('4k60-weather-footage-3d' if args.stress_only else 'timed-rain-snow-footage-3d',p)
        if args.stress_only:
            auto=copy.deepcopy(p);auto['export'].pop('bitrateMbps',None)
            render('4k60-weather-footage-3d-auto-bitrate',auto)
        if args.world_fast_only:
            fast=copy.deepcopy(base);fast['canvas']={'width':3840,'height':2160,'fps':60};fast['exportRange']={'in':.5,'out':1}
            fast['background'].update(textSpace='scene',weather='snow',weatherLightning=False,effects={'rain':70})
            render('4k60-ocean-weather-direct-GPU',fast)
        for direction in ([] if args.stress_only else ['up','bank'] if args.compact else ['forward','left','right','up','down','ascend','dive','drift','bank']):
            p=copy.deepcopy(base);p['background'].update(weather='snow',textSpace='scene',sceneDirection=direction)
            render('ocean-direction-'+direction,p)
        # Extract one frame for honest visual inspection.
        from PIL import Image
        names=['ocean-flat-clear','ocean-flat-rain','ocean-flat-snow','video-scene-clear','video-scene-rain','video-scene-snow']
        tiles=[Image.fromarray(samples[name].astype('uint8')).resize((320,180)) for name in names if name in samples]
        sheet=Image.new('RGB',(960,360))
        for index,tile in enumerate(tiles):sheet.paste(tile,((index%3)*320,(index//3)*180))
        sheet.save(out/f'{args.label}-contact.png')
        (out/f'{args.label}-results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
        (out/f'{args.label}-projects.json').write_text(json.dumps(case_projects,indent=2),encoding='utf-8')
    finally:
        delete_asset(video.id);delete_asset(image.id)


if __name__=='__main__':main()
