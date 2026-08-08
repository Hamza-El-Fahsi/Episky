"""Skill Activation: the per-session, reversible, Policy-gated, audited
lifecycle (RFC-0011 §23; RFC-0002 §2.2/§4.7; RFC-0008; RFC-0011 §16).

Owner: RFC-0011 §23 (activation makes a validated Skill usable within a
    session, per Policy: per-session and reversible, RFC-0002 §2.2;
    Policy-gated, RFC-0008; grants no authority — an activated Skill still
    proposes, §4; an unauthenticated Skill is never substituted, RFC-0002
    §4.7; audited, §16); §16 (every Skill event is recorded — activation,
    deactivation, refusal — and Skill identity is recorded: version,
    signature, declared surface).
Responsibility: the deterministic mechanics of the §23 lifecycle for a Skill
    the Registry already loaded and registered (`loader.py`, C3): take an
    activation request that binds a session identity to a loaded Skill; gate
    it on an injected Policy decision (RFC-0008) — missing or refused
    decisions fail closed (SK5); transition the per-session stage between
    INACTIVE and ACTIVE reversibly; refuse identity mismatch, double
    activation, and deactivation of a not-active activation; and emit the
    §16 audited event (ACTIVATED / DEACTIVATED / REFUSED) with the session
    and Skill identity attached. Activation creates no authority: the
    record binds only {session, skill, stage}, an activated Skill still only
    proposes (§4), and nothing here is a Fact, an approval, a token, or an
    execution surface.
Forbidden responsibility: never authenticates or re-validates the declared
    surface (the loader did, C3) — the Policy decision is injected and never
    judged here (RFC-0008), and the unauthenticated-substitution guard is
    fail-closed at the type/stage boundary (RFC-0002 §4.7); never runs the
    consultation or owns the session scope (those are `core`'s, RFC-0002
    §6/§2.2; DN-81); never participates in the gate (that is `runtime.py`,
    §24; DN-81); no I/O, no clock, no randomness, no serialization, no
    subprocess, no hidden state, no `secrets`, `audit`, `executor`,
    `verification`, `providers`, or `core` (blueprint §4.2; RFC-0011 §15;
    SK14/SK8; DN-82). Deterministic: identical inputs always produce the
    identical ActivationOutcome and every refusal is loud and disclosed
    (RFC-0011 §10).
"""

from collections.abc import Callable
from dataclasses import dataclass
from enum import Enum, auto

from episky.skills.loader import Skill, SkillManifest, SkillStage

__all__ = [
    "Activation",
    "ActivationEvent",
    "ActivationOutcome",
    "ActivationRefusal",
    "ActivationRequest",
    "ActivationStage",
    "ActivationVerdict",
    "activate",
    "deactivate",
]


class ActivationStage(Enum):
    """The per-session activation stage of a registered Skill (RFC-0011 §23).

    Activation is per-session and reversible (RFC-0002 §2.2): a loaded Skill
    is INACTIVE until a session activates it, ACTIVE for that session, and
    INACTIVE again when the session deactivates it. The registry stage is
    unchanged throughout — a deactivated Skill is still REGISTERED (§22).

    Members:
        INACTIVE: Registered but not activated for this session; not usable.
        ACTIVE: Activated for this session; usable, yet still only proposes
            (§4) and passes the exact same gate (§24).
    """

    INACTIVE = auto()

    ACTIVE = auto()


class ActivationVerdict(Enum):
    """The injected Policy decision for the activation (RFC-0008; §5).

    Members:
        PERMITTED: The activated Skill is within Policy for this session;
            the activation proceeds.
        REFUSED: Policy declines the activation; it is refused, audited, and
            nothing is substituted (RFC-0002 §4.7).
    """

    PERMITTED = "permitted"

    REFUSED = "refused"


class ActivationEvent(Enum):
    """The §16 audited events the activation boundary records (RFC-0011 §16).

    Every Skill event is recorded — activation, deactivation, refusal — with
    the session and Skill identity attached; the audit *write* is `core`'s
    (RFC-0013 §23; DN-81). Members:
        ACTIVATED: The Skill became active for a session.
        DEACTIVATED: The Skill returned to the not-active, registered state.
        REFUSED: The activation was refused; the reason is disclosed.
    """

    ACTIVATED = auto()

    DEACTIVATED = auto()

    REFUSED = auto()


class ActivationRefusal(Enum):
    """The deterministic refusal reasons of the activation boundary (fail-closed).

    Members:
        MALFORMED_REQUEST: The value is not a declared ActivationRequest.
        NO_SESSION: The request carries no session identity; activation is
            per-session (RFC-0002 §2.2).
        NOT_REGISTERED: The value is not a loaded, registered Skill; an
            unauthenticated/unregistered Skill is never substituted (RFC-0002
            §4.7).
        ALREADY_ACTIVE: The session already has this Skill active; double
            activation is refused (per-session).
        NOT_ACTIVE: Deactivation of an activation that is not ACTIVE is an
            illegal transition (reversible — nothing to reverse).
        IDENTITY_MISMATCH: The carried activation is bound to a different
            session or a different Skill identity; no cross-session
            deactivation and no silent substitution.
        POLICY_DENIED: The injected Policy decision was missing or refused
            (RFC-0008; SK5).
    """

    MALFORMED_REQUEST = "malformed-request"

    NO_SESSION = "no-session"

    NOT_REGISTERED = "not-registered"

    ALREADY_ACTIVE = "already-active"

    NOT_ACTIVE = "not-active"

    IDENTITY_MISMATCH = "identity-mismatch"

    POLICY_DENIED = "policy-denied"


