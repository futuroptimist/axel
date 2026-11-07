# Kanban subtickets and remaining-effort scores

**Status: proposed design, 2026-11-07.** Add first-class subtickets and an E0–E9
remaining-effort score to make large outcomes easier to plan, execute and review.
This document specifies behavior and a card-ready implementation backlog. It does
not create cards, change the board, implement features, migrate data or authorize
execution, merge or deployment. The recommended defaults below remain subject to
design review; accepting this document is not implementation approval.

## 1. Goals and boundaries

- Break a large outcome into independently actionable, testable cards without
  losing its original identity, acceptance criteria or history.
- Distinguish priority (P), the board's existing clarity measure (C), remaining
  effort (E), and time spent waiting. Preserve existing P/C meanings.
- Make scope transfers visible. A smaller parent E must not imply that the whole
  outcome has become smaller or nearly complete.
- Keep every child discoverable, linkable and accountable in its own status lane.
- Define completion, filtering and work-in-progress (WIP) consistently across the
  domain, UI and future adapters.

Non-goals: time tracking, billing, person-performance scores, automatic scheduling,
automatic task creation from prose, multi-parent subtickets, unbounded nesting,
production migration, new approval powers, or an ETA generated from an E score.

### Current repository baseline

Inspected main commit: `3af0f304846bfe6db4debc82cf74c809ef61f82c`.

| Surface | Current behavior | Design implication |
| --- | --- | --- |
| [Web model](../../web/src/model.ts) and [selectors](../../web/src/selectors.ts) | Synthetic read-only tasks; six statuses; independent archive flag; six facets; P0–P4/Unranked and Clear/Needs detail; no hierarchy or effort | Introduce invented hierarchy fixtures first. Do not claim the live board's full P/C vocabulary already exists here. |
| [Web milestone](web-milestone-one.md) and [parity ledger](web-parity-ledger.md) | Permanent links, independent collapse preferences, temporary hidden-target reveal, local assets and no live effects | Preserve those behaviors while adding family views and E filters. |
| [Lifecycle foundation](lifecycle-foundation.md) | Isolated synthetic records, atomic append and advisory readiness; stage-bound dependencies and evidence | Design a versioned extension. Do not silently change its strict encoding or turn advisory results into authority. |
| [Legacy task manager](../../axel/task_manager.py) | Separate JSON list with numeric IDs, descriptions and a completed flag | Leave it unchanged in the first milestones. No silent conversion to the new model. |
| [Sanitized kanban contract](sanitized-kanban-contract.md) | Proposed identity, privacy, service, migration and multi-PR boundaries | Reuse those boundaries; this design is a focused addition, not a replacement. |

All examples below are newly invented. Public source, screenshots and CI artifacts
must contain no private board records, owner quotations, source snapshots or
operational receipts. An eventual private-board pilot is a separate authorized
operation. No private IDs or task content are needed to implement this contract.

## 2. Effort means remaining work owned by this card

`E` is an **ordinal size band for the active work still owned by the card**.
It excludes scope explicitly assigned to children. It includes the card's own
remaining design, implementation, testing, review fixes, integration and acceptance
work, regardless of whether a person or an approved agent will do that work.

Waiting for review, permission, CI, a delivery or a deployment window is recorded
as a wait/blocker, not inflated into effort. Work needed to resolve a blocker does
count if this card owns it. Unknown fixes are uncertainty, not a fabricated number.
E is neither elapsed time nor a promise about agent throughput or reviewer response.

- Store a nullable integer `effort_remaining` in 0…9. Render null as **E?**, never E0.
  Reject fractions, strings, booleans and out-of-range values at typed boundaries.
- E0 means no active work remains in this card's own scope. A parent can be E0 and
  still wait on required children. A card can be E0 while awaiting an owner action.
  E0 does not set Done, authorize a transition or bypass acceptance evidence.
- Record a short estimate rationale, who estimated it and when. An estimate is
  tied to a task revision and rubric version. If scope changes without an accepted
  re-estimate, present E? and retain the previous estimate in history.
