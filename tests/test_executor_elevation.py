"""Scoped elevation lifecycle (RFC-0008 §8; RFC-0001 §8.6; RFC-0009
SC10; DN-53, DN-60).

Behavioral tests for Iteration 8 Commit C4 (`executor/elevation.py`):
the deterministic elevation lifecycle — a per-Action request carrying
its bounds (which `policy` already enforced as at-least-Consequential,
DN-53) and a revocation that fires at the end of that Action or on any
invalidation. Elevation never covers unapproved work (the request must
be for the token's one approved Action), never persists (pure immutable
values, no module state), never forms a standing root session, and
never displays or records a value (SC10). The machine's own mechanism
(RFC-0021 §3.3, Draft) is injected at the boundary and called with the
REQUEST/REVOKE signals; the module performs no I/O itself. Every
refusal and every failed revocation is disclosed (RFC-0001 §8.12), and a
failed revocation never claims the elevation revoked (fail closed). AST
conformance mirrors the runner: no forbidden imports, no forbidden
stdlib, no forbidden runtime calls, no top-level runtime logic.
"""

import ast
import importlib
import pathlib
from dataclasses import FrozenInstanceError
from datetime import datetime, timedelta

import pytest

from episky.executor.elevation import (
    ElevationOutcome,
    ElevationReason,
    ElevationRequest,
    ElevationSignal,
    ElevationState,
    request,
    revoke,
)
from episky.executor.runner import TokenHandoff
from episky.schema.action import Action

ELEVATION_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "executor"
    / "elevation.py"
)

NOW = datetime(2026, 8, 7, 12, 0, 0)
LATER = datetime(2026, 8, 7, 12, 0, 30)

SESSION = object()
BOUND = object()
BOUND_2 = object()
_UNSET = object()


def _action(description="ls -l"):
    return Action(
        description=description,
        risk_properties=("read-only",),
        verification_criteria=(),
    )


def _token(action=_UNSET, *, elevation_bounds=_UNSET):
    return TokenHandoff(
        action_id="action-1",
        action=_action() if action is _UNSET else action,
        risk_class="consequential",
        gate="goal-check",
        issued_at=NOW,
        expiry=NOW + timedelta(hours=1),
        session=SESSION,
        state_snapshot=object(),
        elevation_bounds=() if elevation_bounds is _UNSET else elevation_bounds,
        override=False,
        consumed=False,
        invalidated=False,
    )


def _mechanism(result=True, log=None):
    def mechanism(mechanism_request, signal):
        if log is not None:
            log.append((mechanism_request, signal))
        return result

    return mechanism


def _active(mechanism=None, action=None, token=None, now=NOW):
    mechanism = mechanism if mechanism is not None else _mechanism(True)
    action = action if action is not None else _action()
    token = (
        token if token is not None else _token(action=action, elevation_bounds=(BOUND,))
    )
    return request(mechanism, action, token, now=now)


# --- public surface -----------------------------------------------------------


def test_elevation_owns_exactly_the_elevation_vocabulary():
    elevation_module = importlib.import_module("episky.executor.elevation")
    assert set(elevation_module.__all__) == {
        "ElevationMechanism",
        "ElevationOutcome",
        "ElevationReason",
        "ElevationRequest",
        "ElevationSignal",
        "ElevationState",
        "request",
        "revoke",
    }


def test_elevation_dataclasses_are_frozen_and_slotted():
    for cls in (ElevationOutcome, ElevationRequest):
        params = cls.__dataclass_params__
        assert params.frozen and params.slots, f"{cls.__name__} is not frozen+slots"


def test_elevation_outcomes_are_immutable():
    active = _active()
    with pytest.raises(FrozenInstanceError):
        active.state = ElevationState.REVOKED
    with pytest.raises(FrozenInstanceError):
        active.started_at = LATER


# --- the request never covers unapproved work (RFC-0008 §8) --------------------


def test_a_request_with_no_bound_action_is_refused():
    outcome = request(
        _mechanism(True),
        _action(),
        _token(action=None, elevation_bounds=(BOUND,)),
        now=NOW,
    )
    assert outcome.state is ElevationState.REFUSED
    assert outcome.reason is ElevationReason.NOT_APPROVED
    assert outcome.message is not None
    assert outcome.started_at is None


def test_a_request_for_an_unapproved_action_is_refused():
    outcome = request(
        _mechanism(True),
        _action(description="rm -rf /"),
        _token(elevation_bounds=(BOUND,)),
        now=NOW,
    )
    assert outcome.state is ElevationState.REFUSED
    assert outcome.reason is ElevationReason.NOT_APPROVED
    assert "unapproved work" in outcome.message


# --- the request carries its bounds (P12; DN-53) -------------------------------


def test_a_request_without_token_elevation_bounds_is_refused():
    action = _action()
    outcome = request(
        _mechanism(True), action, _token(action=action, elevation_bounds=()), now=NOW
    )
    assert outcome.state is ElevationState.REFUSED
    assert outcome.reason is ElevationReason.NO_ELEVATION
    assert "no elevation bounds" in outcome.message
    assert outcome.request is None


# --- the request lifecycle (DN-60) --------------------------------------------


