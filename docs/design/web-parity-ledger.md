# Web presentation parity ledger

This is a rolling scope ledger, not a claim of complete product parity. It records
the synthetic presentation subset only. No private source snapshots, board data,
owner quotations or operational receipts belong in this document. Future changes
must update the applicable row and evidence without treating fixture success as
proof of migration or online behavior.

| Capability | Synthetic implementation | Evidence / remaining boundary |
| --- | --- | --- |
| Six status lanes | Ordered lanes; terminal status distinct from archive | Fixture and selector tests; browser board/archive journey |
| Detail and history | Expandable, literal read-only text; explicit revision and ID | Model validation, hostile markup and browser detail tests |
| Search and six filters | Combined constraints; stable facet vocabulary and coherent counts | Individual/combined filters, zero counts and archived-only records |
| Stable sorting | Fixture, title, priority and revision; deterministic ties | Selector tests, browser sort control |
| Collapse and stretch | Presentation preferences only | Browser persistence and lane restore journeys |
| Permanent links | Scroll without altering collapsed state; temporary hidden/archive reveal | Repeated links, Dismiss/Escape, browser history and pending-scroll tests |
| Async reads | Bundled normal/slow/error/empty fixture responses | Generation race and retry tests; no live reader |
| Responsive and keyboard views | Compact responsive lanes, focus indicators, labels and announcements | Chromium/Firefox/WebKit automation; 320–2560 CSS pixels; CSS zoom reflow probe |
| No live effects | Local built assets; no runtime dependency, remote resource or task mutation | Request-denial test, storage assertions and independent source/artifact review |
| Editing and approvals | Excluded | No controls or authority engine |
| Import/export and migration | Excluded | Existing design contracts remain authoritative; no fidelity claim |
| Authentication and integrations | Excluded | No login, API, worker ownership, credentials or deployment |
| PDF previews | Excluded | No preview engine |

See [milestone design](web-milestone-one.md) and [local demo instructions](../../web/README.md).
