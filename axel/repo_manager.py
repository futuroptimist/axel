from pathlib import Path
from typing import List

DEFAULT_REPO_FILE = Path(__file__).resolve().parent.parent / "repos.txt"


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


def list_repos(path: Path = DEFAULT_REPO_FILE) -> List[str]:
    """Return the list of repository URLs."""
    return load_repos(path)


if __name__ == "__main__":
    for repo in list_repos():
        print(repo)
