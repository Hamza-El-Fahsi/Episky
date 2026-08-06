"""Operator-owned, default-deny policy evaluation (RFC-0008 §7, §8, §10).

Behavioral tests for Iteration 7 Commit C2 (`policy/policy.py`): the
Operator-owned default-deny mechanism — read-only-allowlist membership
(empty by default, Q7), elevation and standing-approval bounds (Q8), and
per-class retry ceilings (Q7) — with a fail-closed ``load`` (P3), the
deterministic decision that composes a C1 Classification with the §6 gate
table into exactly one outcome, never loosening the Operator's bounds
(RFC-0004 §9.7), the standing-approval construct (scope/ceiling/expiry,
never covering a Blocked Action and never raising a ceiling, P11), time as
an argument and never a clock read, determinism and immutability, the
owned public surface, and the dependency rule (stdlib + `episky.schema` +
`episky.policy.classify`/`gates` only; the runtime/executor edges stay
latent).
"""

import ast
import importlib
import pathlib
import sys
from datetime import datetime

import pytest

from episky.policy.classify import (
    Gate,
    RiskClass,
    classify,
)
from episky.policy.gates import ALLOWLISTED_READ_ONLY_GATE
from episky.policy.policy import (
    ElevationBound,
    StandingApproval,
    allowlisted,
    decide,
    elevation_bound_for,
    load,
    retry_ceiling,
    standing_approval_applies,
)
from episky.schema.action import Action

POLICY_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "policy"
    / "policy.py"
)

# The owned public surface of policy.py (design review §6; DN-51/52/53).
EXPECTED_PUBLIC_SURFACE = {
    "ElevationBound",
    "Policy",
    "PolicyDecision",
    "StandingApproval",
    "allowlisted",
    "decide",
    "elevation_bound_for",
    "load",
    "retry_ceiling",
    "standing_approval_applies",
}

NOW = datetime(2026, 8, 6, 12, 0, 0)


def _action(*props, description="an Action"):
    return Action(
        description=description,
        risk_properties=tuple(props),
        verification_criteria=(),
    )


def _classification(*props, description="an Action"):
    return classify(_action(*props, description=description))


# --- The default policy: nothing shipped, default deny (Q7; DN-51) ---


def test_default_policy_ships_no_rules():
    policy = load()
    assert policy.allowlist == frozenset()
    assert policy.elevation_bounds == ()
    assert policy.standing_approvals == ()
    assert policy.retry_ceilings == {}


def test_default_policy_allowlists_nothing():
    assert allowlisted(load(), _action("reads")) is False


def test_default_policy_has_no_elevation_bound():
    assert elevation_bound_for(load(), _action("reads")) is None


def test_default_policy_has_no_retry_ceiling():
    assert retry_ceiling(load(), RiskClass.READ_ONLY) is None


def test_default_policy_has_no_standing_approval():
    assert (
        standing_approval_applies(
            StandingApproval(
                scope="collect package list",
                ceiling=RiskClass.READ_ONLY,
                expiry=NOW,
            ),
            _classification("reads", description="collect package list"),
            NOW,
        )
        is False
    )


@pytest.mark.parametrize(
    ("props", "expected_gate"),
    [
        (("reads",), Gate.CONFIRM),
        (("mutates", "reversible"), Gate.CONFIRM),
        (("mutates", "reversible", "touches-configuration"), Gate.CONFIRM_WITH_WARNING),
        (("mutates", "touches-storage"), Gate.BLOCKED),
    ],
)
def test_default_policy_decides_each_class_to_its_section_six_gate(
    props, expected_gate
):
    decision = decide(load(), _classification(*props), NOW)
    assert decision.gate is expected_gate
    assert decision.retry_ceiling is None
    assert decision.standing_approval is None
    assert decision.elevation_bound is None
    assert decision.allowlisted is False


def test_default_deny_for_an_unclassifiable_action():
    decision = decide(load(), _classification(description="strange: unknown"), NOW)
    assert decision.risk_class is None
    assert decision.gate is Gate.BLOCKED
    assert decision.reason


# --- Allowlist membership (Q7; RFC-0008 §6) ---


def test_allowlisted_matches_by_exact_description():
    policy = load(allowlist=("collect package list",))
    assert (
        allowlisted(policy, _action("reads", description="collect package list"))
        is True
    )
    assert allowlisted(policy, _action("reads", description="collect other")) is False


def test_allowlisted_is_deterministic():
    policy = load(allowlist=("collect package list",))
    action = _action("reads", description="collect package list")
    assert allowlisted(policy, action) == allowlisted(policy, action)


