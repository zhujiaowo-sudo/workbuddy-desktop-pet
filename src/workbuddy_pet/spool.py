"""Bounded local queues; never write the original hook input."""
import hashlib
import re
from collections import deque
from dataclasses import dataclass
from pathlib import Path

from .events import EVENT_LIMIT, Event, parse_event
from .storage import file_lock, plain

MAX_FILE = 2 * 1024 * 1024
MAX_SESSIONS = 32
OWNED_NAME = re.compile(r"[0-9a-f]{24}(?:\.previous)?\.jsonl\Z")


def queue_path(root: Path, session_id: str) -> Path:
    return plain(root / (hashlib.sha256(session_id.encode()).hexdigest()[:24] + ".jsonl"))


def write_event(root: Path, event: Event) -> bool:
    try:
        root = plain(root)
        raw = event.to_bytes()
        if len(raw) > EVENT_LIMIT or parse_event(raw) is None:
            return False
        with file_lock(root / ".writer.lock"):
            path = queue_path(root, event.session_id)
            queues = [p for p in root.glob("*.jsonl") if OWNED_NAME.fullmatch(p.name) and ".previous" not in p.name]
            if not path.exists() and len(queues) >= MAX_SESSIONS:
                oldest = min(queues, key=lambda p: p.stat().st_mtime_ns)
                plain(oldest.with_suffix(".previous.jsonl")).unlink(missing_ok=True)
                plain(oldest).unlink()
            if path.exists() and path.stat().st_size + len(raw) + 1 > MAX_FILE:
                previous = plain(path.with_suffix(".previous.jsonl"))
                previous.unlink(missing_ok=True)
                path.replace(previous)
            with path.open("ab") as stream:
                stream.write(raw + b"\n")
        return True
    except (OSError, ValueError, TimeoutError):
        return False


@dataclass
class Cursor:
    identity: tuple
    offset: int = 0
    carry: bytes = b""
    skipping: bool = False
    prefix: bytes = b""


class SpoolReader:
    def __init__(self, root: Path):
        self.root = plain(root)
        self.cursors: dict[Path, Cursor] = {}
        self.seen: set[str] = set()
        self.order: deque[str] = deque()
        self.invalid_lines = 0

    def poll(self) -> list[Event]:
        if not self.root.exists():
            return []
        result = []
        paths = [p for p in self.root.glob("*.jsonl") if OWNED_NAME.fullmatch(p.name)]
        if len(paths) > MAX_SESSIONS * 2:
            paths = sorted(paths, key=lambda p: p.stat().st_mtime_ns)[-MAX_SESSIONS * 2:]
        for path in sorted(paths, key=lambda p: (p.name[:24], ".previous" not in p.name)):
            try:
                path = plain(path)
                with path.open("rb") as stream:
                    stat = path.stat()
                    identity = (stat.st_dev, stat.st_ino)
                    head = stream.read(128)
                    cursor = self.cursors.get(path)
                    if (cursor is None or cursor.identity != identity or stat.st_size < cursor.offset
                            or not head.startswith(cursor.prefix)):
                        cursor = Cursor(identity)
                    stream.seek(cursor.offset)
                    data = stream.read(128 * 1024)
                    cursor.offset += len(data)
                    cursor.prefix = head
                chunks = (cursor.carry + data).split(b"\n")
                cursor.carry = chunks.pop()
                for raw in chunks:
                    if cursor.skipping:
                        cursor.skipping = False
                        continue
                    event = parse_event(raw)
                    if event is None:
                        self.invalid_lines += 1
                    elif event.id not in self.seen:
                        self.seen.add(event.id)
                        self.order.append(event.id)
                        result.append(event)
                        if len(self.order) > 8192:
                            self.seen.discard(self.order.popleft())
                if len(cursor.carry) > EVENT_LIMIT:
                    cursor.carry = b""
                    cursor.skipping = True
                self.cursors[path] = cursor
            except (OSError, ValueError):
                continue
        self.cursors = {p: c for p, c in self.cursors.items() if p in paths}
        return sorted(result, key=lambda event: (event.at, event.kind != "UserPromptSubmit"))
