"""Deterministic structured-output validation (RFC-0010 §4, §8; RFC-0008 §5).

Owner: RFC-0010 §4 (Provider Outputs), §8 (Failure Model, PR13/PR11);
    RFC-0008 §5 (the gate's input — the Proposal and its expected effect).
Responsibility: validate the finite RFC-0010 §4 structured outputs
    (Proposal, Explanation, Questions, Clarifications, Alternative Plans,
    Refusal, Failure, Need More Evidence) as deterministic validators over
    the ``schema`` types, and apply the expected-effect rule — a Proposal is
    not complete without the expected Post-condition it claims to produce,
    so an incomplete Proposal is rejected (RFC-0010 §4 rule 2; RFC-0008 §5;
    PR13), never interpreted into validity, never classified, and never a
    Fact (F6; PR2/PR3/PR6). Validation is deterministic (RFC-0007 S7) and
    degrades, never crashes (PR11).
Forbidden responsibility: output is never a Fact (F6), never an instruction,
    never authority (PR2/PR3/PR6), never executes (PR1), never verifies
    (PR6); nothing is coerced into validity (PR13); no decision about what
    the machine is or what to do; no I/O, no vendor call, no serialization,
    no clock read, no randomness, no hidden state.
"""

from dataclasses import dataclass
from enum import Enum, auto

from episky.schema.action import Action, Plan, Proposal

__all__ = [
    "AlternativePlans",
    "Clarifications",
    "Explanation",
    "Failure",
    "NeedMoreEvidence",
    "ProviderOutputKind",
    "Questions",
    "Refusal",
    "ValidationDisposition",
    "ValidationOutcome",
    "ValidationRefusal",
    "validate",
]


class ProviderOutputKind(Enum):
    """The finite RFC-0010 §4 structured outputs, in the table's order.

    A provider returns exactly one of these; anything else is malformed
    (RFC-0010 §4, §8). The kind is the deterministic routing vocabulary:
    the Core routes each output to its deterministic consumer (RFC-0002
    §6; DN-78) — the provider package never routes.

    Members:
        PROPOSAL: A proposed Action or plan of proposed Actions, each
            carrying its expected effect — the gate's input (RFC-0008 §5).
        EXPLANATION: Human-readable justification of a Proposal.
        QUESTIONS: Requests for information the provider needs.
        CLARIFICATIONS: Restatements of the goal or evidence.
        ALTERNATIVE_PLANS: One or more distinct courses of action.
        REFUSAL: A plain statement that the provider will not do the
            asked-for thing.
        FAILURE: A report that the provider could not complete the request.
        NEED_MORE_EVIDENCE: A request for additional Facts or inspection.
    """

    PROPOSAL = auto()
    EXPLANATION = auto()
    QUESTIONS = auto()
    CLARIFICATIONS = auto()
    ALTERNATIVE_PLANS = auto()
    REFUSAL = auto()
    FAILURE = auto()
    NEED_MORE_EVIDENCE = auto()


class ValidationDisposition(Enum):
    """Whether a value conforms to the contract or is rejected (PR13).

    Members:
        CONFORMS: The value is a valid instance of one finite §4 output.
        REJECTED: No usable output is produced; the refusal is disclosed.
    """

    CONFORMS = auto()
    REJECTED = auto()


class ValidationRefusal(Enum):
    """The deterministic rejection reasons, disclosed not silent (RFC-0001 §8.12).

    Members:
        MALFORMED: The value is not a valid contract output (RFC-0010 §4,
            §8; PR13) — never interpreted into validity.
        INCOMPLETE_PROPOSAL: A Proposal lacks its expected effect and is
            not classifiable (RFC-0010 §4 rule 2; RFC-0008 §5).
    """

    MALFORMED = auto()
    INCOMPLETE_PROPOSAL = auto()


@dataclass(frozen=True, slots=True)
class Explanation:
    """Human-readable justification of a Proposal, for the Operator (RFC-0010 §4).

    Advisory content only: text to read, never a Fact, never a command,
    never an authority (RFC-0010 §2; PR1/PR2/PR3).

    Attributes:
        text: The justification text.
    """

    text: str


