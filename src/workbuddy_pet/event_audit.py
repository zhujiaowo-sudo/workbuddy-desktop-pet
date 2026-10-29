"""Content-free hook coverage, for human-observed compatibility verification."""
from collections import Counter

from .spool import SpoolReader


def audit_events(root, since=0):
    reader = SpoolReader(root / 'events')
    counts = Counter()
    notifications = Counter()
    children = {}
    newest = None
    exhausted = False
    for _ in range(64):
        before = {p: (c.identity, c.offset) for p, c in reader.cursors.items()}
        for event in reader.poll():
            if event.at < since:
                continue
            newest = max(newest or event.at, event.at)
            counts[event.kind] += 1
            if event.notification_kind:
                notifications[event.notification_kind] += 1
            if event.parent_session_id and event.kind in ('SubagentStart', 'SubagentStop'):
                children.setdefault((event.session_id, event.parent_session_id), set()).add(event.kind)
        after = {p: (c.identity, c.offset) for p, c in reader.cursors.items()}
        if before == after:
            exhausted = True
            break
    coverage = {
        'task_start': counts['UserPromptSubmit'] > 0,
        'tool_start': counts['PreToolUse'] > 0,
        'tool_end': counts['PostToolUse'] > 0,
        'task_stop': counts['Stop'] > 0,
        'permission': counts['PermissionRequest'] > 0 or notifications['permission_prompt'] > 0,
        'waiting_input': any(notifications[k] for k in ('input_required', 'elicitation_dialog')),
        'idle_notification': notifications['idle_prompt'] > 0,
        'tool_failure': counts['PostToolUseFailure'] > 0,
        'child_start_stop': any({'SubagentStart', 'SubagentStop'} <= kinds for kinds in children.values()),
    }
    return {'schema': 1, 'source': 'local_hook_queue', 'since': since, 'newest_event_at': newest,
            'event_counts': dict(counts), 'notification_counts': dict(notifications),
            'observed': coverage, 'not_observed': [key for key, found in coverage.items() if not found],
            'scan_complete': exhausted, 'invalid_lines': reader.invalid_lines,
            'note': '仅表示队列中观察到事件；是否真实触发及界面响应须人工核对，不等同兼容性验收通过。'}
