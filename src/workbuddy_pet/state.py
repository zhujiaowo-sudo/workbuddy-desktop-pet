"""Pure, conservative session state. Silence is never a successful completion."""
from dataclasses import dataclass, replace
from typing import Mapping

from .events import Event

PRIORITY = {"idle": 0, "done": 1, "thinking": 2, "working": 3, "failed": 4, "waiting": 5, "review": 6}


@dataclass(frozen=True)
class Reminder:
    id: str
    session_id: str
    kind: str


@dataclass(frozen=True)
class SessionState:
    session_id: str
    state: str = "idle"
    at: float = 0
    phase: int = 0
    started: float = 0
    turn_id: str | None = None
    parent_session_id: str | None = None
    tools: frozenset[str] = frozenset()
    terminal: bool = False
    reminder: Reminder | None = None
    seen: tuple[str, ...] = ()
    completed_tools: tuple[str, ...] = ()


@dataclass(frozen=True)
class DisplayState:
    state: str = "idle"
    connection: str = "disconnected"
    session_id: str | None = None
    reminders: tuple[Reminder, ...] = ()
    session_count: int = 0


def reduce_event(sessions: Mapping[str, SessionState], event: Event) -> dict[str, SessionState]:
    result = dict(sessions)
    old = result.get(event.session_id, SessionState(event.session_id))
    if event.id in old.seen or event.at < old.started:
        return result
    if event.kind != "UserPromptSubmit" and old.turn_id and event.turn_id and old.turn_id != event.turn_id:
        return result
    if event.kind == "UserPromptSubmit" and event.at < old.at:
        return result
    # SubagentStop often carries the parent's session_id. It must never finish it.
    if event.kind in ("SubagentStart", "SubagentStop") and not event.parent_session_id:
        return result
    if old.terminal and event.kind not in ("UserPromptSubmit", "SessionStart", "SessionEnd"):
        return result
    if (event.kind in ('PreToolUse', 'PostToolUse', 'PostToolUseFailure')
            and event.tool_call_id and event.tool_call_id in old.completed_tools):
        return result
    s = replace(old, at=max(old.at, event.at), seen=(*old.seen[-255:], event.id),
                parent_session_id=event.parent_session_id or old.parent_session_id)
    if event.kind == "UserPromptSubmit":
        s = replace(s, phase=s.phase + 1, started=event.at, turn_id=event.turn_id,
                    state="thinking", terminal=False, tools=frozenset(), reminder=None, completed_tools=())
    elif event.kind == "SessionStart":
        # WorkBuddy can emit startup after UserPromptSubmit/tool activity.
        # A new session already defaults to idle; never erase active state.
        pass
    elif event.kind == "SessionEnd":
        s = replace(s, state="idle", terminal=True, tools=frozenset(), reminder=None)
    elif event.kind in ("PreToolUse", "SubagentStart"):
        tool = event.tool_call_id or "anonymous-" + event.id
        s = replace(s, state="working", tools=s.tools | {tool}, reminder=None)
    elif event.kind in ("PostToolUse", "PostToolUseFailure"):
        tools = set(s.tools)
        if event.tool_call_id:
            tools.discard(event.tool_call_id)
            s = replace(s, completed_tools=(*s.completed_tools[-511:], event.tool_call_id))
        elif tools:
            tools.remove(sorted(tools)[0])
        s = replace(s, state="failed" if event.kind == "PostToolUseFailure" else "working" if tools else "thinking",
                    tools=frozenset(tools), reminder=None)
    elif event.kind == "PermissionRequest" or event.kind == "Notification" and event.notification_kind == "permission_prompt":
        s = replace(s, state="review")
    elif event.kind == "Notification" and event.notification_kind in ("idle_prompt", "input_required", "elicitation_dialog"):
        s = replace(s, state="waiting")
    elif event.kind in ("Stop", "SubagentStop"):
        if s.parent_session_id or event.kind == "SubagentStop":
            s = replace(s, state="idle", terminal=True, tools=frozenset(), reminder=None)
        else:
            s = replace(s, state="failed" if old.state == "failed" else "done", terminal=True, tools=frozenset())
    if s.state in ("review", "waiting", "done", "failed") and s.parent_session_id is None:
        kind = s.state
        reminder = Reminder(f"{s.session_id}:{s.turn_id or format(s.started, '.6f')}:{kind}", s.session_id, kind)
        # Preserve acknowledgement while staying in the same state/phase.
        if old.state != s.state or old.phase != s.phase or old.session_id not in result:
            s = replace(s, reminder=reminder)
    result[event.session_id] = s
    if len(result) > 32:
        oldest = min((k for k in result if k != event.session_id), key=lambda k: result[k].at)
        del result[oldest]
    return result


def effective_state(session, now):
    if session.state in ('thinking', 'working') and now-session.at >= 120:
        return 'idle'
    return 'idle' if session.state == 'done' and session.reminder is None else session.state


def derive_display(sessions: Mapping[str, SessionState], now: float) -> DisplayState:
    if not sessions:
        return DisplayState()
    states = list(sessions.values())
    top = max(states, key=lambda s: (PRIORITY[effective_state(s, now)], s.at))
    business = effective_state(top, now)
    stale = top.state in ("working", "thinking") and now - top.at >= 120
    reminders = tuple(s.reminder for s in sorted(states, key=lambda s: (-PRIORITY[s.state], -s.at)) if s.reminder)
    return DisplayState(business, "stale" if stale else "connected", top.session_id, reminders, len(states))


def acknowledge(sessions: Mapping[str, SessionState], reminder_id: str) -> dict[str, SessionState]:
    return {k: replace(s, reminder=None) if s.reminder and s.reminder.id == reminder_id else s for k, s in sessions.items()}
