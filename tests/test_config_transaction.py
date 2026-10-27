import json

from workbuddy_pet.integration import PLUGIN_ID, install_integration, uninstall_integration


def test_repeated_install_and_uninstall_restore_original_disabled_flag(tmp_path):
    home, state = tmp_path / "home", tmp_path / "state"
    home.mkdir()
    original = {"enabledPlugins": {PLUGIN_ID: False, "other@team": True}, "userPreference": 17}
    (home / "settings.json").write_text(json.dumps(original), encoding="utf-8")
    install_integration(home, state, ["C:/test/python.exe", "C:/test/launch.py"])
    install_integration(home, state, ["C:/test/python.exe", "C:/test/launch.py"])
    assert len(list((state / "backups").glob("*.json"))) == 1
    current = json.loads((home / "settings.json").read_text(encoding="utf-8"))
    current["userPreference"] = 18
    current["enabledPlugins"]["added@team"] = True
    (home / "settings.json").write_text(json.dumps(current), encoding="utf-8")
    uninstall_integration(home, state)
    cleaned = json.loads((home / "settings.json").read_text(encoding="utf-8"))
    assert cleaned["userPreference"] == 18
    assert cleaned["enabledPlugins"][PLUGIN_ID] is False
    assert cleaned["enabledPlugins"]["added@team"] is True


def test_malformed_settings_are_not_replaced(tmp_path):
    import pytest
    home = tmp_path / "home"
    home.mkdir()
    path = home / "settings.json"
    path.write_bytes(b"not-json")
    with pytest.raises(ValueError):
        install_integration(home, tmp_path / "state", ["test.exe"])
    assert path.read_bytes() == b"not-json"
