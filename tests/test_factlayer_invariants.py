"""Layer-2 behavioral invariants: Scenario 30 and the F-suite gaps (C7).

Transcribes design review §9.3 and the failure-injection walkthrough
Scenario 30, realized at the *status* level (design review §11, §16):
an unsupported family/ecosystem is a distinct status (RFC-0005 §4
"Unsupported", §13 F11), reached by normalization matching a "not
supported" family/ecosystem case — never a guess, never nothing, never a
collapsed status. Unsupported families have no Family Profile and the
runtime never fabricates one (RFC-0021 §2.1, §2.3; Scenario 30). The F
invariants below are the ones not already closed by the C1–C6 suites:
the Unsupported production path (F11/Scenario 30), fail-closed identity
for unknown environments, distro-independence of the claim (F7),
determinism of the whole collect→normalize path (F5), and the A4/F8
no-mutation and immutability guarantees.
"""

from datetime import datetime, timedelta

import pytest

from episky.collectors.registry import COLLECTOR_SPECS
from episky.factlayer.collect import Observation, RawOutput, collect
from episky.factlayer.normalize import _MACHINE_IDENTITY, normalize
from episky.factlayer.provenance import freshness_state
from episky.factlayer.store import FactIdentity, FactStore, StoreOutcome, record
from episky.schema.fact import Collector, FactStatus, FreshnessState
from episky.systemmodel.profiles import (
    FAMILY_PROFILES,
    FAMILY_STATUS,
    DistributionFamily,
    FamilyStatus,
)

COLLECTED_AT = datetime(2026, 8, 5, 12, 0, 0)
DEBIAN = FAMILY_PROFILES[DistributionFamily.DEBIAN]
RED_HAT = FAMILY_PROFILES[DistributionFamily.RED_HAT]
ARCH = FAMILY_PROFILES[DistributionFamily.ARCH]

# The families that must never appear in FAMILY_PROFILES (RFC-0021 §2.1;
# Scenario 30: Unsupported families have no Family Profile).
PROFILE_FREE_FAMILIES = (
    DistributionFamily.IMMUTABLE,
    DistributionFamily.OTHER_DISTROS,
    DistributionFamily.NON_LINUX,
    DistributionFamily.ANDROID,
)


def _observation(collector_name, output, exit_status=0, at=COLLECTED_AT):
    return Observation(
        raw_output=RawOutput(output=output),
        collector=Collector(name=collector_name, version="1"),
        collected_at=at,
        exit_status=exit_status,
    )


def test_family_profiles_exist_for_supported_and_planned_families_only():
    promised = {
        family
        for family, status in FAMILY_STATUS.items()
        if status in {FamilyStatus.SUPPORTED, FamilyStatus.PLANNED}
    }
    assert set(FAMILY_PROFILES) == promised
    assert set(FAMILY_PROFILES).isdisjoint(PROFILE_FREE_FAMILIES)


@pytest.mark.parametrize(
    "family",
    PROFILE_FREE_FAMILIES,
    ids=lambda family: family.name,
)
def test_unsupported_family_yields_unsupported_status(family):
    fact = normalize(
        _observation("distro", family.name),
        family_profile=None,
    )
    assert fact.status == FactStatus.UNSUPPORTED
    assert fact.scope.subject.name == "machine"
    assert fact.scope.property.name == "distribution-family"
    assert fact.scope.value.value == family.name


@pytest.mark.parametrize(
    "family",
    (DistributionFamily.DEBIAN, DistributionFamily.RED_HAT),
    ids=lambda family: family.name,
)
def test_supported_family_yields_observed_identity(family):
    fact = normalize(
        _observation("distro", family.name),
        family_profile=FAMILY_PROFILES[family],
    )
    assert fact.status == FactStatus.OBSERVED
    assert fact.scope.value.value == family.name


@pytest.mark.parametrize(
    "family",
    (DistributionFamily.ARCH, DistributionFamily.OPENSUSE),
    ids=lambda family: family.name,
)
def test_planned_family_yields_observed_identity_but_not_capabilities(family):
    fact = normalize(
        _observation("distro", family.name),
        family_profile=FAMILY_PROFILES[family],
    )
    assert fact.status == FactStatus.OBSERVED
    capability = normalize(_observation("package-state", "pacman 6.1"), ARCH)
    assert capability.status == FactStatus.UNSUPPORTED


def test_unrecognized_environment_fails_closed_as_unknown():
    fact = normalize(_observation("distro", "Ubuntu 24.04"), family_profile=None)
    assert fact.status == FactStatus.UNKNOWN
    assert fact.scope.value.value == "unknown"


