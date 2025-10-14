# Axel CLI & Analytics Polish Plan

## Overview
This plan sequences the CLI refactor, analytics persistence, deterministic sampling, broadened tests,
documentation refresh, and developer-experience polish into focused, reviewable pull requests. Every
slice keeps the CLI/repo/analysis boundaries thin, honors alpha guardrails (dry runs by default,
explicit telemetry opt-ins), and lands with the required checks (`flake8`, `pytest --cov`,
`pre-commit`, credential scan) ahead of review.

### Goals at a Glance
- Deliver a modular CLI (`axel/cli`, `axel/repos`, `axel/analysis`) that isolates argument parsing and
  presentation from data access and analytics math.
- Persist analytics runs, provide an explicit telemetry opt-in toggle, and document outbound fields
  before any upload attempts.
- Offer seeded sampling to keep large repo sets reproducible across repos, tasks, and analytics flows.
- Extend automated coverage (golden outputs, normalization, analytics math, persistence, telemetry,
  concurrency) and refresh docs/prompts so contributors and users understand the new behaviors.

### Release Stream
| PR | Theme | Implementation Slices | QA & Docs Hooks |
| --- | --- | --- | --- |
| 1 | Module boundary realignment | Reshuffle packages, introduce CLI facades, wire providers | Regression tests for dry runs/auth errors; update import paths |
| 2 | Persistence & telemetry | Analytics run ledger, telemetry config store, UX copy | Persistence round-trip tests; telemetry enable/disable tests; doc stub |
| 3 | Deterministic sampling | Shared `--sample/--seed` flags, propagated metadata | Reproducibility tests; concurrency fixtures; persisted sampling metadata |
| 4 | CLI UX polish | Golden outputs, `--json` parity, shell completion plumbing | Golden fixtures; completion generation tests; UX copy review |
| 5 | Analytics math validation | Fixture repos, orthogonality/saturation baselines | Metric assertions; performance smoke notes |
| 6 | Docs & prompt migration | README/FAQ refresh, analytics docs, prompt link updates | Docs lint (if any), cross-link verification, PR summary call-outs |

## Release Slices & Sequencing
1. **Module boundary realignment**
   - Carve the package into `axel/cli`, `axel/repos`, and `axel/analysis` namespaces with explicit
     facades so the CLI layer is limited to argument parsing, option validation, and output formatting.
     Providers are injected, keeping analytics ignorant of filesystem/network effects.
   - Add adapters translating CLI options into repository-provider requests while preserving guardrail
     behaviors (dry run defaults, telemetry off). Document import path updates for contributors.
   - Backfill regression tests that pin current command flows (auth failure messaging, missing repo
     manifests) to catch behavioral drift during the move.

2. **Persistence & telemetry groundwork**
   - Persist analytics runs beneath `~/.config/axel/analytics/<slug>.json`, capturing inputs, sampling
     parameters, metrics, CLI version, timestamps, exit status, and telemetry state. Include schema
     versioning for forward compatibility.
   - Introduce a `TelemetryConfig` helper storing opt-in flag, consent timestamp, consent text hash,
     last upload attempt, and pending payload identifiers.
   - Ship `axel config telemetry --enable|--disable[--status][--yes]` with UX copy that explains the
     default-off posture, enumerates outbound fields, and requires confirmation unless `--yes` is
     supplied for automation. Block uploads until consent is explicit.
   - Extend analytics flows to respect telemetry state, retry persistence with actionable errors, and
     surface telemetry state in `--json` output. Cover these paths with integration tests.

3. **Deterministic sampling rollout**
   - Add shared `--sample` and `--seed` flags to `axel repos`, `axel tasks`, and `axel analytics`.
     Ensure the filtered set flows through repo discovery, task aggregation, and analytics providers so
     downstream consumers observe the identical subset.
   - Annotate human-readable and JSON outputs with sampling decisions, and embed sampling metadata in
     persisted analytics records for auditing. Expose sampling knobs to analytics persistence and
     telemetry payloads.
   - Add reproducibility tests (seeded runs produce stable selections), concurrency fixtures that
     stress simultaneous persistence writes, and regression coverage for dry-run guardrails.

4. **CLI UX polish & golden coverage**
   - Capture golden fixtures for the main commands (`repos`, `tasks`, analytics subcommands) covering
     both text and `--json` modes. Assert that `--json` switches exist everywhere and keep output keys
     consistent.
   - Refine error messaging for missing GitHub auth or repo manifests, ensure dry-run messaging stays
     prominent, and improve exit codes where necessary.
   - Wire `axel --install-completions` to generate shell completion scripts (bash/zsh/fish) and verify
     they install cleanly. Document the workflow in quickstarts.

