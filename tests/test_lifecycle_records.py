"""Invented fixtures and structural acceptance tests; no real user records."""

import json
from dataclasses import FrozenInstanceError, replace
from pathlib import Path

import pytest

from axel import lifecycle_records as m

FIXTURE = json.loads(
    (Path(__file__).parent / "fixtures/lifecycle/invented.json").read_text()
)
SCOPE = m.Scope(FIXTURE["workspace"], FIXTURE["profile"])
DIGEST = "a" * 64
PR = m.PullRequest("invented-repository", 17, "b" * 40, "ready")
PR2 = m.PullRequest("invented-companion", 23, "c" * 40, "ready")


def envelope(record_id="task-1", task_id="task", revision=1, **changes):
    values = dict(
        record_id=record_id,
        scope=SCOPE,
        task_id=task_id,
        task_revision=revision,
        input_digest=DIGEST,
        contract_digest=DIGEST,
        environment="none",
        subject_id=task_id,
        source="fixture",
        source_event_id=record_id,
        source_revision=1,
        status="observed",
        observed_at=100,
        source_at=100,
        correlation_id="correlation",
        audience_policy="local-only",
    )
    values.update(changes)
    return m.Envelope(**values)


def task(task_id="task", revision=1, **changes):
    values = dict(
        envelope=envelope(f"{task_id}-{revision}", task_id, revision),
        title=FIXTURE["title"],
        requester="invented-requester",
        owner=FIXTURE["owner"],
        intent=FIXTURE["untrusted_text"],
        action_profile="draft-only",
        project_digest=DIGEST,
        capabilities=("offline",),
        harness="synthetic",
        execution_state="pending",
        board_column="review",
        stage="design",
        required_prs=(),
        required_checks=(),
        required_reviews=(FIXTURE["owner"],),
    )
    values.update(changes)
    return m.TaskRevision(**values)


def review(record_id="review", target=None, **changes):
    target = target or task()
    values = dict(
        envelope=replace(
            target.envelope, record_id=record_id, source_event_id=record_id
        ),
        reviewer=FIXTURE["owner"],
        principal_kind="human",
        stage=target.stage,
        decision="accepted",
        findings=(),
        required_prs=target.required_prs,
    )
    values.update(changes)
    return m.ReviewDecision(**values)


def ci(record_id="ci", target=None, pr=PR, **changes):
    target = target or task()
    values = dict(
        envelope=replace(
            target.envelope, record_id=record_id, source_event_id=record_id
        ),
        kind="ci",
        result="success",
        artifact_id="artifact-" + record_id,
        artifact_digest=DIGEST,
        pr=pr,
        execution=m.SourceExecution(pr, "tests", "run-" + record_id, 1, "unit"),
    )
    values.update(changes)
    return m.Evidence(**values)


def dependency(downstream, upstream, record_id="dependency", stage="design", **changes):
    return m.Dependency(
        replace(downstream.envelope, record_id=record_id),
        upstream.envelope.task_id,
        stage,
        changes.get("acceptance_digest", DIGEST),
    )


def snapshot(*records, revision=1):
    return m.Snapshot(SCOPE, revision, tuple(records))


def test_invented_identity_immutable_and_round_trip():
    first, second = task("first"), task("second")
    assert (
        first.title == second.title
        and first.envelope.observed_at == second.envelope.observed_at
    )
    assert first.envelope.record_id != second.envelope.record_id
    assert first.envelope.task_id != second.envelope.task_id
    with pytest.raises(FrozenInstanceError):
        first.title = "changed"
    assert m.decode_record(m.encode_record(first)) == first
    assert (
        m.canonical({"z": None, "a": [True, -(2**63), 2**63 - 1, "\u2603"]})
        == (
            '{"a":[true,-9223372036854775808,9223372036854775807,' '"\u2603"],"z":null}'
        ).encode()
    )


@pytest.mark.parametrize(
    "value",
    [
        1.0,
        float("nan"),
        float("inf"),
        2**63,
        -(2**63) - 1,
        b"bytes",
        object(),
        {1: "bad"},
        "\ud800",
        "x" * 65537,
    ],
    ids=lambda value: type(value).__name__,
)
def test_canonical_rejects_unsupported_or_oversized(value):
    with pytest.raises(m.RecordError):
        m.canonical(value)


@pytest.mark.parametrize(
    "changes",
    [
        dict(task_revision=True),
        dict(schema_version=2),
        dict(input_digest="bad"),
        dict(environment="online"),
        dict(source_revision=0),
        dict(source_at=101),
        dict(record_id="bad id"),
    ],
)
def test_envelope_rejects_bad_schema_and_exact_types(changes):
    with pytest.raises(m.RecordError):
        envelope(**changes)


def test_scope_and_mutable_fields_rejected():
    with pytest.raises(m.RecordError):
        m.Scope("workspace", "profile", "online")
    with pytest.raises(m.RecordError):
        task(capabilities=["offline"])
    with pytest.raises(m.RecordError):
        snapshot(
            task(),
            task(
                "other",
                envelope=envelope("other", "other", scope=m.Scope("other", "profile")),
            ),
        )


