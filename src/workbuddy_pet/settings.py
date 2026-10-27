import json
from dataclasses import asdict, dataclass
from pathlib import Path
from typing import Sequence

from .storage import atomic_json, plain


@dataclass(frozen=True)
class Rect:
    x: int
    y: int
    width: int
    height: int


@dataclass(frozen=True)
class Settings:
    workbuddy_path: str = ""
    size: int = 160
    notifications: bool = True
    position: tuple[int, int] | None = None
    startup: bool = False


def clamp_position(position: tuple[int, int], size: tuple[int, int], screens: Sequence[Rect]) -> tuple[int, int]:
    if not screens:
        return (0, 0)
    x, y = position
    screen = min(screens, key=lambda r: max(r.x - x, 0, x - (r.x + r.width)) ** 2
                 + max(r.y - y, 0, y - (r.y + r.height)) ** 2)
    return (max(screen.x, min(x, screen.x + screen.width - size[0])),
            max(screen.y, min(y, screen.y + screen.height - size[1])))


def load_settings(root: Path) -> Settings:
    try:
        value = json.loads(plain(root / "settings.json").read_text(encoding="utf-8"))
        if not isinstance(value, dict):
            return Settings()
        size = value.get("size", 160)
        if type(size) is not int or not 100 <= size <= 240:
            size = 160
        position = value.get("position")
        if not (isinstance(position, list) and len(position) == 2 and all(type(n) is int and abs(n) < 100000 for n in position)):
            position = None
        path = value.get("workbuddy_path", "")
        if not isinstance(path, str) or len(path) > 1024 or any(c in path for c in "\r\n\x00"):
            path = ""
        return Settings(path, size, value.get("notifications") if type(value.get("notifications")) is bool else True,
                        tuple(position) if position else None, value.get("startup") is True)
    except (OSError, ValueError, TypeError):
        return Settings()


def save_settings(root: Path, value: Settings) -> None:
    atomic_json(root / "settings.json", asdict(value))
