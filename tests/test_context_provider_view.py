"""Deterministic Provider View derivation (RFC-0010 §3, §11; RFC-0012 §13,
§27; RFC-0007 §12; RFC-0002 I-4; RFC-0007 S7).

Behavioral tests for Iteration 9 Commit C4 (`context/provider_view.py`): the
pure projection from the assembled Context to the Provider View — the only
outward channel (PR14) — carrying exactly the RFC-0010 §3 elements (Operator
Goal, evidence/Allowed Context, Conversation State, routing state) and
nothing else (no Audit, no secrets, no raw output, no provider identity;
SC3). The projection derives entirely from Context: it invents nothing,
reasons over nothing, classifies nothing, sanitizes nothing, verifies
nothing, and calls no provider — it selects the already-bounded,
already-purpose-limited, already-labeled material into an immutable,
disposable semantic representation (RFC-0007 §12; DN-68). Deterministic and
value-preserving: the same Context always yields the same View (S7), in the
Context's order. Fail-closed: a Stale working set is rebuilt, never
projected (RFC-0012 §16.2; RFC-0002 §2.4), and a blank Goal statement is
malformed; refusals are explicit and disclosed, never silent (RFC-0001
§8.12). No I/O, no clock read, no randomness, no serialization, no `audit`
import (CM15).
"""

import ast
import importlib
import pathlib
from dataclasses import FrozenInstanceError, replace
from datetime import datetime

import pytest

from episky.context.assemble import (
    ContextState,
    EvidenceLabel,
    GoalValue,
    HistoryLabel,
    RoutingMarker,
    TurnRecord,
    assemble,
    mark_stale,
)
from episky.context.provider_view import (
    ProviderView,
    ProviderViewOutcome,
    ViewDisposition,
    ViewRefusal,
    derive,
)
from episky.factlayer.store import FactIdentity, FactStore
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
from episky.schema.outcome import VerificationOutcome

PROVIDER_VIEW_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "context"
    / "provider_view.py"
)

NOW = datetime(2026, 8, 7, 12, 0, 0)

PURPOSE = "diagnose boot failure"

MACHINE_IDENTITY = MachineIdentity()

EXPECTED_PUBLIC_SURFACE = {
    "ProviderView",
    "ProviderViewOutcome",
    "ViewDisposition",
    "ViewRefusal",
    "derive",
}


def _fact(
    subject="systemd",
    property="running-state",
    value="running",
    status=FactStatus.OBSERVED,
    freshness=FreshnessState.CURRENT,
    collected_at=NOW,
):
    return Fact(
        scope=Scope(
            subject=Subject(name=subject),
            property=Property(name=property),
            value=Value(value=value),
        ),
        status=status,
        confidence=ConfidenceSource(name="systemctl-is-active"),
        provenance=Provenance(
            observation=ObservationReference(),
            collector=Collector(name="systemd-state", version="1"),
            collected_at=collected_at,
        ),
        freshness=Freshness(state=freshness),
        machine_identity=MACHINE_IDENTITY,
    )


def _store(*facts):
    current = {}
    for fact in facts:
        identity = FactIdentity(
            machine_identity=fact.machine_identity,
            subject=fact.scope.subject,
            property=fact.scope.property,
        )
        current[identity] = fact
    return FactStore(machine_identity=MACHINE_IDENTITY, current=current)


def _goal(statement="repair the boot", scope="boot configuration"):
    return GoalValue(statement=statement, scope=scope)


def _turn(
    content="the machine fails to boot",
    label=HistoryLabel.OPERATOR_INPUT,
    purpose=PURPOSE,
):
    return TurnRecord(content=content, label=label, purpose=purpose)


def _evidence(outcome=VerificationOutcome.VERIFIED_SUCCESS, purpose=PURPOSE):
    return EvidenceLabel(outcome=outcome, purpose=purpose)


def _routing(outstanding_question=None, current_decision="decision-1"):
    return RoutingMarker(
        outstanding_question=outstanding_question,
        current_decision=current_decision,
    )


def _assemble(
    goal=None,
    store=None,
    *,
    purpose=PURPOSE,
    history=(),
    evidence=(),
    routing=None,
):
    return assemble(
        goal=_goal() if goal is None else goal,
        fact_store=_store(_fact()) if store is None else store,
        purpose=purpose,
        history=history,
        evidence=evidence,
        routing=_routing() if routing is None else routing,
    )


def _context(**kwargs):
    return _assemble(**kwargs).context


# --- Public surface and structure ---


def test_provider_view_public_surface_is_exactly_the_owned_vocabulary():
    mod = importlib.import_module("episky.context.provider_view")
    assert set(mod.__all__) == EXPECTED_PUBLIC_SURFACE


def test_every_owned_type_is_a_frozen_slotted_dataclass():
    for cls in (ProviderView, ProviderViewOutcome):
        params = cls.__dataclass_params__
        assert params.frozen, f"{cls.__name__} is not frozen"
        assert params.slots, f"{cls.__name__} is not slot-based"


