# Token Rotation Guidance

Regularly rotating API tokens reduces the impact of leaked credentials. Follow these steps for services used by axel:

- **GitHub**: visit <https://github.com/settings/tokens> to revoke old tokens and generate new ones. Update any environment variables or CI secrets that reference the old token.
- **Discord Bot**: in the [Developer Portal](https://discord.com/developers/applications), reset the bot token under the "Bot" tab. Update `DISCORD_BOT_TOKEN` in your environment.
- **token.place**: run `tp auth rotate` (once implemented) to replace old relay or server keys.

Store new tokens in environment variables or encrypted secrets files. Avoid committing them to source control.
