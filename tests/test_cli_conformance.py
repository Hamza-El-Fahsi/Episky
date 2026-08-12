"""Layer-7 presentation conformance (RFC-0004 §7; RFC-0001 §5; design-review
§14 C4).

Iteration 12 Commit C4 behavioral oracle. The CLI is a Presentation-only cell:
it never classifies, never gates, never issues or blocks, never executes,
never touches a secret value, never decides policy (RFC-0004 §7). This oracle
asserts that guarantee on the *behavior* of the presentation surface,
complementing the structural import oracle (``test_cli_imports.py``):

  - ``present()`` derives the presented model from the step's owned surfaces
    verbatim (DN-98) — never recomputed, never invented (I-9).
  - the presented types carry no actor-authority field: no gate, token,
    block, classification, issuance, execution, verification, or secret
    value can be presented (RFC-0004 §7; SC4).
  - a Tone is presentation-only: it can never change the step's state,
    goal, boundaries, or consultations (RFC-0001 §5; RFC-0004 §7).
  - ``present()``/``tone_for()`` are deterministic (RFC-0007 S7).
  - only `cli` imports `core` (the AST edge, re-asserted here).

Deterministic (RFC-0007 S7), I/O-free (DN-103).
"""

import ast
import pathlib

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

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parents[1] / "src" / "episky"


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
    return LoopStep(
        session=overrides.get("session", _session()),
        work=overrides.get("work", Workstate()),
        writes=overrides.get("writes", (_approval_write(),)),
        consultations=overrides.get("consultations", (_consultation(),)),
        disclosures=overrides.get("disclosures", ("degraded mode: facts only",)),
    )


# ---------------------------------------------------------------------------
# The presented model is derived verbatim from the step's owned surfaces
# ---------------------------------------------------------------------------


class TestVerbatimDerivation:
    def test_presented_state_is_the_session_state(self):
        session = _session(state=State.EXECUTING, goal="repair the boot")
        presented = present(_step(session=session))
        assert presented.state.state is State.EXECUTING
        assert presented.state.goal == "repair the boot"
        assert presented.state.disclosures == ("degraded mode: facts only",)

    def test_presented_events_mirror_the_boundary_writes(self):
        presented = present(_step(writes=(_approval_write(),)))
        assert len(presented.events) == 1
        event = presented.events[0]
        assert event.category is RecordCategory.APPROVAL
        assert event.kind is EventKind.OP_APPROVE
        assert event.from_state is State.AWAITING_APPROVAL
        assert event.to_state is State.EXECUTING

    def test_presented_consultations_mirror_the_consultations(self):
        presented = present(_step(consultations=(_consultation(),)))
        assert len(presented.consultations) == 1
        consultation = presented.consultations[0]
        assert consultation.subsystem is Subsystem.PROVIDER
        assert consultation.state is State.DIAGNOSING

    def test_nothing_is_invented_beyond_the_step(self):
        # An empty step presents an empty, honest model — no fabricated
        # events, consultations, or disclosures (I-9).
        presented = present(
            LoopStep(
                session=_session(),
                work=Workstate(),
                writes=(),
                consultations=(),
                disclosures=(),
            )
        )
        assert presented.events == ()
        assert presented.consultations == ()


# ---------------------------------------------------------------------------
# Presentation is not an actor (RFC-0004 §7): no authority, no values
# ---------------------------------------------------------------------------


class TestNoActorAuthority:
    _AUTHORITY_WORDS = (
        "gate",
        "token",
        "block",
        "classif",
        "approv",
        "issu",
        "execut",
        "verif",
        "secret",
        "value",
        "policy",
        "risk",
    )

    @pytest.mark.parametrize(
        "cls", [Presented, PresentedState, PresentedEvent, PresentedConsultation]
    )
    def test_presented_types_carry_no_actor_authority_field(self, cls):
        fields = set(cls.__dataclass_fields__)
        offenders = [
            name
            for name in fields
            if any(word in name for word in self._AUTHORITY_WORDS)
        ]
        assert not offenders, (
            f"{cls.__name__} exposes an actor-authority field: {offenders} "
            "(RFC-0004 §7 — Presentation never classifies, gates, mints, "
            "blocks, executes, or holds a secret)"
        )

    def test_tone_cannot_change_core_derived_material(self):
        step = _step()
        base = present(step, gate="confirm")
        loud = present(step, gate="blocked")
        assert base.state.state == loud.state.state
        assert base.state.goal == loud.state.goal
        assert base.events == loud.events
        assert base.consultations == loud.consultations
        assert base.state.disclosures == loud.state.disclosures
        assert base.state.tone is not loud.state.tone  # presentation-only


# ---------------------------------------------------------------------------
# Determinism (RFC-0007 S7)
# ---------------------------------------------------------------------------


class TestDeterminism:
    def test_present_is_deterministic(self):
        step = _step()
        assert present(step, gate="confirm") == present(step, gate="confirm")

    def test_tone_for_is_total_and_deterministic(self):
        for gate in ("auto-permitted", "confirm", "confirm-with-warning", "blocked"):
            assert isinstance(tone_for(None, gate), Tone)
        for risk in ("read-only", "benign", "consequential", "destructive"):
            assert isinstance(tone_for(risk, None), Tone)
        assert tone_for(None, None) is Tone.NEUTRAL
        assert tone_for("unknown", None) is Tone.NEUTRAL  # never invents (I-9)


# ---------------------------------------------------------------------------
# The AST edge: only `cli` imports `core` (blueprint §4.1)
# ---------------------------------------------------------------------------


def _import_names(source):
    tree = ast.parse(source)
    names = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            names.update(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            names.add(node.module)
    return names


def test_only_cli_imports_core():
    for path in PACKAGE_ROOT.rglob("*.py"):
        if path.parts[-2] in ("episky", "core", "cli"):
            continue
        for module in _import_names(path.read_text(encoding="utf-8")):
            assert not (module == "episky.core" or module.startswith("episky.core.")), (
                f"{path.relative_to(PACKAGE_ROOT)} imports episky.core; only the "
                "TUI (cli) may consume core (blueprint §4.1)"
            )
