"""C1 render tests — the presentation model and the tone map (RFC-0001 §5).

Iteration 12 Commit C1. Asserts the ratified readings of design-review §14 C1:
the presentable state is derived from the owned surfaces only (DN-98); the
risk-class/gate → tone map is closed, total, deterministic, and
presentation-only (DN-101); the boundary records are presented metadata-only
(SC4); identical inputs yield identical presentations (RFC-0007 S7). The
presented model is in-memory semantic structure (DN-97); no I/O anywhere
(DN-103).
"""

import pytest

from episky.cli.render import (
    Presented,
    PresentedConsultation,
    PresentedEvent,
    PresentedState,
    Tone,
    present,
    tone_for,
)
from episky.core.consultation import Subsystem
from episky.core.events import AuditRecord, EventKind, RecordCategory
from episky.core.loop import Consultation, LoopStep, Workstate
from episky.core.session import Session
from episky.core.state_machine import State

# ---------------------------------------------------------------------------
# Fixtures: a representative LoopStep boundary trace (owned surfaces only).
# ---------------------------------------------------------------------------


def _session(state=State.AWAITING_APPROVAL, goal="install the nvidia driver"):
    return Session(state=state, goal=goal)


def _approval_write():
    return AuditRecord(
        category=RecordCategory.APPROVAL,
        kind=EventKind.OP_APPROVE,
        from_state=State.AWAITING_APPROVAL,
        to_state=State.EXECUTING,
    )


def _consultation():
    return Consultation(subsystem=Subsystem.PROVIDER, state=State.DIAGNOSING)


def _step(**overrides):
    step = LoopStep(
        session=overrides.get("session", _session()),
        work=overrides.get("work", Workstate()),
        writes=overrides.get("writes", (_approval_write(),)),
        consultations=overrides.get("consultations", (_consultation(),)),
        disclosures=overrides.get("disclosures", ("degraded mode: facts only",)),
    )
    return step


# ---------------------------------------------------------------------------
# Tone map (Q6 / DN-101)
# ---------------------------------------------------------------------------


class TestToneFor:
    @pytest.mark.parametrize(
        ("gate", "tone"),
        [
            ("auto-permitted", Tone.NEUTRAL),
            ("confirm", Tone.NOTICE),
            ("confirm-with-warning", Tone.WARNING),
            ("blocked", Tone.CRITICAL),
        ],
    )
    def test_gate_names_map_closedly(self, gate, tone):
        assert tone_for(risk_class=None, gate=gate) is tone

    @pytest.mark.parametrize(
        ("risk_class", "tone"),
        [
            ("read-only", Tone.NEUTRAL),
            ("benign", Tone.NOTICE),
            ("consequential", Tone.WARNING),
            ("destructive", Tone.CRITICAL),
        ],
    )
    def test_risk_class_names_map_closedly(self, risk_class, tone):
        assert tone_for(risk_class=risk_class, gate=None) is tone

    def test_gate_takes_precedence_over_risk_class(self):
        assert tone_for(risk_class="destructive", gate="auto-permitted") is Tone.NEUTRAL

    def test_absent_names_are_neutral(self):
        assert tone_for(risk_class=None, gate=None) is Tone.NEUTRAL

    @pytest.mark.parametrize("name", ["", "goal-check", "silent", "notify", "UNKNOWN"])
    def test_out_of_vocabulary_names_fall_back_to_neutral(self, name):
        # Never a fabricated severity (I-9); "silent"/"notify" are RFC-0015
        # presentation faces, not gates (RFC-0008 §6).
        assert tone_for(risk_class=name, gate=None) is Tone.NEUTRAL
        assert tone_for(risk_class=None, gate=name) is Tone.NEUTRAL

    def test_map_is_total_and_deterministic(self):
        for risk_class in (None, "read-only", "benign", "consequential", "destructive"):
            for gate in (
                None,
                "auto-permitted",
                "confirm",
                "confirm-with-warning",
                "blocked",
            ):
                first = tone_for(risk_class=risk_class, gate=gate)
                assert first is tone_for(risk_class=risk_class, gate=gate)
                assert isinstance(first, Tone)


# ---------------------------------------------------------------------------
# The presented state (Q3 / DN-98)
# ---------------------------------------------------------------------------


class TestPresentState:
    def test_state_goal_and_disclosures_come_from_the_trace(self):
        step = _step()
        presented = present(step)
        assert isinstance(presented, Presented)
        assert presented.state.state is step.session.state
        assert presented.state.goal == step.session.goal
        assert presented.state.disclosures == step.disclosures

    def test_tone_is_derived_from_the_record_names(self):
        assert (
            present(_step(), risk_class="destructive", gate="blocked").state.tone
            is Tone.CRITICAL
        )
        assert present(_step(), gate="confirm").state.tone is Tone.NOTICE
        assert present(_step()).state.tone is Tone.NEUTRAL

    def test_boundary_records_are_presented_metadata_only(self):
        presented = present(_step())
        (event,) = presented.events
        assert isinstance(event, PresentedEvent)
        assert event.category is RecordCategory.APPROVAL
        assert event.kind is EventKind.OP_APPROVE
        assert event.from_state is State.AWAITING_APPROVAL
        assert event.to_state is State.EXECUTING

    def test_consultations_are_presented(self):
        (consult,) = present(_step()).consultations
        assert isinstance(consult, PresentedConsultation)
        assert consult.subsystem is Subsystem.PROVIDER
        assert consult.state is State.DIAGNOSING

    def test_empty_trace_is_presentable(self):
        step = LoopStep(
            session=_session(),
            work=Workstate(),
            writes=(),
            consultations=(),
            disclosures=(),
        )
        presented = present(step)
        assert presented.events == ()
        assert presented.consultations == ()
        assert presented.state.disclosures == ()

    def test_never_renders_raw_provider_material(self):
        # A write's metadata is enums only; a presented event cannot carry an
        # arbitrary string (argv, machine state, command text) by construction
        # (SC4; RFC-0013 §10). Presenting an identity-carrying write yields no
        # value-shaped field anywhere in the presented model.
        write = AuditRecord(
            category=RecordCategory.EXECUTION,
            kind=EventKind.ACTION_STARTED,
            from_state=State.EXECUTING,
            to_state=State.EXECUTING,
        )
        presented = present(_step(writes=(write,), consultations=()))
        (event,) = presented.events
        for field in (event.category, event.kind, event.from_state, event.to_state):
            assert isinstance(field, (RecordCategory, EventKind, State))

    def test_presentation_is_deterministic(self):
        step = _step()
        assert present(
            step, risk_class="consequential", gate="confirm-with-warning"
        ) == present(step, risk_class="consequential", gate="confirm-with-warning")
        assert present(step) == present(step)

    def test_presented_state_carries_corpus_vocabulary_only(self):
        presented = present(_step())
        assert isinstance(presented.state, PresentedState)
        assert presented.state.state in State
