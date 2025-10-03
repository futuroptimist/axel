import argparse
import json
import os
from pathlib import Path
from typing import Dict, List

DEFAULT_TASK_FILE = Path(__file__).resolve().parent.parent / "tasks.json"


def get_task_file() -> Path:
    """Return the task list path, honoring ``AXEL_TASK_FILE`` if set."""
    return Path(os.getenv("AXEL_TASK_FILE", DEFAULT_TASK_FILE)).expanduser()


def _resolve_path(path: Path | None) -> Path:
    """Return ``path`` with ``~`` expanded, defaulting to :func:`get_task_file`."""

    if path is None:
        return get_task_file()
    return Path(path).expanduser()


def load_tasks(path: Path | None = None) -> List[Dict]:
    """Load tasks from a JSON file.

    Returns an empty list for missing, empty, invalid, or non-list JSON files.
    """
    path = _resolve_path(path)
    if not path.exists():
        return []
    try:
        with path.open(encoding="utf-8") as f:
            data = json.load(f)
    except json.JSONDecodeError:
        # Treat empty or corrupt files as no tasks
        return []
    if not isinstance(data, list):
        return []
    return data


def add_task(description: str, path: Path | None = None) -> List[Dict]:
    """Add a task with ``description`` to the JSON database.

    ``description`` is stripped of surrounding whitespace and must not be empty.
    """
    path = _resolve_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    description = description.strip()
    if not description:
        raise ValueError("description must not be empty")
    tasks = load_tasks(path)
    next_id = max((t["id"] for t in tasks), default=0) + 1
    task = {"id": next_id, "description": description, "completed": False}
    tasks.append(task)
    path.write_text(
        json.dumps(tasks, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return tasks


def complete_task(task_id: int, path: Path | None = None) -> List[Dict]:
    """Mark the task with ``task_id`` as completed."""
    path = _resolve_path(path)
    tasks = load_tasks(path)
    for task in tasks:
        if task["id"] == task_id:
            task["completed"] = True
            path.write_text(
                json.dumps(tasks, indent=2, ensure_ascii=False) + "\n",
                encoding="utf-8",
            )
            return tasks
    raise ValueError(f"task id {task_id} not found")


def remove_task(task_id: int, path: Path | None = None) -> List[Dict]:
    """Remove the task with ``task_id`` from the JSON database."""
    path = _resolve_path(path)
    tasks = load_tasks(path)
    new_tasks = [t for t in tasks if t["id"] != task_id]
    if len(new_tasks) == len(tasks):
        raise ValueError(f"task id {task_id} not found")
    path.write_text(
        json.dumps(new_tasks, indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return new_tasks


def list_tasks(path: Path | None = None) -> List[Dict]:
    """Return the list of tasks."""
    return load_tasks(path)


def clear_tasks(path: Path | None = None) -> List[Dict]:
    """Remove all tasks from the JSON database."""
    path = _resolve_path(path)
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text("[]\n", encoding="utf-8")
    return []


def main(argv: List[str] | None = None) -> None:
    """Simple command-line interface for managing tasks."""
    parser = argparse.ArgumentParser(description="Manage task list")
    parser.add_argument(
        "--path",
        type=Path,
        default=get_task_file(),
        help="Path to task database",
    )
    sub = parser.add_subparsers(dest="cmd")

    add_p = sub.add_parser("add", help="Add a task")
    add_p.add_argument("description")

    sub.add_parser("list", help="List tasks")

    complete_p = sub.add_parser("complete", help="Mark a task as completed")
    complete_p.add_argument("id", type=int)

    remove_p = sub.add_parser("remove", help="Remove a task")
    remove_p.add_argument("id", type=int)

    sub.add_parser("clear", help="Remove all tasks")

    args = parser.parse_args(argv)

    if args.cmd == "add":
        tasks = add_task(args.description, path=args.path)
    elif args.cmd == "complete":
        tasks = complete_task(args.id, path=args.path)
    elif args.cmd == "remove":
        tasks = remove_task(args.id, path=args.path)
    elif args.cmd == "clear":
        tasks = clear_tasks(path=args.path)
    else:
        tasks = list_tasks(path=args.path)
    for task in tasks:
        status = "[x]" if task["completed"] else "[ ]"
        print(f"{task['id']} {status} {task['description']}")


if __name__ == "__main__":  # pragma: no cover - manual use
    main()
