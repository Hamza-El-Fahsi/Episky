"""Provider boundary, capability model, lifecycle, and failure classification
(RFC-0010 §3, §5, §6, §7, §8; RFC-0002 §4.3, invariant 4; RFC-0012 §13, §27;
RFC-0007 S7, T3; RFC-0009 SC3; RFC-0005 F6).

Behavioral tests for Iteration 10 Commit C2 (`providers/view.py`): the
deterministic mechanics the Core uses to drive a provider. It consumes
exactly the Provider View built by `context` and nothing else (PR14; RFC-0002
invariant 4; RFC-0012 §13, §27) — an Audit record, a secret-shaped value, raw
output, or a provider identity is refused because none of it may cross (SC3).
The capability vocabulary (§5) is the fixed eight-member set, declared at
registration and carrying no authority (PR12; §5.4). The §6 negotiation
adapts deterministically off the declaration — never the vendor. The §7
lifecycle (REGISTERED → ACTIVATED → REMOVED) is deterministic and fail-closed:
an empty declaration is MALFORMED_DECLARATION, a declaration without the
minimum Reasoning capability is UNUSABLE and can never activate, and every
illegal transition refuses without crashing (PR11). The §8 failure modes
classify into the RFC-0002 §4.3 events honestly (PR16, no fabricated
recommendation) and degrade, never crash (PR11). Deterministic (RFC-0007 S7).

The package performs no I/O, no network call, no clock read, no randomness,
no serialization, no subprocess, and imports only `context` — never `audit`,
`executor`, `policy`, `verification`, or a vendor adapter (DNS-76, DNS-78).
"""

import ast
import importlib
import pathlib
from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from episky.context.assemble import (
    GoalValue,
    HistoryLabel,
    RoutingMarker,
    TurnRecord,
    assemble,
)
from episky.context.provider_view import derive
from episky.factlayer.store import FactIdentity, FactStore
from episky.providers.view import (
    CapabilityDeclaration,
    Consumption,
    ConsumptionDisposition,
    ConsumptionRefusal,
    LifecycleDisposition,
    LifecycleOutcome,
    LifecycleRefusal,
    Negotiation,
    ProviderCapability,
    ProviderEvent,
    ProviderFailure,
    ProviderLifecycle,
    ProviderStage,
    RequestKind,
    activate,
    classify,
    consume,
    declare,
    negotiate,
    register,
    remove,
)
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

SOURCE = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "providers"
    / "view.py"
)

NOW = datetime(2026, 8, 7, 12, 0, 0)

PURPOSE = "diagnose boot failure"

MACHINE_IDENTITY = MachineIdentity()

EXPECTED_PUBLIC_SURFACE = {
    "CapabilityDeclaration",
    "Consumption",
    "ConsumptionDisposition",
    "ConsumptionRefusal",
    "LifecycleDisposition",
    "LifecycleOutcome",
    "LifecycleRefusal",
    "Negotiation",
    "ProviderCapability",
    "ProviderEvent",
    "ProviderFailure",
    "ProviderLifecycle",
    "ProviderStage",
    "RequestKind",
    "activate",
    "classify",
    "consume",
    "declare",
    "negotiate",
    "register",
    "remove",
}

EXPECTED_CAPABILITIES = (
    ProviderCapability.REASONING,
    ProviderCapability.TOOL_PLANNING,
    ProviderCapability.STREAMING,
    ProviderCapability.STRUCTURED_RESPONSES,
    ProviderCapability.LONG_CONTEXT,
    ProviderCapability.IMAGE_UNDERSTANDING,
    ProviderCapability.OFFLINE,
    ProviderCapability.LOCAL,
)

EXPECTED_STAGES = (
    ProviderStage.REGISTERED,
    ProviderStage.ACTIVATED,
    ProviderStage.REMOVED,
)

EXPECTED_FAILURES = (
    ProviderFailure.TIMEOUT,
    ProviderFailure.UNAVAILABLE,
    ProviderFailure.MALFORMED_OUTPUT,
    ProviderFailure.INCOMPLETE_PROPOSAL,
    ProviderFailure.UNSUPPORTED_CAPABILITY,
    ProviderFailure.HALLUCINATION,
    ProviderFailure.REFUSAL,
)

EXPECTED_EVENTS = (
    ProviderEvent.PROVIDER_RESPONSE,
    ProviderEvent.PROVIDER_REFUSAL,
    ProviderEvent.PROVIDER_UNAVAILABLE,
    ProviderEvent.PROVIDER_TIMEOUT,
    ProviderEvent.PROVIDER_FALLBACK_OK,
    ProviderEvent.PROVIDER_FALLBACK_FAILED,
)

OWNED_DATACLASSES = (
    CapabilityDeclaration,
    Consumption,
    LifecycleOutcome,
    Negotiation,
    ProviderLifecycle,
)


