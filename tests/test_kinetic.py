"""Preview/export parity for the kinetic lyric engine.

static/kinetic.js drives the browser preview and phrasync/kinetic.py drives the
MP4 export. They must agree, so this evaluates the JavaScript in Node and
compares it against the Python implementation over a grid of inputs. When Node
is unavailable the JS half is skipped and the Python invariants still run.
"""

from __future__ import annotations

import json
import shutil
import subprocess
from pathlib import Path

import pytest

from phrasync import kinetic

ROOT = Path(__file__).resolve().parent.parent
KINETIC_JS = ROOT / "static" / "kinetic.js"

CUE = {"id": "cue-1", "start": 2.0, "end": 6.0, "text": "hold the line tonight", "words": []}
TIMED_CUE = {
    "id": "cue-2",
    "start": 1.0,
    "end": 4.0,
    "text": "one two three",
    "words": [
        {"text": "one", "start": 1.0, "end": 1.6},
        {"text": "two", "start": 1.8, "end": 2.4},
        {"text": "three", "start": 2.6, "end": 3.9},
    ],
}
STYLE = {"fontSize": 160, "maxWidth": 88, "fontPreset": "impact"}
CANVAS = {"width": 1920, "height": 1080}

HARNESS = r"""
const fs = require("fs");
global.window = {};
new Function(fs.readFileSync(process.argv[2], "utf8"))();
const K = global.window.VFKinetic;
const input = JSON.parse(fs.readFileSync(process.argv[3], "utf8"));

const out = { words: {}, states: [], budget: [], focus: {}, beat: [], lines: {} };

for (const [name, cue] of Object.entries(input.cues)) {
  out.words[name] = K.cueWords(cue).map(w => [w.text, +w.start.toFixed(6), +w.end.toFixed(6)]);
}
for (const [name, cue] of Object.entries(input.cues)) {
  const words = K.cueWords(cue);
  for (const presetId of input.presets) {
    const spec = K.preset(presetId);
    for (const t of input.times) {
      for (const beat of input.beats) {
        for (const word of words) {
          const s = K.wordState(word, cue, t, spec, beat);
          out.states.push([
            name, presetId, t, beat, word.text,
            s.visible ? 1 : 0,
            +s.opacity.toFixed(6), +s.scale.toFixed(6), +s.dx.toFixed(6),
            +s.dy.toFixed(6), +s.rotate.toFixed(6), +s.blur.toFixed(6),
            +s.fill.toFixed(6), +s.fillAlpha.toFixed(6), +s.glow.toFixed(6), s.role
          ]);
        }
      }
    }
  }
}
out.budget = [];
for (const presetId of input.presets)
  for (const style of input.styles)
    out.budget.push(K.charBudget(style, input.canvas, K.preset(presetId)));
for (const token of input.tokens) out.focus[token] = +K.focusScale(token).toFixed(6);
for (const [t, bpm, offset] of input.beatArgs) out.beat.push(+K.beatPulse(t, bpm, offset).toFixed(6));
for (const presetId of input.presets) {
  const words = K.cueWords(input.cues.plain);
  out.lines[presetId] = K.layoutLines(words, K.preset(presetId), input.budget)
    .map(line => line.map(w => w.text));
}
process.stdout.write(JSON.stringify(out));
"""


def _node_results(payload: dict) -> dict:
    node = shutil.which("node")
    if not node:
        pytest.skip("Node.js is not installed; skipping cross-engine parity check")
    tmp = ROOT / ".kinetic_parity"
    tmp.mkdir(exist_ok=True)
    harness = tmp / "harness.js"
    data = tmp / "input.json"
    try:
        harness.write_text(HARNESS, encoding="utf-8")
        data.write_text(json.dumps(payload), encoding="utf-8")
        result = subprocess.run(
            [node, str(harness), str(KINETIC_JS), str(data)],
            capture_output=True, text=True, timeout=120,
        )
        if result.returncode != 0:
            pytest.fail(f"Node harness failed: {result.stderr[:800]}")
        return json.loads(result.stdout)
    finally:
        shutil.rmtree(tmp, ignore_errors=True)


