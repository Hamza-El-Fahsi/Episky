"""Layer-2 conformance of the `collectors` and `factlayer` packages.

Mirrors test_schema_conformance.py / test_systemmodel_conformance.py for
the pipeline packages (design review §9.2): every `collectors` and
`factlayer` module imports only the standard library and the packages
blueprint §4.1 allows for its layer — never the forbidden
authority-bearing packages (F2, F3, F6; DN-7), never I/O-, concurrency-,
or persistence-capable stdlib modules — carries no forbidden runtime
logic and performs no I/O at import time, and exposes exactly the public
surface its owning RFC assigns (blueprint §10), with the internal
placeholders (MachineIdentity, ObservationReference, the placeholder
bounds) never leaking into a public API (DN-15, DN-18).
"""

import ast
import importlib
import pathlib
import sys

import pytest

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parents[1] / "src" / "episky"
STDLIB = set(sys.stdlib_module_names) | {"__future__"}

# Blueprint §4.1 allowed targets per package; DN-7 keeps `trust` out of the
# pipeline until its own iteration, so it is not allowed here.
ALLOWED_PACKAGES = {
    "collectors": {"schema", "systemmodel"},
    "factlayer": {"collectors", "schema", "systemmodel"},
}

# Blueprint §4.2 / design review §3.2: the pipeline never imports these
# authority-bearing or future packages (F2, F3, F6; verification is
# Iteration 4; trust is deferred by DN-7).
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
        "verification",
        "core",
        "cli",
    }
)

# Stdlib modules that can perform filesystem/network I/O, concurrency, or
# persistence; the pipeline is read-only in-memory state (A4; RFC-0005 §2;
# DN-19) and must never import them.
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

# I/O-capable builtins and functions that must never appear as calls in the
# pipeline, at any scope (no filesystem, no network, no console).
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
# time. Function and class definitions, imports, docstrings, and owned
# module-level assignments are the only permitted top-level statements.
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

# Design review §11 / blueprint §10 ownership, transcribed: each module's
# public surface is exactly the names its owning RFC assigns.
PUBLIC_SURFACE = {
    "collectors.registry": {"COLLECTOR_SPECS", "CollectorSpec"},
    "factlayer.collect": {"Observation", "RawOutput", "collect"},
    "factlayer.normalize": {"normalize"},
    "factlayer.provenance": {"build_provenance", "freshness_state"},
    "factlayer.store": {
        "FactStore",
        "FactIdentity",
        "RetiredFact",
        "StoreOutcome",
        "StoreRecord",
        "REASON_MACHINE_MISMATCH",
        "REASON_NOT_SUPERSEDING",
        "REASON_PROVENANCE_LOST",
        "REASON_STATUS_UNESTABLISHED",
        "REASON_SUPERSEDED",
        "record",
    },
}

# Module-level names each module legitimately assigns beyond `__all__`:
# owned data tables and the internal placeholders/markers.
DATA_TABLES = {
    "collectors.registry": {"COLLECTOR_SPECS"},
    "factlayer.collect": {"DEFAULT_OUTPUT_BOUND"},
    "factlayer.normalize": {"CANONICAL_DEFINITIONS", "_MACHINE_IDENTITY"},
    "factlayer.provenance": {
        "DEFAULT_FRESHNESS_BOUND",
        "_POSSIBLY_STALE_AFTER",
        "_OBSERVATION_REFERENCE",
    },
    "factlayer.store": {
        "CURRENT_STATUSES",
        "REASON_PROVENANCE_LOST",
        "REASON_MACHINE_MISMATCH",
        "REASON_STATUS_UNESTABLISHED",
        "REASON_NOT_SUPERSEDING",
        "REASON_SUPERSEDED",
    },
}

# The internal placeholders and policy constants must never be public.
NON_PUBLIC_INTERNALS = {
    "MachineIdentity",
    "ObservationReference",
    "DEFAULT_OUTPUT_BOUND",
    "DEFAULT_FRESHNESS_BOUND",
    "_POSSIBLY_STALE_AFTER",
}


def _pipeline_modules():
    for package in ("collectors", "factlayer"):
        for path in sorted((PACKAGE_ROOT / package).glob("*.py")):
            yield package, path


