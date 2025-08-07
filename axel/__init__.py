"""axel package."""

from .discord_bot import run as run_discord_bot
from .repo_manager import (
    add_repo,
    fetch_repos,
    get_repo_file,
    list_repos,
    load_repos,
    remove_repo,
)

__all__ = [
    "add_repo",
    "fetch_repos",
    "get_repo_file",
    "list_repos",
    "load_repos",
    "remove_repo",
    "run_discord_bot",
]
