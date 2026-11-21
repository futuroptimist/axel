# Versioned hierarchy and effort schema plan

**Status: provisional ST-02 supporting analysis, 2026-11-08.** Depends on acceptance of
[ST-01 decisions](kanban-hierarchy-decisions.md). This plan may be reviewed in
parallel but remains conditional on those decisions. It introduces no code,
record type, migration, reader or writer. Names below are proposed allocations,
not claims about today's supported formats.

Inspected baseline: `cf44d14234cb58126a799eeef7d3c037535e3173`.
Source contracts: [subtickets and remaining effort](kanban-subtickets-effort.md)
and the merged [dependency extension](kanban-dependency-management.md). DG-01
reviews the edge record with ST-02 before implementation; the proposed structural
references here do not replace the dependency design.

## 1. Current contracts that must remain readable

| Surface | Verified baseline | Extension boundary |
| --- | --- | --- |
| `web/src/model.ts` | `Board` is an unversioned array; `parseBoard` validates up to 1,000 tasks and copies recognized properties, silently dropping unknown row/history fields. P0–P4/Unranked and Clear/Needs detail are presentation vocabularies. | Do not pass new hierarchy records through that reader. Add a separately selected strict envelope/reader and explicit old-fixture upgrade. Preserve the legacy reader's behavior for legacy fixtures. |
| `web/src/fixture-reader.ts` | Complete fixture reads, loading/error/ready states and newest-request generation fencing; no remote service. | Carry snapshot identity/completeness through the new reader. Preserve delayed/error handling and request fencing. |
| `axel/lifecycle_records.py` | Strict frozen dataclasses, envelope schema 1, exact field sets and canonical UTF-8 JSON; fixed `RECORD_TYPES`; `TaskRevision` has no parentage or effort. | New record types/version dispatch; never append fields to v1 canonical bytes or silently change decoding. |
| `Dependency` and `Snapshot` | Downstream task envelope plus upstream ID, required stage and acceptance digest; complete history and bounded current graph validation. | Include required-child completion edges in a new combined validator. Preserve explicit prerequisites and their stage/contract bindings. |
| `axel/lifecycle_store.py` | SQLite schema version 1, exact schema checks, exclusive new store, explicit open and atomic append with retained receipts. | Qualified version-2 store and explicit upgrade, deferred to ST-10. V1 open must reject V2 storage. |
| `axel/task_manager.py` | Separate legacy CLI JSON list with its existing loader semantics. | No change, conversion, integration or fallback from new storage to this loader. |

The presentation's old 1,000-task ceiling is not the hierarchy budget. A new
hierarchy snapshot is capped at 256 cards. Oversized old fixtures fail explicit
upgrade; never truncate them to satisfy the new limit.

## 2. Proposed presentation envelope

Allocate `axel.synthetic-hierarchy.v1` independently of lifecycle schema numbers.
An envelope contains exactly `schema`, `snapshot_id`, `snapshot_revision`,
`board_id`, `profile_id`, `complete` and `cards`. IDs are opaque strings; revisions
are nonnegative safe integers. This synthetic envelope has no authenticity claim.

Only `complete: true` after full validation produces a usable family snapshot.
Partial/unavailable data stays in an explicit loader state without authoritative
counts or completion eligibility. A failed read cannot become an empty envelope.
An empty complete board is valid only when explicitly supplied by the fixture.

Each card retains all existing presentation fields and adds the exact fields below.
Reject unknown keys at every new typed object boundary, including history and
estimate values. Copy and freeze nested values; do not retain mutable input aliases.

| Field | Proposed type and rule |
| --- | --- |
| `parent_id` | Opaque ID or null; sole stored source of parent membership. |
| `required_for_parent` | Boolean for a child, null for a root; creation preview defaults a child to true, but serialized records must supply the value explicitly. |
| `parent_acceptance_stage` | `design`, `source` or `runtime` for required children; null for roots and optional children. |
| `parent_acceptance_digest` | Exact lowercase 64-hex digest for required children; otherwise null. Binds the child's contract required by the parent. |
| `own_scope` | Nonempty string or null. Null means old scope has not been explicitly mapped; no invented ownership transfer. |
| `acceptance_criteria` | Ordered array of nonempty strings or null. Null means unmapped, not satisfied. An empty array needs an explicit reviewed contract explaining why no additional criteria exist. |
| `effort_remaining` | Integer 0…9 or null. Reject booleans, fractions, strings and out-of-range values. Null is E?, never zero. |
| `estimate` | Null when no current estimate exists; otherwise exact object with `rationale`, `estimator`, `estimated_at`, `task_revision`, `rubric_version`. |
| `assumptions`, `unresolved_questions`, `waits` | Separate arrays of inert strings; never folded into C or interpreted as authorization. |
| `dependencies` | Provisional read-only projection of exact `{upstream_id, required_stage, acceptance_digest}` objects for accepted-stage edges; no prose inference. It does not represent all explicit dependency requirements. |
| `upgrade_origin` | Null for native records, or explicit `{schema, task_revision}` identifying the legacy fixture interpretation. |

