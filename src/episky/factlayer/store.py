"""Fact storage, status, and invalidation.

Owner: RFC-0005 §4, §6, §7 (DN-19, DN-20).
Responsibility: the in-memory current set of Facts for one machine
    (Machine State, RFC-0003 §2.1; RFC-0005 §7) — record canonical
    Facts, retire superseded Facts on the RFC-0005 §6 component identity
    (DN-20), and fail closed on rule-violating Facts (F10, F12, F16).
Forbidden responsibility: never creates a Fact (F1 — only normalization
    does; design review §2.2), never carries permissions (F2), never
    executes (F3), never persists (DN-19; RFC-0012/0013 own storage),
    never verifies, and never mutates a stored Fact (F8) — recording is
    pure, deterministic, and side-effect free (no clock, no timer, no
    state beyond the current set and its retirement record).
"""

from collections.abc import Mapping
from dataclasses import dataclass, field
from enum import Enum, auto
from types import MappingProxyType

from episky.schema.fact import (
    Fact,
    FactStatus,
    MachineIdentity,
    Property,
    Subject,
)

__all__ = [
    "FactStore",
    "FactIdentity",
    "RetiredFact",
    "StoreOutcome",
    "StoreRecord",
    "REASON_MACHINE_MISMATCH",
    "REASON_NOT_SUPERSEDING",
    "REASON_PROVENANCE_LOST",
    "REASON_STATUS_UNESTABLISHED",
    "REASON_SUPERSEDED",
    "record",
]

# The statuses the current set holds (RFC-0005 §4; F11): exactly the four
# the pipeline produces. A Fact carrying any other status is not a claim
# the store can establish as current, so admitting it would fail closed
# (F16); Verified becomes admissible when verification lands (Iteration 4).
CURRENT_STATUSES = frozenset(
    {
        FactStatus.OBSERVED,
        FactStatus.UNKNOWN,
        FactStatus.UNAVAILABLE,
        FactStatus.UNSUPPORTED,
    }
)

REASON_PROVENANCE_LOST = "provenance lost (F10)"
REASON_MACHINE_MISMATCH = "machine identity mismatch (F12)"
REASON_STATUS_UNESTABLISHED = "status cannot be established (F16)"
REASON_NOT_SUPERSEDING = "not superseding (not fresher or not at least as strong)"
REASON_SUPERSEDED = "superseded"


@dataclass(frozen=True, slots=True)
class FactIdentity:
    """The component identity on which Facts supersede (RFC-0005 §6).

    Two Facts are the same claim — the same Fact Identity — when they
    have the same Machine Identity, the same Subject, and the same
    Property (RFC-0005 §6). This is the component identity, not an
    Identifier: no Identifier format or generation is invented (DN-20;
    the Identifier component remains RFC-0020's).

    Attributes:
        machine_identity: The machine the claim describes (§6, §11).
        subject: The Subject of the claim (§3).
        property: The Property of the Subject being asserted (§3).
    """

    machine_identity: MachineIdentity
    subject: Subject
    property: Property


@dataclass(frozen=True, slots=True)
class RetiredFact:
    """The lifecycle record of one retired Fact (RFC-0005 §7).

    A Fact that stops being current is retired, not dropped and never
    edited: the record keeps the retired Fact and names the Fact that
    superseded it (DN-20), so it does not vanish and keeps its
    provenance (RFC-0005 §5, §7). Storage of the record beyond the
    current set is RFC-0012/0013's (DN-19).

    Attributes:
        fact: The retired Fact, unchanged (F8).
        successor: The Fact that superseded it (§6, §8).
        reason: Why the Fact was retired.
    """

    fact: Fact
    successor: Fact
    reason: str


class StoreOutcome(Enum):
    """The disposition of one record() call (RFC-0005 §4, §7).

    Members:
        ADMITTED: The Fact is now the current Fact for its identity —
            a fresh claim (§7 Creation).
        SUPERSEDED: The Fact became current and retired an older Fact
            of the same identity (§6, §7 Replacement; DN-20).
        REJECTED: The Fact was not admitted — it did not supersede the
            current Fact (not fresher, or evidence not at least as
            strong, or a distinct status, F11), which stays current.
        INVALID: The Fact was blocked by a canonical-rule violation
            (F10, F12, F16) and disclosed; it never enters the current
            set (RFC-0005 §7 Deletion; F16).
    """

    ADMITTED = auto()
    SUPERSEDED = auto()
    REJECTED = auto()
    INVALID = auto()


@dataclass(frozen=True, slots=True)
class StoreRecord:
    """The result of one record() call.

    Attributes:
        outcome: The Fact's disposition.
        fact: The Fact that was recorded.
        reason: Why the disposition was reached (empty on ADMITTED).
        store: The resulting store (unchanged on REJECTED and INVALID).
        retired: The Fact retired on SUPERSEDED, else None.
    """

    outcome: StoreOutcome
    fact: Fact
    reason: str
    store: "FactStore"
    retired: Fact | None = None


