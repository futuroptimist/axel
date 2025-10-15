"""Speculative merge helpers and conflict classification utilities."""

from __future__ import annotations

import argparse
import json
import subprocess
import tempfile
from collections import Counter
from dataclasses import dataclass
from fnmatch import fnmatch
from pathlib import Path
from typing import Any, Mapping, Sequence

import yaml


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
                    code = line[:2]
                    if code in _CONFLICT_CODES:
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
                "auto_resolvable": _auto_resolvable(summary, conflicts),
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


_CONFLICT_CODES: set[str] = {"DD", "AU", "UD", "UA", "DU", "AA", "UU"}


@dataclass(frozen=True)
class MergePlan:
    """Structured response tying merge results to enforcement policy."""

    base: str
    head: str
    result: dict[str, Any]
    resolutions: dict[str, str]
    safety_checks: list[dict[str, Any]]
    auto_resolve: bool
    requires_manual_review: bool
    policy_metadata: dict[str, Any]


_POLICY_PATH = Path(__file__).resolve().parent / "policies" / "merge_policy.yaml"


_COMMENT_PREFIXES: tuple[str, ...] = (
    "#",
    "//",
    "/*",
    "*",
    "--",
)


def _auto_resolvable(summary: dict[str, int], conflicts: bool) -> bool:
    if conflicts and not summary:
        return False
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


def load_merge_policy(path: str | Path | None = None) -> dict[str, Any]:
    """Return the configured merge policy as a mapping."""

    location = Path(path) if path is not None else _POLICY_PATH
    data = yaml.safe_load(location.read_text(encoding="utf-8"))
    if data is None:
        return {}
    if not isinstance(data, Mapping):
        raise ValueError("Merge policy must be a mapping")
    return dict(data)


def _match_priority_rule(name: str, rules: Sequence[Mapping[str, Any]]) -> str | None:
    for rule in rules:
        pattern = rule.get("pattern") if isinstance(rule, Mapping) else None
        resolution = rule.get("resolution") if isinstance(rule, Mapping) else None
        if pattern and resolution and fnmatch(name, pattern):
            return str(resolution)
    return None


def _build_resolutions(
    classifications: Mapping[str, str],
    conflict_policy: Mapping[str, Any],
) -> tuple[dict[str, str], bool]:
    rules = (
        conflict_policy.get("priority_rules")
        if isinstance(conflict_policy, Mapping)
        else []
    )
    fallback = (
        conflict_policy.get("fallback")
        if isinstance(conflict_policy, Mapping)
        else "manual_review"
    )
    heuristics = (
        conflict_policy.get("heuristics")
        if isinstance(conflict_policy, Mapping)
        else {}
    )
    comment_auto = bool(
        isinstance(heuristics, Mapping)
        and heuristics.get("comment_only_conflicts_auto_resolve")
    )
    resolutions: dict[str, str] = {}
    rule_entries: Sequence[Mapping[str, Any]]
    if isinstance(rules, Sequence):
        rule_entries = [rule for rule in rules if isinstance(rule, Mapping)]
    else:  # pragma: no cover - defensive branch
        rule_entries = []
    for name, classification in classifications.items():
        matched = _match_priority_rule(name, rule_entries)
        if matched:
            resolutions[name] = matched
            continue
        if classification == "comment_only" and comment_auto:
            resolutions[name] = "auto_resolve_comment"
            continue
        resolutions[name] = str(fallback or "manual_review")
    return resolutions, comment_auto


def plan_merge_actions(
    repo_path: str | Path,
    base: str,
    head: str,
    *,
    policy_path: str | Path | None = None,
) -> MergePlan:
    """Run merge detection and map conflicts to policy guidance."""

    policy = load_merge_policy(policy_path)
    merge_policy = policy.get("merge_policy") if isinstance(policy, Mapping) else {}
    conflict_policy = (
        merge_policy.get("conflict_resolution")
        if isinstance(merge_policy, Mapping)
        else {}
    )
    result = speculative_merge_check(repo_path, base, head)
    classifications = result.get("conflict_classification") or {}
    if not isinstance(classifications, Mapping):
        classifications = {}
    resolutions, comment_auto = _build_resolutions(classifications, conflict_policy)

    conflicts_present = bool(result.get("conflicts"))
    auto_resolve = not conflicts_present
    if conflicts_present:
        auto_resolve = bool(result.get("auto_resolvable"))
        if classifications and comment_auto:
            auto_resolve = all(
                classification == "comment_only"
                for classification in classifications.values()
            )

    raw_checks = (
        merge_policy.get("safety_checks") if isinstance(merge_policy, Mapping) else []
    )
    safety_checks: list[dict[str, Any]] = []
    if isinstance(raw_checks, Sequence):
        for entry in raw_checks:
            if isinstance(entry, Mapping):
                safety_checks.append(dict(entry))

    metadata = merge_policy.get("metadata") if isinstance(merge_policy, Mapping) else {}
    if not isinstance(metadata, Mapping):
        metadata = {}

    return MergePlan(
        base=base,
        head=head,
        result=result,
        resolutions=resolutions,
        safety_checks=safety_checks,
        auto_resolve=auto_resolve,
        requires_manual_review=not auto_resolve,
        policy_metadata=dict(metadata),
    )


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
