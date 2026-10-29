import json

from workbuddy_pet.event_audit import audit_events
from workbuddy_pet.events import Event
from workbuddy_pet.spool import write_event


def test_report_excludes_identifiers_and_filters_time(tmp_path):
    root=tmp_path/'events'
    write_event(root,Event('old',1,'private-old','PermissionRequest'))
    for i,kind in enumerate(('UserPromptSubmit','PreToolUse','PostToolUseFailure','Notification','Stop'),10):
        write_event(root,Event(str(i),i,'private-session',kind,notification_kind='input_required' if kind=='Notification' else None))
    report=audit_events(tmp_path,10)
    assert report['observed']['tool_failure'] and report['observed']['waiting_input']
    assert not report['observed']['permission'] and not report['observed']['child_start_stop']
    assert report['scan_complete'] and report['newest_event_at']==14
    assert 'private-' not in json.dumps(report) and str(tmp_path) not in json.dumps(report)


def test_child_coverage_requires_paired_child_identity_and_parent(tmp_path):
    root=tmp_path/'events'
    for id,session,kind in [('1','child-a','SubagentStart'),('2','child-b','SubagentStop')]:
        write_event(root,Event(id,10,session,kind,parent_session_id='parent'))
    assert not audit_events(tmp_path)['observed']['child_start_stop']
    write_event(root,Event('3',11,'child-a','SubagentStop',parent_session_id='parent'))
    assert audit_events(tmp_path)['observed']['child_start_stop']


def test_idle_notification_is_not_input_dialog_evidence(tmp_path):
    write_event(tmp_path/'events',Event('1',10,'synthetic','Notification',notification_kind='idle_prompt'))
    report=audit_events(tmp_path)
    assert report['observed']['idle_notification'] and not report['observed']['waiting_input']
