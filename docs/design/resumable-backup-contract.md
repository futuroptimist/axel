# Bounded resumable backup and restore design

**Status: proposed, documentation only. Reviewed 2026-10-09.** This document
specifies an offline-first backup contract for Axel's future owner-local workspace
and compatible storage adapters. It does not add a backup command, select a deployed
database, create a snapshot, migrate data, or authorize implementation or deployment.

The recommendation is to separate coherent capture, deterministic serialization,
durable transfer and independent restore verification. Start with a local adapter
and synthetic fixtures. A hosted D1 adapter is a conditional, separately reviewed
option for an already authorized hosted dataset. D1, R2, Internet access and model
inference are never dependencies of the owner-local backup path.

## Privacy and integrity invariants

These requirements govern every adapter, retry, restore and later rollout.

| ID | Required invariant |
| --- | --- |
| B1: local privacy | Sensitive-profile source data, captures, manifests, checkpoints, restored data and backup UI remain on the owner's harness device in encrypted, access-controlled storage. No cloud-sync directory, remote backup agent, telemetry, hosted logs or inference service receives them. |
| B2: separate authority | Capturing or validating a local backup does not authorize outward sharing, cleanup, schema migration, production restore, credential creation, merge or deployment. A backup identifier, hash, cursor, file or model output cannot grant access or execution authority. |
| B3: one coherent source | Each completed snapshot represents one committed application state, including its referenced files. All source tables, history, principals and schema within the approved inventory are preserved. Mixed-time pagination and silent omission are failures. |
| B4: immutable identity | A sealed snapshot, manifest and chunk identity never change bytes. Resume is bound to exact source namespace, snapshot, format and manifest digest. A replacement capture has a new identity. |
| B5: bounded work | Memory, CPU time, response size, index size, concurrency, storage and retries have explicit enforced budgets. A small page response is insufficient if producing it materializes the whole database or an oversized cell. |
| B6: durable progress | Validated durable bytes are authoritative. A checkpoint is a cache. A timeout, last chunk, progress counter or successful capture alone never proves a complete recoverable backup. |
| B7: exact logical restore | Completion requires independent, isolated restore proof of the entire declared source inventory, exact supported values and history. Normalization is explicit; physical database-file identity is not promised. |
| B8: fail-closed recovery | Restored approvals, consumed action keys, revocations and trust state cannot revive old authority. Unknown freshness or interrupted state blocks dispatch, sharing and source promotion. |
| B9: preserve recovery points | No automatic deletion, implicit expiry renewal or eviction is introduced. The owner must select retention and recovery policy before real data. At capacity, fail visibly while preserving existing verified artifacts. |

