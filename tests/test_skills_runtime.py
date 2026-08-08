"""Skill Runtime — deterministic gate-participation boundary tests (RFC-0011
§24, §12, §13, §14, §4; RFC-0008 §5, §7; RFC-0004 A3; SK4, SK11, SK12,
SK6; RFC-0002 §4.7).

Behavioral tests for Iteration 10 Commit C5 (`skills/runtime.py`): the
mechanics that route a registered Skill's Proposal into the same gate any
Action passes — never approving the Skill as a unit (RFC-0008 §5; SK4),
with declared Preconditions and Postconditions riding every Action
(SK11/SK12), expected effects enforced (a Proposal without them is
incomplete, RFC-0008 §5), the verification approach carried as a
declaration only (SK6), and no classification, approval, execution, or
verification performed here (RFC-0008 §7/P2; RFC-0004 A3).

The boundary is value-free, deterministic, and fail-closed: the admission
grantss nothing — the units carry an Action, the declared conditions, and
a verification declaration, and nothing else; an unregistered Skill, a
non-Proposal offering, a non-Action/Plan candidate, or an Action/Step
without its expected effect is refused with a disclosed reason. It performs
no I/O, no clock read, no randomness, no serialization, no subprocess, and
imports only `episky.schema.action` and `episky.skills.loader` — never
`secrets`, `audit`, `executor`, `verification`, `policy`, `providers`, or
`core` (blueprint §4.2; DN-82; RFC-0001 §4.7).
"""

import ast
import importlib
import pathlib
from dataclasses import FrozenInstanceError

import pytest

from episky.policy.classify import RiskClass
from episky.schema.action import Action, Plan, PostCondition, Proposal, Step
from episky.schema.fact import (
    Freshness,
    FreshnessState,
    Property,
    Subject,
    Value,
)
from episky.skills.loader import (
    AuthenticationVerdict,
    PolicyVerdict,
    SkillCapability,
    SkillManifest,
    SkillStage,
    load,
)
from episky.skills.runtime import (
    GateDisposition,
    GateRefusal,
    SkillActionUnit,
    SkillGate,
    admit,
)

SOURCE = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "skills"
    / "runtime.py"
)

EXPECTED_PUBLIC_SURFACE = {
    "GateDisposition",
    "GateRefusal",
    "SkillActionUnit",
    "SkillGate",
    "admit",
}

EXPECTED_DISPOSITIONS = (
    GateDisposition.ADMITTED,
    GateDisposition.REFUSED,
)

EXPECTED_REFUSALS = (
    GateRefusal.NOT_REGISTERED,
    GateRefusal.MALFORMED_OFFER,
    GateRefusal.MALFORMED_CANDIDATE,
    GateRefusal.INCOMPLETE_EFFECT,
)

OWNED_DATACLASSES = (
    SkillActionUnit,
    SkillGate,
)


def _capabilities(*names):
    return frozenset(SkillCapability[name] for name in names)


def _manifest(**overrides):
    base = {
        "name": "boot-care",
        "version": "1.0.0",
        "signature": "sig-abc",
        "targets": ("debian-12",),
        "privileges": ("read-boot-log",),
        "risk": RiskClass.READ_ONLY,
        "capabilities": _capabilities("DIAGNOSTICS", "EXPLANATION"),
        "dependencies": (),
        "collectors": ("distro", "kernel"),
        "preconditions": ("boot-completed",),
        "postconditions": ("boot-log-observed",),
        "verification": "compare Facts against declared Postconditions",
    }
    base.update(overrides)
    return SkillManifest(**base)


def _verifier(verdict=AuthenticationVerdict.AUTHENTICATED):
    return lambda manifest: verdict


def _policy(verdict=PolicyVerdict.PERMITTED):
    return lambda manifest: verdict


def _skill(**manifest_overrides):
    outcome = load(
        _manifest(**manifest_overrides),
        verifier=_verifier(),
        policy=_policy(),
    )
    assert outcome.skill is not None
    return outcome.skill


def _postcondition(**overrides):
    base = {
        "subject": Subject(name="boot"),
        "property": Property(name="state"),
        "expected_value": Value(value="running"),
        "freshness": Freshness(state=FreshnessState.CURRENT),
    }
    base.update(overrides)
    return PostCondition(**base)


