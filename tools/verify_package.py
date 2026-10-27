"""Exercise frozen stdin collection, safe shell arguments, and GUI startup."""
import argparse
import base64
import json
import os
from pathlib import Path
import subprocess
import sys
import uuid


def main():
    parser = argparse.ArgumentParser()
    parser.add_argument("--scratch", type=Path, required=True)
    args = parser.parse_args()
    project = Path(__file__).resolve().parents[1]
    sys.path.insert(0, str(project / "src"))
    from workbuddy_pet.integration import powershell_command
    exe = project / "dist/WorkBuddyDesktopPet/WorkBuddyDesktopPet.exe"
    root = args.scratch.absolute() / ("verify-" + uuid.uuid4().hex)
    payload = json.dumps({"session_id": "synthetic-packaged-test", "prompt": "NEVER-WRITE-THIS"}).encode()
    result = subprocess.run([str(exe), "--root", str(root), "--hook", "UserPromptSubmit"],
                            input=payload, capture_output=True, timeout=15)
    assert result.returncode == 0 and not result.stdout, "Frozen collector failed"
    files = list((root / "events").glob("*.jsonl"))
    assert len(files) == 1 and b"NEVER-WRITE-THIS" not in files[0].read_bytes()
    # Real PowerShell stdin forwarding, including apostrophes and spaces in paths.
    shell_root = root / "spaces and ' quote"
    command = powershell_command([str(exe), "--root", str(shell_root), "--hook", "Stop"])
    result = subprocess.run(command.split(), input=payload, capture_output=True, timeout=15)
    assert result.returncode == 0 and not result.stdout
    assert list((shell_root / "events").glob("*.jsonl")), "PowerShell lost stdin or literal arguments"
    gui_root = root / "gui"
    env = dict(os.environ, QT_QPA_PLATFORM="offscreen")
    result = subprocess.run([str(exe), "--root", str(gui_root), "--demo", "--smoke-seconds", "2",
                             "--capture", str(root / "preview.png")], env=env, capture_output=True, timeout=20)
    assert result.returncode == 0, f"Frozen GUI failed: exit={result.returncode}, stderr={result.stderr[-2000:]!r}"
    runtime = json.loads((gui_root / "runtime.json").read_text(encoding="utf-8"))
    assert runtime["demo"] is True and runtime["version"] == "0.1.0"
    assert (root / "preview.png").is_file()
    print(json.dumps({"frozen_collector": True, "powershell_stdin": True, "frozen_gui": True,
                      "capture": str(root / "preview.png")}, indent=2))


if __name__ == "__main__":
    main()
