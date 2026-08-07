"""Guardrails for the sanctioned run (RFC-0001 §5, §8.8, §8.12; RFC-0002
§2.8; RFC-0009 SC8/SC10/SC14; DN-59).

Behavioral tests for Iteration 8 Commit C4 (`executor/guards.py`): the
deterministic guardrail envelope around an injected run primitive —
scoping the run to the token's one approved Action (nothing beyond the
named scope ever runs, RFC-0004 §4.9/P12), a deterministic timeout
decision over explicit time inputs with a placeholder default bound (a
run at/after its deadline yields an outcome-unknown result, RFC-0002
§2.8 → Interrupted), and bounded, truncated output capture redacted via
`secrets` before it crosses (DN-18 marker, never silently dropped;
SC8/SC10; a line that cannot be proven non-secret is withheld and
disclosed, SC14). Any guardrail error fails closed and is disclosed
(RFC-0001 §8.12). The guard reads no clock, performs no I/O, creates no
execution authority, and keeps no hidden state. AST conformance mirrors
the runner: no forbidden imports, no forbidden stdlib, no forbidden
runtime calls, no top-level runtime logic.
"""

import ast
import importlib
import pathlib
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta

import pytest

from episky.executor.guards import (
    DEFAULT_OUTPUT_BOUND,
    DEFAULT_TIMEOUT_BOUND,
    GuardedResult,
    GuardrailFailure,
    GuardrailReason,
    guard,
)
from episky.executor.runner import RunResult, TokenHandoff
from episky.schema.action import Action
from episky.secrets.classify import (
    NonSecretDesignation,
    SecretDatum,
    SecretOrigin,
    classify,
)
from episky.trust.classes import TrustClass

GUARDS_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "executor"
    / "guards.py"
)

NOW = datetime(2026, 8, 7, 12, 0, 0)

SESSION = object()
OTHER = object()
_UNSET = object()

BEARER_TOKEN = "0123456789ABCDEF0123"
API_KEY = "sk-abcdefghijklmnopqrst0123456789"
SECRET_LINE = f"Authorization: Bearer {BEARER_TOKEN}"
KEY_LINE = f"key: {API_KEY}"


def _action(description="ls -l"):
    return Action(
        description=description,
        risk_properties=("read-only",),
        verification_criteria=(),
    )


def _token(action=_UNSET, *, action_id="action-1"):
    return TokenHandoff(
        action_id=action_id,
        action=_action() if action is _UNSET else action,
        risk_class="read-only",
        gate="goal-check",
        issued_at=NOW,
        expiry=NOW + timedelta(hours=1),
        session=SESSION,
        state_snapshot=object(),
        elevation_bounds=(),
        override=False,
        consumed=False,
        invalidated=False,
    )


def _primitive(returns=None, log=None):
    def primitive(action, argv):
        if log is not None:
            log.append(argv)
        return RunResult(0, ()) if returns is None else returns

    return primitive


def _designated(line):
    return classify(
        SecretDatum(
            content=line,
            origin=SecretOrigin.CAPTURED,
            designation=NonSecretDesignation.SANITIZED_TEXT,
        )
    )


def _default_classify(line):
    return classify(SecretDatum(content=line, origin=SecretOrigin.CAPTURED))


def _guarded(
    action=None,
    token=None,
    *,
    primitive=None,
    started_at=NOW,
    timeout_bound=DEFAULT_TIMEOUT_BOUND,
    output_bound=DEFAULT_OUTPUT_BOUND,
    classify_output=None,
    trust_class=TrustClass.UNTRUSTED,
):
    """Build the guarded primitive and return it with its bound Action.

    The Action is shared between the token and the invocation, so the
    identity-based scoping check holds; a caller that wants a mismatch
    passes a different Action to ``_run``. Output is classified under
    ``secrets``' fail-closed CAPTURED origin by default; a test that
    wants plain lines to cross supplies ``_designated``.
    """
    action = _action() if action is None else action
    token = token if token is not None else _token(action=action)
    primitive = primitive if primitive is not None else _primitive()
    return (
        guard(
            primitive,
            token=token,
            started_at=started_at,
            timeout_bound=timeout_bound,
            output_bound=output_bound,
            classify_output=classify_output or _default_classify,
            trust_class=trust_class,
        ),
        action,
    )


def _run(guarded, action, argv=("ls", "-l"), now=NOW):
    return guarded(action, argv, now)


# --- public surface -----------------------------------------------------------


def test_guards_owns_exactly_the_guardrail_vocabulary():
    guards_module = importlib.import_module("episky.executor.guards")
    assert set(guards_module.__all__) == {
        "DEFAULT_OUTPUT_BOUND",
        "DEFAULT_TIMEOUT_BOUND",
        "GuardedPrimitive",
        "GuardedResult",
        "GuardrailFailure",
        "GuardrailReason",
        "guard",
    }


def test_guards_dataclasses_are_frozen_and_slotted():
    for cls in (GuardedResult, GuardrailFailure):
        params = cls.__dataclass_params__
        assert params.frozen and params.slots, f"{cls.__name__} is not frozen+slots"


