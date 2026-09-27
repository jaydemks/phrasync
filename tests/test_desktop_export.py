from pathlib import Path
from unittest.mock import Mock

import webview

from phrasync.desktop_export import DesktopExportBridge


def test_choose_directory_and_save_completed_mp4(tmp_path, monkeypatch):
    bridge = DesktopExportBridge()
    export_dir = tmp_path / "my exports"
    export_dir.mkdir()
    source = export_dir / "song_123.mp4"
    source.write_bytes(b"mp4 data")
    copy_path = tmp_path / "copy.mp4"
    bridge._window = Mock()
    bridge._window.create_file_dialog.side_effect = [(str(export_dir),), (str(copy_path),)]
    monkeypatch.setattr("phrasync.desktop_export.manager.output_path", lambda job_id: source if job_id == "done" else None)

    assert bridge.choose_render_directory() == str(export_dir.resolve())
    assert bridge.get_render_directory() == str(export_dir.resolve())
    assert bridge.save_render_as("done") == str(copy_path.resolve())
    assert copy_path.read_bytes() == b"mp4 data"
    assert bridge._window.create_file_dialog.call_args_list[0].args[0] == webview.FileDialog.FOLDER
    assert bridge._window.create_file_dialog.call_args_list[1].args[0] == webview.FileDialog.SAVE


def test_cancelled_dialog_does_not_change_destination(tmp_path):
    bridge = DesktopExportBridge()
    bridge._window = Mock()
    bridge._window.create_file_dialog.return_value = None
    original = bridge.get_render_directory()
    assert bridge.choose_render_directory() is None
    assert bridge.get_render_directory() == original


def test_open_render_folder_uses_completed_job_location(tmp_path, monkeypatch):
    bridge = DesktopExportBridge()
    source = tmp_path / "render.mp4"
    source.write_bytes(b"video")
    monkeypatch.setattr("phrasync.desktop_export.manager.output_path", lambda _: source)
    launched = []
    monkeypatch.setattr("phrasync.desktop_export.subprocess.Popen", lambda args, **kwargs: launched.append(args))
    assert bridge.open_render_directory("done") == str(tmp_path)
    assert launched == [["explorer.exe", str(tmp_path)]]


def test_open_default_folder_ignores_selected_export_folder(tmp_path, monkeypatch):
    bridge = DesktopExportBridge()
    bridge._directory = tmp_path / "chosen"
    default = tmp_path / ".phrasync" / "renders"
    monkeypatch.setattr("phrasync.desktop_export.RENDERS_DIR", default)
    launched = []
    monkeypatch.setattr("phrasync.desktop_export.subprocess.Popen", lambda args, **kwargs: launched.append(args))
    assert bridge.open_default_render_directory() == str(default)
    assert default.is_dir()
    assert launched == [["explorer.exe", str(default)]]
