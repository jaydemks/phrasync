"""Refresh the native local candidate, retaining the user's current project."""
import time
from pathlib import Path
from qa_scene import DevTools, websocket_url

dev = DevTools(websocket_url(9227), origin=None)
try:
    dev.eval('scheduleSave()')
    time.sleep(2)
    assert dev.eval('JSON.stringify(project)===localStorage.getItem(STORAGE_KEY)')
    dev.call('Page.reload', {'ignoreCache': True})
    time.sleep(4)
    assert dev.eval("typeof initTextOrientation==='function'")
    # Reveal only the requested controls; retain all content and styling.
    dev.eval("els.textSpace.value='scene';els.textSpace.dispatchEvent(new Event('change'));document.querySelectorAll('dialog[open]').forEach(d=>d.close())")
    time.sleep(1)
    assert dev.eval("!document.getElementById('textOrientationControls').hidden")
    dev.shot('body').save(Path('qa_out/orientation-native.png'))
    print('Native candidate refreshed; project preserved; orientation controls available.')
finally:
    dev.close()