Use the existing card revision as the estimate binding; retain the estimate on an
unchanged revision only. `estimated_at` is strict UTC whole-second ISO text,
`rubric_version` is the explicit identifier `effort-rubric.v1`, and rationale and
estimator are nonempty bounded strings. Non-null effort requires estimate metadata;
null effort requires `estimate: null`. Previous values remain in immutable history,
including the reason an estimate was invalidated. Future lifecycle transitions must
record the E0 acceptance rationale rather than inventing an estimator identity.

Bound every envelope to 16 MiB UTF-8 and every card to 64 KiB, including nested
strings, arrays and history. Retain at most 1,000 presentation history entries per
card within that byte cap. Check byte size before parsing and traversal depth before
recursive decoding; raw JSON rejects duplicate keys and non-finite numbers.
Canonical lifecycle encoding remains a separate requirement, not an assumed property
of ordinary web JSON. Implementation review must pin the exact bounded decoder.

## 3. Invented examples and upgrade

These examples specify field relationships, not complete serialized fixtures:

| Card | Parent and requiredness | Own work and effort | Acceptance binding |
| --- | --- | --- | --- |
| `demo:harbor/release` | Root; all parent fields null | Integration scope; E2 with current provenance | Its own criteria remain unsatisfied until integration is accepted. |
| `demo:harbor/model` | Parent `demo:harbor/release`; true | Model scope; E3 with current provenance | Source stage and the exact digest of its invented model acceptance contract. |
| `demo:harbor/view` | Parent `demo:harbor/release`; true | View scope; E? with null estimate | Source stage and a distinct invented view contract digest. |
| `demo:harbor/checks` | Parent `demo:harbor/release`; false | Optional follow-up; E1 with current provenance | Parent acceptance stage/digest are null. |

Generate real test digests from explicit invented contract bytes; no placeholder
string may pass a digest validator. Tests must also include roots without children,
archived unfinished children, optional open children and a missing target.

An explicit `upgradeLegacyFixture` operation validates a recognized legacy fixture
shape before using the old copying parser, so unknown input fields cannot silently
disappear. It preserves every recognized legacy value, ID, revision and history
entry, and adds root/null parent fields, E?/null estimate, empty dependencies and
observation arrays, null own scope/criteria and a labeled upgrade origin. This is
an explicit interpretation of a known flat fixture, not inference from its title,
status or description. Retain the description verbatim; it is not automatically an
accepted own-scope contract. Done legacy cards therefore gain no new family
acceptance evidence merely from upgrade. Record the source fixture digest in the
upgrade report and verify value-preserving round-trip comparison.

## 4. Proposed lifecycle extension

Reserve distinct `TaskRevisionV2` and `EnvelopeV2` types in a new codec dispatch;
the envelope version is 2. Carry the current task fields unchanged and add the
hierarchy/scope/estimate fields above using immutable typed values. Use the existing
lifecycle epoch-second time convention for estimate timestamps rather than the web
ISO presentation. Explicit prerequisites remain `Dependency`-shaped records with
a V2 envelope and a distinct V2 record type. There is no inline second authority
for dependency storage in lifecycle records; the web array is a projection.
DG-01 must reconcile exact record fields, edge identity/revision and the distinct
`card_done` requirement before any feature claims to support that requirement.
Do not convert it to an accepted-stage binding or drop it to make the graph valid.

V1 records remain byte-for-byte v1, including original IDs, digests and operation
receipts. A qualified V2 reader may dispatch retained v1 records to the unchanged
v1 decoder and new records to a strict v2 decoder. Unsupported types/versions fail
before interpretation. Do not weaken v1 `RECORD_TYPES`, envelope validation or
unknown-field checks to accept future records accidentally.

The V2 snapshot projection gives retained flat v1 heads an explicit root/E?
interpretation without writing replacement historical records. First modification
appends a new contiguous V2 task revision. Old approval references stay evidence
references; acceptance must be reevaluated at the new revision and contract. Copying
records or moving scope must never copy executable authority.

A current required child's relationship contributes a parent-to-child completion
gate with stage/digest. The candidate snapshot must validate all affected records,
including every old/new parent and child. Reparenting, optionalization or removal
that drops a required gate remains rejected until the separate requirement-removal
policy is accepted. Existing PR/check/reviewer monotonicity remains enforced.

