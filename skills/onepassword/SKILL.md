---
name: onepassword
description: Read, create, update, and manage the agent's credentials through 1Password CLI using a vault-scoped service account.
---

# 1Password CLI

Use `op` directly with your own service account. No custom wrapper, desktop unlock, or interactive personal-account session is required.

## Customize once

- Account: `<your-account>.1password.com`
- Agent vault: `<your-agent-vault>` (prefer its vault ID in automation).
- Install the current [1Password CLI](https://developer.1password.com/docs/cli/get-started/).
- Follow the [service-account setup guide](https://developer.1password.com/docs/service-accounts/get-started/) and [CLI authentication instructions](https://developer.1password.com/docs/service-accounts/use-with-1password-cli/).
- Grant access only to the intended agent vault. Use read/write access if the agent should save credentials it creates. Do not grant vault-creation permission unless needed. Built-in Personal/Private/Employee and default Shared vaults are not supported.
- Supply `OP_SERVICE_ACCOUNT_TOKEN` securely to the actual Catty process and jobs through your protected service environment. Do not paste it into this skill, chat, shell history, command arguments, or tracked workspace files. Keep a recovery copy under the operator's control. Service-account access permissions are immutable; replace the account when those permissions need changing.
- If `OP_CONNECT_HOST` or `OP_CONNECT_TOKEN` are set, they take precedence over service-account authentication. Inspect variable presence without printing their values; use the intended authentication mode rather than silently switching accounts.

## Operating rules

- Default to the configured agent vault. Confirm the destination before creating shared infrastructure credentials elsewhere.
- Verify the active identity and vault access before modifying items. Scope commands with `--vault`; do not assume the CLI selected the right vault.
- Use the least data needed. **`op item get --format json` can contain secret values.** JSON output is not redaction. Capture and parse it locally, never dump it into a chat or tool log.
- Prefer secret references with `op run` to inject credentials into a child process. Do not echo secret values or expanded environments. See [secret references](https://developer.1password.com/docs/cli/secret-references/).
- Use stdin/JSON templates for sensitive writes rather than literal secrets in command arguments. Capture command output too: item create/edit responses can include secrets.
- If temporary secret files are unavoidable, create them with restrictive permissions (directory 700, files 600), outside git. Clean them up after use. Do not use predictable shared `/tmp/item.json` paths.
- Never disclose passwords, tokens, recovery codes or TOTP seeds. Follow your workspace's explicit policy for sharing a requested verification code; code handling does not authorize revealing its seed.
- Store TOTP seeds/URIs in an actual `OTP` field, not notes. Verify code generation without printing seeds.
- Do not delete items, rotate live credentials, or expand access without authorization. For authorized rotation, update the consuming runtime and verify it before considering the old credential retired.
- On authentication/keychain errors or hangs, stop and report a sanitized blocker. Do not fall back to another person's account.

## Verify authentication

These commands show identity and vault metadata, not stored passwords. Still keep private account metadata out of public channels.

```bash
op user get --me
op vault list --format json
```

Confirm the result is the intended service account and the expected vault is accessible.

## Common operations

Replace `<your-agent-vault>` with your actual vault name or ID. Inspect `op <command> --help` before unfamiliar operations; do not guess field names or flags.

List item metadata (titles/IDs may still be private):

```bash
op item list --vault '<your-agent-vault>' --format json
```

Read a needed field **only into the consuming process**, not stdout visible to chat/logs:

```bash
op read 'op://<your-agent-vault>/<item-id>/<field-id>'
```

The command above prints a secret; redirect/capture its output securely in actual use. Prefer `op run` when the consumer can read environment variables.

For creation/editing, obtain the appropriate CLI item template, populate it locally using secure input, then pass it with `op item create --vault ... --template ...` or `op item edit <item-id> --vault ... --template ...`. Capture output, verify only non-secret metadata, and remove temporary files. Consult the [item command reference](https://developer.1password.com/docs/cli/reference/management-commands/item/) for current fields and examples.

After a write, confirm the expected item exists in the correct vault and that the consumer can use it. Never claim a password/TOTP was saved merely because a command exited successfully.
