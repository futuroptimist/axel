from __future__ import annotations

import subprocess
from pathlib import Path

import pytest

from axel.merge import (
    MergePlan,
    load_merge_policy,
    plan_merge_actions,
    speculative_merge_check,
)


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


def test_speculative_merge_reports_delete_vs_modify_conflict(git_repo: Path) -> None:
    (git_repo / "shared.txt").write_text("alpha\n", encoding="utf-8")
    _run_git("add", "shared.txt", cwd=git_repo)
    _run_git("commit", "-m", "initial", cwd=git_repo)

    _run_git("checkout", "-b", "feature", cwd=git_repo)
    (git_repo / "shared.txt").write_text("feature\n", encoding="utf-8")
    _run_git("commit", "-am", "feature", cwd=git_repo)

    _run_git("checkout", "main", cwd=git_repo)
    (git_repo / "shared.txt").unlink()
    _run_git("commit", "-am", "delete", cwd=git_repo)

    result = speculative_merge_check(git_repo, "main", "feature")

    assert result["conflicts"] is True
    assert "shared.txt" in result["conflicted_files"]
    summary = result.get("conflict_summary") or {}
    assert summary.get("unknown") == 1
    assert result.get("auto_resolvable") is False


def test_speculative_merge_classifies_comment_only_conflicts(git_repo: Path) -> None:
    (git_repo / "notes.py").write_text("# seed\nvalue = 1\n", encoding="utf-8")
    _run_git("add", "notes.py", cwd=git_repo)
    _run_git("commit", "-m", "initial", cwd=git_repo)

    _run_git("checkout", "-b", "feature", cwd=git_repo)
    (git_repo / "notes.py").write_text(
        "# feature comment\nvalue = 1\n",
        encoding="utf-8",
    )
    _run_git("commit", "-am", "feature", cwd=git_repo)

    _run_git("checkout", "main", cwd=git_repo)
    (git_repo / "notes.py").write_text(
        "# main comment\nvalue = 1\n",
        encoding="utf-8",
    )
    _run_git("commit", "-am", "main", cwd=git_repo)

    result = speculative_merge_check(git_repo, "main", "feature")

    assert result["conflicts"] is True
    classifications = result.get("conflict_classification") or {}
    summary = result.get("conflict_summary") or {}
    note_class = classifications.get("notes.py")
    assert note_class == "comment_only"
    assert summary.get("comment_only") == 1
    assert result.get("auto_resolvable") is True


def test_speculative_merge_classifies_code_conflicts(git_repo: Path) -> None:
    (git_repo / "app.py").write_text("value = 1\n", encoding="utf-8")
    _run_git("add", "app.py", cwd=git_repo)
    _run_git("commit", "-m", "initial", cwd=git_repo)

    _run_git("checkout", "-b", "feature", cwd=git_repo)
    (git_repo / "app.py").write_text("value = 2\n", encoding="utf-8")
    _run_git("commit", "-am", "feature", cwd=git_repo)

    _run_git("checkout", "main", cwd=git_repo)
    (git_repo / "app.py").write_text("value = 3\n", encoding="utf-8")
    _run_git("commit", "-am", "main", cwd=git_repo)

    result = speculative_merge_check(git_repo, "main", "feature")

    assert result["conflicts"] is True
    classifications = result.get("conflict_classification") or {}
    summary = result.get("conflict_summary") or {}
    app_class = classifications.get("app.py")
    assert app_class == "code"
    assert summary.get("code") == 1
    assert result.get("auto_resolvable") is False


def test_classify_conflicts_marks_missing_files_unknown(tmp_path: Path) -> None:
    from axel import merge as merge_module

    classifications = merge_module._classify_conflicts(tmp_path, ["missing.txt"])

    assert classifications["missing.txt"] == "unknown"


def test_classify_segments_handles_html_comments() -> None:
    from axel import merge as merge_module

    result = merge_module._classify_segments([(["<!-- note -->"], ["<!-- alt -->"])])

    assert result == "comment_only"


def test_extract_conflict_segments_handles_blank_lines(tmp_path: Path) -> None:
    from axel import merge as merge_module

    content = (
        "<<<<<<< ours\n"
        "# comment\n"
        "\n"
        "=======\n"
        "# alt\n"
        "\n"
        ">>>>>>> theirs\n"
    )
    file_path = tmp_path / "conflict.txt"
    file_path.write_text(content, encoding="utf-8")

    segments = merge_module._extract_conflict_segments(
        file_path.read_text(encoding="utf-8")
    )

    assert segments == [(["# comment", ""], ["# alt", ""])]


def test_classify_segments_returns_unknown_for_empty_segments() -> None:
    from axel import merge as merge_module

    assert merge_module._classify_segments([]) == "unknown"


def test_is_comment_line_handles_blank_and_html() -> None:
    from axel import merge as merge_module

    assert merge_module._is_comment_line("   ")
    assert merge_module._is_comment_line("<!-- reminder -->")


