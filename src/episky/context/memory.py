"""Consented, in-memory Memory (RFC-0012 §7, §18–§22; RFC-0001 §9.2/§9.5;
RFC-0009 SC16; RFC-0004 §4.11).

Owner: RFC-0012 §7 (Memory Categories), §18 (Visibility), §20
    (Destruction), §22 (Persistence Philosophy).
Responsibility: the deterministic, in-memory consented store (DN-69): the
    promotion gate — material moves to Memory only with an explicit
    consent carrying a stated purpose (CM11); exactly the three §7
    categories (Preference Memory, Machine Memory, Durable Context),
    which are promotions from Context and so never secret values, raw
    output, the Audit record, or private content without demotion (SC16);
    list, export, and wipe are first-class (CM14); wipe is complete and
    irreversible with no restore path (CM12/CM13); and Memory decides
    nothing (CM2). Every transition returns a new immutable store and
    emits the deterministic promotion/destruction boundary events
    (DN-70, Q6). The durable backing, retention, deletion, export, and
    what survives a resume are RFC-0014/RFC-0020's (Q5).
Forbidden responsibility: no decision, approval, or truth path (CM2); no
    restore path (CM13); no secret value (SC2 — the enforcement point is
    `boundaries` at Context entry; Memory is a promotion from Context,
    RFC-0012 §2 rule 1); no I/O, no persistence, no clock read (time is
    always an explicit argument), no randomness, no UUID, no event bus,
    no audit write, never the Audit (CM15).
"""

from dataclasses import dataclass
from datetime import date
from enum import Enum, auto

from episky.context.assemble import BoundaryEventKind

__all__ = [
    "Memory",
    "MemoryCategory",
    "MemoryEntry",
    "MemoryEvent",
    "MemoryOutcome",
    "MemoryRefusal",
    "empty",
    "export",
    "list_entries",
    "promote",
    "remove",
    "wipe",
]


class MemoryCategory(Enum):
    """The three Memory categories (RFC-0012 §7; DN-69).

    Exactly three, all promotions from Context under consent; none may
    hold a secret value, raw output, or personal data without explicit
    Operator demotion (RFC-0009 SC16).

    Members:
        PREFERENCE: Operator preferences — verbosity, provider choice,
            skill selection (§7 rule 1).
        MACHINE: High-signal Facts about the machine, collected not
            guessed, retained across sessions under consent (§7 rule 2).
        DURABLE: Anything the Operator explicitly asked to be remembered
            beyond the session, purpose-scoped and reversible (§7 rule 3).
    """

    PREFERENCE = auto()
    MACHINE = auto()
    DURABLE = auto()


class MemoryRefusal(Enum):
    """The deterministic refusal reasons, disclosed not silent (RFC-0001 §8.12).

    Members:
        NO_CONSENT: No explicit consent — durable retention exists only
            under consent (CM11; RFC-0012 §22 rule 2).
        UNPURPOSEFUL: No stated purpose — nothing is retained without one
            (CM11; RFC-0012 §22 rule 3).
        MALFORMED: The request is structurally invalid (a blank identity
            or blank content) and fails closed.
        NOT_FOUND: A targeted removal names no held entry.
    """

    NO_CONSENT = auto()
    UNPURPOSEFUL = auto()
    MALFORMED = auto()
    NOT_FOUND = auto()


@dataclass(frozen=True, slots=True)
class MemoryEntry:
    """One consented, retained entry (RFC-0012 §7, §22).

    The entry is the value-safe material promoted from Context — a
    subset of Context, so already secret-free by the enforcement point
    at Context entry (SC2; RFC-0012 §2 rule 1) — retained with the
    stated purpose it serves (CM11) and the explicit date consent was
    granted. The identity is a stable, value-free name for deterministic
    replacement and targeted removal; it is not a persistence identifier
    (durable identifiers are RFC-0014's).

    Attributes:
        category: The §7 Memory category.
        identity: The stable, value-free name of the entry.
        content: The value-safe material retained.
        purpose: The stated purpose carried at consent (CM11).
        consented_on: The date consent was granted (an explicit input;
            no clock read).
    """

    category: MemoryCategory
    identity: str
    content: str
    purpose: str
    consented_on: date


