"""Unified command-line interface for axel."""

from __future__ import annotations

import argparse
from typing import Sequence

from . import repo_manager, task_manager


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the unified axel CLI."""

    parser = argparse.ArgumentParser(
        prog="axel",
        description="Unified CLI for repository and task helpers",
    )
    parser.add_argument(
        "command",
        nargs="?",
        choices=("repos", "tasks"),
        help="Subcommand to run",
    )
    parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help=argparse.SUPPRESS,
    )

    parsed = parser.parse_args(argv)

    if parsed.command == "repos":
        repo_manager.main(parsed.args)
        return 0
    if parsed.command == "tasks":
        task_manager.main(parsed.args)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
