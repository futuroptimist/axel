# Guidelines for LLM Assistants

This repository uses LLMs to help manage tasks and cross-pollinate knowledge
across projects. Repos are stored in `repos.txt` and managed via
`python -m axel.repo_manager`.

- Keep the roadmap in `README.md` up to date as tasks progress.
- Add new repos using the CLI or `axel.repo_manager.add_repo`.
- Run `flake8 axel tests` and `pytest --cov=axel --cov=tests` before committing.
- Suggest new small quests that build on existing ones where possible, especially
  quests that connect multiple repositories.
