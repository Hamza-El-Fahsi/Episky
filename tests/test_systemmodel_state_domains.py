"""Type-level conformance tests for the RFC-0021 §6 State Domain vocabulary.

Transcribes RFC-0021 §6.2–§6.8 (the seven State Domains) and §6.10 (the
normative subsystem↔State Domain mapping) as type-level and data-level
assertions. No behavior is tested — there is none (blueprint §8.0;
design review plan Commit 6). The §6.9 independence/influence summary is
explanatory, not normative (§16 A6), and is not encoded.
"""

import ast
import pathlib
from types import MappingProxyType

from episky.systemmodel.subsystems import (
    SUBSYSTEM_STATE_REPRESENTATION,
    MachineSubsystem,
    StateDomain,
    StateRepresentation,
)

SUBSYSTEMS_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "systemmodel"
    / "subsystems.py"
)


def test_state_domain_has_exactly_seven_members():
    assert len(StateDomain) == 7


def test_state_domain_members_match_rfc_0021_sections_6_2_to_6_8():
    expected = {
        "PACKAGE",
        "SERVICE",
        "CONFIGURATION",
        "FILESYSTEM",
        "NETWORK",
        "USER",
        "SECURITY",
    }
    assert {member.name for member in StateDomain} == expected


def test_state_domain_members_are_unique():
    assert len({member.value for member in StateDomain}) == len(StateDomain)


def test_state_representation_is_frozen():
    assert StateRepresentation.__dataclass_params__.frozen is True
    assert StateRepresentation.__dataclass_params__.slots is True


def test_state_representation_is_data_only():
    representation = StateRepresentation(
        domains=frozenset({StateDomain.USER}), facts_only=False
    )
    assert representation.domains == frozenset({StateDomain.USER})
    assert representation.facts_only is False
    assert not callable(representation)


def test_subsystem_state_representation_covers_every_subsystem():
    assert set(SUBSYSTEM_STATE_REPRESENTATION) == set(MachineSubsystem)


def test_subsystem_state_representation_has_no_undefined_subsystems():
    for subsystem in SUBSYSTEM_STATE_REPRESENTATION:
        assert isinstance(subsystem, MachineSubsystem)


def test_subsystem_state_representation_matches_rfc_0021_section_6_10():
    expected = {
        MachineSubsystem.HARDWARE: StateRepresentation(
            domains=frozenset(), facts_only=True
        ),
        MachineSubsystem.BOOT: StateRepresentation(
            domains=frozenset({StateDomain.CONFIGURATION}), facts_only=False
        ),
        MachineSubsystem.KERNEL: StateRepresentation(
            domains=frozenset({StateDomain.CONFIGURATION}), facts_only=False
        ),
        MachineSubsystem.USERS: StateRepresentation(
            domains=frozenset({StateDomain.USER}), facts_only=False
        ),
        MachineSubsystem.SERVICES: StateRepresentation(
            domains=frozenset({StateDomain.SERVICE}), facts_only=False
        ),
        MachineSubsystem.STORAGE: StateRepresentation(
            domains=frozenset({StateDomain.FILESYSTEM}), facts_only=False
        ),
        MachineSubsystem.FILESYSTEMS: StateRepresentation(
            domains=frozenset({StateDomain.FILESYSTEM}), facts_only=False
        ),
        MachineSubsystem.PACKAGES: StateRepresentation(
            domains=frozenset({StateDomain.PACKAGE}), facts_only=False
        ),
        MachineSubsystem.NETWORKING: StateRepresentation(
            domains=frozenset({StateDomain.NETWORK}), facts_only=False
        ),
        MachineSubsystem.SECURITY: StateRepresentation(
            domains=frozenset({StateDomain.SECURITY}), facts_only=False
        ),
        MachineSubsystem.LOGS: StateRepresentation(
            domains=frozenset(), facts_only=True
        ),
        MachineSubsystem.APPLICATIONS: StateRepresentation(
            domains=frozenset({StateDomain.FILESYSTEM, StateDomain.USER}),
            facts_only=False,
        ),
    }
    assert expected == dict(SUBSYSTEM_STATE_REPRESENTATION)


def test_facts_only_subsystems_are_hardware_and_logs():
    assert SUBSYSTEM_STATE_REPRESENTATION[MachineSubsystem.HARDWARE].facts_only is True
    assert SUBSYSTEM_STATE_REPRESENTATION[MachineSubsystem.LOGS].facts_only is True


def test_no_subsystem_has_two_state_representations():
    for _subsystem, representation in SUBSYSTEM_STATE_REPRESENTATION.items():
        assert isinstance(representation, StateRepresentation)
        assert isinstance(representation.domains, frozenset)
        assert isinstance(representation.facts_only, bool)


def test_state_domain_references_are_defined_domains():
    for representation in SUBSYSTEM_STATE_REPRESENTATION.values():
        for domain in representation.domains:
            assert domain in StateDomain


def test_subsystem_state_representation_is_immutable():
    assert isinstance(SUBSYSTEM_STATE_REPRESENTATION, MappingProxyType)


def test_state_domain_module_has_no_behavior():
    tree = ast.parse(SUBSYSTEMS_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        assert not isinstance(
            node,
            (
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
            ),
        ), (
            f"subsystems.py contains {type(node).__name__}; it is "
            "vocabulary and data only"
        )


def test_state_domain_public_surface_is_exactly_the_owned_vocabulary():
    from episky.systemmodel import subsystems

    assert set(subsystems.__all__) == {
        "MachineSubsystem",
        "SUBSYSTEM_DEPENDENCIES",
        "SUBSYSTEM_STATE_REPRESENTATION",
        "StateDomain",
        "StateRepresentation",
    }
