# axel

axel helps organize short, medium and long term goals using chat, reasoning and agentic LLMs. The project begins by keeping track of the GitHub repositories you contribute to. Over time it will fetch this list automatically and provide tools to analyze those repos and generate actionable quests.

[![CI](https://github.com/futuroptimist/axel/actions/workflows/ci.yml/badge.svg)](https://github.com/futuroptimist/axel/actions/workflows/ci.yml)

## roadmap
- [x] maintain a list of repos in `repos.txt`
- [x] simple CLI for managing repos
- [x] contributor guide
- [ ] fetch repos from the GitHub API
- [ ] integrate LLM assistants to suggest quests across repos

## usage

1. Add a repo with `python -m axel.repo_manager add <url>` or edit `repos.txt`.
2. View the list with `python -m axel.repo_manager list`.
3. Run `flake8 axel tests` and `pytest --cov=axel --cov=tests` before committing.
4. Pass `--path <file>` or set `AXEL_REPO_FILE` to use a custom repo list.

See `examples/` for a sample repo list.

The repos in `repos.txt` come from various projects like
[`dspace`](https://github.com/democratizedspace/dspace) and
[`futuroptimist`](https://github.com/futuroptimist/futuroptimist). Axel aims to
cross‑pollinate ideas between them by suggesting quests that touch multiple
codebases.

See [CONTRIBUTORS.md](CONTRIBUTORS.md) for guidelines on sending pull requests.
