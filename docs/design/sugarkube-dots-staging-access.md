# Sugarkube staging access from ChatGPT Dots

**Status: proposed design, documentation only. Reviewed 2026-11-08.** No server,
client, credentials, network route, plugin connection, cluster permissions, or
deployment is provisioned by this proposal. Implementation needs a separate decision.

## Recommendation

Build a **small Sugarkube operations service with a narrow MCP interface**, if a
read-only connection test proves that the intended ChatGPT Dot can use it. ChatGPT
is the MCP host/client; a second custom conversational client is not needed. A
local CLI/test client can exercise the same service during development.

Start with chart verification and sanitized staging diagnostics. Keep the owner-run
command workflow as the immediate fallback. A dedicated connected executor with
restricted SSH is the simpler intermediate option when its network permissions
actually permit the connection. Do not build an unrestricted SSH, shell, or
Kubernetes proxy and call it a narrow MCP server.

The recommendation separates three decisions:

1. **Reachability:** which approved execution environment or service can reach the
   staging operations host and registry?
2. **Capability:** which fixed operations and resources can that identity access?
3. **Authority:** which operations may run now, and which remain owner-operated?

MCP improves the shape, discoverability, and auditability of capabilities. It does
not grant network reachability, make credentials safe by itself, or authorize a
deployment. The first milestone needs neither cluster mutation nor a new GHCR
credential if an authorized existing registry login already works.

## Scope and relationship to existing designs

Axel owns the orchestration contract and this comparison. Sugarkube should own the
cluster-specific adapter, operation catalog, and deployment/runbook implementation.
Keep reusable MCP protocol code thin. Reuse tested Sugarkube checks rather than
reimplementing Helm, Kubernetes, or release-verification logic in a chat client.

This is a network-capable, explicitly opted-in operations profile. It does not
relax the separate [private LAN planning design](chat-operations-contract.md),
grant access to its private corpus, or reuse its isolated approval UI as a remotely
reachable endpoint. The [remote Claude Code design](remote-claude-code-control.md)
is also separate. Sugarkube already has a [remote-operations design][sugarkube-remote]
and a [chart-lock contract][chart-lock]; neither proves a particular Dot has access.

In scope:

- Pull and inspect an exact approved chart; compare version and digest evidence.
- Obtain bounded staging workload status, events, and selected sanitized logs.
- Plan later, explicitly authorized staging experiments and validation.
- Compare a human handoff, connected computers, direct APIs, MCP, CI, and GitOps.

Out of scope for the initial service:

- Production access, cluster-wide administration, arbitrary code execution, or a
  general terminal exposed to the model.
- Merge, publish, deploy, rollback, persistent-volume deletion, node reset, package
  upload, credential rotation, or security-setting changes.
- Registering a plugin, opening a firewall, enrolling a VPN node, creating an OAuth
  grant, or changing any current approval policy as part of this documentation PR.

Staging can be a disposable experiment target without making every associated
asset disposable. Registry credentials, production isolation, backups, personal
data, other LAN devices, and the control service itself remain protected.

## Feasibility and evidence boundary

An owner terminal reaching a host does not establish that the assistant's selected
executor can reach it. A local socket-access denial can occur before SSH
authentication. A different SSH key cannot repair that denial. Stop and use the
supported permission/configuration process or an owner-run handoff; do not try an
alternate port, proxy, tunnel, UI-launched terminal, or executor to evade it.

For example, an owner-run SSH session can succeed while a restricted assistant
process on the same computer is denied before authentication. That is a permission
or execution-context distinction to diagnose, not evidence of a bad SSH credential.
Keep private addresses, device/account identifiers, fingerprints, credential history,
and raw diagnostic output out of public evidence. No connectivity test is claimed here.

The following remain acceptance gates, not assumptions:

- The intended Dot/account can discover and call the proposed integration through
  a supported connection path. A server working in another client is insufficient.
- The selected executor/service has an authorized route to the staging target.
  Cloud execution does not automatically join a private LAN or tailnet.
- The registry identity can pull the exact chart, not merely log into GHCR.
- The downstream identity is independently unable to reach production resources.
- The connection can be revoked and the resulting denial observed.

## Options compared

All rows assume explicit setup authorization and existing owner action gates.
Relative setup cost includes securing and maintaining the solution, not just making
a successful demo. Transport choices such as a tailnet are additions to an access
option, not replacements for authorization or Kubernetes RBAC.

