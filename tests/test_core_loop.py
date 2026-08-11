"""RFC-0002 §5/§6 loop and consultation conformance (RFC-0002 §5, §6, §9
I-1/I-4/I-11/I-13; RFC-0013 §7, §21/§23; RFC-0010 PR14; DN-86–DN-94).

Behavioral tests for Iteration 11 Commit C3 (`core/consultation.py` + the
`core/loop.py` conductor): the §6 consult matrix as immutable data, and the
session-loop conductor that advances a session through the autonomous phases —
Machine Inspection, Context Building, Diagnosis, Planning, classification and
gating, Execution, Verification, Replanning — until a pause point. The loop is
the deterministic conductor (DN-94): every responder is injected, every
consultation is gated by `consultation.py` (§6; the never-rule), every
cognitive consultation requires a fresh Provider View (DN-93), every boundary
record is written before its consequence and fail-closed (I-13; AU8; DN-88),
and the approval path is classify → gate → token → re-validate → Executor
(I-1/I-11; DN-89). `advance` applies one operator/§4 event; `pump` runs the
autonomous loop to a pause point. Deterministic (RFC-0007 S7), I/O-free
(DN-94), and immutable (frozen/slotted values).
"""

import importlib
import pathlib
import re
from types import MappingProxyType

import pytest

from episky.core.consultation import (
    CONSULTED,
    DIAGNOSTICS_CONSULTED_STATES,
    EXECUTOR_CONSULTED_STATES,
    NEVER,
    PROVIDER_CONSULTED_STATES,
    SKILL_CONSULTED_STATES,
    Subsystem,
    consultation_refusal,
    diagnostics_consultable,
    may_consult,
    may_consult_provider,
    provider_consultation_allowed,
    skills_consultable,
)
from episky.core.events import (
    AuditRecord,
    EventKind,
    OpApprove,
    OpCancel,
    OpExit,
    OpGoal,
    OpInterrupt,
    OpOverride,
    OpRefine,
    OpReject,
    OpReply,
    RecordCategory,
)
from episky.core.loop import (
    Consultation,
    Decision,
    GateResult,
    Inspection,
    Loop,
    LoopStep,
    Reply,
    RunKind,
    RunResult,
    VerifyKind,
    VerifyResult,
    ViewResult,
    Workstate,
    WriteStatus,
    advance,
    pump,
)
from episky.core.session import Prerequisites, Session, Step
from episky.core.state_machine import Refusal, State, permitted

CORE_DIR = pathlib.Path(__file__).resolve().parents[1] / "src" / "episky" / "core"
LOOP_PATH = CORE_DIR / "loop.py"
CONSULTATION_PATH = CORE_DIR / "consultation.py"

EXPECTED_CONSULTATION_SURFACE = {
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
}

EXPECTED_LOOP_SURFACE = {
    "Consultation",
    "Decision",
    "GateResult",
    "Inspection",
    "Loop",
    "LoopStep",
    "Reply",
    "RunKind",
    "RunResult",
    "VerifyKind",
    "VerifyResult",
    "ViewResult",
    "Workstate",
    "WriteStatus",
    "advance",
    "pump",
}

OK = Prerequisites(
    elevation_available=True,
    machine_fingerprint_verified=True,
    audit_writable=True,
)

COGNITIVE = frozenset({State.DIAGNOSING, State.PLANNING, State.REPLANNING})

#: A shared provider-view sentinel so Workstate values compare equal across runs.
VIEW = object()


