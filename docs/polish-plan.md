# Axel CLI & Analytics Polish Plan

## Overview
This plan sequences the CLI boundary refactor, analytics persistence, deterministic sampling,
expanded test coverage, documentation refresh, and developer-experience polish into focused pull
requests. Each slice keeps guardrails intact, preserves thin module dependencies, and lands with the
required checks (`flake8`, `pytest --cov`, `pre-commit`, credential scan) before review.

### Goals at a Glance
- Deliver a modular CLI (`axel/cli`, `axel/repos`, `axel/analysis`) that keeps orchestration thin and
  testable.
- Persist analytics runs, expose an explicit telemetry opt-in toggle, and document outbound data.
- Provide seeded sampling so large repo sets remain reproducible across repos, tasks, and analytics.
- Maintain comprehensive test coverage (CLI golden files, normalization, analytics math,
  persistence, telemetry, concurrency) and refresh docs/prompts to guide contributors.

### PR Stream
| PR | Focus | Key Deliverables |
| --- | --- | --- |
| 1 | Module boundary realignment | Package reshuffle, CLI facade adapters, regression tests |
| 2 | Persistence + telemetry | Analytics persistence, telemetry CLI UX, opt-in schema + tests |
| 3 | Deterministic sampling | Shared sampling flags, metadata propagation, reproducibility tests |
| 4 | CLI UX polish | Golden outputs, error messaging, `--json` parity, shell completions |
| 5 | Analytics math validation | Fixture repos, metric assertions, performance notes |
| 6 | Docs & prompts | README/FAQ refresh, telemetry/sampling docs, prompt link migrations |

## Release Slices & Sequencing
1. **Module boundary realignment**
   - Restructure the package into `axel/cli`, `axel/repos`, and `axel/analysis` namespaces with
     explicit facades. Keep the CLI layer limited to argument parsing, option validation, and output
     formatting while delegating work to injected services from the repos and analysis layers.
   - Introduce adapters that translate CLI options into repository-provider requests, ensuring
     analytics never touch filesystem/network code directly.
   - Backfill unit tests that pin existing command behaviors (e.g., dry-run defaults, auth failure
     messaging) to catch regressions during the move.

2. **Persistence + telemetry groundwork**
   - Implement analytics run persistence beneath
     `~/.config/axel/analytics/<slug>.json`, capturing inputs, sampling parameters, metrics, CLI
     version, timestamps, and command variants.
   - Add a `TelemetryConfig` helper storing opt-in state, consent timestamps, and last upload
     metadata. Build `axel config telemetry --enable|--disable` with explicit UX copy that explains
     default-off behavior, enumerates transmitted fields, and requires interactive confirmation (or a
     `--yes` bypass for CI).
   - Extend analytics flows to read telemetry state, short-circuit uploads when disabled, and record
     persistence failures with actionable error messages.
   - Cover persistence schema, telemetry toggles, and dry-run protection with integration tests.

3. **Deterministic sampling rollout**
   - Add shared `--sample` and `--seed` flags to `axel repos`, `axel tasks`, and `axel analytics`,
     flowing the filtered set through repo discovery, task aggregation, and analysis providers so all
     downstream consumers observe the same subset.
   - Document sampling decisions in human-readable output and `--json` payloads, and embed sampling
     metadata in persisted analytics records.
   - Add reproducibility tests (seeded runs yield identical selections) plus concurrency fixtures to
     ensure multi-process analytics writes remain race-safe.

4. **CLI UX polish & golden tests**
   - Introduce golden fixtures for primary commands covering default text output and `--json` modes,
     and verify `--json` support exists on repos, tasks, and analytics entry points.
   - Harden error messaging (missing GitHub auth, absent repo manifests) and ensure dry-run guardrails
     stay prominent.
   - Add shell completion plumbing exposed via `axel --install-completions` and surface generated
     scripts in the docs and quickstarts.

