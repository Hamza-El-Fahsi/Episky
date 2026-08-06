"""Deterministic Policy Token machinery (RFC-0008 §8, §9, §10; §13 P5–P10,
P13, P14; RFC-0002 invariant 11).

Owner: RFC-0008 §8 (Approval Tokens — creation, ownership, scope, lifetime
    and expiration, invalidation, single-use, standing approvals, elevation),
    §9 (Preconditions, checked by deterministic comparison), §10 (TOCTOU —
    the binding and the deterministic re-validation function), §13 (P5–P10,
    P13, P14), §16 (expiry windows); RFC-0001 §8.3; RFC-0004 §4.8 (the
    Approval Engine administers; "May never decide: whether to approve"),
    A6/A10; RFC-0002 invariants 11 and 13; ratified decision notes DN-49
    (explicit decision input), DN-50 (P13 as layer-boundary records), DN-53
    (elevation bounds on the token), DN-54 (plan envelope).
Responsibility: the Approval Token record and its deterministic lifecycle —
    the token's binding (Action identity, class, gate, the Facts it was
    approved against, the machine-state snapshot reference (Q4), elevation
    bounds (DN-53), the issuing session's identity, a per-class expiry, and
    the presented Step set of a plan envelope (DN-54)); ``mint`` on a prior
    classification plus an explicit decision input (DN-49); single-use
    consumption (P7); invalidation on boundary events and policy reload
    (P8, P14), never resurrected; ``validate``/``revalidate`` — the
    deterministic boundary re-validation (Action identity + Facts + state
    snapshot, P6/P9; Q4) that refuses on any uncertainty; and the in-memory
    issuance/override/auto-permit/rejection records (P13, DN-50).
Forbidden responsibility: never decides whether to approve (RFC-0004 §4.8
    C11), never executes an Action, never grants, revokes, or transfers
    authority (RFC-0004 A6/A8) — a token is never authority by itself;
    never mints on its own authority or on silence (DN-49; §13 P5); never
    reads a clock — time is an argument, never a side effect; never
    generates an identifier — no UUID, no randomness, no hashing, no crypto
    (session and snapshot references are caller-supplied and only carried);
    never writes a durable record, never contacts the runtime or the Audit
    (the durable write is ``audit``'s, DN-50); no I/O, no persistence, no
    caches, no plugins, no execution hooks, no global registry, no hidden
    state — the lifecycle is pure: a consumed or invalidated token is a new
    immutable record, and the earlier one is unchanged.
"""

from collections.abc import Mapping
from dataclasses import dataclass, replace
from datetime import datetime, timedelta
from enum import Enum
from types import MappingProxyType

from episky.policy.classify import (
    Classification,
    Gate,
    PlanClassification,
    RiskClass,
)
from episky.policy.policy import ElevationBound, Policy, allowlisted
from episky.schema.action import Action, Step
from episky.schema.fact import Fact

__all__ = [
    "EXPIRY_WINDOWS",
    "Decision",
    "InvalidationReason",
    "MintOutcome",
    "RecordKind",
    "Token",
    "TokenRecord",
    "TokenStatus",
    "consume",
    "expiry_for",
    "invalidate",
    "mint",
    "revalidate",
    "validate",
]


class Decision(Enum):
    """The explicit decision input ``mint`` requires (RFC-0008 §8; DN-49).

    The Operator's decision is an argument — approve, auto-permit (an
    allowlisted read-only Action), override (a blocked Action), or reject
    (RFC-0002 §2.7) — never inferred and never granted on silence (§13 P5;
    "no 'accept after timeout'"). ``mint`` never decides whether to approve
    (RFC-0004 §4.8 C11).

    Members:
        APPROVE: Approves a confirm or confirm-with-warning Action.
        AUTO_PERMIT: Per an allowlisted read-only Action (§8; §13 P5).
        OVERRIDE: Overrides a blocked Action — the only path past a block
            (§13 P10).
        REJECT: Refuses the Action; mints nothing (§13 P5).
    """

    APPROVE = "approve"
    AUTO_PERMIT = "auto-permit"
    OVERRIDE = "override"
    REJECT = "reject"