def test_allowlisted_accepts_list_or_tuple():
    assert load(allowlist=["a", "b"]).allowlist == frozenset({"a", "b"})
    assert load(allowlist=("a",)).allowlist == frozenset({"a"})


# --- The decision never loosens the Operator's bounds (RFC-0004 §9.7) ---


def test_allowlisted_read_only_is_auto_permitted():
    policy = load(allowlist=("collect package list",))
    decision = decide(
        policy, _classification("reads", description="collect package list"), NOW
    )
    assert decision.gate is ALLOWLISTED_READ_ONLY_GATE
    assert decision.gate is Gate.AUTO_PERMITTED
    assert decision.allowlisted is True


def test_allowlist_never_loosens_a_benign_action():
    policy = load(allowlist=("make a backup",))
    decision = decide(
        policy,
        _classification("mutates", "reversible", description="make a backup"),
        NOW,
    )
    assert decision.allowlisted is True
    assert decision.gate is Gate.CONFIRM


def test_allowlist_never_loosens_a_consequential_action():
    policy = load(allowlist=("edit the fstab",))
    decision = decide(
        policy,
        _classification(
            "mutates",
            "reversible",
            "touches-configuration",
            description="edit the fstab",
        ),
        NOW,
    )
    assert decision.allowlisted is True
    assert decision.gate is Gate.CONFIRM_WITH_WARNING


def test_allowlist_never_loosens_a_destructive_action():
    policy = load(allowlist=("wipe the disk",))
    decision = decide(
        policy,
        _classification("mutates", "touches-storage", description="wipe the disk"),
        NOW,
    )
    assert decision.allowlisted is True
    assert decision.gate is Gate.BLOCKED


def test_a_standing_approval_never_loosens_a_destructive_action():
    policy = load(
        standing_approvals=(
            StandingApproval(
                scope="wipe the disk",
                ceiling=RiskClass.CONSEQUENTIAL,
                expiry=datetime(2026, 8, 7),
            ),
        )
    )
    decision = decide(
        policy,
        _classification("mutates", "touches-storage", description="wipe the disk"),
        NOW,
    )
    assert decision.standing_approval is None
    assert decision.gate is Gate.BLOCKED


# --- Determinism, purity, and immutability (§10; RFC-0002 invariant 7) ---


def test_decide_is_deterministic():
    policy = load(
        allowlist=("collect package list",),
        standing_approvals=(
            StandingApproval(
                scope="collect package list",
                ceiling=RiskClass.READ_ONLY,
                expiry=datetime(2026, 8, 7),
            ),
        ),
        elevation_bounds=(ElevationBound("collect package list"),),
        retry_ceilings={RiskClass.READ_ONLY: 3},
    )
    classification = _classification("reads", description="collect package list")
    assert decide(policy, classification, NOW) == decide(policy, classification, NOW)


def test_decide_same_now_same_answer_on_repeated_evaluation():
    policy = load()
    classification = _classification("mutates", "reversible")
    first = decide(policy, classification, NOW)
    for _ in range(50):
        assert decide(policy, classification, NOW) == first


def test_decide_is_side_effect_free():
    policy = load(allowlist=("collect package list",))
    classification = _classification("reads", description="collect package list")
    policy_before = repr(policy)
    classification_before = repr(classification)
    decide(policy, classification, NOW)
    assert repr(policy) == policy_before
    assert repr(classification) == classification_before


def test_policy_is_frozen_and_slot_based():
    policy = load()
    with pytest.raises(AttributeError):
        policy.allowlist = frozenset({"x"})
    assert hasattr(policy, "__slots__")


def test_policy_decision_is_frozen_and_slot_based():
    decision = decide(load(), _classification("reads"), NOW)
    with pytest.raises(AttributeError):
        decision.gate = Gate.BLOCKED
    assert hasattr(decision, "__slots__")


def test_elevation_bound_is_frozen_and_slot_based():
    bound = ElevationBound("x")
    with pytest.raises(AttributeError):
        bound.scope = "y"
    assert hasattr(bound, "__slots__")


def test_standing_approval_is_frozen_and_slot_based():
    approval = StandingApproval("x", RiskClass.READ_ONLY, NOW)
    with pytest.raises(AttributeError):
        approval.expiry = datetime(2026, 8, 7)
    assert hasattr(approval, "__slots__")


