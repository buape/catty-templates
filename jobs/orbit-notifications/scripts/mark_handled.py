#!/usr/bin/env python3
from __future__ import annotations

import sys
from orbit_job_lib import STATE_DIR, orbit_dismiss_notification, read_json, release_lock, write_json

HANDLED_PATH = STATE_DIR / "handled.json"


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: mark_handled.py <notification_id> <created_at>", file=sys.stderr)
        return 2
    notification_id, created_at = sys.argv[1], sys.argv[2]
    orbit_dismiss_notification(notification_id)
    handled = read_json(HANDLED_PATH, {})
    handled[notification_id] = created_at
    write_json(HANDLED_PATH, handled)
    release_lock(notification_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
