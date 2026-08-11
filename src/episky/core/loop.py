"""The RFC-0002 §5 session-loop conductor (RFC-0002 §5, §6; RFC-0008 §5/§8).

Owner: RFC-0002 §5 (The Session Loop — the ordered sequence in which
    subsystems participate), §6 (Component Consultation Rules — when each
    subsystem is consulted, and when it is never consulted), §9 I-1/I-4/I-6/
    I-11/I-13; RFC-0008 §5 (Approval Units), §8 (Tokens); RFC-0004 §4.3 (the
    Orchestrator routes, never decides — propose/refuse/explain only);
    RFC-0013 §7 (record categories), §23 (write points, before the
    consequence); DN-86 (the reachable set), DN-88 (core is the single
    runtime writer, fail-closed AU8), DN-89 (token re-validation at the
    Awaiting Approval → Executing edge), DN-91 (degraded mode is facts-only),
    DN-93 (the fresh-View rule), DN-94 (injected, deterministic responders;
    I/O-free core).
Responsibility: the conductor. ``Loop`` is the frozen set of injected,
    deterministic responders (design-review §6 injection points: inspect,
    assemble, provider_reply, skill_plan, classify_and_gate, revalidate,
    run_executor, verify, record). ``pump`` advances a session through the
    autonomous phases of the 10-step loop — Machine Inspection, Context
    Building, Diagnosis, Planning, classification and gating, Execution,
    Verification, Replanning — until a pause point (Idle, Awaiting Approval,
    Awaiting Input, Interrupted, an outcome, or END), enforcing the §6
    consult matrix (consultation.py), the fresh-View rule (DN-93), the
    classify → gate → token → re-validate → Executor path (I-1/I-11/DN-89),
    and writing every boundary record via ``record`` before its consequence,
    fail-closed (I-13; AU8). ``advance`` applies one operator or §4 event
    (OP_GOAL via ``adopt_goal``, OP_EXIT via ``stop``, OP_APPROVE/OP_OVERRIDE
    through the DN-89 re-validation) under the same audit-before-consequence
    rule. The event-less §2 cognitive edges — Context Building →
    Diagnosis/Planning, Diagnosis → Planning, cognitive → Machine Inspection
    (fresh facts / fresh View), cognitive → Awaiting Input (context-routed),
    cognitive → Completed/Failed (diagnostic-only / hopeless) — are conductor
    continuations checked against the reachable oracle (DN-86) and carry no
    record: the closed §4 catalog (DN-87) has no event for them and a record
    exists only for an event's kind. The boundaries the catalog does name —
    goal adoption, proposal, classification, approval, override, execution
    start/end, verification, provider/Skill events — are all written here.
Forbidden responsibility: no classification, verification, approval, or
    execution logic (RFC-0004 §4.3; RFC-0002 §9 I-7) — the loop only routes,
    and the Executor is reachable only through classify → gate → token →
    re-validate; no I/O, no clock, no randomness, no hidden mutable state
    (DN-55; DN-94).
"""

from __future__ import annotations

from collections.abc import Callable, Mapping
from dataclasses import dataclass, field, replace
from enum import Enum, auto
from types import MappingProxyType

from episky.core.consultation import (
    Subsystem,
    may_consult,
    provider_consultation_allowed,
    skills_consultable,
)
from episky.core.events import (
    ActionBlocked,
    ActionClassified,
    ActionFailed,
    ActionInterrupted,
    ActionPartial,
    ActionStarted,
    ActionSucceeded,
    ActionTimeout,
    AuditRecord,
    CollectorFailed,
    EventKind,
    FactsCollected,
    OpReply,
    PartialHalt,
    PlanReady,
    ProviderFallbackFailed,
    ProviderResponse,
    RebootRequested,
    RuntimeEvent,
    VerificationFailed,
    VerificationInconclusive,
    VerificationPassed,
)
from episky.core.session import Session
from episky.core.state_machine import Refusal, State, permitted

