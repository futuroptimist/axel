"""Explicit, bounded SQLite storage for invented local lifecycle records only.

No startup, legacy import, repair, restore, pruning, arbitrary SQL or execution
interface. Checksums detect accidental corruption, not malicious replacement.
"""

from __future__ import annotations

import json
import os
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from . import lifecycle_records as model

SCHEMA_VERSION = 1
APPLICATION_ID = 0x41584C46
MAX_DATABASE_BYTES = 64 * 1024 * 1024
SCHEMA = (
    "CREATE TABLE metadata (singleton INTEGER PRIMARY KEY CHECK(singleton=1), "
    "workspace TEXT NOT NULL, profile TEXT NOT NULL, revision INTEGER NOT NULL, "
    "record_count INTEGER NOT NULL, payload_bytes INTEGER NOT NULL)",
    "CREATE TABLE operations (revision INTEGER PRIMARY KEY, principal TEXT NOT NULL, "
    "operation_key TEXT NOT NULL, digest TEXT NOT NULL, command BLOB NOT NULL, "
    "UNIQUE(principal, operation_key))",
    "CREATE TABLE records (sequence INTEGER PRIMARY KEY, "
    "record_id TEXT NOT NULL UNIQUE, "
    "revision INTEGER NOT NULL REFERENCES operations(revision) "
    "DEFERRABLE INITIALLY DEFERRED, payload BLOB NOT NULL)",
    "CREATE TABLE task_heads (task_id TEXT PRIMARY KEY, revision INTEGER NOT NULL, "
    "record_id TEXT NOT NULL REFERENCES records(record_id))",
    "CREATE TABLE audit (revision INTEGER PRIMARY KEY REFERENCES operations(revision) "
    "DEFERRABLE INITIALLY DEFERRED, digest TEXT NOT NULL)",
)


class RecoveryRequired(RuntimeError):
    """Storage is absent, incompatible, mismatched or corrupt; never auto-repair."""


class Conflict(ValueError):
    """Expected revisions or an existing operation payload do not match."""


class StoreUnavailable(RuntimeError):
    """A bounded lock wait or storage error prevented a confirmed append."""


class CommitUnknown(StoreUnavailable):
    """Reconcile the original operation key; do not invent a new retry key."""


@dataclass(frozen=True)
class Append:
    principal: str
    operation_key: str
    expected_ledger_revision: int
    expected_task_revisions: tuple[tuple[str, int], ...]
    records: tuple


def _command(scope, command, payloads):
    return model.canonical(
        {
            "scope": scope,
            "principal": command.principal,
            "operation_key": command.operation_key,
            "kind": "append",
            "expected_ledger_revision": command.expected_ledger_revision,
            "expected_task_revisions": command.expected_task_revisions,
            "records": [model.payload_digest(p) for p in payloads],
        }
    )


def _validate_command(command):
    model.require(type(command) is Append, "command")
    model.require(
        type(command.principal) is str and type(command.operation_key) is str, "command"
    )
    model.identifier(command.principal)
    model.identifier(command.operation_key)
    model.require(
        type(command.expected_ledger_revision) is int
        and command.expected_ledger_revision >= 0,
        "revision",
    )
    model.require(
        type(command.records) is tuple
        and 0 < len(command.records) <= model.MAX_COMMAND_RECORDS,
        "command_limit",
    )
    expected = command.expected_task_revisions
    model.require(
        type(expected) is tuple and len(expected) <= model.MAX_TASKS, "expected_tasks"
    )
    for pair in expected:
        model.require(
            type(pair) is tuple
            and len(pair) == 2
            and type(pair[0]) is str
            and type(pair[1]) is int
            and pair[1] >= 0,
            "expected_tasks",
        )
        model.identifier(pair[0])
    model.require(
        tuple(sorted(expected)) == expected and len(dict(expected)) == len(expected),
        "expected_tasks",
    )
    payloads = tuple(model.encode_record(record) for record in command.records)
    model.require(
        {r.envelope.task_id for r in command.records} <= dict(expected).keys(),
        "missing_expectation",
    )
    return payloads


