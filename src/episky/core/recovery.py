"""Recovery rules.

Owner: RFC-0002 §8, §10; RFC-0008 §11, §15; RFC-0013 §21; RFC-0006 §6.
Responsibility: the deterministic recovery order — determinism,
    disclosure, decision, action (RFC-0002 §8; DN-90) — and the
    decisions for provider failure (the bounded pure reducer, Q6 /
    DN-90), action failure, collector failure, policy failure, partial
    execution, and interruption.
Forbidden responsibility: no state-machine transitions of its own —
    this module only *decides*; the conductor routes through
    `state_machine.evolve` / `session.apply` exactly as already defined.
    No clock (backoff is data, scheduled by the caller), no I/O, no
    randomness, no persistence, and no policy values: retry budgets,
    backoff schedules, and fallback chains are supplied as data and are
    RFC-0020 content (DN-1, DN-14). No automatic rollback: a rollback is
    itself an approved action (I-8, I-15), and the runtime never
    fabricates what it cannot establish (I-9).
"""

from __future__ import annotations

from dataclasses import dataclass, replace
from datetime import timedelta
from enum import Enum, auto

__all__ = [
    "ActionFailureDecision",
    "ActionFailureKind",
    "ActionRecovery",
    "CollectorFailureDecision",
    "CollectorFailureKind",
    "CollectorRecovery",
    "InterruptDecision",
    "InterruptRecovery",
    "PartialDecision",
    "PartialRecovery",
    "PolicyFailureDecision",
    "PolicyFailureKind",
    "PolicyRecovery",
    "ProviderFailureKind",
    "ProviderReaction",
    "ProviderRecovery",
    "ProviderRecoveryState",
    "RecoveryOrder",
    "RecoveryStep",
    "backoff_delay",
    "decide_provider_reaction",
    "on_action_failure",
    "on_collector_failure",
    "on_interrupt",
    "on_partial",
    "on_policy_failure",
    "on_provider_failure",
    "recover",
    "recovery_order",
    "reduce_provider_failure",
]


class RecoveryStep(Enum):
    """The recovery order's fixed stages (RFC-0002 §8; DN-90).

    Determinism first: recovery is decided by rules, never by
    improvisation; disclosure before decision so the Operator always
    learns what happened before anything changes; decision before
    action so a consequence is never the first step. The order is
    fixed and is a single transcription of RFC-0002 §8.
    """

    DETERMINISM = auto()
    DISCLOSURE = auto()
    DECISION = auto()
    ACTION = auto()


#: The fixed recovery order. The exact four steps in this exact order.
RecoveryOrder = tuple[RecoveryStep, RecoveryStep, RecoveryStep, RecoveryStep]


class ProviderFailureKind(Enum):
    """A provider interaction's failure (RFC-0002 §10; §4.3).

    REFUSAL is a provider refusing to reason over the Goal (the
    Operator may re-request; retrying is not automatic); UNAVAILABLE
    and TIMEOUT are transient provider loss that a bounded retry may
    absorb (RFC-0002 §4.3 PROVIDER_TIMEOUT).
    """

    REFUSAL = auto()
    UNAVAILABLE = auto()
    TIMEOUT = auto()


class ProviderReaction(Enum):
    """The next provider attempt (RFC-0002 §10, §4.3).

    RETRY re-asks after a bounded, data-scheduled delay; FALLBACK
    moves to the next configured fallback; DEGRADE is the terminal
    provider posture — facts-only, no recommendations, never silent
    (DN-91; RFC-0002 §4.3).
    """

    RETRY = auto()
    FALLBACK = auto()
    DEGRADE = auto()


class ActionFailureKind(Enum):
    """An executed action's failure (RFC-0002 §4.5; RFC-0008 §11).

    STEP_FAILED is a recorded, non-ambiguous failure of the step;
    STEP_TIMEOUT and STEP_PARTIAL are ambiguous halts whose actual
    effect on the machine is unknown.
    """

    STEP_FAILED = auto()
    STEP_TIMEOUT = auto()
    STEP_PARTIAL = auto()


class ActionRecovery(Enum):
    """What an action failure means for the machine (RFC-0008 §11).

    VERIFY_THEN_REPLAN: the failed step goes through Verification, and
    its honest outcome re-opens the plan (V5; RFC-0008 §11: failed
    step → Replanning). HALT_INTERRUPTED: an ambiguous halt or an
    unhealthy executor — no further actions run until actual state is
    re-established (I-8); an interrupt is not an authorization (I-15).
    """

    VERIFY_THEN_REPLAN = auto()
    HALT_INTERRUPTED = auto()


