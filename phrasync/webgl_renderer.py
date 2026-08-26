from __future__ import annotations

import json
import shutil
import socket
import subprocess
import tempfile
import time
import urllib.request
from pathlib import Path
from typing import Any, Callable
from urllib.parse import urlparse

from websockets.sync.client import connect


ProgressCallback = Callable[[float, str], None]


def _browser_path() -> Path:
    candidates = (
        shutil.which("chrome"),
        shutil.which("chromium"),
        shutil.which("microsoft-edge"),
        r"C:\Program Files\Google\Chrome\Application\chrome.exe",
        r"C:\Program Files (x86)\Microsoft\Edge\Application\msedge.exe",
        "/Applications/Google Chrome.app/Contents/MacOS/Google Chrome",
        "/Applications/Microsoft Edge.app/Contents/MacOS/Microsoft Edge",
        "/usr/bin/google-chrome",
        "/usr/bin/chromium",
        "/usr/bin/chromium-browser",
    )
    for candidate in candidates:
        if candidate and Path(candidate).exists():
            return Path(candidate)
    raise RuntimeError("Chrome or Edge is required to export Odyssey WebGL video.")


def _free_port() -> int:
    with socket.socket() as handle:
        handle.bind(("127.0.0.1", 0))
        return int(handle.getsockname()[1])


def _local_origin(value: Any) -> str:
    parsed = urlparse(str(value or ""))
    if parsed.scheme != "http" or parsed.hostname not in {"127.0.0.1", "localhost", "::1"}:
        raise RuntimeError("The WebGL export origin must be the running local Phrasync server.")
    return f"{parsed.scheme}://{parsed.netloc}"


def _target_socket(port: int) -> str:
    endpoint = f"http://127.0.0.1:{port}/json/list"
    for _ in range(100):
        try:
            with urllib.request.urlopen(endpoint, timeout=0.5) as response:
                targets = json.load(response)
            return next(item["webSocketDebuggerUrl"] for item in targets if item.get("type") == "page")
        except (OSError, StopIteration, KeyError):
            time.sleep(0.1)
    raise RuntimeError("The WebGL export browser did not become ready.")


class _DevTools:
    def __init__(self, url: str, port: int):
        self.socket = connect(url, origin=f"http://localhost:{port}", max_size=None)
        self.counter = 0

    def call(self, method: str, params: dict[str, Any] | None = None) -> dict[str, Any]:
        self.counter += 1
        request_id = self.counter
        self.socket.send(json.dumps({"id": request_id, "method": method, "params": params or {}}))
        while True:
            reply = json.loads(self.socket.recv())
            if reply.get("id") != request_id:
                continue
            if "error" in reply:
                raise RuntimeError(f"Chrome {method}: {reply['error']}")
            return reply.get("result", {})

    def evaluate(self, expression: str, *, await_promise: bool = True) -> Any:
        result = self.call("Runtime.evaluate", {
            "expression": expression,
            "awaitPromise": await_promise,
            "returnByValue": True,
        }).get("result", {})
        if result.get("subtype") == "error":
            raise RuntimeError(result.get("description") or "WebGL browser evaluation failed")
        return result.get("value")

    def close(self) -> None:
        self.socket.close()


