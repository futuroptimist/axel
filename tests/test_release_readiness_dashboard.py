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


def test_release_dashboard_marks_security_scans_complete() -> None:
    """Security checklist should flip once CodeQL and scanning ship."""

    root = Path(__file__).resolve().parents[1]
    dashboard = (root / "docs" / "RELEASE-READINESS-DASHBOARD.md").read_text(
        encoding="utf-8"
    )
    assert "- [x] Security: CodeQL + credential scanning + Dependabot" in dashboard

    workflow = root / ".github" / "workflows" / "04-security.yml"
    assert workflow.exists(), "CodeQL workflow should be present for security scans"


def test_release_dashboard_marks_community_complete() -> None:
    """Community checklist should confirm templates and starter issues exist."""

    root = Path(__file__).resolve().parents[1]
    dashboard = (root / "docs" / "RELEASE-READINESS-DASHBOARD.md").read_text(
        encoding="utf-8"
    )
    assert (
        "- [x] Community: CONTRIBUTING, CoC, Issue/PR templates, ≥3 good first issues"
        in dashboard
    )

    templates_dir = root / ".github" / "ISSUE_TEMPLATE"
    assert templates_dir.exists(), "Issue templates directory should exist"
    assert any(
        path.suffix.lower() in {".md", ".markdown", ".yml", ".yaml"}
        for path in templates_dir.iterdir()
        if path.is_file()
    ), "Issue templates should include Markdown or YAML files"

    pr_template = root / ".github" / "PULL_REQUEST_TEMPLATE.md"
    assert pr_template.exists(), "Pull request template should exist"

    issue_dir = root / "issues"
    tagged = [
        path
        for path in issue_dir.glob("*.md")
        if "good first issue" in path.read_text(encoding="utf-8").lower()
    ]
    assert len(tagged) >= 3


def test_release_notes_cover_v0_sections() -> None:
    """Release notes should outline v0.1.0 highlights and onboarding guidance."""

    root = Path(__file__).resolve().parents[1]
    release_notes = (root / "docs" / "RELEASE_NOTES.md").read_text(encoding="utf-8")
    assert "## v0.1.0" in release_notes

    lines = release_notes.splitlines()
    headings = {
        "### What's New": None,
        "### Try it in 60s": None,
        "### Roadmap next": None,
    }

    for index, line in enumerate(lines):
        if line.strip() in headings:
            headings[line.strip()] = index

    for heading, position in headings.items():
        assert position is not None, f"Missing heading: {heading}"
        next_index = next(
            (
                idx
                for idx in range(position + 1, len(lines))
                if lines[idx].startswith("## ") or lines[idx].startswith("### ")
            ),
            len(lines),
        )
        section_lines = lines[position + 1 : next_index]
        assert any(
            line.strip().startswith("-") for line in section_lines
        ), f"Heading {heading} should include at least one bullet"

    dashboard = (root / "docs" / "RELEASE-READINESS-DASHBOARD.md").read_text(
        encoding="utf-8"
    )
    expected_line = (
        '- [x] Draft v0.1.0 release notes covering "What\'s new", '
        '"Try it in 60s", and "Roadmap next"'
    )
    assert expected_line in dashboard
