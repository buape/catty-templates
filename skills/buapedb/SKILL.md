---
name: buapedb
description: "Access Buape databases with the published buapedb CLI. Use for Buape database access, temporary credentials, connection URLs, renewal, or ending credentials. Buape work only."
---

# buapedb

## Install

```sh
brew update
brew install buape/tap/buapedb
buapedb --version
```

Use the Homebrew-managed binary on PATH. Keep only `SKILL.md` in this skill
directory; do not bundle or copy an executable here. No additional CLI helpers
or toolchains are required. Update with `brew upgrade buape/tap/buapedb`.

## Usage

```sh
buapedb list
buapedb kiai
buapedb orbit --write
buapedb kiai --renew <id>
buapedb orbit --end
```

- Read-only unless `--write` is requested. Discover available databases with
  `buapedb list`; do not hardcode an inventory.
- The full connection URL goes to the clipboard. Tell the user to **paste in
  your database tool**. Password output stays `***` when copying succeeds.
- If clipboard copying fails, the CLI prints the full password and URL. Treat
  both as secrets; do not copy them into chat, tickets, commits, or logs.
- `--json` deliberately outputs credentials for scripts. Use only when needed;
  consume its output privately, not as progress or verification text.
- Let the user complete sign-in. Keep status generic, such as “Signing in…”.
  Do not narrate backend implementation, policies, or sign-in prompt steps.
- Never use an operator/root token to stand in for a user's login. In particular,
  do not set `BAO_TOKEN` from an operator credential when fetching user access.
- Use the displayed expiry. An expired saved connection needs fresh credentials;
  do not promise that renewal will revive an expired credential.
- Scope `--end` to the requested database. It ends credentials tracked on this
  machine for that database, not every server-side credential.
- On denied access or failed renewal/revocation, report the error; do not claim
  success, silently drop failures, or bypass access controls.
