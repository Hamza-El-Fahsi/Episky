"""Skill Runtime — deterministic gate-participation boundary (RFC-0011 §24,
§12, §13, §14, §4; RFC-0008 §5, §7; RFC-0004 A3; SK4, SK11, SK12, SK6).

Owner: RFC-0011 §24 (Skill Actions pass the exact same classification and
    approval gate as any Action; no unit approval — a Skill is never
    approved as a whole, RFC-0008 §5; no skill-based shortcut; the
    proposing Skill gains no trust, authority, or power from proposing),
    §12/SK11/SK12 (declared Preconditions ride the Action and can never be
    waived — an incomplete Proposal is rejected, RFC-0008 §5), §13/SK11
    (Postconditions are declared before execution; a Proposal is not
    complete without them), §14/SK6 (the Skill declares its verification
    approach and never performs it), §4 (Skill Actions still only propose).
Responsibility: the deterministic mechanics by which a registered Skill's
    Proposal is presented at the approval gate: not approved for the Skill
    as a unit (RFC-0008 §5), but destructured into individual Actions —
    each unit carries the declared Preconditions and Postconditions
    (SK11; RFC-0011 §12/§13) and the declared verification approach
    (SK6, declaration only), and the Skill's identity or words give no
    shortcut (§24.2; RFC-0008 §7/P2). Nothing here classifies, approves,
    executes, or verifies; the units only propose (RFC-0004 A3;
    RFC-0008 §5).
Forbidden responsibility: never classifies risk or decides approval (that
    is `policy`'s, RFC-0008 §6/§7; skills consumes types only, never a
    decision path — blueprint §4.2), never executes or invokes an Action
    (RFC-0002 invariant 3; SK1), never verifies (SK6; RFC-0006), never
    modifies Policy (SK7) or Audit (SK14; RFC-0004 A7), never consults a
    Skill in a session (that is `core`'s, RFC-0002 §6; DN-81), never the
    provider↔skill interaction (DN-82 — no `providers` edge), never
    sandboxes execution (RFC-0020), performs no I/O, no clock, no
    randomness, no serialization, no hidden state, and imports no
    `secrets`/`audit`/`executor`/`verification`/`providers`/`core`.
    Deterministic and fail-closed: identical inputs always produce the
    identical SkillGate and every non-admission is loud and disclosed
    (RFC-0011 §10).
"""

from dataclasses import dataclass
from enum import Enum, auto

from episky.schema.action import Action, Plan, PostCondition, Proposal
from episky.skills.loader import Skill, SkillStage

__all__ = [
    "GateDisposition",
    "GateRefusal",
    "SkillActionUnit",
    "SkillGate",
    "admit",
]


class GateDisposition(Enum):
    """Whether a Skill's Action offering is admitted to the gate (RFC-0011 §24).

    Admission establishes only that the offering is a registered Skill's
    Proposal destructured into per-Action units; it is not classification,
    approval, or execution (RFC-0008 §5; RFC-0001 §8.6).

    Members:
        ADMITTED: Destructured into per-Action gate units; each still
            proposes and passes the same gate as any Action.
        REFUSED: The offering does not participate; the refusal is loud and
            disclosed (RFC-0011 §10).
    """

    ADMITTED = auto()

    REFUSED = auto()


class GateRefusal(Enum):
    """The deterministic refusal reasons of the gate surface (fail-closed).

    Members:
        NOT_REGISTERED: The value is not a registered Skill; an
            unauthenticated or unregistered Skill never reaches the gate
            (RFC-0002 §4.7; RFC-0011 §5).
        MALFORMED_OFFER: The offering is not a schema.Proposal — the only
            material a Skill offers (RFC-0011 §4).
        MALFORMED_CANDIDATE: The Proposal's candidate is neither an Action
            nor a Plan; nothing usable is offered.
        INCOMPLETE_EFFECT: An Action or a Plan Step carries no expected
            Postconditions — a Proposal is not complete without its
            expected effect (RFC-0008 §5; RFC-0011 §13; SK11) — or a Plan
            Step has no declared verification approach (SK6; RFC-0011 §14).
    """

    NOT_REGISTERED = "not-registered"

    MALFORMED_OFFER = "malformed-offer"

    MALFORMED_CANDIDATE = "malformed-candidate"

    INCOMPLETE_EFFECT = "incomplete-effect"


@dataclass(frozen=True, slots=True)
class SkillActionUnit:
    """One per-Action approval unit of a registered Skill's offering.

    The atomic approval unit (RFC-0008 §5) is an Action, and a Skill is
    never the bundle: RFC-0008 §5 "a Skill is never approved as a unit;
    only its individual Actions pass the gate". Each unit carries the
    declared Preconditions, the expected Postconditions, and the declared
    verification approach — declarations whose presence is checked here,
    whose content is never judged, and none of which the offering can
    waive (RFC-0011 §12/SK12).

    Attributes:
        action: The Action — the atomic approval unit.
        preconditions: The declared Preconditions that must hold (RFC-0011
            §12, SK11; riding the unit, they cannot be silently dropped).
        postconditions: The expected Postconditions, declared before
            execution (RFC-0011 §13; RFC-0006 §5; SK11).
        verification_method: The declared verification approach carried as
            a declaration, never performed (SK6).
    """

    action: Action
    preconditions: tuple[object, ...]
    postconditions: tuple[PostCondition, ...]
    verification_method: str