def _connect(path, *, readonly, timeout):
    uri = path.as_uri() + ("?mode=ro&immutable=1" if readonly else "?mode=rw")
    connection = sqlite3.connect(uri, uri=True, timeout=timeout, isolation_level=None)
    # The optional method is absent on builds without extension-loading support.
    disable_extensions = getattr(connection, "enable_load_extension", None)
    if disable_extensions is not None:
        disable_extensions(False)
    connection.execute("PRAGMA trusted_schema=OFF")
    connection.execute("PRAGMA foreign_keys=ON")
    connection.execute("PRAGMA synchronous=FULL")
    return connection


def _local_path(path):
    # No network-share adapter. Mounted filesystem qualification remains external.
    if str(path).startswith(("\\\\", "//")):
        raise RecoveryRequired("network_path")
    return Path(path).absolute()


def _read_history(db, scope):
    model.require(
        db.execute("PRAGMA application_id").fetchone()[0] == APPLICATION_ID
        and db.execute("PRAGMA user_version").fetchone()[0] == SCHEMA_VERSION,
        "schema",
    )
    model.require(
        db.execute("PRAGMA journal_mode").fetchone()[0] == "delete"
        and db.execute("PRAGMA synchronous").fetchone()[0] == 2
        and db.execute("PRAGMA foreign_keys").fetchone()[0] == 1,
        "settings",
    )
    actual = {
        row[0]
        for row in db.execute("SELECT sql FROM sqlite_schema WHERE sql IS NOT NULL")
    }
    model.require(actual == set(SCHEMA), "schema")
    model.require(
        db.execute("PRAGMA quick_check").fetchall() == [("ok",)]
        and not db.execute("PRAGMA foreign_key_check").fetchall(),
        "integrity",
    )
    metadata = db.execute("SELECT * FROM metadata").fetchall()
    model.require(len(metadata) == 1, "metadata")
    _, workspace, profile, revision, count, size = metadata[0]
    model.require(
        (workspace, profile) == (scope.workspace_id, scope.profile_id),
        "scope",
    )
    # Aggregate lengths before fetching any untrusted encoded payload.
    inventory = db.execute(
        "SELECT count(*), coalesce(sum(length(payload)),0), "
        "coalesce(max(length(payload)),0) FROM records"
    ).fetchone()
    model.require(
        inventory[:2] == (count, size)
        and 0 <= count <= model.MAX_RECORDS
        and 0 <= size <= model.MAX_PAYLOAD_BYTES
        and inventory[2] <= model.MAX_RECORD_BYTES,
        "retention",
    )
    operations_size = db.execute(
        "SELECT count(*), coalesce(max(length(command)),0), "
        "coalesce(sum(length(command)),0) FROM operations"
    ).fetchone()
    model.require(
        operations_size[0] == revision
        and 0 <= revision <= count
        and operations_size[1] <= model.MAX_RECORD_BYTES
        and operations_size[2] <= model.MAX_PAYLOAD_BYTES,
        "operations",
    )
    model.require(
        db.execute("SELECT count(*) FROM task_heads").fetchone()[0] <= model.MAX_TASKS
        and db.execute("SELECT count(*) FROM audit").fetchone()[0] == revision,
        "projection_size",
    )
    rows = db.execute(
        "SELECT sequence, record_id, revision, payload "
        "FROM records ORDER BY sequence"
    ).fetchall()
    model.require([row[0] for row in rows] == list(range(1, count + 1)), "sequence")
    records = tuple(model.decode_record(row[3]) for row in rows)
    model.require(
        all(row[1] == record.envelope.record_id for row, record in zip(rows, records)),
        "record_id",
    )
    snapshot = model.Snapshot(scope, revision, records)
    latest = model.validate_snapshot(snapshot)
    heads = set(db.execute("SELECT * FROM task_heads"))
    model.require(
        heads
        == {
            (task, r.envelope.task_revision, r.envelope.record_id)
            for task, r in latest.items()
        },
        "projection",
    )
    operations = db.execute("SELECT * FROM operations ORDER BY revision").fetchall()
    model.require(
        [r[0] for r in operations] == list(range(1, revision + 1)),
        "operation_sequence",
    )
    model.require(
        set(db.execute("SELECT * FROM audit")) == {(r[0], r[3]) for r in operations},
        "audit",
    )
    receipts, groups = {}, {}
    for row in rows:
        groups.setdefault(row[2], []).append(row)
    for rev, principal, key, digest, raw in operations:
        group = groups.get(rev, [])
        model.require(0 < len(group) <= model.MAX_COMMAND_RECORDS, "operation_records")
        data = json.loads(raw)
        model.require(
            model.canonical(data) == raw and model.payload_digest(raw) == digest,
            "operation_digest",
        )
        model.require(
            data["records"] == [model.payload_digest(row[3]) for row in group]
            and data["expected_ledger_revision"] == rev - 1
            and data["principal"] == principal
            and data["operation_key"] == key
            and data["kind"] == "append"
            and model.canonical(data["scope"]) == model.canonical(scope),
            "operation_binding",
        )
        receipts[(principal, key)] = model.OperationReceipt(
            scope, principal, key, digest, rev, tuple(row[1] for row in group)
        )
    return snapshot, receipts, size


