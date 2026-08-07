"""Deterministic sanctioned runner (RFC-0004 §4.9; RFC-0002 §2.8, §6.2; I-1,
I-5, I-11, I-13; RFC-0008 §8/§9/§10; RFC-0013 §7/§21; AU5, AU8; DN-55,
DN-56, DN-57, DN-58, DN-61).

Behavioral tests for Iteration 8 Commit C3 (`executor/runner.py`): the
deterministic decision boundary — one approved Action runs only under a
valid, unexpired, state-consistent token (I-1/I-11), re-validated locally
from the structural handoff value (DN-56) and against the consumed boundary
verdict (DN-57); anything uncertain fails closed with a deterministic,
disclosed refusal. The runner derives an argv-structured descriptor and never
a shell string (I-5, DN-58), executes through an injected run primitive
(DN-55), writes the execution-start record before the run and the end record
after through `audit` (I-13), and a failed pre-write blocks the run and is
disclosed (AU8, DN-61). Outputs are immutable values; the decision depends
only on explicit inputs (no clock, no randomness, no hidden state); the
runner creates no execution authority. AST conformance mirrors the audit
layer: no forbidden imports, no forbidden stdlib, no forbidden runtime
calls, no top-level runtime logic.
"""

import ast
import importlib
import pathlib
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta

import pytest

from episky.audit.records import ExecutionPhase, ExecutionRecord, RecordCategory
from episky.audit.store import AuditStore, StoreStatus
from episky.executor.runner import (
    BoundaryVerdict,
    Refusal,
    RefusalReason,
    RunOutcome,
    RunResult,
    TokenHandoff,
    run,
)
from episky.schema.action import Action

RUNNER_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "executor"
    / "runner.py"
)

NOW = datetime(2026, 8, 7, 12, 0, 0)

SESSION = object()
SNAPSHOT = object()
OTHER = object()
_UNSET = object()


def _action(description="ls -l"):
    return Action(
        description=description,
        risk_properties=("read-only",),
        verification_criteria=(),
    )


def _token(
    action=_UNSET,
    *,
    action_id="action-1",
    risk_class="read-only",
    gate="goal-check",
    issued_at=NOW,
    expiry=None,
    session=SESSION,
    state_snapshot=SNAPSHOT,
    consumed=False,
    invalidated=False,
):
    return TokenHandoff(
        action_id=action_id,
        action=_action() if action is _UNSET else action,
        risk_class=risk_class,
        gate=gate,
        issued_at=issued_at,
        expiry=expiry if expiry is not None else NOW + timedelta(hours=1),
        session=session,
        state_snapshot=state_snapshot,
        elevation_bounds=(),
        override=False,
        consumed=consumed,
        invalidated=invalidated,
    )


def _verdict(state_consistent=True, session=SESSION, state_snapshot=SNAPSHOT):
    return BoundaryVerdict(
        session=session,
        state_snapshot=state_snapshot,
        state_consistent=state_consistent,
    )


def _recording_store():
    return AuditStore().begin_recording()


def _primitive(returns=None, log=None):
    def primitive(action, argv):
        if log is not None:
            log.append(argv)
        return RunResult(0, ("ok",)) if returns is None else returns

    return primitive


def _run(
    action=None,
    token=None,
    verdict=None,
    *,
    store=None,
    primitive=None,
    now=NOW,
    start_record_id="start-1",
    end_record_id="end-1",
):
    action = _action() if action is None else action
    token = token if token is not None else _token(action=action)
    verdict = verdict if verdict is not None else _verdict()
    store = store if store is not None else _recording_store()
    primitive = primitive if primitive is not None else _primitive()
    return run(
        action,
        token,
        verdict,
        now=now,
        store=store,
        primitive=primitive,
        start_record_id=start_record_id,
        end_record_id=end_record_id,
    )


# --- public surface -----------------------------------------------------------


def test_runner_owns_exactly_the_runner_vocabulary():
    runner_module = importlib.import_module("episky.executor.runner")
    assert set(runner_module.__all__) == {
        "BoundaryVerdict",
        "Refusal",
        "RefusalReason",
        "RunOutcome",
        "RunPrimitive",
        "RunResult",
        "TokenHandoff",
        "run",
    }


def test_runner_dataclasses_are_frozen_and_slotted():
    for cls in (TokenHandoff, BoundaryVerdict, Refusal, RunResult, RunOutcome):
        params = cls.__dataclass_params__
        assert params.frozen and params.slots, f"{cls.__name__} is not frozen+slots"