@dataclass(frozen=True, slots=True)
class Memory:
    """The in-memory consented store, an immutable value (DN-69).

    Entries are held in insertion order, so the store is deterministic
    for a deterministic sequence of transitions. Frozen and slot-based:
    there is no hidden mutable state, and every transition returns a new
    Memory.
    """

    entries: tuple[MemoryEntry, ...]


@dataclass(frozen=True, slots=True)
class MemoryEvent:
    """A deterministic, value-free memory boundary event (DN-70; Q6).

    Carries kind, category, identity, and size — never the material
    itself. `core` writes these as RFC-0013 §7 cat. 9 records at the
    runtime boundary (RFC-0013 §23); the package never imports `audit`
    (CM15).

    Attributes:
        kind: ENTERED for a promotion, DESTROYED for a removal or wipe.
        category: The Memory category the event concerns, or None for a
            full wipe.
        identity: A stable, value-free label — the entry's identity, the
            category name, or "memory" for a full wipe.
        size: The number of entries the event concerns.
    """

    kind: BoundaryEventKind
    category: MemoryCategory | None
    identity: str
    size: int


@dataclass(frozen=True, slots=True)
class MemoryOutcome:
    """The deterministic result of a store transition (fail-loud).

    Frozen and slot-based: the new store, the boundary event when a
    transition happened, and the refusal when it did not. A refused
    transition leaves the store unchanged and discloses the reason,
    never silently dropping the request.

    Attributes:
        memory: The store after the transition (unchanged when refused).
        event: The promotion/destruction event, or None when refused.
        refusal: The deterministic refusal reason, None when the
            transition happened.
        reason: Why the transition happened or was refused (fail-loud).
    """

    memory: Memory
    event: MemoryEvent | None
    refusal: MemoryRefusal | None
    reason: str


def _refuse(memory: Memory, refusal: MemoryRefusal, reason: str) -> MemoryOutcome:
    """Build the fail-closed outcome: no transition, no event, the reason disclosed."""
    return MemoryOutcome(memory=memory, event=None, refusal=refusal, reason=reason)


def empty() -> Memory:
    """The empty store (RFC-0012 §7): no entries, no state."""
    return Memory(entries=())


def list_entries(
    memory: Memory, category: MemoryCategory | None = None
) -> tuple[MemoryEntry, ...]:
    """The visible set, deterministically ordered (CM14; RFC-0012 §18 rule 1).

    Returns the entries in insertion order, optionally restricted to one
    §7 category, so the Operator always sees exactly what is held.
    """
    if category is None:
        return memory.entries
    return tuple(entry for entry in memory.entries if entry.category is category)


def export(memory: Memory) -> tuple[MemoryEntry, ...]:
    """The complete, honest export (CM14; RFC-0012 §18 rule 2).

    In-memory the export is the full entry set in insertion order —
    complete and deterministic (RFC-0001 §9.2). The durable export form
    is RFC-0014's (Q5).
    """
    return memory.entries


