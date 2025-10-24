"""Analytics tools for orthogonality and prompt saturation insights."""

from __future__ import annotations

import argparse
import json
import math
import os
from collections import Counter
from dataclasses import dataclass
from datetime import datetime, timezone
from difflib import SequenceMatcher
from importlib import metadata as importlib_metadata
from itertools import combinations
from pathlib import Path
from typing import Any, Iterable, Mapping

import pandas as pd
import requests

from .config import load_telemetry_config

ANALYTICS_ROOT = Path("analytics")
_DEFAULT_RECENT_WINDOW = 10
_ORTHOGONALITY_BINS = 5

_CURRENT_REPO: str | None = None
_LATEST_RUN_METRICS: dict[str, Any] | None = None


@dataclass
class PullRequestSnapshot:
    """Small helper container for pull request state used in analytics."""

    merged: bool
    mergeable_state: str | None


def set_repository(repo: str | None) -> None:
    """Store the repository for API lookups used by ``analyze_orthogonality``."""

    global _CURRENT_REPO
    _CURRENT_REPO = repo


def set_latest_run_metrics(metrics: dict[str, Any] | None) -> None:
    """Persist the most recent Codex run metrics for saturation tracking."""

    global _LATEST_RUN_METRICS
    _LATEST_RUN_METRICS = metrics


def _now_iso() -> str:
    return datetime.now(timezone.utc).isoformat()


def _ensure_directory(path: Path) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)


def _append_jsonl(path: Path, payload: dict[str, Any]) -> None:
    _ensure_directory(path)
    with path.open("a", encoding="utf-8") as handle:
        handle.write(json.dumps(payload, default=str))
        handle.write("\n")


def _cli_metadata() -> dict[str, Any]:
    """Return CLI metadata persisted alongside analytics entries."""

    try:
        version = importlib_metadata.version("axel")
    except importlib_metadata.PackageNotFoundError:
        version = None
    config = load_telemetry_config()
    return {
        "cli_version": version,
        "telemetry_opt_in": bool(config.opt_in),
        "telemetry_consent_timestamp": config.consent_timestamp,
    }


def _config_analytics_root() -> Path:
    """Return the configuration directory used for analytics history."""

    return Path.home() / ".config" / "axel" / "analytics"


def _append_config_analytics(metric: str, payload: dict[str, Any]) -> None:
    """Append analytics payloads to the per-metric config ledger."""

    path = _config_analytics_root() / f"{metric}.jsonl"
    _append_jsonl(path, payload)


def _load_history(path: Path) -> pd.DataFrame:
    if not path.exists():
        return pd.DataFrame()
    records: list[dict[str, Any]] = []
    with path.open("r", encoding="utf-8") as handle:
        for line in handle:
            line = line.strip()
            if not line:
                continue
            try:
                records.append(json.loads(line))
            except json.JSONDecodeError:
                continue
    if not records:
        return pd.DataFrame()
    return pd.DataFrame(records)


def _fetch_pull_request(repo: str, pr_number: int) -> PullRequestSnapshot | None:
    """Load merge status for a pull request via the GitHub REST API."""

    token = os.getenv("GITHUB_TOKEN")
    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"Bearer {token}"
    url = f"https://api.github.com/repos/{repo}/pulls/{pr_number}"
    response = requests.get(url, headers=headers, timeout=10)
    if response.status_code != 200:
        return None
    data = response.json()
    merged = bool(data.get("merged"))
    mergeable_state = data.get("mergeable_state")
    mergeable = data.get("mergeable")
    if merged is False and mergeable is False and mergeable_state is None:
        mergeable_state = "dirty"
    return PullRequestSnapshot(merged=merged, mergeable_state=mergeable_state)


