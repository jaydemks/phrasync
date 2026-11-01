"""Cancel a real packaged export after its first frames, not a mocked job."""
import json
from pathlib import Path
import time
import urllib.request

origin='http://127.0.0.1:5573'
out=Path(__file__).resolve().parents[1]/'qa_out/custom-fonts-051'

def api(path,payload=None):
    req=urllib.request.Request(origin+path,data=json.dumps(payload).encode() if payload is not None else None,
        headers={'Origin':origin,'Content-Type':'application/json'})
    with urllib.request.urlopen(req,timeout=30) as response:return json.load(response)

project={'title':'Cancel QA','duration':20,'__renderOrigin':origin,'canvas':{'width':1280,'height':720,'fps':30},
    'background':{'type':'dynamic','visual':'scene3d','sceneKit':'ocean','textSpace':'scene','weather':'snow','daytime':'sunset'},
    'style':{'fontPreset':'impact','fontSize':100,'preset':'bold-stack'},
    'cues':[{'id':'cue','start':0,'end':20,'text':'Cancellation test'}],'export':{'preset':'fast'}}
job=api('/api/render',{'project':project,'title':'cancel-test','outputDirectory':str(out)})
deadline=time.monotonic()+60
while time.monotonic()<deadline:
    job=api('/api/render/'+job['id'])
    assert job['state'] not in {'failed','complete','cancelled'},job
    if job.get('progress',0)>.06:break
    time.sleep(.2)
else:raise RuntimeError('Export did not begin rendering in time')
started=time.monotonic();api('/api/render/'+job['id']+'/cancel',{})
while time.monotonic()-started<60:
    job=api('/api/render/'+job['id'])
    if job['state'] in {'failed','complete','cancelled'}:break
    time.sleep(.2)
assert job['state']=='cancelled',job
report={'ok':True,'state':job['state'],'secondsAfterCancel':round(time.monotonic()-started,3)}
(out/'packaged-cancellation.json').write_text(json.dumps(report,indent=2),encoding='utf-8')
print(json.dumps(report))