class CollectorFailureKind(Enum):
    """A Collector's failure to produce evidence (RFC-0005; RFC-0002 §4.2).

    NON_CRITICAL facts can be carried as Unknown-with-provenance;
    CRITICAL baseline facts cannot be established at all; HOPELESS
    means continuing the Goal is pointless.
    """

    NON_CRITICAL = auto()
    CRITICAL = auto()
    HOPELESS = auto()


class CollectorRecovery(Enum):
    """The recovery decision for a failed Collector (RFC-0002 §4.2).

    FACT_UNKNOWN carries "fact unknown" with its provenance — recorded,
    never silent, never claimed as evidence (RFC-0006 §6; I-9).
    DISCLOSE_AND_ASK presents the disclosure and awaits Operator
    direction. FAIL ends the plan when the Goal cannot be pursued.
    """

    FACT_UNKNOWN = auto()
    DISCLOSE_AND_ASK = auto()
    FAIL = auto()


class PolicyFailureKind(Enum):
    """A policy/approval failure (RFC-0008 §8, §10, §15; RFC-0013 §21).

    TOKEN_INVALID: the approval token was consumed, invalidated, or
    expired; PLAN_BLOCKED: the presented plan is blocked and no
    override was given; EXECUTION_UNRECORDED: a consequence could not
    be audited (the failed audit write blocks its consequence).
    """

    TOKEN_INVALID = auto()
    PLAN_BLOCKED = auto()
    EXECUTION_UNRECORDED = auto()


class PolicyRecovery(Enum):
    """The recovery decision for a policy failure (RFC-0008; RFC-0013 §21).

    RE_OPEN_AND_RE_PRESENT: the invalid token is cleared and the plan
    is re-presented for a fresh decision (RFC-0008 §8, §15) — reuse of
    a token is never offered. DISCLOSE_AND_ASK: disclose the block and
    await the Operator's explicit choice (override or abandon).
    REFUSE: fail closed — never proceed without a recorded approval
    (I-1; RFC-0013 §21).
    """

    RE_OPEN_AND_RE_PRESENT = auto()
    DISCLOSE_AND_ASK = auto()
    REFUSE = auto()


class PartialRecovery(Enum):
    """What a partial execution means (RFC-0002 §10; I-8, I-9).

    RE_ESTABLISH_THEN_PRESENT: actual machine state is re-established,
    exactly what ran is recorded, and the Operator decides — nothing
    resumes and nothing rolls back automatically (a rollback is itself
    an approved action, I-15).
    """

    RE_ESTABLISH_THEN_PRESENT = auto()


class InterruptRecovery(Enum):
    """The interrupt protocol's decision (RFC-0002 §10; I-15).

    RE_ASSESS: a machine-touching halt — the machine halts, actual
    state is re-established, and nothing resumes without fresh
    approval. CANCEL_CALL: a cognitive (Context Building) call is
    cancelled and the runtime awaits input, disclosing the pause.
    END: the second press ends the session.
    """

    RE_ASSESS = auto()
    CANCEL_CALL = auto()
    END = auto()


# --- Provider failure: the bounded pure reducer (Q6; DN-90) --------------


@dataclass(frozen=True, slots=True)
class ProviderRecoveryState:
    """Bounded, immutable reducer state for provider recovery (Q6; DN-90).

    Every bound is data supplied by the caller (RFC-0020 content): the
    per-provider retry budget, the backoff schedule, the fallback chain,
    and whether facts-only degradation is permitted. The counters move
    only forward and never past their bounds, so the reducer is bounded
    by construction and deterministic: the same events produce the same
    state. There is no clock — ``backoff_delay`` returns the scheduled
    delay as data and the caller decides when to schedule it.

    Attributes:
        retry_budget: The maximum retries per provider (>= 0).
        backoff: The scheduled retry delays, in order (data, not a
            clock).
        fallback_chain: Named fallbacks, in order (RFC-0002 §10).
        degraded_allowed: Whether facts-only degradation is permitted.
        current_index: The provider position; 0 is the primary provider
            and i (>= 1) is ``fallback_chain[i - 1]``. Never exceeds
            ``len(fallback_chain)``.
        retries_used: Retries committed on the current provider
            (<= retry_budget).
        moved: The most recent failure advanced the provider, so the
            next reaction is to attempt the new provider (FALLBACK),
            never to retry.
        retrying: The most recent failure was absorbed by the retry
            budget, so the next reaction is a retry (RETRY) of the
            current provider.
        degraded: Facts-only mode reached (terminal for the reducer).
        halted: No provider attempt remains and degradation is not
            permitted (terminal for the reducer).
    """

    retry_budget: int
    backoff: tuple[timedelta, ...]
    fallback_chain: tuple[str, ...]
    degraded_allowed: bool
    current_index: int = 0
    retries_used: int = 0
    moved: bool = False
    retrying: bool = False
    degraded: bool = False
    halted: bool = False

    @property
    def terminal(self) -> bool:
        """Whether no further reduction changes the state (Q6)."""
        return self.degraded or self.halted


