"""Render — the presentable state, the boundary trace, and the presentation tone.

Owner: RFC-0001 §5 (Presentation).
Responsibility: derive the semantic presentation of a `core` ``LoopStep`` (the
    session state, the honest disclosure trace, the boundary records, and the
    consultations) and translate the record-carried risk-class/gate *names*
    into a closed presentation tone. The presented model is in-memory semantic
    structure only (DN-97); the visual/layout binding is RFC-0015's.
Forbidden responsibility: never classifies, gates, decides, or mints (RFC-0004
    §7: Presentation not an actor); a tone never alters a gate (RFC-0001 §5);
    never renders raw provider/skill/machine data (I-4/I-5/I-7); never a secret
    value (RFC-0009 SC2); no I/O, no clock, no randomness (DN-55/DN-103).
Layer 7 (blueprint §4.1). Imports: core (the LoopStep boundary trace).
"""

from dataclasses import dataclass
from enum import Enum

from episky.core.consultation import Subsystem
from episky.core.events import EventKind, RecordCategory
from episky.core.loop import LoopStep
from episky.core.state_machine import State

__all__ = [
    "Presented",
    "PresentedConsultation",
    "PresentedEvent",
    "PresentedState",
    "Tone",
    "present",
    "tone_for",
]


class Tone(Enum):
    """The closed presentation-tone vocabulary (DN-101).

    RFC-0001 §5 translates risk levels into presentation tone; the §6 "silent"
    and "notify" words are presentation faces of ``AUTO_PERMITTED`` (RFC-0008
    §6). The tones are the semantic vocabulary RFC-0015 will bind to layout and
    color; they are presentation-only and never a policy judgment (RFC-0004
    §7).

    Members:
        NEUTRAL: No risk context to convey — an auto-permitted or read-only
            presentation.
        NOTICE: A routine confirmation — a confirm-gated presentation.
        WARNING: A consequential confirmation — a confirm-with-warning-gated
            presentation.
        CRITICAL: A destructive or blocked presentation.
    """

    NEUTRAL = "neutral"
    NOTICE = "notice"
    WARNING = "warning"
    CRITICAL = "critical"


#: The canonical gate names → tone (RFC-0008 §6; the names the records carry,
#: RFC-0013 §7 cat. 4). The gate is the decision-time label and takes
#: precedence over the risk class.
_GATE_TONE: dict[str, Tone] = {
    "auto-permitted": Tone.NEUTRAL,
    "confirm": Tone.NOTICE,
    "confirm-with-warning": Tone.WARNING,
    "blocked": Tone.CRITICAL,
}

#: The canonical risk-class names → tone (RFC-0008 §6; RFC-0013 §7 cat. 4).
_RISK_TONE: dict[str, Tone] = {
    "read-only": Tone.NEUTRAL,
    "benign": Tone.NOTICE,
    "consequential": Tone.WARNING,
    "destructive": Tone.CRITICAL,
}


def tone_for(risk_class: str | None, gate: str | None) -> Tone:
    """The presentation tone for the record-carried risk-class/gate names.

    The gate name (the decision-time label) takes precedence; the risk-class
    name is the fallback; with neither, or with a name outside the canonical
    vocabulary, the tone is neutral — the CLI never invents a severity it
    cannot support (I-9). Total, deterministic (RFC-0007 S7), and
    presentation-only: a tone never changes a gate, mints, or blocks
    (RFC-0001 §5; RFC-0004 §7).
    """
    if gate is not None:
        return _GATE_TONE.get(gate, Tone.NEUTRAL)
    if risk_class is not None:
        return _RISK_TONE.get(risk_class, Tone.NEUTRAL)
    return Tone.NEUTRAL


@dataclass(frozen=True, slots=True)
class PresentedState:
    """The presented session state (RFC-0001 §5: render the current state).

    ``state`` is the canonical RFC-0002 state name; ``goal`` the adopted goal
    statement (held verbatim, RFC-0003 §2.6); ``disclosures`` the honest I-9
    disclosure trace the runtime emitted; ``tone`` the presentation tone
    derived from the record-carried risk names. All corpus vocabulary — the
    friendly labels and layout are RFC-0015's (DN-97).
    """

    state: State
    goal: str | None
    disclosures: tuple[str, ...]
    tone: Tone


@dataclass(frozen=True, slots=True)
class PresentedEvent:
    """One boundary record presented (RFC-0013 §7; metadata only, SC4).

    The category, kind, and boundary states of a record written at the
    boundary — never material, never a secret value (RFC-0013 §10; SC4).
    """

    category: RecordCategory
    kind: EventKind
    from_state: State
    to_state: State


@dataclass(frozen=True, slots=True)
class PresentedConsultation:
    """One consultation presented (RFC-0002 §6).

    Which subsystem was consulted in which state; the CLI presents it, it
    never re-runs or re-decides it.
    """

    subsystem: Subsystem
    state: State


@dataclass(frozen=True, slots=True)
class Presented:
    """The semantic presentation of one `core` ``LoopStep`` (RFC-0001 §5).

    The in-memory, deterministic, I/O-free presentable model (DN-97/DN-103):
    the current state, the boundary records just written, and the
    consultations, derived from the owned surfaces only (DN-98).
    """

    state: PresentedState
    events: tuple[PresentedEvent, ...]
    consultations: tuple[PresentedConsultation, ...]


def present(
    step: LoopStep,
    *,
    risk_class: str | None = None,
    gate: str | None = None,
) -> Presented:
    """Derive the presentable model from one `core` ``LoopStep`` (DN-98).

    The tone is ``tone_for(risk_class, gate)``; in the product the names come
    from the approval/classification record at the boundary (RFC-0013 §7 cat.
    3/4). Derived from the owned boundary trace only — never raw provider/
    skill/machine data (I-4/I-5/I-7). Deterministic: identical steps and names
    yield identical presentations (RFC-0007 S7).
    """
    session = step.session
    state = PresentedState(
        state=session.state,
        goal=session.goal,
        disclosures=step.disclosures,
        tone=tone_for(risk_class, gate),
    )
    events = tuple(
        PresentedEvent(
            category=write.category,
            kind=write.kind,
            from_state=write.from_state,
            to_state=write.to_state,
        )
        for write in step.writes
    )
    consultations = tuple(
        PresentedConsultation(subsystem=consult.subsystem, state=consult.state)
        for consult in step.consultations
    )
    return Presented(state=state, events=events, consultations=consultations)
