"""Real packaged transcription with VAD+alignment and native icon inspection."""
import argparse
import ctypes
import json
import time
import urllib.request
from pathlib import Path


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument('--url', default='http://127.0.0.1:5512')
    parser.add_argument('--pid', type=int, required=True)
    parser.add_argument('--model', default='base')
    parser.add_argument('--version', default='0.4.1')
    args = parser.parse_args()

    def call(path, payload=None, binary=None):
        data = binary if binary is not None else json.dumps(payload).encode() if payload is not None else None
        req = urllib.request.Request(args.url + path, data=data,
            headers={'Content-Type':'application/octet-stream' if binary is not None else 'application/json'})
        with urllib.request.urlopen(req, timeout=60) as response:
            return json.load(response)

    health = call('/api/health')
    assert health['version'] == args.version, health
    asset = call('/api/assets/audio/stream?filename=qa-packaged-onset.wav',
                 binary=Path('qa_out/timing-known-onset.wav').read_bytes())
    job = call('/api/transcriptions', {'assetId':asset['id'], 'model':args.model,
        'language':'en', 'vadFilter':True, 'align':True})
    deadline = time.monotonic() + 120
    download = []
    while job['state'] not in ('complete', 'failed', 'cancelled') and time.monotonic() < deadline:
        time.sleep(.5)
        job = call('/api/transcriptions/' + job['id'])
        if job.get('phase') == 'model-download':
            download.append({'bytes':job.get('downloaded_bytes'), 'total':job.get('total_bytes')})
    assert job['state'] == 'complete', job
    assert job['result']['cues'], job
    assert not job['result'].get('alignment', {}).get('error'), job

    user = ctypes.windll.user32
    user.SendMessageW.argtypes = [ctypes.c_void_p, ctypes.c_uint, ctypes.c_size_t, ctypes.c_ssize_t]
    user.SendMessageW.restype = ctypes.c_ssize_t
    icons = []
    callback_type = ctypes.WINFUNCTYPE(ctypes.c_bool, ctypes.c_void_p, ctypes.c_ssize_t)

    @callback_type
    def visit(hwnd, _):
        pid = ctypes.c_ulong()
        user.GetWindowThreadProcessId(ctypes.c_void_p(hwnd), ctypes.byref(pid))
        if pid.value == args.pid and user.IsWindowVisible(ctypes.c_void_p(hwnd)):
            icon = user.SendMessageW(hwnd, 0x007F, 1, 0)
            if icon:
                icons.append(icon)
        return True

    user.EnumWindows(visit, 0)
    assert icons, 'No native application window icon found'
    result = {'version':health['version'], 'job':job['id'], 'state':job['state'],
              'device':job['result']['device'], 'cues':len(job['result']['cues']), 'nativeIcon':True,
              'model':args.model, 'download':download}
    print(json.dumps(result))
    Path('qa_out/packaged-verification.json').write_text(json.dumps(result, indent=2), encoding='utf-8')


if __name__ == '__main__':
    main()