def _capabilities(*names):
    return frozenset(ProviderCapability[name] for name in names)


def _declaration(*names):
    return declare(_capabilities(*names))


def _registered(*names):
    return register(_capabilities(*names)).state


def _activated(*names):
    return activate(_registered(*names)).state


def _removed(*names):
    return remove(_registered(*names)).state


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
            collected_at=NOW,
        ),
        freshness=Freshness(state=FreshnessState.CURRENT),
        machine_identity=MACHINE_IDENTITY,
    )


def _view():
    fact = _fact()
    identity = FactIdentity(
        machine_identity=fact.machine_identity,
        subject=fact.scope.subject,
        property=fact.scope.property,
    )
    context = assemble(
        goal=GoalValue(statement="repair the boot", scope="boot configuration"),
        fact_store=FactStore(
            machine_identity=MACHINE_IDENTITY,
            current={identity: fact},
        ),
        purpose=PURPOSE,
        history=(
            TurnRecord(
                content="the machine fails to boot",
                label=HistoryLabel.OPERATOR_INPUT,
                purpose=PURPOSE,
            ),
        ),
        evidence=(),
        routing=RoutingMarker(outstanding_question=None, current_decision="decision-1"),
    ).context
    return derive(context).view


class _LookAlike_ViewLot:
    """A view-shaped value that is not :class:`ProviderView`."""

    goal = None
    facts = ()
    history = ()
    evidence = ()
    routing = None


def _lookalike():
    return _LookAlike_ViewLot()


# --- Public surface and structure ---


def test_public_surface_is_exactly_the_owned_provider_mechanics():
    mod = importlib.import_module("episky.providers.view")
    assert set(mod.__all__) == EXPECTED_PUBLIC_SURFACE


def test_every_owned_type_is_a_frozen_slotted_dataclass():
    for cls in OWNED_DATACLASSES:
        params = cls.__dataclass_params__
        assert params.frozen, f"{cls.__name__} is not frozen"
        assert params.slots, f"{cls.__name__} is not slot-based"


def test_owned_types_keep_no_hidden_module_state():
    mod = importlib.import_module("episky.providers.view")
    mutable_globals = {
        name
        for name, value in vars(mod).items()
        if isinstance(value, (list, dict, set))
        and not (name.startswith("__") and name.endswith("__"))
    }
    assert not mutable_globals


# --- The capability vocabulary (RFC-0010 §5) ---


def test_capability_vocabulary_is_the_fixed_eight_in_order():
    assert tuple(ProviderCapability) == EXPECTED_CAPABILITIES


def test_no_capability_leaks_a_vendor_name():
    vendor_names = {"anthropic", "openai", "google", "claude", "gpt", "gemini"}
    assert vendor_names.isdisjoint(
        name.lower() for name in ProviderCapability.__members__
    )


def test_declaration_is_immutable_vocabulary():
    declaration = _declaration("REASONING", "STREAMING")
    assert declaration.capabilities == _capabilities("REASONING", "STREAMING")
    with pytest.raises(AttributeError):
        declaration.capabilities = _capabilities("LOCAL")


def test_no_capability_names_an_authority_or_action():
    for name in ProviderCapability.__members__:
        assert "approve" not in name.lower()
        assert "execute" not in name.lower()


def test_declaration_snapshots_the_given_set():
    mutable = set(_capabilities("REASONING"))
    declaration = declare(mutable)
    mutable.add(ProviderCapability.LOCAL)
    assert ProviderCapability.LOCAL not in declaration.capabilities


# --- Consumption: exactly the Provider View, nothing else (PR14) ---


def test_consume_admits_exactly_the_provider_view_type():
    outcome = consume(_view())
    assert outcome.disposition is ConsumptionDisposition.CONSUMED
    assert outcome.refusal is None
    assert outcome.reason


def test_consume_refuses_a_view_shaped_lookalike():
    outcome = consume(_lookalike())
    assert outcome.disposition is ConsumptionDisposition.REFUSED
    assert outcome.refusal is ConsumptionRefusal.NOT_A_PROVIDER_VIEW


def test_consume_refuses_audit_and_secret_shaped_values():
    for sample in (
        _lookalike(),
        {"audit": "transcript", "provider": "vendor", "vendor": "openai"},
        {"secret": "sk-0123"},
        "a provider identity string",
        ("raw", "output"),
    ):
        outcome = consume(sample)
        assert outcome.disposition is ConsumptionDisposition.REFUSED, sample


def test_consume_refuses_none_and_every_non_view_runtime_value():
    for sample in (None, 42, "Bearer token", b"bytes", [], (), {"goal": None}):
        outcome = consume(sample)
        assert outcome.disposition is ConsumptionDisposition.REFUSED, sample