@dataclass(frozen=True, slots=True)
class Questions:
    """Requests for information the provider needs to continue reasoning (RFC-0010 §4).

    Advisory content only: nothing a question asks is executed, and no
    question grants the provider anything (RFC-0010 §2; PR1/PR2).

    Attributes:
        questions: The requests for information.
    """

    questions: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class Clarifications:
    """Restatements of the goal or evidence, checking understanding (RFC-0010 §4).

    Advisory content only; a restatement is data, never a claim about the
    machine (RFC-0010 §2; PR3).

    Attributes:
        statements: The restatements.
    """

    statements: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class AlternativePlans:
    """One or more distinct courses of action, for the Operator to choose (RFC-0010 §4).

    Each alternative is a Proposal over the ``schema`` types and must carry
    its expected effect like any Proposal (RFC-0010 §4 rule 2; RFC-0008 §5);
    an alternative without one is rejected. Advisory content only: no
    alternative is approved, executed, or verified here (RFC-0010 §2; PR1).

    Attributes:
        alternatives: The distinct courses of action, as Proposals.
    """

    alternatives: tuple[Proposal, ...]


@dataclass(frozen=True, slots=True)
class Refusal:
    """A plain statement that the provider will not do the asked-for thing.

    A first-class §4 output, not a defect (RFC-0010 §4 rule 4); it is a
    report the Core presents, never a verdict and never an instruction
    (PR1/PR6).

    Attributes:
        reason: The provider's statement of refusal.
    """

    reason: str


@dataclass(frozen=True, slots=True)
class Failure:
    """A report that the provider could not complete the request (RFC-0010 §4).

    A first-class output, not a defect (RFC-0010 §4 rule 4); it degrades,
    never crashes (PR11), and never changes the machine (PR5).

    Attributes:
        report: The provider's report of the failure.
    """

    report: str


@dataclass(frozen=True, slots=True)
class NeedMoreEvidence:
    """A request for additional Facts or inspection before reasoning further.

    A first-class §4 output (RFC-0010 §4). Advisory content only: the
    request names nothing the provider may see beyond the Provider View
    (RFC-0010 §11; PR14) and grants nothing (PR2).

    Attributes:
        request: The provider's request for more evidence.
    """

    request: str


@dataclass(frozen=True, slots=True)
class ValidationOutcome:
    """The deterministic result of validating a value against the contract.

    A rejected outcome produces no result: nothing is coerced into
    validity (PR13), nothing is a Fact (F6), nothing executes (PR1), and
    nothing is approved or verified (PR2/PR3/PR6).

    Attributes:
        kind: The finite §4 output the value conforms to, or None when
            rejected (a malformed value is none of the finite kinds).
        output: The validated contract-shaped result (a carrier or a
            ``schema.Proposal``), or None when rejected.
        disposition: CONFORMS or REJECTED.
        refusal: The deterministic rejection reason, None when it conforms.
        reason: Why the value conformed or was rejected (fail-loud).
    """

    kind: ProviderOutputKind | None
    output: object | None
    disposition: ValidationDisposition
    refusal: ValidationRefusal | None
    reason: str


def validate(value: object) -> ValidationOutcome:
    """Validate a provider-returned value against the RFC-0010 §4 contract.

    A pure, deterministic classifier over the finite structured outputs: it
    determines which (if any) of the eight §4 kinds a value conforms to —
    the textual outputs by their contract carriers, Proposals over the
    ``schema`` types (RFC-0008 §5) — and applies the expected-effect rule
    (an incomplete Proposal is rejected, PR13). A value that is none of the
    finite outputs is malformed and yields no result (PR13). The validation
    never interprets anything into validity, never produces a Fact (F6),
    never executes, approves, or verifies (PR1/PR2/PR3/PR6), and degrades
    — never crashes — on any unexpected input (PR11). No I/O, no vendor
    call, no clock read, no randomness, no hidden state.

    Args:
        value: The value a provider returned, to be validated.

    Returns:
        The ValidationOutcome: the finite kind and the validated
        contract-shaped result, or the explicit rejection disclosing why
        no result was produced.
    """
    try:
        if isinstance(value, Proposal):
            return _validate_proposal(value)
        if isinstance(value, Explanation):
            return _accept(ProviderOutputKind.EXPLANATION, value)
        if isinstance(value, Questions):
            return _accept(ProviderOutputKind.QUESTIONS, value)
        if isinstance(value, Clarifications):
            return _accept(ProviderOutputKind.CLARIFICATIONS, value)
        if isinstance(value, AlternativePlans):
            return _validate_alternatives(value)
        if isinstance(value, Refusal):
            return _accept(ProviderOutputKind.REFUSAL, value)
        if isinstance(value, Failure):
            return _accept(ProviderOutputKind.FAILURE, value)
        if isinstance(value, NeedMoreEvidence):
            return _accept(ProviderOutputKind.NEED_MORE_EVIDENCE, value)
        return _reject(
            None,
            ValidationRefusal.MALFORMED,
            "not one of the finite RFC-0010 §4 outputs (PR13)",
        )
    except Exception:
        return _reject(
            None,
            ValidationRefusal.MALFORMED,
            "an unexpected value degrades to a rejection, never a crash (PR11)",
        )


