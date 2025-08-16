---
title: 'Hillclimb Prompts'
slug: 'prompts-hillclimb'
---

# Hillclimb Prompts

Combined planner, coder and critique prompts used by Axel's hillclimb mode.

## Plan Prompt

```text
You are a senior maintainer planning a smallest-viable change to satisfy an ACTION CARD.
Output:
1) Minimal plan satisfying acceptance_criteria and constraints.
2) Exact file list to add/change, each with 1–2 line rationale.
3) Risks (API/security/perf) + mitigations.
4) Test plan (commands + cases).
5) Checklist the coder must satisfy.
Respect the touch budget. Prefer smallest possible change that passes CI.
```

## Code Prompt

```text
Implement the PLANNER plan. Rules:
- Respect touch budget (files_max, loc_max). If exceeded, STOP and return.
- Only modify files listed by the planner unless strictly necessary.
- Update docs/tests alongside code.
- Avoid committing credentials or hard-coded API keys.
- Output a unified diff and list of commands to run tests.
```

## Critique Prompt

```text
Self-review:
- Does the diff meet acceptance_criteria? If not, say why and STOP.
- Are lints/tests likely to pass? Note failures with file:line refs.
- Any security/perf regressions? If yes, propose a smaller alternative.
Conclude with PASS or REVISE and a brief rationale.
```

## Example Action Cards

```yaml
# add-pipx-install.yml
key: add-pipx-install
title: Add 1-click pipx install + Quickstart
applies_to: ["f2clipboard", "gitshelves"]
acceptance_criteria:
  - "Published to PyPI with pinned deps"
  - "README top includes 60s Quickstart using pipx"
  - "CI publishes on tag v*"
constraints:
  files_max: 6
  loc_max: 200
must_pass:
  - "pytest -q"
  - "ruff --version || true"
```

```yaml
# docker-compose-mock.yml
key: docker-compose-mock
title: One-command docker compose (relay + server + mock LLM)
applies_to: ["token.place"]
acceptance_criteria:
  - "docker compose up works with no config"
  - "README Quickstart (<=60s) shows compose path"
  - "Release notes mention compose; image published on tag"
constraints:
  files_max: 8
  loc_max: 250
must_pass:
  - "docker --version"
```

More cards live in `.axel/hillclimb/cards/`.
