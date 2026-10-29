"""Print only event coverage; never export session IDs, paths, or conversations."""
import argparse
import json
from pathlib import Path
import sys
from datetime import datetime

sys.path.insert(0, str(Path(__file__).resolve().parents[1] / 'src'))
from workbuddy_pet.event_audit import audit_events
from workbuddy_pet.storage import data_root


def main():
    parser = argparse.ArgumentParser(description='输出桌宠事件覆盖汇总，不含会话标识或正文')
    parser.add_argument('--root', type=Path, default=data_root())
    parser.add_argument('--since', type=datetime.fromisoformat, required=True,
                        help='本次验收开始时间，建议包含时区，例如2026-10-29T17:00:00+08:00')
    args = parser.parse_args()
    print(json.dumps(audit_events(args.root, args.since.timestamp()), ensure_ascii=True, indent=2))


if __name__ == '__main__':
    main()
