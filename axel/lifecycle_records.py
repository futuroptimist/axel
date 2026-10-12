"""Immutable, inert records for a synthetic local lifecycle experiment.

No identity in these records is authenticated. Approval and delivery IDs are
references to the existing contracts, never a second authority registry.
"""

from __future__ import annotations

import hashlib
import json
import re
from dataclasses import dataclass, fields
from functools import lru_cache
from types import UnionType
from typing import get_args, get_origin, get_type_hints

MAX_RECORD_BYTES = 64 * 1024
MAX_COMMAND_RECORDS = 64
MAX_RECORDS = 10_000
MAX_PAYLOAD_BYTES = 16 * 1024 * 1024
MAX_TASKS = 256
MAX_EDGES = 1024
MAX_DEPTH = 32
STAGES = ("design", "source", "runtime")
RESULTS = ("success", "failure", "unknown", "skipped", "cancelled")


class RecordError(ValueError):
    """Invalid synthetic data; messages deliberately contain no record content."""


def require(condition: bool, code: str) -> None:
    if not condition:
        raise RecordError(code)


def identifier(value: str) -> None:
    require(bool(re.fullmatch(r"[A-Za-z0-9][A-Za-z0-9_.:/-]{0,199}", value)), "id")


def digest(value: str) -> None:
    require(bool(re.fullmatch(r"[0-9a-f]{64}", value)), "digest")


@lru_cache(maxsize=32)
def _hints(cls):
    return get_type_hints(cls)


def _typed(value, hint) -> bool:
    if get_origin(hint) is UnionType:
        return any(_typed(value, option) for option in get_args(hint))
    if get_origin(hint) is tuple:
        return type(value) is tuple and all(
            _typed(item, get_args(hint)[0]) for item in value
        )
    return type(value) is hint


class _Value:
    def __post_init__(self):
        require(
            all(
                _typed(getattr(self, key), hint)
                for key, hint in _hints(type(self)).items()
            ),
            "type",
        )
        canonical(self)  # Bound strings/collections before domain validation.
        _validate(self)


@dataclass(frozen=True)
class Scope(_Value):
    workspace_id: str
    profile_id: str
    mode: str = "local"


@dataclass(frozen=True)
class Envelope(_Value):
    record_id: str
    scope: Scope
    task_id: str
    task_revision: int
    input_digest: str
    contract_digest: str
    environment: str
    subject_id: str
    source: str
    source_event_id: str
    source_revision: int
    status: str
    observed_at: int  # Exact UTC epoch seconds, never an implicit local clock.
    source_at: int
    correlation_id: str
    audience_policy: str
    causation_id: str | None = None
    schema_version: int = 1


@dataclass(frozen=True)
class PullRequest(_Value):
    repository: str  # Stable, synthetic repository identity; not a display name.
    number: int
    head: str
    state: str = "unknown"


@dataclass(frozen=True)
class Check(_Value):
    repository: str
    number: int
    workflow: str
    job: str


@dataclass(frozen=True)
class SourceExecution(_Value):
    pr: PullRequest
    workflow: str
    run_id: str
    run_attempt: int
    job: str


@dataclass(frozen=True)
class TaskRevision(_Value):
    envelope: Envelope
    title: str
    requester: str
    owner: str
    intent: str
    action_profile: str
    project_digest: str
    capabilities: tuple[str, ...]
    harness: str
    execution_state: str
    board_column: str
    stage: str
    required_prs: tuple[PullRequest, ...]
    required_checks: tuple[Check, ...]
    required_reviews: tuple[str, ...]
    deadline: int | None = None
    approval_refs: tuple[str, ...] = ()
    delivery_refs: tuple[str, ...] = ()
    source_refs: tuple[str, ...] = ()


@dataclass(frozen=True)
class Attempt(_Value):
    envelope: Envelope
    attempt_id: str
    sequence: int
    state: str
    lease_until: int | None = None


