import asyncio
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


def read_markdown(path: Path) -> str:
    return path.read_text(encoding="utf-8")


def test_save_message_includes_context(tmp_path: Path) -> None:
    """Thread or reply context is recorded alongside the saved message."""

    db.SAVE_DIR = tmp_path
    context = [
        DummyMessage("earlier", mid=10),
        DummyMessage("mention", mid=11),
    ]
    msg = DummyMessage("final", mid=12, channel=DummyChannel("general"))

    path = db.save_message(msg, context=context)

    assert path == tmp_path / "general" / "12.md"
    content = read_markdown(path)
    assert "## Context" in content
    assert "earlier" in content
    assert "mention" in content


def test_save_message_context_skips_self(tmp_path: Path) -> None:
    """Context entries skip the saved message and handle missing author data."""

    db.SAVE_DIR = tmp_path
    msg = DummyMessage("final", mid=13, channel=DummyChannel("updates"))

    class ContextMessage(DummyMessage):
        def __init__(self) -> None:
            super().__init__("", mid=14)
            self.author = object()
            self.created_at = None

    context = [msg, ContextMessage()]

    path = db.save_message(msg, context=context)

    content = read_markdown(path)
    assert "## Context" in content
    assert "unknown" in content
    assert "(no content)" in content
    assert "final" in content


def test_save_message_includes_metadata(tmp_path: Path) -> None:
    db.SAVE_DIR = tmp_path
    msg = DummyMessage("hello", channel=DummyChannel("general"))
    path = db.save_message(msg)
    assert path == tmp_path / "general" / "1.md"
    assert read_markdown(path) == (
        "# user\n\n"
        "- Channel: general\n"
        "- Timestamp: 2024-01-01T00:00:00+00:00\n"
        "- Link: https://discord.com/channels/1/2/3\n\n"
        "hello\n"
    )


def test_save_message_creates_channel_dir(tmp_path: Path) -> None:
    missing = tmp_path / "discord"
    db.SAVE_DIR = missing
    msg = DummyMessage("hi", mid=2, channel=DummyChannel("updates"))
    path = db.save_message(msg)
    assert path == missing / "updates" / "2.md"
    assert read_markdown(path).endswith("hi\n")
    assert (missing / "updates").is_dir()


def test_save_message_respects_env(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("AXEL_DISCORD_DIR", str(tmp_path))
    msg = DummyMessage("hey", mid=3, channel=DummyChannel("announcements"))
    path = db.save_message(msg)
    assert path == tmp_path / "announcements" / "3.md"
    assert "hey" in read_markdown(path)


def test_save_message_env_expands_user(tmp_path: Path, monkeypatch) -> None:
    monkeypatch.setenv("HOME", str(tmp_path))
    monkeypatch.setenv("AXEL_DISCORD_DIR", "~/discord")
    msg = DummyMessage("home", mid=4, channel=DummyChannel("general"))
    path = db.save_message(msg)
    assert path == tmp_path / "discord" / "general" / "4.md"
    assert "home" in read_markdown(path)


def test_save_message_records_thread_metadata(tmp_path: Path) -> None:
    db.SAVE_DIR = tmp_path
    parent = DummyChannel("general")
    thread = DummyChannel("feature-chat", parent=parent)
    msg = DummyMessage("thread message", mid=5, channel=thread)
    path = db.save_message(msg)
    assert path == tmp_path / "general" / "5.md"
    content = read_markdown(path)
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
    assert path == tmp_path / "direct-message" / "6.md"
    content = read_markdown(path)
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

    assert path == tmp_path / "general" / "7.md"
    attachment_dir = tmp_path / "general" / "7"
    assert attachment_dir.is_dir()
    assert saved == [
        attachment_dir / "report.pdf",
        attachment_dir / "diagram.png",
    ]

    content = read_markdown(path)
    assert "## Attachments" in content
    assert "[report.pdf](./7/report.pdf)" in content
    assert "[diagram.png](./7/diagram.png)" in content


class DummyAsyncHistory:
    def __init__(self, messages: list[DummyMessage]) -> None:
        self._messages = list(messages)

    def __aiter__(self) -> "DummyAsyncHistory":
        self._iter = iter(self._messages)
        return self

    async def __anext__(self) -> DummyMessage:
        try:
            return next(self._iter)
        except StopIteration as exc:
            raise StopAsyncIteration from exc


class HistoryChannel(DummyChannel):
    def __init__(self, name: str, history_messages: list[DummyMessage]):
        super().__init__(name)
        self._history_messages = history_messages
        self.history_calls: list[dict[str, object]] = []

    def history(self, *, limit: int | None = None, oldest_first: bool | None = None):
        self.history_calls.append({"limit": limit, "oldest_first": oldest_first})
        return DummyAsyncHistory(self._history_messages)


def test_gather_context_reads_channel_history(tmp_path: Path) -> None:
    db.SAVE_DIR = tmp_path

    history_messages = [
        DummyMessage("context-1", mid=20),
        DummyMessage("context-2", mid=21),
    ]
    channel = HistoryChannel("threads", history_messages)
    trigger = DummyMessage("mention", mid=30, channel=channel)

    result = asyncio.run(db._gather_context(trigger, limit=2))

    assert len(result) == 2
    assert [msg.id for msg in result] == [20, 21]
    assert channel.history_calls == [{"limit": 2, "oldest_first": True}]


def test_gather_context_without_history_returns_empty(tmp_path: Path) -> None:
    db.SAVE_DIR = tmp_path

    class NoHistoryChannel(DummyChannel):
        pass

    trigger = DummyMessage("mention", mid=40, channel=NoHistoryChannel("chat"))

    result = asyncio.run(db._gather_context(trigger))

    assert result == []


def test_gather_context_typeerror_fallback(tmp_path: Path) -> None:
    db.SAVE_DIR = tmp_path

    class TypeErrorChannel(DummyChannel):
        def __init__(self, name: str, history_messages: list[DummyMessage]):
            super().__init__(name)
            self._history_messages = history_messages
            self.calls: list[dict[str, object]] = []

        def history(self, *args, **kwargs):
            self.calls.append(kwargs)
            if "oldest_first" in kwargs:
                raise TypeError("unexpected keyword")
            return DummyAsyncHistory(self._history_messages)

    history_messages = [DummyMessage("context", mid=50)]
    channel = TypeErrorChannel("threads", history_messages)
    trigger = DummyMessage("mention", mid=60, channel=channel)

    result = asyncio.run(db._gather_context(trigger, limit=1))

    assert [msg.id for msg in result] == [50]
    assert channel.calls == [
        {"limit": 1, "oldest_first": True},
        {"limit": 1},
    ]


def test_capture_message_without_attachments(tmp_path: Path) -> None:
    db.SAVE_DIR = tmp_path
    msg = DummyMessage("just text", mid=8)
    path = asyncio.run(db.capture_message(msg))
    assert path == tmp_path / "general" / "8.md"
    content = read_markdown(path)
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
