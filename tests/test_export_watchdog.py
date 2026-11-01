"""Stalled devices must recover or fail explicitly, never wait indefinitely."""
import json
from pathlib import Path
import shutil
import subprocess
from unittest.mock import Mock

import pytest
from phrasync import webgl_renderer as renderer


def test_export_command_times_out_even_if_unrelated_events_arrive(monkeypatch):
    dev = object.__new__(renderer._DevTools)
    dev.counter = 0
    dev.command_timeout = 2
    dev.cancel_check = None
    dev.socket = Mock()
    dev.socket.recv.return_value = json.dumps({'method': 'irrelevant.event'})
    clock = iter([0, 0, 0, 1, 1, 3])
    monkeypatch.setattr(renderer.time, 'monotonic', lambda: next(clock))
    with pytest.raises(TimeoutError, match='stopped responding'):
        dev.call('Runtime.evaluate')
    assert dev.socket.recv.call_count == 2


def test_export_cancel_interrupts_pending_browser_command():
    dev = object.__new__(renderer._DevTools)
    dev.counter = 0
    dev.command_timeout = 90
    dev.cancel_check = lambda: True
    dev.socket = Mock()
    with pytest.raises(RuntimeError, match='Render cancelled'):
        dev.call('Runtime.evaluate')
    dev.socket.recv.assert_not_called()


def test_gpu_recovery_restarts_once_with_full_project_in_new_session(monkeypatch, tmp_path):
    project = {'background': {'clips': [{'id': 'footage'}], 'effects': {'particles': 50}},
               'cues': [{'text': 'KEEP 3D TEXT'}], 'exportRange': {'in': 2, 'out': 3}}
    render = Mock(side_effect=[renderer.GPUExportRetry('flush stalled'), 'mp4'])
    monkeypatch.setattr(renderer, '_render_webgl_video_once', render)
    progress = Mock()
    assert renderer.render_webgl_video(project, tmp_path/'out.mp4', progress=progress) == 'mp4'
    assert render.call_count == 2
    assert all(call.args[0] is project for call in render.call_args_list)
    assert render.call_args_list[1].kwargs['_force_ffmpeg'] is True
    assert 'all footage' in progress.call_args.args[1]


def test_gpu_retry_never_loops_or_retries_cancellation(monkeypatch, tmp_path):
    render = Mock(side_effect=renderer.GPUExportRetry('stalled'))
    monkeypatch.setattr(renderer, '_render_webgl_video_once', render)
    with pytest.raises(renderer.GPUExportRetry):
        renderer.render_webgl_video({}, tmp_path/'out.mp4')
    assert render.call_count == 2
    render.reset_mock()
    with pytest.raises(RuntimeError, match='cancelled'):
        renderer.render_webgl_video({}, tmp_path/'out.mp4', cancel_check=lambda: True)
    assert render.call_count == 1


