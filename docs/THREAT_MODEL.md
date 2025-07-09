# Threat Model

Axel coordinates multiple repositories and stores user notes locally. This document summarizes security considerations shared by [gabriel](https://github.com/futuroptimist/gabriel).

- Secrets such as API keys should be stored in environment variables or encrypted files, never committed to source control.
- The `local/` directory is gitignored by default. Verify this with `git check-ignore -v local/` after setup.
- When using `token.place` or `gabriel`, review their permissions and rotate tokens regularly. See [docs/ROTATING_TOKENS.md](ROTATING_TOKENS.md) for detailed steps.
- Notes saved under `local/discord/` stay on your machine. Future work may encrypt these files.

See `docs/IMPROVEMENT_CHECKLISTS.md` in the gabriel repository for related tasks.
