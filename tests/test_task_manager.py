import json
import subprocess
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))  # noqa: E402
import pytest  # noqa: E402

from axel import (  # noqa: E402
    add_task,
    clear_tasks,
    complete_task,
    list_tasks,
    load_tasks,
    remove_task,
)


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


def test_add_task_preserves_unicode(tmp_path: Path) -> None:
    """Unicode descriptions are stored without escapes."""
    file = tmp_path / "tasks.json"
    add_task("español café", path=file)
    text = file.read_text(encoding="utf-8")
    assert "español café" in text
    assert "\\u" not in text


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


def test_remove_task(tmp_path: Path) -> None:
    file = tmp_path / "tasks.json"
    add_task("write docs", path=file)
    add_task("write code", path=file)
    remove_task(1, path=file)
    assert load_tasks(path=file) == [
        {"id": 2, "description": "write code", "completed": False},
    ]


def test_remove_task_missing_id(tmp_path: Path) -> None:
    file = tmp_path / "tasks.json"
    add_task("write docs", path=file)
    with pytest.raises(ValueError):
        remove_task(2, path=file)


def test_add_task_expands_user_home(monkeypatch, tmp_path: Path) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    target = Path("~/tasks.json")
    add_task("home scoped", path=target)
    expected = tmp_path / "tasks.json"
    assert expected.exists()
    tasks = load_tasks(path=target)
    assert tasks == [
        {"id": 1, "description": "home scoped", "completed": False},
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
    assert "1 [ ] write code" in result.stdout


def test_main_list_supports_json_output(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from axel import task_manager

    tasks_file = tmp_path / "tasks.json"
    add_task("write docs", path=tasks_file)

    task_manager.main(
        [
            "list",
            "--path",
            str(tasks_file),
            "--json",
        ]
    )

    output = capsys.readouterr().out.strip()
    assert json.loads(output) == [
        {"id": 1, "description": "write docs", "completed": False},
    ]


def test_main_add_accepts_path_after_subcommand(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    from axel.task_manager import main

    file = tmp_path / "tasks.json"

    main(
        [
            "add",
            "write docs",
            "--path",
            str(file),
        ]
    )

    assert load_tasks(path=file) == [
        {"id": 1, "description": "write docs", "completed": False},
    ]
    assert "1 [ ] write docs" in capsys.readouterr().out


def test_main_add_uses_default_task_file(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from axel import task_manager

    default_file = tmp_path / "tasks.json"
    monkeypatch.setattr(task_manager, "get_task_file", lambda: default_file)

    task_manager.main(["add", "write docs"])

    assert load_tasks(path=default_file) == [
        {"id": 1, "description": "write docs", "completed": False},
    ]


def test_main_add_supports_path_equals_form(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from axel import task_manager

    home = tmp_path / "home"
    home.mkdir()
    monkeypatch.setenv("HOME", str(home))

    target = Path("~") / "nested" / "tasks.json"

    task_manager.main(
        [
            "add",
            "write docs",
            f"--path={target}",
        ]
    )

    expected_file = home / "nested" / "tasks.json"
    assert load_tasks(path=expected_file) == [
        {"id": 1, "description": "write docs", "completed": False},
    ]


def test_main_add_accepts_path_before_subcommand(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    from axel import task_manager

    class SneakyStr(str):
        def __eq__(self, other: object) -> bool:
            return False

        __hash__ = str.__hash__

    file = tmp_path / "tasks.json"
    argv = [
        SneakyStr("--path"),
        str(file),
        "add",
        "write docs",
    ]

    task_manager.main(argv)

    assert load_tasks(path=file) == [
        {"id": 1, "description": "write docs", "completed": False},
    ]


def test_main_uses_sys_argv_when_none(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import types

    from axel import task_manager

    file = tmp_path / "tasks.json"

    monkeypatch.setattr(
        task_manager,
        "sys",
        types.SimpleNamespace(
            argv=[
                "prog",
                "add",
                "write docs",
                "--path",
                str(file),
            ]
        ),
    )

    task_manager.main(None)

    assert load_tasks(path=file) == [
        {"id": 1, "description": "write docs", "completed": False},
    ]


def test_main_rejects_path_without_value() -> None:
    from axel.task_manager import main

    with pytest.raises(SystemExit) as excinfo:
        main(["add", "write docs", "--path"])

    assert excinfo.value.code != 0


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
    assert "1 [x] write docs" in result.stdout


def test_cli_remove(tmp_path: Path) -> None:
    file = tmp_path / "tasks.json"
    add_task("write docs", path=file)
    add_task("write code", path=file)
    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "axel.task_manager",
            "--path",
            str(file),
            "remove",
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
        {"id": 2, "description": "write code", "completed": False},
    ]
    assert "2 [ ] write code" in result.stdout


def test_main_remove(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    file = tmp_path / "tasks.json"
    add_task("write docs", path=file)
    add_task("write code", path=file)
    from axel.task_manager import main

    main(["--path", str(file), "remove", "1"])
    assert load_tasks(path=file) == [
        {"id": 2, "description": "write code", "completed": False},
    ]
    assert "2 [ ] write code" in capsys.readouterr().out


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


def test_load_tasks_invalid_json(tmp_path: Path) -> None:
    """Corrupt JSON files are treated as having no tasks."""
    file = tmp_path / "tasks.json"
    file.write_text("{invalid}")
    assert load_tasks(path=file) == []


def test_load_tasks_non_list_json(tmp_path: Path) -> None:
    """Non-list JSON structures are treated as having no tasks."""
    file = tmp_path / "tasks.json"
    file.write_text("{}")
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


def test_remove_task_default_path(monkeypatch, tmp_path: Path) -> None:
    """``remove_task`` honors ``AXEL_TASK_FILE`` when ``path`` is omitted."""
    file = tmp_path / "tasks.json"
    monkeypatch.setenv("AXEL_TASK_FILE", str(file))
    import axel.task_manager as tm

    tm.add_task("write docs")
    tm.add_task("write code")
    tm.remove_task(1)
    assert tm.load_tasks() == [
        {"id": 2, "description": "write code", "completed": False},
    ]


def test_list_tasks_default_path(monkeypatch, tmp_path: Path) -> None:
    """``list_tasks`` honors ``AXEL_TASK_FILE`` when ``path`` is omitted."""
    file = tmp_path / "tasks.json"
    monkeypatch.setenv("AXEL_TASK_FILE", str(file))
    import axel.task_manager as tm

    tm.add_task("write docs")
    assert tm.list_tasks() == [
        {"id": 1, "description": "write docs", "completed": False},
    ]


def test_clear_tasks_default_path(monkeypatch, tmp_path: Path) -> None:
    """``clear_tasks`` honors ``AXEL_TASK_FILE`` when ``path`` is omitted."""
    file = tmp_path / "tasks.json"
    monkeypatch.setenv("AXEL_TASK_FILE", str(file))
    import axel.task_manager as tm

    tm.add_task("write docs")
    tm.clear_tasks()
    assert tm.load_tasks() == []


def test_apply_sampling_edge_cases() -> None:
    """Task sampling helper should mirror repo sampling edge cases."""

    import axel.task_manager as tm

    tasks = [
        {"id": 1},
        {"id": 2},
        {"id": 3},
    ]

    assert tm._apply_sampling(tasks, sample=None, seed=42) == tasks
    assert tm._apply_sampling(tasks, sample=0, seed=42) == []
    assert tm._apply_sampling(tasks, sample=5, seed=42) == tasks


def test_apply_sampling_deterministic() -> None:
    """Sampling with the same seed should produce stable selections."""

    import axel.task_manager as tm

    tasks = [
        {"id": 1},
        {"id": 2},
        {"id": 3},
        {"id": 4},
    ]

    first = tm._apply_sampling(tasks, sample=2, seed=99)
    second = tm._apply_sampling(tasks, sample=2, seed=99)

    assert first == second
    assert [task["id"] for task in first] == [task["id"] for task in second]


def test_main_list_supports_sampling(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """``task_manager.main`` should apply sampling before printing tasks."""

    file = tmp_path / "tasks.json"
    add_task("write docs", path=file)
    add_task("write code", path=file)
    add_task("write tests", path=file)

    import axel.task_manager as tm

    tasks = tm.load_tasks(path=file)
    expected = tm._apply_sampling(tasks, sample=2, seed=7)

    from axel.task_manager import main

    main(
        [
            "--path",
            str(file),
            "list",
            "--sample",
            "2",
            "--seed",
            "7",
        ]
    )

    output = capsys.readouterr().out.strip().splitlines()
    assert len(output) == 2
    printed_ids = [int(line.split()[0]) for line in output]
    assert printed_ids == [task["id"] for task in expected]


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
    assert "1 [ ] write docs" in capsys.readouterr().out
    tm.main(["--path", str(file), "complete", "1"])
    assert "1 [x] write docs" in capsys.readouterr().out
    tm.main(["--path", str(file), "list"])
    assert "1 [x] write docs" in capsys.readouterr().out
    tm.main(["--path", str(file), "clear"])
    assert tm.list_tasks(path=file) == []


def test_main_list_handles_missing_completed_field(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Legacy task entries without ``completed`` default to pending in output."""

    file = tmp_path / "tasks.json"
    file.write_text(json.dumps([{"id": 1, "description": "legacy task"}]))

    from axel import task_manager as tm

    tm.main(["--path", str(file), "list"])
    output = capsys.readouterr().out
    assert "1 [ ] legacy task" in output


def test_clear_tasks(tmp_path: Path) -> None:
    file = tmp_path / "tasks.json"
    add_task("write docs", path=file)
    clear_tasks(path=file)
    assert load_tasks(path=file) == []


def test_cli_clear(tmp_path: Path) -> None:
    file = tmp_path / "tasks.json"
    add_task("write docs", path=file)
    subprocess.run(
        [
            sys.executable,
            "-m",
            "axel.task_manager",
            "--path",
            str(file),
            "clear",
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(Path(__file__).resolve().parents[1])},
        check=True,
    )
    assert load_tasks(path=file) == []
