"""The RFC-0002 session lifecycle: startup, goal adoption, and the outcome return.

Owner: RFC-0002 §1 (Session Lifecycle), §2.1 (Session Initialization), §2.2
    (Idle), §4.1 (Operator events: OP_GOAL, OP_EXIT); RFC-0013 §7 (cat. 1
    Session records — goal adoption and outcome, session lifecycle).
Responsibility: the single-goal, serial session lifecycle as a frozen value.
    ``Session`` holds the current ``State`` and the adopted goal statement; it
    is the one place state advances, and every transition is delegated to the
    authoritative state machine (``state_machine.evolve``), so no second
    competing state machine exists (DN-86). ``start`` runs the §2.1
    safety-critical prerequisite checks — injected and deterministic (DN-55) —
    and is fail-closed: any unmet prerequisite refuses service and ends the
    session (§2.1; RFC-0001 §8). ``adopt_goal`` adopts a goal from Idle
    (Idle → Machine Inspection) with its RFC-0013 §7 goal-adoption record
    bundled before the consequence (I-13), and returns to Idle from a goal
    outcome — the outcome terminals lead only to Idle (§2.2, §4.1; walkthrough
    Stage 17). ``stop`` leaves the runtime from Idle or an outcome (→ END) and
    refuses from an active goal: the interrupt protocol runs first (§4.1; §8;
    C4/RFC-0014). ``apply`` is the general transition mechanism the session
    loop (C3) drives; OP_GOAL and OP_EXIT are refused here and go through
    ``adopt_goal``/``stop``, so goal adoption and exit each have a single
    guarded path. Every consequence is bundled with its boundary record
    (I-13, AU3); the durable audit write is the C3 boundary writer's (DN-88).
Forbidden responsibility: no transition outside the state machine's §2/§3/§2.9
    reachable set; no audit write, no policy/classification/approval/execution
    logic (RFC-0002 §9; RFC-0004 §4.3); no I/O, no clock, no randomness, no
    hidden mutable state (DN-55; DN-94).
"""

from __future__ import annotations

from dataclasses import dataclass

from episky.core.events import AuditRecord, EventKind, OpExit, OpGoal, RuntimeEvent
from episky.core.state_machine import GOAL_ACTIVE, Refusal, State, evolve

__all__ = ["Prerequisites", "Session", "Step"]


@dataclass(frozen=True, slots=True)
class Prerequisites:
    """The §2.1 safety-critical startup prerequisites, injected (DN-55).

    All three must hold for the session to enter service; any failure is
    fail-closed (RFC-0001 §8): the runtime refuses to enter service and ends.
    """

    elevation_available: bool
    machine_fingerprint_verified: bool
    audit_writable: bool


@dataclass(frozen=True, slots=True)
class Step:
    """One session step: the next ``Session`` bundled with its boundary record.

    The record accompanies the consequence (I-13, AU3): a state change never
    exists without its RFC-0013 §7 record.
    """

    session: Session
    record: AuditRecord


#: The goal outcomes (§1 point 4): the terminals that lead only to Idle.
_OUTCOMES: frozenset[State] = frozenset(
    {State.COMPLETED, State.FAILED, State.CANCELLED}
)


