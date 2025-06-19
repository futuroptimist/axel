from pathlib import Path
from typing import List

import argparse
import os

DEFAULT_REPO_FILE = Path(
    os.getenv(
        "AXEL_REPO_FILE",
        Path(__file__).resolve().parent.parent / "repos.txt",
    )
)


def load_repos(path: Path = DEFAULT_REPO_FILE) -> List[str]:
    """Load repository URLs from a text file."""
    if not path.exists():
        return []
    with path.open() as f:
        return [line.strip() for line in f if line.strip()]


def add_repo(url: str, path: Path = DEFAULT_REPO_FILE) -> List[str]:
    """Add a repository URL to the list if not already present."""
    repos = load_repos(path)
    if url not in repos:
        repos.append(url)
        path.write_text("\n".join(repos))
    return repos


def remove_repo(url: str, path: Path = DEFAULT_REPO_FILE) -> List[str]:
    """Remove a repository URL from the list if present."""
    repos = load_repos(path)
    if url in repos:
        repos.remove(url)
        path.write_text("\n".join(repos))
    return repos


def list_repos(path: Path = DEFAULT_REPO_FILE) -> List[str]:
    """Return the list of repository URLs."""
    return load_repos(path)


def main(argv: List[str] | None = None) -> None:
    """Simple command-line interface for managing repos."""
    parser = argparse.ArgumentParser(description="Manage repo list")
    parser.add_argument(
        "--path",
        type=Path,
        default=DEFAULT_REPO_FILE,
        help="Path to repo list",
    )
    sub = parser.add_subparsers(dest="cmd")

    add_p = sub.add_parser("add", help="Add a repository URL")
    add_p.add_argument("url")

    remove_p = sub.add_parser("remove", help="Remove a repository URL")
    remove_p.add_argument("url")

    sub.add_parser("list", help="List repositories")

    args = parser.parse_args(argv)

    if args.cmd == "add":
        repos = add_repo(args.url, path=args.path)
    elif args.cmd == "remove":
        repos = remove_repo(args.url, path=args.path)
    else:
        repos = list_repos(path=args.path)
    for repo in repos:
        print(repo)


if __name__ == "__main__":  # pragma: no cover - manual use
    main()
