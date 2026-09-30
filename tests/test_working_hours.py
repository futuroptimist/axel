from datetime import datetime, timedelta, timezone
from pathlib import Path
from zoneinfo import ZoneInfo

import pytest
import yaml

from axel import working_hours
from axel.working_hours import WorkingHours, load_working_hours


def test_default_policy_matches_checked_in_config():
    assert load_working_hours(Path(".axel/hillclimb/config.yml")) == WorkingHours()
    assert load_working_hours() == WorkingHours()


@pytest.mark.parametrize("day", range(28, 35))
@pytest.mark.parametrize(
    ("clock", "inside"),
    [("08:59:59", False), ("09:00:00", True), ("16:59:59", True), ("17:00:00", False)],
)
def test_weekday_and_weekend_boundaries(day, clock, inside):
    # September 28 through October 4, 2026 is Monday through Sunday.
    date = f"2026-09-{day}" if day <= 30 else f"2026-10-{day - 30:02}"
    local = datetime.fromisoformat(f"{date}T{clock}").replace(
        tzinfo=ZoneInfo("America/Los_Angeles")
    )
    assert WorkingHours().blocks_mutations(local) is (inside and local.weekday() < 5)


@pytest.mark.parametrize(
    ("date", "utc_start"),
    [("2026-03-06", 17), ("2026-03-09", 16), ("2026-10-30", 16), ("2026-11-02", 17)],
)
def test_dst_changes_preserve_nine_am_local_start(date, utc_start):
    policy = WorkingHours()
    before = datetime.fromisoformat(f"{date}T{utc_start - 1}:59:59+00:00")
    start = datetime.fromisoformat(f"{date}T{utc_start}:00:00+00:00")
    assert not policy.blocks_mutations(before)
    assert policy.blocks_mutations(start)
    end = start + timedelta(hours=8)
    assert policy.blocks_mutations(end - timedelta(microseconds=1))
    assert not policy.blocks_mutations(end)


@pytest.mark.parametrize(
    "instant", ["2026-03-08T10:00:00+00:00", "2026-11-01T09:00:00+00:00"]
)
def test_dst_transition_sundays_are_not_blocked(instant):
    assert not WorkingHours().blocks_mutations(datetime.fromisoformat(instant))


def test_utc_date_does_not_determine_local_weekday():
    policy = WorkingHours()
    assert policy.blocks_mutations(datetime.fromisoformat("2026-01-10T00:30:00+00:00"))
    assert not policy.blocks_mutations(
        datetime.fromisoformat("2026-01-12T16:30:00+00:00")
    )


def test_custom_schedule_from_yaml(tmp_path):
    path = tmp_path / "config.yml"
    path.write_text(
        """working_hours:
  timezone: Europe/London
  weekdays: [saturday]
  start: "10:30"
  end: "12:45"
"""
    )
    policy = load_working_hours(path)
    assert policy.blocks_mutations(datetime.fromisoformat("2026-07-04T09:30:00+00:00"))
    assert not policy.blocks_mutations(
        datetime.fromisoformat("2026-07-03T09:30:00+00:00")
    )
    assert not policy.blocks_mutations(
        datetime.fromisoformat("2026-07-04T11:45:00+00:00")
    )


def test_partial_and_missing_section_use_defaults(tmp_path):
    path = tmp_path / "config.yml"
    path.write_text("runs: 4\n")
    assert load_working_hours(path) == WorkingHours()
    path.write_text("working_hours:\n  timezone: UTC\n")
    assert load_working_hours(path) == WorkingHours(timezone="UTC")


@pytest.mark.parametrize(
    "section",
    [
        None,
        [],
        {"enabled": "false"},
        {"timezone": "Not/AZone"},
        {"timezone": 3},
        {"timezone": "/etc/localtime"},
        {"weekdays": []},
        {"weekdays": "monday"},
        {"weekdays": ["monday", "monday"]},
        {"weekdays": ["Monday"]},
        {"weekdays": [True]},
        {"start": "9:00"},
        {"start": 540},
        {"start": "25:00"},
        {"end": "17:00:00"},
        {"start": "17:00"},
        {"start": "22:00", "end": "06:00"},
        {"enabled": False, "timezone": "Not/AZone"},
        {"weekday": ["monday"]},
    ],
)
def test_invalid_configuration_fails_closed(tmp_path, section):
    path = tmp_path / "config.yml"
    path.write_text(yaml.safe_dump({"working_hours": section}))
    with pytest.raises(ValueError):
        load_working_hours(path)


@pytest.mark.parametrize("content", ["", "[]", "null", "working_hours: ["])
def test_invalid_configuration_document(tmp_path, content):
    path = tmp_path / "config.yml"
    path.write_text(content)
    with pytest.raises((ValueError, yaml.YAMLError)):
        load_working_hours(path)


def test_missing_explicit_config_fails_closed(tmp_path):
    with pytest.raises(FileNotFoundError):
        load_working_hours(tmp_path / "missing.yml")


def test_disabled_policy_allows_mutations():
    policy = WorkingHours(enabled=False)
    policy.require_mutations_allowed(
        datetime.fromisoformat("2026-09-28T16:00:00+00:00")
    )


def test_naive_timestamps_are_rejected():
    with pytest.raises(ValueError, match="timezone-aware"):
        WorkingHours().blocks_mutations(datetime(2026, 9, 28, 9))


def test_guard_uses_aware_current_time(monkeypatch):
    class Clock(datetime):
        @classmethod
        def now(cls, tz=None):
            assert tz is timezone.utc
            return datetime.fromisoformat("2026-09-28T16:00:00+00:00")

    monkeypatch.setattr(working_hours, "datetime", Clock)
    with pytest.raises(SystemExit, match="blocked during working hours"):
        WorkingHours().require_mutations_allowed()


def test_cli_allowed(monkeypatch, capsys):
    monkeypatch.setattr(WorkingHours, "blocks_mutations", lambda self, now=None: False)
    assert working_hours.main([]) == 0
    assert "other permissions still apply" in capsys.readouterr().out


def test_cli_blocked(monkeypatch):
    monkeypatch.setattr(WorkingHours, "blocks_mutations", lambda self, now=None: True)
    with pytest.raises(SystemExit, match="blocked during working hours"):
        working_hours.main([])


def test_cli_invalid_config(tmp_path):
    with pytest.raises(SystemExit) as error:
        working_hours.main(["--config", str(tmp_path / "missing.yml")])
    assert error.value.code == 2
