"""Minimal Discord bot for ingesting messages mentioned by users."""

from __future__ import annotations

import inspect
import os
import re
from dataclasses import dataclass
from datetime import datetime, timezone
from pathlib import Path
from typing import Sequence

import discord
from cryptography.fernet import Fernet, InvalidToken
from discord import app_commands

from .quests import suggest_cross_repo_quests

SAVE_DIR = Path("local/discord")
CONTEXT_LIMIT = 5
_MIN_CONTEXT_TIMESTAMP = datetime.min.replace(tzinfo=timezone.utc)
SUMMARY_LINE_LIMIT = 2
SUMMARY_MAX_CHARS = 280
_METADATA_PREFIXES: tuple[str, ...] = (
    "- Channel:",
    "- Thread:",
    "- Repository:",
    "- Security:",
    "- Timestamp:",
    "- Link:",
)
_ATTACHMENT_LINE = re.compile(r"\s*-\s*\[[^\]]+\]\(((?:\./|\.\./).+?)\)")
_REPOSITORY_PREFIX = "- repository:"

_CHECKED_CAPTURE_DIRS: set[Path] = set()


@dataclass(frozen=True)
class SearchResult:
    """Lightweight record describing a capture search hit."""

    path: Path
    snippet: str


@dataclass(frozen=True)
class DigestEntry:
    """Summarized view of a capture used in digests."""

    path: Path
    summary: str


def _context_sort_key(message: discord.Message) -> datetime:
    """Return a datetime sort key for ``message`` timestamps."""

    try:
        timestamp = getattr(message, "created_at", None)
    except Exception:
        return _MIN_CONTEXT_TIMESTAMP
    if isinstance(timestamp, datetime):
        if timestamp.tzinfo is None:
            return timestamp.replace(tzinfo=timezone.utc)
        return timestamp
    return _MIN_CONTEXT_TIMESTAMP


def _validate_capture_dir(path: Path, *, require_writable: bool = True) -> Path:
    """Return ``path`` after resolving it and optionally verifying writability."""

    resolved = path.expanduser()
    try:
        resolved = resolved.resolve(strict=False)
    except Exception:
        resolved = resolved.absolute()

    if not require_writable:
        return resolved

    if resolved in _CHECKED_CAPTURE_DIRS:
        return resolved

    try:
        resolved.mkdir(parents=True, exist_ok=True)
    except OSError as exc:
        raise RuntimeError(
            f"Unable to create Discord capture directory at {resolved}"
        ) from exc

    probe = resolved / ".axel-write-test"
    try:
        with probe.open("wb") as handle:
            handle.write(b"")
    except OSError as exc:
        raise RuntimeError(
            f"Discord capture directory {resolved} is not writable"
        ) from exc
    finally:
        try:
            probe.unlink(missing_ok=True)
        except OSError:
            pass

    _CHECKED_CAPTURE_DIRS.add(resolved)
    return resolved


def _get_save_dir(*, require_writable: bool = True) -> Path:
    """Return directory for saving or reading Discord messages."""

    env = os.getenv("AXEL_DISCORD_DIR")
    if env:
        candidate = Path(env)
        if require_writable:
            try:
                return _validate_capture_dir(candidate, require_writable=True)
            except RuntimeError as exc:
                raise RuntimeError(
                    f"AXEL_DISCORD_DIR points to an unwritable directory: {candidate}"
                ) from exc
        return _validate_capture_dir(candidate, require_writable=False)

    if require_writable:
        try:
            return _validate_capture_dir(SAVE_DIR, require_writable=True)
        except RuntimeError:
            fallback = Path.home() / ".axel" / "discord"
            try:
                return _validate_capture_dir(fallback, require_writable=True)
            except RuntimeError as exc:
                raise RuntimeError(
                    "Unable to locate a writable Discord capture directory. "
                    "Set AXEL_DISCORD_DIR to a writable path."
                ) from exc

    return _validate_capture_dir(SAVE_DIR, require_writable=False)


def _format_relative_path(path: Path, root: Path) -> str:
    """Return a POSIX-style path relative to ``root`` without leaking absolutes."""

    try:
        relative = path.relative_to(root)
    except ValueError:
        try:
            rel = os.path.relpath(path, root)
        except ValueError:
            return Path(path).name
        return Path(rel).as_posix()
    return relative.as_posix()


_SAFE_COMPONENT = re.compile(r"[^A-Za-z0-9._-]+")
_NORMALIZE_REPO_NAME = re.compile(r"[^a-z0-9]+")


