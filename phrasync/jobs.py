from __future__ import annotations

import json
import re
import threading
import traceback
import uuid
from concurrent.futures import ThreadPoolExecutor
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from .config import JOBS_DIR, RENDERS_DIR
from .align import align_cues, alignment_stats
from .audio_analysis import analyze_audio
from .qa import postflight_render, preflight_project
from .renderer import render_project
from .transcribe import TranscriptionCancelled, transcribe_audio


def _utc_now() -> str:
    return datetime.now(timezone.utc).isoformat()


def _safe_title(value: str) -> str:
    cleaned = re.sub(r"[^A-Za-z0-9._-]+", "_", value.strip()).strip("._")
    return cleaned[:64] or "phrasync_export"


@dataclass
class Job:
    id: str
    kind: str
    state: str = "queued"
    progress: float = 0.0
    message: str = "Queued"
    created_at: str = field(default_factory=_utc_now)
    updated_at: str = field(default_factory=_utc_now)
    result: dict[str, Any] | None = None
    error: str | None = None
    traceback: str | None = None
    preflight: dict[str, Any] | None = None
    postflight: dict[str, Any] | None = None
    request: dict[str, Any] | None = None
    cancel_requested: bool = False

    def public(self) -> dict[str, Any]:
        data = asdict(self)
        data.pop("traceback", None)
        return data


class JobManager:
    def __init__(self) -> None:
        self.jobs: dict[str, Job] = {}
        self.lock = threading.RLock()
        self.executor = ThreadPoolExecutor(max_workers=1, thread_name_prefix="phrasync-job")

    def _save(self, job: Job) -> None:
        job.updated_at = _utc_now()
        (JOBS_DIR / f"{job.id}.json").write_text(
            json.dumps(job.public(), indent=2), encoding="utf-8"
        )

    def create_render(self, project: dict[str, Any], title: str = "phrasync_export") -> Job:
        job = Job(id=uuid.uuid4().hex, kind="render")
        with self.lock:
            self.jobs[job.id] = job
            self._save(job)
        self.executor.submit(self._run_render, job.id, project, title)
        return job

    def create_transcription(
        self,
        path: Path,
        model: str,
        language: str,
        vad_filter: bool,
        align: bool = True,
        language_spans: list[dict[str, Any]] | None = None,
    ) -> Job:
        job = Job(
            id=uuid.uuid4().hex,
            kind="transcription",
            message="Waiting to transcribe",
            request={
                "model": model,
                "language": language or "auto",
                "task": "transcribe",
                "vadFilter": bool(vad_filter),
                "align": bool(align),
                "languageSpans": list(language_spans or []),
            },
        )
        with self.lock:
            self.jobs[job.id] = job
            self._save(job)
        self.executor.submit(
            self._run_transcription,
            job.id,
            path,
            model,
            language,
            vad_filter,
            align,
            language_spans,
        )
        return job

    def _run_transcription(
        self,
        job_id: str,
        path: Path,
        model: str,
        language: str,
        vad_filter: bool,
        align: bool,
        language_spans: list[dict[str, Any]] | None = None,
    ) -> None:
        job = self.get(job_id)
        if not job:
            return

        def cancelled() -> bool:
            with self.lock:
                return job.cancel_requested

        def update(value: float, message: str) -> None:
            with self.lock:
                job.progress = max(job.progress, min(0.84, 0.04 + float(value) * 0.80))
                job.message = message
                self._save(job)

        try:
            if cancelled():
                raise TranscriptionCancelled("Transcription cancelled")
            with self.lock:
                job.state = "running"
                job.progress = 0.02
                job.message = f"Loading Whisper {model}"
                self._save(job)

            result = transcribe_audio(
                path,
                model,
                language,
                vad_filter,
                progress=update,
                cancel_check=cancelled,
                language_spans=language_spans,
            )
            if cancelled():
                raise TranscriptionCancelled("Transcription cancelled")

            if align:
                with self.lock:
                    job.progress = 0.88
                    job.message = "Analysing audio for alignment"
                    self._save(job)
                analysis = analyze_audio(path, True)
                if cancelled():
                    raise TranscriptionCancelled("Transcription cancelled")
                aligned = align_cues(result["cues"], analysis)
                result["cues"] = aligned["cues"]
                result["alignment"] = aligned["report"]
                result["alignmentStats"] = alignment_stats(aligned["cues"], analysis)

            with self.lock:
                job.result = result
                job.state = "complete"
                job.progress = 1.0
                job.message = "Transcription complete"
                self._save(job)
        except TranscriptionCancelled:
            with self.lock:
                job.state = "cancelled"
                job.message = "Transcription cancelled"
                job.error = None
                self._save(job)
        except Exception as exc:
            with self.lock:
                job.state = "cancelled" if job.cancel_requested else "failed"
                job.error = None if job.cancel_requested else str(exc)
                job.traceback = traceback.format_exc()
                job.message = "Transcription cancelled" if job.cancel_requested else "Transcription failed"
                self._save(job)

    def _run_render(self, job_id: str, project: dict[str, Any], title: str) -> None:
        job = self.get(job_id)
        if not job:
            return
        try:
            report = preflight_project(project)
            with self.lock:
                job.preflight = report.public()
                if not report.ok:
                    job.state = "failed"
                    job.error = "Preflight critic found blocking errors."
                    job.progress = 1.0
                    job.message = "Preflight failed"
                    self._save(job)
                    return
                job.state = "running"
                job.progress = 0.01
                job.message = "Starting renderer"
                self._save(job)

            output_name = f"{_safe_title(title)}_{job.id[:8]}.mp4"
            output_path = RENDERS_DIR / output_name

            def update(value: float, message: str) -> None:
                with self.lock:
                    job.progress = max(job.progress, min(1.0, float(value)))
                    job.message = message
                    self._save(job)

            def cancelled() -> bool:
                with self.lock:
                    return job.cancel_requested

            result = render_project(project, output_path, progress=update, cancel_check=cancelled)
            postflight = postflight_render(output_path, expected_duration=result.get("duration"))
            result["filename"] = output_name
            result["downloadUrl"] = f"/api/render/{job.id}/download"
            with self.lock:
                job.result = result
                job.postflight = postflight.public()
                job.progress = 1.0
                if postflight.ok:
                    job.state = "complete"
                    job.message = "Render complete"
                else:
                    job.state = "failed"
                    job.error = "Post-render critic found a blocking error."
                    job.message = "Postflight failed"
                self._save(job)
        except Exception as exc:
            with self.lock:
                job.state = "cancelled" if job.cancel_requested else "failed"
                job.error = str(exc)
                job.traceback = traceback.format_exc()
                job.progress = 1.0
                job.message = "Cancelled" if job.cancel_requested else "Render failed"
                self._save(job)

    def get(self, job_id: str) -> Job | None:
        with self.lock:
            return self.jobs.get(job_id)

    def cancel(self, job_id: str) -> bool:
        with self.lock:
            job = self.jobs.get(job_id)
            if not job or job.state not in {"queued", "running"}:
                return False
            job.cancel_requested = True
            job.message = "Cancellation requested"
            self._save(job)
            return True

    def output_path(self, job_id: str) -> Path | None:
        job = self.get(job_id)
        if not job or not job.result:
            return None
        path = Path(job.result.get("path", ""))
        return path if path.exists() else None


manager = JobManager()