This follows the proposed
[private LAN planning contract](https://github.com/futuroptimist/axel/blob/5632350c20c0a3dc6aac2ce3024047518d506901/docs/design/chat-operations-contract.md)
in [PR #249](https://github.com/futuroptimist/axel/pull/249), which is still separate
from main at review time. Its sensitive profile keeps the corpus and UI device-local;
only minimum approved inference context may reach enrolled private-LAN token.place
compute. Inference enrollment does not grant backup, filesystem or UI access.
This backup design needs no inference. General token.place federation remains outside
this profile and is unchanged.

## Goals and non-goals

### Goals

- Capture an auditable coherent state and finish downloading it despite later edits.
- Resume after process loss using validated local files, including sparse chunks.
- Detect corruption, omissions, schema drift, mixed snapshots and unsupported types.
- Preserve raw source values, every included history generation and original identity.
- Verify full restore offline before claiming recoverability.
- Make storage-specific feasibility, performance costs and approval gates explicit.

### Non-goals

- Implement a server, downloader, restore tool, database migration or retention job.
- Export private workspace content to GitHub, chat, cloud storage or remote agents.
- Treat an existing task-list JSON file as a transactional workspace database.
- Select D1 shadow tables or provision cloud capabilities by approving this design.
- Promise progress during unlimited write churn, unlimited size or unavailable storage.
- Automatically pause writers, remove history, compact source data or delete backups.
- Restore into production, overwrite an existing workspace or replay restored actions.

## Existing implementation and proposed boundary

Axel's [README](../../README.md) describes local task files, repository management,
analytics and token.place helpers. It does not establish this snapshot protocol or
the sensitive-profile isolation guarantees. PR #249 is also a design proposal.
Nothing in this document should be reported as implemented or production-tested.

For an existing producer, a local reconciler can validate saved chunks and propose
a contiguous prefix without changing that producer. A future durable downloader
can improve interrupted-transfer behavior while retaining that producer's limits.
Neither improvement proves that a live paginated source is coherent, that producer
state is quiescent, or that rounded source integers were captured losslessly.

The portable core has four roles:

1. **Capture adapter:** attest a coherent, immutable source view and its lifetime.
2. **Encoder and manifest builder:** deterministically enumerate that view in bounded
   steps, publish authenticated metadata and hashes, then seal the manifest.
3. **Local downloader:** validate and durably store chunks without trusting memory
   counters or blindly repeating an operation with an unknown outcome.
4. **Verifier and restore runner:** reconstruct the declared logical state into a
   new isolated destination and issue a local completion record only after proof.

These roles may share a local process, but their state transitions remain explicit.
An optional network adapter must use the same contract without broadening privacy
or authorization. Serialization into a device-local artifact is distinct from
publishing that artifact to a different audience.

## Coherent capture and adapter choices

### Capability preflight

Before any capture write, the adapter must verify and record:

- Source engine/version, schema inventory, encoding, identity and approved scope.
- Supported snapshot primitive, consistency boundary and durable lifetime.
- Read/write permissions actually available through supported interfaces.
- Transaction, query, cell, response, storage and invocation limits.
- Capacity for capture, temporary files, index, final artifact and restore proof.
- Process-wide or cross-process concurrency enforcement, cancellation semantics,
  idempotency lookup, encryption and filesystem durability capabilities.
- Existing exporter compatibility, authority freshness and the owner's stop rules.

Unknown capabilities are false. Documentation for a provider does not prove the
selected deployment has that capability. Preflight is read-only where possible;
benchmarks that write run only in an explicitly approved disposable environment.
Discovery never provisions an account, obtains credentials or widens permissions.

### Options

| Candidate | Coherence and limits | Proposed use |
| --- | --- | --- |
| Completed local SQLite backup into a separate file | A completed engine backup gives a consistent DB copy; capture can restart under concurrent writers. External files need a coordinated inventory. | First feasibility candidate when a future local workspace actually uses SQLite. |
| Engine-supported immutable snapshot | Lifetime, cross-request identity and restart durability must be demonstrated. A process-bound transaction is not a durable handle. | Prefer when available within the existing local capability. |
| Live keyset reads with a comprehensive mutation fence | Can reject change, but only if every relevant mutation advances the fence; may starve. | Explicit restart-only compatibility mode, never edit-tolerant snapshot mode. |
| Enforced writer pause and bounded copy | Coherent only if every writer participates; changes availability. | Separate owner decision if other candidates fail. |
| Whole payload retained in process memory | Process loss destroys resume state; memory grows with source. | Reject for the bounded durable contract. |
| Object storage receiving live pages | Stores bytes but does not establish their common source state. | Reject as a standalone consistency mechanism. |
| Atomic typed D1 shadow capture | Requires schema and operational writes, storage headroom, compatibility review and measured capture latency. | Conditional hosted-adapter candidate only. |

SQLite's [backup API](https://www.sqlite.org/c3ref/backup_finish.html) can copy a
bounded number of pages per step. Destination access is restricted during the
operation; finish alone does not establish successful completion. Concurrent writes
may restart capture, and [SQLite's backup guidance](https://www.sqlite.org/backup.html)
warns that sufficiently frequent changes can prevent completion. Therefore a local
adapter must bound total capture time/restarts, require successful completion and
durable sealing, and report contention rather than silently pause writers. Transfer
resume starts from the sealed artifact; it does not imply a crashed engine capture
can resume its old in-memory handle.

### Database and file coherence

A database snapshot does not by itself freeze attachments, source files or workdirs.
The preferred proposed workspace model commits references to immutable,
content-addressed file versions in the same application transaction as their
metadata. A capture reservation must prevent reclamation of all versions that a
concurrent capture can reference until its sealed inventory is pinned. Validate
each included file's identity, byte length and hash before publishing the snapshot.

If the source has mutable files, multiple databases or uncoordinated writers, require
an engine/filesystem snapshot covering the whole inventory, or an explicitly approved
comprehensive write pause. Rechecking timestamps, copying the SQLite main file
without its live journal semantics, or walking a changing directory does not prove
B3. Missing or changed referenced files fail capture. Unsupported cross-store
coherence stays blocked rather than yielding a partial backup labelled complete.

### Snapshot lifetime

The capture records its source-state identity, capture interval and consistency
evidence. Do not claim an exact start-time snapshot if the engine completed after
internal restarts. Source discovery outside the consistency boundary is advisory;
the captured inventory and schema signature must be checked within it.

Once sealed, later source edits cannot change the snapshot or its referenced files.
Pinning and capture reservations are explicit operational writes, never hidden page
read side effects. An unsealed or partially copied artifact cannot become READY.
The owner selects a minimum recovery window and any expiry policy before real use.
Expiry is fixed and visible in the sealed manifest; reads do not extend it. Extending
retention requires separately authorized state changes without rewriting manifest
bytes or substituting a different snapshot under the same identifier. Retaining
bytes longer does not extend expired read authority; any access-validity extension
needs its own reviewed authorization model.

## Snapshot state and operation semantics

Proposed states are `REQUESTED -> CAPTURING -> CAPTURED -> HASHING -> READY`.
`FAILED`, `CANCELLED` and `EXPIRED` are explicit terminal states with safe local
diagnostics. A caller may observe `unknown` when delivery was lost; this is lack of
knowledge, not evidence that committed work was rolled back.

| Operation | Effect and contract |
| --- | --- |
| `prepare_snapshot(request_id, format, scope_digest, policy_version)` | Mutating capture request. A durable uniqueness constraint binds request ID to owner/source and exact parameters. Same request and parameters reconcile to the same attempt; changed parameters conflict. |
| `get_snapshot(request_id or snapshot_id)` | Read-only lookup after authorization, including unknown-outcome reconciliation. Returns bounded state and sealed manifest only when READY. |
| `advance_manifest(snapshot_id, expected_progress_version)` | Explicit bounded metadata/hash work. Atomically compare-and-swap cursor, hash state, chunk index and version. A stale version cannot feed bytes twice. |
| `read_index(snapshot_id, manifest_hash, index_cursor)` | Read-only bounded authenticated index page. Binds index proof to the sealed manifest. |
| `read_chunk(snapshot_id, manifest_hash, sequence)` | Read-only exact immutable chunk, bounded by its committed descriptor. Repeated requests return identical bytes. |
| `cancel_snapshot(snapshot_id, expected_version)` | Explicit operational mutation. Reconcile in-flight work; cancellation does not delete files or establish rollback of a committed capture. |

Names are illustrative interfaces, not existing CLI commands or public APIs.
Mutation tools must not be marked read-only. All reads authorize the caller before
returning existence, state, errors, manifest, index or bytes. An adapter must not
create captures, hash work, renew leases or perform maintenance during a read.

One request ID is retained after an ambiguous response; lookup precedes retry.
Concurrent identical requests converge through durable uniqueness. Different
requests share a globally enforced capacity bound; an in-process boolean does not
limit multiple workers. Hash advances use durable compare-and-swap state. Deployment
or process replacement must understand stored encoder/hash-state versions, or stop
with an explicit incompatibility instead of corrupting progress.

Cancellation checks occur between bounded steps. A transaction already committed
remains visible as captured even if the request was cancelled. A durable cancellation
fence prevents later workers from sealing a cancelled attempt. Do not promise that
transport cancellation cancels database work, or that background process lifetime
is a durable job queue.

## Deterministic serialization and manifest

### Source inventory and exact values

The format must name every included table, column, index, trigger, view, migration
ledger, file class and history generation, including empty tables and historical
principals. No owner-only row filter may erase historical identities from the
owner's full authorized source inventory. An unknown application table, column,
schema object or unsupported storage class fails closed.

Preserve source schema text as evidence. Backup-infrastructure definitions and
transient rows must be distinguished from application state with exact, versioned,
reviewed exclusions. A wildcard exclusion is insufficient. The scope is a logical
application backup; excluding staging rows cannot be described as a physical clone.

Specify table/column ordering, primary-key or explicit rowid ordering, duplicate-row
handling, type tags, frame boundaries, length encoding, endianness and byte encoding
before implementation. The format identifier binds those rules and fixed vectors.
Do not parse and reformat JSON-valued TEXT, normalize whitespace or Unicode, drop
NUL bytes, or conflate NULL with an empty string. Preserve source TEXT bytes under
the declared supported encoding; unsupported encodings fail rather than coercing.

Signed 64-bit INTEGER values must be extracted without first passing through an
inexact floating-point number. In a JavaScript SQL adapter, cast integers to decimal
TEXT in SQL before transfer; serialize canonical signed decimal strings and restore
with an exact integer path. A later string conversion cannot repair prior rounding.
Each adapter declares its supported SQLite storage classes. An initial
INTEGER/TEXT/NULL profile rejects REAL/BLOB unless a separately reviewed codec and
boundary vectors support them; a generic SQLite claim must not hide that limitation.

### Bounded cells and chunks

A row limit is not a byte limit. Read bounded cell byte ranges at the storage layer,
using deterministic key/cell/byte cursors against the immutable snapshot. Do not
fetch a full oversized cell before slicing it. Chunk boundaries may split encoded
text; validate bytes before decoding, and decode only through a correctly bounded
streaming decoder. Bound record headers and declared lengths before allocation.

Choose a fixed maximum decoded chunk size per format instance. The final chunk may
be shorter; intermediate chunks follow the committed layout. Base64 or other
transport envelopes have a separate total response-byte limit. Index and manifest
construction cannot buffer all chunks or rows. A request must never rescan or hash
the live source to produce one immutable chunk.

### Manifest structure

The proposed manifest records:

- Format and encoder versions; schema/codec compatibility versions.
- Snapshot ID and opaque source namespace; provenance and consistency evidence.
- Source schema digest, declared inventory and exact exclusions.
- Logical table/file counts and hashes through bounded inventory pages.
- Serialized byte length, chunk count, whole-stream SHA-256 and index-root digest.
- Chunk/index layout, hash algorithm, capture times, expiry and policy identifier.
- Supported type/encoding profile and documented logical-restore normalizations.

The manifest and indexes are private data too. Do not include credentials, public
download tokens, internal paths or content-bearing diagnostics. Provenance only
includes identifiers needed for local verification and remains within the source's
classification. Private identifiers are never examples in repository fixtures.

Every chunk descriptor binds `snapshot_id`, `format`, `sequence`, `offset`,
`length` and `sha256`. Sequence starts at zero. Ranges must cover exactly
`[0, total_length)` once, with no gaps, overlap or extra sequence. Numeric metadata
uses validated canonical integer encodings with implementation-safe bounds. A
receiver checks descriptor identity, range arithmetic and digest before writing.

The compact root manifest binds bounded inventory/index pages by ordered hashes or
a specified tree with explicit domain separation, positions and lengths. Index
proofs cannot be verified against an untrusted replacement root. Define canonical
manifest bytes without an embedded self-hash; carry the manifest digest in its
envelope/checkpoint. This avoids circular hashing. Hashes detect corruption, not
authorization or authenticity: establish the expected root through the authorized
local capture record or an authenticated adapter channel.

Manifest construction scans the immutable snapshot incrementally. Persist the
versioned incremental hash state, cursor, byte offset and index changes atomically.
Use a reviewed hash implementation and fixed resume vectors; whole-buffer digest
calls do not provide a bounded-memory guarantee. READY commits only after counts,
terminal cursors, stream length, index coverage and all hashes agree. The manifest
then becomes immutable. Sparse or reversed chunk reads are valid; ordered final
assembly still verifies the whole stream.

Recreating the same logical source with the same codec must produce the same logical
content hashes. Snapshot IDs, timestamps and permitted physical-layout differences
may change manifest identity; distinguish these from logical-content determinism.

## Durable local downloader

Each capture has a private directory derived from validated opaque namespace,
format, snapshot ID and manifest digest. Never use source text as a path component.
Refuse symlink traversal, unexpected file types and paths outside the selected root.
Only one downloader may mutate a capture directory at a time; use a crash-recoverable
local lock or equivalent durable coordination. Independent read-only verification
must account for a producer still writing and report a stable observation boundary.

For each complete response:

1. Check snapshot/manifest identity, sequence, offset, length, envelope and chunk hash.
2. Write a new temporary file in the destination filesystem; flush and fsync it.
3. Atomically publish the validated immutable chunk without replacing a conflicting
   valid file, then fsync the directory where supported.
4. Atomically replace the checkpoint and durably publish that replacement.

The checkpoint records manifest identity, validated prefix, sparse-set references
and finalization state. It is an optimization, never authority. On every restart,
enumerate and revalidate persisted files against the root-bound index with bounded
memory. Adopt valid chunks absent from the checkpoint; roll back a checkpoint that
claims missing/corrupt bytes. Preserve valid later chunks as a sparse set. Use a
bounded on-disk index or streaming scan instead of loading all filenames into memory.
Do not mutate or delete questionable evidence just to make a reconciliation report
look complete; report it and keep it outside the accepted set.

Interrupted delivery does not prove nothing was saved. Inspect durable state before
repeating an expensive read. Retry the same chunk identity after an unknown read
outcome; never resume from an unverified offset inside a partial base64 response.
Honor bounded backoff, retry-after and an owner-visible recovery deadline. Network
loss in an optional adapter does not trigger a different source or public fallback.

If an older producer invalidates a live export when data changes, stop that attempt
and preserve its isolated files. A new manifest starts a new capture directory.
Do not combine old chunks with the replacement or silently retry forever. Label
this restart-only mode accurately; durable downloading does not cure its producer's
consistency or allocation limits.

For finalization, stream validated chunks in order into a new artifact. Recheck
coverage, exact length, whole hash, schema and logical inventory. Run the isolated
restore proof below, fsync the final artifact and verification record, and atomically
publish a completion marker referencing both exact hashes. A crash after final
rename but before the marker is recoverable by re-verifying existing bytes, without
reading the source again. A last chunk or checkpoint at total length is insufficient.
Where fsync/atomic publication guarantees are unavailable, report the weaker
durability and block a crash-durable completion claim.

## Budgets and backpressure

No production numeric values are selected by this proposal. The implementation
review must fill in, measure and approve the following per-adapter configuration;
unset required bounds block readiness. Fixture values are not production defaults.

| Budget | Enforcement and evidence |
| --- | --- |
| Maximum logical source bytes, rows, tables, files and largest cell | Preflight plus authoritative checks at capture/encoding; reject growth or unsupported overflow. |
| Snapshot and temporary-storage bytes; free-space reserve | Reserve capacity globally, including staging/index/final/restore/WAL or journal overhead and encrypted-storage expansion. |
| Active captures, hash workers and download concurrency | Durable cross-process or database-enforced reservations; bounded queues. |
| Capture elapsed time, lock time and allowable edit latency | Measure contention separately from transfer; report safe failure without silently changing consistency. |
| Per-step CPU, query count, rows and bytes returned | Instrument encoder/adapter boundaries and enforce before allocating or issuing unbounded work. |
| Chunk bytes, envelope bytes, index-page bytes and proof depth | Reject oversized input/output and arithmetic overflow; include base64/JSON overhead. |
| Peak buffered memory | At most configured chunk/cell/index/state/concurrency overhead; no growth proportional to total source or chunk count. |
| Hashing/restore work, disk I/O and total operation deadline | Bounded streaming passes with explicit backpressure; full proof has linear total work, not constant total cost. |
| Retries, contention restarts and backoff window | Reconcile unknown outcomes first; stop with resumable state when the budget expires. |
| Recovery window, snapshot count and retention capacity | Owner-selected before real data; no implicit eviction or deletion to satisfy a quota. |

Measure increasing synthetic sizes and worst-case cells. Record peak memory using
the actual runtime's supported measurement and disclose blind spots. A small local
test does not establish a hosted runtime's limits. Storage footprint, serialized
payload bytes and peak buffered memory are separate quantities. Snapshot capture
may perform work proportional to the database even when application buffers are
bounded; report that cost and any queued owner edits honestly.

## Restore proof and authority after recovery

Restore is a validation operation into a newly allocated isolated local directory,
never an arbitrary supplied database path or the active workspace. Disable network,
extensions, triggers with side effects, external-file access and execution hooks.
Treat manifests, file names, SQL and archived content as untrusted input. Verify all
hashes and inventory before using the reviewed schema; reject unexpected DDL,
virtual tables, path escapes and unsupported types. Do not execute arbitrary SQL
merely because it was stored in a backup.

For a SQL adapter, create approved tables first, insert exact typed rows and explicit
rowids where required, restore allocation state such as `sqlite_sequence`, then
create reviewed indexes/triggers/views in dependency order. Loading with business
triggers already active can create new history or mutate counters, invalidating the
round trip. Reconstruct included files from their exact versioned bytes and verify
every reference. Preserve legacy records, deleted/archived state within the declared
retention scope, duplicate ledger entries, NULLs and all historical principal IDs.

Compare every included table's schema, column inventory, count and deterministic
typed row hash; every included schema object; all attachment/chunk chains, history
generations, operations, ledgers, allocators and current-state pointers. Run engine
integrity and foreign-key checks where supported. Re-export with the same codec and
require equal canonical logical-content hashes. Explicit normalization may exclude
physical page numbers, file layout, capture timestamps and declared infrastructure
state; it cannot excuse missing rows or changed application values.

Exact historical data restoration does not reactivate historical authority. Restore
the old bytes into quarantine, then independently compare current trusted policy,
revocation epochs, consumed execution/export keys, deletion tombstones and replay
horizons before any promotion. The current authority anchor must not be rollable
back merely by replacing the workspace backup. If its freshness cannot be established
offline, remain blocked for owner review; do not make an Internet call or trust the
backup's own assertion. No restored pending task, notification or approval executes
automatically. Promotion into an active workspace is separately authorized and
must preserve newer restrictions and applicable deletion decisions.

Quarantine and current execution policy are a separate effective-authority layer;
they do not rewrite, remove or relabel historical receipts, approval records or
source bytes in the restored evidence. Exact restoration and comparison finish
before any separately approved reconciliation or migration. A newer prohibition
can block use of exact historical data without pretending that the old data changed.

Distinguish `transport_verified`, `restore_verified` and `recovery_ready` in local
reports. A sealed copy in the source database or on the source disk shares that
failure domain. A backup is not disaster recovery merely because restore proof
passes; an independently protected, explicitly approved recovery copy is a separate
decision. This design does not authorize moving sensitive-profile backups off-device.

## Access control and threats

- **Unauthorized readers:** recheck current owner identity on every adapter call,
  including status and expiry responses. Reject caller-supplied owner fields,
  service-only bypasses and guessed IDs. Apply private cache controls; reveal no
  object existence before authorization.
- **Private UI exposure:** UI and approvals bind only device-local sockets or
  loopback, with denial of LAN and same-host online-stage access. No tunnel, proxy
  or port forward exposes backup views. Local authentication alone is insufficient.
- **Stage confusion:** online ingestion/export processes cannot mount snapshots,
  checkpoints, restore directories or encryption keys. Private workers have no
  network-stage credentials. Bundled UI assets make no remote requests.
- **Content injection:** task text, history, attachment names, schema comments and
  model output cannot select SQL, paths, retention, destinations or permissions.
  Use reviewed queries/schema and strict numeric/length validation.
- **Corruption and substitution:** verify root authenticity, chunk/index hashes,
  coverage and full restore. An attacker replacing both data and an unauthenticated
  hash defeats checksums. Storage encryption and access control remain necessary.
- **Replay and rollback:** stale policy, expired approvals and restored consumed keys
  block actions under B8. Reusing a request ID with changed parameters conflicts.
- **Resource exhaustion:** cap parser nesting, declared lengths, decompression,
  allocation, index entries, concurrency and retries before processing untrusted
  content. Compression is optional future scope with separate decompression bounds.
- **Local compromise:** a privileged compromised device can read decrypted data or
  falsify local evidence. This proposal does not claim protection from a hostile OS
  or trusted administrator. Never use hashes as a substitute for that threat boundary.

Any separately permitted outward artifact is a sanitized immutable copy approved for
exact bytes, destination, audience and purpose through the private planning contract.
Backup creation is not such an approval. Automated redaction does not authorize
sharing. Changing packet bytes, destination or purpose requires a new decision.

## Expiry retention and cancellation

Before real data, the owner selects incomplete-capture retention, minimum download
recovery window, verified recovery-point count, deletion handling and storage budget.
Until a policy and the required deletion authority exist, no automatic deletion is
enabled. Capacity exhaustion rejects a new attempt; it never removes the only
verified artifact. Cancellation stops work but does not delete retained evidence.

If maintenance is later authorized, make it explicit, bounded and resumable. Use
tombstones and compare-and-swap catalog changes so expired objects return an
unambiguous authorized error, never replacement bytes. Coordinate cleanup with
reader pins and in-flight captures. Expiry may end a read cleanly but cannot mix
versions. Leases and their renewal are writes requiring the applicable authority.
Local final artifacts and optional server snapshots are distinct retention objects.

Deletion requests must account for retained backups and replay protection; restoring
old content cannot silently undo them. Approved backup deletion, source retention
and promotion policy are separate decisions. No source cleanup, migration, history
pruning or production write is implied by this design.

## Optional hosted D1 and R2 adapter

This section applies only to a separately authorized dataset already hosted outside
Axel's sensitive profile. It is not a route for uploading the device-local private
workspace. No D1/R2 binding, account API, queue, workflow or durable coordinator is
assumed available, and no new credentials or access are requested here.

Cloudflare documents transactional [D1 batch semantics](https://developers.cloudflare.com/d1/worker-api/d1-database/).
Its [limits](https://developers.cloudflare.com/d1/platform/limits/) include a
2,000,000-byte row/string/blob ceiling and a 30-second query duration; the documented
API timeout also bounds the whole batch. A D1 database processes queries serially.
Effective deployment limits and capture-induced edit latency still require direct
verification. Sessions bookmarks support sequential consistency, not a reusable
immutable snapshot handle. The legacy `dump` interface is not a general streaming
capture solution.

Subject to those gates, one candidate is a single atomic capture transaction into
fixed typed shadow tables. Reserve an owner-scoped request, validate exact schema
and capacity within the transaction, record schema/counts/ledgers/allocator state,
copy every approved source table using fixed `INSERT ... SELECT` statements, verify
counts and mark CAPTURED. Return bounded metadata only. Preserve required rowids,
copy INTEGER/TEXT/NULL directly in SQL and omit business triggers on staging tables.
Shadow-key overhead must fit row limits. Backup infrastructure must not create
application history, receipts, operations or source mutations.

This candidate performs database writes and linear database work. It is not a
read-only operation or a final architecture choice. Do not split a failed atomic
capture into changing-source transactions and still claim coherence. If measured
latency/storage is unacceptable, retain the safe local/restart-only option and bring
back the supported-native-capture versus explicitly approved writer-pause decision.

Before same-database staging, test old exporters against new infrastructure tables.
An exporter that rejects unknown tables will break unless a narrowly reviewed
compatibility change recognizes exact infrastructure names/versions and records
their exclusions. Preserve its wire format and original application-data meaning;
unrelated unknown tables must still fail closed. A changed schema can invalidate
old manifest identity, so old partial exports remain isolated. If the exclusion
change is unacceptable, do not deploy this staging design.

An optional [R2 binding](https://developers.cloudflare.com/r2/api/workers/workers-api-reference/)
can hold already coherently captured export bytes using streams/range reads. A later
adapter needs private authenticated access, deterministic object identities,
commit-last manifests and reconciliation of object/catalog partial outcomes. It
must not expose public or bearer download URLs. R2 does not solve source coherence.
Native [D1 account export](https://developers.cloudflare.com/api/resources/d1/subresources/database/methods/export/)
requires separately available account capability and has its own query-blocking
behavior. Neither option permits acquiring hidden credentials or bypassing the
hosting platform's supported interfaces.

## Acceptance tests for future implementation

These are required tests, not passing results. Use synthetic content and invented
identities only. Generate the schema inventory and counts from fixtures, never from
a private deployment. Instrument queries, returned bytes, memory, step durations,
disk states and logical hashes without logging source content.

| ID | Scenario and required evidence |
| --- | --- |
| C01 | Concurrent create/edit/archive/history changes during capture yield one committed source state; later edits during hashing/download cannot change its bytes. |
| C02 | Concurrent attachment replacement/reclamation, multi-store changes and missing files cannot produce a mixed or incomplete declared inventory. Uncoordinated writers fail preflight. |
| C03 | Schema changes between discovery and capture, unknown tables/columns/objects and unsupported types fail closed within the capture boundary. Empty tables and legacy history remain included. |
| C04 | Capture failure, timeout, disk/quota exhaustion and row overflow never expose partial CAPTURED/READY state. Measure rollback and unknown-outcome reconciliation. |
| C05 | Lost successful response and duplicate/racing requests reconcile to one same-ID attempt; changed parameters conflict; global capacity survives worker restarts. |
| C06 | Repeated writer contention reaches a declared bound; no silent pause, incoherent multi-transaction fallback or false promise of eventual capture. |
| H01 | Kill or race each hash advance before/after compare-and-swap; no double-fed bytes or forked manifest. Old hash-state versions fail explicitly. |
| H02 | Independent encoders/verifiers agree on canonical vectors and logical hashes; snapshot metadata differences do not obscure content equality. |
| H03 | Long cells, maximum headers and increasing source size stay within buffer/CPU/response/index budgets. Reject a false length before allocation. |
| H04 | Missing, duplicate, reordered or substituted index pages fail root-bound validation; a replaced unauthenticated root is not accepted as trusted. |
| D01 | Persist several valid chunks, including a sparse later one, while checkpoint remains at zero; restart adopts verified files and requests only missing ranges. |
| D02 | Kill before response, mid-temp write, after fsync, after chunk rename, around checkpoint rename, during final assembly and before completion-marker publication; restart never invents durable progress. |
| D03 | Truncation, altered base64, wrong hash/length/sequence, overlap/gap, extra bytes, stale checkpoints and mixed snapshots fail without a completion marker. |
| D04 | Same chunk read after cancellation/lost delivery returns identical bytes. Concurrent local downloaders cannot overwrite each other's accepted evidence. |
| D05 | Source change in restart-only mode is reported; replacement manifest is isolated. Complete saved chunks permit offline re-finalization without source reads. |
| D06 | Disk-full, permissions, missing fsync support, symlink/path races and producer-active scans have explicit safe outcomes and truthful durability reports. |
| R01 | Restore all original tables/files, raw JSON TEXT, NULL/empty distinctions, actual NUL, CR/LF, escape sequences, non-ASCII and long cells exactly. |
| R02 | INTEGER vectors around 2^53 and both signed-64 boundaries prove exact extraction before any JavaScript Number conversion and exact restore. Unsupported REAL/BLOB fail. |
| R03 | Preserve rowids, duplicate ledgers, historical principals, revisions, operations, schema objects, allocators and current pointers; engine integrity/foreign-key checks and canonical re-export agree. |
| R04 | Valid-looking truncated JSON, missing history/empty table, changed schema/index, omitted file/principal and extra/reordered record cannot pass restore proof. |
| R05 | Hostile schema, virtual tables/extensions, hooks, absolute paths and traversal cannot execute or escape the fresh isolated restore root. |
| R06 | An old backup with unconsumed approvals, revoked nodes or stale deletion state cannot dispatch, share or promote; unknown current authority blocks offline. |
| P01 | With Internet unavailable and inference disabled, local capture/download/restore succeed on supported fixtures. No hidden assets, telemetry, package/model downloads or fallback requests occur. |
| P02 | Other local users, LAN compute, online stages and guessed IDs cannot read source, manifest, status, checkpoint, UI or restore files. Missing/forged identity leaks no existence metadata. |
| P03 | Private canaries in records, errors and paths appear nowhere in remote diagnostics, public artifacts, logs or inference calls. Content cannot change permissions or approve outward export. |
| L01 | At capacity, existing recovery points remain intact. Cancellation and expiry races do not substitute bytes or delete evidence without authority. |
| L02 | If cleanup is separately approved, interruption/tombstone/reader races preserve source tables, approved recovery points and replay barriers. |
| A01 | Optional D1 capture passes actual-runtime latency/storage/row limits and exact allowlist/v1 compatibility tests; unsupported capabilities block before writes. |
| A02 | Optional object/catalog partial outcomes reconcile idempotently; authenticated private range access never publishes incomplete or mixed snapshots. |

## Rollout compatibility and review decisions

1. **Design review:** agree invariants, source inventory, local adapter candidate,
   exact codec/manifest vectors and unresolved budgets. This PR contains prose only.
2. **Separately authorized local prototype:** use synthetic fixtures and provisioned
   offline dependencies. Implement capability preflight, a bounded verifier and
   durable reconciliation before a writer/downloader. Preserve existing evidence.
3. **Capture feasibility:** demonstrate consistency and lifetime, cross-store file
   coordination, exact types and measured resource bounds. Stop if the proposed
   adapter cannot meet the contract; no cloud substitution for the local profile.
4. **Downloader and restore:** run every applicable crash/corruption/privacy test.
   Report passed, failed, skipped and unrun tests separately. Gate completion on an
   independent all-inventory restore, not just one migration ledger or final chunk.
5. **Compatibility review:** preserve old reader/writer formats and known-good
   artifacts; reject unknown major formats and schema changes. A new parser must
   not reinterpret old bytes under a new codec. Existing partial captures retain
   their original identities and supported verifier path.
6. **Optional adapter review:** separately authorize any schema, operational writes,
   provisioning, migration, hosted access or retention changes. Keep applied
   migrations immutable; inspect partial application before retrying. A rollback
   must not remove original source or the only verified recovery point.
7. **Any later release:** recheck exact commit, allowed scope, owner-only access,
   tests and working-hours policy. Run the
   [working-hours guard](../HILLCLIMB.md#working-hours-guard) before each operational
   mutation and after resume; the owner's stricter cutoff wins. This document
   grants no implementation, production, cleanup, merge or deployment authority.

Open decisions are the actual local source engine/inventory, coherent file-version
strategy, supported type profile, final codec grammar, numeric budgets, durable
hash-state representation, independent authority anchor, retention policy and any
separately approved recovery-copy destination. All must be resolved before claiming
implementation readiness for real private data.

## Sources and verification scope

Repository conventions were inspected on Axel main
`32c5c6975cd806870a8ae0fb319d4661e7c69ee7`; the privacy design is linked to the
immutable PR #249 head above. Provider links are primary documentation checked
2026-10-09. Revalidate provider limits and actual capabilities before implementation.
This review inspected documentation and prepared a contract. No runtime, capture,
download, restore, migration, deployment or private-data acceptance test is claimed
to have run.
