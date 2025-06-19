# axel

axel helps organize short, medium and long term goals using chat, reasoning and agentic LLMs. The project begins by keeping track of the GitHub repositories you contribute to. Over time it will fetch this list automatically and provide tools to analyze those repos and generate actionable quests.

[![CI](https://github.com/futuroptimist/axel/actions/workflows/ci.yml/badge.svg)](https://github.com/futuroptimist/axel/actions/workflows/ci.yml)

## roadmap
- [ ] maintain a list of repos in `repos.txt`
- [ ] simple CLI for managing repos
- [ ] fetch repos from the GitHub API
- [ ] integrate LLM assistants to suggest quests across repos

## usage

1. Add your repo URLs to `repos.txt` or use `python -m axel.repo_manager <url>` in the future.
2. Run `pytest` to ensure everything works.

See `examples/` for a sample repo list.
