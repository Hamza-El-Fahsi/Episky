"""Immutable audit record categories (RFC-0013 §7, §9, §31; RFC-0004 §4.12;
AU4, AU5, AU7; DN-63).

Behavioral tests for Iteration 8 Commit C1 (`audit/records.py`): the
canonical record types for this layer's boundaries — execution (cat. 6),
secret-metadata on `secrets` *metadata* types (cat. 10, SC4), and the
approval / auto-permit / rejection and override records (cat. 4/5, DN-50).
Each record is immutable (frozen + slots), category-carrying, carries an
explicit caller-supplied timestamp and an immutable caller-supplied
identifier, is value-free by construction (no value-shaped field, SC4/AU7),
and records deterministically (AU5): identical arguments yield identical
records. The `schema` edge stays latent (DN-44 precedent); the only
cross-package import is `secrets` metadata types (blueprint §4.2).
"""

import ast
import importlib
import pathlib
from datetime import datetime

import pytest

from episky.audit.records import (
    ApprovalDecision,
    ApprovalRecord,
    AuditRecord,
    ExecutionPhase,
    ExecutionRecord,
    OverrideRecord,
    RecordCategory,
    SecretEvent,
    SecretMetadataRecord,
)
from episky.secrets.classify import SecretMetadata

RECORDS_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "audit"
    / "records.py"
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


def _secret_record():
    return SecretMetadataRecord(
        record_id="rec-secret-1",
        recorded_at=NOW,
        category=RecordCategory.SECRET_METADATA,
        event=SecretEvent.USED,
        handle="provider-key",
        metadata=SecretMetadata(existence=True, provider="ollama"),
    )


def _approval():
    return ApprovalRecord(
        record_id="rec-approval-1",
        recorded_at=NOW,
        category=RecordCategory.APPROVAL,
        decision=ApprovalDecision.APPROVAL,
        action_id="action-2",
        risk_class="consequential",
        gate="confirm",
    )


def _override():
    return OverrideRecord(
        record_id="rec-override-1",
        recorded_at=NOW,
        category=RecordCategory.OVERRIDE,
        action_id="action-3",
        reason="explicit operator override of the blocked Action",
        risk_class="destructive",
        gate="blocked",
    )


# --- Immutability and structure (AU4; RFC-0004 §4.12) ---


def test_every_record_type_is_a_frozen_slotted_dataclass():
    for cls in (
        AuditRecord,
        ExecutionRecord,
        SecretMetadataRecord,
        ApprovalRecord,
        OverrideRecord,
    ):
        params = cls.__dataclass_params__
        assert params.frozen, f"{cls.__name__} is not frozen"
        assert params.slots, f"{cls.__name__} is not slot-based"


def test_records_are_immutable():
    rec = _execution()
    with pytest.raises(AttributeError):
        rec.action_id = "mutated"
    with pytest.raises(AttributeError):
        rec.category = RecordCategory.APPROVAL


def test_an_edited_record_is_a_new_record_not_a_mutation():
    rec = _execution()
    replaced = rec.__class__(
        record_id="rec-2",
        recorded_at=rec.recorded_at,
        category=rec.category,
        phase=rec.phase,
        action_id=rec.action_id,
        argv=rec.argv,
        machine_state=rec.machine_state,
    )
    assert replaced.record_id == "rec-2"
    assert rec.record_id == "rec-1"  # the original is unchanged


def test_records_support_structural_equality_only_via_frozen_fields():
    assert _execution() == _execution()
    assert _execution() != _execution(phase=ExecutionPhase.END)


# --- Category carrying (RFC-0013 §7; DN-63) ---


def test_each_record_carries_its_owned_category():
    assert _execution().category is RecordCategory.EXECUTION
    assert _secret_record().category is RecordCategory.SECRET_METADATA
    assert _approval().category is RecordCategory.APPROVAL
    assert _override().category is RecordCategory.OVERRIDE


def test_record_category_is_exactly_this_layers_boundaries():
    assert tuple(RecordCategory) == (
        RecordCategory.APPROVAL,
        RecordCategory.OVERRIDE,
        RecordCategory.EXECUTION,
        RecordCategory.SECRET_METADATA,
    )


def test_every_concrete_record_is_an_audit_record():
    for record in (_execution(), _secret_record(), _approval(), _override()):
        assert isinstance(record, AuditRecord)


# --- Explicit timestamps and identifiers (no clock, no generation) ---


def test_record_carries_the_explicit_caller_timestamp():
    rec = _execution()
    assert rec.recorded_at == NOW


def test_record_carries_the_explicit_caller_identifier():
    rec = _execution()
    assert rec.record_id == "rec-1"
    assert rec.action_id == "action-1"


def test_records_py_never_reads_a_clock():
    src = RECORDS_PATH.read_text(encoding="utf-8")
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


