# Axel FAQ

This FAQ captures quick answers for new contributors and reinforces Axel's alpha status.
For context on how this page stays linked from the README see
`tests/test_readme.py::test_readme_includes_alpha_status_and_supporting_docs`.

## Is Axel production ready?

Not yet. Axel is in **alpha**, so expect rapid changes and occasional rough edges. See
[Known Issues & Footguns](KNOWN_ISSUES.md) before using the automation on critical repositories.

## Where should I start?

Follow the [Quickstart](../README.md#quickstart-60s) and review the roadmap in the README.
When in doubt, run `pre-commit run --all-files` to mirror the CI checks documented in
`docs/prompts/codex/implement.md`.

## How do I report ideas or bugs?

Open an item under `issues/` or file a GitHub issue so it feeds the questing workflow. Be sure to
reference any captures saved by the Discord bot when the improvement spans multiple repositories.
