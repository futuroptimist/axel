# Token Rotation Guidance

Regularly rotating API tokens reduces the impact of leaked credentials. Follow these steps for services used by axel:

- **GitHub**: visit <https://github.com/settings/tokens> to revoke old tokens and generate new ones. Update any environment variables or CI secrets that reference the old token.
- **Discord Bot**: in the [Developer Portal](https://discord.com/developers/applications), reset the bot token under the "Bot" tab. Update `DISCORD_BOT_TOKEN` in your environment.
- **token.place**: CLI rotation is disabled until secure credential delivery is available.
  Every `python -m axel.token_place rotate` invocation exits with status 1 before parsing
  rotation arguments, resolving credentials, or sending a request. It prints only a fixed
  refusal message to stderr and nothing to stdout, including when extra arguments or `--help`
  are supplied. This prevents new keys from entering captured CLI output; simply hiding keys
  after a successful rotation could discard the operator's only copy.
  The programmatic `axel.token_place.rotate_api_keys()` helper remains available and returns
  the new relay/server credentials without printing them. Its callers remain responsible for
  secure delivery and storage. A replacement CLI delivery mechanism requires a separate design.
  Synthetic coverage lives in `tests/test_token_place.py::test_rotate_api_keys_requests_new_tokens`
  and `tests/test_token_place.py::test_main_rotate_refuses_without_requests_or_credential_output`.

Store new tokens in environment variables or encrypted secrets files. Avoid committing them to source control.
