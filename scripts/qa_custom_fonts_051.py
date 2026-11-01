"""Exercise real local font formats through the shared browser/export engine."""
import argparse
import copy
import json
from pathlib import Path
import sys
import time
import urllib.request
sys.path.insert(0,str(Path(__file__).resolve().parents[1]))
import av
from PIL import ImageFont
from phrasync.storage import store_path,delete_asset
from phrasync.config import UPLOADS_DIR
from phrasync.renderer import render_project
from phrasync.media import decode_test,run_ffmpeg

ROOT=Path(__file__).resolve().parents[1]


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--origin',default='http://127.0.0.1:5571');parser.add_argument('--api',action='store_true');parser.add_argument('--label',default='source');args=parser.parse_args()
    out=ROOT/'qa_out/custom-fonts-051';out.mkdir(parents=True,exist_ok=True)
    fonts=[('sans-ttf','arial.ttf'),('serif-ttf','georgia.ttf'),('mono-ttf','consola.ttf'),('display-otf','BebasNeue-Regular.otf'),('variable-ttf','bahnschrift.ttf'),('cjk-collection','msgothic.ttc')]
    before={p.name for p in UPLOADS_DIR.iterdir()};created=[];results=[]
    run_ffmpeg(['-y','-f','lavfi','-i','testsrc2=size=640x360:rate=30:duration=2','-c:v','libx264','-pix_fmt','yuv420p',str(out/'footage.mp4')])
    video=store_path('video',out/'footage.mp4');created.append(video.id)
    base={'title':'Custom font QA','duration':2,'__renderOrigin':args.origin,'canvas':{'width':1280,'height':720,'fps':30},
      'background':{'type':'dynamic','visual':'scene3d','sceneKit':'ocean','weather':'snow','daytime':'sunset','season':'summer','textSpace':'scene'},
      'style':{'fontPreset':'impact','fontSize':100,'preset':'bold-stack'},'cues':[{'id':'cue','start':0,'end':2,'text':'Font test 日本語 中文'}],
      'exportRange':{'in':.5,'out':.9},'export':{'preset':'fast'}}
    def api(path,payload=None):
        req=urllib.request.Request(args.origin+path,data=json.dumps(payload).encode() if payload is not None else None,headers={'Origin':args.origin,'Content-Type':'application/json'})
        with urllib.request.urlopen(req,timeout=30) as r:return json.load(r)
    try:
        for label,name in fonts:
            path=Path('C:/Windows/Fonts')/name;assert path.exists(),path
            asset=store_path('font',path)
            if Path(asset.path).name not in before:created.append(asset.id)
            font=ImageFont.truetype(str(path),20)
            try:axes=font.get_variation_axes()
            except OSError:axes=[]
            if label=='variable-ttf':assert axes,'Expected a real variable font'
            for space in ['flat','scene']:
                p=copy.deepcopy(base);p['style'].update(fontAssetId=asset.id,fontName=asset.name);p['background']['textSpace']=space
                if space=='scene':p['background'].update(footageEnabled=True,tracks=['V1'],clips=[{'id':'footage','asset':video.public(),'start':0,'end':2,'in':0,'rate':1}],effects={'particles':30,'gradient':20})
                started=time.monotonic()
                try:
                    if args.api:
                        job=api('/api/render',{'project':p,'title':f'{args.label}-{label}-{space}','outputDirectory':str(out)})
                        deadline=time.monotonic()+180
                        while job['state'] not in {'complete','failed','cancelled'} and time.monotonic()<deadline:
                            time.sleep(.3);job=api('/api/render/'+job['id'])
                        assert job['state']=='complete',job
                        assert job['postflight']['ok'];result=job['result']
                    else:result=render_project(p,out/f'{args.label}-{label}-{space}.mp4')
                    assert decode_test(Path(result['path']))[0]
                    with av.open(result['path']) as c:assert sum(1 for _ in c.decode(video=0))==12
                    row={'font':name,'kind':label,'textSpace':space,'ok':True,'wallSeconds':round(time.monotonic()-started,3),'result':result}
                except Exception as e:row={'font':name,'kind':label,'textSpace':space,'ok':False,'error':str(e)}
                results.append(row);(out/f'{args.label}-results.json').write_text(json.dumps(results,indent=2),encoding='utf-8')
                print(json.dumps({k:v for k,v in row.items() if k!='result'}),flush=True)
        assert all(row['ok'] for row in results),[r for r in results if not r['ok']]
    finally:
        for id in set(created):delete_asset(id)


if __name__=='__main__':main()
