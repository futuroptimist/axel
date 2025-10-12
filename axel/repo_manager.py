import argparse
import os
import sys
from pathlib import Path
from typing import List, Sequence

import requests

DEFAULT_REPO_FILE = Path(__file__).resolve().parent.parent / "repos.txt"
_AUTO_FETCH_ENV = "AXEL_AUTO_FETCH_REPOS"


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
    The resulting list is sorted alphabetically, ignoring case. When the target
    file is missing and ``AXEL_AUTO_FETCH_REPOS`` is set to a truthy value
    (``1``, ``true``, ``yes`` or ``on``), the GitHub API is queried via
    :func:`fetch_repos` to populate the list automatically.
    """
    path = _resolve_path(path)
    if not path.exists():
        flag = os.getenv(_AUTO_FETCH_ENV, "").strip().lower()
        if flag in {"1", "true", "yes", "on"}:
            try:
                return fetch_repos(path=path)
            except (RuntimeError, requests.RequestException):
                return []
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
    seen: set[str] = set()
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
        for repo in data:
            url = repo.get("html_url") if isinstance(repo, dict) else None
            if not isinstance(url, str):
                continue
            cleaned = url.strip().rstrip("/")
            if not cleaned:
                continue
            key = cleaned.lower()
            if key in seen:
                continue
            seen.add(key)
            repos.append(cleaned)
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


def main(argv: Sequence[str] | None = None) -> None:
    """Simple command-line interface for managing repos."""
    if argv is None:
        argv = sys.argv[1:]
    else:
        argv = list(argv)

    args_list: list[str] = list(argv)
    path_override: str | None = None
    cleaned: list[str] = []
    i = 0
    while i < len(args_list):
        arg = args_list[i]
        if arg == "--path":
            if i + 1 >= len(args_list):
                cleaned.append(arg)
                i += 1
                continue
            path_override = args_list[i + 1]
            i += 2
            continue
        if arg.startswith("--path="):
            path_override = arg.split("=", 1)[1]
            i += 1
            continue
        cleaned.append(arg)
        i += 1

    parser = argparse.ArgumentParser(description="Manage repo list")
    parser.add_argument(
        "--path",
        type=Path,
        default=None,
        help="Path to repo list (defaults to AXEL_REPO_FILE or repos.txt)",
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

    args = parser.parse_args(cleaned)

    if path_override is not None:
        path = Path(path_override).expanduser()
    elif args.path is not None:
        path = Path(args.path).expanduser()
    else:
        path = get_repo_file()
    args.path = path

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