- Keep uncertainty separate: list assumptions, unresolved questions and blockers.
  Do not reinterpret the existing C scale as estimate confidence. A bounded
  discovery task can have a known E even when its eventual implementation is E?.
- Re-estimate when scope moves, discoveries change the plan or work is completed.
  Estimates may go up. Never subtract child scores from the parent, sum scores,
  average them, or convert them to a completion percentage.
- A validated Done transition records E0 and preserves the last nonzero estimate
  in history. Won't Fix means stopped scope, not zero work or successful completion;
  retain its estimate as historical and exclude it from remaining-work summaries.
  Reopening requires a new estimate or E? plus fresh acceptance evaluation.

### Proposed rubric v1

These qualitative anchors deliberately avoid hours and days. Calibrate against
completed, comparable work during the pilot before considering any separate time
forecast. Adjacent bands express increasing scope, not a fixed ratio.

| Band | Remaining own work | Typical invented example |
| --- | --- | --- |
| E0 | No active own work | Integration accepted; required child still awaiting its final gate |
| E1 | One tiny, well-understood action and verification | Correct a label and check its rendering |
| E2 | Small localized change with a straightforward test | Add a field validator and boundary cases |
| E3 | Several related edits within one component | Add a selector and its focused regression suite |
| E4 | Bounded feature spanning a few components | Add a read-only filter through model, URL and UI |
| E5 | Substantial feature slice with several test paths | Add a family summary and responsive navigation |
| E6 | Large slice with integration or meaningful uncertainty | Reconcile completion rules across a reducer and storage adapter |
| E7 | Several substantial slices or significant discovery | Add a new editing workflow and its conflict/retry behavior |
| E8 | Broad, multi-component outcome; decomposition strongly advised | Build hierarchy editing, validation, migration and UI together |
| E9 | Very large outcome with many distinct deliverables | Deliver an end-to-end board capability across multiple milestones |
| E? | Not yet estimated, or estimate invalidated | Newly discovered scope awaiting clarification |

E7–E9 prompt a decomposition review, not automatic card creation or a hard ban on
large cards. If the work cannot be bounded honestly, choose E? rather than E9.
P retains priority semantics: high effort must not silently lower priority. A high
priority card can be E?; it may need discovery rather than immediate implementation.

## 3. Subtickets are normal cards with explicit scope

Each child keeps a permanent internal ID and the board's normal display number
(for example, a K-number), plus its own title, owner, status, P/C/E, acceptance
criteria, dependencies, evidence, revisions and history. It is not a checklist row
or a number derived from its parent's ID. Renaming, reparenting and archiving do
not change its identity or break links. The synthetic demo retains invented IDs.

Recommended v1: one parent per child, one level of children, and relationships
within the same authorized board/profile only. A child cannot itself be a parent.
Cross-repository children within that board are allowed. Cross-board relationships
and deeper nesting need a later design, including access and bounded traversal.

### Logical fields and invariants

This is a domain proposal, not a new wire codec. Allocate actual record types and
schema versions in implementation review, preserving the existing strict codecs.

| Field or projection | Meaning |
| --- | --- |
| `parent_id: ID or null` | Stored on the child as the single source of parentage; roots use null |
| `required_for_parent: boolean or null` | True by default for a child; null for a root. False explicitly identifies optional follow-up scope |
| `parent_acceptance_stage` and `parent_acceptance_digest` | Required children bind the stage and acceptance contract they must satisfy for their parent; null for roots and optional children |
| `own_scope` and `acceptance_criteria` | Work and completion requirements this card alone owns |
| `effort_remaining`, estimate metadata | Nullable 0…9 plus rationale, rubric version and estimation evidence |
| `dependencies` | Separate prerequisite relationships with required acceptance stage/contract |
| Family summary | Derived from a coherent authorized snapshot; never a second editable child list |
| Execution/wait observations | Existing execution boundary where available; distinct from board status and family progress |

Validate missing parents, self-parenting, duplicate identities, multiple parents,
cycles, depth, incompatible scope and dangling references before committing any
change. Parent membership and requiredness changes are revisioned and audited.
Derived indexes must be rebuildable from canonical records. Unknown fields or
unsupported versions must fail explicitly, not be dropped on read/write.

