"""`loki-cli logs HOST` — print or stream logs from a specific host."""

from __future__ import annotations

import json
import os
import sys
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Optional

import click
import httpx

from loki_cli.client import LokiError, build_client
from loki_cli.commands.labels import (
    HOST_LABEL_CANDIDATES,
    _fetch_label_names,
    _fetch_label_values,
    _parse_duration,
)
from loki_cli.config import resolve_config

# Loki's server-side max per request; we paginate above this.
MAX_LIMIT_PER_REQUEST = 5000

# Shell-completion cache: keep the target list on disk briefly so multiple TAB
# presses don't spam Loki. Location follows XDG cache spec.
_COMPLETION_CACHE_TTL_SECONDS = 60
_COMPLETION_HTTP_TIMEOUT = 3.0


def _completion_cache_path() -> Path:
    base = os.environ.get("XDG_CACHE_HOME") or str(Path.home() / ".cache")
    return Path(base) / "loki-cli" / "targets.txt"


def _read_cached_targets() -> Optional[list[str]]:
    path = _completion_cache_path()
    try:
        stat = path.stat()
    except OSError:
        return None
    if time.time() - stat.st_mtime > _COMPLETION_CACHE_TTL_SECONDS:
        return None
    try:
        return path.read_text(encoding="utf-8").splitlines()
    except OSError:
        return None


def _write_cached_targets(values: list[str]) -> None:
    path = _completion_cache_path()
    try:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text("\n".join(values), encoding="utf-8")
    except OSError:
        pass  # cache is best-effort


def _fetch_targets_for_completion() -> list[str]:
    """Return target values quickly and silently for shell completion.

    Any failure returns an empty list so tab-completion never surfaces errors.
    """
    cached = _read_cached_targets()
    if cached is not None:
        return cached

    try:
        config = resolve_config()
        if not config.url:
            return []
        with build_client(config, timeout=_COMPLETION_HTTP_TIMEOUT) as client:
            names = set(_fetch_label_names(client, {}))
            label = next((c for c in HOST_LABEL_CANDIDATES if c in names), None)
            if label is None:
                return []
            values = _fetch_label_values(client, label, {})
    except Exception:
        return []

    values = sorted(values)
    _write_cached_targets(values)
    return values


def _complete_target(
    ctx: click.Context, param: click.Parameter, incomplete: str
) -> list[str]:
    """Click shell-completion callback for the TARGET positional."""
    try:
        values = _fetch_targets_for_completion()
    except Exception:
        return []
    if not incomplete:
        return values
    return [v for v in values if v.startswith(incomplete)]


def _now_ns() -> int:
    return time.time_ns()


def _fmt_ts(ns: int) -> str:
    # Microsecond ISO 8601 in UTC (nanoseconds truncated).
    dt = datetime.fromtimestamp(ns / 1_000_000_000, tz=timezone.utc)
    return dt.strftime("%Y-%m-%dT%H:%M:%S.%fZ")


def _logql_escape(value: str) -> str:
    return value.replace("\\", "\\\\").replace('"', '\\"')


def _build_selector(label: str, host: str, filters: tuple[str, ...]) -> str:
    query = f'{{{label}="{_logql_escape(host)}"}}'
    for f in filters:
        query += f' |= "{_logql_escape(f)}"'
    return query


def _print_entries(entries: list[tuple[int, str, dict]], output: str) -> None:
    """Write entries to stdout. Caller is responsible for chronological order."""
    out = sys.stdout
    if output == "raw":
        for _ts, line, _labels in entries:
            out.write(line)
            out.write("\n")
    elif output == "json":
        for ts, line, labels in entries:
            out.write(
                json.dumps(
                    {"ts": _fmt_ts(ts), "line": line, "labels": labels},
                    ensure_ascii=False,
                )
            )
            out.write("\n")
    else:  # "text" — default
        for ts, line, _labels in entries:
            out.write(_fmt_ts(ts))
            out.write("  ")
            out.write(line)
            out.write("\n")
    out.flush()


def _query_range(
    client: httpx.Client,
    query: str,
    start_ns: int,
    end_ns: int,
    limit: int,
    direction: str = "forward",
) -> list[tuple[int, str, dict]]:
    resp = client.get(
        "/loki/api/v1/query_range",
        params={
            "query": query,
            "start": str(start_ns),
            "end": str(end_ns),
            "limit": str(limit),
            "direction": direction,
        },
    )
    if resp.status_code >= 400:
        raise LokiError(f"Loki returned HTTP {resp.status_code}: {resp.text[:300]}")
    data = resp.json().get("data") or {}
    if data.get("resultType") != "streams":
        return []
    entries: list[tuple[int, str, dict]] = []
    for stream in data.get("result", []):
        labels = stream.get("stream", {})
        for ts_str, line in stream.get("values", []):
            entries.append((int(ts_str), line, labels))
    entries.sort(key=lambda e: e[0])
    return entries


