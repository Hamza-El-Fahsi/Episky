"""Layer-4 conformance of the `context` package (blueprint §4.1/§4.2, §5, §10;
design review §3, §4, §5, §8; DN-65…DN-74).

Mirrors test_audit_conformance.py / test_policy_conformance.py for the
context layer (Iteration 9 Commits C1–C4): every context module imports
only the standard library, the packages blueprint §4.1 allows for Layer 4
(`schema`, `factlayer`, `trust`, `secrets` classifier types, `systemmodel`)
and its own package — never the forbidden authority-bearing or
orchestration packages (`providers`, `policy`, `executor`, `audit`), and
never the declared-but-latent `systemmodel` edge (the DN-44 precedent) —
never I/O-, concurrency-, persistence-, randomness-, or crypto-capable
stdlib modules, carries no forbidden runtime logic and performs no I/O at
import time, and exposes exactly the public surface its owning RFC assigns
(blueprint §10; design review §4), with the public data structures frozen
and slot-based (DN-34). The facade re-exports nothing. Layers below 4
never import context (blueprint §4.1: only `providers`, `cli`, `core` may).
"""

import ast
import importlib
import pathlib
import sys

import pytest

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parents[1] / "src" / "episky"
CONTEXT_ROOT = PACKAGE_ROOT / "context"
STDLIB = set(sys.stdlib_module_names) | {"__future__"}

# Blueprint §4.1: the context layer may import schema, factlayer, trust,
# secrets (classifier types only per §4.2), and systemmodel, plus itself.
ALLOWED_PACKAGES = {"schema", "factlayer", "trust", "secrets", "systemmodel"}

# Design review §5: context never imports these authority-bearing or
# orchestration packages, nor the latent systemmodel edge (DN-44).
FORBIDDEN_PACKAGES = frozenset(
    {
        "collectors",
        "verification",
        "policy",
        "executor",
        "audit",
        "providers",
        "skills",
        "core",
        "cli",
    }
)

# Stdlib modules that can perform filesystem/network I/O, concurrency,
# persistence, randomness, or cryptography; context is a pure, in-memory,
# deterministic layer (DN-1).
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
        "random",
        "uuid",
        "hashlib",
        "hmac",
        "secrets",
        "base64",
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

# The only functions context modules may call while building module-level
# constant data: `frozenset` for the freshness closure in assemble.
ALLOWED_TOPLEVEL_CALLS = frozenset({"frozenset"})

# Design review §4 / blueprint §10 ownership, transcribed from the C1–C4
# ratification: each module's public surface is exactly the names its
# owning RFC assigns.
PUBLIC_SURFACE = {
    "assemble": {
        "Assembly",
        "BoundaryEvent",
        "BoundaryEventKind",
        "Context",
        "ContextCategory",
        "ContextState",
        "DEFAULT_EVIDENCE_BOUND",
        "DEFAULT_FACT_BOUND",
        "DEFAULT_HISTORY_BOUND",
        "DEFAULT_SKILL_BOUND",
        "Disclosure",
        "EvidenceLabel",
        "GoalValue",
        "HistoryLabel",
        "REASON_OVERFLOW",
        "REASON_STALE_EXCLUDED",
        "REASON_UNPURPOSEFUL",
        "RoutingMarker",
        "SkillMaterialItem",
        "Supersession",
        "TurnRecord",
        "assemble",
        "mark_stale",
        "supersede_question",
    },
    "boundaries": {
        "BoundaryDecision",
        "BoundaryDisposition",
        "BoundaryInput",
        "BoundaryRefusal",
        "BoundaryReport",
        "DEFAULT_BOUNDARY_LIMIT",
        "admit",
        "admit_all",
    },
    "memory": {
        "Memory",
        "MemoryCategory",
        "MemoryEntry",
        "MemoryEvent",
        "MemoryOutcome",
        "MemoryRefusal",
        "empty",
        "export",
        "list_entries",
        "promote",
        "remove",
        "wipe",
    },
    "provider_view": {
        "ProviderView",
        "ProviderViewOutcome",
        "ViewDisposition",
        "ViewRefusal",
        "derive",
    },
}

OWNED_NAMES = {name for surface in PUBLIC_SURFACE.values() for name in surface}

# Module-level constant data each module legitimately assigns beyond
# `__all__`: the provisional bounds and disclosure reasons (assemble) and
# the boundary limit (boundaries).
DATA_TABLES = {
    "assemble": {
        "DEFAULT_EVIDENCE_BOUND",
        "DEFAULT_FACT_BOUND",
        "DEFAULT_HISTORY_BOUND",
        "DEFAULT_SKILL_BOUND",
        "REASON_OVERFLOW",
        "REASON_STALE_EXCLUDED",
        "REASON_UNPURPOSEFUL",
        "_ADMISSIBLE_FRESHNESS",
    },
    "boundaries": {"DEFAULT_BOUNDARY_LIMIT"},
    "memory": set(),
    "provider_view": set(),
}

