from __future__ import annotations

import subprocess
import sys
from pathlib import Path

import pytest


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
