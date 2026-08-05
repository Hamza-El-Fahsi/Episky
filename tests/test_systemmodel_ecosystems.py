"""Type-level conformance tests for the RFC-0021 §5 ecosystem vocabulary.

Transcribes RFC-0021 §5.1 (the four ecosystem statuses) and §5.2 (the
eight ecosystems and their base status) as type-level and data-level
assertions. No behavior is tested — there is none (blueprint §8.0;
design review plan Commit 2). The §5.2 "Native (Debian family)" /
"Native (Red Hat family)" per-family nuance is carried by the Family
Profile (RFC-0021 §2.3; plan Commit 3), not by this base table.
"""

from episky.systemmodel.profiles import (
    ECOSYSTEM_STATUS,
    EcosystemStatus,
    PackageEcosystem,
)


def test_ecosystem_status_has_exactly_four_members():
    assert len(EcosystemStatus) == 4


def test_ecosystem_status_members_match_rfc_0021_section_5_1():
    expected = {"NATIVE", "SECONDARY", "EXPERIMENTAL", "UNSUPPORTED"}
    assert {member.name for member in EcosystemStatus} == expected


def test_package_ecosystem_has_exactly_eight_members():
    assert len(PackageEcosystem) == 8


def test_package_ecosystem_members_match_rfc_0021_section_5_2():
    expected = {
        "APT_DPKG",
        "DNF_RPM",
        "PACMAN",
        "ZYPPER",
        "NIX",
        "FLATPAK",
        "SNAP",
        "APPIMAGE",
    }
    assert {member.name for member in PackageEcosystem} == expected


def test_ecosystem_status_data_covers_every_ecosystem():
    assert set(ECOSYSTEM_STATUS) == set(PackageEcosystem)


def test_ecosystem_status_data_matches_rfc_0021_section_5_2():
    expected = {
        PackageEcosystem.APT_DPKG: EcosystemStatus.NATIVE,
        PackageEcosystem.DNF_RPM: EcosystemStatus.NATIVE,
        PackageEcosystem.PACMAN: EcosystemStatus.EXPERIMENTAL,
        PackageEcosystem.ZYPPER: EcosystemStatus.EXPERIMENTAL,
        PackageEcosystem.NIX: EcosystemStatus.EXPERIMENTAL,
        PackageEcosystem.FLATPAK: EcosystemStatus.SECONDARY,
        PackageEcosystem.SNAP: EcosystemStatus.SECONDARY,
        PackageEcosystem.APPIMAGE: EcosystemStatus.SECONDARY,
    }
    assert expected == ECOSYSTEM_STATUS


def test_native_ecosystems_are_apt_dpkg_and_dnf_rpm():
    assert ECOSYSTEM_STATUS[PackageEcosystem.APT_DPKG] == EcosystemStatus.NATIVE
    assert ECOSYSTEM_STATUS[PackageEcosystem.DNF_RPM] == EcosystemStatus.NATIVE
