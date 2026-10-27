import io
import json
import subprocess
import sys
import time
from dataclasses import replace
from pathlib import Path

from workbuddy_pet.cli import hook_main
from workbuddy_pet.spool import SpoolReader
from workbuddy_pet.state import derive_display, reduce_event


def test_collector_to_reducer_and_silent_hook_failure(tmp_path):
    for kind in ("UserPromptSubmit", "PreToolUse", "PostToolUse", "Stop"):
        raw = json.dumps({"session_id": "synthetic", "tool_use_id": "t", "tool_name": "Bash"}).encode()
        assert hook_main(kind, io.BytesIO(raw), tmp_path) == 0
    sessions = {}
    for event in SpoolReader(tmp_path / "events").poll():
        sessions = reduce_event(sessions, event)
    display = derive_display(sessions, time.time())
    assert display.state == "done" and len(display.reminders) == 1
    broken = tmp_path / "not-a-directory"
    broken.write_text("file")
    assert hook_main("Stop", io.BytesIO(raw), broken) == 0


def test_hook_dispatch_does_not_import_qt(tmp_path):
    script = "from workbuddy_pet.cli import main; import sys; main(['--hook','Stop','--root',sys.argv[1]]); assert not any(k.startswith('PySide6') for k in sys.modules)"
    import os
    env = dict(os.environ, PYTHONPATH=str(Path(__file__).resolve().parents[1] / "src"))
    result = subprocess.run([sys.executable, "-c", script, str(tmp_path)], input=b'{"session_id":"synthetic"}', capture_output=True, env=env)
    assert result.returncode == 0 and not result.stdout


def test_diagnostics_and_ack_survive_restart(tmp_path, qt_app):
    from workbuddy_pet.app import Controller
    from workbuddy_pet.cli import diagnose
    from workbuddy_pet.events import Event
    from workbuddy_pet.settings import save_settings, Settings
    assert diagnose(tmp_path)["state"] == "plugin_not_configured"
    save_settings(tmp_path, Settings(notifications=False))
    controller = Controller(qt_app, tmp_path, demo=True)
    controller.demo_timer.stop()
    controller.sessions = {}
    now = time.time()
    controller.consume([Event("submit", now, "s", "UserPromptSubmit"), Event("stop", now + 1, "s", "Stop")])
    controller.acknowledge()
    remembered = list(controller.acknowledged)
    controller.shutdown()
    other = Controller(qt_app, tmp_path, demo=True)
    other.demo_timer.stop()
    assert all(i in other.acknowledged for i in remembered)
    other.shutdown()
