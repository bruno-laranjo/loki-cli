"""Configuration handling for loki-cli.

Multiple named profiles are stored as JSON at ``~/.config/loki-cli/config.json``.
The file structure is::

    {
      "active": "default",
      "profiles": {
        "default": {
          "url": "https://loki.example.com",
          "org_id": null,
          "tls_skip_verify": false,
          "auth": {
            "type": "bearer",    # none | basic | bearer
            "username": null,
            "password": null,
            "token": "..."
          }
        }
      }
    }

Any legacy single-profile ``config.yaml`` left behind by previous versions is
auto-migrated on first load: its contents become the ``default`` profile in
the new JSON file, and the YAML is renamed to ``config.yaml.bak``.

Environment variable overrides (``LOKI_URL``, ``LOKI_TOKEN``, etc.) are layered
on top of the stored profile by :func:`resolve_config`.
"""

from __future__ import annotations

import json
import os
from dataclasses import asdict, dataclass, field
from pathlib import Path
from typing import Any, Literal, Optional

import yaml

AuthType = Literal["none", "basic", "bearer"]

DEFAULT_CONFIG_DIR = Path(
    os.environ.get("LOKI_CLI_CONFIG_DIR")
    or (Path(os.environ.get("XDG_CONFIG_HOME", Path.home() / ".config")) / "loki-cli")
)
DEFAULT_CONFIG_PATH = DEFAULT_CONFIG_DIR / "config.json"
LEGACY_YAML_PATH = DEFAULT_CONFIG_DIR / "config.yaml"

DEFAULT_PROFILE_NAME = "default"


# ---------------------------------------------------------------------------
# Data classes
# ---------------------------------------------------------------------------


@dataclass
class AuthConfig:
    type: AuthType = "none"
    username: Optional[str] = None
    password: Optional[str] = None
    token: Optional[str] = None

    @classmethod
    def from_dict(cls, data: Optional[dict[str, Any]]) -> AuthConfig:
        if not data:
            return cls()
        return cls(
            type=data.get("type", "none"),
            username=data.get("username"),
            password=data.get("password"),
            token=data.get("token"),
        )

    def redacted(self) -> AuthConfig:
        """Return a copy with secrets masked, for display."""
        mask = "***"
        return AuthConfig(
            type=self.type,
            username=self.username,
            password=mask if self.password else None,
            token=mask if self.token else None,
        )


@dataclass
class Config:
    """Resolved connection settings for a single Loki endpoint."""

    url: Optional[str] = None
    org_id: Optional[str] = None
    tls_skip_verify: bool = False
    auth: AuthConfig = field(default_factory=AuthConfig)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> Config:
        return cls(
            url=data.get("url"),
            org_id=data.get("org_id"),
            tls_skip_verify=bool(data.get("tls_skip_verify", False)),
            auth=AuthConfig.from_dict(data.get("auth")),
        )

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)


@dataclass
class ProfileStore:
    """The whole config file: an active-profile pointer plus named profiles."""

    active: str = DEFAULT_PROFILE_NAME
    profiles: dict[str, Config] = field(default_factory=dict)

    @classmethod
    def from_dict(cls, data: dict[str, Any]) -> ProfileStore:
        raw_profiles = data.get("profiles") or {}
        if not isinstance(raw_profiles, dict):
            raise ValueError("`profiles` must be a mapping")
        return cls(
            active=data.get("active") or DEFAULT_PROFILE_NAME,
            profiles={name: Config.from_dict(p or {}) for name, p in raw_profiles.items()},
        )

    def to_dict(self) -> dict[str, Any]:
        return {
            "active": self.active,
            "profiles": {name: p.to_dict() for name, p in self.profiles.items()},
        }

    def get(self, name: str) -> Config:
        if name not in self.profiles:
            raise KeyError(name)
        return self.profiles[name]

    def upsert(self, name: str, cfg: Config) -> None:
        self.profiles[name] = cfg


# ---------------------------------------------------------------------------
# Persistence
# ---------------------------------------------------------------------------