Containment is not an instruction to execute and is not the same as a dependency.
A child does not automatically depend on its parent completing. A parent depends
on required children for completion, while siblings can run independently unless
an explicit dependency says otherwise. Detect cycles in the combined prerequisite
graph, including parent completion gates: a required child depending on its parent's
completion is invalid even if the standalone dependency graph looks acyclic.

Initial synthetic budgets: at most 256 cards, 32 direct children per parent, hierarchy
depth one, 1,024 combined prerequisite edges and a longest prerequisite path of 32
cards. These align the graph size with
the lifecycle experiment and are proposed limits, not production capacity claims.
Reject over-limit changes atomically. A paginated or partial snapshot must not be
mistaken for the complete family when evaluating completion or summaries.

### Splitting a card

1. Identify distinct deliverables, acceptance tests, owners, dependencies and waits.
   A child should be independently actionable and reviewable, not merely a sentence
   copied from the parent's description.
2. Preview the exact scope transferred to each proposed child and what remains on
   the parent. Keep integration and whole-outcome acceptance explicitly somewhere.
   No scope can silently disappear or be counted as owned by two cards.
3. Assign each child its own estimate. Re-estimate the remaining parent scope.
   Retain an old estimate only as labeled history, not as a family total.
4. Preview all new IDs, required/optional relationships, dependencies, initial
   status/P/C/E and expected revisions. New children start in Backlog unless a
   separate valid transition establishes another state. P/C suggestions may copy
   from the parent for review; they do not stay synchronized afterward.
5. In a later authorized editor, create children and update parent scope in one
   transaction with an operation key and expected revisions for every touched
   record. Same key and payload returns the original result; changed payload or
   stale revision conflicts. An unknown outcome is reconciled before retry.
6. Show the receipt and family summary. Splitting alone does not mark anything Done,
   start a worker, grant permission, or transfer action-specific approvals to children.

Existing children may be linked through the same preview and revision checks.
Detaching or reparenting a required child is an explicit scope decision: show the
old and new completion requirements, account for the abandoned/transferred work,
and re-estimate affected own scopes. Do not turn required work optional merely to
clear a gate. V1 cannot silently weaken the lifecycle foundation's immutable
requirements; any requirement-removal operation needs a separately reviewed policy
extension. Until then, reject it rather than fabricating a completed parent.

## 4. Family progress and completion

The parent represents the overall outcome but its E represents only its own work.
Show both prominently, for example:

> Own effort E2 · 3 of 5 required children Done · 2 required open · 1 blocked
> 1 optional child open · effort on 1 open child unknown

Counts are unique immediate children, include archived records, and distinguish
Done, open, blocked, optional and Won't Fix. Blocked is a subset of open; optional
children are labeled separately. An archived unfinished child still blocks. A
closed or archived parent is not evidence that its children are complete.

An optional family effort breakdown can list the own estimate and a histogram of
open children's bands, such as `parent E2; children E3 × 1, E5 × 1, E? × 1`.
No numeric total, weighted percent, implied ETA or “family E2” label is allowed.
Child-count progress is explicitly **count-based**, not effort-weighted. Unknown
or unavailable records produce an incomplete summary, never an optimistic zero.

### Completion gate

A parent is eligible for Done only when all these conditions hold at the current
coherent revision:

1. Its own acceptance criteria, integration and required evidence are satisfied.
2. Every required child is Done with the required accepted stage/contract and
   current evidence. A design-only child cannot satisfy a source/runtime gate.
3. Every explicit prerequisite is satisfied. Required PR links, exact final-head
   checks/reviews and required owner merge evidence remain independently required.
4. No unresolved blocker, unknown evidence, invalid relationship or stale snapshot
   prevents acceptance. Any required human action has actually occurred.

Eligibility is advisory until an authorized transition commits it with revision
checks. Never auto-complete from E0, a child count, a collapsed view or a PR's mere
existence. Done does not authorize merging or deployment. A verified transition may
set E0; manually setting E0 cannot establish the reverse implication.

