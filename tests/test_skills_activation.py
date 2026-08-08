"""Skill Activation: the per-session, reversible, Policy-gated, audited
lifecycle (RFC-0011 §23; RFC-0002 §2.2/§4.7; RFC-0008; RFC-0011 §16; RFC-0004
A7; SK5; SK8; SK15).

Behavioral tests for Iteration 10 Commit C3/C4 (`skills/activation.py`), per
DN-81/DN-82: activation makes a validated Skill usable within a session, per
Policy. The §23 rules are asserted directly: activation is per-session and
reversible (RFC-0002 §2.2); activation is Policy-gated through an injected
decision, missing or refused decisions fail closed (RFC-0008; SK5); an
activated Skill grants no authority and still only proposes (§4); an
unauthenticated or unregistered value is never substituted (RFC-0002 §4.7);
and every transition or refusal records the §16 audited event with the
session and Skill identity attached (the audit write is `core`'s, RFC-0013
§23).

The boundary is value-free, deterministic, and fail-closed: the record binds
only {session, skill, stage}; no token, approval, permission, or execution
surface is created; deactivation returns the same loaded Skill (and so the
same validated manifest and signature) to the registered, not-active state.
It performs no I/O, no clock read, no randomness, no serialization, no
subprocess, and imports only `episky.skills.loader` — never `secrets`,
`audit`, `executor`, `verification`, `providers`, or `core` (blueprint §4.2;
DN-82).
"""

import ast
import importlib
import pathlib
from dataclasses import FrozenInstanceError

import pytest

from episky.policy.classify import RiskClass
from episky.skills.activation import (
    Activation,
    ActivationEvent,
    ActivationOutcome,
    ActivationRefusal,
    ActivationRequest,
    ActivationStage,
    ActivationVerdict,
    activate,
    deactivate,
)
from episky.skills.loader import (
    AuthenticationVerdict,
    PolicyVerdict,
    Skill,
    SkillCapability,
    SkillManifest,
    SkillStage,
    load,
)

SOURCE = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "skills"
    / "activation.py"
)

EXPECTED_PUBLIC_SURFACE = {
    "Activation",
    "ActivationEvent",
    "ActivationOutcome",
    "ActivationRefusal",
    "ActivationRequest",
    "ActivationStage",
    "ActivationVerdict",
    "activate",
    "deactivate",
}

EXPECTED_STAGES = (
    ActivationStage.INACTIVE,
    ActivationStage.ACTIVE,
)

EXPECTED_VERDICTS = (
    ActivationVerdict.PERMITTED,
    ActivationVerdict.REFUSED,
)

EXPECTED_EVENTS = (
    ActivationEvent.ACTIVATED,
    ActivationEvent.DEACTIVATED,
    ActivationEvent.REFUSED,
)

EXPECTED_REFUSALS = (
    ActivationRefusal.MALFORMED_REQUEST,
    ActivationRefusal.NO_SESSION,
    ActivationRefusal.NOT_REGISTERED,
    ActivationRefusal.ALREADY_ACTIVE,
    ActivationRefusal.NOT_ACTIVE,
    ActivationRefusal.IDENTITY_MISMATCH,
    ActivationRefusal.POLICY_DENIED,
)

OWNED_DATACLASSES = (
    Activation,
    ActivationOutcome,
    ActivationRequest,
)


def _capabilities(*names):
    return frozenset(SkillCapability[name] for name in names)


