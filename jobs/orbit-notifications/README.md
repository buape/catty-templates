# Orbit notifications job

Give this folder to your agent and ask it to adapt it into `<your-workspace>/jobs/orbit-notifications/`. These are ordinary Catty job files, not a template engine. No credentials or notification history are included. The job is disabled until customized.

## Customize before enabling

1. Install Python 3.10+ and ensure Catty's job process has the required executable paths.
2. Configure your own authenticated official Orbit MCP access. This folder expects an existing helper at `<your-workspace>/skills/orbit/bin/orbit_mcp.py`; it is **not bundled here**. Change `ORBIT` / `orbit_call()` in `scripts/orbit_job_lib.py` if your agent uses a different official MCP client. The default adapter executes `<helper> call <tool-name> <json-arguments>` and expects parsed tool data as JSON on stdout, not an MCP envelope, with diagnostics on stderr. Make a Python helper executable or adjust the command to invoke Python explicitly.
3. Confirm the helper supports `orbit_notification_list` (`organizationSlug`) returning a list; `orbit_notification_dismiss` (`organizationSlug`, `notificationId`); and `orbit_issue_get` (`organizationSlug`, `issueKey`) returning an issue object. Verify your live schemas; adapt if your Orbit version differs. The prompt also expects issue status updates and comments with `repliesToId` through your normal Orbit workflow.
4. Replace `<your-orbit-organization-slug>`, `<your-orbit-account-email>`, and `<your-orbit-display-name>` in `scripts/orbit_job_lib.py`. Confirm self-authored filtering matches your account and your instance's notification/comment shape.
5. In the same library, replace the Discord alert channel, operator mention, and absolute Catty config path placeholders. The reporter reads a top-level quoted `token = "..."` line; adapt `discord_token()` to your harness's secret source, or use your approved reporting transport. Never hardcode real credentials. Missing credentials disable Discord delivery; failures still appear in job output. Verify the alert path before enabling.
6. Read `prompt.md` and adapt status names, branch conventions, GitHub linking, review and authorization policies to your workspace. This template grants no merge/release authority.
7. Validate Python syntax and run context generation against empty local state first. **The check script is not read-only:** it dismisses noise/self notifications. Review the filters before the first authenticated run. Run `python3 scripts/check_notifications.py` from the job folder, inspect `.state/actionable.json`, and verify reporting with a harmless sanitized test alert. Increase check/context timeouts in `meta.toml` if your MCP helper's retries or notification volume need longer.
8. Set `enabled = true` in `meta.toml` after setup. Catty discovers the folder; it checks every five minutes and only wakes the agent for actionable work.

## Files and behavior

- `meta.toml`: schedule, deterministic pre-check, context builder.
- `prompt.md`: agent instructions for mentions, assignments, due dates and delivery failures.
- `scripts/check_notifications.py`: filtering, issue enrichment, dedupe and local locks.
- `scripts/context_notifications.py`: builds Markdown context and `.state/actionable-context.json`.
- `scripts/mark_handled.py`: dismisses a notification through MCP and releases its lock.
- `scripts/report_failure.py`: rate-limited operator alerts; takes JSON on stdin.
- `.state/`: generated private notification payloads, dedupe timestamps, locks and reports; do not share or copy another agent's state. Unfinished locks expire after 30 minutes.

Keep the existing `.gitignore`. The agent's final job response is logged, not automatically sent to Discord. Never use direct database edits as an MCP fallback.