| Event | Required behavior |
| --- | --- |
| All children finish but parent integration remains | Parent stays open with its own E and next action |
| Parent own work finishes before children | E0 is allowed; parent stays open and shows outstanding required children |
| Required child becomes Won't Fix | Parent cannot become Done; require an explicit scope decision or also stop the parent |
| Optional child remains open | It does not gate Done; preserve it as a normal visible card with its parent link |
| Required child is archived unfinished | Still blocks; show an archived-child warning and authorized navigation |
| Required child reopens after parent Done | Atomically reopen the parent to Blocked with a reason and fresh acceptance evaluation, preserving prior completion history; parent own effort becomes E? until re-estimated, possibly E0 |
| Evidence is later invalidated or a change is reverted | Surface invalid acceptance; reconcile through a new revision/transition, never erase the old receipt |
| Parent is archived | Do not cascade archive, status or deletion to children; archive is presentation membership only |

The reopen cascade is a proposed future domain behavior, not implemented by today's
advisory reducer. If an adapter cannot commit the dependent transition atomically,
it must show an invalid/incomplete result and block new completion until reconciled.
No client-only “Done” state can override the authoritative acceptance evaluation.

## 5. Board and card UI

### Normal board remains the default

Render each card exactly once in its own status lane, including children. A child
shows its P/C/E and a parent link. A parent offers a **Subtickets** disclosure with
compact child references, status, E and required/optional labels. These references
are not duplicate draggable cards and do not increment lane or facet counts.
Parent details, child disclosure and lane collapse are independent preferences.

Collapsing a parent cannot hide a child's normal board card. A separate family
detail view may group children, but must label their real status and preserve their
normal links. Do not add grouped-lane drag behavior in the first milestone.

Show E with an accessible label such as “Own remaining effort: E3” or “Remaining
effort not estimated.” Do not rely on color. Put the family summary next to the
parent's E so a small own estimate cannot look like whole-outcome completion.

### Filters, sorting and counts

- Add E0…E9 and E? as a facet. Retain zero-count options and the existing rule:
  a facet's counts apply every active constraint except that facet's own choice.
  Effort matches each card's own value, not a child's or a family total.
- Add hierarchy facets: **All cards**, **Parents**, **Subtickets**, **Standalone**,
  and an exact parent/family selector. Parents means cards with at least one child;
  Standalone means no parent and no children. No silent default hides subtickets.
- Search children independently, including their stable IDs. Matching a child does
  not make its parent a matching result. A context breadcrumb can show the parent
  when authorized, explicitly excluded from match and lane counts.
- Archive selection remains per card. Family summaries still account for archived
  children; family details label records outside the selected archive view.
- Provide effort ascending/descending sorts with E? last in both directions and
  the existing stable tie-breaker. Do not silently replace priority ordering.
- Counts use unique card IDs before rendering compact references or temporary
  deep-link reveals. Filtering and collapsing never alter authoritative WIP.

### Navigation, editing and accessibility

Preserve deep links, Back/Forward, Dismiss/Escape, saved collapse preferences and
scroll/focus restoration. A filtered or archived child opens through the existing
temporary reveal mechanism without changing filters or expanding every ancestor.
Repeated navigation must not duplicate history entries. When revealed content is
dismissed, return focus to the initiating control if it still exists, otherwise a
stable board heading. New reads must not overwrite a newer navigation generation.

Use real buttons/links, `aria-expanded`, labeled regions, visible focus, keyboard
operation and concise announcements. Test nested disclosure controls without nested
interactive elements. Family summaries wrap on narrow screens and at 200% reflow.
Reserve space during loading; a failed family read must not show zero children.

The initial milestone stays read-only. Future **Create subticket**, **Split scope**,
**Link existing**, **Reparent** and **Estimate effort** flows require a separate
authorized write boundary. They must show previews, validation errors, pending,
conflict and unknown states; preserve drafts on failed writes; and never signal
success until a receipt is verified. Cancel has no effect. Disallow duplicate
submission while reconciling the same operation key. Untrusted titles/history are
rendered as inert text, as in the current synthetic UI.

## 6. WIP and waiting

