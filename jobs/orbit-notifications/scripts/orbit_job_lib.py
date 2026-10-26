#!/usr/bin/env python3
from __future__ import annotations

import hashlib
import json
import os
import subprocess
import time
import urllib.error
import urllib.request
from pathlib import Path

JOB_DIR = Path(__file__).resolve().parents[1]
WORKSPACE = JOB_DIR.parents[1]
STATE_DIR = JOB_DIR / ".state"
ORBIT = WORKSPACE / "skills" / "orbit" / "bin" / "orbit_mcp.py"
CORE_ERROR_CHANNEL_ID = "<your-discord-alert-channel-id>"
OPERATOR_MENTION = "<@your-discord-user-id>"
ORGANIZATION_SLUG = "<your-orbit-organization-slug>"
SELF_EMAIL = "<your-orbit-account-email>"
SELF_NAME = "<your-orbit-display-name>"

ACTIONABLE_KINDS = {"Mention", "Assignment", "UpcomingDueDate", "PastDueDate", "DeliveryFailure"}
NOISE_KINDS = {"WatchedIssueActivity", "JoinedOrg", "JoinedTeam", "TeamCreated"}

STATE_DIR.mkdir(parents=True, exist_ok=True)


def read_json(path: Path, default):
    try:
        return json.loads(path.read_text())
    except FileNotFoundError:
        return default
    except json.JSONDecodeError:
        return default


def write_json(path: Path, data) -> None:
    tmp = path.with_suffix(path.suffix + ".tmp")
    tmp.write_text(json.dumps(data, indent=2, sort_keys=True))
    tmp.replace(path)


def _clip(value: str | None, limit: int = 1200) -> str:
    text = (value or "").strip()
    if len(text) <= limit:
        return text
    return text[-limit:]


def orbit_call(tool: str, args: dict):
    env = os.environ.copy()
    env["PATH"] = os.environ.get("PATH", os.defpath)
    cmd = [str(ORBIT), "call", tool, json.dumps(args)]
    last_error = None
    for attempt in range(3):
        try:
            result = subprocess.run(
                cmd,
                cwd=str(WORKSPACE),
                env=env,
                check=True,
                stdout=subprocess.PIPE,
                stderr=subprocess.PIPE,
                text=True,
                timeout=75,
            )
            out = result.stdout.strip()
            if not out:
                return None
            try:
                return json.loads(out)
            except json.JSONDecodeError as exc:
                raise RuntimeError(f"{tool} returned non-JSON stdout: {_clip(out)}") from exc
        except subprocess.TimeoutExpired as exc:
            last_error = (
                f"{tool} timed out after {exc.timeout}s; "
                f"stdout={_clip(exc.stdout)} stderr={_clip(exc.stderr)}"
            )
        except subprocess.CalledProcessError as exc:
            last_error = (
                f"{tool} exited {exc.returncode}; "
                f"stdout={_clip(exc.stdout)} stderr={_clip(exc.stderr)}"
            )
        if attempt < 2:
            time.sleep(2 * (attempt + 1))
    raise RuntimeError(last_error or f"{tool} failed")


def orbit_list_notifications():
    notifications = orbit_call(
        "orbit_notification_list", {"organizationSlug": ORGANIZATION_SLUG}
    )
    if not isinstance(notifications, list) or any(
        not isinstance(item, dict) for item in notifications
    ):
        raise RuntimeError("orbit_notification_list returned an invalid notification list")
    return notifications


def orbit_dismiss_notification(notification_id: str):
    return orbit_call(
        "orbit_notification_dismiss",
        {"organizationSlug": ORGANIZATION_SLUG, "notificationId": notification_id},
    )


def issue_key_from_notification(notification: dict) -> str | None:
    action_url = str(notification.get("actionUrl") or "")
    parts = [part for part in action_url.split("/") if part]
    if len(parts) >= 3:
        team_slug = parts[-2]
        friendly_id = parts[-1]
        if friendly_id.isdigit():
            return f"{team_slug.upper()}-{friendly_id}"
    title = str(notification.get("title") or "")
    import re

    match = re.search(r"\[([A-Za-z0-9]+-\d+)\]", title)
    if match:
        return match.group(1).upper()
    return None


def fetch_issue(issue_key: str):
    issue = orbit_call(
        "orbit_issue_get", {"organizationSlug": ORGANIZATION_SLUG, "issueKey": issue_key}
    )
    if not isinstance(issue, dict):
        raise RuntimeError("orbit_issue_get returned an invalid issue object")
    return issue


def is_self_authored_notification(notification: dict, issue: dict | None = None) -> bool:
    body = str(notification.get("body") or "")
    if body.startswith(f"{SELF_NAME} commented:"):
        return True
    if issue:
        comments = issue.get("comments") or []
        if comments:
            latest = comments[-1]
            author = latest.get("author") or {}
            if author.get("email") == SELF_EMAIL:
                return True
    return False


def acquire_lock(notification_id: str, ttl_seconds: int = 1800) -> bool:
    lock_path = STATE_DIR / "locks" / f"{notification_id}.lock"
    lock_path.parent.mkdir(parents=True, exist_ok=True)
    now = time.time()
    if lock_path.exists():
        try:
            existing = json.loads(lock_path.read_text())
            created = float(existing.get("created", 0) or 0)
        except Exception:
            created = lock_path.stat().st_mtime
        if now - created < ttl_seconds:
            return False
        lock_path.unlink(missing_ok=True)
    lock_path.write_text(json.dumps({"created": now, "pid": os.getpid()}))
    return True


def release_lock(notification_id: str) -> None:
    (STATE_DIR / "locks" / f"{notification_id}.lock").unlink(missing_ok=True)


def discord_token() -> str | None:
    config_path = Path("<absolute-path-to-your-catty-config.toml>").expanduser()
    if not config_path.exists():
        return None
    for raw in config_path.read_text().splitlines():
        line = raw.strip()
        if line.startswith("token") and "=" in line:
            value = line.split("=", 1)[1].strip()
            if value.startswith('"') and value.endswith('"'):
                value = value[1:-1]
            return value or None
    return None


def report_failure(key: str, message: str, min_interval_seconds: int = 3600) -> bool:
    reports_path = STATE_DIR / "failure_reports.json"
    reports = read_json(reports_path, {})
    digest = hashlib.sha256(f"{key}:{message}".encode()).hexdigest()
    now = time.time()
    last = float(reports.get(digest, 0) or 0)
    if now - last < min_interval_seconds:
        return False
    token = discord_token()
    if not token:
        return False
    body = {"content": f"{OPERATOR_MENTION} Agent Orbit notification job error: {message[:1500]}"}
    req = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{CORE_ERROR_CHANNEL_ID}/messages",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "AgentOrbitNotificationJob/1.0",
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            if resp.status >= 300:
                return False
    except (urllib.error.URLError, TimeoutError):
        return False
    reports[digest] = now
    write_json(reports_path, reports)
    return True