def test_a_granted_request_is_active_and_carries_the_bounds():
    logged = []
    mechanism = _mechanism(True, log=logged)
    action = _action()
    outcome = request(
        mechanism,
        action,
        _token(action=action, elevation_bounds=(BOUND, BOUND_2)),
        now=NOW,
    )
    assert outcome.state is ElevationState.ACTIVE
    assert outcome.reason is None
    assert outcome.message is None
    assert outcome.started_at == NOW
    assert outcome.ended_at is None
    assert outcome.request is not None
    assert outcome.request.action_id == "action-1"
    assert outcome.request.action is action
    assert outcome.request.bounds == (BOUND, BOUND_2)
    assert outcome.request.session is SESSION
    assert outcome.request.issued_at == NOW
    assert len(logged) == 1
    assert logged[0][1] is ElevationSignal.REQUEST
    assert logged[0][0] is outcome.request


def test_a_refused_mechanism_fails_closed_and_is_disclosed():
    action = _action()
    outcome = request(
        _mechanism(False),
        action,
        _token(action=action, elevation_bounds=(BOUND,)),
        now=NOW,
    )
    assert outcome.state is ElevationState.REFUSED
    assert outcome.reason is ElevationReason.MECHANISM_REFUSED
    assert "declined" in outcome.message
    assert outcome.started_at is None


def test_the_request_is_deterministic():
    action = _action()
    token = _token(action=action, elevation_bounds=(BOUND,))
    assert request(_mechanism(True), action, token, now=NOW) == request(
        _mechanism(True), action, token, now=NOW
    )


# --- the revocation (RFC-0008 §8; RFC-0001 §8.6) -------------------------------


def test_an_active_elevation_is_revoked_at_end_or_invalidation():
    logged = []
    mechanism = _mechanism(True, log=logged)
    active = _active(mechanism=mechanism)
    outcome = revoke(mechanism, active, now=LATER)
    assert outcome.state is ElevationState.REVOKED
    assert outcome.reason is None
    assert outcome.ended_at == LATER
    assert outcome.started_at == NOW
    assert len(logged) == 2
    assert logged[1][1] is ElevationSignal.REVOKE


def test_a_failed_revocation_never_claims_revoked():
    active = _active(mechanism=_mechanism(True))
    outcome = revoke(_mechanism(False), active, now=LATER)
    assert outcome.state is ElevationState.ACTIVE
    assert outcome.reason is ElevationReason.REVOKE_FAILED
    assert "not revoked" in outcome.message
    assert outcome.ended_at is None


def test_revoking_a_refused_elevation_is_a_no_op():
    action = _action()
    refused = request(
        _mechanism(False),
        action,
        _token(action=action, elevation_bounds=(BOUND,)),
        now=NOW,
    )
    assert revoke(_mechanism(True), refused, now=LATER) == refused


def test_revoking_an_already_revoked_elevation_is_a_no_op():
    active = _active(mechanism=_mechanism(True))
    revoked = revoke(_mechanism(True), active, now=LATER)
    assert revoke(_mechanism(True), revoked, now=LATER) == revoked


def test_the_revocation_is_deterministic():
    active = _active(mechanism=_mechanism(True))
    assert revoke(_mechanism(True), active, now=LATER) == revoke(
        _mechanism(True), active, now=LATER
    )


# --- SC10: elevation exposes nothing, persists nothing -------------------------


def test_elevation_never_exposes_a_value():
    active = _active()
    assert list(ElevationRequest.__dataclass_fields__) == [
        "action_id",
        "action",
        "bounds",
        "session",
        "issued_at",
    ]
    for bound in active.request.bounds:
        assert not isinstance(bound, str)
    assert active.request.bounds == (BOUND,)
    assert active.message is None or "secret" not in active.message


def test_elevation_outcomes_are_values_with_no_module_state():
    first = _active()
    second = _active()
    assert first == second
    assert first.request is not second.request  # each request is its own value


# --- no hidden state, no authority creation -----------------------------------


def _has_call(node):
    return any(isinstance(n, ast.Call) for n in ast.walk(node))


def test_elevation_module_has_no_module_level_state_beyond_all():
    tree = ast.parse(ELEVATION_PATH.read_text(encoding="utf-8"))
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


def test_elevation_creates_no_execution_authority_and_no_secret_handling():
    src = ELEVATION_PATH.read_text(encoding="utf-8")
    for forbidden in (
        "def mint",
        "def approve",
        "def grant",
        "mint(",
        "import policy",
        "from episky.policy",
        "import secrets",
        "from episky.secrets",
        "sudo",
        "polkit",
        "subprocess",
    ):
        assert forbidden not in src, f"elevation.py contains {forbidden}"


# --- AST conformance ----------------------------------------------------------


def _module_imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield 0, alias.name
        elif isinstance(node, ast.ImportFrom):
            yield node.level, node.module or ""


def test_elevation_imports_only_sanctioned_packages_and_stdlib():
    allowed_episky = {
        "episky.executor.runner",
        "episky.schema.action",
    }
    for level, module in _module_imports(ELEVATION_PATH):
        assert level <= 1
        if module.startswith("episky"):
            assert module in allowed_episky, f"elevation.py imports {module}"


def test_elevation_imports_no_forbidden_stdlib():
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
    for _level, module in _module_imports(ELEVATION_PATH):
        assert module.split(".")[0] not in forbidden, f"elevation.py imports {module}"


def test_elevation_calls_no_forbidden_runtime_builtin():
    tree = ast.parse(ELEVATION_PATH.read_text(encoding="utf-8"))
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


def test_elevation_has_no_top_level_runtime_logic():
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
    tree = ast.parse(ELEVATION_PATH.read_text(encoding="utf-8"))
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


def test_elevation_reads_no_clock_and_generates_no_random_or_crypto():
    src = ELEVATION_PATH.read_text(encoding="utf-8")
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
        assert token not in src, f"elevation.py contains {token}"
