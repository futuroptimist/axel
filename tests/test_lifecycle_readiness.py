"""Pure synthetic policy/evidence acceptance; no grants are authenticated here."""

from dataclasses import replace
from datetime import datetime, timezone
from zoneinfo import ZoneInfo

import pytest
from test_lifecycle_records import (
    DIGEST,
    FIXTURE,
    PR,
    PR2,
    SCOPE,
    ci,
    dependency,
    envelope,
    review,
    snapshot,
    task,
)

from axel import lifecycle_readiness as r
from axel import lifecycle_records as m

NOW = datetime.fromtimestamp(110, timezone.utc)
POLICY = r.Policy(SCOPE, "synthetic-policy-1", 0, 1000, 100, ("offline",), "clear")


def evaluate(*records, **kwargs):
    values = dict(expected_ledger_revision=1, now=NOW, policy=POLICY)
    values.update(kwargs)
    return r.evaluate(snapshot(*records), records[0].envelope.task_id, **values)


def source_task(**kwargs):
    values = dict(
        stage="source",
        required_prs=(PR, PR2),
        required_checks=(
            m.Check(PR.repository, PR.number, "tests", "unit"),
            m.Check(PR2.repository, PR2.number, "tests", "unit"),
        ),
    )
    values.update(kwargs)
    return task(**values)


def merge(target, pr, name="merge"):
    return ci(name, target, pr, kind="merge", execution=None, actor=FIXTURE["owner"])


def test_ready_is_advisory_and_columns_are_not_outcomes():
    target = task(board_column="done", execution_state="succeeded")
    result = evaluate(target)
    assert not result.advisory_ready and result.accepted_stage is None
    result = evaluate(target, review(target=target))
    assert result.advisory_ready and result.accepted_stage == "design"
    assert not result.grants_authority
    assert result.execution_state == "succeeded" and result.board_column == "done"


@pytest.mark.parametrize("result", ["failure", "unknown", "skipped", "cancelled"])
def test_non_success_ci_never_passes(result):
    target = source_task()
    result = evaluate(
        target,
        review(target=target),
        ci(target=target, result=result),
        ci("second", target, PR2),
    )
    assert "CI_NOT_SUCCESS" in result.blockers


def test_two_required_prs_partial_merge_and_full_merge():
    target = source_task()
    records = [
        target,
        review(target=target),
        ci(target=target),
        ci("second", target, PR2),
    ]
    result = evaluate(*records)
    assert (
        result.advisory_ready
        and result.accepted_stage is None
        and result.merge_state == "none"
    )
    records.append(merge(target, PR))
    result = evaluate(*records)
    assert (
        result.advisory_ready
        and result.merge_state == "partial"
        and result.accepted_stage is None
    )
    records.append(merge(target, PR2, "merge-second"))
    result = evaluate(*records)
    assert result.accepted_stage == "source" and result.merge_state == "all"


def test_wrong_head_stale_review_and_findings_block():
    target = source_task()
    records = [target, ci(target=target), ci("second", target, PR2)]
    wrong = replace(PR, head="d" * 40)
    result = evaluate(*records, review(target=target, required_prs=(wrong, PR2)))
    assert "REVIEW_HEAD_MISMATCH" in result.blockers
    result = evaluate(*records, review(target=target, findings=("unresolved",)))
    assert "REVIEW_FINDINGS" in result.blockers
    old = review(target=target)
    result = evaluate(
        *records,
        replace(old, envelope=replace(old.envelope, source_at=0)),
        now=datetime.fromtimestamp(111, timezone.utc),
    )
    assert "REVIEW_STALE" in result.blockers


def test_changed_revision_contract_head_and_required_set_invalidate_old_evidence():
    original = source_task(
        required_prs=(PR,),
        required_checks=(m.Check(PR.repository, PR.number, "tests", "unit"),),
    )
    second = source_task(
        envelope=envelope("task-2", revision=2, contract_digest="d" * 64)
    )
    result = r.evaluate(
        snapshot(original, review(target=original), ci(target=original), second),
        "task",
        expected_ledger_revision=1,
        now=NOW,
        policy=POLICY,
    )
    assert {"CI_MISSING", "REVIEW_MISSING"} <= set(result.blockers)


