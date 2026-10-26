#!/usr/bin/env python3
from __future__ import annotations

import json
from orbit_job_lib import (
    ACTIONABLE_KINDS,
    NOISE_KINDS,
    STATE_DIR,
    acquire_lock,
    fetch_issue,
    is_self_authored_notification,
    issue_key_from_notification,
    orbit_dismiss_notification,
    orbit_list_notifications,
    read_json,
    release_lock,
    report_failure,
    write_json,
)

HANDLED_PATH = STATE_DIR / "handled.json"
ACTIONABLE_PATH = STATE_DIR / "actionable.json"
RAW_PATH = STATE_DIR / "notifications.json"


def main() -> int:
    try:
        notifications = orbit_list_notifications()
        write_json(RAW_PATH, notifications)
        handled = read_json(HANDLED_PATH, {})
        actionable = []
        marked_noise = []
        marked_self = []

        for notification in notifications:
            notification_id = str(notification.get("id") or "")
            created_at = str(notification.get("createdAt") or "")
            kind = notification.get("kind")
            if not notification_id:
                continue
            if handled.get(notification_id) == created_at:
                continue
            if not acquire_lock(notification_id):
                continue

            try:
                issue = None
                issue_key = issue_key_from_notification(notification)

                if is_self_authored_notification(notification, issue):
                    orbit_dismiss_notification(notification_id)
                    handled[notification_id] = created_at
                    marked_self.append(notification_id)
                    continue

                if kind in NOISE_KINDS:
                    orbit_dismiss_notification(notification_id)
                    handled[notification_id] = created_at
                    marked_noise.append(notification_id)
                    continue

                if kind not in ACTIONABLE_KINDS:
                    report_failure(
                        f"orbit-notifications:unknown-kind:{kind}",
                        f"unknown Orbit notification kind `{kind}` for notification {notification_id}; leaving it unread",
                    )
                    release_lock(notification_id)
                    continue

                if issue_key:
                    try:
                        issue = fetch_issue(issue_key)
                    except Exception as exc:
                        report_failure(
                            f"orbit-notifications:issue-fetch:{notification_id}",
                            f"failed to fetch Orbit issue `{issue_key}` for notification {notification_id}: {exc}",
                        )

                if is_self_authored_notification(notification, issue):
                    orbit_dismiss_notification(notification_id)
                    handled[notification_id] = created_at
                    marked_self.append(notification_id)
                    continue

                actionable.append({**notification, "issueKey": issue_key, "issue": issue})
            finally:
                if notification_id not in [str(item.get("id") or "") for item in actionable]:
                    release_lock(notification_id)

        write_json(HANDLED_PATH, handled)
        write_json(ACTIONABLE_PATH, actionable)
        if not actionable:
            print(
                json.dumps(
                    {
                        "run": False,
                        "reason": f"no actionable Orbit notifications; marked {len(marked_noise)} noise and {len(marked_self)} self-authored notification(s) done",
                    }
                )
            )
            return 0

        print(
            json.dumps(
                {
                    "run": True,
                    "reason": f"found {len(actionable)} actionable Orbit notification(s); marked {len(marked_noise)} noise and {len(marked_self)} self-authored notification(s) done",
                }
            )
        )
        return 0
    except Exception as exc:
        report_failure("orbit-notifications:check", f"notification check failed: {exc}")
        print(json.dumps({"run": False, "reason": f"notification check failed: {exc}"}))
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