# --- successful sanctioned execution ------------------------------------------


def test_successful_sanctioned_execution():
    outcome = _run()
    assert outcome.refusal is None
    assert outcome.result == RunResult(0, ("ok",))
    assert len(outcome.store.records) == 2
    assert outcome.store.verify()


def test_successful_run_records_start_and_end_in_write_order():
    outcome = _run()
    assert outcome.start_record is not None
    assert outcome.end_record is not None
    records = outcome.store.records
    assert records[0].phase is ExecutionPhase.START
    assert records[1].phase is ExecutionPhase.END
    assert [r.record_id for r in records] == ["start-1", "end-1"]


def test_execution_records_carry_the_boundary_content():
    outcome = _run()
    start = outcome.start_record
    assert start.recorded_at == NOW
    assert start.category is RecordCategory.EXECUTION
    assert start.action_id == "action-1"
    assert start.argv == ("ls", "-l")
    assert start.machine_state is SNAPSHOT
    assert outcome.end_record.action_id == "action-1"
    assert outcome.end_record.argv == ("ls", "-l")


def test_the_primitive_receives_the_sanctioned_descriptor():
    received = []
    outcome = _run(primitive=_primitive(log=received))
    assert outcome.refusal is None
    assert received == [("ls", "-l")]


# --- record-before-consequence (I-13, AU8) ------------------------------------


def test_record_before_consequence_ordering():
    calls = []
    outcome = _run(primitive=_primitive(log=calls))
    assert calls == [("ls", "-l")]
    records = outcome.store.records
    assert records[0].phase is ExecutionPhase.START
    assert records[1].phase is ExecutionPhase.END
    assert outcome.start_record.record_id == "start-1"
    assert outcome.end_record.record_id == "end-1"


def test_failed_pre_write_blocks_the_run_and_is_disclosed():
    store = _recording_store().append(
        ExecutionRecord(
            record_id="start-1",
            recorded_at=NOW,
            category=RecordCategory.EXECUTION,
            phase=ExecutionPhase.START,
            action_id="action-1",
            argv=("ls", "-l"),
            machine_state=SNAPSHOT,
        )
    )
    calls = []
    outcome = _run(store=store, primitive=_primitive(log=calls))
    assert outcome.refusal is not None
    assert outcome.refusal.reason is RefusalReason.STORE_DEGRADED
    assert outcome.refusal.message.startswith("run refused:")
    assert outcome.store.status is StoreStatus.DEGRADED
    assert outcome.store.disclosure is not None
    assert calls == []


def test_primitive_failure_yields_outcome_unknown_and_still_records_end():
    def primitive(action, argv):
        raise RuntimeError("primitive failed")

    outcome = _run(primitive=primitive)
    assert outcome.refusal is None
    assert outcome.result == RunResult(exit_status=None, output=())
    assert [r.phase for r in outcome.store.records] == [
        ExecutionPhase.START,
        ExecutionPhase.END,
    ]


# --- independent re-validation (I-1, I-11, RFC-0008 §9) -----------------------


def test_run_refuses_a_token_without_an_approved_action():
    outcome = _run(token=_token(action=None))
    assert outcome.refusal is not None
    assert outcome.refusal.reason is RefusalReason.NOT_APPROVED


def test_run_refuses_an_expired_authorization():
    token = _token(expiry=NOW - timedelta(minutes=1))
    outcome = _run(token=token)
    assert outcome.refusal.reason is RefusalReason.EXPIRED


def test_run_refuses_at_the_expiry_boundary():
    token = _token(expiry=NOW)
    outcome = _run(token=token)
    assert outcome.refusal.reason is RefusalReason.EXPIRED


def test_run_refuses_a_replayed_consumed_token():
    outcome = _run(token=_token(consumed=True))
    assert outcome.refusal.reason is RefusalReason.CONSUMED


def test_run_refuses_an_invalidated_token():
    outcome = _run(token=_token(invalidated=True))
    assert outcome.refusal.reason is RefusalReason.INVALIDATED


def test_run_refuses_a_mismatched_action():
    outcome = _run(action=_action(description="rm -rf /"), token=_token())
    assert outcome.refusal.reason is RefusalReason.ACTION_MISMATCH


def test_run_refuses_a_mismatched_snapshot():
    outcome = _run(verdict=_verdict(state_snapshot=OTHER))
    assert outcome.refusal.reason is RefusalReason.SNAPSHOT_MISMATCH