__all__ = [
    "Consultation",
    "Decision",
    "GateResult",
    "Inspection",
    "Loop",
    "LoopStep",
    "Reply",
    "RunKind",
    "RunResult",
    "VerifyKind",
    "VerifyResult",
    "ViewResult",
    "Workstate",
    "WriteStatus",
    "advance",
    "pump",
]


class Decision(Enum):
    """A cognitive phase's structured outcome (RFC-0010 §4 as a decision)."""

    GROUNDED = auto()
    NEED_EVIDENCE = auto()
    CLARIFY = auto()
    DIAGNOSTIC_ONLY = auto()
    HOPELESS = auto()


class RunKind(Enum):
    """An executed Action's deterministic outcome (RFC-0002 §4.5)."""

    SUCCEEDED = auto()
    FAILED = auto()
    TIMEOUT = auto()
    INTERRUPTED = auto()
    PARTIAL = auto()
    REBOOT = auto()


class VerifyKind(Enum):
    """A verification's outcome (RFC-0002 §4.6)."""

    PASSED = auto()
    FAILED = auto()
    INCONCLUSIVE = auto()


class WriteStatus(Enum):
    """The audit writer's reply (AU8: a refused write blocks the consequence)."""

    OK = auto()
    REFUSED = auto()


@dataclass(frozen=True, slots=True)
class Inspection:
    """The inspect() result at Machine Inspection (RFC-0002 §2.3)."""

    facts: tuple = ()
    critical: bool = False
    hopeless: bool = False


@dataclass(frozen=True, slots=True)
class ViewResult:
    """The assemble() result at Context Building (RFC-0002 §2.4)."""

    view: object | None = None


@dataclass(frozen=True, slots=True)
class Reply:
    """A provider_reply()/skill_plan() result in a cognitive state."""

    decision: Decision
    plan: tuple = ()
    degraded: bool = False


@dataclass(frozen=True, slots=True)
class GateResult:
    """The classify_and_gate() result at the Planning → Awaiting Approval edge."""

    plan: tuple
    tokens: tuple
    blocked: tuple = ()


@dataclass(frozen=True, slots=True)
class RunResult:
    """The run_executor() result (RFC-0002 §2.8, §4.5)."""

    kind: RunKind
    steps_remaining: bool = False


@dataclass(frozen=True, slots=True)
class VerifyResult:
    """The verify() result (RFC-0002 §2.9, §4.6)."""

    kind: VerifyKind
    steps_remaining: bool = False


@dataclass(frozen=True, slots=True)
class Consultation:
    """One consultation of a subsystem in a state (RFC-0002 §6)."""

    subsystem: Subsystem
    state: State


@dataclass(frozen=True, slots=True)
class Workstate:
    """The conductor's working set, carried between steps (DN-94)."""

    view_is_fresh: bool = False
    view: object | None = None
    facts: object | None = None
    plan: object | None = None
    tokens: tuple = ()
    blocked: tuple = ()
    token: object | None = None
    route: State = State.DIAGNOSING
    presented: bool = False


@dataclass(frozen=True, slots=True)
class LoopStep:
    """One advance: the next Session with its boundary trace."""

    session: Session
    work: Workstate
    writes: tuple[AuditRecord, ...]
    consultations: tuple[Consultation, ...]
    disclosures: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Loop:
    """The conductor's injected, deterministic seams (design-review §6; DN-94)."""

    inspect: Callable[[Workstate], Inspection]
    assemble: Callable[[Workstate], ViewResult]
    provider_reply: Callable[[Workstate], Reply]
    skill_plan: Callable[[Workstate], Reply | None]
    classify_and_gate: Callable[[object, Workstate], GateResult]
    revalidate: Callable[[object, Workstate], bool]
    run_executor: Callable[[object, Workstate], RunResult]
    verify: Callable[[Workstate], VerifyResult]
    record: Callable[[AuditRecord], WriteStatus]


