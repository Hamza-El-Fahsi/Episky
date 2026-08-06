"""Secure Store abstraction (RFC-0009 §4–§12, §15, §28; SC1, SC6, SC7,
SC8, SC12, SC15; DN-41).

Behavioral tests for Iteration 6 Commit C3 (`secrets/store.py`): the
Secure Store abstraction over in-memory, metadata-only records — the
provision / consume-at-boundary / invalidate / destroy lifecycle, the
owner/custody split (SC8), purpose-scoping (SC7), the closed consumer
set (SC6/SC8), the value-at-the-consume-boundary-only property (SC1),
destruction that removes the value and the record (SC12), exposure =
compromise invalidation (SC15), deterministic lifecycle, metadata-only
records that never expose a value, and the ownership, dependency,
immutability, and no-forbidden-behaviour contracts.
"""

import ast
import importlib
import pathlib
import sys
from datetime import date

import pytest

from episky.secrets.classify import SecrecyClass, SecretOrigin
from episky.secrets.store import (
    OPERATOR_OWNER,
    SECURE_STORE_CUSTODIAN,
    Consumer,
    Consumption,
    Destruction,
    Provision,
    SecretRecord,
    SecureStore,
    StoreStatus,
)

STORE_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "secrets"
    / "store.py"
)

# The owned public surface of store.py.
EXPECTED_PUBLIC_SURFACE = {
    "Consumer",
    "Consumption",
    "Destruction",
    "OPERATOR_OWNER",
    "Provision",
    "SECURE_STORE_CUSTODIAN",
    "SecretRecord",
    "SecureStore",
    "StoreStatus",
}

PURPOSE = "authenticate the provider view"
VALUE = "sk-provisioned-test-value"


def _store_with(handle="provider-key", value=VALUE, purpose=PURPOSE):
    store = SecureStore()
    provision = store.provision(handle, value, purpose, date(2026, 8, 6))
    return store, provision


# --- Status and consumer vocabulary (SC6, SC8; RFC-0009 §8) ---


def test_store_status_has_exactly_ok_and_refused():
    assert tuple(StoreStatus) == (StoreStatus.OK, StoreStatus.REFUSED)


def test_the_consumer_set_is_exactly_the_provider_adapter():
    assert tuple(Consumer) == (Consumer.PROVIDER_ADAPTER,)


# --- Provision (SC7, SC8; RFC-0009 §5.1, §7) ---


def test_provision_records_metadata_only_and_never_the_value():
    store, provision = _store_with()
    assert provision.status is StoreStatus.OK
    assert provision.reason
    assert provision.handle == "provider-key"
    assert provision.record.handle == "provider-key"
    assert provision.record.purpose == PURPOSE
    assert VALUE not in repr(provision)
    assert VALUE not in repr(provision.record)


def test_provisioned_secret_is_classified_secret_and_provisioned():
    store, provision = _store_with()
    assert provision.record.classification.secrecy_class is SecrecyClass.SECRET
    assert provision.record.classification.origin is SecretOrigin.PROVISIONED
    assert provision.record.classification.metadata.existence is True


def test_provision_records_the_provider_in_the_metadata():
    store = SecureStore()
    provision = store.provision(
        "k", VALUE, PURPOSE, date(2026, 8, 6), provider="ollama"
    )
    assert provision.record.classification.metadata.provider == "ollama"


def test_provision_binds_the_stated_purpose():
    store, provision = _store_with()
    assert provision.record.purpose == PURPOSE


def test_provision_rejects_an_empty_handle():
    with pytest.raises(ValueError):
        SecureStore().provision("", VALUE, PURPOSE, date(2026, 8, 6))


def test_provision_rejects_an_empty_value():
    with pytest.raises(ValueError):
        SecureStore().provision("k", "", PURPOSE, date(2026, 8, 6))


def test_provision_rejects_an_empty_purpose():
    with pytest.raises(ValueError):
        SecureStore().provision("k", VALUE, "", date(2026, 8, 6))


