"""Append-only, tamper-evident audit store (RFC-0013 §1, §11, §12, §21, §22;
RFC-0002 invariant 13; RFC-0004 A7, §9.12; AU4, AU5, AU8, AU13; DN-62).

Behavioral tests for Iteration 8 Commit C1 (`audit/store.py`): the
in-memory append-only store — append returns new immutable state, prior
records are never mutated or erased (AU4), ordering is deterministic (AU5),
a deterministic structural chain binds each record to its predecessor so a
silent edit is detected (tamper-evidence), the §11 lifecycle (Empty →
Recording → Degraded → Recovering) with the §12 legal transitions (Degraded
→ consequence proceeds is illegal), AU8 fail-closed (a failed or refused
write moves the store to Degraded and is disclosed), §22 reconciliation
(a lost write is recorded as failed-to-record, never invented; AU13), and
the lookup/iteration helpers. Durable backing, retention, deletion, and
export remain deferred to RFC-0020 (DN-62).
"""

import dataclasses
import pathlib
from datetime import datetime

import pytest

from episky.audit.records import (
    ApprovalDecision,
    ApprovalRecord,
    ExecutionPhase,
    ExecutionRecord,
    RecordCategory,
)
from episky.audit.store import AuditStore, StoreStatus

STORE_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "audit"
    / "store.py"
)

NOW = datetime(2026, 8, 7, 12, 0, 0)


def _execution(record_id="rec-1", phase=ExecutionPhase.START):
    return ExecutionRecord(
        record_id=record_id,
        recorded_at=NOW,
        category=RecordCategory.EXECUTION,
        phase=phase,
        action_id="action-1",
        argv=("ls", "-l"),
        machine_state="snapshot-1",
    )


def _recording_store():
    return AuditStore().begin_recording()


def _two_record_store():
    return (
        _recording_store()
        .append(_execution("rec-1"))
        .append(_execution("rec-2", phase=ExecutionPhase.END))
    )


# --- Lifecycle: Empty → Recording → Degraded → Recovering (RFC-0013 §11) ---


def test_a_fresh_store_is_empty_with_no_records():
    store = AuditStore()
    assert store.status is StoreStatus.EMPTY
    assert len(store) == 0
    assert store.records == ()
    assert store.chain == ()
    assert store.disclosure is None


def test_begin_recording_moves_empty_to_recording():
    store = _recording_store()
    assert store.status is StoreStatus.RECORDING
    assert len(store) == 0


def test_begin_recording_is_illegal_from_recording():
    with pytest.raises(ValueError):
        _recording_store().begin_recording()


def test_begin_recording_is_illegal_from_degraded():
    with pytest.raises(ValueError):
        AuditStore().append(_execution()).begin_recording()


def test_status_vocabulary_is_exactly_the_s11_states_this_layer_implements():
    assert tuple(StoreStatus) == (
        StoreStatus.EMPTY,
        StoreStatus.RECORDING,
        StoreStatus.DEGRADED,
        StoreStatus.RECOVERING,
    )


# --- Append-only: append returns new immutable state (AU4, AU5) ---


def test_append_returns_a_new_store_and_leaves_the_receiver_unchanged():
    original = _recording_store()
    successor = original.append(_execution())
    assert len(successor) == 1
    assert len(original) == 0  # the receiver is untouched
    assert original is not successor


def test_append_extends_records_and_chain_in_order():
    store = _two_record_store()
    assert len(store) == 2
    assert store.records == (
        _execution("rec-1"),
        _execution("rec-2", phase=ExecutionPhase.END),
    )
    assert len(store.chain) == 2
    assert store.status is StoreStatus.RECORDING


def test_append_only_exists_no_delete_no_overwrite_no_mutation():
    surface = {name for name in dir(AuditStore) if not name.startswith("_")}
    assert "delete" not in surface
    assert "clear" not in surface
    assert "remove" not in surface
    assert "overwrite" not in surface
    assert "edit" not in surface


def test_records_are_immutable_after_append():
    store = _two_record_store()
    with pytest.raises(AttributeError):
        store.records[0].argv = ("rm", "-rf")
    assert store.records[0].argv == ("ls", "-l")


def test_identical_appends_yield_identical_stores_deterministically():
    a = _recording_store().append(_execution("rec-1"))
    b = _recording_store().append(_execution("rec-1"))
    assert a == b
    assert a.chain == b.chain


def test_the_same_record_sequence_reproduces_the_same_chain():
    one = (
        _recording_store()
        .append(_execution("rec-1"))
        .append(_execution("rec-2", phase=ExecutionPhase.END))
    )
    two = (
        _recording_store()
        .append(_execution("rec-1"))
        .append(_execution("rec-2", phase=ExecutionPhase.END))
    )
    assert one.chain == two.chain