#: The pause points: states where the conductor stops and the Operator acts.
_PAUSE: frozenset[State] = frozenset(
    {
        State.INITIALIZING,
        State.IDLE,
        State.AWAITING_APPROVAL,
        State.AWAITING_INPUT,
        State.INTERRUPTED,
        State.COMPLETED,
        State.FAILED,
        State.CANCELLED,
        State.END,
    }
)

#: States where the approval envelope ends (I-11, I-15): a halt, a replan, or
#: an outcome leaves no standing authorization.
_BOUNDARY_CLEAR: frozenset[State] = frozenset(
    {
        State.INTERRUPTED,
        State.REPLANNING,
        State.CANCELLED,
        State.COMPLETED,
        State.FAILED,
    }
)

#: The cognitive phase routes (RFC-0002 §2.5, §2.6, §2.10). Planning's
#: GROUNDED exit is special-cased (classify → gate → Awaiting Approval).
_ROUTE: Mapping[State, Mapping[Decision, State]] = MappingProxyType(
    {
        State.DIAGNOSING: MappingProxyType(
            {
                Decision.GROUNDED: State.PLANNING,
                Decision.NEED_EVIDENCE: State.INSPECTING,
                Decision.CLARIFY: State.AWAITING_INPUT,
                Decision.DIAGNOSTIC_ONLY: State.COMPLETED,
                Decision.HOPELESS: State.FAILED,
            }
        ),
        State.PLANNING: MappingProxyType(
            {
                Decision.NEED_EVIDENCE: State.INSPECTING,
                Decision.CLARIFY: State.AWAITING_INPUT,
                Decision.DIAGNOSTIC_ONLY: State.COMPLETED,
                Decision.HOPELESS: State.FAILED,
            }
        ),
        State.REPLANNING: MappingProxyType(
            {
                Decision.GROUNDED: State.PLANNING,
                Decision.NEED_EVIDENCE: State.DIAGNOSING,
                Decision.CLARIFY: State.AWAITING_INPUT,
                Decision.DIAGNOSTIC_ONLY: State.PLANNING,
                Decision.HOPELESS: State.FAILED,
            }
        ),
    }
)


@dataclass(slots=True)
class _Trace:
    """A function-local accumulator, frozen into LoopStep (never escapes)."""

    writes: list[AuditRecord] = field(default_factory=list)
    consultations: list[Consultation] = field(default_factory=list)
    disclosures: list[str] = field(default_factory=list)


def _write(loop: Loop, record: AuditRecord, trace: _Trace) -> Refusal | None:
    """Write ``record`` before its consequence; fail-closed (I-13; AU8; DN-88)."""
    if loop.record(record) is not WriteStatus.OK:
        trace.disclosures.append(
            "an audit write was refused; the consequence is blocked (RFC-0013 §21; AU8)"
        )
        return Refusal("audit write refused before the consequence (I-13; AU8)")
    trace.writes.append(record)
    return None


def _write_event(
    loop: Loop, session: Session, work: Workstate, event: RuntimeEvent, trace: _Trace
) -> Refusal | tuple[Session, Workstate]:
    """Apply ``event`` through the session, writing its record before the effect."""
    step = session.apply(event)
    if isinstance(step, Refusal):
        return Refusal(step.reason)
    blocked = _write(loop, step.record, trace)
    if blocked is not None:
        return blocked
    return step.session, work


def _continue(
    session: Session, target: State, work: Workstate, trace: _Trace
) -> Refusal | tuple[Session, Workstate]:
    """The conductor's event-less §2 continuation, checked against DN-86."""
    if not permitted(session.state, target):
        return Refusal(
            f"{session.state.name} cannot continue to {target.name}: "
            "outside the RFC-0002 reachable set (DN-86)"
        )
    return Session(target, session.goal), work


