"""axel package."""

from .repo_manager import add_repo, get_repo_file, list_repos, load_repos, remove_repo
from .task_manager import add_task, get_task_file, list_tasks, load_tasks


def run_discord_bot() -> None:
    """Run the Discord bot without requiring ``discord`` at import time."""

    from .discord_bot import run

    run()


__all__ = [
    "add_repo",
    "get_repo_file",
    "list_repos",
    "load_repos",
    "remove_repo",
    "run_discord_bot",
    "add_task",
    "get_task_file",
    "list_tasks",
    "load_tasks",
]
