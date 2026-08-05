"""Layer-2 conformance of the `verification` package (blueprint §4.1/§4.2, §8.5).

Mirrors test_factlayer_conformance.py for the verification package
(design review §3, §5, §12): every `verification` module imports only
the standard library and the packages blueprint §4.1 allows for Layer 2
— never the forbidden authority-bearing packages (design review §3.2),
never I/O-, concurrency-, or persistence-capable stdlib modules, never
the factlayer pipeline actuators (`collect`/`normalize`/`store`;
DN-25/DN-27: no Collect invocation, no normalization, no store write) —
carries no forbidden runtime logic and performs no I/O at import time,
and exposes exactly the public surface its owning RFC assigns (blueprint
§10; design review §5), with the public data structures frozen and
slot-based (V8, F8).
"""

import ast
import importlib
import pathlib
import sys

import pytest

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parents[1] / "src" / "episky"
VERIFICATION_ROOT = PACKAGE_ROOT / "verification"
STDLIB = set(sys.stdlib_module_names) | {"__future__"}

# Blueprint §4.1: Layer 2 allows verification to import these packages
# (plus its own package).
ALLOWED_PACKAGES = {"factlayer", "schema", "systemmodel"}

# Blueprint §4.2 / design review §3.2: verification never imports these
# authority-bearing or orchestration packages.
FORBIDDEN_PACKAGES = frozenset(
    {
        "providers",
        "executor",
        "policy",
        "skills",
        "context",
        "audit",
        "secrets",
        "trust",
        "core",
        "cli",
    }
)

# The factlayer pipeline actuators (DN-25, DN-27): verification never
# invokes Collect, never normalizes, and never writes to the store.
FORBIDDEN_FACTLAYER_ACTUATORS = frozenset(
    {"factlayer.collect", "factlayer.normalize", "factlayer.store"}
)

# Stdlib modules that can perform filesystem/network I/O, concurrency, or
# persistence; verification is a pure in-memory comparison (V8; DN-27).
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
# time. Function/class definitions, imports, docstrings, and the owned
# `__all__` assignment are the only permitted top-level statements.
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

# Design review §5 / blueprint §10 ownership, transcribed: each module's
# public surface is exactly the names its owning RFC assigns.
PUBLIC_SURFACE = {
    "compare": {
        "CompareResult",
        "PostconditionResult",
        "PostconditionVerdict",
        "compare",
    },
    "outcome": {"OutcomeRecord", "determine"},
}


def _verification_modules():
    return sorted(VERIFICATION_ROOT.glob("*.py"))


def _module_imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.level, alias.name
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


@pytest.mark.parametrize("path", _verification_modules(), ids=lambda p: p.name)
def test_verification_module_imports_only_stdlib_and_allowed_packages(path):
    for level, module in _module_imports(path):
        assert level <= 1, f"{path.name}: relative import escapes verification"
        if level == 1:
            continue
        parts = module.split(".")
        if parts[0] == "episky":
            assert len(parts) > 1 and (
                parts[1] == "verification" or parts[1] in ALLOWED_PACKAGES
            ), (
                f"{path.name} imports episky.{'.'.join(parts[1:])}, but "
                f"verification allows only {sorted(ALLOWED_PACKAGES)} "
                "and its own package"
            )
        else:
            assert parts[0] in STDLIB, (
                f"{path.name} imports {module}, which is not stdlib"
            )


@pytest.mark.parametrize("path", _verification_modules(), ids=lambda p: p.name)
def test_verification_module_never_imports_a_forbidden_package(path):
    for _level, module in _module_imports(path):
        parts = module.split(".")
        if parts[0] == "episky" and len(parts) > 1:
            assert parts[1] not in FORBIDDEN_PACKAGES, (
                f"{path.name} imports episky.{parts[1]}, a forbidden "
                "authority-bearing package"
            )


