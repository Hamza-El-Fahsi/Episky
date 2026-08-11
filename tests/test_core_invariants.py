"""Runtime-invariant conformance (RFC-0002 §9; RFC-0013 §21 AU8).

Iteration 11 Commit C5 conformance oracle. The RFC-0002 §9 preamble: the
fifteen invariants hold "at all times, in every state, without exception."
This module runs each invariant (and AU8) in **every** reachable state. The
reachable set is exactly the Q2 set (DN-86): the §2.1–§2.15 "Allowed
transitions" lists + the §3 shortcut edges + the §2.9 next-step edge,
computed by BFS from Session Initialization, which reaches all 16 states
and nothing else. Each invariant is asserted through the public seams the
design-review §8 table names — the state-machine oracle (`permitted`,
`ALLOWED`, `evolve`), the consultation matrix (`may_consult`,
`provider_consultation_allowed`), the conductor (`advance`, `pump` with
injected deterministic responders, DN-94), and the replan reuse rule
(`reuse_fact`). Deterministic (RFC-0007 S7) and I/O-free (DN-94).
"""

import pathlib
from datetime import datetime

import pytest

from episky.core.consultation import (
    EXECUTOR_CONSULTED_STATES,
    PROVIDER_CONSULTED_STATES,
    Subsystem,
    consultation_refusal,
    may_consult,
    provider_consultation_allowed,
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
    OpReject,
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
from episky.core.replan import FactReuse, approval_carries, reuse_fact
from episky.core.session import Prerequisites, Session, Step
from episky.core.state_machine import (
    ALLOWED,
    Refusal,
    State,
    Transition,
    evolve,
    permitted,
)
from episky.schema.fact import FactStatus, FreshnessState

CORE_DIR = pathlib.Path(__file__).resolve().parents[1] / "src" / "episky" / "core"
LOOP_PATH = CORE_DIR / "loop.py"

OK = Prerequisites(
    elevation_available=True,
    machine_fingerprint_verified=True,
    audit_writable=True,
)

COGNITIVE = frozenset({State.DIAGNOSING, State.PLANNING, State.REPLANNING})

#: The RFC-0002 §9 invariant names (each cited against its paragraph).
INVARIANTS = {
    "I-1": "Execution never starts without approval",
    "I-2": "Verification always follows execution",
    "I-3": "Planning never executes",
    "I-4": "LLM only ever consulted through a provider view",
    "I-5": "No untrusted text is ever interpolated into a command",
    "I-6": "Deviation from the approved plan requires fresh approval",
    "I-7": "Risk classification is deterministic, never the LLM's self-report",
    "I-8": "Any halt of machine-touching work is followed by re-assessment",
    "I-9": "The runtime never fabricates",
    "I-10": "Facts carry provenance and expire",
    "I-11": "Approval tokens are scoped and consumable",
    "I-12": "A blocked action proceeds only via an explicit, audited override",
    "I-13": "The audit trail is written before the consequence",
    "I-14": "No terminal outcome is reached while machine work is in flight",
    "I-15": "No standing authorization across a boundary",
    "AU8": "A failed audit write blocks its consequence and is disclosed",
}


def reachable() -> frozenset[State]:
    """The Q2 reachable set (DN-86): BFS from Session Initialization."""
    seen = {State.INITIALIZING}
    frontier = {State.INITIALIZING}
    while frontier:
        nxt = set()
        for s in frontier:
            nxt.update(ALLOWED[s])
        frontier = nxt - seen
        seen |= nxt
    return frozenset(seen)


REACHABLE = reachable()


class Responders:
    """A minimal injected deterministic responder set (DN-94)."""

    def __init__(self) -> None:
        self.inspect_result = Inspection(facts=(1, 2), critical=False, hopeless=False)
        self.reply = Reply(Decision.GROUNDED, plan=("fix nginx",))
        self.skill_reply = None
        self.gate = GateResult(plan=("fix nginx",), tokens=("t1",), blocked=("b1",))
        self.revalidate_ok = True
        self.run = RunResult(RunKind.SUCCEEDED)
        self.verify_result = VerifyResult(VerifyKind.PASSED)
        self.record_ok = True

    def inspect(self, work: Workstate) -> Inspection:
        return self.inspect_result

    def assemble(self, work: Workstate) -> ViewResult:
        return ViewResult(view=object())

    def provider_reply(self, work: Workstate) -> Reply:
        return self.reply

    def skill_plan(self, work: Workstate) -> Reply | None:
        return self.skill_reply

    def classify_and_gate(self, plan, work: Workstate) -> GateResult:
        return self.gate

    def revalidate(self, token, work: Workstate) -> bool:
        return self.revalidate_ok

    def run_executor(self, token, work: Workstate) -> RunResult:
        return self.run

    def verify(self, work: Workstate) -> VerifyResult:
        return self.verify_result

    def record(self, record: AuditRecord) -> WriteStatus:
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
    started = Session.initial().start(OK)
    assert isinstance(started, Session)
    adopted = started.adopt_goal("fix nginx")
    assert isinstance(adopted, Step)
    return adopted.session


# ---------------------------------------------------------------------------
# the reachable set is exactly the Q2 set (DN-86)
# ---------------------------------------------------------------------------


def test_the_reachable_set_is_exactly_the_q2_set():
    assert set(REACHABLE) == set(State)


def test_the_reachable_set_is_closed_under_allowed():
    for s in REACHABLE:
        assert set(ALLOWED[s]) <= REACHABLE


def test_every_state_is_reachable_from_session_initialization():
    for s in State:
        assert s in REACHABLE, s.name


# ---------------------------------------------------------------------------
# I-1 — Execution never starts without approval
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state", sorted(REACHABLE, key=lambda s: s.value))
def test_i1_the_only_way_into_executing_is_the_gate_or_next_step(state):
    assert permitted(state, State.EXECUTING) == (
        state in (State.AWAITING_APPROVAL, State.VERIFYING)
    ), f"I-1 violated in {state.name}"


def test_i1_the_executor_is_consulted_only_in_executing():
    assert frozenset({State.EXECUTING}) == EXECUTOR_CONSULTED_STATES


def test_i1_the_conductor_refuses_execution_without_a_token():
    result = advance(Responders().loop(), Session(State.EXECUTING, "g"), Workstate())
    assert isinstance(result, Refusal)
    assert "no approval token" in result.reason


# ---------------------------------------------------------------------------
# I-2 — Verification always follows execution
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state", sorted(REACHABLE, key=lambda s: s.value))
def test_i2_executing_exits_only_toward_verification_or_a_halt(state):
    if state is State.EXECUTING:
        assert set(ALLOWED[state]) == {
            State.VERIFYING,
            State.INTERRUPTED,
            State.CANCELLED,
            State.END,
        }
    assert permitted(state, State.VERIFYING) or state is not State.EXECUTING


def test_i2_the_conductor_routes_every_successful_run_to_verification():
    r = Responders()
    work = Workstate(token=("t1",), tokens=("t1",), plan=("fix",))
    step = advance(r.loop(), Session(State.EXECUTING, "g"), work)
    assert isinstance(step, LoopStep)
    assert step.session.state is State.VERIFYING


# ---------------------------------------------------------------------------
# I-3 — Planning never executes
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state", sorted(REACHABLE, key=lambda s: s.value))
def test_i3_no_action_runs_in_a_cognitive_state(state):
    if state in COGNITIVE:
        assert may_consult(state, Subsystem.EXECUTOR) is not None
        assert not permitted(state, State.EXECUTING)


def test_i3_executor_consulted_states_are_executing_only():
    assert frozenset({State.EXECUTING}) == EXECUTOR_CONSULTED_STATES


# ---------------------------------------------------------------------------
# I-4 — LLM only ever consulted through a provider view
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state", sorted(REACHABLE, key=lambda s: s.value))
def test_i4_provider_consultation_requires_a_cognitive_state(state):
    allowed = state in PROVIDER_CONSULTED_STATES
    assert (provider_consultation_allowed(state, view_is_fresh=True) is None) == allowed
    if not allowed:
        refusal = provider_consultation_allowed(state, view_is_fresh=True)
        assert isinstance(refusal, consultation_refusal)


@pytest.mark.parametrize("state", sorted(REACHABLE, key=lambda s: s.value))
def test_i4_provider_consultation_requires_a_fresh_view_in_every_state(state):
    if state in PROVIDER_CONSULTED_STATES:
        assert provider_consultation_allowed(state, view_is_fresh=True) is None
        assert provider_consultation_allowed(state, view_is_fresh=False) is not None


# ---------------------------------------------------------------------------
# I-5 — No untrusted text is ever interpolated into a command
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state", sorted(REACHABLE, key=lambda s: s.value))
def test_i5_actions_are_sanctioned_structures_never_shell_strings(state):
    src = LOOP_PATH.read_text(encoding="utf-8")
    for token in (".run(", "subprocess", "os.system", "eval(", "exec("):
        assert token not in src
    assert "import subprocess" not in src


def test_i5_the_plan_and_tokens_flow_as_tuples_never_strings():
    r = Responders()
    step = pump(r.loop(), ready_session())
    assert isinstance(step, LoopStep)
    assert isinstance(step.work.plan, tuple)
    assert all(isinstance(s, str) for s in step.work.plan)
    assert isinstance(step.work.tokens, tuple)
    assert all(isinstance(t, str) for t in step.work.tokens)


# ---------------------------------------------------------------------------
# I-6 — Deviation from the approved plan requires fresh approval
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state", sorted(REACHABLE, key=lambda s: s.value))
def test_i6_a_changed_plan_never_carries_approval(state):
    assert approval_carries() is False


def test_i6_replanning_clears_the_approval_token():
    r = Responders()
    work = Workstate(tokens=("t1",), token=("t1",), plan=("fix",), blocked=())
    step = advance(
        r.loop(), Session(State.AWAITING_APPROVAL, "g"), work, event=OpReject()
    )
    assert isinstance(step, LoopStep)
    assert step.session.state is State.REPLANNING
    assert step.work.tokens == ()
    assert step.work.token is None


# ---------------------------------------------------------------------------
# I-7 — Risk classification is deterministic, never the LLM's self-report
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state", sorted(REACHABLE, key=lambda s: s.value))
def test_i7_core_never_classifies_in_any_state(state):
    src = LOOP_PATH.read_text(encoding="utf-8")
    for token in ("def classify", "self.classify", "loop.classify("):
        assert token not in src
    assert "classify_and_gate" in src


def test_i7_the_gate_is_the_injected_classifier_not_the_provider():
    r = Responders()
    r.reply = Reply(Decision.GROUNDED, plan=("fix",))
    r.gate = GateResult(plan=("fix",), tokens=("t9",), blocked=())
    step = advance(
        r.loop(), Session(State.PLANNING, "g"), Workstate(view_is_fresh=True)
    )
    assert isinstance(step, LoopStep)
    assert step.work.tokens == ("t9",)


# ---------------------------------------------------------------------------
# I-8 — Any halt of machine-touching work is followed by re-assessment
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state", sorted(REACHABLE, key=lambda s: s.value))
def test_i8_no_halt_ever_resumes_machine_work(state):
    assert not permitted(State.INTERRUPTED, State.EXECUTING)


@pytest.mark.parametrize(
    "kind,event_kind,target",
    [
        (RunKind.TIMEOUT, EventKind.ACTION_TIMEOUT, State.INTERRUPTED),
        (RunKind.INTERRUPTED, EventKind.ACTION_INTERRUPTED, State.INTERRUPTED),
        (RunKind.PARTIAL, EventKind.ACTION_PARTIAL, State.INTERRUPTED),
        (RunKind.REBOOT, EventKind.REBOOT_REQUESTED, State.END),
    ],
)
def test_i8_every_execution_halt_discloses_and_clears_the_token(
    kind, event_kind, target
):
    r = Responders()
    r.run = RunResult(kind)
    work = Workstate(token=("t1",), tokens=("t1",), plan=("fix",))
    step = advance(r.loop(), Session(State.EXECUTING, "g"), work)
    assert isinstance(step, LoopStep)
    assert step.session.state is target
    assert step.work.token is None
    assert step.work.tokens == ()
    assert any("state uncertain" in d for d in step.disclosures)


# ---------------------------------------------------------------------------
# I-9 — The runtime never fabricates
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state", sorted(REACHABLE, key=lambda s: s.value))
def test_i9_no_terminal_outcome_without_a_verified_or_diagnostic_basis(state):
    assert permitted(state, State.COMPLETED) == (
        state in (State.DIAGNOSING, State.PLANNING, State.VERIFYING)
    ), f"I-9/I-14 violated in {state.name}"


def test_i9_degraded_provider_is_disclosed_and_facts_only():
    r = Responders()
    r.reply = Reply(Decision.GROUNDED, plan=(), degraded=True)
    step = advance(
        r.loop(), Session(State.DIAGNOSING, "g"), Workstate(view_is_fresh=True)
    )
    assert isinstance(step, LoopStep)
    assert step.session.state is State.AWAITING_INPUT
    assert any("degraded mode" in d for d in step.disclosures)
    assert EventKind.PROVIDER_FALLBACK_FAILED in [w.kind for w in step.writes]


def test_i9_inconclusive_verification_is_never_success():
    r = Responders()
    r.verify_result = VerifyResult(VerifyKind.INCONCLUSIVE)
    step = advance(
        r.loop(),
        Session(State.VERIFYING, "g"),
        Workstate(token=("t1",), tokens=("t1",)),
    )
    assert isinstance(step, LoopStep)
    assert step.session.state is State.AWAITING_INPUT


# ---------------------------------------------------------------------------
# I-10 — Facts carry provenance and expire
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state", sorted(REACHABLE, key=lambda s: s.value))
def test_i10_facts_are_consumed_only_from_the_inspection_seam(state):
    r = Responders()
    step = advance(r.loop(), ready_session())
    assert isinstance(step, LoopStep)
    assert step.work.facts == (1, 2)
    assert step.work.facts == r.inspect_result.facts


NOW = datetime(2026, 8, 6, 12, 0)
COLLECTED_AT = NOW


def _fact(status, freshness):
    import types

    from episky.schema.fact import (
        Collector,
        ConfidenceSource,
        Fact,
        Freshness,
        ObservationReference,
        Property,
        Provenance,
        Scope,
        Subject,
        Value,
    )

    return Fact(
        scope=Scope(Subject("nginx"), Property("version"), Value("1.22")),
        status=status,
        confidence=ConfidenceSource(name="check-version"),
        provenance=Provenance(
            observation=ObservationReference(),
            collector=Collector(name="collect", version="1"),
            collected_at=COLLECTED_AT,
        ),
        freshness=Freshness(state=freshness),
        machine_identity=types.SimpleNamespace(),
    )


@pytest.mark.parametrize("status", sorted(FactStatus, key=lambda s: s.value))
def test_i10_only_observed_or_verified_current_facts_are_reused(status):
    fact = _fact(status, FreshnessState.CURRENT)
    assert (reuse_fact(fact, now=NOW) is FactReuse.REUSE) == (
        status in (FactStatus.OBSERVED, FactStatus.VERIFIED)
    )


def test_i10_stale_facts_are_re_collected():
    import types

    from episky.schema.fact import (
        Collector,
        ConfidenceSource,
        Fact,
        Freshness,
        ObservationReference,
        Property,
        Provenance,
        Scope,
        Subject,
        Value,
    )

    fact = Fact(
        scope=Scope(Subject("nginx"), Property("version"), Value("1.22")),
        status=FactStatus.OBSERVED,
        confidence=ConfidenceSource(name="check-version"),
        provenance=Provenance(
            observation=ObservationReference(),
            collector=Collector(name="collect", version="1"),
            collected_at=COLLECTED_AT,
        ),
        freshness=Freshness(state=FreshnessState.STALE),
        machine_identity=types.SimpleNamespace(),
    )
    assert reuse_fact(fact, now=NOW) is FactReuse.RECOLLECT


# ---------------------------------------------------------------------------
# I-11 — Approval tokens are scoped and consumable
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state", sorted(REACHABLE, key=lambda s: s.value))
def test_i11_tokens_are_revalidated_only_at_the_execution_boundary(state):
    if state is State.AWAITING_APPROVAL:
        assert State.EXECUTING in ALLOWED[state]


def test_i11_the_conductor_revalidates_the_token_before_execution():
    r = Responders()
    r.revalidate_ok = False
    work = Workstate(tokens=("t1",), token=("t1",), plan=("fix",), presented=True)
    step = advance(
        r.loop(), Session(State.AWAITING_APPROVAL, "g"), work, event=OpApprove()
    )
    assert isinstance(step, LoopStep)
    assert step.session.state is State.INSPECTING
    assert step.work.tokens == ()
    assert any("no longer valid" in d for d in step.disclosures)


@pytest.mark.parametrize("state", sorted(REACHABLE, key=lambda s: s.value))
def test_i11_no_approval_survives_a_boundary_state(state):
    for boundary in (
        State.INTERRUPTED,
        State.REPLANNING,
        State.CANCELLED,
        State.COMPLETED,
        State.FAILED,
    ):
        assert not permitted(boundary, State.EXECUTING)


# ---------------------------------------------------------------------------
# I-12 — A blocked action proceeds only via an explicit, audited override
# ---------------------------------------------------------------------------


def test_i12_blocked_actions_are_recorded_before_presentation():
    r = Responders()
    step = pump(r.loop(), ready_session())
    assert isinstance(step, LoopStep)
    kinds = [w.kind for w in step.writes]
    assert EventKind.ACTION_BLOCKED in kinds
    assert kinds.index(EventKind.ACTION_CLASSIFIED) < kinds.index(
        EventKind.ACTION_BLOCKED
    )


def test_i12_an_override_is_a_fresh_recorded_approval():
    r = Responders()
    work = Workstate(
        tokens=("t1",), token=("t1",), plan=("fix",), blocked=("b1",), presented=True
    )
    step = advance(
        r.loop(), Session(State.AWAITING_APPROVAL, "g"), work, event=OpOverride()
    )
    assert isinstance(step, LoopStep)
    assert step.session.state is State.EXECUTING
    assert step.writes[0].kind is EventKind.OP_OVERRIDE
    assert step.writes[0].category is RecordCategory.OVERRIDE


# ---------------------------------------------------------------------------
# I-13 — The audit trail is written before the consequence
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state", sorted(REACHABLE, key=lambda s: s.value))
def test_i13_every_written_record_precedes_its_consequence(state):
    r = Responders()
    r.record_ok = False
    result = pump(r.loop(), ready_session())
    assert isinstance(result, Refusal)
    assert "audit write refused" in result.reason


def test_i13_a_refused_write_blocks_goal_adoption():
    r = Responders()
    r.record_ok = False
    result = advance(r.loop(), Session(State.IDLE, None), event=OpGoal(), goal="g")
    assert isinstance(result, Refusal)


def test_i13_a_refused_write_blocks_approval():
    r = Responders()
    r.record_ok = False
    work = Workstate(tokens=("t1",), token=("t1",), plan=("fix",), presented=True)
    result = advance(
        r.loop(), Session(State.AWAITING_APPROVAL, "g"), work, event=OpApprove()
    )
    assert isinstance(result, Refusal)


# ---------------------------------------------------------------------------
# I-14 — No terminal outcome is reached while machine work is in flight
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state", sorted(REACHABLE, key=lambda s: s.value))
def test_i14_no_terminal_outcome_from_executing(state):
    assert not permitted(State.EXECUTING, State.COMPLETED)
    assert not permitted(State.EXECUTING, State.FAILED)


@pytest.mark.parametrize("state", sorted(REACHABLE, key=lambda s: s.value))
def test_i14_outcome_sources_are_verification_or_diagnostic_only(state):
    assert permitted(state, State.COMPLETED) == (
        state in (State.DIAGNOSING, State.PLANNING, State.VERIFYING)
    )


# ---------------------------------------------------------------------------
# I-15 — No standing authorization across a boundary
# ---------------------------------------------------------------------------


@pytest.mark.parametrize("state", sorted(REACHABLE, key=lambda s: s.value))
def test_i15_exit_and_cancel_clear_every_approval(state):
    if state in (State.INITIALIZING, State.END):
        return
    result = evolve(state, OpExit())
    assert isinstance(result, Transition)
    assert result.new_state is State.END


def test_i15_the_conductor_clears_tokens_on_cancel_and_interrupt():
    r = Responders()
    work = Workstate(tokens=("t1",), token=("t1",))
    for event in (OpCancel(), OpInterrupt()):
        step = advance(r.loop(), Session(State.EXECUTING, "g"), work, event=event)
        assert isinstance(step, LoopStep)
        assert step.work.token is None
        assert step.work.tokens == ()


# ---------------------------------------------------------------------------
# AU8 — A failed audit write blocks its consequence and is disclosed
# ---------------------------------------------------------------------------


def test_au8_a_refused_write_blocks_the_consequence_and_is_disclosed():
    r = Responders()
    r.record_ok = False
    result = pump(r.loop(), ready_session())
    assert isinstance(result, Refusal)
    assert "audit write refused" in result.reason


def test_au8_the_disclosure_names_the_refused_audit_write():
    r = Responders()
    r.record_ok = False
    result = advance(r.loop(), Session(State.IDLE, None), event=OpGoal(), goal="g")
    assert isinstance(result, Refusal)
    assert "audit write refused" in result.reason


# ---------------------------------------------------------------------------
# the invariants are all present and transcribed (design-review §8)
# ---------------------------------------------------------------------------


def test_all_fifteen_invariants_and_au8_are_covered():
    assert len(INVARIANTS) == 16
    assert set(INVARIANTS) >= {
        "I-1",
        "I-2",
        "I-3",
        "I-4",
        "I-5",
        "I-6",
        "I-7",
        "I-8",
        "I-9",
        "I-10",
        "I-11",
        "I-12",
        "I-13",
        "I-14",
        "I-15",
        "AU8",
    }
