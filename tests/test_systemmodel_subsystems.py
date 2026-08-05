"""Type-level conformance tests for the RFC-0021 §4 subsystem vocabulary.

Transcribes RFC-0021 §4.1 (the twelve Machine Subsystems, in tree order)
as type-level assertions. No behavior is tested — there is none
(blueprint §8.0; design review plan Commit 4).
"""

from episky.systemmodel.subsystems import MachineSubsystem


def test_machine_subsystem_has_exactly_twelve_members():
    assert len(MachineSubsystem) == 12


def test_machine_subsystem_members_match_rfc_0021_section_4_1():
    expected = {
        "HARDWARE",
        "BOOT",
        "KERNEL",
        "USERS",
        "SERVICES",
        "STORAGE",
        "FILESYSTEMS",
        "PACKAGES",
        "NETWORKING",
        "SECURITY",
        "LOGS",
        "APPLICATIONS",
    }
    assert {member.name for member in MachineSubsystem} == expected


def test_machine_subsystem_member_names_match_sections_4_2_to_4_13():
    assert MachineSubsystem.HARDWARE.name == "HARDWARE"
    assert MachineSubsystem.BOOT.name == "BOOT"
    assert MachineSubsystem.KERNEL.name == "KERNEL"
    assert MachineSubsystem.USERS.name == "USERS"
    assert MachineSubsystem.SERVICES.name == "SERVICES"
    assert MachineSubsystem.STORAGE.name == "STORAGE"
    assert MachineSubsystem.FILESYSTEMS.name == "FILESYSTEMS"
    assert MachineSubsystem.PACKAGES.name == "PACKAGES"
    assert MachineSubsystem.NETWORKING.name == "NETWORKING"
    assert MachineSubsystem.SECURITY.name == "SECURITY"
    assert MachineSubsystem.LOGS.name == "LOGS"
    assert MachineSubsystem.APPLICATIONS.name == "APPLICATIONS"


def test_machine_subsystem_has_no_missing_members():
    expected = {
        "HARDWARE",
        "BOOT",
        "KERNEL",
        "USERS",
        "SERVICES",
        "STORAGE",
        "FILESYSTEMS",
        "PACKAGES",
        "NETWORKING",
        "SECURITY",
        "LOGS",
        "APPLICATIONS",
    }
    assert expected.issubset({member.name for member in MachineSubsystem})


def test_machine_subsystem_has_no_additional_members():
    expected = {
        "HARDWARE",
        "BOOT",
        "KERNEL",
        "USERS",
        "SERVICES",
        "STORAGE",
        "FILESYSTEMS",
        "PACKAGES",
        "NETWORKING",
        "SECURITY",
        "LOGS",
        "APPLICATIONS",
    }
    assert {member.name for member in MachineSubsystem}.issubset(expected)


def test_machine_subsystem_members_are_unique():
    assert len({member.value for member in MachineSubsystem}) == len(MachineSubsystem)