def _action(**overrides):
    base = {
        "description": "restart the boot service",
        "risk_properties": ("mutates", "reversible", "touches-services"),
        "verification_criteria": (_postcondition(),),
    }
    base.update(overrides)
    return Action(**base)


def _step(**overrides):
    base = {
        "action": _action(),
        "preconditions": (),
        "postcondition": _postcondition(),
        "verification_method": "re-check the boot service state Fact (RFC-0006)",
    }
    base.update(overrides)
    return Step(**base)


def _offer(candidate):
    return Proposal(candidate=candidate)


SEMANTIC_ACTION = _action()
SEMANTIC_STEP = _step()
SEMANTIC_PLAN = Plan(steps=(SEMANTIC_STEP, SEMANTIC_STEP))


class _LookAlikeSkill:
    """A Skill-shaped value that never passed the loader boundary (RFC-0001 §4.7)."""

    stage = SkillStage.REGISTERED
    manifest = _manifest()


# --- Public surface and structure ---


def test_public_surface_is_exactly_the_owned_gate_runtime():
    mod = importlib.import_module("episky.skills.runtime")
    assert set(mod.__all__) == EXPECTED_PUBLIC_SURFACE


def test_every_owned_type_is_a_frozen_slotted_dataclass():
    for cls in OWNED_DATACLASSES:
        params = cls.__dataclass_params__
        assert params.frozen, f"{cls.__name__} is not frozen"
        assert params.slots, f"{cls.__name__} is not slot-based"


def test_owned_types_keep_no_hidden_module_state():
    mod = importlib.import_module("episky.skills.runtime")
    mutable_globals = {
        name
        for name, value in vars(mod).items()
        if isinstance(value, (list, dict, set))
        and not (name.startswith("__") and name.endswith("__"))
    }
    assert not mutable_globals


def test_skill_gate_is_immutable():
    gate = admit(_skill(), _offer(SEMANTIC_ACTION))
    with pytest.raises(FrozenInstanceError):
        gate.units = ()


# --- Vocabulary ---


def test_disposition_vocabulary_is_admitted_then_refused():
    assert tuple(GateDisposition) == EXPECTED_DISPOSITIONS


def test_refusal_vocabulary_is_the_fixed_four_in_order():
    assert tuple(GateRefusal) == EXPECTED_REFUSALS


# --- SK4: the Skill is never a unit; its Actions pass the gate ---


def test_a_registered_skill_single_action_is_admitted():
    skill = _skill()
    gate = admit(skill, _offer(_action()))
    assert gate.disposition is GateDisposition.ADMITTED
    assert gate.refusal is None
    assert gate.reason
    assert len(gate.units) == 1
    unit = gate.units[0]
    assert isinstance(unit, SkillActionUnit)


def test_the_unit_carries_the_exact_offered_action():
    action = _action(description="restart the boot service")
    gate = admit(_skill(), _offer(action))
    assert gate.units[0].action is action


def test_a_skills_plan_is_never_admitted_as_a_unit():
    step_a = _step()
    step_b = _step()
    plan = Plan(steps=(step_a, step_b))
    gate = admit(_skill(), _offer(plan))
    assert gate.disposition is GateDisposition.ADMITTED
    assert len(gate.units) == 2
    assert gate.units[0].action is step_a.action
    assert gate.units[1].action is step_b.action


def test_no_unit_carries_a_plan_or_envelope():
    gate = admit(_skill(), _offer(SEMANTIC_PLAN))
    for unit in gate.units:
        assert isinstance(unit.action, Action)
        assert isinstance(unit, SkillActionUnit)


def test_units_carry_no_approval_token_or_authority():
    fields = set(SkillActionUnit.__dataclass_fields__) | set(
        SkillGate.__dataclass_fields__
    )
    assert not fields & {
        "approve",
        "approved",
        "token",
        "permit",
        "permission",
        "grant",
        "elevation",
        "execution",
        "risk",
        "verdict",
    }


