"""The RFC-0002 session state machine and its reachable-edge oracle.

Owner: RFC-0002 §2 (Runtime States), §3 (State Machine Diagram),
    §2.9 (Verification → Executing, the next approved step); RFC-0013 §7
    (Audit Record Categories), §23 (write points are runtime boundaries,
    written before the consequence).
Responsibility: the pure transition table. ``permitted(from, to)`` is the
    reachable-edge oracle: exactly the §2.1–§2.15 "Allowed transitions"
    lists, plus the §3 shortcut edges and the §2.9 next-step edge (DN-86,
    Q2) — nothing else is reachable (the walkthrough §6.1 impossible-
    transition table). ``evolve(state, event)`` resolves the event's own
    per-event dispatch (events.py) against that oracle and returns a
    ``Transition`` — the new state bundled with its RFC-0013 §7 audit
    record, so a consequence never exists without its record (I-13, AU3) —
    or a ``Refusal``. Information-only events change no state.
Forbidden responsibility: no transition outside the §2/§3/§2.9 set; no
    event routing or audit writing; no approval/verification/classification
    logic (RFC-0002 §9; RFC-0004 §4.3); no I/O, no clock, no randomness,
    no hidden state (DN-55; DN-94).
"""

from __future__ import annotations

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum, auto
from types import MappingProxyType
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from episky.core.events import AuditRecord

__all__ = [
    "ALLOWED",
    "GOAL_ACTIVE",
    "SECTION2_ALLOWED",
    "Refusal",
    "State",
    "Transition",
    "evolve",
    "permitted",
]


class State(Enum):
    """The RFC-0002 §2 runtime states, plus the END terminal (RFC-0002 §3)."""

    INITIALIZING = auto()
    IDLE = auto()
    INSPECTING = auto()
    BUILDING = auto()
    DIAGNOSING = auto()
    PLANNING = auto()
    AWAITING_APPROVAL = auto()
    EXECUTING = auto()
    VERIFYING = auto()
    REPLANNING = auto()
    AWAITING_INPUT = auto()
    INTERRUPTED = auto()
    COMPLETED = auto()
    FAILED = auto()
    CANCELLED = auto()
    END = auto()


