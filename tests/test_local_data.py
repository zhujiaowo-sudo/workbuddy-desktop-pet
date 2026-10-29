import json
import sqlite3
from datetime import datetime, timezone

from workbuddy_pet.local_data import LocalDataReader
from workbuddy_pet.windows import conversation_url


def fixture_home(root):
    db = sqlite3.connect(root / 'workbuddy.db')
    db.executescript('CREATE TABLE sessions(id TEXT, title TEXT, custom_title TEXT, model TEXT, updated_at INTEGER, deleted_at INTEGER);'
                     'CREATE TABLE session_usage(session_id TEXT, used INTEGER, size INTEGER, updated_at INTEGER, credit_json TEXT);')
    db.execute('INSERT INTO sessions VALUES(?,?,?,?,?,?)', ('s', '测试会话', '自定义名称', 'auto', 1, None))
    db.execute('INSERT INTO sessions VALUES(?,?,?,?,?,?)', ('deleted', '已删除', '', 'x', 1, 2))
    db.execute('INSERT INTO session_usage VALUES(?,?,?,?,?)', ('s', 50000, 200000, 1, json.dumps({'r1':1.2,'r2':2,'r3':0.3})))
    db.commit()
    db.close()
    project = root / 'projects' / 'synthetic'
    project.mkdir(parents=True)
    return project / 's.jsonl'


def test_credit_request_join_dedup_dates_unknown_and_readonly(tmp_path):
    path = fixture_home(tmp_path)
    event = {'timestamp':'2026-10-27T01:00:00Z','providerData':{'conversationRequestId':'r1','requestModelId':'model-a'},'content':'不保存正文'}
    path.write_text('\n'.join(map(json.dumps,[event,event,{'timestamp':'2020-01-01T00:00:00Z', 'providerData':{'conversationRequestId':'r2','requestModelId':'auto'}}])), encoding='utf-8')
    reader = LocalDataReader(tmp_path)
    snap = reader.snapshot(now=datetime(2026,10,27,tzinfo=timezone.utc).timestamp())
    assert snap.total_credit == 3.5 and snap.request_count == 3
    assert snap.sessions[0].title == '自定义名称' and len(snap.sessions) == 1
    assert snap.unknown_model == 1 and snap.unknown_time == 1
    assert snap.sessions[0].context_used == 50000
    recent = reader.snapshot(days=7, now=datetime(2026,10,27,23,tzinfo=timezone.utc).timestamp())
    assert recent.total_credit == 1.2 and recent.request_count == 1
    assert recent.models[0].model == 'model-a'
    assert not list(tmp_path.glob('*.db-journal'))
    assert '不保存正文' not in repr(reader.__dict__)


def test_incremental_history_missing_database_and_actual_model(tmp_path):
    reader = LocalDataReader(tmp_path)
    assert reader.snapshot().available is False
    path = fixture_home(tmp_path)
    path.write_text(json.dumps({'timestamp':1,'providerData':{'conversationRequestId':'r1','requestModelId':'auto','responseModelId':'actual'}}), encoding='utf-8')
    snap = reader.snapshot()
    assert any(m.model == 'actual' for m in snap.models)
    with path.open('a',encoding='utf-8') as out:
        out.write('\n'+json.dumps({'timestamp':2,'providerData':{'conversationRequestId':'r3','requestModelId':'new'}}))
    assert any(m.model == 'new' for m in reader.snapshot().models)


def test_deep_link_escapes_and_rejects_control():
    import pytest
    assert conversation_url('session:one') == 'workbuddy://chat/session%3Aone'
    for bad in ('', '../evil', 's\n', 'x?y', 'x\\y'):
        with pytest.raises(ValueError):
            conversation_url(bad)


