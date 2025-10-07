from __future__ import annotations

from pathlib import Path
from typing import Iterator

import pytest

import axel.flywheel as flywheel


class DummyResponse:
    def __init__(self, status_code: int) -> None:
        self.status_code = status_code

    def raise_for_status(self) -> None:
        raise RuntimeError(f"HTTP {self.status_code}")


def make_responses(statuses: list[int]) -> Iterator[DummyResponse]:
    for status in statuses:
        yield DummyResponse(status)


def test_evaluate_flywheel_alignment_reports_missing_workflows(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    calls: list[str] = []
    responses = make_responses([200, 404])

    def fake_get(url: str, *, headers: dict[str, str], timeout: int) -> DummyResponse:
        calls.append(url)
        return next(responses)

    monkeypatch.setattr(flywheel.requests, "get", fake_get)

    repos = ["https://github.com/example/project"]
    results = flywheel.evaluate_flywheel_alignment(repos)

    assert results == [
        {
            "repo": "example/project",
            "workflows": {
                "01-lint-format.yml": True,
                "02-tests.yml": False,
            },
            "missing": ["02-tests.yml"],
            "aligned": False,
        }
    ]
    assert len(calls) == 2


def test_evaluate_handles_unparseable_entry(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = make_responses([404, 404])

    def fake_get(url: str, *, headers: dict[str, str], timeout: int) -> DummyResponse:
        return next(responses)

    monkeypatch.setattr(flywheel.requests, "get", fake_get)

    results = flywheel.evaluate_flywheel_alignment(["example-project"])

    assert results[0]["repo"] == "example-project"
    assert results[0]["missing"] == [
        "01-lint-format.yml",
        "02-tests.yml",
    ]


def test_evaluate_includes_token(monkeypatch: pytest.MonkeyPatch) -> None:
    captured: list[str | None] = []
    responses = make_responses([200, 200])

    def fake_get(url: str, *, headers: dict[str, str], timeout: int) -> DummyResponse:
        captured.append(headers.get("Authorization"))
        return next(responses)

    monkeypatch.setattr(flywheel.requests, "get", fake_get)

    flywheel.evaluate_flywheel_alignment(
        ["https://github.com/example/project"], token="abc123"
    )

    assert captured == ["token abc123", "token abc123"]


def test_main_prints_alignment_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_file = tmp_path / "repos.txt"
    repo_file.write_text("https://github.com/example/project\n", encoding="utf-8")

    captured: dict[str, object] = {}

    def fake_evaluate(repos: list[str], token: str | None = None):
        captured["repos"] = repos
        captured["token"] = token
        return [
            {
                "repo": "example/project",
                "workflows": {
                    "01-lint-format.yml": True,
                    "02-tests.yml": False,
                },
                "missing": ["02-tests.yml"],
                "aligned": False,
            }
        ]

    monkeypatch.setattr(flywheel, "evaluate_flywheel_alignment", fake_evaluate)

    flywheel.main(["--path", str(repo_file)])

    out = capsys.readouterr().out
    assert "example/project" in out
    assert "02-tests.yml" in out
    assert captured["repos"] == ["https://github.com/example/project"]
    assert captured["token"] is None


def test_evaluate_accepts_slug_without_scheme(monkeypatch: pytest.MonkeyPatch) -> None:
    responses = make_responses([200, 200])

    def fake_get(url: str, *, headers: dict[str, str], timeout: int) -> DummyResponse:
        return next(responses)

    monkeypatch.setattr(flywheel.requests, "get", fake_get)

    results = flywheel.evaluate_flywheel_alignment(["owner/project"])

    assert results[0]["repo"] == "owner/project"


def test_main_reports_aligned_repo(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_file = tmp_path / "repos.txt"
    repo_file.write_text("https://github.com/example/project\n", encoding="utf-8")

    monkeypatch.setattr(
        flywheel,
        "evaluate_flywheel_alignment",
        lambda repos, token=None: [
            {
                "repo": "example/project",
                "workflows": {
                    "01-lint-format.yml": True,
                    "02-tests.yml": True,
                },
                "missing": [],
                "aligned": True,
            }
        ],
    )

    flywheel.main(["--path", str(repo_file)])

    out = capsys.readouterr().out
    assert "aligned" in out.lower()


def test_main_handles_empty_repo_file(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_file = tmp_path / "repos.txt"
    repo_file.write_text("", encoding="utf-8")

    flywheel.main(["--path", str(repo_file)])

    assert "no repositories to evaluate" in capsys.readouterr().out.lower()


def test_workflow_exists_raises_on_unexpected_status(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    class ErrorResponse(DummyResponse):
        def raise_for_status(self) -> None:
            raise RuntimeError("boom")

    def fake_get(url: str, *, headers: dict[str, str], timeout: int) -> DummyResponse:
        return ErrorResponse(500)

    monkeypatch.setattr(flywheel.requests, "get", fake_get)

    with pytest.raises(RuntimeError):
        flywheel._workflow_exists(
            "owner/repo",
            "01-lint-format.yml",
            None,
        )


def test_slug_from_url_invalid() -> None:
    with pytest.raises(ValueError):
        flywheel._slug_from_url("not-a-repo")


def test_main_passes_token_to_evaluate(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_file = tmp_path / "repos.txt"
    repo_file.write_text("https://github.com/example/project\n", encoding="utf-8")

    captured: dict[str, object] = {}

    def fake_evaluate(repos: list[str], token: str | None = None):
        captured["token"] = token
        return []

    monkeypatch.setattr(flywheel, "evaluate_flywheel_alignment", fake_evaluate)

    flywheel.main(["--path", str(repo_file), "--token", "secret-token"])

    assert captured["token"] == "secret-token"
