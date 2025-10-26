import importlib
import json
import sys
from pathlib import Path
from types import SimpleNamespace

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


def test_analyze_orthogonality_appends_config_ledger(
    critic_module, monkeypatch, tmp_path
):
    critic_module.ANALYTICS_ROOT = tmp_path / "analytics"

    def fake_fetch(repo: str, pr_number: int):
        return critic_module.PullRequestSnapshot(merged=False, mergeable_state="clean")

    monkeypatch.setattr(critic_module, "_fetch_pull_request", fake_fetch)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(
        critic_module.importlib_metadata,
        "version",
        lambda _name: "test-cli-version",
    )
    monkeypatch.setattr(
        critic_module,
        "load_telemetry_config",
        lambda: SimpleNamespace(opt_in=False, consent_timestamp=None),
    )
    critic_module.set_repository("octo/demo")

    critic_module.analyze_orthogonality(
        [
            "diff --git a/a.txt b/a.txt\n+hello\n",
            "diff --git a/a.txt b/a.txt\n+world\n",
        ],
        [1, 2],
    )

    ledger = tmp_path / ".config" / "axel" / "analytics" / "orthogonality.jsonl"
    assert ledger.exists()
    lines = ledger.read_text(encoding="utf-8").strip().splitlines()
    assert lines, "ledger should include at least one entry"
    payload = json.loads(lines[-1])
    assert payload["metric"] == "orthogonality"
    assert "orthogonality_score" in payload
    assert payload["cli_version"] == "test-cli-version"
    assert payload["telemetry_opt_in"] is False
    assert payload["telemetry_consent_timestamp"] is None


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