Recommended rule: **one slot per distinct card actively executing its own work**.
An actively implementing child consumes one slot. A parent consumes an additional
slot only while its own integration, implementation or acceptance work is actively
executing. A parent merely summarizing active children consumes no extra slot.
Counting only leaves would miss real parent work; counting every open ancestor
would double-charge coordination.

Keep the board's existing numerical WIP limit. This proposal changes attribution,
not the limit, staffing or scheduling permissions. Work eligibility still depends
on the existing policy, time restrictions, dependencies and action authorization.

Use explicit execution/wait observations, not E or inherited family status, to
derive slots. Multiple workers on one card still count as one card, with separate
worker-capacity accounting. A requested pause/cancel does not release a slot until
execution has actually stopped. Queued reservations must remain separately visible
and block overbooking. Admission counts the union of active and reserved card IDs,
so a reservation turning into execution does not consume a second slot. Unknown
execution state is shown as unknown and prevents
assuming spare capacity; a low E or archived state never frees a running slot.

Blocked, review-waiting and scheduling-waiting cards do not consume an active slot
once stopped and unreserved, but appear in separate waiting counts with next actor
and unblock condition. Waiting parents still appear open on the board. The initial
demo can display invented observations; it must not imply a live scheduler exists.

## 7. Consistency, compatibility and rollout

### Read and write contracts

Derive family counts, completion eligibility and WIP from one authorized snapshot
and expose its revision. For future online use, authorize every referenced card
before disclosure, including counts, breadcrumbs, filters and errors. A partial
reader sees “family status unavailable,” not private IDs or an aggregate that
reveals hidden work. Completion evaluation requires complete privileged access at
the policy boundary; client knowledge cannot grant it.

Reuse the lifecycle foundation's compare-and-swap and retained idempotency concepts
for future writes. A split, reparent, reopen or completion operation must validate
the whole affected graph and either commit all intended records or none. On stale
read, refresh and preview again. Do not silently merge conflicting scope edits.
Keep scope changes and estimate reasons in immutable history. Approval references
remain evidence; moving scope cannot copy executable authority to a new identity.

### Compatibility and migration

1. Add a versioned synthetic presentation schema/reader. Existing invented records
   explicitly upgrade to root cards with E?; never guess effort or parentage from
   title, prose, status, P or C. Keep the old fixture codec's behavior explicit.
2. Design versioned lifecycle records and readers before persistence changes.
   Unsupported old/new schema combinations fail clearly. Do not silently alter
   canonical bytes or rewrite existing history. A tested explicit upgrade is
   necessary before old stores can accept new records.
3. Keep legacy CLI JSON, online adapters and private data untouched until their own
   implementation/migration approval. Do not make missing/corrupt new storage look
   like an empty board through the legacy loader's permissive fallback.
4. Any eventual private migration follows the
   [backup/restore contract](resumable-backup-contract.md): complete inventory,
   archive/history and relationship preservation, coherent snapshot, quarantine,
   independent restore/re-export checks, single-writer cutover and rollback plan.
   Update compatibility manifests so old readers cannot drop new fields.
5. Pilot one large, authorized card only after synthetic acceptance and the write
   boundary are qualified. Record original scope and estimate, transfer every
   acceptance criterion, verify counts and links, and review whether the next
   action is clearer. Do not bulk-split the backlog automatically.

Rollback of a presentation-only release can disable new controls while retaining
the data. Once hierarchy records exist, an old writer must not run against them.
Rollback must preserve new records/history and use a compatible reader or a reviewed
forward repair. Deleting children to restore a flat view is not a rollback strategy.

## 8. Acceptance scenarios

The following are planned gates, not tests executed by this documentation PR.

