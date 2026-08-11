"""RFC-0002 §4 event-catalog conformance (RFC-0002 §4; RFC-0013 §7).

Behavioral tests for Iteration 11 Commit C1 (`core/events.py`): the typed
§4.1–§4.7 catalog exists in full (DN-87, Q3), every event is a frozen,
slot-based dataclass carrying its `kind` and its RFC-0013 §7 record
`category`, and the per-event dispatch — the event → transition relation
declared once — matches the transcribed table exactly. The information-only
events (OP_VIEW, ACTION_STARTED, ACTION_CLASSIFIED) change no state in any
state and emit audited notes. Every consequential event carries the record
category it is written under, so the audit mapping is complete by construction
(AU3, AU6, I-13); `evolve` bundles each consequence with its `AuditRecord`, so
the record always precedes the consequence. Deterministic (RFC-0007 S7) and
I/O-free (DN-55, DN-94). The `Deadline` primitive (Q8) is data, never a clock.
"""

import ast
import importlib
import pathlib
from dataclasses import FrozenInstanceError

import pytest

from episky.core.events import (
    CATALOG,
    INFORMATION_ONLY,
    ActionPartial,
    AuditRecord,
    CollectorFailed,
    Deadline,
    EventKind,
    OpReply,
    PartialHalt,
    RecordCategory,
    Timeout,
    VerificationPassed,
)
from episky.core.state_machine import (
    GOAL_ACTIVE,
    Refusal,
    State,
    Transition,
    evolve,
    permitted,
)

EVENTS_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "core"
    / "events.py"
)

OPERATOR = (
    EventKind.OP_GOAL,
    EventKind.OP_REPLY,
    EventKind.OP_APPROVE,
    EventKind.OP_OVERRIDE,
    EventKind.OP_REJECT,
    EventKind.OP_REFINE,
    EventKind.OP_CANCEL,
    EventKind.OP_INTERRUPT,
    EventKind.OP_EXIT,
    EventKind.OP_VIEW,
)
MACHINE = (
    EventKind.FACTS_COLLECTED,
    EventKind.COLLECTOR_FAILED,
    EventKind.STATE_CHANGED_DETECTED,
)
PROVIDER = (
    EventKind.PROVIDER_RESPONSE,
    EventKind.PROVIDER_REFUSAL,
    EventKind.PROVIDER_UNAVAILABLE,
    EventKind.PROVIDER_TIMEOUT,
    EventKind.PROVIDER_FALLBACK_OK,
    EventKind.PROVIDER_FALLBACK_FAILED,
)
PLAN = (
    EventKind.PLAN_READY,
    EventKind.ACTION_CLASSIFIED,
    EventKind.ACTION_BLOCKED,
    EventKind.PLAN_REJECTED,
    EventKind.PLAN_REFINED,
)
EXECUTION = (
    EventKind.ACTION_STARTED,
    EventKind.ACTION_SUCCEEDED,
    EventKind.ACTION_FAILED,
    EventKind.ACTION_TIMEOUT,
    EventKind.ACTION_INTERRUPTED,
    EventKind.ACTION_PARTIAL,
)
VERIFICATION = (
    EventKind.VERIFICATION_PASSED,
    EventKind.VERIFICATION_FAILED,
    EventKind.VERIFICATION_INCONCLUSIVE,
)
SYSTEM = (
    EventKind.SKILL_UNAVAILABLE,
    EventKind.CONTEXT_FULL,
    EventKind.TIMEOUT,
    EventKind.REBOOT_REQUESTED,
    EventKind.REBOOT_DETECTED,
    EventKind.CONFIG_CHANGED,
)

_ALL_SELF = {s: s for s in State}

_COGNITIVE_SELF = {
    State.DIAGNOSING: State.DIAGNOSING,
    State.PLANNING: State.PLANNING,
    State.REPLANNING: State.REPLANNING,
}

