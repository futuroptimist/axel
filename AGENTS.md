# Guidelines for LLM Assistants

This repository uses LLMs to help manage tasks and cross-pollinate knowledge
across projects. Repos are stored in `repos.txt` and managed via
`python -m axel.repo_manager`.

- Keep the roadmap in `README.md` up to date as tasks progress.
- Add new repos using the CLI or `axel.repo_manager.add_repo`, and remove them
  with `axel.repo_manager.remove_repo` when needed.
- Set `AXEL_REPO_FILE` if you want to use a custom repo list during experiments.
- Run `flake8 axel tests` and `pytest --cov=axel --cov=tests` before committing.
- Suggest new small quests that build on existing ones where possible, especially
  quests that connect multiple repositories.
- Look for opportunities to integrate or document `token.place` clients across
  the repositories listed in `repos.txt`.
- Highlight synergies with [futuroptimist/gabriel](https://github.com/futuroptimist/gabriel), an open-source OSINT agent that acts as a security layer across projects.
- Use [`futuroptimist/flywheel`](https://github.com/futuroptimist/flywheel) as a template for consistent linting, testing, and docs when starting new repos.
- Keep markdown issues in the `issues/` folder up to date.
- Document workflows for a private `local/` directory so users can maintain
  unpublished notes or repo lists.
- Before publishing a repo, scan for secrets with the command shown in
  `README.md`.
- Refer to `CONTRIBUTING.md` for more detailed contribution instructions.
- Use `uv` to manage the virtual environment and install dependencies.
- Treat users' goals and ambitions with care. Keep data local whenever
  possible and follow [gabriel](https://github.com/futuroptimist/gabriel)
  guidance for security. Use the open-source nature of this project to
  provide transparency and auditability, taking inspiration from
  [`flywheel`](https://github.com/futuroptimist/flywheel) for best
  practices.
