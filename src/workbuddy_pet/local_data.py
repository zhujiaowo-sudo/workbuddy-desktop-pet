"""Read-only local usage. Billing credits and context capacity are distinct."""
from dataclasses import dataclass, field
from contextlib import closing
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
import hashlib
import math
import os
from pathlib import Path
import sqlite3
import time

HISTORY_READ_LIMIT = 64 * 1024 * 1024
HISTORY_LINE_LIMIT = 2 * 1024 * 1024


@dataclass
class HistoryCursor:
    identity: tuple
    signature: tuple = ()
    offset: int = 0
    eof: bool = False
    skipping: bool = False
    fingerprints: tuple = ()
    metadata: dict = field(default_factory=dict)


def _fingerprint(stream, start, size):
    stream.seek(start)
    return hashlib.sha256(stream.read(size)).digest()


def _merge_metadata(metadata, line):
    try:
        item = request_metadata(json.loads(line))
    except (ValueError, RecursionError):
        return
    if item:
        request, data = item
        old = metadata.get(request)
        times = [v for v in (data[1], old[1] if old else None) if v is not None]
        winner = data if old is None or data[2] >= old[2] else old
        metadata[request] = (winner[0], min(times) if times else None, winner[2])


def _read_history(path, previous):
    with path.open('rb') as stream:
        stat = os.fstat(stream.fileno())
        identity = (stat.st_dev, stat.st_ino)
        signature = (stat.st_size, stat.st_mtime_ns, stat.st_ctime_ns)
        cursor = previous
        if cursor:
            rewritten = (cursor.identity != identity or stat.st_size < cursor.signature[0]
                         or stat.st_size == cursor.signature[0] and signature != cursor.signature)
            if not rewritten:
                rewritten = any(_fingerprint(stream, start, length) != digest
                                for start, length, digest in cursor.fingerprints)
            if rewritten:
                cursor = None
            elif signature == cursor.signature and cursor.eof:
                return cursor
        if cursor is None:
            cursor = HistoryCursor(identity)
        stream.seek(cursor.offset)
        budget = HISTORY_READ_LIMIT
        cursor.eof = False
        while budget > 0 and stream.tell() < stat.st_size:
            line = stream.readline(min(HISTORY_LINE_LIMIT + 1, budget, stat.st_size - stream.tell()))
            if not line:
                break
            budget -= len(line)
            ended = line.endswith(b'\n')
            if cursor.skipping or len(line) > HISTORY_LINE_LIMIT:
                cursor.skipping = not ended
                cursor.offset = stream.tell()
                continue
            if ended:
                _merge_metadata(cursor.metadata, line)
                cursor.offset = stream.tell()
            elif stream.tell() >= stat.st_size:
                # Compatible with complete final JSON without a newline. Re-read this
                # tail after append; retain only metadata, never the partial body.
                _merge_metadata(cursor.metadata, line)
                break
            else:
                # Budget cut through a line. Start at its boundary next poll.
                break
        cursor.eof = stream.tell() >= stat.st_size
        cursor.signature = signature
        length = min(128, stat.st_size)
        boundary_length = min(128, cursor.offset)
        spans = {(0, length), (stat.st_size - length, length),
                 (cursor.offset - boundary_length, boundary_length)}
        cursor.fingerprints = tuple((start, size, _fingerprint(stream, start, size)) for start, size in spans)
        return cursor


@dataclass(frozen=True)
class SessionInfo:
    id: str
    title: str
    model: str
    credit: float = 0
    context_used: int = 0
    context_size: int = 0


@dataclass(frozen=True)
class ModelUsage:
    model: str
    requests: int
    credit: float


@dataclass(frozen=True)
class UsageSnapshot:
    available: bool = False
    message: str = '尚未找到 WorkBuddy 本地数据库'
    sessions: tuple[SessionInfo, ...] = ()
    models: tuple[ModelUsage, ...] = ()
    total_credit: float = 0
    request_count: int = 0
    unknown_model: int = 0
    unknown_time: int = 0
    days: int | None = None
    today_credit: float = 0
    today_requests: int = 0
    today_date: str = ''


def timestamp(value):
    if type(value) in (int, float) and math.isfinite(value):
        return value / 1000 if value > 1e11 else value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value.replace('Z', '+00:00')).timestamp()
        except ValueError:
            pass
    return None


