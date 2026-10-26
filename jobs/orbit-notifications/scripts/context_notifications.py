#!/usr/bin/env python3
from __future__ import annotations

import json
from orbit_job_lib import STATE_DIR, issue_key_from_notification, read_json, write_json

ACTIONABLE_PATH = STATE_DIR / "actionable.json"
CONTEXT_JSON_PATH = STATE_DIR / "actionable-context.json"


def compact(value, limit=10000):
    text = json.dumps(value, indent=2, sort_keys=True)
    if len(text) <= limit:
        return text
    return text[:limit] + "\n... truncated ..."


def main() -> int:
    notifications = read_json(ACTIONABLE_PATH, [])
    write_json(CONTEXT_JSON_PATH, notifications)

    print("# Orbit notification context")
    print()
    print(f"Actionable notifications: {len(notifications)}")
    print()
    print(f"Full JSON context: `{CONTEXT_JSON_PATH}`")
    print()
    for item in notifications:
        issue_key = item.get("issueKey") or issue_key_from_notification(item)
        print(f"## Notification {item.get('id')} — {item.get('kind')}")
        print()
        print(f"- Created: `{item.get('createdAt')}`")
        print(f"- Title: {item.get('title')}")
        print(f"- Body: {item.get('body')}")
        print(f"- Action URL: `{item.get('actionUrl')}`")
        print(f"- Issue key: `{issue_key}`")
        issue = item.get("issue")
        if issue:
            print(f"- Issue title: {issue.get('title')}")
            print(f"- Issue status: `{issue.get('status')}`")
            assignee = issue.get("assignee") or {}
            print(f"- Issue assignee: {assignee.get('name')} <{assignee.get('email')}>")
            print()
            print("### Issue payload")
            print()
            print("```json")
            print(compact(issue))
            print("```")
        print()
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
