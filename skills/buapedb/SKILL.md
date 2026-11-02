---
name: buapedb
description: Fetch short-lived production database credentials for the named project database with the buapedb CLI, and paste them into a DB client like TablePlus. Authenticate through SSO, never store long-lived DB credentials. Use when the user asks to access, inspect, seed, or debug a prod/staging database, or wants DB credentials.
---

# buapedb — short-lived DB credentials

Buape's prod databases do not accept shared passwords. `buapedb` mints a
unique, short-lived Postgres user for the requested role, gated by your SSO
group membership. The credential dies with its lease, so nothing long-lived
ends up in a DB client.

## Customize once

- `BAO_ADDR` (default `https://bao.b1.buape.com`) — override via env if the
  OpenBao cluster is deployed elsewhere.
- Databases and roles are discovered from OpenBao at runtime; nothing to
  update when a new database is added.
- Install OpenBao CLI: `brew install openbao` (+ `jq`; macOS clipboard needs
  nothing extra).

## Install

```bash
gh api repos/buape/catty-templates/contents/skills/buapedb/buapedb --jq '.content' | sudo base64 -d | sudo tee /usr/local/bin/buapedb >/dev/null && sudo chmod +x /usr/local/bin/buapedb
```

## Usage

```bash
buapedb kiai          # read-only creds (sensible default)
buapedb orbit --write # read-write, only if SSO groups allow it
buapedb list          # live inventory: every advertised mount and role
```

Flow: if no token is held, a browser window opens for SSO login; then a
username prints and the password lands on the clipboard. Paste both into the
DB client (TablePlus etc.). It's an ordinary username/password connection —
the only speciality is that expiry deletes the user automatically.

## Operating rules

- Saved DB-client connections are expected to break: the credential expired.
  Re-run `buapedb` and paste the fresh password; that is not an outage.
- Never persist the password anywhere other than the client's own connection
  cache — it is revoked with the lease regardless.
- Every credential request is attributed to your identity; treat prod access
  accordingly.
- "no database credentials match" means a missing SSO group or an unknown
  role — `buapedb list` settles which. Escalate access requests to an
  operator rather than working around them.
- Do not attempt to bypass expiration by reusing old credentials or sharing
  fetched ones; each mint is per-identity and audited.