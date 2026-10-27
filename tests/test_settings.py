from pathlib import Path

from workbuddy_pet.settings import Rect, Settings, clamp_position, load_settings, save_settings
from workbuddy_pet.windows import validate_workbuddy_path

import pytest


def test_restore_removed_monitor_and_negative_coordinates():
    assert clamp_position((6000, 20), (160, 190), [Rect(0, 0, 1920, 1040)]) == (1760, 20)
    assert clamp_position((-1800, 20), (160, 190), [Rect(-1920, 0, 1920, 1040)]) == (-1800, 20)
    assert clamp_position((10, 10), (500, 400), [Rect(0, 0, 200, 100)]) == (0, 0)


def test_malformed_settings_and_atomic_save(tmp_path):
    (tmp_path / "settings.json").write_text('{"size":true,"notifications":"no","position":[null]}')
    settings = load_settings(tmp_path)
    assert settings.size == 160 and settings.notifications is True
    save_settings(tmp_path, Settings(size=200, notifications=False, position=(-100, 20)))
    loaded = load_settings(tmp_path)
    assert loaded.size == 200 and loaded.position == (-100, 20) and not loaded.notifications
    assert not list(tmp_path.glob("*.tmp"))


def test_path_validation(tmp_path):
    with pytest.raises(ValueError):
        validate_workbuddy_path(tmp_path / "missing.exe")
    bad = tmp_path / "other.exe"
    bad.write_bytes(b"MZbinary")
    with pytest.raises(ValueError):
        validate_workbuddy_path(bad)
    good = tmp_path / "WorkBuddy.exe"
    good.write_bytes(b"wrong")
    with pytest.raises(ValueError):
        validate_workbuddy_path(good)
    good.write_bytes(b"MZbinary")
    assert validate_workbuddy_path(good) == good.absolute()
