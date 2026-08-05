"""Type-level conformance tests for the RFC-0021 §4 subsystem dependencies.

Transcribes RFC-0021 §4.2–§4.13 (each subsystem's "Depends on" clause)
as data-level assertions against SUBSYSTEM_DEPENDENCIES. No behavior is
tested — there is none (blueprint §8.0; design review plan Commit 5).
"""

import ast
import importlib
import pathlib
from types import MappingProxyType

from episky.systemmodel.subsystems import (
    SUBSYSTEM_DEPENDENCIES,
    MachineSubsystem,
)

SUBSYSTEMS_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "systemmodel"
    / "subsystems.py"
)

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


def test_dependency_data_covers_every_subsystem():
    assert set(SUBSYSTEM_DEPENDENCIES) == set(MachineSubsystem)


def test_dependency_data_has_no_undefined_subsystems():
    for subsystem in SUBSYSTEM_DEPENDENCIES:
        assert isinstance(subsystem, MachineSubsystem)


def test_dependency_data_matches_rfc_0021_sections_4_2_to_4_13():
    expected = {
        MachineSubsystem.HARDWARE: frozenset(),
        MachineSubsystem.BOOT: frozenset({MachineSubsystem.HARDWARE}),
        MachineSubsystem.KERNEL: frozenset(
            {MachineSubsystem.HARDWARE, MachineSubsystem.BOOT}
        ),
        MachineSubsystem.USERS: frozenset(
            {MachineSubsystem.FILESYSTEMS, MachineSubsystem.KERNEL}
        ),
        MachineSubsystem.SERVICES: frozenset(
            {
                MachineSubsystem.BOOT,
                MachineSubsystem.USERS,
                MachineSubsystem.FILESYSTEMS,
                MachineSubsystem.NETWORKING,
            }
        ),
        MachineSubsystem.STORAGE: frozenset(
            {MachineSubsystem.HARDWARE, MachineSubsystem.KERNEL}
        ),
        MachineSubsystem.FILESYSTEMS: frozenset(
            {MachineSubsystem.STORAGE, MachineSubsystem.KERNEL}
        ),
        MachineSubsystem.PACKAGES: frozenset(
            {
                MachineSubsystem.FILESYSTEMS,
                MachineSubsystem.NETWORKING,
                MachineSubsystem.KERNEL,
            }
        ),
        MachineSubsystem.NETWORKING: frozenset(
            {
                MachineSubsystem.HARDWARE,
                MachineSubsystem.KERNEL,
                MachineSubsystem.SERVICES,
            }
        ),
        MachineSubsystem.SECURITY: frozenset(
            {
                MachineSubsystem.KERNEL,
                MachineSubsystem.PACKAGES,
                MachineSubsystem.SERVICES,
                MachineSubsystem.USERS,
            }
        ),
        MachineSubsystem.LOGS: frozenset(
            {
                MachineSubsystem.SERVICES,
                MachineSubsystem.BOOT,
                MachineSubsystem.KERNEL,
            }
        ),
        MachineSubsystem.APPLICATIONS: frozenset(
            {
                MachineSubsystem.FILESYSTEMS,
                MachineSubsystem.USERS,
                MachineSubsystem.PACKAGES,
                MachineSubsystem.NETWORKING,
            }
        ),
    }
    assert expected == dict(SUBSYSTEM_DEPENDENCIES)


def test_hardware_is_the_bottom_of_the_stack():
    assert SUBSYSTEM_DEPENDENCIES[MachineSubsystem.HARDWARE] == frozenset()


def test_every_dependency_is_a_defined_subsystem():
    for dependencies in SUBSYSTEM_DEPENDENCIES.values():
        for dependency in dependencies:
            assert dependency in MachineSubsystem


def test_dependency_values_are_unique_per_subsystem():
    for dependencies in SUBSYSTEM_DEPENDENCIES.values():
        assert len(dependencies) == len(set(dependencies))


def test_dependency_data_is_immutable():
    assert isinstance(SUBSYSTEM_DEPENDENCIES, MappingProxyType)
    for dependencies in SUBSYSTEM_DEPENDENCIES.values():
        assert isinstance(dependencies, frozenset)


def test_dependency_data_has_no_behavior():
    tree = ast.parse(SUBSYSTEMS_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        assert not isinstance(node, FORBIDDEN_LOGIC), (
            f"subsystems.py contains {type(node).__name__}; it is "
            "vocabulary and data only"
        )


def test_dependency_public_surface_is_exactly_the_owned_vocabulary():
    mod = importlib.import_module("episky.systemmodel.subsystems")
    assert set(mod.__all__) == {
        "MachineSubsystem",
        "SUBSYSTEM_DEPENDENCIES",
        "SUBSYSTEM_STATE_REPRESENTATION",
        "StateDomain",
        "StateRepresentation",
    }


def test_dependency_public_names_are_defined_by_their_owning_module():
    importlib.import_module("episky.systemmodel.subsystems")
    assert MachineSubsystem.__module__ == "episky.systemmodel.subsystems"
    assert SUBSYSTEM_DEPENDENCIES.__class__.__module__ == "builtins"