def _conflict_rate(
    repo: str | None, pr_numbers: Iterable[int], total_tasks: int
) -> float:
    if not repo or not pr_numbers or total_tasks <= 0:
        return 0.0
    conflict_count = 0
    for pr_number in pr_numbers:
        snapshot = _fetch_pull_request(repo, pr_number)
        if snapshot and snapshot.mergeable_state == "dirty":
            conflict_count += 1
    return conflict_count / total_tasks


def _average_pairwise_similarity(task_versions: list[str]) -> float:
    if len(task_versions) < 2:
        return 0.0
    similarities = []
    for idx_a, idx_b in combinations(range(len(task_versions)), 2):
        a = task_versions[idx_a]
        b = task_versions[idx_b]
        matcher = SequenceMatcher(a=a, b=b)
        similarities.append(matcher.ratio())
    if not similarities:
        return 0.0
    return sum(similarities) / len(similarities)


def _clip_score(value: float) -> float:
    return max(0.0, min(1.0, value))


def analyze_orthogonality(
    task_versions: list[str], merged_prs: list[int]
) -> dict[str, Any]:
    """Compute the orthogonality score for a group of Codex task versions."""

    timestamp = _now_iso()
    repo = _CURRENT_REPO or os.getenv("AXEL_GITHUB_REPO")
    total_tasks = len(task_versions)
    avg_similarity = _average_pairwise_similarity(task_versions)
    conflict_rate = _conflict_rate(repo, merged_prs, total_tasks)
    merge_conflict_penalty = 0.1 * conflict_rate
    orthogonality = _clip_score(1.0 - (avg_similarity + merge_conflict_penalty))
    result = {
        "timestamp": timestamp,
        "orthogonality_score": orthogonality,
        "avg_pairwise_similarity": avg_similarity,
        "merge_conflict_penalty": merge_conflict_penalty,
        "merge_conflict_rate": conflict_rate,
        "merged_prs": merged_prs,
        "total_tasks": total_tasks,
    }
    date_key = timestamp.split("T", 1)[0]
    log_path = ANALYTICS_ROOT / "orthogonality" / f"{date_key}.jsonl"
    _append_jsonl(log_path, result)
    config_payload = result | {"metric": "orthogonality"} | _cli_metadata()
    _append_config_analytics("orthogonality", config_payload)
    return result


def _load_latest_metrics() -> dict[str, Any]:
    if _LATEST_RUN_METRICS is not None:
        return _LATEST_RUN_METRICS
    env_payload = os.getenv("AXEL_PROMPT_RUN_METRICS")
    if not env_payload:
        return {}
    try:
        return json.loads(env_payload)
    except json.JSONDecodeError:
        return {}


def _collect_recent_scores(entries: pd.Series) -> list[float]:
    scores: list[float] = []
    for value in entries.dropna():
        if isinstance(value, list):
            scores.extend(float(v) for v in value)
        else:
            try:
                scores.append(float(value))
            except (TypeError, ValueError):
                continue
    return scores


def _orthogonality_entropy(scores: list[float]) -> float:
    if not scores:
        return 0.0
    series = pd.Series(scores, dtype="float")
    if series.nunique(dropna=False) <= 1:
        return 0.0
    try:
        bins = pd.cut(
            series,
            bins=_ORTHOGONALITY_BINS,
            include_lowest=True,
            duplicates="drop",
        )
    except ValueError:
        return 0.0
    counts = Counter(bins.dropna())
    if not counts:
        return 0.0
    total = sum(counts.values())
    probs = [count / total for count in counts.values() if count > 0]
    if len(probs) <= 1:
        return 0.0
    entropy = -sum(p * math.log(p) for p in probs)
    max_entropy = math.log(len(probs))
    if max_entropy == 0:
        return 0.0
    return entropy / max_entropy


