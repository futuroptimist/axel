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
    subparsers = parser.add_subparsers(dest="command")

    repos_parser = subparsers.add_parser(
        "repos",
        help="Manage the repository list (delegates to axel.repo_manager)",
    )
    repos_parser.add_argument(
        "args",
        nargs=argparse.REMAINDER,
        help=argparse.SUPPRESS,
    )

    tasks_parser = subparsers.add_parser(
        "tasks",
        help="Manage the task list (delegates to axel.task_manager)",
    )
    tasks_parser.add_argument(
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