def test_provision_rejects_a_duplicate_handle():
    store = SecureStore()
    store.provision("k", VALUE, PURPOSE, date(2026, 8, 6))
    with pytest.raises(ValueError):
        store.provision("k", "another value", "another purpose", date(2026, 8, 6))


def test_multiple_secrets_are_keyed_independently_by_opaque_handle():
    store = SecureStore()
    store.provision("a-key", "value-a", PURPOSE, date(2026, 8, 6))
    store.provision("b-key", "value-b", PURPOSE, date(2026, 8, 6))
    a = store.consume("a-key", Consumer.PROVIDER_ADAPTER, PURPOSE, date(2026, 8, 7))
    b = store.consume("b-key", Consumer.PROVIDER_ADAPTER, PURPOSE, date(2026, 8, 7))
    assert a.value == "value-a"
    assert b.value == "value-b"
    assert len(store.records()) == 2


# --- Custody (SC1): a value exists only in the store's custody ---


def test_the_metadata_view_never_carries_a_value():
    store, _ = _store_with()
    rendered = "".join(repr(r) for r in store.records())
    assert VALUE not in rendered
    assert "sk-provisioned" not in rendered


def test_provisioned_values_cannot_be_reconstructed_from_records():
    store, _ = _store_with()
    for record in store.records():
        assert record.classification.metadata.existence is True
        assert record.classification.metadata.provider is None


def test_values_are_never_exposed_anywhere_but_consume():
    store, provision = _store_with()
    assert VALUE not in repr(provision)
    assert all(VALUE not in repr(r) for r in store.records())
    result = store.consume(
        "provider-key", Consumer.PROVIDER_ADAPTER, PURPOSE, date(2026, 8, 7)
    )
    assert result.value == VALUE
    assert VALUE not in result.reason
    assert VALUE not in repr(result.consumed_on)
    assert all(VALUE not in repr(r) for r in store.records())


# --- Consume (SC6, SC7, SC8; RFC-0009 §8) ---


def test_consume_materializes_the_value_at_the_named_boundary():
    store, _ = _store_with()
    result = store.consume(
        "provider-key", Consumer.PROVIDER_ADAPTER, PURPOSE, date(2026, 8, 7)
    )
    assert result.status is StoreStatus.OK
    assert result.value == VALUE
    assert result.consumer is Consumer.PROVIDER_ADAPTER
    assert result.purpose == PURPOSE
    assert result.reason


def test_consume_records_last_use_as_metadata_only():
    store, _ = _store_with()
    store.consume("provider-key", Consumer.PROVIDER_ADAPTER, PURPOSE, date(2026, 8, 7))
    record = store.records()[0]
    assert record.last_used_on == date(2026, 8, 7)
    assert record.provisioned_on == date(2026, 8, 6)
    assert record.last_used_on is not None


def test_consume_never_exposes_plaintext_beyond_the_boundary():
    store, _ = _store_with()
    result = store.consume(
        "provider-key", Consumer.PROVIDER_ADAPTER, PURPOSE, date(2026, 8, 7)
    )
    assert result.value == VALUE
    assert VALUE not in repr(result.reason)
    assert VALUE not in repr(result.consumed_on)
    assert all(VALUE not in repr(r) for r in store.records())
    invalidation = store.invalidate("provider-key", "test", date(2026, 8, 8))
    assert VALUE not in repr(invalidation)
    destruction = store.destroy("provider-key", "test", date(2026, 8, 9))
    assert VALUE not in repr(destruction)


def test_consume_unknown_handle_is_refused_and_nothing_crosses():
    store, _ = _store_with()
    result = store.consume(
        "missing", Consumer.PROVIDER_ADAPTER, PURPOSE, date(2026, 8, 7)
    )
    assert result.status is StoreStatus.REFUSED
    assert result.value == ""
    assert result.reason


def test_consume_for_a_purpose_other_than_the_bound_one_is_refused():
    store, _ = _store_with()
    result = store.consume(
        "provider-key", Consumer.PROVIDER_ADAPTER, "some other use", date(2026, 8, 7)
    )
    assert result.status is StoreStatus.REFUSED
    assert result.value == ""
    assert result.reason


