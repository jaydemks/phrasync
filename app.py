from __future__ import annotations

import argparse
import asyncio
import ipaddress
import json
import platform
import threading
import time
import webbrowser
from contextlib import asynccontextmanager
from pathlib import Path
from typing import Any, AsyncIterator

import uvicorn
from fastapi import Body, FastAPI, File, HTTPException, UploadFile
from fastapi import Request
from fastapi.responses import FileResponse, JSONResponse, PlainTextResponse
from fastapi.staticfiles import StaticFiles
from starlette.concurrency import run_in_threadpool

from phrasync import APP_NAME, APP_VERSION
from phrasync.cuda import configure_cuda_paths

CUDA_PATHS = configure_cuda_paths()

from phrasync.config import (
    ASSETS_DIR,
    DEFAULT_HOST,
    DEFAULT_PORT,
    PROJECTS_DIR,
    STATIC_DIR,
    UPLOADS_DIR,
    WORKSPACE,
)
from phrasync.align import align_cues, alignment_stats, estimate_offset
from phrasync.audio_analysis import AnalysisUnavailable, analyze_audio
from phrasync.font_utils import font_status
from phrasync.jobs import manager
from phrasync.media import ffmpeg_exe, probe_duration
from phrasync.ocr import OCRUnavailable, capability_status as ocr_status, ocr_image
from phrasync.qa import preflight_project
from phrasync.storage import delete_asset, get_asset, get_av_asset, list_assets, store_stream
from phrasync.server import (
    available_port,
    browser_host,
    install_windows_transport_error_filter,
    instance_url,
)
from phrasync.settings import apply_saved_settings, hf_token_status, remove_hf_token, save_hf_token
from phrasync.subtitles import (
    cues_to_ass,
    cues_to_enhanced_lrc,
    cues_to_lrc,
    cues_to_srt,
    cues_to_vtt,
    parse_lyrics_file,
)
from phrasync.transcribe import (
    TranscriptionUnavailable,
    capability_status as transcription_status,
    transcribe_audio,
)

apply_saved_settings()


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncIterator[None]:
    install_windows_transport_error_filter(asyncio.get_running_loop())
    yield


app = FastAPI(
    title=APP_NAME,
    version=APP_VERSION,
    docs_url="/api/docs",
    redoc_url=None,
    lifespan=lifespan,
)
server: uvicorn.Server | None = None
class RevalidatingStatic(StaticFiles):
    """Serve editor assets with must-revalidate.

    Without it a browser happily keeps a cached app.js after an update and the
    editor silently runs old code against new markup, which looks like a bug in
    the app rather than a stale file. ETags keep the revalidation cheap.
    """

    def file_response(self, *args, **kwargs):
        response = super().file_response(*args, **kwargs)
        response.headers["Cache-Control"] = "no-cache, must-revalidate"
        return response


app.mount("/static", RevalidatingStatic(directory=STATIC_DIR), name="static")
app.mount("/media", StaticFiles(directory=UPLOADS_DIR), name="media")
app.mount("/bundled", StaticFiles(directory=ASSETS_DIR), name="bundled")


@app.get("/", include_in_schema=False)
def index() -> FileResponse:
    return FileResponse(STATIC_DIR / "index.html")


@app.get("/favicon.svg", include_in_schema=False)
def favicon() -> FileResponse:
    return FileResponse(STATIC_DIR / "favicon.svg", media_type="image/svg+xml")


@app.get("/api/health")
def health() -> dict[str, Any]:
    try:
        ffmpeg = ffmpeg_exe()
        ffmpeg_ok = True
    except Exception as exc:
        ffmpeg = str(exc)
        ffmpeg_ok = False
    return {
        "app": APP_NAME,
        "version": APP_VERSION,
        "platform": platform.platform(),
        "python": platform.python_version(),
        "workspace": str(WORKSPACE),
        "ffmpeg": {"available": ffmpeg_ok, "path": ffmpeg},
        "ocr": ocr_status(),
        "transcription": transcription_status(),
        "fonts": font_status(),
        "cudaPaths": CUDA_PATHS,
    }


