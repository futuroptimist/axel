# Synthetic local lifecycle foundation

This experiment implements immutable observations, explicit local SQLite storage,
and a pure advisory readiness reducer. Use **invented data only**. It is not a
production ledger, executor, authentication system, online board or recovery tool.
Nothing imports it from the existing entry points or package exports. Legacy task
storage remains unchanged.

The modules extend the record boundaries in the
[chat operations contract](chat-operations-contract.md) and the identity/evidence
rules in the [sanitized kanban contract](sanitized-kanban-contract.md). They do not
implement the [backup/restore contract](resumable-backup-contract.md), replace its
codec, or enable either a sensitive profile or an online integration.

## Records and identity

`lifecycle_records.py` defines frozen `TaskRevision`, `Attempt`, `Evidence`,
`Dependency`, `ReviewDecision`, `Transition` and `OperationReceipt` values. Nested
collections are immutable tuples with exact element types. IDs are caller-supplied
opaque values, independent of title, content and timestamp. A record observation,
task revision, attempt, artifact and external source execution have separate IDs.

Every observation has a versioned envelope: workspace/profile, task/revision,
input and contract digests, subject, environment, source/event/revision/status,
UTC source and observation times, correlation/causation and audience-policy
reference. Task records retain requester/owner, project digest, fixed action
profile, required capabilities, harness, execution state, board column and deadline.
Approval and delivery fields are **references only** to the existing contracts;
there is no new approval registry or consumption operation.

Only local scope is supported. Cross-profile records, missing task revisions,
inconsistent bindings and duplicate record IDs fail. Task revisions must be
contiguous. Required PR identities, checks and reviewers cannot shrink in this
slice. A changed head, input, contract or requirement needs a new task revision
and new evidence. Removing requirements needs a later, separately designed policy
operation; it cannot be used as a shortcut to completion.

The bounded canonical JSON encoding preserves exact signed 64-bit integers,
strings, booleans and null. It uses UTF-8, sorted keys and no insignificant
whitespace. It does not normalize Unicode. Floats (including NaN), arbitrary
objects, duplicate keys, unknown fields, noncanonical encodings and excessive
nesting fail. This is an internal experimental record encoding, not a backup wire
format. URLs and source text remain inert strings.

## Explicit storage and atomic append

`LifecycleStore.initialize_new(path, scope)` exclusively creates a new file and
refuses existing files or journal sidecars. `open_existing(path, scope)` never
creates, repairs or migrates storage. Missing, corrupt, incompatible or mismatched
storage raises `RecoveryRequired`. Rejected opens leave bytes untouched in the
tested cases. UNC/network-share paths are rejected. Filesystem mounts, permissions
and OS containment still require separate qualification.

The adapter verifies its fixed schema, application/schema version, foreign keys,
`DELETE` journal mode and `FULL` synchronous mode. Extension loading is disabled.
It accepts typed append commands, not SQL or callbacks. Private implementation
attributes are not a sandbox against hostile Python running in the same process.

An `Append` includes a principal label, operation key, expected complete ledger
revision, sorted expected task revisions and one bounded tuple of records. Every
touched task needs an expected revision (zero means absent). One `BEGIN IMMEDIATE`
transaction validates the current history and candidate graph, then writes records,
task heads, audit, metadata and the receipt. Separate connections serialize writers;
the default lock wait is 250 ms, configurable from zero through two seconds.
There is no unbounded retry loop.

Idempotency is scoped to workspace/profile, principal, operation kind and key. The
digest binds every encoded record and the original expected revisions. The same
key and exact payload return the original receipt even after later commits. A
changed payload conflicts; a new key with stale expectations conflicts. Receipts
never contain cached current readiness, and they have no expiry or pruning.

On an uncertain commit, reconcile with the **original command and key** after
reopening; never make a fresh key to bypass uncertainty. Failure before commit
rolls back the transaction in tested cases. The fault-injection seam is an internal
no-op method patched only by tests, not an execution interface. New opens refuse
journal sidecars rather than attempting automatic recovery; opening during an
active writer may therefore require retry after that writer finishes. This is a
conservative experimental restriction, not a journal-recovery implementation.

Reads check counts and encoded sizes before loading payloads, revalidate immutable
history, compare task projections, and reconcile operation/audit digests and record
membership. These detect the tested accidental corruptions. An attacker replacing
both content and checksums is outside the claim; no trusted freshness anchor,
tamper resistance, encryption or secure deletion is provided.

| Experimental budget | Limit |
| --- | ---: |
| One encoded record or operation descriptor | 64 KiB |
| Records per append | 64 |
| Retained records | 10,000 |
| Cumulative encoded record payload | 16 MiB |
| Cumulative encoded operation descriptors | 16 MiB |
| Tasks in the dependency graph | 256 |
| Current dependency edges | 1,024 |
| Longest dependency path, counting tasks | 32 |
| Physical file accepted by open-existing | 64 MiB |

Capacity rejection never truncates history. Logical byte budgets do not describe
SQLite page/index/journal overhead or peak memory. The implementation deliberately
revalidates the bounded complete history; it is not an online service engine.

One synthetic measurement used a single invented task plus inert transitions,
appended in batches of 64. Sizes below are bytes and are observations, not bounds:

