import subprocess
import sys

import pytest


def run_scan(data: str) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        [sys.executable, "scripts/scan-secrets.py"],
        input=data,
        text=True,
        capture_output=True,
    )


def test_detects_keywords() -> None:
    result = run_scan("password=123")
    assert result.returncode == 1
    assert "password" in result.stderr.lower()


def test_allows_safe_text() -> None:
    result = run_scan("hello world")
    assert result.returncode == 0
    assert result.stderr == ""


@pytest.mark.parametrize("var", ["apikey", "api_key", "api-key"])
def test_detects_api_keys(var: str) -> None:
    result = run_scan(f"{var}=123")
    assert result.returncode == 1
    assert var in result.stderr.lower()
