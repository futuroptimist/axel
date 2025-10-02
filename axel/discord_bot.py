"""Minimal Discord bot for ingesting messages mentioned by users."""

from __future__ import annotations

import inspect
import os
import re
from pathlib import Path
from typing import Sequence

import discord
from cryptography.fernet import Fernet

SAVE_DIR = Path("local/discord")
_KEY_ENV = "AXEL_DISCORD_KEY"
_KEY_FILE_ENV = "AXEL_DISCORD_KEY_FILE"
_DEFAULT_KEY_FILENAME = ".axel-discord.key"


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


def _fernet_from_raw(raw: str | bytes) -> Fernet:
    """Return a Fernet instance constructed from ``raw`` key data."""

    if isinstance(raw, str):
        raw = raw.strip().encode()
    try:
        return Fernet(raw)
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise ValueError(
            "AXEL_DISCORD_KEY must be a valid base64-encoded 32-byte key"
        ) from exc


def _get_key_path(save_dir: Path) -> Path:
    """Return the filesystem path for the Discord encryption key."""

    override = os.getenv(_KEY_FILE_ENV)
    if override:
        return Path(override).expanduser()
    return save_dir / _DEFAULT_KEY_FILENAME


def _load_fernet(save_dir: Path, *, create: bool) -> Fernet:
    """Return a Fernet instance for ``save_dir``.

    When ``create`` is ``True`` and no key exists, a new key is generated and stored
    alongside the captures. When ``False`` and no key exists, ``FileNotFoundError``
    is raised.
    """

    env_key = os.getenv(_KEY_ENV)
    if env_key:
        return _fernet_from_raw(env_key)

    key_path = _get_key_path(save_dir)
    if key_path.exists():
        return _fernet_from_raw(key_path.read_text(encoding="utf-8"))

    if not create:
        raise FileNotFoundError(key_path)

    key_path.parent.mkdir(parents=True, exist_ok=True)
    key = Fernet.generate_key()
    key_path.write_text(key.decode("utf-8"), encoding="utf-8")
    return _fernet_from_raw(key)


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


def save_message(
    message: discord.Message,
    *,
    attachments: Sequence[tuple[str, Path]] | None = None,
) -> Path:
    """Persist the provided message as encrypted markdown with metadata.

    Ensures the save directory exists before writing. The directory can be overridden
    via the ``AXEL_DISCORD_DIR`` environment variable. Messages are grouped by channel
    name to match the documented layout
    ``local/discord/<channel>/<message_id>.md.enc`` and include channel/thread metadata,
    timestamps, the source link, and optional attachment references when provided.
    Content is encrypted using a Fernet key sourced from ``AXEL_DISCORD_KEY`` or
    ``AXEL_DISCORD_KEY_FILE`` (defaulting to a generated key stored alongside the
    captures).
    """
    save_dir = _get_save_dir()
    fernet = _load_fernet(save_dir, create=True)
    channel_name, thread_name = _channel_metadata(message)
    channel_dir = save_dir / _sanitize_component(channel_name)
    channel_dir.mkdir(parents=True, exist_ok=True)

    path = channel_dir / f"{message.id}.md.enc"
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
    lines.append(message.content)
    lines.append("")
    if attachments:
        lines.append("## Attachments")
        for display_name, relative_path in attachments:
            rel = relative_path.as_posix()
            if not rel.startswith("./") and not rel.startswith("../"):
                rel = f"./{rel}"
            lines.append(f"- [{display_name}]({rel})")
        lines.append("")

    content = "\n".join(lines)
    encrypted = fernet.encrypt(content.encode("utf-8"))
    path.write_bytes(encrypted)
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


async def capture_message(message: discord.Message) -> Path:
    """Download attachments (if any) and persist ``message`` to disk."""

    save_dir = _get_save_dir()
    channel_name, _ = _channel_metadata(message)
    channel_dir = save_dir / _sanitize_component(channel_name)
    channel_dir.mkdir(parents=True, exist_ok=True)
    attachments = await _download_attachments(message, channel_dir)
    return save_message(message, attachments=attachments)


def decrypt_message(path: Path, *, key: str | bytes | None = None) -> str:
    """Return decrypted markdown content for the saved Discord capture.

    ``key`` may be provided explicitly; otherwise it is resolved from the same
    environment variables and key file locations as :func:`save_message`.
    """

    save_dir = path.parent.parent
    fernet = (
        _fernet_from_raw(key)
        if key is not None
        else _load_fernet(save_dir, create=False)
    )
    decrypted = fernet.decrypt(path.read_bytes())
    return decrypted.decode("utf-8")


class AxelClient(discord.Client):
    async def on_ready(self) -> None:  # pragma: no cover - network call
        print(f"Logged in as {self.user}")

    async def on_message(self, message: discord.Message) -> None:  # pragma: no cover
        if self.user is None or message.author == self.user:
            return
        if self.user.mentioned_in(message) and message.reference:
            original = await message.channel.fetch_message(message.reference.message_id)
            path = await capture_message(original)
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