def _advance_provider(
    state: ProviderRecoveryState,
) -> ProviderRecoveryState:
    """Move to the next fallback, else degrade or halt (RFC-0002 §10)."""
    if state.current_index < len(state.fallback_chain):
        return replace(
            state,
            current_index=state.current_index + 1,
            retries_used=0,
            moved=True,
            retrying=False,
        )
    if state.degraded_allowed:
        return replace(state, degraded=True)
    return replace(state, halted=True)


def reduce_provider_failure(
    state: ProviderRecoveryState,
    kind: ProviderFailureKind,
) -> ProviderRecoveryState:
    """Reduce one provider failure into the bounded state (pure; Q6).

    A monotonic, bounded fold. REFUSAL is never auto-retried — the
    Operator may re-request, the runtime moves to the next provider
    (failure-injection-walkthrough Scenario 4); UNAVAILABLE and TIMEOUT
    are absorbed by a retry while the budget lasts, then the next
    provider, then facts-only degradation (RFC-0002 §10, §4.3). The
    most recent failure's disposition is recorded (``retrying`` vs
    ``moved``), so the reaction derived from the state always matches
    the last event: a failure that just committed a retry is answered by
    that retry, a failure that just advanced the provider is answered by
    an attempt of the new provider. A terminal state is left unchanged.
    Nothing here consults a clock and nothing exceeds the caller-supplied
    bounds.

    Args:
        state: The current recovery state.
        kind: The provider failure that just occurred.

    Returns:
        The advanced state.
    """
    if state.terminal:
        return state
    if kind is ProviderFailureKind.REFUSAL:
        return _advance_provider(state)
    if state.retries_used < state.retry_budget:
        return replace(
            state,
            retries_used=state.retries_used + 1,
            moved=False,
            retrying=True,
        )
    return _advance_provider(state)


def decide_provider_reaction(
    state: ProviderRecoveryState,
) -> ProviderReaction:
    """Decide the next provider reaction from the state (pure).

    Terminal states yield DEGRADE (facts-only; the halted case means the
    runtime discloses and stops, never degrades silently); a retry just
    committed yields RETRY; a provider advance just taken yields FALLBACK
    (attempt the new provider); otherwise RETRY is the defensive default
    for the untouched initial state. Deterministic — the same state
    always decides the same reaction.

    Args:
        state: The recovery state.

    Returns:
        The reaction the caller should take next.
    """
    if state.terminal:
        return ProviderReaction.DEGRADE
    if state.retrying:
        return ProviderReaction.RETRY
    if state.moved:
        return ProviderReaction.FALLBACK
    return ProviderReaction.RETRY


def backoff_delay(
    state: ProviderRecoveryState,
) -> timedelta | None:
    """The scheduled retry delay as data (RFC-0002 §4.3; no clock).

    The delay is the committed retry's slot in the caller-supplied
    backoff schedule; when the schedule is exhausted the last scheduled
    value is reused as a stable bound. It is data, never a clock: the
    caller decides when to schedule it. None when no retry is pending
    (the initial state, a FALLBACK, or a terminal state).

    Args:
        state: The recovery state.

    Returns:
        The scheduled delay, or None when no retry is pending.
    """
    if state.terminal or not state.retrying:
        return None
    slot = state.retries_used - 1
    if state.backoff:
        return state.backoff[min(slot, len(state.backoff) - 1)]
    return None


@dataclass(frozen=True, slots=True)
class ProviderRecovery:
    """A provider-failure recovery decision and its disclosures (Q6).

    Attributes:
        state: The bounded reducer state after the injected events.
        reaction: The reaction the caller takes next.
        delay: The scheduled retry delay, or None when not retrying.
        fallback: The fallback to attempt, or None when not falling back.
        disclosures: The deterministic disclosure lines (RFC-0002 §8,
            disclosure before decision).
    """

    state: ProviderRecoveryState
    reaction: ProviderReaction
    delay: timedelta | None
    fallback: str | None
    disclosures: tuple[str, ...]