def test_consume_by_any_consumer_other_than_the_provider_adapter_is_refused():
    store, _ = _store_with()
    for other in ("skill", "diagnostics", "audit", "fact-layer"):
        result = store.consume("provider-key", other, PURPOSE, date(2026, 8, 7))
        assert result.status is StoreStatus.REFUSED
        assert result.value == ""
        assert result.reason


# --- Invalidate (RFC-0009 §6; SC15) ---


def test_invalidate_marks_the_record_and_records_when():
    store, _ = _store_with()
    result = store.invalidate(
        "provider-key", "revoked by the Operator", date(2026, 8, 8)
    )
    assert result.status is StoreStatus.OK
    assert result.invalidated_on == date(2026, 8, 8)
    assert result.destroyed_on is None
    record = store.records()[0]
    assert record.invalidated_on == date(2026, 8, 8)


def test_an_invalidated_secret_is_refused_at_every_boundary():
    store, _ = _store_with()
    store.invalidate("provider-key", "revoked", date(2026, 8, 8))
    result = store.consume(
        "provider-key", Consumer.PROVIDER_ADAPTER, PURPOSE, date(2026, 8, 9)
    )
    assert result.status is StoreStatus.REFUSED
    assert result.value == ""


def test_invalidate_unknown_handle_is_refused():
    store, _ = _store_with()
    result = store.invalidate("missing", "test", date(2026, 8, 8))
    assert result.status is StoreStatus.REFUSED
    assert result.reason


def test_invalidate_an_invalidated_secret_is_refused_not_silently_repeated():
    store, _ = _store_with()
    store.invalidate("provider-key", "first", date(2026, 8, 8))
    second = store.invalidate("provider-key", "second", date(2026, 8, 9))
    assert second.status is StoreStatus.REFUSED
    assert second.reason
    assert second.invalidated_on == date(2026, 8, 8)


def test_invalidate_requires_a_non_empty_reason():
    store, _ = _store_with()
    with pytest.raises(ValueError):
        store.invalidate("provider-key", "", date(2026, 8, 8))


def test_suspected_exposure_invalidates_immediately_and_destroys():
    store, _ = _store_with()
    exposure = store.invalidate(
        "provider-key",
        "suspected exposure (RFC-0009 §13.4, §15; SC15)",
        date(2026, 8, 7),
    )
    assert exposure.status is StoreStatus.OK
    assert exposure.invalidated_on == date(2026, 8, 7)
    refused = store.consume(
        "provider-key", Consumer.PROVIDER_ADAPTER, PURPOSE, date(2026, 8, 7)
    )
    assert refused.status is StoreStatus.REFUSED
    assert refused.value == ""
    destruction = store.destroy(
        "provider-key",
        "suspected exposure (RFC-0009 §13.4, §15; SC15)",
        date(2026, 8, 7),
    )
    assert destruction.status is StoreStatus.OK
    assert store.records() == ()
    assert destruction.invalidated_on == date(2026, 8, 7)


# --- Destroy (SC12; RFC-0009 §12) ---


def test_destroy_removes_the_value_and_the_record():
    store, _ = _store_with()
    result = store.destroy("provider-key", "purpose lapsed", date(2026, 8, 9))
    assert result.status is StoreStatus.OK
    assert result.destroyed_on == date(2026, 8, 9)
    assert store.records() == ()


def test_destroyed_secrets_are_invalidated_for_every_operation():
    store, _ = _store_with()
    store.destroy("provider-key", "test", date(2026, 8, 9))
    assert store.records() == ()
    consume = store.consume(
        "provider-key", Consumer.PROVIDER_ADAPTER, PURPOSE, date(2026, 8, 9)
    )
    assert consume.status is StoreStatus.REFUSED
    assert consume.value == ""
    assert (
        store.invalidate("provider-key", "test", date(2026, 8, 9)).status
        is StoreStatus.REFUSED
    )
    assert (
        store.destroy("provider-key", "test", date(2026, 8, 9)).status
        is StoreStatus.REFUSED
    )