# --- Record-before-consequence and deterministic ordering (I-13) ---


def test_start_is_recorded_before_end():
    store = _two_record_store()
    assert store.record_at(0).phase is ExecutionPhase.START
    assert store.record_at(1).phase is ExecutionPhase.END
    assert store.record_at(0).record_id < store.record_at(1).record_id


def test_append_order_is_deterministic_across_categories():
    store = (
        _recording_store()
        .append(_execution("rec-1"))
        .append(
            ApprovalRecord(
                "rec-2",
                NOW,
                RecordCategory.APPROVAL,
                ApprovalDecision.APPROVAL,
                "action-2",
            )
        )
        .append(_execution("rec-3", phase=ExecutionPhase.END))
    )
    assert [r.record_id for r in store] == ["rec-1", "rec-2", "rec-3"]
    assert [r.category for r in store] == [
        RecordCategory.EXECUTION,
        RecordCategory.APPROVAL,
        RecordCategory.EXECUTION,
    ]


def test_a_consequence_never_proceeds_unrecorded_on_a_failed_store():
    store = _two_record_store().fail("the write was lost")
    refused = store.append(_execution("rec-3"))
    assert refused.status is StoreStatus.DEGRADED
    assert len(refused) == 2  # rec-3 never entered the record


# --- Refused writes move the store to Degraded (AU8) ---


def test_append_before_recording_is_refused_and_disclosed():
    refused = AuditStore().append(_execution())
    assert refused.status is StoreStatus.DEGRADED
    assert refused.disclosure is not None
    assert len(refused) == 0


def test_append_of_a_non_record_is_refused_and_disclosed():
    refused = _recording_store().append("not an audit record")
    assert refused.status is StoreStatus.DEGRADED
    assert refused.disclosure is not None
    assert len(refused) == 0


def test_append_of_a_duplicate_record_id_is_refused():
    store = _recording_store().append(_execution("rec-1"))
    refused = store.append(_execution("rec-1"))
    assert refused.status is StoreStatus.DEGRADED
    assert refused.disclosure is not None
    assert len(refused) == 1


def test_refused_write_keeps_prior_records_intact():
    store = _two_record_store()
    refused = store.append(_execution("rec-1"))
    assert refused.records == store.records
    assert refused.chain == store.chain


# --- Degraded → consequence proceeds is illegal (RFC-0013 §12; RFC-0004 §9.12) ---


def test_append_while_degraded_is_refused_and_stays_degraded():
    degraded = _recording_store().fail("write failed")
    refused = degraded.append(_execution("rec-1"))
    assert refused.status is StoreStatus.DEGRADED
    assert refused.disclosure is not None
    assert len(refused) == 0


def test_fail_moves_recording_to_degraded_with_a_disclosure():
    store = _two_record_store().fail("the backing write was lost")
    assert store.status is StoreStatus.DEGRADED
    assert store.disclosure == "the backing write was lost"
    assert store.records == _two_record_store().records


def test_fail_is_illegal_from_empty_and_degraded():
    with pytest.raises(ValueError):
        AuditStore().fail("boom")
    with pytest.raises(ValueError):
        _recording_store().fail("boom").fail("boom again")


def test_fail_requires_a_non_empty_message():
    with pytest.raises(ValueError):
        _recording_store().fail("")
    with pytest.raises(ValueError):
        _recording_store().fail("   ")


# --- Tamper-evidence (RFC-0001 §8.10; AU4) ---


def test_the_chain_binds_each_record_to_its_predecessor():
    store = _two_record_store()
    assert store.verify() is True


def test_editing_a_prior_record_is_detected():
    store = _two_record_store()
    tampered = dataclasses.replace(store.records[1], argv=("rm", "-rf", "/"))
    forged = dataclasses.replace(store, records=(store.records[0], tampered))
    assert forged.verify() is False


def test_editing_the_first_record_is_detected():
    store = _two_record_store()
    tampered = dataclasses.replace(store.records[0], action_id="a-different-action")
    forged = dataclasses.replace(store, records=(tampered, store.records[1]))
    assert forged.verify() is False


def test_dropping_a_record_is_detected():
    store = _two_record_store()
    truncated = dataclasses.replace(store, records=store.records[:1])
    assert truncated.verify() is False


# --- §22 reconciliation: failed-to-record, never invented (AU13) ---


def test_recover_moves_degraded_to_recovering():
    degraded = _recording_store().append(_execution()).fail("write lost")
    recovering = degraded.recover()
    assert recovering.status is StoreStatus.RECOVERING
    assert recovering.disclosure == "write lost"


def test_recover_is_illegal_from_recording_and_recovering():
    with pytest.raises(ValueError):
        _recording_store().recover()
    with pytest.raises(ValueError):
        _recording_store().append(_execution()).fail("x").recover().recover()


