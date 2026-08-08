"""Skill Registry load-and-authenticate boundary, declared surface, and
capability vocabulary (RFC-0011 §3, §8, §19, §22; RFC-0002 §4.7; RFC-0001
§11.2/§11.3/§11.5; RFC-0007 §6.11).

Behavioral tests for Iteration 10 Commit C3 (`skills/loader.py`): the
deterministic mechanics the Skill Registry uses to turn a Skill's packaged
content into a validated contract instance. Loading reads the declared
surface, authenticates signature and provenance through an injected verifier
(unauthenticated Skills are never loaded, never substituted, RFC-0002 §4.7;
SK5), validates the declaration deterministically (targets, privileges, risk,
capabilities, dependencies, Preconditions, Postconditions, verification
approach; RFC-0011 §22), checks bundled Collectors against the `collectors`
registry (§11), checks Policy before activation (RFC-0008) through an injected
decision, and registers with the Core (RFC-0001 §11.2). The version and
signature ride the manifest (§19).

The loader is value-free and fail-closed: a loaded Skill carries its declared
surface and nothing else, no capability implies permission (§8), nothing here
is a Fact, an approval, or an execution surface (§4), and load has no side
effects (RFC-0011 §22). It performs no I/O, no clock read, no randomness, no
serialization, no subprocess, and imports only `collectors` and `policy` —
never `secrets`, `audit`, `executor`, `core`, a provider, or `verification`.
"""

import ast
import importlib
import pathlib
from dataclasses import FrozenInstanceError

import pytest

from episky.collectors.registry import COLLECTOR_SPECS
from episky.policy.classify import RiskClass
from episky.skills.loader import (
    AuthenticationVerdict,
    LoadDisposition,
    LoadOutcome,
    LoadRefusal,
    PolicyVerdict,
    Skill,
    SkillCapability,
    SkillDependency,
    SkillManifest,
    SkillStage,
    load,
)

SOURCE = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "skills"
    / "loader.py"
)

EXPECTED_PUBLIC_SURFACE = {
    "AuthenticationVerdict",
    "LoadDisposition",
    "LoadOutcome",
    "LoadRefusal",
    "PolicyVerdict",
    "Skill",
    "SkillCapability",
    "SkillDependency",
    "SkillManifest",
    "SkillStage",
    "load",
}

EXPECTED_CAPABILITIES = (
    SkillCapability.DIAGNOSTICS,
    SkillCapability.EXPLANATION,
    SkillCapability.PROPOSAL,
    SkillCapability.PLANNING,
    SkillCapability.VERIFICATION_APPROACH,
    SkillCapability.DETERMINISTIC_OPERATION,
)

EXPECTED_REFUSALS = (
    LoadRefusal.UNAUTHENTICATED,
    LoadRefusal.MALFORMED_SURFACE,
    LoadRefusal.INVALID_DECLARATION,
    LoadRefusal.INVALID_DEPENDENCY,
    LoadRefusal.UNKNOWN_COLLECTOR,
    LoadRefusal.POLICY_DENIED,
)

OWNED_DATACLASSES = (
    LoadOutcome,
    Skill,
    SkillDependency,
    SkillManifest,
)


def _capabilities(*names):
    return frozenset(SkillCapability[name] for name in names)


def _dependencies(*pairs):
    return tuple(SkillDependency(name=name, version=version) for name, version in pairs)


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


def _loaded(**overrides):
    return load(_manifest(**overrides), verifier=_verifier(), policy=_policy())


class _LookAlikeManifest:
    """A manifest-shaped value that is not :class:`SkillManifest`."""

    name = "audit-boot"
    version = "1.0.0"
    signature = "sig-abc"
    targets = ("debian-12",)
    privileges = ("read-boot-log",)
    risk = RiskClass.READ_ONLY
    capabilities = _capabilities("DIAGNOSTICS")
    dependencies = ()
    collectors = ("distro",)
    preconditions = ("boot-completed",)
    postconditions = ("boot-log-observed",)
    verification = "compare Facts against declared Postconditions"


def _lookalike():
    return _LookAlikeManifest()


def _loaded(**manifest_overrides):
    return load(
        _manifest(**manifest_overrides),
        verifier=_verifier(),
        policy=_policy(),
    )


# --- Public surface and structure ---


def test_public_surface_is_exactly_the_owned_loading_mechanics():
    mod = importlib.import_module("episky.skills.loader")
    assert set(mod.__all__) == EXPECTED_PUBLIC_SURFACE