| Option | Dot feasibility and connectivity | Useful capabilities | Isolation and credential custody | Setup / ongoing operation | Audit, revocation, and owner gates | Assessment |
| --- | --- | --- | --- | --- | --- | --- |
| A. Owner runs reviewed commands | Works without assistant LAN access; owner supplies sanitized results | Exact chart checks, diagnostics, and owner-executed changes | Credentials remain on owner's machine/host; human must review output | Lowest setup; highest repeated owner effort | Command/result evidence; owner controls every execution | Immediate fallback and recovery path |
| B. Connected desktop plus restricted SSH | Requires that exact assistant executor to permit TCP/SSH; depends on desktop availability | Allowlisted host checks and chart verification; wider operations only after separate authorization | Dedicated key and forced-command account; private key stays on executor | Low to medium; host trust, key rotation, sleep/offline issues | SSH identity plus operation receipts; remove key; no arbitrary shell | Best small intermediate step when proven reachable |
| C. Dedicated connected remote executor plus restricted SSH | Persistent approved executor with a legitimate LAN/overlay route; product registration must be supported | Same as B, with more reliable availability | Dedicated machine/account and staging-only route; no personal workstation or production credentials | Medium; patching, connection health, backup and revocation | Per-executor identity and wrapper audit; revoke both executor and key | Useful if ongoing host operations justify a maintained machine |
| D. Direct scoped Kubernetes API plus separate GHCR access | Needs approved API endpoint reachability and a compatible execution tool; no SSH required | Namespace diagnostics; no host/service logs; chart pull uses a separate client | RBAC credential and full allowed objects reach executor; RBAC does not redact fields; never use admin kubeconfig | Medium; TLS, short-lived identity, network policy, client configuration | Kubernetes audit/RBAC revocation; no deployment permission by default | Good for Kubernetes-only work, weaker output privacy than a filtered service |
| E. Remote authenticated MCP operations service | Verify Dot onboarding; remote HTTPS or OpenAI Secure MCP Tunnel, subject to account/workspace support | Fixed chart/health/log tools; later approved operations with explicit contracts | Backend holds downstream credentials; Dot receives scoped service authorization and sanitized results | Medium to high; service, authentication, schema, transport and availability | Central per-call audit; revoke service grant and downstream identity; server enforces policy | Preferred long-term interface after a read-only feasibility spike |
| F. Local stdio MCP server on a workstation | Useful in a client that launches it; local Codex configuration does not prove cloud Dot exposure | Same typed tools as E while workstation runs | Local process identity and local credentials; stdio is transport, not a sandbox | Low to medium locally; separate Dot integration may still be required | Process/OS controls plus tool audit; stop process/revoke local identity | Useful developer harness; not a proven Dot delivery path |
| G. Fixed CI workflow / job broker | GitHub connector can observe supported runs; dispatch support and LAN runner routing need verification | Registry validation and reproducible bounded jobs; slower interactive diagnosis | Prefer ephemeral workflow token; LAN runner must not execute untrusted PR code with cluster access | Medium; pinned workflows, isolated runner, queue and artifact hygiene | Run ID, commit/digest and environment gates; revoke runner/token | Strong option for registry-only checks or controlled repeatable jobs |
| H. GitOps with owner-reviewed desired state | Dot can prepare approved PRs; cluster controller handles reconciliation | Declarative rollout and status; weak for ad hoc host diagnosis | Controller holds cluster credentials; agent needs only authorized repo rights | Medium to high unless already adopted; controller and rollback design | Git history plus controller audit; revoke repo/controller permissions; merge triggers deployment | Later deployment architecture, unnecessary for the initial read check |

### Why not simply SSH as the existing administrator?

It is easy to demonstrate but gives a broad host identity access to unrelated files,
stored registry logins, sudo, and often the cluster administrator configuration.
Adding a new key to that account does not reduce those OS permissions. Prefer a
separate account and fixed operation wrapper. OpenSSH's `restrict` option disables
forwarding/PTY-related features; it does **not** itself constrain commands. Pair it
with a protected forced command when that is the intended boundary. [OpenSSH][ssh]

No SSH forwarding is useful hardening, but does not stop a general shell from making
ordinary outbound connections. An honest staging-only boundary also needs network,
filesystem, and downstream-identity restrictions.

### Why not start with a VPN, a generic Kubernetes MCP server, or GitOps?