def on_provider_failure(
    events: tuple[ProviderFailureKind, ...],
    *,
    retry_budget: int,
    backoff: tuple[timedelta, ...],
    fallback_chain: tuple[str, ...],
    degraded_allowed: bool,
) -> ProviderRecovery:
    """Compute provider recovery from an injected failure sequence (Q6).

    The bounded pure reducer applied to the whole injected event
    sequence at once: the caller hands in the provider-failure events
    observed since the last good contact, and this returns the
    deterministic recovery decision together with its disclosures.
    Deterministic (same events → same decision) and bounded (counters
    never exceed the caller-supplied budgets).

    Args:
        events: The provider failures observed, in order.
        retry_budget: The maximum retries per provider.
        backoff: The scheduled retry delays.
        fallback_chain: Named fallbacks, in order.
        degraded_allowed: Whether facts-only degradation is permitted.

    Returns:
        The recovery decision and its disclosures.
    """
    state = ProviderRecoveryState(
        retry_budget=retry_budget,
        backoff=backoff,
        fallback_chain=fallback_chain,
        degraded_allowed=degraded_allowed,
    )
    for event in events:
        state = reduce_provider_failure(state, event)
    reaction = decide_provider_reaction(state)
    fallback = (
        state.fallback_chain[state.current_index - 1]
        if state.current_index > 0
        else (state.fallback_chain[0] if state.fallback_chain else None)
    )
    return ProviderRecovery(
        state=state,
        reaction=reaction,
        delay=backoff_delay(state),
        fallback=fallback if reaction is ProviderReaction.FALLBACK else None,
        disclosures=_provider_disclosures(state, reaction),
    )


def _provider_disclosures(
    state: ProviderRecoveryState,
    reaction: ProviderReaction,
) -> tuple[str, ...]:
    """The deterministic disclosure lines for a provider recovery (DN-90)."""
    lines: list[str] = []
    if reaction is ProviderReaction.DEGRADE:
        lines.append(
            "provider unavailable with no fallback: degraded mode — "
            "facts-only, no recommendations (I-9; DN-91)"
        )
        if state.halted:
            lines.append(
                "degraded mode is not permitted; provider attempts are "
                "exhausted (RFC-0002 §10)"
            )
    return tuple(lines)


# --- The recovery order ------------------------------------------------


def recovery_order() -> RecoveryOrder:
    """The fixed recovery order (RFC-0002 §8; DN-90).

    Determinism → disclosure → decision → action. Every recovery path
    in this module follows exactly this order; the order is fixed and
    is transcribed once.

    Returns:
        The four RecoveryStep values in order.
    """
    return (
        RecoveryStep.DETERMINISM,
        RecoveryStep.DISCLOSURE,
        RecoveryStep.DECISION,
        RecoveryStep.ACTION,
    )


# --- Action failure ------------------------------------------------------


@dataclass(frozen=True, slots=True)
class ActionFailureDecision:
    """Recovery decision for an action failure (RFC-0008 §11; I-8).

    Attributes:
        recovery: VERIFY_THEN_REPLAN or HALT_INTERRUPTED.
        disclosures: The deterministic disclosure lines.
    """

    recovery: ActionRecovery
    disclosures: tuple[str, ...]


def on_action_failure(
    kind: ActionFailureKind,
    *,
    executor_healthy: bool,
) -> ActionFailureDecision:
    """Decide what an action failure means (RFC-0008 §11; I-8).

    A recorded, unambiguous step failure with a healthy executor is
    routed through Verification, whose honest outcome re-opens the plan
    (RFC-0006 §7; V5; RFC-0008 §11: failed step → Replanning). An
    ambiguous halt (timeout, partial) or an unhealthy executor halts
    the machine: state is uncertain, no further action runs, and actual
    state must be re-established before anything else (I-8). An
    executor that is itself broken fails closed — safety-critical
    (RFC-0001 §7).

    Args:
        kind: How the action failed.
        executor_healthy: Whether the executor subsystem itself is
            still functioning.

    Returns:
        The recovery decision and its disclosures.
    """
    if kind is ActionFailureKind.STEP_FAILED and executor_healthy:
        return ActionFailureDecision(
            recovery=ActionRecovery.VERIFY_THEN_REPLAN,
            disclosures=(
                "the failed step goes through Verification; only its "
                "honest outcome re-opens the plan (RFC-0008 §11; V5)",
            ),
        )
    if not executor_healthy:
        return ActionFailureDecision(
            recovery=ActionRecovery.HALT_INTERRUPTED,
            disclosures=(
                "the executor itself failed: no further actions can run "
                "(fail closed; RFC-0001 §7)",
            ),
        )
    return ActionFailureDecision(
        recovery=ActionRecovery.HALT_INTERRUPTED,
        disclosures=(
            f"execution halted: {kind.name.lower()} — state uncertain; "
            "re-assessment is required before anything else (I-8)",
        ),
    )