def _module_imports(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.level, alias.name
        elif isinstance(node, ast.ImportFrom):
            yield node.level, node.module or ""


def _call_names(tree):
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            if isinstance(func, ast.Name):
                yield func.id
            elif isinstance(func, ast.Attribute):
                yield func.attr


@pytest.mark.parametrize(
    "path", sorted(p[1] for p in _pipeline_modules()), ids=lambda p: p.name
)
def test_pipeline_module_imports_only_stdlib_and_allowed_packages(path):
    package = path.parts[-2]
    for level, module in _module_imports(ast.parse(path.read_text(encoding="utf-8"))):
        assert level <= 1, f"{path.name}: relative import escapes its package"
        if level == 1:
            continue
        parts = module.split(".")
        if parts[0] == "episky":
            assert len(parts) > 1 and (
                parts[1] == package or parts[1] in ALLOWED_PACKAGES[package]
            ), (
                f"{path.name} imports episky.{'.'.join(parts[1:])}, but "
                f"{package} allows only {sorted(ALLOWED_PACKAGES[package])} "
                "and its own package"
            )
        else:
            assert parts[0] in STDLIB, (
                f"{path.name} imports {module}, which is not stdlib"
            )


@pytest.mark.parametrize(
    "path", sorted(p[1] for p in _pipeline_modules()), ids=lambda p: p.name
)
def test_pipeline_module_never_imports_a_forbidden_package(path):
    for _level, module in _module_imports(ast.parse(path.read_text(encoding="utf-8"))):
        parts = module.split(".")
        if parts[0] == "episky" and len(parts) > 1:
            assert parts[1] not in FORBIDDEN_PACKAGES, (
                f"{path.name} imports episky.{parts[1]}, a forbidden "
                "authority-bearing package"
            )


@pytest.mark.parametrize(
    "path", sorted(p[1] for p in _pipeline_modules()), ids=lambda p: p.name
)
def test_pipeline_module_imports_no_io_or_persistence_stdlib(path):
    for _level, module in _module_imports(ast.parse(path.read_text(encoding="utf-8"))):
        parts = module.split(".")
        if parts[0] != "episky":
            assert parts[0] not in FORBIDDEN_STDLIB, (
                f"{path.name} imports {module}, an I/O/concurrency/"
                "persistence-capable stdlib module"
            )


@pytest.mark.parametrize(
    "path", sorted(p[1] for p in _pipeline_modules()), ids=lambda p: p.name
)
def test_pipeline_module_calls_no_forbidden_io_builtin(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    calls = set(_call_names(tree))
    assert calls.isdisjoint(FORBIDDEN_CALLS), (
        f"{path.name} calls {sorted(calls & FORBIDDEN_CALLS)}; the pipeline "
        "performs no filesystem, network, or console I/O"
    )


@pytest.mark.parametrize(
    "path", sorted(p[1] for p in _pipeline_modules()), ids=lambda p: p.name
)
def test_pipeline_module_has_no_top_level_runtime_logic(path):
    module = path.stem
    package = path.parts[-2]
    key = f"{package}.{module}"
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
                assert target.id == "__all__" or target.id in DATA_TABLES[key], (
                    f"{path.name}: module-level assignment to {target.id} is "
                    "not an owned data table"
                )


@pytest.mark.parametrize("module", sorted(PUBLIC_SURFACE))
def test_pipeline_public_surface_is_exactly_the_owned_vocabulary(module):
    mod = importlib.import_module(f"episky.{module}")
    assert set(mod.__all__) == PUBLIC_SURFACE[module]


@pytest.mark.parametrize("module", sorted(PUBLIC_SURFACE))
def test_pipeline_public_names_are_defined_by_their_owning_module(module):
    mod = importlib.import_module(f"episky.{module}")
    for name in PUBLIC_SURFACE[module]:
        value = getattr(mod, name)
        owner = getattr(value, "__module__", None)
        if owner is None:
            assert name in mod.__dict__, f"{name} is not defined in episky.{module}"
        else:
            assert owner == f"episky.{module}", (
                f"{name} is defined in {owner}, not its owning module"
            )


def test_pipeline_public_surface_has_no_ownership_overlap():
    names = [name for surface in PUBLIC_SURFACE.values() for name in surface]
    assert len(names) == len(set(names)), "a name is owned by two modules"


def test_no_placeholder_leaks_into_a_public_surface():
    for module in PUBLIC_SURFACE:
        assert PUBLIC_SURFACE[module].isdisjoint(NON_PUBLIC_INTERNALS), (
            f"episky.{module} publicly exposes an internal placeholder"
        )


def test_schema_and_systemmodel_never_import_the_pipeline():
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        source_pkg = path.parts[-2]
        if source_pkg not in ("schema", "systemmodel"):
            continue
        for _level, module in _module_imports(
            ast.parse(path.read_text(encoding="utf-8"))
        ):
            assert "collectors" not in module and "factlayer" not in module, (
                f"{path.relative_to(PACKAGE_ROOT)} imports {module}; Layer 0 "
                "and Layer 1 never import Layer 2"
            )


def test_only_normalization_constructs_a_fact():
    # F1 / DN-2: normalize is the only construction path to a Fact.
    for path in _pipeline_modules():
        source = path[1].read_text(encoding="utf-8")
        if path[1].name == "normalize.py":
            continue
        for node in ast.walk(ast.parse(source)):
            if isinstance(node, ast.Call):
                func = node.func
                name = getattr(func, "id", None)
                if name == "Fact" or getattr(func, "attr", None) == "Fact":
                    pytest.fail(
                        f"{path[1].name} constructs a Fact; only normalize may (F1)"
                    )


def test_pipeline_dataclasses_are_frozen_and_slotted():
    for module in PUBLIC_SURFACE:
        mod = importlib.import_module(f"episky.{module}")
        for name in PUBLIC_SURFACE[module]:
            value = getattr(mod, name)
            if not isinstance(value, type) or not hasattr(
                value, "__dataclass_params__"
            ):
                continue
            params = value.__dataclass_params__
            assert params.frozen and params.slots, (
                f"episky.{module}.{name} is a dataclass that is not frozen "
                "and slot-based (F8)"
            )