A tailnet can supply an approved route but does not enroll ChatGPT's cloud services
automatically, expose local tools to a Dot, or override executor policy. The existing
Sugarkube remote-access design remains the source for any separately authorized
network work. Do not publish SSH or the Kubernetes API to the Internet just to make
an assistant integration convenient.

A generic Kubernetes MCP server may expose more APIs than this use case needs.
Selectively advertising tools is not enough if its backend identity is still
cluster-admin. A reviewed existing implementation could be reused only after its
tool surface, transitive permissions, and output handling meet this contract.

GitOps is attractive for eventual declarative deployment, but cannot establish that
a registry artifact exists or that a host is healthy on its own. Merging desired
state can be a deployment even without an explicit deploy command; preserve owner
control at that boundary.

## Proposed MCP architecture

The intended flow is:

1. ChatGPT Dot uses an owner-installed, supported MCP/plugin connection.
2. An authenticated service validates caller identity, audience, scopes, operation
   schema, current policy, and resource allowlists.
3. A staging-only adapter runs one fixed operation using a separately constrained
   registry, Kubernetes, or host identity.
4. An output filter returns bounded structured evidence plus a correlation ID.
   Audit storage receives metadata, not credential-bearing command transcripts.

Keep the control service outside the staging failure domain where practical. If it
runs inside staging, explicitly accept that a staging rebuild or outage may remove
both access and diagnostics; preserve the owner-run recovery path. Network isolation
must still hold if the service, adapter, or staging workload is compromised.

### Server, client, and connector responsibilities

- **MCP server:** publishes typed tools/resources and implements the operations
  boundary. Use a maintained SDK, minimal dependencies, and pinned builds.
- **ChatGPT:** supplies the agent-facing MCP client/host through its supported
  integration. Account eligibility, distribution, discovery, and authentication
  must be demonstrated on the intended Dot before implementation expands.
- **Optional local client:** CLI smoke tests and protocol tests, not a new chat UI
  or a bearer of broad production credentials.
- **Private-network connector, if needed:** a distinct authenticated transport
  component, not the conversational MCP client. Its availability, supported
  product path, and allowed destinations require separate validation.

### Supported OpenAI connection paths

OpenAI documents custom MCP servers as personal or workspace plugins. The setup
creates the plugin, configures authentication, and installs it before use. Account
and workspace restrictions still apply. These sources establish ChatGPT/Work
support, not successful availability to this particular Dot or its background
tasks; phase 1 must demonstrate the intended runtime. [Custom MCP connections][openai-custom]
[Plugin testing][openai-connect]

Option E has two transport variants:

- **E1: Remote HTTPS.** A reachable HTTPS endpoint using Streamable HTTP, normally
  `/mcp`. Custom connections also support SSE; prefer Streamable HTTP for this new
  service. Public network reachability does not require anonymous access or public
  plugin-directory distribution. [Custom MCP connections][openai-custom]
- **E2: Secure MCP Tunnel.** A separately authorized host that already reaches the
  private MCP server makes an outbound-only connection to OpenAI. The maintained
  tunnel client forwards requests to a local stdio or HTTP backend. It needs
  outbound HTTPS, a runtime API key, tunnel permissions, and the correct Platform
  organization/ChatGPT workspace association. Creating a tunnel requires Read and
  Manage permissions; running or selecting it requires Read and Use. No public MCP
  ingress is needed, and public plugin distribution is not supported through this
  path. [Secure MCP Tunnel][openai-tunnel]

For this private staging service, evaluate E2 before public ingress, subject to
account availability, operational cost, and separately approved setup. Its client
is transport infrastructure, not a second conversational client. Neither variant
is a workaround for an executor denial. Compare E1's ingress/authentication burden
with E2's always-on connector and control-plane credential lifecycle.

Local desktop/CLI MCP configuration is a different path: ChatGPT web does not read
local Codex configuration, and local transports may be unavailable to cloud
orchestration. A working stdio test alone does not establish Dot access. Do not
assume a repo-local server, loopback URL, or private DNS name becomes cloud-reachable
without an explicit supported connection. [MCP client configuration][openai-local]

The label "Personal" alone does not prove owner-only access. Verify plugin access
settings, tunnel workspace association, authenticated-user allowlist, and an
unauthorized-user denial test. No such account configuration has been inspected
for this proposal, and this document authorizes no public exposure or setup.

### Initial tool catalog

