"""Deterministic Compare against declared Postconditions.

Owner: RFC-0006 §6 (V3, V7, V10) and §9; ratified decision notes DN-25,
    DN-26, DN-28, DN-29, DN-32, DN-33.
Responsibility: the Compare step over already-normalized Facts — given
    the after-execution Facts and the declared Postconditions (V10),
    produce a per-Postcondition verdict (HELD / NOT_HELD / UNKNOWN /
    CONTRADICTED) with the Facts that determined it (V11 evidence).
    Scope follows the Postconditions (§9.7, DN-28); comparable evidence
    is gated by Fact status (DN-26) and freshness (V4, DN-32);
    contradiction is a comparison-level rule only (V7, DN-33).
Forbidden responsibility: never invokes Collect, never executes,
    never mutates the Fact store (V8, DN-27), never normalizes, never
    verifies trust, never orchestrates, never reads or writes files,
    never skips a Postcondition (V14), never consumes stale Facts (V4),
    never computes confidence (DN-30), never determines the Outcome
    (that is outcome.py).
"""

from collections.abc import Iterable
from dataclasses import dataclass
from enum import Enum, auto

from episky.schema.action import PostCondition
from episky.schema.fact import Fact, FactStatus, FreshnessState

__all__ = ["CompareResult", "PostconditionResult", "PostconditionVerdict", "compare"]


class PostconditionVerdict(Enum):
    """The verdict for a single declared Postcondition (RFC-0006 §9).

    Exhaustive and mutually exclusive for one Postcondition. The
    strictest-wins precedence across Postconditions (Contradicted >
    Verified Failure > Unknown; §7 rule 2) is the outcome module's, not
    this enum's.

    Members:
        HELD: comparable Facts establish exactly the expected value
            (RFC-0006 §9.2).
        NOT_HELD: comparable Facts establish a different value —
            Verified Failure evidence (§7).
        UNKNOWN: no comparable evidence — missing, stale, or excluded
            (V4, V9, V14); never success.
        CONTRADICTED: comparable Facts conflict, or a Contradicted-status
            Fact is present (V7; DN-33).
    """

    HELD = auto()
    NOT_HELD = auto()
    UNKNOWN = auto()
    CONTRADICTED = auto()


@dataclass(frozen=True, slots=True)
class PostconditionResult:
    """The verdict for one declared Postcondition (RFC-0006 §6, §9).

    Frozen and slot-based: a Compare result is immutable and carries no
    behavior (V3, V8).

    Attributes:
        postcondition: The declared Postcondition this verdict is about
            (fixed before Compare, V10).
        verdict: HELD / NOT_HELD / UNKNOWN / CONTRADICTED.
        evidence: The comparable Facts that determined the verdict
            (V11 evidence). Empty when the verdict is UNKNOWN, because
            no Fact was comparable.
    """

    postcondition: PostCondition
    verdict: PostconditionVerdict
    evidence: tuple[Fact, ...]


@dataclass(frozen=True, slots=True)
class CompareResult:
    """The deterministic output of the Compare step (RFC-0006 §6).

    One ``PostconditionResult`` per declared Postcondition, in the
    declared order (V6, V10). Read-only and pure (V8): the same Facts
    produce the same result every time (V3).

    Attributes:
        results: The per-Postcondition verdicts, in Postcondition order.
    """

    results: tuple[PostconditionResult, ...]


def compare(
    facts: Iterable[Fact],
    postconditions: Iterable[PostCondition],
) -> CompareResult:
    """Compare after-execution Facts against the declared Postconditions.

    Deterministic (V3): the Facts are sorted into a canonical order
    before comparison, so the same set of Facts yields the same
    CompareResult regardless of the order they arrive in. The
    Postconditions keep their declared order (V6, V10). Each
    Postcondition is evaluated independently over exactly the Facts in
    its scope — the Facts whose Subject and Property it names (§9.7,
    DN-28); Facts outside every Postcondition scope are never compared.

    A Fact is comparable evidence for a Postcondition only when its
    status is Observed or Verified (DN-26) and its freshness state is
    Current, the factlayer's own determination (V4, F14/F15, DN-32);
    the Postcondition's freshness is the declared bound the comparison
    checks against (RFC-0006 §5, DN-32). When no comparable evidence
    exists, the verdict is UNKNOWN — missing evidence is never success
    (V9) and never skipped (V14).

    Args:
        facts: The after-execution Facts (RFC-0006 §6, Facts step).
        postconditions: The declared expected Postconditions (V10).

    Returns:
        The per-Postcondition verdicts, one per declared Postcondition.
    """
    ordered_facts = tuple(sorted(facts, key=_fact_sort_key))
    declared = tuple(postconditions)
    results = tuple(
        _verdict_for(postcondition, ordered_facts) for postcondition in declared
    )
    return CompareResult(results=results)