class RecordKind(Enum):
    """The in-memory token records (RFC-0008 §13 P13; DN-50).

    Every issuance, auto-permit, override, and rejection mints a metadata
    record alongside the outcome — the layer-boundary form of "approval is
    recorded before it is spent" (RFC-0002 invariant 13). The durable Audit
    write of these records is ``audit``'s (Iteration 8), not this layer's.

    Members:
        ISSUANCE: An APPROVE decision recorded a spendable token.
        AUTO_PERMIT: An AUTO_PERMIT decision recorded a spendable token.
        OVERRIDE: An OVERRIDE decision recorded a blocked-Action token.
        REJECTION: A REJECT decision recorded a refusal; no token.
    """

    ISSUANCE = "issuance"
    AUTO_PERMIT = "auto-permit"
    OVERRIDE = "override"
    REJECTION = "rejection"


class InvalidationReason(Enum):
    """Why a token is invalidated — the boundary events of §8, §13 P8.

    Each is a deterministic input to ``invalidate``: a state change, an
    interrupt or partial execution, a reboot, a session restart, a policy
    reload, or revocation by the Operator. A token invalidated for any of
    these reasons is never resurrected (I-15).

    Members:
        STATE_CHANGE: The Machine State it was approved against changed.
        INTERRUPT: An interrupt or partial execution occurred.
        REBOOT: The machine rebooted.
        SESSION_RESTART: The producing session restarted or exited.
        POLICY_RELOAD: The policy was reloaded; outstanding tokens are
            re-validated or invalidated (§13 P14).
        REVOCATION: The Operator revoked it before it was spent.
    """

    STATE_CHANGE = "state-change"
    INTERRUPT = "interrupt"
    REBOOT = "reboot"
    SESSION_RESTART = "session-restart"
    POLICY_RELOAD = "policy-reload"
    REVOCATION = "revocation"


class TokenStatus(Enum):
    """The deterministic outcome of ``validate``/``revalidate`` (§8, §9).

    Members:
        VALID: Alive and consistent with everything it is bound to.
        CONSUMED: Spent by its one use; dead (§13 P7).
        EXPIRED: Past its per-class lifetime; dead (§8; §13 P8).
        INVALIDATED: Killed by a boundary event; never resurrected (§13 P8).
        ACTION_MISMATCH: The Action (or Step set) no longer matches (§9 §9.3).
        FACT_CHANGED: A referenced Fact is stale or changed (§9 §9.1).
        STATE_CHANGED: The state snapshot no longer matches (§9 §9.2; Q4).
        SESSION_MISMATCH: The producing session no longer matches (§8).
    """

    VALID = "valid"
    CONSUMED = "consumed"
    EXPIRED = "expired"
    INVALIDATED = "invalidated"
    ACTION_MISMATCH = "action-mismatch"
    FACT_CHANGED = "fact-changed"
    STATE_CHANGED = "state-changed"
    SESSION_MISMATCH = "session-mismatch"


# The deterministic per-class expiry windows (RFC-0008 §8: "fixed by Policy
# per risk class — short, never open-ended"). The mechanism, not the final
# content: the shipped windows are RFC-0020's (§16; DN-51) and are tuned
# there; what is fixed here is that each class has one deterministic window
# and that a more restrictive class never outlives a less restrictive one.
# ``expiry_for`` derives the token's expiry from its class and issued_at —
# the same class and time always yield the same expiry (§13 P8).
EXPIRY_WINDOWS: Mapping[RiskClass, timedelta] = MappingProxyType(
    {
        RiskClass.READ_ONLY: timedelta(hours=24),
        RiskClass.BENIGN: timedelta(hours=12),
        RiskClass.CONSEQUENTIAL: timedelta(hours=4),
        RiskClass.DESTRUCTIVE: timedelta(minutes=30),
    }
)


