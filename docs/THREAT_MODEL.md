# Threat Model

Axel coordinates multiple repositories and stores user notes locally. This document summarizes security considerations shared by [gabriel](https://github.com/futuroptimist/gabriel).

- Secrets such as API keys should be stored in environment variables or encrypted files, never committed to source control.
- The `local/` directory is ignored by Git by default. Verify this with `git check-ignore -v local/` after setup.
- When using `token.place` or `gabriel`, review their permissions and rotate tokens regularly. See [docs/ROTATING_TOKENS.md](ROTATING_TOKENS.md) for detailed steps.
- Notes saved under `local/discord/` stay on your machine and are encrypted with a Fernet key.
  Store the key in `AXEL_DISCORD_KEY` or in a gitignored key file to avoid leaking it.
- Before publishing the repository, scan for accidental secrets with:

  ```bash
  git ls-files -z | xargs -0 grep -i --line-number --context=1 -e token -e secret -e password
  ```

See `docs/IMPROVEMENT_CHECKLISTS.md` in the gabriel repository for related tasks.
