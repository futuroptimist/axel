# Axel Merge Policy — Foundations from Flywheel and Codex Workflows

## Context

Because Codex tasks can only pull from the remote **once, at kickoff**, each task tree behaves like a **virtual git worktree**. Subsequent follow-ups or fix tasks cannot rebase from remote, so merges happen later via PRs from feature branches into `main`. This design is deliberate: it ensures deterministic runs and clean lineage between Codex task trees.

Over the summer, Futuroptimist improved drastically at diff reading and manual merge resolution, leading to the evolution of a **merge-conflicts prompt doc** in Flywheel — the precursor to what Axel will eventually orchestrate automatically.

This document captures the core design patterns, heuristics, and policy primitives Axel will use once it becomes an autonomous orchestrator for multi-agent repos.

---

## Current Workflow Model

| Stage | Description |
|-------|-------------|
| **1. Codex kickoff** | Task pulls remote once, creating a self-contained virtual worktree. |
| **2. Local task development** | Codex executes within the isolated branch, using static repo context (no new pulls). |
| **3. PR submission** | Human or future agent merges branches into `main` via GitHub PRs, resolving conflicts manually. |
| **4. Merge heuristic application** | The Flywheel merge prompt doc provides guidance and resolution policies. |
| **5. Future automation** | Axel will integrate and execute these merge heuristics automatically. |

---

## Merge Conflict Policy (Conceptual Schema)

```yaml
merge_policy:
  rebase_strategy:
    allow_rebase: true
    prefer_rebase_on_main: true
    auto_abort_on_failed_tests: true

  conflict_resolution:
    priority_rules:
      - pattern: "infra/**"
        resolution: "main_wins"
      - pattern: "cli/**"
        resolution: "feature_wins"
      - pattern: "docs/**"
        resolution: "merge_both"
    heuristics:
      - detect_structural_conflicts: true
      - detect_functional_conflicts: true
      - detect_comment_only_conflicts: true
      - comment_only_conflicts_auto_resolve: true
    fallback: "manual_review"

  safety_checks:
    - type: lint
      command: "flywheel lint"
    - type: test
      command: "pytest --maxfail=1"
    - type: ci
      must_pass: true

  metadata:
    author: "Futuroptimist"
    system: "Axel"
    lineage: "flywheel → codex → axel"
```

---

## Heuristic Layers (from the Flywheel Prompt Doc)

Axel’s future merge logic will evolve through three cognitive layers:

1. **Syntactic Awareness**
   - Detect and reconcile identical or trivial conflict hunks (e.g., comment changes, whitespace).
   - Automatically stage non-functional merges.

2. **Semantic Awareness**
   - Identify renamed arguments, function refactors, or docstring drift.
   - Evaluate merge safety using static analysis + regression heuristics.

3. **Behavioral Awareness** *(Axel v2)*
   - Infer intent behind conflicting code (e.g., both branches improving CLI UX).
   - Choose merges that move the repo closer to the “prompt doc North Star.”

---

## Integration Strategy

To mitigate conflicts before full autonomy:

- Keep **task branches short-lived** — 24h max.
- Use **“checkpoint tasks”** that intentionally rebase from `main` every few runs.
- Merge smaller PRs first to minimize drift.
- Apply **feature toggles** where applicable to merge earlier with behavioral gating.
- Standardize merge commit messages:

  ```
  merge: resolve conflicts between {feature_branch} and main
  policy: flywheel/v1 merge heuristics applied
  ```

---

## Roadmap: Manual → Semi-Agentic → Fully Agentic

| Phase | Responsibility | Description |
|-------|----------------|-------------|
| **Manual** | Human (Futuroptimist) | Copy/paste merge prompt docs into GPT-5 Instant sessions to resolve conflicts. |
| **Semi-Agentic** | Codex | Apply static merge heuristics based on task metadata (non-networked). |
| **Agentic (Axel)** | Axel orchestrator | Pull latest remote state, detect drift, simulate merge outcomes, and apply policies autonomously. |

---

## Future Work

- [x] Convert this doc into `axel/docs/merge_policy.md`.
- [x] Define `axel/policies/merge_policy.yaml` for programmatic enforcement.
- [x] Extend Flywheel’s merge prompt doc with critic self-evaluation and conflict classification
  (see `tests/test_merge.py::test_speculative_merge_classifies_comment_only_conflicts`,
  `tests/test_merge.py::test_speculative_merge_classifies_code_conflicts`,
  `tests/test_critic.py::test_self_evaluate_merge_conflicts_rewards_comment_only`, and
  `tests/test_critic.py::test_self_evaluate_merge_conflicts_detects_code_conflicts`).
- [x] Implement “speculative merge” checks for open Codex branches (see
  `tests/test_merge.py::test_speculative_merge_reports_clean_result` and
  `tests/test_merge.py::test_speculative_merge_reports_conflicts`).
- [x] Develop Axel agent hooks for merge detection and policy enforcement (see
  `tests/test_merge.py::test_plan_merge_actions_auto_resolves_comment_conflicts` and
  `tests/test_merge.py::test_plan_merge_actions_uses_priority_rules`).

Use `axel.merge.plan_merge_actions` to combine `speculative_merge_check` output with the
policy defined in `axel/policies/merge_policy.yaml`. The helper highlights whether conflicts
can be auto-resolved, surfaces file-level resolutions using priority rules, and echoes the
safety checks agents must run before merging.

Run speculative merge analysis locally with:

```bash
python -m axel.merge check --base main --head codex/feature-branch
```

The command uses a temporary git worktree to detect conflicts without modifying
the active checkout.

---

**Provenance:** Derived from Futuroptimist’s summer 2025 merge-workflow reflections, Flywheel’s evolving prompt docs, and Codex task orchestration patterns.
**Purpose:** Foundation for Axel’s future autonomous merge-resolution layer.
