"""RFC-0002 state-machine conformance (RFC-0002 §2, §3, §2.9, §9; RFC-0013 §7).

Behavioral tests for Iteration 11 Commit C1 (`core/state_machine.py`): the
pure transition table. `SECTION2_ALLOWED` transcribes the §2.1–§2.15
"Allowed transitions" lists exactly; `ALLOWED` adds the §3 shortcut edges and
the §2.9 next-step edge (DN-86, Q2); `permitted` is exactly that set and
refuses everything else, so the walkthrough §6.1 impossible-transition table
holds. `evolve(state, event)` resolves the event's own per-event dispatch
against the oracle and returns a `Transition` — the new state bundled with its
RFC-0013 §7 audit record, so no consequence exists without its record (I-13,
AU3) — or a `Refusal`. Invariants 8, 14, and 15 hold in every reachable state:
a halt is always followed by re-assessment (I-8), no terminal outcome is
reached while machine work is in flight (I-14), and the only way into Executing
is the gate or the verified next step, so no approval survives a boundary
(I-15, I-1). Deterministic (RFC-0007 S7) and I/O-free (DN-55, DN-94).
"""

import importlib
import pathlib

import pytest

from episky.core.events import (
    CATALOG,
    ActionPartial,
    ActionStarted,
    EventKind,
    OpCancel,
    OpExit,
    OpGoal,
    OpInterrupt,
    OpReply,
    RecordCategory,
    RuntimeEvent,
    Timeout,
    VerificationPassed,
)
from episky.core.state_machine import (
    ALLOWED,
    GOAL_ACTIVE,
    SECTION2_ALLOWED,
    Refusal,
    State,
    Transition,
    evolve,
    permitted,
)

STATE_MACHINE_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "core"
    / "state_machine.py"
)

EXPECTED_PUBLIC_SURFACE = {
    "ALLOWED",
    "GOAL_ACTIVE",
    "SECTION2_ALLOWED",
    "Refusal",
    "State",
    "Transition",
    "evolve",
    "permitted",
}

#: The §2.1–§2.15 "Allowed transitions" lists, transcribed from RFC-0002 for
#: the oracle check. END is terminal.
EXPECTED_SECTION2 = {
    State.INITIALIZING: {State.IDLE, State.INSPECTING, State.END},
    State.IDLE: {State.INSPECTING, State.END},
    State.INSPECTING: {
        State.BUILDING,
        State.AWAITING_INPUT,
        State.FAILED,
        State.INTERRUPTED,
    },
    State.BUILDING: {State.DIAGNOSING, State.PLANNING},
    State.DIAGNOSING: {
        State.PLANNING,
        State.INSPECTING,
        State.AWAITING_INPUT,
        State.COMPLETED,
        State.FAILED,
    },
    State.PLANNING: {
        State.AWAITING_APPROVAL,
        State.INSPECTING,
        State.AWAITING_INPUT,
        State.COMPLETED,
        State.FAILED,
    },
    State.AWAITING_APPROVAL: {
        State.EXECUTING,
        State.REPLANNING,
        State.CANCELLED,
        State.INTERRUPTED,
        State.INSPECTING,
    },
    State.EXECUTING: {State.VERIFYING, State.INTERRUPTED, State.CANCELLED, State.END},
    State.VERIFYING: {
        State.COMPLETED,
        State.EXECUTING,
        State.REPLANNING,
        State.AWAITING_INPUT,
        State.INTERRUPTED,
    },
    State.REPLANNING: {
        State.PLANNING,
        State.DIAGNOSING,
        State.INSPECTING,
        State.AWAITING_INPUT,
        State.FAILED,
    },
    State.AWAITING_INPUT: {
        State.DIAGNOSING,
        State.PLANNING,
        State.CANCELLED,
        State.END,
    },
    State.INTERRUPTED: {
        State.INSPECTING,
        State.AWAITING_APPROVAL,
        State.REPLANNING,
        State.CANCELLED,
        State.END,
    },
    State.COMPLETED: {State.IDLE, State.END},
    State.FAILED: {State.IDLE, State.END},
    State.CANCELLED: {State.IDLE, State.END},
    State.END: set(),
}

