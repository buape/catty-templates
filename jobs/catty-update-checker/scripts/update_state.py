#!/usr/bin/env python3
"""Show pending version data or acknowledge a successfully delivered alert."""
import json
from pathlib import Path
import sys

from check_updates import write_json

STATE = Path(__file__).resolve().parents[1] / ".state"


def main() -> None:
    if len(sys.argv) != 2 or sys.argv[1] not in ("context", "mark-notified"):
        raise SystemExit("usage: update_state.py context|mark-notified")
    pending = json.loads((STATE / "pending.json").read_text())
    if sys.argv[1] == "context":
        print(json.dumps(pending))
    else:
        if not pending.get("available_version"):
            raise SystemExit("No available version to acknowledge")
        write_json(STATE / "notified.json", pending)
        print("Notification recorded")


if __name__ == "__main__":
    main()
