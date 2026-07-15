"""`loki-cli config` — manage named profiles."""

from __future__ import annotations

import json as _json
from typing import Optional
from urllib.parse import urlparse

import click

from loki_cli.client import LokiError, verify_connection
from loki_cli.config import (
    DEFAULT_CONFIG_PATH,
    DEFAULT_PROFILE_NAME,
    AuthConfig,
    Config,
    load_store,
    save_store,
)


def _validate_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise click.BadParameter(
            "URL must be an http(s) URL, e.g. https://loki.example.com"
        )
    return url.rstrip("/")


def _emit(
    payload,
    output: str,
    table_headers: Optional[list[str]] = None,
    table_rows: Optional[list[list[str]]] = None,
) -> None:
    """Emit ``payload`` as JSON or as an aligned text table."""
    if output == "json":
        click.echo(_json.dumps(payload, indent=2, sort_keys=False))
        return
    if table_headers is None or table_rows is None:
        # Fall back to JSON if the caller didn't supply table data
        click.echo(_json.dumps(payload, indent=2, sort_keys=False))
        return
    widths = [len(h) for h in table_headers]
    for row in table_rows:
        for i, cell in enumerate(row):
            widths[i] = max(widths[i], len(cell))
    fmt = "  ".join(f"{{:<{w}}}" for w in widths)
    click.echo(fmt.format(*table_headers))
    click.echo(fmt.format(*["-" * w for w in widths]))
    for row in table_rows:
        click.echo(fmt.format(*row))


@click.group("config")
def config_group() -> None:
    """Manage named connection profiles."""


@config_group.command("set")
@click.option(
    "--profile",
    "-p",
    "profile",
    default=DEFAULT_PROFILE_NAME,
    show_default=True,
    help="Name of the profile to create or update.",
)
@click.option("--url", required=True, help="Loki base URL, e.g. https://loki.example.com.")
@click.option("-u", "--username", default=None, help="HTTP basic auth username.")
@click.option("--password", default=None, help="HTTP basic auth password (prompted if omitted).")
@click.option("--token", default=None, help="Bearer token / API key.")
@click.option("--org-id", default=None, help="Tenant ID sent as X-Scope-OrgID.")
@click.option("--tls-skip-verify", is_flag=True, default=False, help="Disable TLS verification.")
@click.option(
    "--no-verify",
    "skip_verify_login",
    is_flag=True,
    default=False,
    help="Skip live connection check.",
)
@click.option(
    "--activate/--no-activate",
    default=True,
    show_default=True,
    help="Set this profile as the active one after saving.",
)
def config_set(
    profile: str,
    url: str,
    username: Optional[str],
    password: Optional[str],
    token: Optional[str],
    org_id: Optional[str],
    tls_skip_verify: bool,
    skip_verify_login: bool,
    activate: bool,
) -> None:
    """Create or update a named profile."""
    url = _validate_url(url)
    if token and username:
        raise click.UsageError("Use either --token or --username, not both.")

    if token:
        auth = AuthConfig(type="bearer", token=token)
    elif username:
        if password is None:
            password = click.prompt("Password", hide_input=True, confirmation_prompt=False)
        auth = AuthConfig(type="basic", username=username, password=password)
    else:
        auth = AuthConfig(type="none")

    cfg = Config(url=url, org_id=org_id, tls_skip_verify=tls_skip_verify, auth=auth)

    if not skip_verify_login:
        click.echo(f"Verifying connection to {url} ...", err=True)
        try:
            status = verify_connection(cfg)
        except LokiError as exc:
            raise click.ClickException(str(exc)) from exc
        click.echo(f"  {status}", err=True)

    store = load_store()
    store.upsert(profile, cfg)
    if activate or not store.active or store.active not in store.profiles:
        store.active = profile
    path = save_store(store)
    click.echo(f"Saved profile '{profile}' to {path}")
    if store.active == profile:
        click.echo(f"Active profile is now '{profile}'.")


@config_group.command("unset")
@click.argument("profile")
def config_unset(profile: str) -> None:
    """Remove a named profile."""
    store = load_store()
    if profile not in store.profiles:
        raise click.ClickException(f"No such profile: '{profile}'")
    del store.profiles[profile]
    if store.active == profile:
        store.active = next(iter(store.profiles), DEFAULT_PROFILE_NAME)
    save_store(store)
    click.echo(f"Removed profile '{profile}'.")


@config_group.command("list")
@click.option(
    "-o", "--output",
    type=click.Choice(["table", "json"]),
    default="table",
    show_default=True,
)
def config_list(output: str) -> None:
    """List all configured profiles."""
    store = load_store()
    payload = {
        "active": store.active,
        "profiles": [
            {
                "name": name,
                "active": name == store.active,
                "url": cfg.url,
                "auth": cfg.auth.type,
                "org_id": cfg.org_id,
            }
            for name, cfg in store.profiles.items()
        ],
    }
    headers = ["ACTIVE", "NAME", "URL", "AUTH", "ORG-ID"]
    rows = [
        [
            "*" if p["active"] else " ",
            p["name"],
            p["url"] or "",
            p["auth"] or "",
            p["org_id"] or "",
        ]
        for p in payload["profiles"]
    ]
    if not rows and output == "table":
        click.echo("(no profiles configured; run `loki-cli config set --url ...`)")
        return
    _emit(payload, output, headers, rows)


@config_group.command("show")
@click.option("--profile", "-p", default=None, help="Profile to show (default: active).")
@click.option(
    "-o", "--output",
    type=click.Choice(["table", "json"]),
    default="table",
    show_default=True,
)
def config_show(profile: Optional[str], output: str) -> None:
    """Show the resolved settings for a profile (secrets redacted)."""
    store = load_store()
    name = profile or store.active
    if name not in store.profiles:
        raise click.ClickException(f"No such profile: '{name}'")
    cfg = store.profiles[name]
    redacted = cfg.auth.redacted()
    payload = {
        "name": name,
        "active": name == store.active,
        "url": cfg.url,
        "org_id": cfg.org_id,
        "tls_skip_verify": cfg.tls_skip_verify,
        "auth": {
            "type": redacted.type,
            "username": redacted.username,
            "password": redacted.password,
            "token": redacted.token,
        },
    }
    headers = ["KEY", "VALUE"]
    rows = [
        ["name", name],
        ["active", "yes" if payload["active"] else "no"],
        ["url", cfg.url or ""],
        ["org_id", cfg.org_id or ""],
        ["tls_skip_verify", str(cfg.tls_skip_verify).lower()],
        ["auth.type", redacted.type],
        ["auth.username", redacted.username or ""],
        ["auth.password", redacted.password or ""],
        ["auth.token", redacted.token or ""],
    ]
    _emit(payload, output, headers, rows)


@config_group.command("use")
@click.argument("profile")
def config_use(profile: str) -> None:
    """Set the active profile."""
    store = load_store()
    if profile not in store.profiles:
        raise click.ClickException(f"No such profile: '{profile}'")
    store.active = profile
    save_store(store)
    click.echo(f"Active profile is now '{profile}'.")


@config_group.command("current")
def config_current() -> None:
    """Print the name of the active profile."""
    store = load_store()
    if not store.profiles:
        click.echo("(no profiles configured)")
        return
    click.echo(store.active)


@config_group.command("path")
def config_path() -> None:
    """Print the config file path."""
    click.echo(str(DEFAULT_CONFIG_PATH))
