# Catty Homebrew update checker

Give this folder to your agent to adapt into `<your-workspace>/jobs/catty-update-checker/`. Disabled by default; checks every 24 hours once enabled. No automatic upgrades or restarts.

## Setup

1. Install Python 3.10+ and Catty through `buape/tap/catty` in Homebrew on the machine running the job. Works with macOS Homebrew and Linuxbrew. It checks the installed formula, not the running process version, npm installs, or HEAD commits.
2. Ensure the job process can find `brew`, or set `BREW_BIN` in its inherited environment to an absolute executable path. Standard Apple Silicon, Intel Mac, and Linuxbrew paths are also detected. Run under the Homebrew owner's account, never root/sudo.
3. Replace `<your-discord-channel-id>` in `prompt.md`. Verify your agent has permission and a working Discord delivery tool for that channel. Adapt delivery instructions if you use another transport.
4. From the job folder, run `python3 -m unittest discover -s scripts -p 'test_*.py'`, then `python3 scripts/check_updates.py`. The latter runs `brew update` to refresh all configured tap metadata (no package upgrades), then queries this formula. Allow up to 13 minutes for the check; subprocess calls have individual four-minute timeouts. Errors fail the check and appear in Catty job logs rather than masquerading as 'up to date'. Monitor those logs using your normal job-error reporting.
5. Inspect `.state/pending.json` and run `python3 scripts/update_state.py context`. Test notification delivery before enabling. Only run `mark-notified` after a real successful alert.
6. Set `enabled = true` in `meta.toml`. Keep `.gitignore`; state is private and host-specific.

The deterministic pre-check returns `run: false` without waking the agent when there is no new version to announce. Once a notification succeeds, that available version is suppressed until a different version becomes available. Failed delivery is retried on the next daily check. Pinned formulae are still reported; this job never unpins them. Homebrew metadata refresh affects all taps, so coordinate with other Homebrew maintenance on this host.

This template checks its local host only. Installing it on a Mac does not check a separate Linux box; put it on that box's Catty workspace instead. It grants no remote-access or self-update authority.
