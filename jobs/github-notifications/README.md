# GitHub notifications job

Give this folder to your agent and ask it to adapt it into `<your-workspace>/jobs/github-notifications/`. These are ordinary Catty job files, not a template engine. No credentials or notification history are included. The job is disabled until customized.

## Customize before enabling

1. Install Python 3.10+ and `gh`; ensure Catty's job process can find both on PATH.
2. Replace `<your-github-login>` in `scripts/github_job_lib.py` and `scripts/check_notifications.py`, and `<your-github-organization>` in the latter. The organization scopes the backup search for requested changes on your own PRs; normal notifications come from your account inbox.
3. Authenticate **your own account** in a job-local config, using an absolute path: `GH_CONFIG_DIR=<absolute-job-folder>/.gh gh auth login`. Verify with the same environment and `gh api user --jq .login`. The helper will not copy or switch your global configuration. Ensure that account has the repository and notification access it needs. Watch relevant repos if you expect all their activity.
4. In `scripts/github_job_lib.py`, replace the Discord alert channel, operator mention, and absolute Catty config path placeholders. The example reporter reads a top-level quoted `token = "..."` line; adapt `discord_token()` to your harness's actual secret source, or replace `report_failure()` with your approved alert transport. Never paste a real token into the template/scripts. Missing credentials disable Discord delivery; check failures still appear in job output. Do not enable before the alert path is verified.
5. Read `prompt.md` and replace generic workflow references with your own review skill, authorization and escalation policies. This template grants no merge/release/admin permission.
6. Validate Python syntax and run context generation against an empty local state first. **The check script is not read-only:** it marks noise/self/stale notifications done. Inspect its filters before the first authenticated run. Then run `python3 scripts/check_notifications.py` from the job folder, inspect `.state/actionable.json`, and verify error reporting with a harmless sanitized test message.
7. Set `enabled = true` in `meta.toml` after setup. Catty discovers the folder; the example checks every five minutes and only wakes the agent for actionable work.

## Files and behavior

- `meta.toml`: schedule, deterministic pre-check, context builder.
- `prompt.md`: instructions for the agent when there is work.
- `scripts/check_notifications.py`: noise filtering, self-notification suppression, stale-mention filtering, external activity on your PRs, and a requested-changes backup search.
- `scripts/context_notifications.py`: fetches subject/latest-comment context; fuller data stays in `.state/actionable-context.json`.
- `scripts/mark_handled.py`: completes a notification and releases its local lock.
- `scripts/report_failure.py`: rate-limited operator alerts; takes JSON on stdin.
- `.state/`: generated private state, dedupe timestamps, locks and reports. Never copy another agent's state. Unfinished locks expire after 30 minutes.
- `.gh/`: private job-local GitHub authentication. Never commit or share it.

Keep the existing `.gitignore`. The agent's final job response is logged, not automatically sent to Discord.
