"""Architectural conformance of the `schema` package (blueprint §4.1, §8.2).

Enforces the Layer-0 contract: every `schema` module imports only the
standard library and intra-package modules, and carries no implementation
logic — nothing beyond type declarations (blueprint §8.2 DoD: "zero imports
beyond stdlib"; §2 `schema` row: "No behavior"). Also fixes the package
ownership boundary (blueprint §10): each module's public surface is exactly
the canonical vocabulary its owning RFC assigns, no more.
"""

import ast
import importlib
import pathlib
import sys

import pytest

SCHEMA_ROOT = pathlib.Path(__file__).resolve().parents[1] / "src" / "episky" / "schema"
STDLIB = set(sys.stdlib_module_names) | {"__future__"}

# Blueprint §10 ownership, transcribed: each module's public surface is
# exactly the canonical types its owning RFC assigns.
PUBLIC_SURFACE = {
    "fact": {
        "Collector",
        "ConfidenceSource",
        "Fact",
        "FactStatus",
        "Freshness",
        "FreshnessState",
        "Property",
        "Provenance",
        "Scope",
        "Subject",
        "Value",
    },
    "action": {"Action", "Plan", "PostCondition", "Proposal", "Step"},
    "outcome": {"VerificationOutcome"},
}

FORBIDDEN_LOGIC = (
    ast.FunctionDef,
    ast.AsyncFunctionDef,
    ast.If,
    ast.For,
    ast.While,
    ast.Try,
    ast.With,
    ast.Raise,
    ast.Assert,
    ast.Lambda,
    ast.Global,
    ast.Nonlocal,
    ast.Delete,
    ast.Await,
    ast.ListComp,
    ast.SetComp,
    ast.DictComp,
    ast.GeneratorExp,
    ast.IfExp,
)


def _schema_modules():
    return sorted(SCHEMA_ROOT.glob("*.py"))


def _module_imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.level, alias.name
        elif isinstance(node, ast.ImportFrom):
            yield node.level, node.module or ""


@pytest.mark.parametrize("path", _schema_modules(), ids=lambda p: p.name)
def test_schema_module_imports_are_stdlib_or_intra_package(path):
    for level, module in _module_imports(path):
        assert level <= 1, f"{path.name}: relative import escapes schema"
        if level == 1:
            continue
        parts = module.split(".")
        if parts[0] == "episky":
            assert len(parts) > 1 and parts[1] == "schema", (
                f"{path.name} imports episky.{'.'.join(parts[1:])}, but schema "
                "is Layer 0"
            )
        else:
            assert parts[0] in STDLIB, (
                f"{path.name} imports {module}, which is not stdlib"
            )


@pytest.mark.parametrize("path", _schema_modules(), ids=lambda p: p.name)
def test_schema_module_has_no_implementation_logic(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        assert not isinstance(node, FORBIDDEN_LOGIC), (
            f"{path.name} contains {type(node).__name__}; schema is type "
            "declarations only"
        )
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                assert isinstance(target, ast.Name) and target.id == "__all__", (
                    f"{path.name}: module-level assignment to "
                    f"{getattr(target, 'id', type(target).__name__)}"
                )


@pytest.mark.parametrize("module", sorted(PUBLIC_SURFACE))
def test_schema_public_surface_is_exactly_the_owned_vocabulary(module):
    mod = importlib.import_module(f"episky.schema.{module}")
    assert set(mod.__all__) == PUBLIC_SURFACE[module]


@pytest.mark.parametrize("module", sorted(PUBLIC_SURFACE))
def test_schema_public_names_are_defined_by_their_owning_module(module):
    mod = importlib.import_module(f"episky.schema.{module}")
    for name in PUBLIC_SURFACE[module]:
        owner = getattr(mod, name).__module__
        assert owner == f"episky.schema.{module}", (
            f"{name} is defined in {owner}, not its owning module"
        )


def test_schema_internal_markers_are_not_public():
    fact = importlib.import_module("episky.schema.fact")
    assert "MachineIdentity" not in fact.__all__
    assert "ObservationReference" not in fact.__all__
    assert hasattr(fact, "MachineIdentity")
    assert hasattr(fact, "ObservationReference")