def _inspect_phase(
    loop: Loop, session: Session, work: Workstate, trace: _Trace
) -> Refusal | tuple[Session, Workstate]:
    gate = may_consult(session.state, Subsystem.DIAGNOSTICS)
    if gate is not None:
        return Refusal(gate.reason)
    trace.consultations.append(Consultation(Subsystem.DIAGNOSTICS, session.state))
    result = loop.inspect(work)
    work = replace(work, facts=result.facts, view_is_fresh=False)
    if result.hopeless:
        return _write_event(loop, session, work, CollectorFailed(hopeless=True), trace)
    if result.critical:
        return _write_event(loop, session, work, CollectorFailed(critical=True), trace)
    return _write_event(loop, session, work, FactsCollected(), trace)


def _build_phase(
    loop: Loop, session: Session, work: Workstate, trace: _Trace
) -> Refusal | tuple[Session, Workstate]:
    gate = may_consult(session.state, Subsystem.CONTEXT)
    if gate is not None:
        return Refusal(gate.reason)
    trace.consultations.append(Consultation(Subsystem.CONTEXT, session.state))
    result = loop.assemble(work)
    if result.view is None:
        trace.disclosures.append(
            "no usable provider view could be assembled; disclosing and asking "
            "(RFC-0002 §2.4)"
        )
        return _continue(session, State.AWAITING_INPUT, work, trace)
    work = replace(work, view=result.view, view_is_fresh=True)
    return _continue(session, work.route, work, trace)


def _route_cognitive(
    loop: Loop, session: Session, work: Workstate, trace: _Trace, reply: Reply
) -> Refusal | tuple[Session, Workstate]:
    state = session.state
    if state is State.PLANNING and reply.decision is Decision.GROUNDED:
        if not reply.plan:
            return _continue(session, State.COMPLETED, work, trace)
        gate = loop.classify_and_gate(reply.plan, work)
        work = replace(
            work,
            plan=reply.plan,
            tokens=gate.tokens,
            blocked=gate.blocked,
            presented=False,
        )
        return _write_event(loop, session, work, PlanReady(), trace)
    target = _ROUTE[state][reply.decision]
    if target in (State.INSPECTING, State.AWAITING_INPUT):
        work = replace(work, route=state)
    else:
        work = replace(work, route=target)
    return _continue(session, target, work, trace)


def _cognitive_phase(
    loop: Loop, session: Session, work: Workstate, trace: _Trace
) -> Refusal | tuple[Session, Workstate]:
    state = session.state
    if skills_consultable(state):
        reply = loop.skill_plan(work)
        if reply is not None:
            trace.consultations.append(Consultation(Subsystem.SKILLS, state))
            return _route_cognitive(loop, session, work, trace, reply)
    gate = provider_consultation_allowed(state, view_is_fresh=work.view_is_fresh)
    if gate is not None:
        if "fresh Context Building" in gate.reason:
            work = replace(work, route=state)
            return _continue(session, State.INSPECTING, work, trace)
        return Refusal(gate.reason)
    trace.consultations.append(Consultation(Subsystem.PROVIDER, state))
    reply = loop.provider_reply(work)
    session, work = _write_event(loop, session, work, ProviderResponse(), trace)
    if isinstance(session, Refusal):
        return session
    if reply.degraded:
        trace.disclosures.append(
            "provider unavailable with no fallback: degraded mode — facts-only, "
            "no recommendations (I-9; DN-91)"
        )
        return _write_event(loop, session, work, ProviderFallbackFailed(), trace)
    return _route_cognitive(loop, session, work, trace, reply)


def _present_phase(
    loop: Loop, session: Session, work: Workstate, trace: _Trace
) -> Refusal | tuple[Session, Workstate]:
    for _ in work.plan:
        session, work = _write_event(loop, session, work, ActionClassified(), trace)
        if isinstance(session, Refusal):
            return session
    for _ in work.blocked:
        session, work = _write_event(loop, session, work, ActionBlocked(), trace)
        if isinstance(session, Refusal):
            return session
    return session, replace(work, presented=True)