@dataclass(frozen=True)
class Evidence(_Value):
    envelope: Envelope
    kind: str  # ci, merge or runtime observation
    result: str
    artifact_id: str
    artifact_digest: str
    execution: SourceExecution | None = None
    pr: PullRequest | None = None
    attempt_id: str | None = None
    actor: str | None = None
    supersedes: tuple[str, ...] = ()


@dataclass(frozen=True)
class Dependency(_Value):
    envelope: Envelope
    upstream_task_id: str
    required_stage: str
    acceptance_digest: str


@dataclass(frozen=True)
class ReviewDecision(_Value):
    envelope: Envelope
    reviewer: str
    principal_kind: str
    stage: str
    decision: str
    findings: tuple[str, ...]
    required_prs: tuple[PullRequest, ...]
    supersedes: tuple[str, ...] = ()


@dataclass(frozen=True)
class Transition(_Value):
    """An inert audit observation, including explicitly latched stop/resume."""

    envelope: Envelope
    action: str
    resume_of: str | None = None


@dataclass(frozen=True)
class OperationReceipt(_Value):
    scope: Scope
    principal: str
    operation_key: str
    payload_digest: str
    ledger_revision: int
    record_ids: tuple[str, ...]
    operation_kind: str = "append"


RECORD_TYPES = (TaskRevision, Attempt, Evidence, Dependency, ReviewDecision, Transition)
VALUE_TYPES = RECORD_TYPES + (
    Scope,
    Envelope,
    PullRequest,
    Check,
    SourceExecution,
    OperationReceipt,
)


def _validate(value):
    if isinstance(value, Scope):
        identifier(value.workspace_id)
        identifier(value.profile_id)
        require(value.mode == "local", "unsupported_scope")
    elif isinstance(value, Envelope):
        require(value.schema_version == 1, "schema")
        for name in (
            "record_id",
            "task_id",
            "subject_id",
            "source",
            "source_event_id",
            "correlation_id",
            "audience_policy",
            "status",
        ):
            identifier(getattr(value, name))
        if value.causation_id is not None:
            identifier(value.causation_id)
        require(value.task_revision > 0 and value.source_revision > 0, "revision")
        require(0 <= value.source_at <= value.observed_at, "time")
        require(value.environment in ("none", "staging", "prod"), "environment")
        digest(value.input_digest)
        digest(value.contract_digest)
    elif isinstance(value, (PullRequest, Check)):
        identifier(value.repository)
        require(value.number > 0, "pr_number")
        if isinstance(value, PullRequest):
            require(
                value.state in ("unknown", "draft", "ready", "closed", "merged"),
                "pr_state",
            )
            require(bool(re.fullmatch(r"[0-9a-f]{40}", value.head)), "head")
        else:
            identifier(value.workflow)
            identifier(value.job)
    elif isinstance(value, SourceExecution):
        for part in (value.workflow, value.run_id, value.job):
            identifier(part)
        require(value.run_attempt > 0, "run_attempt")
    elif isinstance(value, TaskRevision):
        digest(value.project_digest)
        for part in (value.requester, value.owner, value.action_profile, value.harness):
            identifier(part)
        require(value.stage in STAGES, "stage")
        require(
            value.execution_state
            in ("pending", "running", "succeeded", "cancelled", "unknown"),
            "state",
        )
        require(
            value.board_column in ("backlog", "in_progress", "review", "done"), "column"
        )
        require(len(value.required_prs) <= 64, "pr_limit")
        require(
            len({(p.repository, p.number) for p in value.required_prs})
            == len(value.required_prs),
            "duplicate_pr",
        )
        for collection in (
            value.required_checks,
            value.required_reviews,
            value.capabilities,
        ):
            require(len(set(collection)) == len(collection), "duplicate_requirement")
        prs = {(p.repository, p.number) for p in value.required_prs}
        require(
            all((c.repository, c.number) in prs for c in value.required_checks),
            "check_pr",
        )
        for part in (
            value.required_reviews
            + value.capabilities
            + value.approval_refs
            + value.delivery_refs
            + value.source_refs
        ):
            identifier(part)
        require(value.deadline is None or value.deadline >= 0, "deadline")
    elif isinstance(value, Attempt):
        identifier(value.attempt_id)
        require(value.sequence > 0, "sequence")
        require(
            value.state in ("running", "succeeded", "failed", "cancelled", "unknown"),
            "state",
        )
        require(value.lease_until is None or value.lease_until >= 0, "lease")
    elif isinstance(value, Evidence):
        require(value.kind in ("ci", "merge", "runtime"), "evidence_kind")
        require(value.result in RESULTS, "result")
        identifier(value.artifact_id)
        digest(value.artifact_digest)
        if value.attempt_id is not None:
            identifier(value.attempt_id)
        if value.actor is not None:
            identifier(value.actor)
        if value.kind == "ci":
            require(
                value.execution is not None and value.pr == value.execution.pr,
                "ci_binding",
            )
            require(value.attempt_id is None, "external_attempt")
        elif value.kind == "merge":
            require(
                value.pr is not None
                and value.actor is not None
                and value.execution is None,
                "merge_binding",
            )
        else:
            require(
                value.pr is None
                and value.execution is None
                and value.attempt_id is not None,
                "runtime_binding",
            )
    elif isinstance(value, Dependency):
        identifier(value.upstream_task_id)
        digest(value.acceptance_digest)
        require(value.required_stage in STAGES, "stage")
    elif isinstance(value, ReviewDecision):
        identifier(value.reviewer)
        require(value.principal_kind in ("human", "model"), "principal_kind")
        require(value.stage in STAGES, "stage")
        require(
            value.decision in ("accepted", "rejected", "unknown", "dismissed"),
            "decision",
        )
    elif isinstance(value, Transition):
        require(value.action in ("observe", "stop", "resume"), "transition")
        require((value.action == "resume") == (value.resume_of is not None), "resume")
    elif isinstance(value, OperationReceipt):
        identifier(value.principal)
        identifier(value.operation_key)
        digest(value.payload_digest)
        require(
            value.ledger_revision > 0 and value.operation_kind == "append", "receipt"
        )
        require(0 < len(value.record_ids) <= MAX_COMMAND_RECORDS, "receipt_records")
    if hasattr(value, "supersedes"):
        require(len(set(value.supersedes)) == len(value.supersedes), "supersedes")
        for item in value.supersedes:
            identifier(item)


