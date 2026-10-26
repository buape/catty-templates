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
STATE_DIR = JOB_DIR / ".state"
GH_DIR = JOB_DIR / ".gh"
CORE_ERROR_CHANNEL_ID = "<your-discord-alert-channel-id>"
OPERATOR_MENTION = "<@your-discord-user-id>"
ACTIONABLE_REASONS = {
    "assign",
    "invitation",
    "mention",
    "review_requested",
    "security_alert",
    "team_mention",
}
NOISE_REASONS = {"author", "ci_activity", "comment", "manual", "state_change", "subscribed"}

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


def ensure_gh_config() -> None:
    if not GH_DIR.exists():
        raise RuntimeError(f"Authenticate your own GitHub account first: GH_CONFIG_DIR={GH_DIR} gh auth login")
    env = os.environ.copy()
    env["GH_CONFIG_DIR"] = str(GH_DIR)
    env["PATH"] = os.environ.get("PATH", os.defpath)
    result = subprocess.run(
        ["gh", "auth", "switch", "--user", "<your-github-login>"],
        env=env,
        check=False,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
        text=True,
    )
    if result.returncode != 0:
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        details = [f"gh auth switch --user <your-github-login> exited {result.returncode}"]
        if stdout:
            details.append(f"stdout={stdout[:1000]}")
        if stderr:
            details.append(f"stderr={stderr[:1000]}")
        raise RuntimeError("; ".join(details))


def gh_api(*args: str, method: str | None = None, input_json=None):
    ensure_gh_config()
    env = os.environ.copy()
    env["GH_CONFIG_DIR"] = str(GH_DIR)
    env["PATH"] = os.environ.get("PATH", os.defpath)
    cmd = ["gh", "api"]
    if method:
        cmd += ["-X", method]
    cmd += list(args)
    kwargs = {
        "env": env,
        "stdout": subprocess.PIPE,
        "stderr": subprocess.PIPE,
        "text": True,
    }
    if input_json is not None:
        kwargs["input"] = json.dumps(input_json)
    result = subprocess.run(cmd, **kwargs)
    if result.returncode != 0:
        stdout = (result.stdout or "").strip()
        stderr = (result.stderr or "").strip()
        details = [f"gh api {' '.join(args)} exited {result.returncode}"]
        if stdout:
            details.append(f"stdout={stdout[:1000]}")
        if stderr:
            details.append(f"stderr={stderr[:1000]}")
        raise RuntimeError("; ".join(details))
    if result.stdout.strip():
        try:
            return json.loads(result.stdout)
        except json.JSONDecodeError as exc:
            raise RuntimeError(
                f"gh api {' '.join(args)} returned invalid JSON: {exc}; stdout={result.stdout[:1000]}"
            ) from exc
    return None


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
    lower_message = message.lower()
    # Release PRs blocked on normal GitHub approval/code-owner review are expected.
    # the operator gets those from GitHub; do not turn them into Discord pings.
    if "release pr" in lower_message and any(
        marker in lower_message
        for marker in ("code-owner", "code owner", "review", "approval", "approve", "agent review")
    ):
        return False

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

    body = {
        "content": f"{OPERATOR_MENTION} Agent GitHub notification job error: {message[:1500]}"
    }
    req = urllib.request.Request(
        f"https://discord.com/api/v10/channels/{CORE_ERROR_CHANNEL_ID}/messages",
        data=json.dumps(body).encode(),
        headers={
            "Authorization": f"Bot {token}",
            "Content-Type": "application/json",
            "User-Agent": "AgentGitHubNotificationJob/1.0",
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


def acquire_lock(thread_id: str, ttl_seconds: int = 1800) -> bool:
    lock_path = STATE_DIR / "locks" / f"{thread_id}.lock"
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


def mark_thread_done(thread_id: str) -> None:
    gh_api(f"notifications/threads/{thread_id}", method="DELETE")


def release_lock(thread_id: str) -> None:
    (STATE_DIR / "locks" / f"{thread_id}.lock").unlink(missing_ok=True)
