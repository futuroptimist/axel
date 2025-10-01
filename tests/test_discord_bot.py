import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest

discord = pytest.importorskip("discord")

sys.path.append(str(Path(__file__).resolve().parents[1]))  # noqa: E402

import axel.discord_bot as db  # noqa: E402


class DummyAuthor:
    display_name = "user"


class DummyChannel:
    def __init__(self, name: str, parent: "DummyChannel | None" = None) -> None:
        self.name = name
        self.parent = parent


class DummyMessage:
    def __init__(
        self,
        content: str,
        mid: int = 1,
        created_at: datetime | None = None,
        channel: DummyChannel | None = None,
        jump_url: str = "https://discord.com/channels/1/2/3",
    ) -> None:
        self.content = content
        self.id = mid
        self.author = DummyAuthor()
        self.created_at = created_at or datetime(2024, 1, 1, tzinfo=timezone.utc)
        self.channel = channel or DummyChannel("general")
        self.jump_url = jump_url


def test_save_message(tmp_path: Path) -> None:
    db.SAVE_DIR = tmp_path
    msg = DummyMessage("hello")
    path = db.save_message(msg)
    expected = (
        "# user\n\n"
        "- timestamp: 2024-01-01T00:00:00+00:00\n"
        "- channel: general\n"
        "- link: https://discord.com/channels/1/2/3\n\n"
        "hello\n"
    )
    assert path == tmp_path / "general" / "1.md"
    assert path.read_text() == expected


def test_save_message_creates_dir(tmp_path: Path) -> None:
    missing = tmp_path / "discord"
    db.SAVE_DIR = missing
    msg = DummyMessage("hi", mid=2)
    path = db.save_message(msg)
    assert path.read_text() == (
        "# user\n\n"
        "- timestamp: 2024-01-01T00:00:00+00:00\n"
        "- channel: general\n"
        "- link: https://discord.com/channels/1/2/3\n\n"
        "hi\n"
    )
    assert missing.exists()


def test_save_message_respects_env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AXEL_DISCORD_DIR", str(tmp_path))
    msg = DummyMessage("hey", mid=3)
    path = db.save_message(msg)
    assert path.parent == tmp_path / "general"
    assert path.read_text() == (
        "# user\n\n"
        "- timestamp: 2024-01-01T00:00:00+00:00\n"
        "- channel: general\n"
        "- link: https://discord.com/channels/1/2/3\n\n"
        "hey\n"
    )


def test_save_message_env_expands_user(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AXEL_DISCORD_DIR", "~/discord")
    msg = DummyMessage("home", mid=4)
    path = db.save_message(msg)
    assert path.parent == tmp_path / "discord" / "general"
    assert path.read_text() == (
        "# user\n\n"
        "- timestamp: 2024-01-01T00:00:00+00:00\n"
        "- channel: general\n"
        "- link: https://discord.com/channels/1/2/3\n\n"
        "home\n"
    )


def test_save_message_includes_thread_metadata(tmp_path: Path) -> None:
    db.SAVE_DIR = tmp_path
    parent = DummyChannel("design")
    thread = DummyChannel("Sprint Review", parent=parent)
    msg = DummyMessage("thread note", mid=5, channel=thread)
    path = db.save_message(msg)
    assert path == tmp_path / "design" / "5.md"
    assert "- thread: Sprint Review" in path.read_text()


def test_save_message_sanitizes_channel_name(tmp_path: Path) -> None:
    db.SAVE_DIR = tmp_path
    channel = DummyChannel("design/review 💬")
    msg = DummyMessage("sanitize", mid=6, channel=channel)
    path = db.save_message(msg)
    assert path == tmp_path / "design-review" / "6.md"


def test_run_requires_env_variable(monkeypatch) -> None:
    """``run`` exits if the Discord bot token variable is missing."""
    monkeypatch.delenv(db.TOKEN_ENV_VAR, raising=False)
    with pytest.raises(SystemExit):
        db.run()


def test_run_invokes_client(monkeypatch) -> None:
    """``run`` initializes and runs ``AxelClient`` with the token."""

    captured: dict[str, object] = {}

    class DummyClient:
        def __init__(self, *, intents: object) -> None:
            captured["intents"] = intents

        def run(self, token: str) -> None:
            captured["token"] = token

    monkeypatch.setattr(db, "AxelClient", DummyClient)
    monkeypatch.setenv(db.TOKEN_ENV_VAR, "123")

    db.run()

    assert captured["token"] == "123"
    intents = captured["intents"]
    assert isinstance(intents, discord.Intents)
    assert intents.message_content is True