def test_unrelated_or_late_success_cannot_resolve_failed_ci():
    target = source_task()
    failed = ci(target=target, result="failure")
    other = ci("second", target, PR2)
    conflict = ci("success", target)
    result = evaluate(target, review(target=target), failed, other, conflict)
    assert "CI_CONFLICT" in result.blockers
    fixed = replace(conflict, supersedes=(failed.envelope.record_id,))
    assert evaluate(target, review(target=target), failed, other, fixed).advisory_ready
    wrong_head = ci("wrong", target, replace(PR, head="e" * 40))
    assert (
        "CI_HEAD_MISMATCH"
        in evaluate(target, review(target=target), wrong_head, other).blockers
    )


@pytest.mark.parametrize(
    "kind,decision",
    [
        ("model", "accepted"),
        ("human", "dismissed"),
        ("human", "unknown"),
        ("human", "rejected"),
    ],
)
def test_claimed_model_and_nonacceptance_cannot_substitute_human_review(kind, decision):
    assert not evaluate(
        task(), review(principal_kind=kind, decision=decision)
    ).advisory_ready


def test_explicit_stop_latches_across_revision_restart_and_clock_advance(tmp_path):
    from axel.lifecycle_store import Append, LifecycleStore

    target = task()
    stop = m.Transition(envelope("stop"), "stop")
    path = tmp_path / "db"
    with LifecycleStore.initialize_new(path, SCOPE) as store:
        store.append(
            Append(
                "invented-writer",
                "stop-op",
                0,
                (("task", 0),),
                (target, review(), stop),
            )
        )
    with LifecycleStore.open_existing(path, SCOPE) as store:
        result = r.evaluate(
            store.snapshot(),
            "task",
            expected_ledger_revision=1,
            now=datetime.fromtimestamp(300, timezone.utc),
            policy=POLICY,
        )
        assert "STOP_LATCHED" in result.blockers
    second = task(revision=2)
    assert (
        "STOP_LATCHED"
        in evaluate(target, stop, second, review("review-2", second)).blockers
    )
    resume = m.Transition(envelope("resume"), "resume", "stop")
    assert evaluate(target, review(), stop, resume).advisory_ready
    with pytest.raises(m.RecordError):
        snapshot(target, stop, replace(resume, resume_of="wrong"))


@pytest.mark.parametrize("clock,blocked", [(109, False), (110, True), (111, True)])
def test_configurable_cutoff_is_inclusive(clock, blocked):
    result = evaluate(
        task(),
        review(),
        now=datetime.fromtimestamp(clock, timezone.utc),
        policy=replace(POLICY, cutoff_at=110),
    )
    assert ("CUTOFF" in result.blockers) is blocked


@pytest.mark.parametrize(
    "date", ["2026-03-06", "2026-03-09", "2026-10-30", "2026-11-02"]
)
def test_explicit_utc_policy_windows_cover_dst(date):
    zone = ZoneInfo("America/Los_Angeles")
    start = int(
        datetime.fromisoformat(date + "T09:00:00").replace(tzinfo=zone).timestamp()
    )
    end = int(
        datetime.fromisoformat(date + "T17:00:00").replace(tzinfo=zone).timestamp()
    )
    policy = replace(
        POLICY,
        valid_until=end + 100,
        evidence_max_age=end + 100,
        blocked_windows=((start, end),),
    )
    for clock, blocked in (
        (start - 1, False),
        (start, True),
        (end - 1, True),
        (end, False),
    ):
        result = evaluate(
            task(),
            review(),
            now=datetime.fromtimestamp(clock, timezone.utc),
            policy=policy,
        )
        assert ("WORKING_HOURS" in result.blockers) is blocked


