import json
import shutil
import subprocess
from pathlib import Path

import pytest


def test_track_removal_preserves_library_reindexes_and_confirms():
    node = shutil.which("node")
    if not node:
        pytest.skip("Node unavailable")
    source = (Path(__file__).resolve().parents[1] / "static/app-visual-tracks.js").read_text(encoding="utf-8")
    probe = """
const ITALIAN={}, t=x=>x;let accepted=true;
async function confirmAction(){return accepted}
function refreshFootageControls(){} function footageChanged(){}
const project={background:{tracks:['V1','V2','V3'],footageEnabled:true,mediaLibrary:[{id:'original'}],clips:[{id:'a',track:0},{id:'b',track:1},{id:'c',track:2}]}};
    SOURCE
const assert=require('node:assert/strict');
(async()=>{
accepted=false;const before=JSON.stringify(project);await removeBackgroundTrack(1);assert.equal(JSON.stringify(project),before);
accepted=true;await removeBackgroundTrack(1);assert.deepEqual(project.background.clips,[{id:'a',track:0},{id:'c',track:1}]);assert.equal(project.background.mediaLibrary[0].id,'original');
await removeBackgroundTrack(0);assert.deepEqual(project.background.clips,[{id:'c',track:0}]);
await removeBackgroundTrack(0);assert.equal(project.background.tracks.length,0);assert.equal(project.background.clips.length,0);assert.equal(project.background.footageEnabled,false);assert.equal(project.background.mediaLibrary.length,1);
await removeBackgroundTrack(99);assert.equal(project.background.mediaLibrary.length,1);
})().catch(e=>{console.error(e);process.exitCode=1});
""".replace("SOURCE", source)
    result = subprocess.run([node, "-"], input=probe, text=True, capture_output=True, encoding="utf-8", timeout=30)
    assert result.returncode == 0, result.stderr