Tool names below are proposed application APIs, not existing ChatGPT capabilities.
All initial operations are read-only against the cluster and registry. Local scratch
downloads are bounded, non-executing, and separately cleaned under retention policy.

| Tool | Inputs and evidence | Required boundary |
| --- | --- | --- |
| `staging_identity` | Returns configured environment label, opaque cluster identity, adapter version, observation time | No arbitrary endpoint or context selector; never return kubeconfig or certificate material |
| `verify_chart` | Approved application key, exact version and/or OCI manifest digest; returns pull outcome, OCI manifest digest, chart archive SHA-256, selected metadata and named verification-profile result | Resolve registry/path from server configuration; bounded download/parser; no upload, install, dependency execution, or arbitrary URL |
| `workload_status` | Approved application key; returns rollout state, image digests, readiness and restart counts | Fixed staging namespace/resource mapping; field allowlist and response limits |
| `recent_events` | Application key plus bounded time window; returns normalized event summary | No cross-namespace search; redact message fields and cap volume |
| `log_excerpt` | Application key, allowed component, bounded time window and line limit | Opt-in per workload; strip credentials/private payloads; block unsafe output rather than return raw logs |

Use small enums and strict schemas with unknown fields rejected. Never accept raw
shell, `kubectl`/Helm arguments, file paths, kubeconfig text, arbitrary selectors,
registry hosts, namespaces, URLs, proxy settings, plugins, or post-renderers. Invoke
fixed binaries with argument arrays, a scrubbed environment, fixed working
directories, timeouts, and output limits. Do not evaluate model-produced commands.

Tag reads accurately for host UX, but treat MCP read-only/destructive annotations
as descriptive hints. Enforcement belongs in the server and downstream identity.
Chart content, logs, events, and tool descriptions are data, never authorization.

## Authentication, credentials, and least privilege

### Independent identities

Maintain separate identities for the Dot-to-service connection, service-to-staging
access, and GHCR downloads. A registry token cannot SSH into a host, and an SSH key
does not grant registry permission. Separate revocation and expiry make failures
diagnosable without increasing privileges.

For remote HTTP MCP, follow the current [MCP authorization specification][mcp-auth]
and [security guidance][mcp-security]: authenticated TLS, audience-bound tokens,
validated issuer/resource, least scopes, short expiry, and supported OAuth discovery
and consent. Never accept an unrelated upstream bearer token or pass the incoming
service token through to Kubernetes/GHCR. Keep authorization checks on every call;
session IDs alone are not authorization. Verify transport, Origin handling, and
deployment requirements against the selected supported client/server versions.

For an authenticated custom ChatGPT connection, use OAuth 2.1 authorization-code
flow with PKCE S256, protected-resource metadata, authorization-server discovery,
and supported client registration. Prefer an established identity provider.
ChatGPT's consent or tool-confirmation UI does not replace server authorization.
OpenAI-managed mTLS identifies the ChatGPT client, not the end user, and does not
replace OAuth. Tunnel-control-plane credentials, user OAuth, and downstream
Kubernetes/GHCR credentials remain separate boundaries. [Plugin authentication][openai-auth]

Only the owner performs or explicitly approves new persistent-access enrollment.
Use secure setup surfaces or local hidden input as appropriate; never paste private
keys, PATs, passwords, or kubeconfigs into chat. Do not invent a generic Dot SSH vault
or assume an HTTPS network-secret facility supports SSH private keys.

### Registry access

First establish chart visibility and test existing authorized access. Public GHCR
artifacts can be pulled anonymously. For private downloads outside GitHub Actions,
GitHub currently documents a classic PAT with `read:packages`; fine-grained PATs
do not support Packages. No `repo`, package-write, or package-delete scope is needed
for this verifier. Classic PATs are not per-package capabilities: their effective
read access also follows the account's package permissions. Consider a dedicated
identity with only the required package access if that narrower boundary justifies
the administration. [GHCR authentication][ghcr] [PAT limitations][github-pat]

Inside an authorized Actions workflow, prefer a scoped ephemeral `GITHUB_TOKEN`
when the repository has access to the package. Do not export it for persistent host
use. Keep registry credentials in the adapter's secret store or protected client
configuration. Do not print Helm/Docker configuration, copy a user's whole home,
or automatically distribute a credential to every node.

An exact `helm pull`/metadata verification establishes artifact access; successful
`helm registry login` alone does not. Compare the retrieved immutable digest with
the approved reference. Registry verification requires no Kubernetes credential.
Cluster image pulls are another consumer and may use a different credential path.
[Helm OCI documentation][helm-oci]

