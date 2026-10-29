from dataclasses import replace

import pytest

from workbuddy_pet.events import Event
from workbuddy_pet.state import acknowledge, derive_display, reduce_event


def e(kind, at=100, session="main", **kwargs):
    return Event(f"{session}-{kind}-{at}", at, session, kind, **kwargs)


@pytest.mark.parametrize("kind,wanted", [("UserPromptSubmit", "thinking"), ("PreToolUse", "working"),
    ("PermissionRequest", "review"), ("PostToolUseFailure", "failed"), ("Stop", "done")])
def test_event_mapping(kind, wanted):
    assert derive_display(reduce_event({}, e(kind)), 100).state == wanted


def test_duplicate_stop_notifies_once_and_acknowledges():
    s = reduce_event({}, e("UserPromptSubmit"))
    stop = e("Stop", 101)
    s = reduce_event(s, stop)
    s = reduce_event(s, replace(stop, id="second-stop", at=102))
    display = derive_display(s, 102)
    assert len(display.reminders) == 1
    s = acknowledge(s, display.reminders[0].id)
    assert derive_display(s, 103).state == "idle"
    assert not derive_display(s, 103).reminders


def test_subagent_stop_does_not_complete_parent():
    s = reduce_event({}, e("PreToolUse"))
    s = reduce_event(s, e("SubagentStart", 101, session="child", parent_session_id="main"))
    s = reduce_event(s, e("SubagentStop", 102, session="child", parent_session_id="main"))
    assert derive_display(s, 103).state == "working"
    assert not derive_display(s, 103).reminders


def test_late_events_and_old_turns():
    s = reduce_event({}, e("UserPromptSubmit", turn_id="a"))
    s = reduce_event(s, e("Stop", 101, turn_id="a"))
    s = reduce_event(s, e("PostToolUse", 102, turn_id="a"))
    assert derive_display(s, 102).state == "done"
    s = reduce_event(s, e("UserPromptSubmit", 103, turn_id="b"))
    s = reduce_event(s, e("Stop", 104, turn_id="a"))
    assert derive_display(s, 104).state == "thinking"


def test_priority_and_staleness():
    s = reduce_event({}, e("PreToolUse"))
    assert derive_display(s, 219.999).connection == "connected"
    assert derive_display(s, 220).connection == "stale"
    s = reduce_event(s, e("PermissionRequest", 101, session="other"))
    assert derive_display(s, 1000).state == "review"
    assert derive_display(s, 1000).connection == "connected"
    assert derive_display({}, 1).connection == "disconnected"


def test_tools_parallel_and_session_end_is_not_success():
    s = reduce_event({}, e("PreToolUse", tool_call_id="one"))
    s = reduce_event(s, e("PreToolUse", 101, tool_call_id="two"))
    s = reduce_event(s, e("PostToolUse", 102, tool_call_id="one"))
    assert derive_display(s, 102).state == "working"
    s = reduce_event(s, e("SessionEnd", 103))
    assert not derive_display(s, 103).reminders
    assert derive_display(s, 103).state == "idle"


def test_late_tool_start_and_duplicate_end_do_not_reopen_completed_tool():
    s = reduce_event({}, e('UserPromptSubmit', turn_id='a'))
    s = reduce_event(s, e('PostToolUse', 102, tool_call_id='one', turn_id='a'))
    s = reduce_event(s, e('PreToolUse', 101, tool_call_id='one', turn_id='a'))
    assert not s['main'].tools and s['main'].state == 'thinking'
    s = reduce_event(s, e('PermissionRequest', 103))
    s = reduce_event(s, e('PostToolUse', 102.5, tool_call_id='one'))
    assert s['main'].state == 'review'
    s = reduce_event(s, e('UserPromptSubmit', 104, turn_id='b'))
    s = reduce_event(s, e('PreToolUse', 105, tool_call_id='one', turn_id='b'))
    assert s['main'].tools == frozenset({'one'})


def test_late_distinct_parallel_tool_is_not_discarded():
    s = reduce_event({}, e('PreToolUse', 102, tool_call_id='new'))
    s = reduce_event(s, e('PreToolUse', 101, tool_call_id='old'))
    s = reduce_event(s, e('PostToolUse', 103, tool_call_id='new'))
    assert s['main'].tools == frozenset({'old'})
    assert s['main'].state == 'working'


@pytest.mark.parametrize('kind,state',[('UserPromptSubmit','thinking'),('PreToolUse','working'),('PermissionRequest','review')])
def test_late_session_start_keeps_active_business_state(kind,state):
    s=reduce_event({},e(kind,100))
    s=reduce_event(s,e('SessionStart',101))
    assert s['main'].state==state
