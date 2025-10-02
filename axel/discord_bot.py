"""Minimal Discord bot for ingesting messages mentioned by users."""

from __future__ import annotations

import inspect
import os
import re
from datetime import datetime
from pathlib import Path
from typing import Sequence

import discord

SAVE_DIR = Path("local/discord")
CONTEXT_LIMIT = 5


def _get_save_dir() -> Path:
    """Return directory for saving Discord messages."""

    env = os.getenv("AXEL_DISCORD_DIR")
    return Path(env).expanduser() if env else SAVE_DIR


_SAFE_COMPONENT = re.compile(r"[^A-Za-z0-9._-]+")


def _sanitize_component(name: str | None) -> str:
    """Return a filesystem-friendly version of ``name``."""

    cleaned = (name or "unknown").strip()
    sanitized = _SAFE_COMPONENT.sub("_", cleaned)
    return sanitized or "unknown"


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


def _display_name(author: object) -> str:
    """Return a display-friendly name for ``author``."""

    for attr in ("display_name", "global_name", "name"):
        value = getattr(author, attr, None)
        if value:
            return str(value)
    return "unknown"


def save_message(
    message: discord.Message,
    *,
    attachments: Sequence[tuple[str, Path]] | None = None,
    context: Sequence[discord.Message] | None = None,
) -> Path:
    """Persist the provided message as markdown with metadata.

    Ensures the save directory exists before writing. The directory can be overridden
    via the ``AXEL_DISCORD_DIR`` environment variable. Messages are grouped by channel
    name to match the documented layout ``local/discord/<channel>/<message_id>.md`` and
    include channel/thread metadata, timestamps, the source link, optional
    attachment references, and recent thread or reply context when supplied.
    """
    save_dir = _get_save_dir()
    channel_name, thread_name = _channel_metadata(message)
    channel_dir = save_dir / _sanitize_component(channel_name)
    channel_dir.mkdir(parents=True, exist_ok=True)

    path = channel_dir / f"{message.id}.md"
    timestamp = message.created_at.isoformat()
    author = message.author.display_name
    jump_url = getattr(message, "jump_url", "")

    lines = [f"# {author}", ""]
    lines.append(f"- Channel: {channel_name or 'unknown'}")
    if thread_name:
        lines.append(f"- Thread: {thread_name}")
    lines.append(f"- Timestamp: {timestamp}")
    if jump_url:
        lines.append(f"- Link: {jump_url}")
    lines.append("")

    context_lines: list[str] = []
    if context:
        for ctx in context:
            if getattr(ctx, "id", None) == message.id:
                continue
            author = _display_name(getattr(ctx, "author", None))
            timestamp = getattr(ctx, "created_at", None)
            ts_str = timestamp.isoformat() if hasattr(timestamp, "isoformat") else ""
            body = getattr(ctx, "content", "") or "(no content)"
            entry = f"- {author}: {body}"
            if ts_str:
                entry += f" ({ts_str})"
            context_lines.append(entry)
    if context_lines:
        lines.append("## Context")
        lines.extend(context_lines)
        lines.append("")

    lines.append(message.content)
    lines.append("")

    if context:
        lines.append("## Context")
        for ctx in context:
            author = getattr(getattr(ctx, "author", None), "display_name", "unknown")
            timestamp = getattr(ctx, "created_at", None)
            ts = timestamp.isoformat() if isinstance(timestamp, datetime) else ""
            jump_url = getattr(ctx, "jump_url", "")
            entry = f"- {author}"
            if ts:
                entry += f" @ {ts}"
            if jump_url:
                entry += f" ({jump_url})"
            lines.append(entry)
            content = getattr(ctx, "content", "")
            if content:
                lines.append(f"  {content}")
        lines.append("")
    if attachments:
        lines.append("## Attachments")
        for display_name, relative_path in attachments:
            rel = relative_path.as_posix()
            if not rel.startswith("./") and not rel.startswith("../"):
                rel = f"./{rel}"
            lines.append(f"- [{display_name}]({rel})")
        lines.append("")

    path.write_text("\n".join(lines), encoding="utf-8")
    return path


async def _download_attachments(
    message: discord.Message, channel_dir: Path
) -> list[tuple[str, Path]]:
    """Download attachments for ``message`` into ``channel_dir``.

    Returns a list of ``(display_name, relative_path)`` tuples suitable for
    ``save_message``.
    """

    attachments = list(getattr(message, "attachments", []) or [])
    if not attachments:
        return []

    attachment_dir = channel_dir / str(message.id)
    attachment_dir.mkdir(parents=True, exist_ok=True)
    saved: list[tuple[str, Path]] = []
    for index, attachment in enumerate(attachments, start=1):
        filename = getattr(attachment, "filename", f"attachment-{index}")
        sanitized = _sanitize_component(Path(filename).name)
        destination = attachment_dir / sanitized
        result = attachment.save(destination)
        if inspect.isawaitable(result):
            await result
        saved.append((filename, Path(str(message.id)) / sanitized))
    return saved


async def capture_message(
    message: discord.Message,
    *,
    context: Sequence[discord.Message] | None = None,
) -> Path:
    """Download attachments (if any) and persist ``message`` to disk."""

    save_dir = _get_save_dir()
    channel_name, _ = _channel_metadata(message)
    channel_dir = save_dir / _sanitize_component(channel_name)
    channel_dir.mkdir(parents=True, exist_ok=True)
    attachments = await _download_attachments(message, channel_dir)
    return save_message(message, attachments=attachments, context=context)


async def _gather_context(
    trigger_message: discord.Message, *, limit: int = CONTEXT_LIMIT
) -> list[discord.Message]:
    """Return recent history for the channel or thread of ``trigger_message``."""

    channel = getattr(trigger_message, "channel", None)
    if channel is None or not hasattr(channel, "history"):
        return []
    try:
        history = channel.history(limit=limit, oldest_first=True)
    except TypeError:
        history = channel.history(limit=limit)
    messages: list[discord.Message] = []
    async for item in history:
        messages.append(item)
    return messages


class AxelClient(discord.Client):
    async def on_ready(self) -> None:  # pragma: no cover - network call
        print(f"Logged in as {self.user}")

    async def on_message(self, message: discord.Message) -> None:  # pragma: no cover
        if self.user is None or message.author == self.user:
            return
        if self.user.mentioned_in(message) and message.reference:
            original = await message.channel.fetch_message(message.reference.message_id)
            context = await _gather_context(message)
            context = [
                ctx
                for ctx in context
                if getattr(ctx, "id", None) != getattr(original, "id", None)
            ]
            path = await capture_message(original, context=context)
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
