"""Direct contextual-world screenshot review, without editor transport."""
import json, subprocess, sys, tempfile, time
from pathlib import Path
from PIL import Image, ImageDraw
from qa_scene import DevTools, chrome_path, websocket_url

root=Path(__file__).resolve().parents[1]
out=root/'qa_out/context-world-review.jpg';out.parent.mkdir(exist_ok=True)
with tempfile.TemporaryDirectory(prefix='context-world-') as profile:
    server=subprocess.Popen([sys.executable,'-m','http.server','5592','--bind','127.0.0.1'],cwd=root,stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    browser=subprocess.Popen([str(chrome_path()),'--headless=new','--remote-debugging-port=9232','--remote-allow-origins=*','--window-size=960,620',f'--user-data-dir={profile}','http://127.0.0.1:5592/'],stdout=subprocess.DEVNULL,stderr=subprocess.DEVNULL)
    dev=None
    try:
        dev=DevTools(websocket_url(9232));time.sleep(.6);dev.call('Page.navigate',{'url':'http://127.0.0.1:5592/'});time.sleep(.6)
        dev.eval("""(async()=>{document.body.innerHTML='<canvas id="world"></canvas>';document.body.style.cssText='margin:0;overflow:hidden';await import('/static/scene3d-gl.js');window.testWorld=VFSceneGL.get(document.querySelector('canvas'));testWorld.setSize(960,540);})()""")
        sheet=Image.new('RGB',(1200,1432),'#20232a');draw=ImageDraw.Draw(sheet);report=[]
        for row,kit in enumerate(['japan','italy','china','usa']):
            for col,direction in enumerate(['forward','left']):
                options={'direction':direction,'artStyle':'cinematic','environment':{'daytime':'day','season':'summer','weather':'clear'}}
                result=dev.eval(f"testWorld.build('{kit}');testWorld.update(7.25,{json.dumps(options)});testWorld.render();({{draws:testWorld.renderer.info.render.calls,triangles:testWorld.renderer.info.render.triangles}})")
                shot=dev.shot('#world').resize((600,337));sheet.paste(shot,(col*600,row*358));draw.text((col*600+8,row*358+340),f'{kit} / {direction}',fill='white');report.append({'kit':kit,'direction':direction,'render':result})
        sheet.save(out);print(json.dumps({'image':str(out),'cases':report}))
    finally:
        if dev:dev.close()
        browser.terminate();server.terminate();browser.wait(timeout=15);server.wait(timeout=15);time.sleep(.5)