def test_today_uses_local_midnight_and_is_independent_of_report_range(tmp_path):
    path=fixture_home(tmp_path)
    # Naive datetime uses the machine's local calendar, including its DST rules.
    midnight=datetime(2026,10,27).timestamp()
    now=datetime(2026,10,27,12).timestamp()
    credits={'yesterday':5,'midnight':1.2,'now':2.3,'future':7,'unknown':11}
    with sqlite3.connect(tmp_path/'workbuddy.db') as db:
        db.execute('UPDATE session_usage SET credit_json=? WHERE session_id=?',(json.dumps(credits),'s'))
    events=[{'timestamp':at,'providerData':{'conversationRequestId':rid,'requestModelId':'test'}}
            for rid,at in [('yesterday',midnight-1),('midnight',midnight),('now',now),('future',now+1)]]
    path.write_text('\n'.join(json.dumps(e) for e in [*events,events[1]]),encoding='utf-8')
    reader=LocalDataReader(tmp_path)
    for days in (None,7,30):
        snap=reader.snapshot(days,now)
        assert snap.today_credit==3.5 and snap.today_requests==2
        assert snap.today_date=='2026-10-27' and snap.unknown_time==1
    tomorrow=reader.snapshot(now=datetime(2026,10,28).timestamp())
    assert tomorrow.today_credit==0 and tomorrow.today_requests==0


def history_line(request, model='test', content=''):
    return json.dumps({'timestamp':1,'providerData':{'requestId':request,'model':model},'content':content}).encode()+b'\n'


def test_append_only_parses_new_records_and_partial_line_keeps_no_content(tmp_path,monkeypatch):
    import workbuddy_pet.local_data as module
    path=fixture_home(tmp_path)
    path.write_bytes(b''.join(history_line(str(i)) for i in range(100)))
    reader=LocalDataReader(tmp_path);reader._history({'s'})
    parsed=[];original=module.request_metadata
    monkeypatch.setattr(module,'request_metadata',lambda value:parsed.append(1) or original(value))
    extra=history_line('next',content='PRIVATE-SENTINEL')
    with path.open('ab') as stream:stream.write(extra[:45])
    reader._history({'s'})
    assert 'PRIVATE-SENTINEL' not in repr(reader.__dict__)
    with path.open('ab') as stream:stream.write(extra[45:])
    data=reader._history({'s'})
    assert ('s','next') in data and len(parsed)==1
    reader._history({'s'});assert len(parsed)==1
    assert 'PRIVATE-SENTINEL' not in repr(reader.__dict__)


def test_history_reset_on_truncation_replacement_and_same_size_edit(tmp_path):
    path=fixture_home(tmp_path);reader=LocalDataReader(tmp_path)
    path.write_bytes(history_line('old')+history_line('old2'))
    assert ('s','old') in reader._history({'s'})
    path.write_bytes(history_line('new'))
    assert set(reader._history({'s'}))=={('s','new')}
    before=path.stat().st_mtime_ns
    path.write_bytes(history_line('now'))
    import os
    os.utime(path,ns=(before+10000000,before+10000000))
    assert set(reader._history({'s'}))=={('s','now')}
    replacement=path.with_suffix('.replacement');replacement.write_bytes(history_line('other'))
    replacement.replace(path)
    assert set(reader._history({'s'}))=={('s','other')}
    path.unlink();assert not reader._history({'s'}) and not reader.cache


def test_history_scan_budget_continues_next_poll_and_skips_oversized_lines(tmp_path,monkeypatch):
    import workbuddy_pet.local_data as module
    monkeypatch.setattr(module,'HISTORY_READ_LIMIT',512,raising=False)
    monkeypatch.setattr(module,'HISTORY_LINE_LIMIT',200,raising=False)
    path=fixture_home(tmp_path)
    path.write_bytes(history_line('too-large',content='x'*900)+b''.join(history_line(str(i)) for i in range(20)))
    reader=LocalDataReader(tmp_path)
    first=reader._history({'s'})
    assert not first
    for _ in range(20):data=reader._history({'s'})
    assert len(data)==20 and ('s','19') in data and ('s','too-large') not in data
