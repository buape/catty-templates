#!/usr/bin/env python3
from __future__ import annotations

import json
import re
import sys
from datetime import datetime, timezone
from github_job_lib import (
    ACTIONABLE_REASONS,
    NOISE_REASONS,
    STATE_DIR,
    acquire_lock,
    gh_api,
    mark_thread_done,
    read_json,
    release_lock,
    report_failure,
    write_json,
)

HANDLED_PATH = STATE_DIR / "handled.json"
ACTIONABLE_PATH = STATE_DIR / "actionable.json"
RAW_PATH = STATE_DIR / "notifications.json"
REPROCESS_PATH = STATE_DIR / "reprocess.json"
SELF_LOGIN = "<your-github-login>"
GITHUB_ORGANIZATION = "<your-github-organization>"


def api_path_from_url(url: str | None) -> str | None:
    if not url:
        return None
    prefix = "https://api.github.com/"
    if not url.startswith(prefix):
        return None
    return url[len(prefix) :]


def fetch_optional(url: str | None):
    path = api_path_from_url(url)
    if not path:
        return None
    try:
        return gh_api(path)
    except Exception:
        return None


def notification_authors(notification: dict) -> tuple[str | None, str | None]:
    subject = notification.get("subject") or {}
    latest_author = None
    subject_author = None

    latest_comment = fetch_optional(subject.get("latest_comment_url"))
    if isinstance(latest_comment, dict):
        latest_author = (latest_comment.get("user") or {}).get("login")

    subject_data = fetch_optional(subject.get("url"))
    if isinstance(subject_data, dict):
        subject_author = (subject_data.get("user") or {}).get("login")

    return latest_author, subject_author


def notification_is_from_self(notification: dict) -> bool:
    latest_author, _subject_author = notification_authors(notification)
    return latest_author == SELF_LOGIN


def pull_request_path_from_subject(notification: dict) -> tuple[str, str, str] | None:
    subject = notification.get("subject") or {}
    url = subject.get("url") or ""
    match = re.fullmatch(r"https://api\.github\.com/repos/([^/]+)/([^/]+)/pulls/(\d+)", url)
    if not match:
        return None
    return match.group(1), match.group(2), match.group(3)


