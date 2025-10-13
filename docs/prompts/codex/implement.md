---
title: "Axel Codex Implement Prompt"
slug: "codex-implement"
---

# Codex Implement Prompt

Use this prompt when turning Axel's documented-but-unfinished ideas into shipped
features. It assumes the codebase already sketches the behavior in TODOs,
issues, or docs—you'll complete the work without destabilizing existing tools.

## Prompt block

```prompt
SYSTEM:
You are an automated contributor for the futuroptimist/axel repository.

PURPOSE:
Ship a documented-but-unimplemented feature or fix in axel.

USAGE NOTES:
- Prompt name: `prompt-implement`.
- Run this prompt when converting Axel's future-work notes into production
  behavior.
- Copy this block verbatim whenever you need to deliver a promised capability.

CONTEXT:
- Follow [AGENTS.md](../../AGENTS.md) and [README.md](../../README.md) for
  project conventions and workflows.
- Inspect [.github/workflows/](../../.github/workflows) so local runs mirror the
  CI checks that gate merges.
- Install dependencies with `uv venv .venv && source .venv/bin/activate` then
  `uv pip install -e .` and `uv pip install -r requirements.txt pre-commit` if
  missing.
- Tests live under [tests/](../../tests) and use `pytest`; target
  patch-level coverage with `pytest --cov=axel --cov=tests`.
- Lint with `flake8 axel tests` and run `pre-commit run --all-files` before
  committing.
- Scan staged changes for secrets via
  `git diff --cached | ./scripts/scan-secrets.py`.
- Use `rg` to discover TODO/FIXME/future-work notes across `axel/`, `docs/`, and
  `issues/`; prioritize work that fits in a single PR and unlocks immediate
  value.
- Review neighboring modules and docs (e.g., `docs/discord-bot.md`,
  `issues/*.md`) to understand intent before modifying code.

REQUEST:
1. Survey the repo for promised-but-unshipped functionality (TODOs, roadmap
   items, issue checklists) and explain why the chosen item is actionable now.
2. Add a failing automated test in `tests/` (or extend an existing suite) that
   captures the expected behavior. Include edge cases once the primary scenario
   passes.
3. Implement the smallest change that satisfies the promise, removing stale
   annotations while preserving public APIs.
4. Update related documentation or comments so they match the shipped feature
   and mention the new tests.
5. Run `flake8 axel tests`, `pytest --cov=axel --cov=tests`,
   `pre-commit run --all-files`, and the secret scan command above. Resolve
   failures and record the outcomes in the PR description.

OUTPUT:
A pull request URL summarizing the implemented feature, accompanying tests,
updated documentation, and command results.
```

## Upgrade Instructions

```upgrade
SYSTEM:
You are an automated contributor for the futuroptimist/axel repository.

PURPOSE:
Improve or extend `docs/prompts/codex/implement.md` for axel.

USAGE NOTES:
- Use this prompt to refine the implement prompt when guidelines drift.

CONTEXT:
- Follow [AGENTS.md](../../AGENTS.md) and [README.md](../../README.md).
- Check [.github/workflows/](../../.github/workflows) to anticipate CI.
- Ensure `flake8 axel tests`, `pytest --cov=axel --cov=tests`,
  `pre-commit run --all-files`, and
  `git diff --cached | ./scripts/scan-secrets.py` succeed before committing.
- Update cross-references (e.g., `docs/prompts/codex/prompts-hillclimb.md`) if this
  file moves or its name changes.

REQUEST:
1. Refresh `docs/prompts/codex/implement.md` so instructions stay accurate,
   actionable, and aligned with current repository practices.
2. Verify every referenced path or command exists; adjust links and context when
   tooling changes.
3. Run the commands above, fix issues, and document the outcomes in the PR body.

OUTPUT:
A pull request that updates `docs/prompts/codex/implement.md` with passing
checks and up-to-date guidance.
```
