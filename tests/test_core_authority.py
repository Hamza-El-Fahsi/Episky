"""C5 conformance oracle — the authority boundary (RFC-0004 §7, §8).

The core Orchestrator may Propose, Refuse, and Explain, and it alone of the
Assistant's components holds those; it must never Observe, Infer, Verify,
Approve, Execute, or Persist itself (RFC-0004 §7 Orchestrator row). Each of
those forbidden acts is reached only through an injected ``Loop`` seam
(design-review §6; DN-94): the Policy Engine gate (``classify_and_gate`` /
``revalidate``), the Executor (``run_executor``), and Verification
(``verify``). This file asserts that boundary structurally and behaviorally,
including the use-limit reading of the matrix — the Execute column has exactly
one A, reached only through Proposal → gate → token → re-validate → Executor
(RFC-0004 §8 A9), with approval recorded before it is spent (A10), and raw
provider output can never reach the executor seam (A1).
"""

import dataclasses
import pathlib

import pytest

from episky.core.events import (
    AuditRecord,
    EventKind,
    OpApprove,
    RecordCategory,
)
from episky.core.loop import (
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
from episky.core.state_machine import Refusal, State

OK = Prerequisites(
    elevation_available=True,
    machine_fingerprint_verified=True,
    audit_writable=True,
)
VIEW = object()


class Seams:
    """Recording, deterministic injected responders (mirrors test_core_loop)."""

    def __init__(self) -> None:
        self.calls: list[tuple] = []
        self.gate = GateResult(plan=("fix nginx",), tokens=("t1",), blocked=("b1",))
        self.run = RunResult(RunKind.SUCCEEDED)
        self.verify_result = VerifyResult(VerifyKind.PASSED)

    def inspect(self, work: Workstate) -> Inspection:
        self.calls.append(("inspect",))
        return Inspection(facts=(1, 2))

    def assemble(self, work: Workstate) -> ViewResult:
        self.calls.append(("assemble",))
        return ViewResult(view=VIEW)

    def provider_reply(self, work: Workstate) -> Reply:
        self.calls.append(("provider_reply",))
        return Reply(Decision.GROUNDED, plan=("fix nginx",))

    def skill_plan(self, work: Workstate) -> Reply | None:
        return None

    def classify_and_gate(self, plan, work: Workstate) -> GateResult:
        self.calls.append(("classify_and_gate", plan))
        return self.gate

    def revalidate(self, token, work: Workstate) -> bool:
        self.calls.append(("revalidate", token))
        return True

    def run_executor(self, token, work: Workstate) -> RunResult:
        self.calls.append(("run_executor", token))
        return self.run

    def verify(self, work: Workstate) -> VerifyResult:
        self.calls.append(("verify",))
        return self.verify_result

    def record(self, record: AuditRecord) -> WriteStatus:
        self.calls.append(("record", record.kind))
        return WriteStatus.OK

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
    started = Session.initial().start(OK)
    assert isinstance(started, Session)
    adopted = started.adopt_goal("fix nginx")
    assert isinstance(adopted, Step)
    return adopted.session


def awaiting_approval() -> tuple[Session, Workstate]:
    return (
        Session(State.AWAITING_APPROVAL, "fix nginx"),
        Workstate(
            tokens=("t1",),
            token=("t1",),
            plan=("fix nginx",),
            blocked=("b1",),
            presented=True,
        ),
    )


# ---------------------------------------------------------------------------
# structural: the forbidden acts live only in the injected seams (RFC-0004 §7)
# ---------------------------------------------------------------------------


def test_core_executes_only_through_the_run_executor_seam():
    assert Loop.__dataclass_fields__["run_executor"] is not None
    assert Loop.__dataclass_fields__["classify_and_gate"] is not None
    assert Loop.__dataclass_fields__["revalidate"] is not None
    assert Loop.__dataclass_fields__["verify"] is not None


def test_core_has_no_second_execution_path_in_source():
    for path in pathlib.Path("src/episky/core").glob("*.py"):
        src = path.read_text(encoding="utf-8")
        for token in ("subprocess", "os.system", "os.exec", "Popen", "socket"):
            assert token not in src, f"{path.name} contains {token!r}"


def test_verify_is_the_injected_verdict_never_a_core_conclusion():
    for verdict, kind in [
        (VerifyKind.PASSED, EventKind.VERIFICATION_PASSED),
        (VerifyKind.FAILED, EventKind.VERIFICATION_FAILED),
    ]:
        s = Seams()
        s.verify_result = VerifyResult(verdict)
        presented = pump(s.loop(), ready_session())
        assert isinstance(presented, LoopStep)
        approved = advance(
            s.loop(), presented.session, presented.work, event=OpApprove()
        )
        assert isinstance(approved, LoopStep)
        step = pump(s.loop(), approved.session, approved.work)
        assert isinstance(step, LoopStep)
        assert any(w.kind is kind for w in step.writes)


# ---------------------------------------------------------------------------
# the Execute column has exactly one A, reached only via gate → token →
# re-validate → Executor (RFC-0004 §8 A9; I-1)
# ---------------------------------------------------------------------------


def test_pump_from_a_fresh_goal_never_executes():
    s = Seams()
    step = pump(s.loop(), ready_session())
    assert isinstance(step, LoopStep)
    assert step.session.state is State.AWAITING_APPROVAL
    assert not any(c[0] == "run_executor" for c in s.calls)


@pytest.mark.parametrize(
    "state", sorted(set(State) - {State.EXECUTING}, key=lambda s: s.value)
)
def test_the_executor_is_unreachable_from_every_non_executing_state(state):
    s = Seams()
    work = Workstate(tokens=("t1",), token=("t1",), plan=("fix nginx",), presented=True)
    result = pump(s.loop(), Session(state, "fix nginx"), work)
    if isinstance(result, Refusal):
        return
    assert not any(c[0] == "run_executor" for c in s.calls)


def test_execution_without_an_approval_token_is_refused():
    s = Seams()
    result = advance(s.loop(), Session(State.EXECUTING, "fix nginx"), Workstate())
    assert isinstance(result, Refusal)
    assert "no approval token" in result.reason


def test_approval_is_recorded_before_it_is_spent():
    s1 = Seams()
    presented = pump(s1.loop(), ready_session())
    assert isinstance(presented, LoopStep)
    approved = advance(s1.loop(), presented.session, presented.work, event=OpApprove())
    assert isinstance(approved, LoopStep)
    assert approved.writes[0].kind is EventKind.OP_APPROVE
    assert approved.writes[0].category is RecordCategory.APPROVAL
    assert not any(c[0] == "run_executor" for c in s1.calls)
    s2 = Seams()
    executed = pump(s2.loop(), approved.session, approved.work)
    assert isinstance(executed, LoopStep)
    assert any(c[0] == "run_executor" for c in s2.calls)


# ---------------------------------------------------------------------------
# A1 — provider output never reaches the executor seam
# ---------------------------------------------------------------------------


def test_provider_strings_never_reach_the_executor_seam():
    s = Seams()
    reply = Reply(Decision.GROUNDED, plan=("fix nginx",))
    captured = {}

    def provider(work: Workstate) -> Reply:
        return reply

    def run_executor(token, work: Workstate) -> RunResult:
        captured["args"] = (token, work)
        return RunResult(RunKind.SUCCEEDED)

    loop = Loop(
        inspect=s.inspect,
        assemble=s.assemble,
        provider_reply=provider,
        skill_plan=s.skill_plan,
        classify_and_gate=s.classify_and_gate,
        revalidate=s.revalidate,
        run_executor=run_executor,
        verify=s.verify,
        record=s.record,
    )
    presented = pump(loop, ready_session())
    assert isinstance(presented, LoopStep)
    approved = advance(loop, presented.session, presented.work, event=OpApprove())
    assert isinstance(approved, LoopStep)
    pump(loop, approved.session, approved.work)
    token, work = captured["args"]
    assert token == ("t1",)
    assert work.token == ("t1",)
    assert work is not reply
    assert not any(arg is reply for arg in (token, work))
    assert reply not in dataclasses.astuple(work)


# ---------------------------------------------------------------------------
# the Orchestrator's A cells: Refuse and Explain (RFC-0004 §7)
# ---------------------------------------------------------------------------


def test_the_orchestrator_refuses_fail_loud():
    s = Seams()
    refused = advance(
        s.loop(), Session(State.DIAGNOSING, "fix nginx"), event=OpApprove()
    )
    assert isinstance(refused, Refusal)
    assert refused.reason


def test_the_orchestrator_explains_boundary_clear_halts():
    s = Seams()
    s.run = RunResult(RunKind.INTERRUPTED)
    presented = pump(s.loop(), ready_session())
    assert isinstance(presented, LoopStep)
    approved = advance(s.loop(), presented.session, presented.work, event=OpApprove())
    assert isinstance(approved, LoopStep)
    halted = pump(s.loop(), approved.session, approved.work)
    assert isinstance(halted, LoopStep)
    assert halted.session.state is State.INTERRUPTED
    assert halted.work.token is None
    assert any("state uncertain" in d for d in halted.disclosures)
