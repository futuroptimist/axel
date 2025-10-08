from pathlib import Path


def test_readme_marks_llm_quests_complete() -> None:
    """The roadmap should reflect the shipped cross-repo quest helper."""

    readme = Path(__file__).resolve().parents[1] / "README.md"
    content = readme.read_text(encoding="utf-8")

    assert "- [x] integrate LLM assistants to suggest quests across repos" in content


def test_readme_marks_gabriel_security_layer_complete() -> None:
    """The roadmap should acknowledge the gabriel security integration."""

    readme = Path(__file__).resolve().parents[1] / "README.md"
    content = readme.read_text(encoding="utf-8")

    expected = (
        "- [x] integrate [`gabriel`](https://github.com/futuroptimist/gabriel) "
        "as a security layer across repos"
    )
    assert expected in content
