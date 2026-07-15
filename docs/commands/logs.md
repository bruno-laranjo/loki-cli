# `logs`

Print or stream logs from a specific target.

```
loki-cli logs TARGET
              [--label NAME]
              [--since DURATION]
              [-f | --follow]
              [--filter TEXT ...]
              [--limit N]
              [--interval SECONDS]
              [-o text|raw|json]
```

The `TARGET` positional supports **shell tab-completion** (see
[Shell completion](../completion.md)).

| Option | Description |
|---|---|
| `TARGET` *(positional)* | Target value to filter on. LogQL-escaped for you. |
| `--label NAME` | Label used to match the target; auto-detected otherwise. |
| `--since DURATION` | How far back to fetch history. Default `1h`. |
| `-f, --follow` | Poll for new lines after the history dump. |
| `--filter TEXT` | Repeatable server-side substring filter (`|=`). |
| `--limit N` | Max entries per HTTP request (1–5000, default 1000). Paginates automatically. |
| `--interval SEC` | Poll interval for `--follow` (0.2–60, default 2). |
| `-o, --output` | `text` (default): `<ISO ts>  <line>`, `raw`: line only, `json`: `{ts, line, labels}` per line. |

## Stderr diagnostics

All prefixed with `#`, so pipes ignore them by default:

- `# using label: <name>` — auto-picked target label
- `# query: {hostname="..."}` — the LogQL that was sent
- `# fetched N line(s)` — historical batch total
- `# following (poll every 2s, Ctrl+C to stop)` — entered follow mode
- `# poll error: ...` — one poll failed (follow continues)
- `# stopped` — Ctrl+C in follow mode

## Behaviour

- History is fetched in chronological order (`direction=forward`).
- Follow mode tracks the last-seen nanosecond timestamp and asks for
  `(last_ts + 1) .. now` each interval, so there are no duplicates and no
  gaps across polls.
- Piping into an early-closing command (e.g. `| head`) exits cleanly.

## Examples

```bash
loki-cli logs my-host-01                              # last 1h, text
loki-cli logs my-host-01 --since 15m -f               # live tail w/ 15m history
loki-cli logs my-host-01 -o raw | grep -i err         # pipe-friendly
loki-cli logs my-host-01 -f --filter error --filter kernel
loki-cli logs my-host-01 -o json | jq -r '.line'
loki-cli --profile prod logs some-host -f            # use a named profile
```
