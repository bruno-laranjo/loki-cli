# `labels`

List every label name known to the Loki instance.

```
loki-cli labels [--since DURATION] [-o text|json]
```

| Option | Description |
|---|---|
| `--since DURATION` | Only consider streams active within the window (`15m`, `1h`, `24h`, `7d`, …). Omit to use the server default. |
| `-o, --output` | `text` (default, one label per line) or `json` (JSON array on stdout). |

Examples:

```bash
loki-cli labels
loki-cli labels --since 15m
loki-cli labels -o json | jq
```