@dataclass(frozen=True, slots=True)
class ActivationRequest:
    """The per-session ask: bind a session identity to a loaded Skill.

    Activation is per-session (RFC-0002 §2.2): this request names the session
    the Skill is being made usable in. The session handle is `core`'s session
    scope, carried here opaquely — this module never opens a session, only
    binds the identity.

    Attributes:
        session: The session identity the activation is for; must be a
            non-None value (per-session, RFC-0002 §2.2).
        skill: The loaded, registered Skill to activate.
    """

    session: object
    skill: Skill


@dataclass(frozen=True, slots=True)
class Activation:
    """The per-session activation record; grants nothing (RFC-0011 §23).

    Activation makes a validated Skill usable within a session and grants no
    authority — an activated Skill still proposes (§4), carries no token, no
    approval, no permission, and no execution surface. Reversible: the same
    record transitions INACTIVE -> ACTIVE -> INACTIVE while always referring
    back to the same loaded Skill (and so to the same validated manifest and
    signature).

    Attributes:
        session: The session identity this activation is bound to.
        skill: The loaded Skill being activated for that session.
        stage: INACTIVE or ACTIVE for this session.
    """

    session: object
    skill: Skill
    stage: ActivationStage


@dataclass(frozen=True, slots=True)
class ActivationOutcome:
    """The deterministic result of an activation or deactivation attempt.

    Fail-loud (RFC-0011 §10): a refusal is explicit, deterministic, and
    disclosed, and nothing is substituted on any refusal path (RFC-0002
    §4.7).

    Attributes:
        activation: The per-session Activation record after a transition;
            None when refused.
        event: The §16 audited event (ACTIVATED / DEACTIVATED / REFUSED).
        refusal: The refusal reason when refused; None on a transition.
        reason: Why the transition applied or was refused.
    """

    activation: Activation | None
    event: ActivationEvent
    refusal: ActivationRefusal | None
    reason: str


def _refused(
    event: ActivationEvent,
    refusal: ActivationRefusal,
    reason: str,
) -> ActivationOutcome:
    return ActivationOutcome(
        activation=None,
        event=event,
        refusal=refusal,
        reason=reason,
    )


def _identity(skill: Skill) -> tuple[str, str]:
    """The Skill identity the activation binds: (name, version), §19."""
    return skill.manifest.name, skill.manifest.version