def test_an_action_carries_no_command_surface():
    unit = admit(_skill(), _offer(SEMANTIC_ACTION)).units[0]
    assert not hasattr(unit.action, "command")
    assert not hasattr(unit.action, "execute")


# --- SK11/SK12: declared Pre/Postconditions ride the Action ---


def test_declared_preconditions_ride_the_unit():
    skill = _skill()
    gate = admit(skill, _offer(SEMANTIC_ACTION))
    assert gate.units[0].preconditions == skill.manifest.preconditions
    assert gate.units[0].preconditions == ("boot-completed",)


def test_the_offering_cannot_replace_the_declared_preconditions():
    gate = admit(_skill(), _offer(SEMANTIC_ACTION))
    assert gate.units[0].preconditions == ("boot-completed",)
    assert "magical" not in gate.units[0].preconditions


def test_declared_postconditions_ride_the_unit():
    action = _action()
    gate = admit(_skill(), _offer(action))
    assert gate.units[0].postconditions == action.verification_criteria
    assert gate.units[0].postconditions == (_postcondition(),)


def test_an_action_without_expected_postconditions_is_incomplete():
    gate = admit(_skill(), _offer(_action(verification_criteria=())))
    assert gate.disposition is GateDisposition.REFUSED
    assert gate.refusal is GateRefusal.INCOMPLETE_EFFECT
    assert gate.units == ()


def test_a_plan_step_without_an_expected_effect_is_incomplete():
    step = _step(action=_action(verification_criteria=()))
    gate = admit(_skill(), _offer(Plan(steps=(step,))))
    assert gate.disposition is GateDisposition.REFUSED
    assert gate.refusal is GateRefusal.INCOMPLETE_EFFECT
    assert gate.units == ()


def test_a_step_without_a_declared_verification_method_is_refused():
    step = _step(verification_method="   ")
    gate = admit(_skill(), _offer(Plan(steps=(step,))))
    assert gate.disposition is GateDisposition.REFUSED
    assert gate.refusal is GateRefusal.INCOMPLETE_EFFECT


def test_an_empty_plan_offers_no_expected_effect():
    gate = admit(_skill(), _offer(Plan(steps=())))
    assert gate.disposition is GateDisposition.REFUSED
    assert gate.refusal is GateRefusal.INCOMPLETE_EFFECT
    assert gate.units == ()


# --- SK6: the verification approach is a declaration only ---


def test_the_verification_approach_is_declared_never_performed():
    skill = _skill()
    gate = admit(skill, _offer(SEMANTIC_ACTION))
    assert gate.units[0].verification_method == skill.manifest.verification
    assert gate.units[0].verification_method


def test_a_plan_step_carries_its_declared_verification_method():
    step = _step()
    gate = admit(_skill(), _offer(Plan(steps=(step,))))
    assert gate.units[0].verification_method == step.verification_method


def test_no_unit_carries_a_verification_verdict():
    gate = admit(_skill(), _offer(SEMANTIC_ACTION))
    unit = gate.units[0]
    assert not hasattr(unit, "outcome")
    assert not hasattr(unit, "verdict")
    assert not hasattr(unit, "confirmed")
    assert gate.units[0].verification_method is not None


# --- Fail-closed and malformed inputs ---


def test_an_unregistered_or_non_skill_value_never_reaches_the_gate():
    for sample in (None, 42, "a-skill", _LookAlikeSkill()):
        gate = admit(sample, _offer(SEMANTIC_ACTION))
        assert gate.disposition is GateDisposition.REFUSED, sample
        assert gate.refusal is GateRefusal.NOT_REGISTERED, sample
        assert gate.units == ()


def test_a_non_proposal_offering_is_refused():
    skill = _skill()
    for sample in (None, 42, "do-it", SEMANTIC_ACTION, SEMANTIC_PLAN):
        gate = admit(skill, sample)
        assert gate.disposition is GateDisposition.REFUSED, sample
        assert gate.refusal is GateRefusal.MALFORMED_OFFER, sample
        assert gate.units == ()


def test_a_candidate_that_is_neither_an_action_nor_a_plan_is_refused():
    gate = admit(_skill(), _offer(42))
    assert gate.disposition is GateDisposition.REFUSED
    assert gate.refusal is GateRefusal.MALFORMED_CANDIDATE
    assert gate.units == ()