#: The §3 shortcut edges (DN-86) beyond the §2 lists: OP_CANCEL → Cancelled
#: from any active state; OP_INTERRUPT → Awaiting Input for cognitive work;
#: OP_EXIT → END from an active state. The §2.9 next-step edge (VERIFYING →
#: EXECUTING) is already in VERIFYING's §2.9 list.
EXPECTED_SHORTCUT = {
    State.INSPECTING: {State.CANCELLED, State.END},
    State.BUILDING: {State.CANCELLED, State.AWAITING_INPUT, State.END},
    State.DIAGNOSING: {State.CANCELLED, State.END},
    State.PLANNING: {State.CANCELLED, State.END},
    State.AWAITING_APPROVAL: {State.END},
    State.VERIFYING: {State.CANCELLED, State.END},
    State.REPLANNING: {State.CANCELLED, State.END},
}


class _Renegade(RuntimeEvent):
    """A deliberately non-permitted dispatch, to prove the oracle refuses it."""

    kind = EventKind.OP_GOAL
    category = RecordCategory.SESSION
    _DISPATCH = {State.PLANNING: State.EXECUTING}


# --- Public surface and structure ---


def test_state_machine_public_surface_is_exactly_the_owned_vocabulary():
    mod = importlib.import_module("episky.core.state_machine")
    assert set(mod.__all__) == EXPECTED_PUBLIC_SURFACE


def test_state_enum_is_the_section_2_states_in_order_plus_end():
    assert tuple(State) == (
        State.INITIALIZING,
        State.IDLE,
        State.INSPECTING,
        State.BUILDING,
        State.DIAGNOSING,
        State.PLANNING,
        State.AWAITING_APPROVAL,
        State.EXECUTING,
        State.VERIFYING,
        State.REPLANNING,
        State.AWAITING_INPUT,
        State.INTERRUPTED,
        State.COMPLETED,
        State.FAILED,
        State.CANCELLED,
        State.END,
    )


def test_goal_active_is_the_lifecycle_states_only():
    assert (
        frozenset(
            {
                State.INSPECTING,
                State.BUILDING,
                State.DIAGNOSING,
                State.PLANNING,
                State.AWAITING_APPROVAL,
                State.EXECUTING,
                State.VERIFYING,
                State.REPLANNING,
                State.AWAITING_INPUT,
                State.INTERRUPTED,
            }
        )
        == GOAL_ACTIVE
    )


# --- The pure §2 table ---


@pytest.mark.parametrize("state", sorted(State, key=lambda s: s.value))
def test_section2_transcribes_the_section_2_lists_exactly(state):
    assert set(SECTION2_ALLOWED[state]) == EXPECTED_SECTION2[state]


def test_end_is_terminal():
    assert set(SECTION2_ALLOWED[State.END]) == set()


# --- The oracle: §2 ∪ §3 shortcuts ∪ §2.9 next-step ---


@pytest.mark.parametrize("state", sorted(State, key=lambda s: s.value))
def test_allowed_is_section2_union_shortcuts(state):
    expected = EXPECTED_SECTION2[state] | EXPECTED_SHORTCUT.get(state, set())
    assert set(ALLOWED[state]) == expected


def test_permitted_matches_the_oracle_for_every_state_pair():
    for source in State:
        for target in State:
            assert permitted(source, target) == (target in ALLOWED[source])


def test_every_section_2_edge_is_permitted():
    for source, targets in EXPECTED_SECTION2.items():
        for target in targets:
            assert permitted(source, target), f"§2 edge {source} -> {target} refused"


def test_every_shortcut_edge_is_permitted():
    for source, targets in EXPECTED_SHORTCUT.items():
        for target in targets:
            assert permitted(source, target), f"§3 edge {source} -> {target} refused"


def test_the_section_2_9_next_step_edge_is_permitted():
    assert permitted(State.VERIFYING, State.EXECUTING)


# --- The impossible-transition table (walkthrough §6.1) ---


@pytest.mark.parametrize(
    "source,target",
    [
        (State.PLANNING, State.EXECUTING),
        (State.DIAGNOSING, State.EXECUTING),
        (State.IDLE, State.EXECUTING),
        (State.EXECUTING, State.COMPLETED),
        (State.INTERRUPTED, State.EXECUTING),
        (State.AWAITING_APPROVAL, State.COMPLETED),
        (State.EXECUTING, State.FAILED),
        (State.INSPECTING, State.DIAGNOSING),
        (State.BUILDING, State.INSPECTING),
        (State.COMPLETED, State.EXECUTING),
    ],
)
def test_impossible_transitions_are_refused(source, target):
    assert not permitted(source, target)
    assert target not in ALLOWED[source]


# --- evolve: dispatch against the oracle ---