def test_load_normalizes_to_immutable_collections():
    policy = load(
        allowlist=["a", "b"],
        elevation_bounds=[ElevationBound("x")],
        standing_approvals=[
            StandingApproval("y", RiskClass.READ_ONLY, datetime(2026, 8, 7))
        ],
        retry_ceilings={RiskClass.READ_ONLY: 3},
    )
    assert type(policy.allowlist) is frozenset
    assert isinstance(policy.retry_ceilings, dict) is False
    with pytest.raises(TypeError):
        policy.retry_ceilings[RiskClass.READ_ONLY] = 9
    assert type(policy.elevation_bounds) is tuple
    assert type(policy.standing_approvals) is tuple


# --- Fail-closed load: a policy never loads partially (P3; §8.12) ---


@pytest.mark.parametrize(
    "allowlist",
    [("",), ("a", ""), (123,), (None,)],
)
def test_load_rejects_a_malformed_allowlist(allowlist):
    with pytest.raises(ValueError):
        load(allowlist=allowlist)


@pytest.mark.parametrize(
    "bounds",
    [
        (ElevationBound(""),),
        ("not-a-bound",),
        (None,),
    ],
)
def test_load_rejects_a_malformed_elevation_bound(bounds):
    with pytest.raises(ValueError):
        load(elevation_bounds=bounds)


def test_load_rejects_a_non_risk_class_standing_approval_ceiling():
    with pytest.raises(ValueError):
        load(
            standing_approvals=(
                StandingApproval("x", "read-only", datetime(2026, 8, 7)),  # type: ignore[arg-type]
            )
        )


def test_load_rejects_a_standing_approval_without_a_datetime_expiry():
    with pytest.raises(ValueError):
        load(
            standing_approvals=(
                StandingApproval("x", RiskClass.READ_ONLY, "2026-08-07"),  # type: ignore[arg-type]
            )
        )


@pytest.mark.parametrize(
    "approvals",
    [
        (StandingApproval("", RiskClass.READ_ONLY, NOW),),
        (StandingApproval("x", RiskClass.DESTRUCTIVE, NOW),),
        ("not-an-approval",),
        (None,),
    ],
)
def test_load_rejects_a_malformed_standing_approval(approvals):
    with pytest.raises(ValueError):
        load(standing_approvals=approvals)


@pytest.mark.parametrize(
    "ceilings",
    [
        {"benign": 1},
        {RiskClass.READ_ONLY: 0},
        {RiskClass.READ_ONLY: -1},
        {RiskClass.READ_ONLY: 1.5},
        {RiskClass.READ_ONLY: "3"},
    ],
)
def test_load_rejects_a_malformed_retry_ceiling(ceilings):
    with pytest.raises(ValueError):
        load(retry_ceilings=ceilings)


def test_load_failure_produces_no_policy_and_defaults_stay_intact():
    default = load()
    with pytest.raises(ValueError):
        load(retry_ceilings={RiskClass.READ_ONLY: 0})
    assert load() == default


# --- Standing approval: scope, ceiling, expiry (DN-52; P11) ---


def test_standing_approval_applies_in_scope_unexpired_within_ceiling():
    approval = StandingApproval(
        scope="collect package list",
        ceiling=RiskClass.CONSEQUENTIAL,
        expiry=datetime(2026, 8, 7),
    )
    assert (
        standing_approval_applies(
            approval, _classification("reads", description="collect package list"), NOW
        )
        is True
    )


def test_standing_approval_covers_any_class_at_or_below_the_ceiling():
    approval = StandingApproval(
        scope="collect package list",
        ceiling=RiskClass.CONSEQUENTIAL,
        expiry=datetime(2026, 8, 7),
    )
    for props in (("reads",), ("mutates", "reversible")):
        assert (
            standing_approval_applies(
                approval,
                _classification(*props, description="collect package list"),
                NOW,
            )
            is True
        )


def test_standing_approval_does_not_apply_out_of_scope():
    approval = StandingApproval(
        scope="collect package list",
        ceiling=RiskClass.CONSEQUENTIAL,
        expiry=datetime(2026, 8, 7),
    )
    assert (
        standing_approval_applies(
            approval, _classification("reads", description="collect other"), NOW
        )
        is False
    )


def test_standing_approval_does_not_apply_above_the_ceiling():
    approval = StandingApproval(
        scope="edit the fstab",
        ceiling=RiskClass.READ_ONLY,
        expiry=datetime(2026, 8, 7),
    )
    assert (
        standing_approval_applies(
            approval,
            _classification("mutates", "reversible", description="edit the fstab"),
            NOW,
        )
        is False
    )