def _execute_phase(
    loop: Loop, session: Session, work: Workstate, trace: _Trace
) -> Refusal | tuple[Session, Workstate]:
    if work.token is None:
        return Refusal("no approval token; execution cannot start (I-1; RFC-0008 §8)")
    gate = may_consult(session.state, Subsystem.EXECUTOR)
    if gate is not None:
        return Refusal(gate.reason)
    trace.consultations.append(Consultation(Subsystem.EXECUTOR, session.state))
    session, work = _write_event(loop, session, work, ActionStarted(), trace)
    if isinstance(session, Refusal):
        return session
    result = loop.run_executor(work.token, work)
    if result.kind is RunKind.SUCCEEDED:
        event = ActionSucceeded()
    elif result.kind is RunKind.FAILED:
        event = ActionFailed()
    elif result.kind is RunKind.TIMEOUT:
        event = ActionTimeout()
    elif result.kind is RunKind.INTERRUPTED:
        event = ActionInterrupted()
    elif result.kind is RunKind.PARTIAL:
        event = ActionPartial(PartialHalt.INTERRUPTED)
    else:
        event = RebootRequested()
    session, work = _write_event(loop, session, work, event, trace)
    if isinstance(session, Refusal):
        return session
    if result.kind in (RunKind.SUCCEEDED, RunKind.FAILED):
        return session, work
    trace.disclosures.append(
        f"execution halted: {result.kind.name.lower()} — state uncertain; "
        "re-assessment is required before anything else (I-8)"
    )
    return session, replace(work, token=None, tokens=())


def _verify_phase(
    loop: Loop, session: Session, work: Workstate, trace: _Trace
) -> Refusal | tuple[Session, Workstate]:
    gate = may_consult(session.state, Subsystem.DIAGNOSTICS)
    if gate is not None:
        return Refusal(gate.reason)
    trace.consultations.append(Consultation(Subsystem.DIAGNOSTICS, session.state))
    result = loop.verify(work)
    if result.kind is VerifyKind.PASSED:
        event = VerificationPassed(steps_remaining=result.steps_remaining)
    elif result.kind is VerifyKind.FAILED:
        event = VerificationFailed()
    else:
        event = VerificationInconclusive()
    session, work = _write_event(loop, session, work, event, trace)
    if isinstance(session, Refusal):
        return session
    if result.kind is VerifyKind.PASSED and result.steps_remaining:
        return session, work
    return session, replace(work, token=None, tokens=())


def _approve(
    loop: Loop,
    session: Session,
    work: Workstate,
    event: RuntimeEvent,
    trace: _Trace,
) -> Refusal | tuple[Session, Workstate]:
    if session.state is not State.AWAITING_APPROVAL or not work.tokens:
        return Refusal(
            f"{event.kind.name} is not applicable: no presented, classified plan "
            "awaits a decision (RFC-0002 §2.7)"
        )
    token = work.tokens[0]
    if not loop.revalidate(token, work):
        trace.disclosures.append(
            "the approval token is no longer valid (state or policy changed); "
            "the approval is invalidated and the plan re-opens (I-11; P8; DN-89)"
        )
        work = replace(work, token=None, tokens=())
        return _continue(session, State.INSPECTING, work, trace)
    step = session.apply(event)
    if isinstance(step, Refusal):
        return Refusal(step.reason)
    blocked = _write(loop, step.record, trace)
    if blocked is not None:
        return blocked
    return step.session, replace(work, token=work.tokens, presented=False)


def _run_phase(
    loop: Loop, session: Session, work: Workstate, trace: _Trace
) -> Refusal | tuple[Session, Workstate]:
    state = session.state
    if state is State.INSPECTING:
        return _inspect_phase(loop, session, work, trace)
    if state is State.BUILDING:
        return _build_phase(loop, session, work, trace)
    if state in (State.DIAGNOSING, State.PLANNING, State.REPLANNING):
        return _cognitive_phase(loop, session, work, trace)
    if state is State.EXECUTING:
        return _execute_phase(loop, session, work, trace)
    if state is State.VERIFYING:
        return _verify_phase(loop, session, work, trace)
    return session, work