def _sanitize_component(name: str | None) -> str:
    """Return a filesystem-friendly version of ``name``."""

    cleaned = (name or "unknown").strip()
    sanitized = _SAFE_COMPONENT.sub("_", cleaned)
    return sanitized or "unknown"


def _normalize_repo_key(value: str | None) -> str:
    """Return a normalized key for repository or channel comparisons."""

    if not value:
        return ""
    return _NORMALIZE_REPO_NAME.sub("", value.lower())


def _matching_repo_urls(
    channel_name: str | None, thread_name: str | None = None
) -> list[str]:
    """Return repos whose slugs match the channel or thread names."""

    candidate_keys: list[str] = []
    seen_keys: set[str] = set()
    for value in (channel_name, thread_name):
        key = _normalize_repo_key(value)
        if key and key not in seen_keys:
            candidate_keys.append(key)
            seen_keys.add(key)

    if not candidate_keys:
        return []

    from .repo_manager import load_repos

    candidate_to_urls: dict[str, list[str]] = {key: [] for key in candidate_keys}
    seen_urls: set[str] = set()

    for repo in load_repos():
        slug = repo.rstrip("/").rsplit("/", 1)[-1]
        if not slug:
            continue
        slug_key = _normalize_repo_key(slug)
        if slug_key in candidate_to_urls and repo not in seen_urls:
            candidate_to_urls[slug_key].append(repo)
            seen_urls.add(repo)

    matches: list[str] = []
    for key in candidate_keys:
        matches.extend(candidate_to_urls.get(key, ()))
    return matches


def _decode_utf8(data: bytes) -> str:
    """Return ``data`` decoded as UTF-8, falling back to ``errors='ignore'``."""

    try:
        return data.decode("utf-8")
    except UnicodeDecodeError:
        return data.decode("utf-8", "ignore")


def _plaintext_fallback(data: bytes) -> str | None:
    """Best-effort plaintext decoding for legacy captures."""

    text = _decode_utf8(data)
    if not text.strip():
        return None
    stripped = text.lstrip()
    prefixes = ("#", "- ", "##")
    if "\n" not in text and not any(stripped.startswith(prefix) for prefix in prefixes):
        return None
    return text


def _read_capture(path: Path, encrypter: Fernet | None) -> str | None:
    """Return the markdown contents for ``path`` handling encryption."""

    try:
        data = path.read_bytes()
    except OSError:
        return None

    if encrypter is None:
        try:
            return data.decode("utf-8")
        except UnicodeDecodeError:
            return None

    try:
        decrypted = encrypter.decrypt(data)
    except InvalidToken:
        return _plaintext_fallback(data)
    except Exception:
        return None

    return _decode_utf8(decrypted)


def _repository_urls_from_text(text: str) -> list[str]:
    """Return repository URLs parsed from capture ``text``."""

    urls: list[str] = []
    for line in text.splitlines():
        stripped = line.strip()
        if not stripped:
            continue
        if not stripped.lower().startswith(_REPOSITORY_PREFIX):
            continue
        _, _, value = stripped.partition(":")
        candidate = value.strip()
        if candidate:
            urls.append(candidate)
    return urls


def _capture_repository_urls(path: Path) -> list[str]:
    """Return repository URLs recorded in the capture stored at ``path``."""

    text = _read_capture(path, _get_encrypter())
    if not text:
        return []
    return _repository_urls_from_text(text)


def search_captures(query: str, *, limit: int = 5) -> list[SearchResult]:
    """Return saved capture snippets containing ``query``.

    Searches the configured Discord capture directory (including encrypted
    markdown files) for lines that include ``query`` in a case-insensitive
    comparison. Results are returned in path-sorted order and truncated to
    ``limit`` entries. Non-positive limits or missing directories yield an empty
    list.
    """

    if limit <= 0:
        return []

    root = _get_save_dir(require_writable=False)
    if not root.exists():
        return []

    encrypter = _get_encrypter()
    query_lower = query.lower()
    matches: list[SearchResult] = []

    for path in sorted(root.rglob("*.md")):
        text = _read_capture(path, encrypter)
        if not text:
            continue
        for line in text.splitlines():
            if query_lower in line.lower():
                snippet = line.strip()
                if len(snippet) > 120:
                    snippet = snippet[:117] + "..."
                matches.append(SearchResult(path=path, snippet=snippet))
                break
        if len(matches) >= limit:
            break

    return matches


