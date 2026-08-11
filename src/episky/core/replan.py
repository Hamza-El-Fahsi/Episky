"""Replanning rules.

Owner: RFC-0002 §2.10, §4.7, §7, §10; RFC-0008 §11, §15; RFC-0006 §7.
Responsibility: deciding when a plan re-opens (the replan triggers),
    the provenance-reuse rules for carrying Facts into a revised plan
    (RFC-0005 §12 F14/F15), targeted revision versus rebuild
    (RFC-0002 §4.7), and that a revised plan is re-normalized,
    re-classified, and re-presented with no carried approval (I-6;
    RFC-0008 §8, §15).
Forbidden responsibility: no state-machine transitions of its own —
    this module only *decides*; the conductor routes through
    `state_machine.evolve` / `session.apply` exactly as already
    defined (a revised plan re-enters at Planning/Replanning,
    RFC-0002 §4.7, never mid-execution). No clock, no I/O, no
    randomness, no persistence, and no policy values: numeric budgets
    are RFC-0020's, and the freshness bound values of RFC-0005 §12 are
    referenced, not owned (DN-14). Contradiction is decided by the
    Fact Layer; this module only reads the resulting Fact status
    (RFC-0006 §7).
"""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum, auto

from episky.core.events import EventKind
from episky.core.state_machine import State
from episky.factlayer.provenance import DEFAULT_FRESHNESS_BOUND, freshness_state
from episky.schema.fact import Fact, FactStatus, FreshnessState

__all__ = [
    "FactReuse",
    "ReentrySequence",
    "ReentryStage",
    "ReplanDecision",
    "ReplanTrigger",
    "RevisionScope",
    "approval_carries",
    "reentry_sequence",
    "reopen",
    "reuse_fact",
    "revise_scope",
    "trigger_from_event",
]

#: The Fact statuses that may be carried into a revised plan (RFC-0005 §4).
#: UNKNOWN/UNAVAILABLE/UNSUPPORTED assert nothing usable as evidence;
#: CONTRADICTED is invalidated and fresh evidence wins (RFC-0006 §7);
#: STALE is never Current (F11/F14); INVALID is a failed Fact. Only an
#: OBSERVED or VERIFIED claim is reusable.
_REUSEABLE_STATUSES = frozenset({FactStatus.OBSERVED, FactStatus.VERIFIED})

#: The §2.10/§11 events that open a replan (RFC-0008 §11: failed step →
#: Replanning; RFC-0002 §2.10). The ActionFailed event names the step that
#: failed; the replan itself is entered from Verification (RFC-0006 §7):
#: the conductor first routes the failed step through Verify, and only
#: Verification's honest outcome re-opens the plan (V5).
#: States a ReplanDecision may name as its next cognitive phase. This is
#: exactly the §2.13 successor set of REPLANNING, so every decision this
#: module can produce is provably reachable by the state machine (single
#: state-machine rule; DN-86). Transcribed from SECTION2_ALLOWED.
_REPLAN_SUCCESSORS: frozenset[State] = frozenset(
    {
        State.PLANNING,
        State.DIAGNOSING,
        State.INSPECTING,
        State.AWAITING_INPUT,
        State.FAILED,
    }
)


class ReplanTrigger(Enum):
    """Why a plan re-opens (RFC-0002 §2.10; RFC-0008 §11)."""

    VERIFICATION_FAILED = auto()
    VERIFICATION_INCONCLUSIVE = auto()
    ACTION_FAILED = auto()
    PLAN_REJECTED = auto()
    PLAN_REFINED = auto()
    PRECONDITIONS_CHANGED = auto()
    BLOCKED_NOT_OVERRIDDEN = auto()


