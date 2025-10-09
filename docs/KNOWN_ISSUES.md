# Known Issues & Footguns

Track common pitfalls while Axel matures. The README links here alongside the FAQ and is guarded
by `tests/test_readme.py::test_readme_includes_alpha_status_and_supporting_docs` to keep the docs
discoverable.

## Discord capture directory permissions

Running the Discord bot inside a read-only checkout prevents captures from being saved under
`local/discord/`. Ensure the working tree is writable or point `AXEL_DISCORD_DIR` to a location with
write access.

## GitHub token scope requirements

`python -m axel.repo_manager fetch` requires a personal access token with the `repo` scope to access
private repositories. Without that scope GitHub returns 403 responses.

## Running CI locally

Commands referenced throughout the docs assume `uv` created a virtual environment.
If you use another tool, ensure `flake8 axel tests` and `pytest --cov=axel --cov=tests` still succeed
before committing.