def test_standing_approval_does_not_apply_when_expired():
    approval = StandingApproval(
        scope="collect package list",
        ceiling=RiskClass.READ_ONLY,
        expiry=datetime(2026, 8, 6, 11, 59, 59),
    )
    assert (
        standing_approval_applies(
            approval, _classification("reads", description="collect package list"), NOW
        )
        is False
    )


def test_standing_approval_does_not_apply_at_the_moment_of_expiry():
    approval = StandingApproval(
        scope="collect package list",
        ceiling=RiskClass.READ_ONLY,
        expiry=NOW,
    )
    assert (
        standing_approval_applies(
            approval, _classification("reads", description="collect package list"), NOW
        )
        is False
    )


def test_standing_approval_never_covers_a_destructive_action():
    approval = StandingApproval(
        scope="wipe the disk",
        ceiling=RiskClass.CONSEQUENTIAL,
        expiry=datetime(2026, 8, 7),
    )
    assert (
        standing_approval_applies(
            approval,
            _classification("mutates", "touches-storage", description="wipe the disk"),
            NOW,
        )
        is False
    )


def test_standing_approval_never_covers_an_unclassifiable_action():
    approval = StandingApproval(
        scope="mystery",
        ceiling=RiskClass.CONSEQUENTIAL,
        expiry=datetime(2026, 8, 7),
    )
    assert (
        standing_approval_applies(approval, _classification(description="mystery"), NOW)
        is False
    )


def test_standing_approval_applies_is_deterministic():
    approval = StandingApproval(
        scope="collect package list",
        ceiling=RiskClass.READ_ONLY,
        expiry=datetime(2026, 8, 7),
    )
    classification = _classification("reads", description="collect package list")
    assert standing_approval_applies(
        approval, classification, NOW
    ) == standing_approval_applies(approval, classification, NOW)


def test_first_matching_standing_approval_wins():
    policy = load(
        standing_approvals=(
            StandingApproval(
                "collect package list",
                RiskClass.READ_ONLY,
                datetime(2026, 8, 7),
            ),
            StandingApproval(
                "collect package list",
                RiskClass.CONSEQUENTIAL,
                datetime(2026, 8, 7),
            ),
        )
    )
    decision = decide(
        policy, _classification("reads", description="collect package list"), NOW
    )
    assert decision.standing_approval is policy.standing_approvals[0]


def test_a_standing_approval_never_raises_a_ceiling():
    policy = load(
        standing_approvals=(
            StandingApproval(
                "edit the fstab", RiskClass.READ_ONLY, datetime(2026, 8, 7)
            ),
        )
    )
    decision = decide(
        policy,
        _classification(
            "mutates",
            "reversible",
            "touches-configuration",
            description="edit the fstab",
        ),
        NOW,
    )
    assert decision.standing_approval is None
    assert decision.gate is Gate.CONFIRM_WITH_WARNING


# --- Elevation bounds and retry ceilings (DN-53; Q7; RFC-0008 §8) ---


def test_elevation_bound_matches_by_scope():
    policy = load(elevation_bounds=(ElevationBound("run pacman"),))
    assert (
        elevation_bound_for(policy, _action(description="run pacman")).scope
        == "run pacman"
    )
    assert elevation_bound_for(policy, _action(description="run apt")) is None


def test_elevation_bound_is_carried_by_the_decision():
    policy = load(elevation_bounds=(ElevationBound("run pacman"),))
    decision = decide(policy, _classification("mutates", description="run pacman"), NOW)
    assert decision.elevation_bound.scope == "run pacman"


def test_an_elevation_bound_never_changes_a_gate():
    policy = load(elevation_bounds=(ElevationBound("run pacman"),))
    decision = decide(policy, _classification("mutates", description="run pacman"), NOW)
    assert decision.gate is Gate.CONFIRM_WITH_WARNING


def test_retry_ceiling_is_per_class_and_carried():
    policy = load(retry_ceilings={RiskClass.READ_ONLY: 3})
    assert retry_ceiling(policy, RiskClass.READ_ONLY) == 3
    assert retry_ceiling(policy, RiskClass.BENIGN) is None
    decision = decide(policy, _classification("reads"), NOW)
    assert decision.retry_ceiling == 3


# --- The composed pipeline and the decision's carried facts (§7; §10) ---


