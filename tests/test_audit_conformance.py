"""Layer-4 conformance of the `audit` package (blueprint §4.1/§4.2, §5, §10;
design review §3, §4, §5, §8; DN-1, DN-62, DN-63).

Mirrors test_policy_conformance.py / test_secrets_conformance.py for the
audit layer (Iteration 8 Commit C1): every audit module imports only the
standard library, the `secrets` *metadata* types (blueprint §4.2 qualifier;
SC4), and its own package — never the forbidden authority-bearing or
orchestration packages (RFC-0004 §4.12; AU1), and never the declared-but-
latent `schema` edge (the DN-44 precedent) — never I/O-, concurrency-,
persistence-, randomness-, or crypto-capable stdlib modules, carries no
forbidden runtime logic and performs no I/O at import time, exposes exactly
the public surface its owning RFC assigns (blueprint §10; design review
§4), with the public data structures frozen and slot-based (DN-34).
The facade re-exports nothing. Layer 0 never imports audit, and no record
carries a value-shaped field (SC4/AU7). The store reads no clock and
generates no identifier: time is an argument and identifiers are
caller-supplied (DN-62).
"""

import ast
import importlib
import pathlib
import sys

import pytest

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parents[1] / "src" / "episky"
AUDIT_ROOT = PACKAGE_ROOT / "audit"
STDLIB = set(sys.stdlib_module_names) | {"__future__"}

# Blueprint §4.1 / design review §5: the audit layer may import `secrets`
# (metadata types only) and `schema`. C1 consumes only `secrets` metadata
# types; the `schema` edge stays latent (DN-44 precedent).
ALLOWED_PACKAGES = {"schema", "secrets"}

# Everything else is forbidden: higher layers, authority-bearing and
# orchestration packages, and the packages that must never see the record.
FORBIDDEN_PACKAGES = frozenset(
    {
        "collectors",
        "trust",
        "factlayer",
        "verification",
        "systemmodel",
        "policy",
        "executor",
        "context",
        "providers",
        "skills",
        "core",
        "cli",
    }
)

# Stdlib modules that can perform filesystem/network I/O, concurrency,
# persistence, randomness, or cryptography; audit is a pure, in-memory,
# deterministic layer (DN-1) whose tamper-evidence chain is a deterministic
# structural encoding, never a cryptographic digest (the policy/secrets
# precedent; DN-62).
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
# time. Imports, function/class definitions, docstrings, and the owned
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

# C1 builds no module-level constant data beyond `__all__`: no module-level
# calls at all.
ALLOWED_TOPLEVEL_CALLS = frozenset()

# Design review §4 / blueprint §10 ownership, transcribed: each C1 module's
# public surface is exactly the names its owning RFC assigns. transcript.py
# is a C2 stub and exposes no surface yet.
PUBLIC_SURFACE = {
    "records": {
        "ApprovalDecision",
        "ApprovalRecord",
        "AuditRecord",
        "ExecutionPhase",
        "ExecutionRecord",
        "OverrideRecord",
        "RecordCategory",
        "SecretEvent",
        "SecretMetadataRecord",
    },
    "store": {"AuditStore", "StoreStatus"},
}

# Module-level names each module legitimately assigns beyond `__all__`: none.
DATA_TABLES = {"records": set(), "store": set(), "transcript": set()}

OWNED_NAMES = {name for surface in PUBLIC_SURFACE.values() for name in surface}


def _audit_modules():
    return sorted(AUDIT_ROOT.glob("*.py"))


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


@pytest.mark.parametrize("path", _audit_modules(), ids=lambda p: p.name)
def test_audit_module_imports_only_stdlib_and_allowed_packages(path):
    for level, module in _module_imports(path):
        assert level <= 1, f"{path.name}: relative import escapes audit"
        if level == 1:
            continue
        parts = module.split(".")
        if parts[0] == "episky":
            assert len(parts) > 1 and (
                parts[1] == "audit" or parts[1] in ALLOWED_PACKAGES
            ), (
                f"{path.name} imports episky.{'.'.join(parts[1:])}, but audit "
                f"allows only {sorted(ALLOWED_PACKAGES)} and its own package"
            )
        else:
            assert parts[0] in STDLIB, (
                f"{path.name} imports {module}, which is not stdlib"
            )


@pytest.mark.parametrize("path", _audit_modules(), ids=lambda p: p.name)
def test_audit_module_never_imports_a_forbidden_package(path):
    for _level, module in _module_imports(path):
        parts = module.split(".")
        if parts[0] == "episky" and len(parts) > 1:
            assert parts[1] not in FORBIDDEN_PACKAGES, (
                f"{path.name} imports episky.{parts[1]}, a forbidden "
                "higher-layer or authority-bearing package"
            )


@pytest.mark.parametrize("path", _audit_modules(), ids=lambda p: p.name)
def test_audit_module_keeps_the_schema_edge_latent(path):
    for _level, module in _module_imports(path):
        parts = module.split(".")
        if parts[0] == "episky" and len(parts) > 1:
            assert parts[1] != "schema", (
                f"{path.name} imports episky.schema; the edge stays latent "
                "(the DN-44 precedent)"
            )


