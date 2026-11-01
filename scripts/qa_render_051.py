"""Local-only report regression cases. Never edits original projects or publishes."""
import copy
import argparse
import json
from pathlib import Path
import sys
import time
sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from phrasync import webgl_renderer
from phrasync.renderer import render_project
from phrasync.media import decode_test, run_ffmpeg
from phrasync.storage import get_asset, store_path, delete_asset
from phrasync.config import UPLOADS_DIR

ROOT = Path(__file__).resolve().parents[1]
OUT = ROOT/'qa_out/render-051'


def main():
    parser=argparse.ArgumentParser();parser.add_argument('--label',default='review-final');args=parser.parse_args()
    OUT.mkdir(parents=True, exist_ok=True)
    p = json.loads((ROOT/'qa_out/real-project-050/I_Still_Wait_real_footage.phrasync.json').read_text(encoding='utf-8'))
    assert get_asset(p['audioAssetId']) and get_asset(p['background']['clips'][0]['asset']['id'])
    p['__renderOrigin'] = 'http://127.0.0.1:5571'
    p['background']['type'] = 'video'
    p['background']['textSpace'] = 'scene'
    p['style']['preset'] = 'constellation'
    p['export'] = {'preset': 'fast', 'bitrateMbps': 50}
    cases = []
    def add(name, size, fps, *, flat=False, effects=True, forced=None, ranged=True):
        c = copy.deepcopy(p)
        c['canvas'] = {'width': size[0], 'height': size[1], 'fps': fps}
        c['exportRange'] = {'in': 13, 'out': 15 if ranged else 29}
        c['background']['textSpace'] = 'flat' if flat else 'scene'
        if not effects: c['background']['effects'] = {}
        cases.append((name, c, forced))
    add('real-1080p30-constellation-all-fx', (1920,1080), 30, ranged=False)
    add('real-portrait-3d-fx', (1080,1920), 30)
    add('real-4k60-3d-fx', (3840,2160), 60)
    add('real-4k30-3d-fx', (3840,2160), 30)
    add('real-1080p30-2d-fx', (1920,1080), 30, flat=True)
    add('real-1080p30-2d-clean', (1920,1080), 30, flat=True, effects=False)
    add('real-stalled-gpu-flush-recovery', (1920,1080), 30, forced='flush')
    add('real-unavailable-webcodecs-nvenc', (1920,1080), 30, forced='unsupported')
    existing={path.name for path in UPLOADS_DIR.iterdir()}
    font = store_path('font', Path('C:/Windows/Fonts/arial.ttf'))
    custom = copy.deepcopy(cases[0][1]); custom['exportRange']['out'] = 15
    custom['style'].update(fontAssetId=font.id, fontName='Arial test')
    cases.append(('real-custom-font-3d-fx', custom, None))
    for _,candidate,forced in cases:
        if forced:
            candidate['background'].update(type='dynamic',visual='scene3d',sceneKit='ocean',footageEnabled=False,clips=[],effects={},effectClips=[],sceneWave=False)
            candidate['canvas']={'width':1280,'height':720,'fps':30};candidate['export'].pop('bitrateMbps',None)
    original = webgl_renderer._DevTools.evaluate
    current = None
    injected = False
    def evaluate(self, expression, **kwargs):
        nonlocal injected
        if current == 'unsupported' and expression.startswith('VFGPUEncoder.prepare'):
            injected=True
            return False
        if current == 'flush' and not injected and expression.startswith('VFGPUEncoder.batch'):
            injected = True
            original(self, 'VideoEncoder.prototype.flush = function(){return new Promise(()=>{})};true')
        return original(self, expression, **kwargs)
    webgl_renderer._DevTools.evaluate = evaluate
    results = []
    try:
        for name, project, forced in cases:
            current, injected = forced, False
            events = []
            started = time.monotonic()
            try:
                result = render_project(project, OUT/(args.label+'-'+name+'.mp4'), progress=lambda value,message:events.append([value,message]))
                assert decode_test(Path(result['path']))[0]
                assert result['frames'] == round(result['duration']*project['canvas']['fps'])
                if forced == 'flush':
                    assert injected,'GPU stall injection did not execute'
                    assert any('Recovering video encoder' in msg for _,msg in events)
                if forced=='unsupported':assert injected,'Unsupported codec injection did not execute'
                with __import__('av').open(result['path']) as container:
                    stream = container.streams.video[0]
                    assert stream.width == project['canvas']['width']
                    assert float(stream.average_rate) == project['canvas']['fps']
                    assert sum(1 for _ in container.decode(stream)) == result['frames']
                run_ffmpeg(['-y','-ss','0.8','-i',result['path'],'-frames:v','1','-vf','scale=960:-1',str(OUT/(name+'.jpg'))])
                row = {'case':name, 'ok':True, 'result':result, 'events':events}
            except Exception as error:
                row = {'case':name, 'ok':False, 'error':str(error), 'events':events}
            row['wallSeconds'] = round(time.monotonic()-started,3)
            results.append(row)
            (OUT/(args.label+'-real-results.json')).write_text(json.dumps(results,indent=2),encoding='utf-8')
            print(json.dumps({k:v for k,v in row.items() if k!='events'}),flush=True)
    finally:
        webgl_renderer._DevTools.evaluate = original
        if Path(font.path).name not in existing:delete_asset(font.id)
    assert all(row['ok'] for row in results)


if __name__ == '__main__':
    main()
