#!/usr/bin/env python3
"""Read-only installed-package check; brew update refreshes Homebrew metadata."""
from __future__ import annotations

import json
import os
from pathlib import Path
import shutil
import subprocess
import sys

ROOT = Path(__file__).resolve().parents[1]
STATE = ROOT / ".state"
FORMULA = "buape/tap/catty"


def write_json(path: Path, data: dict) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    temporary = path.with_suffix(".tmp")
    temporary.write_text(json.dumps(data, indent=2) + "\n")
    temporary.replace(path)


def brew_command() -> str:
    configured = os.environ.get("BREW_BIN")
    if configured:
        return configured
    found = shutil.which("brew")
    if found:
        return found
    for candidate in ("/opt/homebrew/bin/brew", "/usr/local/bin/brew", "/home/linuxbrew/.linuxbrew/bin/brew"):
        if Path(candidate).is_file():
            return candidate
    raise RuntimeError("Homebrew not found; configure BREW_BIN or the job process PATH")


def run_brew(brew: str, *args: str) -> str:
    result = subprocess.run(
        [brew, *args], text=True, capture_output=True, timeout=240,
        env={**os.environ, "HOMEBREW_NO_AUTO_UPDATE": "1", "HOMEBREW_NO_ANALYTICS": "1"},
    )
    # `outdated` exits 1 when an explicitly requested formula is outdated.
    if result.returncode and not (args[0] == "outdated" and result.returncode == 1):
        # Do not echo raw command output: tap URLs can contain credentials.
        raise RuntimeError(f"brew {' '.join(args)} failed (exit {result.returncode}); inspect Homebrew locally")
    return result.stdout


def main() -> int:
    try:
        brew = brew_command()
        run_brew(brew, "update")
        info = json.loads(run_brew(brew, "info", "--json=v2", FORMULA))
        formula = next(f for f in info["formulae"] if f["full_name"] == FORMULA)
        installed = [entry["version"] for entry in formula.get("installed", [])]
        if not installed:
            raise RuntimeError(f"{FORMULA} is not installed with Homebrew on this host")
        outdated = json.loads(run_brew(brew, "outdated", "--formula", "--json=v2", FORMULA))
        candidate = next((f for f in outdated["formulae"] if f["name"] in ("catty", FORMULA)), None)
        previous = json.loads((STATE / "notified.json").read_text()) if (STATE / "notified.json").exists() else {}
        version = candidate["current_version"] if candidate else None
        pending = {"formula": FORMULA, "installed_versions": installed, "available_version": version}
        write_json(STATE / "pending.json", pending)
        should_run = bool(version and previous.get("available_version") != version)
        print(json.dumps({"run": should_run, "reason": f"Catty {version} is available" if should_run else "no unannounced Catty update"}))
        return 0
    except Exception as exc:
        print(f"Catty update check failed: {exc}", file=sys.stderr)
        return 1


if __name__ == "__main__":
    raise SystemExit(main())
