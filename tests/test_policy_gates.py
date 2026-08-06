"""Gates per risk class (RFC-0008 §6; RFC-0001 §5).

Behavioral tests for Iteration 7 Commit C2 (`policy/gates.py`): the §6
class→gate table transcribed exactly as data, the deterministic
(risk class, allowlist membership) → gate lookup, a blocked Action never
loosened (RFC-0004 §9.7), fail-closed lookup on a non-class, immutability,
the owned public surface, and the dependency rule (stdlib +
`episky.policy.classify` only; no `episky.schema`, no forbidden packages,
no I/O, no forbidden runtime behavior).
"""

import ast
import importlib
import pathlib
import sys

import pytest

from episky.policy.classify import Gate, RiskClass
from episky.policy.gates import (
    ALLOWLISTED_READ_ONLY_GATE,
    CLASS_GATES,
    gate_for,
)

GATES_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "policy"
    / "gates.py"
)

# The owned public surface of gates.py (design review §6; RFC-0008 §6).
EXPECTED_PUBLIC_SURFACE = {
    "ALLOWLISTED_READ_ONLY_GATE",
    "CLASS_GATES",
    "gate_for",
}

# RFC-0008 §6 table, transcribed: class → gate (read-only's non-allowlisted
# face is confirm; auto-permitted applies iff allowlisted).
EXPECTED_GATES = {
    RiskClass.READ_ONLY: Gate.CONFIRM,
    RiskClass.BENIGN: Gate.CONFIRM,
    RiskClass.CONSEQUENTIAL: Gate.CONFIRM_WITH_WARNING,
    RiskClass.DESTRUCTIVE: Gate.BLOCKED,
}


# --- The §6 table as data ---


def test_class_gates_covers_exactly_the_four_classes():
    assert set(CLASS_GATES) == set(RiskClass)
    assert len(CLASS_GATES) == 4


def test_class_gates_transcribes_the_section_six_table():
    assert dict(CLASS_GATES) == EXPECTED_GATES


def test_allowlisted_read_only_gate_is_auto_permitted():
    assert ALLOWLISTED_READ_ONLY_GATE is Gate.AUTO_PERMITTED


def test_class_gates_is_immutable():
    with pytest.raises(TypeError):
        CLASS_GATES[RiskClass.READ_ONLY] = Gate.BLOCKED


def test_class_gates_values_are_gate_members():
    for gate in CLASS_GATES.values():
        assert isinstance(gate, Gate)


# --- The gate lookup (class, allowlist membership) → gate ---


@pytest.mark.parametrize(
    ("risk_class", "expected_gate"),
    [
        (RiskClass.READ_ONLY, Gate.CONFIRM),
        (RiskClass.BENIGN, Gate.CONFIRM),
        (RiskClass.CONSEQUENTIAL, Gate.CONFIRM_WITH_WARNING),
        (RiskClass.DESTRUCTIVE, Gate.BLOCKED),
    ],
)
def test_gate_for_yields_one_gate_per_class(risk_class, expected_gate):
    assert gate_for(risk_class) is expected_gate


def test_allowlisted_read_only_is_auto_permitted():
    assert gate_for(RiskClass.READ_ONLY, allowlisted=True) is Gate.AUTO_PERMITTED
    assert gate_for(RiskClass.READ_ONLY, allowlisted=False) is Gate.CONFIRM


@pytest.mark.parametrize("risk_class", [RiskClass.BENIGN, RiskClass.CONSEQUENTIAL])
def test_allowlist_never_loosens_a_non_read_only_gate(risk_class):
    assert gate_for(risk_class, allowlisted=True) is gate_for(risk_class)


def test_destructive_is_never_loosened_by_the_allowlist():
    assert gate_for(RiskClass.DESTRUCTIVE, allowlisted=True) is Gate.BLOCKED
    assert gate_for(RiskClass.DESTRUCTIVE, allowlisted=False) is Gate.BLOCKED


def test_gate_for_is_deterministic():
    for risk_class in RiskClass:
        for allowlisted in (True, False):
            assert gate_for(risk_class, allowlisted) == gate_for(
                risk_class, allowlisted
            )
            assert gate_for(risk_class, allowlisted) is gate_for(
                risk_class, allowlisted
            )


@pytest.mark.parametrize("bad", [None, "benign", 3, Gate.CONFIRM])
def test_gate_for_fails_closed_on_a_non_class(bad):
    with pytest.raises(ValueError):
        gate_for(bad)


# --- Public surface and ownership ---


def test_public_surface_is_exactly_the_owned_vocabulary():
    module = importlib.import_module("episky.policy.gates")
    assert set(module.__all__) == EXPECTED_PUBLIC_SURFACE


def test_public_names_are_defined_by_gates_py():
    module = importlib.import_module("episky.policy.gates")
    for name in EXPECTED_PUBLIC_SURFACE:
        assert name in module.__dict__


def test_module_ownership_docstring_names_rfc_0008_and_the_guarantees():
    doc = importlib.import_module("episky.policy.gates").__doc__
    assert "RFC-0008" in doc
    assert "deterministic" in doc.lower()
    assert "never" in doc


# --- Dependency rule and forbidden runtime behavior ---


def test_gates_py_imports_only_stdlib_and_classify():
    tree = ast.parse(GATES_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] in sys.stdlib_module_names
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "no relative imports"
            parts = node.module.split(".")
            if parts[0] != "episky":
                assert parts[0] in sys.stdlib_module_names
            else:
                assert parts[1] == "policy" and parts[2] == "classify", (
                    "gates.py may import only episky.policy.classify"
                )


def test_gates_py_never_imports_schema_or_a_forbidden_package():
    src = GATES_PATH.read_text(encoding="utf-8")
    for token in ("episky.schema", "systemmodel", "trust", "factlayer", "secrets"):
        assert token not in src


def test_gates_py_imports_no_io_or_persistence_stdlib():
    src = GATES_PATH.read_text(encoding="utf-8")
    for token in (
        "import os",
        "import pathlib",
        "import socket",
        "import urllib",
        "import random",
        "import subprocess",
        "import sqlite3",
        "import json",
        "import threading",
    ):
        assert token not in src


def test_gates_py_calls_no_forbidden_io_builtin():
    tree = ast.parse(GATES_PATH.read_text(encoding="utf-8"))
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            calls.add(func.id if isinstance(func, ast.Name) else func.attr)
    assert calls.isdisjoint({"open", "print", "input", "exec", "eval", "breakpoint"})
