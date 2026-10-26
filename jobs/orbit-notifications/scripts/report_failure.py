#!/usr/bin/env python3
from __future__ import annotations

import json
import sys
from orbit_job_lib import report_failure


def main() -> int:
    try:
        payload = json.load(sys.stdin)
        key = str(payload.get("key") or "orbit-notifications:unknown")
        message = str(payload.get("message") or "unknown failure")
    except Exception as exc:
        key = "orbit-notifications:reporter"
        message = f"failure reporter received invalid payload: {exc}"
    reported = report_failure(key, message)
    print("reported" if reported else "suppressed")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