#: The §2.10/§11 events that open a replan (RFC-0008 §11: failed step →
#: Replanning; RFC-0002 §2.10). The ActionFailed event names the step that
#: failed; the replan itself is entered from Verification (RFC-0006 §7):
#: the conductor first routes the failed step through Verify, and only
#: Verification's honest outcome re-opens the plan (V5).
_TRIGGER_EVENTS: dict[EventKind, ReplanTrigger] = {
    EventKind.VERIFICATION_FAILED: ReplanTrigger.VERIFICATION_FAILED,
    EventKind.VERIFICATION_INCONCLUSIVE: ReplanTrigger.VERIFICATION_INCONCLUSIVE,
    EventKind.ACTION_FAILED: ReplanTrigger.ACTION_FAILED,
    EventKind.PLAN_REJECTED: ReplanTrigger.PLAN_REJECTED,
    EventKind.PLAN_REFINED: ReplanTrigger.PLAN_REFINED,
    EventKind.STATE_CHANGED_DETECTED: ReplanTrigger.PRECONDITIONS_CHANGED,
    EventKind.ACTION_BLOCKED: ReplanTrigger.BLOCKED_NOT_OVERRIDDEN,
}


class RevisionScope(Enum):
    """How much of a plan a revision touches (RFC-0002 §4.7).

    TARGETED revises only the invalidated part and re-enters Planning;
    REBUILD discards the plan's basis (hypothesis undermined or the
    machine changed beneath it) and re-establishes state first, from
    Diagnosis (RFC-0002 §2.10; failure-injection-walkthrough Scenario
    17). Replanning is never mid-execution resumption (RFC-0002 §4.7).
    """

    TARGETED = auto()
    REBUILD = auto()


class FactReuse(Enum):
    """Whether a Fact may be carried into the revised plan (F14, F15).

    REUSE means the Fact is still valid current evidence under the
    provenance-reuse rules; RECOLLECT means the revised plan must obtain
    it fresh before it counts (a re-collected Fact flows marked by its
    new provenance). Reuse is decided, never assumed (F10, F15).
    """

    REUSE = auto()
    RECOLLECT = auto()


class ReentryStage(Enum):
    """The pipeline stages a revised plan re-enters (RFC-0002 §4.7).

    A replanned plan is re-normalized (fresh Facts through the Fact
    Layer), re-classified (a fresh Risk classification), and re-presented
    (a fresh Operator decision); nothing from the previous presentation
    carries over (I-6, I-15; RFC-0008 §8, §15).
    """

    RE_NORMALIZE = auto()
    RE_CLASSIFY = auto()
    RE_PRESENT = auto()


#: The fixed re-entry order. A plan never skips a stage and never
#: re-enters mid-execution (RFC-0002 §4.7).
ReentrySequence = tuple[ReentryStage, ReentryStage, ReentryStage]


@dataclass(frozen=True, slots=True)
class ReplanDecision:
    """A deterministic replan decision (RFC-0002 §2.10, §4.7).

    This is a decision only: it names the trigger, the revision scope,
    the Facts that may be carried versus re-collected, and the cognitive
    phase the revision needs. It performs no transition; the conductor
    routes it through the state machine exactly as defined, and the
    named phase is always a §2.13 successor of REPLANNING.

    Attributes:
        trigger: Why the plan re-opened.
        scope: TARGETED or REBUILD.
        reuse: Facts whose provenance is still valid, carried as-is.
        recollect: Facts the revised plan must obtain fresh.
        next_phase: The cognitive phase the revision needs (always a
            successor of REPLANNING).
        approval_cleared: Always True — a changed plan carries no
            approval (I-6); the previous token is consumed (I-11).
    """

    trigger: ReplanTrigger
    scope: RevisionScope
    reuse: tuple[Fact, ...]
    recollect: tuple[Fact, ...]
    next_phase: State
    approval_cleared: bool = True


def _event_trigger(kind: EventKind) -> ReplanTrigger | None:
    """Map an event to the replan trigger it opens, or None (pure).

    The events whose arrival the state machine routes into REPLANNING
    (or, for a detected state change, back through Inspection into a
    re-plan) are the replan triggers; everything else is not a replan
    reason. The mapping is declared once, so "when to replan" is a
    single transcription of RFC-0002 §2.10 and RFC-0008 §11.
    """
    return _TRIGGER_EVENTS.get(kind)


