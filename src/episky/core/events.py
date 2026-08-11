"""The RFC-0002 §4 event catalog with per-event dispatch (RFC-0002 §4; RFC-0013 §7).

Owner: RFC-0002 §4.1–§4.7 (Events); RFC-0013 §7 (Audit Record Categories),
    §23 (the write points are runtime boundaries).
Responsibility: the typed §4.1–§4.7 catalog — every event exists as a frozen,
    slot-based dataclass carrying its ``kind``, its RFC-0013 §7 record
    ``category``, and its per-event dispatch (the event → transition relation
    declared once): ``next_state(state)`` yields the target state, the same
    state for a recorded no-op, or None when the event does not apply there.
    The transition-less, information-only events — OP_VIEW, ACTION_STARTED,
    ACTION_CLASSIFIED — change no state and emit audited notes (DN-87; Q3).
    Every consequential event carries the record category it is written under,
    so the audit mapping is complete by construction (AU3; AU6; I-13). The
    ``Deadline`` primitive (Q8) is the injected-deadline token the TIMEOUT
    event carries. ``AuditRecord`` is the deterministic, metadata-only record
    the state machine bundles with a consequence (RFC-0001 §7.6; SC4).
Forbidden responsibility: no transition outside the state machine's §2/§3
    reachable set (state_machine.py enforces it); no audit writing, no routing
    decisions, no I/O, no clock, no randomness, no hidden state (DN-55; DN-94).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum, auto
from typing import ClassVar

from episky.core.state_machine import GOAL_ACTIVE, State

__all__ = [
    "CATALOG",
    "INFORMATION_ONLY",
    "AuditRecord",
    "ActionBlocked",
    "ActionClassified",
    "ActionFailed",
    "ActionInterrupted",
    "ActionPartial",
    "ActionStarted",
    "ActionSucceeded",
    "ActionTimeout",
    "CollectorFailed",
    "ConfigChanged",
    "ContextFull",
    "Deadline",
    "EventKind",
    "FactsCollected",
    "OpApprove",
    "OpCancel",
    "OpExit",
    "OpGoal",
    "OpInterrupt",
    "OpOverride",
    "OpRefine",
    "OpReject",
    "OpReply",
    "OpView",
    "PartialHalt",
    "PlanReady",
    "PlanRefined",
    "PlanRejected",
    "ProviderFallbackFailed",
    "ProviderFallbackOk",
    "ProviderRefusal",
    "ProviderResponse",
    "ProviderTimeout",
    "ProviderUnavailable",
    "RebootDetected",
    "RebootRequested",
    "RecordCategory",
    "RuntimeEvent",
    "SkillUnavailable",
    "StateChangedDetected",
    "Timeout",
    "VerificationFailed",
    "VerificationInconclusive",
    "VerificationPassed",
]


class EventKind(Enum):
    """The full §4.1–§4.7 event vocabulary, in the catalog's order (DN-87)."""

    OP_GOAL = auto()
    OP_REPLY = auto()
    OP_APPROVE = auto()
    OP_OVERRIDE = auto()
    OP_REJECT = auto()
    OP_REFINE = auto()
    OP_CANCEL = auto()
    OP_INTERRUPT = auto()
    OP_EXIT = auto()
    OP_VIEW = auto()
    FACTS_COLLECTED = auto()
    COLLECTOR_FAILED = auto()
    STATE_CHANGED_DETECTED = auto()
    PROVIDER_RESPONSE = auto()
    PROVIDER_REFUSAL = auto()
    PROVIDER_UNAVAILABLE = auto()
    PROVIDER_TIMEOUT = auto()
    PROVIDER_FALLBACK_OK = auto()
    PROVIDER_FALLBACK_FAILED = auto()
    PLAN_READY = auto()
    ACTION_CLASSIFIED = auto()
    ACTION_BLOCKED = auto()
    PLAN_REJECTED = auto()
    PLAN_REFINED = auto()
    ACTION_STARTED = auto()
    ACTION_SUCCEEDED = auto()
    ACTION_FAILED = auto()
    ACTION_TIMEOUT = auto()
    ACTION_INTERRUPTED = auto()
    ACTION_PARTIAL = auto()
    VERIFICATION_PASSED = auto()
    VERIFICATION_FAILED = auto()
    VERIFICATION_INCONCLUSIVE = auto()
    SKILL_UNAVAILABLE = auto()
    CONTEXT_FULL = auto()
    TIMEOUT = auto()
    REBOOT_REQUESTED = auto()
    REBOOT_DETECTED = auto()
    CONFIG_CHANGED = auto()


