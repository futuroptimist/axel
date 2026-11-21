# Hierarchy and effort decision record

**Status: proposed for review, 2026-11-08.** This is the ST-01 deliverable from
[the subtickets design](kanban-subtickets-effort.md). Preparing this record does not
accept its decisions or authorize implementation. ST-02 may be prepared against
these explicit assumptions; it cannot be called accepted before ST-01 is reviewed.
No board records, runtime behavior, storage or permissions change here.

Baseline inspected: `cf44d14234cb58126a799eeef7d3c037535e3173`.
Reviewed against the merged [dependency design](kanban-dependency-management.md),
which retains the separate DG review and pilot gates. This record does not accept
those decisions or register dependencies.

## Decisions requested

Decision metadata for D1–D8: status **proposed**; proposer **assistant**;
proposal date **2026-11-08**; reviewer and acceptance date **not recorded**.

Each row is **proposed**, with no recorded reviewer decision. Review should accept
or amend each row, identify the reviewed revision, and separately identify any
implementation slice authorized to proceed. A merged proposal alone is not a
runtime, editing or migration approval.

| Key | Proposed decision | Evidence required for acceptance |
| --- | --- | --- |
| D1 | Retain the design's qualitative rubric v1: E0–E9 measure remaining own work; null renders E?. No arithmetic rollup, hours or ETA mapping. | Review examples below and acceptance scenarios A1–A7. |
| D2 | One parent per child, one child level, same board/profile; cross-repository relationships allowed inside that scope. | Review root/required/optional examples and combined-cycle/limit cases in the schema plan (A9/A10). |
| D3 | Children are required by default; optional children explicitly represent follow-up scope. | Confirm optional work remains visible and does not gate the parent. Removing a requirement remains separately gated (A5/A6). |
| D4 | A required child reopening invalidates parent acceptance immediately. Keep that internal gate separate from the visible lane. The original design proposes Blocked, but an adapter may reserve that lane for owner-actionable waits. | Resolve lane policy explicitly before implementing a transition (A7); preserve history and fail closed until coherent status reconciliation succeeds. |
| D5 | Count cards doing active own work and reservations separately from waits. A coordinating parent consumes no active slot unless it also performs own work. Preserve the configured numeric limit. | Review two-child/parent-integration and uncertain-stop examples (A13/A14). No live admission control changes. |
| D6 | Preserve existing P/C semantics. The synthetic web fixture retains P0–P4/Unranked and Clear/Needs detail; no invented conversion to another board's scale. | Inspect the actual web model and verify independent P/C/E labels. An adapter needs its own explicit vocabulary mapping. |
| D7 | First product destination is Axel's synthetic read-only demo, with isolated pure domain functions. | Review ST-03–09 boundaries; no legacy CLI, online adapter, live worker or real records. |
| D8 | Any live pilot is one separately selected card after editing, adapter and recovery qualification. | ST-12 plan must name the proposed destination, scope, recovery evidence and later authorization needed for ST-13. No card is selected here. |

## Rubric v1 review examples

The canonical band definitions remain in the original design. These examples
clarify how to apply them; they do not assign estimates to real work.

- A tiny label correction plus rendering verification is E1; a local field
  validator and boundary cases is E2. Remaining tests and review fixes count.
- An invented selector and focused regressions is E3; a filter spanning model,
  navigation and UI is E4. Adjacent bands are qualitative, not fixed ratios.
- A substantial family-summary slice may be E5; integration across reducer and
  storage with meaningful uncertainty may be E6. List assumptions separately.
- E7–E9 prompt decomposition review. Choose E? when the scope cannot be bounded;
  do not use E9 as a substitute for admitting uncertainty.
- Splitting parent E8 into children E3/E5/E? and remaining integration E2 yields
  **own E2** and a child-band breakdown. It never yields a numeric family total,
  completion percentage or forecast. Preserve the original E8 in history.
- A parent with no remaining own work can be E0 while a required child is open.
  The parent stays open. If its own acceptance work remains, use nonzero E or E?.
- Waiting for an external reviewer does not increase E. Known fixes the card owns
  do count; uncertain fixes belong in assumptions/questions until estimated.
- A scope change invalidates the current estimate to E? until an accepted
  re-estimate binds the new task revision. Retain the old value as history.
- Done requires acceptance evidence and records E0 on the validated transition.
  Setting E0 never establishes Done. Won't Fix retains a historical estimate and
  is excluded from remaining-work summaries. Reopening needs a fresh estimate
  or E?, even when a later assessment restores E0.

Estimate provenance consists of rationale, estimator label, timestamp, task
revision and rubric version. An estimator label is attribution, not authenticated
authority. Assumptions, unresolved questions and waits remain separate from C.

## Completion and scope gates

Required children bind an acceptance stage and exact contract digest. A design
result cannot satisfy a source/runtime requirement. Optional open children stay
visible. Missing, archived-unfinished, unreadable and Won't Fix required children
must never produce an optimistic complete family. Count-based child progress is
labeled as such and does not replace parent integration or its own acceptance.

A dependency is directed from the dependent to its prerequisite. Required
parent-child completion gates point from parent to required child. A required
child depending on its parent's completion is therefore a combined-graph cycle.
Containment alone neither starts a worker nor adds a child-to-parent prerequisite.

## Reopening and lane policy require a separate decision

The original proposal's unconditional reopen-to-Blocked must not silently override
a target board's status semantics. Recommended refinement: first invalidate current
acceptance and expose a separate internal prerequisite gate. A qualified writer
then atomically replaces the parent's current Done claim with a policy-approved
open lane and records the reason, preserving the prior completion receipt. If no
own work is active and no owner action can unblock it, Backlog is the proposed
waiting lane; In progress requires actual active own work. Blocked is appropriate
only when the selected board policy and next actor justify it.

Until that mapping and transaction are reviewed, a reader reports invalid current
acceptance and pending status reconciliation, excludes the parent from accepted-Done
counts, and refuses new completion/admission decisions that depend on it. It does
not rewrite stored status client-side or pretend a multi-record transition occurred.
The public synthetic demo must label this distinction instead of asserting live
board parity. The pending choice is whether to amend the original synthetic rule
to this explicit policy mapping or retain its fixed lane only for that demo.

## Review and delivery boundaries

| Slice | Deliverable and evidence | Stop point |
| --- | --- | --- |
| ST-01 | This decision record, reviewed D1–D8 and concept coverage A1–A7/A13 | Record explicit disposition before claiming rules settled. |
| ST-02 | [Versioned schema and compatibility plan](kanban-hierarchy-schema.md), reviewed examples and A9/A15 test specification | Schema acceptance is separate from permission to implement it. |
| ST-03–09 | Pure validators/selectors and synthetic read-only UI, with relevant A1–A17 tests, final-commit checks and review | No implied editing, live effects or production parity. |
| ST-10–11 | Separately approved synthetic commands/editor plus atomicity, conflict, cancellation and upgrade evidence | Keep real adapters disconnected. |
| ST-12 | Compatibility evidence and bounded pilot proposal | No private data movement. |
| ST-13 | Separately authorized single-card pilot with scope/history preservation and calibrated estimates | Expansion requires another explicit decision. |

Open review items are D1–D8, the schema identifiers and transition policy in ST-02,
and the exact implementation slice to authorize. There is no accepted decision,
implementation completion, live migration or deployment evidence in this record.