def test_python_word_timing_is_monotonic():
    words = kinetic.cue_words(CUE)
    assert len(words) == 4
    assert words[0]["start"] == pytest.approx(CUE["start"])
    for previous, current in zip(words, words[1:]):
        assert current["start"] >= previous["start"]
        assert current["end"] > current["start"]


def test_every_preset_has_a_python_and_js_twin():
    js = KINETIC_JS.read_text(encoding="utf-8")
    for preset_id in kinetic.PRESETS:
        assert f'"{preset_id}"' in js, f"{preset_id} missing from static/kinetic.js"


def test_engines_agree():
    presets = list(kinetic.PRESETS)
    times = [0.5, 1.9, 2.0, 2.05, 2.3, 3.0, 4.4, 5.9, 6.0, 6.15, 6.4, 7.5]
    beats = [0.0, 0.7]
    tokens = ["I", "love", "passwords", "certainty", "a"]
    beat_args = [[1.0, 120.0, 0.2], [2.34, 139.67, 0.4094], [5.0, 0.0, 0.0]]
    styles = [
        {"fontSize": 160, "maxWidth": 88, "fontPreset": "impact"},
        {"fontSize": 90, "maxWidth": 70, "fontPreset": "modern"},
        {"fontSize": 240, "maxWidth": 96, "fontPreset": "mono"},
    ]
    cues = {"plain": CUE, "timed": TIMED_CUE}
    payload = {
        "cues": cues, "presets": presets, "times": times, "beats": beats,
        "styles": styles, "canvas": CANVAS, "tokens": tokens,
        "beatArgs": beat_args, "budget": 22,
    }
    js = _node_results(payload)

    for name, cue in cues.items():
        expected = [
            [word["text"], round(word["start"], 6), round(word["end"], 6)]
            for word in kinetic.cue_words(cue)
        ]
        assert js["words"][name] == expected, f"cue_words mismatch for {name}"

    index = 0
    for name, cue in cues.items():
        words = kinetic.cue_words(cue)
        for preset_id in presets:
            spec = kinetic.get_preset(preset_id)
            for t in times:
                for beat in beats:
                    for word in words:
                        state = kinetic.word_state(word, cue, t, spec, beat)
                        row = js["states"][index]
                        index += 1
                        label = f"{name}/{preset_id}/t={t}/beat={beat}/{word['text']}"
                        assert row[:5] == [name, preset_id, t, beat, word["text"]], label
                        assert row[5] == (1 if state.visible else 0), label
                        for offset, value in enumerate(
                            [state.opacity, state.scale, state.dx, state.dy,
                             state.rotate, state.blur, state.fill, state.fill_alpha,
                             state.glow]
                        ):
                            assert row[6 + offset] == pytest.approx(value, abs=1e-6), (
                                f"{label} field {offset}"
                            )
                        assert row[15] == state.role, label
    assert index == len(js["states"])

    cursor = 0
    for preset_id in presets:
        spec = kinetic.get_preset(preset_id)
        for style in styles:
            assert js["budget"][cursor] == kinetic.char_budget(style, CANVAS, spec), (preset_id, style)
            cursor += 1
    for token in tokens:
        assert js["focus"][token] == pytest.approx(kinetic.focus_scale(token), abs=1e-6)
    for row, (t, bpm, offset) in zip(js["beat"], beat_args):
        assert row == pytest.approx(kinetic.beat_pulse(t, bpm, offset), abs=1e-6)

    words = kinetic.cue_words(CUE)
    for preset_id in presets:
        spec = kinetic.get_preset(preset_id)
        expected = [[word["text"] for word in line] for line in kinetic.layout_lines(words, spec, 22)]
        assert js["lines"][preset_id] == expected, f"layout mismatch for {preset_id}"
