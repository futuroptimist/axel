"""Minimal Discord bot for ingesting messages mentioned by users."""

from __future__ import annotations

import os
import re
from pathlib import Path

import discord

SAVE_DIR = Path("local/discord")


def _get_save_dir() -> Path:
    """Return directory for saving Discord messages."""

    env = os.getenv("AXEL_DISCORD_DIR")
    return Path(env).expanduser() if env else SAVE_DIR


def _sanitize_component(name: str) -> str:
    """Return a filesystem-friendly version of ``name``."""

    sanitized = re.sub(r"[^\w.-]+", "-", name.strip())
    sanitized = sanitized.strip("-")
    return sanitized or "channel"


def _channel_metadata(message: discord.Message) -> tuple[str, str | None]:
    """Return channel and optional thread names for ``message``."""

    channel = getattr(message, "channel", None)
    if channel is None:
        return ("direct-message", None)

    parent = getattr(channel, "parent", None)
    channel_name = getattr(channel, "name", "direct-message")
    if parent and getattr(parent, "name", None):
        return (str(parent.name), str(channel_name))
    return (str(channel_name), None)


def save_message(message: discord.Message) -> Path:
    """Persist the provided message as markdown with metadata."""

    save_dir = _get_save_dir()
    channel_name, thread_name = _channel_metadata(message)
    channel_dir = save_dir / _sanitize_component(channel_name)
    channel_dir.mkdir(parents=True, exist_ok=True)

    path = channel_dir / f"{message.id}.md"
    timestamp = message.created_at.isoformat()
    jump_url = getattr(message, "jump_url", "")

    lines = [f"# {message.author.display_name}", ""]
    lines.append(f"- **Timestamp:** {timestamp}")
    lines.append(f"- **Channel:** {channel_name}")
    if thread_name:
        lines.append(f"- **Thread:** {thread_name}")
    if jump_url:
        lines.append(f"- **Link:** {jump_url}")
    lines.append("")
    lines.append(message.content)
    lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
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
