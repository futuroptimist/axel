# Known Issues & Footguns

Track common pitfalls while Axel matures. The README links here alongside the FAQ and is guarded
by `tests/test_readme.py::test_readme_includes_alpha_status_and_supporting_docs` to keep the docs
discoverable.

## Discord capture directory fallback

Axel now falls back to `~/.axel/discord/` when the default `local/discord/` path is read-only so
captures are still persisted. Set `AXEL_DISCORD_DIR` to point at another location if you prefer a
different directory; the bot validates that the path is writable and raises a clear error when it
is not (see `tests/test_discord_bot.py::test_get_save_dir_falls_back_when_default_unwritable` and
`tests/test_discord_bot.py::test_get_save_dir_errors_when_env_dir_unwritable`).

## GitHub token scope requirements

`python -m axel.repo_manager fetch` requires a personal access token with the `repo` scope to access
private repositories. Without that scope GitHub returns 403 responses.

## Running CI locally

Commands referenced throughout the docs assume `uv` created a virtual environment.
If you use another tool, ensure `flake8 axel tests` and `pytest --cov=axel --cov=tests` still succeed
before committing.
