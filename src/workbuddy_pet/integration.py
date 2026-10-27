"""Create an owned formal marketplace plugin; preserve unrelated settings."""
import base64
import copy
import json
import sys
import uuid
from pathlib import Path

from . import __version__
from .events import EVENT_KINDS
from .storage import atomic_json, file_lock, plain

MARKETPLACE = "workbuddy-desktop-pet-local"
PLUGIN_NAME = "workbuddy-desktop-pet"
PLUGIN_ID = PLUGIN_NAME + "@" + MARKETPLACE


def config_object(value: object) -> dict:
    if not isinstance(value, dict):
        raise ValueError("WorkBuddy 配置格式不是对象，未作修改")
    for field in ("enabledPlugins", "extraKnownMarketplaces"):
        if field in value and not isinstance(value[field], dict):
            raise ValueError("WorkBuddy 插件配置格式异常，未作修改")
    return copy.deepcopy(value)


def merge_plugin_config(existing: dict, plugin_id: str, entry: dict) -> dict:
    value = config_object(existing)
    marketplaces = value.setdefault("extraKnownMarketplaces", {})
    if MARKETPLACE in marketplaces and marketplaces[MARKETPLACE] != entry:
        raise ValueError("同名插件市场已存在且位置不同，请先检查原配置")
    marketplaces[MARKETPLACE] = copy.deepcopy(entry)
    value.setdefault("enabledPlugins", {})[plugin_id] = True
    return value


def remove_plugin_config(existing: dict, plugin_id: str, installed_entry: dict) -> dict:
    value = config_object(existing)
    if value.get("extraKnownMarketplaces", {}).get(MARKETPLACE) == installed_entry:
        del value["extraKnownMarketplaces"][MARKETPLACE]
    if value.get("enabledPlugins", {}).get(plugin_id) is True:
        del value["enabledPlugins"][plugin_id]
    return value


def powershell_command(arguments: list[str]) -> str:
    # Base64 transports literal arguments across both Git Bash and PowerShell.
    # No input from a hook payload is ever placed in this command.
    script = "& " + " ".join("'" + str(arg).replace("\\", "/").replace("'", "''") + "'" for arg in arguments)
    encoded = base64.b64encode(script.encode("utf-16le")).decode("ascii")
    return "powershell.exe -NoProfile -NonInteractive -WindowStyle Hidden -EncodedCommand " + encoded


def build_plugin(root: Path, command: list[str]) -> None:
    root = plain(root)
    atomic_json(root / ".codebuddy-plugin/marketplace.json", {
        "name": MARKETPLACE, "owner": {"name": "WorkBuddy Desktop Pet"},
        "plugins": [{"name": PLUGIN_NAME, "source": "./plugin", "version": __version__,
                     "description": "本地桌宠工作状态与完成提醒"}],
    })
    atomic_json(root / "plugin/.codebuddy-plugin/plugin.json", {
        "name": PLUGIN_NAME, "version": __version__, "description": "本地桌宠状态事件采集器",
        "author": {"name": "WorkBuddy Desktop Pet"},
    })
    hooks = {kind: [{"hooks": [{"type": "command", "timeout": 5,
                               "command": powershell_command([*command, "--hook", kind])}]}]
             for kind in EVENT_KINDS}
    # The standard hooks/hooks.json location is discovered automatically.
    atomic_json(root / "plugin/hooks/hooks.json", {"hooks": hooks})


def runtime_command(root: Path) -> list[str]:
    if getattr(sys, "frozen", False):
        return [sys.executable, "--root", str(root)]
    launcher = Path(__file__).resolve().parents[2] / "launch.py"
    return [sys.executable, str(launcher), "--root", str(root)]


def install_integration(workbuddy_home: Path, root: Path, command: list[str] | None = None) -> dict:
    root, workbuddy_home = plain(root), plain(workbuddy_home)
    settings_path = plain(workbuddy_home / "settings.json")
    plugin_root = root / "integration"
    entry = {"source": {"source": "directory", "path": str(plugin_root)}}
    build_plugin(plugin_root, command or runtime_command(root))
    with file_lock(workbuddy_home / ".desktop-pet-config.lock", timeout=1):
        existing = json.loads(settings_path.read_text(encoding="utf-8")) if settings_path.exists() else {}
        updated = merge_plugin_config(existing, PLUGIN_ID, entry)
        receipt_path = root / "integration-receipt.json"
        if receipt_path.exists():
            receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
            if receipt.get("home") != str(workbuddy_home) or receipt.get("entry") != entry:
                raise ValueError("已有不同的接入记录，未修改配置")
        else:
            backup = root / "backups" / (uuid.uuid4().hex + ".json")
            atomic_json(backup, existing)
            receipt = {"schema": 1, "home": str(workbuddy_home), "entry": entry,
                       "backup": str(backup), "plugin_id": PLUGIN_ID}
            atomic_json(receipt_path, receipt)
        atomic_json(settings_path, updated)
    return {"state": "configured", "reload_required": True, "plugin_id": PLUGIN_ID}


def uninstall_integration(workbuddy_home: Path, root: Path) -> dict:
    root, workbuddy_home = plain(root), plain(workbuddy_home)
    receipt_path = root / "integration-receipt.json"
    receipt = json.loads(receipt_path.read_text(encoding="utf-8"))
    if receipt.get("home") != str(workbuddy_home):
        raise ValueError("接入记录与当前 WorkBuddy 目录不符")
    backup_path = plain(Path(receipt["backup"]))
    if not backup_path.is_relative_to(root / "backups"):
        raise ValueError("备份记录位置无效")
    original = config_object(json.loads(backup_path.read_text(encoding="utf-8")))
    with file_lock(workbuddy_home / ".desktop-pet-config.lock", timeout=1):
        settings = workbuddy_home / "settings.json"
        current = json.loads(settings.read_text(encoding="utf-8"))
        updated = remove_plugin_config(current, PLUGIN_ID, receipt["entry"])
        for field, key in (("enabledPlugins", PLUGIN_ID), ("extraKnownMarketplaces", MARKETPLACE)):
            if key not in updated.get(field, {}) and key in original.get(field, {}):
                updated.setdefault(field, {})[key] = original[field][key]
        atomic_json(settings, updated)
        receipt_path.unlink()
    return {"state": "removed", "reload_required": True}


def probe_compatibility(workbuddy_exe: Path) -> dict:
    from .windows import validate_workbuddy_path
    try:
        validate_workbuddy_path(workbuddy_exe)
    except (ValueError, OSError):
        return {"state": "missing_application", "verified_events": [], "unverified_events": list(EVENT_KINDS)}
    return {"state": "requires_live_probe", "verified_events": [], "unverified_events": list(EVENT_KINDS)}
