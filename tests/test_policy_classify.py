"""Deterministic risk classification (RFC-0008 §6; RFC-0002 invariant 7).

Behavioral tests for Iteration 7 Commit C1 (`policy/classify.py`): the four
§6 Risk Classes and four Gates in the table's order, the canonical
risk-property vocabulary (DN-47) and the membership test over it — no
percentage, probability, score, or proposer words (P2/I-7) — one carried
gate per class (P4), fail-closed blocking on unknown or unclassifiable
input (P3), the elevation rule (at least Consequential, DN-53/Q9), the meet
rule for Plans (DN-54/Q10), determinism and immutability, the owned public
surface, and the dependency rule (stdlib + `episky.schema` only; the
`systemmodel`/`trust`/`factlayer` edges stay latent).
"""

import ast
import importlib
import pathlib
import sys
from datetime import datetime

import pytest

from episky.policy.classify import (
    RISK_PROPERTIES,
    Classification,
    Gate,
    PlanClassification,
    RiskClass,
    classify,
    classify_plan,
    meet,
)
from episky.schema.action import Action, Plan, PostCondition, Step
from episky.schema.fact import (
    Collector,
    ConfidenceSource,
    Fact,
    FactStatus,
    Freshness,
    FreshnessState,
    MachineIdentity,
    ObservationReference,
    Property,
    Provenance,
    Scope,
    Subject,
    Value,
)

CLASSIFY_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "policy"
    / "classify.py"
)

# RFC-0008 §6 table order, transcribed.
FOUR_CLASSES = (
    RiskClass.READ_ONLY,
    RiskClass.BENIGN,
    RiskClass.CONSEQUENTIAL,
    RiskClass.DESTRUCTIVE,
)

# RFC-0008 §6 gate order, transcribed.
FOUR_GATES = (
    Gate.AUTO_PERMITTED,
    Gate.CONFIRM,
    Gate.CONFIRM_WITH_WARNING,
    Gate.BLOCKED,
)

# The owned public surface of classify.py (design review §6; DN-46/47/53/54).
EXPECTED_PUBLIC_SURFACE = {
    "Classification",
    "Gate",
    "PlanClassification",
    "RISK_PROPERTIES",
    "RiskClass",
    "classify",
    "classify_plan",
    "meet",
}


def _fact():
    return Fact(
        scope=Scope(
            subject=Subject(name="systemd"),
            property=Property(name="running-state"),
            value=Value(value="running"),
        ),
        status=FactStatus.OBSERVED,
        confidence=ConfidenceSource(name="systemctl-is-active"),
        provenance=Provenance(
            observation=ObservationReference(),
            collector=Collector(name="systemd-state", version="1"),
            collected_at=datetime(2026, 8, 6, 12, 0, 0),
        ),
        freshness=Freshness(state=FreshnessState.CURRENT),
        machine_identity=MachineIdentity(),
    )


def _action(*props, description="an Action"):
    return Action(
        description=description,
        risk_properties=tuple(props),
        verification_criteria=(),
    )


def _postcondition():
    return PostCondition(
        subject=Subject(name="systemd"),
        property=Property(name="running-state"),
        expected_value=Value(value="running"),
        freshness=Freshness(state=FreshnessState.CURRENT),
    )


def _step(*props, description="a Step"):
    return Step(
        action=_action(*props, description=description),
        preconditions=(),
        postcondition=_postcondition(),
        verification_method="re-observe",
    )


def _plan(*props_lists):
    return Plan(steps=tuple(_step(*props) for props in props_lists))


# --- Vocabulary: completeness and ordering (RFC-0008 §6) ---


def test_risk_class_has_exactly_four_members_in_table_order():
    assert tuple(RiskClass) == FOUR_CLASSES


def test_risk_class_member_values_are_mutually_exclusive():
    values = [member.value for member in RiskClass]
    assert len(set(values)) == len(values) == len(FOUR_CLASSES)


def test_risk_class_most_restrictive_is_the_meet_minimum():
    assert RiskClass.DESTRUCTIVE.value < RiskClass.CONSEQUENTIAL.value
    assert RiskClass.CONSEQUENTIAL.value < RiskClass.BENIGN.value
    assert RiskClass.BENIGN.value < RiskClass.READ_ONLY.value


def test_gate_has_exactly_the_four_gates_in_table_order():
    assert tuple(Gate) == FOUR_GATES


def test_gate_values_are_mutually_exclusive():
    values = [member.value for member in Gate]
    assert len(set(values)) == len(values) == len(FOUR_GATES)