@app.get("/api/instance")
def instance() -> dict[str, str]:
    """Lightweight identity check used by the cross-platform launcher."""
    return {"app": APP_NAME, "version": APP_VERSION}


def _require_local_request(request: Request) -> None:
    try:
        is_local = ipaddress.ip_address(request.client.host).is_loopback if request.client else False
    except ValueError:
        is_local = False
    if not is_local:
        raise HTTPException(status_code=403, detail="Local settings are only available on this computer")


@app.post("/api/shutdown")
def shutdown(request: Request) -> dict[str, bool]:
    """Gracefully stop a locally launched server without killing a process."""
    _require_local_request(request)
    if server is None:
        raise HTTPException(status_code=409, detail="This server is not managed by the launcher")
    server.should_exit = True
    return {"stopping": True}


@app.get("/api/settings")
def settings_status(request: Request) -> dict[str, Any]:
    _require_local_request(request)
    return {"huggingFace": hf_token_status()}


@app.put("/api/settings/hugging-face")
def update_hugging_face_settings(request: Request, payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    _require_local_request(request)
    try:
        return {"huggingFace": save_hf_token(str(payload.get("token") or ""))}
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc


@app.delete("/api/settings/hugging-face")
def delete_hugging_face_settings(request: Request) -> dict[str, Any]:
    _require_local_request(request)
    return {"huggingFace": remove_hf_token()}


@app.get("/api/assets")
def assets() -> dict[str, Any]:
    return {"assets": list_assets()}


@app.post("/api/assets/{kind}")
def upload_asset(kind: str, file: UploadFile = File(...)) -> dict[str, Any]:
    try:
        asset = store_stream(kind, file.filename or "asset", file.file)
        result = asset.public()
        if kind in {"audio", "video"}:
            result["duration"] = probe_duration(Path(asset.path))
        return result
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Upload failed: {exc}") from exc
    finally:
        file.file.close()


@app.delete("/api/assets/{asset_id}")
def remove_asset(asset_id: str) -> dict[str, bool]:
    return {"deleted": delete_asset(asset_id)}


@app.post("/api/ocr")
async def run_ocr(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    asset = get_asset(payload.get("assetId"), "image")
    if not asset:
        raise HTTPException(status_code=404, detail="OCR image asset not found")
    try:
        return await run_in_threadpool(
            ocr_image, Path(asset.path), str(payload.get("language", "auto"))
        )
    except OCRUnavailable as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"OCR failed: {exc}") from exc


@app.post("/api/transcribe")
async def run_transcription(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    asset = get_av_asset(payload.get("assetId"))
    if not asset:
        raise HTTPException(status_code=404, detail="Audio or video source not found")
    try:
        result = await run_in_threadpool(
            transcribe_audio,
            Path(asset.path),
            str(payload.get("model", "base")),
            str(payload.get("language", "auto")),
            bool(payload.get("vadFilter", False)),
            None,
            None,
            payload.get("languageSpans") or None,
        )
        if payload.get("align", True):
            try:
                analysis = await run_in_threadpool(analyze_audio, Path(asset.path), True)
                aligned = await run_in_threadpool(align_cues, result["cues"], analysis)
                result["cues"] = aligned["cues"]
                result["alignment"] = aligned["report"]
                result["alignmentStats"] = alignment_stats(aligned["cues"], analysis)
            except Exception as exc:  # alignment is a bonus pass, never fatal
                result["alignment"] = {"error": str(exc)}
        return result
    except TranscriptionUnavailable as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Transcription failed: {exc}") from exc


@app.post("/api/transcriptions")
def create_transcription_job(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    asset = get_av_asset(payload.get("assetId"))
    if not asset:
        raise HTTPException(status_code=404, detail="Audio or video source not found")
    job = manager.create_transcription(
        Path(asset.path),
        str(payload.get("model", "base")),
        str(payload.get("language", "auto")),
        bool(payload.get("vadFilter", False)),
        bool(payload.get("align", True)),
        payload.get("languageSpans") or None,
    )
    return JSONResponse(job.public(), status_code=202)


@app.get("/api/transcriptions/{job_id}")
def get_transcription_job(job_id: str) -> dict[str, Any]:
    job = manager.get(job_id)
    if not job or job.kind != "transcription":
        raise HTTPException(status_code=404, detail="Transcription job not found")
    return job.public()


@app.post("/api/transcriptions/{job_id}/cancel")
def cancel_transcription(job_id: str) -> dict[str, bool]:
    job = manager.get(job_id)
    if not job or job.kind != "transcription":
        raise HTTPException(status_code=404, detail="Transcription job not found")
    return {"cancelled": manager.cancel(job_id)}


@app.post("/api/analyze")
async def analyze(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    asset = get_av_asset(payload.get("assetId"))
    if not asset:
        raise HTTPException(status_code=404, detail="Audio or video source not found")
    try:
        return await run_in_threadpool(
            analyze_audio, Path(asset.path), not bool(payload.get("refresh"))
        )
    except AnalysisUnavailable as exc:
        raise HTTPException(status_code=501, detail=str(exc)) from exc
    except Exception as exc:
        raise HTTPException(status_code=500, detail=f"Analysis failed: {exc}") from exc


@app.post("/api/align")
async def align(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    cues = payload.get("cues") or []
    if not cues:
        raise HTTPException(status_code=400, detail="No cues to align")
    analysis = payload.get("analysis")
    if not analysis:
        asset = get_av_asset(payload.get("assetId"))
        if not asset:
            raise HTTPException(status_code=400, detail="Provide analysis data or an audio/video assetId")
        analysis = await run_in_threadpool(analyze_audio, Path(asset.path), True)
    options = payload.get("options") or {}
    result = await run_in_threadpool(
        align_cues,
        cues,
        analysis,
        offset=options.get("offset"),
        snap_words=bool(options.get("snapWords", True)),
        word_window=float(options.get("wordWindow", 0.14)),
        word_strength=float(options.get("wordStrength", 0.85)),
        snap_phrases=bool(options.get("snapPhrases", False)),
        phrase_grid=str(options.get("phraseGrid", "beat")),
        auto_offset=bool(options.get("autoOffset", True)),
    )
    result["stats"] = alignment_stats(result["cues"], analysis)
    return result


@app.post("/api/align/offset")
async def align_offset(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    cues = payload.get("cues") or []
    analysis = payload.get("analysis") or {}
    if not analysis:
        asset = get_av_asset(payload.get("assetId"))
        if not asset:
            raise HTTPException(status_code=400, detail="Provide analysis data or an audio/video assetId")
        analysis = await run_in_threadpool(analyze_audio, Path(asset.path), True)
    return await run_in_threadpool(estimate_offset, cues, analysis.get("onsets") or [])


@app.post("/api/lyrics/import")
def import_lyrics(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    asset = get_asset(payload.get("assetId"), "lyrics")
    if not asset:
        raise HTTPException(status_code=404, detail="Lyrics asset not found")
    try:
        cues = parse_lyrics_file(Path(asset.path), duration=payload.get("duration"))
        return {"cues": cues}
    except Exception as exc:
        raise HTTPException(status_code=400, detail=f"Could not parse lyrics: {exc}") from exc


@app.post("/api/lyrics/export/{format_name}")
def export_lyrics(format_name: str, payload: dict[str, Any] = Body(...)):
    cues = payload.get("cues") or []
    if format_name == "srt":
        return PlainTextResponse(cues_to_srt(cues), media_type="application/x-subrip")
    if format_name == "lrc":
        return PlainTextResponse(cues_to_lrc(cues), media_type="text/plain")
    if format_name == "vtt":
        return PlainTextResponse(cues_to_vtt(cues), media_type="text/vtt")
    if format_name == "elrc":
        return PlainTextResponse(cues_to_enhanced_lrc(cues), media_type="text/plain")
    if format_name == "ass":
        # Carries the per-word timing into Aegisub, mpv, ffmpeg and the NLEs.
        return PlainTextResponse(
            cues_to_ass(cues, payload.get("style") or {}, payload.get("canvas") or {}),
            media_type="text/x-ssa",
        )
    raise HTTPException(
        status_code=400,
        detail="Supported lyric formats: srt, vtt, lrc, elrc, ass",
    )


@app.post("/api/preflight")
def preflight(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    project = payload.get("project", payload)
    return preflight_project(project).public()


@app.post("/api/render")
def create_render(payload: dict[str, Any] = Body(...)) -> JSONResponse:
    project = payload.get("project")
    if not isinstance(project, dict):
        raise HTTPException(status_code=400, detail="Missing project payload")
    title = str(payload.get("title") or project.get("title") or "phrasync_export")
    job = manager.create_render(project, title)
    return JSONResponse(job.public(), status_code=202)


@app.get("/api/render/{job_id}")
def render_status(job_id: str) -> dict[str, Any]:
    job = manager.get(job_id)
    if not job:
        raise HTTPException(status_code=404, detail="Render job not found")
    return job.public()


@app.post("/api/render/{job_id}/cancel")
def cancel_render(job_id: str) -> dict[str, bool]:
    return {"cancelled": manager.cancel(job_id)}


@app.get("/api/render/{job_id}/download")
def download_render(job_id: str) -> FileResponse:
    path = manager.output_path(job_id)
    if not path:
        raise HTTPException(status_code=404, detail="Rendered file is not ready")
    return FileResponse(path, media_type="video/mp4", filename=path.name)


@app.post("/api/projects/save")
def save_project(payload: dict[str, Any] = Body(...)) -> dict[str, Any]:
    project = payload.get("project", payload)
    title = str(project.get("title") or "untitled")
    safe = "".join(char if char.isalnum() or char in "-_" else "_" for char in title)[:64] or "untitled"
    path = PROJECTS_DIR / f"{safe}.phrasync.json"
    path.write_text(json.dumps(project, indent=2, ensure_ascii=False), encoding="utf-8")
    return {"saved": True, "path": str(path), "filename": path.name}


def _open_browser(host: str, port: int) -> None:
    time.sleep(0.9)
    webbrowser.open(f"http://{browser_host(host)}:{port}")


def main() -> None:
    global server
    parser = argparse.ArgumentParser(description=f"Run {APP_NAME}")
    parser.add_argument("--host", default=DEFAULT_HOST)
    parser.add_argument("--port", type=int, default=DEFAULT_PORT)
    parser.add_argument("--no-browser", action="store_true")
    parser.add_argument("--reload", action="store_true")
    parser.add_argument(
        "--strict-port",
        action="store_true",
        help="fail instead of selecting another port when the requested port is busy",
    )
    args = parser.parse_args()

    existing = instance_url(args.host, args.port)
    if existing and not args.reload:
        print(f"{APP_NAME} is already running at {existing}")
        if not args.no_browser:
            webbrowser.open(existing)
        return

    selected_port = args.port
    if not args.strict_port:
        selected_port = available_port(args.host, args.port)
        if selected_port != args.port:
            print(f"Port {args.port} is in use; starting {APP_NAME} on port {selected_port}.")
    if not args.no_browser and not args.reload:
        threading.Thread(target=_open_browser, args=(args.host, selected_port), daemon=True).start()

    if args.reload:
        # Reload needs an import string so Uvicorn can recreate the application.
        uvicorn.run("app:app", host=args.host, port=selected_port, reload=True, log_level="info")
        return

    # Passing the app object keeps this module's server reference available to
    # the local /api/shutdown endpoint.
    config = uvicorn.Config(app, host=args.host, port=selected_port, log_level="info")
    server = uvicorn.Server(config)
    server.run()


if __name__ == "__main__":
    main()