def test_destroy_is_recorded_never_the_value():
    store, _ = _store_with()
    result = store.destroy("provider-key", "rotated", date(2026, 8, 9))
    assert result.reason == "rotated"
    assert result.destroyed_on == date(2026, 8, 9)
    assert VALUE not in repr(result)


def test_destroy_unknown_handle_is_refused():
    store, _ = _store_with()
    result = store.destroy("missing", "test", date(2026, 8, 9))
    assert result.status is StoreStatus.REFUSED
    assert result.reason


def test_destroy_requires_a_non_empty_reason():
    store, _ = _store_with()
    with pytest.raises(ValueError):
        store.destroy("provider-key", "", date(2026, 8, 9))


# --- Fail-closed posture (RFC-0009 §13): unknown never silently succeeds ---


@pytest.mark.parametrize("op", ["consume", "invalidate", "destroy"])
def test_unknown_handles_are_never_silently_succeeded(op):
    store = SecureStore()
    if op == "consume":
        result = store.consume(
            "nope", Consumer.PROVIDER_ADAPTER, PURPOSE, date(2026, 8, 7)
        )
    elif op == "invalidate":
        result = store.invalidate("nope", "test", date(2026, 8, 7))
    else:
        result = store.destroy("nope", "test", date(2026, 8, 7))
    assert result.status is StoreStatus.REFUSED
    assert result.reason


# --- Ownership (SC8; RFC-0009 §4) ---


def test_every_record_has_exactly_one_owner_and_one_custodian():
    store = SecureStore()
    for handle in ("one", "two"):
        store.provision(handle, VALUE, PURPOSE, date(2026, 8, 6))
    assert OPERATOR_OWNER != SECURE_STORE_CUSTODIAN
    for record in store.records():
        assert record.owner == OPERATOR_OWNER
        assert record.custodian == SECURE_STORE_CUSTODIAN
        assert record.owner != record.custodian


# --- Determinism (SC13; RFC-0007 S7) ---


def test_the_lifecycle_is_deterministic_across_stores():
    def run():
        store = SecureStore()
        store.provision("k", VALUE, PURPOSE, date(2026, 8, 6))
        consume = store.consume(
            "k", Consumer.PROVIDER_ADAPTER, PURPOSE, date(2026, 8, 7)
        )
        invalidate = store.invalidate("k", "test", date(2026, 8, 8))
        destroy = store.destroy("k", "test", date(2026, 8, 9))
        return consume, invalidate, destroy, store.records()

    assert run() == run()


def test_records_are_sorted_by_handle_deterministically():
    store = SecureStore()
    for handle in ("zeta", "alpha", "mid"):
        store.provision(handle, VALUE, PURPOSE, date(2026, 8, 6))
    assert [record.handle for record in store.records()] == ["alpha", "mid", "zeta"]


def test_stores_are_independent_instances():
    first, _ = _store_with()
    second = SecureStore()
    assert first.records()
    assert second.records() == ()
    second.provision("other", VALUE, "other purpose", date(2026, 8, 6))
    assert len(first.records()) == 1
    assert len(second.records()) == 1
    first.destroy("provider-key", "test", date(2026, 8, 6))
    assert first.records() == ()
    assert len(second.records()) == 1


# --- Result and record contracts ---


def test_secret_record_carries_exactly_the_metadata_contract():
    fields = tuple(f.name for f in SecretRecord.__dataclass_fields__.values())
    assert fields == (
        "handle",
        "purpose",
        "owner",
        "custodian",
        "classification",
        "provisioned_on",
        "last_used_on",
        "invalidated_on",
    )


def test_provision_carries_exactly_the_result_contract():
    fields = tuple(f.name for f in Provision.__dataclass_fields__.values())
    assert fields == ("handle", "record", "status", "reason")


