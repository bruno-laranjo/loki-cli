"""Backward-compatible login/logout/whoami aliases over the profile system."""

from __future__ import annotations

from typing import Optional
from urllib.parse import urlparse

import click

from loki_cli.client import LokiError, verify_connection
from loki_cli.config import (
    DEFAULT_PROFILE_NAME,
    AuthConfig,
    Config,
    load_store,
    resolve_config,
    resolved_profile_name,
    save_store,
)


def _validate_url(url: str) -> str:
    parsed = urlparse(url)
    if parsed.scheme not in ("http", "https") or not parsed.netloc:
        raise click.BadParameter(
            "URL must be an http(s) URL, e.g. https://loki.example.com"
        )
    return url.rstrip("/")


@click.command("login")
@click.option(
    "--profile",
    "-p",
    default=DEFAULT_PROFILE_NAME,
    show_default=True,
    help="Profile to create or update.",
)
@click.option("--url", required=True, help="Base URL of the Loki instance.")
@click.option("-u", "--username", default=None, help="HTTP basic auth username.")
@click.option("--password", default=None, help="Password (prompted if omitted).")
@click.option("--token", default=None, help="Bearer token / API key.")
@click.option("--org-id", default=None, help="Tenant ID (X-Scope-OrgID).")
@click.option("--tls-skip-verify", is_flag=True, default=False, help="Skip TLS verification.")
@click.option(
    "--no-verify",
    "skip_verify_login",
    is_flag=True,
    default=False,
    help="Skip live connection check.",
)
def login_command(
    profile: str,
    url: str,
    username: Optional[str],
    password: Optional[str],
    token: Optional[str],
    org_id: Optional[str],
    tls_skip_verify: bool,
    skip_verify_login: bool,
) -> None:
    """Log in to a Loki instance and save it as a profile.

    Equivalent to `loki-cli config set --profile <profile> --url ...` with
    `--activate`.
    """
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
    store.active = profile
    path = save_store(store)
    click.echo(f"Saved profile '{profile}' to {path}")


@click.command("logout")
@click.option("--profile", "-p", default=None, help="Profile to remove (default: active).")
def logout_command(profile: Optional[str]) -> None:
    """Delete a saved profile."""
    store = load_store()
    name = profile or store.active
    if name not in store.profiles:
        click.echo(f"No profile '{name}' to remove.")
        return
    del store.profiles[name]
    if store.active == name:
        store.active = next(iter(store.profiles), DEFAULT_PROFILE_NAME)
    save_store(store)
    click.echo(f"Removed profile '{name}'.")


@click.command("whoami")
@click.pass_context
def whoami_command(ctx: click.Context) -> None:
    """Show the currently active profile and endpoint."""
    profile = ctx.obj.get("profile") if ctx.obj else None
    cfg = resolve_config(profile)
    name = resolved_profile_name(profile)
    if not cfg.url:
        click.echo(
            "Not logged in. Run `loki-cli login --url <URL>` or "
            "`loki-cli config set --url <URL>`."
        )
        return
    click.echo(f"profile: {name}")
    click.echo(f"url:     {cfg.url}")
    click.echo(f"auth:    {cfg.auth.type}")
    if cfg.auth.type == "basic":
        click.echo(f"user:    {cfg.auth.username}")
    if cfg.org_id:
        click.echo(f"org-id:  {cfg.org_id}")
    if cfg.tls_skip_verify:
        click.echo("tls:     verify=OFF (insecure)")