def trigger_from_event(kind: EventKind) -> ReplanTrigger | None:
    """Decide whether ``kind`` opens a replan, and why.

    RFC-0002 §2.10: a plan re-opens when Verification fails or is
    inconclusive, an executed step fails, the Operator rejects or refines
    the presented plan, the machine changes beneath the plan's
    preconditions, or a plan is blocked without an override. Any other
    event is not a replan reason and yields ``None``.

    Args:
        kind: The event that arrived.

    Returns:
        The ReplanTrigger, or None when the event does not open a replan.
    """
    return _event_trigger(kind)


def revise_scope(
    trigger: ReplanTrigger,
    *,
    hypothesis_undermined: bool = False,
    preconditions_changed: bool = False,
) -> RevisionScope:
    """Decide whether the revision is TARGETED or a REBUILD (RFC-0002 §4.7).

    The plan's basis is the hypothesis it acts on and the machine state
    its preconditions assert. When the hypothesis itself is contradicted
    by fresh Facts (RFC-0006 §7 Contradicted) or the machine changed
    beneath the plan (RFC-0002 §2.1), the plan is rebuilt from
    re-established state; otherwise only the invalidated part is
    revised and the plan re-enters Planning.

    Args:
        trigger: The replan trigger.
        hypothesis_undermined: The Goal claim was contradicted by fresh
            Facts, not merely an unexecuted step.
        preconditions_changed: A detected state change invalidated the
            plan's preconditions.

    Returns:
        REBUILD when the plan's basis is gone, else TARGETED.
    """
    if hypothesis_undermined or preconditions_changed:
        return RevisionScope.REBUILD
    return RevisionScope.TARGETED


def reuse_fact(
    fact: Fact,
    *,
    now: datetime,
    bound: timedelta | None = DEFAULT_FRESHNESS_BOUND,
) -> FactReuse:
    """Apply the provenance-reuse rule to one Fact (RFC-0005 §12; F14, F15).

    A Fact is carried into a revised plan only when its provenance is
    still valid evidence: its status is OBSERVED or VERIFIED (never
    Unknown, Stale, Contradicted, or Invalid — RFC-0005 §4), its carried
    freshness state is Current, and its freshness is Current when
    re-evaluated now (RFC-0005 §12). The carried state and the re-check
    are both required: the Fact Layer's own verdict is honored, and a
    Fact that was Current when collected is re-checked at the replan, so
    a Fact that has since aged past its bound is re-collected (F14).
    ``now`` is supplied by the caller — there is no clock here (RFC-0005
    §12). The freshness bound is RFC-0020 policy (DN-14);
    ``DEFAULT_FRESHNESS_BOUND`` is the referenced placeholder. A
    contradicted claim arrives with status CONTRADICTED, which this rule
    never reuses: fresh evidence wins (RFC-0006 §7). Reuse is re-decided
    at every replan; it is never carried automatically (F15).

    Args:
        fact: The Fact under consideration.
        now: The time at which freshness is evaluated (caller-supplied).
        bound: The freshness bound, or None when it cannot be computed.

    Returns:
        REUSE when the Fact's provenance is still valid current
        evidence, else RECOLLECT.
    """
    if fact.status not in _REUSEABLE_STATUSES:
        return FactReuse.RECOLLECT
    if fact.freshness.state is not FreshnessState.CURRENT:
        return FactReuse.RECOLLECT
    if (
        freshness_state(fact.provenance.collected_at, now, bound)
        is not FreshnessState.CURRENT
    ):
        return FactReuse.RECOLLECT
    return FactReuse.REUSE


