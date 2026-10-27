import time
from dataclasses import replace

from workbuddy_pet.events import Event
from workbuddy_pet.spool import SpoolReader, queue_path, write_event
from workbuddy_pet.storage import file_lock


def test_reader_keeps_partial_and_skips_bad_line(tmp_path):
    e = Event("e", 1, "s", "Stop")
    p = queue_path(tmp_path, "s")
    reader = SpoolReader(tmp_path)
    p.write_bytes(b"broken\n" + e.to_bytes()[:15])
    assert reader.poll() == []
    with p.open("ab") as f:
        f.write(e.to_bytes()[15:] + b"\n")
    assert reader.poll() == [e]
    assert reader.poll() == []


def test_rotation_truncation_and_duplicate(tmp_path, monkeypatch):
    import workbuddy_pet.spool as spool
    monkeypatch.setattr(spool, "MAX_FILE", 240)
    reader = SpoolReader(tmp_path)
    first = Event("a", 1, "s", "UserPromptSubmit")
    assert write_event(tmp_path, first)
    assert reader.poll() == [first]
    second = replace(first, id="b", at=2)
    assert write_event(tmp_path, second)
    assert reader.poll() == [second]
    path = queue_path(tmp_path, "s")
    third = replace(first, id="c", at=3)
    path.write_bytes(third.to_bytes() + b"\n")
    assert reader.poll() == [third]
    assert write_event(tmp_path, third)
    assert reader.poll() == []


def test_concurrent_writer_lock_timeout(tmp_path):
    with file_lock(tmp_path / ".writer.lock"):
        started = time.monotonic()
        assert not write_event(tmp_path, Event("e", 1, "s", "Stop"))
        assert time.monotonic() - started < .3


def test_session_limit_and_no_external_names(tmp_path, monkeypatch):
    import workbuddy_pet.spool as spool
    monkeypatch.setattr(spool, "MAX_SESSIONS", 2)
    for i in range(5):
        assert write_event(tmp_path, Event(str(i), i, str(i), "Stop"))
    assert len(list(tmp_path.glob("*.jsonl"))) <= 4
    assert all(len(p.name.split(".")[0]) == 24 for p in tmp_path.glob("*.jsonl"))


def test_oversized_partial_is_skipped_until_newline(tmp_path):
    p = queue_path(tmp_path, "s")
    reader = SpoolReader(tmp_path)
    p.write_bytes(b"x" * 5000)
    assert reader.poll() == []
    e = Event("good", 1, "s", "Stop")
    with p.open("ab") as f:
        f.write(b"more\n" + e.to_bytes() + b"\n")
    assert reader.poll() == [e]
