"""Deterministic Provider View derivation (RFC-0010 §3, §11; RFC-0012 §13,
§27; RFC-0007 §12; RFC-0002 I-4).

Owner: RFC-0010 §3 (Provider Inputs), §11 (Context Boundary); RFC-0012 §13
    (the Context → Provider View boundary).
Responsibility: the pure, deterministic projection from the assembled
    Context to the Provider View — the only outward channel (PR14;
    RFC-0007 T3). The View derives exactly the RFC-0010 §3 elements the
    Context already holds — Operator Goal, evidence/Allowed Context,
    Conversation State, and the routing-state marker (DN-68, Q4) — and
    nothing else (no Audit, no secrets, no raw output, no provider
    identity). It never invents information, never reasons, never
    classifies, never sanitizes, never verifies, and never calls a
    provider: it selects the already-sanitized (`boundaries`, C2),
    already-bounded and purpose-limited (`assemble`, C1), already-labeled
    Context material into an immutable, disposable semantic
    representation (RFC-0007 §12). The shape is reported here; the
    presentation *form* is RFC-0015's and the final signatures RFC-0020's
    (DN-1). Malformed or unsupported input fails closed with an explicit
    refusal — a Stale working set is rebuilt, never projected (RFC-0012
    §16.2; RFC-0002 §2.4 → Awaiting Input) — disclosed, not silent
    (RFC-0001 §8.12).
Forbidden responsibility: no secret value (SC3 — Context is secret-free
    by the enforcement point at entry, SC2/CM4); no decision about what
    the provider may see beyond what Context already holds (the
    purpose-limit and bounds are applied at assembly, CM5/CM6); no I/O,
    no serialization, no transport, no persistence, no clock read, no
    randomness, no identifiers, no event emission, never the Audit
    (CM15).
"""

from dataclasses import dataclass
from enum import Enum, auto

from episky.context.assemble import (
    Context,
    ContextState,
    EvidenceLabel,
    GoalValue,
    RoutingMarker,
    TurnRecord,
)
from episky.schema.fact import Fact

__all__ = [
    "ProviderView",
    "ProviderViewOutcome",
    "ViewDisposition",
    "ViewRefusal",
    "derive",
]


class ViewDisposition(Enum):
    """Whether the projection derived a View or refused (fail-closed).

    Members:
        DERIVED: The Context projected to a usable Provider View.
        REFUSED: No usable View was built; the refusal is disclosed
            (RFC-0002 §2.4).
    """

    DERIVED = auto()
    REFUSED = auto()


class ViewRefusal(Enum):
    """The deterministic refusal reasons, disclosed not silent (RFC-0001 §8.12).

    Members:
        STALE_WORKING_SET: The set is Stale; it is rebuilt, never
            projected (RFC-0012 §16.2; RFC-0002 §2.4 — the caller
            discloses and returns to Awaiting Input).
        MALFORMED: The set is structurally invalid (a blank Goal
            statement) and fails closed.
    """

    STALE_WORKING_SET = auto()
    MALFORMED = auto()


@dataclass(frozen=True, slots=True)
class ProviderView:
    """The immutable Provider View (RFC-0010 §3; RFC-0007 §12).

    The only outward representation of Context (PR14), carrying exactly
    the §3 elements the Context holds — and nothing else. An immutable
    semantic representation only: no serialization, no transport, no
    request, no persistence. Deterministic for a deterministic Context:
    the same Context always yields the same View (RFC-0007 S7).

    Attributes:
        goal: The Operator Goal (RFC-0010 §3) — the active Goal
            statement and scope.
        facts: The Allowed Context (RFC-0010 §3) — the bounded,
            purpose-limited Facts assembled from the Fact Layer.
        history: The Conversation State (RFC-0010 §3) — the structured,
            labeled record of the current reasoning thread.
        evidence: The Provider View evidence (RFC-0010 §3) — the labeled
            verification Outcomes (RFC-0012 §6 cat. 4).
        routing: The routing-state marker (RFC-0012 §6 cat. 6).
    """

    goal: GoalValue
    facts: tuple[Fact, ...]
    history: tuple[TurnRecord, ...]
    evidence: tuple[EvidenceLabel, ...]
    routing: RoutingMarker


@dataclass(frozen=True, slots=True)
class ProviderViewOutcome:
    """The deterministic result of projection (fail-loud).

    Attributes:
        view: The derived View, or None when refused.
        disposition: DERIVED or REFUSED.
        refusal: The deterministic refusal reason, None when derived.
        reason: Why the View was derived or refused (fail-loud).
    """

    view: ProviderView | None
    disposition: ViewDisposition
    refusal: ViewRefusal | None
    reason: str


def derive(context: Context) -> ProviderViewOutcome:
    """Project the assembled Context to the Provider View (RFC-0010 §3; PR14).

    A pure projection from Context: it selects the §3 elements the set
    already holds — goal, facts, history, evidence, routing — in the
    Context's deterministic order, and invents nothing. It refuses a
    Stale working set (rebuilt, never projected; RFC-0012 §16.2) and a
    blank Goal statement (malformed), disclosing the reason rather than
    building a View that cannot be used (RFC-0002 §2.4). No I/O, no
    provider call, no serialization, no clock read, no hidden state.

    Args:
        context: The assembled working set to project; never mutated.

    Returns:
        The ProviderViewOutcome: the immutable View carrying exactly the
        §3 elements, or the explicit refusal disclosing why no usable
        View was built.
    """
    if context.state is ContextState.STALE:
        return ProviderViewOutcome(
            view=None,
            disposition=ViewDisposition.REFUSED,
            refusal=ViewRefusal.STALE_WORKING_SET,
            reason="a Stale working set is rebuilt, never projected (RFC-0012 §16.2)",
        )
    if not context.goal.statement.strip():
        return ProviderViewOutcome(
            view=None,
            disposition=ViewDisposition.REFUSED,
            refusal=ViewRefusal.MALFORMED,
            reason="a Provider View needs an active Goal statement (RFC-0010 §3)",
        )
    view = ProviderView(
        goal=context.goal,
        facts=context.facts,
        history=context.history,
        evidence=context.evidence,
        routing=context.routing,
    )
    return ProviderViewOutcome(
        view=view,
        disposition=ViewDisposition.DERIVED,
        refusal=None,
        reason="projected from the assembled Context (PR14)",
    )