def activate(
    request: object,
    policy: Callable[[SkillManifest], ActivationVerdict] | None = None,
    current: Activation | None = None,
) -> ActivationOutcome:
    """Activate a loaded Skill for a session, per Policy (RFC-0011 §23).

    The deterministic, side-effect-free transition of the §23 lifecycle:
    take a request binding a session identity to a loaded, registered Skill
    (an unauthenticated or unregistered value is never substituted, RFC-0002
    §4.7); refuse a request with no session (per-session, RFC-0002 §2.2);
    refuse a session that is already active or bound to a different Skill
    identity (double activation and substitution are refused); gate the
    activation on the injected Policy decision (RFC-0008) — a missing or
    refused decision fails closed (SK5); and only then record the ACTIVE
    transition as the §16 audited event.

    The Policy decision is injected and never judged here (RFC-0008 §7; the
    DN-55 injected-primitive precedent), so this module decides no Policy.
    The audit *write* is `core`'s (RFC-0013 §23); the outcome carries the
    event and identity for that record.

    Args:
        request: The ActivationRequest to satisfy. Anything else is refused
            MALFORMED_REQUEST.
        policy: The injected Policy gate returning PERMITTED or REFUSED for
            the activated Skill. If omitted, the activation is refused
            POLICY_DENIED (unverified Policy, fail closed).
        current: The session's current per-session Activation, if any. A
            session already active is refused ALREADY_ACTIVE; a session bound
            to a different identity is refused IDENTITY_MISMATCH. When the
            current activation is INACTIVE and shares the identity, the
            activation is reversible (reactivation is allowed).

    Returns:
        An ActivationOutcome: the ACTIVE record (ACTIVATED) or an explicit,
        deterministic refusal with its disclosed reason.
    """
    if not isinstance(request, ActivationRequest):
        return _refused(
            ActivationEvent.REFUSED,
            ActivationRefusal.MALFORMED_REQUEST,
            "only an ActivationRequest activates a Skill (RFC-0011 §23)",
        )

    if request.session is None:
        return _refused(
            ActivationEvent.REFUSED,
            ActivationRefusal.NO_SESSION,
            "activation is per-session; a session identity is required "
            "(RFC-0011 §23; RFC-0002 §2.2)",
        )

    if not isinstance(request.skill, Skill):
        return _refused(
            ActivationEvent.REFUSED,
            ActivationRefusal.NOT_REGISTERED,
            "only a loaded, registered Skill is activated; an "
            "unauthenticated Skill is never substituted (RFC-0002 §4.7; "
            "RFC-0011 §5)",
        )

    if request.skill.stage is not SkillStage.REGISTERED:
        return _refused(
            ActivationEvent.REFUSED,
            ActivationRefusal.NOT_REGISTERED,
            "only a loaded, registered Skill is activated; a Skill outside "
            "the registry stage is never substituted (RFC-0011 §22; "
            "RFC-0002 §4.7)",
        )

    if current is not None:
        if current.session != request.session:
            return _refused(
                ActivationEvent.REFUSED,
                ActivationRefusal.IDENTITY_MISMATCH,
                "the carried activation belongs to a different session; "
                "activation is per-session (RFC-0011 §23; RFC-0002 §2.2)",
            )
        if _identity(current.skill) != _identity(request.skill):
            return _refused(
                ActivationEvent.REFUSED,
                ActivationRefusal.IDENTITY_MISMATCH,
                "this session is bound to a different Skill identity; no "
                "silent substitution (RFC-0002 §4.7; RFC-0011 §23)",
            )
        if current.stage is ActivationStage.ACTIVE:
            return _refused(
                ActivationEvent.REFUSED,
                ActivationRefusal.ALREADY_ACTIVE,
                "this session already has this Skill active; activation is "
                "per-session (RFC-0011 §23; RFC-0002 §2.2)",
            )

    if policy is None:
        return _refused(
            ActivationEvent.REFUSED,
            ActivationRefusal.POLICY_DENIED,
            "activation is Policy-gated; a missing decision fails closed "
            "(RFC-0008; RFC-0011 §23; SK5)",
        )

    if policy(request.skill.manifest) is not ActivationVerdict.PERMITTED:
        return _refused(
            ActivationEvent.REFUSED,
            ActivationRefusal.POLICY_DENIED,
            "activation is Policy-gated; the refused decision blocks the "
            "activation (RFC-0008; RFC-0011 §23; SK5)",
        )

    return ActivationOutcome(
        activation=Activation(
            session=request.session,
            skill=request.skill,
            stage=ActivationStage.ACTIVE,
        ),
        event=ActivationEvent.ACTIVATED,
        refusal=None,
        reason="activated for the session; an activated Skill still only "
        "proposes (§4) and passes the exact same gate (§24)",
    )


def deactivate(
    activation: Activation | None,
    session: object | None = None,
) -> ActivationOutcome:
    """Deactivate a per-session activation; reversible (RFC-0011 §23).

    The inverse transition of the §23 lifecycle: return an ACTIVE per-session
    activation to INACTIVE, always referring back to the same loaded Skill
    (and so to the same validated manifest and signature). Deactivation
    requires an Activation record that is ACTIVE — a not-active record is an
    illegal transition (nothing to reverse), and a record bound to a
    different session identity is refused (no cross-session deactivation).
    The deactivated record stays bound to the loaded Skill, which returns to
    the registered, not-active state (§22).

    Args:
        activation: The ACTIVE per-session Activation to reverse. Anything
            that is not an Activation is refused MALFORMED_REQUEST; an
            INACTIVE one is refused NOT_ACTIVE.
        session: The session identity to deactivate under, if known. When
            given and different from the record's bound session, the
            deactivation is refused IDENTITY_MISMATCH.

    Returns:
        An ActivationOutcome: the INACTIVE record (DEACTIVATED) or an
        explicit, deterministic refusal with its disclosed reason.
    """
    if not isinstance(activation, Activation):
        return _refused(
            ActivationEvent.REFUSED,
            ActivationRefusal.MALFORMED_REQUEST,
            "only a per-session Activation is deactivated (RFC-0011 §23)",
        )

    if session is not None and session != activation.session:
        return _refused(
            ActivationEvent.REFUSED,
            ActivationRefusal.IDENTITY_MISMATCH,
            "the session identity does not match the activation's bound "
            "session; no cross-session deactivation (RFC-0011 §23)",
        )

    if activation.stage is not ActivationStage.ACTIVE:
        return _refused(
            ActivationEvent.REFUSED,
            ActivationRefusal.NOT_ACTIVE,
            "only an ACTIVE activation is deactivated; activation is "
            "reversible (RFC-0011 §23; RFC-0002 §2.2)",
        )

    return ActivationOutcome(
        activation=Activation(
            session=activation.session,
            skill=activation.skill,
            stage=ActivationStage.INACTIVE,
        ),
        event=ActivationEvent.DEACTIVATED,
        refusal=None,
        reason="deactivated; the Skill returns to the registered, not-active "
        "state and still only proposes (§4)",
    )
