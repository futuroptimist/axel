"""axel package."""

from .critic import (
    analyze_orthogonality,
    self_evaluate_merge_conflicts,
    track_prompt_saturation,
)
from .flywheel import evaluate_flywheel_alignment
from .merge import (
    MergePlan,
    load_merge_policy,
    plan_merge_actions,
    speculative_merge_check,
)
from .quests import suggest_cross_repo_quests
from .repo_manager import add_repo, get_repo_file, list_repos, load_repos, remove_repo
from .task_manager import (
    add_task,
    clear_tasks,
    complete_task,
    get_task_file,
    list_tasks,
    load_tasks,
    remove_task,
)
from .utils import strip_ansi


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
    "strip_ansi",
    "suggest_cross_repo_quests",
    "MergePlan",
    "speculative_merge_check",
    "plan_merge_actions",
    "load_merge_policy",
    "evaluate_flywheel_alignment",
    "analyze_orthogonality",
    "track_prompt_saturation",
    "self_evaluate_merge_conflicts",
    "add_task",
    "complete_task",
    "get_task_file",
    "list_tasks",
    "load_tasks",
    "remove_task",
    "clear_tasks",
]
