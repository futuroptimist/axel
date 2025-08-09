# Self-Hosted Discord Bot

This document outlines a proposed architecture for running a local Discord bot
that ingests messages from your server.

## Goals

- Allow a user to invite a bot to their personal server using the standard
  Discord bot OAuth flow.
- Keep all bot logic and data on the user's machine to avoid leaking private
  information.
- When the bot is mentioned in a reply, download the parent message and store a
  local copy for future reference.
- Persist messages under `local/discord/` which is gitignored by default.

## Launching the Bot

```bash
uv pip install discord.py
python -m axel.discord_bot
```

This will start the bot using the token set in the `DISCORD_BOT_TOKEN`
environment variable. Once running, it appears online in the server.

Ensure the **Message Content Intent** is enabled for the bot in the Discord
Developer Portal so it can read message text. The client enables this intent
when starting.

## Usage

Mention the bot in reply to any message you want to save. The bot fetches the
original message and writes a markdown file under
`local/discord/<message_id>.md`. The directory is created automatically if it
doesn't exist. Each file records the author's display name, an ISO 8601
timestamp, and the message content.

Future iterations can analyze these notes alongside `token.place` and
[`gabriel`](https://github.com/futuroptimist/gabriel) to suggest quests across
repositories.
