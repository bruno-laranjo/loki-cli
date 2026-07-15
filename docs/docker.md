# Docker & Kubernetes

## Prebuilt image

Images are published to **Docker Hub** by the `docker` workflow on every
push to `main` and every `v*` tag, for both `linux/amd64` and `linux/arm64`.
Replace `<user>` with the Docker Hub account configured in the repo secrets
(`DOCKERHUB_USERNAME`):

```bash
docker pull <user>/loki-cli:latest        # latest main
docker pull <user>/loki-cli:0.1.0         # a specific release
docker pull <user>/loki-cli:sha-1a2b3c4   # a specific commit
```

Available tag formats:

| Tag | Source |
|---|---|
| `latest` | Latest `main` build |
| `main` | Same as `latest` |
| `v1.2.3` → `1.2.3`, `1.2`, `1`, `latest` | Git tag `v1.2.3` |
| `sha-<short>` | Every build |
| `pr-<N>` | PR builds (built for CI, not pushed) |

### Enabling the pipeline (one-time)

Create two repository secrets under **Settings → Secrets and variables →
Actions**:

- `DOCKERHUB_USERNAME` — your Docker Hub username
- `DOCKERHUB_TOKEN` — an *access token* (create at
  <https://hub.docker.com/settings/security>), **not** your account password

## Build locally

```bash
make docker              # builds `loki-cli:local`
# or:
docker build -t loki-cli:local .
```

## Run one-off commands

```bash
docker run --rm <user>/loki-cli:latest --help
```

Passing env vars is the simplest way to inject credentials, since the
container has no persistent config by default:

```bash
docker run --rm \
  -e LOKI_URL=https://loki.example.com \
  -e LOKI_TOKEN=... \
  <user>/loki-cli:latest target --count
```

## Persist profiles

Mount `~/.config/loki-cli` into the container to reuse your host profiles:

```bash
docker run --rm \
  -v "$HOME/.config/loki-cli:/home/app/.config/loki-cli" \
  loki-cli:local whoami
```

## Kubernetes: on-demand `Job`

```yaml
apiVersion: batch/v1
kind: Job
metadata:
  name: loki-cli-count-targets
spec:
  template:
    spec:
      restartPolicy: Never
      containers:
        - name: loki-cli
          image: <user>/loki-cli:latest
          args: ["target", "--count"]
          env:
            - name: LOKI_URL
              value: https://loki.svc.cluster.local:3100
            - name: LOKI_TOKEN
              valueFrom:
                secretKeyRef: { name: loki-cli, key: token }
```

## Kubernetes: `CronJob` health/summary

```yaml
apiVersion: batch/v1
kind: CronJob
metadata:
  name: loki-cli-hourly-summary
spec:
  schedule: "0 * * * *"
  jobTemplate:
    spec:
      template:
        spec:
          restartPolicy: OnFailure
          containers:
            - name: loki-cli
              image: <user>/loki-cli:latest
              args: ["target", "--since", "1h", "--count"]
              envFrom:
                - secretRef: { name: loki-cli-env }
```

The container image runs as an unprivileged user (`app`) — no additional
`securityContext` is required for a locked-down Pod spec.
