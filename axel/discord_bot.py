"""Minimal Discord bot for ingesting messages mentioned by users."""

from __future__ import annotations

import os
from pathlib import Path

import discord

SAVE_DIR = Path("local/discord")
SAVE_DIR.mkdir(parents=True, exist_ok=True)


def save_message(message: discord.Message) -> Path:
    """Persist the provided message as markdown."""
    path = SAVE_DIR / f"{message.id}.md"
    content = f"# {message.author.display_name}\n\n{message.content}\n"
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
    client = AxelClient(intents=discord.Intents.default())
    client.run(token)


if __name__ == "__main__":  # pragma: no cover - manual use
    run()
