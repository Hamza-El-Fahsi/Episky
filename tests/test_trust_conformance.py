"""Layer-1 conformance of the `trust` package (blueprint §4.1/§4.2, §5, §10).

Mirrors test_verification_conformance.py for the trust package (design
review §3, §8, §12): every `trust` module imports only the standard
library and the packages blueprint §4.1 allows for Layer 1 — `schema`
and nothing else (DN-37: the `schema` edge is declared but remains
latent; no trust module may consume it this iteration) — never the
forbidden authority-bearing or orchestration packages (design review
§3.2), never I/O-, concurrency-, or persistence-capable stdlib modules,
carries no forbidden runtime logic and performs no I/O at import time,
and exposes exactly the public surface its owning RFC assigns (blueprint
§10; design review §4), with the public data structures frozen and
slot-based (DN-34, Q6). The facade re-exports nothing: no owned name and
no internal placeholder leaks at package level (design review §4).
"""

import ast
import importlib
import pathlib
import sys

import pytest

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parents[1] / "src" / "episky"
TRUST_ROOT = PACKAGE_ROOT / "trust"
STDLIB = set(sys.stdlib_module_names) | {"__future__"}

# Blueprint §4.1: Layer 1 allows trust to import schema (plus itself).
ALLOWED_PACKAGES = {"schema"}