def test_main_analyze_orthogonality_sampling(
    critic_module, monkeypatch, tmp_path, capsys
) -> None:
    critic_module.ANALYTICS_ROOT = tmp_path / "analytics"

    def fake_fetch(repo: str, pr_number: int):
        return critic_module.PullRequestSnapshot(merged=False, mergeable_state="clean")

    monkeypatch.setattr(critic_module, "_fetch_pull_request", fake_fetch)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    diffs = []
    contents = [
        "diff --git a/a.txt b/a.txt\n+alpha\n",
        "diff --git a/b.txt b/b.txt\n+beta\n",
        "diff --git a/c.txt b/c.txt\n+gamma\n",
    ]
    for index, content in enumerate(contents, start=1):
        path = tmp_path / f"diff{index}.txt"
        path.write_text(content, encoding="utf-8")
        diffs.append(path)

    exit_code = critic_module.main(
        [
            "analyze-orthogonality",
            "--diff-file",
            str(diffs[0]),
            "--diff-file",
            str(diffs[1]),
            "--diff-file",
            str(diffs[2]),
            "--repo",
            "octo/demo",
            "--pr",
            "101",
            "--pr",
            "102",
            "--pr",
            "103",
            "--sample",
            "2",
            "--seed",
            "11",
            "--json",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    payload = json.loads(captured.out)
    assert payload["total_tasks"] == 2
    assert payload["merged_prs"] == [102, 103]
    sampling = payload.get("sampling")
    assert sampling is not None
    assert sampling["requested"] == 2
    assert sampling["seed"] == 11
    assert sampling["original_task_count"] == 3
    assert sampling["sampled_task_count"] == 2
    assert sampling["applied"] is True

    ledger = tmp_path / ".config" / "axel" / "analytics" / "orthogonality.jsonl"
    assert ledger.exists()
    latest = json.loads(ledger.read_text(encoding="utf-8").strip().splitlines()[-1])
    assert latest["sampling"]["sampled_task_count"] == 2


def test_main_analyze_orthogonality_sampling_text_output(
    critic_module, monkeypatch, tmp_path, capsys
) -> None:
    """Plain-text CLI output should surface sampling metadata."""

    critic_module.ANALYTICS_ROOT = tmp_path / "analytics"

    def fake_fetch(repo: str, pr_number: int):
        return critic_module.PullRequestSnapshot(merged=False, mergeable_state="clean")

    monkeypatch.setattr(critic_module, "_fetch_pull_request", fake_fetch)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    diffs = []
    contents = [
        "diff --git a/a.txt b/a.txt\n+alpha\n",
        "diff --git a/b.txt b/b.txt\n+beta\n",
        "diff --git a/c.txt b/c.txt\n+gamma\n",
    ]
    for index, content in enumerate(contents, start=1):
        path = tmp_path / f"diff{index}.txt"
        path.write_text(content, encoding="utf-8")
        diffs.append(path)

    exit_code = critic_module.main(
        [
            "analyze-orthogonality",
            "--diff-file",
            str(diffs[0]),
            "--diff-file",
            str(diffs[1]),
            "--diff-file",
            str(diffs[2]),
            "--repo",
            "octo/demo",
            "--pr",
            "101",
            "--pr",
            "102",
            "--pr",
            "103",
            "--sample",
            "2",
            "--seed",
            "11",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "Sampling:" in captured.out
    assert "2 of 3 tasks" in captured.out
    assert "seed=11" in captured.out


def test_main_analyze_orthogonality_sampling_text_output_full_dataset(
    critic_module, monkeypatch, tmp_path, capsys
) -> None:
    """When sampling covers all tasks, the CLI should flag the full dataset usage."""

    critic_module.ANALYTICS_ROOT = tmp_path / "analytics"

    def fake_fetch(repo: str, pr_number: int):
        return critic_module.PullRequestSnapshot(merged=False, mergeable_state="clean")

    monkeypatch.setattr(critic_module, "_fetch_pull_request", fake_fetch)
    monkeypatch.setattr(Path, "home", lambda: tmp_path)

    diffs: list[Path] = []
    for index, content in enumerate(
        (
            "diff --git a/a.txt b/a.txt\n+alpha\n",
            "diff --git a/b.txt b/b.txt\n+beta\n",
            "diff --git a/c.txt b/c.txt\n+gamma\n",
        ),
        start=1,
    ):
        path = tmp_path / f"diff{index}.txt"
        path.write_text(content, encoding="utf-8")
        diffs.append(path)

    exit_code = critic_module.main(
        [
            "analyze-orthogonality",
            "--diff-file",
            str(diffs[0]),
            "--diff-file",
            str(diffs[1]),
            "--diff-file",
            str(diffs[2]),
            "--repo",
            "octo/demo",
            "--pr",
            "101",
            "--pr",
            "102",
            "--sample",
            "5",
            "--seed",
            "7",
        ]
    )

    captured = capsys.readouterr()
    assert exit_code == 0
    assert "full dataset used" in captured.out
    assert "seed=7" in captured.out


def test_apply_sampling_handles_non_positive_requests(critic_module) -> None:
    entries = ["one", "two", "three"]
    assert critic_module._apply_sampling(entries, sample=0, seed=5) == []


def test_apply_sampling_returns_all_when_large_sample(critic_module) -> None:
    entries = ["alpha", "beta"]
    assert critic_module._apply_sampling(entries, sample=10, seed=42) == entries


def test_apply_sampling_returns_all_when_sample_none(critic_module) -> None:
    entries = ["left", "right"]
    assert critic_module._apply_sampling(entries, sample=None, seed=99) == entries


def test_track_prompt_saturation_appends_config_ledger(
    critic_module, monkeypatch, tmp_path
):
    critic_module.ANALYTICS_ROOT = tmp_path / "analytics"
    monkeypatch.setattr(Path, "home", lambda: tmp_path)
    monkeypatch.setattr(
        critic_module.importlib_metadata,
        "version",
        lambda _name: "test-cli-version",
    )
    monkeypatch.setattr(
        critic_module,
        "load_telemetry_config",
        lambda: SimpleNamespace(
            opt_in=True, consent_timestamp="2025-01-01T00:00:00+00:00"
        ),
    )
    critic_module.set_latest_run_metrics(
        {
            "fitness_delta": 0.1,
            "merged": 1,
            "closed": 0,
            "orthogonality_scores": [0.2, 0.4],
        }
    )

    critic_module.track_prompt_saturation("octo/demo", "implement.md")

    ledger = tmp_path / ".config" / "axel" / "analytics" / "saturation.jsonl"
    assert ledger.exists()
    lines = ledger.read_text(encoding="utf-8").strip().splitlines()
    assert lines, "ledger should include at least one entry"
    payload = json.loads(lines[-1])
    assert payload["metric"] == "saturation"
    assert payload["repo"] == "octo/demo"
    assert payload["prompt"] == "implement.md"
    assert payload["cli_version"] == "test-cli-version"
    assert payload["telemetry_opt_in"] is True
    assert payload["telemetry_consent_timestamp"] == "2025-01-01T00:00:00+00:00"


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

    common_args = [
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

    exit_code = critic_module.main(common_args)
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Orthogonality" in output

    exit_code = critic_module.main([*common_args, "--json"])
    assert exit_code == 0
    json_output = json.loads(capsys.readouterr().out)
    assert json_output["total_tasks"] == 2
    assert json_output["merged_prs"] == [1, 2]

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

    sat_args = [
        "analyze-saturation",
        "--repo",
        "octo/demo",
        "--prompt",
        "implement.md",
        "--metrics",
        str(metrics_file),
    ]

    exit_code = critic_module.main(sat_args)
    assert exit_code == 0
    output = capsys.readouterr().out
    assert "Saturation" in output

    exit_code = critic_module.main([*sat_args, "--json"])
    assert exit_code == 0
    sat_json = json.loads(capsys.readouterr().out)
    assert sat_json["repo"] == "octo/demo"
    assert sat_json["prompt"] == "implement.md"


def test_load_history_handles_missing_and_invalid_lines(critic_module, tmp_path):
    missing_path = tmp_path / "missing.jsonl"
    missing_history = critic_module._load_history(missing_path)
    assert missing_history.empty

    history_path = tmp_path / "history.jsonl"
    history_payload = [
        "",
        json.dumps({"value": 1}),
        "not-json",
        json.dumps({"value": 2}),
    ]
    history_path.write_text("\n".join(history_payload) + "\n", encoding="utf-8")
    history = critic_module._load_history(history_path)
    assert len(history) == 2

    invalid_only_path = tmp_path / "invalid_only.jsonl"
    invalid_only_path.write_text("not-json\n", encoding="utf-8")
    invalid_history = critic_module._load_history(invalid_only_path)
    assert invalid_history.empty


def test_self_evaluate_merge_conflicts_rewards_comment_only(critic_module):
    summary = {"comment_only": 2, "unknown": 1}

    result = critic_module.self_evaluate_merge_conflicts(summary)

    assert 0.0 <= result["conflict_score"] <= 1.0
    assert result["auto_resolvable"] is False
    assert result["comment_only"] == 2
    assert result["unknown"] == 1
    assert "comment" in (result["assessment"] or "").lower()


def test_self_evaluate_merge_conflicts_detects_code_conflicts(critic_module):
    summary = {"code": 1}

    result = critic_module.self_evaluate_merge_conflicts(summary)

    assert result["conflict_score"] == 0.0
    assert result["auto_resolvable"] is False
    assert result["code"] == 1
    assert "manual" in (result["assessment"] or "").lower()


def test_self_evaluate_merge_conflicts_auto_resolves_comments(critic_module):
    summary = {"comment_only": 3}

    result = critic_module.self_evaluate_merge_conflicts(summary)

    assert result["conflict_score"] == 1.0
    assert result["auto_resolvable"] is True
    assert "safe" in (result["assessment"] or "").lower()


def test_self_evaluate_merge_conflicts_handles_empty_summary(critic_module):
    result = critic_module.self_evaluate_merge_conflicts({})

    assert result["conflict_score"] == 1.0
    assert result["auto_resolvable"] is True
    assert result["assessment"].lower().startswith("no conflicts")


def test_fetch_pull_request_handles_api_errors(monkeypatch, critic_module):
    class DummyResponse:
        def __init__(self, status_code: int, payload: dict[str, object]):
            self.status_code = status_code
            self._payload = payload

        def json(self) -> dict[str, object]:
            return self._payload

    responses = [
        DummyResponse(500, {}),
        DummyResponse(
            200,
            {
                "merged": False,
                "mergeable": False,
                "mergeable_state": None,
            },
        ),
    ]

    def fake_get(url: str, headers: dict[str, str], timeout: int):  # noqa: ARG001
        return responses.pop(0)

    monkeypatch.setenv("GITHUB_TOKEN", "secret-token")
    monkeypatch.setattr(critic_module.requests, "get", fake_get)

    assert critic_module._fetch_pull_request("octo/demo", 1) is None
    snapshot = critic_module._fetch_pull_request("octo/demo", 2)
    assert snapshot is not None
    assert snapshot.mergeable_state == "dirty"


def test_conflict_rate_handles_inputs(monkeypatch, critic_module):
    assert critic_module._conflict_rate(None, [], 0) == 0.0

    def fake_fetch(repo: str, pr_number: int):  # noqa: ARG001
        return critic_module.PullRequestSnapshot(merged=False, mergeable_state="dirty")

    monkeypatch.setattr(critic_module, "_fetch_pull_request", fake_fetch)
    rate = critic_module._conflict_rate("octo/demo", [1, 2], 2)
    assert rate == 1.0


def test_average_similarity_handles_short_sequences(monkeypatch, critic_module):
    assert critic_module._average_pairwise_similarity(["only"]) == 0.0

    monkeypatch.setattr(critic_module, "combinations", lambda *_args, **_kwargs: [])
    assert critic_module._average_pairwise_similarity(["a", "b"]) == 0.0


def test_load_latest_metrics_prefers_cache_and_env(monkeypatch, critic_module):
    monkeypatch.setattr(critic_module, "_LATEST_RUN_METRICS", {"cached": True})
    cached = critic_module._load_latest_metrics()
    assert cached == {"cached": True}

    monkeypatch.setattr(critic_module, "_LATEST_RUN_METRICS", None)
    monkeypatch.setenv("AXEL_PROMPT_RUN_METRICS", "not-json")
    assert critic_module._load_latest_metrics() == {}

    payload = json.dumps({"fitness_delta": 0.5})
    monkeypatch.setenv("AXEL_PROMPT_RUN_METRICS", payload)
    parsed = critic_module._load_latest_metrics()
    assert parsed["fitness_delta"] == 0.5


def test_load_latest_metrics_handles_missing_env(monkeypatch, critic_module):
    monkeypatch.setattr(critic_module, "_LATEST_RUN_METRICS", None)
    monkeypatch.delenv("AXEL_PROMPT_RUN_METRICS", raising=False)
    assert critic_module._load_latest_metrics() == {}


def test_collect_recent_scores_flattens_values(critic_module):
    series = critic_module.pd.Series(
        [[0.1, "0.2"], "0.3", object(), None], dtype=object
    )
    scores = critic_module._collect_recent_scores(series)
    assert scores == [0.1, 0.2, 0.3]


def test_cli_metadata_handles_missing_package(monkeypatch, critic_module):
    def raise_missing(_name: str) -> str:
        raise critic_module.importlib_metadata.PackageNotFoundError

    monkeypatch.setattr(critic_module.importlib_metadata, "version", raise_missing)
    monkeypatch.setattr(
        critic_module,
        "load_telemetry_config",
        lambda: SimpleNamespace(opt_in=False, consent_timestamp=None),
    )

    metadata = critic_module._cli_metadata()

    assert metadata["cli_version"] is None
    assert metadata["telemetry_opt_in"] is False


def test_orthogonality_entropy_identical_scores_returns_zero(critic_module):
    result = critic_module._orthogonality_entropy([0.5, 0.5, 0.5, 0.5])
    assert result == 0.0


def test_orthogonality_entropy_handles_pd_cut_error(critic_module, monkeypatch):
    def fake_cut(*_args, **_kwargs):
        raise ValueError("duplicate edges")

    monkeypatch.setattr(critic_module.pd, "cut", fake_cut)
    result = critic_module._orthogonality_entropy([0.1, 0.9])
    assert result == 0.0


def test_orthogonality_entropy_handles_empty_bins(monkeypatch, critic_module):
    assert critic_module._orthogonality_entropy([]) == 0.0

    def fake_cut_empty(series, **_kwargs):
        return critic_module.pd.Series([critic_module.pd.NA] * len(series))

    monkeypatch.setattr(critic_module.pd, "cut", fake_cut_empty)
    assert critic_module._orthogonality_entropy([0.1, 0.9]) == 0.0

    def fake_cut_single(series, **_kwargs):
        return critic_module.pd.Series(["bin"] * len(series))

    monkeypatch.setattr(critic_module.pd, "cut", fake_cut_single)
    assert critic_module._orthogonality_entropy([0.2, 0.8]) == 0.0


def test_orthogonality_entropy_handles_zero_max_entropy(monkeypatch, critic_module):
    monkeypatch.setattr(critic_module.math, "log", lambda _value: 0.0)
    result = critic_module._orthogonality_entropy([0.1, 0.9, 0.5])
    assert result == 0.0


def test_track_prompt_saturation_coerces_non_list_scores(critic_module, tmp_path):
    critic_module.ANALYTICS_ROOT = tmp_path / "analytics"
    critic_module.set_latest_run_metrics(
        {
            "fitness_delta": 0.1,
            "merged": 1,
            "closed": 1,
            "orthogonality_scores": "not-a-list",
        }
    )

    result = critic_module.track_prompt_saturation("octo", "prompt.md")
    assert result["orthogonality_entropy"] == 0.0


def test_format_saturation_output_includes_recommendation(critic_module):
    formatted = critic_module._format_saturation_output(
        {
            "prompt": "prompt.md",
            "saturation_score": 0.25,
            "fitness_delta_avg": 0.2,
            "merge_rate": 0.4,
            "orthogonality_entropy": 0.3,
            "prompt_refresh_recommended": True,
        }
    )
    assert "Recommendation" in formatted


def test_main_without_command_shows_help(critic_module, capsys):
    exit_code = critic_module.main([])
    output = capsys.readouterr().out
    assert exit_code == 1
    assert "usage" in output.lower()
