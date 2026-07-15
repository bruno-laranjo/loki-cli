# `login` / `logout` / `whoami`

These are convenience wrappers over `config set/unset/current`. They exist
because "log in / log out" reads naturally when you're only using one Loki
instance.

## `login`

```
loki-cli login --url URL
               [--profile NAME]
               [-u USER | --token TOKEN] [--password PASS]
               [--org-id TENANT] [--tls-skip-verify] [--no-verify]
```

The named profile (default `default`) is created/updated **and set as
active**. Live connection check is performed unless `--no-verify` is passed.

Examples:

```bash
loki-cli login --url http://localhost:3100                           # anonymous
loki-cli login --url https://loki.example.com --username alice       # basic
loki-cli login --url https://loki.example.com --token "$LOKI_TOKEN"  # bearer
loki-cli login --profile prod --url https://loki.prod.example.com --token "$T"
```

## `logout`

```
loki-cli logout [--profile NAME]
```

Removes the named profile (default: currently active). If you delete the
active profile, the CLI picks another one at random to activate, or falls
back to `default`.

## `whoami`

```bash
loki-cli whoami
```

Shows the resolved profile / URL / auth mode. Example output:

```
profile: prod
url:     https://loki.prod.example.com
auth:    bearer
org-id:  team-a
```
