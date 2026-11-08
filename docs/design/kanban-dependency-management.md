# Kanban dependency management and UI

**Status: proposed design extension, 2026-11-07.** This adds dependency management
to the [subticket and effort design](kanban-subtickets-effort.md), merged in
[PR #266](https://github.com/futuroptimist/axel/pull/266). It specifies UI and the
domain, persistence and adapter support needed to make that UI truthful. This PR
changes documentation only. It neither creates live edges nor authorizes runtime
implementation, private-data movement, publication, merge or deployment.

## 1. Problem, baseline and scope

A card can list prerequisite links without any supported operation to register
them in the board's dependency graph. A source-defined graph can also show links
that ordinary card editing cannot change. Separately recorded completion
conditions do not establish that the graph UI reads or enforces the same data.
The UI must distinguish these cases instead of treating every link as a saved,
enforced dependency. Adding buttons alone cannot remove the storage/API gap.

At inspected main commit `cf44d14234cb58126a799eeef7d3c037535e3173`:

- [The web model](../../web/src/model.ts) and
  [fixture reader](../../web/src/fixture-reader.ts) provide synthetic read-only
  cards, not persistent dependency records or an authorized mutation service.
- [Lifecycle records](../../axel/lifecycle_records.py) define stage/contract-bound
  `Dependency` observations. Current edges are selected by the dependent task's
  current revision; validation checks missing endpoints, cycles and graph bounds.
  There is no dedicated stable-edge create/edit/remove command or UI. This is not
  an authenticated board backend.
- [Lifecycle storage](lifecycle-foundation.md) supplies a bounded local atomic
  append experiment with revision checks and operation receipts. Its strict v1
  encoding and advisory readiness are not implicitly upgraded by this design.
- [The service design](sanitized-kanban-contract.md) defines proposed identity,
  isolation and adapter boundaries, not an already available online writer.

Deliver the read-only dependency experience first, then a separately approved,
qualified synthetic writer and editor, then an explicitly authorized adapter/pilot.
All public examples, fixtures, screenshots and CI evidence must be newly invented.
Keep private board IDs, source catalogs, card text, receipts and inventories out of
the repository. Existing navigation fixes remain their own deliverable; this work
reuses their link/reveal/return contract rather than claiming to have shipped them.

Non-goals: automatic prose-to-edge extraction, changing priorities or WIP limits,
automatic scheduling, cross-board/profile relationships, graph-layout editing,
bulk migration, a new permission system, or making the legacy CLI a board adapter.

## 2. One directed relation, two views

Use one canonical direction: **dependent depends on prerequisite**. Store
`dependent_id -> prerequisite_id`. The dependent lists **Prerequisites**; the
prerequisite lists **Required by** (dependents). The second list is a reverse
projection of the same edge, never a reciprocal edge. Navigation is bidirectional;
execution ordering is not. Label direction in words, not just arrows or color.

Example: invented `demo:harbor/view` depends on `demo:harbor/model`. The model
appears in the view's Prerequisites, and the view appears in the model's Required
by. Only one relation exists. Neither card must depend on its containing parent.

### Proposed logical record

The following is a schema-design contract, not a new wire format. DG-01 allocates
record names/versions with ST-02 before code or storage changes.

| Field | Contract |
| --- | --- |
| Scope and `edge_id` | Immutable board/profile scope and opaque edge identity, independent of titles, display numbers or list position |
| `dependent_id`, `prerequisite_id` | Immutable endpoint card identities; same authorized board/profile |
| Edge revision and state | Contiguous revision; active or retired. Retirement preserves every previous version |
| Requirement | Either `card_done`, or `accepted_stage` with exact stage and acceptance-contract digest; no implicit upgrade or fallback between them |
| Reason and provenance | Bounded inert rationale, actor provenance, time, source and operation reference; proposed/manual/import origins remain distinguishable |
| Task/contract bindings | Revisions and contract references used to validate this change and recompute current acceptance; historical accepted bindings stay intact |

Only one active explicit edge per ordered endpoint pair in v1. Editing its
requirement creates a new edge revision. Changing either endpoint retires the old
edge and creates a new identity in one transaction, with replacement provenance.
A second active duplicate is rejected, including reversed-form submissions of the
same direction. An actual reverse relation is a different edge and must pass cycle
validation; no reverse edge is synthesized for Required by.

Parentage remains separate. A required child contributes an implicit completion
gate `parent -> child` with origin **Required subticket**. Show it beside explicit
prerequisites with its origin and stage, but edit it through hierarchy controls.
An explicit edge that overlaps such a gate does not override it. Reject an exact
redundant requirement with a clear reason; preserve a distinct stronger condition
as an additional gate. Never count duplicate endpoint references as extra cards or erase an
implicit gate when retiring an explicit edge.

### Completion integration

An active explicit dependency is required, not an optional informational link.
Ordinary links remain a different field. `card_done` requires a currently valid
authoritative Done acceptance, not just a cached status badge. `accepted_stage`
requires the exact accepted stage/contract and its evidence; design acceptance
cannot substitute for source/runtime acceptance. The display shows both upstream
status and requirement satisfaction so they cannot be mistaken for each other.

One canonical dependency collection feeds both endpoint views and readiness.
Completion contracts reference edge identities/revisions or a checked projection
digest. They must not maintain an independently editable duplicate edge list.
Pre-existing non-edge acceptance conditions remain intact. A disagreement between
the graph and completion projection is an explicit integrity blocker, never an
optimistic merge of two sources.

Changes invalidate affected readiness and completion evidence. Re-evaluate the
transitive dependent closure, including parent gates. Never mark cards Done, start
workers, clear an owner wait or reduce effort merely because an edge was removed.
No edge supplies action authorization. A changed requirement on a terminal card
requires the approved reopen/contract-revision workflow first, or rejection.

Dependency waiting is metadata with an unmet condition and next actor. It must
not automatically move a card into a column reserved for owner-actionable waits.
ST-01 must resolve the parent design's proposed synthetic reopen-to-Blocked rule
against the destination's column policy before any live adapter. When acceptance
becomes stale, expose **Acceptance needs revalidation** and prevent a current
completion claim; do not invent a successful status transition.

## 3. Dependency visibility and navigation

Every card detail has separate Prerequisites and Required by sections. Each row
shows an authorized card link, current status, archive marker, requirement type,
required stage if relevant, satisfaction or unknown state, and origin. Compact
board badges summarize unmet prerequisites only from a complete authorized read.
Counts are unique cards; detailed conditions stay visible if several origins share
an endpoint. A small own-effort E or a collapsed section cannot hide unmet work.

The reader returns scope, coherent graph/task revision, completeness, provenance
and capabilities separately. Presentation must distinguish:

| State | Required presentation |
| --- | --- |
| Complete authoritative graph, no edges | “No prerequisites” / “No dependents” |
| Complete authoritative graph with unmet conditions | Name authorized unmet conditions; show the evaluated revision |
| Source-defined or informational references | “Reference only”; identify that this is not a writable or enforcement-qualified graph |
| Intended edges awaiting registration | “Dependency registration pending”; show intended direction and requirement without a saved-edge badge |
| Unsupported writer | “Dependency editing is not available here”; retain readable relationships and do not offer a fake Save |
| Missing capability or owner action required | Explain the allowed next action; distinguish permission from unsupported functionality |
| Loading, failed, partial, stale or unreadable graph | “Dependency status unavailable” or a labeled stale result; never show zero, ready or complete |

Do not infer registration from prose, a link, a task's creation receipt, a PR merge
or the existence of a completion contract. Success needs a persisted edge receipt
plus a coherent read of both endpoint projections and enforcement binding. Until
then, intended prerequisites remain explicit planning constraints, not satisfied
because the graph happens to be empty.

Reuse normal in-board permalinks and temporary hidden-target reveals. Keep filters,
sort, archive view, lane/card collapse and scroll intact. A related card excluded
by filters is revealed as context, not added to result/facet counts. Required by
links must work from either end across archive views. Dismiss/Escape and browser
Back/Forward restore the initiating focus or a stable heading. Repeated clicks,
old reads arriving late and navigation while saving must not change the wrong card.

Use labeled link/button controls, visible focus, keyboard operation, separate
disclosures and concise live announcements. Support narrow widths and 200% reflow
without nested interactive elements or relying on a visual graph. Link titles and
history remain inert text. A hidden endpoint must not leak through titles, counts,
autocomplete results, cycle paths, errors, notifications or cached reverse indexes.

## 4. Create, edit and remove flows

Only show enabled mutation controls when the adapter advertises a supported
version and current capabilities. Recheck authority at commit; enabled UI is not
authorization. A planning draft may be copied as text, explicitly unregistered;
do not silently queue future live writes when support or permission returns.

1. **Add prerequisite:** Search authorized candidates by stable ID or title, then
   show the exact selected identity and “This card depends on …”. Choose whole-card
   Done or exact stage/contract. Show archive state, rationale and current condition.
2. **Add dependent:** From Required by, select the other card and explicitly show
   “Selected card depends on this card”. Validate permission to change the selected
   dependent's requirements; permission on the viewed prerequisite alone is not enough.
3. **Edit:** Show old/new requirement and all affected acceptance bindings. An
   endpoint replacement previews retirement plus addition, not an in-place ID edit.
   Client-side candidate filtering helps, but server validation remains authoritative.
4. **Remove:** Use **Remove dependency**, show direction and the requirement being
   removed, explain that history remains, and require a reason. It never deletes a
   card or an implicit subticket gate. Offer no blind “Undo”: restoration is a fresh
   validated change against current revisions and policy.
5. **Preview and submit:** Show the full before/after relation set, impacted cards,
   contract changes, newly unmet requirements and any required scope decision.
   A single explicit submit sends the bounded operation. Cancel before submission
   writes nothing; no persistence in browser local storage is implied.
6. **Pending, conflict, uncertain:** Disable duplicate submission, retain the local
   draft while safe, and never optimistically claim persistence. A stale revision
   requires refresh and a new preview. An uncertain outcome reconciles the original
   operation key before any retry; leaving the view does not cancel a committed write.
7. **Verified result:** Display the receipt/revision, refresh both directions and
   readiness, then announce the exact change. If commit succeeded but refresh failed,
   say “Saved; current dependency status unavailable”, not fully synchronized.

Retirement, retargeting, lowering the stage or changing the acceptance digest can
weaken a completion requirement. They need an exact scope-change decision from the
authorized owner under a separately accepted policy, bound to the old/new graph,
contract and expected revisions. Generic card-edit permission, model text or an old
approval cannot satisfy it. This design proposes the workflow, not its authority:
until that policy and its evidence verification are implemented, reject the change
with `REQUIREMENT_CHANGE_UNSUPPORTED`. Preserve the lifecycle foundation's existing
PR/check/reviewer non-shrink rules. Adding an edge also rechecks whether it changes
approved scope; it never transfers approval from one card to another.

## 5. Domain, storage and adapter contract

### Atomic command boundary

Define typed create/revise/retire/replace commands over a shared domain service.
UI and a future agent/MCP adapter must use that same boundary. Generic card field
patches, raw database edits, completion-contract edits and source-code catalogs
must not bypass graph validation. No proposed endpoint is claimed available today.

A command includes authenticated scope/principal, operation key, bounded intent,
expected graph generation/revision, expected endpoint/edge/task/contract revisions,
and any required verified scope-change evidence. Validate the complete candidate
graph in one transaction or equivalently qualified serializable operation. The
graph revision fences even disjoint-endpoint edits that could form a cycle together.
An adapter unable to provide atomicity/conflict detection remains read-only.

Commit all edge versions, task/contract revisions, invalidation markers, audit and
receipt together, or none. Reverse indexes are rebuildable projections. Reopen
transitions may commit only through an approved atomic lifecycle policy; otherwise
persist an invalidation gate and fail completion until explicit reconciliation.
Read models must not combine an old forward list with a new reverse list. Return
the committed graph revision, touched identities and payload digest, not cached
current readiness. Re-evaluate readiness against the new coherent snapshot.

Scope idempotency to principal, board/profile, operation kind and key. Same key
and exact payload returns the original receipt; changed payload conflicts. Retain
retired edges, receipts and operation bindings in history and backups. Do not
fabricate a new key after timeout, and recheck read authorization before disclosing
any reconciled receipt. A later revocation does not make an old write repeatable.

### Validation and permissions

- Authenticate and authorize scope before revealing whether either endpoint exists.
  Require read access to both endpoints and dependency-edit capability on the
  dependent; Required by is not a shortcut around it. Scope-changing operations
  additionally require the specific verified decision. Check policy/work-hours and
  current revocation at use, not just at preview.
- Reject unknown/foreign endpoints, self-links, duplicate active pairs, invalid
  stage/digest/type, stale contracts, stale revisions and unsupported schema.
  Same-board cross-repository edges are allowed; cross-board/profile edges are not.
- Validate explicit plus implicit required-child gates together, irrespective of
  archive, filter or current satisfaction. Retiring an explicit edge cannot remove
  another gate's cycle contribution. Cycles receive a bounded authorized path when
  disclosure is safe; otherwise use a non-enumerating error.
- Keep the parent design's synthetic limits: 256 cards, 1,024 combined prerequisite
  edges and longest path of 32 cards, plus hierarchy limits. Reject over-budget
  reads/commands atomically; never truncate to make a graph valid. These are test
  budgets, not production capacity or timing claims.
- Archived endpoints retain relations and gates. Existing references stay readable
  when authorized; new edits involving archived cards require the destination's
  explicit restore workflow first. Terminal dependents need reopen before edits.
  A missing endpoint or incomplete snapshot blocks mutation/evaluation, not history
  recovery by silent edge deletion. No cascade deletion is introduced.

Use typed errors such as `UNSUPPORTED_CAPABILITY`, `FORBIDDEN`, `REVISION_CONFLICT`,
`SELF_DEPENDENCY`, `DUPLICATE_DEPENDENCY`, `DEPENDENCY_CYCLE`, `GRAPH_LIMIT`,
`INCOMPLETE_GRAPH` and `REQUIREMENT_CHANGE_UNSUPPORTED`. Public errors must not
distinguish missing from inaccessible identities. Internal diagnostics and audit
follow the same approved data boundary; they are not public telemetry.

## 6. Migration and release gates

1. Keep the synthetic read model versioned. Fixtures explicitly distinguish no
   edges from unavailable/unsupported graphs. Do not infer requirements from
   display text or label existing links as authoritative edges during parsing.
2. Define an explicit store upgrade before accepting new edge records. Preserve
   canonical historical bytes and old operation receipts. Qualify old-reader
   rejection, restart, bounded storage and reverse-index reconstruction. No silent
   changes to the current lifecycle v1 codec or legacy task JSON are allowed.
3. For any approved adapter, inventory separately its existing source-defined
   relations, completion-contract prerequisites and intended-but-unregistered links.
   Bind the inventory to a coherent source revision and retain original provenance.
   Reconcile endpoint identity, direction, duplicate pairs and acceptance semantics
   for every entry. Conflicts remain unresolved until reviewed, not guessed.
4. Use a dry-run mapping and owner-reviewed import manifest. Existing source links
   are not automatically `card_done`, and prose is never parsed into live edges.
   The manifest names exact intended edges and requirements; imported receipts are
   historical evidence, never newly minted approvals. Keep all real material in
   the approved private destination. Public migration tests use invented catalogs.
5. Follow the [backup/restore contract](resumable-backup-contract.md): complete
   inventory and backup, independent restore/re-export validation, archive/history
   preservation, single-writer cutover and an exact compatible release manifest.
   Test interruption before/after commit and partial read failures. Verify each
   imported edge from both endpoints and through readiness, not only record count.
6. Retire the old source catalog as a writer only after equivalence and restoration
   checks pass. Keep its provenance. Do not dual-write two competing authorities.
   Disable editing safely on rollback, retaining all edges/history; an older writer
   unable to preserve the new schema cannot be the fallback. Forward repair or a
   qualified compatible release is required after new records exist.

No live data import, capability rollout or Site publication is part of the design
PR. A private pilot requires its own scope, approval, destination, permissions,
backup and rollback evidence. An owner-private release exception, where applicable,
does not establish broader implementation or data-migration authorization.

## 7. Acceptance matrix

These are planned tests, not results of this documentation change. Combine them
with A1–A17 from the parent design and the existing navigation regression suite.

| ID | Scenario | Expected result |
| --- | --- | --- |
| D1 | Create view -> model; reload and navigate both ends | One persisted edge; correct Prerequisites/Required by; matching revision and receipt; no reciprocal edge |
| D2 | Same submit twice, timeout after commit, same key with changed payload | Reconcile original receipt once; changed payload conflicts; no duplicate edge |
| D3 | Edit requirement; replace endpoint; retire relation | Atomic versioned history and both projections; invalidated acceptance; original records retained |
| D4 | Self-link, duplicate, missing/foreign endpoint, invalid stage/digest | Typed rejection; no partial writes or unauthorized existence disclosure |
| D5 | Direct/long cycle, diamond, required-child cycle, concurrent disjoint edits | Cycles rejected across the combined graph; valid diamond accepted; CAS serializes graph changes |
| D6 | Graph limits and incomplete/over-budget reads | Exact boundary checks; no truncation, guessed empty graph or optimistic readiness |
| D7 | Upstream Done with wrong stage/contract or stale evidence | Requirement still unmet; graph and completion projection agree; no stage fallback |
| D8 | Archived/terminal endpoints, reopened upstream, changed evidence | Relations retained; edits follow restore/reopen policy; transitive invalidation prevents stale Done claims |
| D9 | Add dependent from reverse view; revoked role; scope-weakening removal | Dependent-side permission checked; revocation blocks; exact owner decision required; unsupported policy rejects |
| D10 | Unsupported writer, reference-only graph, pending registration, failed read | Honest capability/provenance states; no fake Save, saved-edge badge or zero count |
| D11 | Conflicting card/edge/contract revision and lost refresh after save | Draft retained safely; refresh/re-preview on conflict; committed-but-unavailable labeled accurately |
| D12 | Filter/archive reveal, repeated clicks, late reads, Back/Forward, Escape | Both-endpoint links preserve view and focus; no count inflation or wrong-card update |
| D13 | Keyboard, screen reader labels, narrow viewport and 200% reflow | Both lists and all editor states usable without a graphical layout or color |
| D14 | Unauthorized endpoint through search/count/history/cycle/cache | No identity, title, hidden count or conditional error leakage; authorize before disclosure |
| D15 | Upgrade/import/rollback, projection rebuild, interrupted transaction | IDs, exact history and requirements preserved; old writers rejected; all-or-none persistence |
| D16 | Inert malicious text, privacy canaries, synthetic UI/API tests | No execution or hidden live effects; no real data in source, build, screenshots or logs |

Use pure domain tests for graph and policy rules; storage integration tests for
concurrent writers, faults and idempotency; adapter contract tests for capability,
authorization and projections; and Chromium/Firefox/WebKit journeys for UI states.
Record exact tested commit, schema/fixture versions and actual passed, failed,
skipped or unrun checks. Synthetic tests do not establish production durability,
authentication, dispatch fencing or migration safety.

## 8. Scoped backlog and ST integration

DG keys below are public planning keys, not allocated board cards or permission to
execute. Keep all thirteen ST keys and their existing dependency ordering. Add
explicit integration gates rather than silently expanding ST estimates or treating
prose links as registered edges. Assign owners/P/C at triage; E? remains until each
slice is bounded with reviewed policy and adapter decisions.

| Key | Outcome and bounded scope | Prerequisites | Acceptance |
| --- | --- | --- | --- |
| DG-01 | Review dependency semantics, versioned edge/contract schema, capability states and scope-change decision policy | ST-01, ST-02 | D1/D3/D7/D9/D10 design review; current v1 behavior distinguished from proposed rules |
| DG-02 | Implement pure dependency validation, canonical projections and completion invalidation using invented data | DG-01, ST-03, ST-04 | D4–D8/D14; no storage or online effects |
| DG-03 | Add read-only prerequisite/dependent UI, capability notices and navigation fixtures | DG-01, DG-02, ST-05, ST-07, ST-08 | D1/D7/D10/D12–D14/D16; no writer controls that imply persistence |
| DG-04 | Implement qualified synthetic transactional edge commands and upgrade/recovery tests | DG-02, ST-10 and separate write-slice approval | D1–D9/D11/D15; retained receipts/history, atomic graph/contract binding |
| DG-05 | Add reviewed add/edit/remove UI over the qualified writer | DG-03, DG-04, ST-11 and editor approval | D2/D3/D9–D14/D16; preview, safe cancellation and unknown-outcome reconciliation |
| DG-06 | Qualify adapter/migration contract and pilot readiness, without live import | DG-03, DG-04, DG-05, ST-12 | D1–D16 evidence review; dry-run mapping, compatible fallback and privacy review |
| DG-07 | Run a separately authorized bounded dependency pilot | DG-06, ST-13 readiness and explicit live-use authority | Exact approved edge set persists, renders and gates correctly; no automatic wider rollout |

ST-01 resolves status/reopen and owner-decision semantics; ST-02 keeps schema work
compatible; ST-03/04 supply shared graph and completion rules. ST-05–08 retain
hierarchy/effort presentation and navigation ownership. ST-09 remains WIP/wait
accounting, with dependency waits as metadata. ST-10/11 retain family command and
editor ownership, while DG-04/05 own explicit dependency commands and controls.
ST-12 remains the hierarchy compatibility gate. For a combined pilot, ST-13 also
requires DG-06; DG-07 depends on ST-13's readiness decision, not its completion,
so the two pilot gates do not form a scheduling cycle. Hierarchy-only qualification
can finish independently but cannot be reported as dependency-feature completion.

Design review must settle DG-01 decisions before implementation is scheduled.
Record additional scope and any revised E explicitly on affected planning cards;
do not claim the already registered ST backlog contains the new DG deliverables.
Separate private graph-registration work remains pending until a supported writer
actually commits and verifies it. This PR's completion means only that the proposed
extension is reviewable, not that any runtime limitation has been removed.