@pytest.mark.skipif(not shutil.which('node'), reason='Node required')
def test_gpu_flush_and_upload_stalls_are_bounded_and_abort_does_not_wait():
    source = (Path(__file__).resolve().parents[1]/'static/gpu-encoder.js').read_text(encoding='utf-8')
    script = r"""
const vm=require('node:vm'), assert=require('node:assert/strict');
function fixture(mode) {
 let closed=0, framesClosed=0, configuration;
 class Encoder {
  static async isConfigSupported(c){configuration=c;return {supported:true}}
  constructor(c){this.cb=c;this.state='unconfigured'}
  configure(){this.state='configured'}
  encode(){this.cb.output({byteLength:1,copyTo(){}})}
  flush(){return mode==='flush'?new Promise(()=>{}):Promise.resolve()}
  close(){closed++;this.state='closed'}
 }
 const context={window:{VideoEncoder:Encoder,VideoFrame:true},VideoEncoder:Encoder,
  VideoFrame:class{close(){framesClosed++}},AbortController,
  setTimeout:(cb,ms)=>setTimeout(cb,Math.min(ms,10)),clearTimeout,
  VFExport:{renderFrame:async()=>{},canvas:()=>({})},
  fetch:()=>mode==='upload'?new Promise(()=>{}):Promise.resolve({ok:true})};
 vm.runInNewContext(SOURCE,context);
 return {api:context.window.VFGPUEncoder,stats:()=>({closed,framesClosed,configuration})};
}
(async()=>{
 for(const mode of ['flush','upload']){
  const f=fixture(mode);assert(await f.api.prepare(320,180,30,2e6,'private'));
  await assert.rejects(f.api.batch([[0,0,[]]],30,0,60),/timed out/);
  await f.api.abort();assert.equal(f.stats().closed,1);assert.equal(f.stats().framesClosed,1);
  assert.equal(f.stats().configuration.latencyMode,'realtime');
 }
 const f=fixture('normal');await f.api.prepare(320,180,30,2e6,'private');
 await f.api.batch([[0,0,[]],[1/30,0,[]]],30,0,60);await f.api.finish();await f.api.abort();
 assert.equal(f.stats().closed,1);assert.equal(f.stats().framesClosed,2);
})().catch(e=>{console.error(e);process.exitCode=1});
""".replace('SOURCE', json.dumps(source))
    result = subprocess.run([shutil.which('node'), '-'], input=script, text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(not shutil.which('node'), reason='Node required')
def test_transcription_button_keeps_wand_and_resets_all_busy_states():
    source = (Path(__file__).resolve().parents[1]/'static/app-workflows.js').read_text(encoding='utf-8')
    script = r"""
const vm=require('node:vm'),assert=require('node:assert/strict');
const label={}, insight={}, attributes={}, classes={};
const button={disabled:false,classList:{toggle:(k,v)=>classes[k]=v},setAttribute:(k,v)=>attributes[k]=v};
const c={ITALIAN:{},project:{mode:'lyric'},els:{transcribeButton:button,whisperModel:{value:'base'}},
 document:{getElementById:id=>id==='modelInsight'?insight:label},t:x=>x,
 MODE_COPY:{lyric:{transcribe:'Generate lyrics'},subtitles:{transcribe:'Generate subtitles'}}};
vm.runInNewContext(SOURCE,c);
for(const phase of ['model-download','model-load','transcription']){
 c.setTranscriptionButtonState(true,phase);assert.equal(attributes['aria-busy'],'true');assert(classes['is-generating']);
}
c.setTranscriptionButtonState(false);assert.equal(label.textContent,'Generate lyrics');assert(!classes['is-generating']);
c.project.mode='subtitles';c.setTranscriptionButtonState(false);assert.equal(label.textContent,'Generate subtitles');
for(const value of ['tiny','base','small','medium','large-v3']){c.els.whisperModel.value=value;c.updateModelInsight();assert(insight.textContent.length>30)}
assert.equal(attributes['aria-busy'],'false');assert.equal(button.textContent,undefined);
""".replace('SOURCE', json.dumps(source))
    result = subprocess.run([shutil.which('node'), '-'], input=script, text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr


@pytest.mark.skipif(not shutil.which('node'), reason='Node required')
def test_footage_gradient_is_not_painted_over_3d_text():
    source = (Path(__file__).resolve().parents[1]/'static/media-effects.js').read_text(encoding='utf-8')
    script = r"""
const vm=require('node:vm'),assert=require('node:assert/strict');let fills=0;
const project={background:{type:'video',textSpace:'scene',effects:{gradient:50}}};
const ctx={canvas:{width:1920,height:1080},save(){},restore(){},fillRect(){fills++},
 createLinearGradient:()=>({addColorStop(){}})};
const c={window:{},project};vm.runInNewContext(SOURCE,c);const media=c.window.VFMedia;
assert(media.gradientUnderText());media.drawGradient(ctx);assert.equal(fills,1);
media.drawOverlay(ctx,0,0);assert.equal(fills,1);
project.background={type:'dynamic',footageEnabled:true,visual:'scene3d',effects:{gradient:50}};
assert(media.gradientUnderText());media.drawOverlay(ctx,0,0);assert.equal(fills,1);
project.background.footageEnabled=false;assert(!media.gradientUnderText());
media.drawOverlay(ctx,0,0);assert.equal(fills,2);
""".replace('SOURCE', json.dumps(source))
    result = subprocess.run([shutil.which('node'), '-'], input=script, text=True, capture_output=True, timeout=10)
    assert result.returncode == 0, result.stderr