def summarize_capture(
    path: Path, *, line_limit: int = SUMMARY_LINE_LIMIT
) -> str | None:
    """Return a short summary for the capture stored at ``path``.

    Summaries favor the message body over metadata and context. When the
    capture cannot be read or lacks meaningful content, ``None`` is returned.
    """

    text = _read_capture(path, _get_encrypter())
    if not text:
        return None

    summary_lines: list[str] = []
    metadata_preamble = True
    lines = text.splitlines()
    index = 0

    def _consume_saved_context(start: int) -> int | None:
        """Return the index after stored context or ``None`` for user content."""

        idx = start + 1
        saw_indented = False
        while idx < len(lines):
            candidate = lines[idx]
            if not candidate.strip():
                break
            if candidate.startswith("  "):
                saw_indented = True
                idx += 1
                continue
            if candidate.lstrip().startswith("- "):
                idx += 1
                continue
            return None
        return idx if saw_indented else None

    def _consume_saved_attachments(start: int) -> int | None:
        """Return the index after saved attachments or ``None`` for user content."""

        idx = start + 1
        matched = False
        while idx < len(lines):
            candidate = lines[idx]
            if not candidate.strip():
                break
            if _ATTACHMENT_LINE.match(candidate):
                matched = True
                idx += 1
                continue
            return None
        return idx if matched else None

    while index < len(lines):
        raw_line = lines[index]
        stripped = raw_line.strip()

        if metadata_preamble:
            if not stripped:
                index += 1
                continue
            lowered = stripped.lower()
            if lowered.startswith("## context"):
                consumed = _consume_saved_context(index)
                if consumed is not None:
                    index = consumed
                    continue
                metadata_preamble = False
                continue
            if lowered.startswith("## attachments"):
                consumed = _consume_saved_attachments(index)
                if consumed is not None:
                    index = consumed
                    continue
                metadata_preamble = False
                continue
            if stripped.startswith("#"):
                index += 1
                continue
            if any(stripped.startswith(prefix) for prefix in _METADATA_PREFIXES):
                index += 1
                continue
            if raw_line.startswith("  "):
                index += 1
                continue
            metadata_preamble = False
            continue

        if not stripped:
            index += 1
            continue

        lowered = stripped.lower()
        if lowered.startswith("## attachments"):
            index += 1
            while index < len(lines) and lines[index].strip():
                if _ATTACHMENT_LINE.match(lines[index]):
                    index += 1
                    continue
                break
            continue
        if stripped.startswith("##"):
            index += 1
            continue
        if stripped.startswith("#") and not summary_lines:
            index += 1
            continue
        if any(stripped.startswith(prefix) for prefix in _METADATA_PREFIXES):
            index += 1
            continue
        if raw_line.startswith("  "):
            index += 1
            continue

        if stripped.startswith("- "):
            cleaned = stripped[2:].strip()
        else:
            cleaned = stripped

        if not cleaned or cleaned == "-":
            index += 1
            continue

        summary_lines.append(cleaned)
        if len(summary_lines) >= line_limit:
            break
        index += 1

    if summary_lines:
        summary = " ".join(summary_lines)
    else:
        stripped_text = text.strip()
        if not stripped_text:
            return None
        summary = stripped_text.splitlines()[0].strip()

    summary = re.sub(r"\s+", " ", summary).strip()
    if len(summary) > SUMMARY_MAX_CHARS:
        summary = summary[: SUMMARY_MAX_CHARS - 3].rstrip() + "..."
    return summary


def digest_captures(query: str, *, limit: int = 3) -> list[DigestEntry]:
    """Return summarized captures that match ``query``.

    Results reuse :func:`search_captures` to locate relevant files and
    :func:`summarize_capture` to condense their contents. Entries lacking
    readable content are skipped. ``limit`` controls the number of summarized
    captures returned, with non-positive limits producing an empty list.
    """

    if limit <= 0:
        return []

    matches = search_captures(query, limit=max(limit * 2, limit))
    digest: list[DigestEntry] = []
    for match in matches:
        summary = summarize_capture(match.path)
        if not summary:
            continue
        digest.append(DigestEntry(path=match.path, summary=summary))
        if len(digest) >= limit:
            break
    return digest


