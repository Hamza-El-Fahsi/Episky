"""Deterministic, bounded Context assembly (RFC-0012 §6, §8, §10–§12, §16,
§17, §33; RFC-0007 S7).

Owner: RFC-0012 §12.
Responsibility: the pure, deterministic Context composition over the explicit
    boundary inputs (DN-66) — a schema-shaped Goal value, the Fact current
    set read from `factlayer` at its freshness, bounded labeled history,
    labeled Evidence on `schema.VerificationOutcome` (DN-74), sanitized
    Skill material, and the routing-state marker (RFC-0012 §33; DN-71) —
    plus a stated purpose that bounds what may enter (CM5). It applies the
    §12 composition order, the six §6 categories as explicit types (DN-73),
    the freshness gates and a mark-stale function (CM7/CM8, DN-72), size
    bounds with transparent consolidation and a placeholder default (CM6),
    one Goal per working set with no cross-session merge (CM9), and
    deterministic, value-free context-boundary events (DN-70) that `core`
    writes as RFC-0013 §7 cat. 9 records before the material's use (RFC-0002
    I-13).
Forbidden responsibility: no I/O, no provider call, no live session state,
    no secret value (SC2; the enforcement point is `boundaries`), no raw
    Observation or unprovenanced claim (RFC-0012 §9), no truth verdict
    (CM1), no restore path (CM13), never the Audit (CM15; the record is
    `core`'s write), never verification power (DN-74).
"""

from dataclasses import dataclass, replace
from enum import Enum, auto

from episky.factlayer.store import FactStore
from episky.schema.fact import Fact, FreshnessState
from episky.schema.outcome import VerificationOutcome

__all__ = [
    "Assembly",
    "BoundaryEvent",
    "BoundaryEventKind",
    "Context",
    "ContextCategory",
    "ContextState",
    "DEFAULT_EVIDENCE_BOUND",
    "DEFAULT_FACT_BOUND",
    "DEFAULT_HISTORY_BOUND",
    "DEFAULT_SKILL_BOUND",
    "Disclosure",
    "EvidenceLabel",
    "GoalValue",
    "HistoryLabel",
    "REASON_OVERFLOW",
    "REASON_STALE_EXCLUDED",
    "REASON_UNPURPOSEFUL",
    "RoutingMarker",
    "SkillMaterialItem",
    "Supersession",
    "TurnRecord",
    "assemble",
    "mark_stale",
    "supersede_question",
]

DEFAULT_FACT_BOUND = 64
"""Provisional default Fact bound (CM6; RFC-0001 §9.3).

Provisional: RFC-0020 owns the concrete per-category size bounds
(RFC-0012 §37 OQ1); this constant makes the default deterministic and
overridable now, following the DN-18 placeholder-default precedent.
"""

DEFAULT_HISTORY_BOUND = 24
"""Provisional default history-turn bound (CM6). See DEFAULT_FACT_BOUND."""

DEFAULT_EVIDENCE_BOUND = 16
"""Provisional default Evidence bound (CM6). See DEFAULT_FACT_BOUND."""

DEFAULT_SKILL_BOUND = 8
"""Provisional default Skill-material bound (CM6). See DEFAULT_FACT_BOUND."""

REASON_UNPURPOSEFUL = "unpurposeful material refused (CM5)"
REASON_STALE_EXCLUDED = "Stale/Expired/Unknown-freshness Fact excluded (CM7)"
REASON_OVERFLOW = "overflow consolidated, never silently grown (CM6)"

# The freshness states a Fact may carry into Context (RFC-0012 §16; RFC-0005
# §12): Current is believed without re-collection; Possibly-stale is usable
# only with caution and does not make the working set Stale. Stale, Expired,
# and Unknown-freshness are excluded at the gate (CM7).
_ADMISSIBLE_FRESHNESS = frozenset(
    {FreshnessState.CURRENT, FreshnessState.POSSIBLY_STALE}
)


