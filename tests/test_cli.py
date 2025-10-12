import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))  # noqa: E402

import pytest  # noqa: E402

import axel.cli as cli  # noqa: E402


def test_cli_repos_list(capsys: pytest.CaptureFixture[str], tmp_path: Path) -> None:
    """The unified CLI should delegate to the repo manager."""

    repo_file = tmp_path / "repos.txt"
    repo_file.write_text("https://github.com/example/alpha\n")

    exit_code = cli.main(["repos", "list", "--path", str(repo_file)])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "https://github.com/example/alpha" in captured.out


def test_cli_repos_forwards_flags(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Flags before the repo verb should flow through to the manager."""

    repo_file = tmp_path / "repos.txt"
    repo_file.write_text("https://github.com/example/beta\n")

    exit_code = cli.main(["repos", "--path", str(repo_file), "list"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "https://github.com/example/beta" in captured.out


def test_cli_tasks_round_trip(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """The unified CLI should delegate to the task manager."""

    tasks_file = tmp_path / "tasks.json"

    add_code = cli.main(
        [
            "tasks",
            "add",
            "write docs",
            "--path",
            str(tasks_file),
        ]
    )
    add_output = capsys.readouterr().out

    list_code = cli.main(["tasks", "list", "--path", str(tasks_file)])
    list_output = capsys.readouterr().out

    assert add_code == 0
    assert list_code == 0
    assert "write docs" in add_output
    assert "[ ] write docs" in list_output


def test_cli_tasks_forwards_flags(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """Flags preceding the task verb should reach the manager unchanged."""

    tasks_file = tmp_path / "tasks.json"

    exit_code = cli.main(
        [
            "tasks",
            "--path",
            str(tasks_file),
            "add",
            "finish docs",
        ]
    )

    add_output = capsys.readouterr().out

    list_code = cli.main(["tasks", "--path", str(tasks_file), "list"])
    list_output = capsys.readouterr().out

    assert exit_code == 0
    assert list_code == 0
    assert "finish docs" in add_output
    assert "[ ] finish docs" in list_output


def test_cli_prints_help_for_missing_command(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Calling the CLI without arguments should show the help text."""

    exit_code = cli.main([])
    output = capsys.readouterr().out

    assert exit_code == 0
    assert "usage:" in output


def test_cli_prints_help_for_flag(capsys: pytest.CaptureFixture[str]) -> None:
    """The unified CLI should print help when invoked with --help."""

    exit_code = cli.main(["--help"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Unified CLI for repository and task helpers" in captured.out


def test_cli_unknown_command(capsys: pytest.CaptureFixture[str]) -> None:
    """An unknown command should produce an argparse error exit code."""

    exit_code = cli.main(["unknown"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "unknown command: unknown" in captured.err


def test_cli_defaults_to_sys_argv(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    """When argv is omitted the CLI should read from sys.argv."""

    repo_file = tmp_path / "repos.txt"
    repo_file.write_text("https://github.com/example/sysargv\n")

    monkeypatch.setattr(
        sys,
        "argv",
        [
            "axel",
            "repos",
            "list",
            "--path",
            str(repo_file),
        ],
    )

    exit_code = cli.main()
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "https://github.com/example/sysargv" in captured.out


def test_cli_repos_propagates_exit_code(monkeypatch: pytest.MonkeyPatch) -> None:
    """Exit codes returned by the repo manager should bubble up."""

    def fake_main(args: list[str]) -> int:
        assert args == ["--custom"]
        return 3

    monkeypatch.setattr(cli.repo_manager, "main", fake_main)

    assert cli.main(["repos", "--custom"]) == 3


def test_cli_tasks_coerces_bool_exit(monkeypatch: pytest.MonkeyPatch) -> None:
    """Boolean return values from the task manager should convert to ints."""

    def fake_main(args: list[str]) -> bool:
        assert args == []
        return True

    monkeypatch.setattr(cli.task_manager, "main", fake_main)

    assert cli.main(["tasks"]) == 1
