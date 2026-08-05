"""Deterministic Outcome determination.

Owner: RFC-0006 §7 (rules 1–5; V5, V6, V9, V14, V15), §10, §11, §13;
    ratified decision notes DN-27, DN-30, DN-31, DN-34.
Responsibility: the Outcome step over the Compare result — given the
    per-Postcondition verdicts, determine exactly one of the RFC-0006
    §7 Outcomes by the strictest-wins precedence (§7 rule 2), report it
    verbatim without silent upgrading (§7 rule 3), and carry the Facts
    that determined it (rule 4, V11). Scope follows the compared
    Postconditions (§11); an Outcome is only as valid as the Facts it
    was determined from, and re-collection after staleness is the
    runtime's, never this module (§10, V4; DN-31). Read-only and pure
    (V8): nothing is mutated and nothing is written to the Fact store
    (DN-27).
Forbidden responsibility: never inspects raw Facts directly, never
    invokes compare(), never invokes Collect, never normalizes, never
    executes, never mutates the Fact store (V8, DN-27), never verifies
    trust, never orchestrates, never reads or writes files, never
    interacts with the runtime, never assigns a confidence level
    (DN-30), never produces Interrupted or Expired (DN-31; orchestration
    only), never claims success without fresh Facts (V5, V9).
"""

from dataclasses import dataclass

from episky.schema.fact import Fact
from episky.schema.outcome import VerificationOutcome
from episky.verification.compare import CompareResult, PostconditionVerdict

__all__ = ["OutcomeRecord", "determine"]


@dataclass(frozen=True, slots=True)
class OutcomeRecord:
    """The in-memory result of the Outcome step (RFC-0006 §7 rule 4; DN-34).

    Frozen and slot-based: the record is immutable (V8) and lives only
    in memory — durable recording, retention, and audit wiring are
    RFC-0013's (DN-34).

    Attributes:
        outcome: Exactly one of the RFC-0006 §7 Outcomes, determined by
            the strictest-wins precedence (§7 rule 2).
        evidence: The comparable Facts that determined the outcome
            (rule 4, V11), in deterministic order; empty when the
            outcome is UNKNOWN, because no Fact was comparable.
    """

    outcome: VerificationOutcome
    evidence: tuple[Fact, ...]


def determine(result: CompareResult) -> OutcomeRecord:
    """Determine the Outcome from a Compare result (RFC-0006 §7).

    Deterministic (V3): the same CompareResult always yields the same
    OutcomeRecord. Classification follows the strictest-wins precedence
    (§7 rule 2):

    - Contradicted wins over everything (V7);
    - Verified Failure wins when comparable Facts establish that the
      observed state matches none of the expected Postconditions;
    - Unknown wins over success and partial when any expected evidence
      is missing (V9) — missing evidence is never success;
    - Partially Successful is the distinct outcome for a mix of held
      and not-held Postconditions (V6);
    - Verified Success requires every declared Postcondition to hold on
      fresh Facts (V5).

    Interrupted and Expired are never produced here: they are
    orchestration outcomes (RFC-0002 §2.9; DN-31). No confidence level
    is computed or carried (DN-30; V15). The OutcomeRecord is never
    written back to the Fact store (DN-27).

    Args:
        result: The Compare step's per-Postcondition verdicts.

    Returns:
        The OutcomeRecord carrying the Outcome and the Facts that
        determined it.
    """
    verdicts = tuple(r.verdict for r in result.results)
    evidence = _gather_evidence(result)

    if not verdicts:
        outcome = VerificationOutcome.UNKNOWN
    elif PostconditionVerdict.CONTRADICTED in verdicts:
        outcome = VerificationOutcome.CONTRADICTED
    elif (
        PostconditionVerdict.NOT_HELD in verdicts
        and PostconditionVerdict.HELD not in verdicts
    ):
        outcome = VerificationOutcome.VERIFIED_FAILURE
    elif PostconditionVerdict.UNKNOWN in verdicts:
        outcome = VerificationOutcome.UNKNOWN
    elif (
        PostconditionVerdict.HELD in verdicts
        and PostconditionVerdict.NOT_HELD in verdicts
    ):
        outcome = VerificationOutcome.PARTIALLY_SUCCESSFUL
    else:
        outcome = VerificationOutcome.VERIFIED_SUCCESS
    return OutcomeRecord(outcome=outcome, evidence=evidence)


def _gather_evidence(result: CompareResult) -> tuple[Fact, ...]:
    """The comparable Facts that determined the outcome (rule 4, V11).

    The union of every verdict's evidence, in the Postconditions'
    declared order with duplicates removed — deterministic (V3).
    """
    seen: set[Fact] = set()
    evidence: list[Fact] = []
    for verdict_result in result.results:
        for fact in verdict_result.evidence:
            if fact not in seen:
                seen.add(fact)
                evidence.append(fact)
    return tuple(evidence)
