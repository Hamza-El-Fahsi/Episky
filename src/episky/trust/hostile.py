"""Hostile quarantine and fail-closed behaviour.

Owner: RFC-0007 §15 (failure behaviour, §15.5–§15.8), §13 (invariants
    T11, T12); ratified decision notes DN-39 (Hostile is produced only
    by the fail-closed paths) and Q8 (in-memory quarantine record;
    durable recording is RFC-0013's, Iteration 7). Load-bearing:
    RFC-0002 invariants 4 and 5 — made testable at this boundary, with
    the runtime enforcement belonging to `core`.
Responsibility: the in-memory Hostile quarantine — admitting only
    content already held at Hostile (fail-closed admission, §15.5;
    DN-39), recording it with its reason and withheld/disclosed state
    (§15.5–§15.8), enforcing the excluded-from-Context/Provider-View
    invariant (§15.5, T11; RFC-0002 invariant 4), and T12's downward
    contagion from a quarantined source (§9.7). In-memory only (Q8):
    nothing is written to disk or to an audit trail.
Forbidden responsibility: never produces Hostile — that is classify()'s
    and sanitize()'s deterministic fail-closed paths (DN-39) — never
    detects a hostile signal (RFC-0012 §16.6), never quarantines
    non-Hostile content, never lets a Hostile boundary hold open (§15.6,
    §15.7), never persists (RFC-0013's, Iteration 7), never executes,
    never grants authority (RFC-0004 §7), never invokes policy, never
    performs I/O, never mutates, and never depends on runtime state.
"""

from dataclasses import dataclass
from enum import Enum

from episky.trust.classes import Datum, Demotion, TrustClass

__all__ = ["DisclosureState", "Quarantine", "contaminate", "quarantine"]


class DisclosureState(Enum):
    """Whether quarantined content is shown to the Operator (RFC-0007 §15).

    Members:
        WITHHELD: The content is not shown; the Operator is told it was
            withheld and why (§15.6).
        DISCLOSED: The content is shown contained for the Operator to
            inspect (§15.5, §15.8). The presentation form is RFC-0015's
            (§16.4).
    """

    WITHHELD = "withheld"
    DISCLOSED = "disclosed"


@dataclass(frozen=True, slots=True)
class Quarantine:
    """The in-memory quarantine record for a Hostile datum (§15.5; Q8).

    The datum, its class (always Hostile), the reason it was
    quarantined, and its withheld/disclosed state. Frozen and
    slot-based: immutable and in-memory only — durable recording,
    retention, and audit wiring are RFC-0013's (Iteration 7; DN-34
    precedent). A quarantine record is, by definition, content that may
    not cross into Context or the Provider View (see ``excluded``).

    Attributes:
        datum: The quarantined datum — category, content, provenance,
            and origin (§4, DN-37).
        trust_class: The datum's class; always Hostile, the only class
            quarantine admits (DN-39).
        reason: Why the content is quarantined; the Operator is told the
            reason (§15.6), so a quarantine never withholds silently.
        disclosure: Whether the content is withheld or disclosed
            contained to the Operator (§15.5–§15.8).
    """

    datum: Datum
    trust_class: TrustClass
    reason: str
    disclosure: DisclosureState

    @property
    def excluded(self) -> bool:
        """True: quarantined content is excluded from Context and the Provider View.

        The §15.5 exclusion invariant (T11; RFC-0002 invariant 4): a
        quarantined datum never enters Context and never reaches the LLM
        except through the contained Provider View it is excluded from.
        The record is frozen and this property is unconditional, so a
        non-excluded quarantine cannot exist.
        """
        return True


# T12's contagion step, one class down in the §5 order, capped at
# Untrusted: suspicion spreads *downward* (§9.7, T12) but never
# fabricates Hostile — the Hostile set is exactly the fail-closed paths
# of DN-39, so only already-Untrusted content stays Untrusted and
# already-Hostile content stays Hostile.
_CONTAMINATION_STEP = {
    TrustClass.TRUSTED: TrustClass.CONDITIONAL,
    TrustClass.CONDITIONAL: TrustClass.UNTRUSTED,
    TrustClass.UNTRUSTED: TrustClass.UNTRUSTED,
    TrustClass.HOSTILE: TrustClass.HOSTILE,
}


def quarantine(
    datum: Datum,
    trust_class: TrustClass,
    reason: str,
    disclosure: DisclosureState = DisclosureState.DISCLOSED,
) -> Quarantine:
    """Admit a Hostile datum to quarantine (fail-closed admission; §15.5).

    Only content already held at Hostile is admitted. Hostile is
    produced only by the deterministic fail-closed paths of classify()
    and sanitize() (T11, DN-39), so quarantine never fabricates a
    Hostile class — it records one; non-Hostile content is rejected
    rather than silently admitted as Hostile. Pure and deterministic:
    the same arguments always yield the same record, with no I/O, no
    mutation, and no persistence (Q8).

    Args:
        datum: The Hostile datum to quarantine.
        trust_class: The datum's class; must be Hostile (DN-39).
        reason: Why the content is quarantined; must be non-empty so the
            Operator is always told why (§15.6).
        disclosure: Whether the content is withheld or disclosed
            contained to the Operator (§15.5–§15.8).

    Returns:
        The quarantine record carrying the datum, its Hostile class, the
        reason, and the disclosure state.

    Raises:
        ValueError: If ``trust_class`` is not Hostile, or ``reason`` is
            empty.
    """
    if trust_class is not TrustClass.HOSTILE:
        raise ValueError(
            "only Hostile content is admitted to quarantine (RFC-0007 §15.5; DN-39)"
        )
    if not reason:
        raise ValueError("a quarantine must carry a non-empty reason")
    return Quarantine(
        datum=datum, trust_class=trust_class, reason=reason, disclosure=disclosure
    )


def contaminate(quarantine: Quarantine, trust_class: TrustClass) -> Demotion:
    """Downgrade content from a quarantined source (T12; §9.7).

    Suspicion is contagious *downward*: content recently received from a
    source that has been quarantined as Hostile is downgraded one class
    in the §5 order — Trusted to Conditional, Conditional to Untrusted —
    and never fabricated into Hostile (the Hostile set stays exactly the
    fail-closed paths of DN-39). Trust is presumptively revoked until
    re-verified (§9.7, T12). The reason travels with the result,
    carrying the source quarantine's reason.

    Args:
        quarantine: The quarantined Hostile source.
        trust_class: The class of content recently received from it.

    Returns:
        The Demotion carrying the downgraded class and the reason.
    """
    return Demotion(
        trust_class=_CONTAMINATION_STEP[trust_class],
        reason=(
            f"source quarantined as Hostile: {quarantine.reason} (RFC-0007 §9.7, T12)"
        ),
    )
