import asyncio
import sys
from datetime import datetime, timezone
from pathlib import Path
from types import SimpleNamespace

import pytest
from cryptography.fernet import Fernet

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


def test_read_capture_returns_none_when_plaintext_unavailable(tmp_path: Path) -> None:
    missing_path = tmp_path / "missing.md"

    assert db._read_capture(missing_path, None) is None


def test_read_capture_returns_none_when_plaintext_decode_fails(tmp_path: Path) -> None:
    broken_path = tmp_path / "broken.md"
    broken_path.write_bytes(b"\xff\xfe")

    assert db._read_capture(broken_path, None) is None


def test_read_capture_returns_none_when_encrypted_file_missing(tmp_path: Path) -> None:
    class DummyEncrypter:
        def decrypt(self, data: bytes) -> bytes:  # pragma: no cover - defensive
            raise AssertionError("decrypt should not be called")

    missing_path = tmp_path / "missing.md"

    assert db._read_capture(missing_path, DummyEncrypter()) is None


def test_read_capture_returns_none_when_decryption_fails(tmp_path: Path) -> None:
    encrypted_path = tmp_path / "encrypted.md"
    encrypted_path.write_bytes(b"payload")

    class DummyEncrypter:
        def decrypt(self, data: bytes) -> bytes:
            raise ValueError("cannot decrypt")

    assert db._read_capture(encrypted_path, DummyEncrypter()) is None


def test_read_capture_decodes_with_ignore_when_utf8_invalid(tmp_path: Path) -> None:
    encrypted_path = tmp_path / "encrypted.md"
    encrypted_path.write_bytes(b"payload")

    class DummyEncrypter:
        def decrypt(self, data: bytes) -> bytes:
            return b"\xff\xfe"

    assert db._read_capture(encrypted_path, DummyEncrypter()) == ""


def test_summarize_capture_extracts_message_body(tmp_path: Path) -> None:
    capture = tmp_path / "general" / "1.md"
    capture.parent.mkdir(parents=True)
    capture.write_text(
        "\n".join(
            [
                "# user",
                "",
                "- Channel: general",
                "- Timestamp: 2024-01-01T00:00:00+00:00",
                "",
                "## Context",
                "- helper @ 2024-01-01T00:00:00+00:00",
                "  helper message",
                "",
                "Key insight from the captured message.",
                "Follow-up action items listed here.",
                "",
                "## Attachments",
                "- [report.pdf](./1/report.pdf)",
            ]
        ),
        encoding="utf-8",
    )

    summary = db.summarize_capture(capture)

    assert summary is not None
    assert "Key insight" in summary
    assert "helper" not in summary  # context lines are skipped
    assert "Channel" not in summary  # metadata lines are skipped


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


def test_save_message_writes_single_context_section(tmp_path: Path) -> None:
    """Context history is emitted once with metadata for each message."""

    db.SAVE_DIR = tmp_path
    context = [
        DummyMessage(
            "earlier",
            mid=20,
            created_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
        ),
        DummyMessage(
            "mention",
            mid=21,
            created_at=datetime(2024, 1, 1, 0, 5, tzinfo=timezone.utc),
        ),
    ]
    msg = DummyMessage("final", mid=22, channel=DummyChannel("general"))

    path = db.save_message(msg, context=context)

    content = read_markdown(path)
    assert content.count("## Context") == 1
    assert "earlier" in content
    assert "mention" in content
    context_section = content.split("## Context", 1)[1]
    assert context_section.count("- user @") == 2


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


def test_save_message_orders_context_oldest_first(tmp_path: Path) -> None:
    """Context entries render in chronological order even when unsorted."""

    db.SAVE_DIR = tmp_path
    earlier = DummyMessage(
        "earlier",
        mid=30,
        created_at=datetime(2024, 1, 1, 0, 0, tzinfo=timezone.utc),
    )
    later = DummyMessage(
        "later",
        mid=31,
        created_at=datetime(2024, 1, 1, 0, 5, tzinfo=timezone.utc),
    )
    msg = DummyMessage("final", mid=32, channel=DummyChannel("general"))

    path = db.save_message(msg, context=[later, earlier])

    content = read_markdown(path)
    context_section = content.split("## Context", 1)[1]
    assert context_section.index("earlier") < context_section.index("later")


def test_save_message_limits_context_entries(tmp_path: Path) -> None:
    """No more than ``CONTEXT_LIMIT`` prior messages are recorded."""

    db.SAVE_DIR = tmp_path
    context = [
        DummyMessage(
            f"context-{index}",
            mid=100 + index,
            created_at=datetime(2024, 1, 1, 0, index, tzinfo=timezone.utc),
        )
        for index in range(db.CONTEXT_LIMIT + 3)
    ]
    msg = DummyMessage("final", mid=200, channel=DummyChannel("general"))

    path = db.save_message(msg, context=context)

    content = read_markdown(path)
    # Only the most recent ``CONTEXT_LIMIT`` entries appear, still oldest-first.
    assert content.count("- user @") == db.CONTEXT_LIMIT
    assert "context-0" not in content
    assert f"context-{db.CONTEXT_LIMIT}" in content