def _fact_sort_key(fact: Fact) -> tuple:
    """Canonical total order over Facts, so Compare is deterministic (V3)."""
    scope = fact.scope
    prov = fact.provenance
    return (
        scope.subject.name,
        scope.property.name,
        scope.value.value,
        fact.status.value,
        fact.confidence.name,
        prov.collected_at,
        prov.collector.name,
        prov.collector.version,
        fact.freshness.state.value,
        type(prov.observation).__name__,
        type(fact.machine_identity).__name__,
    )


def _in_scope(fact: Fact, postcondition: PostCondition) -> bool:
    """True if the Fact is within the Postcondition's declared scope (§9.7)."""
    return (
        fact.scope.subject.name == postcondition.subject.name
        and fact.scope.property.name == postcondition.property.name
    )


def _freshness_rank(state: FreshnessState) -> int:
    """Order over freshness states, freshest first (RFC-0005 §12, F14/F15)."""
    if state is FreshnessState.CURRENT:
        return 4
    if state is FreshnessState.POSSIBLY_STALE:
        return 3
    if state is FreshnessState.STALE:
        return 2
    if state is FreshnessState.EXPIRED:
        return 1
    return 0  # UNKNOWN_FRESHNESS


def _is_comparable(fact: Fact, postcondition: PostCondition) -> bool:
    """The status gate (DN-26) and freshness gate (V4, DN-32).

    A Fact is comparable evidence only when its status is Observed or
    Verified and its freshness state is Current — the state factlayer
    already decided (F14/F15); Compare never re-derives staleness. The
    Postcondition's freshness is the declared bound the comparison
    checks against (RFC-0006 §5, DN-32): under the Current gate every
    comparable Fact already satisfies it, so this is a conservative
    guard, not a relaxation.
    """
    if fact.status not in (FactStatus.OBSERVED, FactStatus.VERIFIED):
        return False
    if fact.freshness.state is not FreshnessState.CURRENT:
        return False
    return _freshness_rank(fact.freshness.state) >= _freshness_rank(
        postcondition.freshness.state
    )


def _verdict_for(
    postcondition: PostCondition, facts: tuple[Fact, ...]
) -> PostconditionResult:
    """Determine the verdict for one Postcondition from its scope Facts.

    Precedence within a scope: a Contradicted-status Fact wins (DN-26,
    V7); otherwise conflicting comparable Facts win (DN-33, V7); then
    comparable Facts decide HELD or NOT_HELD against the expected value
    (§9.2); with no comparable evidence the verdict is UNKNOWN (V4, V9,
    V14). Non-comparable Facts are never evidence (DN-26).
    """
    scope_facts = tuple(f for f in facts if _in_scope(f, postcondition))

    contradicted = tuple(f for f in scope_facts if f.status is FactStatus.CONTRADICTED)
    if contradicted:
        return PostconditionResult(
            postcondition, PostconditionVerdict.CONTRADICTED, contradicted
        )

    comparable = tuple(f for f in scope_facts if _is_comparable(f, postcondition))
    if not comparable:
        return PostconditionResult(postcondition, PostconditionVerdict.UNKNOWN, ())

    values = {f.scope.value.value for f in comparable}
    if len(values) > 1:
        return PostconditionResult(
            postcondition, PostconditionVerdict.CONTRADICTED, comparable
        )

    held = comparable[0].scope.value.value == postcondition.expected_value.value
    verdict = PostconditionVerdict.HELD if held else PostconditionVerdict.NOT_HELD
    return PostconditionResult(postcondition, verdict, comparable)