def test_every_owned_type_is_a_frozen_slotted_dataclass():
    for cls in OWNED_DATACLASSES:
        params = cls.__dataclass_params__
        assert params.frozen, f"{cls.__name__} is not frozen"
        assert params.slots, f"{cls.__name__} is not slot-based"


def test_owned_types_keep_no_hidden_module_state():
    mod = importlib.import_module("episky.skills.loader")
    mutable_globals = {
        name
        for name, value in vars(mod).items()
        if isinstance(value, (list, dict, set))
        and not (name.startswith("__") and name.endswith("__"))
    }
    assert not mutable_globals


# --- The capability and stage/refusal vocabularies ---


def test_capability_vocabulary_is_the_fixed_six_in_order():
    assert tuple(SkillCapability) == EXPECTED_CAPABILITIES


def test_no_capability_implies_an_authority_or_an_action():
    for name in SkillCapability.__members__:
        assert "approve" not in name.lower()
        assert "execute" not in name.lower()
        assert "permit" not in name.lower()
        assert "grant" not in name.lower()


def test_stage_vocabulary_is_the_fixed_registered_stage():
    assert tuple(SkillStage) == (SkillStage.REGISTERED,)


def test_refusal_vocabulary_is_the_fixed_six_in_order():
    assert tuple(LoadRefusal) == EXPECTED_REFUSALS


def test_disposition_vocabulary_is_loaded_and_refused():
    assert tuple(LoadDisposition) == (
        LoadDisposition.LOADED,
        LoadDisposition.REFUSED,
    )


def test_load_outcome_is_immutable():
    outcome = _loaded()
    with pytest.raises(FrozenInstanceError):
        outcome.disposition = LoadDisposition.REFUSED


# --- Loading: exactly a declared surface, nothing else (RFC-0011 §22) ---


def test_load_admits_a_declared_manifest():
    outcome = load(_manifest(), verifier=_verifier(), policy=_policy())
    assert outcome.disposition is LoadDisposition.LOADED
    assert outcome.refusal is None
    assert outcome.reason
    assert outcome.skill is not None


def test_load_refuses_a_surface_shaped_lookalike():
    outcome = load(_lookalike(), verifier=_verifier(), policy=_policy())
    assert outcome.disposition is LoadDisposition.REFUSED
    assert outcome.refusal is LoadRefusal.MALFORMED_SURFACE
    assert outcome.skill is None


def test_load_refuses_none_and_every_non_manifest_value():
    for sample in (None, 42, "a skill filename", b"packaged", [], (), {"name": "x"}):
        outcome = load(sample, verifier=_verifier(), policy=_policy())
        assert outcome.disposition is LoadDisposition.REFUSED, sample
        assert outcome.refusal is LoadRefusal.MALFORMED_SURFACE, sample


def test_load_is_deterministic():
    assert load(_manifest(), verifier=_verifier(), policy=_policy()) == load(
        _manifest(), verifier=_verifier(), policy=_policy()
    )
    assert load(_lookalike(), verifier=_verifier(), policy=_policy()) == load(
        _lookalike(), verifier=_verifier(), policy=_policy()
    )


def test_load_reason_is_loud():
    outcome = load(_lookalike(), verifier=_verifier(), policy=_policy())
    assert "manifest" in outcome.reason


# --- Authentication: unauthenticated is never loaded (SK5; RFC-0002 §4.7) ---


def test_missing_verifier_fails_closed_as_unauthenticated():
    outcome = load(_manifest())
    assert outcome.disposition is LoadDisposition.REFUSED
    assert outcome.refusal is LoadRefusal.UNAUTHENTICATED


def test_unauthenticated_verdict_refuses_the_load():
    outcome = load(
        _manifest(),
        verifier=_verifier(AuthenticationVerdict.UNAUTHENTICATED),
        policy=_policy(),
    )
    assert outcome.disposition is LoadDisposition.REFUSED
    assert outcome.refusal is LoadRefusal.UNAUTHENTICATED
    assert outcome.skill is None


def test_a_manifest_without_a_signature_is_unauthenticated():
    outcome = load(
        _manifest(signature=""),
        verifier=_verifier(),
        policy=_policy(),
    )
    assert outcome.disposition is LoadDisposition.REFUSED
    assert outcome.refusal is LoadRefusal.UNAUTHENTICATED


