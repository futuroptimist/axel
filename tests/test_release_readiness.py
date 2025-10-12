from __future__ import annotations

from pathlib import Path


def test_release_dashboard_marks_quickstart_complete() -> None:
    """Release dashboard should acknowledge the shipped Quickstart workflow."""

    root = Path(__file__).resolve().parents[1]
    dashboard = (root / "docs" / "RELEASE-READINESS-DASHBOARD.md").read_text(
        encoding="utf-8"
    )
    assert "- [x] Quickstart (≤60s) at top of README" in dashboard

    readme_lines = (root / "README.md").read_text(encoding="utf-8").splitlines()
    quickstart_index = next(
        (
            idx
            for idx, line in enumerate(readme_lines)
            if line.strip().lower() == "## quickstart (≤60s)"
        ),
        None,
    )
    status_index = next(
        (
            idx
            for idx, line in enumerate(readme_lines)
            if line.strip().lower() == "## status"
        ),
        None,
    )

    assert quickstart_index is not None, "README.md must include a Quickstart section"
    assert status_index is not None, "README.md must include a status section"
    assert (
        quickstart_index < status_index
    ), "Quickstart section should appear before the status section in README.md"