class ContextCategory(Enum):
    """The six Context categories (RFC-0012 §6; DN-73).

    The §6 closure, fixed as explicit types before the live producers
    land: adding a category later is an additive amendment (RFC-0012 §34
    rule 2; RFC-0003 Part II), so there are exactly these six.

    Members:
        GOAL: The active Goal statement and its scope (category 1).
        FACTS: Current, provenance-carrying Facts (category 2).
        HISTORY: Bounded, labeled conversation and turn history (category 3).
        EVIDENCE: Verification Outcomes as labeled material (category 4).
        SKILL_MATERIAL: Sanitized, bounded Skill content (category 5).
        ROUTING_STATE: The outstanding-question marker and current
            decision pointer (category 6).
    """

    GOAL = auto()
    FACTS = auto()
    HISTORY = auto()
    EVIDENCE = auto()
    SKILL_MATERIAL = auto()
    ROUTING_STATE = auto()


class ContextState(Enum):
    """The working-set lifecycle states this module owns (RFC-0012 §10–§11).

    Empty, Assembling, Promoted, and Destroyed are not this module's:
    Empty/Assembling are `core`'s wiring (RFC-0002 §2.4) and Promoted/
    Destroyed are `memory.py`'s (C3). Assembly produces Current or
    Consolidated; mark-stale produces Stale. Anything not listed is
    illegal (RFC-0012 §11; RFC-0001 §8.2).

    Members:
        CURRENT: A valid working set is ready.
        STALE: A carried Fact lapsed or a state change invalidated the
            set; it is rebuilt, never patched.
        CONSOLIDATED: Overflow forced bounding; Current in content,
            smaller, and the consolidation is disclosed.
    """

    CURRENT = auto()
    STALE = auto()
    CONSOLIDATED = auto()


class HistoryLabel(Enum):
    """The label a history turn travels with (RFC-0007 §12; RFC-0012 §6 cat. 3).

    History is material, never Facts: a proposal or hypothesis is labeled
    as such and never becomes a Fact through Context, and a Provider reply
    is untrusted data (RFC-0004 A1) that stays labeled material.

    Members:
        OPERATOR_INPUT: An Operator input turn.
        PROVIDER_REPLY: A Provider reply.
        PROPOSAL: A proposal presented for approval.
        HYPOTHESIS: A hypothesis, never a Fact.
        DECISION: A decision taken (for example, an Operator approval).
    """

    OPERATOR_INPUT = auto()
    PROVIDER_REPLY = auto()
    PROPOSAL = auto()
    HYPOTHESIS = auto()
    DECISION = auto()


class BoundaryEventKind(Enum):
    """The kind of context-boundary event (DN-70).

    Members:
        ENTERED: Material entered Context at assembly.
        INVALIDATED: A working set was marked Stale (CM8), recorded
            before any use (RFC-0002 I-13).
        DESTROYED: Material was destroyed with no restore path
            (CM12/CM13); emitted by `memory.py` (C3).
    """

    ENTERED = auto()
    INVALIDATED = auto()
    DESTROYED = auto()


@dataclass(frozen=True, slots=True)
class GoalValue:
    """A schema-shaped Goal value: statement and scope (RFC-0003 §2.3; DN-66).

    The Goal is the Core's and a canonical Goal schema is RFC-0020's
    (DN-1); this is the plain boundary value assembly consumes — one
    active Goal per working set (CM9) — never a claim and never an
    authority.

    Attributes:
        statement: The active Goal statement.
        scope: The scope the Goal is bounded to.
    """

    statement: str
    scope: str


