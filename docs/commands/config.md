# `config`

Manage named connection profiles.

## `config set`

Create or update a profile.

```
loki-cli config set --url URL
                    [--profile NAME] [-u USER] [--password PASS]
                    [--token TOKEN] [--org-id TENANT]
                    [--tls-skip-verify] [--no-verify]
                    [--activate/--no-activate]
```

| Option | Description |
|---|---|
| `--profile NAME` | Profile to create/update (default: `default`). |
| `--url URL` *(required)* | Loki base URL. |
| `-u, --username USER` | Enable HTTP basic auth; password prompted. |
| `--password PASS` | Non-interactive password (prefer the prompt). |
| `--token TOKEN` | Bearer token. Mutually exclusive with `--username`. |
| `--org-id TENANT` | Sent as `X-Scope-OrgID`. |
| `--tls-skip-verify` | Disable TLS certificate validation. |
| `--no-verify` | Skip the live-connection sanity check. |
| `--activate / --no-activate` | Whether to switch active to this profile after saving. Default: activate. |

## `config unset`

```bash
loki-cli config unset dev
```

## `config list`

```bash
loki-cli config list                # table (default)
loki-cli config list -o json
```

## `config show`

```bash
loki-cli config show                # active profile, table
loki-cli config show --profile prod -o json
```

Secrets (password, token) are always redacted as `***`.

## `config use`

```bash
loki-cli config use prod
```

## `config current`

```bash
loki-cli config current
# prod
```

## `config path`

```bash
loki-cli config path
# /home/alice/.config/loki-cli/config.json
```