def canonical(value, *, limit=MAX_RECORD_BYTES) -> bytes:
    """Exact bounded JSON: signed 64-bit integers, Unicode, bool and null.

    Strings are not normalized. Floats, duplicate keys, arbitrary objects and
    excessive nesting are rejected. Tuples become arrays; keys sort by codepoint.
    """
    budget = [0, 0]

    def convert(item, depth=0):
        budget[0] += 1
        require(depth <= 12 and budget[0] <= 8192, "encoding_limit")
        if type(item) in VALUE_TYPES:
            return convert(
                {f.name: getattr(item, f.name) for f in fields(item)}, depth + 1
            )
        if type(item) is str:
            require(len(item) <= limit, "encoding_limit")
            try:
                budget[1] += len(item.encode("utf-8"))
            except UnicodeError as exc:
                raise RecordError("unicode") from exc
            require(budget[1] <= limit, "encoding_limit")
            return item
        if type(item) is int:
            require(-(2**63) <= item < 2**63, "integer")
            return item
        if item is None or type(item) is bool:
            return item
        if type(item) in (tuple, list):
            require(len(item) <= 2048, "encoding_limit")
            return [convert(x, depth + 1) for x in item]
        if type(item) is dict:
            require(len(item) <= 128 and all(type(k) is str for k in item), "object")
            return {
                convert(k, depth + 1): convert(v, depth + 1) for k, v in item.items()
            }
        raise RecordError("type")

    result = json.dumps(
        convert(value),
        sort_keys=True,
        ensure_ascii=False,
        separators=(",", ":"),
        allow_nan=False,
    ).encode("utf-8")
    require(len(result) <= limit, "encoding_limit")
    return result


