# Agents.md for axel

This file guides LLM assistants working on this repository. See the [Agents.md specification](https://gist.github.com/dpaluy/cc42d59243b0999c1b3f9cf60dfd3be6) and [agentsmd.net](https://agentsmd.net/) for background.

## Project Structure
- `axel/` – Python package with the CLI and helpers
- `tests/` – pytest suite
- `docs/` – documentation and security notes
- `examples/` – sample repo lists
- `issues/` – markdown tasks to track progress

## Coding Conventions
- Python 3.11+
- Black and isort formatting
- Descriptive names and inline comments for complex logic
- Keep modules small; prefer functions over large classes

## Testing Requirements
- Run `flake8 axel tests` and `pytest --cov=axel --cov=tests` before committing
- `pre-commit run --all-files` enforces formatting and runs tests
- Add tests for new functionality

## Pull Request Guidelines
1. Provide a clear description and reference related issues
2. Ensure all checks pass and coverage does not regress
3. Include screenshots if UI changes are introduced
4. Keep each PR focused on one concern

## Programmatic Checks
```bash
flake8 axel tests
pytest --cov=axel --cov=tests
```

## Workflow Notes
- Before commits, pushes, or other operational mutations, run
  `python -m axel.working_hours --config .axel/hillclimb/config.yml` and proceed only
  when it succeeds. Repeat the check before each later mutation. Default blocked
  working hours are Monday–Friday, 09:00 inclusive to 17:00 exclusive in
  `America/Los_Angeles` (DST-aware). Read-only inspection and planning may continue.
  Forks/clones can customize the configuration; see
  [the working-hours guide](docs/HILLCLIMB.md#working-hours-guard).
- Manage repositories with `python -m axel.repo_manager`
- Set `AXEL_REPO_FILE` for a custom repo list
- Keep the [roadmap](README.md#roadmap) updated
- Suggest quests that link multiple projects from `repos.txt`
- Document private notes in `local/` (ignored by Git)
- Scan for secrets with the command in `README.md` before publishing
- Integrate `token.place` clients and coordinate with [gabriel](https://github.com/futuroptimist/gabriel)
- Use [`futuroptimist/flywheel`](https://github.com/futuroptimist/flywheel) when starting new repositories to
  inherit preconfigured linting, testing, and docs checks