def _get_encrypter() -> Fernet | None:
    """Return a Fernet instance when encryption is enabled."""

    key = os.getenv("AXEL_DISCORD_ENCRYPTION_KEY", "").strip()
    if not key:
        return None
    try:
        return Fernet(key.encode())
    except (TypeError, ValueError) as exc:  # pragma: no cover - defensive
        raise RuntimeError(
            "AXEL_DISCORD_ENCRYPTION_KEY must be a valid Fernet key"
        ) from exc


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
    author = _display_name(getattr(message, "author", None))
    jump_url = getattr(message, "jump_url", "")

    lines = [f"# {author}", ""]
    lines.append(f"- Channel: {channel_name or 'unknown'}")
    if thread_name:
        lines.append(f"- Thread: {thread_name}")
    matched_repos = _matching_repo_urls(channel_name, thread_name)
    needs_gabriel = any("token.place" in repo.lower() for repo in matched_repos)
    for repo_url in matched_repos:
        lines.append(f"- Repository: {repo_url}")
    if needs_gabriel:
        lines.append("- Security: https://github.com/futuroptimist/gabriel")
    lines.append(f"- Timestamp: {timestamp}")
    if jump_url:
        lines.append(f"- Link: {jump_url}")
    lines.append("")

    context_lines: list[str] = []
    if context:
        entries = [
            ctx
            for ctx in list(context)
            if getattr(ctx, "id", None) != getattr(message, "id", None)
        ]
        try:
            entries.sort(key=_context_sort_key)
        except Exception:
            pass
        if CONTEXT_LIMIT is not None and len(entries) > CONTEXT_LIMIT:
            entries = entries[-CONTEXT_LIMIT:]
        for ctx in entries:
            author = _display_name(getattr(ctx, "author", None))
            timestamp = getattr(ctx, "created_at", None)
            ts = timestamp.isoformat() if isinstance(timestamp, datetime) else ""
            jump_url = getattr(ctx, "jump_url", "")
            entry = f"- {author}"
            if ts:
                entry += f" @ {ts}"
            if jump_url:
                entry += f" ({jump_url})"
            context_lines.append(entry)
            body = getattr(ctx, "content", "")
            if body:
                context_lines.append(f"  {body}")
            else:
                context_lines.append("  (no content)")
    if context_lines:
        lines.append("## Context")
        lines.extend(context_lines)
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

    rendered = "\n".join(lines)
    encrypter = _get_encrypter()
    if encrypter:
        token = encrypter.encrypt(rendered.encode("utf-8"))
        path.write_bytes(token)
    else:
        path.write_text(rendered, encoding="utf-8")
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
    if context is None:
        context = await _collect_context(message)
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


async def _collect_context(
    trigger_message: discord.Message, *, limit: int = CONTEXT_LIMIT
) -> list[discord.Message]:
    """Return recent channel history while ignoring failures.

    The helper mirrors :func:`_gather_context` but guards against ``discord``
    permission errors, unexpected return types (plain lists), and iteration
    failures. Since context is a best-effort feature, any problem encountered
    while reading history results in an empty list instead of propagating.
    """

    channel = getattr(trigger_message, "channel", None)
    if channel is None or not hasattr(channel, "history"):
        return []

    call_variants = [
        {"limit": limit, "before": trigger_message, "oldest_first": True},
        {"limit": limit, "before": trigger_message},
        {"limit": limit},
    ]

    history_result: object | None = None
    for kwargs in call_variants:
        try:
            history_result = channel.history(**kwargs)
        except TypeError:
            continue
        except Exception:
            return []
        else:
            break

    if history_result is None:
        return []

    try:
        if inspect.isawaitable(history_result):
            history_result = await history_result
    except Exception:
        return []

    collected: list[discord.Message] = []

    def _append(item: object) -> None:
        if not item:
            return
        if getattr(item, "id", None) == getattr(trigger_message, "id", None):
            return
        collected.append(item)  # type: ignore[arg-type]

    if hasattr(history_result, "__aiter__"):
        iterator = history_result  # type: ignore[assignment]
        try:
            async for entry in iterator:
                _append(entry)
        except Exception:
            return []
    else:
        try:
            iterator = iter(history_result)  # type: ignore[arg-type]
        except TypeError:
            return []
        try:
            for entry in iterator:
                _append(entry)
        except Exception:
            return []

    if not collected:
        return []

    try:
        collected.sort(key=_context_sort_key)
    except Exception:
        pass

    if limit is not None:
        return collected[:limit]
    return collected


