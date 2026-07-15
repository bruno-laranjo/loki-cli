# loki-cli

A small `logcli`-style command-line tool for querying
[Grafana Loki](https://grafana.com/oss/loki/).

## Feature snapshot

| Command | Purpose |
|---|---|
| `config` | Manage named connection profiles (`set`, `show`, `list`, `use`, `current`, `unset`, `path`) |
| `login` / `logout` / `whoami` | Convenience wrappers over `config` |
| `labels` | List all label names known to the server |
| `target` | List targets (values of a host-identifying label) |
| `logs` | Print or stream logs from a specific target |

Plus:

- **Named profiles** stored at `~/.config/loki-cli/config.json`
- **Environment variable overrides** (`LOKI_URL`, `LOKI_TOKEN`, …)
- **Pipe-friendly output**: data on stdout, diagnostics on stderr, `SIGPIPE` handled
- **Shell tab completion** with a 60-second target cache
- **Cross-platform binaries** via PyInstaller (CI-built for Linux + Windows)
- **Docker image** for use in Kubernetes `Job` / `CronJob`

Continue with the [Getting started](getting-started.md) guide.