class RecordCategory(Enum):
    """The RFC-0013 §7 audit record categories, in the section's order."""

    SESSION = auto()
    PROPOSAL = auto()
    CLASSIFICATION = auto()
    APPROVAL = auto()
    OVERRIDE = auto()
    EXECUTION = auto()
    VERIFICATION = auto()
    FACT_LIFECYCLE = auto()
    CONTEXT_BOUNDARY = auto()
    SECRET_METADATA = auto()
    SKILL_EVENT = auto()
    OPERATOR_VISIBILITY = auto()


class PartialHalt(Enum):
    """Why a batch stopped partway (RFC-0002 §4.5 ACTION_PARTIAL)."""

    INTERRUPTED = auto()
    CANCELLED = auto()


@dataclass(frozen=True, slots=True)
class Deadline:
    """An injected phase-deadline primitive (Q8, DN-92).

    Numeric budgets are RFC-0020's; the deadline is a token the phase watchdog
    carries. It is data, never a clock read.
    """

    phase: str


@dataclass(frozen=True, slots=True)
class AuditRecord:
    """The deterministic, metadata-only record for one boundary (RFC-0013 §7).

    Written by the runtime before the consequence (I-13; AU3; AU8). Holds the
    record category, the event kind, and the boundary states — never material
    (RFC-0001 §7.6; SC4).
    """

    category: RecordCategory
    kind: EventKind
    from_state: State
    to_state: State


class RuntimeEvent:
    """Base of every §4 event: kind, RFC-0013 §7 category, per-event dispatch.

    Not itself a dataclass: the shared ``kind``/``category``/``information_only``
    and ``_DISPATCH`` are class attributes carried by each concrete event, so a
    subclass's ``__dataclass_fields__`` is exactly the fields it declares.
    ``next_state`` declares the event → transition relation once: the target
    state from a given state, the same state for a recorded no-op, or None
    when the event does not apply there. Information-only events apply in
    every state and never change it (DN-87).
    """

    kind: ClassVar[EventKind]
    category: ClassVar[RecordCategory]
    information_only: ClassVar[bool] = False
    _DISPATCH: ClassVar[Mapping[State, State]] = {}

    def next_state(self, state: State) -> State | None:
        """The target state from ``state``, or None when the event does not apply."""
        if self.information_only:
            return state
        return self._DISPATCH.get(state)

    def record(self, from_state: State, to_state: State) -> AuditRecord:
        """The deterministic RFC-0013 §7 record for this boundary (metadata only)."""
        return AuditRecord(
            category=self.category,
            kind=self.kind,
            from_state=from_state,
            to_state=to_state,
        )


# ---------------------------------------------------------------------------
# §4.1 Operator events
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class OpGoal(RuntimeEvent):
    """§4.1 OP_GOAL — the Operator states or revises a goal (RFC-0002 §4.1)."""

    kind = EventKind.OP_GOAL
    category = RecordCategory.SESSION
    _DISPATCH = {
        State.IDLE: State.INSPECTING,
        State.AWAITING_INPUT: State.DIAGNOSING,
        State.COMPLETED: State.IDLE,
        State.FAILED: State.IDLE,
        State.CANCELLED: State.IDLE,
    }


