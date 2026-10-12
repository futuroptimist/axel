"""Transactional, bounded-store tests using temporary invented databases."""

import sqlite3
import threading
import time
from concurrent.futures import ThreadPoolExecutor
from dataclasses import replace

import pytest
from test_lifecycle_records import SCOPE, envelope, review, task

from axel import lifecycle_records as m
from axel.lifecycle_store import (
    Append,
    CommitUnknown,
    Conflict,
    LifecycleStore,
    RecoveryRequired,
    StoreUnavailable,
)


def command(*records, key="operation", revision=0, expected=(("task", 0),)):
    return Append(
        "invented-writer", key, revision, expected, tuple(records or (task(),))
    )


def test_explicit_create_reopen_and_historical_replay(tmp_path):
    path = tmp_path / "ledger.sqlite"
    with pytest.raises(RecoveryRequired):
        LifecycleStore.open_existing(path, SCOPE)
    assert not path.exists()
    first = command()
    with LifecycleStore.initialize_new(path, SCOPE) as store:
        receipt = store.append(first)
        assert receipt.ledger_revision == 1
        with pytest.raises(RecoveryRequired):
            LifecycleStore.initialize_new(path, SCOPE)
        store.append(
            command(review(), key="later", revision=1, expected=(("task", 1),))
        )
        assert store.append(first) == receipt
        assert store.snapshot().ledger_revision == 2
    with LifecycleStore.open_existing(path, SCOPE) as store:
        assert store.snapshot().records == (task(), review())
        assert store.append(first) == receipt


def test_changed_key_payload_and_stale_cas_are_atomic(tmp_path):
    with LifecycleStore.initialize_new(tmp_path / "db", SCOPE) as store:
        store.append(command())
        before = store.snapshot()
        for changed in (
            command(task(title="different")),
            command(key="new"),
            command(review(), key="new", revision=1),
        ):
            with pytest.raises(Conflict):
                store.append(changed)
            assert store.snapshot() == before
        with pytest.raises(m.RecordError):
            store.append(command(review(), key="new", revision=1, expected=()))


def test_two_connections_same_operation_commit_one_receipt(tmp_path):
    path = tmp_path / "db"
    LifecycleStore.initialize_new(path, SCOPE).close()
    barrier = threading.Barrier(2)

    def append_once(_):
        with LifecycleStore.open_existing(path, SCOPE, timeout=2) as store:
            barrier.wait(timeout=5)
            return store.append(command())

    with ThreadPoolExecutor(max_workers=2) as pool:
        results = list(pool.map(append_once, range(2)))
    assert results[0] == results[1]
    with LifecycleStore.open_existing(path, SCOPE) as store:
        assert store.snapshot().records == (task(),)
        assert store._db.execute("SELECT count(*) FROM audit").fetchone() == (1,)


STEPS = [
    "before_begin",
    "after_begin",
    "before_record:0",
    "after_record:0",
    "before_record:1",
    "after_record:1",
    "before_projection",
    "before_head:task",
    "after_head:task",
    "after_projection",
    "before_audit",
    "after_audit",
    "before_receipt",
    "after_receipt",
    "before_metadata",
    "after_metadata",
    "before_commit",
    "after_commit",
]


@pytest.mark.parametrize("step", STEPS)
@pytest.mark.parametrize("error", [OSError, sqlite3.OperationalError])
def test_every_append_boundary_is_atomic_and_reconciles(tmp_path, step, error):
    path = tmp_path / "db"
    store = LifecycleStore.initialize_new(path, SCOPE)
    request = command(task(), review())

    def inject(current):
        if current == step:
            raise error("injected write failure")

    store._checkpoint = inject
    with pytest.raises((OSError, StoreUnavailable)) as caught:
        store.append(request)
    if step == "after_commit":
        assert isinstance(caught.value, CommitUnknown)
    store.close()
    with LifecycleStore.open_existing(path, SCOPE) as reopened:
        state = reopened.snapshot()
        assert len(state.records) == (2 if step == "after_commit" else 0)
        for table in ("operations", "audit", "task_heads"):
            assert reopened._db.execute(f"SELECT count(*) FROM {table}").fetchone()[
                0
            ] == (1 if step == "after_commit" else 0)
        receipt = reopened.append(request)
        assert receipt.ledger_revision == 1
        assert reopened.snapshot().records == (task(), review())


def test_real_sqlite_lock_wait_is_bounded(tmp_path):
    path = tmp_path / "db"
    with LifecycleStore.initialize_new(path, SCOPE, timeout=0.02) as store:
        writer = sqlite3.connect(path)
        writer.execute("BEGIN IMMEDIATE")
        start = time.monotonic()
        with pytest.raises(StoreUnavailable):
            store.append(command())
        assert time.monotonic() - start < 3
        writer.rollback()
        writer.close()
        assert store.snapshot().ledger_revision == 0
        store.append(command())


def test_real_sqlite_full_rolls_back(tmp_path):
    with LifecycleStore.initialize_new(tmp_path / "db", SCOPE) as store:
        pages = store._db.execute("PRAGMA page_count").fetchone()[0]
        store._db.execute(f"PRAGMA max_page_count={pages}")
        with pytest.raises(StoreUnavailable):
            store.append(command(task(title="x" * 50000)))
        assert store.snapshot().records == ()


