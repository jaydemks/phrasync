from __future__ import annotations

import re
import shutil
import subprocess
from pathlib import Path
from typing import Callable

import numpy as np

try:
    import imageio_ffmpeg
except ImportError:  # pragma: no cover - surfaced by health endpoint
    imageio_ffmpeg = None

DURATION_RE = re.compile(r"Duration:\s*(\d+):(\d+):(\d+(?:\.\d+)?)")


def ffmpeg_exe() -> str:
    override = shutil.which("ffmpeg")
    if override:
        return override
    if imageio_ffmpeg is not None:
        return imageio_ffmpeg.get_ffmpeg_exe()
    raise RuntimeError("FFmpeg is unavailable. Install imageio-ffmpeg or FFmpeg.")


def run_ffmpeg(args: list[str], *, check: bool = True, input_bytes: bytes | None = None) -> subprocess.CompletedProcess:
    command = [ffmpeg_exe(), *args]
    return subprocess.run(
        command,
        input=input_bytes,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        check=check,
    )


def probe_duration(path: Path) -> float | None:
    process = run_ffmpeg(["-hide_banner", "-i", str(path)], check=False)
    text = process.stderr.decode("utf-8", errors="replace")
    match = DURATION_RE.search(text)
    if not match:
        return None
    hours, minutes, seconds = match.groups()
    return int(hours) * 3600 + int(minutes) * 60 + float(seconds)


def decode_audio_mono(path: Path, sample_rate: int = 8000) -> np.ndarray:
    process = run_ffmpeg(
        [
            "-v",
            "error",
            "-i",
            str(path),
            "-vn",
            "-ac",
            "1",
            "-ar",
            str(sample_rate),
            "-f",
            "f32le",
            "pipe:1",
        ],
        check=True,
    )
    if not process.stdout:
        return np.zeros(0, dtype=np.float32)
    return np.frombuffer(process.stdout, dtype=np.float32).copy()


def audio_envelope(
    path: Path | None,
    duration: float,
    fps: int,
    sample_rate: int = 8000,
    progress: Callable[[float], None] | None = None,
) -> np.ndarray:
    frame_count = max(1, int(round(duration * fps)))
    if path is None:
        return np.zeros(frame_count, dtype=np.float32)
    samples = decode_audio_mono(path, sample_rate=sample_rate)
    if samples.size == 0:
        return np.zeros(frame_count, dtype=np.float32)
    per_frame = sample_rate / fps
    envelope = np.zeros(frame_count, dtype=np.float32)
    for frame in range(frame_count):
        start = int(frame * per_frame)
        end = min(samples.size, int((frame + 1) * per_frame))
        if end > start:
            chunk = samples[start:end]
            envelope[frame] = float(np.sqrt(np.mean(chunk * chunk) + 1e-12))
        if progress and frame % max(1, frame_count // 20) == 0:
            progress(frame / frame_count)
    peak = float(np.percentile(envelope, 98)) if envelope.size else 0.0
    if peak > 1e-6:
        envelope = np.clip(envelope / peak, 0.0, 1.25)
    # A small temporal smoothing makes visuals feel musical instead of jittery.
    if envelope.size >= 5:
        kernel = np.array([0.1, 0.2, 0.4, 0.2, 0.1], dtype=np.float32)
        envelope = np.convolve(envelope, kernel, mode="same").astype(np.float32)
    return envelope


def decode_test(path: Path) -> tuple[bool, str]:
    process = run_ffmpeg(
        ["-v", "error", "-i", str(path), "-map", "0", "-f", "null", "-"],
        check=False,
    )
    message = process.stderr.decode("utf-8", errors="replace").strip()
    return process.returncode == 0, message


def decode_video_frame(path: Path) -> tuple[bool, str]:
    """Decode one video frame to validate an input without scanning it in full."""
    process = run_ffmpeg(
        [
            "-v",
            "error",
            "-i",
            str(path),
            "-map",
            "0:v:0",
            "-frames:v",
            "1",
            "-f",
            "null",
            "-",
        ],
        check=False,
    )
    message = process.stderr.decode("utf-8", errors="replace").strip()
    return process.returncode == 0, message


def decode_audio_frame(path: Path) -> tuple[bool, str]:
    """Decode a short audio sample, failing cleanly when no audio stream exists."""
    process = run_ffmpeg(
        [
            "-v",
            "error",
            "-i",
            str(path),
            "-map",
            "0:a:0",
            "-t",
            "0.05",
            "-f",
            "null",
            "-",
        ],
        check=False,
    )
    message = process.stderr.decode("utf-8", errors="replace").strip()
    return process.returncode == 0, message
