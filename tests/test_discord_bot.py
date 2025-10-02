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


def test_capture_message_without_channel_context(tmp_path: Path) -> None:
    db.SAVE_DIR = tmp_path

    class NoChannelMessage(DummyMessage):
        def __init__(self) -> None:
            super().__init__("dm capture", mid=99, channel=None)
            del self.channel

    msg = NoChannelMessage()
    path = asyncio.run(db.capture_message(msg))

    assert path == tmp_path / "direct-message" / "99.md"
    content = read_markdown(path)
    assert "dm capture" in content
    assert "## Context" not in content


def test_capture_message_includes_thread_history(tmp_path: Path) -> None:
    db.SAVE_DIR = tmp_path

    parent = DummyChannel("general")

    class ThreadChannel(DummyChannel):
        def __init__(self, name: str, parent: DummyChannel) -> None:
            super().__init__(name, parent=parent)
            self._history_messages: list[DummyMessage] = []

        def history(
            self,
            *,
            limit: int | None = None,
            before: DummyMessage | None = None,
        ):
            return DummyAsyncHistory(self._history_messages)

    thread = ThreadChannel("feature-chat", parent=parent)

    context_messages = [
        DummyMessage(
            "initial note",
            mid=101,
            channel=thread,
            created_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        ),
        DummyMessage(
            "follow-up",
            mid=102,
            channel=thread,
            created_at=datetime(2024, 1, 1, 0, 5, tzinfo=timezone.utc),
        ),
    ]

    thread._history_messages = context_messages  # type: ignore[attr-defined]

    target = DummyMessage(
        "decision recorded",
        mid=103,
        channel=thread,
        created_at=datetime(2024, 1, 1, 0, 10, tzinfo=timezone.utc),
    )

    path = asyncio.run(db.capture_message(target))

    assert path == tmp_path / "general" / "103.md"

    content = read_markdown(path)
    assert "## Context" in content
    assert "initial note" in content
    assert "follow-up" in content
    first_index = content.index("initial note")
    second_index = content.index("follow-up")
    assert first_index < second_index


def test_collect_context_handles_history_type_error() -> None:
    class LimitedHistoryChannel(DummyChannel):
        def history(self, *, limit: int | None = None):
            return None

    msg = DummyMessage("history", channel=LimitedHistoryChannel("general"))
    context = asyncio.run(db._collect_context(msg))
    assert context == []


def test_collect_context_returns_empty_on_history_error() -> None:
    class ErrorChannel(DummyChannel):
        def history(
            self,
            *,
            limit: int | None = None,
            before: DummyMessage | None = None,
        ):
            raise RuntimeError("missing permissions")

    msg = DummyMessage("history", channel=ErrorChannel("general"))
    context = asyncio.run(db._collect_context(msg))
    assert context == []


def test_collect_context_returns_empty_on_iteration_error() -> None:
    class BrokenHistory:
        def __aiter__(self):
            return self

        async def __anext__(self):
            raise RuntimeError("iteration failure")

    class BrokenChannel(DummyChannel):
        def history(
            self,
            *,
            limit: int | None = None,
            before: DummyMessage | None = None,
        ):
            return BrokenHistory()

    msg = DummyMessage("history", channel=BrokenChannel("general"))
    context = asyncio.run(db._collect_context(msg))
    assert context == []


def test_collect_context_returns_empty_on_await_error() -> None:
    class AwaitErrorChannel(DummyChannel):
        async def history(
            self,
            *,
            limit: int | None = None,
            before: DummyMessage | None = None,
        ) -> list[DummyMessage]:
            raise RuntimeError("network failure")

    msg = DummyMessage("history", channel=AwaitErrorChannel("general"))
    context = asyncio.run(db._collect_context(msg))
    assert context == []


def test_collect_context_handles_awaitable_and_list_history() -> None:
    parent = DummyChannel("general")

    class AwaitableChannel(DummyChannel):
        async def history(
            self,
            *,
            limit: int | None = None,
            before: DummyMessage | None = None,
        ):
            ctx1 = DummyMessage(
                "older",
                mid=201,
                channel=self,
                created_at=datetime(2024, 1, 1, 0, 1, tzinfo=timezone.utc),
            )
            ctx2 = DummyMessage("unknown", mid=202, channel=self)
            ctx2.created_at = None
            return [before, ctx1, ctx2]

    thread = AwaitableChannel("thread", parent=parent)
    target = DummyMessage(
        "latest",
        mid=200,
        channel=thread,
        created_at=datetime(2024, 1, 1, 0, 2, tzinfo=timezone.utc),
    )

    context = asyncio.run(db._collect_context(target))
    ids = [ctx.id for ctx in context]
    assert ids == [202, 201]


def test_collect_context_skips_falsy_and_self_entries() -> None:
    class FalsyChannel(DummyChannel):
        def history(
            self,
            *,
            limit: int | None = None,
            before: DummyMessage | None = None,
            **_: object,
        ):
            return [None, before]

    target = DummyMessage("target", channel=FalsyChannel("general"))
    context = asyncio.run(db._collect_context(target))

    assert context == []


def test_collect_context_handles_non_iterable_history() -> None:
    class NonIterableChannel(DummyChannel):
        def history(
            self,
            *,
            limit: int | None = None,
            before: DummyMessage | None = None,
            **_: object,
        ):
            return 42

    msg = DummyMessage("history", channel=NonIterableChannel("general"))
    context = asyncio.run(db._collect_context(msg))

    assert context == []


def test_collect_context_returns_empty_on_sync_iteration_error() -> None:
    class BadIterable:
        def __iter__(self):
            return self

        def __next__(self):
            raise RuntimeError("sync failure")

    class SyncErrorChannel(DummyChannel):
        def history(
            self,
            *,
            limit: int | None = None,
            before: DummyMessage | None = None,
            **_: object,
        ):
            return BadIterable()

    msg = DummyMessage("history", channel=SyncErrorChannel("general"))
    context = asyncio.run(db._collect_context(msg))

    assert context == []


def test_collect_context_normalizes_naive_timestamps_when_unbounded() -> None:
    class MixedTimestampChannel(DummyChannel):
        def history(
            self,
            *,
            limit: int | None = None,
            before: DummyMessage | None = None,
            **_: object,
        ):
            older = DummyMessage(
                "older",
                mid=310,
                channel=self,
                created_at=datetime(2024, 1, 1, 0, 3),
            )
            newer = DummyMessage(
                "newer",
                mid=311,
                channel=self,
                created_at=datetime(2024, 1, 1, 0, 4, tzinfo=timezone.utc),
            )
            return [newer, older, before]

    channel = MixedTimestampChannel("general")
    target = DummyMessage(
        "latest",
        mid=312,
        channel=channel,
        created_at=datetime(2024, 1, 1, 0, 5, tzinfo=timezone.utc),
    )

    context = asyncio.run(db._collect_context(target, limit=None))

    assert [ctx.id for ctx in context] == [310, 311]


def test_collect_context_ignores_sort_failures() -> None:
    class ExplodingMessage(DummyMessage):
        @property
        def created_at(self):
            raise RuntimeError("boom")

        @created_at.setter
        def created_at(self, value):
            self._created_at = value

    class ExplodingChannel(DummyChannel):
        def history(
            self,
            *,
            limit: int | None = None,
            before: DummyMessage | None = None,
            **_: object,
        ):
            return [ExplodingMessage("ctx", mid=410, channel=self)]

    target = DummyMessage("latest", mid=411, channel=ExplodingChannel("general"))
    context = asyncio.run(db._collect_context(target))

    assert [ctx.id for ctx in context] == [410]


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
