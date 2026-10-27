"""Project untrusted hook input onto a content-free protocol."""
import json
import math
import re
import uuid
from dataclasses import asdict, dataclass
from typing import Mapping

RAW_LIMIT = 64 * 1024
EVENT_LIMIT = 4 * 1024
EVENT_KINDS = (
    "SessionStart", "UserPromptSubmit", "PreToolUse", "PostToolUse",
    "PostToolUseFailure", "Notification", "PermissionRequest", "Stop",
    "SessionEnd", "SubagentStart", "SubagentStop",
)
IDENTIFIER = re.compile(r"[a-zA-Z0-9_.:@-]{1,128}\Z")
NOTIFICATIONS = {"permission_prompt", "idle_prompt", "input_required", "elicitation_dialog"}
CATEGORIES = {"command", "files", "web", "other"}


@dataclass(frozen=True)
class Event:
    id: str
    at: float
    session_id: str
    kind: str
    schema: int = 1
    parent_session_id: str | None = None
    turn_id: str | None = None
    tool_call_id: str | None = None
    tool_category: str | None = None
    notification_kind: str | None = None

    def to_bytes(self) -> bytes:
        return json.dumps({k: v for k, v in asdict(self).items() if v is not None},
                          ensure_ascii=True, separators=(",", ":"), allow_nan=False).encode()


def identifier(value: object) -> str | None:
    return value if isinstance(value, str) and IDENTIFIER.fullmatch(value) else None


def tool_category(value: object) -> str:
    name = value.lower() if isinstance(value, str) else ""
    if any(part in name for part in ("bash", "shell", "terminal", "command")):
        return "command"
    if any(part in name for part in ("read", "write", "edit", "file", "glob", "grep")):
        return "files"
    if any(part in name for part in ("browser", "fetch", "search", "web")):
        return "web"
    return "other"


def project_event(event_name: str, payload: Mapping[str, object], now: float) -> Event | None:
    if event_name not in EVENT_KINDS or not isinstance(payload, Mapping):
        return None
    session = identifier(payload.get("session_id"))
    if not session or isinstance(now, bool) or not isinstance(now, (int, float)) or not math.isfinite(now):
        return None
    if payload.get("hook_event_name", event_name) != event_name:
        return None
    notification = payload.get("notification_type")
    if not isinstance(notification, str) or notification not in NOTIFICATIONS:
        notification = None
    event = Event(
        id=uuid.uuid4().hex, at=float(now), session_id=session, kind=event_name,
        parent_session_id=identifier(payload.get("parent_session_id")),
        turn_id=identifier(payload.get("generation_id")),
        tool_call_id=identifier(payload.get("tool_use_id")),
        tool_category=tool_category(payload.get("tool_name")) if "ToolUse" in event_name else None,
        notification_kind=notification,
    )
    return event if len(event.to_bytes()) <= EVENT_LIMIT else None


def parse_event(raw: bytes) -> Event | None:
    if len(raw) > EVENT_LIMIT:
        return None
    try:
        value = json.loads(raw)
        if not isinstance(value, dict) or set(value) - set(Event.__dataclass_fields__):
            return None
        event = Event(**value)
        if type(event.schema) is not int or event.schema != 1 or not identifier(event.id):
            return None
        if not identifier(event.session_id) or event.kind not in EVENT_KINDS:
            return None
        if type(event.at) not in (int, float) or not math.isfinite(event.at) or event.at < 0:
            return None
        for field in (event.parent_session_id, event.turn_id, event.tool_call_id):
            if field is not None and not identifier(field):
                return None
        if event.tool_category is not None and event.tool_category not in CATEGORIES:
            return None
        if event.notification_kind is not None and event.notification_kind not in NOTIFICATIONS:
            return None
        return event
    except (ValueError, TypeError, UnicodeError, RecursionError):
        return None