# Blueprint §4.2 / design review §3.2: trust never imports these
# authority-bearing, orchestration, or higher-layer packages.
FORBIDDEN_PACKAGES = frozenset(
    {
        "collectors",
        "factlayer",
        "verification",
        "secrets",
        "policy",
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
# persistence; trust is a pure, in-memory, deterministic layer (DN-1).
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
# constant data, and the owned `__all__` assignment are the only
# permitted top-level statements.
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

# The only functions trust modules may call while building module-level
# constant data: `MappingProxyType` and `frozenset` for the vocabulary
# tables, `re.compile` for the static neutralization patterns, and the
# pure `chr`/`ord`/`range` helpers the table comprehensions use.
ALLOWED_TOPLEVEL_CALLS = frozenset(
    {"MappingProxyType", "frozenset", "compile", "chr", "ord", "range"}
)

# Design review §4 / blueprint §10 ownership, transcribed: each module's
# public surface is exactly the names its owning RFC assigns.
PUBLIC_SURFACE = {
    "classes": {
        "CATEGORY_DEFAULTS",
        "CATEGORY_ORIGINS",
        "Classification",
        "Datum",
        "Demotion",
        "PROVENANCE_LOSS_DEMOTION",
        "ProvenanceState",
        "TRUST_DOMAIN_POSTURES",
        "TrustCategory",
        "TrustClass",
        "TrustDomain",
        "classify",
        "downgrade",
        "join",
        "meet",
    },
    "sanitize": {
        "DEFAULT_LIMIT",
        "Sanitization",
        "SanitizationStatus",
        "bound",
        "neutralize_control",
        "quote",
        "sanitize",
        "strip_ansi",
        "tame_unicode",
    },
    "hostile": {"DisclosureState", "Quarantine", "contaminate", "quarantine"},
}

OWNED_NAMES = {name for surface in PUBLIC_SURFACE.values() for name in surface}


def _trust_modules():
    return sorted(TRUST_ROOT.glob("*.py"))


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


@pytest.mark.parametrize("path", _trust_modules(), ids=lambda p: p.name)
def test_trust_module_imports_only_stdlib_and_allowed_packages(path):
    for level, module in _module_imports(path):
        assert level <= 1, f"{path.name}: relative import escapes trust"
        if level == 1:
            continue
        parts = module.split(".")
        if parts[0] == "episky":
            assert len(parts) > 1 and (
                parts[1] == "trust" or parts[1] in ALLOWED_PACKAGES
            ), (
                f"{path.name} imports episky.{'.'.join(parts[1:])}, but trust "
                f"allows only {sorted(ALLOWED_PACKAGES)} and its own package"
            )
        else:
            assert parts[0] in STDLIB, (
                f"{path.name} imports {module}, which is not stdlib"
            )


@pytest.mark.parametrize("path", _trust_modules(), ids=lambda p: p.name)
def test_trust_module_never_imports_a_forbidden_package(path):
    for _level, module in _module_imports(path):
        parts = module.split(".")
        if parts[0] == "episky" and len(parts) > 1:
            assert parts[1] not in FORBIDDEN_PACKAGES, (
                f"{path.name} imports episky.{parts[1]}, a forbidden "
                "authority-bearing or higher-layer package"
            )


@pytest.mark.parametrize("path", _trust_modules(), ids=lambda p: p.name)
def test_trust_module_never_imports_the_declared_schema_edge(path):
    for _level, module in _module_imports(path):
        parts = module.split(".")
        if parts[0] == "episky" and len(parts) > 1:
            assert parts[1] != "schema", (
                f"{path.name} imports episky.schema; the edge stays latent (DN-37)"
            )


@pytest.mark.parametrize("path", _trust_modules(), ids=lambda p: p.name)
def test_trust_module_imports_no_io_or_persistence_stdlib(path):
    for _level, module in _module_imports(path):
        parts = module.split(".")
        if parts[0] != "episky":
            assert parts[0] not in FORBIDDEN_STDLIB, (
                f"{path.name} imports {module}, an I/O/concurrency/"
                "persistence-capable stdlib module"
            )


@pytest.mark.parametrize("path", _trust_modules(), ids=lambda p: p.name)
def test_trust_module_calls_no_forbidden_io_builtin(path):
    calls = set(_call_names(path))
    assert calls.isdisjoint(FORBIDDEN_CALLS), (
        f"{path.name} calls {sorted(calls & FORBIDDEN_CALLS)}; trust performs "
        "no filesystem, network, console, or execution side effects"
    )


@pytest.mark.parametrize("path", _trust_modules(), ids=lambda p: p.name)
def test_trust_module_has_no_top_level_runtime_logic(path):
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


@pytest.mark.parametrize("path", _trust_modules(), ids=lambda p: p.name)
def test_trust_module_builds_only_constant_data_at_module_level(path):
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
def test_trust_public_surface_is_exactly_the_owned_vocabulary(module):
    mod = importlib.import_module(f"episky.trust.{module}")
    assert set(mod.__all__) == PUBLIC_SURFACE[module]


@pytest.mark.parametrize("module", sorted(PUBLIC_SURFACE))
def test_trust_public_names_are_defined_by_their_owning_module(module):
    mod = importlib.import_module(f"episky.trust.{module}")
    for name in PUBLIC_SURFACE[module]:
        value = getattr(mod, name)
        owner = getattr(value, "__module__", None)
        if owner is None:
            assert name in mod.__dict__, f"{name} is not defined in trust"
        else:
            assert owner == f"episky.trust.{module}", (
                f"{name} is defined in {owner}, not its owning module"
            )


def test_trust_public_surface_has_no_ownership_overlap():
    assert len(OWNED_NAMES) == len(
        {name for surface in PUBLIC_SURFACE.values() for name in surface}
    ), "a name is owned by two modules"


@pytest.mark.parametrize("module", sorted(PUBLIC_SURFACE))
def test_trust_public_surface_leaks_no_internal_placeholder(module):
    mod = importlib.import_module(f"episky.trust.{module}")
    for name in set(mod.__all__):
        assert not name.startswith("_"), (
            f"episky.trust.{module} exports the private placeholder {name}"
        )


def test_trust_dataclasses_are_frozen_and_slotted():
    for module in PUBLIC_SURFACE:
        mod = importlib.import_module(f"episky.trust.{module}")
        for name in PUBLIC_SURFACE[module]:
            value = getattr(mod, name)
            if not isinstance(value, type) or not hasattr(
                value, "__dataclass_params__"
            ):
                continue
            params = value.__dataclass_params__
            assert params.frozen and params.slots, (
                f"episky.trust.{module}.{name} is a dataclass that is not "
                "frozen and slot-based (DN-34)"
            )


def test_trust_package_has_exactly_the_blueprint_modules():
    modules = {path.stem for path in TRUST_ROOT.glob("*.py")}
    assert modules == {"__init__", "classes", "sanitize", "hostile"}


def test_trust_facade_reexports_nothing_and_leaks_nothing():
    mod = importlib.import_module("episky.trust")
    public = {name for name in dir(mod) if not name.startswith("_")}
    assert public <= {"classes", "sanitize", "hostile"}, (
        "the facade exposes a public name beyond its submodules"
    )
    private = {
        name for name in dir(mod) if name.startswith("_") and not name.startswith("__")
    }
    assert private == set(), "the facade must leak no internal placeholders"


def test_schema_never_imports_trust():
    schema_root = PACKAGE_ROOT / "schema"
    for path in sorted(schema_root.rglob("*.py")):
        for _level, module in _module_imports(path):
            assert "trust" not in module, (
                f"schema imports {module}; Layer 0 never imports the trust layer"
            )