@dataclass(frozen=True, slots=True)
class OpReply(RuntimeEvent):
    """§4.1 OP_REPLY — a free-text answer, context-routed to Diagnosis or Planning."""

    kind = EventKind.OP_REPLY
    category = RecordCategory.PROPOSAL
    routes_to: State

    def __post_init__(self) -> None:
        if self.routes_to not in (State.DIAGNOSING, State.PLANNING):
            raise ValueError(
                f"OP_REPLY routes to Diagnosis or Planning only, got "
                f"{self.routes_to!r}"
            )

    def next_state(self, state: State) -> State | None:
        if state is not State.AWAITING_INPUT:
            return None
        return self.routes_to


@dataclass(frozen=True, slots=True)
class OpApprove(RuntimeEvent):
    """§4.1 OP_APPROVE — the Operator approves the presented actions."""

    kind = EventKind.OP_APPROVE
    category = RecordCategory.APPROVAL
    _DISPATCH = {State.AWAITING_APPROVAL: State.EXECUTING}


@dataclass(frozen=True, slots=True)
class OpOverride(RuntimeEvent):
    """§4.1 OP_OVERRIDE — the explicit, audited override of a blocked action (I-12)."""

    kind = EventKind.OP_OVERRIDE
    category = RecordCategory.OVERRIDE
    _DISPATCH = {State.AWAITING_APPROVAL: State.EXECUTING}


@dataclass(frozen=True, slots=True)
class OpReject(RuntimeEvent):
    """§4.1 OP_REJECT — the Operator rejects the presented actions
    (reason → evidence)."""

    kind = EventKind.OP_REJECT
    category = RecordCategory.PROPOSAL
    _DISPATCH = {State.AWAITING_APPROVAL: State.REPLANNING}


@dataclass(frozen=True, slots=True)
class OpRefine(RuntimeEvent):
    """§4.1 OP_REFINE — the Operator requests plan changes."""

    kind = EventKind.OP_REFINE
    category = RecordCategory.PROPOSAL
    _DISPATCH = {State.AWAITING_APPROVAL: State.REPLANNING}


@dataclass(frozen=True, slots=True)
class OpCancel(RuntimeEvent):
    """§4.1 OP_CANCEL — abandon the goal from any active state (shortcut, §3/DN-86)."""

    kind = EventKind.OP_CANCEL
    category = RecordCategory.SESSION
    _DISPATCH = dict.fromkeys(GOAL_ACTIVE, State.CANCELLED)


@dataclass(frozen=True, slots=True)
class OpInterrupt(RuntimeEvent):
    """§4.1 OP_INTERRUPT — Ctrl+C; machine work → Interrupted, cognitive → Awaiting
    Input, a second press from a halt → END (shortcut, §3; RFC-0002 §2.11/§2.12)."""

    kind = EventKind.OP_INTERRUPT
    category = RecordCategory.SESSION
    _DISPATCH = {
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
    }


@dataclass(frozen=True, slots=True)
class OpExit(RuntimeEvent):
    """§4.1 OP_EXIT — leave the runtime from Idle, a goal outcome, or an active
    state (the interrupt protocol runs first; §3/DN-86)."""

    kind = EventKind.OP_EXIT
    category = RecordCategory.SESSION
    _DISPATCH = {
        state: State.END
        for state in State
        if state not in (State.INITIALIZING, State.END)
    }


@dataclass(frozen=True, slots=True)
class OpView(RuntimeEvent):
    """§4.1 OP_VIEW — informational only; renders Context or Audit, no state change."""

    kind = EventKind.OP_VIEW
    category = RecordCategory.OPERATOR_VISIBILITY
    information_only = True


# ---------------------------------------------------------------------------
# §4.2 Machine events
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class FactsCollected(RuntimeEvent):
    """§4.2 FACTS_COLLECTED — an inspection returned facts, fully or partially."""

    kind = EventKind.FACTS_COLLECTED
    category = RecordCategory.FACT_LIFECYCLE
    _DISPATCH = {State.INSPECTING: State.BUILDING}