def test_unauthenticated_load_substitutes_nothing():
    outcome = load(
        _manifest(),
        verifier=_verifier(AuthenticationVerdict.UNAUTHENTICATED),
        policy=_policy(),
    )
    assert outcome.skill is None


# --- Declaration validation (RFC-0011 §22; RFC-0001 §11.3) ---


def test_empty_targets_are_invalid():
    outcome = load(_manifest(targets=()), verifier=_verifier(), policy=_policy())
    assert outcome.disposition is LoadDisposition.REFUSED
    assert outcome.refusal is LoadRefusal.INVALID_DECLARATION


def test_empty_privileges_are_invalid():
    outcome = load(_manifest(privileges=()), verifier=_verifier(), policy=_policy())
    assert outcome.disposition is LoadDisposition.REFUSED
    assert outcome.refusal is LoadRefusal.INVALID_DECLARATION


def test_empty_capabilities_are_invalid():
    outcome = load(
        _manifest(capabilities=frozenset()),
        verifier=_verifier(),
        policy=_policy(),
    )
    assert outcome.disposition is LoadDisposition.REFUSED
    assert outcome.refusal is LoadRefusal.INVALID_DECLARATION


def test_a_capability_outside_the_fixed_vocabulary_is_invalid():
    outcome = load(
        _manifest(capabilities=frozenset({"BOGUS"})),
        verifier=_verifier(),
        policy=_policy(),
    )
    assert outcome.disposition is LoadDisposition.REFUSED
    assert outcome.refusal is LoadRefusal.INVALID_DECLARATION


def test_empty_preconditions_are_invalid():
    outcome = load(_manifest(preconditions=()), verifier=_verifier(), policy=_policy())
    assert outcome.disposition is LoadDisposition.REFUSED
    assert outcome.refusal is LoadRefusal.INVALID_DECLARATION


def test_empty_postconditions_are_invalid():
    outcome = load(_manifest(postconditions=()), verifier=_verifier(), policy=_policy())
    assert outcome.disposition is LoadDisposition.REFUSED
    assert outcome.refusal is LoadRefusal.INVALID_DECLARATION


def test_empty_verification_approach_is_invalid():
    outcome = load(_manifest(verification="  "), verifier=_verifier(), policy=_policy())
    assert outcome.disposition is LoadDisposition.REFUSED
    assert outcome.refusal is LoadRefusal.INVALID_DECLARATION


def test_an_untyped_risk_is_invalid():
    outcome = load(_manifest(risk="READ_ONLY"), verifier=_verifier(), policy=_policy())
    assert outcome.disposition is LoadDisposition.REFUSED
    assert outcome.refusal is LoadRefusal.INVALID_DECLARATION


def test_a_manifest_without_identity_is_malformed():
    for overrides in ({"name": ""}, {"version": ""}, {"signature": ""}):
        if overrides == {"signature": ""}:
            continue
        outcome = load(_manifest(**overrides), verifier=_verifier(), policy=_policy())
        assert outcome.disposition is LoadDisposition.REFUSED
        assert outcome.refusal is LoadRefusal.MALFORMED_SURFACE


# --- Dependencies (RFC-0011 §9) ---


def test_an_unpinned_dependency_is_invalid():
    outcome = load(
        _manifest(dependencies=_dependencies(("boot-checks", ""))),
        verifier=_verifier(),
        policy=_policy(),
    )
    assert outcome.disposition is LoadDisposition.REFUSED
    assert outcome.refusal is LoadRefusal.INVALID_DEPENDENCY


def test_a_nameless_dependency_is_invalid():
    outcome = load(
        _manifest(dependencies=_dependencies(("", "1.0"))),
        verifier=_verifier(),
        policy=_policy(),
    )
    assert outcome.disposition is LoadDisposition.REFUSED
    assert outcome.refusal is LoadRefusal.INVALID_DEPENDENCY


def test_a_dependency_on_itself_is_rejected():
    outcome = load(
        _manifest(
            dependencies=_dependencies(("audit-boot", "2.0.0")),
        ),
        verifier=_verifier(),
        policy=_policy(),
    )
    assert outcome.disposition is LoadDisposition.REFUSED
    assert outcome.refusal is LoadRefusal.INVALID_DEPENDENCY


def test_pinned_external_dependencies_are_accepted():
    outcome = load(
        _manifest(dependencies=_dependencies(("boot-checks", "1.0.0"))),
        verifier=_verifier(),
        policy=_policy(),
    )
    assert outcome.disposition is LoadDisposition.LOADED


