"""Hostile quarantine and fail-closed behaviour (RFC-0007 §15, T11, T12).

Behavioral tests for Iteration 5 Commit C3 (`trust/hostile.py`): the
in-memory quarantine record (datum + class + reason + withheld/disclosed
state; Q8), fail-closed admission — only Hostile content is admitted,
never fabricated (DN-39) — the §15.5 excluded-from-Context/Provider-View
invariant (T11; RFC-0002 invariant 4), and T12's downward contagion
(§9.7) that never introduces Hostile. Nothing is persisted, executed,
or escalated.
"""

import ast
import importlib
import pathlib
import sys

import pytest

from episky.trust.classes import (
    Datum,
    ProvenanceState,
    TrustCategory,
    TrustClass,
    TrustDomain,
    classify,
)
from episky.trust.hostile import DisclosureState, Quarantine, contaminate, quarantine

HOSTILE_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "trust"
    / "hostile.py"
)

ALL_CLASSES = tuple(TrustClass)
NON_HOSTILE = tuple(c for c in ALL_CLASSES if c is not TrustClass.HOSTILE)

# The owned public surface of hostile.py.
EXPECTED_PUBLIC_SURFACE = {"DisclosureState", "Quarantine", "contaminate", "quarantine"}


def _datum(content="payload", provenance=ProvenanceState.LOST):
    return Datum(
        category=TrustCategory.LOGS,
        content=content,
        provenance=provenance,
        origin=TrustDomain.MACHINE,
    )


def _quarantine(reason="unclassifiable (RFC-0007 §15.5)"):
    return quarantine(_datum(), TrustClass.HOSTILE, reason)


# --- The quarantine record (Q8) ---


def test_quarantine_record_is_frozen_and_slotted():
    assert Quarantine.__dataclass_params__.frozen
    assert Quarantine.__dataclass_params__.slots


def test_quarantine_record_carries_the_datum_class_reason_and_disclosure():
    datum = _datum()
    record = quarantine(datum, TrustClass.HOSTILE, "unclassifiable (RFC-0007 §15.5)")
    assert record.datum == datum
    assert record.trust_class is TrustClass.HOSTILE
    assert record.reason == "unclassifiable (RFC-0007 §15.5)"
    assert record.disclosure is DisclosureState.DISCLOSED


def test_quarantine_record_cannot_be_mutated():
    record = _quarantine()
    with pytest.raises(AttributeError):
        record.reason = "changed"
    with pytest.raises(AttributeError):
        record.trust_class = TrustClass.UNTRUSTED


def test_disclosure_state_has_exactly_withheld_and_disclosed():
    assert tuple(DisclosureState) == (
        DisclosureState.WITHHELD,
        DisclosureState.DISCLOSED,
    )


# --- Admission semantics (fail-closed; §15.5, DN-39) ---


@pytest.mark.parametrize("cls", NON_HOSTILE)
def test_quarantine_rejects_non_hostile_admission(cls):
    with pytest.raises(ValueError):
        quarantine(_datum(), cls, "reason")


def test_quarantine_admits_hostile_content():
    record = _quarantine()
    assert record.trust_class is TrustClass.HOSTILE


def test_quarantine_rejects_an_empty_reason():
    with pytest.raises(ValueError):
        quarantine(_datum(), TrustClass.HOSTILE, "")


def test_quarantine_defaults_to_disclosed():
    record = _quarantine()
    assert record.disclosure is DisclosureState.DISCLOSED


def test_quarantine_honors_withheld_disclosure():
    record = quarantine(
        _datum(),
        TrustClass.HOSTILE,
        "sanitization failure (S6)",
        disclosure=DisclosureState.WITHHELD,
    )
    assert record.disclosure is DisclosureState.WITHHELD


def test_quarantine_never_fabricates_hostile():
    for cls in NON_HOSTILE:
        with pytest.raises(ValueError):
            quarantine(_datum(), cls, "reason")


def test_hostile_content_from_the_fail_closed_paths_is_admissible():
    datum = Datum(
        TrustCategory.OBSERVATION,
        "payload",
        ProvenanceState.LOST,
        TrustDomain.DIAGNOSTICS,
    )
    classification = classify(datum)
    assert classification.trust_class is TrustClass.HOSTILE
    record = quarantine(datum, classification.trust_class, classification.reason)
    assert record.trust_class is TrustClass.HOSTILE