def self_evaluate_merge_conflicts(summary: Mapping[str, int]) -> dict[str, Any]:
    """Return a critic assessment for merge conflicts based on classification counts."""

    summary_counter = Counter({k: int(v) for k, v in summary.items() if int(v) > 0})
    total_conflicts = sum(summary_counter.values())
    comment_only = summary_counter.get("comment_only", 0)
    code_conflicts = summary_counter.get("code", 0)
    unknown_conflicts = summary_counter.get("unknown", 0)
    if total_conflicts == 0:
        return {
            "conflict_score": 1.0,
            "auto_resolvable": True,
            "comment_only": 0,
            "code": 0,
            "unknown": 0,
            "assessment": "No conflicts detected",
        }
    score = comment_only / total_conflicts
    auto_resolvable = code_conflicts == 0 and unknown_conflicts == 0
    if code_conflicts:
        assessment = "Manual review required for code conflicts"
    elif unknown_conflicts:
        assessment = (
            "Comment-focused conflicts require inspection before auto-resolution"
            if comment_only
            else "Conflicts require inspection before auto-resolution"
        )
    else:
        assessment = "Conflicts limited to comments; safe to auto-resolve"
    return {
        "conflict_score": _clip_score(score),
        "auto_resolvable": auto_resolvable,
        "comment_only": comment_only,
        "code": code_conflicts,
        "unknown": unknown_conflicts,
        "assessment": assessment,
    }


def track_prompt_saturation(repo: str, prompt_doc: str) -> dict[str, Any]:
    """Compute and persist prompt saturation analytics for the given prompt document."""

    timestamp = _now_iso()
    prompt_name = Path(prompt_doc).name
    metrics = _load_latest_metrics()
    fitness_delta = float(metrics.get("fitness_delta", 0.0))
    merged = int(metrics.get("merged", 0))
    closed = int(metrics.get("closed", 0))
    orth_scores = metrics.get("orthogonality_scores", [])
    if not isinstance(orth_scores, list):
        orth_scores = []
    log_path = ANALYTICS_ROOT / "saturation" / repo / f"{prompt_name}.jsonl"
    history = _load_history(log_path)
    new_entry = {
        "timestamp": timestamp,
        "repo": repo,
        "prompt": prompt_name,
        "fitness_delta": fitness_delta,
        "merged": merged,
        "closed": closed,
        "orthogonality_scores": orth_scores,
    }
    history = pd.concat([history, pd.DataFrame([new_entry])], ignore_index=True)
    recent_window = history.tail(_DEFAULT_RECENT_WINDOW)
    fitness_delta_avg = (
        float(abs(recent_window["fitness_delta"].astype(float).mean()))
        if not recent_window.empty
        else 0.0
    )
    merged_sum = float(recent_window.get("merged", pd.Series(dtype=float)).sum())
    closed_sum = float(recent_window.get("closed", pd.Series(dtype=float)).sum())
    total_attempts = merged_sum + closed_sum
    merge_rate = merged_sum / total_attempts if total_attempts else 0.0
    recent_scores = _collect_recent_scores(
        recent_window.get("orthogonality_scores", pd.Series(dtype=object))
    )
    orth_entropy = _orthogonality_entropy(recent_scores)
    saturation = (
        0.5 * (1 - min(1.0, fitness_delta_avg)) + 0.3 * merge_rate + 0.2 * orth_entropy
    )
    saturation = _clip_score(saturation)
    recommendation = None
    prompt_refresh = False
    if saturation < 0.3:
        recommendation = "Prompt Refresh recommended"
        prompt_refresh = True
    enriched_entry = {
        **new_entry,
        "fitness_delta_avg": fitness_delta_avg,
        "merge_rate": merge_rate,
        "orthogonality_entropy": orth_entropy,
        "saturation_score": saturation,
        "prompt_refresh_recommended": prompt_refresh,
    }
    _append_jsonl(log_path, enriched_entry)
    config_payload = enriched_entry | {"metric": "saturation"} | _cli_metadata()
    _append_config_analytics("saturation", config_payload)
    return {
        "timestamp": timestamp,
        "repo": repo,
        "prompt": prompt_name,
        "saturation_score": saturation,
        "fitness_delta_avg": fitness_delta_avg,
        "merge_rate": merge_rate,
        "orthogonality_entropy": orth_entropy,
        "prompt_refresh_recommended": prompt_refresh,
        "recommendation": recommendation,
    }