# --- Collector failure ---------------------------------------------------


@dataclass(frozen=True, slots=True)
class CollectorFailureDecision:
    """Recovery decision for a failed Collector (RFC-0002 §4.2; RFC-0006 §6).

    Attributes:
        recovery: FACT_UNKNOWN, DISCLOSE_AND_ASK, or FAIL.
        disclosures: The deterministic disclosure lines.
    """

    recovery: CollectorRecovery
    disclosures: tuple[str, ...]


def on_collector_failure(
    kind: CollectorFailureKind,
) -> CollectorFailureDecision:
    """Decide what a Collector failure means (RFC-0002 §4.2; RFC-0006 §6).

    A non-critical missing Fact is carried as Unknown-with-provenance —
    recorded, never silent, never treated as evidence (RFC-0006 §6;
    I-9). A critical baseline failure cannot proceed on guesswork: the
    runtime discloses and awaits the Operator (RFC-0002 §4.2). A
    hopeless failure ends the plan rather than fabricate a path (I-9).

    Args:
        kind: How the collection failed.

    Returns:
        The recovery decision and its disclosures.
    """
    if kind is CollectorFailureKind.NON_CRITICAL:
        return CollectorFailureDecision(
            recovery=CollectorRecovery.FACT_UNKNOWN,
            disclosures=(
                "the missing fact is carried as Unknown with its "
                "provenance; it is never treated as evidence (RFC-0006 §6)",
            ),
        )
    if kind is CollectorFailureKind.CRITICAL:
        return CollectorFailureDecision(
            recovery=CollectorRecovery.DISCLOSE_AND_ASK,
            disclosures=(
                "a critical fact could not be collected; proceeding on "
                "guesswork is refused (RFC-0002 §4.2)",
            ),
        )
    return CollectorFailureDecision(
        recovery=CollectorRecovery.FAIL,
        disclosures=(
            "the Goal cannot be pursued: the failure is hopeless (RFC-0002 §4.2)",
        ),
    )


# --- Policy failure ------------------------------------------------------


@dataclass(frozen=True, slots=True)
class PolicyFailureDecision:
    """Recovery decision for a policy/approval failure (RFC-0008; RFC-0013 §21).

    Attributes:
        recovery: RE_OPEN_AND_RE_PRESENT, DISCLOSE_AND_ASK, or REFUSE.
        disclosures: The deterministic disclosure lines.
    """

    recovery: PolicyRecovery
    disclosures: tuple[str, ...]


def on_policy_failure(
    kind: PolicyFailureKind,
) -> PolicyFailureDecision:
    """Decide what a policy failure means (RFC-0008 §8, §10, §15; I-1).

    An invalid, consumed, or expired token is never reused: it is
    cleared and the plan re-opens for a fresh decision (RFC-0008 §8,
    §15; failure-injection-walkthrough Scenario 9). A blocked plan is
    disclosed and the Operator chooses (override explicitly or
    abandon) — an override is the Operator's explicit act, never
    automatic (RFC-0008 §10). An unrecorded consequence is refused:
    fail closed, the failed audit write blocks its consequence
    (RFC-0013 §21; AU8).

    Args:
        kind: How the policy/approval failed.

    Returns:
        The recovery decision and its disclosures.
    """
    if kind is PolicyFailureKind.TOKEN_INVALID:
        return PolicyFailureDecision(
            recovery=PolicyRecovery.RE_OPEN_AND_RE_PRESENT,
            disclosures=(
                "the approval token is no longer valid; it is never "
                "reused and the plan re-opens for a fresh decision "
                "(I-11; RFC-0008 §15)",
            ),
        )
    if kind is PolicyFailureKind.PLAN_BLOCKED:
        return PolicyFailureDecision(
            recovery=PolicyRecovery.DISCLOSE_AND_ASK,
            disclosures=(
                "the plan is blocked; an override is the Operator's "
                "explicit act, never automatic (RFC-0008 §10)",
            ),
        )
    return PolicyFailureDecision(
        recovery=PolicyRecovery.REFUSE,
        disclosures=(
            "no consequence proceeds without a recorded approval: fail "
            "closed (I-1; RFC-0013 §21)",
        ),
    )