#: The per-event dispatch as transcribed from RFC-0002 §4, keyed by kind. The
#: representative instances below drive these; a state absent from a mapping
#: means the event does not apply there (None).
EXPECTED_DISPATCH: dict[EventKind, dict[State, State]] = {
    EventKind.OP_GOAL: {
        State.IDLE: State.INSPECTING,
        State.AWAITING_INPUT: State.DIAGNOSING,
        State.COMPLETED: State.IDLE,
        State.FAILED: State.IDLE,
        State.CANCELLED: State.IDLE,
    },
    EventKind.OP_REPLY: {State.AWAITING_INPUT: State.DIAGNOSING},
    EventKind.OP_APPROVE: {State.AWAITING_APPROVAL: State.EXECUTING},
    EventKind.OP_OVERRIDE: {State.AWAITING_APPROVAL: State.EXECUTING},
    EventKind.OP_REJECT: {State.AWAITING_APPROVAL: State.REPLANNING},
    EventKind.OP_REFINE: {State.AWAITING_APPROVAL: State.REPLANNING},
    EventKind.OP_CANCEL: dict.fromkeys(GOAL_ACTIVE, State.CANCELLED),
    EventKind.OP_INTERRUPT: {
        State.INSPECTING: State.INTERRUPTED,
        State.EXECUTING: State.INTERRUPTED,
        State.VERIFYING: State.INTERRUPTED,
        State.AWAITING_APPROVAL: State.INTERRUPTED,
        State.BUILDING: State.AWAITING_INPUT,
        State.DIAGNOSING: State.AWAITING_INPUT,
        State.PLANNING: State.AWAITING_INPUT,
        State.REPLANNING: State.AWAITING_INPUT,
        State.AWAITING_INPUT: State.END,
        State.INTERRUPTED: State.END,
    },
    EventKind.OP_EXIT: {
        s: State.END for s in State if s not in (State.INITIALIZING, State.END)
    },
    EventKind.OP_VIEW: _ALL_SELF,
    EventKind.FACTS_COLLECTED: {State.INSPECTING: State.BUILDING},
    EventKind.COLLECTOR_FAILED: {State.INSPECTING: State.INSPECTING},
    EventKind.STATE_CHANGED_DETECTED: {
        **{s: s for s in State if s not in (State.END, State.AWAITING_APPROVAL)},
        State.AWAITING_APPROVAL: State.INSPECTING,
    },
    EventKind.PROVIDER_RESPONSE: _COGNITIVE_SELF,
    EventKind.PROVIDER_REFUSAL: _COGNITIVE_SELF,
    EventKind.PROVIDER_UNAVAILABLE: _COGNITIVE_SELF,
    EventKind.PROVIDER_TIMEOUT: _COGNITIVE_SELF,
    EventKind.PROVIDER_FALLBACK_OK: _COGNITIVE_SELF,
    EventKind.PROVIDER_FALLBACK_FAILED: {
        State.DIAGNOSING: State.AWAITING_INPUT,
        State.PLANNING: State.AWAITING_INPUT,
        State.REPLANNING: State.AWAITING_INPUT,
    },
    EventKind.PLAN_READY: {State.PLANNING: State.AWAITING_APPROVAL},
    EventKind.ACTION_CLASSIFIED: _ALL_SELF,
    EventKind.ACTION_BLOCKED: {State.AWAITING_APPROVAL: State.AWAITING_APPROVAL},
    EventKind.PLAN_REJECTED: {
        State.AWAITING_APPROVAL: State.AWAITING_APPROVAL,
        State.REPLANNING: State.REPLANNING,
    },
    EventKind.PLAN_REFINED: {
        State.AWAITING_APPROVAL: State.AWAITING_APPROVAL,
        State.REPLANNING: State.REPLANNING,
    },
    EventKind.ACTION_STARTED: _ALL_SELF,
    EventKind.ACTION_SUCCEEDED: {State.EXECUTING: State.VERIFYING},
    EventKind.ACTION_FAILED: {State.EXECUTING: State.VERIFYING},
    EventKind.ACTION_TIMEOUT: {State.EXECUTING: State.INTERRUPTED},
    EventKind.ACTION_INTERRUPTED: {State.EXECUTING: State.INTERRUPTED},
    EventKind.ACTION_PARTIAL: {State.EXECUTING: State.INTERRUPTED},
    EventKind.VERIFICATION_PASSED: {State.VERIFYING: State.COMPLETED},
    EventKind.VERIFICATION_FAILED: {State.VERIFYING: State.REPLANNING},
    EventKind.VERIFICATION_INCONCLUSIVE: {State.VERIFYING: State.AWAITING_INPUT},
    EventKind.SKILL_UNAVAILABLE: _COGNITIVE_SELF,
    EventKind.CONTEXT_FULL: {State.BUILDING: State.BUILDING},
    EventKind.TIMEOUT: {
        State.DIAGNOSING: State.AWAITING_INPUT,
        State.PLANNING: State.AWAITING_INPUT,
        State.REPLANNING: State.AWAITING_INPUT,
        State.INSPECTING: State.INTERRUPTED,
        State.EXECUTING: State.INTERRUPTED,
        State.VERIFYING: State.INTERRUPTED,
        State.AWAITING_APPROVAL: State.INTERRUPTED,
        State.BUILDING: State.BUILDING,
        State.AWAITING_INPUT: State.AWAITING_INPUT,
    },
    EventKind.REBOOT_REQUESTED: {State.EXECUTING: State.END},
    EventKind.REBOOT_DETECTED: {State.INITIALIZING: State.INSPECTING},
    EventKind.CONFIG_CHANGED: {s: s for s in State if s is not State.END},
}