@dataclass(frozen=True, slots=True)
class CollectorFailed(RuntimeEvent):
    """§4.2 COLLECTOR_FAILED — a diagnostic failed or timed out.

    Non-critical: recorded as "fact unknown"; inspection continues. Critical:
    disclose → Awaiting Input; hopeless → Failed (RFC-0002 §2.3/§4.2, §10).
    """

    kind = EventKind.COLLECTOR_FAILED
    category = RecordCategory.FACT_LIFECYCLE
    critical: bool = False
    hopeless: bool = False

    def __post_init__(self) -> None:
        if self.hopeless:
            object.__setattr__(self, "critical", True)

    def next_state(self, state: State) -> State | None:
        if state is not State.INSPECTING:
            return None
        if self.hopeless:
            return State.FAILED
        if self.critical:
            return State.AWAITING_INPUT
        return state


@dataclass(frozen=True, slots=True)
class StateChangedDetected(RuntimeEvent):
    """§4.2 STATE_CHANGED_DETECTED — the read-only watchdog saw external change.

    In Awaiting Approval the approval is invalidated → Machine Inspection;
    elsewhere dependent facts are invalidated (context marked stale) and the
    next fact-consuming decision re-inspects first — no transition here.
    """

    kind = EventKind.STATE_CHANGED_DETECTED
    category = RecordCategory.FACT_LIFECYCLE

    def next_state(self, state: State) -> State | None:
        if state is State.END:
            return None
        if state is State.AWAITING_APPROVAL:
            return State.INSPECTING
        return state


# ---------------------------------------------------------------------------
# §4.3 Provider events
# ---------------------------------------------------------------------------

_COGNITIVE = frozenset({State.DIAGNOSING, State.PLANNING, State.REPLANNING})


def _cognitive_noop(state: State) -> State | None:
    """Recorded no-op in the cognitive states (RFC-0002 §4.3 consumption rule)."""
    return state if state in _COGNITIVE else None


@dataclass(frozen=True, slots=True)
class ProviderResponse(RuntimeEvent):
    """§4.3 PROVIDER_RESPONSE — the LLM returned a valid, parseable reply."""

    kind = EventKind.PROVIDER_RESPONSE
    category = RecordCategory.PROPOSAL

    next_state = staticmethod(_cognitive_noop)


@dataclass(frozen=True, slots=True)
class ProviderRefusal(RuntimeEvent):
    """§4.3 PROVIDER_REFUSAL — the provider declined or produced unusable output."""

    kind = EventKind.PROVIDER_REFUSAL
    category = RecordCategory.PROPOSAL

    next_state = staticmethod(_cognitive_noop)


@dataclass(frozen=True, slots=True)
class ProviderUnavailable(RuntimeEvent):
    """§4.3 PROVIDER_UNAVAILABLE — connection or service failure (bounded retry)."""

    kind = EventKind.PROVIDER_UNAVAILABLE
    category = RecordCategory.PROPOSAL

    next_state = staticmethod(_cognitive_noop)


@dataclass(frozen=True, slots=True)
class ProviderTimeout(RuntimeEvent):
    """§4.3 PROVIDER_TIMEOUT — no reply within the phase bound."""

    kind = EventKind.PROVIDER_TIMEOUT
    category = RecordCategory.PROPOSAL

    next_state = staticmethod(_cognitive_noop)


@dataclass(frozen=True, slots=True)
class ProviderFallbackOk(RuntimeEvent):
    """§4.3 PROVIDER_FALLBACK_OK — a fallback provider is usable; the cognitive
    phase continues with a fresh Context Building (the fresh-View rule is
    consultation.py's, C3/DN-93)."""

    kind = EventKind.PROVIDER_FALLBACK_OK
    category = RecordCategory.PROPOSAL

    next_state = staticmethod(_cognitive_noop)


