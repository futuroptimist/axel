"""Minimal Discord bot for ingesting messages mentioned by users."""

from __future__ import annotations

import os
from pathlib import Path

import discord

SAVE_DIR = Path("local/discord")


def _get_save_dir() -> Path:
    """Return directory for saving Discord messages.

    Honors ``AXEL_DISCORD_DIR`` and expands ``~`` to the user's home.
    """
    env = os.getenv("AXEL_DISCORD_DIR")
    return Path(env).expanduser() if env else SAVE_DIR


def save_message(message: discord.Message) -> Path:
    """Persist the provided message as markdown.

    Ensures the save directory exists before writing. The directory can be overridden
    via the ``AXEL_DISCORD_DIR`` environment variable.
    """
    save_dir = _get_save_dir()
    save_dir.mkdir(parents=True, exist_ok=True)
    path = save_dir / f"{message.id}.md"
    timestamp = message.created_at.isoformat()
    content = f"# {message.author.display_name}\n\n{timestamp}\n\n{message.content}\n"
    path.write_text(content)
    return path


class AxelClient(discord.Client):
    async def on_ready(self) -> None:  # pragma: no cover - network call
        print(f"Logged in as {self.user}")

    async def on_message(self, message: discord.Message) -> None:  # pragma: no cover
        if self.user is None or message.author == self.user:
            return
        if self.user.mentioned_in(message) and message.reference:
            original = await message.channel.fetch_message(message.reference.message_id)
            path = save_message(original)
            await message.channel.send(f"Saved to {path}")


def run() -> None:
    token = os.environ.get("DISCORD_BOT_TOKEN")
    if not token:
        raise SystemExit("DISCORD_BOT_TOKEN not set")
    intents = discord.Intents.default()
    intents.message_content = True
    client = AxelClient(intents=intents)
    client.run(token)


if __name__ == "__main__":  # pragma: no cover - manual use
    run()