#: The RFC-0013 §7 record category each event is written under (complete by
#: construction — AU3, AU6, I-13).
EXPECTED_CATEGORIES: dict[EventKind, RecordCategory] = {
    EventKind.OP_GOAL: RecordCategory.SESSION,
    EventKind.OP_REPLY: RecordCategory.PROPOSAL,
    EventKind.OP_APPROVE: RecordCategory.APPROVAL,
    EventKind.OP_OVERRIDE: RecordCategory.OVERRIDE,
    EventKind.OP_REJECT: RecordCategory.PROPOSAL,
    EventKind.OP_REFINE: RecordCategory.PROPOSAL,
    EventKind.OP_CANCEL: RecordCategory.SESSION,
    EventKind.OP_INTERRUPT: RecordCategory.SESSION,
    EventKind.OP_EXIT: RecordCategory.SESSION,
    EventKind.OP_VIEW: RecordCategory.OPERATOR_VISIBILITY,
    EventKind.FACTS_COLLECTED: RecordCategory.FACT_LIFECYCLE,
    EventKind.COLLECTOR_FAILED: RecordCategory.FACT_LIFECYCLE,
    EventKind.STATE_CHANGED_DETECTED: RecordCategory.FACT_LIFECYCLE,
    EventKind.PROVIDER_RESPONSE: RecordCategory.PROPOSAL,
    EventKind.PROVIDER_REFUSAL: RecordCategory.PROPOSAL,
    EventKind.PROVIDER_UNAVAILABLE: RecordCategory.PROPOSAL,
    EventKind.PROVIDER_TIMEOUT: RecordCategory.PROPOSAL,
    EventKind.PROVIDER_FALLBACK_OK: RecordCategory.PROPOSAL,
    EventKind.PROVIDER_FALLBACK_FAILED: RecordCategory.PROPOSAL,
    EventKind.PLAN_READY: RecordCategory.PROPOSAL,
    EventKind.ACTION_CLASSIFIED: RecordCategory.CLASSIFICATION,
    EventKind.ACTION_BLOCKED: RecordCategory.CLASSIFICATION,
    EventKind.PLAN_REJECTED: RecordCategory.PROPOSAL,
    EventKind.PLAN_REFINED: RecordCategory.PROPOSAL,
    EventKind.ACTION_STARTED: RecordCategory.EXECUTION,
    EventKind.ACTION_SUCCEEDED: RecordCategory.EXECUTION,
    EventKind.ACTION_FAILED: RecordCategory.EXECUTION,
    EventKind.ACTION_TIMEOUT: RecordCategory.EXECUTION,
    EventKind.ACTION_INTERRUPTED: RecordCategory.EXECUTION,
    EventKind.ACTION_PARTIAL: RecordCategory.EXECUTION,
    EventKind.VERIFICATION_PASSED: RecordCategory.VERIFICATION,
    EventKind.VERIFICATION_FAILED: RecordCategory.VERIFICATION,
    EventKind.VERIFICATION_INCONCLUSIVE: RecordCategory.VERIFICATION,
    EventKind.SKILL_UNAVAILABLE: RecordCategory.SKILL_EVENT,
    EventKind.CONTEXT_FULL: RecordCategory.CONTEXT_BOUNDARY,
    EventKind.TIMEOUT: RecordCategory.SESSION,
    EventKind.REBOOT_REQUESTED: RecordCategory.SESSION,
    EventKind.REBOOT_DETECTED: RecordCategory.SESSION,
    EventKind.CONFIG_CHANGED: RecordCategory.SESSION,
}


def _instance(cls):
    """A representative instance for each catalog class."""
    if cls is OpReply:
        return cls(routes_to=State.DIAGNOSING)
    if cls is ActionPartial:
        return cls(halt=PartialHalt.INTERRUPTED)
    if cls is VerificationPassed:
        return cls(steps_remaining=False)
    if cls is Timeout:
        return cls(deadline=Deadline(phase="provider"))
    return cls()


# --- The catalog ---


def test_events_public_surface_covers_catalog_and_support_types():
    mod = importlib.import_module("episky.core.events")
    names = set(mod.__all__)
    assert names == {
        "CATALOG",
        "INFORMATION_ONLY",
        "AuditRecord",
        "Deadline",
        "EventKind",
        "PartialHalt",
        "RecordCategory",
        "RuntimeEvent",
    } | {cls.__name__ for cls in CATALOG}