def test_ambiguous_time_stale_unknown_policy_deadline_and_capabilities():
    assert (
        "AMBIGUOUS_TIME"
        in evaluate(task(), review(), now=datetime(2026, 11, 1, 1, 30)).blockers
    )
    assert (
        "POLICY_STALE"
        in evaluate(task(), review(), policy=replace(POLICY, valid_until=110)).blockers
    )
    assert (
        "POLICY_UNKNOWN"
        in evaluate(
            task(), review(), policy=replace(POLICY, stop_state="unknown")
        ).blockers
    )
    assert (
        "CAPABILITY_MISSING"
        in evaluate(
            task(), review(), policy=replace(POLICY, available_capabilities=())
        ).blockers
    )
    assert "DEADLINE" in evaluate(task(deadline=110), review()).blockers
    assert (
        "SNAPSHOT_CHANGED"
        in evaluate(task(), review(), expected_ledger_revision=2).blockers
    )


@pytest.mark.parametrize("state", ["cancelled", "unknown", "failed", "running"])
def test_cancelled_unknown_and_elapsed_lease_never_imply_success(state):
    attempt = m.Attempt(envelope("attempt-observation"), "attempt", 1, state, 105)
    result = evaluate(task(), review(), attempt)
    assert not result.advisory_ready and not result.grants_authority
    if state == "running":
        assert "LEASE_EXPIRED" in result.blockers


def test_dependency_requires_exact_acceptance_stage_and_contract():
    downstream, upstream = task("downstream"), task("upstream")
    records = (
        downstream,
        upstream,
        review("down-review", downstream),
        review("up-review", upstream),
    )
    assert evaluate(*records, dependency(downstream, upstream)).advisory_ready
    assert (
        "DEPENDENCY_UNSATISFIED"
        in evaluate(*records, dependency(downstream, upstream, stage="source")).blockers
    )
    assert (
        "DEPENDENCY_UNSATISFIED"
        in evaluate(
            *records, dependency(downstream, upstream, acceptance_digest="b" * 64)
        ).blockers
    )


def test_runtime_requires_actual_matching_success_observation():
    target = source_task(stage="runtime", execution_state="succeeded")
    records = [
        target,
        review(target=target),
        ci(target=target),
        ci("second", target, PR2),
        merge(target, PR),
        merge(target, PR2, "merge-second"),
    ]
    assert "RUNTIME_MISSING" in evaluate(*records).blockers
    attempt = m.Attempt(envelope("attempt"), "local-attempt", 1, "succeeded")
    evidence = m.Evidence(
        envelope("runtime"),
        "runtime",
        "success",
        "artifact",
        DIGEST,
        attempt_id="local-attempt",
    )
    assert evaluate(*records, attempt, evidence).accepted_stage == "runtime"


def test_injected_text_is_inert_and_reducer_performs_no_io(monkeypatch):
    import builtins
    import socket
    import subprocess

    records = (task(), review())

    def denied(*args, **kwargs):
        raise AssertionError("unexpected I/O")

    monkeypatch.setattr(builtins, "open", denied)
    monkeypatch.setattr(socket, "socket", denied)
    monkeypatch.setattr(subprocess, "Popen", denied)
    assert evaluate(*records).advisory_ready
    assert not evaluate(
        *records, policy=replace(POLICY, stop_state="stopped")
    ).advisory_ready


@pytest.mark.parametrize("state", ["unknown", "draft", "closed"])
def test_pr_state_requires_explicit_ready_observation(state):
    pr = replace(PR, state=state)
    target = source_task(required_prs=(pr, PR2))
    result = evaluate(
        target,
        review(target=target),
        ci(target=target, pr=pr),
        ci("other", target, PR2),
    )
    assert "PR_" + state.upper() in result.blockers


def test_malformed_snapshot_policy_and_missing_task_are_safe():
    result = r.evaluate(
        None, "task", expected_ledger_revision=1, now=NOW, policy=POLICY
    )
    assert result.blockers == ("INVALID_SNAPSHOT",)
    assert (
        "POLICY_UNKNOWN"
        in evaluate(
            task(), review(), policy=replace(POLICY, available_capabilities=[])
        ).blockers
    )
    assert (
        "POLICY_SCOPE"
        in evaluate(
            task(), review(), policy=replace(POLICY, scope=m.Scope("other", "local"))
        ).blockers
    )
    result = r.evaluate(
        snapshot(task()), "absent", expected_ledger_revision=1, now=NOW, policy=POLICY
    )
    assert result.blockers == ("TASK_MISSING",)