def test_run_refuses_a_mismatched_session():
    outcome = _run(verdict=_verdict(session=OTHER))
    assert outcome.refusal.reason is RefusalReason.SESSION_MISMATCH


def test_run_fails_closed_on_an_uncertain_boundary_verdict():
    outcome = _run(verdict=_verdict(state_consistent=False))
    assert outcome.refusal.reason is RefusalReason.STATE_UNCERTAIN


def test_run_fails_closed_on_a_degraded_store_input():
    store = _recording_store().fail("a previous write failed")
    outcome = _run(store=store)
    assert outcome.refusal.reason is RefusalReason.STORE_DEGRADED
    assert outcome.store.status is StoreStatus.DEGRADED


def test_run_fails_closed_on_a_recovering_store_input():
    store = _recording_store().fail("a previous write failed").recover()
    outcome = _run(store=store)
    assert outcome.refusal.reason is RefusalReason.STORE_DEGRADED


def test_validation_refusals_never_run_and_never_record():
    cases = [
        lambda: _run(token=_token(action=None)),
        lambda: _run(token=_token(expiry=NOW - timedelta(minutes=1))),
        lambda: _run(token=_token(consumed=True)),
        lambda: _run(token=_token(invalidated=True)),
        lambda: _run(action=_action(description="rm -rf /"), token=_token()),
        lambda: _run(verdict=_verdict(state_snapshot=OTHER)),
        lambda: _run(verdict=_verdict(session=OTHER)),
        lambda: _run(verdict=_verdict(state_consistent=False)),
    ]
    for call in cases:
        outcome = call()
        assert outcome.refusal is not None
        assert outcome.result is None
        assert outcome.start_record is None
        assert outcome.end_record is None
        assert len(outcome.store.records) == 0


def test_refusal_disclosures_are_deterministic():
    first = _run(token=_token(consumed=True))
    second = _run(token=_token(consumed=True))
    assert first.refusal == second.refusal
    assert first.refusal.message == second.refusal.message


# --- no shell string (I-5, DN-58) ---------------------------------------------


def test_no_shell_string_is_ever_constructed_from_hostile_text():
    hostile = "rm -rf /; echo pwned && whoami"
    received = []

    def primitive(action, argv):
        received.append(argv)
        return RunResult(0, ())

    outcome = _run(action=_action(description=hostile), primitive=primitive)
    assert outcome.refusal is None
    assert received == [tuple(hostile.split())]
    assert all(isinstance(token, str) for token in received[0])
    assert outcome.start_record.argv == tuple(hostile.split())
    assert outcome.end_record.argv == tuple(hostile.split())


def test_argv_derivation_is_deterministic_and_shell_free():
    action = _action(description="  install    openssh-client  ")
    received = []
    outcome = _run(action=action, primitive=_primitive(log=received))
    assert received == [("install", "openssh-client")]
    assert outcome.start_record.argv == ("install", "openssh-client")


# --- deterministic outputs (AU5) ----------------------------------------------


def test_identical_inputs_yield_identical_outcomes():
    store = _recording_store()
    first = _run(store=store)
    second = _run(store=store)
    assert first == second
    assert first.result == second.result
    assert first.store == second.store


def test_the_decision_depends_on_the_explicit_now_argument():
    token = _token(expiry=NOW + timedelta(hours=1))
    assert _run(token=token, now=NOW).refusal is None
    expired = _run(token=token, now=NOW + timedelta(hours=2))
    assert expired.refusal is not None
    assert expired.refusal.reason is RefusalReason.EXPIRED


# --- immutable outputs --------------------------------------------------------


def test_outputs_are_immutable_values():
    outcome = _run()
    assert isinstance(outcome.result, RunResult)
    assert isinstance(outcome.store.records, tuple)
    with pytest.raises(FrozenInstanceError):
        outcome.result.output = ()
    refusal = Refusal(RefusalReason.EXPIRED, "run refused: expired")
    with pytest.raises(FrozenInstanceError):
        refusal.message = "changed"


def test_an_empty_run_result_is_immutable_and_hashable():
    result = RunResult(0, ("ok",))
    assert result == RunResult(0, ("ok",))
    assert hash(result) == hash(RunResult(0, ("ok",)))
    with pytest.raises(FrozenInstanceError):
        result.exit_status = 1


# --- no hidden state, no authority creation -----------------------------------


def _has_call(node):
    return any(isinstance(n, ast.Call) for n in ast.walk(node))