@dataclass(frozen=True, slots=True)
class ProviderFallbackFailed(RuntimeEvent):
    """§4.3 PROVIDER_FALLBACK_FAILED — no provider is usable → degraded mode →
    Awaiting Input (facts-only presentation; no recommendations; I-9)."""

    kind = EventKind.PROVIDER_FALLBACK_FAILED
    category = RecordCategory.PROPOSAL
    _DISPATCH = {
        State.DIAGNOSING: State.AWAITING_INPUT,
        State.PLANNING: State.AWAITING_INPUT,
        State.REPLANNING: State.AWAITING_INPUT,
    }


# ---------------------------------------------------------------------------
# §4.4 Plan and approval events
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PlanReady(RuntimeEvent):
    """§4.4 PLAN_READY — a plan was normalized into discrete proposed actions."""

    kind = EventKind.PLAN_READY
    category = RecordCategory.PROPOSAL
    _DISPATCH = {State.PLANNING: State.AWAITING_APPROVAL}


@dataclass(frozen=True, slots=True)
class ActionClassified(RuntimeEvent):
    """§4.4 ACTION_CLASSIFIED — the engine assigned a risk class and gate.

    Informational: determines presentation; no state change (DN-87).
    """

    kind = EventKind.ACTION_CLASSIFIED
    category = RecordCategory.CLASSIFICATION
    information_only = True


@dataclass(frozen=True, slots=True)
class ActionBlocked(RuntimeEvent):
    """§4.4 ACTION_BLOCKED — an action was classified as blocked; it is presented
    as blocked and proceeds only through an audited OP_OVERRIDE (I-12)."""

    kind = EventKind.ACTION_BLOCKED
    category = RecordCategory.CLASSIFICATION

    def next_state(self, state: State) -> State | None:
        return state if state is State.AWAITING_APPROVAL else None


_PRESENTED = frozenset({State.AWAITING_APPROVAL, State.REPLANNING})


@dataclass(frozen=True, slots=True)
class PlanRejected(RuntimeEvent):
    """§4.4 PLAN_REJECTED — the rejection is folded in as evidence (OP_REJECT
    drives the transition; this records the folded-in outcome)."""

    kind = EventKind.PLAN_REJECTED
    category = RecordCategory.PROPOSAL

    def next_state(self, state: State) -> State | None:
        return state if state in _PRESENTED else None


@dataclass(frozen=True, slots=True)
class PlanRefined(RuntimeEvent):
    """§4.4 PLAN_REFINED — the refinement request is folded in (OP_REFINE drives
    the transition; this records the folded-in outcome)."""

    kind = EventKind.PLAN_REFINED
    category = RecordCategory.PROPOSAL

    def next_state(self, state: State) -> State | None:
        return state if state in _PRESENTED else None


# ---------------------------------------------------------------------------
# §4.5 Execution events
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ActionStarted(RuntimeEvent):
    """§4.5 ACTION_STARTED — internal; audited; no state change (DN-87)."""

    kind = EventKind.ACTION_STARTED
    category = RecordCategory.EXECUTION
    information_only = True


@dataclass(frozen=True, slots=True)
class ActionSucceeded(RuntimeEvent):
    """§4.5 ACTION_SUCCEEDED — exit status and deterministic signal → Verification."""

    kind = EventKind.ACTION_SUCCEEDED
    category = RecordCategory.EXECUTION
    _DISPATCH = {State.EXECUTING: State.VERIFYING}


@dataclass(frozen=True, slots=True)
class ActionFailed(RuntimeEvent):
    """§4.5 ACTION_FAILED — → Verification first to establish the actual state (I-2)."""

    kind = EventKind.ACTION_FAILED
    category = RecordCategory.EXECUTION
    _DISPATCH = {State.EXECUTING: State.VERIFYING}