@dataclass(frozen=True, slots=True)
class Token:
    """The scoped, consumable, invalidated Approval Token (§8; I-11).

    The only thing that carries permission to the Executor (RFC-0004 A2) —
    and it is never authority by itself: it carries what was approved, and
    execution is outside this layer (A6). The token binds exactly what was
    shown: the approved Action, or the presented Step set of a plan
    envelope (DN-54); everything it does not name is not approved (§13 P6).
    It records the Facts it was approved against and an opaque reference to
    the machine-state snapshot it was approved against (Q4) — both
    caller-supplied and never interpreted here. Its expiry is deterministic
    per class (§8). ``session`` and ``state_snapshot`` are caller-supplied
    references, carried for the binding and compared by identity on
    re-validation; the layer never generates an identifier. Frozen and
    slot-based: immutable, in-memory only. A consumed or invalidated token
    is a new record produced by ``consume``/``invalidate``; the original is
    never mutated and never resurrected (I-15).

    Attributes:
        action: The approved Action; ``None`` for a plan-envelope token.
        risk_class: The risk class at mint time.
        gate: The carried gate at mint time (decided before presentation).
        issued_at: When the token was minted (an explicit-time input).
        expiry: ``issued_at`` plus the class's deterministic window.
        session: The identity of the producing session, carried for the
            binding (RFC-0008 §8).
        state_snapshot: The machine-state snapshot reference the Action was
            approved against (Q4), carried for the binding.
        facts: The referenced-Fact set the Action was approved against.
        steps: The presented Step set of a plan envelope (DN-54); empty for
            a single-Action token.
        elevation_bounds: The elevation bounds the approved Action declared
            (DN-53; §8), recorded for P12's testable half.
        override: Whether this token was minted through an override (§13 P10).
        consumed: Whether the token's one use has been spent (§13 P7).
        invalidated: Whether a boundary event killed it (§13 P8).
        invalidation_reason: Why it was invalidated, when it was.
    """

    action: Action | None
    risk_class: RiskClass
    gate: Gate
    issued_at: datetime
    expiry: datetime
    session: object
    state_snapshot: object
    facts: tuple[Fact, ...] = ()
    steps: tuple[Step, ...] = ()
    elevation_bounds: tuple[ElevationBound, ...] = ()
    override: bool = False
    consumed: bool = False
    invalidated: bool = False
    invalidation_reason: InvalidationReason | None = None


@dataclass(frozen=True, slots=True)
class TokenRecord:
    """The in-memory issuance/override/auto-permit/rejection record (§13 P13).

    Created with every ``mint`` outcome so that no token is spendable
    without a prior record (RFC-0002 invariant 13; DN-50): a record is
    produced before, and alongside, any spendable token. The durable Audit
    write of these records is ``audit``'s (Iteration 8). Frozen and
    slot-based: immutable metadata, in-memory only.

    Attributes:
        kind: ISSUANCE, AUTO_PERMIT, OVERRIDE, or REJECTION.
        action: The Action the decision was about; ``None`` for a plan
            envelope.
        risk_class: The risk class at decision time, if one was reached.
        gate: The carried gate at decision time.
        decided_at: When the decision was made (an explicit-time input).
        override_reason: The explicit reason for an override (P10).
    """

    kind: RecordKind
    action: Action | None
    risk_class: RiskClass | None
    gate: Gate
    decided_at: datetime
    override_reason: str | None = None


@dataclass(frozen=True, slots=True)
class MintOutcome:
    """One ``mint`` result: at most one token and the record that precedes it.

    ``token`` is ``None`` exactly when nothing was minted — a rejection, an
    absent decision, or a decision the gate refuses (§13 P5). ``record`` is
    ``None`` only for an absent decision; every other call produces a
    record (§13 P13). Frozen and slot-based: the outcome is immutable.

    Attributes:
        token: The spendable token, or ``None``.
        record: The issuance/auto-permit/override/rejection record, or
            ``None`` for an absent decision.
    """

    token: Token | None = None
    record: TokenRecord | None = None


