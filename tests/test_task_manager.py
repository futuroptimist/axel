import json
import subprocess
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))  # noqa: E402
import pytest  # noqa: E402

from axel import add_task, complete_task, list_tasks, load_tasks  # noqa: E402


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


def test_complete_task(tmp_path: Path) -> None:
    file = tmp_path / "tasks.json"
    add_task("write docs", path=file)
    add_task("write code", path=file)
    complete_task(1, path=file)
    assert load_tasks(path=file) == [
        {"id": 1, "description": "write docs", "completed": True},
        {"id": 2, "description": "write code", "completed": False},
    ]


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


def test_cli_complete(tmp_path: Path) -> None:
    file = tmp_path / "tasks.json"
    add_task("write docs", path=file)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "axel.task_manager",
            "--path",
            str(file),
            "complete",
            "1",
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(Path(__file__).resolve().parents[1])},
        check=True,
    )
    data = json.loads(file.read_text())
    assert data == [
        {"id": 1, "description": "write docs", "completed": True},
    ]
    assert "1 write docs" in result.stdout


def test_env_default_var(monkeypatch, tmp_path: Path) -> None:
    """``AXEL_TASK_FILE`` controls the default task file."""
    task_file = tmp_path / "tasks.json"
    monkeypatch.setenv("AXEL_TASK_FILE", str(task_file))
    import axel.task_manager as tm

    tm.add_task("dyn")
    assert task_file.read_text().strip()


def test_load_tasks_empty_file(tmp_path: Path) -> None:
    """Empty JSON files yield an empty task list."""
    file = tmp_path / "tasks.json"
    file.write_text("")
    assert load_tasks(path=file) == []


def test_load_tasks_non_list(tmp_path: Path) -> None:
    """Non-list JSON structures load as an empty list."""
    file = tmp_path / "tasks.json"
    file.write_text('{"a": 1}')
    assert load_tasks(path=file) == []


def test_load_tasks_default_path(monkeypatch, tmp_path: Path) -> None:
    """``load_tasks`` uses ``AXEL_TASK_FILE`` when no path is provided."""
    file = tmp_path / "tasks.json"
    monkeypatch.setenv("AXEL_TASK_FILE", str(file))
    import axel.task_manager as tm

    assert tm.load_tasks() == []


def test_complete_task_default_path(monkeypatch, tmp_path: Path) -> None:
    """``complete_task`` honors ``AXEL_TASK_FILE`` when ``path`` is omitted."""
    file = tmp_path / "tasks.json"
    monkeypatch.setenv("AXEL_TASK_FILE", str(file))
    import axel.task_manager as tm

    tm.add_task("write docs")
    tm.complete_task(1)
    assert tm.load_tasks() == [
        {"id": 1, "description": "write docs", "completed": True},
    ]


def test_complete_task_missing_id(tmp_path: Path) -> None:
    """Completing an unknown task id raises ``ValueError``."""
    file = tmp_path / "tasks.json"
    add_task("write docs", path=file)
    with pytest.raises(ValueError):
        complete_task(2, path=file)


def test_list_tasks(tmp_path: Path) -> None:
    """``list_tasks`` returns the stored tasks."""
    file = tmp_path / "tasks.json"
    add_task("write docs", path=file)
    assert list_tasks(path=file) == [
        {"id": 1, "description": "write docs", "completed": False},
    ]


def test_main_branches(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    """``main`` handles add, complete and list commands."""
    file = tmp_path / "tasks.json"
    import axel.task_manager as tm

    tm.main(["--path", str(file), "add", "write docs"])
    assert "1 write docs" in capsys.readouterr().out
    tm.main(["--path", str(file), "complete", "1"])
    assert "1 write docs" in capsys.readouterr().out
    tm.main(["--path", str(file), "list"])
    assert "1 write docs" in capsys.readouterr().out