def test_unrecognized_environment_is_never_guessed_observed():
    fact = normalize(_observation("distro", "mykylinux"), family_profile=None)
    assert fact.status is not FactStatus.OBSERVED
    assert fact.scope.value.value == "unknown"


def test_package_state_requires_a_native_ecosystem():
    fact = normalize(_observation("package-state", "apt 2.7.14"), DEBIAN)
    assert fact.status == FactStatus.OBSERVED
    assert fact.scope.value.value == "apt 2.7.14"


def test_package_state_without_native_ecosystem_is_unsupported():
    fact = normalize(_observation("package-state", "pacman 6.1"), ARCH)
    assert fact.status == FactStatus.UNSUPPORTED
    assert fact.scope.value.value == "unknown"


def test_package_state_with_no_profile_fails_closed_as_unsupported():
    fact = normalize(
        _observation("package-state", "anything at all"),
        family_profile=None,
    )
    assert fact.status == FactStatus.UNSUPPORTED
    assert fact.scope.value.value == "unknown"


def test_normalize_never_fabricates_a_profile_for_an_unknown_family():
    assert normalize(_observation("distro", "mystery os"), None).status == (
        FactStatus.UNKNOWN
    )
    assert normalize(_observation("package-state", "x"), None).status == (
        FactStatus.UNSUPPORTED
    )


def test_kernel_claim_is_distro_independent():
    observation = _observation("kernel", "6.8.12-arch1-1")
    assert normalize(observation, DEBIAN) == normalize(observation, RED_HAT)


def test_failed_run_is_unknown_and_never_fabricates_a_value():
    fact = normalize(_observation("kernel", "", exit_status=1), DEBIAN)
    assert fact.status == FactStatus.UNKNOWN
    assert fact.scope.value.value == "unknown"


def test_collect_normalize_path_is_deterministic():
    spec = COLLECTOR_SPECS["kernel"]
    first = collect(spec, "6.8.12-arch1-1", collected_at=COLLECTED_AT)
    second = collect(spec, "6.8.12-arch1-1", collected_at=COLLECTED_AT)
    assert normalize(first, DEBIAN) == normalize(second, DEBIAN)


def test_collecting_twice_yields_equal_but_distinct_observations():
    spec = COLLECTOR_SPECS["kernel"]
    first = collect(spec, "6.8.12-arch1-1", collected_at=COLLECTED_AT)
    second = collect(spec, "6.8.12-arch1-1", collected_at=COLLECTED_AT)
    assert first == second
    assert first is not second
    assert second.raw_output is not first.raw_output


def test_normalize_returns_a_freshly_current_fact():
    fact = normalize(_observation("kernel", "6.8.12-arch1-1"), DEBIAN)
    assert fact.freshness.state == FreshnessState.CURRENT
    assert (
        freshness_state(
            fact.provenance.collected_at,
            COLLECTED_AT + timedelta(hours=23),
        )
        is FreshnessState.POSSIBLY_STALE
    )
    assert (
        freshness_state(
            fact.provenance.collected_at,
            COLLECTED_AT + timedelta(hours=25),
        )
        is FreshnessState.STALE
    )


def test_unsupported_fact_flows_through_the_store_uncollapsed():
    store = FactStore(machine_identity=_MACHINE_IDENTITY)
    unsupported = normalize(
        _observation("distro", "OTHER_DISTROS"),
        family_profile=None,
    )
    result = record(store, unsupported)
    assert result.outcome == StoreOutcome.ADMITTED
    identity = FactIdentity(
        machine_identity=_MACHINE_IDENTITY,
        subject=unsupported.scope.subject,
        property=unsupported.scope.property,
    )
    assert result.store.current[identity].status is FactStatus.UNSUPPORTED


def test_an_unknown_fact_never_degrades_an_unsupported_status():
    store = FactStore(machine_identity=_MACHINE_IDENTITY)
    unsupported = normalize(
        _observation("distro", "OTHER_DISTROS"),
        family_profile=None,
    )
    store = record(store, unsupported).store
    unknown = normalize(
        _observation("distro", "Ubuntu 24.04"),
        family_profile=None,
    )
    result = record(store, unknown)
    assert result.outcome == StoreOutcome.REJECTED
    identity = FactIdentity(
        machine_identity=_MACHINE_IDENTITY,
        subject=unsupported.scope.subject,
        property=unsupported.scope.property,
    )
    assert result.store.current[identity].status is FactStatus.UNSUPPORTED
