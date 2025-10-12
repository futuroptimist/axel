"""Tests for the release-readiness dashboard documentation."""

from pathlib import Path


def test_release_dashboard_marks_doc_status_complete() -> None:
    """Docs checklist should reflect shipped FAQ, issues, and status badge."""

    dashboard = (
        Path(__file__).resolve().parents[1]
        / "docs"
        / "RELEASE-READINESS-DASHBOARD.md"
    )
    content = dashboard.read_text(encoding="utf-8")
    assert (
        "- [x] Docs: FAQ, Known issues/Footguns, Status: Alpha badge" in content
    )
