"""RFC-0002 session-lifecycle conformance (RFC-0002 §1, §2.1–§2.2, §4.1; RFC-0013 §7).

Behavioral tests for Iteration 11 Commit C2 (`core/session.py`): the
single-goal, serial session lifecycle as a frozen value. `Session` is the one
place state advances; every transition is delegated to the authoritative
state machine (`state_machine.evolve`), so the session never invents a
transition and no second competing state machine exists (DN-86). `start`
runs the §2.1 safety-critical prerequisite gate — fail-closed: any unmet
prerequisite refuses service and ends (RFC-0001 §8). `adopt_goal` adopts a
goal from Idle (Idle → Machine Inspection) with its RFC-0013 §7
goal-adoption record bundled before the consequence (I-13), and returns to
Idle from a goal outcome — the outcome terminals lead only to Idle (§2.2,
§4.1). `stop` leaves the runtime from Idle or an outcome and refuses from an
active goal (the interrupt protocol runs first; C4/RFC-0014). `apply` is the
general transition mechanism, refusing OP_GOAL/OP_EXIT so adoption and exit
each have a single guarded path. The lifecycle is single-goal and serial:
no parallel goal. Deterministic (RFC-0007 S7), I/O-free (DN-55, DN-94), and
immutable (frozen/slotted values).
"""

import importlib
import pathlib

import pytest

from episky.core.events import (
    ActionStarted,
    EventKind,
    FactsCollected,
    OpCancel,
    OpExit,
    OpGoal,
    ProviderFallbackFailed,
    RecordCategory,
)
from episky.core.session import Prerequisites, Session, Step
from episky.core.state_machine import (
    ALLOWED,
    GOAL_ACTIVE,
    Refusal,
    State,
    evolve,
    permitted,
)

SESSION_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "core"
    / "session.py"
)

EXPECTED_PUBLIC_SURFACE = {"Prerequisites", "Session", "Step"}

OK = Prerequisites(
    elevation_available=True,
    machine_fingerprint_verified=True,
    audit_writable=True,
)

OUTCOMES = {State.COMPLETED, State.FAILED, State.CANCELLED}


# --- Public surface and structure ---


def test_session_public_surface_is_exactly_the_owned_vocabulary():
    mod = importlib.import_module("episky.core.session")
    assert set(mod.__all__) == EXPECTED_PUBLIC_SURFACE


def test_session_step_and_prerequisites_are_frozen_slotted_dataclasses():
    for cls in (Session, Step, Prerequisites):
        params = cls.__dataclass_params__
        assert params.frozen
        assert params.slots


def test_initial_session_is_session_initialization_with_no_goal():
    s = Session.initial()
    assert s.state is State.INITIALIZING
    assert s.goal is None


def test_prerequisites_transcribe_section_2_1():
    fields = tuple(Prerequisites.__dataclass_fields__)
    assert fields == (
        "elevation_available",
        "machine_fingerprint_verified",
        "audit_writable",
    )


def test_session_is_a_value_and_operations_never_mutate_it():
    s = Session.initial()
    started = s.start(OK)
    assert s.state is State.INITIALIZING and s.goal is None
    assert started.state is State.IDLE
    step = started.adopt_goal("update nginx")
    assert started.state is State.IDLE and started.goal is None
    assert step.session.state is State.INSPECTING


def test_session_value_equality():
    assert Session.initial() == Session(State.INITIALIZING, None)
    assert Session(State.IDLE, None) == Session(State.IDLE, None)
    assert Session(State.INSPECTING, "g") != Session(State.INSPECTING, "h")


# --- start: the §2.1 prerequisite gate ---


def test_start_with_all_prerequisites_reaches_idle():
    s = Session.initial().start(OK)
    assert isinstance(s, Session)
    assert s.state is State.IDLE
    assert s.goal is None


@pytest.mark.parametrize(
    "bad",
    [
        Prerequisites(
            elevation_available=False,
            machine_fingerprint_verified=True,
            audit_writable=True,
        ),
        Prerequisites(
            elevation_available=True,
            machine_fingerprint_verified=False,
            audit_writable=True,
        ),
        Prerequisites(
            elevation_available=True,
            machine_fingerprint_verified=True,
            audit_writable=False,
        ),
    ],
)
def test_start_fails_closed_to_end_when_any_prerequisite_is_missing(bad):
    s = Session.initial().start(bad)
    assert isinstance(s, Session)
    assert s.state is State.END
    assert s.goal is None


def test_start_only_from_session_initialization():
    for state in State:
        if state is State.INITIALIZING:
            continue
        result = Session(state, None).start(OK)
        assert isinstance(result, Refusal)
        assert result.reason