Keep `oci_manifest_digest` and `chart_archive_sha256` separate. The first identifies
the registry manifest; the second hashes the exact downloaded compressed `.tgz`
bytes. They are not interchangeable. Sugarkube's linked offline chart-lock contract
uses an archive hash and an exact HTTPS package URL, and its validator is inert.
An OCI pull result does not automatically satisfy that contract or authorize chart
admission/deployment. Name the verification profile and version in each receipt;
any OCI-to-lock mapping needs its own reviewed contract and tests.

### Cluster and host access

Use a purpose-built Kubernetes identity and explicit resource/verb permissions.
Avoid wildcard RBAC and the default K3s admin kubeconfig, which grants unrestricted
cluster access. Do not grant Secret reads merely to make Helm release inspection
convenient; Helm's storage backend may contain sensitive values. Prefer sanitized
workload evidence or a separately reviewed release-metadata adapter. [K3s][k3s-access]

RBAC authorizes whole resources, not safe fields within them. Even an allowed Pod
can contain literal environment values, and ConfigMaps can hold private data.
Direct API option D therefore exposes a broader data surface to its executor than
the filtered service. Approve that scope explicitly or use a server-side field
filter; client formatting after receiving an object does not prevent its exposure.

Initial identities exclude write verbs, pod exec/attach, port-forwarding, node proxy,
impersonation, role binding/escalation, token creation, and Secret reads. A future
namespace mutation role must account for workload-created access to secrets and
service-account permissions. Namespace scoping alone does not prevent privileged
pods, host mounts, or lateral network access. Use appropriate admission controls and
network separation before calling a broader role staging-only. [RBAC][k8s-rbac]

For host-only diagnostics, use fixed root-owned wrappers and a dedicated non-admin
account. Any necessary sudo entry must name an immutable fixed helper, not a shell,
interpreter, package manager, or arbitrary command. Keep host trust independently
verified and allow immediate owner revocation. Do not disable host-key checking.

## Threat model and failure behavior

| Threat / failure | Required mitigation and evidence |
| --- | --- |
| Prompt injection in chart metadata, logs, or events | Inert bounded output, server-enforced schemas and allowlists; injection tests cannot grant new tools or change policy |
| Confused deputy / arbitrary network destination | Server maps stable application IDs to fixed endpoints; validate destination and redirects; no model-supplied URLs or proxy escape |
| Stolen service credential | Audience/scope/expiry checks, revocation, rate limits, and independent least-privilege downstream identity |
| Staging compromise reaching production | No production credentials, mounts, contexts, service identities or network route in the adapter; negative isolation tests from the actual service runtime |
| Private data or credential disclosure | Allowlisted fields, reviewed log profiles, bounded errors; no raw Secrets/configs/dumps; fail closed on unsafe output |
| Resource exhaustion or malicious chart archive | Size, decompression, path, recursion, CPU/time and concurrency limits; non-executing parser sandbox; no writes outside scratch |
| Replay, retry, or lost response | Read-only calls have correlation IDs; future writes require durable idempotency and inspect-before-retry; unknown outcome stays unknown |
| Wrong cluster / stale context | Bind service configuration to expected staging cluster identity and TLS trust; recheck before each operation; no default kubeconfig fallback |
| Policy change, owner stop, or expired permission | Evaluate current policy on each call and before queued execution; deny stale approvals and suppress automatic retries |
| Control-plane outage | Bounded failures and health evidence; owner-run recovery remains available; no production or broad-admin fallback |
| Malicious CI/PR code on a LAN runner | Never run untrusted PR code with staging credentials; isolate validation from trusted operation runner and pin dispatch workflow inputs |

Audit records should include caller identity, operation, approved resource alias,
request ID, observation time, policy version, artifact digest when relevant, outcome,
and redaction status. Exclude tokens, complete command environments, raw logs, and
private payloads. Document retention, owner access, and outage behavior. Tool output
sent to a cloud Dot is an intentional external data flow, not LAN-only processing;
the owner must approve the actual data classes and destination before enabling it.

## Owner gates and future staging mutations

The initial contract does not expose a mutation tool. Creating credentials, changing
security/network settings, connecting the service, and starting a persistent worker
are separate setup actions. Existing work windows, stop instructions, and required
owner handoffs continue to apply. A transport migration must not weaken them.

