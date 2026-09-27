"""Smoke-test an actual ocean MP4 from the packaged local server."""
import argparse
import json
import time
import urllib.request
from pathlib import Path
from qa_scene import DevTools, websocket_url


def main():
    parser=argparse.ArgumentParser()
    parser.add_argument('--url',default='http://127.0.0.1:5513')
    parser.add_argument('--debug-port',type=int,default=9227)
    args=parser.parse_args()
    dev=DevTools(websocket_url(args.debug_port),origin=None)
    try:
        project=dev.eval('JSON.parse(JSON.stringify(DEFAULT_PROJECT))')
        # Only stage the ocean in an untouched sample project, never a user's edit.
        shown=dev.eval("""(() => {
          if(project.audioAssetId || project.title!=='Untitled lyric video')return false;
          for(const [id,v] of [['visualSelect','scene3d'],['sceneKit','ocean'],['sceneDirection','forward'],['daytime','sunset']]){
            const e=document.getElementById(id);e.value=v;e.dispatchEvent(new Event('input'));e.dispatchEvent(new Event('change'));
          }
          document.querySelectorAll('dialog[open]').forEach(d=>d.close());
          seekTo(3);return true;
        })()""")
    finally:
        dev.close()
    project.update(title='Ocean packaged smoke',duration=1.6,__renderOrigin=args.url)
    project['canvas'].update(width=640,height=360,fps=12)
    project['background'].update(type='dynamic',visual='scene3d',sceneKit='ocean',daytime='sunset',textSpace='flat',shade=0,grain=0)
    project['style'].update(preset='minimal',fontSize=80,fontPreset='modern')
    project['cues']=[{'id':'qa-ocean','start':.3,'end':1.4,'text':'LOST IN THE OCEAN','words':[]}]
    request=urllib.request.Request(args.url+'/api/render',data=json.dumps({'project':project}).encode(),headers={'Content-Type':'application/json'})
    with urllib.request.urlopen(request) as response:job=json.load(response)
    deadline=time.monotonic()+120
    while job['state'] not in ('complete','failed','cancelled') and time.monotonic()<deadline:
        time.sleep(.5)
        with urllib.request.urlopen(args.url+'/api/render/'+job['id']) as response:job=json.load(response)
    assert job['state']=='complete',job
    out=Path('qa_out/ocean-packaged-smoke.mp4')
    urllib.request.urlretrieve(args.url+job['result']['downloadUrl'],out)
    print(json.dumps({'oceanPreviewSelected':shown,'result':job['result'],'file':str(out.resolve())}))


if __name__=='__main__':main()
