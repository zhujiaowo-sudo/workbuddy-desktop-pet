import io
import json
import math

import pytest

from workbuddy_pet.events import RAW_LIMIT, Event, parse_event, project_event


def test_projection_excludes_content():
    payload = dict(session_id="safe-session", generation_id="turn-1", tool_use_id="tool-1",
                   tool_name="Bash", prompt="PRIVATE-PROMPT", tool_input={"command": "SECRET"},
                   transcript_path="C:/private/diary", message="PRIVATE-REPLY")
    event = project_event("PreToolUse", payload, 100)
    assert event.tool_category == "command"
    assert event.turn_id == "turn-1"
    assert not any(value in event.to_bytes().decode() for value in ("PRIVATE", "SECRET", "diary"))
    assert parse_event(event.to_bytes()) == event


@pytest.mark.parametrize("payload,now", [({}, 1), ({"session_id": 3}, 1),
    ({"session_id": "../../escape"}, 1), ({"session_id": "s"}, math.nan),
    ({"session_id": "s"}, True)])
def test_bad_projection(payload, now):
    assert project_event("Stop", payload, now) is None


def test_strict_wire_protocol():
    value = json.loads(Event("e", 1, "s", "Stop").to_bytes())
    value["prompt"] = "must-not-pass"
    assert parse_event(json.dumps(value).encode()) is None
    assert parse_event(b"x" * 4097) is None
    assert parse_event(b'{"schema":1}') is None
    assert parse_event(b"[" * 1100 + b"]" * 1100) is None
    assert project_event("Unknown", {"session_id": "s"}, 1) is None


def test_hook_size_limit_and_no_decision(tmp_path, capsys):
    from workbuddy_pet.cli import hook_main
    for raw in (b"x" * (RAW_LIMIT + 1), b"{}", b"{bad-json"):
        assert hook_main("Stop", io.BytesIO(raw), tmp_path) == 0
    valid = json.dumps({"session_id": "s", "prompt": "hidden"}).encode()
    assert hook_main("Stop", io.BytesIO(valid), tmp_path) == 0
    assert capsys.readouterr().out == ""
    assert list((tmp_path / "events").glob("*.jsonl"))
