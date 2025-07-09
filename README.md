# axel

axel helps organize short, medium and long term goals using chat, reasoning and agentic LLMs. The project begins by keeping track of the GitHub repositories you contribute to. Over time it will fetch this list automatically and provide tools to analyze those repos and generate actionable quests.

[![CI](https://github.com/futuroptimist/axel/actions/workflows/ci.yml/badge.svg)](https://github.com/futuroptimist/axel/actions/workflows/ci.yml)
[![Coverage](https://codecov.io/gh/futuroptimist/axel/branch/main/graph/badge.svg)](https://codecov.io/gh/futuroptimist/axel)

## roadmap
- [x] maintain a list of repos in `repos.txt`
- [x] simple CLI for managing repos
- [x] contributor guide
- [x] remove repos from the list
- [ ] fetch repos from the GitHub API
- [ ] integrate LLM assistants to suggest quests across repos
- [ ] integrate `token.place` clients across all repos
- [ ] integrate [`gabriel`](https://github.com/futuroptimist/gabriel) as a security layer across repos
- [ ] self-hosted Discord bot for ingesting messages when mentioned
- [ ] represent personal flywheel of projects and highlight cross-pollination
- [x] document workflow for a private `local/` directory
- [x] track tasks with markdown files in the `issues/` folder

## installation

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e .
```

## usage

1. Add a repo with `python -m axel.repo_manager add <url>` or edit `repos.txt`.
2. View the list with `python -m axel.repo_manager list`.
3. Remove a repo with `python -m axel.repo_manager remove <url>`.
4. Run `pre-commit run --all-files` before committing to check formatting and tests.
5. Pass `--path <file>` or set `AXEL_REPO_FILE` to use a custom repo list.

## local setup

To keep personal notes and repo lists private, create a `local/` directory and
add it to `.gitignore`. Set `AXEL_REPO_FILE=local/repos.txt` to use a private
repo list without committing it to source control.

Example:

```bash
mkdir -p local
echo "https://github.com/your/private-repo" > local/repos.txt
export AXEL_REPO_FILE=local/repos.txt
```

See `examples/` for a sample repo list.

## privacy & transparency

Axel treats your goals with respect. Repository lists and any Discord notes
are stored locally by default. Follow guidance from
[gabriel](https://github.com/futuroptimist/gabriel) when sharing sensitive
information. Because this project is entirely open source, the community can
audit how data is handled. We rely on the
[flywheel](https://github.com/futuroptimist/flywheel) template to keep our
lint, test and documentation practices transparent.

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
