import importlib
import json
import sys
from pathlib import Path

import pytest


def _ensure_repo_on_path() -> None:
    root = str(Path(__file__).resolve().parents[1])
    if root not in sys.path:
        sys.path.insert(0, root)


@pytest.fixture()
def critic_module(monkeypatch):
    _ensure_repo_on_path()
    module = importlib.import_module("axel.critic")
    monkeypatch.setattr(module, "_CURRENT_REPO", None)
    monkeypatch.setattr(module, "_LATEST_RUN_METRICS", None)
    return module


def test_analyze_orthogonality_records_log(critic_module, monkeypatch, tmp_path):
    critic_module.ANALYTICS_ROOT = tmp_path / "analytics"

    def fake_fetch(repo: str, pr_number: int):
        state = "dirty" if pr_number % 2 == 0 else "clean"
        return critic_module.PullRequestSnapshot(
            merged=pr_number % 3 == 0, mergeable_state=state
        )

    monkeypatch.setattr(critic_module, "_fetch_pull_request", fake_fetch)
    critic_module.set_repository("octo/demo")

    diffs = [
        """diff --git a/a.txt b/a.txt\n+hello world\n""",
        """diff --git a/a.txt b/a.txt\n+hello moon\n""",
        """diff --git a/a.txt b/a.txt\n+goodbye sun\n""",
    ]
    result = critic_module.analyze_orthogonality(diffs, [1, 2, 3])

    assert 0.0 <= result["orthogonality_score"] <= 1.0
    assert result["merge_conflict_rate"] > 0
    log_dir = critic_module.ANALYTICS_ROOT / "orthogonality"
    files = list(log_dir.glob("*.jsonl"))
    assert files, "orthogonality log should be created"
    content = files[0].read_text(encoding="utf-8").strip()
    assert "orthogonality_score" in content


def test_track_prompt_saturation_updates_log(critic_module, tmp_path):
    critic_module.ANALYTICS_ROOT = tmp_path / "analytics"
    history_path = (
        critic_module.ANALYTICS_ROOT / "saturation" / "octo" / "implement.md.jsonl"
    )
    critic_module._append_jsonl(  # type: ignore[attr-defined]
        history_path,
        {
            "timestamp": "2024-01-01T00:00:00+00:00",
            "repo": "octo",
            "prompt": "implement.md",
            "fitness_delta": 0.95,
            "merged": 0,
            "closed": 4,
            "orthogonality_scores": [0.1],
            "fitness_delta_avg": 0.95,
            "merge_rate": 0.0,
            "orthogonality_entropy": 0.0,
            "saturation_score": 0.05,
            "prompt_refresh_recommended": True,
        },
    )

    critic_module.set_latest_run_metrics(
        {
            "fitness_delta": 0.9,
            "merged": 0,
            "closed": 1,
            "orthogonality_scores": [],
        }
    )

    result = critic_module.track_prompt_saturation("octo", "implement.md")

    assert 0.0 <= result["saturation_score"] <= 1.0
    assert result["prompt_refresh_recommended"] is True
    log_content = history_path.read_text(encoding="utf-8").strip().splitlines()
    assert len(log_content) == 2


def test_cli_commands(critic_module, monkeypatch, tmp_path, capsys):
    critic_module.ANALYTICS_ROOT = tmp_path / "analytics"

    def fake_fetch(repo: str, pr_number: int):
        state = "dirty" if pr_number == 2 else "clean"
        return critic_module.PullRequestSnapshot(
            merged=pr_number == 1, mergeable_state=state
        )

    monkeypatch.setattr(critic_module, "_fetch_pull_request", fake_fetch)

    diff_a = tmp_path / "diff_a.patch"
    diff_b = tmp_path / "diff_b.patch"
    diff_a.write_text("diff --git a/file b/file\n+foo\n", encoding="utf-8")
    diff_b.write_text("diff --git a/file b/file\n+bar\n", encoding="utf-8")

    exit_code = critic_module.main(
        [
            "analyze-orthogonality",
            "--diff-file",
            str(diff_a),
            "--diff-file",
            str(diff_b),
            "--pr",
            "1",
            "--pr",
            "2",
            "--repo",
            "octo/demo",
        ]
    )
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Orthogonality" in output

    metrics_file = tmp_path / "metrics.json"
    metrics_file.write_text(
        json.dumps(
            {
                "fitness_delta": 0.2,
                "merged": 1,
                "closed": 1,
                "orthogonality_scores": [0.4, 0.6],
            }
        ),
        encoding="utf-8",
    )

    exit_code = critic_module.main(
        [
            "analyze-saturation",
            "--repo",
            "octo/demo",
            "--prompt",
            "implement.md",
            "--metrics",
            str(metrics_file),
        ]
    )
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Saturation" in output


def test_orthogonality_entropy_identical_scores_returns_zero(critic_module):
    result = critic_module._orthogonality_entropy([0.5, 0.5, 0.5, 0.5])
    assert result == 0.0


def test_orthogonality_entropy_handles_pd_cut_error(critic_module, monkeypatch):
    def fake_cut(*_args, **_kwargs):
        raise ValueError("duplicate edges")

    monkeypatch.setattr(critic_module.pd, "cut", fake_cut)
    result = critic_module._orthogonality_entropy([0.1, 0.9])
    assert result == 0.0
