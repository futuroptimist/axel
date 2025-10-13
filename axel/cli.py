"""Unified command-line interface for axel."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from . import critic, repo_manager, task_manager


def _normalize_exit_code(result: object) -> int:
    """Convert a manager return value into a process exit code."""

    if isinstance(result, bool):
        return int(result)
    if isinstance(result, int):
        return result
    return 0


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
        choices=("repos", "tasks", "analyze-orthogonality", "analyze-saturation"),
        help="Subcommand to run",
    )

    if not argv or argv[0] in {"-h", "--help"}:
        parser.print_help()
        return 0

    command, forwarded = argv[0], argv[1:]

    if command == "repos":
        return _normalize_exit_code(repo_manager.main(forwarded))
    if command == "tasks":
        return _normalize_exit_code(task_manager.main(forwarded))
    if command in {"analyze-orthogonality", "analyze-saturation"}:
        return _normalize_exit_code(critic.main([command, *forwarded]))

    try:
        parser.error(f"unknown command: {command}")
    except SystemExit as exc:  # pragma: no cover - argparse handles messaging
        return int(exc.code)


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
