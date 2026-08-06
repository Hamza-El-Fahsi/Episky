"""Deterministic risk classification (RFC-0008 §6; RFC-0002 invariant 7).

Owner: RFC-0008 §6 (risk classification), §13 (P2, P3, P4); RFC-0007
    §5.1 (meet precedent); ratified decision notes DN-46 (input is
    ``schema.Action`` + a referenced-Fact set), DN-47 (internal canonical
    risk-property vocabulary; the ``systemmodel``/State-Domain edge stays
    latent), DN-53 (an elevation risk-property makes the class at least
    Consequential), DN-54 (a Plan's class is the meet of its Steps'
    classes).
Responsibility: the four §6 Risk Classes and four Gates, the canonical
    risk-property vocabulary (DN-47), the deterministic membership-test
    classification over an Action's declared risk properties — never the
    proposer's words (RFC-0002 invariant 7; §13 P2) — the meet rule for
    Plans (§6; RFC-0007 §5.1; DN-54), and the carried, never re-derived
    gate (§13 P4).
Forbidden responsibility: never classifies by the proposer's
    characterization, a percentage, a probability, or a score (P2/I-7);
    never auto-permits on uncertainty — an unclassified Action, an
    unknown property, or a classification error is blocked and disclosed,
    never auto-permitted (§13 P3); never executes and never reads raw
    untrusted text to classify against (RFC-0007 T2); no I/O, no runtime
    state, no persistence, no elevation mechanism (that is
    ``executor``'s, RFC-0008 §8; DN-53); the ``systemmodel`` edge stays
    latent (DN-47). Deterministic: the same Action and Facts always
    classify the same way.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from functools import reduce
from types import MappingProxyType

from episky.schema.action import Action, Plan
from episky.schema.fact import Fact

__all__ = [
    "Classification",
    "Gate",
    "PlanClassification",
    "RISK_PROPERTIES",
    "RiskClass",
    "classify",
    "classify_plan",
    "meet",
]


class RiskClass(Enum):
    """The four risk classes of RFC-0008 §6, in the table's order.

    ``value`` encodes the class in the risk order with the **most
    restrictive first** — Destructive at the top — so the meet (the most
    restrictive of a set, §6; RFC-0007 §5.1) is the minimum value, and
    "at least Consequential" (RFC-0008 §8; DN-53) is a value bound
    (``<= CONSEQUENTIAL``). A class is a property of one Action, never
    of a proposer (RFC-0002 invariant 7).

    Members:
        READ_ONLY: Observes machine state; changes nothing; runs through
            the Diagnostics contract (RFC-0004 A4).
        BENIGN: Mutates state recoverably and narrowly — within one
            user-owned or session-relevant surface; reversible;
            deterministic verification available.
        CONSEQUENTIAL: Mutates state that affects system behavior
            broadly, or is slow or uncertain to reverse: system-wide
            configuration, services, network, boot-affecting, or
            anything requiring elevation.
        DESTRUCTIVE: Irrecoverable or security-critical: erasure, boot
            or security-state damage, mass package removal, anything
            that can strand or lock out the system.
    """

    READ_ONLY = 4
    BENIGN = 3
    CONSEQUENTIAL = 2
    DESTRUCTIVE = 1


class Gate(Enum):
    """The four gates of RFC-0008 §6, in the table's order.

    The gate is a **carried** field of a classification — decided before
    presentation and never re-derived by it or by the Operator's response
    (§13 P4). The §6 "silent" and "notify" words are presentation faces
    of ``AUTO_PERMITTED``, owned by the interface (RFC-0015), not gates
    of their own.

    Members:
        AUTO_PERMITTED: Runs without a per-case decision — a read-only
            Action inside the read-only allowlist (RFC-0008 §6).
        CONFIRM: The Operator confirms before execution.
        CONFIRM_WITH_WARNING: The Operator confirms, shown the warning
            grounds carried with the classification.
        BLOCKED: Not executable by default; proceeds only by explicit,
            audited override (§13 P10).
    """

    AUTO_PERMITTED = "auto-permitted"
    CONFIRM = "confirm"
    CONFIRM_WITH_WARNING = "confirm-with-warning"
    BLOCKED = "blocked"


# The canonical risk-property vocabulary (DN-47): the deterministic
# property names RFC-0008 §6 lists, as they appear on
# ``schema.Action.risk_properties``. A class is a membership test over
# this set — no percentage, probability, score, or proposer word (P2).
# The name -> State-Domain semantics is RFC-0021's (Draft) and stays
# latent (DN-47).
RISK_PROPERTIES: frozenset[str] = frozenset(
    {
        "mutates",
        "reads",
        "touches-packages",
        "touches-services",
        "touches-configuration",
        "touches-network",
        "touches-users",
        "touches-storage",
        "touches-security-state",
        "uses-elevation",
        "reversible",
        "boot-affecting",
        "auth-affecting",
    }
)

# One gate per class (§13 P3; RFC-0008 §6 table). Read-only carries
# ``confirm`` here — the gate under the default-empty read-only
# allowlist (RFC-0008 §16; Q7); the allowlist-dependent auto-permit is
# policy content for ``policy/policy.py`` (RFC-0020's contents).
_CLASS_GATES: Mapping[RiskClass, Gate] = MappingProxyType(
    {
        RiskClass.READ_ONLY: Gate.CONFIRM,
        RiskClass.BENIGN: Gate.CONFIRM,
        RiskClass.CONSEQUENTIAL: Gate.CONFIRM_WITH_WARNING,
        RiskClass.DESTRUCTIVE: Gate.BLOCKED,
    }
)

# Subsystems whose mutation affects system behavior broadly (§6: "system
# services, system-wide configuration, network settings, users").
_SYSTEM_WIDE_TOUCHES = frozenset(
    {
        "touches-configuration",
        "touches-services",
        "touches-network",
        "touches-users",
    }
)


@dataclass(frozen=True, slots=True)
class Classification:
    """The deterministic result of classifying one Action (RFC-0008 §6).

    The risk class, the carried gate (§13 P4), the warning grounds for a
    confirm-with-warning gate or the reason for a blocked gate, and the
    deterministic inputs the classification was computed from — the
    Action and its referenced Facts (DN-46). When the Action cannot be
    classified, ``risk_class`` is ``None`` and the gate is blocked:
    unclassified is blocked and disclosed, never auto-permitted (§13 P3).
    Frozen and slot-based: the record is immutable and in-memory only.

    Attributes:
        risk_class: The risk class, or ``None`` when unclassifiable
            (§13 P3).
        gate: The carried gate, decided at classification time (§13 P4).
        action: The Action that was classified (a deterministic input).
        facts: The referenced-Fact set passed at the entry (DN-46).
        warning_grounds: Why the gate is confirm-with-warning; populated
            only for ``Gate.CONFIRM_WITH_WARNING``.
        reason: Why the outcome is blocked; populated only for
            ``Gate.BLOCKED``.
    """

    risk_class: RiskClass | None
    gate: Gate
    action: Action
    facts: tuple[Fact, ...] = ()
    warning_grounds: str | None = None
    reason: str | None = None


@dataclass(frozen=True, slots=True)
class PlanClassification:
    """The deterministic result of classifying a Plan (RFC-0008 §6, §11).

    A Plan's class is the meet of its Steps' classes — the most
    restrictive among them (RFC-0008 §6; RFC-0007 §5.1; DN-54) — with
    each Step's own class and gate carried so the whole is shown per
    Step (§11). If any Step is unclassifiable, the Plan fails closed:
    blocked and disclosed, never auto-permitted (§13 P3).
    Frozen and slot-based: the record is immutable and in-memory only.

    Attributes:
        risk_class: The meet of the Steps' classes, or ``None`` when a
            Step (or the empty Plan) is unclassifiable (§13 P3).
        gate: The carried gate for the meet class (§13 P4).
        steps: Each Step's own classification, in Plan order.
        warning_grounds: Why the gate is confirm-with-warning; populated
            only for ``Gate.CONFIRM_WITH_WARNING``.
        reason: Why the outcome is blocked; populated only for
            ``Gate.BLOCKED``.
    """

    risk_class: RiskClass | None
    gate: Gate
    steps: tuple[Classification, ...]
    warning_grounds: str | None = None
    reason: str | None = None


def meet(a: RiskClass, b: RiskClass) -> RiskClass:
    """The meet (∧) of two risk classes — the most restrictive (§6).

    A Plan takes the most restrictive class of its Steps (Destructive ∧
    Read-only = Destructive), mirroring the trust lattice meet
    (RFC-0007 §5.1; DN-54).

    Args:
        a: A risk class.
        b: A risk class.

    Returns:
        The more restrictive of ``a`` and ``b``.
    """
    return a if a.value <= b.value else b


def _membership(props: frozenset[str]) -> tuple[RiskClass | None, str]:
    """The §6 membership test: one class for a property set, or a
    fail-closed reason.

    Deterministic and content-independent (P2): only the canonical
    property names are read. An ambiguous set — mutation and read
    together, or touches-without-a-read-or-mutate axis — has no class:
    the caller fails it closed (§13 P3).

    Args:
        props: The Action's declared risk properties (already validated
            against RISK_PROPERTIES).

    Returns:
        ``(risk_class, grounds)`` where ``grounds`` names the §6 rule for
        the class, or ``(None, reason)`` when the set is unclassifiable.
    """
    mutates = "mutates" in props
    reads = "reads" in props
    if mutates and reads:
        return None, (
            "declares both mutation and read-only; an Action either "
            "mutates a State Domain or only reads it (RFC-0008 §6; §13 P3)"
        )
    if not mutates and not reads:
        if not props:
            return None, "no risk properties declared (RFC-0008 §6; §13 P3)"
        return None, (
            "touches subsystems without declaring mutation or read "
            "(RFC-0008 §6; §13 P3)"
        )
    if mutates:
        if "touches-security-state" in props:
            return RiskClass.DESTRUCTIVE, (
                "mutates security state (RFC-0008 §6: Destructive)"
            )
        if "boot-affecting" in props:
            return RiskClass.DESTRUCTIVE, (
                "could prevent the machine from booting (RFC-0008 §6: Destructive)"
            )
        if "auth-affecting" in props:
            return RiskClass.DESTRUCTIVE, (
                "could prevent authenticating or lock out the Operator "
                "(RFC-0008 §6: Destructive)"
            )
        if "reversible" not in props:
            if "touches-storage" in props:
                return RiskClass.DESTRUCTIVE, (
                    "irrecoverable storage change (RFC-0008 §6: Destructive)"
                )
            if "touches-packages" in props:
                return RiskClass.DESTRUCTIVE, (
                    "irrecoverable package change (RFC-0008 §6: Destructive)"
                )
            return RiskClass.CONSEQUENTIAL, (
                "mutation is slow or uncertain to reverse (RFC-0008 §6: Consequential)"
            )
        if "uses-elevation" in props:
            return RiskClass.CONSEQUENTIAL, (
                "uses the machine's elevation mechanism (RFC-0008 §8; "
                "DN-53: at least Consequential)"
            )
        if props & _SYSTEM_WIDE_TOUCHES:
            return RiskClass.CONSEQUENTIAL, (
                "mutates a system-wide subsystem (RFC-0008 §6: Consequential)"
            )
        return RiskClass.BENIGN, ""
    if "uses-elevation" in props:
        return RiskClass.CONSEQUENTIAL, (
            "uses the machine's elevation mechanism (RFC-0008 §8; "
            "DN-53: at least Consequential)"
        )
    return RiskClass.READ_ONLY, ""


def classify(action: Action, facts: tuple[Fact, ...] = ()) -> Classification:
    """Classify one Action deterministically (RFC-0008 §6; DN-46).

    Pure and deterministic (P2): the class is a membership test over the
    Action's declared risk properties and the referenced-Fact set passed
    at the entry; the description and the proposer's words are never
    read (RFC-0002 invariant 7). The gate is derived once, from the
    class, and carried in the result (§13 P4). An unknown property, an
    ambiguous property set, or an unclassifiable Action is blocked and
    disclosed, never auto-permitted (§13 P3).

    Args:
        action: The Action to classify (the atomic approval unit,
            RFC-0008 §5).
        facts: The referenced-Fact set the classification is built on
            (DN-46), carried as a deterministic input.

    Returns:
        The Classification: the risk class (or ``None`` when
        unclassifiable), the carried gate, and the warning grounds or
        reason.
    """
    declared = frozenset(action.risk_properties)
    unknown = declared - RISK_PROPERTIES
    if unknown:
        name = sorted(unknown)[0]
        return Classification(
            risk_class=None,
            gate=Gate.BLOCKED,
            action=action,
            facts=facts,
            reason=(f"unknown risk property {name!r} (RFC-0008 §13 P3; DN-47)"),
        )
    risk_class, grounds = _membership(declared)
    if risk_class is None:
        return Classification(
            risk_class=None,
            gate=Gate.BLOCKED,
            action=action,
            facts=facts,
            reason=grounds,
        )
    gate = _CLASS_GATES[risk_class]
    if gate is Gate.CONFIRM_WITH_WARNING:
        return Classification(
            risk_class=risk_class,
            gate=gate,
            action=action,
            facts=facts,
            warning_grounds=grounds,
        )
    if gate is Gate.BLOCKED:
        return Classification(
            risk_class=risk_class,
            gate=gate,
            action=action,
            facts=facts,
            reason=grounds,
        )
    return Classification(
        risk_class=risk_class,
        gate=gate,
        action=action,
        facts=facts,
    )


def classify_plan(plan: Plan, facts: tuple[Fact, ...] = ()) -> PlanClassification:
    """Classify a Plan by the meet rule (RFC-0008 §6; RFC-0007 §5.1; DN-54).

    Each Step's Action is classified with the referenced-Fact set passed
    at the entry (Step preconditions are the Plan view and are not
    re-derived here, DN-46); the Plan's class is the meet — the most
    restrictive — of its Steps' classes. An empty Plan, or a Plan with an
    unclassifiable Step, fails closed: blocked and disclosed, never
    auto-permitted (§13 P3).

    Args:
        plan: The Plan to classify (the envelope unit, RFC-0008 §11).
        facts: The referenced-Fact set, carried into each Step's
            classification (DN-46).

    Returns:
        The PlanClassification: the meet class (or ``None`` when
        unclassifiable), the carried gate, and each Step's own
        classification.
    """
    steps = tuple(classify(step.action, facts) for step in plan.steps)
    if not steps:
        return PlanClassification(
            risk_class=None,
            gate=Gate.BLOCKED,
            steps=steps,
            reason=(
                "an empty Plan has no Steps to classify; default deny "
                "(RFC-0008 §7; §13 P3)"
            ),
        )
    if any(step.risk_class is None for step in steps):
        return PlanClassification(
            risk_class=None,
            gate=Gate.BLOCKED,
            steps=steps,
            reason=(
                "a Step is unclassifiable; the Plan fails closed (RFC-0008 §13 P3)"
            ),
        )
    plan_class = reduce(meet, (step.risk_class for step in steps))
    gate = _CLASS_GATES[plan_class]
    if gate is Gate.CONFIRM_WITH_WARNING:
        return PlanClassification(
            risk_class=plan_class,
            gate=gate,
            steps=steps,
            warning_grounds=(
                "Plan class is the meet of its Steps' classes: "
                f"{plan_class.name} (RFC-0008 §6; RFC-0007 §5.1)"
            ),
        )
    if gate is Gate.BLOCKED:
        return PlanClassification(
            risk_class=plan_class,
            gate=gate,
            steps=steps,
            reason=(
                "Plan class is the meet of its Steps' classes: "
                f"{plan_class.name} (RFC-0008 §6; RFC-0007 §5.1; §13 P10)"
            ),
        )
    return PlanClassification(
        risk_class=plan_class,
        gate=gate,
        steps=steps,
    )
