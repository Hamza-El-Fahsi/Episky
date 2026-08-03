"""Iteration 0 smoke tests.

These prove the scaffold: every package and module required by blueprint §2
exists and imports, and every file carries its architectural ownership in its
docstring (blueprint §3, §10). No behavior is tested — there is none yet.
"""

import importlib
import pathlib

import pytest

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parents[1] / "src" / "episky"

# Blueprint §2 tree, transcribed exactly. Keys are packages, values the
# internal-only modules each package must expose. "adapters" is a subpackage.
EXPECTED_TREE = {
    "episky": [],
    "episky.schema": ["fact", "action", "outcome"],
    "episky.systemmodel": ["profiles", "subsystems"],
    "episky.trust": ["classes", "sanitize", "hostile"],
    "episky.collectors": ["registry"],
    "episky.factlayer": ["collect", "normalize", "provenance", "store"],
    "episky.verification": ["compare", "outcome"],
    "episky.secrets": ["classify", "redact", "store"],
    "episky.policy": ["classify", "gates", "tokens", "policy"],
    "episky.executor": ["runner", "guards", "elevation"],
    "episky.audit": ["records", "store", "transcript"],
    "episky.context": ["assemble", "boundaries", "memory", "provider_view"],
    "episky.providers": ["contract", "view", "adapters"],
    "episky.skills": ["loader", "activation", "runtime"],
    "episky.core": [
        "session",
        "state_machine",
        "events",
        "loop",
        "consultation",
        "replan",
        "recovery",
    ],
    "episky.cli": ["render", "collect", "expose"],
}

MODULES = list(EXPECTED_TREE) + [
    f"{pkg}.{mod}" for pkg, mods in EXPECTED_TREE.items() for mod in mods
]


def _module_file_for(module):
    """Path of `module` inside PACKAGE_ROOT (which already is the episky dir)."""
    if module == "episky":
        return PACKAGE_ROOT / "__init__.py"
    rel = module[len("episky.") :]
    if module.endswith(".adapters"):
        return PACKAGE_ROOT / "providers" / "adapters" / "__init__.py"
    if module in EXPECTED_TREE:
        return PACKAGE_ROOT / rel / "__init__.py"
    return PACKAGE_ROOT / f"{rel.replace('.', '/')}.py"


@pytest.mark.parametrize("module", sorted(MODULES))
def test_module_imports(module):
    importlib.import_module(module)


@pytest.mark.parametrize("module", sorted(MODULES))
def test_module_has_ownership_docstring(module):
    text = _module_file_for(module).read_text(encoding="utf-8")
    assert text.lstrip().startswith('"""'), f"{module} lacks a module docstring"
    doc = text.strip()
    assert "RFC-" in doc, f"{module} docstring does not cite an owning RFC"


def test_tree_matches_blueprint_exactly():
    """No module beyond blueprint §2 exists (no unused / invented files)."""
    actual_modules = set()
    for p in PACKAGE_ROOT.rglob("*.py"):
        rel = p.relative_to(PACKAGE_ROOT)
        if rel == pathlib.Path("__init__.py"):
            actual_modules.add("episky")
        elif rel.name == "__init__.py":
            actual_modules.add("episky." + rel.parent.as_posix().replace("/", "."))
        else:
            actual_modules.add("episky." + rel.as_posix()[:-3].replace("/", "."))
    assert actual_modules == set(MODULES)
