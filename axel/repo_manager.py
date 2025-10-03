import argparse
import os
from pathlib import Path
from typing import List

import requests

DEFAULT_REPO_FILE = Path(__file__).resolve().parent.parent / "repos.txt"


def get_repo_file() -> Path:
    """Return the repository list path, honoring ``AXEL_REPO_FILE`` if set.

    ``AXEL_REPO_FILE`` may include a ``~`` to reference the user's home directory.
    """
    return Path(os.getenv("AXEL_REPO_FILE", DEFAULT_REPO_FILE)).expanduser()


def _resolve_path(path: Path | None) -> Path:
    """Return ``path`` with ``~`` expanded, defaulting to :func:`get_repo_file`."""

    if path is None:
        return get_repo_file()
    return Path(path).expanduser()


def load_repos(path: Path | None = None) -> List[str]:
    """Load repository URLs from a text file.

    Trailing slashes are stripped to keep entries canonical and duplicates are
    removed case-insensitively while preserving the first occurrence's case.
    The resulting list is sorted alphabetically, ignoring case.
    """
    path = _resolve_path(path)
    if not path.exists():
        return []
    repos: List[str] = []
    seen: set[str] = set()
    with path.open() as f:
        for line in f:
            # Allow comments using ``#`` and strip inline notes
            line = line.split("#", 1)[0].strip().rstrip("/")
            key = line.lower()
            if line and key not in seen:
                repos.append(line)
                seen.add(key)
    repos.sort(key=str.lower)
    return repos


def add_repo(url: str, path: Path | None = None) -> List[str]:
    """Add a repository URL to the list if not already present.

    ``url`` must include the scheme (for example ``https://``). Trailing slashes
    in ``url`` are removed before processing. Comparison is case-insensitive. The
    resulting list is kept sorted alphabetically regardless of case.
    """
    path = _resolve_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    url = url.strip().rstrip("/")
    if "://" not in url:
        raise ValueError(
            "url must include scheme, e.g., 'https://github.com/user/repo'"
        )
    repos = load_repos(path)
    seen = {r.lower() for r in repos}
    if url and url.lower() not in seen:
        repos.append(url)
        repos.sort(key=str.lower)
        path.write_text("\n".join(repos) + "\n")
    return repos


def remove_repo(url: str, path: Path | None = None) -> List[str]:
    """Remove a repository URL from the list if present.

    Trailing slashes in ``url`` are removed before processing and comparison is
    case-insensitive. The remaining list is kept sorted alphabetically,
    ignoring case.
    """
    path = _resolve_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    url = url.strip().rstrip("/")
    repos = load_repos(path)
    removed = False
    for existing in repos:
        if existing.lower() == url.lower():
            repos.remove(existing)
            removed = True
            break
    if removed:
        repos.sort(key=str.lower)
        text = "\n".join(repos)
        if text:
            text += "\n"
        path.write_text(text)
    return repos


def list_repos(path: Path | None = None) -> List[str]:
    """Return the list of repository URLs."""
    return load_repos(path)


def fetch_repo_urls(
    token: str | None = None, visibility: str | None = None
) -> List[str]:
    """Fetch repositories for the authenticated user via GitHub API.

    The token may be provided directly or read from ``GH_TOKEN`` or
    ``GITHUB_TOKEN``. When ``visibility`` is set to ``"public"`` or
    ``"private"``, only repositories matching that visibility are returned.
    ``None`` (the default) requests all repositories.
    """
    if token is None:
        token = os.getenv("GH_TOKEN") or os.getenv("GITHUB_TOKEN")
    if not token:
        raise RuntimeError("GH_TOKEN or GITHUB_TOKEN is required to fetch repositories")
    headers = {"Authorization": f"token {token}"}
    page = 1
    repos: List[str] = []
    while True:
        params = {"per_page": 100, "page": page}
        if visibility:
            params["visibility"] = visibility
        resp = requests.get(
            "https://api.github.com/user/repos",
            headers=headers,
            params=params,
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        repos.extend(repo["html_url"] for repo in data)
        page += 1
    repos.sort(key=str.lower)
    return repos


def fetch_repos(
    path: Path | None = None,
    token: str | None = None,
    visibility: str | None = None,
) -> List[str]:
    """Fetch repo URLs and replace the repo list file.

    ``token`` overrides ``GH_TOKEN``/``GITHUB_TOKEN`` when provided.
    ``visibility`` filters repositories returned by the GitHub API.
    """
    path = _resolve_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    repos = fetch_repo_urls(token=token, visibility=visibility)
    text = "\n".join(repos)
    if text:
        text += "\n"
    path.write_text(text)
    return repos


def main(argv: List[str] | None = None) -> None:
    """Simple command-line interface for managing repos."""
    parser = argparse.ArgumentParser(description="Manage repo list")
    parser.add_argument(
        "--path",
        type=Path,
        default=get_repo_file(),
        help="Path to repo list",
    )
    sub = parser.add_subparsers(dest="cmd")

    add_p = sub.add_parser("add", help="Add a repository URL")
    add_p.add_argument("url")

    remove_p = sub.add_parser("remove", help="Remove a repository URL")
    remove_p.add_argument("url")

    sub.add_parser("list", help="List repositories")
    fetch_p = sub.add_parser("fetch", help="Fetch repositories from GitHub")
    fetch_p.add_argument("--token", help="GitHub token", default=None)
    fetch_p.add_argument(
        "--visibility",
        choices=["public", "private", "all"],
        help="Limit fetched repositories by visibility",
        default=None,
    )

    args = parser.parse_args(argv)

    if args.cmd == "add":
        repos = add_repo(args.url, path=args.path)
    elif args.cmd == "remove":
        repos = remove_repo(args.url, path=args.path)
    elif args.cmd == "fetch":
        repos = fetch_repos(
            path=args.path, token=args.token, visibility=args.visibility
        )
    else:
        repos = list_repos(path=args.path)
    for repo in repos:
        print(repo)


if __name__ == "__main__":  # pragma: no cover - manual use
    main()
