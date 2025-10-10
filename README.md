# axel

axel helps organize short, medium and long term goals using chat, reasoning and agentic
LLMs. The project begins by keeping track of the GitHub repositories you contribute to.
Over time it will fetch this list automatically and provide tools to analyze those repos
and generate actionable quests.

[![Lint & Format](https://img.shields.io/github/actions/workflow/status/futuroptimist/axel/.github/workflows/01-lint-format.yml?label=lint%20%26%20format)](https://github.com/futuroptimist/axel/actions/workflows/01-lint-format.yml)
[![Tests](https://img.shields.io/github/actions/workflow/status/futuroptimist/axel/.github/workflows/02-tests.yml?label=tests)](https://github.com/futuroptimist/axel/actions/workflows/02-tests.yml)
[![Coverage](https://codecov.io/gh/futuroptimist/axel/branch/main/graph/badge.svg)](https://codecov.io/gh/futuroptimist/axel)
[![Docs](https://img.shields.io/github/actions/workflow/status/futuroptimist/axel/.github/workflows/03-docs.yml?label=docs)](https://github.com/futuroptimist/axel/actions/workflows/03-docs.yml)
[![Status: Alpha](https://img.shields.io/badge/status-alpha-orange)](docs/FAQ.md)
[![License](https://img.shields.io/github/license/futuroptimist/axel)](LICENSE)

## Quickstart (≤60s)

```bash
git clone https://github.com/futuroptimist/axel
cd axel
docker compose -f docker-compose-mock.yml up
```

This launches the token.place server, relay and a mock LLM using one command.

## status

Axel is currently in **alpha** while workflows and integrations continue to harden.
Start with the [FAQ](docs/FAQ.md) for common setup questions and read through
[Known Issues & Footguns](docs/KNOWN_ISSUES.md) before running the CLI across multiple repositories.
Automated coverage for these references lives in
`tests/test_readme.py::test_readme_includes_alpha_status_and_supporting_docs`.

## roadmap
- [x] maintain a list of repos in `repos.txt`
- [x] simple CLI for managing repos (`python -m axel.repo_manager`)
- [x] contributor guide (see `CONTRIBUTING.md`)
- [x] remove repos from the list (`python -m axel.repo_manager remove`)
- [x] fetch repos from the GitHub API (`python -m axel.repo_manager fetch`)
- [x] integrate LLM assistants to suggest quests across repos
- [x] integrate `token.place` clients across all repos
- [x] integrate [`gabriel`](https://github.com/futuroptimist/gabriel) as a security layer across repos
- [x] self-hosted Discord bot for ingesting messages when mentioned (see docs/discord-bot.md)
- [x] represent personal flywheel of projects and highlight cross-pollination (see repo list below)
- [x] document workflow for a private `local/` directory (see local setup below)
- [x] track tasks with markdown files in the `issues/` folder
- [x] verify `local/` directories are ignored by Git (see `.gitignore`)
- [x] add `THREAT_MODEL.md` with cross-repo considerations (see `docs/THREAT_MODEL.md`)
- [x] provide token rotation guidance in docs (see `docs/ROTATING_TOKENS.md`)
- [x] adopt [`flywheel`](https://github.com/futuroptimist/flywheel) template for new repositories
- [x] encrypt notes saved under `local/discord/`
- [x] review permissions for integrated tools (token.place, gabriel) (see docs/THREAT_MODEL.md)
- [x] achieve 100% test coverage

## installation

```bash
uv venv .venv
source .venv/bin/activate
uv pip install -e .
uv pip install -r requirements.txt pre-commit
pre-commit install
```

## usage

1. Add a repo with `python -m axel.repo_manager add <url>` (use `https://...`).
   Alternatively, edit `repos.txt`.
   Lines starting with `#` or with trailing `#` comments are ignored.
   Whitespace around the URL is stripped automatically and trailing slashes are
   removed.
   The repository list is kept sorted alphabetically, ignoring case. Removing entries
   preserves this order. Duplicate URLs are automatically removed (case-insensitive).
2. View the list with `python -m axel.repo_manager list`. Output is sorted
   alphabetically, ignoring case.
3. Remove a repo with `python -m axel.repo_manager remove <url>`.
4. Replace `repos.txt` with the authenticated user's repos via
   `python -m axel.repo_manager fetch`. Pass `--token` or set ``GH_TOKEN`` or
   ``GITHUB_TOKEN``. Use `--visibility public|private|all` to filter the
   repositories returned by the GitHub API.
5. Run `pre-commit run --all-files` before committing to check formatting and tests.
6. Pass `--path <file>` or set `AXEL_REPO_FILE` to use a custom repo list. The CLI accepts
   `--path` before or after the subcommand (see
   `tests/test_repo_manager.py::test_main_add_accepts_path_after_subcommand`).
7. Coverage reports are uploaded to [Codecov](https://codecov.io/gh/futuroptimist/axel) via CI.
8. Add a task with `python -m axel.task_manager add "write docs"`. Tasks are
   saved in `tasks.json` and listed with `python -m axel.task_manager list`.
   Descriptions may include Unicode characters and are stored unescaped using
   UTF-8 for readability.
   Listings show `[ ]` for pending tasks and `[x]` when completed.
9. Remove a task with `python -m axel.task_manager remove 1`.
10. Mark a task complete with `python -m axel.task_manager complete 1`.

## quests

Generate cross-repo quests with `python -m axel.quests --limit 3`. The helper reads
`repos.txt` (or the path supplied via `--path`/`AXEL_REPO_FILE`) and emits deterministic
pairings that highlight how multiple repositories can collaborate on a shared goal. This
module powers the "suggest quests" promise described in the roadmap and is covered by
`tests/test_quests.py::test_suggest_cross_repo_quests_links_repos` and
`tests/test_quests.py::test_cli_prints_suggestions`.
Quests that involve token.place automatically reference `gabriel` to reinforce the
security layer described in `issues/0003-gabriel-security-layer.md`; see
`tests/test_quests.py::test_suggest_cross_repo_quests_mentions_gabriel_for_sensitive_pairs`.
When a token.place server is reachable (for example via `docker compose -f
docker-compose-mock.yml up`), Axel now queries `/api/v1/models` to highlight the
featured model in the quest details. Coverage lives in
`tests/test_token_place.py::test_list_models_parses_openai_like_payload` and
`tests/test_quests.py::test_suggest_cross_repo_quests_enriches_token_place_with_models`,
with graceful fallback behaviour asserted in
`tests/test_quests.py::test_suggest_cross_repo_quests_handles_token_place_errors`.
The roadmap entry for this integration stays checked via
`tests/test_readme.py::test_readme_marks_llm_quests_complete`, and
`tests/test_readme.py::test_readme_marks_gabriel_security_layer_complete` ensures the
gabriel security layer milestone remains marked complete.
11. Clear all tasks with `python -m axel.task_manager clear`.
12. Pass `--path <file>` or set `AXEL_TASK_FILE` to use a custom task list. The task CLI also
    accepts `--path` before or after the subcommand (see
    `tests/test_task_manager.py::test_main_add_accepts_path_after_subcommand`).
13. Empty, invalid, or non-list `tasks.json` files are treated as containing no tasks.
14. Legacy task entries missing the `completed` field default to pending output (see
    `tests/test_task_manager.py::test_main_list_handles_missing_completed_field`).
15. Set `AXEL_DISCORD_ENCRYPTION_KEY` to a Fernet key to encrypt Discord captures on disk.
16. Audit repositories for flywheel workflow coverage with `python -m axel.flywheel --path repos.txt`.
    The command reports missing workflows (lint/tests) so you can align each project with the
    flywheel template. Automated coverage lives in
    `tests/test_flywheel.py::test_evaluate_flywheel_alignment_reports_missing_workflows` and
    `tests/test_flywheel.py::test_main_prints_alignment_summary`.
17. Inspect available token.place models with `python -m axel.token_place --base-url http://localhost:5000/api/v1`.
    This lists the advertised models (using `TOKEN_PLACE_API_KEY` when set) or reports a helpful error
    if the API is unreachable. Coverage lives in
    `tests/test_token_place.py::test_main_prints_models` and
    `tests/test_token_place.py::test_main_reports_errors`.
    The `clients` subcommand continues to support pairing token.place repositories with others in
    your repo list, reusing live model metadata when available. Coverage lives in
    `tests/test_token_place.py::test_plan_client_integrations_generates_pairs`,
    `tests/test_token_place.py::test_plan_client_integrations_reuses_model_metadata`, and
    `tests/test_token_place.py::test_main_clients_prints_plan`.

## quests

Generate cross-repo quests with `python -m axel.quests --limit 3`. The helper reads
`repos.txt` (or the path supplied via `--path`/`AXEL_REPO_FILE`) and emits deterministic
pairings that highlight how multiple repositories can collaborate on a shared goal. This
module powers the "suggest quests" promise described in the roadmap and is covered by
`tests/test_quests.py::test_suggest_cross_repo_quests_links_repos` and
`tests/test_quests.py::test_cli_prints_suggestions`.
Quests that involve token.place automatically reference `gabriel` to reinforce the
security layer described in `issues/0003-gabriel-security-layer.md`; see
`tests/test_quests.py::test_suggest_cross_repo_quests_mentions_gabriel_for_sensitive_pairs`.
The roadmap entry for this integration stays checked via
`tests/test_readme.py::test_readme_marks_llm_quests_complete`.

## local setup

To keep personal notes and repo lists private, set `AXEL_REPO_FILE` to a path
under `local/`, which is ignored by Git. The repo manager creates the directory
automatically if it doesn't already exist. Paths beginning with `~` expand to
the user's home directory. Automated coverage for this behavior lives in
`tests/test_repo_manager.py::test_add_repo_expands_user_home` and
`tests/test_task_manager.py::test_add_task_expands_user_home`.

Example:

```bash
python -m axel.repo_manager add https://github.com/your/private-repo --path local/repos.txt
export AXEL_REPO_FILE=local/repos.txt
git check-ignore -v local/
```

The `git check-ignore` command confirms that `local/` is excluded from version
control.

Start with `examples/local/repos_example.txt` when creating your private repo list.

To store tasks privately, point `AXEL_TASK_FILE` to a file under `local/`:

```bash
python -m axel.task_manager add "write docs" --path local/tasks.json
export AXEL_TASK_FILE=local/tasks.json
```

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
For example, run gabriel alongside token.place and dspace to cross-check repository data
for OSINT insights before sharing.

## API

```python
from axel import add_repo, list_repos, strip_ansi

add_repo("https://github.com/example/repo")
print(list_repos())
strip_ansi("\x1b[2K\x1b[31merror\x1b[0m")  # -> "error"
strip_ansi("\x1b]0;title\x07error")  # OSC sequences removed -> "error"
strip_ansi(b"\x1b[31merror\x1b[0m")  # bytes are accepted
strip_ansi(bytearray(b"\x1b[31merror\x1b[0m"))  # bytearrays are accepted
strip_ansi(memoryview(b"\x1b[31merror\x1b[0m"))  # memoryviews are accepted
strip_ansi(None)  # -> ""
strip_ansi(123)  # raises TypeError for invalid types
```

## discord bot

See [docs/discord-bot.md](docs/discord-bot.md) for running a local Discord bot
that saves mentioned messages to `local/discord/`. The bot exposes a `/axel search`
slash command backed by `axel.discord_bot.search_captures` so you can locate saved
notes without leaving Discord (see
`tests/test_discord_bot.py::test_axel_search_command_replies_with_matches`). Use
`/axel summarize` to condense the first matching capture into a short
description. Coverage spans
`tests/test_discord_bot.py::test_summarize_capture_extracts_message_body`,
`tests/test_discord_bot.py::test_summarize_capture_includes_bullet_message_body`,
`tests/test_discord_bot.py::test_summarize_capture_reads_plaintext_with_encryption_enabled`,
and `tests/test_discord_bot.py::test_axel_summarize_command_replies_with_summary`.
Run `/axel quest` to transform capture metadata into a cross-repo quest powered
by `axel.quests.suggest_cross_repo_quests`. Coverage spans
`tests/test_discord_bot.py::test_axel_quest_command_replies_with_suggestion` and
`tests/test_discord_bot.py::test_axel_quest_command_reports_missing_repositories`.

## publishing

Before flipping this repository to public, search the codebase for accidental credentials.
A quick sanity check is:

```bash
git ls-files -z | xargs -0 grep -i --line-number --context=1 \
  -e token -e secret -e password -e api_key -e api-key
```

Review the output and remove any sensitive data. Make sure `repos.txt` contains only repositories you wish to share.

For staged changes, run:

```bash
git diff --cached | python scripts/scan-secrets.py
```

This helper flags suspicious lines containing keywords like "token", "secret",
"password", or "api key" in the diff before they reach the commit history.

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

## hardware

OpenSCAD source files live in `hardware/cad`. Run `bash scripts/build_stl.sh`
to regenerate matching files in `hardware/stl`.

See [CONTRIBUTING.md](CONTRIBUTING.md) for guidelines on sending pull requests.
This project adheres to the [Code of Conduct](CODE_OF_CONDUCT.md).
For LLM-specific tips see [AGENTS.md](AGENTS.md).
