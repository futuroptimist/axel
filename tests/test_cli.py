import json
import sys
from pathlib import Path

sys.path.append(str(Path(__file__).resolve().parents[1]))  # noqa: E402

import pytest  # noqa: E402

import axel.cli as cli  # noqa: E402
from axel.completions import CompletionInstallation, install_completions  # noqa: E402


def test_cli_analyze_orthogonality_delegates_to_critic(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """The analytics verb should flow through to the critic module."""

    captured: dict[str, list[str]] = {}

    def fake_main(argv: list[str]) -> int:
        captured["argv"] = argv
        return 0

    proxy = type("CriticProxy", (), {"main": staticmethod(fake_main)})()
    monkeypatch.setattr(cli, "critic", proxy, raising=False)

    exit_code = cli.main(["analyze-orthogonality", "--diff-file", "a.diff"])

    assert exit_code == 0
    assert captured["argv"] == ["analyze-orthogonality", "--diff-file", "a.diff"]


def test_cli_analyze_saturation_normalizes_bool_exit(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Boolean exits from the critic should coerce to integers."""

    captured: dict[str, list[str]] = {}

    def fake_main(argv: list[str]) -> bool:
        captured["argv"] = argv
        return True

    proxy = type("CriticProxy", (), {"main": staticmethod(fake_main)})()
    monkeypatch.setattr(cli, "critic", proxy, raising=False)

    exit_code = cli.main(
        [
            "analyze-saturation",
            "--repo",
            "demo/repo",
            "--prompt",
            "prompt.md",
        ]
    )

    assert exit_code == 1
    assert captured["argv"] == [
        "analyze-saturation",
        "--repo",
        "demo/repo",
        "--prompt",
        "prompt.md",
    ]


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


def test_cli_repos_list_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_file = tmp_path / "repos.txt"
    repo_file.write_text("https://github.com/example/json\n")

    exit_code = cli.main(
        [
            "repos",
            "list",
            "--path",
            str(repo_file),
            "--json",
        ]
    )

    output = capsys.readouterr().out.strip()
    assert exit_code == 0
    assert json.loads(output) == ["https://github.com/example/json"]


def test_cli_tasks_list_json(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tasks_file = tmp_path / "tasks.json"
    cli.main(
        [
            "tasks",
            "add",
            "write docs",
            "--path",
            str(tasks_file),
        ]
    )
    capsys.readouterr()

    exit_code = cli.main(
        [
            "tasks",
            "list",
            "--path",
            str(tasks_file),
            "--json",
        ]
    )

    output = capsys.readouterr().out.strip()
    assert exit_code == 0
    assert json.loads(output) == [
        {"id": 1, "description": "write docs", "completed": False}
    ]


def test_cli_config_telemetry_status(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """The unified CLI should forward config commands to the config module."""

    monkeypatch.setenv("AXEL_CONFIG_DIR", str(tmp_path))

    exit_code = cli.main(["config", "telemetry", "--status"])

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Telemetry is disabled by default" in captured.out


def test_cli_tasks_list_sample(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    tasks_file = tmp_path / "tasks.json"
    cli.main(
        [
            "tasks",
            "add",
            "alpha",
            "--path",
            str(tasks_file),
        ]
    )
    cli.main(
        [
            "tasks",
            "add",
            "beta",
            "--path",
            str(tasks_file),
        ]
    )
    cli.main(
        [
            "tasks",
            "add",
            "gamma",
            "--path",
            str(tasks_file),
        ]
    )
    capsys.readouterr()

    exit_code = cli.main(
        [
            "tasks",
            "list",
            "--path",
            str(tasks_file),
            "--sample",
            "1",
            "--seed",
            "3",
        ]
    )

    output_lines = capsys.readouterr().out.strip().splitlines()
    assert exit_code == 0
    assert len(output_lines) == 1

    import axel.task_manager as tm

    expected = tm._apply_sampling(tm.load_tasks(path=tasks_file), sample=1, seed=3)
    printed_id = int(output_lines[0].split()[0])
    assert printed_id == expected[0]["id"]


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


def test_install_completions_writes_script(tmp_path: Path) -> None:
    """Installing completions should create the requested script."""

    destination = tmp_path / "axel.bash"
    result = install_completions(shell="bash", path=destination)

    assert isinstance(result, CompletionInstallation)
    assert result.shell == "bash"
    assert result.path == destination
    assert destination.exists()
    content = destination.read_text(encoding="utf-8")
    assert "complete -F _axel_completions axel" in content


def test_install_completions_accepts_shell_suffix(tmp_path: Path) -> None:
    """Shell names with suffixes should normalize to the supported shell."""

    destination = tmp_path / "axel.zsh"
    result = install_completions(shell="/usr/local/bin/zsh-5.9", path=destination)

    assert result.shell == "zsh"
    assert destination.read_text(encoding="utf-8").startswith("# Axel shell")


def test_install_completions_infers_shell(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """When shell is omitted the helper should infer it from $SHELL."""

    monkeypatch.setenv("SHELL", "/usr/bin/fish")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    result = install_completions()

    expected = tmp_path / ".config" / "fish" / "completions" / "axel.fish"
    assert result.shell == "fish"
    assert result.path == expected
    assert expected.exists()


def test_install_completions_rejects_unknown_shell(tmp_path: Path) -> None:
    """Unsupported shells should raise a ValueError."""

    destination = tmp_path / "axel.csh"

    with pytest.raises(ValueError):
        install_completions(shell="csh", path=destination)


def test_install_completions_requires_explicit_shell_value(tmp_path: Path) -> None:
    """Empty shell values should be rejected when provided explicitly."""

    destination = tmp_path / "axel.bash"

    with pytest.raises(ValueError):
        install_completions(shell="", path=destination)


def test_install_completions_defaults_to_bash(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Missing SHELL should fall back to bash destinations."""

    monkeypatch.delenv("SHELL", raising=False)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    result = install_completions()

    expected = tmp_path / ".local" / "share" / "axel" / "completions" / "axel.bash"
    assert result.shell == "bash"
    assert result.path == expected
    assert expected.exists()


def test_install_completions_falls_back_for_unknown_shell(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Unknown detected shells should fall back to bash destinations."""

    monkeypatch.setenv("SHELL", "/usr/local/bin/tcsh")
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    result = install_completions()

    expected = tmp_path / ".local" / "share" / "axel" / "completions" / "axel.bash"
    assert result.shell == "bash"
    assert result.path == expected
    assert expected.exists()


def test_cli_install_completions_command(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """--install-completions should write the script and print instructions."""

    target = tmp_path / "axel.bash"
    exit_code = cli.main(
        ["--install-completions", "--shell", "bash", "--path", str(target)]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert target.exists()
    assert "Installed axel completions for bash" in captured.out
    assert "source" in captured.out


def test_cli_install_completions_fish_custom_path(
    capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Custom fish destinations should prompt the user to link the file manually."""

    target = tmp_path / "custom" / "axel.fish"
    exit_code = cli.main(
        ["--install-completions", "--shell", "fish", "--path", str(target)]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert target.exists()
    assert "Copy the file into ~/.config/fish/completions" in captured.out


def test_cli_install_completions_fish_default(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """The CLI should install to the default fish path when --path is omitted."""

    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    exit_code = cli.main(["--install-completions", "--shell", "fish"])
    captured = capsys.readouterr()

    expected = tmp_path / ".config" / "fish" / "completions" / "axel.fish"
    assert exit_code == 0
    assert expected.exists()
    assert "Fish loads files" in captured.out


def test_cli_install_completions_help_flag(capsys: pytest.CaptureFixture[str]) -> None:
    """Passing --help with --install-completions should print the completions help."""

    exit_code = cli.main(["--install-completions", "--help"])
    captured = capsys.readouterr()

    assert exit_code == 0
    assert "Install shell completion scripts" in captured.out


def test_cli_install_completions_missing_shell_value(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Missing values for --shell should surface argparse's helpful error."""

    exit_code = cli.main(["--install-completions", "--shell"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "expected one argument" in captured.err


def test_cli_install_completions_rejects_extra_arguments(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Additional arguments after --install-completions should trigger an error."""

    exit_code = cli.main(["--install-completions", "--", "extra"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "does not accept additional arguments: -- extra" in captured.err


def test_cli_install_completions_rejects_flag_like_arguments(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Flag-style arguments should also be rejected when installing completions."""

    exit_code = cli.main(["--install-completions", "-x"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "does not accept additional arguments: -x" in captured.err


def test_cli_shell_flag_requires_install(capsys: pytest.CaptureFixture[str]) -> None:
    """Passing --shell alone should surface a helpful error."""

    exit_code = cli.main(["--shell", "bash"])
    captured = capsys.readouterr()
    assert exit_code == 2
    assert "--shell and --path require --install-completions" in captured.err


def test_cli_install_completions_rejects_invalid_shell(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Unsupported shells via the CLI should surface a helpful error."""

    exit_code = cli.main(["--install-completions", "--shell", "csh"])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "unsupported shell: csh" in captured.err


def test_cli_install_completions_rejects_empty_shell(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Explicit empty shell values should be treated as missing."""

    exit_code = cli.main(["--install-completions", "--shell", ""])
    captured = capsys.readouterr()

    assert exit_code == 2
    assert "shell is required" in captured.err


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