@dataclass(frozen=True, slots=True)
class ActionTimeout(RuntimeEvent):
    """§4.5 ACTION_TIMEOUT — the watchdog killed the action → Interrupted (state
    unknown; I-8; the §3 shortcut, DN-86)."""

    kind = EventKind.ACTION_TIMEOUT
    category = RecordCategory.EXECUTION
    _DISPATCH = {State.EXECUTING: State.INTERRUPTED}


@dataclass(frozen=True, slots=True)
class ActionInterrupted(RuntimeEvent):
    """§4.5 ACTION_INTERRUPTED — the action was killed mid-run → Interrupted."""

    kind = EventKind.ACTION_INTERRUPTED
    category = RecordCategory.EXECUTION
    _DISPATCH = {State.EXECUTING: State.INTERRUPTED}


@dataclass(frozen=True, slots=True)
class ActionPartial(RuntimeEvent):
    """§4.5 ACTION_PARTIAL — a batch stopped partway → Interrupted or Cancelled,
    with exact accounting of which steps ran (RFC-0002 §2.8, §10)."""

    kind = EventKind.ACTION_PARTIAL
    category = RecordCategory.EXECUTION
    halt: PartialHalt

    def __post_init__(self) -> None:
        if not isinstance(self.halt, PartialHalt):
            raise TypeError(f"halt must be a PartialHalt, got {self.halt!r}")

    def next_state(self, state: State) -> State | None:
        if state is not State.EXECUTING:
            return None
        if self.halt is PartialHalt.CANCELLED:
            return State.CANCELLED
        return State.INTERRUPTED


# ---------------------------------------------------------------------------
# §4.6 Verification events
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class VerificationPassed(RuntimeEvent):
    """§4.6 VERIFICATION_PASSED — → Completed if no steps remain, else → Executing
    (the §2.9 next approved step)."""

    kind = EventKind.VERIFICATION_PASSED
    category = RecordCategory.VERIFICATION
    steps_remaining: bool

    def next_state(self, state: State) -> State | None:
        if state is not State.VERIFYING:
            return None
        if self.steps_remaining:
            return State.EXECUTING
        return State.COMPLETED


@dataclass(frozen=True, slots=True)
class VerificationFailed(RuntimeEvent):
    """§4.6 VERIFICATION_FAILED — the post-condition was not met → Replanning."""

    kind = EventKind.VERIFICATION_FAILED
    category = RecordCategory.VERIFICATION
    _DISPATCH = {State.VERIFYING: State.REPLANNING}


@dataclass(frozen=True, slots=True)
class VerificationInconclusive(RuntimeEvent):
    """§4.6 VERIFICATION_INCONCLUSIVE — the state cannot be observed → Awaiting
    Input; no success is claimed (I-9)."""

    kind = EventKind.VERIFICATION_INCONCLUSIVE
    category = RecordCategory.VERIFICATION
    _DISPATCH = {State.VERIFYING: State.AWAITING_INPUT}


# ---------------------------------------------------------------------------
# §4.7 System events
# ---------------------------------------------------------------------------


@dataclass(frozen=True, slots=True)
class SkillUnavailable(RuntimeEvent):
    """§4.7 SKILL_UNAVAILABLE — a referenced skill cannot load or authenticate; its
    material is refused and the plan/diagnosis is revised without it."""

    kind = EventKind.SKILL_UNAVAILABLE
    category = RecordCategory.SKILL_EVENT

    next_state = staticmethod(_cognitive_noop)


@dataclass(frozen=True, slots=True)
class ContextFull(RuntimeEvent):
    """§4.7 CONTEXT_FULL — the context ceiling was reached; consolidation happens,
    transparently, then Context Building is re-entered (no state change here)."""

    kind = EventKind.CONTEXT_FULL
    category = RecordCategory.CONTEXT_BOUNDARY

    def next_state(self, state: State) -> State | None:
        return state if state is State.BUILDING else None


