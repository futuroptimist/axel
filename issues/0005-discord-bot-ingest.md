# Issue 0005: Self-Hosted Discord Bot Ingestion

Add a simple Discord bot that users can run locally. When mentioned in a reply,
the bot downloads the parent message and stores it under `local/discord/`.
This keeps any notes private while making them accessible to axel for
future LLM-powered quests.

- [ ] create `axel.discord_bot` module
- [ ] document workflow in `docs/discord-bot.md`
- [ ] update roadmap with this feature
- [ ] explore integrations with `token.place` and `gabriel`
