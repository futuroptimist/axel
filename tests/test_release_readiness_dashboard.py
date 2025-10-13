"""Tests for the release-readiness dashboard documentation."""

from pathlib import Path


def test_release_dashboard_marks_doc_status_complete() -> None:
    """Docs checklist should reflect shipped FAQ, issues, and status badge."""

    dashboard = (
        Path(__file__).resolve().parents[1] / "docs" / "RELEASE-READINESS-DASHBOARD.md"
    )
    content = dashboard.read_text(encoding="utf-8")
    assert "- [x] Docs: FAQ, Known issues/Footguns, Status: Alpha badge" in content


def test_release_dashboard_marks_ci_and_coverage_complete() -> None:
    """Release dashboard should acknowledge CI health and coverage badge."""

    root = Path(__file__).resolve().parents[1]
    dashboard = (root / "docs" / "RELEASE-READINESS-DASHBOARD.md").read_text(
        encoding="utf-8"
    )
    assert "- [x] CI green on default branch; coverage badge visible" in dashboard

    readme = (root / "README.md").read_text(encoding="utf-8")
    assert "[![Coverage]" in readme