@dataclass(frozen=True, slots=True)
class TurnRecord:
    """One bounded, labeled history turn (RFC-0012 §6 cat. 3; RFC-0007 §12).

    The turn is supplied already-labeled and already-sanitized (DN-66);
    `boundaries` is the sanitization enforcement point.

    Attributes:
        content: The turn's content.
        label: The label the turn travels with (claims vs. hypotheses vs.
            quotes, RFC-0007 §12 rule 3); never a Fact.
        purpose: The stated purpose the turn serves (CM5); assembly
            refuses a turn whose purpose is not the assembly's.
    """

    content: str
    label: HistoryLabel
    purpose: str


@dataclass(frozen=True, slots=True)
class EvidenceLabel:
    """Labeled Evidence on `schema.VerificationOutcome` (RFC-0012 §6 cat. 4; DN-74).

    Evidence enters Context as labeled material carrying the Outcome's
    canonical form — never as verification power, never as a decision
    input, and never through Context as a Fact (CM1; RFC-0006 §14). The
    write boundary that produces this material stays `verification`'s.

    Attributes:
        outcome: The verification Outcome this evidence labels.
        purpose: The stated purpose the evidence serves (CM5).
    """

    outcome: VerificationOutcome
    purpose: str


@dataclass(frozen=True, slots=True)
class SkillMaterialItem:
    """Sanitized, bounded Skill material (RFC-0011 §26; RFC-0012 §6 cat. 5).

    Skill content enters Context only after the sanitization enforcement
    point (`boundaries`, C2); assembly consumes the already-sanitized
    item, and Skill code never enters Context (RFC-0007 §6.12).

    Attributes:
        content: The sanitized, bounded Skill content.
        source: The Skill the material came from.
        purpose: The stated purpose the material serves (CM5).
    """

    content: str
    source: str
    purpose: str


@dataclass(frozen=True, slots=True)
class RoutingMarker:
    """The routing-state marker (RFC-0012 §6 cat. 6, §33; DN-71).

    The minimal state to route the next input: the outstanding-question
    marker and the current decision pointer. Process state, never
    evidence, never truth. The routing transitions are `core`'s (RFC-0002
    §2.5/§2.6); cross-interrupt persistence is RFC-0014's.

    Attributes:
        outstanding_question: The last outstanding Operator question, or
            None when none is outstanding.
        current_decision: The current decision pointer, or None.
    """

    outstanding_question: str | None = None
    current_decision: str | None = None


@dataclass(frozen=True, slots=True)
class Supersession:
    """The §33 supersede-disclose result (RFC-0012 §33; DN-71).

    Attributes:
        active: The routing marker after the new question is applied.
        superseded: The outstanding question that was superseded, or None
            when nothing was superseded (never silently dropped).
        replaced: Whether a supersession (replacement) occurred.
    """

    active: RoutingMarker
    superseded: str | None
    replaced: bool


@dataclass(frozen=True, slots=True)
class Context:
    """A valid working set (RFC-0012 §10), never a source of truth (CM1).

    The six §6 categories as explicit fields in the §12 composition
    order — Facts first with provenance, Goal and scope, bounded history,
    Evidence, Skill material last, routing state folded in. Bounds were
    applied at assembly, not after (CM6); the set holds one Goal and
    never merges across sessions (CM9).

    Attributes:
        facts: The carried Facts with provenance, status, and freshness
            (the only category trusted as Fact, RFC-0007 §9); carried at
            their trust class, never upgraded.
        goal: The one active Goal and its scope.
        history: The bounded, labeled history turns.
        evidence: The labeled verification Outcomes.
        skill_material: The sanitized, bounded Skill material.
        routing: The routing-state marker.
        state: The lifecycle state of the working set (§10).
    """

    facts: tuple[Fact, ...]
    goal: GoalValue
    history: tuple[TurnRecord, ...]
    evidence: tuple[EvidenceLabel, ...]
    skill_material: tuple[SkillMaterialItem, ...]
    routing: RoutingMarker
    state: ContextState


