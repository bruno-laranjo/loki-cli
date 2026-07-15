"""Root Click group for loki-cli."""

from __future__ import annotations

import signal
import sys
from typing import Optional

import click

from loki_cli import __version__
from loki_cli.commands.config import config_group
from loki_cli.commands.labels import labels_command, target_command
from loki_cli.commands.login import login_command, logout_command, whoami_command
from loki_cli.commands.logs import logs_command
from loki_cli.config import ENV_PROFILE

# Restore default SIGPIPE handling so `loki-cli ... | head` exits quietly
# instead of raising BrokenPipeError deep in the interpreter.
if hasattr(signal, "SIGPIPE"):
    signal.signal(signal.SIGPIPE, signal.SIG_DFL)

# Line-buffered stdout so streamed lines appear immediately when piped.
try:
    sys.stdout.reconfigure(line_buffering=True)  # type: ignore[attr-defined]
except Exception:
    pass


@click.group(context_settings={"help_option_names": ["-h", "--help"]})
@click.version_option(__version__, prog_name="loki-cli")
@click.option(
    "--profile",
    "-p",
    "profile",
    default=None,
    envvar=ENV_PROFILE,
    help=(
        "Named profile to use (default: active profile from config). "
        f"Overrides ${ENV_PROFILE} env var."
    ),
)
@click.pass_context
def main(ctx: click.Context, profile: Optional[str]) -> None:
    """loki-cli — query Grafana Loki from the command line."""
    ctx.ensure_object(dict)
    ctx.obj["profile"] = profile


main.add_command(config_group)
main.add_command(login_command)
main.add_command(logout_command)
main.add_command(whoami_command)
main.add_command(labels_command)
main.add_command(target_command)
main.add_command(logs_command)


if __name__ == "__main__":
    main()
