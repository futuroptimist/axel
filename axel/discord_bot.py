"""Minimal Discord bot for ingesting messages mentioned by users."""

from __future__ import annotations

import os
import re
from pathlib import Path

import discord

SAVE_DIR = Path("local/discord")
TOKEN_ENV_VAR = "DISCORD_BOT_TOKEN"
SAFE_COMPONENT_RE = re.compile(r"[^A-Za-z0-9._-]+")


def _get_save_dir() -> Path:
    """Return directory for saving Discord messages.

    Honors ``AXEL_DISCORD_DIR`` and expands ``~`` to the user's home.
    """
    env = os.getenv("AXEL_DISCORD_DIR")
    return Path(env).expanduser() if env else SAVE_DIR


def _sanitize_component(value: str, fallback: str) -> str:
    """Return a filesystem-safe path component."""

    value = str(value).strip()
    sanitized = SAFE_COMPONENT_RE.sub("-", value)
    sanitized = sanitized.strip("-._")
    return sanitized or fallback


def save_message(message: discord.Message) -> Path:
    """Persist the provided message as markdown with metadata.

    Ensures the save directory exists before writing. The directory can be overridden
    via the ``AXEL_DISCORD_DIR`` environment variable. Files are stored under
    ``<save_dir>/<channel>/<message_id>.md``.
    """

    save_dir = _get_save_dir()

    channel = getattr(message, "channel", None)
    channel_name = "channel"
    thread_name: str | None = None
    if channel is not None:
        base_name = getattr(channel, "name", None) or channel_name
        parent = getattr(channel, "parent", None)
        if parent is not None:
            channel_name = getattr(parent, "name", None) or base_name
            thread_name = getattr(channel, "name", None) or None
        else:
            channel_name = base_name

    channel_dir = save_dir / _sanitize_component(channel_name, "channel")
    channel_dir.mkdir(parents=True, exist_ok=True)
    path = channel_dir / f"{message.id}.md"

    timestamp = message.created_at.isoformat()
    jump_url = getattr(message, "jump_url", "")
    content_lines = [
        f"# {message.author.display_name}",
        "",
        f"- timestamp: {timestamp}",
        f"- channel: {channel_name}",
    ]
    if thread_name:
        content_lines.append(f"- thread: {thread_name}")
    if jump_url:
        content_lines.append(f"- link: {jump_url}")
    content_lines.append("")
    content_lines.append(str(message.content or ""))
    content_lines.append("")

    path.write_text("\n".join(content_lines), encoding="utf-8")
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
    token = os.environ.get(TOKEN_ENV_VAR)
    if not token:
        raise SystemExit(f"{TOKEN_ENV_VAR} not set")
    intents = discord.Intents.default()
    intents.message_content = True
    client = AxelClient(intents=intents)
    client.run(token)


if __name__ == "__main__":  # pragma: no cover - manual use
    run()