@dataclass(frozen=True, slots=True)
class BoundaryEvent:
    """A deterministic, value-free context-boundary event (DN-70).

    Carries category, size, identity, and kind — never the material
    itself (SC4-compatible). `core` writes these as RFC-0013 §7 cat. 9
    records at the runtime boundary before the material's use (RFC-0013
    §23; RFC-0002 I-13); the package never imports `audit` (CM15).

    Attributes:
        kind: ENTERED, INVALIDATED, or DESTROYED.
        category: The Context category the event concerns.
        identity: A stable, value-free label — the stated purpose the
            material serves, or the invalidation's reason.
        size: The number of items carried in the category (1 for the
            singleton Goal and routing categories).
    """

    kind: BoundaryEventKind
    category: ContextCategory
    identity: str
    size: int


@dataclass(frozen=True, slots=True)
class Disclosure:
    """A transparent record of what assembly refused or consolidated.

    Consolidation is explicit, never silent (CM6; RFC-0007 S8); excluded
    stale Facts (CM7) and refused unpurposeful material (CM5) are
    disclosed the same way.

    Attributes:
        category: The category the disclosure concerns.
        reason: Why material was refused, excluded, or consolidated.
        count: How many items were affected.
    """

    category: ContextCategory
    reason: str
    count: int


@dataclass(frozen=True, slots=True)
class Assembly:
    """The deterministic result of assembly (RFC-0012 §12; RFC-0007 S7).

    Attributes:
        context: The assembled working set, in the §12 composition order.
        events: The context-boundary events, in §12 order, preceding the
            material's use (RFC-0002 I-13; the cat-9 write is `core`'s).
        disclosures: What was refused, excluded, or consolidated,
            transparently (CM5/CM6/CM7).
    """

    context: Context
    events: tuple[BoundaryEvent, ...]
    disclosures: tuple[Disclosure, ...]


def _disclose(
    disclosures: list[Disclosure],
    category: ContextCategory,
    reason: str,
    count: int,
) -> None:
    """Record a disclosure when anything was affected (CM5/CM6/CM7)."""
    if count:
        disclosures.append(Disclosure(category=category, reason=reason, count=count))


def _carry_facts(
    fact_store: FactStore,
    fact_bound: int,
    disclosures: list[Disclosure],
) -> tuple[tuple[Fact, ...], int]:
    """Carry the fresh Facts from the current set (RFC-0012 §12 rule 1; CM7).

    Stale, Expired, and Unknown-freshness Facts never enter Context: they
    are excluded at the gate and disclosed, and their count marks the
    working set Stale (RFC-0012 §16–§17). Admitted Facts are ordered
    deterministically by collection time and carried most-recent-first,
    bounded to ``fact_bound`` with the overflow disclosed (CM6).
    """
    fresh: list[Fact] = []
    stale = 0
    for fact in fact_store.current.values():
        if fact.freshness.state in _ADMISSIBLE_FRESHNESS:
            fresh.append(fact)
        else:
            stale += 1
    _disclose(disclosures, ContextCategory.FACTS, REASON_STALE_EXCLUDED, stale)
    fresh.sort(
        key=lambda fact: (
            fact.provenance.collected_at,
            fact.scope.subject.name,
            fact.scope.property.name,
        )
    )
    kept = tuple(fresh)
    if len(fresh) > fact_bound:
        kept = tuple(fresh[-fact_bound:])
        _disclose(
            disclosures,
            ContextCategory.FACTS,
            REASON_OVERFLOW,
            len(fresh) - fact_bound,
        )
    return kept, stale


