import copy

import pytest

from workbuddy_pet.integration import (PLUGIN_ID, MARKETPLACE, merge_plugin_config,
    remove_plugin_config, build_plugin)


def test_merge_and_remove_preserve_unrelated_hooks(tmp_path):
    original = {"hooks": {"Stop": [{"hooks": [{"type": "command", "command": "existing"}]}]},
                "enabledPlugins": {"unrelated@team": True}}
    before = copy.deepcopy(original)
    entry = {"source": {"source": "directory", "path": str(tmp_path)}}
    merged = merge_plugin_config(original, PLUGIN_ID, entry)
    assert original == before
    assert merged["hooks"] == original["hooks"]
    assert merged["enabledPlugins"]["unrelated@team"] is True
    merged["enabledPlugins"]["new@team"] = True
    cleaned = remove_plugin_config(merged, PLUGIN_ID, entry)
    assert cleaned["enabledPlugins"] == {"unrelated@team": True, "new@team": True}
    assert MARKETPLACE not in cleaned.get("extraKnownMarketplaces", {})


def test_preserves_conflicting_user_changes(tmp_path):
    entry = {"source": {"source": "directory", "path": str(tmp_path)}}
    merged = merge_plugin_config({}, PLUGIN_ID, entry)
    merged["extraKnownMarketplaces"][MARKETPLACE] = {"user": "changed"}
    merged["enabledPlugins"][PLUGIN_ID] = False
    cleaned = remove_plugin_config(merged, PLUGIN_ID, entry)
    assert cleaned["extraKnownMarketplaces"][MARKETPLACE] == {"user": "changed"}
    assert cleaned["enabledPlugins"][PLUGIN_ID] is False
    with pytest.raises(ValueError):
        merge_plugin_config({"enabledPlugins": []}, PLUGIN_ID, entry)


def test_plugin_manifest_commands_quote_paths(tmp_path):
    import json
    build_plugin(tmp_path, ["C:/My App/python.exe", "C:/My App/launch.py"])
    manifest = json.loads((tmp_path / "plugin/.codebuddy-plugin/plugin.json").read_text(encoding="utf-8"))
    assert manifest["name"] == "workbuddy-desktop-pet"
    hooks = json.loads((tmp_path / "plugin/hooks/hooks.json").read_text(encoding="utf-8"))["hooks"]
    assert "Stop" in hooks and "UserPromptSubmit" in hooks
    import base64
    command = hooks["Stop"][0]["hooks"][0]["command"]
    script = base64.b64decode(command.split()[-1]).decode("utf-16le")
    assert "'C:/My App/python.exe'" in script
    assert "permissionDecision" not in json.dumps(hooks)