If later authorized, keep planning and execution separate. A mutation proposal must
bind the exact staging target, action, immutable artifact digest, configuration
hash, expected current revision, data-loss scope, rollback/recovery limits, expiry,
and idempotency key. Trusted owner approval must be recorded outside model-supplied
arguments. A Boolean such as `approved: true` is never sufficient evidence.

Recheck current policy, target identity, and preconditions immediately before
execution. Changed target/artifact/values or expanded risk needs a new decision.
Consumed approvals and uncertain outcomes survive restart. A rollback is itself a
mutation and can lose data; do not promise Helm rollback restores databases or
deleted volumes. If current policy reserves an action for the owner, return a
reviewable plan and keep the execution capability disabled.

## Phased plan and acceptance criteria

| Phase | Deliverable | Exit evidence / decision |
| --- | --- | --- |
| 0. Review this design | Choose intended interface, executor/hosting candidate, data classes, and operational owner | Agreement on scope; no infrastructure change implied |
| 1. Connectivity feasibility, separately authorized | Synthetic authenticated read-only MCP tool with no registry/cluster credential, or a bounded restricted-SSH test if choosing B/C | Actual intended Dot discovers and calls it; unauthorized caller denied; revocation tested; no workaround for an existing denial |
| 2. Registry-only verifier | One allowlisted chart source with exact version/digest verification | Correct artifact succeeds; absent/wrong digest, bad credentials, hostile metadata/archive and arbitrary URL inputs fail safely; no cluster access |
| 3. Staging observation | Scoped identity, fixed resource map, sanitized status/events and optional log profile | Positive allowed reads and negative Secret/write/production tests from the service runtime; output/privacy review; audit and outage drill |
| 4. Reliability and operational readiness | Patch/rotation/runbook, health checks, quotas, revocation and owner-run recovery | Expiry, restart, partial failure, stale policy, rate-limit and credential-leak tests; documented maintenance owner |
| 5. Optional bounded mutation design | Separate reviewed proposal for exact staging operations | Explicit owner policy change where needed; durable approval/idempotency, data-loss and recovery tests; no production expansion |

For each phase record the tested client/product version, server revision, schema
version, permission manifest, dates, and evidence. A successful local CLI test is
not a successful Dot test. A running MCP endpoint is not proof that tools are
available to the selected Dot or permitted in unattended/background use.

Before implementation, resolve only the decisions that affect the chosen phase:

1. Which supported Dot connection/distribution route is actually available to the
   owner, including whether private connectivity is supported?
2. Should the initial service live on a dedicated management host outside staging,
   or is losing it during a staging outage an acceptable tradeoff?
3. Which chart/app IDs and sanitized fields may leave the LAN for this Dot?
4. Can current registry access satisfy verification without a new credential?
5. Who maintains the service and performs enrollment, recovery, and revocation?

## Sources

Product capabilities are time-sensitive. Recheck official integration documentation
and account-specific availability during phase 1. These references establish
protocols and upstream behavior, not a completed deployment or a grant of access.

[sugarkube-remote]: https://github.com/futuroptimist/sugarkube/blob/main/docs/design/tailscale-remote-ops.md
[chart-lock]: https://github.com/futuroptimist/sugarkube/blob/main/docs/design/chart-lock-contract.md
[ssh]: https://man.openbsd.org/sshd.8
[mcp-auth]: https://modelcontextprotocol.io/specification/2025-11-25/basic/authorization
[mcp-security]: https://modelcontextprotocol.io/specification/2025-11-25/basic/security_best_practices
[ghcr]: https://docs.github.com/en/packages/working-with-a-github-packages-registry/working-with-the-container-registry
[github-pat]: https://docs.github.com/en/authentication/keeping-your-account-and-data-secure/managing-your-personal-access-tokens
[helm-oci]: https://helm.sh/docs/v3/topics/registries/
[k3s-access]: https://docs.k3s.io/cluster-access
[k8s-rbac]: https://kubernetes.io/docs/concepts/security/rbac-good-practices/
[openai-custom]: https://developers.openai.com/api/docs/guides/custom-mcp-server
[openai-connect]: https://developers.openai.com/plugins/deploy/connect-chatgpt
[openai-tunnel]: https://developers.openai.com/api/docs/guides/secure-mcp-tunnels
[openai-local]: https://learn.chatgpt.com/docs/extend/mcp
[openai-auth]: https://developers.openai.com/plugins/build/auth
