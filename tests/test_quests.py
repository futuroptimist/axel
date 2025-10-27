from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest
from pytest import CaptureFixture


@pytest.fixture(autouse=True)
def _reset_token_place_cache() -> None:
    """Ensure token.place model cache stays isolated per test."""

    import axel.token_place as token_place

    token_place._clear_model_cache()
    yield
    token_place._clear_model_cache()


def test_suggest_cross_repo_quests_links_repos() -> None:
    from axel.quests import suggest_cross_repo_quests

    repos = [
        "https://github.com/futuroptimist/axel",
        "https://github.com/futuroptimist/gabriel",
        "https://github.com/futuroptimist/token.place",
    ]

    suggestions = suggest_cross_repo_quests(repos, limit=2)

    assert len(suggestions) == 2
    first = suggestions[0]
    assert first["repos"] == ["futuroptimist/axel", "futuroptimist/gabriel"]
    assert "axel" in first["summary"].lower()
    assert "gabriel" in first["summary"].lower()
    assert "security" in first["details"].lower()


def test_suggest_cross_repo_quests_mentions_gabriel_for_sensitive_pairs() -> None:
    from axel.quests import suggest_cross_repo_quests

    repos = [
        "https://github.com/futuroptimist/token.place",
        "https://github.com/futuroptimist/dspace",
    ]

    suggestions = suggest_cross_repo_quests(repos, limit=1)

    assert "gabriel" in suggestions[0]["details"].lower()


def test_suggest_cross_repo_quests_prioritizes_token_template() -> None:
    from axel.quests import suggest_cross_repo_quests

    repos = [
        "https://github.com/futuroptimist/token.place",
        "https://github.com/futuroptimist/blog",
    ]

    suggestions = suggest_cross_repo_quests(repos, limit=1)
    details = suggestions[0]["details"].lower()

    assert "gabriel" in details
    assert "token.place" in details


