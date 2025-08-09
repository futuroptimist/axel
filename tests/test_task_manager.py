import json
import subprocess
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))  # noqa: E402
import pytest  # noqa: E402

from axel import add_task, load_tasks  # noqa: E402


def test_add_and_load(tmp_path: Path) -> None:
    file = tmp_path / "tasks.json"
    add_task("write docs", path=file)
    assert load_tasks(path=file) == [
        {"id": 1, "description": "write docs", "completed": False},
    ]


def test_add_task_strips_whitespace(tmp_path: Path) -> None:
    file = tmp_path / "tasks.json"
    add_task("  write docs  \n", path=file)
    assert load_tasks(path=file) == [
        {"id": 1, "description": "write docs", "completed": False},
    ]


def test_add_task_rejects_empty_description(tmp_path: Path) -> None:
    file = tmp_path / "tasks.json"
    with pytest.raises(ValueError):
        add_task("   \n", path=file)


def test_cli_add(tmp_path: Path) -> None:
    file = tmp_path / "tasks.json"
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "axel.task_manager",
            "--path",
            str(file),
            "add",
            "write code",
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(Path(__file__).resolve().parents[1])},
        check=True,
    )
    data = json.loads(file.read_text())
    assert data == [
        {"id": 1, "description": "write code", "completed": False},
    ]
    assert "1 write code" in result.stdout
