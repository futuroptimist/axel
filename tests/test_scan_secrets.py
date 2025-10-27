import subprocess
import sys
from subprocess import CompletedProcess

import pytest

PW_LITERAL = "".join(("pass", "word"))
API_MARKER_VARIANTS = [
    "".join(("api", "key")),
    "".join(("api", "_", "key")),
    "".join(("api", "-", "key")),
    "".join(("api", " ", "key")),
]
SEGMENTS_BY_VARIANT = {
    API_MARKER_VARIANTS[0]: ("api", "key"),
    API_MARKER_VARIANTS[1]: ("api", "_", "key"),
    API_MARKER_VARIANTS[2]: ("api", "-", "key"),
    API_MARKER_VARIANTS[3]: ("api", " ", "key"),
}


def run_scan(data: str) -> CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/scan-secrets.py"],
        input=data,
        text=True,
        capture_output=True,
    )


def _make_added_line(*segments: str) -> str:
    return "+" + "".join(segments) + "\n"


def _make_context_line(*segments: str) -> str:
    return " " + "".join(segments) + "\n"


def test_detects_keywords() -> None:
    result = run_scan(_make_added_line("pass", "word=123"))
    assert result.returncode == 1
    assert PW_LITERAL in result.stderr.lower()


def test_allows_safe_text() -> None:
    result = run_scan(_make_context_line("hello world"))
    assert result.returncode == 0
    assert result.stderr == ""


@pytest.mark.parametrize("var", API_MARKER_VARIANTS)
def test_detects_api_keys(var: str) -> None:
    suspect = _make_added_line(*SEGMENTS_BY_VARIANT[var], "=123")
    result = run_scan(suspect)
    assert result.returncode == 1
    assert var in result.stderr.lower()


def test_ignores_context_lines() -> None:
    """Context lines prefixed with space should not trigger detections."""

    result = run_scan(_make_context_line("pass", "word=123"))
    assert result.returncode == 0
    assert result.stderr == ""
