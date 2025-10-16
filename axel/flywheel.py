"""Helpers for auditing repos against the flywheel CI template."""

from __future__ import annotations

import argparse
from pathlib import Path
from typing import Dict, List, Sequence
from urllib.parse import urlparse

import requests

from .repo_manager import get_repo_file, load_repos

REQUIRED_WORKFLOWS: tuple[str, ...] = (
    "01-lint-format.yml",
    "02-tests.yml",
)
_API_TIMEOUT = 10


def _slug_from_url(url: str) -> str:
    """Return ``owner/repo`` slug for ``url`` or raise ``ValueError``."""

    def _clean_repo(segment: str) -> str:
        """Return the repository portion of ``segment`` without a ``.git`` suffix."""

        repo = segment.split("/", 1)[0]
        return repo[:-4] if repo.endswith(".git") else repo

    parsed = urlparse(url)
    if parsed.netloc:
        parts = [part for part in parsed.path.split("/") if part]
        if len(parts) >= 2:
            owner = parts[0]
            repo = _clean_repo(parts[1])
            return f"{owner}/{repo}"
    cleaned = url.strip().strip("/")
    if cleaned.count("/") >= 1:
        owner, repo = cleaned.split("/", 1)
        return f"{owner}/{_clean_repo(repo)}"
    raise ValueError(f"Cannot determine repository slug from: {url}")


def _workflow_exists(slug: str, filename: str, token: str | None) -> bool:
    """Return ``True`` when ``filename`` exists in the repo's workflow directory."""

    headers = {"Accept": "application/vnd.github+json"}
    if token:
        headers["Authorization"] = f"token {token}"
    url = f"https://api.github.com/repos/{slug}/contents/.github/workflows/{filename}"
    response = requests.get(url, headers=headers, timeout=_API_TIMEOUT)
    if response.status_code == 200:
        return True
    if response.status_code == 404:
        return False
    if response.status_code in {401, 403}:
        location = f"{slug}/.github/workflows/{filename}"
        raise RuntimeError(
            "GitHub returned HTTP "
            f"{response.status_code} for {location}. "
            "Provide a token via --token or set GH_TOKEN/GITHUB_TOKEN "
            "to access private repositories."
        )
    response.raise_for_status()
    return False  # pragma: no cover - raise_for_status always raises here


def evaluate_flywheel_alignment(
    repos: Sequence[str], token: str | None = None
) -> List[Dict[str, object]]:
    """Return flywheel workflow coverage for each repository in ``repos``."""

    results: List[Dict[str, object]] = []
    for entry in repos:
        try:
            slug = _slug_from_url(entry)
        except ValueError:
            slug = entry.strip().strip("/") or entry
        statuses: Dict[str, bool] = {}
        for workflow in REQUIRED_WORKFLOWS:
            statuses[workflow] = _workflow_exists(slug, workflow, token)
        missing = [name for name, present in statuses.items() if not present]
        results.append(
            {
                "repo": slug,
                "workflows": statuses,
                "missing": missing,
                "aligned": not missing,
            }
        )
    return results


def main(argv: Sequence[str] | None = None) -> None:
    """CLI entry point for reporting flywheel workflow alignment."""

    parser = argparse.ArgumentParser(
        description="Check repos for flywheel workflow coverage",
    )
    parser.add_argument(
        "--path",
        type=Path,
        default=get_repo_file(),
        help="Repository list (defaults to AXEL_REPO_FILE or repos.txt)",
    )
    parser.add_argument(
        "--token",
        default=None,
        help="GitHub token for authenticated requests",
    )
    args = parser.parse_args(argv)

    repos = load_repos(path=args.path)
    if not repos:
        print("No repositories to evaluate")
        return

    results = evaluate_flywheel_alignment(repos, token=args.token)
    for result in results:
        slug = str(result["repo"])
        if result.get("aligned"):
            print(f"{slug}: aligned")
            continue
        missing = ", ".join(result.get("missing", []))
        print(f"{slug}: missing {missing}")


if __name__ == "__main__":  # pragma: no cover - CLI use only
    main()
