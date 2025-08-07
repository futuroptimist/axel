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


def load_repos(path: Path | None = None) -> List[str]:
    """Load repository URLs from a text file."""
    if path is None:
        path = get_repo_file()
    if not path.exists():
        return []
    with path.open() as f:
        return [line.strip() for line in f if line.strip()]


def add_repo(url: str, path: Path | None = None) -> List[str]:
    """Add a repository URL to the list if not already present."""
    if path is None:
        path = get_repo_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    url = url.strip()
    repos = load_repos(path)
    if url and url not in repos:
        repos.append(url)
        path.write_text("\n".join(repos) + "\n")
    return repos


def remove_repo(url: str, path: Path | None = None) -> List[str]:
    """Remove a repository URL from the list if present."""
    if path is None:
        path = get_repo_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    url = url.strip()
    repos = load_repos(path)
    if url in repos:
        repos.remove(url)
        text = "\n".join(repos)
        if text:
            text += "\n"
        path.write_text(text)
    return repos


def list_repos(path: Path | None = None) -> List[str]:
    """Return the list of repository URLs."""
    return load_repos(path)


def fetch_repos(path: Path | None = None, token: str | None = None) -> List[str]:
    """Fetch repositories from GitHub and overwrite the repo list."""
    if token is None:
        token = os.getenv("GH_TOKEN")
    if not token:
        raise RuntimeError("GH_TOKEN environment variable is required")
    headers = {
        "Authorization": f"Bearer {token}",
        "Accept": "application/vnd.github+json",
    }
    repos: List[str] = []
    page = 1
    while True:
        resp = requests.get(
            "https://api.github.com/user/repos",
            headers=headers,
            params={"per_page": 100, "page": page},
            timeout=10,
        )
        resp.raise_for_status()
        data = resp.json()
        if not data:
            break
        repos.extend(item["html_url"] for item in data if "html_url" in item)
        page += 1
    if path is None:
        path = get_repo_file()
    path.parent.mkdir(parents=True, exist_ok=True)
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
    sub.add_parser("fetch", help="Fetch repositories from GitHub")

    args = parser.parse_args(argv)

    if args.cmd == "add":
        repos = add_repo(args.url, path=args.path)
    elif args.cmd == "remove":
        repos = remove_repo(args.url, path=args.path)
    elif args.cmd == "fetch":
        repos = fetch_repos(path=args.path)
    else:
        repos = list_repos(path=args.path)
    for repo in repos:
        print(repo)


if __name__ == "__main__":  # pragma: no cover - manual use
    main()