def test_every_section_six_gate_is_reachable_through_decide():
    reachable = {
        decide(
            load(allowlist=("collect package list",))
            if props == ("reads",)
            else load(),
            _classification(*props, description="collect package list"),
            NOW,
        ).gate
        for props in (
            ("reads",),
            ("mutates", "reversible"),
            ("mutates", "reversible", "touches-configuration"),
            ("mutates", "touches-storage"),
        )
    }
    assert reachable == {
        Gate.AUTO_PERMITTED,
        Gate.CONFIRM,
        Gate.CONFIRM_WITH_WARNING,
        Gate.BLOCKED,
    }


def test_decide_requires_a_classification():
    with pytest.raises(ValueError):
        decide(load(), "not a classification", NOW)  # type: ignore[arg-type]


def test_decide_carries_warning_grounds_from_the_classification():
    decision = decide(
        load(), _classification("mutates", "reversible", "touches-configuration"), NOW
    )
    assert decision.gate is Gate.CONFIRM_WITH_WARNING
    assert decision.warning_grounds


def test_decide_carries_the_block_reason_from_the_classification():
    decision = decide(load(), _classification("mutates", "touches-storage"), NOW)
    assert decision.gate is Gate.BLOCKED
    assert decision.reason


def test_decide_carries_the_action_and_allowlist_flag():
    action = _action("reads", description="collect package list")
    decision = decide(load(allowlist=("collect package list",)), classify(action), NOW)
    assert decision.action is action
    assert decision.allowlisted is True
    assert decision.risk_class is RiskClass.READ_ONLY


def test_classify_then_decide_composes_deterministically():
    policy = load()
    for _ in range(25):
        decision = decide(policy, _classification("mutates", "reversible"), NOW)
        assert decision.gate is Gate.CONFIRM
        assert decision.risk_class is RiskClass.BENIGN


# --- Public surface and ownership (blueprint §10) ---


def test_public_surface_is_exactly_the_owned_vocabulary():
    module = importlib.import_module("episky.policy.policy")
    assert set(module.__all__) == EXPECTED_PUBLIC_SURFACE


def test_public_names_are_defined_by_policy_py():
    module = importlib.import_module("episky.policy.policy")
    for name in EXPECTED_PUBLIC_SURFACE:
        value = getattr(module, name)
        if hasattr(value, "__module__"):
            assert value.__module__ == "episky.policy.policy"
        else:
            assert name in module.__dict__


def test_public_surface_leaks_no_private_placeholder():
    module = importlib.import_module("episky.policy.policy")
    for name in module.__all__:
        assert not name.startswith("_")


def test_module_ownership_docstring_names_rfc_0008_and_the_guarantees():
    doc = importlib.import_module("episky.policy.policy").__doc__
    assert "RFC-0008" in doc
    assert "deterministic" in doc.lower()
    assert "default-deny" in doc
    assert "never" in doc


# --- Dependency rule: stdlib + schema + policy only; edges stay latent ---


def test_policy_py_imports_only_stdlib_schema_and_policy():
    tree = ast.parse(POLICY_PATH.read_text(encoding="utf-8"))
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
                if parts[1] == "schema":
                    continue
                assert parts[1] == "policy", "policy.py may import only episky.policy"
                assert parts[2] in ("classify", "gates")


def test_policy_py_keeps_the_latent_edges_latent():
    src = POLICY_PATH.read_text(encoding="utf-8")
    for token in (
        "episky.core",
        "episky.executor",
        "episky.trust",
        "episky.factlayer",
        "episky.systemmodel",
        "episky.secrets",
        "import trust",
        "import factlayer",
    ):
        assert token not in src


def test_policy_py_reads_no_clock():
    src = POLICY_PATH.read_text(encoding="utf-8")
    for token in (
        "datetime.now",
        "utcnow",
        "time.time",
        "time.monotonic",
        "perf_counter",
        "import time",
        "from time import",
    ):
        assert token not in src


def test_policy_py_imports_no_io_or_persistence_stdlib():
    src = POLICY_PATH.read_text(encoding="utf-8")
    for token in (
        "import os",
        "import pathlib",
        "import socket",
        "import urllib",
        "import random",
        "import subprocess",
        "import sqlite3",
        "import json",
        "import pickle",
        "import threading",
        "import asyncio",
    ):
        assert token not in src


def test_policy_py_calls_no_forbidden_io_builtin():
    tree = ast.parse(POLICY_PATH.read_text(encoding="utf-8"))
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            calls.add(func.id if isinstance(func, ast.Name) else func.attr)
    assert calls.isdisjoint({"open", "print", "input", "exec", "eval", "breakpoint"})
