"""Operator-owned, default-deny policy mechanism (RFC-0008 §7, §8, §10).

Owner: RFC-0008 §7 (policy evaluation and decision), §8 (standing
    approvals, retry ceilings, elevation bounds), §10 (TOCTOU — the
    decision is a pure function of its inputs), §13 (P3, P8, P11);
    RFC-0001 §8.2 (default deny), §8.3 (standing approvals), §8.12 (fail
    closed); RFC-0004 §9.7 (never loosens), A6 (no Approve/Execute/
    Observe); ratified decision notes DN-51 (the mechanism now, the
    shipped contents RFC-0020's), DN-52 (standing-approval construct),
    DN-53 (elevation bounds).
Responsibility: the Operator-owned, default-deny policy *mechanism* — the
    read-only-allowlist membership function (empty by default, Q7),
    elevation and standing-approval bounds, per-class retry ceilings, a
    fail-closed ``load``, and the deterministic decision that composes a
    C1 Classification with the §6 gate table into exactly one outcome: a
    risk class and a carried gate, with warning grounds or reason (§7).
Forbidden responsibility: never loosens the Operator's bounds on its own
    (RFC-0004 §9.7); never Approves, never Executes, never Observes (A6);
    never reads a clock — time is an argument, never a side effect; never
    mints a token, never writes an audit record, never contacts the
    runtime (the §6.2 edges are ``core``'s); no I/O, no persistence, no
    global state, no caches, no execution.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from datetime import datetime
from types import MappingProxyType

from episky.policy.classify import Classification, Gate, RiskClass
from episky.policy.gates import gate_for
from episky.schema.action import Action

__all__ = [
    "ElevationBound",
    "Policy",
    "PolicyDecision",
    "StandingApproval",
    "allowlisted",
    "decide",
    "elevation_bound_for",
    "load",
    "retry_ceiling",
    "standing_approval_applies",
]


@dataclass(frozen=True, slots=True)
class ElevationBound:
    """A bound on elevation an Operator permits (RFC-0008 §8; DN-53).

    Elevation is explicit, per-action, and scoped; a bound names the
    canonical scope within which elevation is permitted. No bounds are
    shipped by default — which bounds exist is RFC-0020 content (DN-51;
    RFC-0008 §16). The mechanism that *invokes and revokes* the machine's
    privilege-escalation is ``executor``'s (DN-53), never this layer's.
    Frozen and slot-based: an in-memory, immutable policy value.

    Attributes:
        scope: The canonical scope of the elevation, matched exactly
            against the Action's description (mechanism; the scopes are
            RFC-0020's).
    """

    scope: str


@dataclass(frozen=True, slots=True)
class StandingApproval:
    """A scoped, expiring, ceiling-bound approval (RFC-0008 §8; DN-52).

    A Policy construct that pre-authorizes a class of Actions within a
    defined scope and a risk-class ceiling, expiring at ``expiry``. It
    never covers a Blocked Action and never raises a ceiling (P11). No
    standing approvals are shipped by default — which ones the project
    ships is RFC-0020's (DN-52; §16). Pre-minting is exercised through
    the token machinery (C3, DN-49), never as blanket authority.
    Frozen and slot-based: an in-memory, immutable policy value.

    Attributes:
        scope: The canonical scope the approval covers, matched exactly
            against the Action's description (mechanism; the scopes are
            RFC-0020's).
        ceiling: The most restrictive risk class the approval covers.
        expiry: The approval's expiry; time is an argument, never a
            clock read.
    """

    scope: str
    ceiling: RiskClass
    expiry: datetime


@dataclass(frozen=True, slots=True)
class Policy:
    """The Operator-owned, default-deny policy (RFC-0008 §7; DN-51).

    Holds the deterministic rule set: the read-only allowlist (empty by
    default — contents RFC-0020's), elevation bounds, standing-approval
    bounds, and per-class retry ceilings. The class→gate table itself is
    ``gates.CLASS_GATES``; this record carries the Operator-configurable
    bounds on top of it. Frozen and slot-based; ``load`` is the
    fail-closed construction path.

    Attributes:
        allowlist: The read-only-allowlist entries (canonical Action
            descriptions), empty by default (Q7).
        elevation_bounds: The elevation bounds, empty by default.
        standing_approvals: The standing approvals, empty by default.
        retry_ceilings: Per-risk-class retry ceilings, unset by default.
    """

    allowlist: frozenset[str] = frozenset()
    elevation_bounds: tuple[ElevationBound, ...] = ()
    standing_approvals: tuple[StandingApproval, ...] = ()
    retry_ceilings: Mapping[RiskClass, int] = MappingProxyType({})


@dataclass(frozen=True, slots=True)
class PolicyDecision:
    """Exactly one policy outcome for one Action (RFC-0008 §7).

    A risk class and a carried gate with warning grounds (confirm-with-
    warning) or reason (blocked), plus the policy-evaluation results the
    decision was built from — whether allowlisted, which standing
    approval (if any) applies, to which elevation bound, and the class's
    retry ceiling. The gate is decided here, before presentation, and is
    never re-derived by it (§13 P4). When the Action cannot be
    classified, ``risk_class`` is ``None`` and the gate is blocked:
    default deny and fail closed (§13 P3; RFC-0001 §8.2). Frozen and
    slot-based: immutable, in-memory only.

    Attributes:
        risk_class: The risk class, or ``None`` when unclassifiable.
        gate: The carried gate.
        action: The Action the decision is about (a deterministic input).
        allowlisted: Whether the Action is inside the read-only allowlist.
        standing_approval: The standing approval that applies, if any.
        elevation_bound: The elevation bound that applies, if any.
        retry_ceiling: The class's retry ceiling, if one is configured.
        warning_grounds: Why the gate is confirm-with-warning; populated
            only for ``Gate.CONFIRM_WITH_WARNING``.
        reason: Why the outcome is blocked; populated only for
            ``Gate.BLOCKED``.
    """

    risk_class: RiskClass | None
    gate: Gate
    action: Action
    allowlisted: bool
    standing_approval: StandingApproval | None
    elevation_bound: ElevationBound | None
    retry_ceiling: int | None
    warning_grounds: str | None = None
    reason: str | None = None


def load(
    *,
    allowlist: tuple[str, ...] | list[str] = (),
    elevation_bounds: tuple[ElevationBound, ...] | list[ElevationBound] = (),
    standing_approvals: tuple[StandingApproval, ...] | list[StandingApproval] = (),
    retry_ceilings: Mapping[RiskClass, int] = MappingProxyType({}),
) -> Policy:
    """Build a Policy, failing closed on an unparseable rule (P3, §8.12).

    The mechanism, not the content: every value here is the Operator's
    to set; the shipped defaults (which Actions are allowlisted, which
    approvals exist, the expiry windows, the ceilings) are RFC-0020's
    (DN-51; §16). Any malformed rule raises ``ValueError`` and no Policy
    is produced — a policy never loads partially and never loosens the
    Operator's bounds on its own (RFC-0004 §9.7).

    Args:
        allowlist: Canonical descriptions of read-only Actions; each must
            be a non-empty string. Empty by default.
        elevation_bounds: ``ElevationBound`` records with non-empty
            scopes. Empty by default.
        standing_approvals: ``StandingApproval`` records with non-empty
            scopes and non-Destructive ceilings. Empty by default.
        retry_ceilings: RiskClass → positive integer. Empty by default.

    Returns:
        The immutable Policy.

    Raises:
        ValueError: If any rule is malformed (empty entry, non-positive
            ceiling, a standing approval that would cover a Blocked
            Action, or a wrong type).
    """
    for entry in allowlist:
        if not isinstance(entry, str) or not entry:
            raise ValueError(
                "allowlist entries must be non-empty descriptions (RFC-0008 §6)"
            )
    for bound in elevation_bounds:
        if not isinstance(bound, ElevationBound) or not bound.scope:
            raise ValueError(
                "an elevation bound needs a non-empty scope (RFC-0008 §8; §13 P3)"
            )
    for approval in standing_approvals:
        if not isinstance(approval, StandingApproval) or not approval.scope:
            raise ValueError(
                "a standing approval needs a non-empty scope (RFC-0008 §8; §13 P3)"
            )
        if not isinstance(approval.ceiling, RiskClass):
            raise ValueError(
                "a standing approval ceiling must be a RiskClass (RFC-0008 §8)"
            )
        if approval.ceiling is RiskClass.DESTRUCTIVE:
            raise ValueError(
                "a standing approval never covers a Blocked Action "
                "(RFC-0008 §8; §13 P11)"
            )
        if not isinstance(approval.expiry, datetime):
            raise ValueError(
                "a standing approval needs a datetime expiry (RFC-0008 §8)"
            )
    ceilings: dict[RiskClass, int] = {}
    for risk_class, ceiling in retry_ceilings.items():
        if not isinstance(risk_class, RiskClass):
            raise ValueError("retry ceilings are keyed by RiskClass (RFC-0008 §8)")
        if not isinstance(ceiling, int) or ceiling < 1:
            raise ValueError("retry ceilings are positive integers (RFC-0008 §8)")
        ceilings[risk_class] = ceiling
    return Policy(
        allowlist=frozenset(allowlist),
        elevation_bounds=tuple(elevation_bounds),
        standing_approvals=tuple(standing_approvals),
        retry_ceilings=MappingProxyType(ceilings),
    )


def allowlisted(policy: Policy, action: Action) -> bool:
    """The read-only-allowlist membership function (RFC-0008 §6; Q7).

    Deterministic exact-description membership over the allowlist, empty
    by default (nothing is auto-permitted until RFC-0020 ships contents).
    Membership alone never loosens a non-read-only gate — the §6 gate
    table applies the allowlist only to ``RiskClass.READ_ONLY``.

    Args:
        policy: The policy holding the allowlist.
        action: The Action to test.

    Returns:
        Whether the Action's description is allowlisted.
    """
    return action.description in policy.allowlist


def elevation_bound_for(policy: Policy, action: Action) -> ElevationBound | None:
    """The elevation bound that applies to an Action, if any (RFC-0008 §8).

    Empty by default — no elevation is permitted until an Operator
    configures a bound (DN-53; §16). Carried by the decision; the
    *mechanism* that invokes and revokes elevation is ``executor``'s.

    Args:
        policy: The policy holding the elevation bounds.
        action: The Action to match.

    Returns:
        The first matching bound, or ``None``.
    """
    for bound in policy.elevation_bounds:
        if bound.scope == action.description:
            return bound
    return None


def retry_ceiling(policy: Policy, risk_class: RiskClass) -> int | None:
    """The retry ceiling for a risk class, if configured (RFC-0008 §8).

    A retry is a new execution of the same Action, bounded per risk class
    by a small, explicit ceiling. Unset by default — the concrete ceiling
    values are RFC-0020's (DN-51). Counting retries is execution-boundary
    behavior (``core``/``executor``); this is the policy value only.

    Args:
        policy: The policy holding the ceilings.
        risk_class: The risk class to look up.

    Returns:
        The ceiling, or ``None`` when unconfigured.
    """
    return policy.retry_ceilings.get(risk_class)


def standing_approval_applies(
    approval: StandingApproval,
    classification: Classification,
    now: datetime,
) -> bool:
    """Whether a standing approval applies to a classification (DN-52; P11).

    Applies only if the Action is in scope, the class is at or below the
    ceiling, and the approval is unexpired. It never covers a Blocked
    Action and never raises a ceiling (RFC-0008 §8; §13 P11). Time is an
    argument, never a clock read — the same ``now`` always yields the
    same answer.

    Args:
        approval: The standing approval to evaluate.
        classification: The C1 Classification of the Action.
        now: The current time, supplied by the caller.

    Returns:
        Whether the approval applies.
    """
    risk_class = classification.risk_class
    if risk_class is None or risk_class is RiskClass.DESTRUCTIVE:
        return False
    if risk_class.value < approval.ceiling.value:
        return False
    if not approval.expiry > now:
        return False
    return approval.scope == classification.action.description


def decide(
    policy: Policy, classification: Classification, now: datetime
) -> PolicyDecision:
    """The deterministic policy decision for one Action (RFC-0008 §7).

    Composes a C1 Classification with the §6 gate table and the policy's
    bounds into exactly one outcome: a risk class and a carried gate,
    with warning grounds (confirm-with-warning) or reason (blocked). Pure
    and deterministic — the same Policy, Classification, and ``now``
    always yield the same decision. Where no rule matches — an
    unclassifiable Action — the decision is blocked, default deny and
    fail closed (§13 P3; RFC-0001 §8.2). Never loosens the Operator's
    bounds: the allowlist, a standing approval, or an elevation bound
    never changes a blocked or warned gate (RFC-0004 §9.7).

    Args:
        policy: The Operator-owned policy.
        classification: The Classification produced by C1's ``classify``.
        now: The current time, supplied by the caller.

    Returns:
        The PolicyDecision: the class, the carried gate, and the
        policy-evaluation results it was built from.

    Raises:
        ValueError: If ``classification`` is not a ``Classification``.
    """
    if not isinstance(classification, Classification):
        raise ValueError("decide requires a Classification (RFC-0008 §7)")
    action = classification.action
    in_allowlist = allowlisted(policy, action)
    if classification.risk_class is None:
        return PolicyDecision(
            risk_class=None,
            gate=Gate.BLOCKED,
            action=action,
            allowlisted=in_allowlist,
            standing_approval=None,
            elevation_bound=None,
            retry_ceiling=None,
            reason=classification.reason
            or "unclassified Action: default deny (RFC-0008 §7; §13 P3)",
        )
    return PolicyDecision(
        risk_class=classification.risk_class,
        gate=gate_for(classification.risk_class, in_allowlist),
        action=action,
        allowlisted=in_allowlist,
        standing_approval=_applicable(policy, classification, now),
        elevation_bound=elevation_bound_for(policy, action),
        retry_ceiling=retry_ceiling(policy, classification.risk_class),
        warning_grounds=classification.warning_grounds,
        reason=classification.reason,
    )


def _applicable(
    policy: Policy, classification: Classification, now: datetime
) -> StandingApproval | None:
    """The first standing approval that applies, if any (deterministic)."""
    for approval in policy.standing_approvals:
        if standing_approval_applies(approval, classification, now):
            return approval
    return None