def test_consumption_carries_exactly_the_result_contract():
    fields = tuple(f.name for f in Consumption.__dataclass_fields__.values())
    assert fields == (
        "handle",
        "value",
        "status",
        "consumer",
        "purpose",
        "consumed_on",
        "reason",
    )


def test_destruction_carries_exactly_the_result_contract():
    fields = tuple(f.name for f in Destruction.__dataclass_fields__.values())
    assert fields == ("handle", "status", "reason", "invalidated_on", "destroyed_on")


# --- Immutability ---


def test_records_and_results_are_frozen_and_slotted():
    for record_type in (SecretRecord, Provision, Consumption, Destruction):
        assert record_type.__dataclass_params__.frozen
        assert record_type.__dataclass_params__.slots


def test_records_and_results_cannot_be_mutated():
    store, provision = _store_with()
    with pytest.raises(AttributeError):
        provision.record.purpose = "changed"
    result = store.consume(
        "provider-key", Consumer.PROVIDER_ADAPTER, PURPOSE, date(2026, 8, 7)
    )
    with pytest.raises(AttributeError):
        result.value = "changed"


# --- No forbidden runtime behaviour (DN-41; RFC-0009 §9) ---


def test_store_has_no_io_no_random_no_clock_no_persistence():
    src = STORE_PATH.read_text(encoding="utf-8")
    for token in (
        "import os",
        "import socket",
        "import urllib",
        "import requests",
        "import random",
        "import statistics",
        "import json",
        "import sqlite3",
        "import subprocess",
        "open(",
        "datetime.now",
        "date.today",
        "keyring",
        "vault",
        "SecretService",
        "dbus",
    ):
        assert token not in src


def test_store_has_no_forbidden_responsibility_surface():
    tree = ast.parse(STORE_PATH.read_text(encoding="utf-8"))
    identifiers = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.id, str)
    }
    assert identifiers.isdisjoint(
        {
            "sanitize",
            "redact",
            "detect",
            "summari",
            "promote",
            "quarantine",
            "executor",
            "runtime",
            "collect",
            "persist",
            "audit",
            "skills",
            "providers",
            "context",
            "verification",
            "factlayer",
            "policy",
            "schema",
        }
    ), "store.py names a responsibility it does not own"


def test_module_has_no_global_mutable_state():
    tree = ast.parse(STORE_PATH.read_text(encoding="utf-8"))
    assignments = [
        node
        for node in tree.body
        if isinstance(node, ast.Assign)
        and not (
            isinstance(node.targets[0], ast.Name)
            and node.targets[0].id
            in ("OPERATOR_OWNER", "SECURE_STORE_CUSTODIAN", "__all__")
        )
    ]
    assert not assignments, "store.py carries a global mutable state"


# --- Public surface and ownership (blueprint §10) ---


def test_public_surface_is_exactly_the_owned_vocabulary():
    module = importlib.import_module("episky.secrets.store")
    assert set(module.__all__) == EXPECTED_PUBLIC_SURFACE


def test_public_names_are_defined_by_store_py():
    module = importlib.import_module("episky.secrets.store")
    for name in EXPECTED_PUBLIC_SURFACE:
        value = getattr(module, name)
        if hasattr(value, "__module__"):
            assert value.__module__ == "episky.secrets.store"
        else:
            assert name in module.__dict__


def test_module_ownership_docstring_names_rfc_0009_and_dn_41():
    doc = importlib.import_module("episky.secrets.store").__doc__
    assert "RFC-0009" in doc
    assert "DN-41" in doc
    assert "metadata" in doc
    assert "deterministic" in doc.lower()


# --- Dependency rules (blueprint §4.1; DN-41) ---


def test_store_imports_only_stdlib_and_secrets_classify():
    tree = ast.parse(STORE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] in sys.stdlib_module_names
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                continue
            parts = node.module.split(".")
            if parts[0] == "episky":
                assert parts[1] == "secrets"
                assert parts[2:] == ["classify"]
            else:
                assert parts[0] in sys.stdlib_module_names