def _format_orthogonality_output(result: dict[str, Any]) -> str:
    conflicts = result.get("merge_conflict_rate", 0.0)
    total = result.get("total_tasks", 0)
    merged = len(result.get("merged_prs", []) or [])
    orthogonality = result.get("orthogonality_score", 0.0)
    avg_similarity = result.get("avg_pairwise_similarity", 0.0)
    lines = [
        f"Codex Task Group: {result['timestamp']}",
        f"Orthogonality: {orthogonality:.2f} (avg similarity {avg_similarity:.2f})",
        f"Merge Conflicts: {conflicts * total:.0f}/{total}",
        f"Merged PRs: {merged}",
    ]
    return "\n".join(lines)


def _format_saturation_output(result: dict[str, Any]) -> str:
    metrics_line = (
        f"Fitness Δ avg: {result['fitness_delta_avg']:.2f} | "
        f"Merge Rate: {result['merge_rate']:.2f} | "
        f"Orth Entropy: {result['orthogonality_entropy']:.2f}"
    )
    lines = [
        f"Prompt Doc: {result['prompt']}",
        f"Saturation: {result['saturation_score']:.2f}",
        metrics_line,
    ]
    if result.get("prompt_refresh_recommended"):
        lines.append("Recommendation: consider a Prompt Refresh")
    return "\n".join(lines)


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Axel analytics utilities")
    subparsers = parser.add_subparsers(dest="command")

    ortho_parser = subparsers.add_parser(
        "analyze-orthogonality", help="Compute orthogonality analytics"
    )
    ortho_parser.add_argument(
        "--diff-file",
        action="append",
        required=True,
        dest="diff_files",
        help="Path to a diff file",
    )
    ortho_parser.add_argument(
        "--pr",
        dest="prs",
        action="append",
        type=int,
        default=[],
        help="Pull request numbers to inspect",
    )
    ortho_parser.add_argument(
        "--repo", dest="repo", help="owner/name for GitHub repository"
    )
    ortho_parser.add_argument(
        "--json",
        action="store_true",
        help="Output orthogonality analytics as JSON",
    )

    sat_parser = subparsers.add_parser(
        "analyze-saturation", help="Compute prompt saturation analytics"
    )
    sat_parser.add_argument("--repo", required=True, help="Repository name owner/name")
    sat_parser.add_argument(
        "--prompt", required=True, help="Path or name of the prompt doc"
    )
    sat_parser.add_argument(
        "--metrics",
        help="Path to JSON file containing latest run metrics",
    )
    sat_parser.add_argument(
        "--json",
        action="store_true",
        help="Output saturation analytics as JSON",
    )

    args = parser.parse_args(argv)
    if args.command == "analyze-orthogonality":
        if args.repo:
            set_repository(args.repo)
        task_versions: list[str] = []
        for file_path in args.diff_files:
            data = Path(file_path).read_text(encoding="utf-8")
            task_versions.append(data)
        result = analyze_orthogonality(task_versions, args.prs or [])
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        print(_format_orthogonality_output(result))
        return 0
    if args.command == "analyze-saturation":
        metrics: dict[str, Any] | None = None
        if args.metrics:
            metrics = json.loads(Path(args.metrics).read_text(encoding="utf-8"))
        set_latest_run_metrics(metrics)
        result = track_prompt_saturation(args.repo, args.prompt)
        if args.json:
            print(json.dumps(result, indent=2, ensure_ascii=False))
            return 0
        print(_format_saturation_output(result))
        return 0
    parser.print_help()
    return 1


if __name__ == "__main__":  # pragma: no cover
    raise SystemExit(main())