@pytest.mark.parametrize(
    "payload",
    [
        b'{"type":0,"type":1}',
        b"[" * 14 + b"]" * 14,
        b"{}",
        b"null",
        b"\xff",
        b" " * 65537,
    ],
    ids=lambda value: str(len(value)),
)
def test_decoder_rejects_malformed(payload):
    with pytest.raises(m.RecordError):
        m.decode_record(payload)


def test_canonical_vectors_and_record_limit():
    record = task(title="x" * 64000)
    assert len(m.encode_record(record)) < m.MAX_RECORD_BYTES
    with pytest.raises(m.RecordError):
        task(title="x" * 65536)
    raw = m.encode_record(task())
    with pytest.raises(m.RecordError):
        m.decode_record(raw + b" ")
    with pytest.raises(m.RecordError):
        m.decode_record(raw.replace(b'"task_revision":1', b'"task_revision":true'))


@pytest.mark.parametrize(
    "field,value",
    [
        ("input_digest", "b" * 64),
        ("contract_digest", "b" * 64),
        ("subject_id", "wrong"),
        ("environment", "staging"),
        ("task_id", "wrong"),
    ],
)
def test_observation_binding_is_exact(field, value):
    r = review()
    with pytest.raises(m.RecordError):
        snapshot(task(), replace(r, envelope=replace(r.envelope, **{field: value})))


def test_revision_conflicts_and_required_sets_cannot_shrink():
    with pytest.raises(m.RecordError):
        snapshot(task(), task())
    with pytest.raises(m.RecordError):
        snapshot(task(revision=2))
    with pytest.raises(m.RecordError):
        snapshot(task(required_prs=(PR, PR2)), task(revision=2, required_prs=(PR,)))
    with pytest.raises(m.RecordError):
        snapshot(task(), task(revision=2, required_reviews=()))


def test_attempt_observations_bind_one_task_and_cannot_reopen_terminal():
    attempt = m.Attempt(envelope("a"), "attempt", 1, "succeeded")
    snapshot(task(), attempt)
    with pytest.raises(m.RecordError):
        snapshot(
            task(),
            attempt,
            replace(attempt, envelope=envelope("b"), sequence=2, state="running"),
        )
    with pytest.raises(m.RecordError):
        snapshot(task(), m.Attempt(envelope("b"), "attempt", 2, "running"))
    with pytest.raises(m.RecordError):
        ci(attempt_id="fabricated")


def test_supersession_requires_matching_channel_and_time():
    failed = ci(result="failure")
    fixed = ci("fixed", supersedes=("ci",))
    snapshot(task(), failed, fixed)
    with pytest.raises(m.RecordError):
        snapshot(task(), failed, ci("other", pr=PR2, supersedes=("ci",)))
    with pytest.raises(m.RecordError):
        snapshot(
            task(), failed, replace(fixed, envelope=envelope("fixed", source_at=99))
        )


def test_dependencies_missing_cycles_diamonds_and_exact_stage():
    a, b, c, d = [task(x) for x in "abcd"]
    with pytest.raises(m.RecordError):
        snapshot(a, dependency(a, b))
    with pytest.raises(m.RecordError):
        snapshot(a, b, dependency(a, b, "ab"), dependency(b, a, "ba"))
    assert snapshot(
        a,
        b,
        c,
        d,
        dependency(a, b, "ab"),
        dependency(a, c, "ac"),
        dependency(b, d, "bd"),
        dependency(c, d, "cd"),
    )


@pytest.mark.parametrize("length,valid", [(32, True), (33, False)])
def test_graph_depth_boundary(length, valid):
    tasks = [task(f"node-{i}") for i in range(length)]
    records = tasks + [
        dependency(tasks[i], tasks[i + 1], f"edge-{i}") for i in range(length - 1)
    ]
    if valid:
        snapshot(*records)
    else:
        with pytest.raises(m.RecordError, match="depth_limit"):
            snapshot(*records)


@pytest.mark.parametrize("count,valid", [(256, True), (257, False)])
def test_graph_task_boundary(count, valid):
    records = [task(f"node-{i}") for i in range(count)]
    if valid:
        snapshot(*records)
    else:
        with pytest.raises(m.RecordError, match="task_limit"):
            snapshot(*records)


