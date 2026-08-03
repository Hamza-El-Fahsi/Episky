"""Action / Step / Proposal / Plan types.

Owner: RFC-0003 §2.6 (Action/Step/Proposal/Plan); RFC-0006 §5
    (Postconditions, decision note DN-4).
Forbidden: no behavior, no execution, no schema (RFC-0020).
"""

from dataclasses import dataclass

from .fact import Fact, Freshness, Property, Subject, Value

__all__ = ["Action", "Plan", "PostCondition", "Proposal", "Step"]


@dataclass(frozen=True, slots=True)
class PostCondition:
    """Expected machine state after an Action (RFC-0006 §5).

    Expressed in the same vocabulary as Facts: a Subject, a Property,
    an expected Status, and a freshness bound (RFC-0006 §5). State,
    not implementation. ``expected_value`` is the expected Status as
    the canonical ``Value`` (RFC-0005 §3). Pure data (DN-4).

    Attributes:
        subject: The Subject the expectation is about.
        property: The Property of the Subject being asserted.
        expected_value: The value the Property must have after the Action.
        freshness: The freshness state the check must find.
    """

    subject: Subject
    property: Property
    expected_value: Value
    freshness: Freshness


@dataclass(frozen=True, slots=True)
class Action:
    """The atomic unit of work (RFC-0003 §2.6; RFC-0008 §5).

    Carries a description, risk-relevant properties, and verification
    criteria, bound to one change to the machine. A shell string is
    an implementation, never the Action itself — no command field
    exists. The verification criteria are the expected Postconditions
    (RFC-0006 §5).

    Attributes:
        description: The Action's description.
        risk_properties: Canonical risk-relevant property names (RFC-0008 §6).
        verification_criteria: The Postconditions the executed Action must
            satisfy (RFC-0006 §5).
    """

    description: str
    risk_properties: tuple[str, ...]
    verification_criteria: tuple[PostCondition, ...]


@dataclass(frozen=True, slots=True)
class Step:
    """One element of a Plan (RFC-0003 §2.6; RFC-0008 §5).

    An Action positioned in sequence with its preconditions, expected
    Post-condition, and verification method. Preconditions are Facts
    that must hold before execution may begin (RFC-0006 §4).

    Attributes:
        action: The Action this Step applies.
        preconditions: Facts that must hold before the Action runs.
        postcondition: The expected Post-condition to confirm.
        verification_method: How the Post-condition is confirmed.
    """

    action: Action
    preconditions: tuple[Fact, ...]
    postcondition: PostCondition
    verification_method: str


@dataclass(frozen=True, slots=True)
class Plan:
    """A goal-scoped, ordered set of Steps (RFC-0003 §2.6).

    Normalized into discrete proposed Actions, subject to
    classification and Approval. Planning never executes (RFC-0002
    invariant 3). The tuple preserves order; the Goal (RFC-0003 §2.3)
    is the Core's.
    """

    steps: tuple[Step, ...]


@dataclass(frozen=True, slots=True)
class Proposal:
    """A candidate Action or Plan (RFC-0003 §2.6).

    Offered by the LLM, a Skill, or the Core for consideration; not
    yet classified, approved, or executed. Carries no approval state
    and no execution capability.
    """

    candidate: Action | Plan