def test_guards_placeholder_bounds_are_positive_literals():
    assert isinstance(DEFAULT_OUTPUT_BOUND, int) and DEFAULT_OUTPUT_BOUND > 0
    assert isinstance(DEFAULT_TIMEOUT_BOUND, int) and DEFAULT_TIMEOUT_BOUND > 0


def test_guarded_results_are_immutable():
    guarded, action = _guarded()
    result = _run(guarded, action)
    with pytest.raises(FrozenInstanceError):
        result.result.output = ("mutated",)
    with pytest.raises(FrozenInstanceError):
        result.failures = ()
    with pytest.raises(FrozenInstanceError):
        result.truncated = True


# --- scoping (RFC-0004 §4.9, P12) ---------------------------------------------


def test_guarded_run_is_scoped_to_the_one_approved_action():
    guarded, action = _guarded()
    outcome = _run(guarded, action)
    assert outcome.failures == ()
    assert outcome.result == RunResult(0, ())


def test_a_run_outside_the_token_scope_fails_closed_and_nothing_runs():
    calls = []
    guarded, action = _guarded(primitive=_primitive(log=calls))
    outcome = _run(guarded, _action(description="rm -rf /"))
    assert outcome.failures[0].reason is GuardrailReason.SCOPING
    assert "named scope" in outcome.failures[0].message
    assert outcome.result == RunResult(exit_status=None, output=())
    assert calls == []


def test_a_run_with_no_bound_action_fails_closed():
    calls = []
    guarded, action = _guarded(
        token=_token(action=None), primitive=_primitive(log=calls)
    )
    outcome = _run(guarded, action)
    assert outcome.failures[0].reason is GuardrailReason.SCOPING
    assert outcome.result == RunResult(exit_status=None, output=())
    assert calls == []


# --- deterministic timeout (RFC-0002 §2.8 → Interrupted; DN-59) ----------------


def test_a_run_within_budget_runs_normally():
    guarded, action = _guarded(started_at=NOW, timeout_bound=30)
    outcome = _run(guarded, action, now=NOW + timedelta(seconds=29))
    assert outcome.failures == ()
    assert outcome.result == RunResult(0, ())


def test_a_run_at_the_deadline_yields_outcome_unknown_and_nothing_runs():
    calls = []
    guarded, action = _guarded(
        started_at=NOW, timeout_bound=30, primitive=_primitive(log=calls)
    )
    outcome = _run(guarded, action, now=NOW + timedelta(seconds=30))
    assert outcome.failures[0].reason is GuardrailReason.TIMEOUT
    assert "time bound is exhausted" in outcome.failures[0].message
    assert outcome.result == RunResult(exit_status=None, output=())
    assert calls == []


def test_a_run_past_the_deadline_yields_outcome_unknown_and_nothing_runs():
    calls = []
    guarded, action = _guarded(
        started_at=NOW, timeout_bound=30, primitive=_primitive(log=calls)
    )
    outcome = _run(guarded, action, now=NOW + timedelta(seconds=31))
    assert outcome.failures[0].reason is GuardrailReason.TIMEOUT
    assert outcome.result == RunResult(exit_status=None, output=())
    assert calls == []


def test_the_timeout_decision_depends_on_explicit_time_inputs():
    guarded, action = _guarded(started_at=NOW, timeout_bound=30)
    assert _run(guarded, action, now=NOW + timedelta(seconds=29)).failures == ()
    assert _run(guarded, action, now=NOW + timedelta(seconds=31)).failures[
        0
    ].reason is (GuardrailReason.TIMEOUT)


def test_guard_rejects_non_positive_bounds():
    with pytest.raises(ValueError):
        _guarded(timeout_bound=0)
    with pytest.raises(ValueError):
        _guarded(output_bound=-1)


# --- bounded output capture (RFC-0001 §8.8; DN-18) -----------------------------


def test_output_past_the_bound_is_truncated_never_silently():
    many = tuple(f"line {i}" for i in range(10))
    guarded, action = _guarded(
        primitive=_primitive(returns=RunResult(0, many)),
        output_bound=3,
        classify_output=_designated,
    )
    outcome = _run(guarded, action)
    assert outcome.truncated is True
    assert outcome.result.output == ("«line 0»", "«line 1»", "«line 2»")
    assert outcome.failures == ()


def test_output_within_the_bound_is_not_truncated():
    two = ("a", "b")
    guarded, action = _guarded(
        primitive=_primitive(returns=RunResult(0, two)),
        output_bound=3,
        classify_output=_designated,
    )
    outcome = _run(guarded, action)
    assert outcome.truncated is False
    assert outcome.result.output == ("«a»", "«b»")


# --- redaction via secrets (SC8/SC10/SC14) -------------------------------------


def test_secret_shaped_output_is_redacted_via_secrets():
    guarded, action = _guarded(
        primitive=_primitive(returns=RunResult(0, (SECRET_LINE, KEY_LINE))),
        output_bound=10,
    )
    outcome = _run(guarded, action)
    assert outcome.failures == ()
    combined = "\n".join(outcome.result.output)
    assert "[REDACTED]" in combined
    assert BEARER_TOKEN not in combined
    assert API_KEY not in combined