def _admit_material(
    items,
    purpose: str,
    category: ContextCategory,
    bound: int,
    disclosures: list[Disclosure],
    keep_recent: bool,
) -> tuple:
    """Admit the material whose stated purpose is the assembly's (CM5), bounded (CM6).

    An item without the stated purpose is refused and disclosed — nothing
    enters without a purpose in service of the Goal. On overflow, the
    bound is applied at assembly with a transparent disclosure: the most
    recent items survive for time-ordered categories, the head for Skill
    material.
    """
    admitted = []
    refused = 0
    for item in items:
        if item.purpose == purpose:
            admitted.append(item)
        else:
            refused += 1
    _disclose(disclosures, category, REASON_UNPURPOSEFUL, refused)
    if len(admitted) > bound:
        kept = tuple(admitted[-bound:] if keep_recent else admitted[:bound])
        _disclose(disclosures, category, REASON_OVERFLOW, len(admitted) - bound)
    else:
        kept = tuple(admitted)
    return kept


def assemble(
    *,
    goal: GoalValue,
    fact_store: FactStore,
    purpose: str,
    history: tuple[TurnRecord, ...] = (),
    evidence: tuple[EvidenceLabel, ...] = (),
    skill_material: tuple[SkillMaterialItem, ...] = (),
    routing: RoutingMarker | None = None,
    fact_bound: int = DEFAULT_FACT_BOUND,
    history_bound: int = DEFAULT_HISTORY_BOUND,
    evidence_bound: int = DEFAULT_EVIDENCE_BOUND,
    skill_bound: int = DEFAULT_SKILL_BOUND,
) -> Assembly:
    """Assemble a working set deterministically (RFC-0012 §12; RFC-0007 S7).

    A pure function over the explicit boundary inputs (DN-66): the same
    Goal, Fact current set, history, Evidence, Skill material, routing
    marker, purpose, and bounds always yield the same Assembly. It reads
    Facts from ``fact_store`` at their trust class and freshness
    (RFC-0012 §8), applies the §12 composition order and bounds at
    assembly, refuses anything without the stated purpose (CM5), excludes
    stale Facts or marks the set Stale (CM7), and emits the deterministic
    context-boundary events before the material's use (DN-70; RFC-0002
    I-13). No I/O, no provider call, no live session state.

    Args:
        goal: The one active Goal and its scope (CM9).
        fact_store: The Fact current set read from `factlayer`.
        purpose: The stated purpose that bounds what may enter (CM5).
        history: The bounded, already-labeled history turns.
        evidence: The labeled verification Outcomes (DN-74).
        skill_material: The sanitized, bounded Skill material.
        routing: The routing-state marker (RFC-0012 §33); empty when none.
        fact_bound: The Fact size bound (CM6).
        history_bound: The history-turn size bound (CM6).
        evidence_bound: The Evidence size bound (CM6).
        skill_bound: The Skill-material size bound (CM6).

    Returns:
        The deterministic Assembly: the working set, its events, and its
        disclosures.

    Raises:
        ValueError: If the Goal statement is blank, the purpose is blank,
            or a bound is below 1.
    """
    if not goal.statement.strip():
        raise ValueError("a working set needs an active Goal statement (CM9)")
    if not purpose.strip():
        raise ValueError("nothing enters Context without a stated purpose (CM5)")
    for name, value in (
        ("fact_bound", fact_bound),
        ("history_bound", history_bound),
        ("evidence_bound", evidence_bound),
        ("skill_bound", skill_bound),
    ):
        if value < 1:
            raise ValueError(f"{name} must be at least 1 (CM6)")

    disclosures: list[Disclosure] = []

    facts, stale_excluded = _carry_facts(fact_store, fact_bound, disclosures)
    admitted = (
        _admit_material(
            items,
            purpose,
            category,
            bound,
            disclosures,
            keep_recent,
        )
        for items, category, bound, keep_recent in (
            (history, ContextCategory.HISTORY, history_bound, True),
            (evidence, ContextCategory.EVIDENCE, evidence_bound, True),
            (skill_material, ContextCategory.SKILL_MATERIAL, skill_bound, False),
        )
    )
    history_turns, evidence_items, skill_items = admitted

    entered = (
        (ContextCategory.FACTS, len(facts)),
        (ContextCategory.GOAL, 1),
        (ContextCategory.HISTORY, len(history_turns)),
        (ContextCategory.EVIDENCE, len(evidence_items)),
        (ContextCategory.SKILL_MATERIAL, len(skill_items)),
        (ContextCategory.ROUTING_STATE, 1),
    )
    events = [
        BoundaryEvent(
            kind=BoundaryEventKind.ENTERED,
            category=category,
            identity=purpose,
            size=size,
        )
        for category, size in entered
        if size
    ]
    if stale_excluded:
        events.append(
            BoundaryEvent(
                kind=BoundaryEventKind.INVALIDATED,
                category=ContextCategory.FACTS,
                identity=REASON_STALE_EXCLUDED,
                size=stale_excluded,
            )
        )

    consolidated = any(
        disclosure.reason == REASON_OVERFLOW for disclosure in disclosures
    )
    if stale_excluded:
        state = ContextState.STALE
    elif consolidated:
        state = ContextState.CONSOLIDATED
    else:
        state = ContextState.CURRENT

    context = Context(
        facts=facts,
        goal=goal,
        history=history_turns,
        evidence=evidence_items,
        skill_material=skill_items,
        routing=RoutingMarker() if routing is None else routing,
        state=state,
    )
    return Assembly(
        context=context,
        events=tuple(events),
        disclosures=tuple(disclosures),
    )


