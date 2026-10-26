#!/usr/bin/env python3
from __future__ import annotations

import sys
from github_job_lib import STATE_DIR, mark_thread_done, read_json, release_lock, write_json

HANDLED_PATH = STATE_DIR / "handled.json"
REPROCESS_PATH = STATE_DIR / "reprocess.json"


def main() -> int:
    if len(sys.argv) != 3:
        print("usage: mark_handled.py <thread_id> <updated_at>", file=sys.stderr)
        return 2
    thread_id, updated_at = sys.argv[1], sys.argv[2]
    if not thread_id.startswith("synthetic:"):
        mark_thread_done(thread_id)
    handled = read_json(HANDLED_PATH, {})
    handled[thread_id] = updated_at
    write_json(HANDLED_PATH, handled)
    reprocess = [item for item in read_json(REPROCESS_PATH, []) if str(item) != thread_id]
    if reprocess:
        write_json(REPROCESS_PATH, reprocess)
    else:
        REPROCESS_PATH.unlink(missing_ok=True)
    release_lock(thread_id)
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
