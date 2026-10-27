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