def test_records_py_generates_no_identifier_or_randomness():
    src = RECORDS_PATH.read_text(encoding="utf-8")
    for token in (
        "import random",
        "random.",
        "os.urandom",
        "import uuid",
        "uuid4",
        "import hmac",
        "import hashlib",
    ):
        assert token not in src


# --- Determinism (AU5) ---


def test_identical_arguments_yield_identical_records():
    assert _execution() == _execution()
    assert _approval() == _approval()
    assert _secret_record() == _secret_record()
    assert _override() == _override()


def test_differing_timestamps_differ_only_in_time():
    rec = _execution()
    later = rec.__class__(
        record_id=rec.record_id,
        recorded_at=datetime(2026, 8, 7, 12, 0, 1),
        category=rec.category,
        phase=rec.phase,
        action_id=rec.action_id,
        argv=rec.argv,
        machine_state=rec.machine_state,
    )
    assert later.recorded_at == datetime(2026, 8, 7, 12, 0, 1)
    assert rec.recorded_at == NOW


# --- SC4 / AU7: no secret value, no value-shaped field ---


def test_execution_record_carries_sanitized_argv_not_a_shell_string():
    rec = _execution()
    assert rec.argv == ("ls", "-l")
    assert isinstance(rec.argv, tuple)


def test_secret_record_carries_only_secrets_metadata_types():
    rec = _secret_record()
    assert isinstance(rec.metadata, SecretMetadata)
    assert rec.metadata.existence is True
    assert rec.metadata.provider == "ollama"
    assert not hasattr(rec, "value")
    assert not hasattr(rec, "content")


def test_secret_record_metadata_is_value_free():
    rec = _secret_record()
    secret_value = "sk-provisioned-test-value"
    assert secret_value not in repr(rec)
    assert secret_value not in repr(rec.metadata)


def test_no_record_has_a_value_shaped_field():
    value_shaped = {"content", "value", "secret", "raw", "material", "payload"}
    for cls in (ExecutionRecord, SecretMetadataRecord, ApprovalRecord, OverrideRecord):
        fields = set(cls.__dataclass_fields__)
        assert not (value_shaped & fields), f"{cls.__name__} carries a value field"


# --- The four record shapes (RFC-0013 §7 cat. 4, 5, 6, 10) ---


def test_execution_phase_is_start_then_end():
    assert tuple(ExecutionPhase) == (ExecutionPhase.START, ExecutionPhase.END)


def test_execution_record_holds_phase_action_and_machine_state():
    rec = _execution()
    assert rec.phase is ExecutionPhase.START
    assert rec.action_id == "action-1"
    assert rec.machine_state == "snapshot-1"


def test_secret_event_covers_the_s31_lifecycle():
    assert tuple(SecretEvent) == (
        SecretEvent.PROVISIONED,
        SecretEvent.USED,
        SecretEvent.INVALIDATED,
        SecretEvent.DESTROYED,
        SecretEvent.EXPOSED,
        SecretEvent.VISIBILITY_REQUEST,
    )


def test_approval_decision_covers_issuance_auto_permit_and_rejection():
    assert tuple(ApprovalDecision) == (
        ApprovalDecision.APPROVAL,
        ApprovalDecision.AUTO_PERMIT,
        ApprovalDecision.REJECTION,
    )


def test_approval_record_carries_decision_and_canonical_labels():
    rec = _approval()
    assert rec.decision is ApprovalDecision.APPROVAL
    assert rec.risk_class == "consequential"
    assert rec.gate == "confirm"


def test_override_record_carries_the_explicit_reason():
    rec = _override()
    assert rec.category is RecordCategory.OVERRIDE
    assert "explicit operator override" in rec.reason


# --- Public surface and dependency contracts ---


def test_records_public_surface_is_exactly_the_owned_vocabulary():
    mod = importlib.import_module("episky.audit.records")
    assert set(mod.__all__) == {
        "ApprovalDecision",
        "ApprovalRecord",
        "AuditRecord",
        "ExecutionPhase",
        "ExecutionRecord",
        "OverrideRecord",
        "RecordCategory",
        "SecretEvent",
        "SecretMetadataRecord",
    }


def test_records_imports_only_stdlib_and_secrets_metadata_types():
    tree = ast.parse(RECORDS_PATH.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    episky_imports = [name for name in imported if name.startswith("episky")]
    assert episky_imports == ["episky.secrets.classify"]
    assert all(not name.startswith("episky.schema") for name in imported)


def test_records_py_calls_no_forbidden_io_builtin():
    tree = ast.parse(RECORDS_PATH.read_text(encoding="utf-8"))
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            calls.add(func.id if isinstance(func, ast.Name) else func.attr)
    assert calls.isdisjoint({"open", "print", "input", "exec", "eval", "breakpoint"})