@pytest.mark.parametrize(
    "mutation",
    [
        "PRAGMA user_version=999",
        "CREATE TABLE unexpected (value TEXT)",
        "UPDATE metadata SET profile='other'",
        "UPDATE metadata SET record_count=0",
        "UPDATE task_heads SET revision=9",
        "DELETE FROM audit",
        "UPDATE operations SET digest='corrupt'",
        "UPDATE records SET payload=x'00'",
    ],
)
def test_corrupt_or_incompatible_storage_is_untouched(tmp_path, mutation):
    path = tmp_path / "db"
    with LifecycleStore.initialize_new(path, SCOPE) as store:
        store.append(command())
    with sqlite3.connect(path) as db:
        db.execute(mutation)
    before = path.read_bytes()
    inventory = set(tmp_path.iterdir())
    with pytest.raises(RecoveryRequired):
        LifecycleStore.open_existing(path, SCOPE)
    assert path.read_bytes() == before
    assert set(tmp_path.iterdir()) == inventory


def test_bad_file_wrong_scope_and_unrecovered_journal_fail_closed(tmp_path):
    path = tmp_path / "db"
    path.write_bytes(b"not sqlite")
    with pytest.raises(RecoveryRequired):
        LifecycleStore.open_existing(path, SCOPE)
    assert path.read_bytes() == b"not sqlite"
    other = tmp_path / "valid"
    LifecycleStore.initialize_new(other, SCOPE).close()
    with pytest.raises(RecoveryRequired):
        LifecycleStore.open_existing(other, m.Scope("elsewhere", "synthetic-local"))
    (tmp_path / "valid-journal").write_bytes(b"invented interrupted journal")
    with pytest.raises(RecoveryRequired):
        LifecycleStore.open_existing(other, SCOPE)


def test_command_and_retention_limits_reject_without_truncation(tmp_path, monkeypatch):
    with LifecycleStore.initialize_new(tmp_path / "db", SCOPE) as store:
        records = [task()] + [
            m.Transition(envelope(f"observation-{i}"), "observe") for i in range(64)
        ]
        with pytest.raises(m.RecordError, match="command_limit"):
            store.append(command(*records))
        store.append(command(*records[:64]))
        before = store.snapshot()
        monkeypatch.setattr(m, "MAX_RECORDS", 64)
        with pytest.raises(m.RecordError, match="record_limit"):
            store.append(
                command(records[64], key="next", revision=1, expected=(("task", 1),))
            )
        assert store.snapshot() == before


def test_invalid_graph_and_scope_reject_entire_batch(tmp_path):
    with LifecycleStore.initialize_new(tmp_path / "db", SCOPE) as store:
        invalid = m.Dependency(envelope("dependency"), "missing", "design", "a" * 64)
        with pytest.raises(m.RecordError):
            store.append(command(task(), invalid))
        assert store.snapshot().records == ()
        bad = replace(
            task(),
            envelope=replace(task().envelope, scope=m.Scope("different", "profile")),
        )
        with pytest.raises(m.RecordError):
            store.append(command(bad))
        assert store.snapshot().records == ()


def test_no_extension_or_sql_command_interface(tmp_path):
    with LifecycleStore.initialize_new(tmp_path / "db", SCOPE) as store:
        with pytest.raises(sqlite3.OperationalError, match="not authorized"):
            store._db.execute("SELECT load_extension('invented')")
        with pytest.raises(m.RecordError):
            store.append("DELETE FROM records")


def test_failed_initialization_and_live_corruption_require_recovery(
    tmp_path, monkeypatch
):
    from axel import lifecycle_store

    original = lifecycle_store._connect

    def failed(*args, **kwargs):
        raise sqlite3.OperationalError("injected initialization failure")

    monkeypatch.setattr(lifecycle_store, "_connect", failed)
    with pytest.raises(RecoveryRequired):
        LifecycleStore.initialize_new(tmp_path / "failed", SCOPE)
    assert (tmp_path / "failed").exists()
    monkeypatch.setattr(lifecycle_store, "_connect", original)
    with LifecycleStore.initialize_new(tmp_path / "valid", SCOPE) as store:
        store._db.execute("UPDATE metadata SET profile='mismatched'")
        with pytest.raises(RecoveryRequired):
            store.snapshot()
        with pytest.raises(RecoveryRequired):
            store.append(command())


def test_orphan_journal_and_network_paths_are_refused(tmp_path):
    (tmp_path / "db-journal").write_bytes(b"invented journal")
    with pytest.raises(RecoveryRequired):
        LifecycleStore.initialize_new(tmp_path / "db", SCOPE)
    assert not (tmp_path / "db").exists()
    for factory in (LifecycleStore.initialize_new, LifecycleStore.open_existing):
        with pytest.raises(RecoveryRequired, match="network_path"):
            factory("//invented.invalid/share/db", SCOPE)


def test_initialization_verification_failure_closes_connection(tmp_path, monkeypatch):
    def failed(self):
        raise m.RecordError("injected verification failure")

    with monkeypatch.context() as patch:
        patch.setattr(LifecycleStore, "_read", failed)
        with pytest.raises(RecoveryRequired):
            LifecycleStore.initialize_new(tmp_path / "db", SCOPE)
    with LifecycleStore.open_existing(tmp_path / "db", SCOPE) as store:
        assert store.snapshot().records == ()