def test_consume_is_deterministic():
    assert consume(_view()) == consume(_view())
    assert consume(_lookalike()) == consume(_lookalike())


def test_consume_reason_is_loud():
    outcome = consume(_lookalike())
    assert "Provider View" in outcome.reason


# --- Lifecycle: the deterministic §7 transitions ---


def test_register_builds_a_registered_state():
    outcome = register(_capabilities("REASONING", "STREAMING"))
    assert outcome.disposition is LifecycleDisposition.TRANSITIONED
    assert outcome.refusal is None
    assert outcome.state.stage is ProviderStage.REGISTERED
    assert outcome.state.declaration.capabilities == _capabilities(
        "REASONING", "STREAMING"
    )


def test_register_an_empty_declaration_is_malformed():
    outcome = register(frozenset())
    assert outcome.disposition is LifecycleDisposition.REFUSED
    assert outcome.refusal is LifecycleRefusal.MALFORMED_DECLARATION
    assert outcome.state is None
    assert outcome.reason


def test_register_is_deterministic():
    capabilities = _capabilities("REASONING")
    assert register(capabilities) == register(capabilities)


def test_register_accepts_no_authority_decision():
    declaration = _registered("REASONING").declaration
    assert declaration.capabilities == _capabilities("REASONING")


def test_activate_a_registered_reasoning_provider():
    state = _registered("REASONING", "STREAMING")
    outcome = activate(state)
    assert outcome.disposition is LifecycleDisposition.TRANSITIONED
    assert outcome.refusal is None
    assert outcome.state.stage is ProviderStage.ACTIVATED
    assert outcome.state.declaration.capabilities == state.declaration.capabilities


def test_activate_an_unusable_provider_is_refused():
    state = _registered("STREAMING")
    outcome = activate(state)
    assert outcome.disposition is LifecycleDisposition.REFUSED
    assert outcome.refusal is LifecycleRefusal.UNUSABLE
    assert outcome.state is state


def test_activate_nothing_or_a_removed_state_is_illegal():
    removed = remove(_registered("REASONING")).state
    for target in (None, removed):
        outcome = activate(target)
        assert outcome.disposition is LifecycleDisposition.REFUSED, target
        assert outcome.refusal is LifecycleRefusal.ILLEGAL_TRANSITION, target


def test_activate_an_already_activated_state_is_illegal():
    active = _activated("REASONING")
    outcome = activate(active)
    assert outcome.disposition is LifecycleDisposition.REFUSED
    assert outcome.refusal is LifecycleRefusal.ILLEGAL_TRANSITION


def test_remove_a_registered_or_activated_provider():
    for target in (
        _registered("REASONING"),
        _activated("REASONING", "STREAMING"),
    ):
        outcome = remove(target)
        assert outcome.disposition is LifecycleDisposition.TRANSITIONED
        assert outcome.state.stage is ProviderStage.REMOVED


def test_remove_nothing_or_an_already_removed_state_is_illegal():
    removed = _removed("REASONING")
    for target in (None, removed):
        outcome = remove(target)
        assert outcome.disposition is LifecycleDisposition.REFUSED
        assert outcome.refusal is LifecycleRefusal.ILLEGAL_TRANSITION


def test_transitions_preserve_the_declared_capabilities():
    capabilities = _capabilities("REASONING", "OFFLINE")
    state = activate(_registered("REASONING", "OFFLINE")).state
    assert state.declaration.capabilities == capabilities


def test_lifecycle_state_is_immutable():
    state = _registered("REASONING")
    with pytest.raises(FrozenInstanceError):
        state.stage = ProviderStage.REMOVED


# --- Negotiation: the deterministic request shape (RFC-0010 §6) ---


def test_negotiation_asks_for_a_single_proposal_without_a_planner():
    assert negotiate(_declaration("REASONING")).request_kind is RequestKind.PROPOSAL


def test_negotiation_asks_for_a_plan_only_with_both_enablers():
    for names in (
        ("REASONING", "TOOL_PLANNING"),
        ("REASONING", "STRUCTURED_RESPONSES"),
    ):
        assert negotiate(_declaration(*names)).request_kind is RequestKind.PROPOSAL
    full = _declaration("REASONING", "TOOL_PLANNING", "STRUCTURED_RESPONSES")
    assert negotiate(full).request_kind is RequestKind.PLAN


def test_negotiation_expects_structured_only_when_declared():
    assert negotiate(_declaration("REASONING")).expects_structured is False
    assert (
        negotiate(_declaration("REASONING", "STRUCTURED_RESPONSES")).expects_structured
        is True
    )


def test_negotiation_is_deterministic():
    declaration = _declaration("REASONING", "TOOL_PLANNING", "STRUCTURED_RESPONSES")
    assert negotiate(declaration) == negotiate(declaration)