@dataclass(frozen=True, slots=True)
class FactStore:
    """The in-memory current set of Facts for one machine (RFC-0005 §7).

    Machine State is "the current set of verified Facts together with
    the known unknowns" at a moment (RFC-0003 §2.1). This store is that
    set for exactly one Machine Identity (F12; RFC-0005 §11): it holds
    one current Fact per component identity (§6) and the retirement
    record of every Fact that stopped being current (§7; DN-19). The
    store is in-memory only — no persistence, no format, no engine
    (DN-19). It is immutable: recording returns a new store and never
    edits a stored Fact (F8; RFC-0005 §7 "Facts are never edited").

    Attributes:
        machine_identity: The single machine this current set is bound
            to (F12; §11).
        current: The current set — one Fact per component identity (§6).
        retired: The lifecycle record — every retired Fact per identity
            (§7), with its successor (DN-20).
    """

    machine_identity: MachineIdentity
    current: Mapping[FactIdentity, Fact] = field(default_factory=dict)
    retired: Mapping[FactIdentity, tuple[RetiredFact, ...]] = field(
        default_factory=dict
    )

    def __post_init__(self) -> None:
        object.__setattr__(self, "current", MappingProxyType(dict(self.current)))
        object.__setattr__(self, "retired", MappingProxyType(dict(self.retired)))


def _evidence_strength(status: FactStatus) -> int:
    """Evidence strength of a status for supersession (RFC-0005 §6; DN-20).

    RFC-0005 §4: an Observed claim is established ("believed current"),
    so it is stronger evidence than a claim that was not established.
    Unknown, Unavailable, and Unsupported are all "no claim established"
    and are one equal, weaker tier; their distinctness is never lost
    (F11), because different failure statuses never supersede one
    another (record() additionally requires the same status). Verified is
    the strongest status overall (§4) but is not producible or
    admissible in Iteration 3 (no verification yet).
    """
    if status is FactStatus.VERIFIED:
        return 3
    if status is FactStatus.OBSERVED:
        return 2
    if status in (
        FactStatus.UNKNOWN,
        FactStatus.UNAVAILABLE,
        FactStatus.UNSUPPORTED,
    ):
        return 1
    return 0


def _supersedes(new_fact: Fact, old_fact: Fact) -> bool:
    """Whether ``new_fact`` supersedes ``old_fact`` (RFC-0005 §6; DN-20).

    A newer Fact supersedes an older one when it has the same component
    identity, is fresher, and its evidence is at least as strong; the
    older is then retired with the newer recorded as its successor.
    "At least as strong" never crosses distinct failure statuses (F11):
    a fresh run may update the same status's record, and an Observed
    claim may replace a not-established one, but a weaker or differently
    statused Fact never displaces the current claim.
    """
    if new_fact.provenance.collected_at <= old_fact.provenance.collected_at:
        return False
    new_strength = _evidence_strength(new_fact.status)
    old_strength = _evidence_strength(old_fact.status)
    if new_strength > old_strength:
        return True
    return new_strength == old_strength and new_fact.status is old_fact.status


def _rule_violation(store: FactStore, fact: Fact) -> str | None:
    """The canonical-rule violation a Fact fails on admission, or None.

    F10: provenance must answer "who" — an unnamed Collector identity is
    a lost provenance. F12: a Fact is valid only for the machine the
    store's current set is bound to (§11). F16: a status the store
    cannot establish as current is a rule failure and fails closed
    (F11, F14, F16).
    """
    collector = fact.provenance.collector
    if not collector.name.strip() or not collector.version.strip():
        return REASON_PROVENANCE_LOST
    if fact.machine_identity != store.machine_identity:
        return REASON_MACHINE_MISMATCH
    if fact.status not in CURRENT_STATUSES:
        return REASON_STATUS_UNESTABLISHED
    return None


def record(store: FactStore, fact: Fact) -> StoreRecord:
    """Record one Fact into the current set (RFC-0005 §4, §7; DN-20).

    A pure, deterministic function: it reads the store and the Fact and
    returns the disposition (StoreOutcome) with the resulting store. A
    Fact is either admitted to the current set — as a fresh claim or as
    the supersession of the current Fact of the same component identity
    (§6) — or not admitted: rejected because it did not supersede, or
    blocked because it violates a canonical rule, in which case it is
    Invalid and disclosed (F10, F12, F16). Nothing is mutated: the Fact
    is never edited (F8; §7), the input store is untouched, and a
    retired Fact stays in the record with its provenance (§7).

    Args:
        store: The current set to record into; never mutated.
        fact: The canonical Fact to record; never mutated.

    Returns:
        The disposition, its reason, the resulting store, and (on
        SUPERSEDED) the Fact that was retired.
    """
    violation = _rule_violation(store, fact)
    if violation is not None:
        return StoreRecord(
            outcome=StoreOutcome.INVALID,
            fact=fact,
            reason=violation,
            store=store,
        )

    identity = FactIdentity(
        machine_identity=fact.machine_identity,
        subject=fact.scope.subject,
        property=fact.scope.property,
    )
    old = store.current.get(identity)
    if old is None:
        current = dict(store.current)
        current[identity] = fact
        return StoreRecord(
            outcome=StoreOutcome.ADMITTED,
            fact=fact,
            reason="",
            store=FactStore(
                machine_identity=store.machine_identity,
                current=current,
                retired=store.retired,
            ),
        )

    if _supersedes(fact, old):
        current = dict(store.current)
        current[identity] = fact
        retired = dict(store.retired)
        retired[identity] = store.retired.get(identity, ()) + (
            RetiredFact(fact=old, successor=fact, reason=REASON_SUPERSEDED),
        )
        return StoreRecord(
            outcome=StoreOutcome.SUPERSEDED,
            fact=fact,
            reason=REASON_SUPERSEDED,
            retired=old,
            store=FactStore(
                machine_identity=store.machine_identity,
                current=current,
                retired=retired,
            ),
        )

    return StoreRecord(
        outcome=StoreOutcome.REJECTED,
        fact=fact,
        reason=REASON_NOT_SUPERSEDING,
        store=store,
    )