| Records | Encoded records | Operation descriptors | Closed SQLite file | Largest sampled journal | Peak traced Python heap |
| ---: | ---: | ---: | ---: | ---: | ---: |
| 64 | 42,505 | 4,525 | 86,016 | 37,448 | 259,181 |
| 256 | 168,767 | 18,105 | 237,568 | 37,448 | 1,075,730 |

Journal samples were taken at append checkpoints. Python `tracemalloc` excludes
SQLite native allocations, OS page cache and other process memory. These small
measurements do not qualify maximum-capacity performance or power-loss durability.

## Advisory readiness

`evaluate(snapshot, task_id, expected_ledger_revision=..., now=..., policy=...)`
performs no I/O and reads no system clock. It accepts an explicit UTC-aware
`datetime`; naive or local-wall clocks return `AMBIGUOUS_TIME`. A caller must
resolve working-hour intervals to UTC with its timezone/DST rules before calling.
Policy windows are start-inclusive/end-exclusive. Explicit cutoff and deadline
instants are inclusive: the exact instant blocks. Policy expiry blocks at expiry.

The result includes sorted stable blocker codes, the evaluated ledger/task
revisions, execution state, board column, merge state and accepted stage.
`advisory_ready` and `accepted_stage` are **synthetic observations**, never grants.
`grants_authority` is always false in evaluator results. Claimed human names and
policy versions are not authenticated. A real integration must establish their
provenance independently and recheck current policy at use.

- CI binds the exact repository/PR/head, workflow/run/attempt/job, task revision,
  input/contract, environment and subject. External CI has no fabricated local
  attempt. Unknown, failed, skipped, cancelled, stale or future required evidence
  blocks readiness.
- Conflicting observations require explicit, matching supersession. A later
  unrelated success cannot hide a failed check. Supersession preserves history,
  requires the same source/channel/binding and cannot regress source time or run
  attempt. Arrival order is not evidence of success.
- Reviews bind the complete required PR/head tuple and requested stage. Model
  status cannot replace a human observation; unresolved findings, dismissal,
  stale reviews and missing required reviews block. Draft, closed and unknown PR
  states block source/runtime readiness.
- Awaiting an owner merge is separate from review readiness. One of two required
  merge observations remains partial; source/runtime acceptance requires all of
  them. Accepted design does not establish source or runtime acceptance. Runtime
  additionally requires successful, matching local attempt/evidence observations.
- Dependencies require the exact upstream acceptance stage and contract digest.
  Missing targets, cycles and graph limits fail on append and evaluation. A changed
  complete snapshot revision requires re-evaluation. This is snapshot consistency,
  not dispatch-time fencing.
- Explicit stop observations remain latched across clock advance, revision change
  and reopen. Only an explicit resume referencing the current stop clears the
  synthetic latch. Missing/stale policy, unknown stop state and missing
  capabilities block. Lease expiry cannot imply completion or retry permission.

## Acceptance coverage and deferred gates

The tests in `test_lifecycle_records.py`, `test_lifecycle_store.py` and
`test_lifecycle_readiness.py` use newly invented fixtures and temporary files.
The fixture text deliberately contains an inert relay URL and instruction-like
content. No fixture is a transformed private record.

| Group | Implemented test boundary | Still deferred |
| --- | --- | --- |
| Identity | Immutable exact types, distinct IDs, schema/scope/digest/binding and conflicting revision rejection | Authenticated identities and online tenancy |
| Idempotency | Two concurrent connections, same receipt, changed-payload conflict, retained replay | Reservations, replay horizons and approval consumption |
| Atomicity | Faults before/after records, projections, audit, receipt, metadata and commit; actual SQLite lock/full errors | Power loss and all filesystem/write-error behavior |
| Recovery | Clean reopen, exact history, post-commit uncertainty reconciled by original key | Abrupt process death, journal recovery and dispatch acknowledgement |
| Evidence | Wrong head/binding, stale/conflicting evidence, skipped/cancelled checks, explicit supersession | Provider authentication and live adapters |
| Dependencies | Missing targets, cycles, diamonds, exact stage/contract, graph and stale-CAS limits | Dispatch-time races and fencing |
| Cancellation | Unknown/cancelled observations and expired leases block | Worker cancellation, lease renewal and retry authority |
| Human review | Exact stage/head/PR set, findings, model rejection, partial/full merge observations | Verified owner decisions and merge authority |
| Stop policy | Inclusive cutoff, deadline, DST-resolved windows, latch/resume and reopen | Live scheduler and authenticated owner policy |
| Restore | No import, restore, activation or executor API exists | Exact backup codec, quarantine proof and independent freshness anchor |
| Corruption | Missing/incompatible/corrupt storage fails; logical caps reject without truncation | Blob sealing, tamper resistance and disaster recovery |
| Isolation | Inert injected text, reducer I/O guards, module import guards and no entrypoint wiring | OS/LAN containment, online authentication and secure storage |

Run the new tests, the existing regression suite and the repository's configured
format/lint/pre-commit checks. Report actual failures, skipped checks and missing
tools separately. An import/test guard proves only the instrumented behavior,
not production containment. Final PR evidence must identify the tested commit and
distinguish local platform limitations from current CI results.

No executor, inference, network adapter, exporter, CLI/UI integration, approval
consumption, dispatch reservation, migration, restore or activation is supplied.
Real data and those integration gates require separate bounded work and evidence.