class AxelClient(discord.Client):
    def __init__(self, *, intents: discord.Intents):
        super().__init__(intents=intents)
        self.tree = app_commands.CommandTree(self)
        self._register_commands()

    def _register_commands(self) -> None:
        axel_group = app_commands.Group(
            name="axel",
            description="Axel local assistant commands",
        )

        @axel_group.command(
            name="search",
            description="Search saved Discord captures for text.",
        )
        @app_commands.describe(
            query="Text to search for within saved Discord captures.",
        )
        async def _search_command(interaction: discord.Interaction, query: str) -> None:
            results = search_captures(query)
            if not results:
                await interaction.response.send_message(
                    f"No captures found for '{query}'.",
                    ephemeral=True,
                )
                return

            root = _get_save_dir(require_writable=False)
            lines = [f"Matches for '{query}':"]
            for result in results:
                display_path = _format_relative_path(result.path, root)
                lines.append(f"- {display_path}: {result.snippet}")

            await interaction.response.send_message(
                "\n".join(lines),
                ephemeral=True,
            )

        @axel_group.command(
            name="summarize",
            description="Summarize the first capture that matches the query.",
        )
        @app_commands.describe(
            query="Text to locate a capture before summarizing it.",
        )
        async def _summarize_command(
            interaction: discord.Interaction, query: str
        ) -> None:
            results = search_captures(query, limit=1)
            if not results:
                await interaction.response.send_message(
                    f"No captures found for '{query}'.",
                    ephemeral=True,
                )
                return

            result = results[0]
            root = _get_save_dir(require_writable=False)
            display_path = _format_relative_path(result.path, root)

            summary = summarize_capture(result.path)
            if not summary:
                message = (
                    "Capture " f"{display_path} has no readable content to summarize."
                )
            else:
                message = f"Summary for '{query}' ({display_path}): {summary}"

            await interaction.response.send_message(message, ephemeral=True)

        @axel_group.command(
            name="digest",
            description="Summarize multiple captures that match the query.",
        )
        @app_commands.describe(
            query="Text to locate captures before generating a digest.",
        )
        async def _digest_command(interaction: discord.Interaction, query: str) -> None:
            digest = digest_captures(query)
            if not digest:
                await interaction.response.send_message(
                    f"No captures found for '{query}'.",
                    ephemeral=True,
                )
                return

            root = _get_save_dir(require_writable=False)
            lines = [f"Digest for '{query}':"]
            for entry in digest:
                display_path = _format_relative_path(entry.path, root)

                summary = entry.summary or "(no summary)"
                lines.append(f"- {display_path}: {summary}")

            await interaction.response.send_message(
                "\n".join(lines),
                ephemeral=True,
            )

        @axel_group.command(
            name="quest",
            description="Suggest a cross-repo quest from capture metadata.",
        )
        @app_commands.describe(
            query="Text to locate a capture before suggesting quests.",
        )
        async def _quest_command(interaction: discord.Interaction, query: str) -> None:
            results = search_captures(query, limit=1)
            if not results:
                await interaction.response.send_message(
                    f"No captures found for '{query}'.",
                    ephemeral=True,
                )
                return

            result = results[0]
            root = _get_save_dir(require_writable=False)
            relative_path = _format_relative_path(result.path, root)

            repos = _capture_repository_urls(result.path)
            if len(repos) < 2:
                message = (
                    f"Capture {relative_path} does not reference multiple "
                    "repositories."
                )
                await interaction.response.send_message(
                    message,
                    ephemeral=True,
                )
                return

            suggestions = suggest_cross_repo_quests(repos, limit=1)
            if not suggestions:
                message = f"No quest suggestions available for {relative_path}."
                await interaction.response.send_message(
                    message,
                    ephemeral=True,
                )
                return

            suggestion = suggestions[0]
            summary = str(suggestion.get("summary", "")).strip()
            details = str(suggestion.get("details", "")).strip()
            message = f"Quest for '{query}' ({relative_path}): {summary}"
            if details:
                message += f" — {details}"

            await interaction.response.send_message(message, ephemeral=True)

        self.tree.add_command(axel_group)

    async def setup_hook(self) -> None:  # pragma: no cover - network call
        await self.tree.sync()

    async def on_ready(self) -> None:  # pragma: no cover - network call
        print(f"Logged in as {self.user}")

    async def on_message(self, message: discord.Message) -> None:  # pragma: no cover
        if self.user is None or message.author == self.user:
            return
        if not self.user.mentioned_in(message):
            return

        context = await _gather_context(message)

        original: discord.Message | None = None
        reference = getattr(message, "reference", None)
        message_id = getattr(reference, "message_id", None)

        if message_id is not None and hasattr(message.channel, "fetch_message"):
            try:
                original = await message.channel.fetch_message(message_id)
            except Exception:
                original = None

        if original is None:
            original = message

        original_id = getattr(original, "id", None)
        trigger_id = getattr(message, "id", None)
        filtered_context = [
            ctx
            for ctx in context
            if getattr(ctx, "id", None) not in {original_id, trigger_id}
        ]
        path = await capture_message(original, context=filtered_context)
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