def test_prune_common_lines_removes_shared_entries() -> None:
    from axel import merge as merge_module

    ours_unique, theirs_unique = merge_module._prune_common_lines(
        ["# main", "value"],
        ["# feature", "value"],
    )

    assert ours_unique == ["# main"]
    assert theirs_unique == ["# feature"]


def test_classify_segments_skips_identical_chunks() -> None:
    from axel import merge as merge_module

    result = merge_module._classify_segments([(["value"], ["value"])])

    assert result == "comment_only"


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


def test_plan_merge_actions_auto_resolves_comment_conflicts(git_repo: Path) -> None:
    """Comment-only conflicts should auto-resolve per policy heuristics."""

    (git_repo / "notes.py").write_text("# seed\nvalue = 1\n", encoding="utf-8")
    _run_git("add", "notes.py", cwd=git_repo)
    _run_git("commit", "-m", "initial", cwd=git_repo)

    _run_git("checkout", "-b", "feature", cwd=git_repo)
    (git_repo / "notes.py").write_text("# feature\nvalue = 1\n", encoding="utf-8")
    _run_git("commit", "-am", "feature", cwd=git_repo)

    _run_git("checkout", "main", cwd=git_repo)
    (git_repo / "notes.py").write_text("# main\nvalue = 1\n", encoding="utf-8")
    _run_git("commit", "-am", "main", cwd=git_repo)

    plan = plan_merge_actions(git_repo, "main", "feature")

    assert isinstance(plan, MergePlan)
    assert plan.auto_resolve is True
    assert plan.requires_manual_review is False
    assert plan.resolutions.get("notes.py") == "auto_resolve_comment"
    assert any(check.get("command") for check in plan.safety_checks)
    assert plan.policy_metadata.get("author") == "Futuroptimist"


def test_plan_merge_actions_uses_priority_rules(git_repo: Path) -> None:
    """Priority rules should steer resolutions for matching paths."""

    (git_repo / "infra").mkdir()
    config = git_repo / "infra" / "config.yml"
    config.write_text("value: 1\n", encoding="utf-8")
    _run_git("add", "infra/config.yml", cwd=git_repo)
    _run_git("commit", "-m", "initial", cwd=git_repo)

    _run_git("checkout", "-b", "feature", cwd=git_repo)
    config.write_text("value: feature\n", encoding="utf-8")
    _run_git("commit", "-am", "feature", cwd=git_repo)

    _run_git("checkout", "main", cwd=git_repo)
    config.write_text("value: main\n", encoding="utf-8")
    _run_git("commit", "-am", "main", cwd=git_repo)

    plan = plan_merge_actions(git_repo, "main", "feature")

    assert plan.auto_resolve is False
    assert plan.requires_manual_review is True
    assert plan.resolutions.get("infra/config.yml") == "main_wins"


def test_auto_resolvable_false_for_conflicts_without_summary() -> None:
    from axel import merge as merge_module

    assert merge_module._auto_resolvable({}, conflicts=True) is False


def test_load_merge_policy_requires_mapping(tmp_path: Path) -> None:
    invalid = tmp_path / "policy.yaml"
    invalid.write_text("[]", encoding="utf-8")

    with pytest.raises(ValueError):
        load_merge_policy(invalid)


def test_load_merge_policy_returns_empty_for_blank_file(tmp_path: Path) -> None:
    empty = tmp_path / "policy.yaml"
    empty.write_text("", encoding="utf-8")

    assert load_merge_policy(empty) == {}


def test_plan_merge_actions_handles_non_mapping_classifications(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    def _fake_speculative_merge(
        repo_path: Path | str, base: str, head: str
    ) -> dict[str, object]:
        return {
            "conflicts": False,
            "auto_resolvable": True,
            "conflict_classification": ["unexpected"],
        }

    monkeypatch.setattr("axel.merge.speculative_merge_check", _fake_speculative_merge)

    plan = plan_merge_actions(".", "main", "feature")

    assert plan.auto_resolve is True
    assert plan.resolutions == {}


def test_plan_merge_actions_uses_fallback_and_metadata_defaults(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    policy = {
        "merge_policy": {
            "conflict_resolution": {"fallback": "manual_review"},
            "metadata": "string",  # triggers defensive branch
            "safety_checks": [{"command": "pytest"}],
        }
    }

    def _fake_policy(path: Path | str | None = None) -> dict[str, object]:
        return policy

    def _fake_spec(repo_path: Path | str, base: str, head: str) -> dict[str, object]:
        return {
            "conflicts": True,
            "auto_resolvable": False,
            "conflict_classification": {"src/app.py": "code"},
        }

    monkeypatch.setattr("axel.merge.load_merge_policy", _fake_policy)
    monkeypatch.setattr("axel.merge.speculative_merge_check", _fake_spec)

    plan = plan_merge_actions(".", "main", "feature")

    assert plan.auto_resolve is False
    assert plan.requires_manual_review is True
    assert plan.resolutions.get("src/app.py") == "manual_review"
    assert plan.policy_metadata == {}
