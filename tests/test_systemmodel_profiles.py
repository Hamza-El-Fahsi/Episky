"""Type-level conformance tests for the RFC-0021 §2 family vocabulary.

Transcribes RFC-0021 §2.1 (the five status words, ratified DN-8:
including Experimental) and §2.2 (the eight family rows and their
statuses) as type-level and data-level assertions. No behavior is
tested — there is none (blueprint §8.0; design review plan Commit 1).
"""

from episky.systemmodel.profiles import (
    FAMILY_STATUS,
    DistributionFamily,
    FamilyStatus,
)


def test_family_status_has_exactly_five_members():
    assert len(FamilyStatus) == 5


def test_family_status_members_match_rfc_0021_section_2_1():
    expected = {
        "SUPPORTED",
        "PLANNED",
        "EXPERIMENTAL",
        "UNSUPPORTED",
        "OUT_OF_SCOPE",
    }
    assert {member.name for member in FamilyStatus} == expected


def test_distribution_family_has_exactly_eight_members():
    assert len(DistributionFamily) == 8


def test_distribution_family_members_match_rfc_0021_section_2_2():
    expected = {
        "DEBIAN",
        "RED_HAT",
        "ARCH",
        "OPENSUSE",
        "IMMUTABLE",
        "OTHER_DISTROS",
        "NON_LINUX",
        "ANDROID",
    }
    assert {member.name for member in DistributionFamily} == expected


def test_family_status_data_covers_every_family_row():
    assert set(FAMILY_STATUS) == set(DistributionFamily)


def test_family_status_data_matches_rfc_0021_section_2_2():
    expected = {
        DistributionFamily.DEBIAN: FamilyStatus.SUPPORTED,
        DistributionFamily.RED_HAT: FamilyStatus.SUPPORTED,
        DistributionFamily.ARCH: FamilyStatus.PLANNED,
        DistributionFamily.OPENSUSE: FamilyStatus.PLANNED,
        DistributionFamily.IMMUTABLE: FamilyStatus.EXPERIMENTAL,
        DistributionFamily.OTHER_DISTROS: FamilyStatus.UNSUPPORTED,
        DistributionFamily.NON_LINUX: FamilyStatus.OUT_OF_SCOPE,
        DistributionFamily.ANDROID: FamilyStatus.OUT_OF_SCOPE,
    }
    assert expected == FAMILY_STATUS


def test_immutable_row_is_experimental():
    assert FAMILY_STATUS[DistributionFamily.IMMUTABLE] == FamilyStatus.EXPERIMENTAL