_COGNITIVE = frozenset({State.DIAGNOSING, State.PLANNING, State.REPLANNING})
_MACHINE_HALT = frozenset({State.INSPECTING, State.EXECUTING, State.VERIFYING})


@dataclass(frozen=True, slots=True)
class Timeout(RuntimeEvent):
    """§4.7 TIMEOUT — a phase watchdog fired (stalled phase; Q8, DN-92).

    Cognitive → Awaiting Input (disclose); machine-touching → Interrupted.
    Carries the injected ``Deadline`` it fired against.
    """

    kind = EventKind.TIMEOUT
    category = RecordCategory.SESSION
    deadline: Deadline

    def __post_init__(self) -> None:
        if not isinstance(self.deadline, Deadline):
            raise TypeError(f"deadline must be a Deadline, got {self.deadline!r}")

    def next_state(self, state: State) -> State | None:
        if state in _COGNITIVE:
            return State.AWAITING_INPUT
        if state in _MACHINE_HALT:
            return State.INTERRUPTED
        if state is State.AWAITING_APPROVAL:
            return State.INTERRUPTED
        if state in (State.BUILDING, State.AWAITING_INPUT):
            return state
        return None


@dataclass(frozen=True, slots=True)
class RebootRequested(RuntimeEvent):
    """§4.7 REBOOT_REQUESTED — the approved plan includes a reboot → write a
    resume marker → END (machine reboots; RFC-0002 §8)."""

    kind = EventKind.REBOOT_REQUESTED
    category = RecordCategory.SESSION
    _DISPATCH = {State.EXECUTING: State.END}


@dataclass(frozen=True, slots=True)
class RebootDetected(RuntimeEvent):
    """§4.7 REBOOT_DETECTED — the runtime is starting after a reboot → the resume
    path: Session Initialization → Machine Inspection (re-orient)."""

    kind = EventKind.REBOOT_DETECTED
    category = RecordCategory.SESSION
    _DISPATCH = {State.INITIALIZING: State.INSPECTING}


@dataclass(frozen=True, slots=True)
class ConfigChanged(RuntimeEvent):
    """§4.7 CONFIG_CHANGED — configuration or policy was reloaded. Informational;
    outstanding approvals are re-validated against the new policy (RFC-0008 P9)."""

    kind = EventKind.CONFIG_CHANGED
    category = RecordCategory.SESSION

    def next_state(self, state: State) -> State | None:
        return None if state is State.END else state


#: The §4.1–§4.7 catalog, in the RFC's order (DN-87).
CATALOG: tuple[type[RuntimeEvent], ...] = (
    OpGoal,
    OpReply,
    OpApprove,
    OpOverride,
    OpReject,
    OpRefine,
    OpCancel,
    OpInterrupt,
    OpExit,
    OpView,
    FactsCollected,
    CollectorFailed,
    StateChangedDetected,
    ProviderResponse,
    ProviderRefusal,
    ProviderUnavailable,
    ProviderTimeout,
    ProviderFallbackOk,
    ProviderFallbackFailed,
    PlanReady,
    ActionClassified,
    ActionBlocked,
    PlanRejected,
    PlanRefined,
    ActionStarted,
    ActionSucceeded,
    ActionFailed,
    ActionTimeout,
    ActionInterrupted,
    ActionPartial,
    VerificationPassed,
    VerificationFailed,
    VerificationInconclusive,
    SkillUnavailable,
    ContextFull,
    Timeout,
    RebootRequested,
    RebootDetected,
    ConfigChanged,
)

#: The transition-less, information-only events (DN-87; Q3): audited notes,
#: no state change, applicable in every state.
INFORMATION_ONLY: frozenset[EventKind] = frozenset(
    {EventKind.OP_VIEW, EventKind.ACTION_STARTED, EventKind.ACTION_CLASSIFIED}
)