# --- Bundled Collectors validated against the registry (RFC-0011 §11) ---


def test_a_bundled_collector_not_in_the_registry_is_refused():
    outcome = load(
        _manifest(collectors=("no-such-collector",)),
        verifier=_verifier(),
        policy=_policy(),
    )
    assert outcome.disposition is LoadDisposition.REFUSED
    assert outcome.refusal is LoadRefusal.UNKNOWN_COLLECTOR


def test_bundled_collectors_in_the_registry_are_accepted():
    outcome = load(
        _manifest(collectors=tuple(sorted(COLLECTOR_SPECS))),
        verifier=_verifier(),
        policy=_policy(),
    )
    assert outcome.disposition is LoadDisposition.LOADED


# --- Policy is checked before activation (RFC-0008; RFC-0011 §22) ---


def test_a_refused_policy_decision_blocks_the_load():
    outcome = load(
        _manifest(),
        verifier=_verifier(),
        policy=_policy(PolicyVerdict.REFUSED),
    )
    assert outcome.disposition is LoadDisposition.REFUSED
    assert outcome.refusal is LoadRefusal.POLICY_DENIED
    assert outcome.skill is None


def test_a_missing_policy_decision_fails_closed():
    outcome = load(_manifest(), verifier=_verifier())
    assert outcome.disposition is LoadDisposition.REFUSED
    assert outcome.refusal is LoadRefusal.POLICY_DENIED


def test_a_permitted_policy_decision_loads():
    outcome = load(
        _manifest(),
        verifier=_verifier(),
        policy=_policy(PolicyVerdict.PERMITTED),
    )
    assert outcome.disposition is LoadDisposition.LOADED


# --- The loaded Skill: registered, surface-riding, authority-free (§19; §4) ---


def test_a_loaded_skill_is_registered_with_the_core_enumeration():
    outcome = _loaded()
    assert outcome.disposition is LoadDisposition.LOADED
    assert outcome.skill.stage is SkillStage.REGISTERED
    assert outcome.skill.manifest.name == "audit-boot"
    assert outcome.skill.manifest.version == "1.0.0"
    assert outcome.skill.manifest.signature == "sig-abc"


def test_a_loaded_skill_keeps_the_validated_surface_unchanged():
    manifest = _manifest()
    outcome = load(manifest, verifier=_verifier(), policy=_policy())
    assert outcome.skill.manifest is manifest
    assert outcome.skill.manifest.targets == manifest.targets
    assert outcome.skill.manifest.privileges == manifest.privileges
    assert outcome.skill.manifest.capabilities == manifest.capabilities


def test_a_loaded_skill_carries_no_authority_and_no_execution_surface():
    fields = set(Skill.__dataclass_fields__)
    assert fields == {"manifest", "stage"}
    assert not {
        "approve",
        "execution",
        "permission",
        "grant",
        "proceed",
        "execute",
    } & set(SkillManifest.__dataclass_fields__)


def test_duplicate_identity_is_deterministic():
    assert _loaded() == _loaded()


def test_loading_does_not_register_a_secret_shaped_value():
    lookalike = _LookAlikeManifest()
    lookalike.__dict__["secret"] = "sk-0123"
    outcome = load(lookalike, verifier=_verifier(), policy=_policy())
    assert outcome.disposition is LoadDisposition.REFUSED
    assert outcome.refusal is LoadRefusal.MALFORMED_SURFACE
    assert outcome.skill is None


# --- Conformance: imports, no I/O, no reasoning/sanitizing/verification ---


def test_loader_imports_only_the_allowed_layers():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    episky_imports = sorted({name for name in imported if name.startswith("episky")})
    assert episky_imports == [
        "episky.collectors.registry",
        "episky.policy.classify",
    ]


def test_loader_calls_no_classify_sanitize_verify_execute_or_verifier():
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


def test_loader_never_reads_a_clock_or_randomness():
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


def test_loader_generates_no_serialization_or_persistence():
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


def test_loader_performs_no_io_and_calls_no_forbidden_builtin():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            calls.add(func.id if isinstance(func, ast.Name) else func.attr)
    assert calls.isdisjoint({"open", "print", "input", "exec", "eval", "breakpoint"})


def test_loader_never_imports_execution_verification_an_audit_or_secrets():
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
                "episky.providers",
                "episky.core",
            )
        )
        for name in imported
    )
