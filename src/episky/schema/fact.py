"""Canonical Fact model.

Owner: RFC-0005 §3, §4, §5, §12.
Responsibility: the canonical Fact — status, provenance,
    freshness, machine identity, and scope.
Forbidden responsibility: never LLM-authored (F1), never
    carries permissions (F2), never executes (F3).
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum, auto

__all__ = [
    "Collector",
    "ConfidenceSource",
    "FactStatus",
    "Freshness",
    "FreshnessState",
    "Property",
    "Provenance",
    "Scope",
    "Subject",
    "Value",
]


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


@dataclass(frozen=True, slots=True)
class Collector:
    """Identity of the inspection that ran (RFC-0005 §5 "Who collected it?").

    The exact Collector identity — a name and a version — that ran the
    inspection (RFC-0005 §5). A Collector is a deterministic, read-only
    inspection procedure that produces Observations and carries declared
    inputs and provenance behavior (RFC-0003 §2.4). This type carries
    only the identity; the procedure itself is the Collector's own and
    belongs to the pipeline (Iteration 3). Frozen: an identity does not
    change.

    Attributes:
        name: The Collector's name.
        version: The Collector's version.
    """

    name: str
    version: str


@dataclass(frozen=True, slots=True)
class ConfidenceSource:
    """Why a Fact's value is believed — a named check, never a number.

    RFC-0005 §3: the Confidence Source is *why* the value is believed —
    a named deterministic check, a re-observation, or a Collector —
    never a percentage and never an LLM estimate. It is a Fact's
    grounds, not a score.

    This type carries the check's name and nothing else: its only field
    is a ``str``, so a numeric confidence score is structurally
    inexpressible — the type-level reading of "never a percentage"
    (RFC-0005 §3; F16).

    Attributes:
        name: The name of the deterministic check that grounds the
            claim.
    """

    name: str


class ObservationReference:
    """Placeholder for the Observation a Provenance names (RFC-0005 §5).

    RFC-0005 §5 requires every Fact to answer "where did this come
    from?" by naming the Observation it was normalized from. This
    deliberately empty class preserves that dependency now. It is:

    - NOT the Observation model — that is owned exclusively by the
      pipeline (RFC-0005 §2; Iteration 3 / RFC-0020);
    - NOT an identifier, persistence, or serialization format, and NOT
      a handle;
    - NOT an implementation of RFC-0005 §2; it carries no data and no
      behavior;
    - an internal Iteration 1 marker only, never a public contract
      (deliberately excluded from ``__all__``).

    It owns no semantics beyond "references an Observation that will be
    defined later." Iteration 1 code must never inspect, compare, parse,
    validate, serialize, resolve, or interpret it. Iteration 3 must be
    able to replace it with the real Observation model with zero
    semantic changes to Provenance: the placeholder is only the type of
    ``Provenance.observation``.
    """

    __slots__ = ()


@dataclass(frozen=True, slots=True)
class Provenance:
    """Provenance of a Fact — where, who, when, how, reproducible.

    RFC-0005 §5: every Fact must answer five questions, and provenance
    is not optional metadata — an unprovenanced claim is not a Fact
    (F10). This record answers them. Every component is mandatory
    (provenance is attached at normalization, never added later,
    RFC-0005 §5) and the record is immutable (F8).

    - where: ``observation`` — the Observation the Fact was normalized
      from (an ObservationReference placeholder; the real Observation
      model is Iteration 3's);
    - who: ``collector`` — the exact Collector identity that ran the
      inspection;
    - when: ``collected_at`` and ``re_collected_at`` — the collection
      timestamp and every re-collection timestamp;
    - using what / can it be reproduced: the named Collector and its
      declared inputs and provenance behavior (RFC-0003 §2.4);
      reproduction is by re-running the same Collector under the same
      conditions (RFC-0005 §5). The concrete reproduction record is
      RFC-0020's to define and is deferred here, like the freshness
      bound (RFC-0005 §12; design review §16 #8).

    Attributes:
        observation: The Observation this Fact was normalized from
            (see ObservationReference).
        collector: The Collector identity that ran the inspection.
        collected_at: When the underlying Observation was collected.
        re_collected_at: Every re-collection timestamp, if any.
    """

    observation: ObservationReference
    collector: Collector
    collected_at: datetime
    re_collected_at: tuple[datetime, ...] = ()


@dataclass(frozen=True, slots=True)
class Subject:
    """What a Fact is about (RFC-0005 §3).

    The Subject is the thing the claim names — a machine, a subsystem, a
    State Domain, a device, a package, or a service (RFC-0005 §3). Its
    canonical, distro-independent vocabulary is RFC-0021's (Iteration 2);
    this type carries the canonical name so a Subject is a distinct,
    non-stringly-typed component (RFC-0005 §1, §3). Together with
    Property it names the claim; Value and Status say what is claimed.
    Frozen: a naming component does not change.

    Attributes:
        name: The canonical, distro-independent name of the Subject.
    """

    name: str


@dataclass(frozen=True, slots=True)
class Property:
    """The attribute of the Subject being asserted (RFC-0005 §3).

    Examples per RFC-0005 §3: installed-version, running-state,
    mount-point. Together Subject + Property name the claim; Value and
    Status say what is claimed. Frozen: a naming component does not
    change.

    Attributes:
        name: The canonical name of the asserted attribute.
    """

    name: str


@dataclass(frozen=True, slots=True)
class Value:
    """The asserted content of a Property (RFC-0005 §3).

    The Value is the claim's content in canonical, distro-independent
    terms. It is distinct from Status: "the service is stopped" (a
    Value) is not "the service's state is unknown" (a Status), and a
    Value never contains a permission or authority (F2). Frozen: an
    immutable observation component (F8).

    Attributes:
        value: The canonical, distro-independent asserted content.
    """

    value: str


@dataclass(frozen=True, slots=True)
class Scope:
    """Exactly what a Fact asserts — its Subject, Property, and Value.

    RFC-0005 §3: a Fact asserts exactly its Subject, Property, and
    Value; nothing more may be inferred (F13). This record carries those
    three components and nothing else.

    RFC-0005 §3 and §10 also make the category part of Scope; the
    FactCategory vocabulary is owned by RFC-0021 / Iteration 2 and is
    deferred (design review §16 #4), so it is not a field here. Commit 5
    adds it additively, with zero semantic change to this type.

    Attributes:
        subject: The Subject the Fact is about.
        property: The Property of the Subject being asserted.
        value: The asserted content of the Property.
    """

    subject: Subject
    property: Property
    value: Value


class MachineIdentity:
    """Opaque placeholder for the machine a Fact describes (RFC-0005 §11).

    Every Fact carries the identity of the machine its Observation was
    collected on, and a Fact is valid only for the machine it names
    (RFC-0005 §11; F12). The precise contents of Machine Identity are
    RFC-0014's to define, and RFC-0014 does not exist yet. This
    deliberately empty class preserves the dependency now. It is:

    - NOT the machine-identity model — contents are owned by RFC-0014;
    - NOT an identifier, persistence, or serialization format, and NOT
      a handle;
    - NOT an implementation of RFC-0005 §11; it carries no data and no
      behavior;
    - an internal Iteration 1 marker only, never a public contract
      (deliberately excluded from ``__all__`` until RFC-0014 defines
      it).

    It owns no semantics beyond "the machine this Fact describes, to be
    defined later." Iteration 1 code must never inspect, compare, parse,
    validate, serialize, resolve, or interpret it. RFC-0014 must be able
    to replace it with the real Machine Identity model with zero
    semantic changes to its consumers: the placeholder is only the type
    of the field that names the machine.
    """

    __slots__ = ()
