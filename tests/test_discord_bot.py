import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path

import pytest
from cryptography.fernet import Fernet

discord = pytest.importorskip("discord")

sys.path.append(str(Path(__file__).resolve().parents[1]))  # noqa: E402

import axel.discord_bot as db  # noqa: E402

TEST_KEY = Fernet.generate_key().decode()


@pytest.fixture(autouse=True)
def configure_encryption(monkeypatch):
    monkeypatch.setenv("AXEL_DISCORD_KEY", TEST_KEY)
    monkeypatch.delenv("AXEL_DISCORD_KEY_FILE", raising=False)


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
        *,
        created_at: datetime | None = None,
        channel: DummyChannel | None = None,
        jump_url: str | None = None,
        attachments: list[object] | None = None,
    ) -> None:
        self.content = content
        self.id = mid
        self.author = DummyAuthor()
        self.created_at = created_at or datetime(2024, 1, 1, tzinfo=timezone.utc)
        self.channel = channel or DummyChannel("general")
        self.jump_url = jump_url or "https://discord.com/channels/1/2/3"
        self.attachments = attachments or []


def read_capture(path: Path) -> str:
    return db.decrypt_message(path, key=TEST_KEY)


def test_save_message_includes_metadata(tmp_path: Path) -> None:
    db.SAVE_DIR = tmp_path
    msg = DummyMessage("hello", channel=DummyChannel("general"))
    path = db.save_message(msg)
    assert path == tmp_path / "general" / "1.md.enc"
    assert read_capture(path) == (
        "# user\n\n"
        "- Channel: general\n"
        "- Timestamp: 2024-01-01T00:00:00+00:00\n"
        "- Link: https://discord.com/channels/1/2/3\n\n"
        "hello\n"
    )


def test_save_message_encrypts_content(tmp_path: Path) -> None:
    db.SAVE_DIR = tmp_path
    msg = DummyMessage("super secret", channel=DummyChannel("general"))
    path = db.save_message(msg)
    assert b"super secret" not in path.read_bytes()
    assert "super secret" in read_capture(path)


