"""Unified command-line interface for axel."""

from __future__ import annotations

import argparse
import sys
from typing import Sequence

from . import critic, repo_manager, task_manager
from .completions import CompletionInstallation, install_completions

COMMANDS = ("repos", "tasks", "analyze-orthogonality", "analyze-saturation")


def _normalize_exit_code(result: object) -> int:
    """Convert a manager return value into a process exit code."""

    if isinstance(result, bool):
        return int(result)
    if isinstance(result, int):
        return result
    return 0


def _build_help_parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(
        prog="axel",
        description="Unified CLI for repository and task helpers",
    )
    parser.add_argument(
        "--install-completions",
        action="store_true",
        help="Install shell completion scripts for the axel CLI",
    )
    parser.add_argument(
        "--shell",
        choices=("bash", "zsh", "fish"),
        help="Shell to target when installing completions (defaults to $SHELL)",
    )
    parser.add_argument(
        "--path",
        help=(
            "Destination for the completion script "
            "(defaults to a shell-specific location)"
        ),
    )
    parser.add_argument(
        "command",
        nargs="?",
        help=(
            "Subcommand to run (repos, tasks, analyze-orthogonality, "
            "analyze-saturation)"
        ),
    )
    parser.add_argument("args", nargs=argparse.REMAINDER, help=argparse.SUPPRESS)
    return parser


def _completion_message(result: CompletionInstallation, *, custom_path: bool) -> str:
    base = f"Installed axel completions for {result.shell} at {result.path}"
    if result.shell == "fish":
        if custom_path:
            note = (
                "Copy the file into ~/.config/fish/completions "
                "or source it from config.fish."
            )
        else:
            note = "Fish loads files from ~/.config/fish/completions automatically."
        return f"{base}\n{note}"

    rc_file = "~/.bashrc" if result.shell == "bash" else "~/.zshrc"
    note = (
        f"Add 'source {result.path}' to {rc_file} or " "source it in the current shell."
    )
    return f"{base}\n{note}"


def main(argv: Sequence[str] | None = None) -> int:
    """Entry point for the unified axel CLI."""

    if argv is None:
        argv = list(sys.argv[1:])
    else:
        argv = list(argv)

    option_parser = argparse.ArgumentParser(add_help=False, prog="axel")
    option_parser.add_argument("--install-completions", action="store_true")
    option_parser.add_argument("--shell")
    option_parser.add_argument("--path")
    option_parser.add_argument("-h", "--help", action="store_true", dest="help_flag")

    prefix: list[str] = []
    index = 0
    while index < len(argv):
        token = argv[index]
        if token == "--":
            break
        if token == "--install-completions":
            prefix.append(token)
            index += 1
            continue
        if token in {"--shell", "--path"}:
            if index + 1 >= len(argv):
                prefix.extend(argv[index:])
                index = len(argv)
                break
            prefix.extend([token, argv[index + 1]])
            index += 2
            continue
        if token in {"-h", "--help"}:
            prefix.append(token)
            index += 1
            continue
        if token.startswith("-"):
            break
        break

    try:
        parsed = option_parser.parse_args(prefix)
    except SystemExit as exc:  # pragma: no cover - argparse handles messaging
        return int(exc.code)

    remaining = argv[index:]

    help_parser = _build_help_parser()

    if not parsed.install_completions and (
        parsed.shell is not None or parsed.path is not None
    ):
        try:
            help_parser.error("--shell and --path require --install-completions")
        except SystemExit as exc:  # pragma: no cover - argparse handles messaging
            return int(exc.code)

    if parsed.help_flag and not parsed.install_completions:
        help_parser.print_help()
        return 0

    if parsed.install_completions:
        if parsed.help_flag:
            help_parser.print_help()
            return 0
        if remaining:
            extra = " ".join(remaining)
            message = (
                "--install-completions does not accept additional arguments: "
                f"{extra}"
            )
            try:
                help_parser.error(message)
            except SystemExit as exc:  # pragma: no cover - argparse handles messaging
                return int(exc.code)
        try:
            result = install_completions(shell=parsed.shell, path=parsed.path)
        except ValueError as exc:
            try:
                help_parser.error(str(exc))
            except SystemExit as error:  # pragma: no cover - argparse handles messaging
                return int(error.code)
        message = _completion_message(result, custom_path=parsed.path is not None)
        print(message)
        return 0

    if not remaining:
        help_parser.print_help()
        return 0

    command, forwarded = remaining[0], remaining[1:]

    if command not in COMMANDS:
        try:
            help_parser.error(f"unknown command: {command}")
        except SystemExit as exc:  # pragma: no cover - argparse handles messaging
            return int(exc.code)

    if command == "repos":
        return _normalize_exit_code(repo_manager.main(forwarded))
    if command == "tasks":
        return _normalize_exit_code(task_manager.main(forwarded))
    return _normalize_exit_code(critic.main([command, *forwarded]))


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