#: The goal-lifecycle states the §3 OP_CANCEL shortcut applies to ("from any
#: active state", RFC-0002 §4.1); Idle, Initialization, and the goal outcomes
#: are not active.
GOAL_ACTIVE = frozenset(
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

#: The §2.1–§2.15 "Allowed transitions" lists, transcribed exactly. Each state
#: maps to its own list; END is terminal. This is the §2 half of the oracle.
SECTION2_ALLOWED: Mapping[State, frozenset[State]] = MappingProxyType(
    {
        State.INITIALIZING: frozenset({State.IDLE, State.INSPECTING, State.END}),
        State.IDLE: frozenset({State.INSPECTING, State.END}),
        State.INSPECTING: frozenset(
            {State.BUILDING, State.AWAITING_INPUT, State.FAILED, State.INTERRUPTED}
        ),
        State.BUILDING: frozenset({State.DIAGNOSING, State.PLANNING}),
        State.DIAGNOSING: frozenset(
            {
                State.PLANNING,
                State.INSPECTING,
                State.AWAITING_INPUT,
                State.COMPLETED,
                State.FAILED,
            }
        ),
        State.PLANNING: frozenset(
            {
                State.AWAITING_APPROVAL,
                State.INSPECTING,
                State.AWAITING_INPUT,
                State.COMPLETED,
                State.FAILED,
            }
        ),
        State.AWAITING_APPROVAL: frozenset(
            {
                State.EXECUTING,
                State.REPLANNING,
                State.CANCELLED,
                State.INTERRUPTED,
                State.INSPECTING,
            }
        ),
        State.EXECUTING: frozenset(
            {State.VERIFYING, State.INTERRUPTED, State.CANCELLED, State.END}
        ),
        State.VERIFYING: frozenset(
            {
                State.COMPLETED,
                State.EXECUTING,
                State.REPLANNING,
                State.AWAITING_INPUT,
                State.INTERRUPTED,
            }
        ),
        State.REPLANNING: frozenset(
            {
                State.PLANNING,
                State.DIAGNOSING,
                State.INSPECTING,
                State.AWAITING_INPUT,
                State.FAILED,
            }
        ),
        State.AWAITING_INPUT: frozenset(
            {State.DIAGNOSING, State.PLANNING, State.CANCELLED, State.END}
        ),
        State.INTERRUPTED: frozenset(
            {
                State.INSPECTING,
                State.AWAITING_APPROVAL,
                State.REPLANNING,
                State.CANCELLED,
                State.END,
            }
        ),
        State.COMPLETED: frozenset({State.IDLE, State.END}),
        State.FAILED: frozenset({State.IDLE, State.END}),
        State.CANCELLED: frozenset({State.IDLE, State.END}),
        State.END: frozenset(),
    }
)

#: The §3 shortcut edges (DN-86) that the §2 lists do not already contain:
#: OP_CANCEL → Cancelled from any active state; OP_INTERRUPT → Awaiting Input
#: for cognitive work (Context Building); OP_EXIT → END from an active state
#: (the interrupt protocol runs first). The remaining §3 shortcuts
#: (ACTION_TIMEOUT/ACTION_INTERRUPTED → Interrupted; provider loss → degraded
#: mode → Awaiting Input; approved REBOOT → END; STATE_CHANGED_DETECTED →
#: Machine Inspection) are already §2 edges. The §2.9 Verification → Executing
#: next-step edge is already in VERIFYING's §2.9 list.
_SHORTCUT: Mapping[State, frozenset[State]] = MappingProxyType(
    {
        State.INSPECTING: frozenset({State.CANCELLED, State.END}),
        State.BUILDING: frozenset({State.CANCELLED, State.AWAITING_INPUT, State.END}),
        State.DIAGNOSING: frozenset({State.CANCELLED, State.END}),
        State.PLANNING: frozenset({State.CANCELLED, State.END}),
        State.AWAITING_APPROVAL: frozenset({State.END}),
        State.VERIFYING: frozenset({State.CANCELLED, State.END}),
        State.REPLANNING: frozenset({State.CANCELLED, State.END}),
    }
)

#: The complete reachable-edge oracle: §2.1–§2.15 lists ∪ §3 shortcut edges
#: ∪ the §2.9 next-step edge. ``permitted`` is this set; nothing else is
#: reachable (DN-86).
ALLOWED: Mapping[State, frozenset[State]] = MappingProxyType(
    {
        state: SECTION2_ALLOWED[state] | _SHORTCUT.get(state, frozenset())
        for state in State
    }
)


def permitted(source: State, target: State) -> bool:
    """True iff the (source → target) edge is in the §2/§3/§2.9 reachable set."""
    return target in ALLOWED[source]


@dataclass(frozen=True, slots=True)
class Transition:
    """A consequence bundled with its RFC-0013 §7 audit record (I-13, AU3)."""

    new_state: State
    record: AuditRecord


@dataclass(frozen=True, slots=True)
class Refusal:
    """A refused transition: the event was not applicable, or not permitted."""

    reason: str


def evolve(state: State, event) -> Transition | Refusal:
    """Resolve ``event`` from ``state`` to a ``Transition`` or a ``Refusal``.

    The event's own per-event dispatch (events.py) declares the candidate
    target; ``permitted`` is the §2/§3/§2.9 oracle. A declared target that is
    not permitted, or an event in a state it does not apply to, is refused.
    Information-only events return a Transition on the same state (an audited
    note; no state change). The audit record always accompanies the
    consequence, so the state change cannot be taken without its record.
    Deterministic and I/O-free (RFC-0007 S7; DN-94).
    """
    target = event.next_state(state)
    if target is None:
        return Refusal(f"{event.kind} is not applicable in {state.name}")
    if target is state:
        return Transition(state, event.record(state, state))
    if not permitted(state, target):
        return Refusal(
            f"{event.kind} cannot move {state.name} -> {target.name}: "
            "outside the RFC-0002 §2/§3/§2.9 reachable set"
        )
    return Transition(target, event.record(state, target))