@pytest.mark.parametrize("path", _audit_modules(), ids=lambda p: p.name)
def test_audit_module_imports_no_io_persistence_random_or_crypto_stdlib(path):
    for _level, module in _module_imports(path):
        parts = module.split(".")
        if parts[0] != "episky":
            assert parts[0] not in FORBIDDEN_STDLIB, (
                f"{path.name} imports {module}, an I/O/concurrency/"
                "persistence/randomness/crypto-capable stdlib module"
            )


@pytest.mark.parametrize("path", _audit_modules(), ids=lambda p: p.name)
def test_audit_module_calls_no_forbidden_io_builtin(path):
    calls = set(_call_names(path))
    assert calls.isdisjoint(FORBIDDEN_CALLS), (
        f"{path.name} calls {sorted(calls & FORBIDDEN_CALLS)}; audit performs "
        "no filesystem, network, console, or execution side effects"
    )


@pytest.mark.parametrize("path", _audit_modules(), ids=lambda p: p.name)
def test_audit_module_has_no_top_level_runtime_logic(path):
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
                    "not the owned __all__"
                )


@pytest.mark.parametrize("path", _audit_modules(), ids=lambda p: p.name)
def test_audit_module_builds_only_constant_data_at_module_level(path):
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
def test_audit_public_surface_is_exactly_the_owned_vocabulary(module):
    mod = importlib.import_module(f"episky.audit.{module}")
    assert set(mod.__all__) == PUBLIC_SURFACE[module]


@pytest.mark.parametrize("module", sorted(PUBLIC_SURFACE))
def test_audit_public_names_are_defined_by_their_owning_module(module):
    mod = importlib.import_module(f"episky.audit.{module}")
    for name in PUBLIC_SURFACE[module]:
        value = getattr(mod, name)
        owner = getattr(value, "__module__", None)
        if owner is None:
            assert name in mod.__dict__, f"{name} is not defined in audit"
        else:
            assert owner == f"episky.audit.{module}", (
                f"{name} is defined in {owner}, not its owning module"
            )


def test_audit_public_surface_has_no_ownership_overlap():
    assert len(OWNED_NAMES) == len(
        {name for surface in PUBLIC_SURFACE.values() for name in surface}
    ), "a name is owned by two modules"


@pytest.mark.parametrize("module", sorted(PUBLIC_SURFACE))
def test_audit_public_surface_leaks_no_internal_placeholder(module):
    mod = importlib.import_module(f"episky.audit.{module}")
    for name in set(mod.__all__):
        assert not name.startswith("_"), (
            f"episky.audit.{module} exports the private placeholder {name}"
        )


def test_audit_dataclasses_are_frozen_and_slotted():
    for module in PUBLIC_SURFACE:
        mod = importlib.import_module(f"episky.audit.{module}")
        for name in PUBLIC_SURFACE[module]:
            value = getattr(mod, name)
            if not isinstance(value, type) or not hasattr(
                value, "__dataclass_params__"
            ):
                continue
            params = value.__dataclass_params__
            assert params.frozen and params.slots, (
                f"episky.audit.{module}.{name} is a dataclass that is not "
                "frozen and slot-based (DN-34)"
            )


def test_audit_package_has_exactly_the_blueprint_modules():
    modules = {path.stem for path in AUDIT_ROOT.glob("*.py")}
    assert modules == {"__init__", "records", "store", "transcript"}


def test_audit_facade_reexports_nothing_and_leaks_nothing():
    mod = importlib.import_module("episky.audit")
    public = {name for name in dir(mod) if not name.startswith("_")}
    assert public <= {"records", "store", "transcript"}, (
        "the facade exposes a public name beyond its submodules"
    )
    private = {
        name for name in dir(mod) if name.startswith("_") and not name.startswith("__")
    }
    assert private == set(), "the facade must leak no internal placeholders"


def test_layers_below_four_never_import_audit():
    lower = {
        "schema",
        "trust",
        "systemmodel",
        "collectors",
        "factlayer",
        "verification",
    }
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        source_pkg = path.parts[-2]
        if source_pkg not in lower:
            continue
        for _level, module in _module_imports(path):
            assert "audit" not in module, (
                f"{path.relative_to(PACKAGE_ROOT)} imports {module}; Layers 0–3 "
                "never import the audit"
            )


def test_audit_records_carry_no_value_shaped_field():
    from episky.audit.records import (
        ApprovalRecord,
        ExecutionRecord,
        OverrideRecord,
        SecretMetadataRecord,
    )

    value_shaped = {"content", "value", "secret", "raw", "material", "payload"}
    for cls in (ExecutionRecord, SecretMetadataRecord, ApprovalRecord, OverrideRecord):
        fields = set(cls.__dataclass_fields__)
        assert not (value_shaped & fields), (
            f"episky.audit.records.{cls.__name__} carries a value-shaped field; "
            "records are metadata only (RFC-0013 §10, §31; SC4, AU7)"
        )


def test_audit_records_import_only_secrets_metadata_types():
    for _level, module in _module_imports(AUDIT_ROOT / "records.py"):
        if module.startswith("episky"):
            assert module in (
                "episky.audit",
                "episky.secrets.classify",
            ), f"records.py imports {module}, a non-metadata-type edge"


@pytest.mark.parametrize("path", _audit_modules(), ids=lambda p: p.name)
def test_audit_module_reads_no_clock(path):
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


@pytest.mark.parametrize("path", _audit_modules(), ids=lambda p: p.name)
def test_audit_module_generates_no_random_or_crypto(path):
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