class Responders:
    """A recording, configurable set of deterministic injected responders (DN-94)."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.inspect_result = Inspection(facts=(1, 2), critical=False, hopeless=False)
        self.view = VIEW
        self.reply = Reply(Decision.GROUNDED, plan=("fix nginx",))
        self.skill_reply = None
        self.gate = GateResult(plan=("fix nginx",), tokens=("t1",), blocked=("b1",))
        self.revalidate_ok = True
        self.run = RunResult(RunKind.SUCCEEDED, steps_remaining=False)
        self.verify_result = VerifyResult(VerifyKind.PASSED, steps_remaining=False)
        self.record_ok = True

    def inspect(self, work: Workstate) -> Inspection:
        self.calls.append(("inspect",))
        return self.inspect_result

    def assemble(self, work: Workstate) -> ViewResult:
        self.calls.append(("assemble",))
        return ViewResult(view=self.view)

    def provider_reply(self, work: Workstate) -> Reply:
        self.calls.append(("provider_reply", work.facts))
        return self.reply

    def skill_plan(self, work: Workstate) -> Reply | None:
        self.calls.append(("skill_plan",))
        return self.skill_reply

    def classify_and_gate(self, plan, work: Workstate) -> GateResult:
        self.calls.append(("classify_and_gate", plan))
        return self.gate

    def revalidate(self, token, work: Workstate) -> bool:
        self.calls.append(("revalidate", token))
        return self.revalidate_ok

    def run_executor(self, token, work: Workstate) -> RunResult:
        self.calls.append(("run_executor", token))
        return self.run

    def verify(self, work: Workstate) -> VerifyResult:
        self.calls.append(("verify",))
        return self.verify_result

    def record(self, record: AuditRecord) -> WriteStatus:
        self.calls.append(("record", record.kind))
        return WriteStatus.OK if self.record_ok else WriteStatus.REFUSED

    def loop(self) -> Loop:
        return Loop(
            inspect=self.inspect,
            assemble=self.assemble,
            provider_reply=self.provider_reply,
            skill_plan=self.skill_plan,
            classify_and_gate=self.classify_and_gate,
            revalidate=self.revalidate,
            run_executor=self.run_executor,
            verify=self.verify,
            record=self.record,
        )


def ready_session() -> Session:
    """A started session with an adopted goal, at Machine Inspection."""
    started = Session.initial().start(OK)
    assert isinstance(started, Session)
    adopted = started.adopt_goal("fix nginx")
    assert isinstance(adopted, Step)
    return adopted.session


def named(writes) -> list[str]:
    return [w.kind.name for w in writes]


# ---------------------------------------------------------------------------
# §6 consult matrix: public surface and structure
# ---------------------------------------------------------------------------


def test_consultation_public_surface_is_exactly_the_owned_vocabulary():
    mod = importlib.import_module("episky.core.consultation")
    assert set(mod.__all__) == EXPECTED_CONSULTATION_SURFACE


def test_consultation_values_are_frozen_slotted_dataclasses():
    params = consultation_refusal.__dataclass_params__
    assert params.frozen
    assert params.slots


def test_consultation_matrices_cover_every_state():
    assert set(CONSULTED) == set(State)
    assert set(NEVER) == set(State)


def test_consultation_matrices_are_immutable_mappings():
    with pytest.raises(TypeError):
        CONSULTED[State.IDLE] = frozenset()  # type: ignore[index]
    with pytest.raises(TypeError):
        NEVER[State.IDLE] = frozenset()  # type: ignore[index]
    assert isinstance(CONSULTED, MappingProxyType)
    assert isinstance(NEVER, MappingProxyType)


def test_consulted_and_never_are_disjoint_in_every_state():
    for state in State:
        assert CONSULTED[state].isdisjoint(NEVER[state]), state.name


# ---------------------------------------------------------------------------
# §6 consult matrix: the "when" sets
# ---------------------------------------------------------------------------


def test_provider_consulted_states_are_the_cognitive_states_only():
    assert (
        frozenset({State.DIAGNOSING, State.PLANNING, State.REPLANNING})
        == PROVIDER_CONSULTED_STATES
    )


def test_skill_consulted_states_include_inspection():
    assert (
        frozenset({State.DIAGNOSING, State.PLANNING, State.INSPECTING})
        == SKILL_CONSULTED_STATES
    )


def test_diagnostics_consulted_states_are_reassessment_points():
    assert (
        frozenset({State.INSPECTING, State.VERIFYING, State.INTERRUPTED})
        == DIAGNOSTICS_CONSULTED_STATES
    )


def test_executor_consulted_states_is_executing_only():
    assert frozenset({State.EXECUTING}) == EXECUTOR_CONSULTED_STATES


def test_consulted_matrix_transcribes_section_5_and_6():
    assert CONSULTED[State.INITIALIZING] == frozenset()
    assert CONSULTED[State.IDLE] == frozenset()
    assert CONSULTED[State.INSPECTING] == frozenset(
        {Subsystem.DIAGNOSTICS, Subsystem.SKILLS}
    )
    assert CONSULTED[State.BUILDING] == frozenset({Subsystem.CONTEXT})
    assert CONSULTED[State.DIAGNOSING] == frozenset(
        {Subsystem.PROVIDER, Subsystem.SKILLS}
    )
    assert CONSULTED[State.PLANNING] == frozenset(
        {Subsystem.PROVIDER, Subsystem.SKILLS}
    )
    assert CONSULTED[State.AWAITING_APPROVAL] == frozenset(
        {Subsystem.POLICY, Subsystem.PRESENTATION}
    )
    assert CONSULTED[State.EXECUTING] == frozenset({Subsystem.EXECUTOR})
    assert CONSULTED[State.VERIFYING] == frozenset({Subsystem.DIAGNOSTICS})
    assert CONSULTED[State.REPLANNING] == frozenset(
        {Subsystem.PROVIDER, Subsystem.SKILLS}
    )
    assert CONSULTED[State.AWAITING_INPUT] == frozenset(
        {Subsystem.CONTEXT, Subsystem.PRESENTATION}
    )
    assert CONSULTED[State.INTERRUPTED] == frozenset({Subsystem.DIAGNOSTICS})
    assert CONSULTED[State.COMPLETED] == frozenset()
    assert CONSULTED[State.FAILED] == frozenset()
    assert CONSULTED[State.CANCELLED] == frozenset()
    assert CONSULTED[State.END] == frozenset()


def test_never_matrix_forbids_the_wrong_consultations():
    assert NEVER[State.INSPECTING] >= frozenset({Subsystem.PROVIDER})
    assert NEVER[State.BUILDING] >= frozenset(
        {Subsystem.PROVIDER, Subsystem.SKILLS, Subsystem.DIAGNOSTICS}
    )
    assert NEVER[State.DIAGNOSING] >= frozenset({Subsystem.DIAGNOSTICS})
    assert NEVER[State.PLANNING] >= frozenset({Subsystem.DIAGNOSTICS})
    assert NEVER[State.AWAITING_APPROVAL] >= frozenset(
        {Subsystem.PROVIDER, Subsystem.SKILLS, Subsystem.EXECUTOR}
    )
    assert NEVER[State.EXECUTING] >= frozenset(
        {Subsystem.PROVIDER, Subsystem.SKILLS, Subsystem.DIAGNOSTICS}
    )
    assert NEVER[State.VERIFYING] >= frozenset(
        {Subsystem.PROVIDER, Subsystem.SKILLS, Subsystem.POLICY, Subsystem.EXECUTOR}
    )
    assert NEVER[State.REPLANNING] >= frozenset({Subsystem.DIAGNOSTICS})
    assert NEVER[State.AWAITING_INPUT] >= frozenset(
        {Subsystem.PROVIDER, Subsystem.SKILLS, Subsystem.DIAGNOSTICS}
    )
    assert NEVER[State.INTERRUPTED] >= frozenset({Subsystem.PROVIDER, Subsystem.SKILLS})
    for terminal in (State.COMPLETED, State.FAILED, State.CANCELLED, State.END):
        assert NEVER[terminal] == frozenset(Subsystem)


# ---------------------------------------------------------------------------
# §6 consult matrix: may_consult
# ---------------------------------------------------------------------------


def test_may_consult_allows_exactly_the_consulted_set():
    for state in State:
        for subsystem in Subsystem:
            allowed = subsystem in CONSULTED[state]
            assert (may_consult(state, subsystem) is None) == allowed, (
                f"{subsystem.name} in {state.name}"
            )


@pytest.mark.parametrize(
    "state,subsystem",
    [
        (State.INSPECTING, Subsystem.PROVIDER),
        (State.BUILDING, Subsystem.SKILLS),
        (State.DIAGNOSING, Subsystem.DIAGNOSTICS),
        (State.PLANNING, Subsystem.POLICY),
        (State.AWAITING_APPROVAL, Subsystem.PROVIDER),
        (State.EXECUTING, Subsystem.DIAGNOSTICS),
        (State.VERIFYING, Subsystem.PROVIDER),
        (State.COMPLETED, Subsystem.PROVIDER),
        (State.END, Subsystem.EXECUTOR),
    ],
)
def test_may_consult_refuses_the_never_rule_fail_loud(state, subsystem):
    refusal = may_consult(state, subsystem)
    assert isinstance(refusal, consultation_refusal)
    assert refusal.subsystem is subsystem
    assert refusal.state is state
    assert subsystem.name in refusal.reason
    assert state.name in refusal.reason


def test_may_consult_is_deterministic_and_pure():
    for state in State:
        for subsystem in Subsystem:
            assert may_consult(state, subsystem) == may_consult(state, subsystem)


# ---------------------------------------------------------------------------
# the fresh-View rule (DN-93) and the "when" helpers
# ---------------------------------------------------------------------------


def test_provider_consultation_requires_a_cognitive_state():
    for state in State:
        if state in PROVIDER_CONSULTED_STATES:
            continue
        refusal = provider_consultation_allowed(state, view_is_fresh=True)
        assert isinstance(refusal, consultation_refusal)
        assert "never consulted" in refusal.reason


def test_provider_consultation_requires_a_fresh_view():
    for state in PROVIDER_CONSULTED_STATES:
        assert provider_consultation_allowed(state, view_is_fresh=True) is None
        refusal = provider_consultation_allowed(state, view_is_fresh=False)
        assert isinstance(refusal, consultation_refusal)
        assert "fresh Context Building" in refusal.reason


def test_may_consult_provider_is_the_loop_gate_alias():
    for state in State:
        for fresh in (True, False):
            assert may_consult_provider(state, view_is_fresh=fresh) == (
                provider_consultation_allowed(state, view_is_fresh=fresh)
            )


def test_skills_consultable_matches_the_skill_when_set():
    for state in State:
        assert skills_consultable(state) == (state in SKILL_CONSULTED_STATES)


def test_diagnostics_consultable_matches_the_diagnostics_when_set():
    for state in State:
        assert diagnostics_consultable(state) == (state in DIAGNOSTICS_CONSULTED_STATES)


def test_consultation_module_holds_no_mutable_module_state():
    mod = importlib.import_module("episky.core.consultation")
    mutable_globals = {
        name
        for name, value in vars(mod).items()
        if isinstance(value, (list, dict, set))
        and not (name.startswith("__") and name.endswith("__"))
    }
    assert not mutable_globals


def test_consultation_module_performs_no_io_and_no_authority():
    src = CONSULTATION_PATH.read_text(encoding="utf-8")
    for token in (
        "import time",
        "time.time",
        "time.monotonic",
        "perf_counter",
        "datetime.now",
        "import random",
        "random.",
        "os.urandom",
        "import uuid",
        "import hmac",
        "import hashlib",
        "import secrets",
        "import subprocess",
        "import os",
        "import socket",
        "import requests",
        "import json",
        "open(",
        "print(",
        "approve(",
        "execute(",
        "classify(",
        "verify(",
        "audit.",
        ".run(",
    ):
        assert token not in src


# ---------------------------------------------------------------------------
# loop structure: surface and value semantics
# ---------------------------------------------------------------------------


def test_loop_public_surface_is_exactly_the_owned_vocabulary():
    mod = importlib.import_module("episky.core.loop")
    assert set(mod.__all__) == EXPECTED_LOOP_SURFACE


def test_loop_values_are_frozen_slotted_dataclasses():
    for cls in (
        Inspection,
        ViewResult,
        Reply,
        GateResult,
        RunResult,
        VerifyResult,
        Consultation,
        Workstate,
        LoopStep,
        Loop,
    ):
        params = cls.__dataclass_params__
        assert params.frozen, cls.__name__
        assert params.slots, cls.__name__


def test_workstate_defaults_are_the_idle_conductor_state():
    work = Workstate()
    assert work.view_is_fresh is False
    assert work.view is None
    assert work.facts is None
    assert work.plan is None
    assert work.tokens == ()
    assert work.blocked == ()
    assert work.token is None
    assert work.route is State.DIAGNOSING
    assert work.presented is False


def test_loop_step_is_a_value():
    r = Responders()
    session = ready_session()
    step = advance(r.loop(), session)
    assert isinstance(step, LoopStep)
    assert step == advance(r.loop(), ready_session())


def test_loop_imports_only_core_modules_and_no_io_modules():
    src = LOOP_PATH.read_text(encoding="utf-8")
    for token in (
        "import episky.audit",
        "import episky.policy",
        "import episky.executor",
        "import episky.providers",
        "import episky.skills",
        "import episky.context",
        "import episky.secrets",
        "import episky.verification",
        "import episky.factlayer",
        "import episky.cli",
        "import time",
        "time.time",
        "time.monotonic",
        "perf_counter",
        "datetime.now",
        "import random",
        "random.",
        "os.urandom",
        "import uuid",
        "import hmac",
        "import hashlib",
        "import secrets",
        "import subprocess",
        "import os",
        "import socket",
        "import requests",
        "import json",
        "open(",
        "print(",
    ):
        assert token not in src


def test_loop_holds_no_mutable_module_state():
    mod = importlib.import_module("episky.core.loop")
    mutable_globals = {
        name
        for name, value in vars(mod).items()
        if isinstance(value, (list, dict, set))
        and not (name.startswith("__") and name.endswith("__"))
    }
    assert not mutable_globals


def test_loop_calls_only_the_injected_seams():
    """The conductor routes; every effectful call goes through the injected
    responders (DN-94), never a real policy/executor/verification module."""
    src = LOOP_PATH.read_text(encoding="utf-8")
    calls = set(re.findall(r"\bloop\.(\w+)\(", src))
    assert calls <= {
        "inspect",
        "assemble",
        "provider_reply",
        "skill_plan",
        "classify_and_gate",
        "revalidate",
        "run_executor",
        "verify",
        "record",
    }, calls
    assert calls == {
        "inspect",
        "assemble",
        "provider_reply",
        "skill_plan",
        "classify_and_gate",
        "revalidate",
        "run_executor",
        "verify",
        "record",
    }


# ---------------------------------------------------------------------------
# advance: operator events (OP_GOAL, OP_EXIT, OP_CANCEL, OP_INTERRUPT)
# ---------------------------------------------------------------------------


def test_advance_op_goal_adopts_with_record_before_consequence():
    r = Responders()
    step = advance(r.loop(), Session(State.IDLE, None), event=OpGoal(), goal="g")
    assert isinstance(step, LoopStep)
    assert step.session.state is State.INSPECTING
    assert step.session.goal == "g"
    assert named(step.writes) == [EventKind.OP_GOAL.name]
    assert step.writes[0].category is RecordCategory.SESSION
    assert step.writes[0].from_state is State.IDLE
    assert step.writes[0].to_state is State.INSPECTING


def test_advance_op_goal_refuses_without_a_goal_statement():
    result = advance(
        Responders().loop(), Session(State.IDLE, None), event=OpGoal(), goal=None
    )
    assert isinstance(result, Refusal)
    assert "goal" in result.reason


def test_advance_op_goal_refuses_while_a_goal_is_active():
    result = advance(
        Responders().loop(),
        Session(State.DIAGNOSING, "in flight"),
        event=OpGoal(),
        goal="second",
    )
    assert isinstance(result, Refusal)


def test_advance_op_goal_from_an_outcome_returns_to_idle():
    step = advance(
        Responders().loop(), Session(State.COMPLETED, "done"), event=OpGoal(), goal="g"
    )
    assert isinstance(step, LoopStep)
    assert step.session.state is State.IDLE
    assert step.session.goal is None


def test_advance_op_exit_reaches_end_from_idle():
    step = advance(Responders().loop(), Session(State.IDLE, None), event=OpExit())
    assert isinstance(step, LoopStep)
    assert step.session.state is State.END
    assert step.writes[0].kind is EventKind.OP_EXIT


def test_advance_op_exit_refuses_from_initialization():
    result = advance(
        Responders().loop(), Session(State.INITIALIZING, None), event=OpExit()
    )
    assert isinstance(result, Refusal)


def test_advance_op_cancel_abandons_the_goal_and_clears_tokens():
    work = Workstate(tokens=("t1",), token=("t1",))
    step = advance(
        Responders().loop(), Session(State.EXECUTING, "g"), work, event=OpCancel()
    )
    assert isinstance(step, LoopStep)
    assert step.session.state is State.CANCELLED
    assert step.session.goal == "g"
    assert step.work.token is None
    assert step.work.tokens == ()
    assert step.writes[0].kind is EventKind.OP_CANCEL


def test_advance_op_interrupt_cognitive_goes_to_awaiting_input():
    step = advance(
        Responders().loop(),
        Session(State.DIAGNOSING, "g"),
        event=OpInterrupt(),
    )
    assert isinstance(step, LoopStep)
    assert step.session.state is State.AWAITING_INPUT


def test_advance_op_interrupt_machine_work_goes_to_interrupted():
    work = Workstate(tokens=("t1",), token=("t1",))
    step = advance(
        Responders().loop(), Session(State.INSPECTING, "g"), work, event=OpInterrupt()
    )
    assert isinstance(step, LoopStep)
    assert step.session.state is State.INTERRUPTED
    assert step.work.token is None
    assert step.work.tokens == ()


# ---------------------------------------------------------------------------
# advance: approval-path operator events (OP_APPROVE / OP_OVERRIDE / OP_REJECT /
# OP_REFINE / OP_REPLY)
# ---------------------------------------------------------------------------


def _awaiting_approval():
    return (
        Session(State.AWAITING_APPROVAL, "g"),
        Workstate(
            tokens=("t1",),
            token=("t1",),
            plan=("fix",),
            blocked=("b1",),
            presented=True,
        ),
    )


def test_advance_op_approve_revalidates_and_reaches_executing():
    session, work = _awaiting_approval()
    r = Responders()
    step = advance(r.loop(), session, work, event=OpApprove())
    assert isinstance(step, LoopStep)
    assert ("revalidate", "t1") in r.calls
    assert step.session.state is State.EXECUTING
    assert step.work.token == ("t1",)
    assert step.work.presented is False
    assert step.writes[0].kind is EventKind.OP_APPROVE
    assert step.writes[0].category is RecordCategory.APPROVAL


def test_advance_op_override_uses_the_override_category():
    session, work = _awaiting_approval()
    step = advance(Responders().loop(), session, work, event=OpOverride())
    assert isinstance(step, LoopStep)
    assert step.session.state is State.EXECUTING
    assert step.writes[0].kind is EventKind.OP_OVERRIDE
    assert step.writes[0].category is RecordCategory.OVERRIDE


def test_advance_op_approve_refuses_outside_awaiting_approval():
    result = advance(
        Responders().loop(),
        Session(State.DIAGNOSING, "g"),
        event=OpApprove(),
    )
    assert isinstance(result, Refusal)


def test_advance_op_approve_refuses_without_a_presented_plan():
    result = advance(
        Responders().loop(),
        Session(State.AWAITING_APPROVAL, "g"),
        Workstate(),
        event=OpApprove(),
    )
    assert isinstance(result, Refusal)
    assert "no presented, classified plan" in result.reason


def test_advance_op_approve_revalidation_failure_reopens_the_plan():
    session, work = _awaiting_approval()
    r = Responders()
    r.revalidate_ok = False
    step = advance(r.loop(), session, work, event=OpApprove())
    assert isinstance(step, LoopStep)
    assert step.session.state is State.INSPECTING
    assert step.work.token is None
    assert step.work.tokens == ()
    assert any("no longer valid" in d for d in step.disclosures)


@pytest.mark.parametrize(
    "event,category",
    [(OpReject(), RecordCategory.PROPOSAL), (OpRefine(), RecordCategory.PROPOSAL)],
)
def test_advance_op_reject_and_op_refine_replan_and_clear_tokens(event, category):
    session, work = _awaiting_approval()
    step = advance(Responders().loop(), session, work, event=event)
    assert isinstance(step, LoopStep)
    assert step.session.state is State.REPLANNING
    assert step.work.token is None
    assert step.work.tokens == ()
    assert step.work.view_is_fresh is False
    assert step.writes[0].kind is event.kind
    assert step.writes[0].category is category


def test_advance_op_reply_routes_through_the_work_route():
    work = Workstate(route=State.PLANNING, view_is_fresh=True)
    step = advance(
        Responders().loop(),
        Session(State.AWAITING_INPUT, "g"),
        work,
        event=OpReply(routes_to=State.DIAGNOSING),
    )
    assert isinstance(step, LoopStep)
    assert step.session.state is State.PLANNING
    assert step.work.view_is_fresh is False
    assert step.writes[0].kind is EventKind.OP_REPLY
    assert step.writes[0].category is RecordCategory.PROPOSAL


def test_advance_op_reply_default_routes_to_diagnosis():
    step = advance(
        Responders().loop(),
        Session(State.AWAITING_INPUT, "g"),
        event=OpReply(routes_to=State.PLANNING),
    )
    assert isinstance(step, LoopStep)
    assert step.session.state is State.DIAGNOSING


# ---------------------------------------------------------------------------
# advance: autonomous phases — Machine Inspection
# ---------------------------------------------------------------------------


def test_advance_inspection_consults_diagnostics_and_collects_facts():
    r = Responders()
    step = advance(r.loop(), ready_session())
    assert isinstance(step, LoopStep)
    assert ("inspect",) in r.calls
    assert step.consultations == (
        Consultation(Subsystem.DIAGNOSTICS, State.INSPECTING),
    )
    assert step.work.facts == (1, 2)
    assert step.work.view_is_fresh is False
    assert step.session.state is State.BUILDING
    assert named(step.writes) == [EventKind.FACTS_COLLECTED.name]
    assert step.writes[0].category is RecordCategory.FACT_LIFECYCLE


def test_advance_inspection_hopeless_fails_closed():
    r = Responders()
    r.inspect_result = Inspection(facts=(), critical=False, hopeless=True)
    step = advance(r.loop(), ready_session())
    assert isinstance(step, LoopStep)
    assert step.session.state is State.FAILED
    assert step.writes[0].kind is EventKind.COLLECTOR_FAILED


def test_advance_inspection_critical_asks_the_operator():
    r = Responders()
    r.inspect_result = Inspection(facts=(), critical=True, hopeless=False)
    step = advance(r.loop(), ready_session())
    assert isinstance(step, LoopStep)
    assert step.session.state is State.AWAITING_INPUT
    assert step.writes[0].kind is EventKind.COLLECTOR_FAILED


# ---------------------------------------------------------------------------
# advance: autonomous phases — Context Building
# ---------------------------------------------------------------------------


def test_advance_building_assembles_a_fresh_view_and_continues_to_the_route():
    r = Responders()
    step = advance(r.loop(), Session(State.BUILDING, "g"))
    assert isinstance(step, LoopStep)
    assert ("assemble",) in r.calls
    assert step.consultations == (Consultation(Subsystem.CONTEXT, State.BUILDING),)
    assert step.work.view is r.view
    assert step.work.view_is_fresh is True
    assert step.session.state is State.DIAGNOSING
    assert step.writes == ()


def test_advance_building_with_no_view_discloses_and_asks_input():
    r = Responders()
    r.view = None
    step = advance(r.loop(), Session(State.BUILDING, "g"))
    assert isinstance(step, LoopStep)
    assert step.session.state is State.AWAITING_INPUT
    assert any("no usable provider view" in d for d in step.disclosures)


# ---------------------------------------------------------------------------
# advance: autonomous phases — cognitive routing
# ---------------------------------------------------------------------------


@pytest.mark.parametrize(
    "decision,target,route",
    [
        (Decision.GROUNDED, State.PLANNING, State.PLANNING),
        (Decision.NEED_EVIDENCE, State.INSPECTING, State.DIAGNOSING),
        (Decision.CLARIFY, State.AWAITING_INPUT, State.DIAGNOSING),
        (Decision.DIAGNOSTIC_ONLY, State.COMPLETED, State.COMPLETED),
        (Decision.HOPELESS, State.FAILED, State.FAILED),
    ],
)
def test_advance_diagnosis_routes_the_decision(decision, target, route):
    r = Responders()
    r.reply = Reply(decision, plan=())
    step = advance(
        r.loop(), Session(State.DIAGNOSING, "g"), Workstate(view_is_fresh=True)
    )
    assert isinstance(step, LoopStep)
    assert step.session.state is target, decision.name
    assert step.work.route is route
    assert step.consultations == (Consultation(Subsystem.PROVIDER, State.DIAGNOSING),)
    assert step.writes[0].kind is EventKind.PROVIDER_RESPONSE


def test_advance_planning_grounded_with_a_plan_classifies_and_gates():
    r = Responders()
    step = advance(
        r.loop(), Session(State.PLANNING, "g"), Workstate(view_is_fresh=True)
    )
    assert isinstance(step, LoopStep)
    assert ("classify_and_gate", ("fix nginx",)) in r.calls
    assert step.session.state is State.AWAITING_APPROVAL
    assert step.work.tokens == ("t1",)
    assert step.work.blocked == ("b1",)
    assert step.work.plan == ("fix nginx",)
    assert step.work.presented is False
    assert step.writes[0].kind is EventKind.PROVIDER_RESPONSE
    assert EventKind.PLAN_READY in [w.kind for w in step.writes]


def test_advance_planning_grounded_with_no_plan_completes_without_classifying():
    r = Responders()
    r.reply = Reply(Decision.GROUNDED, plan=())
    step = advance(
        r.loop(), Session(State.PLANNING, "g"), Workstate(view_is_fresh=True)
    )
    assert isinstance(step, LoopStep)
    assert step.session.state is State.COMPLETED
    assert not any(c[0] == "classify_and_gate" for c in r.calls)
    assert named(step.writes) == [EventKind.PROVIDER_RESPONSE.name]


def test_advance_planning_need_evidence_reenters_inspection():
    r = Responders()
    r.reply = Reply(Decision.NEED_EVIDENCE, plan=())
    step = advance(
        r.loop(), Session(State.PLANNING, "g"), Workstate(view_is_fresh=True)
    )
    assert isinstance(step, LoopStep)
    assert step.session.state is State.INSPECTING
    assert step.work.route is State.PLANNING


def test_advance_replanning_routes_grounded_to_planning():
    r = Responders()
    r.reply = Reply(Decision.GROUNDED, plan=("fix",))
    step = advance(
        r.loop(), Session(State.REPLANNING, "g"), Workstate(view_is_fresh=True)
    )
    assert isinstance(step, LoopStep)
    assert step.session.state is State.PLANNING


def test_advance_replanning_hopeless_fails():
    r = Responders()
    r.reply = Reply(Decision.HOPELESS, plan=())
    step = advance(
        r.loop(), Session(State.REPLANNING, "g"), Workstate(view_is_fresh=True)
    )
    assert isinstance(step, LoopStep)
    assert step.session.state is State.FAILED


def test_advance_cognitive_consultation_requires_a_fresh_view():
    r = Responders()
    step = advance(
        r.loop(),
        Session(State.DIAGNOSING, "g"),
        Workstate(view_is_fresh=False),
    )
    assert isinstance(step, LoopStep)
    assert step.session.state is State.INSPECTING
    assert step.work.route is State.DIAGNOSING
    assert step.consultations == ()
    assert not any(c[0] == "provider_reply" for c in r.calls)


def test_advance_cognitive_skill_reply_precedes_the_provider():
    r = Responders()
    r.skill_reply = Reply(Decision.GROUNDED, plan=("skill plan",))
    step = advance(
        r.loop(), Session(State.DIAGNOSING, "g"), Workstate(view_is_fresh=True)
    )
    assert isinstance(step, LoopStep)
    assert ("skill_plan",) in r.calls
    assert step.consultations == (Consultation(Subsystem.SKILLS, State.DIAGNOSING),)
    assert not any(c[0] == "provider_reply" for c in r.calls)
    assert step.writes == ()


def test_advance_cognitive_degraded_provider_is_facts_only():
    r = Responders()
    r.reply = Reply(Decision.GROUNDED, plan=(), degraded=True)
    step = advance(
        r.loop(), Session(State.DIAGNOSING, "g"), Workstate(view_is_fresh=True)
    )
    assert isinstance(step, LoopStep)
    assert step.session.state is State.AWAITING_INPUT
    assert step.writes[0].kind is EventKind.PROVIDER_RESPONSE
    assert step.writes[1].kind is EventKind.PROVIDER_FALLBACK_FAILED
    assert any("degraded mode" in d for d in step.disclosures)


# ---------------------------------------------------------------------------
# advance: autonomous phases — Execution and Verification
# ---------------------------------------------------------------------------


def test_advance_execution_requires_an_approval_token():
    result = advance(Responders().loop(), Session(State.EXECUTING, "g"), Workstate())
    assert isinstance(result, Refusal)
    assert "no approval token" in result.reason


def test_advance_execution_starts_and_succeeds_into_verification():
    r = Responders()
    work = Workstate(token=("t1",), tokens=("t1",), plan=("fix",))
    step = advance(r.loop(), Session(State.EXECUTING, "g"), work)
    assert isinstance(step, LoopStep)
    assert ("run_executor", ("t1",)) in r.calls
    assert step.consultations == (Consultation(Subsystem.EXECUTOR, State.EXECUTING),)
    assert step.session.state is State.VERIFYING
    assert named(step.writes) == [
        EventKind.ACTION_STARTED.name,
        EventKind.ACTION_SUCCEEDED.name,
    ]


@pytest.mark.parametrize(
    "kind,event_kind,target",
    [
        (RunKind.TIMEOUT, EventKind.ACTION_TIMEOUT, State.INTERRUPTED),
        (RunKind.INTERRUPTED, EventKind.ACTION_INTERRUPTED, State.INTERRUPTED),
        (RunKind.PARTIAL, EventKind.ACTION_PARTIAL, State.INTERRUPTED),
        (RunKind.REBOOT, EventKind.REBOOT_REQUESTED, State.END),
    ],
)
def test_advance_execution_halts_disclose_and_clear_the_token(kind, event_kind, target):
    r = Responders()
    r.run = RunResult(kind, steps_remaining=False)
    work = Workstate(token=("t1",), tokens=("t1",), plan=("fix",))
    step = advance(r.loop(), Session(State.EXECUTING, "g"), work)
    assert isinstance(step, LoopStep)
    assert step.session.state is target, kind.name
    assert step.work.token is None
    assert step.work.tokens == ()
    assert step.writes[1].kind is event_kind
    assert any("state uncertain" in d for d in step.disclosures)


def test_advance_execution_failed_keeps_the_token_through_verification():
    r = Responders()
    r.run = RunResult(RunKind.FAILED)
    work = Workstate(token=("t1",), tokens=("t1",), plan=("fix",))
    step = advance(r.loop(), Session(State.EXECUTING, "g"), work)
    assert isinstance(step, LoopStep)
    assert step.session.state is State.VERIFYING
    assert step.work.token == ("t1",)
    assert step.writes[1].kind is EventKind.ACTION_FAILED


def test_advance_verify_passed_with_no_steps_completes_and_clears_tokens():
    r = Responders()
    r.verify_result = VerifyResult(VerifyKind.PASSED, steps_remaining=False)
    work = Workstate(token=("t1",), tokens=("t1",))
    step = advance(r.loop(), Session(State.VERIFYING, "g"), work)
    assert isinstance(step, LoopStep)
    assert ("verify",) in r.calls
    assert step.session.state is State.COMPLETED
    assert step.work.token is None
    assert step.writes[0].kind is EventKind.VERIFICATION_PASSED


def test_advance_verify_passed_with_steps_remaining_re_executes():
    r = Responders()
    r.verify_result = VerifyResult(VerifyKind.PASSED, steps_remaining=True)
    work = Workstate(token=("t1",), tokens=("t1",))
    step = advance(r.loop(), Session(State.VERIFYING, "g"), work)
    assert isinstance(step, LoopStep)
    assert step.session.state is State.EXECUTING
    assert step.work.token == ("t1",)


@pytest.mark.parametrize(
    "kind,event_kind,target",
    [
        (VerifyKind.FAILED, EventKind.VERIFICATION_FAILED, State.REPLANNING),
        (
            VerifyKind.INCONCLUSIVE,
            EventKind.VERIFICATION_INCONCLUSIVE,
            State.AWAITING_INPUT,
        ),
    ],
)
def test_advance_verify_failed_and_inconclusive(kind, event_kind, target):
    r = Responders()
    r.verify_result = VerifyResult(kind)
    work = Workstate(token=("t1",), tokens=("t1",))
    step = advance(r.loop(), Session(State.VERIFYING, "g"), work)
    assert isinstance(step, LoopStep)
    assert step.session.state is target, kind.name
    assert step.writes[0].kind is event_kind
    assert step.work.token is None
    assert step.work.tokens == ()


def test_advance_in_a_pause_state_without_an_event_is_a_noop():
    session, work = _awaiting_approval()
    step = advance(Responders().loop(), session, work)
    assert isinstance(step, LoopStep)
    assert step.session is session
    assert step.work is work
    assert step.writes == ()
    assert step.consultations == ()


def test_advance_is_deterministic():
    a = advance(Responders().loop(), ready_session())
    b = advance(Responders().loop(), ready_session())
    assert a == b


# ---------------------------------------------------------------------------
# the fresh-View rule re-entry (DN-93) through the conductor
# ---------------------------------------------------------------------------


def test_conductor_reenters_context_building_before_a_stale_cognitive_consult():
    r = Responders()
    session = ready_session()
    step = advance(r.loop(), session)
    assert isinstance(step, LoopStep)
    assert step.session.state is State.BUILDING
    rebuilt = advance(r.loop(), step.session, step.work)
    assert isinstance(rebuilt, LoopStep)
    assert rebuilt.work.view_is_fresh is True
    diagnosis = advance(r.loop(), rebuilt.session, rebuilt.work)
    assert isinstance(diagnosis, LoopStep)
    assert ("provider_reply", (1, 2)) in r.calls


# ---------------------------------------------------------------------------
# pump: the autonomous loop to a pause point
# ---------------------------------------------------------------------------


def test_pump_runs_inspection_building_diagnosis_planning_to_awaiting_approval():
    r = Responders()
    step = pump(r.loop(), ready_session())
    assert isinstance(step, LoopStep)
    assert step.session.state is State.AWAITING_APPROVAL
    assert step.session.goal == "fix nginx"
    assert step.work.presented is True
    assert step.consultations == (
        Consultation(Subsystem.DIAGNOSTICS, State.INSPECTING),
        Consultation(Subsystem.CONTEXT, State.BUILDING),
        Consultation(Subsystem.PROVIDER, State.DIAGNOSING),
        Consultation(Subsystem.PROVIDER, State.PLANNING),
    )
    assert named(step.writes) == [
        EventKind.FACTS_COLLECTED.name,
        EventKind.PROVIDER_RESPONSE.name,
        EventKind.PROVIDER_RESPONSE.name,
        EventKind.PLAN_READY.name,
        EventKind.ACTION_CLASSIFIED.name,
        EventKind.ACTION_BLOCKED.name,
    ]
    assert step.work.tokens == ("t1",)
    assert step.work.blocked == ("b1",)
    assert step.work.token is None


def test_pump_writes_records_before_their_consequences():
    r = Responders()
    step = pump(r.loop(), ready_session())
    assert isinstance(step, LoopStep)
    records = iter(step.writes)
    assert next(records).to_state is State.BUILDING
    assert next(records).from_state is State.DIAGNOSING
    assert next(records).from_state is State.PLANNING
    assert next(records).from_state is State.PLANNING


def test_pump_approve_execute_verify_completes_the_goal():
    r1 = Responders()
    presented = pump(r1.loop(), ready_session())
    assert isinstance(presented, LoopStep)
    approved = advance(r1.loop(), presented.session, presented.work, event=OpApprove())
    assert isinstance(approved, LoopStep)
    assert approved.session.state is State.EXECUTING
    r2 = Responders()
    done = pump(r2.loop(), approved.session, approved.work)
    assert isinstance(done, LoopStep)
    assert done.session.state is State.COMPLETED
    assert done.consultations == (
        Consultation(Subsystem.EXECUTOR, State.EXECUTING),
        Consultation(Subsystem.DIAGNOSTICS, State.VERIFYING),
    )
    assert named(done.writes) == [
        EventKind.ACTION_STARTED.name,
        EventKind.ACTION_SUCCEEDED.name,
        EventKind.VERIFICATION_PASSED.name,
    ]
    assert done.work.token is None
    assert done.work.tokens == ()


def test_pump_stops_at_a_pause_point_hope_loss():
    r = Responders()
    r.inspect_result = Inspection(facts=(), critical=False, hopeless=True)
    step = pump(r.loop(), ready_session())
    assert isinstance(step, LoopStep)
    assert step.session.state is State.FAILED


def test_pump_stops_at_a_pause_point_critical_failure():
    r = Responders()
    r.inspect_result = Inspection(facts=(), critical=True, hopeless=False)
    step = pump(r.loop(), ready_session())
    assert isinstance(step, LoopStep)
    assert step.session.state is State.AWAITING_INPUT


def test_pump_stops_at_awaiting_input_when_no_view_is_assembled():
    r = Responders()
    r.view = None
    step = pump(r.loop(), ready_session())
    assert isinstance(step, LoopStep)
    assert step.session.state is State.AWAITING_INPUT
    assert any("no usable provider view" in d for d in step.disclosures)


def test_pump_does_not_represent_an_already_presented_plan():
    session, work = _awaiting_approval()
    r = Responders()
    step = pump(r.loop(), session, work)
    assert isinstance(step, LoopStep)
    assert step.session is session
    assert step.work.presented is True
    assert not any(c[0] == "record" for c in r.calls)


def test_pump_skill_driven_arc_never_consults_the_provider():
    r = Responders()
    r.skill_reply = Reply(Decision.GROUNDED, plan=("skill fix",))
    step = pump(r.loop(), ready_session())
    assert isinstance(step, LoopStep)
    assert step.session.state is State.AWAITING_APPROVAL
    assert not any(c[0] == "provider_reply" for c in r.calls)
    assert step.consultations == (
        Consultation(Subsystem.DIAGNOSTICS, State.INSPECTING),
        Consultation(Subsystem.CONTEXT, State.BUILDING),
        Consultation(Subsystem.SKILLS, State.DIAGNOSING),
        Consultation(Subsystem.SKILLS, State.PLANNING),
    )


def test_pump_converges_when_evidence_accumulates():
    collected = []

    def inspect(work: Workstate) -> Inspection:
        collected.append(len(collected) + 1)
        return Inspection(facts=tuple(collected), critical=False, hopeless=False)

    def provider(work: Workstate) -> Reply:
        if len(work.facts or ()) < 2:
            return Reply(Decision.NEED_EVIDENCE)
        return Reply(Decision.GROUNDED, plan=("fix",))

    r = Responders()
    loop = Loop(
        inspect=inspect,
        assemble=r.assemble,
        provider_reply=provider,
        skill_plan=r.skill_plan,
        classify_and_gate=r.classify_and_gate,
        revalidate=r.revalidate,
        run_executor=r.run_executor,
        verify=r.verify,
        record=r.record,
    )
    step = pump(loop, ready_session())
    assert isinstance(step, LoopStep)
    assert step.session.state is State.AWAITING_APPROVAL
    assert step.work.facts == (1, 2)


def test_pump_execution_halt_stops_at_interrupted_and_clears_the_token():
    r1 = Responders()
    presented = pump(r1.loop(), ready_session())
    assert isinstance(presented, LoopStep)
    approved = advance(r1.loop(), presented.session, presented.work, event=OpApprove())
    assert isinstance(approved, LoopStep)
    r2 = Responders()
    r2.run = RunResult(RunKind.TIMEOUT)
    halted = pump(r2.loop(), approved.session, approved.work)
    assert isinstance(halted, LoopStep)
    assert halted.session.state is State.INTERRUPTED
    assert halted.work.token is None
    assert halted.work.tokens == ()
    assert any("state uncertain" in d for d in halted.disclosures)


def test_pump_is_deterministic():
    a = pump(Responders().loop(), ready_session())
    b = pump(Responders().loop(), ready_session())
    assert a == b


# ---------------------------------------------------------------------------
# fail-closed audit writes (I-13; AU8; DN-88)
# ---------------------------------------------------------------------------


def test_advance_refused_audit_write_blocks_goal_adoption():
    r = Responders()
    r.record_ok = False
    result = advance(r.loop(), Session(State.IDLE, None), event=OpGoal(), goal="g")
    assert isinstance(result, Refusal)
    assert "audit write refused" in result.reason


def test_pump_refused_audit_write_blocks_the_consequence():
    r = Responders()
    r.record_ok = False
    result = pump(r.loop(), ready_session())
    assert isinstance(result, Refusal)
    assert "audit write refused" in result.reason


def test_advance_refused_audit_write_on_approval_blocks_execution():
    session, work = _awaiting_approval()
    r = Responders()
    r.record_ok = False
    result = advance(r.loop(), session, work, event=OpApprove())
    assert isinstance(result, Refusal)
    assert "audit write refused" in result.reason


# ---------------------------------------------------------------------------
# the reachable set: continuations never invent an edge (DN-86)
# ---------------------------------------------------------------------------


def test_every_conductor_continuation_is_a_machine_permitted_edge():
    session = ready_session()
    r = Responders()
    r.verify_result = VerifyResult(VerifyKind.PASSED, steps_remaining=False)
    step = pump(r.loop(), session)
    assert isinstance(step, LoopStep)
    current = session
    for _ in range(6):
        next_step = advance(r.loop(), current)
        if isinstance(next_step, Refusal):
            continue
        if next_step.session.state is not current.state:
            assert permitted(current.state, next_step.session.state), (
                f"{current.state.name} -> {next_step.session.state.name}"
            )
        current = next_step.session