def _apply_event(
    loop: Loop,
    session: Session,
    work: Workstate,
    event: RuntimeEvent,
    goal: str | None,
    trace: _Trace,
) -> Refusal | tuple[Session, Workstate]:
    if event.kind is EventKind.OP_GOAL:
        if goal is None:
            return Refusal("OP_GOAL requires the goal statement")
        step = session.adopt_goal(goal)
    elif event.kind is EventKind.OP_EXIT:
        step = session.stop()
    elif event.kind in (EventKind.OP_APPROVE, EventKind.OP_OVERRIDE):
        return _approve(loop, session, work, event, trace)
    elif event.kind is EventKind.OP_REPLY:
        step = session.apply(OpReply(routes_to=work.route))
    else:
        step = session.apply(event)
    if isinstance(step, Refusal):
        return Refusal(step.reason)
    blocked = _write(loop, step.record, trace)
    if blocked is not None:
        return blocked
    new_session, new_work = step.session, work
    if new_session.state in _BOUNDARY_CLEAR:
        new_work = replace(new_work, token=None, tokens=())
    if new_session.state is State.REPLANNING:
        new_work = replace(new_work, view_is_fresh=False)
    if event.kind in (EventKind.OP_REPLY, EventKind.OP_REJECT, EventKind.OP_REFINE):
        new_work = replace(new_work, view_is_fresh=False)
    if event.kind is EventKind.OP_GOAL:
        new_work = replace(
            new_work, route=State.DIAGNOSING, view_is_fresh=False, presented=False
        )
    return new_session, new_work


def advance(
    loop: Loop,
    session: Session,
    work: Workstate | None = None,
    *,
    event: RuntimeEvent | None = None,
    goal: str | None = None,
) -> LoopStep | Refusal:
    """Run one step of the conductor.

    With ``event``, applies the operator/§4 event through the session with its
    record written before the consequence (I-13; AU8). Without, runs the
    current state's autonomous phase work. Returns the next ``LoopStep`` or a
    ``Refusal`` (a failed audit write, a forbidden consultation, or an
    inapplicable event all fail loud).
    """
    work = work or Workstate()
    trace = _Trace()
    if event is None:
        outcome = _run_phase(loop, session, work, trace)
    else:
        outcome = _apply_event(loop, session, work, event, goal, trace)
    if isinstance(outcome, Refusal):
        return outcome
    next_session, work = outcome
    return LoopStep(
        next_session,
        work,
        tuple(trace.writes),
        tuple(trace.consultations),
        tuple(trace.disclosures),
    )


def pump(
    loop: Loop, session: Session, work: Workstate | None = None
) -> LoopStep | Refusal:
    """Advance the autonomous 10-step loop until a pause point.

    Runs Machine Inspection, Context Building, Diagnosis, Planning,
    classification/gating (presentation records), Execution, Verification,
    and Replanning until Idle, Awaiting Approval, Awaiting Input, Interrupted,
    an outcome, or END, where the Operator acts. Deterministic and I/O-free
    (DN-94).
    """
    work = work or Workstate()
    trace = _Trace()
    current, work = session, work
    while True:
        if current.state in _PAUSE:
            if current.state is State.AWAITING_APPROVAL and not work.presented:
                outcome = _present_phase(loop, current, work, trace)
                if isinstance(outcome, Refusal):
                    return outcome
                current, work = outcome
                continue
            return LoopStep(
                current,
                work,
                tuple(trace.writes),
                tuple(trace.consultations),
                tuple(trace.disclosures),
            )
        outcome = _run_phase(loop, current, work, trace)
        if isinstance(outcome, Refusal):
            return outcome
        current, work = outcome