def test_event_kind_enum_is_the_full_catalog_in_order():
    assert tuple(EventKind) == (
        *OPERATOR,
        *MACHINE,
        *PROVIDER,
        *PLAN,
        *EXECUTION,
        *VERIFICATION,
        *SYSTEM,
    )


def test_catalog_is_the_section_4_catalog_in_order():
    assert len(CATALOG) == len(tuple(EventKind))
    assert tuple(cls.kind for cls in CATALOG) == tuple(EventKind)


def test_information_only_is_exactly_the_declared_set():
    assert (
        frozenset(
            {EventKind.OP_VIEW, EventKind.ACTION_STARTED, EventKind.ACTION_CLASSIFIED}
        )
        == INFORMATION_ONLY
    )


def test_record_category_enum_is_the_section_7_categories_in_order():
    assert tuple(RecordCategory) == (
        RecordCategory.SESSION,
        RecordCategory.PROPOSAL,
        RecordCategory.CLASSIFICATION,
        RecordCategory.APPROVAL,
        RecordCategory.OVERRIDE,
        RecordCategory.EXECUTION,
        RecordCategory.VERIFICATION,
        RecordCategory.FACT_LIFECYCLE,
        RecordCategory.CONTEXT_BOUNDARY,
        RecordCategory.SECRET_METADATA,
        RecordCategory.SKILL_EVENT,
        RecordCategory.OPERATOR_VISIBILITY,
    )


def test_every_event_is_a_frozen_slotted_dataclass():
    for cls in CATALOG:
        params = cls.__dataclass_params__
        assert params.frozen, f"{cls.__name__} is not frozen"
        assert params.slots, f"{cls.__name__} is not slot-based"


def test_data_carrying_events_declare_exactly_their_fields():
    assert set(OpReply.__dataclass_fields__) == {"routes_to"}
    assert set(CollectorFailed.__dataclass_fields__) == {"critical", "hopeless"}
    assert set(ActionPartial.__dataclass_fields__) == {"halt"}
    assert set(VerificationPassed.__dataclass_fields__) == {"steps_remaining"}
    assert set(Timeout.__dataclass_fields__) == {"deadline"}
    assert set(Deadline.__dataclass_fields__) == {"phase"}


def test_field_carrying_events_are_immutable():
    ev = OpReply(routes_to=State.DIAGNOSING)
    with pytest.raises(FrozenInstanceError):
        ev.routes_to = State.PLANNING


def test_the_deadline_is_data_not_a_clock():
    deadline = Deadline(phase="action")
    assert deadline.phase == "action"
    with pytest.raises(FrozenInstanceError):
        deadline.phase = "other"


# --- The audit mapping is complete (AU3, AU6, I-13) ---


@pytest.mark.parametrize("cls", CATALOG)
def test_every_event_declares_its_section_7_record_category(cls):
    assert cls.category is EXPECTED_CATEGORIES[cls.kind]


def test_every_consequential_event_has_a_record_category():
    for cls in CATALOG:
        assert isinstance(cls.category, RecordCategory)


# --- The per-event dispatch ---


@pytest.mark.parametrize("cls", CATALOG)
def test_per_event_dispatch_matches_the_declared_table(cls):
    ev = _instance(cls)
    expected = EXPECTED_DISPATCH[ev.kind]
    for state in State:
        assert ev.next_state(state) == expected.get(state)


def test_op_reply_routes_to_planning_for_a_direction_answer():
    ev = OpReply(routes_to=State.PLANNING)
    assert ev.next_state(State.AWAITING_INPUT) is State.PLANNING
    assert ev.next_state(State.IDLE) is None


def test_op_reply_routes_only_to_diagnosis_or_planning():
    with pytest.raises(ValueError):
        OpReply(routes_to=State.EXECUTING)
    with pytest.raises(ValueError):
        OpReply(routes_to=State.IDLE)


def test_collector_failed_branches():
    assert CollectorFailed().next_state(State.INSPECTING) is State.INSPECTING
    assert (
        CollectorFailed(critical=True).next_state(State.INSPECTING)
        is State.AWAITING_INPUT
    )
    assert CollectorFailed(hopeless=True).next_state(State.INSPECTING) is State.FAILED
    assert CollectorFailed(hopeless=True).critical is True
    assert CollectorFailed().next_state(State.EXECUTING) is None