def test_evolve_returns_a_transition_bundling_the_audit_record():
    result = evolve(State.IDLE, OpGoal())
    assert isinstance(result, Transition)
    assert result.new_state is State.INSPECTING
    assert result.record.category is RecordCategory.SESSION
    assert result.record.from_state is State.IDLE
    assert result.record.to_state is State.INSPECTING


def test_evolve_refuses_an_event_in_a_state_it_does_not_apply_to():
    result = evolve(State.PLANNING, OpGoal())
    assert isinstance(result, Refusal)
    assert result.reason


def test_evolve_refuses_a_declared_target_outside_the_oracle():
    result = evolve(State.PLANNING, _Renegade())
    assert isinstance(result, Refusal)
    assert "reachable set" in result.reason


def test_evolve_is_deterministic():
    requires_args = {OpReply, ActionPartial, VerificationPassed, Timeout}
    for cls in CATALOG:
        if cls in requires_args:
            continue
        ev = cls()
        for state in State:
            assert evolve(state, ev) == evolve(state, ev)


def test_evolve_never_returns_a_bare_state():
    for source in State:
        for cls in (OpGoal, OpCancel, OpExit, ActionStarted):
            assert isinstance(evolve(source, cls()), (Transition, Refusal))


# --- Invariants 8, 14, 15 hold in every reachable state ---


def test_i8_halt_is_followed_by_re_assessment():
    assert State.INTERRUPTED not in ALLOWED[State.INTERRUPTED]
    assert set(ALLOWED[State.INTERRUPTED]) == {
        State.INSPECTING,
        State.AWAITING_APPROVAL,
        State.REPLANNING,
        State.CANCELLED,
        State.END,
    }
    assert not permitted(State.INTERRUPTED, State.EXECUTING)
    assert permitted(State.INTERRUPTED, State.INSPECTING)


def test_i14_no_terminal_outcome_while_machine_work_is_in_flight():
    assert set(ALLOWED[State.EXECUTING]) == {
        State.VERIFYING,
        State.INTERRUPTED,
        State.CANCELLED,
        State.END,
    }
    assert not permitted(State.EXECUTING, State.COMPLETED)
    assert not permitted(State.EXECUTING, State.FAILED)


def test_i15_and_i1_the_only_way_into_executing_is_the_gate_or_next_step():
    assert {s for s in State if permitted(s, State.EXECUTING)} == {
        State.AWAITING_APPROVAL,
        State.VERIFYING,
    }


def test_interrupt_shortcut_and_second_press():
    assert evolve(State.EXECUTING, OpInterrupt()).new_state is State.INTERRUPTED
    assert evolve(State.DIAGNOSING, OpInterrupt()).new_state is State.AWAITING_INPUT
    assert evolve(State.INTERRUPTED, OpInterrupt()).new_state is State.END
    assert evolve(State.AWAITING_INPUT, OpInterrupt()).new_state is State.END


def test_cancel_shortcut_from_any_active_state_only():
    for active in GOAL_ACTIVE:
        result = evolve(active, OpCancel())
        assert isinstance(result, Transition) and result.new_state is State.CANCELLED
    for resting in (
        State.INITIALIZING,
        State.IDLE,
        State.COMPLETED,
        State.FAILED,
        State.CANCELLED,
    ):
        assert isinstance(evolve(resting, OpCancel()), Refusal)


def test_exit_shortcut_reaches_end_from_every_runtime_state():
    for source in State:
        if source in (State.INITIALIZING, State.END):
            continue
        result = evolve(source, OpExit())
        assert isinstance(result, Transition) and result.new_state is State.END


# --- No I/O, no hidden state, immutable results ---


def test_state_machine_imports_no_episky_package_and_no_io_modules():
    src = STATE_MACHINE_PATH.read_text(encoding="utf-8")
    for token in (
        "import episky",
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
        "os.system",
        "import socket",
        "import requests",
        "import json",
        "open(",
        "print(",
    ):
        assert token not in src


def test_state_machine_holds_no_mutable_module_state():
    mod = importlib.import_module("episky.core.state_machine")
    mutable_globals = {
        name
        for name, value in vars(mod).items()
        if isinstance(value, (list, dict, set))
        and not (name.startswith("__") and name.endswith("__"))
    }
    assert not mutable_globals


def test_transition_and_refusal_are_frozen_slotted_dataclasses():
    for cls in (Transition, Refusal):
        params = cls.__dataclass_params__
        assert params.frozen
        assert params.slots


def test_state_enum_is_immutable():
    with pytest.raises((TypeError, AttributeError)):
        State.EXECUTING = State.IDLE
