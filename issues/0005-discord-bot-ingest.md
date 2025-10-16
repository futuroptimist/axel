# Issue 0005: Self-Hosted Discord Bot Ingestion

Labels: good first issue

Add a simple Discord bot that users can run locally. When mentioned in a reply,
the bot downloads the parent message and stores it under `local/discord/`.
This keeps any notes private while making them accessible to axel for
future LLM-powered quests.

- [x] create `axel.discord_bot` module
- [x] document workflow in `docs/discord-bot.md`
- [x] update roadmap with this feature
- [x] explore integrations with `token.place` and `gabriel`