def expiry_for(risk_class: RiskClass, issued_at: datetime) -> datetime:
    """The deterministic per-class expiry (§8; §13 P8).

    ``issued_at + EXPIRY_WINDOWS[risk_class]`` — the same class and time
    always yield the same expiry, and a token that exceeds it is dead, not
    renewable. Time is an argument, never a clock read.

    Args:
        risk_class: The risk class of the Action.
        issued_at: When the token is issued.

    Returns:
        The expiry datetime.

    Raises:
        ValueError: If ``risk_class`` is not a ``RiskClass`` — a non-class
            gets no window (fail closed, §13 P3).
    """
    if not isinstance(risk_class, RiskClass):
        raise ValueError("expiry_for requires a RiskClass (RFC-0008 §8; §13 P3)")
    return issued_at + EXPIRY_WINDOWS[risk_class]


def mint(
    classification: Classification | PlanClassification,
    decision: Decision | None,
    *,
    now: datetime,
    session: object,
    state_snapshot: object,
    policy: Policy,
    steps: tuple[Step, ...] = (),
    elevation_bounds: tuple[ElevationBound, ...] = (),
    reason: str | None = None,
) -> MintOutcome:
    """Mint a token only on a prior classification and an explicit decision.

    The Approval Engine mints only after (a) the Policy Engine has
    classified and gated the Action and (b) the Operator has made an
    explicit decision (RFC-0008 §8) — this function is that second gate,
    nothing more. ``mint`` never decides whether to approve (RFC-0004 §4.8
    C11) and never mints on its own authority (A6): an absent decision, a
    rejection, or a decision the carried gate refuses produces no token and
    consumes nothing (§13 P5; DN-49). AUTO_PERMIT is accepted only for an
    allowlisted read-only Action (DN-49) — verified against the policy's
    allowlist membership (C2), so no silent or mistaken auto-permission
    passes (RFC-0001 §8.3). OVERRIDE is accepted only for a blocked Action
    and produces an override-scoped token plus an override record with its
    explicit reason (§13 P10). The token's expiry is deterministic per
    class; its binding — Action (or presented Step set, DN-54), Facts,
    state snapshot (Q4), session, and elevation bounds (DN-53) — is
    recorded verbatim, never interpreted. Pure and deterministic: the same
    inputs always yield the same outcome.

    Args:
        classification: The prior ``Classification`` of one Action, or the
            ``PlanClassification`` of a plan envelope (DN-54).
        decision: The Operator's explicit decision, or ``None`` when no
            decision has been given (nothing mints, P5).
        now: The current time, supplied by the caller — the token's
            ``issued_at`` and the base of its deterministic expiry.
        session: The identity of the producing session, carried for the
            binding (RFC-0008 §8). Caller-supplied; never generated here.
        state_snapshot: The machine-state snapshot reference the Action is
            approved against (Q4). Caller-supplied; never interpreted here.
        policy: The Operator-owned policy whose allowlist decides
            ``AUTO_PERMIT`` (C2; DN-49). Nothing else in ``mint`` reads it.
        steps: The presented Step set of a plan envelope (DN-54); required
            non-empty for a ``PlanClassification`` and must be empty for a
            single-Action ``Classification``.
        elevation_bounds: The elevation bounds the approved Action declared
            (DN-53), recorded on the token (P12's testable half).
        reason: The explicit reason for an override (P10); required
            non-empty for ``Decision.OVERRIDE`` and invalid for any other
            decision.

    Returns:
        The ``MintOutcome``: a spendable token with its prior record, or a
        rejection record, or nothing.

    Raises:
        ValueError: For a non-classification, a missing override reason, an
            override reason on a non-override, a Step set that does not fit
            the classification, or a non-``ElevationBound`` bound — all
            fail closed, nothing mints.
    """
    if not isinstance(classification, (Classification, PlanClassification)):
        raise ValueError("mint requires a Classification (RFC-0008 §8)")
    is_plan = isinstance(classification, PlanClassification)
    if is_plan and not steps:
        raise ValueError(
            "a plan envelope token requires the presented Step set "
            "(RFC-0008 §8, §11; DN-54)"
        )
    if not is_plan and steps:
        raise ValueError(
            "a single-Action token never carries a Step set (RFC-0008 §8; DN-54)"
        )
    if not all(isinstance(bound, ElevationBound) for bound in elevation_bounds):
        raise ValueError(
            "elevation bounds must be ElevationBound records (RFC-0008 §8; DN-53)"
        )
    if reason is not None and decision is not Decision.OVERRIDE:
        raise ValueError("only an override carries a reason (RFC-0008 §13 P10)")
    if decision is Decision.OVERRIDE and (reason is None or not reason.strip()):
        raise ValueError("an override requires an explicit reason (RFC-0008 §13 P10)")

    gate = classification.gate
    action = classification.action if not is_plan else None
    facts = classification.facts if not is_plan else ()

    if decision is None:
        return MintOutcome(token=None, record=None)
    if decision is Decision.REJECT:
        return MintOutcome(
            token=None,
            record=TokenRecord(
                kind=RecordKind.REJECTION,
                action=action,
                risk_class=classification.risk_class,
                gate=gate,
                decided_at=now,
            ),
        )
    if decision is Decision.AUTO_PERMIT:
        if is_plan:
            return MintOutcome(token=None, record=None)
        if classification.risk_class is not RiskClass.READ_ONLY:
            return MintOutcome(token=None, record=None)
        if not allowlisted(policy, classification.action):
            return MintOutcome(token=None, record=None)
        kind = RecordKind.AUTO_PERMIT
        effective_gate = Gate.AUTO_PERMITTED
    elif decision is Decision.OVERRIDE:
        if gate is not Gate.BLOCKED:
            return MintOutcome(token=None, record=None)
        kind = RecordKind.OVERRIDE
        effective_gate = gate
    else:
        if gate not in (Gate.CONFIRM, Gate.CONFIRM_WITH_WARNING):
            return MintOutcome(token=None, record=None)
        kind = RecordKind.ISSUANCE
        effective_gate = gate

    risk_class = classification.risk_class
    if risk_class is None:
        return MintOutcome(token=None, record=None)
    token = Token(
        action=action,
        risk_class=risk_class,
        gate=effective_gate,
        issued_at=now,
        expiry=expiry_for(risk_class, now),
        session=session,
        state_snapshot=state_snapshot,
        facts=facts,
        steps=steps,
        elevation_bounds=elevation_bounds,
        override=decision is Decision.OVERRIDE,
    )
    record = TokenRecord(
        kind=kind,
        action=action,
        risk_class=risk_class,
        gate=effective_gate,
        decided_at=now,
        override_reason=reason if decision is Decision.OVERRIDE else None,
    )
    return MintOutcome(token=token, record=record)


