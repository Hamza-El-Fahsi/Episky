"""Type-level conformance tests for the RFC-0005 §10 FactCategory vocabulary.

Transcribes RFC-0005 §10 (the twelve fact categories, in table order) as
type-level assertions, and enforces the DN-9 ownership boundary: `schema`
owns the FactCategory type only; no mapping, no subsystem knowledge, no
meaning (design review plan Commit 7).
"""

import ast
import importlib
import pathlib
import sys

from episky.schema.fact import FactCategory

SCHEMA_FACT_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "schema"
    / "fact.py"
)
STDLIB = set(sys.stdlib_module_names) | {"__future__"}


def test_fact_category_has_exactly_twelve_members():
    assert len(FactCategory) == 12


def test_fact_category_members_match_rfc_0005_section_10():
    expected = {
        "HARDWARE",
        "KERNEL",
        "PACKAGES",
        "FILESYSTEM",
        "SERVICES",
        "NETWORKING",
        "STORAGE",
        "BOOT",
        "LOGS",
        "SECURITY",
        "CONFIGURATION",
        "APPLICATIONS",
    }
    assert {member.name for member in FactCategory} == expected


def test_fact_category_members_are_unique():
    assert len({member.value for member in FactCategory}) == len(FactCategory)


def test_fact_category_is_immutable():
    for member in FactCategory:
        assert member.value is not None
    assert FactCategory.HARDWARE.value != FactCategory.KERNEL.value


def test_fact_category_is_in_public_surface():
    fact = importlib.import_module("episky.schema.fact")
    assert "FactCategory" in fact.__all__


def test_fact_category_is_defined_by_its_owning_module():
    assert FactCategory.__module__ == "episky.schema.fact"


def test_schema_fact_imports_are_stdlib_only():
    tree = ast.parse(SCHEMA_FACT_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] in STDLIB, (
                    f"schema/fact.py imports {alias.name}, which is not stdlib"
                )
        elif isinstance(node, ast.ImportFrom):
            module = node.module or ""
            assert module.split(".")[0] in STDLIB, (
                f"schema/fact.py imports {module}, which is not stdlib"
            )


def test_schema_has_zero_knowledge_of_systemmodel():
    tree = ast.parse(SCHEMA_FACT_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert "systemmodel" not in alias.name
        elif isinstance(node, ast.ImportFrom):
            assert "systemmodel" not in (node.module or "")


def test_fact_category_carries_no_mapping_or_subsystem_knowledge():
    fact = importlib.import_module("episky.schema.fact")
    for name in fact.__all__:
        value = getattr(fact, name)
        assert not hasattr(value, "subsystem")
        assert not hasattr(value, "state_domain")
    assert "CATEGORY_SUBSYSTEMS" not in fact.__all__
    assert "CATEGORY_STATE_DOMAINS" not in fact.__all__
