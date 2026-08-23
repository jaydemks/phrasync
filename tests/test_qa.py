from phrasync.media import run_ffmpeg
from phrasync.qa import preflight_project
from phrasync.storage import delete_asset, store_path


def base_project():
    return {
        "canvas": {"width": 1280, "height": 720, "fps": 30},
        "duration": 4,
        "background": {"type": "dynamic", "visual": "aurora"},
        "style": {
            "fontPreset": "impact",
            "fontSize": 150,
            "maxWidth": 88,
            "textColor": "#f3d7ff",
        },
        "cues": [
            {"id": "a", "start": 0, "end": 2, "text": "STAND YOUR GROUND"},
            {"id": "b", "start": 2, "end": 4, "text": "KEEP MOVING"},
        ],
    }


def test_preflight_clean_enough_without_audio():
    report = preflight_project(base_project())
    assert report.ok
    assert any(issue.code == "no_audio" for issue in report.issues)
    assert report.metrics["cueCount"] == 2


def test_preflight_detects_logic_errors():
    project = base_project()
    project["canvas"]["fps"] = 120
    project["cues"] = []
    report = preflight_project(project)
    assert not report.ok
    codes = {issue.code for issue in report.issues}
    assert "fps_range" in codes
    assert "no_cues" in codes


def test_preflight_rejects_corrupt_background(tmp_path):
    source = tmp_path / "broken.mp4"
    source.write_bytes(b"this is not a video")
    asset = store_path("video", source)
    project = base_project()
    project["background"] = {"type": "video", "assetId": asset.id}
    try:
        report = preflight_project(project)
        assert "background_decode_failed" in {issue.code for issue in report.issues}
    finally:
        delete_asset(asset.id)


def test_preflight_rejects_video_source_without_audio(tmp_path):
    source = tmp_path / "silent.mp4"
    run_ffmpeg([
        "-y", "-f", "lavfi", "-i", "color=c=black:size=160x90:rate=12:duration=0.2",
        "-an", "-c:v", "libx264", "-pix_fmt", "yuv420p", str(source),
    ])
    asset = store_path("video", source)
    project = base_project()
    project["audioAssetId"] = asset.id
    try:
        report = preflight_project(project)
        assert not report.ok
        assert "audio_stream_missing" in {issue.code for issue in report.issues}
    finally:
        delete_asset(asset.id)


def test_preflight_blocks_preview_only_3d_export_modes():
    project = base_project()
    project["background"].update({"visual": "scene3d", "textSpace": "scene"})
    report = preflight_project(project)
    assert not report.ok
    codes = {issue.code for issue in report.issues}
    assert "odyssey_export_unsupported" in codes
    assert "text3d_export_unsupported" in codes


def test_preflight_blocks_flat_odyssey_export_until_renderer_has_parity():
    project = base_project()
    project["background"].update({"visual": "scene", "textSpace": "flat"})
    report = preflight_project(project)
    assert "odyssey_export_unsupported" in {issue.code for issue in report.issues}
