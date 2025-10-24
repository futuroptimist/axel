from __future__ import annotations

import argparse
import hashlib
import json
import os
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

CONSENT_TEXT = (
    "Axel collects telemetry only after an explicit opt-in. When enabled, "
    "the CLI records repository identifiers, command names, timestamps, "
    "analysis metrics, telemetry state, and identifiers for pending uploads."
)
CONSENT_TEXT_HASH = hashlib.sha256(CONSENT_TEXT.encode("utf-8")).hexdigest()
OUTBOUND_FIELDS = (
    "repository identifier",
    "command variant",
    "analytics metrics",
    "timestamps",
    "telemetry opt-in flag",
    "pending payload identifiers",
)


def _config_dir() -> Path:
    override = os.getenv("AXEL_CONFIG_DIR")
    if override:
        return Path(override).expanduser()
    return Path.home() / ".config" / "axel"


def _config_path() -> Path:
    return _config_dir() / "telemetry.json"


@dataclass
class TelemetryConfig:
    """Telemetry consent persisted on disk."""

    opt_in: bool = False
    consent_timestamp: str | None = None
    consent_text_hash: str = CONSENT_TEXT_HASH
    last_upload_attempt: str | None = None
    pending_payload_ids: list[str] = field(default_factory=list)


def load_telemetry_config(path: Path | None = None) -> TelemetryConfig:
    """Return telemetry configuration from *path* or defaults when missing."""

    config_path = path or _config_path()
    try:
        data = json.loads(config_path.read_text(encoding="utf-8"))
    except FileNotFoundError:
        return TelemetryConfig()
    except json.JSONDecodeError:
        return TelemetryConfig()

    return TelemetryConfig(
        opt_in=bool(data.get("opt_in", False)),
        consent_timestamp=data.get("consent_timestamp"),
        consent_text_hash=data.get("consent_text_hash", CONSENT_TEXT_HASH),
        last_upload_attempt=data.get("last_upload_attempt"),
        pending_payload_ids=list(data.get("pending_payload_ids", [])),
    )


def save_telemetry_config(config: TelemetryConfig, *, path: Path | None = None) -> Path:
    """Persist *config* to disk and return the path written."""

    config_path = path or _config_path()
    config_path.parent.mkdir(parents=True, exist_ok=True)
    config.consent_text_hash = CONSENT_TEXT_HASH
    config_path.write_text(
        json.dumps(asdict(config), indent=2, ensure_ascii=False) + "\n",
        encoding="utf-8",
    )
    return config_path


def enable_telemetry(
    *, auto_confirm: bool, path: Path | None = None
) -> TelemetryConfig:
    """Enable telemetry with consent tracking."""

    if not auto_confirm:
        response = input("Type 'yes' to enable telemetry: ").strip().lower()
        if response != "yes":
            print("Telemetry opt-in cancelled.")
            raise SystemExit(1)

    config = load_telemetry_config(path)
    config.opt_in = True
    config.consent_timestamp = datetime.now(timezone.utc).isoformat()
    config.consent_text_hash = CONSENT_TEXT_HASH
    config.pending_payload_ids = []
    config.last_upload_attempt = None
    save_telemetry_config(config, path=path)
    return config


def disable_telemetry(path: Path | None = None) -> TelemetryConfig:
    """Disable telemetry while preserving consent metadata."""

    config = load_telemetry_config(path)
    config.opt_in = False
    config.pending_payload_ids = []
    config.last_upload_attempt = None
    save_telemetry_config(config, path=path)
    return config


def status_message(config: TelemetryConfig) -> str:
    """Return a human-readable summary for *config*."""

    if config.opt_in:
        timestamp = config.consent_timestamp or "unknown time"
        return (
            "Telemetry is enabled; consent captured at "
            f"{timestamp}. Disable anytime with --disable."
        )
    return (
        "Telemetry is disabled by default. Enable with "
        "'axel config telemetry --enable' after reviewing the "
        "outbound fields."
    )


def _print_consent_notice() -> None:
    print("Telemetry remains disabled by default until you opt in. Axel collects:")
    for entry in OUTBOUND_FIELDS:
        print(f"- {entry}")
    print()
    print(CONSENT_TEXT)
    print()


def _validate_action_flags(
    enable: bool, disable: bool, status: bool, parser: argparse.ArgumentParser
) -> None:
    """Ensure exactly one telemetry action flag is provided."""

    if sum(bool(flag) for flag in (enable, disable, status)) != 1:
        parser.error("Specify exactly one of --enable, --disable, or --status")


def main(argv: Sequence[str] | None = None) -> int:
    """CLI entry point for telemetry configuration."""

    parser = argparse.ArgumentParser(description="Axel configuration helpers")
    sub = parser.add_subparsers(dest="command")

    telemetry = sub.add_parser("telemetry", help="Manage telemetry opt-in state")
    telemetry.add_argument("--enable", action="store_true", help="Enable telemetry")
    telemetry.add_argument("--disable", action="store_true", help="Disable telemetry")
    telemetry.add_argument(
        "--status", action="store_true", help="Show telemetry status"
    )
    telemetry.add_argument(
        "--yes",
        action="store_true",
        help="Automatically confirm prompts (useful for automation)",
    )

    args = parser.parse_args(argv)

    if args.command != "telemetry":
        parser.print_help()
        return 1

    _validate_action_flags(args.enable, args.disable, args.status, telemetry)

    config_path = _config_path()

    if args.status:
        config_state = load_telemetry_config(config_path)
        print(status_message(config_state))
        return 0

    if args.enable:
        _print_consent_notice()
        config_state = enable_telemetry(auto_confirm=args.yes, path=config_path)
        print(
            "Telemetry enabled. Consent recorded at "
            f"{config_state.consent_timestamp}."
        )
        return 0

    config_state = disable_telemetry(config_path)
    print("Telemetry disabled. Axel will retain consent history for auditing.")
    return 0


__all__ = [
    "TelemetryConfig",
    "CONSENT_TEXT",
    "CONSENT_TEXT_HASH",
    "OUTBOUND_FIELDS",
    "load_telemetry_config",
    "save_telemetry_config",
    "enable_telemetry",
    "disable_telemetry",
    "status_message",
    "main",
]


if __name__ == "__main__":  # pragma: no cover - CLI use
    raise SystemExit(main())
