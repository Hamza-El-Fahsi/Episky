"""Dependency-rule conformance test.

Transcribes blueprint §4.1 (allowed edges) and §4.2 (forbidden edges) and
verifies the actual import graph of src/episky against them. In Iteration 0
every module is empty, so the graph has no edges yet; this test is the gate
that will catch a violation the moment one is written (blueprint §9, risk 6:
"the import-lint (forbidden edges, §4.2) runs in CI").
"""

import ast
import pathlib

import pytest

PACKAGE_ROOT = pathlib.Path(__file__).resolve().parents[1] / "src" / "episky"

# Blueprint §4.1 — allowed edges, package -> packages it may import.
ALLOWED = {
    "schema": set(),
    "systemmodel": {"schema"},
    "trust": {"schema"},
    "collectors": {"schema", "systemmodel", "trust"},
    "factlayer": {"collectors", "schema", "systemmodel", "trust"},
    "verification": {"factlayer", "schema", "systemmodel"},
    "secrets": {"schema", "trust"},
    "policy": {"schema", "trust", "factlayer"},
    "executor": {"schema", "audit", "secrets"},
    "audit": {"schema", "secrets"},
    "context": {"schema", "factlayer", "trust", "secrets", "systemmodel"},
    "providers": {"schema", "trust", "context"},
    "skills": {"schema", "collectors", "trust", "policy", "factlayer"},
    "core": {
        "schema",
        "systemmodel",
        "trust",
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
    },
    "cli": {"core", "audit", "context", "schema"},
}

# Blueprint §4.2 — forbidden edges, package -> packages it must NOT import.
# The §4.2 table also lists authority qualifiers — "policy (decision)",
# "factlayer (create)", "secrets (values)" — which are *use* restrictions, not
# import bans: those targets appear in the §4.1 allowed list and stay allowed
# at the import level (skills imports policy/factlayer types, context imports
# secrets classifier types, audit imports secrets metadata types).
FORBIDDEN = {
    "providers": {
        "factlayer",
        "executor",
        "policy",
        "verification",
        "audit",
        "secrets",
    },
    "skills": {"executor", "verification", "audit", "secrets"},
    "executor": {"policy", "verification", "factlayer", "providers", "skills"},
    "verification": {"providers", "skills", "executor", "policy"},
    "factlayer": {
        "providers",
        "policy",
        "executor",
        "skills",
        "context",
        "audit",
        "secrets",
    },
    "context": {"providers", "policy", "executor", "audit"},
    "audit": {"factlayer", "providers", "context", "policy", "executor"},
    "cli": {"policy", "executor", "factlayer", "providers", "skills", "secrets"},
}

ALL_PACKAGES = set(ALLOWED)


def _import_edges(tree):
    """Yield (source_package, target_package) for every intra-episky import."""
    edges = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                edges.append(alias.name)
        elif isinstance(node, ast.ImportFrom) and node.module:
            edges.append(node.module)
    return edges


def _resolve(module_name):
    """Map an imported module name to an episky package, or None."""
    parts = module_name.split(".")
    if parts[0] == "episky":
        return parts[1] if len(parts) > 1 else "episky"
    return None


@pytest.mark.parametrize("path", sorted(PACKAGE_ROOT.rglob("*.py")))
def test_no_forbidden_edge(path):
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    source_pkg = path.parts[-2]
    if source_pkg == "episky":
        return  # the top-level package only imports subpackages, checked below
    for imported in _import_edges(tree):
        target = _resolve(imported)
        if target is None or target == "episky":
            continue
        assert target not in FORBIDDEN.get(source_pkg, set()), (
            f"{path.relative_to(PACKAGE_ROOT)} imports forbidden package "
            f"episky.{target} (blueprint §4.2)"
        )


@pytest.mark.parametrize("path", sorted(PACKAGE_ROOT.rglob("*.py")))
def test_all_edges_allowed(path):
    src = path.read_text(encoding="utf-8")
    tree = ast.parse(src)
    source_pkg = path.parts[-2]
    for imported in _import_edges(tree):
        target = _resolve(imported)
        if target is None or target == "episky":
            continue
        assert target == source_pkg or target in ALLOWED.get(source_pkg, set()), (
            f"{path.relative_to(PACKAGE_ROOT)} imports episky.{target}, which "
            f"is not an allowed dependency of {source_pkg} (blueprint §4.1)"
        )


def test_allowed_and_forbidden_are_consistent():
    """Every forbidden target is also outside the allowed set (blueprint §4)."""
    for pkg, forbidden in FORBIDDEN.items():
        for target in forbidden:
            assert target not in ALLOWED.get(pkg, set()), (
                f"{pkg} -> {target} is both allowed and forbidden"
            )
            assert target in ALL_PACKAGES and target != pkg
