from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from pathlib import Path
from typing import Sequence


def _run_git(
    *args: str,
    cwd: str | Path,
    check: bool = True,
    capture_output: bool = False,
) -> subprocess.CompletedProcess[str]:
    """Run a git command and return the completed process."""

    kwargs: dict[str, object] = {"cwd": cwd, "check": check, "text": True}
    if capture_output:
        kwargs["stdout"] = subprocess.PIPE
        kwargs["stderr"] = subprocess.PIPE
    return subprocess.run(["git", *args], **kwargs)


def _resolve_repository(path: str | Path) -> Path:
    """Return the git repository root for ``path``."""

    repo = Path(path).expanduser().resolve()
    if not repo.exists():
        raise ValueError(f"Repository path does not exist: {repo}")
    try:
        result = _run_git("rev-parse", "--show-toplevel", cwd=repo, capture_output=True)
    except subprocess.CalledProcessError as exc:  # pragma: no cover - defensive
        raise ValueError(f"{repo} is not a git repository") from exc
    root = Path(result.stdout.strip())
    return root


def speculative_merge_check(
    repo_path: str | Path,
    base: str,
    head: str,
) -> dict[str, object]:
    """Return conflict details for merging ``head`` into ``base`` without committing.

    The function checks out ``base`` in a temporary worktree, attempts a
    ``git merge --no-commit --no-ff`` with ``head``, and reports whether
    conflicts occur. The repository is left untouched after the speculative
    merge completes.
    """

    repo = _resolve_repository(repo_path)
    _run_git("rev-parse", "--verify", base, cwd=repo, capture_output=True)
    _run_git("rev-parse", "--verify", head, cwd=repo, capture_output=True)

    with tempfile.TemporaryDirectory(prefix="axel-merge-") as tempdir:
        worktree_path = Path(tempdir)
        _run_git(
            "worktree",
            "add",
            "--detach",
            str(worktree_path),
            base,
            cwd=repo,
            capture_output=True,
        )
        try:
            merge_result = _run_git(
                "merge",
                "--no-commit",
                "--no-ff",
                head,
                cwd=worktree_path,
                check=False,
                capture_output=True,
            )
            output = ((merge_result.stdout or "") + (merge_result.stderr or "")).strip()
            conflicts = merge_result.returncode != 0
            conflicted_files: list[str] = []
            if conflicts:
                status = _run_git(
                    "status",
                    "--porcelain",
                    cwd=worktree_path,
                    capture_output=True,
                )
                for line in status.stdout.splitlines():
                    if line.startswith("UU "):
                        conflicted_files.append(line[3:].strip())
                _run_git(
                    "merge",
                    "--abort",
                    cwd=worktree_path,
                    check=False,
                    capture_output=True,
                )
            return {
                "conflicts": conflicts,
                "conflicted_files": conflicted_files,
                "output": output,
            }
        finally:
            _run_git(
                "reset",
                "--hard",
                cwd=worktree_path,
                check=False,
                capture_output=True,
            )
            _run_git(
                "worktree",
                "remove",
                "--force",
                str(worktree_path),
                cwd=repo,
                check=False,
                capture_output=True,
            )


def _format_result(base: str, head: str, result: dict[str, object]) -> str:
    if result.get("conflicts"):
        lines = [
            f"Merge would conflict when merging {head} into {base}",
        ]
        conflicted = result.get("conflicted_files") or []
        if conflicted:
            lines.append("Conflicted files:")
            lines.extend(f"- {name}" for name in conflicted)
    else:
        lines = [f"Merge is clean when merging {head} into {base}"]
    return "\n".join(lines)


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for speculative merge checks."""

    parser = argparse.ArgumentParser(description="Axel merge utilities")
    subparsers = parser.add_subparsers(dest="command")

    check_parser = subparsers.add_parser(
        "check",
        help="Run a speculative merge and report conflicts",
    )
    check_parser.add_argument(
        "--repo",
        default=".",
        help="Path to the repository (defaults to current directory)",
    )
    check_parser.add_argument("--base", required=True, help="Base branch or commit")
    check_parser.add_argument("--head", required=True, help="Head branch or commit")
    check_parser.add_argument(
        "--json",
        action="store_true",
        help="Output results as JSON",
    )

    args = parser.parse_args(argv)

    if args.command != "check":
        parser.print_help()
        return 1

    result = speculative_merge_check(args.repo, args.base, args.head)
    if args.json:
        print(json.dumps(result, indent=2, sort_keys=True))
    else:
        print(_format_result(args.base, args.head, result))
    return 1 if result["conflicts"] else 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
