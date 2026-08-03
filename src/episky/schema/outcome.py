"""Verification Outcome vocabulary.

Owner: RFC-0006 §7.
Responsibility: the verification Outcome vocabulary — all eight
    RFC-0006 §7 Outcomes.
Forbidden: no comparison logic here (that is verification.compare);
    no Goal-level Outcome (RFC-0003 §2.3 is the Core's, DN-6); no
    schema defined here (RFC-0020).
"""

from enum import Enum, auto

__all__ = ["VerificationOutcome"]


class VerificationOutcome(Enum):
    """The Outcome of a verification attempt (RFC-0006 §7).

    Exhaustive and mutually exclusive for a single comparison
    (RFC-0006 §7 rules 1–2); no silent upgrading (rule 3). The
    Goal-level Outcome (Completed / Failed / Cancelled, RFC-0003 §2.3)
    is distinct and owned by the Core (DN-6).

    Members:
        VERIFIED_SUCCESS: Observed state matches the expected Postconditions.
        VERIFIED_FAILURE: Observed state does not match; Facts are trustworthy.
        PARTIALLY_SUCCESSFUL: Some expected Postconditions are met, others not.
        NO_OBSERVABLE_CHANGE: State after execution is indistinguishable from before.
        UNKNOWN: Verification could not be completed.
        CONTRADICTED: Observed Facts contradict the expected Postconditions,
            or each other.
        INTERRUPTED: Verification was halted before Compare.
        EXPIRED: The freshness window closed before Compare.
    """

    VERIFIED_SUCCESS = auto()
    VERIFIED_FAILURE = auto()
    PARTIALLY_SUCCESSFUL = auto()
    NO_OBSERVABLE_CHANGE = auto()
    UNKNOWN = auto()
    CONTRADICTED = auto()
    INTERRUPTED = auto()
    EXPIRED = auto()
