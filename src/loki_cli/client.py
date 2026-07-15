"""Thin HTTP client for the Grafana Loki HTTP API."""

from __future__ import annotations

from typing import Optional

import httpx

from loki_cli.config import Config

USER_AGENT = "loki-cli/0.1.0"


class LokiError(Exception):
    """Raised for non-2xx responses or connectivity failures."""


def _auth_and_headers(config: Config) -> tuple[Optional[httpx.Auth], dict[str, str]]:
    headers: dict[str, str] = {"User-Agent": USER_AGENT}
    if config.org_id:
        headers["X-Scope-OrgID"] = config.org_id

    auth: Optional[httpx.Auth] = None
    if config.auth.type == "basic":
        if not config.auth.username:
            raise LokiError("Basic auth requires a username.")
        auth = httpx.BasicAuth(config.auth.username, config.auth.password or "")
    elif config.auth.type == "bearer":
        if not config.auth.token:
            raise LokiError("Bearer auth requires a token.")
        headers["Authorization"] = f"Bearer {config.auth.token}"
    return auth, headers


def build_client(config: Config, timeout: float = 15.0) -> httpx.Client:
    if not config.url:
        raise LokiError("No Loki URL configured. Run `loki-cli login` first.")
    auth, headers = _auth_and_headers(config)
    return httpx.Client(
        base_url=config.url.rstrip("/"),
        auth=auth,
        headers=headers,
        timeout=timeout,
        verify=not config.tls_skip_verify,
        follow_redirects=True,
    )


def verify_connection(config: Config) -> str:
    """Verify Loki reachability and credentials.

    Hits ``/loki/api/v1/labels`` because it exercises the auth path (unlike
    ``/ready``, which is often unauthenticated). Returns a short status string.
    Raises :class:`LokiError` on any failure.
    """
    try:
        with build_client(config) as client:
            resp = client.get("/loki/api/v1/labels", params={"limit": 1})
    except httpx.HTTPError as exc:
        raise LokiError(f"Could not reach Loki at {config.url}: {exc}") from exc

    if resp.status_code == 401:
        raise LokiError("Authentication failed (HTTP 401). Check your credentials.")
    if resp.status_code == 403:
        raise LokiError("Access denied (HTTP 403). Check tenant/org-id and permissions.")
    if resp.status_code >= 400:
        raise LokiError(
            f"Loki returned HTTP {resp.status_code}: {resp.text[:200]}"
        )

    try:
        data = resp.json()
    except ValueError:
        return "connected (non-JSON response)"

    status = data.get("status", "unknown")
    labels = data.get("data") or []
    return f"connected (status={status}, labels_seen={len(labels)})"