# --- Partial execution ----------------------------------------------------


@dataclass(frozen=True, slots=True)
class PartialDecision:
    """Recovery decision for a partial execution (RFC-0002 §10; I-8, I-9).

    Attributes:
        recovery: RE_ESTABLISH_THEN_PRESENT.
        ran: The steps recorded as having run (I-9: exactly what ran).
        not_ran: The steps recorded as not run.
        disclosures: The deterministic disclosure lines.
    """

    recovery: PartialRecovery
    ran: tuple[str, ...]
    not_ran: tuple[str, ...]
    disclosures: tuple[str, ...]


def on_partial(
    ran: tuple[str, ...],
    not_ran: tuple[str, ...],
) -> PartialDecision:
    """Account for a partial execution honestly (RFC-0002 §10; I-8, I-9).

    Exactly what ran and what did not is recorded — nothing is invented
    to fill the gap (I-9) — and actual machine state is re-established
    before anything else (I-8). Nothing resumes and nothing rolls back
    automatically: a rollback is itself an approved action (I-15). The
    Operator then decides from the honest record.

    Args:
        ran: The steps that ran (named by the executor, in order).
        not_ran: The steps that did not run.

    Returns:
        The recovery decision and its disclosures.
    """
    return PartialDecision(
        recovery=PartialRecovery.RE_ESTABLISH_THEN_PRESENT,
        ran=ran,
        not_ran=not_ran,
        disclosures=(
            "partial execution: exactly the recorded steps ran; "
            "actual state must be re-established before anything else "
            "(I-8, I-9)",
            "no automatic rollback: a rollback is itself an approved action (I-15)",
        ),
    )


# --- Interruption ---------------------------------------------------------


@dataclass(frozen=True, slots=True)
class InterruptDecision:
    """Recovery decision for an interrupt (RFC-0002 §10; I-15).

    Attributes:
        recovery: RE_ASSESS, CANCEL_CALL, or END.
        disclosures: The deterministic disclosure lines.
    """

    recovery: InterruptRecovery
    disclosures: tuple[str, ...]


def on_interrupt(
    *,
    machine_touching: bool,
    second_press: bool = False,
) -> InterruptDecision:
    """Decide the interrupt protocol (RFC-0002 §10; I-15).

    The second press ends the session. A machine-touching halt is not
    an authorization: the machine halts, actual state is re-established,
    and nothing resumes without fresh approval (I-15). A cognitive
    (Context Building) call is cancelled and the runtime awaits input,
    disclosing the pause.

    Args:
        machine_touching: Whether the interrupted work touches the
            machine (execution/approval) rather than cognitive Context
            Building.
        second_press: Whether this is the second press of the
            interrupt protocol.

    Returns:
        The recovery decision and its disclosures.
    """
    if second_press:
        return InterruptDecision(
            recovery=InterruptRecovery.END,
            disclosures=("interrupt confirmed: the session ends",),
        )
    if machine_touching:
        return InterruptDecision(
            recovery=InterruptRecovery.RE_ASSESS,
            disclosures=(
                "the machine is halted; actual state must be "
                "re-established and nothing resumes without fresh "
                "approval (I-15)",
            ),
        )
    return InterruptDecision(
        recovery=InterruptRecovery.CANCEL_CALL,
        disclosures=("the Context Building call is cancelled (RFC-0002 §10)",),
    )


# --- The composed path -----------------------------------------------------


def recover(
    decision: ActionFailureDecision
    | CollectorFailureDecision
    | PolicyFailureDecision
    | PartialDecision
    | InterruptDecision
    | ProviderRecovery,
) -> RecoveryOrder:
    """Recover: apply the fixed order to any recovery decision (RFC-0002 §8).

    The recovery order is applied to a decision by *returning* the
    fixed order: determinism decided the decision, the decision's
    disclosures are disclosed, and the decision's recovery is acted on
    by the conductor. This keeps every recovery path in the fixed
    order with no path able to skip disclosure or act first.

    Args:
        decision: Any recovery decision this module produced.

    Returns:
        The recovery order applied to the decision (always the fixed
        four steps).
    """
    return recovery_order()