def _fetch_range_paginated(
    client: httpx.Client,
    query: str,
    start_ns: int,
    end_ns: int,
    limit: int,
    output: str,
) -> Optional[int]:
    """Fetch [start_ns, end_ns] in forward-order chunks, printing as we go.

    Returns the timestamp of the last entry printed, or None if nothing matched.
    """
    last_ts: Optional[int] = None
    total = 0
    cursor = start_ns
    while cursor <= end_ns:
        entries = _query_range(client, query, cursor, end_ns, limit, "forward")
        if not entries:
            break
        _print_entries(entries, output)
        total += len(entries)
        last_ts = entries[-1][0]
        # If we got fewer than the batch limit, we've drained the window.
        if len(entries) < limit:
            break
        # Advance past the last-returned nanosecond to avoid re-fetching it.
        cursor = last_ts + 1
    if total:
        click.echo(f"# fetched {total} line(s)", err=True)
    return last_ts


def _follow(
    client: httpx.Client,
    query: str,
    since_ns: int,
    limit: int,
    interval: float,
    output: str,
) -> None:
    """Poll query_range for new entries until interrupted."""
    click.echo(
        f"# following (poll every {interval:g}s, Ctrl+C to stop)", err=True
    )
    last_ts = since_ns - 1  # inclusive lower bound below
    try:
        while True:
            time.sleep(interval)
            now_ns = _now_ns()
            start = last_ts + 1
            if start > now_ns:
                continue
            try:
                entries = _query_range(client, query, start, now_ns, limit, "forward")
            except LokiError as exc:
                click.echo(f"# poll error: {exc}", err=True)
                continue
            if entries:
                _print_entries(entries, output)
                last_ts = entries[-1][0]
            else:
                # No new lines; move cursor forward so the next query window is small.
                last_ts = now_ns
    except KeyboardInterrupt:
        click.echo("# stopped", err=True)


@click.command("logs")
@click.argument("host", shell_complete=_complete_target)
@click.option(
    "--label",
    default=None,
    help=(
        "Label that identifies the host. "
        f"Auto-detected from {', '.join(HOST_LABEL_CANDIDATES)} if omitted."
    ),
)
@click.option(
    "--since",
    default="1h",
    show_default=True,
    help="Look back this far for historical logs, e.g. 15m, 1h, 24h, 7d.",
)
@click.option(
    "-f", "--follow",
    is_flag=True,
    default=False,
    help="After printing history, keep streaming new lines (polling).",
)
@click.option(
    "--filter",
    "filters",
    multiple=True,
    help="Substring filter (repeatable). Adds `|= \"<text>\"` to the LogQL query.",
)
@click.option(
    "--limit",
    default=1000,
    show_default=True,
    type=click.IntRange(1, MAX_LIMIT_PER_REQUEST),
    help="Max entries per HTTP request (pagination handled automatically).",
)
@click.option(
    "--interval",
    default=2.0,
    show_default=True,
    type=click.FloatRange(0.2, 60.0),
    help="Poll interval in seconds for --follow.",
)
@click.option(
    "-o", "--output",
    type=click.Choice(["text", "raw", "json"]),
    default="text",
    show_default=True,
    help="Output format. Use `raw` to print only the log line (best for pipes).",
)
@click.pass_context
def logs_command(
    ctx: click.Context,
    host: str,
    label: Optional[str],
    since: str,
    follow: bool,
    filters: tuple[str, ...],
    limit: int,
    interval: float,
    output: str,
) -> None:
    """Print logs from HOST. Use -f to stream new lines as they arrive.

    Examples:

      loki-cli logs my-host-01
      loki-cli logs my-host-01 --since 15m -o raw | grep -i error
      loki-cli logs my-host-01 -f --filter warn
      loki-cli logs my-host-01 -o json | jq -r .line
    """
    config = resolve_config(ctx.obj.get("profile") if ctx.obj else None)

    try:
        delta = _parse_duration(since)
    except click.BadParameter:
        raise

    try:
        with build_client(config) as client:
            if label is None:
                names = set(_fetch_label_names(client, {}))
                label = next((c for c in HOST_LABEL_CANDIDATES if c in names), None)
                if label is None:
                    raise click.ClickException(
                        "Could not auto-detect a host label; use --label."
                    )
                click.echo(f"# using label: {label}", err=True)

            query = _build_selector(label, host, filters)
            click.echo(f"# query: {query}", err=True)

            end_ns = _now_ns()
            start_ns = end_ns - int(delta.total_seconds() * 1_000_000_000)

            last_ts = _fetch_range_paginated(
                client, query, start_ns, end_ns, limit, output
            )

            if follow:
                resume_from = last_ts if last_ts is not None else end_ns
                _follow(client, query, resume_from, limit, interval, output)
    except LokiError as exc:
        raise click.ClickException(str(exc)) from exc
    except BrokenPipeError:
        # Downstream pipe closed (e.g. `| head`). Exit quietly.
        try:
            sys.stdout.close()
        except Exception:
            pass
