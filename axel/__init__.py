"""axel package."""

from axel.repo_manager import (
    add_repo,
    get_repo_file,
    list_repos,
    load_repos,
    remove_repo,
)
from axel.task_manager import (
    add_task,
    complete_task,
    get_task_file,
    list_tasks,
    load_tasks,
)
from .utils import strip_ansi


def run_discord_bot() -> None:
    """Run the Discord bot without requiring ``discord`` at import time."""

    from axel.discord_bot import run

    run()


__all__ = [
    "add_repo",
    "get_repo_file",
    "list_repos",
    "load_repos",
    "remove_repo",
    "run_discord_bot",
    "strip_ansi",
    "add_task",
    "complete_task",
    "get_task_file",
    "list_tasks",
    "load_tasks",
]
