"""Speculative merge helpers and conflict classification utilities."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from collections import Counter
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
            classifications: dict[str, str] = {}
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
                classifications = _classify_conflicts(worktree_path, conflicted_files)
                summary = dict(Counter(classifications.values()))
                _run_git(
                    "merge",
                    "--abort",
                    cwd=worktree_path,
                    check=False,
                    capture_output=True,
                )
            else:
                summary = {}
            return {
                "conflicts": conflicts,
                "conflicted_files": conflicted_files,
                "output": output,
                "conflict_classification": classifications,
                "conflict_summary": summary,
                "auto_resolvable": _auto_resolvable(summary),
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
        summary = result.get("conflict_summary") or {}
        if summary:
            lines.append("Conflict summary:")
            for key, value in sorted(summary.items()):
                lines.append(f"- {key}: {value}")
    else:
        lines = [f"Merge is clean when merging {head} into {base}"]
    return "\n".join(lines)


_COMMENT_PREFIXES: tuple[str, ...] = (
    "#",
    "//",
    "/*",
    "*",
    "--",
)


def _auto_resolvable(summary: dict[str, int]) -> bool:
    if not summary:
        return True
    code_conflicts = summary.get("code", 0)
    unknown_conflicts = summary.get("unknown", 0)
    return code_conflicts == 0 and unknown_conflicts == 0


def _extract_conflict_segments(content: str) -> list[tuple[list[str], list[str]]]:
    segments: list[tuple[list[str], list[str]]] = []
    ours: list[str] = []
    theirs: list[str] = []
    state: str | None = None
    for line in content.splitlines():
        if line.startswith("<<<<<<<"):
            ours = []
            theirs = []
            state = "ours"
            continue
        if line.startswith("=======") and state == "ours":
            state = "theirs"
            continue
        if line.startswith(">>>>>>>") and state == "theirs":
            segments.append((ours, theirs))
            state = None
            continue
        if state == "ours":
            ours.append(line)
        elif state == "theirs":
            theirs.append(line)
    return segments


def _is_comment_line(line: str) -> bool:
    stripped = line.strip()
    if not stripped:
        return True
    for prefix in _COMMENT_PREFIXES:
        if stripped.startswith(prefix):
            return True
    if stripped.endswith("-->") and stripped.startswith("<!--"):
        return True
    return False


def _prune_common_lines(
    ours: list[str], theirs: list[str]
) -> tuple[list[str], list[str]]:
    theirs_counter = Counter(theirs)
    ours_unique: list[str] = []
    for line in ours:
        if theirs_counter.get(line, 0) > 0:
            theirs_counter[line] -= 1
        else:
            ours_unique.append(line)
    ours_counter = Counter(ours)
    theirs_unique: list[str] = []
    for line in theirs:
        if ours_counter.get(line, 0) > 0:
            ours_counter[line] -= 1
        else:
            theirs_unique.append(line)
    return ours_unique, theirs_unique


def _classify_segments(segments: list[tuple[list[str], list[str]]]) -> str:
    if not segments:
        return "unknown"
    for ours, theirs in segments:
        ours_unique, theirs_unique = _prune_common_lines(ours, theirs)
        lines = [*ours_unique, *theirs_unique]
        if not lines:
            continue
        if not all(_is_comment_line(line) for line in lines):
            return "code"
    return "comment_only"


def _classify_conflicts(
    worktree_path: Path, conflicted_files: list[str]
) -> dict[str, str]:
    classifications: dict[str, str] = {}
    for name in conflicted_files:
        file_path = worktree_path / name
        try:
            content = file_path.read_text(encoding="utf-8", errors="ignore")
        except OSError:
            classifications[name] = "unknown"
            continue
        segments = _extract_conflict_segments(content)
        classifications[name] = _classify_segments(segments)
    return classifications


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
