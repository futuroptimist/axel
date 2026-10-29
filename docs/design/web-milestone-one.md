# Synthetic web board: milestone one

This slice adds a local read-only presentation demo in `web/`. It does not change
the Python CLI or implement a backend. All twelve tasks, names, opaque IDs,
revisions and history entries are invented specifically for the fixture.

## Boundaries

`model.ts` validates and copies a presentation model with opaque identity, explicit
revision, separate status/archive fields and ordered inert history. The six status
labels are Backlog, In progress, Blocked, Ready for review, Done and Won't Fix.
Neither terminal status nor historical text implies an action or authority.

`fixture-reader.ts` is the sole asynchronous read boundary. It returns frozen,
validated copies of bundled data. Scenarios simulate delay, error and empty data.
The loader clears the visible generation while loading and publishes only the
newest response, including when older failures or successes settle later.

`selectors.ts` combines search with repository, workstream, status, type, clarity
and priority. Facets enumerate the whole invented vocabulary; counts respect the
view and every other filter. Stable sorting uses original order for ties and puts
unranked priority after ranked values. Selectors do not modify fixture records.

`navigation.ts` encodes view/filter/target state in local URLs. A task link scrolls
to its card without changing collapse preferences. If filters or archive membership
hide it, the target appears in a temporary reveal region. Dismiss and Escape return
to the prior view and focus; browser history restores navigation state. Repeated
clicks on the current target do not add history entries. User scrolling cancels a
pending automatic deep-link scroll. Presentation preferences are the only browser
storage data; records and drafts never persist there.

`render.ts` builds DOM elements and assigns untrusted content through `textContent`.
The synthetic banner remains visible in every state. Loading placeholders reserve
space but contain no actions. Empty and failed reads are explicit; Retry requests
the normal scenario. Help describes the available views and exclusions.

## Evidence and limits

The [web README](../../web/README.md) records commands and pinned tooling. Unit
tests exercise validation, selectors, fixture coverage and asynchronous generation
races. Browser suites exercise navigation, display preferences, keyboard controls,
responsive widths, simulated 200 percent zoom, and built-asset no-live-effects
checks. Unexpected requests or external navigation fail the latter test. Layout
shift observations are descriptive only. Screenshots and browser runs are synthetic
automation evidence, not physical-device or production qualification.

The frontend workflow has read-only repository permissions and no deploy job or
credential requirement. Build outputs, source maps, logs and screenshots must be
reviewed for public-source cleanliness before a review handoff. A green build is
not deployment, and a skipped check is not a pass. Exact head, hashes, CI results,
independent review and automated reviewer findings belong in PR delivery evidence.

## Later work

The [sanitized application contract](sanitized-kanban-contract.md) and
[resumable backup contract](resumable-backup-contract.md) remain the references for
future implementation. This fixture is not a storage format, codec, importer,
exporter or live adapter. Before real migration, establish inventory, canonical
typed encoding, identity/history mappings, quarantine validation, independent
restore/re-export proof, freshness, single-writer cutover and rollback. None of
those operations, tenant authentication, approval engines, worker ownership,
online integrations or PDF previews are implemented here.