def test_every_refusal_produces_no_unit_and_is_loud():
    outcomes = [
        admit(42, _offer(SEMANTIC_ACTION)),
        admit(_skill(), SEMANTIC_ACTION),
        admit(_skill(), _offer(42)),
        admit(_skill(), _offer(_action(verification_criteria=()))),
    ]
    for gate in outcomes:
        assert gate.disposition is GateDisposition.REFUSED
        assert gate.units == ()
        assert gate.reason


# --- The Skill's words give no consideration (RFC-0008 §7/P2) ---


def test_the_action_description_is_never_reasoning_material():
    action = _action(description="grant root access to everyone")
    gate = admit(_skill(), _offer(action))
    assert gate.disposition is GateDisposition.ADMITTED
    assert "grant root access" not in gate.reason


def test_the_unit_does_not_repeat_the_skill_words():
    gate = admit(_skill(), _offer(SEMANTIC_ACTION))
    assert "restart" not in gate.units[0].verification_method


# --- Determinism and immutability ---


def test_admission_is_deterministic():
    skill = _skill()
    offer = _offer(_action())
    assert admit(skill, offer) == admit(skill, offer)


def test_refusal_is_deterministic():
    assert admit(_skill(), _offer(42)) == admit(_skill(), _offer(42))


# --- SC5/SK8: secret-shaped values never reach a unit's declaration ---


def test_secret_shaped_values_stay_out_of_the_declaration():
    action = _action(description="fix sk-0123 and password=hunter2")
    unit = admit(_skill(), _offer(action)).units[0]
    assert isinstance(unit, SkillActionUnit)
    assert "sk-0123" not in unit.verification_method
    assert "sk-0123" not in "".join(map(str, unit.preconditions))
    assert "password" not in unit.verification_method


# --- Conformance: imports, no I/O, no reasoning/classification/execution ---


def test_runtime_imports_only_the_allowed_layers():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    episky_imports = sorted({name for name in imported if name.startswith("episky")})
    assert episky_imports == [
        "episky.schema.action",
        "episky.skills.loader",
    ]


def test_runtime_calls_no_classify_verify_execute_or_approve():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            calls.add(func.id if isinstance(func, ast.Name) else func.attr)
    forbidden = {
        "classify",
        "classify_plan",
        "verify",
        "execute",
        "approve",
        "sanitize",
        "admit",
        "gate",
        "mint",
        "subprocess",
        "os.system",
        "socket",
        "requests",
        "urllib",
    }
    assert not calls & forbidden


def test_runtime_never_reads_a_clock_or_randomness():
    src = SOURCE.read_text(encoding="utf-8")
    for token in (
        "datetime.now",
        "utcnow",
        "datetime.today",
        "time.time",
        "time.monotonic",
        "import time",
        "import random",
        "random.",
        "os.urandom",
        "import uuid",
        "uuid4",
        "token_hex",
        "import hmac",
        "import hashlib",
    ):
        assert token not in src


def test_runtime_generates_no_serialization_or_persistence():
    src = SOURCE.read_text(encoding="utf-8")
    for token in (
        "import json",
        "json.",
        "import yaml",
        "yaml.",
        "markdown",
        "dump",
        "dumps",
        "encode",
        "pickle",
        "sqlite",
        "shelve",
        "pathlib",
        "import os",
        "open(",
    ):
        assert token not in src


def test_runtime_performs_no_io_and_calls_no_forbidden_builtin():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            calls.add(func.id if isinstance(func, ast.Name) else func.attr)
    assert calls.isdisjoint({"open", "print", "input", "exec", "eval", "breakpoint"})


def test_runtime_never_imports_execution_verification_an_audit_or_secrets():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert not any(
        name.startswith(
            (
                "episky.audit",
                "episky.executor",
                "episky.verification",
                "episky.secrets",
                "episky.policy",
                "episky.core",
                "episky.providers",
                "episky.context",
                "episky.trust",
            )
        )
        for name in imported
    )


def test_runtime_has_no_providers_or_core_edge():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert not any(
        name.startswith(("episky.providers", "episky.core")) for name in imported
    )
