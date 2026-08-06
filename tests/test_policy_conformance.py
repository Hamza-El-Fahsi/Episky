"""Layer-3 conformance of the `policy` package (blueprint §4.1, §5, §10).

Mirrors test_trust_conformance.py / test_secrets_conformance.py for the
Approval & Policy Engine package (design review §3, §8, §12): every policy
module imports only the standard library, `episky.schema`, and the policy
package itself — never the authority-bearing or orchestration packages, and
never the declared-but-latent `trust`/`factlayer`/`systemmodel` edges
(DN-47) — never I/O-, concurrency-, or persistence-capable stdlib modules,
carries no forbidden runtime logic and performs no I/O at import time, and
exposes exactly the public surface its owning RFC assigns (blueprint §10;
design review §4), with the public data structures frozen and slot-based
(DN-34, Q6). The facade re-exports nothing: no owned name and no internal
placeholder leaks at package level. Layer 0 never imports policy.
"""

import ast
import importlib
import pathlib
import sys

import pytest

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parents[1] / "src" / "episky"
POLICY_ROOT = PACKAGE_ROOT / "policy"
STDLIB = set(sys.stdlib_module_names) | {"__future__"}

# Blueprint §4.1: the policy layer may import schema (plus its own package).
# The trust/factlayer rows are declared in blueprint §4.1 but stay latent
# this iteration (DN-47; the C1–C3 briefs) — a conformance failure below.
ALLOWED_PACKAGES = {"schema"}

# Design review §3.2 / the C1–C3 briefs: policy never imports these
# authority-bearing, orchestration, or higher-layer packages, nor the
# latent trust/factlayer/systemmodel edges.
FORBIDDEN_PACKAGES = frozenset(
    {
        "collectors",
        "trust",
        "factlayer",
        "verification",
        "secrets",
        "executor",
        "audit",
        "context",
        "providers",
        "skills",
        "core",
        "cli",
        "systemmodel",
    }
)

# Stdlib modules that can perform filesystem/network I/O, concurrency, or
# persistence; policy is a pure, in-memory, deterministic layer (DN-1).
FORBIDDEN_STDLIB = frozenset(
    {
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
    }
)

# I/O-capable builtins and functions that must never appear as calls, at
# any scope (no filesystem, no network, no console, no execution).
FORBIDDEN_CALLS = {
    "open",
    "print",
    "input",
    "exec",
    "eval",
    "breakpoint",
    "__import__",
}

