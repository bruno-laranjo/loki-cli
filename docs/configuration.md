# Profiles & environment variables

## Named profiles

Profiles let you keep credentials for several Loki instances side by side.
They are stored as JSON at `~/.config/loki-cli/config.json` (respects
`$XDG_CONFIG_HOME`; override entirely with `LOKI_CLI_CONFIG_DIR=/some/dir`).

```json
{
  "active": "prod",
  "profiles": {
    "default": {
      "url": "http://localhost:3100",
      "org_id": null,
      "tls_skip_verify": false,
      "auth": { "type": "none", "username": null, "password": null, "token": null }
    },
    "prod": {
      "url": "https://loki.prod.example.com",
      "org_id": "team-a",
      "tls_skip_verify": false,
      "auth": { "type": "bearer", "username": null, "password": null, "token": "..." }
    }
  }
}
```

The file is written with permissions `0600` (owner read/write only).

### Migration from legacy YAML

If a `config.yaml` from an earlier version is found without a `config.json`
next to it, the CLI transparently migrates its contents into a `default`
profile in the new format and renames the old file to `config.yaml.bak`.

## Environment variables

| Variable | Purpose |
|---|---|
| `LOKI_URL` | Loki base URL |
| `LOKI_ORG_ID` | Tenant ID (sent as `X-Scope-OrgID`) |
| `LOKI_TLS_SKIP_VERIFY` | Truthy (`1`, `true`, `yes`, `on`) disables TLS verification |
| `LOKI_TOKEN` | Bearer token / API key (takes precedence over basic auth) |
| `LOKI_USERNAME` | HTTP basic username |
| `LOKI_PASSWORD` | HTTP basic password |
| `LOKI_PROFILE` | Named profile to use (same as `--profile`) |
| `LOKI_CLI_CONFIG_DIR` | Override the config file directory |
| `XDG_CONFIG_HOME` | Standard XDG override for `~/.config` |

A sample `.env` layout ships with the repo at `.env.example`.

## Precedence

For any given command invocation the effective settings are resolved as:

1. **CLI overrides** (per-command flags such as `--url`, `--token` on
   `login` or `config set`).
2. **Environment variables** (`LOKI_*` above).
3. **Selected profile** (from `--profile NAME`, else `$LOKI_PROFILE`, else
   the store's `active` entry).
4. **Empty defaults** (fields left blank; commands that need them will fail
   with a clear message).

## Switching profiles

```bash
loki-cli config list                 # see everything, active marked with *
loki-cli config current              # print just the active profile name
loki-cli config use dev              # persist a new active profile
loki-cli --profile prod target       # one-off override, doesn't change active
LOKI_PROFILE=prod loki-cli target    # same, via env
```
