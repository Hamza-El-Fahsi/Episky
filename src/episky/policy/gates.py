"""Gates per risk class (RFC-0008 §6; RFC-0001 §5).

Owner: RFC-0008 §6 (the class→gate table), §7 (gate evaluation), §13 (P4);
    RFC-0001 §5 (one gate per class).
Responsibility: the §6 class→gate table as data and the deterministic
    gate lookup — (class, allowlist membership) → gate — so every Action
    is carried by exactly one gate (§13 P4) and a Blocked Action is never
    loosened (RFC-0004 §9.7).
Forbidden responsibility: never decides who may approve or whether an
    approval is granted (RFC-0004 §7 — the Policy Engine has no Approve
    authority); never reads the proposer's words (RFC-0002 invariant 7;
    §13 P2); no I/O, no state, no execution, no persistence.
"""

from collections.abc import Mapping
from types import MappingProxyType

from episky.policy.classify import Gate, RiskClass

__all__ = ["ALLOWLISTED_READ_ONLY_GATE", "CLASS_GATES", "gate_for"]

# The §6 class→gate table, transcribed exactly (RFC-0008 §6). A read-only
# Action is auto-permitted iff it is inside the read-only allowlist
# (ALLOWLISTED_READ_ONLY_GATE); otherwise its gate is confirm — the entry
# here is that default (the allowlist contents are RFC-0020's, §16).
CLASS_GATES: Mapping[RiskClass, Gate] = MappingProxyType(
    {
        RiskClass.READ_ONLY: Gate.CONFIRM,
        RiskClass.BENIGN: Gate.CONFIRM,
        RiskClass.CONSEQUENTIAL: Gate.CONFIRM_WITH_WARNING,
        RiskClass.DESTRUCTIVE: Gate.BLOCKED,
    }
)

# The gate a read-only Action receives when it is inside the read-only
# allowlist (RFC-0008 §6): auto-permitted. Auto-permission is per-Action —
# each allowlisted read-only Action still receives its own fresh token at
# its own execution boundary (§8); it is never a reusable pass
# (RFC-0001 §8.3).
ALLOWLISTED_READ_ONLY_GATE: Gate = Gate.AUTO_PERMITTED


def gate_for(risk_class: RiskClass, allowlisted: bool = False) -> Gate:
    """The §6 gate for a risk class (RFC-0008 §6; §13 P4).

    Deterministic and content-independent: only the class and the
    allowlist-membership flag are read, never the proposer's words
    (RFC-0002 invariant 7). A Blocked Action stays blocked whether or not
    it is allowlisted — nothing here loosens the Operator's bounds
    (RFC-0004 §9.7).

    Args:
        risk_class: The risk class to gate.
        allowlisted: Whether the Action is inside the read-only allowlist;
            meaningful only for ``RiskClass.READ_ONLY``.

    Returns:
        The §6 gate: auto-permitted for an allowlisted read-only Action,
        confirm for Read-only/Benign, confirm-with-warning for
        Consequential, blocked for Destructive.

    Raises:
        ValueError: If ``risk_class`` is not a ``RiskClass`` — a
            non-class is never given a gate (fail closed, §13 P3).
    """
    if not isinstance(risk_class, RiskClass):
        raise ValueError("gate_for requires a RiskClass (RFC-0008 §6; §13 P3)")
    if risk_class is RiskClass.READ_ONLY and allowlisted:
        return ALLOWLISTED_READ_ONLY_GATE
    return CLASS_GATES[risk_class]
