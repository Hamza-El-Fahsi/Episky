"""The RFC-0002 §6 component-consultation rules, as data (RFC-0002 §5, §6;
I-4; RFC-0010 PR14; DN-93).

Owner: RFC-0002 §5 (the Session Loop — the ordered sequence in which
    subsystems participate) and §6 (Component Consultation Rules — when each
    subsystem is consulted, and when it is never consulted); RFC-0002 I-4
    (the LLM is only ever consulted through a Provider View); RFC-0010 §3/PR14
    (the Provider View is the only channel).
Responsibility: the §6 consult matrix as immutable data — the ``CONSULTED``
    and ``NEVER`` sets for every state; the LLM "when" (Diagnosis, Planning,
    Replanning, and only after a fresh Context Building has produced a
    provider view, DN-93); the Skill "when" (Diagnosis, Planning, Machine
    Inspection); the Deterministic-tools "when" (Machine Inspection,
    Verification, state re-assessment); the Executor "only in Executing".
    ``may_consult`` is the never-rule gate (a consultation the §6 matrix
    forbids in the current state is refused). ``may_consult_provider`` is the
    fresh-View rule (DN-93): a cognitive consultation is allowed only when the
    current Provider View covers the current facts, otherwise Context Building
    is re-entered first (RFC-0002 §6; I-4). ``skills_consultable`` and
    ``diagnostics_consultable`` answer the Skill/Collector "when".
Forbidden responsibility: no routing decisions, no transition logic, no
    authority grant (RFC-0004 §4.3) — this module only states who may be
    consulted where; ``loop.py`` (the conductor) enforces it. No I/O, no
    clock, no randomness, no hidden state (DN-55; DN-94).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum, auto
from types import MappingProxyType

from episky.core.state_machine import State

__all__ = [
    "CONSULTED",
    "DIAGNOSTICS_CONSULTED_STATES",
    "EXECUTOR_CONSULTED_STATES",
    "NEVER",
    "PROVIDER_CONSULTED_STATES",
    "SKILL_CONSULTED_STATES",
    "Subsystem",
    "consultation_refusal",
    "diagnostics_consultable",
    "may_consult",
    "may_consult_provider",
    "provider_consultation_allowed",
    "skills_consultable",
]


class Subsystem(Enum):
    """The §6 components a session phase may consult (RFC-0002 §6).

    Members:
        PROVIDER: The LLM, reached only through a Provider View (I-4).
        SKILLS: Authenticated, gate-bound Skills.
        DIAGNOSTICS: The Diagnostics & Fact Layer — the only reader of the
            machine.
        POLICY: The Approval & Policy Engine.
        EXECUTOR: The sanctioned Action runner.
        CONTEXT: The Context & Memory subsystem (assembly).
        AUDIT: The Audit & Transcript recordkeeper.
        PRESENTATION: The TUI surface.
    """

    PROVIDER = auto()
    SKILLS = auto()
    DIAGNOSTICS = auto()
    POLICY = auto()
    EXECUTOR = auto()
    CONTEXT = auto()
    AUDIT = auto()
    PRESENTATION = auto()


#: The states the LLM may be consulted in (RFC-0002 §6): Diagnosis, Planning,
#: Replanning — and only after a fresh Context Building (DN-93).
PROVIDER_CONSULTED_STATES: frozenset[State] = frozenset(
    {State.DIAGNOSING, State.PLANNING, State.REPLANNING}
)

#: The states Skills may be consulted in (RFC-0002 §6): Diagnosis, Planning,
#: Machine Inspection.
SKILL_CONSULTED_STATES: frozenset[State] = frozenset(
    {State.DIAGNOSING, State.PLANNING, State.INSPECTING}
)

#: The states the Deterministic tools may be consulted in (RFC-0002 §6):
#: Machine Inspection (collection), Verification (re-check), and state
#: re-assessment after interruption.
DIAGNOSTICS_CONSULTED_STATES: frozenset[State] = frozenset(
    {State.INSPECTING, State.VERIFYING, State.INTERRUPTED}
)

#: The Executor is consulted only in Executing (RFC-0002 §6), and only with
#: a valid, re-validated approval token (I-1, I-11; DN-89).
EXECUTOR_CONSULTED_STATES: frozenset[State] = frozenset({State.EXECUTING})

#: Which subsystems may be consulted in each state (§5/§6).
CONSULTED: Mapping[State, frozenset[Subsystem]] = MappingProxyType(
    {
        State.INITIALIZING: frozenset(),
        State.IDLE: frozenset(),
        State.INSPECTING: frozenset({Subsystem.DIAGNOSTICS, Subsystem.SKILLS}),
        State.BUILDING: frozenset({Subsystem.CONTEXT}),
        State.DIAGNOSING: frozenset({Subsystem.PROVIDER, Subsystem.SKILLS}),
        State.PLANNING: frozenset({Subsystem.PROVIDER, Subsystem.SKILLS}),
        State.AWAITING_APPROVAL: frozenset({Subsystem.POLICY, Subsystem.PRESENTATION}),
        State.EXECUTING: frozenset({Subsystem.EXECUTOR}),
        State.VERIFYING: frozenset({Subsystem.DIAGNOSTICS}),
        State.REPLANNING: frozenset({Subsystem.PROVIDER, Subsystem.SKILLS}),
        State.AWAITING_INPUT: frozenset({Subsystem.CONTEXT, Subsystem.PRESENTATION}),
        State.INTERRUPTED: frozenset({Subsystem.DIAGNOSTICS}),
        State.COMPLETED: frozenset(),
        State.FAILED: frozenset(),
        State.CANCELLED: frozenset(),
        State.END: frozenset(),
    }
)

#: Which subsystems must never be consulted in each state (§5/§6). The LLM is
#: never consulted in Machine Inspection, Context Building, Awaiting Approval,
#: Executing, or Verification; the Executor never outside Executing; Policy
#: never to design a plan or interpret evidence; Diagnostics never to design,
#: classify, or interpret.
NEVER: Mapping[State, frozenset[Subsystem]] = MappingProxyType(
    {
        State.INITIALIZING: frozenset(
            {
                Subsystem.PROVIDER,
                Subsystem.SKILLS,
                Subsystem.DIAGNOSTICS,
                Subsystem.POLICY,
                Subsystem.EXECUTOR,
            }
        ),
        State.IDLE: frozenset(
            {
                Subsystem.PROVIDER,
                Subsystem.SKILLS,
                Subsystem.DIAGNOSTICS,
                Subsystem.POLICY,
                Subsystem.EXECUTOR,
            }
        ),
        State.INSPECTING: frozenset(
            {Subsystem.PROVIDER, Subsystem.POLICY, Subsystem.EXECUTOR}
        ),
        State.BUILDING: frozenset(
            {
                Subsystem.PROVIDER,
                Subsystem.SKILLS,
                Subsystem.DIAGNOSTICS,
                Subsystem.POLICY,
                Subsystem.EXECUTOR,
            }
        ),
        State.DIAGNOSING: frozenset(
            {Subsystem.DIAGNOSTICS, Subsystem.POLICY, Subsystem.EXECUTOR}
        ),
        State.PLANNING: frozenset(
            {Subsystem.DIAGNOSTICS, Subsystem.POLICY, Subsystem.EXECUTOR}
        ),
        State.AWAITING_APPROVAL: frozenset(
            {
                Subsystem.PROVIDER,
                Subsystem.SKILLS,
                Subsystem.DIAGNOSTICS,
                Subsystem.EXECUTOR,
            }
        ),
        State.EXECUTING: frozenset(
            {
                Subsystem.PROVIDER,
                Subsystem.SKILLS,
                Subsystem.DIAGNOSTICS,
                Subsystem.POLICY,
                Subsystem.CONTEXT,
            }
        ),
        State.VERIFYING: frozenset(
            {Subsystem.PROVIDER, Subsystem.SKILLS, Subsystem.POLICY, Subsystem.EXECUTOR}
        ),
        State.REPLANNING: frozenset(
            {Subsystem.DIAGNOSTICS, Subsystem.POLICY, Subsystem.EXECUTOR}
        ),
        State.AWAITING_INPUT: frozenset(
            {
                Subsystem.PROVIDER,
                Subsystem.SKILLS,
                Subsystem.DIAGNOSTICS,
                Subsystem.POLICY,
                Subsystem.EXECUTOR,
            }
        ),
        State.INTERRUPTED: frozenset(
            {Subsystem.PROVIDER, Subsystem.SKILLS, Subsystem.POLICY, Subsystem.EXECUTOR}
        ),
        State.COMPLETED: frozenset(Subsystem),
        State.FAILED: frozenset(Subsystem),
        State.CANCELLED: frozenset(Subsystem),
        State.END: frozenset(Subsystem),
    }
)


@dataclass(frozen=True, slots=True)
class consultation_refusal:
    """Why a consultation is refused (the §6 matrix, or the DN-93 fresh-View rule).

    Attributes:
        subsystem: The subsystem the consultation would have consulted.
        state: The session state the consultation was requested in.
        reason: The deterministic, fail-loud refusal (RFC-0001 §8).
    """

    subsystem: Subsystem
    state: State
    reason: str


def may_consult(state: State, subsystem: Subsystem) -> consultation_refusal | None:
    """None iff §6 allows ``subsystem`` to be consulted in ``state``.

    The never-rule gate: ``CONSULTED`` is the authoritative "may" set — a
    subsystem not listed for the state is refused, both the explicit
    ``NEVER`` forbiddances and the resting, outcome, and terminal states
    where nothing is consulted (RFC-0002 §5/§6).
    """
    if subsystem in CONSULTED[state]:
        return None
    return consultation_refusal(
        subsystem=subsystem,
        state=state,
        reason=f"{subsystem.name} is never consulted in {state.name} (RFC-0002 §6)",
    )


def provider_consultation_allowed(
    state: State, *, view_is_fresh: bool
) -> consultation_refusal | None:
    """None iff the LLM may be consulted in ``state`` with a fresh view.

    The §6 "when" plus the DN-93 fresh-View rule: the LLM is consulted only in
    Diagnosis, Planning, and Replanning, and only after a fresh Context
    Building has produced a Provider View that covers the current facts.
    """
    if state not in PROVIDER_CONSULTED_STATES:
        return consultation_refusal(
            subsystem=Subsystem.PROVIDER,
            state=state,
            reason=f"the LLM is never consulted in {state.name} (RFC-0002 §6)",
        )
    if not view_is_fresh:
        return consultation_refusal(
            subsystem=Subsystem.PROVIDER,
            state=state,
            reason=(
                "a fresh Context Building must produce a Provider View before "
                "a cognitive consultation (DN-93; RFC-0002 I-4)"
            ),
        )
    return None


def may_consult_provider(
    state: State, *, view_is_fresh: bool
) -> consultation_refusal | None:
    """Alias of :func:`provider_consultation_allowed` (the loop's gate)."""
    return provider_consultation_allowed(state, view_is_fresh=view_is_fresh)


def skills_consultable(state: State) -> bool:
    """True iff Skills may be consulted in ``state`` (RFC-0002 §6)."""
    return state in SKILL_CONSULTED_STATES


def diagnostics_consultable(state: State) -> bool:
    """True iff the Deterministic tools may be consulted in ``state`` (§6)."""
    return state in DIAGNOSTICS_CONSULTED_STATES