| ID | Fixture or action | Expected result |
| --- | --- | --- |
| A1 | Split invented parent E8 into three children E3/E5/E?; remaining parent integration E2 | Parent shows own E2 and complete family counts; no arithmetic total or implied percent |
| A2 | Parent E0, required child open, all other evidence valid | Done rejected with the exact unsatisfied child gate |
| A3 | Required children Done, parent integration incomplete | Done rejected; parent own work remains visible |
| A4 | Required child Done at design stage, parent needs source/runtime | Required stage mismatch blocks completion |
| A5 | Required child archived, Won't Fix, missing, or unreadable | No false Done; distinct blocked/incomplete or privacy-safe unavailable result |
| A6 | Optional child open, required children and parent acceptance satisfied | Parent eligible; optional child stays visible and open |
| A7 | Required child reopens after parent completion | Reopen reconciliation preserves historical receipt and prevents a current Done claim |
| A8 | Duplicate split, concurrent scope edit, or lost write acknowledgement | One coherent outcome; same operation reconciles; conflict does not create extra children |
| A9 | Self-parent, cycle, grandchild, cross-board edge, missing target or over-limit family | Atomic rejection; previous graph and history unchanged |
| A10 | Child depends on the completion of its own required parent | Combined prerequisite-cycle rejection |
| A11 | Collapse parent, then search/filter/deep-link child in another status or archive view | Child remains discoverable; reveal/dismiss restores filter, focus and scroll state |
| A12 | E? alongside E0/E9; combined facets, ascending/descending sorts | No unknown-to-zero conversion; stable sort and coherent unique-card counts |
| A13 | Two active children, coordinating parent; then parent integration starts | WIP changes from two to three; collapsing/filtering has no effect |
| A14 | Worker stop requested, stale observation or expired reservation | No premature capacity release; uncertain capacity blocks new admission |
| A15 | Old fixture/store, unsupported schema, incomplete snapshot or interrupted upgrade | Explicit upgrade/incompatibility path; no guessed fields or lost records |
| A16 | Hostile titles/history, private-data canaries, unexpected network/storage effects | Inert display; no private material or live effects in synthetic source/build/evidence |
| A17 | Keyboard-only navigation at narrow widths and 200% reflow across supported browsers | Usable disclosures, labels, focus and summaries without clipping or traps |

Use invented parent `demo:harbor/release` with children `demo:harbor/model`,
`demo:harbor/view` and `demo:harbor/checks` as a baseline, then generate edge cases.
Keep stable IDs independent of displayed text. Test completion and WIP reducers
without UI as well as end-to-end presentation journeys. Record tested commit,
fixture/rubric/schema versions, actual outcomes and skipped/unrun stages. A passing
synthetic test is not evidence of production migration, permissions or durability.

## 9. Proposed card backlog

These are **planning keys, not allocated Kanban IDs**. Each section can become one
normal card after explicit scheduling approval. Initial state is Backlog; owner and
P/C are assigned in triage under the existing board conventions. E values are
provisional own-effort estimates using rubric v1 and must be re-estimated once scope
and implementation permission are settled. Dependencies below describe sequencing,
not grants to execute. Each card should retain this design link and its acceptance IDs.

### ST-01: Confirm effort and hierarchy rules

- **Outcome:** A reviewed decision record for rubric v1, single-level hierarchy,
  required/optional children, WIP attribution and reopen behavior.
- **Scope:** Resolve section 10; identify the target product milestone and existing
  P/C vocabulary. Define evidence needed to call each later slice complete.
- **Acceptance:** No ambiguous E0/E? meaning; no effort arithmetic; named decisions
  for all gates. Design approval and implementation permission recorded separately.
- **Dependencies:** None. **Estimate:** E2. **Checks:** A1–A7, A13 concept review.

### ST-02: Define versioned hierarchy records

- **Outcome:** A reviewed domain schema and compatibility plan for parentage,
  requiredness, own scope, E estimates and snapshot-derived family data.
- **Scope:** Map to existing records without modifying legacy CLI storage; define
  typed errors, limits, schema upgrades and strict unknown-field behavior.
- **Acceptance:** Old data has an explicit root/E? upgrade; IDs/history preserved;
  examples cover required/optional/root records and unsupported readers.
- **Dependencies:** ST-01. **Estimate:** E3. **Checks:** A9, A15.

### ST-03: Validate family and dependency graphs

- **Outcome:** Pure validation and family-summary functions with invented tests.
- **Scope:** Parent indexes, combined prerequisite cycles, depth/size bounds,
  archived children, incomplete snapshots and unique-count semantics.
- **Acceptance:** A1/A5/A9/A10 pass; no partial graph mutation, double counts,
  arithmetic E rollups or optimistic summaries for incomplete input.
