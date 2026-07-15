# loki-cli

A small `logcli`-style command-line tool for querying
[Grafana Loki](https://grafana.com/oss/loki/).

- Named profiles (`~/.config/loki-cli/config.json`) with an active pointer
- `LOKI_*` environment-variable overrides
- Pipe-friendly output (stdout = data, stderr = diagnostics, `SIGPIPE` handled)
- Shell tab-completion for target names
- Single-file binaries for Linux & Windows (built in CI)
- Docker image usable in Kubernetes `Job` / `CronJob`

Full documentation: **<https://bruno-laranjo.github.io/loki-cli/>**

---

## Install

```bash
git clone https://github.com/bruno-laranjo/loki-cli
cd loki-cli
make install
source .venv/bin/activate
loki-cli --help
```

Prebuilt binaries and Docker images are attached to each GitHub Release.

## Quick start

```bash
loki-cli login --url https://loki.example.com          # or --token / --username
loki-cli labels
loki-cli target --count
loki-cli logs my-host --since 15m
loki-cli logs my-host -f                                # live tail
```

Manage several endpoints with profiles:

```bash
loki-cli config set --profile prod --url https://loki.prod --token "$TP"
loki-cli config set --profile dev  --url https://loki.dev  --token "$TD"
loki-cli config use prod
loki-cli --profile dev target --count                   # one-off override
```

Override anything via env for scripts / CI:

```bash
LOKI_URL=https://loki.example.com LOKI_TOKEN=... loki-cli target --count
```

See [`.env.example`](.env.example) for all variables and precedence rules.

## Commands

| Command | Purpose |
|---|---|
| [`config`](https://bruno-laranjo.github.io/loki-cli/commands/config/) | `set`, `unset`, `list`, `show`, `use`, `current`, `path` |
| [`login` / `logout` / `whoami`](https://bruno-laranjo.github.io/loki-cli/commands/login/) | Convenience wrappers over `config` |
| [`labels`](https://bruno-laranjo.github.io/loki-cli/commands/labels/) | List label names |
| [`target`](https://bruno-laranjo.github.io/loki-cli/commands/target/) | List targets (values of a host-identifying label) |
| [`logs`](https://bruno-laranjo.github.io/loki-cli/commands/logs/) | Print or stream logs from a specific target |

Every command accepts `-p / --profile NAME` (falls back to `$LOKI_PROFILE`,
then the active profile). Every data command supports `-o text|json`
where sensible; `logs` also supports `-o raw`.

## Shell completion

```bash
eval "$(_LOKI_CLI_COMPLETE=bash_source loki-cli)"     # bash
eval "$(_LOKI_CLI_COMPLETE=zsh_source loki-cli)"      # zsh
_LOKI_CLI_COMPLETE=fish_source loki-cli > ~/.config/fish/completions/loki-cli.fish
```

Then `loki-cli logs <TAB>` completes with your Loki targets (60 s cache).

## Development

```bash
make install       # editable install with dev+build+docs extras
make lint          # ruff
make fmt           # ruff --fix + format
make test          # pytest
make build-binary  # PyInstaller single-file exe → dist/
make docs          # preview MkDocs site
make docker        # build loki-cli:local image
```

## Cross-platform binaries

PyInstaller can't cross-compile, so:

- Locally on your OS: `make build-binary`
- For Windows without a Windows box: push a `v*` tag; the CI workflow
  publishes both `loki-cli-linux-x86_64` and `loki-cli-windows-x86_64.exe`
  as GitHub Release assets.

See [Building binaries](https://bruno-laranjo.github.io/loki-cli/building/).

## Docker

```bash
docker pull <user>/loki-cli:latest
docker run --rm -e LOKI_URL=https://loki.example.com <user>/loki-cli:latest target --count
```

Or build locally: `make docker`. See
[Docker & Kubernetes](https://bruno-laranjo.github.io/loki-cli/docker/) for the
image tag scheme and how to enable the Docker Hub pipeline (set
`DOCKERHUB_USERNAME` and `DOCKERHUB_TOKEN` in repo secrets).

## License

MIT — see [LICENSE](LICENSE).
