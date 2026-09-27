"""Native, user-approved destinations for desktop video exports."""

from __future__ import annotations

import os
import shutil
import subprocess
import threading
from pathlib import Path

from .config import RENDERS_DIR
from .jobs import manager


class DesktopExportBridge:
    def __init__(self) -> None:
        self._window = None
        self._lock = threading.RLock()
        self._directory = RENDERS_DIR

    def get_render_directory(self) -> str:
        with self._lock:
            return str(self._directory)

    def choose_render_directory(self) -> str | None:
        if self._window is None:
            raise RuntimeError("Desktop window is not ready")
        import webview

        selected = self._window.create_file_dialog(
            webview.FileDialog.FOLDER, directory=self.get_render_directory()
        )
        if not selected:
            return None
        directory = Path(selected[0]).resolve()
        if not directory.is_dir():
            raise ValueError("The selected export folder does not exist")
        with self._lock:
            self._directory = directory
        return str(directory)

    def open_render_directory(self, job_id: str | None = None) -> str:
        path = manager.output_path(job_id) if job_id else None
        directory = path.parent if path else Path(self.get_render_directory())
        directory.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            subprocess.Popen(["explorer.exe", str(directory)], creationflags=0x08000000)
        else:
            raise RuntimeError("Opening a folder is only supported in the Windows desktop app")
        return str(directory)

    def open_default_render_directory(self) -> str:
        RENDERS_DIR.mkdir(parents=True, exist_ok=True)
        if os.name == "nt":
            subprocess.Popen(["explorer.exe", str(RENDERS_DIR)], creationflags=0x08000000)
        else:
            raise RuntimeError("Opening a folder is only supported in the Windows desktop app")
        return str(RENDERS_DIR)

    def save_render_as(self, job_id: str) -> str | None:
        source = manager.output_path(job_id)
        if source is None:
            raise FileNotFoundError("Rendered MP4 is not ready")
        if self._window is None:
            raise RuntimeError("Desktop window is not ready")
        import webview

        selected = self._window.create_file_dialog(
            webview.FileDialog.SAVE,
            directory=str(source.parent),
            save_filename=source.name,
            file_types=("MP4 video (*.mp4)",),
        )
        if not selected:
            return None
        target = Path(selected[0]).with_suffix(".mp4").resolve()
        if target != source.resolve():
            shutil.copy2(source, target)
        return str(target)