- **Dependencies:** ST-02. **Estimate:** E4. **Checks:** A1, A5, A9, A10.

### ST-04: Gate parent completion and reopening

- **Outcome:** Advisory completion evaluation and a specified reopen transition
  plan covering own acceptance and every required child's accepted stage.
- **Scope:** Required/optional/Won't Fix semantics; exact evidence and multi-PR
  gates; stale snapshots; preserved completion history. No merge/deploy executor.
- **Acceptance:** A2–A7 pass; E0 never grants completion; reopened child invalidates
  current parent acceptance; no weakening of immutable requirements.
- **Dependencies:** ST-03. **Estimate:** E5. **Checks:** A2–A7, A15.

### ST-05: Add synthetic hierarchy and effort fixtures

- **Outcome:** Versioned read-only presentation model and newly invented scenarios.
- **Scope:** E0–E9/E?, parent links, required/optional children, wait observations,
  archive combinations and schema errors. Keep P/C compatibility explicit.
- **Acceptance:** Existing fixture upgrade tested; immutable copies validated;
  delayed/failed/partial reads never appear as a complete empty family.
- **Dependencies:** ST-02, ST-03. **Estimate:** E3. **Checks:** A1, A5, A12, A15, A16.

### ST-06: Add effort and hierarchy selectors

- **Outcome:** Pure filters, facets and stable sorting over the synthetic model.
- **Scope:** E and hierarchy facets, exact family selection, independent child
  matches, archive behavior and unique-card counting.
- **Acceptance:** A12 passes with combined filters; E? last in both sort directions;
  context references/reveals excluded from counts; no UI state changes domain data.
- **Dependencies:** ST-05. **Estimate:** E3. **Checks:** A11, A12.

### ST-07: Show collapsible subtickets and summaries

- **Outcome:** Read-only parent summaries, child badges/links and compact disclosures.
- **Scope:** Own E label, family counts/uncertainty, independent collapse controls,
  effort/hierarchy filter controls and responsive layout.
- **Acceptance:** A1/A11/A12/A17 pass; one normal card per ID; child visibility
  independent of parent collapse; current six status lanes preserved.
- **Dependencies:** ST-05, ST-06. **Estimate:** E4. **Checks:** A1, A11, A12, A17.

### ST-08: Preserve family navigation and accessibility

- **Outcome:** Verified parent/child deep-link journeys across board and archive.
- **Scope:** Temporary reveals, repeated navigation, Back/Forward, pending-read
  races, Dismiss/Escape, focus restoration and screen-reader labels.
- **Acceptance:** A11/A17 pass in Chromium, Firefox and WebKit at existing supported
  widths; no unexpected external requests or record persistence. Add browser evidence
  and update the parity ledger without claiming live-board equivalence.
- **Dependencies:** ST-07. **Estimate:** E4. **Checks:** A11, A16, A17.

### ST-09: Attribute WIP and waiting separately

- **Outcome:** Pure active-card/reservation/wait accounting and read-only display.
- **Scope:** Own work versus coordinating parent; distinct worker capacity;
  uncertainty, stop acknowledgement and unchanged numeric limit.
- **Acceptance:** A13/A14 pass; no counts derived from filters, E, archive or inherited
  status; unknown capacity cannot admit new work. No live scheduler is introduced.
- **Dependencies:** ST-03, ST-05, ST-07. **Estimate:** E4. **Checks:** A13, A14.

### ST-10: Implement transactional family commands

- **Outcome:** Separately approved synthetic write boundary for split/link/reparent,
  effort updates and dependent reopen/completion, with receipts and conflict handling.
- **Scope:** Versioned lifecycle extension and storage upgrade; complete affected
  revision checks, operation-key reconciliation, fault injection and current policy
  checks. Requirement removal stays blocked until its own policy design is accepted.
- **Acceptance:** A8/A9/A15 pass; atomic scope transfer; unknown outcomes cannot
  duplicate cards; no legacy/live adapter wiring or automatic execution.
- **Dependencies:** ST-02, ST-03, ST-04, ST-09. **Estimate:** E6. **Checks:** A7–A10, A14–A16.

