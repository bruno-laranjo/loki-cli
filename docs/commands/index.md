# Commands overview

All commands share these traits:

- **stdout** carries the data; **stderr** carries diagnostics (all `#`-prefixed).
- Pipe-safe: line-buffered stdout, `SIGPIPE` handled cleanly.
- Accept `--profile NAME` (falls back to `$LOKI_PROFILE`, then the active
  profile in the store) at the group level:

  ```bash
  loki-cli --profile prod target
  ```

- Exit codes: `0` on success, `1` on Loki/config errors, `2` on invalid CLI
  arguments.

| Command | Docs |
|---|---|
| `config` | [config](config.md) |
| `login` / `logout` / `whoami` | [login](login.md) |
| `labels` | [labels](labels.md) |
| `target` | [target](target.md) |
| `logs` | [logs](logs.md) |
