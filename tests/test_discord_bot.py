import sys
from pathlib import Path

import discord
import pytest

sys.path.append(str(Path(__file__).resolve().parents[1]))  # noqa: E402

import axel.discord_bot as db  # noqa: E402


class DummyAuthor:
    display_name = "user"


class DummyMessage:
    def __init__(self, content: str, mid: int = 1) -> None:
        self.content = content
        self.id = mid
        self.author = DummyAuthor()


def test_save_message(tmp_path: Path) -> None:
    db.SAVE_DIR = tmp_path
    msg = DummyMessage("hello")
    path = db.save_message(msg)
    assert path.read_text() == "# user\n\nhello\n"


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
    assert captured["intents"] == discord.Intents.default()