# --- The canonical risk-property vocabulary (DN-47; RFC-0008 §6) ---


def test_risk_properties_are_canonical_names():
    assert RISK_PROPERTIES
    assert all(isinstance(name, str) and name for name in RISK_PROPERTIES)
    for name in (
        "mutates",
        "reads",
        "touches-packages",
        "touches-services",
        "touches-configuration",
        "touches-network",
        "touches-users",
        "touches-storage",
        "touches-security-state",
        "uses-elevation",
        "reversible",
        "boot-affecting",
        "auth-affecting",
    ):
        assert name in RISK_PROPERTIES


def test_risk_properties_are_immutable():
    with pytest.raises(AttributeError):
        RISK_PROPERTIES.add("warp-speed")


# --- Read-only (Inspection): observes, changes nothing (§6) ---


def test_read_only_observes_and_changes_nothing():
    result = classify(_action("reads"))
    assert result.risk_class is RiskClass.READ_ONLY
    assert result.gate is Gate.CONFIRM


def test_read_only_reads_a_subsystem():
    result = classify(_action("reads", "touches-configuration"))
    assert result.risk_class is RiskClass.READ_ONLY


def test_read_only_reversible_remains_read_only():
    result = classify(_action("reads", "reversible"))
    assert result.risk_class is RiskClass.READ_ONLY


# --- Benign: recoverable, narrow mutation (§6) ---


def test_benign_mutates_recoverably():
    result = classify(_action("mutates", "reversible"))
    assert result.risk_class is RiskClass.BENIGN
    assert result.gate is Gate.CONFIRM


def test_benign_package_install_from_configured_repo():
    result = classify(_action("mutates", "reversible", "touches-packages"))
    assert result.risk_class is RiskClass.BENIGN


# --- Consequential: broad or uncertain-to-reverse mutation (§6) ---


@pytest.mark.parametrize(
    "props",
    [
        ("mutates", "reversible", "touches-configuration"),
        ("mutates", "reversible", "touches-services"),
        ("mutates", "reversible", "touches-network"),
        ("mutates", "reversible", "touches-users"),
    ],
)
def test_consequential_mutates_a_system_wide_subsystem(props):
    result = classify(_action(*props))
    assert result.risk_class is RiskClass.CONSEQUENTIAL
    assert result.gate is Gate.CONFIRM_WITH_WARNING
    assert result.warning_grounds


def test_consequential_uncertain_to_reverse():
    result = classify(_action("mutates"))
    assert result.risk_class is RiskClass.CONSEQUENTIAL
    assert result.warning_grounds


# --- Elevation: at least Consequential (DN-53; RFC-0008 §8) ---


@pytest.mark.parametrize(
    "props",
    [
        ("mutates", "reversible", "uses-elevation"),
        ("mutates", "uses-elevation"),
        ("reads", "uses-elevation"),
        ("mutates", "reversible", "touches-packages", "uses-elevation"),
    ],
)
def test_elevation_makes_the_class_at_least_consequential(props):
    result = classify(_action(*props))
    assert result.risk_class.value <= RiskClass.CONSEQUENTIAL.value
    assert result.gate in (Gate.CONFIRM_WITH_WARNING, Gate.BLOCKED)


def test_elevated_reversible_mutation_is_consequential_not_benign():
    result = classify(_action("mutates", "reversible", "uses-elevation"))
    assert result.risk_class is RiskClass.CONSEQUENTIAL


def test_elevation_with_a_destructive_signal_is_destructive():
    result = classify(_action("mutates", "uses-elevation", "touches-security-state"))
    assert result.risk_class is RiskClass.DESTRUCTIVE


# --- Destructive: irrecoverable or security-critical (§6) ---


@pytest.mark.parametrize(
    ("props", "ground"),
    [
        (("mutates", "touches-security-state"), "security state"),
        (("mutates", "boot-affecting"), "booting"),
        (("mutates", "auth-affecting"), "authenticating"),
        (("mutates", "touches-storage"), "irrecoverable"),
        (("mutates", "touches-packages"), "irrecoverable"),
    ],
)
def test_destructive_blocks_with_a_named_reason(props, ground):
    result = classify(_action(*props))
    assert result.risk_class is RiskClass.DESTRUCTIVE
    assert result.gate is Gate.BLOCKED
    assert result.reason
    assert ground in result.reason


# --- Fail closed: unknown or unclassifiable is blocked and disclosed (P3) ---