5. **Analytics math validation**
   - Build fixture repositories with predetermined orthogonality and saturation scores to assert
     analytic correctness, including regression tests for edge cases (high overlap, sparse activity,
     drift scenarios).
   - Profile the refactored analysis layer; if persistence or sampling adds overhead, record baseline
     vs. post-change metrics to justify optimizations.

6. **Documentation, prompts, and DX updates**
   - Update README quickstarts, FAQ, and analytics docs with `pipx install axel`, `pipx ensurepath`,
     shell completion instructions, telemetry defaults, sampling behavior, analytics cache paths, and
     jq automation examples.
   - Explain orthogonality (0–0.3 low overlap, 0.3–0.7 acceptable, >0.7 strong parallelism) and
     saturation thresholds (<0.4 under-utilized, 0.4–0.85 healthy, >0.85 slowdown warnings) with
     concrete task comparisons.
   - Ensure all prompt references live under `docs/prompts/codex/`, refresh links across the README,
     hillclimb docs, issue templates, and navigation, and highlight the new prompt location in the PR
     summary.
   - Capture telemetry defaults, sampling expectations, and documentation updates within PR bodies as
     mandated by the migration checklist.

## Data Persistence & Telemetry Details
- **Persisted analytics payloads:** repo list identifiers, normalization metadata, sampling inputs
  (size, seed, filters), executed command, computed metrics, CLI version, timestamps, exit status,
  and telemetry opt-in state at execution time.
- **Telemetry ledger:** opt-in flag, consent text hash/version, confirmation timestamp, last upload
  attempt, success/failure codes, a rolling identifier for pending uploads, and audit entries that
  record which analytics runs were eligible for upload.
- **UX copy requirements:** reinforce that telemetry is disabled by default, enumerate outbound
  fields before enabling, provide `--disable` to revoke consent immediately, surface a `--status`
  view for transparency, and prompt for confirmation unless `--yes` is specified for automation.
- **Thin boundaries:** CLI modules remain pure orchestrators; repos handle filesystem/network I/O and
  caching; analysis only consumes abstract providers, making metric computations deterministic and
  test-friendly while keeping telemetry hooks centralized.

## Automated Test Additions
- Golden output comparisons for repos/tasks/analytics (text + JSON modes).
- Repo normalization coverage across https vs. ssh, `.git` suffixes, and case variations.
- Analytics metric assertions using fixture repos with known orthogonality/saturation values.
- Persistence schema tests and race-condition simulations for concurrent analytics writes.
- Telemetry enable/disable flow tests, including confirmation prompts and non-interactive `--yes`
  usage.
- Deterministic sampling reproducibility checks across commands and persisted records.
- Regression suites guarding dry-run behavior, error messaging, and shell completion generation.

## Documentation & Prompt Updates
- README and FAQ refreshes capturing new installation steps (`pipx install axel`, `pipx ensurepath`,
  shell completion setup), sampling mechanics, telemetry defaults, analytics cache paths, and jq
  automation examples.
- Analytics-focused docs outlining persistence locations, JSON schema, telemetry safeguards, and
  sampling implications, plus examples showing how seeded runs influence orthogonality/saturation
  interpretation.
- Prompt migrations consolidated under `docs/prompts/codex/` with updated cross-links in the README,
  hillclimb guide, issue templates, docs navigation, and any automation referencing prior paths.
- Contributor notes emphasizing required pre-review checks (`flake8`, `pytest --cov`, `pre-commit`,
  the repository's credential scanning tooling run on staged diffs) to keep trunk green and telemetry
  narratives consistent across PR bodies.

## Expected User-Visible Improvements
- Cleaner CLI architecture enabling faster UX tweaks and more predictable behavior.
- Persistent analytics history for trend analysis, plus transparent telemetry controls that respect
  opt-in defaults.
- Deterministic sampling that keeps large runs fast, reproducible, and clearly documented in outputs
  and persisted artifacts.
- Consistent `--json` support, sharper error messaging, and shell completions that enhance scripting
  and onboarding workflows.
- Documentation and prompts that explain metrics, guardrails, and DX tips where users look first.
