"""Canonical Fact model.

Owner: RFC-0005 §3, §4, §5, §12.
Responsibility: the canonical Fact — status, provenance,
    freshness, machine identity, and scope.
Forbidden responsibility: never LLM-authored (F1), never
    carries permissions (F2), never executes (F3).
"""

from dataclasses import dataclass
from enum import Enum, auto

__all__ = ["FactStatus", "Freshness", "FreshnessState"]


class FactStatus(Enum):
    """Fact status per RFC-0005 §4.

    Every Fact carries exactly one status. Status is decided by the
    Fact Layer from evidence, never by rhetoric, and it is part of the
    Fact (RFC-0005 §3). The eight statuses are structurally distinct:
    *Unknown*, *Missing* (recorded as Unavailable), and *Unsupported*
    are three different things and are never collapsed into one, and
    *Stale* is never Current (RFC-0005 §1, §13 F11).

    Members:
        OBSERVED: The claim was normalized from a successful
            Observation and is believed current.
        VERIFIED: The claim was independently re-confirmed after the
            event it describes — the strongest status.
        UNKNOWN: The claim could not be established: the Collector
            failed, timed out, or produced unparseable output.
        UNAVAILABLE: The check could not run at all — permission, tool
            absent, watchdog active (recorded for "Missing").
        UNSUPPORTED: The machine does not have the capability the
            check would describe.
        CONTRADICTED: Fresh evidence says something else; the old
            claim is invalidated and the fresh evidence wins.
        STALE: The Fact is past its freshness bound and may no longer
            describe the machine.
        INVALID: The Fact fails its own requirements — provenance
            lost, identity mismatch, status uncomputable.
    """

    OBSERVED = auto()
    VERIFIED = auto()
    UNKNOWN = auto()
    UNAVAILABLE = auto()
    UNSUPPORTED = auto()
    CONTRADICTED = auto()
    STALE = auto()
    INVALID = auto()


class FreshnessState(Enum):
    """Freshness state of a Fact per RFC-0005 §12.

    Freshness answers how current a Fact is. It is a property of time
    and state, not of truth: a Fact that was correct is still stale
    once it is old (RFC-0002 invariant 10). A Fact whose freshness
    cannot be computed is treated as stale or invalid, never as
    current (RFC-0005 §13 F15).

    Members:
        CURRENT: Within its freshness bound, and no state change
            invalidated it. Believed; used without re-collection.
        POSSIBLY_STALE: Near the bound, or a detected state change
            affects a depended-on Fact. Usable only with caution.
        STALE: Past its freshness bound. Must be re-collected before
            any use as current evidence.
        EXPIRED: The bound has passed and the claim is no longer part
            of the current set. Treated as retired; only the record
            remains.
        UNKNOWN_FRESHNESS: The bound cannot be computed — provenance
            or timing is missing. Treated as stale or invalid, never
            as current.
    """

    CURRENT = auto()
    POSSIBLY_STALE = auto()
    STALE = auto()
    EXPIRED = auto()
    UNKNOWN_FRESHNESS = auto()


@dataclass(frozen=True, slots=True)
class Freshness:
    """Freshness of a claim: its freshness state.

    RFC-0005 §12 fixes the mechanism: a Fact carries a freshness bound
    for its category and a freshness state. This type carries the
    state, which is the RFC-0005 §12 surface. The bound's concrete
    values are policy content owned by RFC-0020 (RFC-0005 §12), and
    its representation (scalar vs policy reference) is a recorded,
    unresolved ambiguity (Iteration 1 design review §16 #8); it is not
    part of this type surface.

    Frozen and slot-based: a Fact is immutable (RFC-0005 §13 F8), so a
    Freshness carried by a Fact must be too.

    Attributes:
        state: The current freshness state (RFC-0005 §12).
    """

    state: FreshnessState
