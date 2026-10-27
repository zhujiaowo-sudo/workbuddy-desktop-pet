"""Dispatch hook collection before importing any Qt module."""
import argparse
import json
import os
import sys
import time
from pathlib import Path
from typing import BinaryIO

from .events import RAW_LIMIT, EVENT_KINDS, project_event
from .storage import data_root


def hook_main(event_name: str, stdin: BinaryIO, root: Path) -> int:
    try:
        raw = stdin.read(RAW_LIMIT + 1)
        if len(raw) > RAW_LIMIT:
            return 0
        value = json.loads(raw)
        event = project_event(event_name, value, time.time())
        if event:
            from .spool import write_event
            write_event(root / "events", event)
    except Exception:
        # Never surface hook payloads, block the parent, or make a permission decision.
        pass
    return 0


def hook_stdin() -> BinaryIO:
    if sys.stdin is not None:
        return sys.stdin.buffer
    if os.name == "nt":
        import ctypes
        import msvcrt
        kernel = ctypes.WinDLL("kernel32", use_last_error=True)
        kernel.GetStdHandle.restype = ctypes.c_void_p
        handle = kernel.GetStdHandle(-10)
        if handle and handle != ctypes.c_void_p(-1).value:
            return os.fdopen(msvcrt.open_osfhandle(handle, os.O_RDONLY | os.O_BINARY), "rb")
    import io
    return io.BytesIO()


def output(value: object) -> None:
    if sys.stdout:
        print(json.dumps(value, ensure_ascii=True, indent=2))


def diagnose(root: Path) -> dict:
    from . import __version__
    from .integration import PLUGIN_ID
    from .settings import load_settings
    from .spool import SpoolReader
    from .windows import validate_workbuddy_path
    settings = load_settings(root)
    app_found = False
    if settings.workbuddy_path:
        try:
            validate_workbuddy_path(Path(settings.workbuddy_path))
            app_found = True
        except (OSError, ValueError):
            pass
    counts = {}
    reader = SpoolReader(root / "events")
    # A bounded diagnostic scan; no content or identifiers in the exported result.
    for _ in range(32):
        batch = reader.poll()
        for event in batch:
            counts[event.kind] = counts.get(event.kind, 0) + 1
        if not batch:
            break
    configured = (root / "integration-receipt.json").is_file()
    return {"schema": 1, "version": __version__, "application_found": app_found,
            "plugin_id": PLUGIN_ID, "plugin_configured": configured,
            "state": "events_received" if counts else "waiting_for_event" if configured else "plugin_not_configured",
            "event_counts": counts, "events_not_observed": [k for k in EVENT_KINDS if k not in counts],
            "invalid_lines": reader.invalid_lines}


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="WorkBuddy 专用桌宠")
    parser.add_argument("--root", type=Path, default=data_root(), help="独立用户数据目录")
    parser.add_argument("--hook", choices=EVENT_KINDS)
    parser.add_argument("--diagnose", action="store_true")
    parser.add_argument("--install-integration", action="store_true")
    parser.add_argument("--uninstall-integration", action="store_true")
    parser.add_argument("--workbuddy-home", type=Path, default=Path.home() / ".workbuddy")
    parser.add_argument("--demo", action="store_true")
    parser.add_argument('--card-only',action='store_true',help='仅显示卡片，不加载人物动画')
    parser.add_argument('--import-pet',type=Path,help='将本地角色 ZIP 或文件夹导入角色库')
    parser.add_argument('--list-pets',action='store_true',help='列出已导入的本地角色')
    parser.add_argument("--quit", action="store_true")
    parser.add_argument("--settings", action="store_true")
    parser.add_argument("--smoke-seconds", type=float, default=0, help=argparse.SUPPRESS)
    parser.add_argument("--capture", type=Path, help=argparse.SUPPRESS)
    parser.add_argument('--capture-page',choices=('summary','details','data','chat','materials','settings','capsule'),default='summary',help=argparse.SUPPRESS)
    args = parser.parse_args(argv)
    if args.hook:
        try:
            return hook_main(args.hook, hook_stdin(), args.root)
        except Exception:
            return 0
    if args.install_integration or args.uninstall_integration:
        from .integration import install_integration, uninstall_integration
        function = install_integration if args.install_integration else uninstall_integration
        try:
            output(function(args.workbuddy_home, args.root))
            return 0
        except (OSError, ValueError) as error:
            output({"state": "failed", "code": type(error).__name__})
            return 1
    if args.diagnose:
        output(diagnose(args.root))
        return 0
    if args.import_pet or args.list_pets:
        from .materials import MaterialLibrary
        library=MaterialLibrary(args.root/'characters')
        try:
            if args.import_pet:
                pack=library.import_pack(args.import_pet)
                output({'key':pack.key,'name':pack.name,'quality':pack.quality})
            else:output([{'key':p.key,'name':p.name,'quality':p.quality} for p in library.list_packs()])
            return 0
        except (OSError,ValueError) as error:
            output({'error':str(error)})
            return 1
    from .app import run_app
    return run_app(args.root, args.demo, quit_requested=args.quit, show_settings=args.settings,
                   smoke_seconds=args.smoke_seconds, capture=args.capture,
                   workbuddy_home=args.workbuddy_home,card_only=args.card_only,capture_page=args.capture_page)