def promote(
    memory: Memory,
    *,
    category: MemoryCategory,
    identity: str,
    content: str,
    purpose: str,
    consent: bool,
    consented_on: date,
) -> MemoryOutcome:
    """Promote material to Memory under explicit consent (CM11; DN-69).

    Pure and deterministic: the same store, category, identity, content,
    purpose, consent, and date always yield the same outcome, with no
    I/O, no clock read, and no hidden state. The promotion gate refuses
    without consent (RFC-0012 §22 rule 2), without a stated purpose
    (rule 3), or with a blank identity or content (fail-closed). An
    admitted promotion replaces an entry of the same (category, identity)
    deterministically and emits the ENTERED boundary event before the
    material's use (DN-70; RFC-0002 I-13).

    Args:
        memory: The store to promote into.
        category: The §7 category being retained.
        identity: The stable, value-free name of the entry.
        content: The value-safe material to retain (promoted from
            Context, secret-free by the boundary at entry; SC2).
        purpose: The stated purpose the retention serves (CM11).
        consent: Whether the Operator explicitly granted retention.
        consented_on: The date consent was granted (an explicit input).

    Returns:
        The MemoryOutcome: the new store with the entry and its ENTERED
        event, or the unchanged store with its refusal.
    """
    if not consent:
        return _refuse(
            memory,
            MemoryRefusal.NO_CONSENT,
            "durable Memory exists only under explicit consent (CM11; RFC-0012 §22)",
        )
    if not purpose.strip():
        return _refuse(
            memory,
            MemoryRefusal.UNPURPOSEFUL,
            "nothing is retained without a stated purpose (CM11; RFC-0012 §22)",
        )
    if not identity.strip() or not content.strip():
        return _refuse(
            memory,
            MemoryRefusal.MALFORMED,
            "a retention needs a named identity and content (fail-closed)",
        )
    entry = MemoryEntry(
        category=category,
        identity=identity,
        content=content,
        purpose=purpose,
        consented_on=consented_on,
    )
    kept = tuple(
        e
        for e in memory.entries
        if not (e.category is category and e.identity == identity)
    )
    event = MemoryEvent(
        kind=BoundaryEventKind.ENTERED,
        category=category,
        identity=identity,
        size=1,
    )
    return MemoryOutcome(
        memory=Memory(entries=kept + (entry,)),
        event=event,
        refusal=None,
        reason="retained under explicit consent (CM11)",
    )


def remove(memory: Memory, *, category: MemoryCategory, identity: str) -> MemoryOutcome:
    """Remove one held entry deterministically (CM14; RFC-0012 §20 rule 1).

    Targeted removal is part of the explicit lifecycle — a purpose lapse
    or an Operator request. A removal that names no held entry refuses
    with NOT_FOUND and changes nothing. When an entry is removed, the
    DESTROYED boundary event precedes the consequence (DN-70; RFC-0002
    I-13) and there is no restore path (CM13).

    Args:
        memory: The store to remove from.
        category: The §7 category of the entry.
        identity: The stable name of the entry to remove.

    Returns:
        The MemoryOutcome: the store without the entry and its DESTROYED
        event, or the unchanged store with a NOT_FOUND refusal.
    """
    kept = tuple(
        e
        for e in memory.entries
        if not (e.category is category and e.identity == identity)
    )
    if len(kept) == len(memory.entries):
        return _refuse(
            memory,
            MemoryRefusal.NOT_FOUND,
            f"no {category.name} entry named {identity!r} is held",
        )
    event = MemoryEvent(
        kind=BoundaryEventKind.DESTROYED,
        category=category,
        identity=identity,
        size=1,
    )
    return MemoryOutcome(
        memory=Memory(entries=kept),
        event=event,
        refusal=None,
        reason="destroyed, complete and recorded (CM12)",
    )


def wipe(memory: Memory, category: MemoryCategory | None = None) -> MemoryOutcome:
    """Wipe Memory completely or by category (CM12/CM14; RFC-0012 §18 rule 3).

    Wipe is always available, complete, and irreversible: the returned
    store holds nothing the wipe removed, and there is no restore path
    (CM13; RFC-0012 §20 rule 3). The DESTROYED event records what was
    removed before the consequence (DN-70; RFC-0002 I-13) — even when
    nothing was held, the wipe is disclosed with size zero rather than
    silently dropped. The durable wipe (across the RFC-0014 backing) is
    RFC-0014's (Q5).

    Args:
        memory: The store to wipe.
        category: Wipe one §7 category, or None to wipe all Memory.

    Returns:
        The MemoryOutcome: the store with the entries gone and its
        DESTROYED event.
    """
    if category is None:
        cleared = Memory(entries=())
        removed = memory.entries
        event_category = None
        identity = "memory"
    else:
        cleared = Memory(
            entries=tuple(e for e in memory.entries if e.category is not category)
        )
        removed = tuple(e for e in memory.entries if e.category is category)
        event_category = category
        identity = category.name
    event = MemoryEvent(
        kind=BoundaryEventKind.DESTROYED,
        category=event_category,
        identity=identity,
        size=len(removed),
    )
    return MemoryOutcome(
        memory=cleared,
        event=event,
        refusal=None,
        reason="wiped, complete and irreversible (CM12/CM13)",
    )