class LifecycleStore:
    """One explicit connection; concurrent writers use separate store instances."""

    def __init__(self, connection, scope):
        self._db = connection
        self.scope = scope

    @classmethod
    def initialize_new(cls, path: Path, scope: model.Scope, *, timeout=0.25):
        """Exclusively allocate a new file. Failure leaves a recovery-required file."""
        cls._arguments(scope, timeout)
        path = _local_path(path)
        if any(
            Path(str(path) + suffix).exists() for suffix in ("-journal", "-wal", "-shm")
        ):
            raise RecoveryRequired("journal_recovery_required")
        try:
            descriptor = os.open(path, os.O_CREAT | os.O_EXCL | os.O_WRONLY, 0o600)
        except OSError as exc:
            raise RecoveryRequired("initialize_refused") from exc
        os.close(descriptor)
        connection = None
        try:
            connection = _connect(path, readonly=False, timeout=timeout)
            connection.execute("PRAGMA journal_mode=DELETE")
            connection.execute("BEGIN IMMEDIATE")
            for statement in SCHEMA:
                connection.execute(statement)
            connection.execute(f"PRAGMA application_id={APPLICATION_ID}")
            connection.execute(f"PRAGMA user_version={SCHEMA_VERSION}")
            connection.execute(
                "INSERT INTO metadata VALUES (1, ?, ?, 0, 0, 0)",
                (scope.workspace_id, scope.profile_id),
            )
            connection.commit()
            store = cls(connection, scope)
            store._read()
            return store
        except (sqlite3.Error, model.RecordError) as exc:
            if connection:
                connection.close()
            raise RecoveryRequired("initialize_failed") from exc

    @classmethod
    def open_existing(cls, path: Path, scope: model.Scope, *, timeout=0.25):
        """Validate read-only first; never create, repair or recover a journal."""
        cls._arguments(scope, timeout)
        path = _local_path(path)
        connection = None
        try:
            if (
                not path.is_file()
                or path.is_symlink()
                or path.stat().st_size > MAX_DATABASE_BYTES
            ):
                raise RecoveryRequired("storage_unavailable")
            if any(
                Path(str(path) + suffix).exists()
                for suffix in ("-journal", "-wal", "-shm")
            ):
                raise RecoveryRequired("journal_recovery_required")
            connection = _connect(path, readonly=True, timeout=timeout)
            cls(connection, scope)._read()
            connection.close()
            connection = _connect(path, readonly=False, timeout=timeout)
            store = cls(connection, scope)
            store.snapshot()  # Check again on the actual connection.
            return store
        except (
            OSError,
            sqlite3.Error,
            ValueError,
            TypeError,
            KeyError,
            RecursionError,
            RecoveryRequired,
        ) as exc:
            if connection:
                connection.close()
            raise RecoveryRequired("open_failed") from exc

    @staticmethod
    def _arguments(scope, timeout):
        model.require(type(scope) is model.Scope, "scope")
        model.require(type(timeout) in (int, float) and 0 <= timeout <= 2, "timeout")

    def close(self):
        self._db.close()

    def __enter__(self):
        return self

    def __exit__(self, *_):
        self.close()

    def _read(self):
        return _read_history(self._db, self.scope)

    def snapshot(self) -> model.Snapshot:
        try:
            self._db.execute("BEGIN")
            result = self._read()[0]
            self._db.rollback()
            return result
        except (sqlite3.Error, ValueError, KeyError, TypeError, RecursionError) as exc:
            self._db.rollback()
            raise RecoveryRequired("snapshot_failed") from exc

    def _checkpoint(self, step):
        """Internal no-op seam for fault injection; never accepts caller code."""

    def append(self, command: Append) -> model.OperationReceipt:
        payloads = _validate_command(command)
        raw = _command(self.scope, command, payloads)
        digest = model.payload_digest(raw)
        committed = commit_started = False
        try:
            self._checkpoint("before_begin")
            self._db.execute("BEGIN IMMEDIATE")
            self._checkpoint("after_begin")
            try:
                snapshot, receipts, size = self._read()
            except (
                sqlite3.DatabaseError,
                ValueError,
                KeyError,
                TypeError,
                RecursionError,
            ) as exc:
                raise RecoveryRequired("append_recovery_required") from exc
            previous = receipts.get((command.principal, command.operation_key))
            if previous:
                if previous.payload_digest != digest:
                    raise Conflict("operation_payload")
                self._db.rollback()
                return previous  # Historical receipt only, never cached readiness.
            if snapshot.ledger_revision != command.expected_ledger_revision:
                raise Conflict("ledger_revision")
            heads = model.validate_snapshot(snapshot)
            for task, expected in command.expected_task_revisions:
                actual = heads[task].envelope.task_revision if task in heads else 0
                if actual != expected:
                    raise Conflict("task_revision")
            revision = snapshot.ledger_revision + 1
            used = self._db.execute(
                "SELECT coalesce(sum(length(command)),0) FROM operations"
            ).fetchone()[0]
            model.require(
                used + len(raw) <= model.MAX_PAYLOAD_BYTES, "command_retention"
            )
            candidate = model.Snapshot(
                self.scope, revision, snapshot.records + command.records
            )
            latest = model.validate_snapshot(candidate)
            for index, (record, payload) in enumerate(zip(command.records, payloads)):
                self._checkpoint(f"before_record:{index}")
                self._db.execute(
                    "INSERT INTO records VALUES (?, ?, ?, ?)",
                    (
                        len(snapshot.records) + index + 1,
                        record.envelope.record_id,
                        revision,
                        payload,
                    ),
                )
                self._checkpoint(f"after_record:{index}")
            self._checkpoint("before_projection")
            for task, record in latest.items():
                self._checkpoint(f"before_head:{task}")
                self._db.execute(
                    "INSERT INTO task_heads VALUES (?, ?, ?) ON CONFLICT(task_id) "
                    "DO UPDATE SET revision=excluded.revision, "
                    "record_id=excluded.record_id",
                    (task, record.envelope.task_revision, record.envelope.record_id),
                )
                self._checkpoint(f"after_head:{task}")
            self._checkpoint("after_projection")
            self._checkpoint("before_audit")
            self._db.execute("INSERT INTO audit VALUES (?, ?)", (revision, digest))
            self._checkpoint("after_audit")
            self._checkpoint("before_receipt")
            self._db.execute(
                "INSERT INTO operations VALUES (?, ?, ?, ?, ?)",
                (revision, command.principal, command.operation_key, digest, raw),
            )
            self._checkpoint("after_receipt")
            self._checkpoint("before_metadata")
            self._db.execute(
                "UPDATE metadata SET revision=?, record_count=?, payload_bytes=? "
                "WHERE singleton=1",
                (revision, len(candidate.records), size + sum(map(len, payloads))),
            )
            self._checkpoint("after_metadata")
            receipt = model.OperationReceipt(
                self.scope,
                command.principal,
                command.operation_key,
                digest,
                revision,
                tuple(r.envelope.record_id for r in command.records),
            )
            self._checkpoint("before_commit")
            commit_started = True
            self._db.commit()
            committed = True
            self._checkpoint("after_commit")
            return receipt
        except BaseException as exc:
            uncertain = commit_started and not self._db.in_transaction
            if self._db.in_transaction:
                self._db.rollback()
            if committed or uncertain:
                raise CommitUnknown("reconcile_original_key") from exc
            if isinstance(exc, sqlite3.Error):
                raise StoreUnavailable("append_storage_error") from exc
            raise
