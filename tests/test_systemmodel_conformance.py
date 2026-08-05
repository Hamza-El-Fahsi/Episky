"""Architectural conformance of the `systemmodel` package (Layer 1).

Enforces the Layer-1 contract (blueprint §4.1, §8.2): every
`systemmodel` module imports only the standard library and `schema`, and
carries no implementation logic — vocabulary, immutable data types, and
module-level data tables only (design review plan Commit 8). Also fixes
the ownership boundaries (blueprint §10; design review §11): each
module's public surface is exactly the canonical vocabulary its owning
RFC assigns, `profiles.py` owns only RFC-0021 §2/§5 profile vocabulary,
`subsystems.py` owns only §4/§6 subsystem/State-Domain vocabulary,
`schema` owns FactCategory (DN-9), and no name is owned twice.
"""

import ast
import importlib
import pathlib
import sys

import pytest

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parents[1] / "src" / "episky"
SYSTEMMODEL_ROOT = PACKAGE_ROOT / "systemmodel"
STDLIB = set(sys.stdlib_module_names) | {"__future__"}

# Blueprint §4.1: Layer 1 allows exactly one intra-package import target.
ALLOWED_PACKAGES = {"schema"}

# Design review §11 ownership, transcribed: each module's public surface is
# exactly the canonical vocabulary its owning RFC assigns.
PUBLIC_SURFACE = {
    "profiles": {
        "DistributionFamily",
        "ECOSYSTEM_STATUS",
        "EcosystemStatus",
        "FAMILY_PROFILES",
        "FAMILY_STATUS",
        "FamilyProfile",
        "FamilyStatus",
        "PackageEcosystem",
    },
    "subsystems": {
        "MachineSubsystem",
        "SUBSYSTEM_DEPENDENCIES",
        "SUBSYSTEM_STATE_REPRESENTATION",
        "StateDomain",
        "StateRepresentation",
    },
}

# Module-level data tables each module owns; the only module-level
# assignments permitted beyond `__all__`.
DATA_TABLES = {
    "profiles": {"ECOSYSTEM_STATUS", "FAMILY_PROFILES", "FAMILY_STATUS"},
    "subsystems": {"SUBSYSTEM_DEPENDENCIES", "SUBSYSTEM_STATE_REPRESENTATION"},
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


def _systemmodel_modules():
    return sorted(SYSTEMMODEL_ROOT.glob("*.py"))


def _module_imports(path):
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                yield node.level, alias.name
        elif isinstance(node, ast.ImportFrom):
            yield node.level, node.module or ""


@pytest.mark.parametrize("path", _systemmodel_modules(), ids=lambda p: p.name)
def test_systemmodel_module_imports_are_stdlib_or_schema(path):
    for level, module in _module_imports(path):
        assert level <= 1, f"{path.name}: relative import escapes systemmodel"
        if level == 1:
            continue
        parts = module.split(".")
        if parts[0] == "episky":
            assert len(parts) > 1 and parts[1] in ALLOWED_PACKAGES, (
                f"{path.name} imports episky.{'.'.join(parts[1:])}, but "
                f"Layer 1 allows only {sorted(ALLOWED_PACKAGES)}"
            )
        else:
            assert parts[0] in STDLIB, (
                f"{path.name} imports {module}, which is not stdlib"
            )


@pytest.mark.parametrize("path", _systemmodel_modules(), ids=lambda p: p.name)
def test_systemmodel_module_has_no_implementation_logic(path):
    module = path.stem
    tree = ast.parse(path.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        assert not isinstance(node, FORBIDDEN_LOGIC), (
            f"{path.name} contains {type(node).__name__}; systemmodel is "
            "vocabulary and data only"
        )
    for stmt in tree.body:
        if isinstance(stmt, ast.Assign):
            for target in stmt.targets:
                assert isinstance(target, ast.Name), (
                    f"{path.name}: module-level assignment to "
                    f"{getattr(target, 'id', type(target).__name__)}"
                )
                assert target.id == "__all__" or target.id in DATA_TABLES[module], (
                    f"{path.name}: module-level assignment to "
                    f"{target.id} is not an owned data table"
                )


@pytest.mark.parametrize("module", sorted(PUBLIC_SURFACE))
def test_systemmodel_public_surface_is_exactly_the_owned_vocabulary(module):
    mod = importlib.import_module(f"episky.systemmodel.{module}")
    assert set(mod.__all__) == PUBLIC_SURFACE[module]


@pytest.mark.parametrize("module", sorted(PUBLIC_SURFACE))
def test_systemmodel_public_names_are_defined_by_their_owning_module(module):
    mod = importlib.import_module(f"episky.systemmodel.{module}")
    for name in PUBLIC_SURFACE[module]:
        value = getattr(mod, name)
        owner = getattr(value, "__module__", None)
        if owner is None:
            assert name in mod.__dict__, (
                f"{name} is not defined in episky.systemmodel.{module}"
            )
        else:
            assert owner == f"episky.systemmodel.{module}", (
                f"{name} is defined in {owner}, not its owning module"
            )


def test_systemmodel_public_surface_has_no_ownership_overlap():
    names = [name for surface in PUBLIC_SURFACE.values() for name in surface]
    assert len(names) == len(set(names)), "a name is owned by two modules"


def test_schema_owns_fact_category_not_systemmodel():
    fact = importlib.import_module("episky.schema.fact")
    assert "FactCategory" in fact.__all__
    assert "FactCategory" not in PUBLIC_SURFACE["profiles"]
    assert "FactCategory" not in PUBLIC_SURFACE["subsystems"]
    assert fact.FactCategory.__module__ == "episky.schema.fact"


def test_systemmodel_has_no_reverse_dependency_into_schema():
    for path in sorted(PACKAGE_ROOT.rglob("*.py")):
        source_pkg = path.parts[-2]
        if source_pkg != "schema":
            continue
        for _level, module in _module_imports(path):
            assert "systemmodel" not in module, (
                f"{path.relative_to(PACKAGE_ROOT)} imports "
                f"{module}; schema must never import systemmodel"
            )


def test_systemmodel_data_tables_are_module_level_constants():
    profiles = importlib.import_module("episky.systemmodel.profiles")
    subsystems = importlib.import_module("episky.systemmodel.subsystems")
    for table in DATA_TABLES["profiles"]:
        assert isinstance(getattr(profiles, table), dict)
    for table in DATA_TABLES["subsystems"]:
        assert isinstance(
            getattr(subsystems, table), type(subsystems.SUBSYSTEM_DEPENDENCIES)
        )