@pytest.mark.parametrize(
    "props",
    [
        (),
        ("warp-speed",),
        ("mutates", "reads"),
        ("touches-packages",),
        ("reads", "mutates", "touches-configuration"),
    ],
)
def test_unclassifiable_input_fails_closed_to_blocked(props):
    result = classify(_action(*props))
    assert result.risk_class is None
    assert result.gate is Gate.BLOCKED
    assert result.reason


def test_unknown_property_is_named_in_the_fail_closed_reason():
    result = classify(_action("mutates", "warp-speed"))
    assert "warp-speed" in result.reason


def test_no_fail_closed_outcome_is_ever_auto_permitted():
    for props in [(), ("warp-speed",), ("mutates", "reads")]:
        assert classify(_action(*props)).gate is Gate.BLOCKED


def test_an_unclassified_action_is_never_granted_a_class():
    result = classify(_action("warp-speed"))
    assert result.risk_class is None
    assert result.risk_class not in set(RiskClass)


# --- One gate per class, carried, never re-derived (P4) ---


@pytest.mark.parametrize(
    ("props", "expected_class", "expected_gate"),
    [
        (("reads",), RiskClass.READ_ONLY, Gate.CONFIRM),
        (("mutates", "reversible"), RiskClass.BENIGN, Gate.CONFIRM),
        (
            ("mutates", "reversible", "touches-configuration"),
            RiskClass.CONSEQUENTIAL,
            Gate.CONFIRM_WITH_WARNING,
        ),
        (
            ("mutates", "touches-security-state"),
            RiskClass.DESTRUCTIVE,
            Gate.BLOCKED,
        ),
    ],
)
def test_one_carried_gate_per_class(props, expected_class, expected_gate):
    result = classify(_action(*props))
    assert result.risk_class is expected_class
    assert result.gate is expected_gate
    assert isinstance(result.gate, Gate)


def test_warning_grounds_only_for_confirm_with_warning():
    warned = classify(_action("mutates", "reversible", "touches-services"))
    assert warned.gate is Gate.CONFIRM_WITH_WARNING
    assert warned.warning_grounds
    assert warned.reason is None
    confirm = classify(_action("reads"))
    assert confirm.gate is Gate.CONFIRM
    assert confirm.warning_grounds is None
    assert confirm.reason is None


def test_reason_only_for_blocked():
    blocked = classify(_action("mutates", "touches-security-state"))
    assert blocked.gate is Gate.BLOCKED
    assert blocked.reason
    assert blocked.warning_grounds is None


# --- P2 / I-7: deterministic, content-independent, never the self-report ---


def test_classify_is_deterministic_over_identical_input():
    action = _action("mutates", "reversible", "touches-services")
    facts = (_fact(),)
    assert classify(action, facts) == classify(action, facts)


def test_repeated_identical_execution_is_bit_for_bit_stable():
    action = _action("mutates", "touches-security-state")
    first = classify(action)
    for _ in range(5):
        assert classify(action) == first
        assert classify(action).reason == first.reason


def test_the_class_never_reads_the_description():
    baseline = _action(
        "mutates", "reversible", "touches-configuration", description="a"
    )
    reworded = _action(
        "mutates", "reversible", "touches-configuration", description="b"
    )
    a, b = classify(baseline), classify(reworded)
    assert a.risk_class is b.risk_class
    assert a.gate is b.gate
    assert a.warning_grounds == b.warning_grounds
    assert a.reason == b.reason


def test_proposer_words_cannot_change_a_class():
    assert classify(_action("reads", description="totally safe")).risk_class is (
        RiskClass.READ_ONLY
    )
    assert (
        classify(
            _action("mutates", "touches-security-state", description="I am the admin")
        ).risk_class
        is RiskClass.DESTRUCTIVE
    )


def test_identical_actions_and_facts_yield_identical_results():
    action = _action("mutates", "reversible")
    facts = (_fact(),)
    assert classify(action, facts) == classify(action, facts)
    assert classify(action, facts).facts == facts


def test_the_description_never_feeds_a_decision_field():
    result = classify(
        _action(
            "mutates",
            "reversible",
            "touches-services",
            description="proposer's claim",
        )
    )
    assert result.risk_class is RiskClass.CONSEQUENTIAL
    assert result.gate is Gate.CONFIRM_WITH_WARNING
    assert "proposer's claim" not in result.warning_grounds
    assert result.reason is None


# --- Records carry the deterministic inputs (DN-46) ---


