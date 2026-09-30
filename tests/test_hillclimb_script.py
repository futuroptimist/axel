import importlib.util
import subprocess
from pathlib import Path

import pytest

spec = importlib.util.spec_from_file_location(
    "hillclimb_axel", Path(".axel/hillclimb/scripts/axel.py")
)
axel_script = importlib.util.module_from_spec(spec)
spec.loader.exec_module(axel_script)


def test_read_missing_file_returns_empty(tmp_path):
    missing = tmp_path / "missing.md"
    assert axel_script.read(missing) == ""


def test_create_task_markdown_no_prompts(tmp_path, monkeypatch):
    monkeypatch.setattr(axel_script, "PROMPTS_DIR", tmp_path)
    card = {"title": "Test", "key": "t", "acceptance_criteria": []}
    cfg = {"touch_budget": {"files_max": 1, "loc_max": 1}}
    result = axel_script.create_task_markdown("o/r", card, 1, cfg, tmp_path)
    assert "AXEL TASK" in result


def test_guard_stops_both_execute_and_dry_run(monkeypatch):
    import argparse

    import pytest

    from axel.working_hours import WorkingHours

    monkeypatch.setattr(WorkingHours, "blocks_mutations", lambda self, now=None: True)
    monkeypatch.setattr(
        axel_script, "load_dotenv", lambda: pytest.fail("runner started")
    )
    for execute in (False, True):
        with pytest.raises(SystemExit, match="blocked during working hours"):
            axel_script.cmd_hillclimb(argparse.Namespace(execute=execute))


def test_mutation_boundaries_recheck_current_time(monkeypatch, tmp_path):
    import pytest

    from axel.working_hours import WorkingHours

    blocked = False
    monkeypatch.setattr(
        WorkingHours, "blocks_mutations", lambda self, now=None: blocked
    )
    axel_script.require_mutations_allowed()
    blocked = True  # The clock crosses 09:00 after the initial check.
    monkeypatch.setattr(
        axel_script.subprocess, "run", lambda *a, **kw: pytest.fail("git ran")
    )
    monkeypatch.setattr(
        axel_script.requests, "post", lambda *a, **kw: pytest.fail("POST ran")
    )
    for command in (
        "git commit -m test",
        "git push",
        "git checkout main",
        "git branch -D test",
    ):
        with pytest.raises(SystemExit, match="blocked during working hours"):
            axel_script.sh(command)
    with pytest.raises(SystemExit, match="blocked during working hours"):
        axel_script.gh_post(None, "https://example.invalid/pulls", {})
    with pytest.raises(SystemExit, match="blocked during working hours"):
        axel_script.write(tmp_path / "subdir" / "task.md", "task")
    assert not (tmp_path / "subdir").exists()
    with pytest.raises(SystemExit, match="blocked during working hours"):
        axel_script.cmd_dashboard(None)


def test_invalid_config_prevents_mutations(monkeypatch, tmp_path):
    import pytest

    path = tmp_path / "config.yml"
    path.write_text("working_hours:\n  timezone: Not/AZone\n")
    monkeypatch.setattr(axel_script, "CONFIG", path)
    with pytest.raises(SystemExit, match="Invalid working-hours configuration"):
        axel_script.require_mutations_allowed()


def test_read_only_diff_is_available_during_working_hours(monkeypatch):
    from types import SimpleNamespace

    from axel.working_hours import WorkingHours

    monkeypatch.setattr(WorkingHours, "blocks_mutations", lambda self, now=None: True)
    monkeypatch.setattr(
        axel_script.subprocess,
        "run",
        lambda *a, **kw: SimpleNamespace(returncode=0, stdout="diff"),
    )
    assert axel_script.fingerprint_patch(".")


def test_mutations_proceed_outside_working_hours(monkeypatch, tmp_path):
    from types import SimpleNamespace

    from axel.working_hours import WorkingHours

    monkeypatch.setattr(WorkingHours, "blocks_mutations", lambda self, now=None: False)
    monkeypatch.setattr(
        axel_script.subprocess,
        "run",
        lambda *a, **kw: SimpleNamespace(returncode=0, stdout="ok"),
    )
    monkeypatch.setattr(
        axel_script.requests,
        "post",
        lambda *a, **kw: SimpleNamespace(status_code=200, json=lambda: {"number": 1}),
    )
    assert axel_script.sh("git commit -m test") == "ok"
    assert axel_script.gh_post(None, "https://example.invalid/pulls", {}) == {
        "number": 1
    }
    path = tmp_path / "task.md"
    axel_script.write(path, "task")
    assert path.read_text() == "task"


def test_config_is_reloaded_between_mutations(monkeypatch, tmp_path):
    import pytest

    path = tmp_path / "config.yml"
    path.write_text("working_hours:\n  enabled: false\n")
    monkeypatch.setattr(axel_script, "CONFIG", path)
    axel_script.require_mutations_allowed()
    path.write_text("working_hours:\n  enabled: maybe\n")
    with pytest.raises(SystemExit, match="Invalid working-hours configuration"):
        axel_script.write(tmp_path / "task.md", "task")
    assert not (tmp_path / "task.md").exists()


