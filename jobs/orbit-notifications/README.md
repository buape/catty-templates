# Orbit notifications job

Give this folder to your agent and ask it to adapt it into `<your-workspace>/jobs/orbit-notifications/`. It uses Catty's built-in MCP tools directly, with no Python helper or separate MCP authentication files.

Before enabling:

1. Connect your Orbit server through Catty's built-in MCP support (`mcpServers` in the workspace's `.pi/mcp.json`). Authenticate as the agent's own account and verify access to the intended organization. Keep credentials outside this folder.
2. Replace the MCP server name, organization, agent identity and operator alert destination placeholders in `prompt.md`. Have the agent discover and inspect the live notification/issue/comment tools through built-in `mcp` before use.
3. Adapt status names, repository workflows and authorization policies to your workspace. This template grants no merge/release authority.
4. Read the prompt before the first run: it dismisses noise/self-authored notifications and may reply to or act on actionable notifications. Verify the intended account and organization first, then set `enabled = true` in `meta.toml`.

Catty runs the agent every five minutes to query notifications via MCP. There is deliberately no shell pre-check or context helper. `.state/` is created locally for completion and alert dedupe; do not share it. Final job responses are logged, not automatically sent to Discord.