def test_disposition_enum_is_exactly_derived_and_refused():
    assert tuple(ViewDisposition) == (
        ViewDisposition.DERIVED,
        ViewDisposition.REFUSED,
    )


def test_refusal_enum_is_the_fixed_fail_closed_reasons():
    assert tuple(ViewRefusal) == (
        ViewRefusal.STALE_WORKING_SET,
        ViewRefusal.MALFORMED,
    )


def test_provider_view_is_immutable():
    view = derive(_context()).view
    with pytest.raises(FrozenInstanceError):
        view.goal = _goal(statement="other")


def test_provider_view_outcome_is_immutable():
    outcome = derive(_context())
    with pytest.raises(FrozenInstanceError):
        outcome.view = None
    with pytest.raises(FrozenInstanceError):
        outcome.reason = "other"


def test_derived_outcome_carries_an_immutable_view():
    outcome = derive(_context())
    view = outcome.view
    with pytest.raises(FrozenInstanceError):
        view.facts = ()


# --- The projection: exactly the §3 elements (RFC-0010 §3; PR14) ---


def test_view_fields_are_exactly_the_five_s3_elements():
    assert set(ProviderView.__dataclass_fields__) == {
        "goal",
        "facts",
        "history",
        "evidence",
        "routing",
    }


def test_view_carries_the_operator_goal():
    context = _context(
        goal=_goal(statement="repair the boot", scope="boot configuration")
    )
    view = derive(context).view
    assert view.goal == context.goal
    assert view.goal.statement == "repair the boot"
    assert view.goal.scope == "boot configuration"


def test_view_carries_the_allowed_context_facts():
    context = _context()
    view = derive(context).view
    assert view.facts == context.facts
    assert view.facts is context.facts  # derived, not copied or transformed


def test_view_carries_the_conversation_state_history():
    turns = (
        _turn(content="the machine fails to boot"),
        _turn(
            content="systemd is running",
            label=HistoryLabel.PROVIDER_REPLY,
            purpose=PURPOSE,
        ),
    )
    context = _context(history=turns)
    view = derive(context).view
    assert view.history == context.history
    assert view.history == turns


def test_view_carries_the_evidence():
    context = _context(evidence=(_evidence(), _evidence(VerificationOutcome.UNKNOWN)))
    view = derive(context).view
    assert view.evidence == context.evidence


def test_view_carries_the_routing_state():
    context = _context(routing=_routing(outstanding_question="which step failed?"))
    view = derive(context).view
    assert view.routing == context.routing
    assert view.routing.outstanding_question == "which step failed?"


def test_view_carries_the_same_material_identity_as_context():
    context = _context()
    view = derive(context).view
    assert view.goal is context.goal
    assert view.history is context.history
    assert view.evidence is context.evidence
    assert view.routing is context.routing


# --- Ordering is deterministic (RFC-0007 S7) ---


def test_projection_preserves_the_context_ordering():
    turns = (
        _turn(content="first"),
        _turn(content="second", label=HistoryLabel.PROVIDER_REPLY),
        _turn(content="third"),
    )
    context = _context(history=turns)
    view = derive(context).view
    assert [turn.content for turn in view.history] == ["first", "second", "third"]


def test_projection_preserves_fact_order():
    store = _store(
        _fact(subject="network", property="link", value="up", collected_at=NOW),
        _fact(
            subject="systemd",
            property="running-state",
            value="running",
            collected_at=NOW,
        ),
    )
    context = _assemble(store=store).context
    view = derive(context).view
    assert [fact.scope.subject.name for fact in view.facts] == [
        fact.scope.subject.name for fact in context.facts
    ]


# --- Determinism and equality (RFC-0007 S7) ---


def test_derive_is_deterministic():
    context = _context()
    assert derive(context) == derive(context)
    assert derive(context).view == derive(context).view


def test_equal_contexts_yield_equal_views():
    store = _store(_fact())
    left = _assemble(store=store).context
    right = _assemble(store=store).context
    assert left == right
    assert derive(left) == derive(right)


def test_different_material_yields_different_views():
    plain = _context()
    extra = _context(history=(_turn(content="an extra turn"),))
    assert derive(plain).view != derive(extra).view


def test_repeated_projection_of_identical_context_is_identical():
    context = _context(
        history=(_turn(), _turn(label=HistoryLabel.HYPOTHESIS)),
        evidence=(_evidence(),),
    )
    outcomes = [derive(context) for _ in range(3)]
    assert outcomes[0] == outcomes[1] == outcomes[2]


# --- Fail-closed behaviour (RFC-0012 §16.2; RFC-0002 §2.4) ---


def test_a_stale_working_set_is_refused_not_projected():
    context = _context()
    stale = mark_stale(context, reason="boot state changed")[0]
    outcome = derive(stale)
    assert outcome.disposition is ViewDisposition.REFUSED
    assert outcome.refusal is ViewRefusal.STALE_WORKING_SET
    assert outcome.view is None
    assert outcome.reason


def test_a_stale_refusal_discloses_the_reason():
    stale = replace(_context(), state=ContextState.STALE)
    outcome = derive(stale)
    assert outcome.reason
    assert "Stale" in outcome.reason