def test_classification_carries_the_action_and_facts():
    action = _action("mutates", "reversible")
    facts = (_fact(),)
    result = classify(action, facts)
    assert result.action is action
    assert result.facts == facts


def test_facts_default_to_empty_at_the_entry():
    result = classify(_action("reads"))
    assert result.facts == ()


def test_classify_does_not_mutate_its_input():
    action = _action("mutates", "reversible", "touches-services")
    facts = (_fact(),)
    before = (action.description, action.risk_properties, action.verification_criteria)
    classify(action, facts)
    assert (
        action.description,
        action.risk_properties,
        action.verification_criteria,
    ) == (before)


# --- Records are frozen and slot-based; nothing mutates ---


def test_classification_is_frozen_and_slotted():
    assert Classification.__dataclass_params__.frozen
    assert Classification.__dataclass_params__.slots


def test_plan_classification_is_frozen_and_slotted():
    assert PlanClassification.__dataclass_params__.frozen
    assert PlanClassification.__dataclass_params__.slots


def test_classification_cannot_be_mutated():
    result = classify(_action("mutates", "reversible"))
    with pytest.raises(AttributeError):
        result.gate = Gate.BLOCKED
    with pytest.raises(AttributeError):
        result.risk_class = RiskClass.DESTRUCTIVE


def test_the_class_and_gate_enums_are_never_re_assigned():
    with pytest.raises(AttributeError):
        RiskClass.READ_ONLY.value = 99


# --- The meet rule for Plans (DN-54; RFC-0008 §6; RFC-0007 §5.1) ---


def test_meet_is_the_most_restrictive_class():
    assert meet(RiskClass.DESTRUCTIVE, RiskClass.READ_ONLY) is RiskClass.DESTRUCTIVE
    assert meet(RiskClass.READ_ONLY, RiskClass.DESTRUCTIVE) is RiskClass.DESTRUCTIVE
    assert meet(RiskClass.BENIGN, RiskClass.CONSEQUENTIAL) is RiskClass.CONSEQUENTIAL
    assert meet(RiskClass.READ_ONLY, RiskClass.BENIGN) is RiskClass.BENIGN
    assert meet(RiskClass.READ_ONLY, RiskClass.READ_ONLY) is RiskClass.READ_ONLY


def test_meet_is_deterministic_and_total_over_the_classes():
    for a in RiskClass:
        for b in RiskClass:
            result = meet(a, b)
            assert result in RiskClass
            assert result.value <= a.value and result.value <= b.value
            assert meet(a, b) is meet(b, a)
            assert meet(a, meet(b, a)) is meet(meet(a, b), a)


def test_plan_class_is_the_meet_of_its_steps_classes():
    plan = _plan(("reads",), ("mutates", "reversible"))
    result = classify_plan(plan)
    assert result.risk_class is RiskClass.BENIGN
    assert result.gate is Gate.CONFIRM


def test_a_plan_with_a_destructive_step_is_destructive():
    plan = _plan(("reads",), ("mutates", "touches-security-state"))
    result = classify_plan(plan)
    assert result.risk_class is RiskClass.DESTRUCTIVE
    assert result.gate is Gate.BLOCKED
    assert result.reason


def test_plan_gate_matches_the_meet_class():
    plan = _plan(("reads",), ("mutates", "reversible", "touches-network"))
    result = classify_plan(plan)
    assert result.risk_class is RiskClass.CONSEQUENTIAL
    assert result.gate is Gate.CONFIRM_WITH_WARNING
    assert result.warning_grounds


def test_plan_carries_each_steps_own_class_and_gate():
    plan = _plan(("reads",), ("mutates", "touches-security-state"))
    result = classify_plan(plan)
    assert len(result.steps) == 2
    assert result.steps[0].risk_class is RiskClass.READ_ONLY
    assert result.steps[1].risk_class is RiskClass.DESTRUCTIVE
    assert result.steps[1].gate is Gate.BLOCKED


def test_empty_plan_fails_closed_to_blocked():
    result = classify_plan(_plan())
    assert result.risk_class is None
    assert result.gate is Gate.BLOCKED
    assert result.reason


def test_plan_with_an_unclassifiable_step_fails_closed_to_blocked():
    plan = _plan(("reads",), ("warp-speed",))
    result = classify_plan(plan)
    assert result.risk_class is None
    assert result.gate is Gate.BLOCKED
    assert result.reason


def test_classify_plan_is_deterministic():
    plan = _plan(("mutates", "reversible"), ("mutates", "reversible", "touches-users"))
    assert classify_plan(plan) == classify_plan(plan)


