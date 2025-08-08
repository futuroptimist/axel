import argparse
import json
import os
from pathlib import Path
from typing import Dict, List

DEFAULT_TASK_FILE = Path(__file__).resolve().parent.parent / "tasks.json"


def get_task_file() -> Path:
    """Return the task list path, honoring ``AXEL_TASK_FILE`` if set."""
    return Path(os.getenv("AXEL_TASK_FILE", DEFAULT_TASK_FILE)).expanduser()


def load_tasks(path: Path | None = None) -> List[Dict]:
    """Load tasks from a JSON file."""
    if path is None:
        path = get_task_file()
    if not path.exists():
        return []
    with path.open() as f:
        return json.load(f)


def add_task(description: str, path: Path | None = None) -> List[Dict]:
    """Add a task with ``description`` to the JSON database."""
    if path is None:
        path = get_task_file()
    path.parent.mkdir(parents=True, exist_ok=True)
    tasks = load_tasks(path)
    next_id = max((t["id"] for t in tasks), default=0) + 1
    task = {"id": next_id, "description": description, "completed": False}
    tasks.append(task)
    path.write_text(json.dumps(tasks, indent=2) + "\n")
    return tasks


def list_tasks(path: Path | None = None) -> List[Dict]:
    """Return the list of tasks."""
    return load_tasks(path)


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

    args = parser.parse_args(argv)

    if args.cmd == "add":
        tasks = add_task(args.description, path=args.path)
    else:
        tasks = list_tasks(path=args.path)
    for task in tasks:
        print(f"{task['id']} {task['description']}")


if __name__ == "__main__":  # pragma: no cover - manual use
    main()