def test_negotiation_keys_off_declaration_never_the_vendor():
    assert set(Negotiation.__dataclass_fields__) == {
        "request_kind",
        "expects_structured",
    }


# --- Failure classification (RFC-0010 §8 -> RFC-0002 §4.3) ---


def test_every_failure_mode_classifies_to_an_event():
    for failure in ProviderFailure:
        assert classify(failure) in EXPECTED_EVENTS


def test_timeout_and_unavailable_keep_their_distinct_events():
    assert classify(ProviderFailure.TIMEOUT) is ProviderEvent.PROVIDER_TIMEOUT
    assert classify(ProviderFailure.UNAVAILABLE) is ProviderEvent.PROVIDER_UNAVAILABLE


def test_unusable_output_failures_all_report_a_refusal():
    degraded = (
        ProviderFailure.MALFORMED_OUTPUT,
        ProviderFailure.INCOMPLETE_PROPOSAL,
        ProviderFailure.UNSUPPORTED_CAPABILITY,
        ProviderFailure.HALLUCINATION,
        ProviderFailure.REFUSAL,
    )
    for failure in degraded:
        assert classify(failure) is ProviderEvent.PROVIDER_REFUSAL, failure


def test_classify_is_deterministic_and_total():
    for failure in ProviderFailure:
        assert classify(failure) == classify(failure)


def test_classify_never_fabricates_a_recommendation():
    for failure in ProviderFailure:
        assert classify(failure) not in (
            ProviderEvent.PROVIDER_RESPONSE,
            ProviderEvent.PROVIDER_FALLBACK_OK,
            ProviderEvent.PROVIDER_FALLBACK_FAILED,
        )


# --- Fail-close, no authority, no inference (PR-2, PR-3, PR-6, PR-9, F-6) ---


def test_owned_mechanics_hold_no_decision_methods():
    for cls in OWNED_DATACLASSES:
        for name, attr in vars(cls).items():
            if name.startswith("__") and name.endswith("__"):
                continue
            assert not callable(attr), f"{cls.__name__} must stay a pure value"


def test_no_owned_carrier_grants_authority_or_an_action():
    for cls in OWNED_DATACLASSES:
        fields = set(cls.__dataclass_fields__)
        assert (
            not {
                "approve",
                "approved",
                "permission",
                "grant",
                "execute",
                "proceed",
                "action",
            }
            & fields
        )


def test_failure_and_event_vocabularies_are_fixed_in_order():
    assert tuple(ProviderFailure) == EXPECTED_FAILURES
    assert tuple(ProviderEvent) == EXPECTED_EVENTS
    assert tuple(ProviderStage) == EXPECTED_STAGES


def test_lifecycle_vocabularies_are_fixed():
    assert tuple(ConsumptionDisposition) == (
        ConsumptionDisposition.CONSUMED,
        ConsumptionDisposition.REFUSED,
    )
    assert tuple(ConsumptionRefusal) == (ConsumptionRefusal.NOT_A_PROVIDER_VIEW,)
    assert tuple(LifecycleDisposition) == (
        LifecycleDisposition.TRANSITIONED,
        LifecycleDisposition.REFUSED,
    )
    assert tuple(LifecycleRefusal) == (
        LifecycleRefusal.ILLEGAL_TRANSITION,
        LifecycleRefusal.MALFORMED_DECLARATION,
        LifecycleRefusal.UNUSABLE,
    )


def test_request_kind_is_proposal_or_plan_only():
    assert tuple(RequestKind) == (RequestKind.PROPOSAL, RequestKind.PLAN)


# --- Conformance: imports, no reasoning/sanitizing/verification/providers ---


def test_view_imports_only_the_allowed_packages():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    episky_imports = sorted({name for name in imported if name.startswith("episky")})
    assert episky_imports == ["episky.context.provider_view"]


def test_view_calls_no_classify_sanitize_verify_execute_or_provider():
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
        "invalid_request",
        "send",
        "fetch",
        "query",
    }
    assert not calls & forbidden
    assert not calls & {"subprocess", "os.system", "socket", "requests", "urllib"}


def test_view_never_reads_a_clock_or_randomness():
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


def test_view_generates_no_serialization_or_persistence():
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


def test_view_performs_no_io_and_calls_no_forbidden_builtin():
    tree = ast.parse(SOURCE.read_text(encoding="utf-8"))
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            calls.add(func.id if isinstance(func, ast.Name) else func.attr)
    assert calls.isdisjoint({"open", "print", "input", "exec", "eval", "breakpoint"})


def test_view_never_imports_execution_verification_or_an_audit():
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
                "episky.policy",
                "episky.verification",
                "episky.collectors",
            )
        )
        for name in imported
    )