def request_metadata(record):
    """Select structural metadata only; never retain prompt or tool contents."""
    found = {}
    pending = [(record, 0)]
    keys = {'conversationRequestId', 'requestId', 'requestModelId', 'requestModelName',
            'responseModelId', 'responseModelName', 'model', 'timestamp', 'createdAt'}
    while pending:
        item, depth = pending.pop()
        if not isinstance(item, dict) or depth > 6:
            continue
        for key, value in item.items():
            short = key.removeprefix('codebuddy.ai/')
            if short in keys and type(value) in (str, int, float):
                found[short] = value
            elif key in ('providerData', '_meta', 'message', 'usage', 'metadata'):
                pending.append((value, depth + 1))
    request = found.get('conversationRequestId') or found.get('requestId')
    if not isinstance(request, str) or len(request) > 512:
        return None
    actual = found.get('responseModelName') or found.get('responseModelId')
    model = actual or found.get('requestModelName') or found.get('requestModelId') or found.get('model')
    model = model[:200] if isinstance(model, str) else '未知模型'
    if model.lower() == 'auto':
        model = 'Auto（实际模型未知）'
    return request, (model, timestamp(found.get('timestamp', found.get('createdAt'))), 2 if actual else 1 if model != '未知模型' else 0)


class LocalDataReader:
    def __init__(self, home: Path):
        self.home = Path(home)
        self.cache = {}

    def _history(self, session_ids):
        result = {}
        present = set()
        # Files are selected by session id; no broad recursive text search.
        for path in (self.home / 'projects').glob('*/*.jsonl'):
            if path.stem not in session_ids or path.is_symlink():
                continue
            present.add(path)
            try:
                cursor = _read_history(path, self.cache.get(path))
                self.cache[path] = cursor
                result.update({(path.stem, request): data[:2] for request, data in cursor.metadata.items()})
            except OSError:
                continue
        self.cache = {p: v for p, v in self.cache.items() if p in present}
        return result

    def snapshot(self, days: int | None = None, now: float | None = None) -> UsageSnapshot:
        path = self.home / 'workbuddy.db'
        if not path.is_file():
            return UsageSnapshot(days=days)
        try:
            with closing(sqlite3.connect(path.resolve().as_uri() + '?mode=ro', uri=True, timeout=.3)) as db:
                db.execute('PRAGMA query_only=ON')
                rows = db.execute('SELECT s.id, s.title, s.custom_title, s.model, u.used, u.size, u.credit_json '
                                  'FROM sessions s LEFT JOIN session_usage u ON u.session_id=s.id '
                                  'WHERE s.deleted_at IS NULL ORDER BY s.updated_at DESC LIMIT 5000').fetchall()
        except (sqlite3.Error, OSError):
            return UsageSnapshot(message='本地数据库暂不可读或版本不兼容，稍后重试', days=days)
        metadata = self._history({r[0] for r in rows})
        sessions, totals = [], {}
        total = Decimal(0)
        count = unknown_model = unknown_time = 0
        current = time.time() if now is None else now
        local_day = datetime.fromtimestamp(current).replace(hour=0,minute=0,second=0,microsecond=0)
        midnight = local_day.timestamp()
        today_total = Decimal(0)
        today_count = 0
        cutoff = current - days * 86400 if days else None
        for sid, title, custom, selected, used, size, credit_raw in rows:
            session_total = Decimal(0)
            try:
                credits = json.loads(credit_raw or '{}')
            except (ValueError, TypeError):
                credits = {}
            if not isinstance(credits, dict):
                credits = {}
            for request, amount in credits.items():
                if type(amount) not in (int, float) or not math.isfinite(amount) or amount < 0:
                    continue
                model, at = metadata.get((sid, request), ('未知模型', None))
                unknown_model += model == '未知模型'
                unknown_time += at is None
                cost = Decimal(str(amount))
                session_total += cost
                if at is not None and midnight <= at <= current:
                    today_total += cost
                    today_count += 1
                if cutoff is not None and (at is None or at < cutoff):
                    continue
                entry = totals.setdefault(model, [0, Decimal(0)])
                entry[0] += 1
                entry[1] += cost
                count += 1
                total += cost
            sessions.append(SessionInfo(sid, str(custom or title or '未命名会话')[:200], str(selected or ''),
                                        float(session_total), used or 0, size or 0))
        models = tuple(ModelUsage(model, n, float(cost)) for model, (n, cost) in sorted(totals.items(), key=lambda p: -p[1][1]))
        return UsageSnapshot(True, '本机记录 · 含本机账户；不代表完整账单', tuple(sessions), models,
                             float(total), count, unknown_model, unknown_time, days,
                             float(today_total),today_count,local_day.date().isoformat())