def validate(token: Token, *, now: datetime) -> TokenStatus:
    """Whether the token record itself is alive at ``now`` (§8; §13 P7/P8).

    Pure and deterministic: a consumed token is dead (P7), an invalidated
    token is dead and never resurrected (P8, I-15), and a token past its
    deterministic per-class expiry is dead — executing under it is a fresh
    approval, not a renewal (§8). Time is an argument, never a clock read.

    Args:
        token: The token to check.
        now: The current time, supplied by the caller.

    Returns:
        ``TokenStatus.VALID``, or the dead state that holds.
    """
    if token.consumed:
        return TokenStatus.CONSUMED
    if token.invalidated:
        return TokenStatus.INVALIDATED
    if now >= token.expiry:
        return TokenStatus.EXPIRED
    return TokenStatus.VALID


def revalidate(
    token: Token,
    *,
    now: datetime,
    action: Action | None = None,
    steps: tuple[Step, ...] = (),
    facts: tuple[Fact, ...] = (),
    state_snapshot: object = None,
    session: object = None,
) -> TokenStatus:
    """The deterministic boundary re-validation (§9, §10; §13 P6/P9/P14).

    The same checks the engine makes at Awaiting Approval → Executing: the
    token is valid/unexpired/state-consistent; the Action at the boundary
    is structurally identical to the one shown, classified, and approved —
    for a plan envelope, the presented Step set (DN-54); the referenced
    Facts are re-checked by deterministic comparison; and the machine-state
    snapshot and producing session still match (Q4). Any mismatch or any
    uncertainty is a refusal: fail closed, disclose, re-present (§9;
    RFC-0002 §2.8). A token invalidated by a reload or state change is
    refused here (§13 P14). Pure and deterministic — the same inputs always
    yield the same status.

    Args:
        token: The token to re-validate.
        now: The current time, supplied by the caller.
        action: The Action at the boundary; required for a single-Action
            token.
        steps: The Step set at the boundary for a plan-envelope token.
        facts: The re-checked referenced-Fact set at the boundary.
        state_snapshot: The boundary's state-snapshot reference (compared
            by identity against the token's; Q4).
        session: The boundary's session identity (compared by identity).

    Returns:
        ``TokenStatus.VALID`` or the first refusal reason.
    """
    status = validate(token, now=now)
    if status is not TokenStatus.VALID:
        return status
    if token.steps:
        if steps != token.steps:
            return TokenStatus.ACTION_MISMATCH
    elif action != token.action:
        return TokenStatus.ACTION_MISMATCH
    if facts != token.facts:
        return TokenStatus.FACT_CHANGED
    if state_snapshot is not token.state_snapshot:
        return TokenStatus.STATE_CHANGED
    if session is not token.session:
        return TokenStatus.SESSION_MISMATCH
    return TokenStatus.VALID


