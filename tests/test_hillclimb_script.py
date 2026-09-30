import importlib.util
from pathlib import Path

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