def test_start_reaches_a_machine_permitted_transition_only():
    started = Session.initial().start(OK)
    assert isinstance(started, Session)
    assert permitted(State.INITIALIZING, started.state)
    assert started.state in ALLOWED[State.INITIALIZING]


def test_start_failed_prerequisites_are_the_fail_closed_abort_edge():
    ended = Session.initial().start(Prerequisites(False, False, False))
    assert isinstance(ended, Session)
    assert ended.state is State.END
    assert permitted(State.INITIALIZING, State.END)


# --- adopt_goal: goal adoption with its record (I-13) ---


def test_adopt_goal_from_idle_adopts_goal_with_record_before_consequence():
    result = Session(State.IDLE, None).adopt_goal("update nginx to latest")
    assert isinstance(result, Step)
    assert result.session.state is State.INSPECTING
    assert result.session.goal == "update nginx to latest"
    assert result.record.category is RecordCategory.SESSION
    assert result.record.kind is EventKind.OP_GOAL
    assert result.record.from_state is State.IDLE
    assert result.record.to_state is State.INSPECTING
    assert result.record == evolve(State.IDLE, OpGoal()).record


def test_adopt_goal_holds_the_statement_verbatim_no_normalization():
    result = Session(State.IDLE, None).adopt_goal("  update nginx  ")
    assert isinstance(result, Step)
    assert result.session.goal == "  update nginx  "


def test_adopt_goal_from_each_outcome_returns_to_idle_only():
    for outcome in OUTCOMES:
        result = Session(outcome, "old goal").adopt_goal("new goal")
        assert isinstance(result, Step)
        assert result.session.state is State.IDLE, (
            f"{outcome.name} must lead to Idle only"
        )
        assert result.session.goal is None
        assert result.record.from_state is outcome
        assert result.record.to_state is State.IDLE
        assert result.record.category is RecordCategory.SESSION


@pytest.mark.parametrize("active", sorted(GOAL_ACTIVE, key=lambda s: s.value))
def test_adopt_goal_refuses_while_a_goal_is_active_no_parallel_goal(active):
    result = Session(active, "in flight").adopt_goal("second goal")
    assert isinstance(result, Refusal)
    assert "single-goal" in result.reason


@pytest.mark.parametrize("bad", [None, 42, "", "   ", "\t\n"])
def test_adopt_goal_refuses_malformed_statements(bad):
    result = Session(State.IDLE, None).adopt_goal(bad)
    assert isinstance(result, Refusal)
    assert "statement" in result.reason


def test_adopt_goal_refuses_before_start_and_after_end():
    assert isinstance(Session.initial().adopt_goal("g"), Refusal)
    assert isinstance(Session(State.END, None).adopt_goal("g"), Refusal)


def test_adopt_goal_reaches_only_machine_permitted_targets():
    for state in (State.IDLE, *OUTCOMES):
        result = Session(state, None).adopt_goal("g")
        assert isinstance(result, Step)
        assert permitted(state, result.session.state)


def test_goal_revision_in_awaiting_input_is_not_adoption():
    result = Session(State.AWAITING_INPUT, "g").adopt_goal("revised")
    assert isinstance(result, Refusal)


# --- stop: leave the runtime ---


def test_stop_from_idle_reaches_end():
    result = Session(State.IDLE, None).stop()
    assert isinstance(result, Step)
    assert result.session.state is State.END
    assert result.record.category is RecordCategory.SESSION
    assert result.record.kind is EventKind.OP_EXIT
    assert result.record.from_state is State.IDLE
    assert result.record.to_state is State.END


@pytest.mark.parametrize("outcome", sorted(OUTCOMES, key=lambda s: s.value))
def test_stop_from_each_outcome_reaches_end(outcome):
    result = Session(outcome, "finished").stop()
    assert isinstance(result, Step)
    assert result.session.state is State.END


@pytest.mark.parametrize("active", sorted(GOAL_ACTIVE, key=lambda s: s.value))
def test_stop_refuses_while_a_goal_is_active_interrupt_protocol_first(active):
    result = Session(active, "in flight").stop()
    assert isinstance(result, Refusal)
    assert "interrupt protocol" in result.reason


def test_stop_refuses_from_initialization_and_end():
    assert isinstance(Session.initial().stop(), Refusal)
    assert isinstance(Session(State.END, None).stop(), Refusal)


# --- apply: the general transition mechanism ---


def test_apply_routes_through_the_state_machine():
    result = Session(State.INSPECTING, "g").apply(FactsCollected())
    assert isinstance(result, Step)
    assert result.session.state is State.BUILDING
    assert result.session.goal == "g"
    assert result.record.category is RecordCategory.FACT_LIFECYCLE
    assert result.record.from_state is State.INSPECTING
    assert result.record.to_state is State.BUILDING


