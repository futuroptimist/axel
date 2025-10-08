# Discord Bot Integration Prompt

This guide describes a self-hosted Discord bot that captures contextual messages from a
private server and saves them for offline analysis with a local language model.

## Goals

- Run entirely on the user's machine to avoid leaking private data.
- Support the standard Discord OAuth flow so the bot can be invited to any personal server.
- When the bot is mentioned in a reply or thread, persist the referenced message and its
  metadata under a gitignored directory.
- Use the saved context to enrich repository knowledge, especially when the Discord channel
  name matches a configured repository name.

## Setup

```bash
uv pip install discord.py
python -m axel.discord_bot
```

The bot reads its token from the `DISCORD_BOT_TOKEN` environment variable and requires the
**Message Content Intent** in the Discord Developer Portal.

Messages are stored under `local/discord/` (configurable via `AXEL_DISCORD_DIR`) which is
already listed in `.gitignore`. The helper `axel.discord_bot.capture_message` downloads
attachments before writing the markdown file, making it easy to exercise the behavior in
tests.

Use `axel.discord_bot.search_captures` to scan saved markdown files for matching text. The helper
handles encrypted captures (when `AXEL_DISCORD_ENCRYPTION_KEY` is set) and limits the number of
results returned; see
`tests/test_discord_bot.py::test_search_captures_returns_matches`,
`tests/test_discord_bot.py::test_search_captures_decrypts_encrypted_files`, and
`tests/test_discord_bot.py::test_search_captures_respects_limit`.

## Encrypting Captures

Set `AXEL_DISCORD_ENCRYPTION_KEY` to a
[Fernet](https://cryptography.io/en/latest/fernet/) key to encrypt saved markdown files.
When the variable is set, `save_message` writes an encrypted token instead of plaintext
markdown. Generate a key locally with:

```bash
python -c "from cryptography.fernet import Fernet; print(Fernet.generate_key().decode())"
```

Store the key securely (for example, in a password manager) and export it before running
the bot. Attachments remain on disk in plaintext so they can be referenced by the markdown
once decrypted.

## Workflow

1. In a private server, reply to an existing message or start a thread.
2. Mention the bot in that reply or thread opener. Mentions inside thread openers are
   captured even when Discord omits a ``message.reference`` pointer.
3. The bot records a markdown file under
   `local/discord/<channel>/<message_id>.md`, where `<channel>` is sanitized to remove
   filesystem-unsafe characters. Each file contains:
   - author display name as the heading
   - bullet-point metadata for the channel, optional thread name, matching repository
     URLs when the channel corresponds to an entry in the repo list, ISO 8601 timestamp,
     and original message link
  - a `## Context` section (when available) listing up to five prior messages in
    oldest-first order, even when Discord's API returns them newest-first. The
    triggering mention is excluded so only earlier context appears. Each entry records
    the author, timestamp, source link, and an indented line with the original message text
    (or `(no content)` when empty).
   - the captured message content beneath the metadata and context
4. If the channel name matches a repository listed in the project's repo list
   (`repos.txt` or a file pointed to by `AXEL_REPO_FILE`), the saved metadata
   includes a `Repository:` entry pointing to the matching URL so you can treat the
   capture as project knowledge for that repo.

### Supported Content Types

- **Text** – stored verbatim in the markdown file.
- **Hyperlinks** – saved alongside the message content.
- **Attachments** – saved to `local/discord/<channel>/<message_id>/` with references inside the
  markdown (see `tests/test_discord_bot.py::test_capture_message_downloads_attachments`).

## Slash Commands

The bot registers `/axel search` as a slash command for quickly locating saved captures by
keyword. Results list relative file paths and the first matching line, returned as an
ephemeral response so only the requester sees the output. Coverage lives in
`tests/test_discord_bot.py::test_axel_search_command_replies_with_matches`.

Use `/axel summarize` to generate a quick synopsis of the first capture that matches the
provided query. The helper prioritizes the saved message body, skipping metadata and
thread context so the summary stays focused on the actionable text. Summaries surface the
relative file path alongside the condensed content in an ephemeral response. Coverage
spans `tests/test_discord_bot.py::test_summarize_capture_extracts_message_body`,
`tests/test_discord_bot.py::test_summarize_capture_includes_bullet_message_body`, and
`tests/test_discord_bot.py::test_axel_summarize_command_replies_with_summary`.

## Analyzing Captured Messages

Saved files can be processed with local LLMs such as
[`llama_cpp_python`](https://pypi.org/project/llama-cpp-python/) or
[Ollama](https://github.com/ollama/ollama). Combine the markdown content and metadata to
summarize discussions, extract tasks, or generate project insights.

Automated coverage for the capture format lives in
`tests/test_discord_bot.py::test_save_message_includes_metadata`,
`tests/test_discord_bot.py::test_save_message_includes_repository_metadata`,
`tests/test_discord_bot.py::test_save_message_records_thread_metadata`,
`tests/test_discord_bot.py::test_save_message_includes_context`,
`tests/test_discord_bot.py::test_save_message_orders_context_oldest_first`,
`tests/test_discord_bot.py::test_save_message_limits_context_entries`,
`tests/test_discord_bot.py::test_gather_context_reads_channel_history`,
`tests/test_discord_bot.py::test_capture_message_downloads_attachments`, and
`tests/test_discord_bot.py::test_save_message_encrypts_when_key_set`,
`tests/test_discord_bot.py::test_axel_client_excludes_trigger_from_context`.

## Roadmap

Future improvements will expand the bot's capabilities:

- **Command interface** – extend the existing `/axel search` and `/axel summarize`
  commands with additional local LLM workflows that operate on stored messages.

Contributions and ideas are welcome. Keep all bot logic local and respect user privacy.
Automated coverage lives in `tests/test_discord_bot.py` (see the tests referenced above).