def _validate_proposal(proposal: Proposal) -> ValidationOutcome:
    """Validate a Proposal over the ``schema`` types (RFC-0008 §5).

    A Proposal's candidate is an Action or a Plan (RFC-0003 §2.6); either
    must carry its expected Post-condition — an Action through non-empty
    ``verification_criteria`` (RFC-0006 §5), a Plan through at least one
    Step — or the Proposal is incomplete and is rejected (RFC-0010 §4 rule
    2; RFC-0008 §5; PR13). No result is produced for an incomplete or
    malformed Proposal (PR13).
    """
    candidate = proposal.candidate
    if isinstance(candidate, Action):
        if not candidate.verification_criteria:
            return _reject(
                ProviderOutputKind.PROPOSAL,
                ValidationRefusal.INCOMPLETE_PROPOSAL,
                "a Proposal is incomplete without its expected effect "
                "(RFC-0010 §4 rule 2; RFC-0008 §5)",
            )
        return _accept(ProviderOutputKind.PROPOSAL, proposal)
    if isinstance(candidate, Plan):
        if not candidate.steps:
            return _reject(
                ProviderOutputKind.PROPOSAL,
                ValidationRefusal.INCOMPLETE_PROPOSAL,
                "a Proposal is incomplete without its expected effect "
                "(RFC-0010 §4 rule 2; RFC-0008 §5)",
            )
        return _accept(ProviderOutputKind.PROPOSAL, proposal)
    return _reject(
        None,
        ValidationRefusal.MALFORMED,
        "a Proposal's candidate is an Action or a Plan (RFC-0003 §2.6)",
    )


def _validate_alternatives(alternatives: AlternativePlans) -> ValidationOutcome:
    """Validate an Alternative Plans output (RFC-0010 §4).

    Each distinct course of action is a Proposal and must carry its
    expected effect like any Proposal (RFC-0010 §4 rule 2; RFC-0008 §5);
    an alternative that is not a Proposal is malformed, and an alternative
    without its expected effect makes the whole output incomplete (PR13).
    """
    for alternative in alternatives.alternatives:
        if not isinstance(alternative, Proposal):
            return _reject(
                ProviderOutputKind.ALTERNATIVE_PLANS,
                ValidationRefusal.MALFORMED,
                "an alternative course of action is a Proposal (RFC-0010 §4)",
            )
        result = _validate_proposal(alternative)
        if result.disposition is ValidationDisposition.REJECTED:
            return _reject(
                ProviderOutputKind.ALTERNATIVE_PLANS,
                result.refusal,
                "an alternative course of action is incomplete without its "
                "expected effect (RFC-0010 §4 rule 2)",
            )
    return _accept(ProviderOutputKind.ALTERNATIVE_PLANS, alternatives)


def _accept(kind: ProviderOutputKind, output: object) -> ValidationOutcome:
    """Build a conforming outcome for a valid §4 output."""
    return ValidationOutcome(
        kind=kind,
        output=output,
        disposition=ValidationDisposition.CONFORMS,
        refusal=None,
        reason=f"conforms to the finite RFC-0010 §4 outputs as {kind.name}",
    )


def _reject(
    kind: ProviderOutputKind | None,
    refusal: ValidationRefusal,
    reason: str,
) -> ValidationOutcome:
    """Build a rejected outcome producing no result (PR13)."""
    return ValidationOutcome(
        kind=kind,
        output=None,
        disposition=ValidationDisposition.REJECTED,
        refusal=refusal,
        reason=reason,
    )
