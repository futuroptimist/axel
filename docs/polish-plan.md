# Axel CLI & Analytics Polish Plan

## Overview
This plan sequences the refactors, persistence upgrades, deterministic sampling features, testing
coverage, documentation refreshes, and developer experience polish required to harden the Axel CLI
while keeping alpha guardrails intact.

## Release Slices & Sequencing
1. **Foundational CLI boundary refactor**
   - Carve the package into three top-level modules: `axel/cli` (argument parsing & UX),
     `axel/repos` (I/O, repo manifest normalization, caching), and `axel/analysis` (metrics
     computation facades).
   - Introduce thin facade classes/functions that expose high-level operations for each command,
     keeping CLI entry points focused on parsing/formatting.
   - Add dependency injection hooks so analysis modules consume repo providers instead of reaching
     directly into filesystem/network code.
   - Include targeted unit tests ensuring the new boundaries preserve existing command behaviors.

2. **Analytics persistence & telemetry groundwork**
   - Implement run record writing beneath `~/.config/axel/analytics/<slug>.json`, capturing inputs,
     metrics, timestamps, CLI version, and sampling metadata.
   - Create a `TelemetryConfig` helper backed by the config directory that stores the opt-in flag,
     consent timestamp, and last upload status.
   - Add `axel config telemetry --enable|--disable` with explicit UX copy describing what data is
     transmitted and reinforcing the default-disabled posture.
   - Wire telemetry checks into analytics flows while keeping dry-run behavior and rejecting uploads
     when opt-in is absent.
   - Extend analytics tests with fixtures verifying persistence artifacts and telemetry gating.

3. **Deterministic sampling for large repo sets**
   - Extend `repos`, `tasks`, and analytics commands with `--sample` and `--seed` flags that accept
     shared defaults.
   - Push sampling choices through repo discovery, task aggregation, and analytics data providers so
     all downstream consumers receive the same filtered set.
   - Document the sampling decision in persistence records and command output (human + `--json`).
   - Add tests covering sampling reproducibility, including multi-process fixtures to ensure
     concurrency safety when persisting analytics runs.

4. **Golden UX polish & CLI outputs**
   - Introduce golden tests for human-readable and JSON outputs across `axel repos`, `axel tasks`,
     and `axel analytics` flows.
   - Ensure every primary command respects `--json` and returns machine-friendly structures.
   - Add shell completion support exposed via `axel --install-completions` and document installation
     in quickstarts.

5. **Documentation & prompt migrations**
   - Update README quickstarts with `pipx install axel`, `pipx ensurepath`, analytics cache details,
     telemetry toggle instructions, deterministic sampling guidance, and jq usage examples.
   - Refresh FAQ entries to surface DX improvements and clarify orthogonality (0–0.3 low overlap,
     0.3–0.7 acceptable, >0.7 high parallelism) and saturation thresholds (<0.4 under-utilized,
     0.4–0.85 healthy, >0.85 slowdown risk) with illustrative scenarios.
   - Move any lingering prompt references into `docs/prompts/codex/`, ensuring navigation and issue
     templates link to the new locations.
   - Capture telemetry defaults, sampling behavior, and documentation updates in the PR body per
     checklist.

6. **Follow-up analytics refinements**
   - Validate orthogonality and saturation math against fixture repos with known metrics; store
     expectations as part of regression tests.
   - Monitor performance implications of persistence and sampling; if needed, iterate on caching
     strategies within `axel/repos` while keeping side effects isolated.

## Data Persistence & Telemetry Considerations
- **Persisted Data:**
  - Analytics inputs (repo list, sampling parameters, command options).
  - Computed metrics (orthogonality, saturation, drift, timestamps, CLI version).
  - Telemetry state (opt-in flag, consent timestamp, last attempted upload metadata).
- **Telemetry UX Copy:**
  - Clearly state telemetry is disabled by default, enumerate the fields sent, and require explicit
    confirmation (`--enable` plus an interactive confirmation prompt or `--yes` flag for scripting).
  - Provide reassurance that disabling telemetry (`--disable`) halts uploads immediately and deletes
    pending queues.
- **Thin Boundaries:**
  - CLI modules remain responsible for parsing, validation, and formatting only; they delegate to
    facades that wrap repos and analysis layers.
  - Repos layer centralizes filesystem/network operations, exposing pure data providers.
  - Analysis layer focuses on computations, consuming dependency-injected providers to stay
    test-friendly.

## Testing Additions
- Golden output tests for `repos`, `tasks`, and analytics commands (text + JSON).
- Repo normalization tests spanning https/ssh URLs, `.git` suffix handling, and casing differences.
- Analytics metric verification using fixture repos with predetermined orthogonality/saturation
  values.
- Persistence tests ensuring analytics runs write the correct JSON schema and remain race-safe under
  concurrent execution.
- Telemetry config tests covering enable/disable flows, confirmation prompts, and behavior when
  telemetry is disabled.
- Deterministic sampling tests verifying seeded reproducibility across commands and persistence
  records.
- Concurrency fixtures exercising sampling plus persistence to guard against write collisions.

## Documentation Updates
- README quickstart (pipx install + ensurepath, completions, telemetry toggle, analytics cache path,
  deterministic sampling guidance, jq snippets).
- FAQ additions for DX notes, orthogonality interpretation, saturation thresholds, and telemetry
  expectations.
- Analytics documentation detailing persistence location, JSON schema, and sampling implications.
- Prompt documentation cleanup consolidating everything under `docs/prompts/codex/` with refreshed
  links (hillclimb, README, issue templates, navigation).
- New or updated developer guides noting required checks (`flake8`, `pytest --cov`, `pre-commit`,
  credential scan) per PR checklist.

## User-Visible Improvements
- Clearer CLI command boundaries that yield faster, more maintainable UX iterations.
- Persistent analytics history enabling trend analysis and reproducible diagnostics.
- Deterministic sampling options that make large repo runs predictable and scriptable.
- Consistent `--json` support plus shell completions, smoothing automation and onboarding.
- Expanded documentation that explains analytics metrics, sampling impacts, telemetry defaults, and
  setup steps, improving contributor confidence in the tooling.