5. **Analytics math validation**
   - Build fixture repositories (or synthetic commit histories) with predetermined orthogonality and
     saturation outcomes so assertions cover low/medium/high overlap scenarios, saturation thresholds,
     and drift cases.
   - Profile analysis performance before/after persistence and sampling updates. If overhead appears,
     capture benchmark notes in the PR description for reviewer context.

6. **Documentation, prompts, and DX updates**
   - Update README quickstarts, FAQ, and analytics docs with `pipx install axel`, `pipx ensurepath`,
     shell completion setup, telemetry defaults, sampling behavior, analytics cache paths, and jq
     automation examples.
   - Provide concrete orthogonality guidance (0–0.3 overlap low, 0.3–0.7 acceptable, >0.7 strong
     parallelism) and saturation thresholds (<0.4 under-utilized, 0.4–0.85 healthy, >0.85 slowdown
     warnings) with real task comparisons and seeded sampling context.
   - Ensure all prompts—including hillclimb references—live under `docs/prompts/codex/`, refresh links
     across README, hillclimb docs, issue templates, and navigation, and note the migration plus link
     fixes in the PR summary as required.
   - Capture telemetry defaults, sampling expectations, and documentation changes explicitly in PR
     bodies per the migration checklist, and remind contributors about mandatory pre-review checks.

## Data Persistence & Telemetry Details
- **Persisted analytics payloads:** repo identifiers (normalized URLs, applied overrides), sampling
  inputs (size, seed, filters), command variant, computed metrics, CLI version, runtime timestamps,
  exit status, telemetry opt-in snapshot, and file integrity hashes for persisted artifacts.
- **Telemetry ledger:** opt-in flag, consent text hash/version, confirmation timestamp, last upload
  attempt timestamp/status, identifiers for eligible analytics runs, and a rolling nonce to prevent
  duplicate uploads.
- **UX copy requirements:** emphasize telemetry is disabled by default, list outbound fields before
  enabling, provide `--disable` for immediate revocation, surface `--status` to audit consent, and
  require confirmation unless `--yes` is set for CI.
- **Thin boundaries:** keep the CLI as an orchestrator; `axel/repos` owns filesystem/network I/O and
  caching; `axel/analysis` consumes provider interfaces for deterministic computation; telemetry hooks
  live in a shared services layer invoked by CLI facades after analytics execution.

## Automated Test Additions
- Golden output comparisons for `repos`, `tasks`, and analytics commands (text and JSON modes).
- Repo normalization tests covering https vs. ssh, `.git` suffixes, case variations, and overrides.
- Analytics metric assertions using fixture repos with known orthogonality/saturation baselines plus
  regression tests for drift detection.
- Persistence schema tests (round-trip + schema versioning) and race-condition simulations across
  processes writing to the analytics cache.
- Telemetry enable/disable/status flow tests, including confirmation prompts, `--yes` automation, and
  disabled-upload guarantees.
- Deterministic sampling reproducibility tests across commands, persisted records, and telemetry logs.
- Regression suites that guard dry-run behavior, error messaging, shell completion generation, and
  JSON parity.

## Documentation & Prompt Updates
- README, quickstarts, and FAQ updates covering installation via `pipx`, path setup, shell completion
  installation, telemetry defaults, analytics cache paths, sampling behavior, and jq automation
  examples for persisted analytics JSON.
- Analytics docs detailing orthogonality/saturation interpretation, seeded sampling impacts, telemetry
  safeguards, persistence schema, and examples showing JSON-to-jq workflows.
- Prompt migrations consolidated under `docs/prompts/codex/` with refreshed cross-links (README,
  hillclimb docs, issue templates, navigation). Call out the new prompt location and updated links in
  the PR summary.
- Contributor guidance capturing the mandatory checks (`flake8 axel tests`, `pytest --cov=axel --cov=tests`,
  `pre-commit run --all-files`, stage-aware credential scanning via the repository's leak-detection helper) plus telemetry/sampling
  narratives expected in PR bodies.

## Expected User-Visible Improvements
- Cleaner CLI architecture that makes command behaviors more predictable and easier to extend.
- Persistent analytics history for trend analysis, complete with transparent telemetry controls that
  respect the default-off policy.
- Deterministic sampling that keeps large runs fast, reproducible, and clearly annotated in outputs
  and persisted artifacts.
- Consistent `--json` support, sharper error messaging, and shell completions that improve scripting
  and onboarding workflows.
- Documentation and prompts that surface metric explanations, guardrails, and DX tips where users look
  first, reducing guesswork for both contributors and operators.
