# Getting started

## Install

=== "From source (development)"

    ```bash
    git clone https://github.com/bruno-laranjo/loki-cli
    cd loki-cli
    make install
    source .venv/bin/activate
    ```

=== "Standalone binary"

    Grab the appropriate artifact from the latest
    [release](https://github.com/bruno-laranjo/loki-cli/releases) and drop it
    on your `$PATH`:

    - `loki-cli-linux-x86_64`
    - `loki-cli-windows-x86_64.exe`

    See [Building binaries](building.md) if you want to build locally.

=== "Docker"

    ```bash
    docker run --rm <user>/loki-cli:latest --help
    ```

    See [Docker & Kubernetes](docker.md).

## First login

```bash
loki-cli login --url https://loki.example.com
# → Verifies the endpoint and saves the profile as `default`.
```

Or use a token:

```bash
loki-cli login --url https://loki.example.com --token "$LOKI_TOKEN"
```

## Explore

```bash
loki-cli labels                 # what labels does the server carry?
loki-cli target --count         # what hosts / sources are shipping logs?
loki-cli logs my-host --since 15m
loki-cli logs my-host -f        # live tail
```

## Multiple environments

```bash
loki-cli config set --profile prod --url https://loki.prod.example.com --token "$T_PROD"
loki-cli config set --profile dev  --url https://loki.dev.example.com  --token "$T_DEV"
loki-cli config use prod
loki-cli --profile dev target --count       # one-off against dev
```

Continue with [Profiles & env vars](configuration.md) for the full precedence
rules.