@dataclass(frozen=True, slots=True)
class Session:
    """The single-goal, serial session lifecycle, as a frozen value.

    ``state`` is the RFC-0002 §2 runtime state; ``goal`` is the adopted goal
    statement (RFC-0003 §2.6 Goal — a statement of desired machine state, held
    verbatim; normalization is the loop's, C3). ``goal`` is set on adoption
    and cleared on the return to Idle. Every method returns a new ``Session``;
    the receiver is never mutated. Transitions are delegated to the state
    machine (DN-86); the session holds no other state and no authority.
    """

    state: State
    goal: str | None

    @classmethod
    def initial(cls) -> Session:
        """A fresh session: Session Initialization, no goal (§2.1 entry)."""
        return cls(State.INITIALIZING, None)

    def start(self, prerequisites: Prerequisites) -> Session | Refusal:
        """The §2.1 prerequisite gate: enter service (Idle) or fail closed (END).

        From Session Initialization only. All three safety-critical
        prerequisites met → Idle (fresh session); any unmet prerequisite →
        END (the runtime refuses to enter service and exits, RFC-0001 §8).
        The resume path (→ Machine Inspection) is RFC-0014's, not C2's. No §4
        event names the fresh-startup boundary, so ``start`` is a lifecycle
        gate and carries no event record (the startup session-lifecycle record
        is the C3 boundary writer's, DN-88).
        """
        if self.state is not State.INITIALIZING:
            return Refusal("start applies only in Session Initialization")
        if not (
            prerequisites.elevation_available
            and prerequisites.machine_fingerprint_verified
            and prerequisites.audit_writable
        ):
            return Session(State.END, None)
        return Session(State.IDLE, None)

    def adopt_goal(self, statement: str) -> Step | Refusal:
        """Adopt a goal from Idle, or return to Idle from a goal outcome (OP_GOAL).

        From Idle: Idle → Machine Inspection; the goal statement is adopted
            (held verbatim) and its RFC-0013 §7 goal-adoption record
            accompanies the consequence (I-13).
        From a goal outcome (Completed/Failed/Cancelled): → Idle only — the
            outcome terminals lead only to Idle (§2.2, §4.1; §1 point 4) —
            and the finished goal is cleared.
        Refused while a goal is active (single-goal and serial; no parallel
            goal, §1) and for a malformed statement. Goal revision in Awaiting
            Input is the loop's continuation, not adoption (C3; §2.11, §4.1).
        """
        if not isinstance(statement, str) or not statement.strip():
            return Refusal("a goal must be a non-empty statement")
        if self.state in GOAL_ACTIVE:
            return Refusal(
                "a goal is active; the lifecycle is single-goal and serial "
                "(no parallel goal)"
            )
        result = evolve(self.state, OpGoal())
        if isinstance(result, Refusal):
            return result
        if result.new_state is State.INSPECTING:
            new_goal = statement
        elif result.new_state is State.IDLE:
            new_goal = None
        else:
            return Refusal(
                f"OP_GOAL from {self.state.name} cannot reach "
                f"{result.new_state.name}: not a goal-adoption or Idle return"
            )
        return Step(Session(result.new_state, new_goal), result.record)

    def stop(self) -> Step | Refusal:
        """Leave the runtime (OP_EXIT; §4.1): from Idle or an outcome → END.

        From an active goal, refused: the interrupt protocol (state accounted,
        resume marker written if a goal is unfinished) runs first (§4.1; §8;
        C4/RFC-0014) — C2 cannot silently skip it. From Session Initialization
        or END, refused (the machine's OP_EXIT dispatch excludes them).
        """
        if self.state is State.INITIALIZING or self.state is State.END:
            return Refusal("the runtime is not running")
        if self.state in GOAL_ACTIVE:
            return Refusal(
                "the interrupt protocol runs first before exiting an active "
                "goal (RFC-0002 §4.1; C4/RFC-0014)"
            )
        result = evolve(self.state, OpExit())
        if isinstance(result, Refusal):
            return result
        return Step(Session(State.END, None), result.record)

    def apply(self, event: RuntimeEvent) -> Step | Refusal:
        """Apply ``event`` through the authoritative state machine.

        The general transition mechanism the session loop (C3) drives: the
        event's own per-event dispatch (events.py) is resolved against the
        §2/§3/§2.9 reachable oracle, so only ratified transitions can occur
        (DN-86). The goal is carried forward. Goal adoption and exit have
        single guarded paths — OP_GOAL → ``adopt_goal``, OP_EXIT → ``stop`` —
        and are refused here.
        """
        if event.kind is EventKind.OP_GOAL:
            return Refusal("OP_GOAL goes through adopt_goal")
        if event.kind is EventKind.OP_EXIT:
            return Refusal("OP_EXIT goes through stop")
        result = evolve(self.state, event)
        if isinstance(result, Refusal):
            return result
        return Step(Session(result.new_state, self.goal), result.record)