# --- The §6 examples, transcribed (RFC-0008 §6; all classes exercised) ---


@pytest.mark.parametrize(
    ("props", "expected_class"),
    [
        (("reads", "touches-packages"), RiskClass.READ_ONLY),
        (("reads", "touches-services"), RiskClass.READ_ONLY),
        (("reads", "touches-storage"), RiskClass.READ_ONLY),
        (("mutates", "reversible", "touches-packages"), RiskClass.BENIGN),
        (("mutates", "reversible"), RiskClass.BENIGN),
        (("mutates", "reversible", "touches-configuration"), RiskClass.CONSEQUENTIAL),
        (("mutates", "reversible", "touches-services"), RiskClass.CONSEQUENTIAL),
        (("mutates", "reversible", "touches-network"), RiskClass.CONSEQUENTIAL),
        (("mutates", "reversible", "uses-elevation"), RiskClass.CONSEQUENTIAL),
        (("mutates", "touches-packages"), RiskClass.DESTRUCTIVE),
        (("mutates", "touches-storage"), RiskClass.DESTRUCTIVE),
        (("mutates", "touches-security-state"), RiskClass.DESTRUCTIVE),
        (("mutates", "boot-affecting"), RiskClass.DESTRUCTIVE),
    ],
)
def test_section_six_examples_classify_to_their_table_class(props, expected_class):
    result = classify(_action(*props))
    assert result.risk_class is expected_class


def test_every_section_six_class_is_reachable():
    reachable = {
        classify(_action(*props)).risk_class
        for props, _ in [
            (("reads",), None),
            (("mutates", "reversible"), None),
            (("mutates", "reversible", "touches-configuration"), None),
            (("mutates", "touches-security-state"), None),
        ]
    }
    assert reachable == set(FOUR_CLASSES)


# --- Public surface and ownership (blueprint §10) ---


def test_public_surface_is_exactly_the_owned_vocabulary():
    module = importlib.import_module("episky.policy.classify")
    assert set(module.__all__) == EXPECTED_PUBLIC_SURFACE


def test_public_names_are_defined_by_classify_py():
    module = importlib.import_module("episky.policy.classify")
    for name in EXPECTED_PUBLIC_SURFACE:
        value = getattr(module, name)
        if hasattr(value, "__module__"):
            assert value.__module__ == "episky.policy.classify"
        else:
            assert name in module.__dict__


def test_public_surface_leaks_no_private_placeholder():
    module = importlib.import_module("episky.policy.classify")
    for name in module.__all__:
        assert not name.startswith("_")


def test_module_ownership_docstring_names_rfc_0008_and_the_guarantees():
    doc = importlib.import_module("episky.policy.classify").__doc__
    assert "RFC-0008" in doc
    assert "deterministic" in doc.lower()
    assert "invariant 7" in doc
    assert "never" in doc


# --- Dependency rule: stdlib + schema only; latent edges stay latent ---


def test_classify_py_imports_only_stdlib_and_the_schema_package():
    tree = ast.parse(CLASSIFY_PATH.read_text(encoding="utf-8"))
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
                assert parts[1] == "schema", "classify.py may import only episky.schema"


def test_classify_py_keeps_the_systemmodel_edge_latent():
    src = CLASSIFY_PATH.read_text(encoding="utf-8")
    assert "episky.systemmodel" not in src
    assert "import systemmodel" not in src


def test_classify_py_keeps_trust_and_factlayer_latent():
    src = CLASSIFY_PATH.read_text(encoding="utf-8")
    assert "import trust" not in src
    assert "import factlayer" not in src
    assert "episky.trust" not in src
    assert "episky.factlayer" not in src


def test_classify_py_imports_no_io_or_persistence_stdlib():
    src = CLASSIFY_PATH.read_text(encoding="utf-8")
    for token in (
        "import os",
        "import pathlib",
        "import socket",
        "import urllib",
        "import random",
        "import statistics",
        "import subprocess",
        "import sqlite3",
        "import pickle",
        "import json",
        "import threading",
        "import asyncio",
    ):
        assert token not in src


def test_classify_py_calls_no_forbidden_io_builtin():
    tree = ast.parse(CLASSIFY_PATH.read_text(encoding="utf-8"))
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            calls.add(func.id if isinstance(func, ast.Name) else func.attr)
    assert calls.isdisjoint({"open", "print", "input", "exec", "eval", "breakpoint"})