Store V2 allocation, exact SQL schema, upgrade manifest and commands are ST-10
work, not implemented by ST-02. Upgrade must create a separate destination under
an explicit operator action, preserve the original store, verify complete retained
bytes/receipts/projections, and prevent old writers from opening the new store.
No initialization-on-open, automatic repair, history rewriting or CLI fallback.
Mixed historical versions are permitted only after the V2 reader/store tests
qualify that exact combination; they are not supported by today's v1 reader.

## 5. Graph, errors and derived data

Validate a complete authorized candidate snapshot before committing any change:

- At most 256 cards, 32 direct children per parent, hierarchy depth one, 1,024
  combined prerequisite edges and a longest prerequisite path of 32 cards.
- IDs are unique; parent and dependency targets exist in the same board/profile;
  no self-parent, grandchild, self-dependency or duplicate explicit dependency.
- Roots and optional children have null parent acceptance bindings. Required
  children have complete stage/digest bindings. A child cannot also be a parent.
- Build a directed graph from explicit prerequisites plus required-child gates.
  Allow only one active explicit edge per ordered pair. Reject an exact duplicate
  of an implicit gate; retain a distinct stronger requirement. Collapse identical
  traversal endpoints for cycles and path length, but count distinct obligations
  toward the edge budget. Reject contradictory contracts rather than silently
  selecting one.
- Reject combined cycles, dangling edges, incomplete input and over-limit changes
  atomically. Archive and status never remove a relationship from validation.

Proposed stable error categories: `UNSUPPORTED_SCHEMA`, `UNKNOWN_FIELD`,
`INVALID_TYPE`, `INVALID_ESTIMATE`, `UNMAPPED_SCOPE`, `DUPLICATE_ID`,
`MISSING_TARGET`, `CROSS_SCOPE`, `INVALID_PARENT_BINDING`, `HIERARCHY_DEPTH`,
`DUPLICATE_DEPENDENCY`, `CONTRACT_CONFLICT`, `PREREQUISITE_CYCLE`, `GRAPH_LIMIT`,
`INCOMPLETE_SNAPSHOT`, `STALE_REVISION`, `REQUIREMENT_REMOVAL_UNSUPPORTED`.
Implementation should map internal detail to privacy-safe errors before an online
adapter exists; errors must not disclose unreadable IDs or counts.

Derive parent indexes, family summaries and reverse prerequisite navigation from
canonical current records. Never store a second editable child list. Counts include
archived immediate children and distinguish required Done/open/blocked/Won't Fix,
optional children and unknown effort. Blocked is a subset of open, not an additional
child. A missing/unreadable record yields unavailable/incomplete, never zero.

No E sum, average, weighted completion, inferred deadline or inherited execution
status is a valid projection. WIP uses separate execution/reservation observations;
ST-09 must define that model before any live admission interpretation.

## 6. Compatibility and acceptance matrix

| Reader / input | Required behavior |
| --- | --- |
| Existing web reader / legacy array | Preserve existing behavior in legacy use only. |
| Existing web reader / new envelope | Reject as non-array; never unwrap new cards for this reader. |
| New web reader / legacy array | Require explicit upgrade, not silent auto-detection. |
| New web reader / supported complete envelope | Validate exact shape, all records and combined graph; immutable result. |
| New web reader / unsupported, partial or failed input | Explicit incompatibility/unavailable state; no complete empty family. |
| V1 lifecycle reader/store / V2 data | Reject without modifying bytes. |
| Qualified V2 reader / preserved V1 history | Explicit version dispatch, root/E? interpretation and no invented acceptance. |
| Qualified V2 store / mixed V1/V2 history | Exact byte/receipt preservation plus full V2 candidate validation. |
| Legacy CLI / hierarchy data | No integration or fallback. |

Reopen acceptance invalidation is separate from visible board-column policy. The
ST-01 lane decision must be settled before allocating a dependent transition; a
reader without a qualified atomic writer exposes invalid acceptance and pending
status reconciliation rather than silently moving the parent to Blocked.

ST-02 acceptance is a reviewed schema plan, not passing runtime tests that do not
exist yet. ST-03/ST-05 must implement A9/A10/A15 tests covering the matrix, unknown
fields at every level, duplicate JSON keys, boolean effort, fractions, E0/E?,
revision mismatch, every graph limit and one over each limit, archive/Won't Fix,
missing/unreadable targets, explicit upgrade preservation and immutable copies.
ST-10 adds interrupted-upgrade, unchanged-original-store and receipt replay tests.

Review must settle the proposed names, bounds, explicit legacy null-scope behavior,
V2 version-dispatch strategy and reopen/removal policy before implementation.
Synthetic acceptance will not establish privacy, authentication, production
capacity, migration durability or authority for live use.
