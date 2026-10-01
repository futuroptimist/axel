"""Configurable working hours during which repository mutations are blocked."""

from __future__ import annotations

import argparse
import re
from collections.abc import Mapping, Sequence
from dataclasses import dataclass
from datetime import datetime, time, timezone
from pathlib import Path
from zoneinfo import ZoneInfo, ZoneInfoNotFoundError

import yaml

WEEKDAYS = (
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
)


def _clock_time(value: str) -> time:
    if not isinstance(value, str) or not re.fullmatch(r"\d{2}:\d{2}", value):
        raise ValueError("Working hours must use quoted HH:MM times")
    try:
        return time.fromisoformat(value)
    except ValueError as exc:
        raise ValueError("Working hours must use valid HH:MM times") from exc


@dataclass(frozen=True)
class WorkingHours:
    """A same-day blocked window, interpreted in an IANA time zone."""

    enabled: bool = True
    timezone: str = "America/Los_Angeles"
    weekdays: tuple[str, ...] = WEEKDAYS[:5]
    start: str = "09:00"
    end: str = "17:00"

    def __post_init__(self) -> None:
        if not isinstance(self.enabled, bool):
            raise ValueError("working_hours.enabled must be true or false")
        if not isinstance(self.timezone, str):
            raise ValueError("working_hours.timezone must be an IANA time zone")
        try:
            ZoneInfo(self.timezone)
        except (ZoneInfoNotFoundError, ValueError) as exc:
            raise ValueError(
                f"Unknown working-hours time zone: {self.timezone}"
            ) from exc
        if (
            not isinstance(self.weekdays, (tuple, list))
            or not self.weekdays
            or any(day not in WEEKDAYS for day in self.weekdays)
            or len(set(self.weekdays)) != len(self.weekdays)
        ):
            raise ValueError("working_hours.weekdays must contain unique weekday names")
        object.__setattr__(self, "weekdays", tuple(self.weekdays))
        if _clock_time(self.start) >= _clock_time(self.end):
            raise ValueError("working_hours.start must be before end on the same day")

    def blocks_mutations(self, now: datetime | None = None) -> bool:
        """Return whether *now* is in the start-inclusive, end-exclusive window.

        An explicit timestamp must be timezone-aware. The system clock is read in
        UTC and converted to the configured zone so DST follows local wall time.
        """
        instant = now if now is not None else datetime.now(timezone.utc)
        if instant.tzinfo is None or instant.utcoffset() is None:
            raise ValueError("Working-hours checks require a timezone-aware timestamp")
        local = instant.astimezone(ZoneInfo(self.timezone))
        return (
            self.enabled
            and WEEKDAYS[local.weekday()] in self.weekdays
            and _clock_time(self.start) <= local.time() < _clock_time(self.end)
        )

    def require_mutations_allowed(self, now: datetime | None = None) -> None:
        """Stop the caller before a mutation if the blocked window is active."""
        if self.blocks_mutations(now):
            raise SystemExit(
                "Repository mutations are blocked during working hours "
                f"({', '.join(self.weekdays)}, {self.start}–{self.end} "
                f"{self.timezone}). Read-only inspection and planning may continue."
            )


def load_working_hours(path: Path | None = None) -> WorkingHours:
    """Load the ``working_hours`` YAML section; omitted fields use defaults.

    An explicitly supplied missing or invalid file fails closed. Only omission
    of the section uses defaults; an invalid section must not disable the guard.
    """
    if path is None:
        return WorkingHours()
    data = yaml.safe_load(Path(path).read_text(encoding="utf-8"))
    if not isinstance(data, Mapping):
        raise ValueError("Working-hours configuration must be a YAML mapping")
    section = data.get("working_hours", {})
    if not isinstance(section, Mapping):
        raise ValueError("working_hours must be a YAML mapping")
    unknown = set(section) - {"enabled", "timezone", "weekdays", "start", "end"}
    if unknown:
        raise ValueError(
            "Unknown working_hours settings: " + ", ".join(map(str, unknown))
        )
    return WorkingHours(**section)


def main(argv: Sequence[str] | None = None) -> int:
    """Read-only guard for scripts: exit 0 when allowed, 1 blocked, 2 invalid."""
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument(
        "--config", type=Path, help="YAML file with working_hours settings"
    )
    args = parser.parse_args(argv)
    try:
        policy = load_working_hours(args.config)
    except (OSError, ValueError, yaml.YAMLError) as exc:
        parser.error(str(exc))
    policy.require_mutations_allowed()
    print("Outside blocked working hours; other permissions still apply.")
    return 0


if __name__ == "__main__":  # pragma: no cover - CLI entry point
    raise SystemExit(main())
