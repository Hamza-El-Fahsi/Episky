"""Layer-3 conformance of the `secrets` package (blueprint §4.1/§4.2, §5,
§10; design review §2.3/§2.4, §4).

Mirrors test_trust_conformance.py / test_factlayer_conformance.py for the
secrets layer (design review §7): every `secrets` module imports only the
standard library and the packages blueprint §4.1 allows for Layer 3 —
`schema` and `trust` — never the forbidden higher-layer or authority-
bearing packages (design review §2.4), never I/O-, concurrency-, or
persistence-capable stdlib modules, carries no forbidden runtime logic
and performs no I/O at import time (RFC-0009 §3 rule 5: the LLM never
classifies), and exposes exactly the public surface its owning RFC
assigns (blueprint §10; design review §4), with the public data
structures frozen and slot-based (DN-34, Q6). The `schema` edge stays
latent (DN-44, the DN-37 precedent); only `redact.py` consumes `trust`
(DN-42). The facade re-exports nothing: no owned name and no internal
placeholder leaks at package level (design review §4), and the records
are structurally value-free — `consume` is the single materialization
point (SC1, SC4), never a field of a metadata record.
"""

import ast
import importlib
import pathlib
import sys

import pytest

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parents[1] / "src" / "episky"
SECRETS_ROOT = PACKAGE_ROOT / "secrets"
STDLIB = set(sys.stdlib_module_names) | {"__future__"}

# Blueprint §4.1: Layer 3 allows secrets to import schema and trust.
ALLOWED_PACKAGES = {"schema", "trust"}

# Design review §2.4 / blueprint §4.2: everything not in ALLOWED —
# higher layers, authority-bearing and orchestration packages, and the
# future consumers of the no-secrets boundary.
FORBIDDEN_PACKAGES = frozenset(
    {
        "collectors",
        "factlayer",
        "verification",
        "runtime",
        "core",
        "providers",
        "executor",
        "policy",
        "audit",
        "context",
        "skills",
        "systemmodel",
        "cli",
    }
)

# Stdlib modules that can perform filesystem/network I/O, concurrency, or
# persistence; secrets is a pure, in-memory, deterministic layer that must
# never hold a value durably (RFC-0009 §23; DN-41; SC11).
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

# The only functions secrets modules may call while building module-level
# constant data: `SecretShape` for the catalogue entries and `re.compile`
# for the mechanical catalogue regexes (classify.py); redact.py and
# store.py build no module-level data beyond literals.
ALLOWED_TOPLEVEL_CALLS = frozenset({"SecretShape", "compile"})

# Design review §4 / blueprint §10 ownership, transcribed: each module's
# public surface is exactly the names its owning RFC assigns.
PUBLIC_SURFACE = {
    "classify": {
        "NonSecretDesignation",
        "SECRET_SHAPES",
        "SecretClassification",
        "SecretDatum",
        "SecretMetadata",
        "SecretOrigin",
        "SecretShape",
        "SecrecyClass",
        "classify",
    },
    "redact": {"REDACTION_MARKER", "Redaction", "RedactionStatus", "redact"},
    "store": {
        "Consumer",
        "Consumption",
        "Destruction",
        "OPERATOR_OWNER",
        "Provision",
        "SECURE_STORE_CUSTODIAN",
        "SecretRecord",
        "SecureStore",
        "StoreStatus",
    },
}

# Module-level names each module legitimately assigns beyond `__all__`:
# the owned constant data tables.
DATA_TABLES = {
    "classify": {"SECRET_SHAPES"},
    "redact": {"REDACTION_MARKER"},
    "store": {"OPERATOR_OWNER", "SECURE_STORE_CUSTODIAN"},
}

OWNED_NAMES = {name for surface in PUBLIC_SURFACE.values() for name in surface}


def _secrets_modules():
    return sorted(SECRETS_ROOT.glob("*.py"))


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


@pytest.mark.parametrize("path", _secrets_modules(), ids=lambda p: p.name)
def test_secrets_module_imports_only_stdlib_and_allowed_packages(path):
    for level, module in _module_imports(path):
        assert level <= 1, f"{path.name}: relative import escapes secrets"
        if level == 1:
            continue
        parts = module.split(".")
        if parts[0] == "episky":
            assert len(parts) > 1 and (
                parts[1] == "secrets" or parts[1] in ALLOWED_PACKAGES
            ), (
                f"{path.name} imports episky.{'.'.join(parts[1:])}, but secrets "
                f"allows only {sorted(ALLOWED_PACKAGES)} and its own package"
            )
        else:
            assert parts[0] in STDLIB, (
                f"{path.name} imports {module}, which is not stdlib"
            )


@pytest.mark.parametrize("path", _secrets_modules(), ids=lambda p: p.name)
def test_secrets_module_never_imports_a_forbidden_package(path):
    for _level, module in _module_imports(path):
        parts = module.split(".")
        if parts[0] == "episky" and len(parts) > 1:
            assert parts[1] not in FORBIDDEN_PACKAGES, (
                f"{path.name} imports episky.{parts[1]}, a forbidden "
                "higher-layer or authority-bearing package"
            )


@pytest.mark.parametrize("path", _secrets_modules(), ids=lambda p: p.name)
def test_secrets_module_never_imports_the_declared_schema_edge(path):
    for _level, module in _module_imports(path):
        parts = module.split(".")
        if parts[0] == "episky" and len(parts) > 1:
            assert parts[1] != "schema", (
                f"{path.name} imports episky.schema; the edge stays latent (DN-44)"
            )


