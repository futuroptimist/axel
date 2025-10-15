---
title: 'Codex Polish Plan'
slug: 'polish'
---

# Codex Polish Prompt

Use this prompt when you are ready to ship CLI polish and repo-analysis upgrades for Axel.

## Prompt

```prompt
SYSTEM:
You are an automated contributor for the futuroptimist/axel repository.

PURPOSE:
Implement polish-focused improvements that elevate the CLI user experience and sharpen
repo-analysis accuracy while honoring the product's alpha-stage guardrails. Each response should
land a reviewable slice of real functionality rather than a meta-plan.

SNAPSHOT:
- CLI entry points:
  - `axel repos …` handles discovery, tagging, and hygiene for entries sourced from `repos.txt`.
  - `axel tasks …` provides prioritization, filtering, and assignment summaries for collaborators.
  - Analytics live under `axel analytics …` (orthogonality, saturation, drift) and reuse the repo &
    task data without their own cache.
- Repo list management:
  - `repos.txt` is the canonical inventory; commands expect normalized URLs and allow overrides via
    `AXEL_REPO_FILE` or `--repos`.
- Alpha guardrails:
  - Hillclimb and analytics flows default to dry runs and require explicit flags for branch writes or
    telemetry.
  - Commands halt safely when GitHub auth or repo manifests are missing.

IMPLEMENTATION TRACKS:
- Modular CLI boundaries:
  - Split functionality into `axel/cli` (argument parsing & UX), `axel/analysis` (metrics such as
    orthogonality, saturation, time-to-green), and `axel/repos` (I/O, normalization, caching).
  - Keep dependencies thin: the CLI invokes facades, analysis consumes repo data providers, and the
    repos layer owns filesystem/network effects. Refactors should ship incrementally with behaviour
    parity tests.
- Analytics persistence & telemetry:
  - Persist each analytics run (inputs, metrics, timestamps) beneath
    `~/.config/axel/analytics/<slug>.json`.
  - Provide an opt-in telemetry toggle (`axel config telemetry --enable|--disable`) documenting what
    leaves the machine; default to disabled and require explicit confirmation before uploads.
  - Capture migrations for existing config files and include smoke tests to prevent regressions.
- Deterministic sampling for large repo sets:
  - Offer seeded sampling flags (e.g., `--sample 50 --seed 2025`) to keep large runs fast yet
    reproducible and propagate the sampling decision across repos, tasks, and analytics.
  - Ensure sampling choices are persisted alongside analytics runs and surfaced in UX copy.

TEST STRATEGY:
- Add golden tests for CLI output covering human-readable and `--json` modes.
- Validate repo URL normalization across https/ssh, `.git` suffixes, and case differences.
- Verify analysis math using fixture repos with known orthogonality/saturation scores.
- Exercise concurrency safety so sampling + persistence avoids race conditions (multi-process
  fixtures, temporary dirs).
- Extend regression tests whenever behaviour changes; avoid test-only PRs by pairing fixes with
  coverage.

DOCUMENTATION TASKS:
- Explain how to interpret orthogonality (0–0.3 overlap, 0.3–0.7 acceptable, >0.7 strong parallelism)
  with concrete examples (e.g., two tasks sharing 80% of touched files vs disjoint ownership).
- Describe saturation thresholds (<0.4 under-utilized, 0.4–0.85 healthy, >0.85 slowdown warnings) and
  how deterministic sampling influences these readings.
- Update quickstarts with `pipx install axel`, `pipx ensurepath`, and shell completion setup.
- Document analytics cache location, telemetry toggles, and provide JSON-to-jq automation examples.
- Keep prompt references, README links, and FAQ snippets in sync with each shipped capability.

DEVELOPER EXPERIENCE POLISH:
- Ensure `repos`, `tasks`, and analytics commands accept `--json` outputs for scripting.
- Publish shell completion installation steps via `axel --install-completions`
  (see `tests/test_cli.py::test_cli_install_completions_command`).
- Capture DX notes inside README/FAQ so contributors discover them quickly.

MIGRATION & PR CHECKLIST:
- Move prompt docs into `docs/prompts/codex/` and refresh links (hillclimb, README, issue templates,
  nav entries).
- Include this `docs/prompts/codex/polish.md` file and link fixes in the PR summary.
- Record telemetry defaults, sampling behavior, and documentation changes in the PR body.
- Run `flake8 axel tests`, `pytest --cov=axel --cov=tests`, `pre-commit run --all-files`, and the
  staged-diff safety scan from `scripts/`; resolve failures before requesting review.

REQUEST:
1. Ship a narrow, production-quality polish improvement drawn from the tracks above (or their
   follow-on tasks) with a clear before/after summary.
2. Explain how data persistence, telemetry toggles, and sampling behaviour are exercised by the
   change, documenting UX copy where needed.
3. Add or update automated tests and documentation so they reflect the shipped behaviour.
4. Summarize the user-visible impact across CLI ergonomics, analytics accuracy, and repo hygiene.

OUTPUT:
A PR-ready implementation that lands code, tests, and documentation updates aligned with the polish
goals, plus a summary that calls out telemetry defaults, sampling behaviour, and prompt link health.
```

## Upgrade Prompt

Run this prompt when the primary polish prompt needs refinement.

```upgrade
SYSTEM:
You are an automated contributor for the futuroptimist/axel repository.

PURPOSE:
Improve `docs/prompts/codex/polish.md`, with emphasis on keeping the primary prompt focused on
shipping impactful polish work.

SCOPE & CONTEXT:
- Follow [AGENTS.md](../../AGENTS.md), [README.md](../../README.md), and the repo's CI workflows.
- Keep migration guidance aligned with other prompts under `docs/prompts/codex/`.

REQUEST:
1. Audit the primary prompt for accuracy, clarity, and completeness; revise or expand sections that
   drift from current architecture, telemetry, or testing practices.
2. Update cross-references, links, and command lists to match the repository's latest structure and
   tooling.
3. Ensure the prompt keeps contributors shipping functional increments instead of meta-plans.
4. Run `flake8 axel tests`, `pytest --cov=axel --cov=tests`, `pre-commit run --all-files`, and the
   staged-diff safety scan from `scripts/`; document outcomes in the PR body.

OUTPUT:
A pull request that refreshes `docs/prompts/codex/polish.md`, particularly the primary prompt, while
passing required checks and keeping linked resources current.
```
