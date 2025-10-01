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
already listed in `.gitignore`.

## Workflow

1. In a private server, reply to an existing message or start a thread.
2. Mention the bot in that reply or thread opener.
3. The bot records a markdown file under
   `local/discord/<channel>/<message_id>.md`. Channel names are sanitized so they
   remain filesystem-safe. Each capture includes:
   - author display name
   - ISO 8601 timestamp
   - channel name and thread (if applicable)
   - original message link
   - message content

   The saved format is covered by `tests/test_discord_bot.py` to prevent future
   regressions.
4. If the channel name matches a repository listed in the project's repo list
   (`repos.txt` or a file pointed to by `AXEL_REPO_FILE`), treat the capture as
   project knowledge for that repo.

### Supported Content Types

- **Text** – stored verbatim in the markdown file.
- **Hyperlinks** – saved alongside the message content.

## Analyzing Captured Messages

Saved files can be processed with local LLMs such as
[`llama_cpp_python`](https://pypi.org/project/llama-cpp-python/) or
[Ollama](https://github.com/ollama/ollama). Combine the markdown content and metadata to
summarize discussions, extract tasks, or generate project insights.

## Roadmap

Future improvements will expand the bot's capabilities:

- **Attachments** – download files with `Attachment.save()` into
  `local/discord/<channel>/<message_id>/` and reference them from the markdown for
  future multimodal models.
- **Thread history** – when mentioned inside a thread, call
  `thread.history()` (or `channel.history()` for replies) to capture context
  before saving.
- **Command interface** – provide slash commands such as `/axel summarize`
  or `/axel search` that run the local LLM on stored messages.

Contributions and ideas are welcome. Keep all bot logic local and respect user privacy.