@pytest.mark.parametrize("count,valid", [(1024, True), (1025, False)])
def test_graph_edge_boundary(count, valid):
    tasks = [task(f"node-{i}") for i in range(66)]
    edges = [
        dependency(tasks[i // 33], tasks[33 + i % 33], f"edge-{i}")
        for i in range(count)
    ]
    if valid:
        snapshot(*tasks, *edges)
    else:
        with pytest.raises(m.RecordError, match="edge_limit"):
            snapshot(*tasks, *edges)


def test_retention_caps_fail_without_truncation(monkeypatch):
    records = (task(), review())
    monkeypatch.setattr(m, "MAX_RECORDS", 1)
    with pytest.raises(m.RecordError, match="record_limit"):
        snapshot(*records)
    monkeypatch.setattr(m, "MAX_RECORDS", 10000)
    monkeypatch.setattr(m, "MAX_PAYLOAD_BYTES", len(m.encode_record(records[0])))
    with pytest.raises(m.RecordError, match="payload_limit"):
        snapshot(*records)
    assert records == (task(), review())


def test_actual_retained_record_limit():
    records = [task()] + [
        m.Transition(envelope(f"observation-{i}"), "observe") for i in range(9999)
    ]
    assert len(snapshot(*records).records) == 10000
    with pytest.raises(m.RecordError, match="record_limit"):
        snapshot(*records, m.Transition(envelope("overflow"), "observe"))


def test_actual_payload_byte_limit():
    records = [task()]
    total = len(m.encode_record(records[0]))
    while True:
        record = review(f"large-{len(records)}", findings=("x" * 60000,))
        size = len(m.encode_record(record))
        if total + size > m.MAX_PAYLOAD_BYTES - 1000:
            break
        records.append(record)
        total += size
    empty = review("padding", findings=("",))
    padding = m.MAX_PAYLOAD_BYTES - total - len(m.encode_record(empty))
    records.append(replace(empty, findings=("x" * padding,)))
    assert sum(len(m.encode_record(r)) for r in records) == m.MAX_PAYLOAD_BYTES
    snapshot(*records)
    with pytest.raises(m.RecordError, match="payload_limit"):
        snapshot(*records, m.Transition(envelope("overflow"), "observe"))


def test_source_revision_and_ci_run_attempt_cannot_regress():
    first = ci()
    second = ci(
        "later", supersedes=("ci",), envelope=replace(first.envelope, record_id="later")
    )
    with pytest.raises(m.RecordError, match="source_revision"):
        snapshot(task(), first, second)
    second = replace(
        second,
        envelope=replace(second.envelope, source_revision=2),
        execution=first.execution,
    )
    snapshot(task(), first, second)
    newer = replace(first, execution=replace(first.execution, run_attempt=2))
    with pytest.raises(m.RecordError, match="supersedes_attempt"):
        snapshot(task(), newer, second)


def test_codec_handles_escaped_text_and_references_without_authority():
    target = task(
        title='Line one\n"quoted" \\ snowman \u2603',
        approval_refs=("approval-reference",),
        delivery_refs=("delivery-reference",),
    )
    assert m.decode_record(m.encode_record(target)) == target
    assert envelope(causation_id="invented-cause").causation_id == "invented-cause"
    assert m.decode_record(m.encode_record(ci())) == ci()
    assert m.evidence_channel(review()) == (
        "review",
        FIXTURE["owner"],
        "human",
        "design",
    )
    invalid = json.loads(m.encode_record(task()))
    invalid["value"]["extra"] = "rejected"
    with pytest.raises(m.RecordError):
        m.decode_record(m.canonical(invalid))


@pytest.mark.parametrize("action", ["resume", "stop"])
@pytest.mark.parametrize("source,observed", [(100, 100), (100, 500)])
def test_stop_latch_changes_cannot_regress_referenced_times(action, source, observed):
    stop = m.Transition(envelope("stop", source_at=500, observed_at=500), "stop")
    change = m.Transition(
        envelope("change", source_at=source, observed_at=observed),
        action,
        "stop" if action == "resume" else None,
    )
    with pytest.raises(m.RecordError, match="stop_time"):
        snapshot(task(), stop, change)
    valid = replace(
        change, envelope=replace(change.envelope, source_at=500, observed_at=500)
    )
    snapshot(task(), stop, valid)


@pytest.mark.parametrize("source,observed", [(50, 50), (50, 100)])
def test_attempt_success_cannot_predate_previous_sequence(source, observed):
    running = m.Attempt(envelope("running"), "attempt", 1, "running")
    succeeded = m.Attempt(
        envelope("succeeded", source_at=source, observed_at=observed),
        "attempt",
        2,
        "succeeded",
    )
    with pytest.raises(m.RecordError, match="attempt_time"):
        snapshot(task(), running, succeeded)
    valid = replace(
        succeeded,
        envelope=replace(succeeded.envelope, source_at=100, observed_at=100),
    )
    snapshot(task(), running, valid)


@pytest.mark.parametrize("source,observed", [(100, 100), (500, 600)])
def test_transition_chronology_remains_bound_after_resume(source, observed):
    stop = m.Transition(envelope("stop", source_at=500, observed_at=500), "stop")
    resume = m.Transition(
        envelope("resume", source_at=600, observed_at=600), "resume", "stop"
    )
    next_stop = m.Transition(
        envelope("next-stop", source_at=source, observed_at=observed), "stop"
    )
    with pytest.raises(m.RecordError, match="stop_time"):
        snapshot(task(), stop, resume, next_stop)
    valid = replace(
        next_stop,
        envelope=replace(next_stop.envelope, source_at=600, observed_at=600),
    )
    snapshot(task(), stop, resume, valid)
