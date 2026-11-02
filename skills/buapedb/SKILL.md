---
name: buapedb
description: Fetch short-lived production database credentials for Buape's prod databases (orbit, kiai, ...) with the buapedb CLI, renew or revoke them, and paste them into the dev's database client. Authenticates through Buape Auth SSO, so no long-lived DB credentials are ever stored. Use when the user asks to access, inspect, query, seed, or debug a Buape prod/staging database, or wants DB credentials. Authenticates through Buape Auth SSO, so no long-lived DB credentials are ever stored. Use when the user asks to access, inspect, query, seed, or debug a Buape prod/staging database, or wants DB credentials.
---

# buapedb — short-lived DB credentials at Buape

Buape's prod databases do not accept shared passwords. `buapedb` mints a
unique, short-lived Postgres user for the requested role, gated by Buape Auth
(SSO) group membership. The credential dies with its lease, so nothing
long-lived ends up in a DB client.

Databases are discovered from OpenBao at runtime — new databases appear
without updating this skill. `buapedb list` shows everything currently
available (orbit and kiai at the time of writing).

## Install

```bash
curl -fsSL https://raw.githubusercontent.com/buape/catty-templates/main/skills/buapedb/buapedb | sudo tee /usr/local/bin/buapedb >/dev/null && sudo chmod +x /usr/local/bin/buapedb
brew install openbao jq
```

Cluster endpoint is `https://bao.b1.buape.com` (override with `BAO_ADDR` if
it moves).

## Usage

```bash
buapedb kiai          # read-only creds (sensible default)
buapedb orbit --write # read-write, only if Buape Auth groups allow it
buapedb list          # live inventory: every advertised mount and role
buapedb --renew <id>  # extend one of your credentials (+1h)
buapedb --end         # revoke every credential minted from this machine
```

`--renew`/`--end` are per-machine: lease ids are tracked in `~/.buapedb/leases`
when credentials are minted here. `--end` drops those DB users immediately
(anything still connected through them dies).

Flow: if no token is held, a browser window opens for Buape Auth login; then
a username prints and the password lands on the clipboard. Paste both into
the DB client (TablePlus etc.). It is an ordinary username/password
connection — the only speciality is that expiry deletes the user
automatically.

## Operating rules

- Saved DB-client connections are expected to break: the credential expired.
  Re-run `buapedb` and paste the fresh password; that is not an outage.
- Never persist the password anywhere other than the client's own connection
  cache — it is revoked with the lease regardless.
- Every credential request is attributed to your identity; treat prod access
  accordingly.
- "no database credentials match" means a missing Buape Auth group or an
  unknown role — `buapedb list` settles which. Escalate access requests
  through the infra channel in Buape Auth rather than working around them.
- Do not attempt to bypass expiration by reusing old credentials or sharing
  fetched ones; each mint is per-identity and audited.