"""Unified command-line interface for axel."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from . import repo_manager, task_manager


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the unified axel CLI."""

    if argv is None:
        argv = list(sys.argv[1:])
    else:
        argv = list(argv)

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

    try:
        parsed = parser.parse_args(argv[:1])
    except SystemExit as exc:  # pragma: no cover - argparse handles messaging
        return int(exc.code)

    forwarded = argv[1:]

    if parsed.command == "repos":
        repo_manager.main(forwarded)
        return 0
    if parsed.command == "tasks":
        task_manager.main(forwarded)
        return 0

    parser.print_help()
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