def encode_record(record) -> bytes:
    require(type(record) in RECORD_TYPES, "record_type")
    return canonical({"type": type(record).__name__, "value": record})


def decode_record(payload: bytes):
    require(
        type(payload) is bytes and len(payload) <= MAX_RECORD_BYTES, "encoding_limit"
    )
    # Bound nesting before invoking the JSON parser, including malicious arrays.
    depth, quoted, escaped = 0, False, False
    for char in payload:
        if quoted:
            if escaped:
                escaped = False
            elif char == 92:
                escaped = True
            elif char == 34:
                quoted = False
        elif char == 34:
            quoted = True
        elif char in (91, 123):
            depth += 1
            require(depth <= 12, "encoding_limit")
        elif char in (93, 125):
            depth -= 1

    def pairs(items):
        result = dict(items)
        require(len(result) == len(items), "duplicate_key")
        return result

    def construct(item, hint):
        if get_origin(hint) is UnionType:
            if item is None and type(None) in get_args(hint):
                return None
            return construct(item, get_args(hint)[0])
        if get_origin(hint) is tuple:
            require(type(item) is list, "type")
            return tuple(construct(x, get_args(hint)[0]) for x in item)
        if hint in VALUE_TYPES:
            require(type(item) is dict and set(item) == set(_hints(hint)), "fields")
            return hint(
                **{key: construct(item[key], t) for key, t in _hints(hint).items()}
            )
        require(type(item) is hint, "type")
        return item

    try:
        data = json.loads(payload, object_pairs_hook=pairs)
        require(type(data) is dict and set(data) == {"type", "value"}, "fields")
        cls = next((c for c in RECORD_TYPES if c.__name__ == data["type"]), None)
        require(cls is not None, "record_type")
        result = construct(data["value"], cls)
        require(encode_record(result) == payload, "noncanonical")
        return result
    except (UnicodeError, TypeError, KeyError, ValueError, RecursionError) as exc:
        raise RecordError("invalid_encoding") from exc


def payload_digest(payload: bytes) -> str:
    return hashlib.sha256(payload).hexdigest()


def binding(envelope: Envelope) -> tuple:
    return (
        envelope.scope,
        envelope.task_id,
        envelope.task_revision,
        envelope.input_digest,
        envelope.contract_digest,
        envelope.environment,
        envelope.subject_id,
    )


def evidence_channel(record) -> tuple:
    """Only explicitly related observations may supersede each other."""
    if isinstance(record, ReviewDecision):
        return ("review", record.reviewer, record.principal_kind, record.stage)
    execution = record.execution
    return (
        record.kind,
        record.pr,
        (execution.workflow, execution.job) if execution else None,
        record.attempt_id,
    )


@dataclass(frozen=True)
class Snapshot:
    scope: Scope
    ledger_revision: int
    records: tuple[
        TaskRevision | Attempt | Evidence | Dependency | ReviewDecision | Transition,
        ...,
    ]

    def __post_init__(self):
        validate_snapshot(self)