def _manifest(**overrides):
    base = {
        "name": "audit-boot",
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


def _gate(verdict=ActivationVerdict.PERMITTED):
    return lambda manifest: verdict


def _loaded(**manifest_overrides):
    return load(
        _manifest(**manifest_overrides),
        verifier=_verifier(),
        policy=_policy(),
    )


def _skill(**manifest_overrides):
    outcome = _loaded(**manifest_overrides)
    assert outcome.skill is not None
    return outcome.skill


def _request(session="session-1", skill=None):
    return ActivationRequest(session=session, skill=skill or _skill())


def _active(**overrides):
    return activate(_request(**overrides), policy=_gate())


class _LookAlikeSkill:
    """A Skill-shaped value that never passed the loader boundary (RFC-0002 §4.7)."""

    manifest = _manifest()
    stage = SkillStage.REGISTERED


# --- Public surface and structure ---


def test_public_surface_is_exactly_the_owned_activation_mechanics():
    mod = importlib.import_module("episky.skills.activation")
    assert set(mod.__all__) == EXPECTED_PUBLIC_SURFACE


def test_every_owned_type_is_a_frozen_slotted_dataclass():
    for cls in OWNED_DATACLASSES:
        params = cls.__dataclass_params__
        assert params.frozen, f"{cls.__name__} is not frozen"
        assert params.slots, f"{cls.__name__} is not slot-based"


def test_owned_types_keep_no_hidden_module_state():
    mod = importlib.import_module("episky.skills.activation")
    mutable_globals = {
        name
        for name, value in vars(mod).items()
        if isinstance(value, (list, dict, set))
        and not (name.startswith("__") and name.endswith("__"))
    }
    assert not mutable_globals


def test_activation_outcome_is_immutable():
    outcome = _active()
    with pytest.raises(FrozenInstanceError):
        outcome.event = ActivationEvent.REFUSED


# --- The stage, verdict, event, and refusal vocabularies ---


def test_stage_vocabulary_is_inactive_then_active():
    assert tuple(ActivationStage) == EXPECTED_STAGES


def test_verdict_vocabulary_is_permitted_and_refused():
    assert tuple(ActivationVerdict) == EXPECTED_VERDICTS


def test_event_vocabulary_is_activated_deactivated_refused():
    assert tuple(ActivationEvent) == EXPECTED_EVENTS


def test_refusal_vocabulary_is_the_fixed_seven_in_order():
    assert tuple(ActivationRefusal) == EXPECTED_REFUSALS


# --- Per-session: activation makes a loaded Skill usable in a session (§23) ---


def test_activation_makes_a_loaded_skill_usable_in_a_session():
    outcome = _active()
    assert outcome.event is ActivationEvent.ACTIVATED
    assert outcome.refusal is None
    assert outcome.reason
    assert outcome.activation is not None
    assert outcome.activation.stage is ActivationStage.ACTIVE


def test_activation_is_per_session():
    first = _active(session="session-1")
    second = _active(session="session-2")
    assert first.event is ActivationEvent.ACTIVATED
    assert second.event is ActivationEvent.ACTIVATED
    assert first.activation.session == "session-1"
    assert second.activation.session == "session-2"


def test_activation_requires_a_session():
    outcome = _active(session=None)
    assert outcome.event is ActivationEvent.REFUSED
    assert outcome.refusal is ActivationRefusal.NO_SESSION
    assert outcome.activation is None


def test_activation_binds_the_declared_skill_identity():
    skill = _skill()
    outcome = activate(
        ActivationRequest(session="session-1", skill=skill),
        policy=_gate(),
    )
    assert outcome.activation.skill is skill
    assert outcome.activation.skill.manifest.name == skill.manifest.name
    assert outcome.activation.skill.manifest.version == skill.manifest.version


# --- Fail-closed: an unauthenticated/unregistered value is never substituted ---


def test_non_skill_values_are_never_activated():
    for sample in (None, 42, "a-skill", _LookAlikeSkill()):
        outcome = activate(
            ActivationRequest(session="session-1", skill=sample),
            policy=_gate(),
        )
        assert outcome.event is ActivationEvent.REFUSED, sample
        assert outcome.refusal is ActivationRefusal.NOT_REGISTERED, sample
        assert outcome.activation is None


def test_non_request_values_are_refused_as_malformed():
    for sample in (None, 42, "activate-this", ("session", _skill())):
        outcome = activate(sample, policy=_gate())
        assert outcome.event is ActivationEvent.REFUSED, sample
        assert outcome.refusal is ActivationRefusal.MALFORMED_REQUEST, sample
        assert outcome.activation is None


def test_every_refusal_substitutes_nothing():
    for outcome in (
        _active(session=None),
        activate(_request(skill=42), policy=_gate()),
        activate(_request(), policy=None),
        activate(_request(), policy=_gate(ActivationVerdict.REFUSED)),
        deactivate(None),
    ):
        assert outcome.event is ActivationEvent.REFUSED
        assert outcome.activation is None


# --- Policy-gated activation (RFC-0008; SK5) ---


def test_a_missing_policy_decision_fails_closed():
    outcome = activate(_request())
    assert outcome.event is ActivationEvent.REFUSED
    assert outcome.refusal is ActivationRefusal.POLICY_DENIED
    assert outcome.activation is None


def test_a_refused_policy_decision_denies():
    outcome = activate(_request(), policy=_gate(ActivationVerdict.REFUSED))
    assert outcome.event is ActivationEvent.REFUSED
    assert outcome.refusal is ActivationRefusal.POLICY_DENIED
    assert outcome.activation is None


def test_a_permitted_policy_decision_activates():
    outcome = activate(_request(), policy=_gate(ActivationVerdict.PERMITTED))
    assert outcome.event is ActivationEvent.ACTIVATED
    assert outcome.refusal is None


def test_policy_sees_the_validated_manifest():
    skill = _skill()
    seen = []
    activate(
        _request(skill=skill),
        policy=lambda manifest: seen.append(manifest) or PolicyVerdict.PERMITTED,
    )
    assert seen == [skill.manifest]


# --- Reversible: deactivation returns the loaded Skill to the registry state ---


def test_activation_is_reversible():
    first = _active()
    restored = deactivate(first.activation)
    assert restored.event is ActivationEvent.DEACTIVATED
    assert restored.refusal is None
    assert restored.activation.stage is ActivationStage.INACTIVE
    reactivated = activate(
        ActivationRequest(
            session=restored.activation.session,
            skill=restored.activation.skill,
        ),
        policy=_gate(),
        current=restored.activation,
    )
    assert reactivated.event is ActivationEvent.ACTIVATED
    assert reactivated.activation.stage is ActivationStage.ACTIVE


def test_deactivation_returns_the_skill_to_the_registered_boundary():
    skill = _skill()
    outcome = _active(skill=skill)
    restored = deactivate(outcome.activation)
    assert restored.activation.skill is skill
    assert restored.activation.skill.manifest.signature == skill.manifest.signature
    assert restored.activation.skill.manifest.name == skill.manifest.name
    assert restored.activation.skill.stage is SkillStage.REGISTERED


def test_deactivation_of_a_not_active_activation_is_refused():
    first = _active()
    restored = deactivate(first.activation)
    again = deactivate(restored.activation)
    assert again.event is ActivationEvent.REFUSED
    assert again.refusal is ActivationRefusal.NOT_ACTIVE
    assert again.activation is None


def test_deactivation_requires_an_activation_record():
    for sample in (None, 42, "deactivate"):
        outcome = deactivate(sample)
        assert outcome.event is ActivationEvent.REFUSED, sample
        assert outcome.refusal is ActivationRefusal.MALFORMED_REQUEST, sample
        assert outcome.activation is None


def test_deactivation_of_a_different_session_is_refused():
    first = _active(session="session-1")
    outcome = deactivate(first.activation, session="session-2")
    assert outcome.event is ActivationEvent.REFUSED
    assert outcome.refusal is ActivationRefusal.IDENTITY_MISMATCH
    assert outcome.activation is None


# --- Double activation and identity (per-session, no substitution) ---


def test_double_activation_is_refused():
    first = _active()
    second = activate(
        ActivationRequest(
            session=first.activation.session,
            skill=first.activation.skill,
        ),
        policy=_gate(),
        current=first.activation,
    )
    assert second.event is ActivationEvent.REFUSED
    assert second.refusal is ActivationRefusal.ALREADY_ACTIVE
    assert second.activation is None


def test_substituting_a_different_skill_for_a_bound_session_is_refused():
    first = _active(skill=_skill(name="audit-boot"))
    other = _skill(name="kernel-logs")
    second = activate(
        ActivationRequest(session=first.activation.session, skill=other),
        policy=_gate(),
        current=first.activation,
    )
    assert second.event is ActivationEvent.REFUSED
    assert second.refusal is ActivationRefusal.IDENTITY_MISMATCH
    assert second.activation is None


def test_reactivating_a_deactivated_session_is_allowed():
    first = _active()
    restored = deactivate(first.activation)
    reactivated = activate(
        ActivationRequest(
            session=restored.activation.session,
            skill=restored.activation.skill,
        ),
        policy=_gate(),
        current=restored.activation,
    )
    assert reactivated.event is ActivationEvent.ACTIVATED
    assert reactivated.activation.skill is first.activation.skill


def test_reactivating_a_different_identity_is_refused():
    first = _active()
    restored = deactivate(first.activation)
    other = _skill(name="kernel-logs")
    second = activate(
        ActivationRequest(session=restored.activation.session, skill=other),
        policy=_gate(),
        current=restored.activation,
    )
    assert second.event is ActivationEvent.REFUSED
    assert second.refusal is ActivationRefusal.IDENTITY_MISMATCH


# --- Grants no authority: an activated Skill still only proposes (§4) ---


def test_activation_grants_no_authority():
    assert set(Activation.__dataclass_fields__) == {"session", "skill", "stage"}
    fields = set(Activation.__dataclass_fields__) | set(Skill.__dataclass_fields__)
    assert not fields & {
        "approve",
        "token",
        "permission",
        "grant",
        "execute",
        "execution",
        "proceed",
        "elevation",
    }


def test_an_activated_skill_still_only_proposes():
    skill = _skill()
    outcome = _active(skill=skill)
    assert outcome.activation.skill is skill
    assert outcome.activation.skill.manifest.capabilities == skill.manifest.capabilities
    assert outcome.activation.skill.manifest.privileges == skill.manifest.privileges
    assert outcome.activation.skill.manifest.targets == skill.manifest.targets


# --- Audited: every transition and refusal records the §16 event ---


def test_every_transition_records_an_audited_event():
    outcomes = [
        _active(),
        deactivate(_active().activation),
        _active(session=None),
        activate(_request(skill=42), policy=_gate()),
        activate(_request(), policy=None),
        activate(_request(), policy=_gate(ActivationVerdict.REFUSED)),
        deactivate(None),
        deactivate(_active().activation, session="other"),
    ]
    for outcome in outcomes:
        assert outcome.event in EXPECTED_EVENTS
        assert outcome.reason


def test_the_audited_event_carries_session_and_skill_identity():
    skill = _skill()
    outcome = activate(
        ActivationRequest(session="session-1", skill=skill),
        policy=_gate(),
    )
    assert outcome.activation.session == "session-1"
    assert outcome.activation.skill.manifest.name == "audit-boot"
    assert outcome.activation.skill.manifest.version == "1.0.0"


def test_the_audited_event_records_the_declared_surface():
    skill = _skill()
    outcome = activate(
        ActivationRequest(session="session-1", skill=skill),
        policy=_gate(),
    )
    assert outcome.activation.skill.manifest.signature == skill.manifest.signature
    assert outcome.activation.skill.manifest.targets == skill.manifest.targets


# --- Determinism ---


def test_activation_is_deterministic():
    assert activate(_request(), policy=_gate()) == activate(_request(), policy=_gate())
    assert activate(_request(), policy=None) == activate(_request(), policy=None)


def test_a_reversible_round_trip_is_deterministic():
    first = _active()
    assert deactivate(first.activation) == deactivate(first.activation)


# --- SC5/SK8: no secret-shaped value reaches an activation ---


def test_secret_shaped_values_never_reach_an_activation():
    lookalike = _LookAlikeSkill()
    lookalike.__dict__["secret"] = "sk-0123"
    outcome = activate(_request(skill=lookalike), policy=_gate())
    assert outcome.event is ActivationEvent.REFUSED
    assert outcome.refusal is ActivationRefusal.NOT_REGISTERED
    assert outcome.activation is None


# --- Conformance: imports, no I/O, no reasoning/sanitizing/verification ---


def test_activation_imports_only_the_allowed_layers():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    episky_imports = sorted({name for name in imported if name.startswith("episky")})
    assert episky_imports == ["episky.skills.loader"]


def test_activation_calls_no_classify_sanitize_verify_execute_or_verifier():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            calls.add(func.id if isinstance(func, ast.Name) else func.attr)
    forbidden = {
        "sanitize",
        "admit",
        "verify",
        "execute",
        "collect",
        "invoke",
        "approve",
        "mint",
        "classify",
    }
    assert not calls & forbidden
    assert not calls & {"subprocess", "os.system", "socket", "requests", "urllib"}


def test_activation_never_reads_a_clock_or_randomness():
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


def test_activation_generates_no_serialization_or_persistence():
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


def test_activation_performs_no_io_and_calls_no_forbidden_builtin():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            calls.add(func.id if isinstance(func, ast.Name) else func.attr)
    assert calls.isdisjoint({"open", "print", "input", "exec", "eval", "breakpoint"})


def test_activation_never_imports_execution_verification_an_audit_or_secrets():
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
                "episky.core",
            )
        )
        for name in imported
    )


def test_activation_has_no_providers_edge():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert not any(name.startswith("episky.providers") for name in imported)
