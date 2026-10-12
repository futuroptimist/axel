"""Pure advisory reduction of synthetic snapshots, never execution authority."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timezone

from . import lifecycle_records as model


@dataclass(frozen=True)
class Policy:
    """Unauthenticated input. UTC windows must be resolved by the caller.

    The reducer does not load a timezone database, read the system clock, infer
    capabilities, or authenticate a principal. Ambiguous clocks fail closed.
    """

    scope: model.Scope
    version: str
    valid_from: int
    valid_until: int
    evidence_max_age: int
    available_capabilities: tuple[str, ...]
    stop_state: str = "unknown"
    cutoff_at: int | None = None
    blocked_windows: tuple[tuple[int, int], ...] = ()


@dataclass(frozen=True)
class Readiness:
    task_id: str
    task_revision: int
    ledger_revision: int
    blockers: tuple[str, ...]
    advisory_ready: bool
    execution_state: str
    board_column: str
    accepted_stage: str | None
    merge_state: str
    grants_authority: bool = False


def _policy_valid(policy):
    return (
        type(policy) is Policy
        and type(policy.scope) is model.Scope
        and type(policy.version) is str
        and 0 < len(policy.version) <= 200
        and all(
            type(x) is int
            for x in (policy.valid_from, policy.valid_until, policy.evidence_max_age)
        )
        and 0 <= policy.valid_from < policy.valid_until
        and policy.evidence_max_age > 0
        and type(policy.available_capabilities) is tuple
        and len(policy.available_capabilities) <= 256
        and all(type(x) is str for x in policy.available_capabilities)
        and policy.stop_state in ("clear", "stopped", "unknown")
        and (policy.cutoff_at is None or type(policy.cutoff_at) is int)
        and type(policy.blocked_windows) is tuple
        and len(policy.blocked_windows) <= 256
        and all(
            type(w) is tuple
            and len(w) == 2
            and all(type(x) is int for x in w)
            and 0 <= w[0] < w[1]
            for w in policy.blocked_windows
        )
    )


def evaluate(
    snapshot: model.Snapshot,
    task_id: str,
    *,
    expected_ledger_revision: int,
    now: datetime,
    policy: Policy,
) -> Readiness:
    """Re-evaluate the complete snapshot at an explicit, unambiguous UTC instant.

    A receipt cannot be passed as cached readiness. Even a positive result grants
    no dispatch, retry, merge, export, approval-consumption or recovery authority.
    """
    global_blockers = set()
    try:
        latest = model.validate_snapshot(snapshot)
    except (model.RecordError, TypeError, AttributeError):
        return Readiness(
            task_id,
            0,
            0,
            ("INVALID_SNAPSHOT",),
            False,
            "unknown",
            "backlog",
            None,
            "unknown",
        )
    if (
        type(expected_ledger_revision) is not int
        or expected_ledger_revision != snapshot.ledger_revision
    ):
        global_blockers.add("SNAPSHOT_CHANGED")
    if type(now) is not datetime or now.tzinfo is not timezone.utc:
        global_blockers.add("AMBIGUOUS_TIME")
        instant = None
    else:
        instant = now.timestamp()
    if not _policy_valid(policy):
        global_blockers.add("POLICY_UNKNOWN")
    else:
        if policy.scope != snapshot.scope:
            global_blockers.add("POLICY_SCOPE")
        if policy.stop_state != "clear":
            global_blockers.add(
                "POLICY_STOPPED" if policy.stop_state == "stopped" else "POLICY_UNKNOWN"
            )
        if instant is not None:
            if not policy.valid_from <= instant < policy.valid_until:
                global_blockers.add("POLICY_STALE")
            if policy.cutoff_at is not None and instant >= policy.cutoff_at:
                global_blockers.add("CUTOFF")
            if any(start <= instant < end for start, end in policy.blocked_windows):
                global_blockers.add("WORKING_HOURS")
    current = {task: [] for task in latest}
    stopped = set()
    for record in snapshot.records:
        env = record.envelope
        if env.task_revision == latest[env.task_id].envelope.task_revision:
            current[env.task_id].append(record)
        if isinstance(record, model.Transition):
            if record.action == "stop":
                stopped.add(env.task_id)
            elif record.action == "resume":
                stopped.discard(env.task_id)
    results = {}

    def reduce(task):
        if task in results:
            return results[task]
        revision = latest[task]
        blockers = set(global_blockers)
        observations = current[task]
        if task in stopped:
            blockers.add("STOP_LATCHED")
        if revision.execution_state in ("cancelled", "unknown"):
            blockers.add("EXECUTION_" + revision.execution_state.upper())
        if _policy_valid(policy):
            if not set(revision.capabilities) <= set(policy.available_capabilities):
                blockers.add("CAPABILITY_MISSING")
        if (
            instant is not None
            and revision.deadline is not None
            and instant >= revision.deadline
        ):
            blockers.add("DEADLINE")
        attempts = {}
        for record in observations:
            if isinstance(record, model.Attempt):
                attempts[record.attempt_id] = record
        for attempt in attempts.values():
            if attempt.state != "succeeded":
                blockers.add("ATTEMPT_" + attempt.state.upper())
            if (
                instant is not None
                and attempt.state == "running"
                and attempt.lease_until is not None
                and instant >= attempt.lease_until
            ):
                blockers.add("LEASE_EXPIRED")

        def choose(items, prefix):
            superseded = {old for item in items for old in item.supersedes}
            active = [
                item for item in items if item.envelope.record_id not in superseded
            ]
            if not active:
                blockers.add(prefix + "_MISSING")
                return None
            if len(active) != 1:
                blockers.add(prefix + "_CONFLICT")
                return None
            item = active[0]
            if instant is not None and _policy_valid(policy):
                # Both source and observation clocks must be plausible/fresh.
                if item.envelope.observed_at > instant:
                    blockers.add(prefix + "_FUTURE")
                if instant - item.envelope.source_at > policy.evidence_max_age:
                    blockers.add(prefix + "_STALE")
            return item

        evidence = [r for r in observations if isinstance(r, model.Evidence)]
        for check in revision.required_checks:
            matches = [
                r
                for r in evidence
                if r.kind == "ci"
                and r.execution.pr.repository == check.repository
                and r.execution.pr.number == check.number
                and r.execution.workflow == check.workflow
                and r.execution.job == check.job
            ]
            item = choose(matches, "CI")
            if item:
                if item.pr not in revision.required_prs:
                    blockers.add("CI_HEAD_MISMATCH")
                if item.result != "success":
                    blockers.add("CI_NOT_SUCCESS")
        if revision.stage in ("source", "runtime"):
            if not revision.required_prs:
                blockers.add("REQUIRED_PRS_MISSING")
            for pr in revision.required_prs:
                if pr.state not in ("ready", "merged"):
                    blockers.add("PR_" + pr.state.upper())
                if not any(
                    (c.repository, c.number) == (pr.repository, pr.number)
                    for c in revision.required_checks
                ):
                    blockers.add("REQUIRED_CHECKS_MISSING")
        if not revision.required_reviews:
            blockers.add("HUMAN_REVIEW_REQUIRED")
        for reviewer in revision.required_reviews:
            item = choose(
                [
                    r
                    for r in observations
                    if isinstance(r, model.ReviewDecision)
                    and r.reviewer == reviewer
                    and r.stage == revision.stage
                ],
                "REVIEW",
            )
            if item:
                if item.principal_kind != "human":
                    blockers.add("HUMAN_REVIEW_REQUIRED")
                if item.decision != "accepted":
                    blockers.add("REVIEW_NOT_ACCEPTED")
                if item.findings:
                    blockers.add("REVIEW_FINDINGS")
                if item.required_prs != revision.required_prs:
                    blockers.add("REVIEW_HEAD_MISMATCH")
        merges = 0
        for pr in revision.required_prs:
            items = [
                r
                for r in evidence
                if r.kind == "merge"
                and (r.pr.repository, r.pr.number) == (pr.repository, pr.number)
            ]
            if not items:
                continue  # Awaiting merge is distinct from review readiness.
            item = choose(items, "MERGE")
            if item:
                if item.pr != pr or item.actor != revision.owner:
                    blockers.add("MERGE_BINDING")
                elif item.result != "success":
                    blockers.add("MERGE_NOT_SUCCESS")
                else:
                    merges += 1
        merge_state = (
            "none"
            if not merges
            else "all" if merges == len(revision.required_prs) else "partial"
        )
        if revision.stage == "runtime":
            item = choose([r for r in evidence if r.kind == "runtime"], "RUNTIME")
            if item and (
                item.result != "success"
                or attempts[item.attempt_id].state != "succeeded"
            ):
                blockers.add("RUNTIME_NOT_SUCCESS")
            if revision.execution_state != "succeeded":
                blockers.add("EXECUTION_INCOMPLETE")
        for dependency in observations:
            if isinstance(dependency, model.Dependency):
                upstream = reduce(dependency.upstream_task_id)
                accepted = latest[dependency.upstream_task_id].envelope.contract_digest
                if (
                    upstream.accepted_stage != dependency.required_stage
                    or accepted != dependency.acceptance_digest
                ):
                    blockers.add("DEPENDENCY_UNSATISFIED")
        accepted_stage = None
        if not blockers and (revision.stage == "design" or merge_state == "all"):
            accepted_stage = revision.stage
        result = Readiness(
            task,
            revision.envelope.task_revision,
            snapshot.ledger_revision,
            tuple(sorted(blockers)),
            not blockers,
            revision.execution_state,
            revision.board_column,
            accepted_stage,
            merge_state,
        )
        results[task] = result
        return result

    if task_id not in latest:
        return Readiness(
            task_id,
            0,
            snapshot.ledger_revision,
            ("TASK_MISSING",),
            False,
            "unknown",
            "backlog",
            None,
            "unknown",
        )
    return reduce(task_id)