def consume(token: Token) -> Token:
    """Spend the token's single use (§8; §13 P7).

    One Action, one token, consumed by that execution, never reused: the
    consumed token is dead and replay is refused (P7). The lifecycle is
    pure — a new immutable record is returned and the original is unchanged.
    Refusing a dead token fails closed; counting and re-presenting retries
    are the execution boundary's (RFC-0008 §8), not this layer's.

    Args:
        token: The token to consume.

    Returns:
        A new token with ``consumed=True``.

    Raises:
        ValueError: If the token is already consumed or invalidated — a
            dead token is never spent.
    """
    if token.consumed or token.invalidated:
        raise ValueError(
            "a consumed or invalidated token cannot be spent (RFC-0008 §13 P7; I-15)"
        )
    return replace(token, consumed=True)


def invalidate(token: Token, reason: InvalidationReason) -> Token:
    """Invalidate the token for a boundary event (§8; §13 P8, P14).

    A state change, interrupt, reboot, session restart, policy reload, or
    revocation invalidates the token, and it is never resurrected (I-15).
    Pure and idempotent: a new immutable record is returned; the original is
    unchanged; invalidating an already-dead token changes nothing.

    Args:
        token: The token to invalidate.
        reason: The boundary event that invalidates it.

    Returns:
        A new token with ``invalidated=True`` and the reason recorded, or
        the token unchanged when it is already dead.

    Raises:
        ValueError: If ``reason`` is not an ``InvalidationReason``.
    """
    if not isinstance(reason, InvalidationReason):
        raise ValueError(
            "invalidation requires an InvalidationReason (RFC-0008 §8; §13 P8)"
        )
    if token.consumed or token.invalidated:
        return token
    return replace(token, invalidated=True, invalidation_reason=reason)