def test_a_line_that_cannot_be_proven_non_secret_is_withheld_and_disclosed():
    guarded, action = _guarded(
        primitive=_primitive(returns=RunResult(0, ("usage: 42%",))),
        output_bound=10,
    )
    outcome = _run(guarded, action)
    assert outcome.result.exit_status == 0
    assert len(outcome.failures) == 1
    assert outcome.failures[0].reason is GuardrailReason.REDACTION
    assert "output line 0 withheld" in outcome.failures[0].message
    assert all("usage: 42%" not in line for line in outcome.result.output)


def test_explicitly_designated_non_secret_output_crosses_contained():
    def designated(line):
        return classify(
            SecretDatum(
                content=line,
                origin=SecretOrigin.CAPTURED,
                designation=NonSecretDesignation.SANITIZED_TEXT,
            )
        )

    guarded, action = _guarded(
        primitive=_primitive(returns=RunResult(0, ("disk-free 42G",))),
        output_bound=10,
        classify_output=designated,
    )
    outcome = _run(guarded, action)
    assert outcome.failures == ()
    assert outcome.result.output == ("«disk-free 42G»",)


def test_redaction_preserves_exit_status_when_the_run_completed():
    guarded, action = _guarded(
        primitive=_primitive(
            returns=RunResult(exit_status=1, output=("usage: 42%", "fatal"))
        ),
        output_bound=10,
    )
    outcome = _run(guarded, action)
    assert outcome.result.exit_status == 1
    assert any(f.reason is GuardrailReason.REDACTION for f in outcome.failures)


# --- fail closed and determinism -------------------------------------------------


def test_a_primitive_that_cannot_report_yields_outcome_unknown():
    def boom(action, argv):
        raise RuntimeError("primitive failed")

    guarded, action = _guarded(primitive=boom)
    outcome = _run(guarded, action)
    assert outcome.result == RunResult(exit_status=None, output=())
    assert outcome.failures == ()


def test_guarded_runs_are_deterministic():
    guarded, action = _guarded(
        primitive=_primitive(returns=RunResult(0, (SECRET_LINE,)))
    )
    assert _run(guarded, action) == _run(guarded, action)


def test_the_guarded_result_is_derived_only_from_explicit_inputs():
    action = _action()
    token = _token(action=action)
    guarded = guard(
        _primitive(returns=RunResult(0, ("ok",))),
        token=token,
        started_at=NOW,
        timeout_bound=30,
        output_bound=10,
        trust_class=TrustClass.UNTRUSTED,
    )
    assert _run(guarded, action) == _run(guarded, action)


# --- no hidden state, no authority creation -----------------------------------


def _has_call(node):
    return any(isinstance(n, ast.Call) for n in ast.walk(node))


def test_guards_module_has_no_module_level_state_beyond_all():
    tree = ast.parse(GUARDS_PATH.read_text(encoding="utf-8"))
    for stmt in tree.body:
        if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            targets = stmt.targets if isinstance(stmt, ast.Assign) else (stmt.target,)
            for target in targets:
                name = getattr(target, "id", type(target).__name__)
                assert isinstance(target, ast.Name), (
                    f"module-level assignment to {name}"
                )
                assert target.id == "__all__" or not _has_call(stmt.value), (
                    f"module-level assignment to {target.id} calls a constructor "
                    "at import time (hidden state)"
                )


def test_guards_creates_no_execution_authority():
    src = GUARDS_PATH.read_text(encoding="utf-8")
    for forbidden in (
        "def mint",
        "def approve",
        "def grant",
        "mint(",
        "import policy",
        "from episky.policy",
    ):
        assert forbidden not in src, f"guards.py contains {forbidden}"


# --- AST conformance ----------------------------------------------------------


def _module_imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield 0, alias.name
        elif isinstance(node, ast.ImportFrom):
            yield node.level, node.module or ""


def test_guards_imports_only_sanctioned_packages_and_stdlib():
    allowed_episky = {
        "episky.executor.runner",
        "episky.schema.action",
        "episky.secrets.classify",
        "episky.secrets.redact",
    }
    for level, module in _module_imports(GUARDS_PATH):
        assert level <= 1
        if module.startswith("episky"):
            assert module in allowed_episky, f"guards.py imports {module}"


def test_guards_imports_no_forbidden_stdlib():
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
    for _level, module in _module_imports(GUARDS_PATH):
        assert module.split(".")[0] not in forbidden, f"guards.py imports {module}"


def test_guards_calls_no_forbidden_runtime_builtin():
    tree = ast.parse(GUARDS_PATH.read_text(encoding="utf-8"))
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


def test_guards_has_no_top_level_runtime_logic():
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
    tree = ast.parse(GUARDS_PATH.read_text(encoding="utf-8"))
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


def test_guards_reads_no_clock_and_generates_no_random_or_crypto():
    src = GUARDS_PATH.read_text(encoding="utf-8")
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
        assert token not in src, f"guards.py contains {token}"
