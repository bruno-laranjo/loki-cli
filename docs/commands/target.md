# `target`

List targets — the distinct values of a host-identifying label.

```
loki-cli target [--label NAME] [--since DURATION] [--count] [-o text|json]
```

| Option | Description |
|---|---|
| `--label NAME` | Force a specific label. If omitted, the CLI picks the first of `host`, `hostname`, `instance`, `node`, `nodename` present on the server. The chosen label is echoed to stderr. |
| `--since DURATION` | Only consider streams active within the window. |
| `--count` | Print `# <N> target(s)` to stderr. |
| `-o, --output` | `text` (default) or `json` (`{"label": ..., "values": [...]}`) |

**Exit code:** `1` when the label has no values.

Examples:

```bash
loki-cli target                        # all targets
loki-cli target --since 15m --count    # only recent
loki-cli target --label instance       # different label
loki-cli target -o json | jq '.values | length'
```