def render_webgl_video(
    project: dict[str, Any],
    encoded_path: Path,
    *,
    width: int,
    height: int,
    fps: int,
    frame_count: int,
    envelope: list[float],
    progress: ProgressCallback | None = None,
    cancel_check: Callable[[], bool] | None = None,
) -> None:
    """Render the real Odyssey WebGL canvas through Chromium WebCodecs."""
    origin = _local_origin(project.get("__renderOrigin"))
    port = _free_port()
    browser = _browser_path()
    encoded_path.unlink(missing_ok=True)

    clean_project = json.loads(json.dumps(project))
    clean_project.pop("__renderOrigin", None)
    clean_project["audio"] = None
    bitrate = int(max(2_000_000, min(28_000_000, width * height * fps * 0.14)))
    key_interval = max(1, fps * 2)

    with tempfile.TemporaryDirectory(prefix="phrasync-webgl-", ignore_cleanup_errors=True) as folder:
        temp_dir = Path(folder)
        profile = temp_dir / "profile"
        download = temp_dir / "download"
        profile.mkdir()
        download.mkdir()
        flags = 0
        if hasattr(subprocess, "CREATE_NO_WINDOW"):
            flags = subprocess.CREATE_NO_WINDOW
        process = subprocess.Popen(
            [
                str(browser), "--headless=new", "--hide-scrollbars", "--mute-audio",
                "--enable-webgl", "--use-angle=swiftshader", "--enable-unsafe-swiftshader",
                f"--remote-debugging-port={port}", "--remote-allow-origins=*",
                f"--user-data-dir={profile}", f"--window-size={width},{height}", "about:blank",
            ],
            stdout=subprocess.DEVNULL,
            stderr=subprocess.DEVNULL,
            creationflags=flags,
        )
        devtools: _DevTools | None = None
        try:
            devtools = _DevTools(_target_socket(port), port)
            devtools.call("Page.enable")
            devtools.call("Runtime.enable")
            devtools.call("Browser.setDownloadBehavior", {
                "behavior": "allow", "downloadPath": str(download), "eventsEnabled": True,
            })
            devtools.call("Emulation.setDeviceMetricsOverride", {
                "width": width, "height": height, "deviceScaleFactor": 1, "mobile": False,
            })
            devtools.call("Page.navigate", {"url": origin})
            time.sleep(1.0)
            devtools.evaluate(
                "localStorage.setItem('phrasync.project.v1', "
                + json.dumps(json.dumps(clean_project)) + "); true"
            )
            devtools.call("Page.reload")

            ready = False
            for _ in range(120):
                ready = bool(devtools.evaluate(
                    "Boolean(window.VFSceneGL?.ready && window.VFExport && typeof project !== 'undefined')",
                    await_promise=False,
                ))
                if ready:
                    break
                time.sleep(0.1)
            if not ready:
                raise RuntimeError("Odyssey WebGL did not initialize in the export browser.")

            setup = {
                "project": clean_project,
                "width": width,
                "height": height,
                "fps": fps,
                "frames": frame_count,
                "bitrate": bitrate,
                "keyInterval": key_interval,
                "envelope": envelope,
            }
            script = """
            (() => {
              const cfg = %s;
              window.__vfEncodeState = { progress: 0, done: false, error: null };
              (async () => {
                try {
                  if (!window.VideoEncoder || !window.VideoFrame) {
                    throw new Error('This Chrome/Edge build does not provide WebCodecs.');
                  }
                  await VFExport.prepare(cfg.width, cfg.height, cfg.project);
                  const encoderConfig = {
                    codec: 'avc1.640028', width: cfg.width, height: cfg.height,
                    bitrate: cfg.bitrate, framerate: cfg.fps,
                    avc: { format: 'annexb' }, latencyMode: 'quality'
                  };
                  const support = await VideoEncoder.isConfigSupported(encoderConfig);
                  if (!support.supported) {
                    encoderConfig.codec = 'avc1.42001f';
                    const fallback = await VideoEncoder.isConfigSupported(encoderConfig);
                    if (!fallback.supported) throw new Error('H.264 WebCodecs encoding is unavailable.');
                  }
                  const chunks = [];
                  const encoder = new VideoEncoder({
                    output(chunk) {
                      const bytes = new Uint8Array(chunk.byteLength);
                      chunk.copyTo(bytes);
                      chunks.push(bytes);
                    },
                    error(error) { window.__vfEncodeState.error = String(error); }
                  });
                  encoder.configure(encoderConfig);
                  const duration = Math.round(1000000 / cfg.fps);
                  for (let index = 0; index < cfg.frames; index += 1) {
                    if (window.__vfEncodeState.cancel) throw new Error('Render cancelled');
                    await VFExport.renderFrame(index / cfg.fps, cfg.envelope[index] || 0);
                    const frame = new VideoFrame(VFExport.canvas(), {
                      timestamp: Math.round(index * 1000000 / cfg.fps), duration
                    });
                    encoder.encode(frame, { keyFrame: index %% cfg.keyInterval === 0 });
                    frame.close();
                    while (encoder.encodeQueueSize > 10) {
                      await new Promise(resolve => setTimeout(resolve, 0));
                    }
                    window.__vfEncodeState.progress = (index + 1) / cfg.frames;
                    if (index %% 6 === 0) await new Promise(resolve => requestAnimationFrame(resolve));
                  }
                  await encoder.flush();
                  encoder.close();
                  if (window.__vfEncodeState.error) throw new Error(window.__vfEncodeState.error);
                  const link = document.createElement('a');
                  link.download = 'odyssey.h264';
                  link.href = URL.createObjectURL(new Blob(chunks, { type: 'video/h264' }));
                  document.body.append(link);
                  link.click();
                  window.__vfEncodeState.done = true;
                } catch (error) {
                  window.__vfEncodeState.error = error?.stack || String(error);
                  window.__vfEncodeState.done = true;
                }
              })();
              return true;
            })()
            """ % json.dumps(setup, separators=(",", ":"))
            devtools.evaluate(script, await_promise=False)

            while True:
                if cancel_check and cancel_check():
                    devtools.evaluate("window.__vfEncodeState.cancel = true", await_promise=False)
                    raise RuntimeError("Render cancelled")
                state = devtools.evaluate("window.__vfEncodeState", await_promise=False) or {}
                value = float(state.get("progress") or 0)
                if progress:
                    progress(0.06 + value * 0.82, f"Rendering WebGL frame {max(1, int(value * frame_count))}/{frame_count}")
                if state.get("done"):
                    if state.get("error"):
                        raise RuntimeError(f"WebGL export failed: {state['error']}")
                    break
                time.sleep(0.25)

            downloaded = download / "odyssey.h264"
            for _ in range(120):
                partials = list(download.glob("*.crdownload"))
                if downloaded.exists() and downloaded.stat().st_size > 0 and not partials:
                    break
                time.sleep(0.1)
            if not downloaded.exists() or downloaded.stat().st_size == 0:
                raise RuntimeError("Chrome did not produce the encoded Odyssey video stream.")
            shutil.copyfile(downloaded, encoded_path)
        finally:
            if devtools:
                devtools.close()
            process.terminate()
            try:
                process.wait(timeout=4)
            except subprocess.TimeoutExpired:
                process.kill()
                process.wait(timeout=4)
