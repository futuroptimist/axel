from __future__ import annotations

import re
from pathlib import Path


def test_llms_sample_repo_link_exists() -> None:
    """The llms.txt sample repo link should exist and contain URLs."""

    root = Path(__file__).resolve().parents[1]
    llms_file = root / "llms.txt"
    content = llms_file.read_text(encoding="utf-8")

    match = re.search(r"\[Sample repos list]\(([^)]+)\)", content)
    assert match, "llms.txt must link to the sample repo list"

    link = match.group(1)
    sample_path = (root / Path(link)).resolve()
    assert sample_path.exists(), f"Sample repo list not found at {link}"

    raw_lines = sample_path.read_text(encoding="utf-8").splitlines()
    lines = [line.strip() for line in raw_lines]
    repo_lines = [line for line in lines if line and not line.startswith("#")]
    assert repo_lines, (
        "Sample repo list should include at least one repository entry"
    )
    assert all(
        line.startswith("https://")
        for line in repo_lines
    ), "Sample repo entries should be GitHub-style URLs"
