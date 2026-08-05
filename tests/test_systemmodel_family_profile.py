"""Type-level conformance tests for the RFC-0021 §2.3 Family Profile.

Transcribes the §2.3 profile shape — the five descriptive dimensions,
ratified DN-12 — and the blueprint §7 / design-review DoD guarantee:
only Supported and Planned families have a profile; Unsupported,
Experimental, and Out-of-Scope families carry none and promise no
Facts. No behavior is tested: a profile is data, never callable
(blueprint §8.0; design review plan Commit 3).
"""

from collections.abc import Mapping

from episky.systemmodel.profiles import (
    FAMILY_PROFILES,
    FAMILY_STATUS,
    DistributionFamily,
    EcosystemStatus,
    FamilyProfile,
    FamilyStatus,
    PackageEcosystem,
)


def test_family_profile_has_the_five_ratified_dimensions():
    profile = FAMILY_PROFILES[DistributionFamily.DEBIAN]
    assert isinstance(profile.package_ecosystems, Mapping)
    assert isinstance(profile.init_contract, str)
    assert isinstance(profile.configuration_conventions, str)
    assert isinstance(profile.release_model, str)
    assert isinstance(profile.verification_conventions, str)


def test_only_supported_and_planned_families_have_a_profile():
    promising = {
        family
        for family in DistributionFamily
        if FAMILY_STATUS[family] in {FamilyStatus.SUPPORTED, FamilyStatus.PLANNED}
    }
    assert set(FAMILY_PROFILES) == promising


def test_supported_and_planned_families_are_exactly_the_four():
    assert set(FAMILY_PROFILES) == {
        DistributionFamily.DEBIAN,
        DistributionFamily.RED_HAT,
        DistributionFamily.ARCH,
        DistributionFamily.OPENSUSE,
    }


def test_unsupported_experimental_and_out_of_scope_have_no_profile():
    for family in DistributionFamily:
        if FAMILY_STATUS[family] in {
            FamilyStatus.UNSUPPORTED,
            FamilyStatus.EXPERIMENTAL,
            FamilyStatus.OUT_OF_SCOPE,
        }:
            assert family not in FAMILY_PROFILES


def test_every_profile_is_a_family_profile_instance():
    assert all(
        isinstance(profile, FamilyProfile) for profile in FAMILY_PROFILES.values()
    )


def test_profiles_are_data_not_callable():
    for profile in FAMILY_PROFILES.values():
        assert not callable(profile)


def test_supported_families_have_native_ecosystem():
    debian = FAMILY_PROFILES[DistributionFamily.DEBIAN]
    assert (
        debian.package_ecosystems[PackageEcosystem.APT_DPKG] == EcosystemStatus.NATIVE
    )
    red_hat = FAMILY_PROFILES[DistributionFamily.RED_HAT]
    assert (
        red_hat.package_ecosystems[PackageEcosystem.DNF_RPM] == EcosystemStatus.NATIVE
    )


def test_planned_families_have_experimental_ecosystem():
    arch = FAMILY_PROFILES[DistributionFamily.ARCH]
    assert (
        arch.package_ecosystems[PackageEcosystem.PACMAN] == EcosystemStatus.EXPERIMENTAL
    )
    opensuse = FAMILY_PROFILES[DistributionFamily.OPENSUSE]
    assert (
        opensuse.package_ecosystems[PackageEcosystem.ZYPPER]
        == EcosystemStatus.EXPERIMENTAL
    )


def test_supported_families_require_systemd_init():
    for family in (DistributionFamily.DEBIAN, DistributionFamily.RED_HAT):
        assert FAMILY_PROFILES[family].init_contract == "systemd"
