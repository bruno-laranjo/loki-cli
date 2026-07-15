"""`loki-cli labels` and `loki-cli target` — discovery commands."""

from __future__ import annotations

import json as _json
import re
import sys
from datetime import datetime, timedelta, timezone
from typing import Optional

import click

from loki_cli.client import LokiError, build_client
from loki_cli.config import resolve_config

# Ordered preference when the user does not specify --label.
HOST_LABEL_CANDIDATES = ("host", "hostname", "instance", "node", "nodename")

_DURATION_RE = re.compile(r"^\s*(\d+)\s*([smhdw])\s*$")
_DURATION_UNITS = {
    "s": 1,
    "m": 60,
    "h": 60 * 60,
    "d": 60 * 60 * 24,
    "w": 60 * 60 * 24 * 7,
}


def _parse_duration(value: str) -> timedelta:
    match = _DURATION_RE.match(value.lower())
    if not match:
        raise click.BadParameter(
            f"Invalid duration '{value}'. Use e.g. 30s, 15m, 1h, 7d."
        )
    n, unit = int(match.group(1)), match.group(2)
    return timedelta(seconds=n * _DURATION_UNITS[unit])


def _time_window(since: Optional[str]) -> dict[str, str]:
    """Return start/end query params for a `since` duration, or {} for server default."""
    if not since:
        return {}
    delta = _parse_duration(since)
    end = datetime.now(timezone.utc)
    start = end - delta
    # Loki accepts RFC3339 or nanoseconds; use nanoseconds to avoid tz ambiguity.
    return {
        "start": str(int(start.timestamp() * 1_000_000_000)),
        "end": str(int(end.timestamp() * 1_000_000_000)),
    }


def _fetch_label_names(client, params: dict[str, str]) -> list[str]:
    resp = client.get("/loki/api/v1/labels", params=params)
    if resp.status_code >= 400:
        raise LokiError(f"Loki returned HTTP {resp.status_code}: {resp.text[:200]}")
    return list(resp.json().get("data") or [])


def _fetch_label_values(client, label: str, params: dict[str, str]) -> list[str]:
    resp = client.get(f"/loki/api/v1/label/{label}/values", params=params)
    if resp.status_code == 404:
        return []
    if resp.status_code >= 400:
        raise LokiError(f"Loki returned HTTP {resp.status_code}: {resp.text[:200]}")
    return list(resp.json().get("data") or [])


@click.command("labels")
@click.option("--since", default=None, help="Time window to search, e.g. 1h, 30m, 7d.")
@click.option(
    "-o", "--output",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
)
@click.pass_context
def labels_command(ctx: click.Context, since: Optional[str], output: str) -> None:
    """List all label names known to the Loki instance."""
    config = resolve_config(ctx.obj.get("profile") if ctx.obj else None)
    params = _time_window(since)
    try:
        with build_client(config) as client:
            names = _fetch_label_names(client, params)
    except LokiError as exc:
        raise click.ClickException(str(exc)) from exc

    if output == "json":
        click.echo(_json.dumps(sorted(names)))
        return
    if not names:
        click.echo("(no labels found)")
        return
    for name in sorted(names):
        click.echo(name)


@click.command("target")
@click.option(
    "--label",
    "label",
    default=None,
    help=(
        "Label name that identifies targets. "
        f"Auto-detected from {', '.join(HOST_LABEL_CANDIDATES)} if omitted."
    ),
)
@click.option("--since", default=None, help="Time window to search, e.g. 1h, 30m, 7d.")
@click.option("--count", is_flag=True, help="Print total count as the last line.")
@click.option(
    "-o", "--output",
    type=click.Choice(["text", "json"]),
    default="text",
    show_default=True,
)
@click.pass_context
def target_command(
    ctx: click.Context,
    label: Optional[str],
    since: Optional[str],
    count: bool,
    output: str,
) -> None:
    """List targets (hosts / sources) present in the Loki instance.

    Loki organizes streams by labels; a "target" is a value of a target-identifying
    label (typically `hostname`, `host`, or `instance`). Use `--label` to force
    a specific label.
    """
    config = resolve_config(ctx.obj.get("profile") if ctx.obj else None)
    params = _time_window(since)

    try:
        with build_client(config) as client:
            if label is None:
                names = set(_fetch_label_names(client, params))
                label = next(
                    (c for c in HOST_LABEL_CANDIDATES if c in names),
                    None,
                )
                if label is None:
                    raise click.ClickException(
                        "Could not auto-detect a target label. "
                        f"Tried {', '.join(HOST_LABEL_CANDIDATES)}. "
                        "Use --label to specify one; run `loki-cli labels` to see options."
                    )
                click.echo(f"# using label: {label}", err=True)
            values = _fetch_label_values(client, label, params)
    except LokiError as exc:
        raise click.ClickException(str(exc)) from exc

    values = sorted(values)

    if output == "json":
        click.echo(_json.dumps({"label": label, "values": values}))
    else:
        for v in values:
            click.echo(v)
    if count:
        click.echo(f"# {len(values)} target(s)", err=True)
    if not values:
        click.echo(f"(no values for label '{label}')", err=True)
        sys.exit(1)