def approval_carries(revision: ReplanDecision | RevisionScope | None = None) -> bool:
    """Whether a revised plan may carry the previous approval.

    Always False: a changed plan is re-normalized, re-classified, and
    re-presented, and the prior token is consumed or invalidated on the
    change (I-6, I-11; RFC-0008 §8, §15). Even a targeted revision with
    an identical step re-presents for a fresh decision; nothing resumes
    without a fresh approval (I-15).

    Args:
        revision: Accepted for a stable call signature; the answer does
            not depend on it.

    Returns:
        False, always.
    """
    return False


def reentry_sequence() -> ReentrySequence:
    """The pipeline re-entry order of a revised plan (RFC-0002 §4.7).

    A revised plan is re-normalized, then re-classified, then
    re-presented. No stage is skipped, and the plan re-enters at
    Planning/Replanning — never mid-execution (RFC-0002 §4.7).

    Returns:
        The ordered re-entry stages.
    """
    return (
        ReentryStage.RE_NORMALIZE,
        ReentryStage.RE_CLASSIFY,
        ReentryStage.RE_PRESENT,
    )


def _next_phase(
    trigger: ReplanTrigger,
    scope: RevisionScope,
) -> State:
    """Name the cognitive phase a revision needs (RFC-0002 §2.10, §4.7).

    A rebuild re-establishes state from Diagnosis; a rejected or
    non-overridable blocked plan requires the Operator's direction
    (Awaiting Input, RFC-0002 §2.8); everything else re-enters
    Planning for a targeted revision. The result is always a §2.13
    successor of REPLANNING.
    """
    if scope is RevisionScope.REBUILD:
        return State.DIAGNOSING
    if trigger in (ReplanTrigger.PLAN_REJECTED, ReplanTrigger.BLOCKED_NOT_OVERRIDDEN):
        return State.AWAITING_INPUT
    return State.PLANNING


def reopen(
    trigger: ReplanTrigger,
    facts: tuple[Fact, ...],
    *,
    now: datetime,
    hypothesis_undermined: bool = False,
    preconditions_changed: bool = False,
    bound: timedelta | None = DEFAULT_FRESHNESS_BOUND,
) -> ReplanDecision:
    """Compute the deterministic replan decision (RFC-0002 §2.10, §4.7).

    Given the trigger and the Facts currently held, this decides the
    revision scope, which Facts may be carried versus re-collected under
    the provenance-reuse rules, the next cognitive phase, and that no
    approval carries. It performs no transition and mutates nothing.

    Args:
        trigger: Why the plan re-opened.
        facts: The Facts currently held, in any order (reuse is a
            per-Fact decision; order does not change it).
        now: The time at which freshness is evaluated (caller-supplied).
        hypothesis_undermined: The Goal claim was contradicted by fresh
            Facts (RFC-0006 §7).
        preconditions_changed: A detected state change invalidated the
            plan's preconditions (RFC-0002 §2.1).
        bound: The freshness bound (RFC-0005 §12; RFC-0020 policy).

    Returns:
        The ReplanDecision: scope, reusable/re-collect Facts, the next
        cognitive phase, and approval_cleared=True.
    """
    scope = revise_scope(
        trigger,
        hypothesis_undermined=hypothesis_undermined,
        preconditions_changed=preconditions_changed,
    )
    reuse = tuple(
        fact
        for fact in facts
        if reuse_fact(fact, now=now, bound=bound) is FactReuse.REUSE
    )
    recollected = tuple(fact for fact in facts if fact not in reuse)
    return ReplanDecision(
        trigger=trigger,
        scope=scope,
        reuse=reuse,
        recollect=recollected,
        next_phase=_next_phase(trigger, scope),
        approval_cleared=True,
    )


#: Every phase `_next_phase` can produce must be reachable (§2.13). This
#: invariant is asserted so a future edit cannot emit an unreachable
#: decision; the module never performs the transition itself (DN-86).
assert all(
    _next_phase(t, s) in _REPLAN_SUCCESSORS
    for t in ReplanTrigger
    for s in RevisionScope
)
