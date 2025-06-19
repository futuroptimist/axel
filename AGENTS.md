# Guidelines for LLM Assistants

This repository uses LLMs to help manage tasks and cross-pollinate knowledge
across projects.

- Keep the roadmap in `README.md` up to date as tasks progress.
- Add new repos to `repos.txt` using `axel.repo_manager.add_repo`.
- Run `flake8` and `pytest --cov=axel --cov=tests` before committing.
- Suggest new small quests that build on existing ones where possible.
