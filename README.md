# axel

axel helps organize short, medium and long term goals using chat, reasoning and agentic LLMs. The project begins by keeping track of the GitHub repositories you contribute to. Over time it will fetch this list automatically and provide tools to analyze those repos and generate actionable quests.

[![CI](https://github.com/futuroptimist/axel/actions/workflows/ci.yml/badge.svg)](https://github.com/futuroptimist/axel/actions/workflows/ci.yml)

## roadmap
- [x] maintain a list of repos in `repos.txt`
- [x] simple CLI for managing repos
- [x] contributor guide
- [x] remove repos from the list
- [ ] fetch repos from the GitHub API
- [ ] integrate LLM assistants to suggest quests across repos
- [ ] integrate `token.place` clients across all repos
- [ ] represent personal flywheel of projects and highlight cross-pollination
- [ ] document workflow for a private `local/` directory
- [x] track tasks with markdown files in the `issues/` folder

## usage

1. Add a repo with `python -m axel.repo_manager add <url>` or edit `repos.txt`.
2. View the list with `python -m axel.repo_manager list`.
3. Remove a repo with `python -m axel.repo_manager remove <url>`.
4. Run `flake8 axel tests` and `pytest --cov=axel --cov=tests` before committing.
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

The repos in `repos.txt` come from various projects like
[`dspace`](https://github.com/democratizedspace/dspace) and
[`futuroptimist`](https://github.com/futuroptimist/futuroptimist). Axel aims to
cross‑pollinate ideas between them by suggesting quests that touch multiple
codebases.
New additions such as [`gabriel`](https://github.com/futuroptimist/gabriel) help expand this flywheel by providing an open-source OSINT agent focused on personal safety.

See [CONTRIBUTORS.md](CONTRIBUTORS.md) for guidelines on sending pull requests.
