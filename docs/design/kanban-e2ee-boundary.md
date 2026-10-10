# Optional future kanban end-to-end encryption

**Long-term roadmap proposal, 2026-10-10; not an initial release requirement.**
The [kanban contract](sanitized-kanban-contract.md) uses an explicitly trusted-server
initial mode with scoped Slack and ChatGPT dot endpoints, TLS, at-rest encryption
and tenant isolation. This optional future mode has a stronger target: hosting,
API, database and backup operators must not receive content plaintext or usable
content keys. Its qualification gates apply only before enabling or claiming this
stronger mode. No implementation, cryptographic qualification, migration or deployment
is performed. Product details below remain open decisions. Earlier published PR
CI does not validate these local amendments.

One public roadmap item tracks this extension:
[Axel #252](https://github.com/futuroptimist/axel/issues/252). Sugarkube owns its
platform implications through the paired design, not a duplicate E2EE issue.

## Boundary required for the optional mode and exposed metadata

Encrypt titles, descriptions, questions/answers, comments, full revision history,
attachment bytes/names, private links/dependencies and content-bearing receipts on
trusted endpoints before hosting. The password unlocks the user's entitled keys;
there is no operator universal decrypt-all password or server master-key escrow.
Operator status never confers recipient status. TLS, RLS, membership checks, narrow
roles and the existing private-LAN profile remain necessary defense in depth.

The hosting plane can see a deliberately inventoried outer envelope: opaque tenant,
board/object/device IDs, account/membership and recipient-key relationships, key
epochs, revisions, ciphertext lengths/counts, timing, IP/access patterns, quotas and
operation status. This metadata is still sensitive and access-controlled. Semantic
columns, PR URLs, private relationships and plaintext content hashes stay encrypted
unless a separately approved minimal disclosure is needed. Deterministic hashes or
search indexes can leak guesses/equality. Padding may reduce length leakage but
does not hide traffic patterns. Do not promise that operators see no user metadata.

A malicious operator can deny service, hide/fork records or bypass its own RLS.
The target is that it cannot decrypt content or substitute itself as a recipient.
Endpoint compromise, malicious authorized recipients, weak passwords and update
authority compromise remain risks. This is not an attack-proof system claim.

## Protocol, passwords and client qualification

Select an established, independently reviewed collaboration/encryption protocol and
maintained libraries with test vectors, audit history, compatible licenses, supported
runtimes and vulnerability response. Independent cryptographic review must qualify
composition, key distribution, nonce rules, concurrent edits, recovery and updates.
Do not invent primitives or assume that choosing an AEAD cipher supplies a protocol.

GitHub sign-in authenticates API access; it neither derives nor releases content
keys. A separate user-chosen password unlocks a randomly generated local key vault.
Use cryptographically random content keys, per-board key epochs and authenticated
key wrapping to individually entitled devices under the qualified protocol. Never
derive all content keys directly from a password or reuse the login credential.
Passwords, derived keys and plaintext never reach the API/BFF, logs or telemetry.

Use a qualified memory-hard password KDF, with Argon2id as the candidate from
[RFC 9106](https://www.rfc-editor.org/rfc/rfc9106.html). Require unique random salts,
authenticated versioned parameters, measured device costs, a minimum security floor
and maximum resource bounds; unsupported devices block rather than silently weaken
the KDF. Stolen encrypted vaults allow offline password guessing. Memory hardness
raises cost, but does not make a weak password safe, and server rate limits cannot
stop offline guessing. Parameter values and supported devices remain decisions.

Password change rewraps the vault after local unlock. Old wrapped vaults/backups
and copied keys remain usable with old secrets; password change is not revocation.
Suspected compromise needs key rotation and a reviewed re-encryption/history policy.
Auto-lock clears usable keys and plaintext caches as far as the qualified platform
permits; browser garbage collection is not guaranteed secure erasure. Protect local
indexes, device backups, swap and crash dumps. A compromised unlocked device or
extension may capture plaintext even when a key is marked non-extractable.

Ordinary operator-served JavaScript can be changed to capture passwords, keys or
plaintext. TLS, CSP, non-extractable keys, server-displayed hashes and reproducible
builds alone do not prevent that operator shipping malicious code. Strong operator
blindness requires a separately installed or independently verified/pinned client,
independently authenticated bootstrap and update signing, explicit update acceptance
and downgrade protection outside hosting control. Qualify the OS/browser and update
authority as well. Sites may provide a generic portal or asset distribution, but a
mutable Sites decrypting frontend without this boundary has a **weaker trusted-frontend
assumption**, not the required strong operator protection. Client choice is unresolved.

## Collaboration, enrollment, revocation and recovery

Use individual recipient/device keys, not a shared board password. Enrollment needs
current server membership and an authorized existing member/device verifying the
new recipient key independently: an authenticated out-of-band fingerprint ceremony
or qualified key transparency resistant to server equivocation. Bind stable
account/device identity, board, role, key fingerprint and membership epoch; verify
signed membership transitions and their authorization. A directory controlled only
by hosting, GitHub login or first-use trust alone does not stop key substitution.
First-device bootstrap, replacement devices and transparency trust roots need an
independent trust path. Server-added members do not automatically receive keys.

Key distribution grants only approved boards/epochs. Sharing old history with new
members is explicit. Removal revokes API/session access, rotates future board keys,
excludes removed devices from new envelopes and fences stale-epoch writes. Concurrent
and offline writers need reviewed epoch reconciliation, not automatic key reuse.
Revocation cannot erase previous plaintext, screenshots, backups or downloaded old
ciphertext plus old keys. Do not claim forward secrecy or post-compromise security
unless the selected protocol and retention policy provide and test those properties.

Recovery material is user-held: a high-entropy recovery secret or independently
approved trusted device can recover the encrypted vault. Operators back up ciphertext
and wrapped envelopes only, with no master-key escrow. Account/password reset
restores authentication, not old decryption capability. A board member may explicitly
re-share keys after verified re-enrollment; this is a new grant, not an administrator
bypass. Without a surviving entitled device/key or user-held recovery material,
affected content is irrecoverable. Show and rehearse that outcome before real use.

## Context integrity and freshness

Authenticated encryption must bind tenant, board, immutable object ID, revision,
payload/schema/protocol version, key epoch, author device and attachment chunk
position/count using canonical encoding. Follow the qualified protocol's nonce
rules and author authentication. Reject substitution, truncation, cross-board replay
and unknown versions before rendering. AEAD alone does not prove authorship or
freshness. Client-verified signed revision/membership chains and checkpoints held
outside hosting control must detect rollback/forks where possible.

An isolated first-time or restored client cannot establish the newest state from
that server alone. Missing independent freshness evidence blocks sensitive actions
and shows stale/unknown state; it must not silently accept old history as current.
Resolve concurrent branches, offline availability, checkpoint loss and trustworthy
recovery bootstrap during protocol qualification. Restoring application backups
cannot restore old action authority, revoke newer policy or silently re-enroll keys.

## Agent and Slack choices for the optional mode

Recommend private-by-default boards, generic content-free Slack notifications that
link to the encrypted-app entry without card IDs/titles, and decrypting agents on
trusted user devices. Notification timing itself reveals activity and still needs
an approved audience policy. Search, semantic validation, content previews and
content-aware agents run only on trusted unlocked endpoints; hosting cannot do
these plaintext operations. A decrypting agent operated by the kanban host breaks
operator blindness. Authorized ChatGPT dots remain a supported design goal as
explicit trusted cloud recipients of selected content, not local-only processing.

For this optional mode, recommend a user-controlled gateway that locally unlocks
only granted board/task content, transmits approved plaintext to the verified dot
and accepts proposed updates through validation, current authorization and revision
checks before client-side encryption. Hosting receives ciphertext only and holds
no content keys. The gateway must be controlled by the user independently of the
hosting operator: an operator-administered decrypting gateway defeats the boundary.
Tenant-owner grants specify recipient, board/task scope, read/write tools, exact
disclosure or a clearly bounded standing disclosure policy, purpose and expiry.
An action grant never silently authorizes every future disclosure. Recheck grants
and revocation per use; bind request IDs, audience, digest and revision for replay
resistance and retain safe audit receipts. Locked/offline/unverified gateway means
blocked cloud-agent access, not hosted decryption or broader fallback.

Selected plaintext crosses into OpenAI processing. No universal key is supplied,
and no claim is made about zero retention, guaranteed deletion or supported product
authentication. Dot/MCP authorization, recipient verification and secure gateway
connectivity require actual capability verification before implementation. Revocation
stops future access; it cannot erase previously disclosed plaintext or copies.

A deliberately trusted user-controlled LAN-only token.place pool may process minimum
approved context under existing enrollment/no-egress rules. Every compute node that
sees plaintext is then an explicit trusted endpoint, not a cryptographically blind
processor. No automatic cloud/model fallback or remote logging is permitted. This
option does not expose the strict profile's corpus, UI or keys to online adapters.

Password-on-every-unlock pauses content work while locked. Unattended processing
requires a separately approved retained local key/session scoped to selected boards,
actions and duration, with revocation, expiry/lock behavior and device hardening.
This availability/exposure tradeoff is not yet an accepted product choice. Hosting
may queue opaque work but cannot decrypt it or bypass a locked client. Read access
and a retained key do not supply action-specific execution/export approval.

Ordinary [Slack message events](https://docs.slack.dev/reference/events/message/)
contain plaintext. Slack and the receiving endpoint can read them; encryption after
receipt cannot retroactively make the path E2EE. Prefer composing private requests
in the trusted client. Optional ordinary Slack intake is a disclosed less-private
path, requiring explicit scope/retention choices and consent. A trusted client or
user-controlled receiver can encrypt before Axel hosting, but Slack still saw the
source. A hosted plaintext receiver is an additional confidentiality exception,
never an operator-blind inbox. When no trusted endpoint is unlocked, processing
waits. Signature, idempotency and audience checks still apply to either chosen path.

## API, migrations and Sugarkube handshake

Bind confidentiality mode to authenticated board metadata, client policy and release
compatibility. Switching an E2EE board to trusted-server mode or exporting plaintext
requires a separate explicit authorized disclosure decision; outages, old clients,
schema migration and recovery must never silently downgrade it. Mode negotiation
cannot rely only on an operator-supplied flag. Keep different-mode grants and caches
separate and visibly label the effective mode before sharing or recovery.

In this optional mode the parent contract's HTTPS/API/MCP routes carry authenticated
ciphertext envelopes and approved metadata. Server-side validation covers membership, quotas,
envelope shape, revision and durable operation semantics; trusted clients validate
plaintext semantics and cryptographic membership. Key enrollment/epoch envelopes
require verified client authorization under the selected protocol. No server-side
decrypt/unwrap endpoint or raw-content search index is permitted.

Keep content-bearing action details/receipts encrypted. An external executor needing
plaintext is a separately authorized trusted recipient, not an implied API service.
Servers can check scope/signatures and ciphertext-bound commitments, but cannot
claim to verify encrypted task semantics or PR completion. Trusted clients verify
and encrypt that evidence, subject to freshness limits; hosted CI integration needs
a separately disclosed PR-metadata scope. Do not silently disclose private PR links
to restore convenient server-side completion checks.

Idempotency commits canonical ciphertext envelope digests, not plaintext hashes.
Preserve exact encrypted bytes across delivery retries; re-encryption is not the
same payload under an existing key. Semantic deduplication remains client-side.
For this optional mode, `ReleaseManifest v1` also binds crypto protocol/envelope versions,
qualified libraries, client artifact/update trust identity and supported key/schema
epochs. A manifest served only by the operator cannot authenticate its own client.

Sugarkube stores/backs up ciphertext and recipient-wrapped envelopes. Infrastructure
backup keys are separate from user content keys and cannot unwrap them. Operational
checksums cover ciphertext; encrypted manifests contain private inventory and logical
hashes. Sugarkube proves ciphertext/infrastructure restore; an authorized unlocked
client separately proves decryption, exact history/attachment recovery and semantic
equivalence. Both receipts are required. Server restore success is not content recovery.

Privileged schema jobs migrate outer storage/envelopes without content keys. Changes
needing plaintext semantics or re-encryption are trusted-client operations with
reviewed dual-version compatibility, not temporary server escrow. Preserve the
existing quarantine/restore/comparison gates before separately approved activation.
Do not drop TLS/RLS just because stored content is encrypted.

Existing plaintext migration is separate work on a trusted conversion endpoint:
inventory every current/archived record, history and attachment; encrypt before
upload; compare privately and preserve required recovery points. Old databases,
WAL, replicas, logs, exports and backups may still contain plaintext or have been
copied by prior operators. Track their retention/deletion plan and residual exposure;
encryption cannot retroactively revoke knowledge or prove all copies vanished.
Neither migration approval nor encrypted backup possession authorizes plaintext
publication. No private data is inspected for this design amendment.

## Proposed unrun negative and recovery tests

Every test below is planned and unexecuted. Record exact protocol/library/client
versions, adversary capabilities, positive controls, measured limits and residual
risks; documentation CI is not cryptographic assurance.

| Boundary | Required negative test and positive control |
| --- | --- |
| Operator access | API/DB/backup dumps and admin accounts reveal no content, keys, password, plaintext indexes or low-entropy content hashes; an entitled verified client decrypts its complete board. |
| Password vault | Wrong password, modified KDF parameters/salt, downgrade and excessive resource demand fail safely; calibrated supported unlock works. Benchmark offline guessing exposure without claiming immunity. |
| Client/update trust | Replaced hosted JavaScript, malicious bootstrap, forged update signer and rollback cannot become the trusted decrypting client; independently authenticated approved update succeeds. Test unlocked endpoint leakage separately. |
| Enrollment/substitution | Server-inserted recipient, key-directory substitution/equivocation, forged membership signature and new device without independent verification obtain no keys; verified enrollment works. |
| Epoch/revocation | Removed device cannot decrypt new-epoch data or write a stale epoch; concurrent/offline edits reconcile safely. Demonstrate that old plaintext/keys/copies remain accessible rather than asserting erasure. |
| Context/freshness | Cross-tenant/board/object/chunk swaps, author substitution, nonce misuse, truncation and unknown schema fail. Rollback/fork, lost checkpoint and isolated new client produce detected or explicitly unknown freshness, not false assurance. |
| Recovery | User recovery secret/trusted device recovers full archived history and attachments; wrong/lost recovery material and authentication reset alone do not. Operator cannot bypass irreversible loss. |
| Agents/Slack | Locked endpoint pauses; scoped retained session expires/revokes; hosting receives no keys. LAN enrollment/no-egress holds. Forged dot recipient, revoked/expired grant, replayed write and offline gateway fail closed; valid scoped dot access works with explicit cloud disclosure. Slack exception is visible and generic notifications contain no card-specific data. |
| Migration/restore | Ciphertext restore matches digests but is not marked content-recovered until trusted-client proof; stale authority remains inert. Inventory legacy plaintext recovery copies and exposure without publishing records. |

Open decisions: independent client/distribution/update trust; qualified collaboration
protocol and libraries; supported device/KDF budget; key verification/bootstrap and
freshness anchors; history sharing, rotation and recovery UX; minimal exposed
metadata; trusted LAN processing versus locked-only work; unattended local sessions;
Slack intake exception versus generic notifications; legacy plaintext retention and
re-encryption/migration policy. No engine is selected and no risk is solved by prose.

## Evidence and references

This local amendment starts from Axel `5e79cdc51f7d58aace96a5de865b65dcb131deb4`.
Sugarkube #2910's published `9bc51b2a1d34eb25fb540e2631464069fbac8f68` was re-inspected:
it aligns API/migration ownership and recovery freshness, but predates these initial-mode
clarifications and optional E2EE roadmap notes. Its local amended platform design
was subsequently read at SHA-256
`9eadb6a27969e609c9475136f62c54d60a3cdd4841a0d411119bb6655e937727`.
The modes and API/migration responsibilities agree. This is evidence for that local
snapshot only, not an unseen final head; recheck any later substantive changes.
Record publication heads in separate review evidence, without circular final hashes.

Primary references checked 2026-10-10: [PostgreSQL encryption options](https://www.postgresql.org/docs/18/encryption-options.html)
distinguishes client-side protection from server-side decryption and disk encryption;
[RFC 9106](https://www.rfc-editor.org/rfc/rfc9106.html) supplies Argon2 guidance and
vectors (the RFC Editor plain-text edition was read);
[WebCrypto security considerations](https://www.w3.org/TR/2017/REC-WebCryptoAPI-20170126/#security-considerations)
warn about protocol composition, script and key-storage trust; and the
[Slack message event](https://docs.slack.dev/reference/events/message/) documents
plaintext message fields. These support the boundary analysis, not a completed
protocol/library qualification or a claim that any deployment passes these tests.