@pytest.mark.parametrize("path", _verification_modules(), ids=lambda p: p.name)
def test_verification_module_never_imports_a_factlayer_actuator(path):
    for _level, module in _module_imports(path):
        parts = module.split(".")
        if parts[0] == "episky":
            imported = ".".join(parts[:2])
            assert imported not in FORBIDDEN_FACTLAYER_ACTUATORS, (
                f"{path.name} imports {imported}; verification never "
                "invokes Collect, normalizes, or writes the store "
                "(DN-25, DN-27)"
            )


@pytest.mark.parametrize("path", _verification_modules(), ids=lambda p: p.name)
def test_verification_module_imports_no_io_or_persistence_stdlib(path):
    for _level, module in _module_imports(path):
        parts = module.split(".")
        if parts[0] != "episky":
            assert parts[0] not in FORBIDDEN_STDLIB, (
                f"{path.name} imports {module}, an I/O/concurrency/"
                "persistence-capable stdlib module"
            )


@pytest.mark.parametrize("path", _verification_modules(), ids=lambda p: p.name)
def test_verification_module_calls_no_forbidden_io_builtin(path):
    calls = set(_call_names(path))
    assert calls.isdisjoint(FORBIDDEN_CALLS), (
        f"{path.name} calls {sorted(calls & FORBIDDEN_CALLS)}; verification "
        "performs no filesystem, network, console, or execution side effects"
    )


@pytest.mark.parametrize("path", _verification_modules(), ids=lambda p: p.name)
def test_verification_module_has_no_top_level_runtime_logic(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for stmt in tree.body:
        assert not isinstance(stmt, FORBIDDEN_TOPLEVEL), (
            f"{path.name}: top-level {type(stmt).__name__} is runtime logic "
            "at import time"
        )
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                assert isinstance(target, ast.Name), (
                    f"{path.name}: module-level assignment to "
                    f"{getattr(target, 'id', type(target).__name__)}"
                )
                assert target.id == "__all__", (
                    f"{path.name}: module-level assignment to {target.id} is "
                    "not the owned public surface"
                )


@pytest.mark.parametrize("module", sorted(PUBLIC_SURFACE))
def test_verification_public_surface_is_exactly_the_owned_vocabulary(module):
    mod = importlib.import_module(f"episky.verification.{module}")
    assert set(mod.__all__) == PUBLIC_SURFACE[module]


@pytest.mark.parametrize("module", sorted(PUBLIC_SURFACE))
def test_verification_public_names_are_defined_by_their_owning_module(module):
    mod = importlib.import_module(f"episky.verification.{module}")
    for name in PUBLIC_SURFACE[module]:
        value = getattr(mod, name)
        owner = getattr(value, "__module__", None)
        if owner is None:
            assert name in mod.__dict__, f"{name} is not defined in verification"
        else:
            assert owner == f"episky.verification.{module}", (
                f"{name} is defined in {owner}, not its owning module"
            )


def test_verification_public_surface_has_no_ownership_overlap():
    names = [name for surface in PUBLIC_SURFACE.values() for name in surface]
    assert len(names) == len(set(names)), "a name is owned by two modules"


def test_verification_dataclasses_are_frozen_and_slotted():
    for module in PUBLIC_SURFACE:
        mod = importlib.import_module(f"episky.verification.{module}")
        for name in PUBLIC_SURFACE[module]:
            value = getattr(mod, name)
            if not isinstance(value, type) or not hasattr(
                value, "__dataclass_params__"
            ):
                continue
            params = value.__dataclass_params__
            assert params.frozen and params.slots, (
                f"episky.verification.{module}.{name} is a dataclass that is "
                "not frozen and slot-based (V8, F8)"
            )


def test_verification_package_has_exactly_the_blueprint_modules():
    modules = {path.stem for path in VERIFICATION_ROOT.glob("*.py")}
    assert modules == {"__init__", "compare", "outcome"}


def test_lower_layers_never_import_verification():
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        source_pkg = path.parts[-2]
        if source_pkg not in (
            "schema",
            "systemmodel",
            "collectors",
            "factlayer",
        ):
            continue
        for _level, module in _module_imports(path):
            assert "verification" not in module, (
                f"{path.relative_to(PACKAGE_ROOT)} imports {module}; Layer 0/1 "
                "and the pipeline never import the verification layer"
            )
