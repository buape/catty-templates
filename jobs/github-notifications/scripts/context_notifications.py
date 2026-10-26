#!/usr/bin/env python3
from __future__ import annotations

import json
import urllib.parse
from github_job_lib import STATE_DIR, gh_api, read_json, write_json

ACTIONABLE_PATH = STATE_DIR / "actionable.json"
CONTEXT_JSON_PATH = STATE_DIR / "actionable-context.json"


def api_path_from_url(url: str | None) -> str | None:
    if not url:
        return None
    parsed = urllib.parse.urlparse(url)
    if parsed.netloc != "api.github.com":
        return None
    return parsed.path.lstrip("/")


def fetch_optional(url: str | None):
    path = api_path_from_url(url)
    if not path:
        return None
    try:
        return gh_api(path)
    except Exception as exc:
        return {"_fetch_error": str(exc), "_url": url}


def compact(value, limit=8000):
    text = json.dumps(value, indent=2, sort_keys=True)
    if len(text) <= limit:
        return text
    return text[:limit] + "\n... truncated ..."


def main() -> int:
    notifications = read_json(ACTIONABLE_PATH, [])
    enriched = []
    for notification in notifications:
        subject = notification.get("subject") or {}
        subject_data = fetch_optional(subject.get("url"))
        latest_comment = fetch_optional(subject.get("latest_comment_url"))

        reply_api_url = None
        if isinstance(subject_data, dict):
            reply_api_url = subject_data.get("comments_url") or subject_data.get("issue_url")
            if notification.get("reason") == "review_requested" and subject.get("type") == "PullRequest":
                reply_api_url = subject_data.get("comments_url")

        enriched.append(
            {
                "thread_id": notification.get("id"),
                "reason": notification.get("reason"),
                "updated_at": notification.get("updated_at"),
                "repository": (notification.get("repository") or {}).get("full_name"),
                "subject": subject,
                "subject_data": subject_data,
                "latest_comment": latest_comment,
                "reply_api_url": reply_api_url,
            }
        )

    write_json(CONTEXT_JSON_PATH, enriched)

    print("# GitHub notification context")
    print()
    print(f"Actionable notifications: {len(enriched)}")
    print()
    print(f"Full JSON context: `{CONTEXT_JSON_PATH}`")
    print()
    for item in enriched:
        subject = item.get("subject") or {}
        print(f"## Thread {item.get('thread_id')} — {item.get('reason')}")
        print()
        print(f"- Repository: `{item.get('repository')}`")
        print(f"- Updated: `{item.get('updated_at')}`")
        print(f"- Subject type: `{subject.get('type')}`")
        print(f"- Subject title: {subject.get('title')}")
        print(f"- Subject API URL: `{subject.get('url')}`")
        print(f"- Latest comment API URL: `{subject.get('latest_comment_url')}`")
        print(f"- Reply API URL: `{item.get('reply_api_url')}`")
        print()
        print("### Latest comment / mention payload")
        print()
        print("```json")
        print(compact(item.get("latest_comment")))
        print("```")
        print()
        if item.get("reason") == "review_requested":
            print("### PR payload")
            print()
            print("```json")
            print(compact(item.get("subject_data"), limit=12000))
            print("```")
            print()

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