def parse_github_time(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def notification_subject_data(notification: dict):
    subject = notification.get("subject") or {}
    return fetch_optional(subject.get("url"))


def should_handle_mention_notification(notification: dict) -> bool:
    subject = notification.get("subject") or {}
    latest_comment_url = subject.get("latest_comment_url")
    if latest_comment_url:
        return True

    subject_data = notification_subject_data(notification)
    if not isinstance(subject_data, dict):
        return False

    # GitHub keeps old mention/team_mention notification threads alive and bumps
    # them for force-pushes, bot refreshes, label edits, etc. Those updates have
    # no latest comment URL and should not make Agent drop a new "did you mean
    # me?" comment. Only handle subject-level mentions when the issue/PR itself
    # is new, where the body/title is the actual notification source.
    created_at = parse_github_time(subject_data.get("created_at"))
    updated_at = parse_github_time(subject_data.get("updated_at"))
    if not created_at or not updated_at:
        return False
    return abs((updated_at - created_at).total_seconds()) <= 60


def happened_near_notification(notification: dict, value: str | None, window_seconds: int = 300) -> bool:
    updated_at = parse_github_time(notification.get("updated_at"))
    event_at = parse_github_time(value)
    if not updated_at or not event_at:
        return False
    return abs((updated_at - event_at).total_seconds()) <= window_seconds


def pr_has_recent_external_activity(notification: dict) -> bool:
    subject = notification.get("subject") or {}
    if subject.get("type") != "PullRequest":
        return False
    pr_path = pull_request_path_from_subject(notification)
    if not pr_path:
        return False

    owner, repo, number = pr_path

    # GitHub sometimes represents comments/reviews on Agent-authored PRs as an
    # `author` notification with no latest_comment_url. Any external comment or
    # review on Agent's PR is actionable, regardless of GitHub's reason label.
    try:
        issue_comments = gh_api(f"repos/{owner}/{repo}/issues/{number}/comments") or []
    except Exception:
        issue_comments = []
    for comment in issue_comments:
        commenter = (comment.get("user") or {}).get("login")
        if commenter and commenter != SELF_LOGIN and happened_near_notification(notification, comment.get("updated_at") or comment.get("created_at")):
            return True

    try:
        reviews = gh_api(f"repos/{owner}/{repo}/pulls/{number}/reviews") or []
    except Exception:
        reviews = []
    for review in reviews:
        reviewer = (review.get("user") or {}).get("login")
        if reviewer and reviewer != SELF_LOGIN and happened_near_notification(notification, review.get("submitted_at")):
            return True

    try:
        review_comments = gh_api(f"repos/{owner}/{repo}/pulls/{number}/comments") or []
    except Exception:
        review_comments = []
    for comment in review_comments:
        commenter = (comment.get("user") or {}).get("login")
        if commenter and commenter != SELF_LOGIN and happened_near_notification(notification, comment.get("updated_at") or comment.get("created_at")):
            return True

    return False


def should_handle_noise_notification(notification: dict) -> bool:
    reason = notification.get("reason")
    subject = notification.get("subject") or {}
    latest_author, subject_author = notification_authors(notification)

    if latest_author == SELF_LOGIN:
        return False

    # Reviews/comments on Agent-authored PRs are actionable: requested changes,
    # follow-up questions, and CI/debug comments on Agent's own work should not be
    # swept away as generic subscribed/comment noise.
    if subject.get("type") != "PullRequest" or subject_author != SELF_LOGIN:
        return False
    if latest_author is not None:
        return True
    if pr_has_recent_external_activity(notification):
        return True
    return False


def merge_notifications(primary: list[dict], extra: list[dict]) -> list[dict]:
    seen = set()
    merged = []
    for notification in [*primary, *extra]:
        thread_id = str(notification.get("id", ""))
        if not thread_id or thread_id in seen:
            continue
        seen.add(thread_id)
        merged.append(notification)
    return merged


def latest_external_change_request(owner: str, repo: str, number: int) -> dict | None:
    try:
        reviews = gh_api(f"repos/{owner}/{repo}/pulls/{number}/reviews") or []
    except Exception:
        return None
    change_requests = [
        review
        for review in reviews
        if review.get("state") == "CHANGES_REQUESTED"
        and (review.get("user") or {}).get("login") != SELF_LOGIN
        and review.get("submitted_at")
    ]
    if not change_requests:
        return None
    return max(change_requests, key=lambda review: review.get("submitted_at") or "")


def has_self_activity_after_change_request(owner: str, repo: str, number: int, review: dict) -> bool:
    submitted_at = parse_github_time(review.get("submitted_at"))
    if not submitted_at:
        return False

    endpoints = [
        f"repos/{owner}/{repo}/issues/{number}/comments",
        f"repos/{owner}/{repo}/pulls/{number}/comments",
        f"repos/{owner}/{repo}/pulls/{number}/reviews",
    ]
    for endpoint in endpoints:
        try:
            items = gh_api(endpoint) or []
        except Exception:
            items = []
        for item in items:
            actor = (item.get("user") or {}).get("login")
            if actor != SELF_LOGIN:
                continue
            happened_at = parse_github_time(
                item.get("submitted_at") or item.get("updated_at") or item.get("created_at")
            )
            if happened_at and happened_at > submitted_at:
                return True
    return False


def synthetic_change_request_notifications() -> list[dict]:
    """Catch Agent-authored PR change requests even when GitHub does not leave an unread notification."""
    try:
        results = gh_api(
            f"search/issues?q=org:{GITHUB_ORGANIZATION}+is:pr+is:open+author:{SELF_LOGIN}+review:changes_requested&per_page=50"
        ) or {}
    except Exception:
        return []

    notifications = []
    for item in results.get("items") or []:
        pull_request = item.get("pull_request") or {}
        api_url = pull_request.get("url")
        match = re.fullmatch(r"https://api\.github\.com/repos/([^/]+)/([^/]+)/pulls/(\d+)", api_url or "")
        if not match:
            continue
        owner, repo, number_text = match.group(1), match.group(2), match.group(3)
        number = int(number_text)
        latest_review = latest_external_change_request(owner, repo, number)
        if not latest_review:
            continue
        if has_self_activity_after_change_request(owner, repo, number, latest_review):
            continue
        review_id = latest_review.get("id")
        submitted_at = latest_review.get("submitted_at")
        notifications.append(
            {
                "id": f"synthetic:changes-requested:{owner}:{repo}:{number}",
                "reason": "author",
                "unread": True,
                "updated_at": submitted_at,
                "repository": {"full_name": f"{owner}/{repo}"},
                "subject": {
                    "title": item.get("title"),
                    "url": api_url,
                    "latest_comment_url": f"https://api.github.com/repos/{owner}/{repo}/pulls/{number}/reviews/{review_id}" if review_id else None,
                    "type": "PullRequest",
                },
            }
        )
    return notifications


def main() -> int:
    try:
        notifications = gh_api("notifications", "--paginate") or []
        notifications = merge_notifications(notifications, synthetic_change_request_notifications())
        reprocess_ids = {str(item) for item in read_json(REPROCESS_PATH, [])}
        if reprocess_ids:
            all_notifications = gh_api("notifications?all=true&per_page=100", "--paginate") or []
            notifications = merge_notifications(
                notifications,
                [notification for notification in all_notifications if str(notification.get("id", "")) in reprocess_ids],
            )
        write_json(RAW_PATH, notifications)
        handled = read_json(HANDLED_PATH, {})
        actionable = []
        marked_noise = []
        marked_self = []
        marked_stale_mentions = []
        actionable_ids = set()
        for notification in notifications:
            thread_id = str(notification.get("id", ""))
            reason = notification.get("reason")
            updated_at = notification.get("updated_at")
            if not thread_id:
                continue
            force_reprocess = thread_id in reprocess_ids
            if handled.get(thread_id) == updated_at and not force_reprocess:
                continue
            if reason in NOISE_REASONS:
                if not acquire_lock(thread_id):
                    continue
                try:
                    if notification_is_from_self(notification):
                        mark_thread_done(thread_id)
                        handled[thread_id] = updated_at
                        marked_self.append(thread_id)
                        continue
                    if should_handle_noise_notification(notification) or thread_id.startswith("synthetic:"):
                        actionable.append(notification)
                        actionable_ids.add(thread_id)
                        continue
                    mark_thread_done(thread_id)
                    handled[thread_id] = updated_at
                    marked_noise.append(thread_id)
                finally:
                    if thread_id not in actionable_ids:
                        release_lock(thread_id)
                continue
            if reason not in ACTIONABLE_REASONS:
                report_failure(
                    f"github-notifications:unknown-reason:{reason}",
                    f"unknown GitHub notification reason `{reason}` for thread {thread_id}; leaving it unread for manual handling",
                )
                continue
            if not acquire_lock(thread_id):
                continue
            try:
                if notification_is_from_self(notification):
                    mark_thread_done(thread_id)
                    handled[thread_id] = updated_at
                    marked_self.append(thread_id)
                    continue
                if reason in {"mention", "team_mention"} and not should_handle_mention_notification(notification):
                    mark_thread_done(thread_id)
                    handled[thread_id] = updated_at
                    marked_stale_mentions.append(thread_id)
                    continue
                actionable.append(notification)
                actionable_ids.add(thread_id)
            finally:
                if thread_id in marked_self or thread_id in marked_stale_mentions:
                    release_lock(thread_id)

        write_json(HANDLED_PATH, handled)
        write_json(ACTIONABLE_PATH, actionable)
        if not actionable:
            print(
                json.dumps(
                    {
                        "run": False,
                        "reason": f"no actionable GitHub notifications; marked {len(marked_noise)} noise, {len(marked_self)} self-authored, and {len(marked_stale_mentions)} stale mention notification(s) done",
                    }
                )
            )
            return 0

        print(
            json.dumps(
                {
                    "run": True,
                    "reason": f"found {len(actionable)} actionable GitHub notification(s); marked {len(marked_noise)} noise, {len(marked_self)} self-authored, and {len(marked_stale_mentions)} stale mention notification(s) done",
                }
            )
        )
        return 0
    except Exception as exc:
        report_failure("github-notifications:check", f"notification check failed: {exc}")
        print(
            json.dumps({"run": False, "reason": f"notification check failed: {exc}"})
        )
        return 0


if __name__ == "__main__":
    raise SystemExit(main())
