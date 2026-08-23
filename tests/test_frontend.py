from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

import pytest


ROOT = Path(__file__).resolve().parent.parent
STATIC = ROOT / "static"
APP_SCRIPTS = [
    "app-state.js",
    "app-modes.js",
    "app-ui.js",
    "app-lyrics.js",
    "app-visuals.js",
    "app-cues.js",
    "app-workflows.js",
    "app-timeline.js",
    "app.js",
]


def test_frontend_fragments_are_ordered_once_and_stay_focused():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    positions = []
    for name in APP_SCRIPTS:
        tag = f'<script src="/static/{name}" defer></script>'
        assert html.count(tag) == 1, name
        positions.append(html.index(tag))
        assert len((STATIC / name).read_text(encoding="utf-8").splitlines()) <= 400, name
    assert positions == sorted(positions)


def test_frontend_fragments_compile_as_one_classic_script_scope():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is not installed")
    source = "\n".join((STATIC / name).read_text(encoding="utf-8") for name in APP_SCRIPTS)
    result = subprocess.run(
        [node, "--check", "-"],
        input=source,
        capture_output=True,
        text=True,
        encoding="utf-8",
        timeout=30,
    )
    assert result.returncode == 0, result.stderr


def test_3d_lyric_world_motion_is_linear_and_passes_camera():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is not installed")
    scene = (STATIC / "scene3d.js").read_text(encoding="utf-8")
    probe = """
global.window = global;
%s
const speed = 2;
const end = 4;
const samples = [-0.6, 0, end, end + 3.5].map(t =>
  VFScene.lyricBoardDistance(end, t, speed, 8));
if (VFScene.lyricBoardZ(end, speed, 8) !== -16) process.exit(1);
if (samples.join(',') !== '17.2,16,8,1') process.exit(2);
""" % scene
    result = subprocess.run(
        [node, "-"], input=probe, capture_output=True, text=True,
        encoding="utf-8", timeout=30,
    )
    assert result.returncode == 0, result.stderr


def test_3d_mode_is_not_coupled_to_background_or_canvas_visibility():
    visuals = (STATIC / "app-visuals.js").read_text(encoding="utf-8")
    lyrics = (STATIC / "app-lyrics.js").read_text(encoding="utf-8")
    ui = (STATIC / "app-ui.js").read_text(encoding="utf-8")

    lyric_mode = visuals[visuals.index("function lyric3DEnabled"):
                         visuals.index("function glLayerNeeded")]
    assert "textSpace === \"scene\"" in lyric_mode
    assert ".hidden" not in lyric_mode
    assert "prepareWebGLOverlay(time)" in visuals
    assert "project.background.type === \"dynamic\"" in visuals
    assert "glScene = prepareWebGLOverlay(time)" in visuals
    assert visuals.index("glScene = drawDynamicVisual(now)") < visuals.index("updatePlaybackUI(time)")
    assert visuals.index("updatePlaybackUI(time)") < visuals.index("glScene?.render()")

    assert "return lyric3DEnabled();" in lyrics
    assert "clearLyric();" in lyrics
    assert "lead: Math.max(spec.lead, 0.6)" in lyrics
    assert "|| project.background.textSpace === \"scene\"" in ui


def test_project_modes_and_environment_controls_are_wired():
    html = (STATIC / "index.html").read_text(encoding="utf-8")
    state = (STATIC / "app-state.js").read_text(encoding="utf-8")
    modes = (STATIC / "app-modes.js").read_text(encoding="utf-8")
    workflow = (STATIC / "app-workflows.js").read_text(encoding="utf-8")
    scene = (STATIC / "scene3d-gl.js").read_text(encoding="utf-8")

    for element_id in (
        "projectMode", "environmentMode", "weather", "daytime", "season",
        "environmentResolved", "text3dOffsetControls", "offset3DX", "offset3DY",
    ):
        assert f'id="{element_id}"' in html
        assert f'$("#{element_id}")' in state
    assert 'mode: "lyric"' in state
    assert 'mode === "subtitles"' in workflow
    assert 'uploadAsset(kind, file)' in workflow
    assert 'video/mp4' in modes and 'video/webm' in modes
    assert 'PRESET_LABELS_3D' in modes
    assert 'resolvedEnvironmentAt(t)' in modes
    assert 'from "/static/scene3d-environment.js"' in scene
    assert "const groundClearance = 0.32" in scene
    assert "style.offset3DX" in scene and "style.offset3DY" in scene
    assert "cam.x + slot.x" not in scene


def test_user_facing_copy_has_no_known_italian_leftovers():
    sources = "\n".join(
        path.read_text(encoding="utf-8")
        for path in [STATIC / "index.html", *sorted(STATIC.glob("*.js"))]
    )
    for leftover in (
        "Giappone", "Italia</option>", "Intensità motion", "Analizza audio",
        "Nessuna analisi", "Esporta</button>", "Mondo rigenerato",
        "Testo 3D non disponibile", "nessuna parola",
    ):
        assert leftover not in sources
