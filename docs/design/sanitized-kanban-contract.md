# Sanitized kanban extraction and service contract

**K269 (P6): proposed, documentation only; reviewed 2026-10-10.** Extract reusable
kanban behavior from the private Kepler product into Axel through newly authored,
sanitized source and synthetic fixtures. This proposal creates no service, identity
registration, database, migration, import, deployment or entitlement. Implementation,
private migration and deployment require separate work and action-specific authority.

**Initial mode: explicitly trusted server, not full E2EE.** The design permits
plaintext only where needed at narrowly scoped API/server, Slack integration and
authorized ChatGPT dot endpoints. It requires tenant isolation, least privilege and
encryption in transit and at rest; privileged operators may still access plaintext.
[Full operator-blind E2EE](kanban-e2ee-boundary.md) is a separate optional long-term
extension tracked in [Axel #252](https://github.com/futuroptimist/axel/issues/252),
not a blocker for initial implementation. Neither mode is implemented or
security-qualified by this documentation.

K269 is one card with two required design PRs:
[Axel #251](https://github.com/futuroptimist/axel/pull/251) and
[Sugarkube #2910](https://github.com/futuroptimist/sugarkube/pull/2910).
Keep both explicit direct PR links on
that card, with independent heads, checks, reviews and merge receipts. A missing
companion link blocks readiness. Only the owner merges; one merge is **partially
merged**, and Done requires both required PRs owner-merged. Implementation is not
an implicit next step. The preparation cutoff is 2026-10-13 07:00
America/Los_Angeles (14:00 UTC); the working-hours guard also applies.

## Privacy and security invariants

These requirements apply across UI, API, adapters, queues, imports and recovery.
They are proposed acceptance gates, not guarantees of today's Axel implementation.

| ID | Required invariant |
| --- | --- |
| K1: clean public source | Never copy the private Site checkout, Git history, snapshots, migration records, generated embedded data or production exports into Axel. Reconstruct reusable behavior in a clean public checkout; only invented fixtures, identifiers and examples enter source, CI, screenshots and artifacts. |
| K2: separate profiles | Preserve offline-first owner-local state/UI and enrolled private-LAN token.place inference. Online Slack/GitHub/Sites integration is separately enabled for an approved online board. It cannot mount or query the sensitive corpus, forward private inference, or authorize private-data egress. |
| K3: identity is not membership | Provider sign-in proves a stable subject. Axel independently grants and rechecks tenant, board and action roles server-side. No client tenant field, display name, email, Sites header or imported approval grants authority. |
| K4: complete isolation | Authorize before existence disclosure on every read, write, search, link resolution, cache hit, subscription, job, attachment, preview, history view and export. Scope queries and durable keys to tenant and board; validate every referenced object. |
| K5: data is not authority | Messages, manifests, card text, model output, PR comments and CI logs are untrusted data. Agents get explicit bounded capabilities; review, approval, merge, migration, deployment and outward release remain distinct actions. |
| K6: durable evidence | Permanent IDs, revisions, questions, receipts, links and history survive archive, migration and retry. Unknown outcomes remain unknown until reconciled. Old state never revives consumed or revoked authority. |
| K7: reproducible release | Source tag, commit, frontend artifact, API contract, schema/migration set and deployment record must match an immutable release manifest. Unknown compatibility blocks rollout; a build success does not prove deployed state. |
| K8: private operations | Private records, identity mappings, manifests, backups and operational evidence stay in approved private storage. Public logs, fixtures, analytics, error reports and build outputs contain none of them. No production access follows from this design. |
| K9: explicit confidentiality mode | Initial mode trusts only the named endpoints needed for a scoped operation. Encrypt transport, stored data and backups with qualified key management, but disclose privileged-operator access. Never label server-readable data E2EE or make an optional stronger mode's guarantees apply to this mode. |
| K10: bounded agent disclosure | A verified ChatGPT dot may read/write explicitly granted board/task scope through API/MCP. Tenant-owner grants bound recipient, data, tools, purpose, duration and disclosure policy; recheck at use. No blanket future disclosure, cross-tenant access or implied merge/deploy authority. |

The [private LAN planning proposal](https://github.com/futuroptimist/axel/blob/5632350c20c0a3dc6aac2ce3024047518d506901/docs/design/chat-operations-contract.md)
in [PR #249](https://github.com/futuroptimist/axel/pull/249) retains its device-only
UI/corpus, no hidden egress, exact outbound packet approval and separate network
stages. This document does not relax those rules. A Sites-hosted online board is
a different data profile, never a remote window onto that sensitive board. Sharing
code does not share credentials, data, workers or policy. General
[Discord ingestion](../discord-bot.md) remains in scope for varied personal tasks;
Slack is an additional opt-in adapter, not a replacement or inference provider.

## Boundaries and ownership

| Component | Proposed responsibility |
| --- | --- |
| Axel domain | Card lifecycle, permanent identity, revisions, dependencies, questions, receipts, multi-PR evidence, authorization decisions and validation independent of storage/UI. |
| Axel UI | Accessible board/card/history/archive/search views, explicit pending/failed/unknown states, approval previews and migration/export journeys. Bundle local assets for offline use. |
| Axel adapters | Local storage, authenticated service storage, identity providers, agent API/MCP and chat normalization. Capabilities are declared and verified, not inferred from provider names. |
| On-prem service | Initial-mode trusted HTTPS API and scoped plaintext processing, session/policy boundary, transactional storage, bounded jobs and safe audit. Minimize plaintext exposure; no direct browser, Slack or agent DB connection. |
| Sites frontend | Build/deploy approved reusable UI assets for the online profile and call the API through a supported authenticated integration. No private data baked into JavaScript, HTML, source maps or static fallback snapshots. |
| Sugarkube | Staging topology, ingress/TLS, database lifecycle, runtime and migration identities, secret injection, network isolation, capacity, monitoring, backup/restore operations, rollout and rollback design. |
| Shared decision | Engine evaluation, isolation proof, schema compatibility, recovery objectives and the release/API handshake. No database engine is selected here. |

Initial-mode data may be decrypted in the selected API/worker when necessary, so
compromised or privileged hosting/API/database/backup operators remain a content
confidentiality risk. Keep runtime, migration, backup and human administration
roles separate; audit access, qualify key custody/rotation/recovery, and minimize
plaintext lifetime and replication. Require verified TLS for every service hop,
encryption for data volumes and all backup copies, and no keys in code, URLs,
logs or model context. Sugarkube owns infrastructure key management and recovery
qualification; Axel defines minimum application access and safe content handling.
Server-side column encryption, TLS or disk encryption does not make the operator
blind: [PostgreSQL's encryption guidance](https://www.postgresql.org/docs/18/encryption-options.html)
distinguishes those protections from client-side encryption. These requirements
are design gates, not statements about current deployments.

Avoid plaintext content in diagnostics, metrics, traces and crash reports. Backups
retain content under encrypted, restricted storage and explicit retention/deletion
policy; authorized restore still exposes it to its trusted recovery environment.
Support/admin procedures must not silently expand board access or export data.
Historical copies and already disclosed plaintext cannot be recalled by revocation.

Use a same-origin backend-for-frontend (BFF) session boundary where the Sites
deployment supports a verified route to it. Otherwise a separate origin needs an
explicitly tested session/CORS/CSRF design. Do not assume Sites can proxy requests,
reach on-prem networks or supply portable identity. These are preflight gates;
unsupported capability blocks deployment rather than exposing the database or
trusting arbitrary headers. Sugarkube decides the approved API ingress path and
staging isolation. No live topology is inspected or changed by this PR.

An offline adapter must support local board operations without GitHub/Slack login
or Internet. Online metadata becomes visibly stale offline; cached evidence cannot
approve actions. Only a separately approved sanitized copy may cross profiles,
with exact-byte export approval under the existing private LAN contract.

## Clean extraction and reproducible packaging

1. Inventory behavior and interfaces from authorized requirements, without reading
   private Discord/work datasets. Do not use the private checkout as a source tree
   or copy its history and then attempt deletion/redaction.
2. Author portable domain/UI code in a fresh branch of public Axel later, after
   implementation authorization. Separate configuration, storage and identity ports
   from UI/domain code. Record provenance and third-party license obligations.
3. Create synthetic cards covering archives, multiple PRs, conflicts, Unicode,
   history and adversarial input. Invent all users, workspace IDs, links and text;
   do not anonymize a real snapshot and call it synthetic.
4. Before publication, scan source, staged diff, complete proposed history and built
   artifacts for credentials, private identifiers, embedded JSON, migration payloads,
   source maps, comments, screenshots and metadata. Use secret detectors plus
   private-data canaries and human provenance review; keyword scans alone cannot
   prove privacy. Quarantine a failed artifact rather than rewriting private history
   into a public repository. No private scan corpus is committed.
5. Build from a clean tagged commit with locked dependencies and pinned toolchain.
   Publish content digests, dependency inventory/SBOM, provenance and reproducibility
   comparison for the reusable bundle. Production records are runtime API data only.

The proposed `ReleaseManifest v1` binds `release_id`, immutable source tag and full
commit SHA, toolchain/lockfile hashes, frontend and service artifact digests,
`api_major`, contract digest, accepted schema range, ordered migration IDs/checksums,
fixture suite version and build provenance. Keep it separate from private import
manifests. Sugarkube's deployment receipt references its digest, environment,
actual deployed digests/schema and verification result. Retagging or rebuilding
different bytes under the same release identity fails verification.

## Identity, sessions and roles

The first online identity adapter is GitHub sign-in using the supported web
Authorization Code flow, PKCE S256 and unguessable one-use state bound to the
initiating browser session. Use an allowlisted exact callback and redirect target,
short expiry, one-use code handling and server-side exchange. Verify the returned
identity through GitHub's authenticated user endpoint on each login. Key the
external identity by provider/issuer and stable numeric subject ID (encoded without
loss), never login name or email. Request only necessary identity scopes; repository
status integration has separate permission and installation boundaries.

Rotate the Axel session on login/role elevation. Use Secure, HttpOnly cookies with
appropriate SameSite policy, idle/absolute expiry, logout invalidation and server-side
revocation. Enforce anti-CSRF tokens and Origin validation on state changes, with
an explicit credentialed CORS allowlist when needed. Never put provider credentials
in frontend bundles, browser storage, URLs, logs or model context. Do not treat
GitHub OAuth as an OIDC ID-token flow. Rate-limit login and account recovery.

Authenticated users without membership receive no board data. Viewer reads scoped
content; requester creates/proposes permitted changes; reviewer records findings;
approver grants only specific authorized actions; board administrator manages
membership under separate policy. Owner-only merge and operational authority are
separate from all of these. Roles are scoped per tenant/board, deny by default,
and rechecked at use and job execution. Review is evidence, not approval.

Link providers only through a freshly authenticated existing Axel session plus
proof of control of the new provider subject, with conflict detection, audit,
notification through an approved channel and a recovery/revocation path. Never
auto-link on matching email/display name. Reassignment, revoked membership and
provider deletion must invalidate effective access without deleting historical IDs.

Treat ChatGPT website sign-in as a selected-partner limited-trial capability for
this proposal, not assumed general availability or entitlement. Define a future
identity adapter behind capability discovery and a separate review of actual
issuer, audience, verification, stable subject, linking and revocation semantics.
Do not substitute ChatGPT session cookies, API keys or a logged-in browser.
Sites-managed identity is platform-local; it is neither an Axel session nor a
trustworthy arbitrary identity header. A future bridge requires a documented,
verified assertion with audience, expiry and replay checks; absent that, use Axel
login. No adapter is enabled by this document.

## Shared API and storage contract for Sugarkube

The following is a proposed versioned interface, not implemented endpoints. All
routes below use authenticated HTTPS and bounded schemas. Tenant in a path selects
requested scope; verified principal membership determines allowed scope. Internal
workers use narrow service identities plus captured actor/scope and current policy.

| Surface | Contract |
| --- | --- |
| `GET /api/v1/session` | Current Axel principal, allowed scopes and policy version; no provider credentials. |
| `GET /api/v1/tenants/{t}/boards/{b}/cards` | Cursor-paged authorized cards; explicit archive filter, bounded bytes/count, stable view revision. History/search/link APIs apply identical scope checks. |
| `POST .../cards`, `PATCH .../cards/{id}` | Validated create/edit with `Idempotency-Key`; edits require `If-Match` revision. Reject stale edits with 412 and changed key payload with 409. |
| `POST .../cards/{id}/requests` | Bounded typed action proposal, actor and input digest; never arbitrary shell/SQL/tool definitions. Does not dispatch or approve. |
| `POST .../approvals` | Authorized human decision binds action, resource/revision, input digest, environment, destination/audience if outward, expiry and nonce. Consumption is atomic with dispatch reservation. |
| `POST .../imports/preview`, `POST .../imports/{id}/commit` | Validate private manifest and mapping, then write and seal the exact reviewed candidate in quarantine only; neither operation changes the live generation. |
| `POST .../imports/{id}/activate` | Separate owner-approved cutover after backup, restore proof and comparison; atomically switch the live generation with a writer fence and expected destination revision. |
| `POST .../exports`, `GET .../operations/{id}` | Explicit coherent capture intent and read-only progress/reconciliation. Export status/download still authorize; reads do not renew leases or start work. |
| `GET /api/v1/compatibility` | Authenticated bounded release/API/schema compatibility metadata for deployment preflight; no operational secrets or database access. |

Agent MCP tools map onto these same domain commands and policies. Chat requests
continue through the authenticated agent API/MCP path; they never write storage
directly. A capability includes subject, permitted action/resource, environment,
expiry and policy version. Server enforcement applies independently of tool labels
or prompt instructions. Agents cannot self-approve, link accounts or mint broader
capabilities. Fixed approved execution profiles are separate from kanban CRUD.

### First-class opt-in ChatGPT dot agent

Support a verified authorized dot as a scoped read/write agent over the same
authenticated API/MCP contract. In initial mode the trusted API may return only
the approved board/task fields needed for that operation and validate returned
updates before committing them. Selected plaintext enters OpenAI processing; it
does not remain local, and no zero-retention or guaranteed-deletion claim is made.
Do not infer product entitlement, autonomous wake behavior or a supported transport.
Actual dot/MCP authentication, recipient/audience verification, secure connectivity
and revocation capabilities must be demonstrated before enabling the adapter.
If unsupported or unverifiable, report blocked; never use shared admin credentials.
Initial mode does not require a local decrypting gateway. This proposal creates no
credentials, grants or authorization to share actual data.

Tenant-owner grants identify recipient, tenant/board/task scope, read versus write
tools, allowed fields, purpose, expiry and either exact disclosure or a clearly
bounded standing disclosure policy. A board grant does not authorize all future
data, tools, destinations or exports. Recheck membership/grant state per request
and queued execution; bind audience, request ID, payload digest and expected revision
to resist substitution/replay. Return safe audit receipts, not raw content logs.
Revocation stops future access and invalidates queued/cached authority; it cannot
erase plaintext the dot/provider previously received. Offline/unavailable endpoints
fail closed, not by widening scope. Agents cannot self-grant or approve actions.

Private-by-default boards and minimal generic Slack notifications are preferred.
Local agents and explicitly enrolled user-controlled LAN-only token.place compute
remain suitable for private work; nodes processing plaintext are trusted endpoints.
This online dot option does not override the sensitive local profile's exact-packet
export rule or create access to its corpus, filesystem, UI or inference sessions.
For optional future E2EE, a user-controlled gateway can provide scoped dot access
without giving hosting content keys; its independent trust and lock/offline limits
are specified in the [extension](kanban-e2ee-boundary.md).

### Shared operation semantics

Common envelopes include contract version, opaque request/operation ID, card ID,
revision, safe status/error code and correlation ID. Durable idempotency binds
tenant, board, principal, operation kind, key and canonical payload digest, in the
same transaction as state/audit/outbox changes. Retry identical requests by looking
up the prior result; after timeout reconcile before redispatch. Bound key retention
against replay horizons and reject expired ambiguous keys instead of creating new
work. Cursor, link, cache and download capabilities are scope-bound and expire.
No shared CDN stores private responses; use private/no-store response policy and
partition any authorized internal cache by scope, principal/policy and revision.

Storage adapters enforce composite tenant/board foreign keys and transaction
constraints; test service predicates plus engine-native isolation when supported.
Runtime DB roles cannot migrate, create roles or bypass isolation. Migration roles
are separately injected for approved bounded jobs and absent from API workers.
API authorization remains necessary even with row-level security. Fail closed on
unknown schema, unsupported transactions or missing policy context. Archive flags
are not access controls. Background tasks recheck membership and cancellation
before reads, writes and delivery; revocation invalidates queued/cached authority.

Sugarkube consumes the release manifest, API compatibility contract, migration
ordering/checksums, required role privileges, health/readiness meaning and bounded
resource requirements. Axel consumes authenticated endpoint configuration, deployed
release/schema receipt and availability state. Neither side receives ambient admin
credentials. Health distinguishes process alive, schema compatible and scoped
service ready. Engine-specific syntax and infrastructure belong in the companion
design. Evaluate memory-safe implementations alongside transaction correctness,
tenant policies, driver/extension safety, operational maturity and recovery proof;
memory safety alone is not isolation, and no engine has been selected.

## Slack request and response lifecycle

Ordinary [Slack message events](https://docs.slack.dev/reference/events/message/)
include plaintext. Slack and the receiving endpoint can see it; later encryption
cannot retroactively make that intake E2EE. Initial mode allows this explicitly
disclosed trusted-endpoint exception only for configured scopes, minimum needed
content and approved retention. A user-controlled receiver can reduce hosting
exposure, but does not hide the source from Slack. Prefer generic content-free
notifications linking to the app entry, without card IDs/titles; notification
timing still reveals activity and needs an approved audience policy. Optional
card-specific replies must also satisfy the durable audience checks below.

Only configured Kepler workspace/channel IDs map to an online tenant/board. Names
are display metadata. Verify Slack's signature over raw request bytes and timestamp
before parsing or queuing; enforce its freshness window, constant-time signature
comparison, bounded body size and rotation-aware secret lookup. A valid signature
proves provider origin, not sender authority. Validate installation/workspace/channel
and sender stable ID, current mapping/membership and allowed event type. URL
verification must not bypass origin checks or activate a channel.

Durably accept a normalized event and idempotent request intent before promptly
acknowledging; process asynchronously. Deduplicate by installation/workspace and
event ID, and by logical message/revision/action to handle retries and overlapping
subscriptions. Same key with changed bytes is a conflict for investigation. Drop
bot/self echoes and unsupported subtypes; retain bounded replay tombstones. An
unknown sender can receive a safe denied result only if that response is authorized;
do not reveal board existence or private titles.

Authorized text produces a proposed kanban request via the same domain/API policy.
Content can suggest intent, never choose tools, override roles or approve execution.
Persist origin channel and thread timestamp with the request. The bot's approved
outbox reply uses that exact originating thread and a canonical authenticated card
link, suppressing mentions and unfurls. Posting a link is itself disclosure: require
the destination's current audience to be allowed to know that card exists. If a
private board has a narrower audience than the channel, withhold the card link and
content; show blocked delivery in authorized UI. Do not fall back to a public
channel or DM. Current audience validation alone is insufficient: retained Slack
history can be read by future joiners, rejoiners and connected organizations.
Card-specific replies require a proven durable membership/history constraint that
keeps every future history reader within the approved existence-disclosure audience,
including invitation, rejoin, revocation, sharing and export paths. If the provider
and workspace policy cannot enforce that constraint, do not post a card-specific
link or title. Show the card link only in authenticated Axel UI; an independently
approved generic portal reply may contain no card identifier or existence detail.
Message deletion and link expiry cannot retract already disclosed existence. The
sensitive local profile still requires exact packet approval.

Edits append source revisions and propose a card change under optimistic concurrency;
they do not silently rewrite approvals, reviewed heads or completed actions. Deletes
record a source tombstone and apply the owner's retention rules without deleting
the card/history or triggering rollback. Late/out-of-order edits cannot resurrect
deleted content; reconcile ambiguous ordering. Audit evidence retention and later
privacy deletion need explicit policy, including search/cache/backups and provider
copies. Ingestion deletion is not permission to destroy records.

Honor provider rate limits and Retry-After with bounded jitter, per-tenant quotas,
backpressure and dead-letter review. Recheck audience/approval on each delivery.
After a send-before-receipt crash, reconcile the delivery key/provider receipt before
resending; report unknown when this cannot be established. Do not claim exactly-once
Slack delivery. Removed channels, changed mapping, lost permissions or exhausted
retry budget leave visible failed/blocked state, never duplicate execution.

## Cards, evidence and complete journeys

Cards have permanent opaque IDs independent of title, column or archive status,
an immutable revision history and scoped links/dependencies. Revisions include
requester, reviewer findings, questions/answers, action approvals, execution and
delivery receipts. Source IDs remain provenance, not login authority. Cycles,
cross-board dependencies and inaccessible targets need explicit validation; do not
leak hidden card titles through backlinks, counts, error messages or search facets.

Each required PR stores repository stable identity, number, direct canonical URL,
current full head SHA, draft/ready state, required-check results and run/attempt
identities, reviews and reviewed SHAs, unresolved findings, merge SHA/actor/time,
observation source/time and evidence freshness. Distinguish optional from required
PRs. Changing that set is an audited owner decision, never an agent shortcut to
Done. New heads invalidate prior readiness evidence. CI success on another head,
skipped checks or stale reviews do not count as final-head readiness. Verify merge
through authoritative GitHub state; a message saying "merged" is insufficient.

Show independent PR rows and states: missing evidence, draft, review needed, blocked,
ready for owner, merged. Aggregate card state distinguishes in progress, ready for
owner, partially merged and Done. Closed-unmerged is blocked. A reopened or reverted
work item records a new decision/history event; do not erase prior merge receipts.
For K269, retain both required design PR links even after archive.

| Actor | End-to-end journey and failure handling |
| --- | --- |
| Requester | Sign in or use authorized local identity, select an allowed board, create via UI/chat/MCP, inspect idempotent receipt/card link, answer questions, preview changes and follow each PR. Denied/stale/unknown requests remain explicit and retryable by original ID. |
| Reviewer | Open an authorized card, inspect exact PR head/diff and CI/review evidence, ask questions and record findings against that revision. New commits show stale review; reviewer cannot turn a finding into action approval. |
| Approver/owner | Inspect exact action/input/scope and each required PR's current head, checks and unresolved findings; approve only that action. Owner merges each PR separately outside this design. Reconciliation records partial merge, then Done only after all required owner merge receipts. |
| Agent | Verify recipient identity and tenant-owner grant; obtain narrow read/write capability, disclose only approved fields to the local/LAN or authorized dot endpoint, and modify with revision checks. Preserve questions/evidence, await action-specific approval, reconcile unknown outcomes and report blockers. No self-grants or inferred merge/deploy authority. |
| Import/export operator | Select authorized inventory and identity mapping, inspect dry-run counts/conflicts/digests, request separate commit/export/cutover approvals, verify restore/comparison and preserve receipts. Failure stays quarantined and resumable without public data release. |

## Import, export, schema migration and cutover

Reuse the [bounded backup contract](resumable-backup-contract.md), including coherent
capture, exact types, immutable chunks, independent restore proof and authority
freshness. Do not invent a competing backup codec. A versioned kanban inventory
profile extends that contract with every current **and archived** card, permanent
IDs, links/dependencies, all revisions, questions/answers, receipts, migration
ledger and history, including historical principals and referenced attachments.
Unknown fields/tables/history generations fail validation rather than disappear.
Archive defaults in the UI must never silently filter a full migration.

`KanbanTransferManifest v1` records the backup format/codec, source namespace,
schema/release versions, coherent snapshot ID, complete inventory, counts, typed
content hashes, attachment/chunk digests, canonical root checksum, mapping digest,
conflict policy and proposed destination scope. The root must be authenticated
through the approved transfer channel; a self-supplied checksum proves no origin.
Manifests, mapping and reports are private artifacts, never PR attachments.

Both UI and API/MCP expose the same stages and receipts:

1. **Preflight and preview:** authenticate source/destination rights, enforce count,
   byte, expansion, nesting, CPU, time, concurrency and disk budgets before allocation.
   Validate version, signature/provenance, checksums and complete inventory. Decode
   inert data with reviewed schema, never executable SQL, scripts or archive paths.
2. **Mapping:** owner explicitly maps source tenant/board/principals to destination.
   Preserve unmapped historical principals as inert identities; no auto-membership or
   account linking. Preserve permanent source IDs with namespace mapping for global
   collisions and durable old-link resolution subject to destination authorization.
3. **Conflict preview:** exact same source namespace/ID/revision/hash is a no-op;
   differing bytes under the same identity conflict. Never overwrite silently.
   Show counts for current/archive/history/files and dangling links, duplicates and
   proposed owner-selected reconciliation. No fabricated approvals or lost history.
4. **Commit into quarantine:** bind operation, manifest/mapping digests, policy,
   destination revision and explicit approval. Use one transaction for promotion
   into quarantined candidate storage where possible; large imports use immutable
   staging chunks and durable checkpoint compare-and-swap, followed by atomic sealing
   of that candidate. This never changes live data or its activation pointer. Restart
   checks actual durable chunks, not progress counters. Mixed visible generations
   and partial live imports are forbidden. Changed inputs invalidate preview.
5. **Backup and test restore:** preserve a verified pre-change recovery point; restore
   the full proposed destination into isolation. Compare exact IDs, typed values,
   revision chains, archive flags, relationships, files and canonical re-export
   hashes, not only totals or one migration ledger. Show missing/extra/conflicting
   records. Report transport-verified separately from restore-verified.
6. **Controlled cutover:** separately approved owner window, writer fence or coherent
   delta capture, final comparison and explicit activation pointer. Keep old source
   read-only and recoverable through the chosen retention period. Dual writers are
   forbidden without a separately proven reconciliation design. If failure occurs,
   stop writes; inspect committed state before choosing resume or rollback.
7. **Rollback/recovery:** retain new writes and receipts before reverting; destructive
   down-migrations are not assumed safe. Prefer compatible forward repair or restore
   plus reviewed delta reconciliation. Independently reestablish current revocations,
   consumed keys and deletion restrictions before dispatch or outward delivery.

Historical approvals/receipts remain unchanged evidence in quarantine; an effective
authority layer marks imported grants non-executable. No imported approval, pending
job, Slack delivery or previous merge permission creates fresh authorization.
Restoring a backup cannot roll back the independent authority freshness anchor.
Unknown freshness blocks activation/dispatch. A private export download is also
authorized at use, scoped, expiring and never a public link.

Axel owns reviewed application schema changes and checksums aligned to releases.
Sugarkube owns privileged execution, backup/test restore, locking, deployment order,
observability and recovery runbooks. Applied migrations are immutable and ledgered;
checksums, preconditions and partial outcomes must reconcile before retry. Prefer
expand/contract compatibility across rolling frontend/API upgrades. Migration lock
and transaction semantics are engine-specific acceptance gates. Runtime roles have
no DDL privileges; no migration runs on API startup or through a card action.

## End-to-end threat model and security regression matrix

Trust boundaries are browser-to-session service, provider-to-ingress, agent-to-policy
API, API-to-DB, queue-to-worker, artifact-to-importer, build-to-deployment and
backup-to-recovery authority. Attackers include malicious tenants, stolen sessions,
forged/replayed events, hostile content, compromised dependencies/workers and stale
or tampered backups. Assets include private card existence/content, membership,
approvals, history integrity and credentials. Each row below is a **planned**
regression gate; none has been executed by this documentation PR.

| Threat / boundary | Required adversarial test and positive control | Residual risk / owner |
| --- | --- | --- |
| Login/session/CSRF | Reject wrong/reused state, substituted code/verifier, callback/open redirect, session fixation, missing CSRF, hostile Origin and expired/revoked sessions; valid login and scoped write succeed. | Browser/provider compromise; Axel identity owner. |
| Account linking/Sites bridge | Same email/name cannot link; swapped subject/issuer/audience, forged header and replay fail; independently verified subject linking succeeds. | Provider recovery fraud; identity owner. |
| Slack forgery/replay/history | Invalid raw-body signature, stale timestamp, wrong workspace/channel, duplicate event and edit/delete reordering cannot create repeated work; valid configured sender creates one request. Future join/rejoin, connected organization, revoked reader and history-export tests must preserve the approved disclosure audience or block card-specific replies. | Provider compromise and ambiguous delivery; integration owner. |
| Prompt injection/tool authority | Malicious text, attachments, CI output and imported approvals cannot invoke shell/SQL, broaden capabilities, approve or deploy; allowed typed proposals work. | Bugs in approved tools; Axel/security reviewer. |
| Tenant/board IDOR | Cross-tenant and same-tenant private-board guesses fail on CRUD, archives, history, search/facets, links, caches, jobs, subscriptions and export/status/download; authorized equivalents succeed without existence leaks. | Policy implementation defects; Axel/storage owner. |
| Import/archive abuse | Truncation, checksum substitution, unknown schema, omitted archives/history, giant cells, bombs, nesting, traversal, symlink and collision tests fail before unsafe allocation/activation; bounded synthetic round trip preserves exact inventory. | Parser defects/resource exhaustion; importer owner. |
| DB isolation/concurrency | Forged tenant context, connection-pool reuse, cross-scope foreign keys, stale revisions, duplicate concurrent requests and crash-before/after-commit cannot bypass policy or duplicate effects. Runtime DDL denied; approved transaction succeeds. | Engine/driver defects, privileged operators; shared owner. |
| Migrations/backups | Wrong release/checksum, interrupted migration, stale restore authority and mixed generations fail closed; backup/test restore and forward/backward compatibility evidence pass on supported versions. | Correlated disk loss, recovery/key loss; Sugarkube. |
| SSRF/XSS/content | Internal/link-local/metadata IPs, DNS rebinding, redirects, dangerous URL schemes, active HTML and malicious filenames cannot fetch privileged targets or execute in UI; escaped inert rendering works. | Sanitizer/browser defects; Axel. |
| Logs/secrets/privacy | Canary private records and credentials never appear in public builds, maps, errors, traces, analytics, notifications or source history; authorized private audit remains useful. | Human publication and third-party retention; shared owner. |
| Supply chain/release | Modified lockfile, tag/artifact substitution, unsigned/untrusted provenance, schema mismatch and compromised dependency fixture block admission; clean rebuild digest and receipt agree. | Trusted builder compromise; release/Sugarkube owners. |
| Recovery/availability | Rate floods, full disk, lost acknowledgement, removed channel, revoked actor, restart and restore preserve idempotency and bounded queues; kill switch stops new work and legitimate recovery remains possible. | Denial of service and unknown external sends; shared owner. |
| Profile separation | With Internet disabled, local board works; private LAN inference cannot reach online adapter routes, telemetry or fallback providers. Online workers cannot reach corpus/UI or local backups. | Host/admin compromise; deployment/security owner. |
| Initial-mode encryption/keys | Plaintext transport, wrong certificate, unencrypted volume/backup, wrong restore key and unauthorized key access fail; approved encrypted backup/restore and rotation succeed. Verify no content in diagnostics. | Privileged operators may still decrypt; shared owner. |
| Dot recipient/disclosure | Forged recipient/audience, cross-board field requests, expired/revoked grants, replayed writes and queued actions after revocation fail; valid scoped read/write succeeds with recorded disclosure scope. No outage fallback to broader tools or credentials. | Already disclosed plaintext/provider retention; Axel/integration owner. |
| Multi-PR completion | One merged/one open, stale head CI, dismissed review, closed-unmerged and missing companion link never yield Done; verified owner merges for every required PR do. | Provider observation delay; Axel owner. |

Implementation evidence must attach fixture version, tested release/head, environment,
expected and actual result, negative/positive controls, resource measurements and
failed/skipped/unrun cases. A unit assertion about a filter is not end-to-end tenant
isolation. Real private data stays blocked until applicable gates and operational
recovery proof are reviewed. This design cannot eliminate compromised administrators,
provider outages or the risk of authorized users copying content.

## Open decisions and review evidence

Before implementation, agree: exact Sites/BFF hosting capabilities and callback
origin; approved API ingress; roles and audience policy; GitHub app type/scopes;
Slack installation/mapping, edit/delete retention and replay horizon; schema/codec
profile and numerical resource limits; authority freshness anchor; DB engine and
isolation proof; backup/key custody, recovery objectives and retention; cutover
window and backward-compatible migration policy. Future ChatGPT identity requires
actual partner access and a separately verified contract. No engine or entitlement
is implied by acceptance of this design. Initial-mode dot identity/tool authorization,
field/disclosure scope, encryption/key management and provider retention review also
remain implementation gates. Website sign-in eligibility is distinct from agent
authorization; neither proves the other. Full E2EE decisions and qualification are
tracked separately in [Axel #252](https://github.com/futuroptimist/axel/issues/252).

The [companion platform design](https://github.com/futuroptimist/sugarkube/blob/9bc51b2a1d34eb25fb540e2631464069fbac8f68/docs/design/axel-database-platform.md)
was re-inspected at published head `9bc51b2a1d34eb25fb540e2631464069fbac8f68`.
That revision predates these initial-mode/dot clarifications and optional E2EE
roadmap notes. The companion's local amended `docs/design/axel-database-platform.md`
was then inspected at SHA-256
`9eadb6a27969e609c9475136f62c54d60a3cdd4841a0d411119bb6655e937727`.
It aligns initial trusted-server processing, scoped dots/Slack without a mandatory
gateway, and optional future E2EE. This identifies an observed local snapshot, not
a published/final head or automatic approval of subsequent edits. Record actual
reviewed heads separately after publication; no mutually dependent final hashes.
Its provisional
PostgreSQL-first evaluation does not select an engine. Its encrypted off-site
recovery proposal applies to the separately approved online service; it does not
change the sensitive profile's device-local backup restriction. Sites publication
automation remains unverified and needs a manual verification gate until supported.

The companion Sugarkube PR must agree the release/compatibility handshake above,
privilege split, health semantics, backup/test-restore gates and staging-only rollout
boundary. Track any disagreement on K269; neither PR silently overrides the other.
Populate both direct links and final-head evidence on the private card without
publishing its private contents. The card cannot be Done during this PR preparation.

Repository inspection used main `07db020ad699f19fe095923d09a107d11d0c3e47`,
root `AGENTS.md` (no `.agents/skills` present), the backup contract, remote-control
design, Discord guide, threat model and pinned PR #249 above. Local/CI documentation
checks belong in the PR evidence and must be distinguished from the planned matrix.
No private checkout/data, live database, migration or deployment was exercised.

Primary protocol references checked 2026-10-10:
[GitHub authorization code and PKCE](https://docs.github.com/en/apps/oauth-apps/building-oauth-apps/authorizing-oauth-apps),
[Slack request verification](https://docs.slack.dev/authentication/verifying-requests-from-slack/).
Revalidate provider behavior and supported deployment capabilities before implementation.
