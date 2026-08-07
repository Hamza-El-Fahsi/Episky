"""Scoped elevation lifecycle (RFC-0008 §8; RFC-0001 §8.6; RFC-0009
SC10; DN-53, DN-60).

Owner: RFC-0008 §8 Elevation (explicit, per-action, scoped,
    re-authenticated; an elevated Action is at least Consequential; the
    elevation bounds are part of the token; revoked at the end of that
    Action or on any invalidation; never persists, never covers
    unapproved work, never a standing root session); RFC-0001 §8.6
    (principle 6).
Responsibility: the deterministic elevation lifecycle — a per-Action
    elevation request carrying its bounds (which ``policy`` already
    enforced as at-least-Consequential, DN-53) and a revocation that
    fires at the end of that Action or on any invalidation (Q6, DN-60).
    The machine's own elevation mechanism (RFC-0021 §3.3, Draft) is
    injected at the boundary, never built here: the module owns the
    request/revoke contract and the SC10 no-exposure boundary.
Forbidden responsibility: never persists anything — every value is an
    in-memory, immutable outcome and there is no module state. Never
    covers unapproved work: the request is bound to the token's one
    approved Action (RFC-0008 §8). Never forms a standing root session
    (RFC-0001 §8.6). Never displays or records a value (SC10): bounds
    are opaque references and disclosures are deterministic labels. No
    clock: time is an explicit argument. No secret handling, no
    authority creation, no mechanism implementation (RFC-0021 §3.3).
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from episky.executor.runner import TokenHandoff
from episky.schema.action import Action

__all__ = [
    "ElevationMechanism",
    "ElevationOutcome",
    "ElevationReason",
    "ElevationRequest",
    "ElevationSignal",
    "ElevationState",
    "request",
    "revoke",
]


class ElevationSignal(Enum):
    """The operation the injected mechanism is asked to perform (DN-60).

    The machine's own mechanism (RFC-0021 §3.3, Draft) receives the
    request and the signal; the module never names or builds the
    mechanism.

    Members:
        REQUEST: Grant the elevation for this one Action.
        REVOKE: Revoke the elevation at the end of that Action or on any
            invalidation (RFC-0008 §8).
    """

    REQUEST = "request"
    REVOKE = "revoke"


class ElevationState(Enum):
    """The deterministic lifecycle state of one elevation (RFC-0008 §8).

    Members:
        ACTIVE: The elevation is granted and bound to the one Action.
        REFUSED: The request failed closed — nothing was granted.
        REVOKED: The elevation was revoked at end or on invalidation.
    """

    ACTIVE = "active"
    REFUSED = "refused"
    REVOKED = "revoked"


class ElevationReason(Enum):
    """The deterministic reason an elevation is refused or not revoked.

    Every event is disclosed (RFC-0001 §8.12) — never silent, never
    guessed.

    Members:
        NO_ELEVATION: The token carries no elevation bounds — nothing to
            elevate (P12; RFC-0008 §8).
        NOT_APPROVED: The request is not for the token's one approved
            Action (RFC-0008 §8; I-1).
        MECHANISM_REFUSED: The injected mechanism declined the request
            (RFC-0001 §8.12).
        REVOKE_FAILED: The injected mechanism could not revoke; the
            elevation is not considered revoked (fail closed).
    """

    NO_ELEVATION = "no-elevation"
    NOT_APPROVED = "not-approved"
    MECHANISM_REFUSED = "mechanism-refused"
    REVOKE_FAILED = "revoke-failed"


@dataclass(frozen=True, slots=True)
class ElevationRequest:
    """The per-Action elevation request (RFC-0008 §8; DN-53, DN-60).

    Carries the approved Action's identity, the Action itself, and the
    elevation bounds the token recorded at mint — ``policy`` already
    enforced them as at-least-Consequential (DN-53). ``session`` binds
    the elevation to the producing session, and ``bounds`` are opaque
    references, never interpreted here and never a value (SC10). Frozen
    and slot-based (DN-34): an immutable, in-memory value.

    Attributes:
        action_id: The immutable identity of the approved Action.
        action: The approved Action the elevation is scoped to.
        bounds: The elevation bounds carried on the token (P12).
        session: The producing session's identity reference.
        issued_at: When the request was issued (an explicit-time input).
    """

    action_id: str
    action: Action
    bounds: tuple[object, ...]
    session: object
    issued_at: datetime


@dataclass(frozen=True, slots=True)
class ElevationOutcome:
    """One elevation decision: the lifecycle state plus its disclosure.

    Deterministic and fail-loud (RFC-0001 §8.12): a refused or failed
    event carries its ``reason`` and a fixed ``message``; a granted
    elevation carries its ``request`` and times. A revocation failure
    leaves the elevation ACTIVE and disclosed — the module never claims
    an elevation revoked when it is not (fail closed). Frozen and
    slot-based (DN-34): an immutable, in-memory value; nothing persists.

    Attributes:
        state: ACTIVE, REFUSED, or REVOKED.
        reason: The disclosed reason when refused or when revocation
            failed; None when the state is unproblematic.
        message: The fixed fail-loud disclosure; None when there is
            nothing to disclose.
        request: The request the outcome belongs to; None when the
            request was refused before it could be formed.
        started_at: When the elevation was granted; None until ACTIVE.
        ended_at: When the elevation was revoked; None until REVOKED.
    """

    state: ElevationState
    reason: ElevationReason | None = None
    message: str | None = None
    request: ElevationRequest | None = None
    started_at: datetime | None = None
    ended_at: datetime | None = None


ElevationMechanism = Callable[[ElevationRequest, ElevationSignal], bool]


def request(
    mechanism: ElevationMechanism,
    action: Action,
    token: TokenHandoff,
    *,
    now: datetime,
) -> ElevationOutcome:
    """Request elevation for the token's one approved Action (RFC-0008 §8).

    Pure and deterministic: the decision depends only on the explicit
    inputs. The request fails closed unless the token is bound to exactly
    the presented Action (never covers unapproved work, RFC-0008 §8) and
    the token carries elevation bounds (P12 — an elevated Action's token
    carries its bound). The injected mechanism (RFC-0021 §3.3) performs
    the machine's elevation and reports success or refusal; the module
    performs no I/O itself. Nothing here displays or records a value
    (SC10).

    Args:
        mechanism: The machine's own elevation mechanism, injected at
            the boundary; called with the request and REQUEST.
        action: The Action elevation is requested for; must be the
            token's one approved Action.
        token: The approval token's public fields (DN-56), carrying the
            approved Action and the elevation bounds.
        now: The current time — an explicit argument, never a clock
            read.

    Returns:
        An ACTIVE outcome with the request when the mechanism granted
        the elevation; a REFUSED outcome with a disclosed reason
        otherwise (RFC-0001 §8.12).
    """
    if token.action is None or action is not token.action:
        return ElevationOutcome(
            state=ElevationState.REFUSED,
            reason=ElevationReason.NOT_APPROVED,
            message=(
                "elevation never covers unapproved work: the request is "
                "not for the token's one approved Action (RFC-0008 §8)"
            ),
        )
    if not token.elevation_bounds:
        return ElevationOutcome(
            state=ElevationState.REFUSED,
            reason=ElevationReason.NO_ELEVATION,
            message=(
                "the token carries no elevation bounds; nothing to elevate "
                "(RFC-0008 §8, P12)"
            ),
        )
    elevation = ElevationRequest(
        action_id=token.action_id,
        action=action,
        bounds=token.elevation_bounds,
        session=token.session,
        issued_at=now,
    )
    if mechanism(elevation, ElevationSignal.REQUEST):
        return ElevationOutcome(
            state=ElevationState.ACTIVE,
            request=elevation,
            started_at=now,
        )
    return ElevationOutcome(
        state=ElevationState.REFUSED,
        reason=ElevationReason.MECHANISM_REFUSED,
        message=(
            "the injected elevation mechanism declined the request; "
            "fail closed (RFC-0001 §8.12)"
        ),
        request=elevation,
    )


def revoke(
    mechanism: ElevationMechanism,
    elevation: ElevationOutcome,
    *,
    now: datetime,
) -> ElevationOutcome:
    """Revoke an elevation at the end of the Action or on any
    invalidation (RFC-0008 §8; DN-60).

    Pure and deterministic. Only an ACTIVE elevation is revoked; a
    REFUSED or REVOKED outcome is returned unchanged (idempotent, never
    persisted). The injected mechanism reports whether the revocation
    completed; a failed revocation leaves the elevation ACTIVE and
    disclosed — the module never claims an elevation revoked when it is
    not (fail closed, RFC-0001 §8.12). Nothing here displays or records
    a value (SC10).

    Args:
        mechanism: The machine's own elevation mechanism, injected at
            the boundary; called with the elevation's request and REVOKE.
        elevation: The outcome to revoke; must be ACTIVE.
        now: The current time — an explicit argument, never a clock
            read.

    Returns:
        A REVOKED outcome with ``ended_at`` set when the mechanism
        revoked; the unchanged ACTIVE outcome with a REVOKE_FAILED
        disclosure when it did not.
    """
    if elevation.state is not ElevationState.ACTIVE or elevation.request is None:
        return elevation
    if mechanism(elevation.request, ElevationSignal.REVOKE):
        return ElevationOutcome(
            state=ElevationState.REVOKED,
            request=elevation.request,
            started_at=elevation.started_at,
            ended_at=now,
        )
    return ElevationOutcome(
        state=ElevationState.ACTIVE,
        reason=ElevationReason.REVOKE_FAILED,
        message=(
            "revocation failed; the elevation is not revoked — fail closed "
            "(RFC-0001 §8.12)"
        ),
        request=elevation.request,
        started_at=elevation.started_at,
    )