# The exact intra-episky imports each module is ratified to carry.
EXPECTED_IMPORTS = {
    "assemble": {
        "episky.factlayer.store",
        "episky.schema.fact",
        "episky.schema.outcome",
    },
    "boundaries": {
        "episky.secrets.classify",
        "episky.trust.classes",
        "episky.trust.hostile",
        "episky.trust.sanitize",
    },
    "memory": {"episky.context.assemble"},
    "provider_view": {"episky.context.assemble", "episky.schema.fact"},
}


def _context_modules():
    return sorted(
        path for path in CONTEXT_ROOT.glob("*.py") if not path.name.startswith("__")
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


@pytest.mark.parametrize("path", _context_modules(), ids=lambda p: p.name)
def test_context_module_imports_only_stdlib_and_allowed_packages(path):
    for level, module in _module_imports(path):
        assert level <= 1, f"{path.name}: relative import escapes context"
        if level == 1:
            continue
        parts = module.split(".")
        if parts[0] == "episky":
            assert len(parts) > 1 and (
                parts[1] == "context" or parts[1] in ALLOWED_PACKAGES
            ), (
                f"{path.name} imports episky.{'.'.join(parts[1:])}, but context "
                f"allows only {sorted(ALLOWED_PACKAGES)} and its own package"
            )
        else:
            assert parts[0] in STDLIB, (
                f"{path.name} imports {module}, which is not stdlib"
            )


@pytest.mark.parametrize("path", _context_modules(), ids=lambda p: p.name)
def test_context_module_imports_exactly_its_ratified_set(path):
    episky_imports = {
        module
        for _level, module in _module_imports(path)
        if module.startswith("episky")
    }
    assert episky_imports == EXPECTED_IMPORTS[path.stem], (
        f"{path.name} imports {sorted(episky_imports)}; expected exactly "
        f"{sorted(EXPECTED_IMPORTS[path.stem])}"
    )


@pytest.mark.parametrize("path", _context_modules(), ids=lambda p: p.name)
def test_context_module_never_imports_a_forbidden_package(path):
    for _level, module in _module_imports(path):
        parts = module.split(".")
        if parts[0] == "episky" and len(parts) > 1:
            assert parts[1] not in FORBIDDEN_PACKAGES, (
                f"{path.name} imports episky.{parts[1]}, a forbidden "
                "authority-bearing or orchestration package"
            )


@pytest.mark.parametrize("path", _context_modules(), ids=lambda p: p.name)
def test_context_module_keeps_the_systemmodel_edge_latent(path):
    for _level, module in _module_imports(path):
        parts = module.split(".")
        if parts[0] == "episky" and len(parts) > 1:
            assert parts[1] != "systemmodel", (
                f"{path.name} imports episky.systemmodel; the edge stays latent "
                "(the DN-44 precedent)"
            )


@pytest.mark.parametrize("path", _context_modules(), ids=lambda p: p.name)
def test_context_module_imports_secrets_classifier_types_only(path):
    for _level, module in _module_imports(path):
        if module.startswith("episky.secrets"):
            assert module == "episky.secrets.classify", (
                f"{path.name} imports {module}; context consumes the secrets "
                "classifier types only (blueprint §4.2)"
            )


@pytest.mark.parametrize("path", _context_modules(), ids=lambda p: p.name)
def test_context_module_imports_no_io_persistence_random_or_crypto_stdlib(path):
    for _level, module in _module_imports(path):
        parts = module.split(".")
        if parts[0] != "episky":
            assert parts[0] not in FORBIDDEN_STDLIB, (
                f"{path.name} imports {module}, an I/O/concurrency/"
                "persistence/randomness/crypto-capable stdlib module"
            )


@pytest.mark.parametrize("path", _context_modules(), ids=lambda p: p.name)
def test_context_module_calls_no_forbidden_io_builtin(path):
    calls = set(_call_names(path))
    assert calls.isdisjoint(FORBIDDEN_CALLS), (
        f"{path.name} calls {sorted(calls & FORBIDDEN_CALLS)}; context performs "
        "no filesystem, network, console, or execution side effects"
    )


@pytest.mark.parametrize("path", _context_modules(), ids=lambda p: p.name)
def test_context_module_reads_no_clock(path):
    src = path.read_text(encoding="utf-8")
    for token in (
        "datetime.now",
        "utcnow",
        "datetime.today",
        "time.time",
        "time.monotonic",
        "perf_counter",
        "import time",
        "from time import",
    ):
        assert token not in src, f"{path.name} reads a clock"


@pytest.mark.parametrize("path", _context_modules(), ids=lambda p: p.name)
def test_context_module_generates_no_random_or_crypto(path):
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


@pytest.mark.parametrize("path", _context_modules(), ids=lambda p: p.name)
def test_context_module_has_no_top_level_runtime_logic(path):
    module = path.stem
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for stmt in tree.body:
        assert not isinstance(stmt, FORBIDDEN_TOPLEVEL), (
            f"{path.name}: top-level {type(stmt).__name__} is runtime logic "
            "at import time"
        )
        if isinstance(stmt, (ast.Assign, ast.AnnAssign)):
            targets = stmt.targets if isinstance(stmt, ast.Assign) else (stmt.target,)
            for target in targets:
                assert isinstance(target, ast.Name), (
                    f"{path.name}: module-level assignment to "
                    f"{getattr(target, 'id', type(target).__name__)}"
                )
                assert target.id == "__all__" or target.id in DATA_TABLES[module], (
                    f"{path.name}: module-level assignment to {target.id} is "
                    "not the owned __all__ or a ratified constant"
                )


@pytest.mark.parametrize("path", _context_modules(), ids=lambda p: p.name)
def test_context_module_builds_only_constant_data_at_module_level(path):
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
def test_context_public_surface_is_exactly_the_owned_vocabulary(module):
    mod = importlib.import_module(f"episky.context.{module}")
    assert set(mod.__all__) == PUBLIC_SURFACE[module]


@pytest.mark.parametrize("module", sorted(PUBLIC_SURFACE))
def test_context_public_names_are_defined_by_their_owning_module(module):
    mod = importlib.import_module(f"episky.context.{module}")
    for name in PUBLIC_SURFACE[module]:
        value = getattr(mod, name)
        owner = getattr(value, "__module__", None)
        if owner is None:
            assert name in mod.__dict__, f"{name} is not defined in context"
        else:
            assert owner == f"episky.context.{module}", (
                f"{name} is defined in {owner}, not its owning module"
            )


def test_context_public_surface_has_no_ownership_overlap():
    assert len(OWNED_NAMES) == len(
        {name for surface in PUBLIC_SURFACE.values() for name in surface}
    ), "a name is owned by two context modules"


@pytest.mark.parametrize("module", sorted(PUBLIC_SURFACE))
def test_context_public_surface_leaks_no_internal_placeholder(module):
    mod = importlib.import_module(f"episky.context.{module}")
    for name in set(mod.__all__):
        assert not name.startswith("_"), (
            f"episky.context.{module} exports the private placeholder {name}"
        )


def test_context_dataclasses_are_frozen_and_slotted():
    for module in PUBLIC_SURFACE:
        mod = importlib.import_module(f"episky.context.{module}")
        for name in PUBLIC_SURFACE[module]:
            value = getattr(mod, name)
            if not isinstance(value, type) or not hasattr(
                value, "__dataclass_params__"
            ):
                continue
            params = value.__dataclass_params__
            assert params.frozen and params.slots, (
                f"episky.context.{module}.{name} is a dataclass that is not "
                "frozen and slot-based (DN-34)"
            )


def test_context_package_has_exactly_the_blueprint_modules():
    modules = {path.stem for path in CONTEXT_ROOT.glob("*.py")}
    assert modules == {"__init__", "assemble", "boundaries", "memory", "provider_view"}


def test_context_facade_reexports_nothing_and_leaks_nothing():
    mod = importlib.import_module("episky.context")
    public = {name for name in dir(mod) if not name.startswith("_")}
    assert public <= {"assemble", "boundaries", "memory", "provider_view"}, (
        "the facade exposes a public name beyond its submodules"
    )
    private = {
        name for name in dir(mod) if name.startswith("_") and not name.startswith("__")
    }
    assert private == set(), "the facade must leak no internal placeholders"


def test_layers_below_four_never_import_context():
    importers = {"providers", "cli", "core"}
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        source_pkg = path.parts[-2]
        if source_pkg == "episky":
            continue
        if source_pkg in importers or source_pkg == "context":
            continue
        for _level, module in _module_imports(path):
            assert "context" not in module, (
                f"{path.relative_to(PACKAGE_ROOT)} imports {module}; only "
                "providers, cli, and core may import the context (blueprint §4.1)"
            )
