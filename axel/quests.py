from __future__ import annotations

import argparse
import json
from dataclasses import dataclass
from itertools import combinations
from pathlib import Path
from typing import Iterable, Sequence
from urllib.parse import urlparse

from . import token_place as token_place_integration
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


def _redact_secret(text: str, secret: str | None) -> str:
    """Return ``text`` with ``secret`` removed when present."""

    if not secret or secret not in text:
        return text
    return text.replace(secret, "***")


def _sanitize_suggestions_for_output(
    suggestions: Sequence[Suggestion],
    secret: str | None,
) -> list[Suggestion]:
    """Return sanitized suggestions safe for CLI output."""

    sanitized: list[Suggestion] = []
    for suggestion in suggestions:
        repos_value = suggestion.get("repos")
        if isinstance(repos_value, list):
            repos = [str(repo) for repo in repos_value]
        else:  # pragma: no cover - defensive
            repos = []
        summary_value = suggestion.get("summary")
        details_value = suggestion.get("details")
        summary = summary_value if isinstance(summary_value, str) else ""
        details = details_value if isinstance(details_value, str) else ""
        sanitized.append(
            {
                "repos": repos,
                "summary": _redact_secret(summary, secret),
                "details": _redact_secret(details, secret),
            }
        )
    return sanitized


def _emit_line(text: str, secret: str | None) -> None:
    """Print ``text`` after applying secret redaction."""

    print(_redact_secret(text, secret))


def _build_suggestion(
    left: RepoInfo,
    right: RepoInfo,
    *,
    token_place_base_url: str | None = None,
    token_place_api_key: str | None = None,
) -> tuple[Suggestion, int]:
    ordered = tuple(sorted((left, right), key=lambda info: info.slug.lower()))
    primary, secondary = ordered
    detail, score, featured_model = _select_detail(
        primary,
        secondary,
        token_place_base_url=token_place_base_url,
        token_place_api_key=token_place_api_key,
    )
    repos = [primary.slug, secondary.slug]
    summary = f"Link {primary.slug} ↔ {secondary.slug}"
    if featured_model:
        summary += f" via {featured_model}"
    suggestion: Suggestion = {"repos": repos, "summary": summary, "details": detail}
    return suggestion, score


def _select_detail(
    primary: RepoInfo,
    secondary: RepoInfo,
    *,
    token_place_base_url: str | None = None,
    token_place_api_key: str | None = None,
) -> tuple[str, int, str | None]:
    ordered = ((primary, secondary), (secondary, primary))

    # ``token`` quests must always reference gabriel even when the paired repo
    # also matches a different keyword (e.g. ``blog`` or ``discord``).
    for repo, other in ordered:
        if "token" in repo.slug.lower():
            detail = token_place_integration.quest_detail(
                repo.slug,
                other.slug,
                base_url=token_place_base_url,
                api_key=token_place_api_key,
            )
            featured_model = token_place_integration.get_featured_model(
                base_url=token_place_base_url,
                api_key=token_place_api_key,
            )
            return detail, 1, featured_model

    for repo, other in ordered:
        lower = repo.slug.lower()
        for keyword, template in _KEYWORD_TEMPLATES:
            if keyword in lower:
                return (
                    template.format(primary=repo.slug, secondary=other.slug),
                    1,
                    None,
                )
    return _DEFAULT_DETAIL.format(a=primary.slug, b=secondary.slug), 0, None


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
    repos: Sequence[str],
    *,
    limit: int = 3,
    token_place_base_url: str | None = None,
    token_place_api_key: str | None = None,
) -> list[Suggestion]:
    """Return quests that connect repositories from ``repos``.

    Suggestions are deterministic, highlight at least two repositories, and
    prefer pairs that match known keywords such as ``token`` or ``gabriel``.
    When fewer than two repositories are provided or ``limit`` is not positive,
    an empty list is returned. ``token_place_base_url`` and
    ``token_place_api_key`` forward optional configuration to
    :func:`axel.token_place.quest_detail`, allowing callers to point at custom
    token.place deployments when enriching quest details.
    """

    if limit <= 0:
        return []

    unique = _unique_repos(repos)
    if len(unique) < 2:
        return []

    ranked: list[tuple[int, Suggestion]] = []
    for left, right in combinations(unique, 2):
        suggestion, score = _build_suggestion(
            left,
            right,
            token_place_base_url=token_place_base_url,
            token_place_api_key=token_place_api_key,
        )
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
    parser.add_argument(
        "--token-place-url",
        dest="token_place_url",
        default=None,
        help="token.place base URL (defaults to AXEL_TOKEN_PLACE_URL when unset)",
    )
    parser.add_argument(
        "--token-place-key",
        dest="token_place_key",
        default=None,
        help="token.place API key (defaults to TOKEN_PLACE_API_KEY when unset)",
    )
    parser.add_argument(
        "--json",
        action="store_true",
        help="Output quest suggestions as JSON",
    )
    args = parser.parse_args(argv)

    repos = load_repos(path=args.path)
    suggestions = suggest_cross_repo_quests(
        repos,
        limit=args.limit,
        token_place_base_url=args.token_place_url,
        token_place_api_key=args.token_place_key,
    )
    redaction_secret = args.token_place_key
    if not suggestions:
        if args.json:
            _emit_line("[]", redaction_secret)
        else:
            _emit_line("No quests available", redaction_secret)
        return

    sanitized_for_output = _sanitize_suggestions_for_output(
        suggestions,
        redaction_secret,
    )
    if args.json:
        json_output = json.dumps(
            sanitized_for_output,
            indent=2,
            ensure_ascii=False,
        )
        _emit_line(json_output, redaction_secret)
        return

    for suggestion in sanitized_for_output:
        repos_line = ", ".join(suggestion["repos"])  # type: ignore[index]
        _emit_line(f"- {suggestion['summary']}", redaction_secret)
        _emit_line(f"  repos: {repos_line}", redaction_secret)
        _emit_line(f"  quest: {suggestion['details']}", redaction_secret)
        _emit_line("", None)


if __name__ == "__main__":  # pragma: no cover - manual use
    main()