def _migrate_legacy_yaml(json_path: Path, yaml_path: Path) -> Optional[ProfileStore]:
    """If a legacy YAML config exists but no JSON, migrate into the new format."""
    if json_path.exists() or not yaml_path.exists():
        return None
    try:
        with yaml_path.open("r", encoding="utf-8") as f:
            data = yaml.safe_load(f) or {}
    except (OSError, yaml.YAMLError):
        return None
    if not isinstance(data, dict) or not data:
        return None
    store = ProfileStore(
        active=DEFAULT_PROFILE_NAME,
        profiles={DEFAULT_PROFILE_NAME: Config.from_dict(data)},
    )
    save_store(store, json_path)
    try:
        yaml_path.rename(yaml_path.with_suffix(".yaml.bak"))
    except OSError:
        pass
    return store


def load_store(path: Path = DEFAULT_CONFIG_PATH) -> ProfileStore:
    """Load the profile store from disk, migrating legacy YAML if needed."""
    if not path.exists():
        migrated = _migrate_legacy_yaml(path, LEGACY_YAML_PATH)
        if migrated is not None:
            return migrated
        return ProfileStore()
    with path.open("r", encoding="utf-8") as f:
        data = json.load(f)
    if not isinstance(data, dict):
        raise ValueError(f"Invalid config format in {path}: expected an object")
    return ProfileStore.from_dict(data)


def save_store(store: ProfileStore, path: Path = DEFAULT_CONFIG_PATH) -> Path:
    """Persist the profile store to disk atomically with mode 0600."""
    path.parent.mkdir(parents=True, exist_ok=True)
    tmp = path.with_suffix(path.suffix + ".tmp")
    with tmp.open("w", encoding="utf-8") as f:
        json.dump(store.to_dict(), f, indent=2, sort_keys=False)
        f.write("\n")
    os.chmod(tmp, 0o600)
    tmp.replace(path)
    return path


# ---------------------------------------------------------------------------
# Resolution (profile + env vars + explicit overrides)
# ---------------------------------------------------------------------------

ENV_URL = "LOKI_URL"
ENV_ORG_ID = "LOKI_ORG_ID"
ENV_TLS_SKIP_VERIFY = "LOKI_TLS_SKIP_VERIFY"
ENV_USERNAME = "LOKI_USERNAME"
ENV_PASSWORD = "LOKI_PASSWORD"
ENV_TOKEN = "LOKI_TOKEN"
ENV_PROFILE = "LOKI_PROFILE"


def _env_truthy(value: Optional[str]) -> bool:
    if value is None:
        return False
    return value.strip().lower() in {"1", "true", "yes", "on"}


def _apply_env_overrides(cfg: Config) -> Config:
    """Overlay LOKI_* environment variables on top of a Config, non-mutating."""
    url = os.environ.get(ENV_URL) or cfg.url
    org_id = os.environ.get(ENV_ORG_ID) or cfg.org_id
    tls_env = os.environ.get(ENV_TLS_SKIP_VERIFY)
    tls_skip_verify = _env_truthy(tls_env) if tls_env is not None else cfg.tls_skip_verify

    token = os.environ.get(ENV_TOKEN)
    username = os.environ.get(ENV_USERNAME)
    password = os.environ.get(ENV_PASSWORD)

    if token:
        auth = AuthConfig(type="bearer", token=token)
    elif username:
        auth = AuthConfig(
            type="basic",
            username=username,
            password=password if password is not None else cfg.auth.password,
        )
    else:
        auth = cfg.auth

    return Config(url=url, org_id=org_id, tls_skip_verify=tls_skip_verify, auth=auth)


def resolve_config(profile: Optional[str] = None) -> Config:
    """Return the effective :class:`Config` for the current invocation.

    Precedence (highest first): env vars > stored profile > empty defaults.
    ``profile`` overrides the active profile; falls back to ``$LOKI_PROFILE``
    and finally to the ``active`` entry in the store.
    """
    store = load_store()
    profile_name = profile or os.environ.get(ENV_PROFILE) or store.active
    if profile_name in store.profiles:
        base = store.profiles[profile_name]
    else:
        base = Config()
    return _apply_env_overrides(base)


def resolved_profile_name(profile: Optional[str] = None) -> str:
    """Report which profile name the CLI would use for this invocation."""
    store = load_store()
    return profile or os.environ.get(ENV_PROFILE) or store.active