### ST-11: Add reviewed hierarchy editing flows

- **Outcome:** Separately approved editor for split scope, create/link child,
  reparent and estimate updates over the qualified write boundary.
- **Scope:** Before/after scope preview, requiredness, P/C/E choices, pending/conflict/
  unknown states, cancellation, draft retention and receipt reconciliation.
- **Acceptance:** A8/A9/A11/A17 pass; duplicate submit safe; Cancel writes nothing;
  controls never imply authorization to execute, merge, deploy or disclose data.
- **Dependencies:** ST-08, ST-10. **Estimate:** E5. **Checks:** A8, A9, A11, A16, A17.

### ST-12: Qualify compatibility and pilot plan

- **Outcome:** Reviewed upgrade/rollback evidence, operator checklist and one-card
  pilot proposal. No private data movement is part of this card by default.
- **Scope:** Synthetic round-trip/restore fixtures, old-reader rejection, archive and
  history preservation, scope coverage checklist, feature rollback and calibration.
- **Acceptance:** A15/A16 pass; explicit gate before any private import, live writer
  or publication; pilot names its authorized destination and exact work separately.
- **Dependencies:** ST-04, ST-08, ST-09, ST-10, ST-11. **Estimate:** E4. **Checks:** A1–A17 review.

### ST-13: Run approved single-card pilot

- **Outcome:** One explicitly authorized large card decomposed with verified scope,
  effort, family counts, next actions and no loss of history.
- **Scope:** Only after implementation, adapter qualification and private-pilot
  approval. Compare before/after scope and usability, then record rubric adjustments.
  Do not copy private evidence into public artifacts or automatically extend rollout.
- **Acceptance:** Parent acceptance criteria mapped exactly; no duplicated or lost
  work; links and WIP agree; each required child has an owner and acceptance test;
  decision to expand rollout remains explicit.
- **Dependencies:** ST-12 and separate live-use authorization. **Estimate:** E?.
  Re-estimate after pilot scope and operational prerequisites are known.

### Delivery sequence and stop points

1. **Design:** ST-01–02. Review schema/rubric and authorize only the desired slice.
2. **Pure domain and read-only demo:** ST-03–09. Domain work and presentation work
   can proceed in parallel along their stated dependencies. Run repository lint,
   Python tests, pre-commit, web type/unit/build/browser checks and privacy review
   as applicable to the final commit. Update documentation and the parity ledger.
3. **Qualified synthetic editing:** ST-10–11 only after separate approval and a
   reviewed version/upgrade contract. Keep real adapters disconnected.
4. **Compatibility and pilot:** ST-12; ST-13 remains blocked on explicit live-use
   approval and operational qualification. No bulk migration follows automatically.

Each card produces a focused reviewable change and evidence for its acceptance IDs.
Do not close the overall feature merely because the read-only demo is complete.
No delivery date or aggregate E is assigned by adding these estimates together.

## 10. Decisions to confirm before implementation

| Decision | Recommended default | Why it remains a decision |
| --- | --- | --- |
| Effort calibration | Qualitative rubric v1, no hours/ETA mapping | Actual examples may reveal bands that need adjustment |
| Depth and scope | One level, one parent, same board/profile | Deeper or cross-board hierarchies need additional validation and access rules |
| Optional work | Explicit optional children allowed; required is default | Owner must agree how follow-up scope is distinguished from committed outcome |
| Completion reversal | Required-child reopen atomically reopens parent to Blocked | Must align with the approved lifecycle transition policy and storage capability |
| WIP attribution | Active own-work cards plus separate reservations; preserve limit | Existing executor semantics must be mapped before live admission changes |
| P/C presentation | Preserve existing board meanings; explicitly map synthetic vocabulary | Current demo is not the full production P/C model |
| First destination | Axel synthetic read-only demo | A private-board implementation or write adapter is separate scope |
| Pilot and migration | One owner-selected card after qualification | Actual card, destination, permissions and recovery plan are not chosen here |

Review should settle these choices, then convert the planning keys into real cards
with current P/C/E, owners and links. The public design can be accepted independently
of implementation, live-board adoption, data migration or deployment.