def validate_snapshot(snapshot: Snapshot) -> dict[str, TaskRevision]:
    """Validate full history and the current graph, without reading any storage."""
    require(
        type(snapshot.scope) is Scope
        and type(snapshot.ledger_revision) is int
        and snapshot.ledger_revision >= 0
        and type(snapshot.records) is tuple,
        "snapshot",
    )
    require(len(snapshot.records) <= MAX_RECORDS, "record_limit")
    require(
        bool(snapshot.records) == bool(snapshot.ledger_revision), "snapshot_revision"
    )
    total = 0
    by_id, revisions, latest, attempts, stops = {}, {}, {}, {}, {}
    for record in snapshot.records:
        payload = encode_record(record)
        total += len(payload)
        require(total <= MAX_PAYLOAD_BYTES, "payload_limit")
        env = record.envelope
        require(env.scope == snapshot.scope, "scope")
        require(env.record_id not in by_id, "duplicate_record")
        key = (env.task_id, env.task_revision)
        if isinstance(record, TaskRevision):
            previous = latest.get(env.task_id)
            require(
                env.task_revision
                == (previous.envelope.task_revision + 1 if previous else 1),
                "task_revision",
            )
            if previous:
                require(
                    {(p.repository, p.number) for p in previous.required_prs}
                    <= {(p.repository, p.number) for p in record.required_prs},
                    "pr_set_shrink",
                )
                require(
                    set(previous.required_checks) <= set(record.required_checks)
                    and set(previous.required_reviews) <= set(record.required_reviews),
                    "requirements_shrink",
                )
            revisions[key] = record
            latest[env.task_id] = record
            require(len(latest) <= MAX_TASKS, "task_limit")
        else:
            require(key in revisions, "missing_revision")
            require(binding(env) == binding(revisions[key].envelope), "binding")
        if isinstance(record, Attempt):
            previous = attempts.get(record.attempt_id)
            require(
                record.sequence == (previous.sequence + 1 if previous else 1),
                "attempt_sequence",
            )
            if previous:
                require(binding(env) == binding(previous.envelope), "attempt_binding")
                require(previous.state in ("running", "unknown"), "terminal_attempt")
            attempts[record.attempt_id] = record
        if isinstance(record, Evidence) and record.attempt_id is not None:
            attempt = attempts.get(record.attempt_id)
            require(
                attempt is not None and binding(attempt.envelope) == binding(env),
                "attempt_binding",
            )
        if isinstance(record, (Evidence, ReviewDecision)):
            for old_id in record.supersedes:
                old = by_id.get(old_id)
                require(
                    type(old) is type(record)
                    and binding(old.envelope) == binding(env)
                    and old.envelope.source == env.source
                    and evidence_channel(old) == evidence_channel(record),
                    "supersedes_binding",
                )
                require(
                    env.source_at >= old.envelope.source_at
                    and env.observed_at >= old.envelope.observed_at,
                    "supersedes_time",
                )
                if env.source_event_id == old.envelope.source_event_id:
                    require(
                        env.source_revision > old.envelope.source_revision,
                        "source_revision",
                    )
                if isinstance(record, Evidence) and record.execution:
                    if record.execution.run_id == old.execution.run_id:
                        require(
                            record.execution.run_attempt >= old.execution.run_attempt,
                            "supersedes_attempt",
                        )
        if isinstance(record, Transition):
            if record.action in ("stop", "resume") and env.task_id in stops:
                stop = by_id[stops[env.task_id]].envelope
                require(
                    env.observed_at >= stop.observed_at
                    and env.source_at >= stop.source_at,
                    "stop_time",
                )
            if record.action == "stop":
                stops[env.task_id] = env.record_id
            elif record.action == "resume":
                require(stops.get(env.task_id) == record.resume_of, "resume_binding")
                del stops[env.task_id]
        by_id[env.record_id] = record
    graph = {task: [] for task in latest}
    for record in snapshot.records:
        if (
            isinstance(record, Dependency)
            and record.envelope.task_revision
            == latest[record.envelope.task_id].envelope.task_revision
        ):
            require(record.upstream_task_id in latest, "missing_dependency")
            graph[record.envelope.task_id].append(record.upstream_task_id)
    require(sum(map(len, graph.values())) <= MAX_EDGES, "edge_limit")
    visiting, depths = set(), {}

    def visit(task):
        require(task not in visiting, "dependency_cycle")
        if task in depths:
            return depths[task]
        require(len(visiting) < MAX_DEPTH, "depth_limit")
        visiting.add(task)
        depth = 1 + max((visit(upstream) for upstream in graph[task]), default=0)
        visiting.remove(task)
        require(depth <= MAX_DEPTH, "depth_limit")
        depths[task] = depth
        return depth

    for task in graph:
        visit(task)
    return latest