def test_save_message_ignores_context_sort_errors(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    """Failures while sorting context should not prevent rendering."""

    db.SAVE_DIR = tmp_path
    first = DummyMessage("first", mid=40)
    second = DummyMessage("second", mid=41)
    msg = DummyMessage("final", mid=42, channel=DummyChannel("general"))

    def boom(_: object) -> datetime:
        raise RuntimeError("boom")

    monkeypatch.setattr(db, "_context_sort_key", boom)

    path = db.save_message(msg, context=[first, second])

    content = read_markdown(path)
    context_section = content.split("## Context", 1)[1]
    assert "first" in context_section and "second" in context_section


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


def test_save_message_includes_repository_metadata(tmp_path: Path, monkeypatch) -> None:
    """Channel names map captures to repos listed in ``AXEL_REPO_FILE``."""

    repo_file = tmp_path / "repos.txt"
    repo_file.write_text(
        "https://github.com/example/project.one\n" "https://github.com/example/other\n",
        encoding="utf-8",
    )
    monkeypatch.setenv("AXEL_REPO_FILE", str(repo_file))

    db.SAVE_DIR = tmp_path
    msg = DummyMessage("repo insight", channel=DummyChannel("project-one"))

    path = db.save_message(msg)

    assert path == tmp_path / "project-one" / "1.md"
    content = read_markdown(path)
    assert "- Channel: project-one" in content
    assert "- Repository: https://github.com/example/project.one" in content


def test_save_message_with_blank_channel_skips_repository_lookup(
    tmp_path: Path, monkeypatch
) -> None:
    """Empty channel names do not attempt repository matching."""

    repo_file = tmp_path / "repos.txt"
    repo_file.write_text("https://github.com/example/project\n", encoding="utf-8")
    monkeypatch.setenv("AXEL_REPO_FILE", str(repo_file))

    db.SAVE_DIR = tmp_path

    class BlankChannel(DummyChannel):
        def __init__(self) -> None:
            super().__init__("")

    msg = DummyMessage("blank", channel=BlankChannel())

    path = db.save_message(msg)

    content = read_markdown(path)
    assert "- Channel: unknown" in content
    assert "Repository:" not in content


def test_save_message_skips_empty_repo_entries(tmp_path: Path, monkeypatch) -> None:
    """Repository matching ignores empty entries from ``load_repos``."""

    import axel.repo_manager as repo_manager

    monkeypatch.setattr(
        repo_manager,
        "load_repos",
        lambda path=None: ["", "https://github.com/example/project"],
    )

    db.SAVE_DIR = tmp_path
    msg = DummyMessage("note", channel=DummyChannel("project"))

    path = db.save_message(msg)

    content = read_markdown(path)
    assert "- Repository: https://github.com/example/project" in content


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


def test_save_message_encrypts_when_key_set(tmp_path: Path, monkeypatch) -> None:
    """When an encryption key is configured the saved file is encrypted."""

    key = Fernet.generate_key()
    db.SAVE_DIR = Path("local/discord")
    monkeypatch.setenv("AXEL_DISCORD_DIR", str(tmp_path))
    monkeypatch.setenv("AXEL_DISCORD_ENCRYPTION_KEY", key.decode())
    msg = DummyMessage("secret payload", mid=99, channel=DummyChannel("general"))

    path = db.save_message(msg)

    assert path == tmp_path / "general" / "99.md"
    raw = path.read_bytes()
    assert b"secret payload" not in raw
    decrypted = Fernet(key).decrypt(raw).decode()
    assert "secret payload" in decrypted


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


def test_search_captures_returns_empty_when_limit_non_positive(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AXEL_DISCORD_DIR", str(tmp_path))

    assert db.search_captures("anything", limit=0) == []
    assert db.search_captures("anything", limit=-1) == []


def test_search_captures_returns_empty_when_directory_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    missing = tmp_path / "missing"
    monkeypatch.setenv("AXEL_DISCORD_DIR", str(missing))

    assert db.search_captures("anything") == []


def test_search_captures_truncates_long_snippets(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AXEL_DISCORD_DIR", str(tmp_path))
    capture_dir = tmp_path / "channel"
    capture_dir.mkdir()
    capture_path = capture_dir / "note.md"
    capture_path.write_text("A" * 130)

    results = db.search_captures("A")

    assert results
    assert len(results[0].snippet) == 120
    assert results[0].snippet.endswith("...")


def test_search_captures_returns_matches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AXEL_DISCORD_DIR", str(tmp_path))
    msg = DummyMessage("search target content", mid=10, channel=DummyChannel("general"))
    db.save_message(msg)

    results = db.search_captures("target")

    assert results
    first = results[0]
    assert first.path == tmp_path / "general" / "10.md"
    assert "target" in first.snippet


def test_search_captures_decrypts_encrypted_files(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    key = Fernet.generate_key()
    monkeypatch.setenv("AXEL_DISCORD_DIR", str(tmp_path))
    monkeypatch.setenv("AXEL_DISCORD_ENCRYPTION_KEY", key.decode())

    msg = DummyMessage("encrypted search note", mid=11, channel=DummyChannel("secure"))
    db.save_message(msg)

    results = db.search_captures("search")

    assert results
    assert results[0].path == tmp_path / "secure" / "11.md"


def test_search_captures_skips_encrypted_when_key_missing(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AXEL_DISCORD_DIR", str(tmp_path))

    secure_dir = tmp_path / "secure"
    secure_dir.mkdir()
    encrypted_path = secure_dir / "20.md"
    encrypted_path.write_bytes(b"\xff\xfe\xfd\x00")

    results = db.search_captures("secret")

    assert results == []


def test_search_captures_respects_limit(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AXEL_DISCORD_DIR", str(tmp_path))
    for mid in range(12, 16):
        db.save_message(
            DummyMessage(
                f"repeated match {mid}",
                mid=mid,
                channel=DummyChannel("general"),
            )
        )

    results = db.search_captures("match", limit=2)

    assert len(results) == 2


def test_search_command_sends_no_results_message(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    intents = discord.Intents.none()
    client = db.AxelClient(intents=intents)
    command = client.tree.get_command("axel").get_command("search")

    class DummyResponse:
        def __init__(self) -> None:
            self.calls: list[tuple[str, bool]] = []

        async def send_message(self, content: str, *, ephemeral: bool) -> None:
            self.calls.append((content, ephemeral))

    interaction = SimpleNamespace(response=DummyResponse())
    monkeypatch.setattr(db, "search_captures", lambda query: [])

    asyncio.run(command.callback(interaction, "query"))

    assert interaction.response.calls == [("No captures found for 'query'.", True)]


def test_search_command_handles_non_relative_paths(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    intents = discord.Intents.none()
    client = db.AxelClient(intents=intents)
    command = client.tree.get_command("axel").get_command("search")

    result_path = tmp_path / "outside" / "note.md"
    result_path.parent.mkdir(parents=True)
    result_path.write_text("match line")

    monkeypatch.setattr(
        db,
        "search_captures",
        lambda query: [db.SearchResult(result_path, "match line")],
    )
    monkeypatch.setattr(db, "_get_save_dir", lambda: tmp_path / "root")

    class DummyResponse:
        def __init__(self) -> None:
            self.calls: list[tuple[str, bool]] = []

        async def send_message(self, content: str, *, ephemeral: bool) -> None:
            self.calls.append((content, ephemeral))

    interaction = SimpleNamespace(response=DummyResponse())

    asyncio.run(command.callback(interaction, "query"))

    assert interaction.response.calls
    message, ephemeral = interaction.response.calls[0]
    assert ephemeral is True
    assert "outside/note.md" in message
    assert "match line" in message


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


def test_axel_client_captures_thread_mentions(monkeypatch, tmp_path: Path) -> None:
    """Mentions inside thread openers are saved even without message references."""

    captured: dict[str, object] = {}

    async def fake_capture(message, *, context=None):
        captured["message"] = message
        captured["context"] = list(context or [])
        return tmp_path / "general" / "1.md"

    async def fake_gather(trigger):
        captured["gathered"] = trigger
        return [DummyMessage("history", mid=2)]

    async def fake_send(content: str) -> None:
        captured["reply"] = content

    thread_parent = DummyChannel("general")
    thread = DummyChannel("thread", parent=thread_parent)
    thread.send = fake_send  # type: ignore[attr-defined]

    message = DummyMessage("thread opener", mid=1, channel=thread)
    message.reference = None  # type: ignore[attr-defined]

    monkeypatch.setattr(db, "capture_message", fake_capture)
    monkeypatch.setattr(db, "_gather_context", fake_gather)

    intents = discord.Intents.none()
    client = db.AxelClient(intents=intents)

    class DummyUser:
        def mentioned_in(self, _: object) -> bool:
            return True

    client._connection.user = DummyUser()  # type: ignore[attr-defined]

    asyncio.run(client.on_message(message))

    assert captured["message"] is message
    assert captured["context"] and captured["context"][0].content == "history"
    assert captured["reply"] == f"Saved to {tmp_path / 'general' / '1.md'}"


def test_axel_client_excludes_trigger_from_context(
    monkeypatch: pytest.MonkeyPatch, tmp_path: Path
) -> None:
    """Context passed to ``capture_message`` omits the trigger mention itself."""

    captured: dict[str, object] = {}

    parent = DummyMessage("parent message", mid=5)
    channel = DummyChannel("general")
    message = DummyMessage("bot please log", mid=6, channel=channel)
    message.reference = SimpleNamespace(  # type: ignore[attr-defined]
        message_id=parent.id,
    )

    async def fake_capture(original, *, context=None):
        captured["original"] = original
        captured["context"] = list(context or [])
        return tmp_path / "general" / "5.md"

    async def fake_gather(trigger):
        captured["trigger"] = trigger
        return [
            parent,
            trigger,
            DummyMessage("earlier note", mid=7),
        ]

    async def fake_fetch_message(message_id: int):
        captured["fetched"] = message_id
        return parent

    async def fake_send(content: str) -> None:
        captured["reply"] = content

    channel.fetch_message = fake_fetch_message  # type: ignore[attr-defined]
    channel.send = fake_send  # type: ignore[attr-defined]

    monkeypatch.setattr(db, "capture_message", fake_capture)
    monkeypatch.setattr(db, "_gather_context", fake_gather)

    intents = discord.Intents.none()
    client = db.AxelClient(intents=intents)

    class DummyUser:
        def mentioned_in(self, _: object) -> bool:
            return True

    client._connection.user = DummyUser()  # type: ignore[attr-defined]

    asyncio.run(client.on_message(message))

    assert captured["original"] is parent
    context_ids = [msg.id for msg in captured["context"]]
    assert context_ids == [7]
    assert captured["reply"] == f"Saved to {tmp_path / 'general' / '5.md'}"


class DummyInteractionResponse:
    def __init__(self) -> None:
        self.content: str | None = None
        self.ephemeral: bool | None = None

    async def send_message(self, content: str, *, ephemeral: bool = False) -> None:
        self.content = content
        self.ephemeral = ephemeral


class DummyInteraction:
    def __init__(self) -> None:
        self.response = DummyInteractionResponse()


def test_axel_search_command_replies_with_matches(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AXEL_DISCORD_DIR", str(tmp_path))
    msg = DummyMessage("searchable content", mid=20, channel=DummyChannel("updates"))
    db.save_message(msg)

    intents = discord.Intents.none()
    client = db.AxelClient(intents=intents)

    axel_command = client.tree.get_command("axel")
    assert axel_command is not None
    search_command = next(
        cmd for cmd in getattr(axel_command, "commands", []) if cmd.name == "search"
    )

    interaction = DummyInteraction()
    asyncio.run(search_command.callback(interaction, query="searchable"))

    assert interaction.response.ephemeral is True
    assert interaction.response.content is not None
    assert "updates/20.md" in interaction.response.content


def test_axel_summarize_command_replies_with_summary(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("AXEL_DISCORD_DIR", str(tmp_path))
    msg = DummyMessage(
        "Summary focus with actionable outcomes.",
        mid=21,
        channel=DummyChannel("updates"),
    )
    db.save_message(msg)

    intents = discord.Intents.none()
    client = db.AxelClient(intents=intents)

    axel_command = client.tree.get_command("axel")
    assert axel_command is not None
    summarize_command = next(
        cmd for cmd in getattr(axel_command, "commands", []) if cmd.name == "summarize"
    )

    interaction = DummyInteraction()
    asyncio.run(summarize_command.callback(interaction, query="summary"))

    assert interaction.response.ephemeral is True
    assert interaction.response.content is not None
    assert "updates/21.md" in interaction.response.content
    assert "Summary for 'summary'" in interaction.response.content
    assert "actionable outcomes" in interaction.response.content


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


def test_collect_context_handles_sort_errors(
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    """Errors during context sorting should not break collection."""

    class SortyChannel(DummyChannel):
        def history(
            self,
            *,
            limit: int | None = None,
            before: DummyMessage | None = None,
            **_: object,
        ):
            return [
                DummyMessage("ctx-1", mid=420, channel=self),
                DummyMessage("ctx-2", mid=421, channel=self),
            ]

    target = DummyMessage("latest", mid=422, channel=SortyChannel("general"))

    def boom(_: object) -> datetime:
        raise RuntimeError("boom")

    monkeypatch.setattr(db, "_context_sort_key", boom)

    context = asyncio.run(db._collect_context(target))

    assert [ctx.id for ctx in context] == [420, 421]


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
