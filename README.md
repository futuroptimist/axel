# axel

axel helps organize short, medium and long term goals using chat, reasoning and agentic LLMs. The project begins by keeping track of the GitHub repositories you contribute to. Over time it will fetch this list automatically and provide tools to analyze those repos and generate actionable quests.

[![Lint & Format](https://img.shields.io/github/actions/workflow/status/futuroptimist/axel/.github/workflows/01-lint-format.yml?label=lint%20%26%20format)](https://github.com/futuroptimist/axel/actions/workflows/01-lint-format.yml)
[![Tests](https://img.shields.io/github/actions/workflow/status/futuroptimist/axel/.github/workflows/02-tests.yml?label=tests)](https://github.com/futuroptimist/axel/actions/workflows/02-tests.yml)
[![Coverage](https://codecov.io/gh/futuroptimist/axel/branch/main/graph/badge.svg)](https://codecov.io/gh/futuroptimist/axel)
[![Docs](https://img.shields.io/github/actions/workflow/status/futuroptimist/axel/.github/workflows/03-docs.yml?label=docs)](https://github.com/futuroptimist/axel/actions/workflows/03-docs.yml)
[![License](https://img.shields.io/github/license/futuroptimist/axel)](LICENSE)

## roadmap
- [x] maintain a list of repos in `repos.txt`
- [x] simple CLI for managing repos (`python -m axel.repo_manager`)
- [x] contributor guide (see `CONTRIBUTING.md`)
- [x] remove repos from the list (`python -m axel.repo_manager remove`)
- [ ] fetch repos from the GitHub API
- [ ] integrate LLM assistants to suggest quests across repos
- [ ] integrate `token.place` clients across all repos
- [ ] integrate [`gabriel`](https://github.com/futuroptimist/gabriel) as a security layer across repos
- [x] self-hosted Discord bot for ingesting messages when mentioned (see docs/discord-bot.md)
- [x] represent personal flywheel of projects and highlight cross-pollination (see repo list below)
- [x] document workflow for a private `local/` directory (see local setup below)
- [x] track tasks with markdown files in the `issues/` folder
- [x] verify `local/` directories are gitignored (see `.gitignore`)
- [x] add `THREAT_MODEL.md` with cross-repo considerations (see `docs/THREAT_MODEL.md`)
- [x] provide token rotation guidance in docs (see `docs/ROTATING_TOKENS.md`)
- [ ] encrypt notes saved under `local/discord/`
- [x] review permissions for integrated tools (token.place, gabriel) (see docs/THREAT_MODEL.md)

## installation

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e .
uv pip install pre-commit
pre-commit install
```

## usage

1. Add a repo with `python -m axel.repo_manager add <url>` or edit `repos.txt`.
   Whitespace around the URL is stripped automatically.
2. View the list with `python -m axel.repo_manager list`.
3. Remove a repo with `python -m axel.repo_manager remove <url>`.
4. Run `pre-commit run --all-files` before committing to check formatting and tests.
5. Pass `--path <file>` or set `AXEL_REPO_FILE` to use a custom repo list.
6. Coverage reports are uploaded to [Codecov](https://codecov.io/gh/futuroptimist/axel) via CI.

## local setup

To keep personal notes and repo lists private, set `AXEL_REPO_FILE` to a path
under `local/`, which is gitignored. The repo manager creates the directory
automatically if it doesn't already exist.

Example:

```bash
python -m axel.repo_manager add https://github.com/your/private-repo --path local/repos.txt
export AXEL_REPO_FILE=local/repos.txt
git check-ignore -v local/
```

The `git check-ignore` command confirms that `local/` is excluded from version
control.

Start with `examples/local/repos_example.txt` when creating your private repo list.

## privacy & transparency

Axel treats your goals with respect. Repository lists and any Discord notes
are stored locally by default. Follow guidance from
[gabriel](https://github.com/futuroptimist/gabriel) when sharing sensitive
information. Because this project is entirely open source, the community can
audit how data is handled. We rely on the
[flywheel](https://github.com/futuroptimist/flywheel) template to keep our
lint, test and documentation practices transparent.
See [docs/THREAT_MODEL.md](docs/THREAT_MODEL.md) for cross-repo security tips.
For instructions on rotating API tokens see [docs/ROTATING_TOKENS.md](docs/ROTATING_TOKENS.md).

## API

```python
from axel import add_repo, list_repos

add_repo("https://github.com/example/repo")
print(list_repos())
```

## discord bot

See [docs/discord-bot.md](docs/discord-bot.md) for running a local Discord bot
that saves mentioned messages to `local/discord/`.

## publishing

Before flipping this repository to public, search the codebase for accidental credentials.
A quick sanity check is:

```bash
git ls-files -z | xargs -0 grep -i --line-number --context=1 -e token -e secret -e password
```

Review the output and remove any sensitive data. Make sure `repos.txt` contains only repositories you wish to share.

The repos in `repos.txt` come from various projects like
[`dspace`](https://github.com/democratizedspace/dspace) and
[`futuroptimist`](https://github.com/futuroptimist/futuroptimist). Axel aims to
cross‑pollinate ideas between them by suggesting quests that touch multiple
codebases.
New additions such as [`gabriel`](https://github.com/futuroptimist/gabriel) help expand this flywheel by providing an open-source OSINT agent focused on personal safety.
The [`flywheel`](https://github.com/futuroptimist/flywheel) template bundles
linting, testing, and documentation checks so new repositories can start with
healthy continuous integration from the beginning.
Other tracked repos include:
[`sigma`](https://github.com/futuroptimist/sigma), an open-source AI pin device,
the [`blog`](https://github.com/futuroptimist/blog) for publishing progress,
and [`esp.ac`](https://github.com/futuroptimist/esp.ac), a simple landing page
for Esp.

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on sending pull requests.
This project adheres to the [Code of Conduct](CODE_OF_CONDUCT.md).
For LLM-specific tips see [AGENTS.md](AGENTS.md).
