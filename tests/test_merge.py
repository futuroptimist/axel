from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from axel.merge import speculative_merge_check


def _run_git(*args: str, cwd: Path) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["git", *args],
        cwd=cwd,
        check=True,
        text=True,
        stdout=subprocess.PIPE,
        stderr=subprocess.PIPE,
    )


def _init_repo(path: Path) -> Path:
    path.mkdir(parents=True, exist_ok=True)
    repo = path / "repo"
    repo.mkdir()
    _run_git("init", "-b", "main", cwd=repo)
    _run_git("config", "user.name", "Axel", cwd=repo)
    _run_git("config", "user.email", "axel@example.com", cwd=repo)
    return repo


@pytest.fixture()
def git_repo(tmp_path: Path) -> Path:
    return _init_repo(tmp_path)


def test_speculative_merge_requires_existing_repo(tmp_path: Path) -> None:
    with pytest.raises(ValueError):
        speculative_merge_check(tmp_path / "missing", "main", "feature")


def test_speculative_merge_reports_clean_result(git_repo: Path) -> None:
    (git_repo / "base.txt").write_text("seed\n", encoding="utf-8")
    _run_git("add", "base.txt", cwd=git_repo)
    _run_git("commit", "-m", "initial", cwd=git_repo)

    _run_git("checkout", "-b", "feature", cwd=git_repo)
    (git_repo / "feature.txt").write_text("feature\n", encoding="utf-8")
    _run_git("add", "feature.txt", cwd=git_repo)
    _run_git("commit", "-m", "feature", cwd=git_repo)

    _run_git("checkout", "main", cwd=git_repo)
    (git_repo / "main.txt").write_text("main\n", encoding="utf-8")
    _run_git("add", "main.txt", cwd=git_repo)
    _run_git("commit", "-m", "main", cwd=git_repo)

    result = speculative_merge_check(git_repo, "main", "feature")

    assert result["conflicts"] is False
    assert result["conflicted_files"] == []
    assert isinstance(result["output"], str)


def test_speculative_merge_reports_conflicts(git_repo: Path) -> None:
    (git_repo / "shared.txt").write_text("alpha\n", encoding="utf-8")
    _run_git("add", "shared.txt", cwd=git_repo)
    _run_git("commit", "-m", "initial", cwd=git_repo)

    _run_git("checkout", "-b", "feature", cwd=git_repo)
    (git_repo / "shared.txt").write_text("feature change\n", encoding="utf-8")
    _run_git("commit", "-am", "feature", cwd=git_repo)

    _run_git("checkout", "main", cwd=git_repo)
    (git_repo / "shared.txt").write_text("main change\n", encoding="utf-8")
    _run_git("commit", "-am", "main", cwd=git_repo)

    result = speculative_merge_check(git_repo, "main", "feature")

    assert result["conflicts"] is True
    assert "shared.txt" in result["conflicted_files"]
    assert (
        "CONFLICT" in result["output"] or "Automatic merge failed" in result["output"]
    )


def test_format_result_lists_conflicted_files() -> None:
    from axel import merge as merge_module

    text = merge_module._format_result(
        "main", "feature", {"conflicts": True, "conflicted_files": ["foo.txt"]}
    )

    assert "foo.txt" in text
    assert "feature" in text


def test_format_result_reports_clean_merge() -> None:
    from axel import merge as merge_module

    text = merge_module._format_result(
        "main", "feature", {"conflicts": False, "conflicted_files": []}
    )

    assert "clean" in text.lower()


def test_merge_cli_outputs_json(tmp_path, capsys) -> None:
    import json

    from axel import merge as merge_module

    repo = _init_repo(tmp_path / "cli-clean")
    (repo / "base.txt").write_text("seed\n", encoding="utf-8")
    _run_git("add", "base.txt", cwd=repo)
    _run_git("commit", "-m", "initial", cwd=repo)
    _run_git("checkout", "-b", "feature", cwd=repo)
    (repo / "feature.txt").write_text("feature\n", encoding="utf-8")
    _run_git("add", "feature.txt", cwd=repo)
    _run_git("commit", "-m", "feature", cwd=repo)
    _run_git("checkout", "main", cwd=repo)

    exit_code = merge_module.main(
        [
            "check",
            "--repo",
            str(repo),
            "--base",
            "main",
            "--head",
            "feature",
            "--json",
        ]
    )
    captured = capsys.readouterr()
    payload = json.loads(captured.out)

    assert exit_code == 0
    assert payload["conflicts"] is False
    assert payload["conflicted_files"] == []


def test_merge_cli_reports_conflicts(tmp_path, capsys) -> None:
    from axel import merge as merge_module

    repo = _init_repo(tmp_path / "cli-conflict")
    (repo / "shared.txt").write_text("seed\n", encoding="utf-8")
    _run_git("add", "shared.txt", cwd=repo)
    _run_git("commit", "-m", "initial", cwd=repo)
    _run_git("checkout", "-b", "feature", cwd=repo)
    (repo / "shared.txt").write_text("feature\n", encoding="utf-8")
    _run_git("commit", "-am", "feature", cwd=repo)
    _run_git("checkout", "main", cwd=repo)
    (repo / "shared.txt").write_text("main\n", encoding="utf-8")
    _run_git("commit", "-am", "main", cwd=repo)

    exit_code = merge_module.main(
        [
            "check",
            "--repo",
            str(repo),
            "--base",
            "main",
            "--head",
            "feature",
        ]
    )
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "conflict" in captured.out.lower()


def test_merge_cli_requires_command(capsys) -> None:
    from axel import merge as merge_module

    exit_code = merge_module.main([])
    captured = capsys.readouterr()

    assert exit_code == 1
    assert "usage" in captured.out.lower()