# Forbidden top-level statements: control flow or side effects at import
# time. Imports, function/class definitions, docstrings, module-level
# constant data, and the owned `__all__` assignment are the only permitted
# top-level statements.
FORBIDDEN_TOPLEVEL = (
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

# The only functions policy modules may call while building module-level
# constant data: `MappingProxyType`/`frozenset` for the vocabulary and
# table mappings and `timedelta` for the deterministic expiry windows.
ALLOWED_TOPLEVEL_CALLS = frozenset({"MappingProxyType", "frozenset", "timedelta"})

# Design review §4 / blueprint §10 ownership, transcribed from the C1–C3
# ratification: each module's public surface is exactly the names its
# owning RFC assigns.
PUBLIC_SURFACE = {
    "classify": {
        "Classification",
        "Gate",
        "PlanClassification",
        "RISK_PROPERTIES",
        "RiskClass",
        "classify",
        "classify_plan",
        "meet",
    },
    "gates": {
        "ALLOWLISTED_READ_ONLY_GATE",
        "CLASS_GATES",
        "gate_for",
    },
    "policy": {
        "ElevationBound",
        "Policy",
        "PolicyDecision",
        "StandingApproval",
        "allowlisted",
        "decide",
        "elevation_bound_for",
        "load",
        "retry_ceiling",
        "standing_approval_applies",
    },
    "tokens": {
        "EXPIRY_WINDOWS",
        "Decision",
        "InvalidationReason",
        "MintOutcome",
        "RecordKind",
        "Token",
        "TokenRecord",
        "TokenStatus",
        "consume",
        "expiry_for",
        "invalidate",
        "mint",
        "revalidate",
        "validate",
    },
}

OWNED_NAMES = {name for surface in PUBLIC_SURFACE.values() for name in surface}


def _policy_modules():
    return sorted(
        path for path in POLICY_ROOT.glob("*.py") if not path.name.startswith("__")
    )


def _module_imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield 0, alias.name
        elif isinstance(node, ast.ImportFrom):
            yield node.level, node.module or ""


def _call_names(path):
    for node in ast.walk(ast.parse(path.read_text(encoding="utf-8"))):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                yield func.id
            elif isinstance(func, ast.Attribute):
                yield func.attr


@pytest.mark.parametrize("path", _policy_modules(), ids=lambda p: p.name)
def test_policy_module_imports_only_stdlib_and_allowed_packages(path):
    for level, module in _module_imports(path):
        assert level <= 1, f"{path.name}: relative import escapes policy"
        if level == 1:
            continue
        parts = module.split(".")
        if parts[0] == "episky":
            assert len(parts) > 1 and (
                parts[1] == "policy" or parts[1] in ALLOWED_PACKAGES
            ), (
                f"{path.name} imports episky.{'.'.join(parts[1:])}, but policy "
                f"allows only {sorted(ALLOWED_PACKAGES)} and its own package"
            )
        else:
            assert parts[0] in STDLIB, (
                f"{path.name} imports {module}, which is not stdlib"
            )


@pytest.mark.parametrize("path", _policy_modules(), ids=lambda p: p.name)
def test_policy_module_never_imports_a_forbidden_package(path):
    for _level, module in _module_imports(path):
        parts = module.split(".")
        if parts[0] == "episky" and len(parts) > 1:
            assert parts[1] not in FORBIDDEN_PACKAGES, (
                f"{path.name} imports episky.{parts[1]}, a forbidden "
                "authority-bearing, higher-layer, or latent package"
            )


@pytest.mark.parametrize("path", _policy_modules(), ids=lambda p: p.name)
def test_policy_module_keeps_the_declared_edges_latent(path):
    for _level, module in _module_imports(path):
        parts = module.split(".")
        if parts[0] == "episky" and len(parts) > 1:
            assert parts[1] not in {"trust", "factlayer", "systemmodel"}, (
                f"{path.name} imports episky.{parts[1]}; the edge stays latent (DN-47)"
            )


@pytest.mark.parametrize("path", _policy_modules(), ids=lambda p: p.name)
def test_policy_module_imports_no_io_or_persistence_stdlib(path):
    for _level, module in _module_imports(path):
        parts = module.split(".")
        if parts[0] != "episky":
            assert parts[0] not in FORBIDDEN_STDLIB, (
                f"{path.name} imports {module}, an I/O/concurrency/"
                "persistence-capable stdlib module"
            )


@pytest.mark.parametrize("path", _policy_modules(), ids=lambda p: p.name)
def test_policy_module_calls_no_forbidden_io_builtin(path):
    calls = set(_call_names(path))
    assert calls.isdisjoint(FORBIDDEN_CALLS), (
        f"{path.name} calls {sorted(calls & FORBIDDEN_CALLS)}; policy performs "
        "no filesystem, network, console, or execution side effects"
    )


@pytest.mark.parametrize("path", _policy_modules(), ids=lambda p: p.name)
def test_policy_module_reads_no_clock(path):
    src = path.read_text(encoding="utf-8")
    for token in (
        "datetime.now",
        "utcnow",
        "time.time",
        "time.monotonic",
        "perf_counter",
        "import time",
        "from time import",
    ):
        assert token not in src, f"{path.name} reads a clock"


@pytest.mark.parametrize("path", _policy_modules(), ids=lambda p: p.name)
def test_policy_module_generates_no_random_or_crypto(path):
    src = path.read_text(encoding="utf-8")
    for token in (
        "import random",
        "random.",
        "os.urandom",
        "import uuid",
        "uuid4",
        "import hmac",
        "import hashlib",
        "import secrets",
        "secrets.token",
    ):
        assert token not in src, f"{path.name} generates a random/opaque value"


@pytest.mark.parametrize("path", _policy_modules(), ids=lambda p: p.name)
def test_policy_module_has_no_top_level_runtime_logic(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for stmt in tree.body:
        assert not isinstance(stmt, FORBIDDEN_TOPLEVEL), (
            f"{path.name}: top-level {type(stmt).__name__} is runtime logic "
            "at import time"
        )
        if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            for target in (
                stmt.targets if isinstance(stmt, ast.Assign) else (stmt.target,)
            ):
                assert isinstance(target, ast.Name), (
                    f"{path.name}: module-level assignment to "
                    f"{getattr(target, 'id', type(target).__name__)}"
                )


@pytest.mark.parametrize("path", _policy_modules(), ids=lambda p: p.name)
def test_policy_module_builds_only_constant_data_at_module_level(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for stmt in tree.body:
        value = getattr(stmt, "value", None)
        if isinstance(stmt, (ast.Assign, ast.AnnAssign)) and value is not None:
            for node in ast.walk(value):
                if isinstance(node, ast.Call):
                    func = node.func
                    target = func.id if isinstance(func, ast.Name) else func.attr
                    assert target in ALLOWED_TOPLEVEL_CALLS, (
                        f"{path.name}: module-level call to {target} is not a "
                        "constant-data constructor"
                    )


@pytest.mark.parametrize("module", sorted(PUBLIC_SURFACE))
def test_policy_public_surface_is_exactly_the_owned_vocabulary(module):
    mod = importlib.import_module(f"episky.policy.{module}")
    assert set(mod.__all__) == PUBLIC_SURFACE[module]


@pytest.mark.parametrize("module", sorted(PUBLIC_SURFACE))
def test_policy_public_names_are_defined_by_their_owning_module(module):
    mod = importlib.import_module(f"episky.policy.{module}")
    for name in PUBLIC_SURFACE[module]:
        assert name in mod.__dict__, f"{name} is not defined in {module}"


def test_policy_public_surface_has_no_ownership_overlap():
    assert len(OWNED_NAMES) == len(
        {name for surface in PUBLIC_SURFACE.values() for name in surface}
    ), "a name is owned by two policy modules"


@pytest.mark.parametrize("module", sorted(PUBLIC_SURFACE))
def test_policy_public_surface_leaks_no_internal_placeholder(module):
    mod = importlib.import_module(f"episky.policy.{module}")
    for name in set(mod.__all__):
        assert not name.startswith("_"), (
            f"episky.policy.{module} exports the private placeholder {name}"
        )


def test_policy_dataclasses_are_frozen_and_slotted():
    for module in PUBLIC_SURFACE:
        mod = importlib.import_module(f"episky.policy.{module}")
        for name in PUBLIC_SURFACE[module]:
            value = getattr(mod, name)
            is_dataclass = hasattr(value, "__dataclass_params__")
            if not isinstance(value, type) or not is_dataclass:
                continue
            params = value.__dataclass_params__
            assert params.frozen and params.slots, (
                f"episky.policy.{module}.{name} is a dataclass that is not "
                "frozen and slot-based (DN-34)"
            )


def test_policy_package_has_exactly_the_ratified_modules():
    modules = {path.stem for path in POLICY_ROOT.glob("*.py")}
    assert modules == {"__init__", "classify", "gates", "tokens", "policy"}


def test_policy_facade_reexports_nothing_and_leaks_nothing():
    mod = importlib.import_module("episky.policy")
    public = {name for name in dir(mod) if not name.startswith("_")}
    assert public <= {"classify", "gates", "tokens", "policy"}, (
        "the facade exposes a public name beyond its submodules"
    )
    private = {
        name for name in dir(mod) if name.startswith("_") and not name.startswith("__")
    }
    assert private == set(), "the facade must leak no internal placeholders"


def test_schema_never_imports_policy():
    schema_root = PACKAGE_ROOT / "schema"
    for path in sorted(schema_root.rglob("*.py")):
        for _level, module in _module_imports(path):
            assert "policy" not in module, (
                f"schema imports {module}; Layer 0 never imports the policy layer"
            )