@dataclass(frozen=True, slots=True)
class SkillGate:
    """The deterministic result of admitting a Skill's offering.

    Attributes:
        units: The per-Action units admitted to the gate; empty when
            refused.
        disposition: ADMITTED or REFUSED.
        refusal: The refusal reason when refused; None when admitted.
        reason: Why the offering participates or was refused (fail-loud).
    """

    units: tuple[SkillActionUnit, ...]
    disposition: GateDisposition
    refusal: GateRefusal | None
    reason: str


_ADMITTED_REASON = (
    "the registered Skill's Proposal is destructured into the per-Action "
    "gate units; each still proposes and passes the same gate as any Action "
    "(RFC-0011 §24; RFC-0008 §5)"
)


def _refused(refusal: GateRefusal, reason: str) -> SkillGate:
    return SkillGate(
        units=(),
        disposition=GateDisposition.REFUSED,
        refusal=refusal,
        reason=reason,
    )


def admit(skill: object, offering: object) -> SkillGate:
    """Admit a registered Skill's Action Proposal to the gate (RFC-0011 §24).

    The deterministic gate-participation boundary: refuse any value that is
    not a registered Skill (an unregistered one never reaches the gate,
    RFC-0002 §4.7), then take the schema Proposal the Skill offers and
    destructure it into per-Action approval units — never admitting the
    Skill, or a whole Plan-as-one, as a unit (RFC-0008 §5; SK4). An Action
    (or a Plan Step) with no expected Postcondition is incomplete and is
    refused (RFC-0008 §5; SK11). Every unit carries the declared
    Preconditions (they ride the unit and cannot be replaced by the
    offering: SK12) and the declared verification approach (carried, never
    performed: SK6). No classification, approval, or execution runs here —
    classification is structural, and the Skill's identity and words give
    no consideration (RFC-0008 §7/P2).

    Args:
        skill: The registered Skill instance produced by the loader
            boundary (RFC-0011 §22). An unregistered or non-Skill value is
            refused.
        offering: The Skill's Proposal (a candidate Action or Plan). A
            non-Proposal value is refused MALFORMED_OFFER.

    Returns:
        The SkillGate: the units (ADMITTED) or the deterministic refusal.
    """
    if not isinstance(skill, Skill) or skill.stage is not SkillStage.REGISTERED:
        return _refused(
            GateRefusal.NOT_REGISTERED,
            "only a registered Skill reaches the gate (RFC-0002 §4.7; RFC-0011 §5)",
        )

    if not isinstance(offering, Proposal):
        return _refused(
            GateRefusal.MALFORMED_OFFER,
            "a Skill offers only a Proposal at the gate (RFC-0011 §4)",
        )

    candidate = offering.candidate

    if isinstance(candidate, Action):
        units = _admit_action(skill, candidate)
        if units is None:
            return _refused(
                GateRefusal.INCOMPLETE_EFFECT,
                "an Action Proposal is incomplete without its expected "
                "Postconditions (RFC-0008 §5; RFC-0011 §13; SK11)",
            )
        return SkillGate(
            units=units,
            disposition=GateDisposition.ADMITTED,
            refusal=None,
            reason=_ADMITTED_REASON,
        )

    if isinstance(candidate, Plan):
        units = _admit_plan(skill, candidate)
        if units is None:
            return _refused(
                GateRefusal.INCOMPLETE_EFFECT,
                "a Plan Step is incomplete without its expected effect, "
                "and a Step with none waives the declared Postconditions "
                "(RFC-0008 §5; RFC-0011 §13; SK11)",
            )
        return SkillGate(
            units=units,
            disposition=GateDisposition.ADMITTED,
            refusal=None,
            reason=_ADMITTED_REASON,
        )

    return _refused(
        GateRefusal.MALFORMED_CANDIDATE,
        "a Proposal's candidate is an Action or a Plan (RFC-0011 §4; RFC-0002 §3.6)",
    )


def _admit_action(skill: Skill, action: Action) -> tuple[SkillActionUnit, ...] | None:
    """One Action approval unit, incomplete if without its expected effect."""
    if not action.verification_criteria:
        return None
    return (
        SkillActionUnit(
            action=action,
            preconditions=(*skill.manifest.preconditions,),
            postconditions=(*action.verification_criteria,),
            verification_method=skill.manifest.verification,
        ),
    )


def _admit_plan(skill: Skill, plan: Plan) -> tuple[SkillActionUnit, ...] | None:
    """Destructure a Plan into per-Action units — never admitted as a unit.

    A Skill offering several Actions is not admitted as a whole: RFC-0008
    §5 never approves a Skill, only its individual Actions, so each Step
    becomes its own action approval unit (§24.1; RFC-0004 A3). Each unit is
    admitted only when the Step carries its expected Postconditions and a
    declared verification approach — a Step with neither (or an empty Plan)
    waives the declared effect and is refused (RFC-0011 §13; SK11).
    Nothing here approves a whole; the individual Actions only propose.
    """
    units: list[SkillActionUnit] = []
    for step in plan.steps:
        if not step.action.verification_criteria:
            return None
        if not step.verification_method.strip():
            return None
        units.append(
            SkillActionUnit(
                action=step.action,
                preconditions=(*skill.manifest.preconditions,),
                postconditions=(*step.action.verification_criteria,),
                verification_method=step.verification_method.strip(),
            )
        )
    return tuple(units) if units else None
