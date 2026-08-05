"""Type/data-level conformance tests for the Collector contract and baseline.

Transcribes the RFC-0003 §2.4 Collector contract (one specific question,
declared inputs, declared provenance behavior, declared Observation
output) and the ratified baseline set (blueprint §8.4; DN-17): exactly
three Collectors — distro, kernel, package-state — with package-state
scoped to the two Native ecosystems (apt/dpkg, dnf/rpm; RFC-0021 §5.2).
No behavior is tested — there is none (design review plan Commit 1).
"""

import dataclasses

import pytest

from episky.collectors.registry import (
    COLLECTOR_SPECS,
    CollectorSpec,
)
from episky.systemmodel.profiles import (
    ECOSYSTEM_STATUS,
    FAMILY_PROFILES,
    DistributionFamily,
    EcosystemStatus,
    PackageEcosystem,
)
from episky.systemmodel.subsystems import MachineSubsystem, StateDomain


def test_baseline_has_exactly_three_collectors():
    assert len(COLLECTOR_SPECS) == 3


def test_baseline_names_match_blueprint_section_8_4():
    assert set(COLLECTOR_SPECS) == {"distro", "kernel", "package-state"}


def test_every_baseline_collector_is_a_collector_spec():
    assert all(isinstance(spec, CollectorSpec) for spec in COLLECTOR_SPECS.values())


def test_collector_spec_is_an_immutable_dataclass():
    assert dataclasses.is_dataclass(CollectorSpec)
    with pytest.raises(dataclasses.FrozenInstanceError):
        COLLECTOR_SPECS["distro"].question = "changed"


def test_every_collector_answers_exactly_one_question():
    for spec in COLLECTOR_SPECS.values():
        assert isinstance(spec.question, str)
        assert spec.question.strip()


def test_every_collector_declares_observation_output():
    for spec in COLLECTOR_SPECS.values():
        assert spec.declared_output == "Observation"


def test_every_collector_carries_an_identity_version():
    for spec in COLLECTOR_SPECS.values():
        assert spec.name in COLLECTOR_SPECS
        assert isinstance(spec.version, str)
        assert spec.version


def test_every_collector_declares_inputs():
    for spec in COLLECTOR_SPECS.values():
        assert isinstance(spec.inputs, tuple)
        assert len(spec.inputs) >= 1


def test_distro_collector_reads_family_vocabulary():
    spec = COLLECTOR_SPECS["distro"]
    assert DistributionFamily in spec.inputs
    assert FAMILY_PROFILES in spec.inputs


def test_kernel_collector_reads_kernel_vocabulary():
    spec = COLLECTOR_SPECS["kernel"]
    assert MachineSubsystem.KERNEL in spec.inputs
    assert StateDomain.CONFIGURATION in spec.inputs


def test_package_state_collector_reads_ecosystem_vocabulary():
    spec = COLLECTOR_SPECS["package-state"]
    assert PackageEcosystem in spec.inputs
    assert ECOSYSTEM_STATUS in spec.inputs
    assert StateDomain.PACKAGE in spec.inputs


def test_package_state_baseline_is_native_ecosystems_only():
    native = {
        ecosystem
        for ecosystem, status in ECOSYSTEM_STATUS.items()
        if status == EcosystemStatus.NATIVE
    }
    assert native == {PackageEcosystem.APT_DPKG, PackageEcosystem.DNF_RPM}
    assert "Native" in COLLECTOR_SPECS["package-state"].question