@pytest.mark.parametrize("path", _secrets_modules(), ids=lambda p: p.name)
def test_secrets_module_imports_no_io_or_persistence_stdlib(path):
    for _level, module in _module_imports(path):
        parts = module.split(".")
        if parts[0] != "episky":
            assert parts[0] not in FORBIDDEN_STDLIB, (
                f"{path.name} imports {module}, an I/O/concurrency/"
                "persistence-capable stdlib module"
            )


@pytest.mark.parametrize("path", _secrets_modules(), ids=lambda p: p.name)
def test_secrets_module_calls_no_forbidden_io_builtin(path):
    calls = set(_call_names(path))
    assert calls.isdisjoint(FORBIDDEN_CALLS), (
        f"{path.name} calls {sorted(calls & FORBIDDEN_CALLS)}; secrets performs "
        "no filesystem, network, console, or execution side effects"
    )


@pytest.mark.parametrize("path", _secrets_modules(), ids=lambda p: p.name)
def test_secrets_module_has_no_top_level_runtime_logic(path):
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
                    "not an owned constant-data table"
                )


@pytest.mark.parametrize("path", _secrets_modules(), ids=lambda p: p.name)
def test_secrets_module_builds_only_constant_data_at_module_level(path):
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
def test_secrets_public_surface_is_exactly_the_owned_vocabulary(module):
    mod = importlib.import_module(f"episky.secrets.{module}")
    assert set(mod.__all__) == PUBLIC_SURFACE[module]


@pytest.mark.parametrize("module", sorted(PUBLIC_SURFACE))
def test_secrets_public_names_are_defined_by_their_owning_module(module):
    mod = importlib.import_module(f"episky.secrets.{module}")
    for name in PUBLIC_SURFACE[module]:
        value = getattr(mod, name)
        owner = getattr(value, "__module__", None)
        if owner is None:
            assert name in mod.__dict__, f"{name} is not defined in secrets"
        else:
            assert owner == f"episky.secrets.{module}", (
                f"{name} is defined in {owner}, not its owning module"
            )


def test_secrets_public_surface_has_no_ownership_overlap():
    assert len(OWNED_NAMES) == len(
        {name for surface in PUBLIC_SURFACE.values() for name in surface}
    ), "a name is owned by two modules"


@pytest.mark.parametrize("module", sorted(PUBLIC_SURFACE))
def test_secrets_public_surface_leaks_no_internal_placeholder(module):
    mod = importlib.import_module(f"episky.secrets.{module}")
    for name in set(mod.__all__):
        assert not name.startswith("_"), (
            f"episky.secrets.{module} exports the private placeholder {name}"
        )


def test_secrets_dataclasses_are_frozen_and_slotted():
    for module in PUBLIC_SURFACE:
        mod = importlib.import_module(f"episky.secrets.{module}")
        for name in PUBLIC_SURFACE[module]:
            value = getattr(mod, name)
            if not isinstance(value, type) or not hasattr(
                value, "__dataclass_params__"
            ):
                continue
            params = value.__dataclass_params__
            assert params.frozen and params.slots, (
                f"episky.secrets.{module}.{name} is a dataclass that is not "
                "frozen and slot-based (DN-34)"
            )


def test_secrets_package_has_exactly_the_blueprint_modules():
    modules = {path.stem for path in SECRETS_ROOT.glob("*.py")}
    assert modules == {"__init__", "classify", "redact", "store"}


def test_secrets_facade_reexports_nothing_and_leaks_nothing():
    mod = importlib.import_module("episky.secrets")
    public = {name for name in dir(mod) if not name.startswith("_")}
    assert public <= {"classify", "redact", "store"}, (
        "the facade exposes a public name beyond its submodules"
    )
    private = {
        name for name in dir(mod) if name.startswith("_") and not name.startswith("__")
    }
    assert private == set(), "the facade must leak no internal placeholders"


def test_schema_and_trust_never_import_secrets():
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        source_pkg = path.parts[-2]
        if source_pkg not in ("schema", "trust"):
            continue
        for _level, module in _module_imports(path):
            assert "secrets" not in module, (
                f"{path.relative_to(PACKAGE_ROOT)} imports {module}; Layers 0–1 "
                "never import Layer 3"
            )


def test_secrets_value_free_records_carry_no_value_field():
    for module in PUBLIC_SURFACE:
        mod = importlib.import_module(f"episky.secrets.{module}")
        for name in PUBLIC_SURFACE[module]:
            value = getattr(mod, name)
            if not isinstance(value, type) or not hasattr(
                value, "__dataclass_fields__"
            ):
                continue
            fields = set(value.__dataclass_fields__)
            if name in ("Consumption", "SecretDatum"):
                continue
            assert not {"content", "value"} & fields, (
                f"episky.secrets.{module}.{name} carries a value-bearing field; "
                "records are metadata only (RFC-0009 §15; SC1, SC4)"
            )


def test_secrets_consume_is_the_single_materialization_point():
    from episky.secrets.store import Consumption

    fields = set(Consumption.__dataclass_fields__)
    assert "value" in fields, "consume must materialize the value (SC1)"
    assert "content" not in fields
