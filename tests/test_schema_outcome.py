"""Type-level conformance tests for the RFC-0006 §7 Outcome vocabulary.

The eight Outcomes are exhaustive and mutually exclusive (RFC-0006 §7
rules 1–2); the Goal-level Outcome (RFC-0003 §2.3) is absent (DN-6).
"""

import episky.schema.outcome
from episky.schema.outcome import VerificationOutcome


def test_verification_outcome_has_exactly_eight_members():
    assert len(VerificationOutcome) == 8


def test_verification_outcome_members_match_rfc_0006_section_7():
    expected = {
        "VERIFIED_SUCCESS",
        "VERIFIED_FAILURE",
        "PARTIALLY_SUCCESSFUL",
        "NO_OBSERVABLE_CHANGE",
        "UNKNOWN",
        "CONTRADICTED",
        "INTERRUPTED",
        "EXPIRED",
    }
    assert {member.name for member in VerificationOutcome} == expected


def test_verification_outcome_is_exhaustive_and_mutually_exclusive():
    assert len(set(VerificationOutcome)) == 8
    assert len({member.value for member in VerificationOutcome}) == 8


def test_no_goal_outcome_is_exported():
    assert episky.schema.outcome.__all__ == ["VerificationOutcome"]
    assert not hasattr(episky.schema.outcome, "GoalOutcome")