def test_action_partial_branches_and_is_typed():
    with pytest.raises(TypeError):
        ActionPartial(halt="nope")
    assert (
        ActionPartial(halt=PartialHalt.CANCELLED).next_state(State.EXECUTING)
        is State.CANCELLED
    )
    assert (
        ActionPartial(halt=PartialHalt.INTERRUPTED).next_state(State.EXECUTING)
        is State.INTERRUPTED
    )
    assert ActionPartial(halt=PartialHalt.CANCELLED).next_state(State.IDLE) is None


def test_verification_passed_branches():
    assert (
        VerificationPassed(steps_remaining=True).next_state(State.VERIFYING)
        is State.EXECUTING
    )
    assert (
        VerificationPassed(steps_remaining=False).next_state(State.VERIFYING)
        is State.COMPLETED
    )
    assert VerificationPassed(steps_remaining=True).next_state(State.IDLE) is None


def test_timeout_is_typed_and_routes_by_phase_kind():
    with pytest.raises(TypeError):
        Timeout(deadline="nope")
    deadline = Deadline(phase="action")
    ev = Timeout(deadline=deadline)
    assert ev.deadline is deadline
    assert ev.next_state(State.EXECUTING) is State.INTERRUPTED
    assert ev.next_state(State.DIAGNOSING) is State.AWAITING_INPUT


def test_every_declared_transition_is_a_permitted_edge():
    for cls in CATALOG:
        ev = _instance(cls)
        for state in State:
            target = ev.next_state(state)
            if target is not None and target is not state:
                assert permitted(state, target), f"{ev.kind} {state} -> {target}"


# --- Information-only events change no state, everywhere ---


def test_information_only_events_change_no_state_in_any_state():
    for cls in CATALOG:
        ev = _instance(cls)
        if not ev.information_only:
            continue
        assert ev.kind in INFORMATION_ONLY
        for state in State:
            assert ev.next_state(state) is state
            result = evolve(state, ev)
            assert result.new_state is state
            assert isinstance(result.record, AuditRecord)
            assert result.record.from_state is state
            assert result.record.to_state is state


# --- Consequential events are refused where they do not apply ---


def test_consequential_events_are_refused_in_states_they_do_not_apply_to():
    for cls in CATALOG:
        ev = _instance(cls)
        if ev.information_only:
            continue
        for state in State:
            if ev.next_state(state) is None:
                result = evolve(state, ev)
                assert result.reason


# --- Audit before consequence (I-13; AU3) ---


def test_every_consequence_carries_its_audit_record():
    for cls in CATALOG:
        ev = _instance(cls)
        for state in State:
            result = evolve(state, ev)
            if not isinstance(result, AuditRecord):
                continue
            assert result.from_state is state
            assert result.to_state is result.new_state


def test_evolve_never_yields_a_bare_state():
    for cls in CATALOG:
        ev = _instance(cls)
        for state in State:
            result = evolve(state, ev)
            assert result is not state
            assert isinstance(result, (Transition, Refusal))


# --- Determinism (RFC-0007 S7) ---


def test_evolve_is_deterministic_for_every_event_and_state():
    for cls in CATALOG:
        ev = _instance(cls)
        for state in State:
            assert evolve(state, ev) == evolve(state, ev)


def test_dispatch_is_deterministic_for_every_event_and_state():
    for cls in CATALOG:
        ev = _instance(cls)
        for state in State:
            assert ev.next_state(state) == ev.next_state(state)


# --- Conformance: imports, no I/O, no hidden state ---


def test_events_imports_only_the_state_machine_module():
    tree = ast.parse(EVENTS_PATH.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    episky_imports = sorted({name for name in imported if name.startswith("episky")})
    assert episky_imports == ["episky.core.state_machine"]


def test_events_performs_no_io_no_clock_no_randomness():
    src = EVENTS_PATH.read_text(encoding="utf-8")
    for token in (
        "import time",
        "from time import",
        "time.time",
        "time.monotonic",
        "perf_counter",
        "datetime.now",
        "utcnow",
        "import random",
        "random.",
        "os.urandom",
        "import uuid",
        "uuid4",
        "import hmac",
        "import hashlib",
        "import secrets",
        "secrets.token",
        "import subprocess",
        "import os",
        "from os import",
        "os.system",
        "import socket",
        "import requests",
        "import json",
        "open(",
        "print(",
    ):
        assert token not in src


def test_events_holds_no_mutable_module_state():
    mod = importlib.import_module("episky.core.events")
    mutable_globals = {
        name
        for name, value in vars(mod).items()
        if isinstance(value, (list, dict, set))
        and not (name.startswith("__") and name.endswith("__"))
    }
    assert not mutable_globals