def test_save_message_generates_key_file(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("AXEL_DISCORD_KEY", raising=False)
    monkeypatch.delenv("AXEL_DISCORD_KEY_FILE", raising=False)
    db.SAVE_DIR = tmp_path
    msg = DummyMessage("needs key", channel=DummyChannel("general"), mid=11)
    path = db.save_message(msg)

    key_file = tmp_path / ".axel-discord.key"
    assert key_file.is_file()
    assert key_file.read_text().strip()

    monkeypatch.delenv("AXEL_DISCORD_KEY", raising=False)
    assert "needs key" in db.decrypt_message(path)


def test_save_message_respects_key_file_env(tmp_path: Path, monkeypatch) -> None:
    custom_key = tmp_path / "secret.key"
    monkeypatch.delenv("AXEL_DISCORD_KEY", raising=False)
    monkeypatch.setenv("AXEL_DISCORD_KEY_FILE", str(custom_key))
    db.SAVE_DIR = tmp_path / "captures"
    msg = DummyMessage("custom key", channel=DummyChannel("general"), mid=12)
    path = db.save_message(msg)

    assert custom_key.is_file()
    monkeypatch.delenv("AXEL_DISCORD_KEY", raising=False)
    monkeypatch.setenv("AXEL_DISCORD_KEY_FILE", str(custom_key))
    assert "custom key" in db.decrypt_message(path)


def test_decrypt_message_without_key_raises(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.delenv("AXEL_DISCORD_KEY", raising=False)
    monkeypatch.delenv("AXEL_DISCORD_KEY_FILE", raising=False)
    path = tmp_path / "general" / "13.md.enc"
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_bytes(b"encrypted")

    with pytest.raises(FileNotFoundError):
        db.decrypt_message(path)


def test_save_message_creates_channel_dir(tmp_path: Path) -> None:
    missing = tmp_path / "discord"
    db.SAVE_DIR = missing
    msg = DummyMessage("hi", mid=2, channel=DummyChannel("updates"))
    path = db.save_message(msg)
    assert path == missing / "updates" / "2.md.enc"
    assert read_capture(path).endswith("hi\n")
    assert (missing / "updates").is_dir()


def test_save_message_respects_env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AXEL_DISCORD_DIR", str(tmp_path))
    msg = DummyMessage("hey", mid=3, channel=DummyChannel("announcements"))
    path = db.save_message(msg)
    assert path == tmp_path / "announcements" / "3.md.enc"
    assert "hey" in read_capture(path)


def test_save_message_env_expands_user(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AXEL_DISCORD_DIR", "~/discord")
    msg = DummyMessage("home", mid=4, channel=DummyChannel("general"))
    path = db.save_message(msg)
    assert path == tmp_path / "discord" / "general" / "4.md.enc"
    assert "home" in read_capture(path)


def test_save_message_records_thread_metadata(tmp_path: Path) -> None:
    db.SAVE_DIR = tmp_path
    parent = DummyChannel("general")
    thread = DummyChannel("feature-chat", parent=parent)
    msg = DummyMessage("thread message", mid=5, channel=thread)
    path = db.save_message(msg)
    assert path == tmp_path / "general" / "5.md.enc"
    content = read_capture(path)
    assert "feature-chat" in content
    assert "general" in content


def test_save_message_without_channel(tmp_path: Path) -> None:
    db.SAVE_DIR = tmp_path

    class NoChannelMessage(DummyMessage):
        def __init__(self) -> None:
            super().__init__("dm message", mid=6, channel=None)
            del self.channel

    msg = NoChannelMessage()
    path = db.save_message(msg)
    assert path == tmp_path / "direct-message" / "6.md.enc"
    content = read_capture(path)
    assert "direct-message" in content


def test_capture_message_downloads_attachments(tmp_path: Path) -> None:
    db.SAVE_DIR = tmp_path

    saved: list[Path] = []

    class DummyAttachment:
        def __init__(self, filename: str, data: bytes) -> None:
            self.filename = filename
            self._data = data

        async def save(self, destination: Path) -> None:
            destination = Path(destination)
            destination.write_bytes(self._data)
            saved.append(destination)

    attachments = [
        DummyAttachment("report.pdf", b"pdf-data"),
        DummyAttachment("diagram.png", b"png-data"),
    ]
    msg = DummyMessage("with attachments", mid=7, attachments=attachments)

    path = asyncio.run(db.capture_message(msg))

    assert path == tmp_path / "general" / "7.md.enc"
    attachment_dir = tmp_path / "general" / "7"
    assert attachment_dir.is_dir()
    assert saved == [
        attachment_dir / "report.pdf",
        attachment_dir / "diagram.png",
    ]

    content = read_capture(path)
    assert "## Attachments" in content
    assert "[report.pdf](./7/report.pdf)" in content
    assert "[diagram.png](./7/diagram.png)" in content


def test_capture_message_without_attachments(tmp_path: Path) -> None:
    db.SAVE_DIR = tmp_path
    msg = DummyMessage("just text", mid=8)
    path = asyncio.run(db.capture_message(msg))
    assert path == tmp_path / "general" / "8.md.enc"
    content = read_capture(path)
    assert "just text" in content
    assert "## Attachments" not in content


def test_run_missing_token(monkeypatch) -> None:
    """``run`` exits if ``DISCORD_BOT_TOKEN`` is not set."""
    monkeypatch.delenv("DISCORD_BOT_TOKEN", raising=False)
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
    monkeypatch.setenv("DISCORD_BOT_TOKEN", "123")

    db.run()

    assert captured["token"] == "123"
    intents = captured["intents"]
    assert isinstance(intents, discord.Intents)
    assert intents.message_content is True