def test_runner_module_has_no_module_level_state_beyond_all():
    tree = ast.parse(RUNNER_PATH.read_text(encoding="utf-8"))
    for stmt in tree.body:
        if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            targets = stmt.targets if isinstance(stmt, ast.Assign) else (stmt.target,)
            for target in targets:
                assert isinstance(target, ast.Name), (
                    "module-level assignment to "
                    f"{getattr(target, 'id', type(target).__name__)}"
                )
                assert target.id == "__all__" or not _has_call(stmt.value), (
                    f"module-level assignment to {target.id} calls a constructor "
                    "at import time (hidden state)"
                )


def test_runner_creates_no_execution_authority():
    outcome = _run()
    assert not hasattr(outcome, "token")
    assert not hasattr(outcome, "approval")
    assert not hasattr(outcome.refusal, "token")
    runner_src = RUNNER_PATH.read_text(encoding="utf-8")
    for forbidden in (
        "def mint",
        "def approve",
        "def grant",
        "mint(",
        "import policy",
        "from episky.policy",
    ):
        assert forbidden not in runner_src, f"runner.py contains {forbidden}"


# --- AST conformance ----------------------------------------------------------


def _module_imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield 0, alias.name
        elif isinstance(node, ast.ImportFrom):
            yield node.level, node.module or ""


def test_runner_imports_only_sanctioned_packages_and_stdlib():
    allowed_episky = {
        "episky.audit.records",
        "episky.audit.store",
        "episky.schema.action",
    }
    for level, module in _module_imports(RUNNER_PATH):
        assert level <= 1
        if module.startswith("episky"):
            assert module in allowed_episky, f"runner.py imports {module}"


def test_runner_imports_no_forbidden_stdlib():
    forbidden = {
        "os",
        "subprocess",
        "socket",
        "pathlib",
        "shutil",
        "tempfile",
        "urllib",
        "http",
        "ssl",
        "ftplib",
        "smtplib",
        "sqlite3",
        "shelve",
        "dbm",
        "pickle",
        "marshal",
        "threading",
        "multiprocessing",
        "concurrent",
        "asyncio",
        "signal",
        "fcntl",
        "termios",
        "pty",
        "tty",
        "mmap",
        "ctypes",
        "json",
        "csv",
        "random",
        "uuid",
        "hashlib",
        "hmac",
        "secrets",
        "base64",
        "logging",
    }
    for _level, module in _module_imports(RUNNER_PATH):
        assert module.split(".")[0] not in forbidden, f"runner.py imports {module}"


def test_runner_calls_no_forbidden_runtime_builtin():
    tree = ast.parse(RUNNER_PATH.read_text(encoding="utf-8"))
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                calls.add(func.id)
            elif isinstance(func, ast.Attribute):
                calls.add(func.attr)
    assert calls.isdisjoint(
        {"open", "print", "input", "exec", "eval", "breakpoint", "__import__"}
    )


def test_runner_has_no_top_level_runtime_logic():
    forbidden = (
        ast.If,
        ast.For,
        ast.While,
        ast.Try,
        ast.With,
        ast.Raise,
        ast.Assert,
        ast.Delete,
        ast.Global,
        ast.Nonlocal,
        ast.Lambda,
        ast.Await,
    )
    tree = ast.parse(RUNNER_PATH.read_text(encoding="utf-8"))
    for stmt in tree.body:
        assert not isinstance(stmt, forbidden), f"top-level {type(stmt).__name__}"
        if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            targets = stmt.targets if isinstance(stmt, ast.Assign) else (stmt.target,)
            for target in targets:
                name = getattr(target, "id", type(target).__name__)
                assert isinstance(target, ast.Name), (
                    f"module-level assignment to {name}"
                )
                assert target.id == "__all__" or not _has_call(stmt.value), (
                    f"module-level assignment to {target.id} calls a constructor "
                    "at import time (runtime logic)"
                )


def test_runner_reads_no_clock_and_generates_no_random_or_crypto():
    src = RUNNER_PATH.read_text(encoding="utf-8")
    for token in (
        "datetime.now",
        "utcnow",
        "time.time",
        "time.monotonic",
        "perf_counter",
        "import time",
        "import random",
        "random.",
        "os.urandom",
        "import uuid",
        "uuid4",
        "import hmac",
        "import hashlib",
        "import secrets",
        "secrets.token",
        "import os",
        "import subprocess",
        "os.system",
        "os.popen",
    ):
        assert token not in src, f"runner.py uses {token}"