@pytest.mark.parametrize("state", ["cancelled", "unknown"])
def test_task_cancellation_and_unknown_state_block(state):
    assert (
        "EXECUTION_" + state.upper()
        in evaluate(task(execution_state=state), review()).blockers
    )


def test_missing_source_requirements_future_evidence_and_merge_failures():
    target = task(stage="source", required_reviews=())
    assert {"REQUIRED_PRS_MISSING", "HUMAN_REVIEW_REQUIRED"} <= set(
        evaluate(target).blockers
    )
    target = source_task(required_checks=())
    assert "REQUIRED_CHECKS_MISSING" in evaluate(target, review(target=target)).blockers
    target = source_task()
    records = [
        target,
        review(target=target),
        ci(target=target),
        ci("second", target, PR2),
    ]
    future = replace(records[1], envelope=replace(records[1].envelope, observed_at=120))
    assert "REVIEW_FUTURE" in evaluate(target, future, *records[2:]).blockers
    assert (
        "MERGE_BINDING"
        in evaluate(*records, replace(merge(target, PR), actor="other-owner")).blockers
    )
    assert (
        "MERGE_NOT_SUCCESS"
        in evaluate(*records, replace(merge(target, PR), result="unknown")).blockers
    )


def test_review_supersession_and_incomplete_runtime():
    first = review(decision="rejected")
    second = review("second", supersedes=("review",))
    assert evaluate(task(), first, second).advisory_ready
    target = source_task(stage="runtime")
    attempt = m.Attempt(envelope("attempt"), "attempt", 1, "failed")
    evidence = m.Evidence(
        envelope("runtime"),
        "runtime",
        "failure",
        "artifact",
        DIGEST,
        attempt_id="attempt",
    )
    result = evaluate(target, attempt, evidence)
    assert {"RUNTIME_NOT_SUCCESS", "EXECUTION_INCOMPLETE"} <= set(result.blockers)


def test_modules_import_without_network_subprocess_or_unexpected_files():
    import os
    import subprocess
    import sys
    from pathlib import Path

    code = """
import dataclasses, datetime, functools, hashlib, json, os, pathlib
import re, sqlite3, sys, types, typing
import axel
root = pathlib.Path(axel.__file__).parent.resolve()
names = ('lifecycle_records', 'lifecycle_store', 'lifecycle_readiness')
allowed = {str(root / (name + '.py')) for name in names}
def audit(event, args):
    if event == 'open':
        path, mode, flags = args
        if isinstance(mode, str) and any(c in mode for c in 'wax+'):
            raise RuntimeError('unexpected write')
        if isinstance(flags, int) and flags & (os.O_WRONLY | os.O_RDWR | os.O_CREAT):
            raise RuntimeError('unexpected write')
        if (str(pathlib.Path(path).resolve()) not in allowed
                and '__pycache__' not in str(path)):
            raise RuntimeError('unexpected read')
    if event.startswith(('socket.', 'subprocess.')):
        raise RuntimeError('unexpected external I/O')
sys.addaudithook(audit)
import axel.lifecycle_records, axel.lifecycle_store, axel.lifecycle_readiness
print('inert import')
"""
    env = dict(os.environ, PYTHONDONTWRITEBYTECODE="1")
    result = subprocess.run(
        [sys.executable, "-B", "-c", code],
        cwd=Path(__file__).parents[1],
        env=env,
        capture_output=True,
        text=True,
        check=True,
    )
    assert result.stdout.strip() == "inert import"
    root = Path(__file__).parents[1]
    for filename in ("__init__.py", "cli.py", "task_manager.py", "repo_manager.py"):
        assert "lifecycle_" not in (root / "axel" / filename).read_text()


def test_diamond_dependency_reuses_one_evaluated_upstream():
    a, b, c, d = [task(x) for x in "abcd"]
    records = [a, b, c, d] + [
        review(f"review-{x.envelope.task_id}", x) for x in (a, b, c, d)
    ]
    records += [
        dependency(a, b, "ab"),
        dependency(a, c, "ac"),
        dependency(b, d, "bd"),
        dependency(c, d, "cd"),
    ]
    assert evaluate(*records).advisory_ready