def test_quarantine_is_deterministic():
    assert _quarantine() == _quarantine()


# --- Exclusion invariant (§15.5, T11; RFC-0002 invariant 4) ---


def test_quarantined_content_is_always_excluded():
    record = _quarantine()
    assert record.excluded is True


def test_no_non_excluded_quarantine_can_exist():
    record = _quarantine()
    assert record.excluded is True
    with pytest.raises(AttributeError):
        record.excluded = False  # frozen: the exclusion cannot be lifted


def test_quarantine_is_in_memory_only():
    record = _quarantine()
    assert isinstance(record, Quarantine)
    assert record.datum is not None
    assert record.reason


# --- T12: suspicion is contagious downward (§9.7) ---


@pytest.mark.parametrize(
    ("cls", "expected"),
    [
        (TrustClass.TRUSTED, TrustClass.CONDITIONAL),
        (TrustClass.CONDITIONAL, TrustClass.UNTRUSTED),
        (TrustClass.UNTRUSTED, TrustClass.UNTRUSTED),
        (TrustClass.HOSTILE, TrustClass.HOSTILE),
    ],
)
def test_contaminate_downgrades_one_step_downward(cls, expected):
    result = contaminate(_quarantine(), cls)
    assert result.trust_class is expected


@pytest.mark.parametrize("cls", ALL_CLASSES)
def test_contaminate_never_upgrades(cls):
    result = contaminate(_quarantine(), cls)
    assert result.trust_class.value <= cls.value


def test_contaminate_never_produces_hostile_from_a_non_hostile_class():
    for cls in NON_HOSTILE:
        result = contaminate(_quarantine(), cls)
        assert result.trust_class is not TrustClass.HOSTILE


def test_contaminate_preserves_the_source_reason():
    record = _quarantine(reason="detected attempt contained (RFC-0007 §15.8)")
    result = contaminate(record, TrustClass.TRUSTED)
    assert "detected attempt contained" in result.reason
    assert "T12" in result.reason


def test_contaminate_is_deterministic():
    record = _quarantine()
    assert contaminate(record, TrustClass.TRUSTED) == contaminate(
        record, TrustClass.TRUSTED
    )


def test_contaminate_returns_a_demotion():
    result = contaminate(_quarantine(), TrustClass.TRUSTED)
    assert hasattr(result, "trust_class") and hasattr(result, "reason")


# --- Ownership and public surface (blueprint §10) ---


def test_public_surface_is_exactly_the_owned_vocabulary():
    module = importlib.import_module("episky.trust.hostile")
    assert set(module.__all__) == EXPECTED_PUBLIC_SURFACE


def test_public_names_are_defined_by_hostile_py():
    module = importlib.import_module("episky.trust.hostile")
    for name in EXPECTED_PUBLIC_SURFACE:
        value = getattr(module, name)
        if hasattr(value, "__module__"):
            assert value.__module__ == "episky.trust.hostile"
        else:
            assert name in module.__dict__


def test_hostile_has_no_forbidden_responsibility_surface():
    tree = ast.parse(HOSTILE_PATH.read_text(encoding="utf-8"))
    identifiers = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.id, str)
    }
    assert identifiers.isdisjoint(
        {
            "secret",
            "redact",
            "detect",
            "promote",
            "persist",
            "store",
            "write",
            "execute",
            "provider",
            "executor",
            "policy",
            "runtime",
            "collect",
        }
    ), "hostile.py names a responsibility it does not own"


def test_hostile_performs_no_io_or_persistence_calls():
    tree = ast.parse(HOSTILE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                assert func.id not in {"open", "print", "input", "exec", "eval"}
            elif isinstance(func, ast.Attribute):
                assert func.attr not in {"write", "open", "persist"}


# --- Dependency rules (blueprint §4.1) ---


def test_hostile_imports_only_stdlib_and_trust_classes():
    tree = ast.parse(HOSTILE_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] in sys.stdlib_module_names
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                continue
            parts = node.module.split(".")
            if parts[0] == "episky":
                assert parts[1] == "trust", "hostile imports outside trust"
                assert parts[2:] == ["classes"], (
                    "hostile imports a non-classes trust module"
                )
            else:
                assert parts[0] in sys.stdlib_module_names
