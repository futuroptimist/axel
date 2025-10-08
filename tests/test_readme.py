from pathlib import Path


def test_readme_marks_llm_quests_complete() -> None:
    """The roadmap should reflect the shipped cross-repo quest helper."""

    readme = Path(__file__).resolve().parents[1] / "README.md"
    content = readme.read_text(encoding="utf-8")

    assert "- [x] integrate LLM assistants to suggest quests across repos" in content