def test_reconcile_returns_to_recording_and_keeps_the_failed_to_record():
    store = _recording_store().append(_execution("rec-1"))
    degraded = store.fail("the write of the outcome was lost")
    reconciled = degraded.recover().reconcile()
    assert reconciled.status is StoreStatus.RECORDING
    assert reconciled.disclosure == "the write of the outcome was lost"
    assert reconciled.records == store.records  # nothing invented
    assert reconciled.chain == store.chain


def test_reconcile_is_illegal_from_recording_and_degrated():
    with pytest.raises(ValueError):
        _recording_store().reconcile()
    with pytest.raises(ValueError):
        _recording_store().append(_execution()).fail("x").reconcile()


def test_after_reconciliation_writes_resume():
    store = _recording_store().append(_execution("rec-1")).fail("lost")
    recovered = store.recover().reconcile()
    resumed = recovered.append(_execution("rec-2"))
    assert resumed.status is StoreStatus.RECORDING
    assert len(resumed) == 2
    assert resumed.verify() is True


def test_reconciliation_never_resurrects_deleted_records():
    store = _two_record_store()
    reconciled = store.fail("lost").recover().reconcile()
    assert len(reconciled) == len(store)
    assert all(original in reconciled.records for original in store.records)


# --- Lookup and iteration helpers (RFC-0013 §13.1) ---


def test_len_and_iteration_preserve_append_order():
    store = _two_record_store()
    assert len(store) == 2
    assert list(store) == [store.records[0], store.records[1]]


def test_record_at_returns_the_positional_record():
    store = _two_record_store()
    assert store.record_at(0).record_id == "rec-1"
    assert store.record_at(1).record_id == "rec-2"


def test_record_at_is_fail_closed_out_of_range():
    with pytest.raises(IndexError):
        _two_record_store().record_at(2)


def test_by_id_returns_the_immutable_identifier():
    store = _two_record_store()
    assert store.by_id("rec-2").phase is ExecutionPhase.END
    assert store.by_id("missing") is None


def test_by_category_preserves_order():
    store = (
        _recording_store()
        .append(_execution("rec-1"))
        .append(
            ApprovalRecord(
                "rec-2",
                NOW,
                RecordCategory.APPROVAL,
                ApprovalDecision.AUTO_PERMIT,
                "action-2",
            )
        )
        .append(_execution("rec-3", phase=ExecutionPhase.END))
    )
    executions = store.by_category(RecordCategory.EXECUTION)
    assert [r.record_id for r in executions] == ["rec-1", "rec-3"]
    assert [r.category for r in store.by_category(RecordCategory.APPROVAL)] == [
        RecordCategory.APPROVAL
    ]
    assert store.by_category(RecordCategory.OVERRIDE) == ()


def test_latest_returns_the_most_recent_record():
    assert _two_record_store().latest().record_id == "rec-2"
    assert _recording_store().latest() is None


# --- Time, randomness, and state contracts ---


def test_store_py_never_reads_a_clock():
    src = STORE_PATH.read_text(encoding="utf-8")
    for token in (
        "datetime.now",
        "utcnow",
        "datetime.today",
        "time.time",
        "time.monotonic",
        "perf_counter",
        "import time",
        "from time import",
    ):
        assert token not in src


def test_store_py_never_hashes_or_generates_randomness():
    src = STORE_PATH.read_text(encoding="utf-8")
    for token in (
        "import random",
        "os.urandom",
        "import uuid",
        "uuid4",
        "import hmac",
        "import hashlib",
        "import secrets",
        "secrets.token",
    ):
        assert token not in src


def test_store_state_is_public_and_explicit_no_hidden_state():
    store = _two_record_store()
    assert store.status is StoreStatus.RECORDING
    assert isinstance(store.records, tuple)
    assert isinstance(store.chain, tuple)
    assert store.disclosure is None
    assert not hasattr(store, "_records")
    assert not hasattr(store, "_chain")


def test_every_store_transition_returns_a_fresh_frozen_value():
    store = AuditStore()
    recording = store.begin_recording()
    one = recording.append(_execution())
    degraded = one.fail("x")
    recovering = degraded.recover()
    reconciled = recovering.reconcile()
    assert recording is not store
    assert one is not recording
    assert degraded is not one
    assert recovering is not degraded
    assert reconciled is not recovering
    assert store.status is StoreStatus.EMPTY  # the receiver never changed
    assert recording.status is StoreStatus.RECORDING
    assert reconciled.status is StoreStatus.RECORDING


def test_append_requires_a_real_audit_record():
    refused = _recording_store().append(object())
    assert refused.status is StoreStatus.DEGRADED
    assert refused.disclosure is not None
