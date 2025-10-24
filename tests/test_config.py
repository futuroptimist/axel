from __future__ import annotations

import argparse
from datetime import datetime
import json
from pathlib import Path

import pytest

import axel.config as config


CONSENT_HASH = config.CONSENT_TEXT_HASH


def _load_config(tmp_path: Path) -> dict[str, object]:
    path = tmp_path / "telemetry.json"
    assert path.exists(), "telemetry config should be written"
    return json.loads(path.read_text(encoding="utf-8"))


def test_enable_telemetry_records_consent(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Enabling telemetry should persist consent metadata with confirmation."""

    monkeypatch.setenv("AXEL_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr("builtins.input", lambda _: "yes")

    config.main(["telemetry", "--enable"])

    output = capsys.readouterr().out
    assert "Telemetry remains disabled by default" in output
    data = _load_config(tmp_path)
    assert data["opt_in"] is True
    assert data["consent_text_hash"] == CONSENT_HASH
    timestamp = data["consent_timestamp"]
    assert isinstance(timestamp, str)
    # ensure timestamp parses as ISO 8601
    datetime.fromisoformat(timestamp)
    assert data["pending_payload_ids"] == []


def test_enable_requires_confirmation(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Telemetry should remain disabled when confirmation is rejected."""

    monkeypatch.setenv("AXEL_CONFIG_DIR", str(tmp_path))
    monkeypatch.setattr("builtins.input", lambda _: "no")

    with pytest.raises(SystemExit) as excinfo:
        config.main(["telemetry", "--enable"])

    assert excinfo.value.code == 1
    output = capsys.readouterr().out
    assert "Telemetry opt-in cancelled" in output
    assert not (tmp_path / "telemetry.json").exists()


def test_enable_with_yes_skips_prompt(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Passing --yes should bypass interactive confirmation."""

    monkeypatch.setenv("AXEL_CONFIG_DIR", str(tmp_path))

    config.main(["telemetry", "--enable", "--yes"])

    data = _load_config(tmp_path)
    assert data["opt_in"] is True


def test_disable_clears_opt_in(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Disabling telemetry should flip the opt-in flag and retain history."""

    monkeypatch.setenv("AXEL_CONFIG_DIR", str(tmp_path))

    config.main(["telemetry", "--enable", "--yes"])
    config.main(["telemetry", "--disable"])

    data = _load_config(tmp_path)
    assert data["opt_in"] is False
    assert data["consent_text_hash"] == CONSENT_HASH


def test_status_reports_current_state(
    monkeypatch: pytest.MonkeyPatch, capsys: pytest.CaptureFixture[str], tmp_path: Path
) -> None:
    """Status output should reflect default-off behavior and opt-in state."""

    monkeypatch.setenv("AXEL_CONFIG_DIR", str(tmp_path))

    config.main(["telemetry", "--status"])
    first_output = capsys.readouterr().out
    assert "Telemetry is disabled by default" in first_output

    config.main(["telemetry", "--enable", "--yes"])
    config.main(["telemetry", "--status"])
    second_output = capsys.readouterr().out
    assert "Telemetry is enabled" in second_output
    assert "consent captured" in second_output


def test_config_dir_defaults_to_home(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Config directory should fall back to ~/.config/axel when unset."""

    monkeypatch.delenv("AXEL_CONFIG_DIR", raising=False)

    def _fake_home() -> Path:
        return tmp_path

    monkeypatch.setattr(config.Path, "home", staticmethod(_fake_home))

    default_dir = config._config_dir()
    assert default_dir == tmp_path / ".config" / "axel"


def test_load_config_handles_invalid_json(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Invalid JSON should return default telemetry configuration."""

    monkeypatch.setenv("AXEL_CONFIG_DIR", str(tmp_path))
    target = tmp_path / "telemetry.json"
    target.write_text("not-json", encoding="utf-8")

    state = config.load_telemetry_config(path=target)
    assert state.opt_in is False
    assert state.consent_timestamp is None


def test_main_requires_action(monkeypatch: pytest.MonkeyPatch) -> None:
    """CLI should error when no telemetry action is provided."""

    with pytest.raises(SystemExit) as excinfo:
        config.main(["telemetry"])

    assert excinfo.value.code == 2


def test_main_without_subcommand_shows_help(
    capsys: pytest.CaptureFixture[str],
) -> None:
    """Invoking the CLI without a subcommand should print help and return 1."""

    result = config.main([])
    output = capsys.readouterr()
    assert "Axel configuration helpers" in output.out
    assert result == 1


def test_validate_action_flags_enforces_single_choice() -> None:
    """Helper should require exactly one telemetry action flag."""

    parser = argparse.ArgumentParser(prog="telemetry")
    with pytest.raises(SystemExit):
        config._validate_action_flags(False, False, False, parser)
    with pytest.raises(SystemExit):
        config._validate_action_flags(True, True, False, parser)

    # Valid combinations should not raise
    config._validate_action_flags(True, False, False, parser)


def test_status_uses_config_path(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Status command should load configuration from the computed path."""

    monkeypatch.setenv("AXEL_CONFIG_DIR", str(tmp_path))
    captured: dict[str, Path] = {}

    def _fake_load(path: Path) -> config.TelemetryConfig:
        captured["path"] = path
        return config.TelemetryConfig()

    monkeypatch.setattr(config, "load_telemetry_config", _fake_load)
    config.main(["telemetry", "--status"])

    expected = tmp_path / "telemetry.json"
    assert captured["path"] == expected