def test_apply_returns_a_refusal_for_a_non_applicable_event():
    result = Session(State.PLANNING, "g").apply(FactsCollected())
    assert isinstance(result, Refusal)
    assert result.reason


def test_apply_refuses_op_goal_and_op_exit_single_guarded_paths():
    for event in (OpGoal(), OpExit()):
        result = Session(State.IDLE, None).apply(event)
        assert isinstance(result, Refusal)


def test_apply_is_deterministic():
    s = Session(State.EXECUTING, "g")
    for event in (
        OpCancel(),
        ActionStarted(),
        FactsCollected(),
        ProviderFallbackFailed(),
    ):
        assert s.apply(event) == s.apply(event)


def test_apply_never_invents_a_transition():
    for state in State:
        s = Session(state, "g")
        for event in (OpCancel(), FactsCollected(), ProviderFallbackFailed()):
            a = s.apply(event)
            e = evolve(state, event)
            if isinstance(e, Refusal):
                assert isinstance(a, Refusal)
            else:
                assert isinstance(a, Step)
                assert a.session.state is e.new_state


def test_apply_carries_the_goal_forward():
    result = Session(State.EXECUTING, "the goal").apply(OpCancel())
    assert isinstance(result, Step)
    assert result.session.goal == "the goal"
    assert result.session.state is State.CANCELLED


def test_apply_on_an_outcome_produces_the_outcome_boundary_record():
    result = Session(State.EXECUTING, "g").apply(OpCancel())
    assert isinstance(result, Step)
    assert result.session.state is State.CANCELLED
    assert result.record.category is RecordCategory.SESSION
    assert result.record.kind is EventKind.OP_CANCEL
    assert result.record.to_state is State.CANCELLED


# --- Lifecycle: single-goal, serial; outcome terminals lead only to Idle ---


def test_outcome_terminals_lead_only_to_idle():
    for outcome in OUTCOMES:
        assert set(ALLOWED[outcome]) == {State.IDLE, State.END}
        returned = Session(outcome, None).adopt_goal("next")
        assert isinstance(returned, Step)
        assert returned.session.state is State.IDLE


def test_single_goal_serial_lifecycle_no_second_goal_while_active():
    s = Session.initial().start(OK)
    assert isinstance(s, Session)
    adopted = s.adopt_goal("first")
    assert isinstance(adopted, Step)
    assert isinstance(adopted.session.adopt_goal("second"), Refusal)


def test_full_lifecycle_arc_to_outcome_and_back_to_idle():
    s = Session.initial().start(OK)
    assert isinstance(s, Session) and s.state is State.IDLE
    adopted = s.adopt_goal("update nginx")
    assert isinstance(adopted, Step)
    s = adopted.session
    s = s.apply(FactsCollected()).session
    assert s.state is State.BUILDING and s.goal == "update nginx"
    cancelled = s.apply(OpCancel())
    assert isinstance(cancelled, Step)
    assert cancelled.session.state is State.CANCELLED
    returned = cancelled.session.adopt_goal("update postgres")
    assert isinstance(returned, Step)
    assert returned.session.state is State.IDLE and returned.session.goal is None
    adopted_again = returned.session.adopt_goal("update postgres")
    assert isinstance(adopted_again, Step)
    assert adopted_again.session.state is State.INSPECTING
    assert adopted_again.session.goal == "update postgres"


# --- No I/O, no hidden state, no authority leakage, sanctioned imports ---


def test_session_imports_only_core_modules_and_no_io_modules():
    src = SESSION_PATH.read_text(encoding="utf-8")
    for token in (
        "import episky.audit",
        "import episky.policy",
        "import episky.executor",
        "import episky.providers",
        "import episky.skills",
        "import episky.context",
        "import episky.secrets",
        "import episky.verification",
        "import episky.factlayer",
        "import episky.cli",
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


def test_session_holds_no_mutable_module_state():
    mod = importlib.import_module("episky.core.session")
    mutable_globals = {
        name
        for name, value in vars(mod).items()
        if isinstance(value, (list, dict, set))
        and not (name.startswith("__") and name.endswith("__"))
    }
    assert not mutable_globals


def test_session_performs_no_audit_write_and_no_execution_call():
    src = SESSION_PATH.read_text(encoding="utf-8")
    for token in (
        "append(",
        "audit.",
        ".run(",
        "execute(",
        "classify(",
        "verify(",
        "compare(",
    ):
        assert token not in src
