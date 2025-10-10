# Token Rotation Guidance

Regularly rotating API tokens reduces the impact of leaked credentials. Follow these steps for services used by axel:

- **GitHub**: visit <https://github.com/settings/tokens> to revoke old tokens and generate new ones. Update any environment variables or CI secrets that reference the old token.
- **Discord Bot**: in the [Developer Portal](https://discord.com/developers/applications), reset the bot token under the "Bot" tab. Update `DISCORD_BOT_TOKEN` in your environment.
- **token.place**: run `python -m axel.token_place rotate --base-url http://localhost:5000/api/v1`
  (pass `--api-key` or set `TOKEN_PLACE_API_KEY`) to replace old relay or server keys. Automated
  coverage lives in `tests/test_token_place.py::test_rotate_api_keys_requests_new_tokens` and
  `tests/test_token_place.py::test_main_rotate_prints_keys`.

Store new tokens in environment variables or encrypted secrets files. Avoid committing them to source control.