def test_suggest_cross_repo_quests_enriches_token_place_with_models(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import axel.token_place as token_place
    from axel.quests import suggest_cross_repo_quests

    monkeypatch.setattr(
        token_place,
        "list_models",
        lambda base_url=None, api_key=None, timeout=token_place.DEFAULT_TIMEOUT: [
            "llama-3-8b-instruct",
            "llama-3-8b-instruct:alignment",
        ],
    )

    repos = [
        "https://github.com/futuroptimist/token.place",
        "https://github.com/futuroptimist/dspace",
    ]

    suggestions = suggest_cross_repo_quests(repos, limit=1)
    details = suggestions[0]["details"].lower()

    assert "llama-3-8b-instruct" in details
    assert "token.place" in details


def test_suggest_cross_repo_quests_handles_token_place_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import axel.token_place as token_place
    from axel.quests import suggest_cross_repo_quests

    def boom(**_: object) -> list[str]:  # pragma: no cover - helper
        raise token_place.TokenPlaceError("offline")

    monkeypatch.setattr(token_place, "list_models", boom)

    repos = [
        "https://github.com/futuroptimist/token.place",
        "https://github.com/futuroptimist/axel",
    ]

    suggestions = suggest_cross_repo_quests(repos, limit=1)
    details = suggestions[0]["details"].lower()

    assert "token.place" in details
    assert "llama-3-8b" not in details


def test_suggest_cross_repo_quests_forwards_token_place_config(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import axel.quests as quests

    captured: dict[str, tuple[str | None, str | None]] = {}

    def fake_detail(
        primary_slug: str,
        secondary_slug: str,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> str:
        captured["slugs"] = (primary_slug, secondary_slug)
        captured["config"] = (base_url, api_key)
        return "token quest"

    monkeypatch.setattr(quests.token_place_integration, "quest_detail", fake_detail)

    repos = [
        "https://github.com/futuroptimist/token.place",
        "https://github.com/futuroptimist/dspace",
    ]

    suggestions = quests.suggest_cross_repo_quests(
        repos,
        limit=1,
        token_place_base_url="https://token.place/api/v1",
        token_place_api_key="secret",
    )

    assert captured["slugs"] == (
        "futuroptimist/token.place",
        "futuroptimist/dspace",
    )
    assert captured["config"] == ("https://token.place/api/v1", "secret")
    assert suggestions[0]["details"] == "token quest"


def test_suggest_cross_repo_quests_includes_featured_model_in_summary(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import axel.token_place as token_place
    from axel.quests import suggest_cross_repo_quests

    monkeypatch.setattr(
        token_place,
        "list_models",
        lambda base_url=None, api_key=None, timeout=token_place.DEFAULT_TIMEOUT: [
            "llama-3-8b-instruct",
            "llama-3-8b-instruct:alignment",
        ],
    )

    repos = [
        "https://github.com/futuroptimist/token.place",
        "https://github.com/futuroptimist/dspace",
    ]

    suggestions = suggest_cross_repo_quests(repos, limit=1)
    summary = suggestions[0]["summary"].lower()

    assert "token.place" in summary
    assert "via llama-3-8b-instruct:alignment" in summary


def test_suggest_cross_repo_quests_exposes_featured_model_metadata(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import axel.token_place as token_place
    from axel.quests import suggest_cross_repo_quests

    monkeypatch.setattr(
        token_place,
        "list_models",
        lambda base_url=None, api_key=None, timeout=token_place.DEFAULT_TIMEOUT: [
            "llama-3-8b-instruct",
            "llama-3-8b-instruct:alignment",
        ],
    )

    repos = [
        "https://github.com/futuroptimist/token.place",
        "https://github.com/futuroptimist/dspace",
    ]

    suggestions = suggest_cross_repo_quests(repos, limit=1)

    assert suggestions[0]["token_place_model"] == "llama-3-8b-instruct:alignment"


def test_suggest_cross_repo_quests_sets_model_to_none_when_unavailable(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    import axel.token_place as token_place
    from axel.quests import suggest_cross_repo_quests

    def boom(**_: object) -> list[str]:  # pragma: no cover - helper
        raise token_place.TokenPlaceError("offline")

    monkeypatch.setattr(token_place, "list_models", boom)

    repos = [
        "https://github.com/futuroptimist/token.place",
        "https://github.com/futuroptimist/axel",
    ]

    suggestions = suggest_cross_repo_quests(repos, limit=1)

    assert suggestions[0]["token_place_model"] is None


@pytest.mark.parametrize(
    "repos",
    [
        [],
        ["https://github.com/futuroptimist/axel"],
    ],
)
def test_suggest_cross_repo_quests_requires_multiple_repos(repos: list[str]) -> None:
    from axel.quests import suggest_cross_repo_quests

    assert suggest_cross_repo_quests(repos) == []


def test_cli_prints_suggestions(tmp_path: Path) -> None:
    repo_file = tmp_path / "repos.txt"
    repo_file.write_text(
        "https://github.com/futuroptimist/axel\n"
        "https://github.com/futuroptimist/gabriel\n"
        "https://github.com/futuroptimist/token.place\n"
    )

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "axel.quests",
            "--path",
            str(repo_file),
            "--limit",
            "1",
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(Path(__file__).resolve().parents[1])},
        check=True,
    )

    output = result.stdout.lower()
    assert "axel" in output
    assert "gabriel" in output
    assert "quest" in output


def test_cli_prints_token_place_model_when_available(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch, capsys: CaptureFixture[str]
) -> None:
    import axel.quests as quests
    import axel.token_place as token_place

    repo_file = tmp_path / "repos.txt"
    repo_file.write_text(
        "https://github.com/futuroptimist/token.place\n"
        "https://github.com/futuroptimist/dspace\n",
        encoding="utf-8",
    )

    monkeypatch.setattr(
        token_place,
        "list_models",
        lambda base_url=None, api_key=None, timeout=token_place.DEFAULT_TIMEOUT: [
            "llama-3-8b-instruct",
            "llama-3-8b-instruct:alignment",
        ],
    )

    quests.main(["--path", str(repo_file), "--limit", "1"])

    out, err = capsys.readouterr()
    assert "token.place model" in out
    assert "llama-3-8b-instruct:alignment" in out
    assert err == ""


def test_cli_forwards_token_place_configuration(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    import axel.quests as quests

    repo_file = tmp_path / "repos.txt"
    repo_file.write_text(
        "https://github.com/futuroptimist/token.place\n"
        "https://github.com/futuroptimist/axel\n",
        encoding="utf-8",
    )

    captured: list[tuple[str | None, str | None]] = []

    def fake_detail(
        primary_slug: str,
        secondary_slug: str,
        *,
        base_url: str | None = None,
        api_key: str | None = None,
    ) -> str:
        captured.append((base_url, api_key))
        return "configured quest"

    monkeypatch.setattr(quests.token_place_integration, "quest_detail", fake_detail)

    quests.main(
        [
            "--path",
            str(repo_file),
            "--limit",
            "1",
            "--token-place-url",
            "https://token.place/api/v1",
            "--token-place-key",
            "secret",
        ]
    )

    assert captured == [("https://token.place/api/v1", "secret")]


def test_suggest_cross_repo_quests_handles_incomplete_urls() -> None:
    from axel.quests import suggest_cross_repo_quests

    repos = [
        "https://github.com/futuroptimist/axel",
        "https://example.com/solo",
        "https://example.com",
    ]

    suggestions = suggest_cross_repo_quests(repos, limit=3)
    slugs = [tuple(item["repos"]) for item in suggestions]

    assert ("futuroptimist/axel", "solo") in slugs
    assert ("example.com", "futuroptimist/axel") in slugs
    assert any("share context" in item["details"] for item in suggestions)


def test_suggest_cross_repo_quests_formats_default_detail() -> None:
    from axel.quests import suggest_cross_repo_quests

    repos = [
        "https://github.com/example/alpha",
        "https://github.com/example/beta",
    ]

    suggestions = suggest_cross_repo_quests(repos, limit=1)

    assert suggestions[0]["details"] == (
        "Plan a quest where example/alpha and example/beta share context to "
        "unlock a cross-repo improvement."
    )


def test_suggest_cross_repo_quests_respects_limit_zero() -> None:
    from axel.quests import suggest_cross_repo_quests

    repos = [
        "https://github.com/futuroptimist/axel",
        "https://github.com/futuroptimist/gitshelves",
    ]

    assert suggest_cross_repo_quests(repos, limit=0) == []


def test_suggest_cross_repo_quests_deduplicates_case_insensitive() -> None:
    from axel.quests import suggest_cross_repo_quests

    repos = [
        "https://github.com/futuroptimist/Axel",
        "https://github.com/futuroptimist/axel",
        "https://github.com/futuroptimist/gitshelves",
    ]

    suggestions = suggest_cross_repo_quests(repos)

    assert len(suggestions) == 1
    assert suggestions[0]["repos"] == ["futuroptimist/Axel", "futuroptimist/gitshelves"]


def test_cli_handles_no_suggestions(tmp_path: Path) -> None:
    repo_file = tmp_path / "repos.txt"
    repo_file.write_text("https://github.com/futuroptimist/axel\n")

    result = subprocess.run(
        [
            sys.executable,
            "-m",
            "axel.quests",
            "--path",
            str(repo_file),
        ],
        cwd=Path(__file__).resolve().parents[1],
        capture_output=True,
        text=True,
        env={"PYTHONPATH": str(Path(__file__).resolve().parents[1])},
        check=True,
    )

    assert "no quests available" in result.stdout.lower()


def test_main_prints_quests(tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
    repo_file = tmp_path / "repos.txt"
    repo_file.write_text(
        "https://github.com/futuroptimist/axel\n"
        "https://github.com/futuroptimist/gabriel\n"
    )

    from axel.quests import main

    main(["--path", str(repo_file), "--limit", "1"])

    output = capsys.readouterr().out.lower()
    assert "axel" in output
    assert "gabriel" in output
    assert "quest" in output


def test_main_handles_no_suggestions(
    tmp_path: Path, capsys: pytest.CaptureFixture[str]
) -> None:
    repo_file = tmp_path / "repos.txt"
    repo_file.write_text("https://github.com/futuroptimist/axel\n")

    from axel.quests import main

    main(["--path", str(repo_file)])

    output = capsys.readouterr().out.lower()
    assert "no quests available" in output
