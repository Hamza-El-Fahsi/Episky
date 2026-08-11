"""C2 collect tests — the closed decision vocabulary and the §4.1 event map.

Iteration 12 Commit C2. Asserts the ratified readings of design-review §14 C2:
the closed Operator-decision vocabulary mapped deterministically to the
RFC-0002 §4.1 operator events (DN-99; RFC-0007 S7); free text is collected as
a payload, never into a command (I-5); an inapplicable decision is refused by
`core` and the `Refusal` surfaces honestly (DN-99; I-9), never swallowed or
re-mapped by the CLI (DN-102).
"""

import pytest

from episky.cli.collect import Collected, Decision, to_event
from episky.core.events import (
    OpApprove,
    OpCancel,
    OpExit,
    OpGoal,
    OpInterrupt,
    OpOverride,
    OpRefine,
    OpReject,
    OpReply,
    OpView,
)
from episky.core.session import Session
from episky.core.state_machine import Refusal, State

_EVENT_CLASS = {
    Decision.GOAL: OpGoal,
    Decision.REPLY: OpReply,
    Decision.APPROVE: OpApprove,
    Decision.OVERRIDE: OpOverride,
    Decision.REJECT: OpReject,
    Decision.REFINE: OpRefine,
    Decision.CANCEL: OpCancel,
    Decision.INTERRUPT: OpInterrupt,
    Decision.EXIT: OpExit,
    Decision.VIEW: OpView,
}


def test_vocabulary_is_closed_and_maps_to_the_operator_events():
    # Every decision maps 1:1 to its RFC-0002 §4.1 operator event.
    assert set(Decision) == set(_EVENT_CLASS)
    for decision, cls in _EVENT_CLASS.items():
        if decision is Decision.REPLY:
            event = to_event(Collected(decision), routes_to=State.DIAGNOSING)
        else:
            event = to_event(Collected(decision))
        assert isinstance(event, cls), (decision, type(event))


@pytest.mark.parametrize("decision", list(Decision))
def test_to_event_is_deterministic(decision):
    if decision is Decision.REPLY:
        first = to_event(Collected(decision), routes_to=State.DIAGNOSING)
        second = to_event(Collected(decision), routes_to=State.DIAGNOSING)
    else:
        first = to_event(Collected(decision))
        second = to_event(Collected(decision))
    assert first == second


def test_goal_payload_is_collected_verbatim_never_in_a_command():
    collected = Collected(Decision.GOAL, payload="fix the boot loader")
    event = to_event(collected)
    assert isinstance(event, OpGoal)
    # The free-text statement travels as the collected payload (to be passed
    # to advance(goal=...)) — never inside the event or a command (I-5).
    assert not hasattr(event, "payload")
    assert collected.payload == "fix the boot loader"


def test_reply_event_carries_the_outstanding_question_routing():
    event = to_event(Collected(Decision.REPLY), routes_to=State.DIAGNOSING)
    assert isinstance(event, OpReply)
    assert event.routes_to is State.DIAGNOSING


def test_reply_requires_a_valid_route():
    # The route is refused by the core type's own rule — the CLI does not
    # pre-decide policy (RFC-0004 §7); core's validation is the authority.
    with pytest.raises(ValueError):
        to_event(Collected(Decision.REPLY), routes_to=State.IDLE)
    with pytest.raises(ValueError):
        to_event(Collected(Decision.REPLY))


def test_override_reason_is_collected_as_payload():
    # The override reason (P10) is collected as data; the CLI never drops it
    # and never decides the override itself (RFC-0004 §4.3).
    collected = Collected(Decision.OVERRIDE, payload="verified safe manually")
    event = to_event(collected)
    assert isinstance(event, OpOverride)
    assert collected.payload == "verified safe manually"


def test_view_is_informational_only():
    event = to_event(Collected(Decision.VIEW))
    assert isinstance(event, OpView)
    assert event.information_only is True


# ---------------------------------------------------------------------------
# The inapplicable decision is refused by `core` and surfaces honestly (DN-99)
# ---------------------------------------------------------------------------


def test_inapplicable_approve_is_refused_by_core():
    # APPROVE is only applicable from Awaiting Approval; from Idle the core
    # state machine refuses it. The CLI presents the Refusal — it never
    # swallows it or re-maps it to another event (DN-99; DN-102).
    event = to_event(Collected(Decision.APPROVE))
    outcome = Session(State.IDLE, None).apply(event)
    assert isinstance(outcome, Refusal)
    assert outcome.reason


def test_applicable_approve_advances_through_core():
    # The same event, applied from the applicable state, advances: the CLI
    # never pre-refuses a decision on its own authority.
    event = to_event(Collected(Decision.APPROVE))
    step = Session(State.AWAITING_APPROVAL, "fix the boot loader").apply(event)
    assert step is not None
    assert not isinstance(step, Refusal)


def test_goal_maps_through_the_guarded_adopt_goal_path():
    # OP_GOAL is refused by Session.apply itself (single guarded path) and
    # goes through adopt_goal with the collected payload as the statement.
    collected = Collected(Decision.GOAL, payload="fix the boot loader")
    outcome = Session(State.IDLE, None).apply(to_event(collected))
    assert isinstance(outcome, Refusal)
    step = Session(State.IDLE, None).adopt_goal(collected.payload)
    assert step is not None and not isinstance(step, Refusal)
    assert step.session.goal == "fix the boot loader"