def mark_stale(context: Context, *, reason: str) -> tuple[Context, BoundaryEvent]:
    """Mark the working set Stale, recording the invalidation (CM8; RFC-0012 §17).

    Consumes the state-change or freshness-lapse event as an explicit
    input (the reason) and returns the set marked Stale together with the
    deterministic invalidation event that `core` writes before any use
    (RFC-0002 I-13). Stale Context is rebuilt, never patched (RFC-0012
    §16.2): this marks and records only; re-assembly is the only forward
    path. A set already Stale is refused — it is rebuilt, not re-marked —
    and an unstated reason is refused (RFC-0012 §17).

    Args:
        context: The working set to mark Stale; never mutated.
        reason: Why the set is invalidated (state change, freshness
            lapse, interruption, or contradiction; RFC-0012 §17).

    Returns:
        The set with state STALE and its INVALIDATED boundary event.

    Raises:
        ValueError: If the set is already Stale or the reason is blank.
    """
    if context.state is ContextState.STALE:
        raise ValueError(
            "a Stale working set is rebuilt, never re-marked (RFC-0012 §16.2)"
        )
    if not reason.strip():
        raise ValueError("an invalidation must state its reason (RFC-0012 §17)")
    stale = replace(context, state=ContextState.STALE)
    event = BoundaryEvent(
        kind=BoundaryEventKind.INVALIDATED,
        category=ContextCategory.FACTS,
        identity=reason,
        size=len(context.facts),
    )
    return stale, event


def supersede_question(marker: RoutingMarker, question: str) -> Supersession:
    """The §33 supersede-disclose semantics (RFC-0012 §33; DN-71).

    A new Operator question supersedes the outstanding-question marker;
    the superseded question is disclosed as superseded — never silently
    dropped (RFC-0002 Q12) — and the new question becomes active. A reply
    that is the same question routes against the marker unchanged, and a
    first question when none is outstanding becomes active with nothing
    superseded. Deterministic and value-free.

    Args:
        marker: The routing marker being superseded.
        question: The new Operator question.

    Returns:
        The active marker and the disclosed superseded question, if any.

    Raises:
        ValueError: If the question is blank.
    """
    if not question.strip():
        raise ValueError("a routing question must be stated (RFC-0012 §33)")
    active = RoutingMarker(
        outstanding_question=question,
        current_decision=marker.current_decision,
    )
    old = marker.outstanding_question
    if old is not None and old != question:
        return Supersession(active=active, superseded=old, replaced=True)
    if old is None:
        return Supersession(active=active, superseded=None, replaced=False)
    return Supersession(active=marker, superseded=None, replaced=False)
