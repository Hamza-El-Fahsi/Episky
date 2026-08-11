"""Collect — Operator decision collection (RFC-0001 §5; RFC-0002 §4.1).

Owner: RFC-0001 §5 (Presentation).
Responsibility: model an Operator decision (approve, reject, override, refine,
    reply, cancel, interrupt, exit, view, goal) with its optional free-text
    payload, and map it deterministically to the RFC-0002 §4.1 operator event
    of the same intent (DN-99).
Forbidden responsibility: never decides policy (RFC-0004 §7: Presentation not
    an actor); never constructs session/state/recovery logic (DN-102); an
    inapplicable decision is refused by `core` and presented honestly, never
    swallowed or re-mapped (DN-99; I-9); free text travels only as a collected
    payload, never into a command (I-5); no I/O, no clock, no randomness
    (DN-55/DN-103).
Layer 7 (blueprint §4.1). Imports: core (the §4.1 operator events).
"""

from dataclasses import dataclass
from enum import Enum

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
    RuntimeEvent,
)
from episky.core.state_machine import State

__all__ = ["Collected", "Decision", "to_event"]


class Decision(Enum):
    """The closed Operator-decision vocabulary (DN-99).

    Each member names the RFC-0002 §4.1 operator event of the same intent
    (RFC-0001 §5: collect approvals, refusals, and input). The vocabulary is
    closed — the CLI presents these decisions and collects them; it never
    invents a decision (RFC-0004 §7).

    Members:
        GOAL: State or revise a goal (OP_GOAL).
        REPLY: A free-text answer to the outstanding question (OP_REPLY).
        APPROVE: Approve the presented actions (OP_APPROVE).
        OVERRIDE: The explicit, audited override of a blocked action (OP_OVERRIDE).
        REJECT: Reject the presented actions (OP_REJECT).
        REFINE: Request plan changes (OP_REFINE).
        CANCEL: Abandon the goal (OP_CANCEL).
        INTERRUPT: Interrupt (Ctrl+C) the runtime (OP_INTERRUPT).
        EXIT: Leave the runtime (OP_EXIT).
        VIEW: Inspect Context or Audit — informational, no state change (OP_VIEW).
    """

    GOAL = "goal"
    REPLY = "reply"
    APPROVE = "approve"
    OVERRIDE = "override"
    REJECT = "reject"
    REFINE = "refine"
    CANCEL = "cancel"
    INTERRUPT = "interrupt"
    EXIT = "exit"
    VIEW = "view"


@dataclass(frozen=True, slots=True)
class Collected:
    """One collected Operator decision and its optional free-text payload.

    The payload is collected and returned as data (RFC-0001 §5: collect
    approvals, refusals, and free-text input); the caller delivers it — the
    goal to ``advance(goal=...)``, the reply text to the injected responder
    seam, the refine/override text to the record seam. `collect` never uses the
    payload itself (I-5: never into a command).
    """

    decision: Decision
    payload: str | None = None


def to_event(collected: Collected, *, routes_to: State | None = None) -> RuntimeEvent:
    """The RFC-0002 §4.1 operator event for a collected decision (DN-99).

    A total, deterministic 1:1 mapping (RFC-0007 S7). REPLY requires the
    outstanding-question routing (RFC-0002 §2.11) and is refused by the core
    type's own rule unless the route is Diagnosis or Planning. Applicability to
    the session state is **not** checked here — `core.advance`/`Session.apply`
    refuses an inapplicable event and the caller presents the `Refusal`
    honestly (DN-99; I-9).
    """
    decision = collected.decision
    if decision is Decision.GOAL:
        return OpGoal()
    if decision is Decision.REPLY:
        return OpReply(routes_to=routes_to)
    if decision is Decision.APPROVE:
        return OpApprove()
    if decision is Decision.OVERRIDE:
        return OpOverride()
    if decision is Decision.REJECT:
        return OpReject()
    if decision is Decision.REFINE:
        return OpRefine()
    if decision is Decision.CANCEL:
        return OpCancel()
    if decision is Decision.INTERRUPT:
        return OpInterrupt()
    if decision is Decision.EXIT:
        return OpExit()
    return OpView()