def test_a_blank_goal_statement_is_refused_as_malformed():
    context = replace(
        _context(),
        goal=GoalValue(statement="   ", scope="boot configuration"),
    )
    outcome = derive(context)
    assert outcome.disposition is ViewDisposition.REFUSED
    assert outcome.refusal is ViewRefusal.MALFORMED
    assert outcome.view is None
    assert outcome.reason


def test_a_consolidated_set_is_still_projectable():
    context = replace(_context(), state=ContextState.CONSOLIDATED)
    outcome = derive(context)
    assert outcome.disposition is ViewDisposition.DERIVED
    assert outcome.refusal is None


def test_a_current_set_is_projectable():
    context = _context()
    outcome = derive(context)
    assert outcome.disposition is ViewDisposition.DERIVED
    assert outcome.refusal is None
    assert outcome.view is not None


# --- The View is derived, never forwarded or transformed ---


def test_the_view_is_the_contained_material_not_a_copy():
    context = _context(
        history=(_turn(content="quoted content"),),
    )
    view = derive(context).view
    assert view.history is context.history
    assert view.history[0].content == "quoted content"


def test_the_view_invents_nothing():
    context = _context()
    view = derive(context).view
    assert view.goal == context.goal
    assert view.facts == context.facts
    assert view.history == context.history
    assert view.evidence == context.evidence
    assert view.routing == context.routing


def test_the_view_carries_no_audit_or_provider_identity_surface():
    fields = set(ProviderView.__dataclass_fields__)
    assert not {"audit", "transcript", "provider", "vendor", "secret", "token"} & fields


def test_a_secret_shaped_value_in_context_stays_out_of_any_new_surface():
    context = _context()
    view = derive(context).view
    for field in ("audit", "transcript", "provider", "vendor", "secret", "token"):
        assert not hasattr(view, field)


# --- Immutability and no hidden state ---


def test_the_context_is_left_unchanged_by_projection():
    context = _context(
        history=(_turn(content="keep me"),),
    )
    derive(context)
    assert [turn.content for turn in context.history] == ["keep me"]
    assert context.state is ContextState.CURRENT


def test_view_collections_are_immutable():
    view = derive(_context()).view
    assert isinstance(view.facts, tuple)
    assert isinstance(view.history, tuple)
    assert isinstance(view.evidence, tuple)
    with pytest.raises((FrozenInstanceError, TypeError)):
        view.facts[0].scope.value.value = "other"


def test_provider_view_keeps_no_hidden_module_state():
    mod = importlib.import_module("episky.context.provider_view")
    mutable_globals = {
        name
        for name, value in vars(mod).items()
        if isinstance(value, (list, dict, set))
        and not (name.startswith("__") and name.endswith("__"))
    }
    assert not mutable_globals
    context = _context()
    assert derive(context) == derive(context)


def test_provider_view_holds_no_decision_methods():
    for cls in (ProviderView, ProviderViewOutcome):
        for name, attr in vars(cls).items():
            if name.startswith("__") and name.endswith("__"):
                continue
            assert not callable(attr), (
                f"{cls.__name__} exposes {name!r}: the View is a projection, "
                "not a decision maker"
            )


# --- Conformance: imports, no reasoning/sanitizing/verification/providers ---


def test_provider_view_imports_only_the_allowed_packages():
    tree = ast.parse(PROVIDER_VIEW_PATH.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    episky_imports = sorted({name for name in imported if name.startswith("episky")})
    assert episky_imports == ["episky.context.assemble", "episky.schema.fact"]


def test_provider_view_calls_no_classify_sanitize_verify_or_provider():
    tree = ast.parse(PROVIDER_VIEW_PATH.read_text(encoding="utf-8"))
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            calls.add(func.id if isinstance(func, ast.Name) else func.attr)
    forbidden = {
        "classify",
        "sanitize",
        "admit",
        "verify",
        "compare",
        "observe",
        "collect",
        "invoke",
        "request",
        "send",
        "fetch",
        "query",
    }
    assert not calls & forbidden
    assert not calls & {"subprocess", "os.system", "socket", "requests", "urllib"}


def test_provider_view_never_reads_a_clock_or_randomness():
    src = PROVIDER_VIEW_PATH.read_text(encoding="utf-8")
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


def test_provider_view_generates_no_serialization_or_persistence():
    src = PROVIDER_VIEW_PATH.read_text(encoding="utf-8")
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


def test_provider_view_performs_no_io_and_calls_no_forbidden_builtin():
    tree = ast.parse(PROVIDER_VIEW_PATH.read_text(encoding="utf-8"))
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            calls.add(func.id if isinstance(func, ast.Name) else func.attr)
    assert calls.isdisjoint({"open", "print", "input", "exec", "eval", "breakpoint"})


def test_provider_view_never_imports_audit():
    tree = ast.parse(PROVIDER_VIEW_PATH.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert not any(
        name.startswith(
            ("episky.audit", "episky.providers", "episky.policy", "episky.executor")
        )
        for name in imported
    )
