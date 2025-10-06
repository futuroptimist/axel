from __future__ import annotations

import argparse
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Iterable, Sequence
from urllib.parse import urlparse

from .repo_manager import get_repo_file, load_repos


@dataclass(frozen=True)
class RepoInfo:
    """Parsed information for a repository URL."""

    url: str
    slug: str
    name: str


def _parse_repo(url: str) -> RepoInfo:
    """Return :class:`RepoInfo` for ``url``.

    Extracts the ``owner/repo`` slug when present and falls back to the raw path
    when the URL is incomplete.
    """

    parsed = urlparse(url)
    parts = [part for part in parsed.path.split("/") if part]
    if len(parts) >= 2:
        owner, repo = parts[:2]
        slug = f"{owner}/{repo}"
        name = repo
    elif parts:
        slug = parts[-1]
        name = slug
    else:
        slug = parsed.netloc or url
        name = slug
    return RepoInfo(url=url, slug=slug, name=name)


KeywordTemplate = tuple[str, str]

_KEYWORD_TEMPLATES: tuple[KeywordTemplate, ...] = (
    (
        "token",
        (
            "{primary} can broker token.place auth while gabriel audits secrets "
            "so {secondary} ships safely."
        ),
    ),
    (
        "gabriel",
        (
            "{primary} can feed security intelligence into {secondary} so quests ship "
            "with guardrails."
        ),
    ),
    (
        "blog",
        (
            "Use {primary} to publish a cross-repo recap that highlights breakthroughs "
            "from {secondary}."
        ),
    ),
    (
        "discord",
        (
            "Route conversations captured by {primary} into {secondary}'s planning "
            "docs to keep quests aligned."
        ),
    ),
)

_KEYWORD_LOOKUP = {keyword: template for keyword, template in _KEYWORD_TEMPLATES}

_DEFAULT_DETAIL = (
    "Plan a quest where {a} and {b} share context to unlock a cross-repo "
    "improvement."
)


Suggestion = dict[str, list[str] | str]


def _build_suggestion(left: RepoInfo, right: RepoInfo) -> tuple[Suggestion, int]:
    ordered = tuple(sorted((left, right), key=lambda info: info.slug.lower()))
    primary, secondary = ordered
    detail, score = _select_detail(primary, secondary)
    repos = [primary.slug, secondary.slug]
    summary = f"Link {primary.slug} ↔ {secondary.slug}"
    suggestion: Suggestion = {"repos": repos, "summary": summary, "details": detail}
    return suggestion, score


def _select_detail(primary: RepoInfo, secondary: RepoInfo) -> tuple[str, int]:
    ordered = ((primary, secondary), (secondary, primary))

    # ``token`` quests must always reference gabriel even when the paired repo
    # also matches a different keyword (e.g. ``blog`` or ``discord``).
    for repo, other in ordered:
        if "token" in repo.slug.lower():
            template = _KEYWORD_LOOKUP["token"]
            return template.format(primary=repo.slug, secondary=other.slug), 1

    for repo, other in ordered:
        lower = repo.slug.lower()
        for keyword, template in _KEYWORD_TEMPLATES:
            if keyword == "token":
                continue
            if keyword in lower:
                return template.format(primary=repo.slug, secondary=other.slug), 1
    return _DEFAULT_DETAIL.format(a=primary.slug, b=secondary.slug), 0


def _unique_repos(repos: Iterable[str]) -> list[RepoInfo]:
    unique: list[RepoInfo] = []
    seen: set[str] = set()
    for url in repos:
        info = _parse_repo(url)
        key = info.slug.lower()
        if key in seen:
            continue
        seen.add(key)
        unique.append(info)
    return unique


def suggest_cross_repo_quests(
    repos: Sequence[str], *, limit: int = 3
) -> list[Suggestion]:
    """Return quests that connect repositories from ``repos``.

    Suggestions are deterministic, highlight at least two repositories, and
    prefer pairs that match known keywords such as ``token`` or ``gabriel``.
    When fewer than two repositories are provided or ``limit`` is not positive,
    an empty list is returned.
    """

    if limit <= 0:
        return []

    unique = _unique_repos(repos)
    if len(unique) < 2:
        return []

    ranked: list[tuple[int, Suggestion]] = []
    for left, right in combinations(unique, 2):
        suggestion, score = _build_suggestion(left, right)
        ranked.append((score, suggestion))

    ranked.sort(key=lambda item: (-item[0], tuple(item[1]["repos"])))
    return [item[1] for item in ranked[:limit]]


def main(argv: Sequence[str] | None = None) -> None:
    """CLI entry point for printing quest suggestions."""

    parser = argparse.ArgumentParser(
        description="Suggest cross-repo quests",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=get_repo_file(),
        help="Path to repository list",
    )
    parser.add_argument(
        "--limit",
        type=int,
        default=3,
        help="Maximum number of quests to print",
    )
    args = parser.parse_args(argv)

    repos = load_repos(path=args.path)
    suggestions = suggest_cross_repo_quests(repos, limit=args.limit)
    if not suggestions:
        print("No quests available")
        return

    for suggestion in suggestions:
        repos_line = ", ".join(suggestion["repos"])  # type: ignore[index]
        print(f"- {suggestion['summary']}")
        print(f"  repos: {repos_line}")
        print(f"  quest: {suggestion['details']}")
        print()


if __name__ == "__main__":  # pragma: no cover - manual use
    main()
