"""Read-only local usage. Billing credits and context capacity are distinct."""
from dataclasses import dataclass
from contextlib import closing
from datetime import datetime
from decimal import Decimal, InvalidOperation
import json
import math
from pathlib import Path
import sqlite3
import time


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
    message: str = '尚未找到 WorkBuddy 本地数据库，请在同一 Windows 账户启动 WorkBuddy 并完成一次对话'
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
                stat = path.stat()
                signature = (stat.st_size, stat.st_mtime_ns)
                previous = self.cache.get(path)
                if previous and previous[0] == signature:
                    metadata = previous[1]
                else:
                    metadata = {}
                    with path.open('rb') as stream:
                        scanned = 0
                        while scanned < 64 * 1024 * 1024:
                            line = stream.readline(2 * 1024 * 1024 + 1)
                            if not line:
                                break
                            scanned += len(line)
                            if len(line) > 2 * 1024 * 1024:
                                while line and not line.endswith(b'\n'):
                                    line = stream.readline(2 * 1024 * 1024)
                                    scanned += len(line)
                                continue
                            try:
                                item = request_metadata(json.loads(line))
                            except (ValueError, RecursionError):
                                continue
                            if item:
                                request, data = item
                                old = metadata.get(request)
                                times = [v for v in (data[1], old[1] if old else None) if v is not None]
                                winner = data if old is None or data[2] >= old[2] else old
                                metadata[request] = (winner[0], min(times) if times else None, winner[2])
                    self.cache[path] = signature, metadata
                result.update({(path.stem, request): data[:2] for request, data in metadata.items()})
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
                columns = {table: {r[1] for r in db.execute('PRAGMA table_info("'+table+'")')}
                           for table in ('sessions','session_usage')}
                sc, uc = columns['sessions'], columns['session_usage']
                if not sc:
                    return UsageSnapshot(message='本机会话数据库尚未初始化，请在 WorkBuddy 完成一次对话后刷新',days=days)
                if 'id' not in sc:
                    return UsageSnapshot(message='本机会话表结构不兼容，请提供 WorkBuddy 版本以便适配',days=days)
                if not {'session_id','credit_json'} <= uc:
                    return UsageSnapshot(message='当前数据库缺少用量字段，请先在 WorkBuddy 完成一次对话；仍无统计时请提供客户端版本',days=days)
                # Only fixed, known identifiers enter SQL; optional UI columns cannot disable billing.
                def col(alias, name, fields):
                    return alias+'."'+name+'"' if name in fields else 'NULL'
                select = ['s.id']+[col('s',name,sc) for name in ('title','custom_title','model')]
                select += [col('u',name,uc) for name in ('used','size','credit_json')]
                query = 'SELECT '+', '.join(select)+' FROM sessions s LEFT JOIN session_usage u ON u.session_id=s.id'
                if 'deleted_at' in sc:query += ' WHERE s.deleted_at IS NULL'
                query += ' ORDER BY '+('s.updated_at DESC' if 'updated_at' in sc else 's.id')+' LIMIT 5000'
                rows = db.execute(query).fetchall()
        except (sqlite3.Error, OSError) as error:
            code = getattr(error,'sqlite_errorcode',0) & 255
            if code in (sqlite3.SQLITE_BUSY,sqlite3.SQLITE_LOCKED):
                message='WorkBuddy 数据库正被占用，桌宠会自动重试，也可稍后点击刷新'
            elif code in (sqlite3.SQLITE_CORRUPT,sqlite3.SQLITE_NOTADB):
                message='无法识别本机数据库格式，请重启 WorkBuddy；仍失败时请提供客户端版本'
            elif isinstance(error,PermissionError) or code in (sqlite3.SQLITE_PERM,sqlite3.SQLITE_AUTH,sqlite3.SQLITE_CANTOPEN,sqlite3.SQLITE_READONLY):
                message='无法打开本机数据库，请使用运行 WorkBuddy 的同一 Windows 账户，并检查数据目录访问权限'
            else:
                message='读取本机统计失败，请重启 WorkBuddy 后刷新（数据库错误码：'+str(code)+'）'
            return UsageSnapshot(message=message, days=days)
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