def test_version_does_not_create_work_dir(monkeypatch, tmp_path, capsys):
    import sys

    from axel.working_hours import WorkingHours

    work_dir = tmp_path / "work"
    monkeypatch.setattr(axel_script, "WORK_DIR", work_dir)
    monkeypatch.setattr(WorkingHours, "blocks_mutations", lambda self, now=None: True)
    monkeypatch.setattr(sys, "argv", ["axel.py", "version"])
    axel_script.main()
    assert "CLI v" in capsys.readouterr().out
    assert not work_dir.exists()


@pytest.mark.parametrize("execute", [False, True], ids=["dry-run", "execute"])
@pytest.mark.parametrize("cutoff", ["write", "add", "commit"])
def test_hillclimb_mid_run_cutoff_preserves_local_state(
    monkeypatch, tmp_path, execute, cutoff
):
    """Run real local Git mutations, then stop at the next boundary at 09:00."""
    from argparse import Namespace
    from datetime import datetime, timezone

    import axel.working_hours as working_hours

    repo = tmp_path / "repo"
    repo.mkdir()

    def git(*args):
        return subprocess.check_output(
            ["git", *args], cwd=repo, text=True, stderr=subprocess.STDOUT
        ).strip()

    git("init", "-b", "main")
    git("config", "user.name", "Test")
    git("config", "user.email", "test@example.invalid")
    git("-c", "commit.gpgsign=false", "commit", "--allow-empty", "-m", "initial")
    baseline = git("rev-parse", "HEAD")
    git("config", "commit.gpgsign", "false")

    clock = datetime(2026, 9, 28, 15, 59, 59, tzinfo=timezone.utc)  # 08:59:59 PDT

    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            assert tz is timezone.utc
            return clock

    def cross_into_working_hours():
        nonlocal clock
        clock = datetime(2026, 9, 28, 16, 0, 0, tzinfo=timezone.utc)  # 09:00 PDT

    monkeypatch.setattr(working_hours, "datetime", Clock)
    monkeypatch.setattr(axel_script, "load_dotenv", lambda: None)
    monkeypatch.setenv("GITHUB_TOKEN", "unused-test-value")
    # Supply an already prepared local repo instead of contacting GitHub.
    monkeypatch.setattr(axel_script, "ensure_clone", lambda *args: repo)
    monkeypatch.setattr(axel_script, "WORK_DIR", tmp_path / "work")
    monkeypatch.setattr(axel_script, "make_branch_name", lambda *args: "hc/test-cutoff")
    repo_list = tmp_path / "repos.yml"
    repo_list.write_text("repos:\n  - slug: example/project\n")
    monkeypatch.setattr(axel_script, "REPOS", repo_list)
    cards = tmp_path / "cards"
    cards.mkdir()
    (cards / "test.yml").write_text("key: test\ntitle: Test cutoff\n")
    monkeypatch.setattr(axel_script, "CARDS_DIR", cards)
    monkeypatch.setattr(
        axel_script.requests, "post", lambda *a, **kw: pytest.fail("unexpected POST")
    )

    original_sh = axel_script.sh
    completed_commands = []

    def run_command(cmd, *args, **kwargs):
        # Keep the real mutation guard and subprocess execution in the path.
        result = original_sh(cmd, *args, **kwargs)
        completed_commands.append(cmd)
        if (cutoff == "add" and cmd.startswith("git add ")) or (
            cutoff == "commit" and cmd.startswith("git commit ")
        ):
            cross_into_working_hours()
        return result

    original_write = axel_script.write

    def write_task(path, content):
        original_write(path, content)
        if cutoff == "write":
            cross_into_working_hours()

    monkeypatch.setattr(axel_script, "sh", run_command)
    monkeypatch.setattr(axel_script, "write", write_task)
    with pytest.raises(SystemExit, match="blocked during working hours"):
        axel_script.cmd_hillclimb(Namespace(execute=execute, card="test", runs=2))

    # No cleanup checkout/deletion, push, or second attempt may run after cutoff.
    assert git("branch", "--show-current") == "hc/test-cutoff"
    assert "AXEL TASK: Test cutoff (Run 1)" in (repo / "AXEL_TASK.md").read_text()
    assert not any(cmd.startswith("git push") for cmd in completed_commands)
    assert not any(cmd.startswith("git branch -D") for cmd in completed_commands)
    assert not any(cmd == "git checkout main" for cmd in completed_commands)
    assert len(completed_commands) == {"write": 1, "add": 2, "commit": 3}[cutoff]
    if cutoff == "commit":
        assert git("rev-parse", "HEAD") != baseline
        assert git("rev-list", "--count", "HEAD") == "2"
        assert git("status", "--porcelain") == ""
        assert "AXEL TASK" in git("show", "HEAD:AXEL_TASK.md")
    else:
        assert git("rev-parse", "HEAD") == baseline
        assert (
            git("status", "--porcelain")
            == {"write": "?? AXEL_TASK.md", "add": "A  AXEL_TASK.md"}[cutoff]
        )
