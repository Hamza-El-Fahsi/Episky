"""Behavioral tests for the normalization stage (RFC-0005 §2; F5, F1, F11).

Transcribes the C4 contract: `normalize(Observation, FamilyProfile) ->
Fact` is the only gate between machine and knowledge — deterministic
(F5), pure, side-effect free, and the sole construction path to a Fact's
components (F1, DN-2). A failed or unparseable run yields an Unknown
Fact naming the Collector as its confidence source (RFC-0002 §4.2;
RFC-0005 §4; DN-16), never a guess and never nothing. Provenance is
attached at normalization (F10; DN-23). The Family Profile absorbs
distro variance (F7).
"""

import dataclasses
from datetime import datetime

import pytest

from episky.factlayer.collect import Observation, RawOutput
from episky.factlayer.normalize import normalize
from episky.schema.fact import (
    Collector,
    ConfidenceSource,
    Fact,
    FactStatus,
    Provenance,
)
from episky.systemmodel.profiles import (
    FAMILY_PROFILES,
    DistributionFamily,
)

COLLECTED_AT = datetime(2026, 8, 5, 12, 0, 0)
DEBIAN = FAMILY_PROFILES[DistributionFamily.DEBIAN]
RED_HAT = FAMILY_PROFILES[DistributionFamily.RED_HAT]


def _observation(collector_name="kernel", output="6.8.12-arch1-1", exit_status=0):
    return Observation(
        raw_output=RawOutput(output=output),
        collector=Collector(name=collector_name, version="1"),
        collected_at=COLLECTED_AT,
        exit_status=exit_status,
    )


def test_normalize_successful_run_yields_an_observed_fact():
    fact = normalize(_observation(), DEBIAN)
    assert isinstance(fact, Fact)
    assert fact.status == FactStatus.OBSERVED
    assert fact.scope.subject.name == "kernel"
    assert fact.scope.property.name == "version"
    assert fact.scope.value.value == "6.8.12-arch1-1"


def test_normalize_is_deterministic_and_repeatable():
    observation = _observation()
    assert normalize(observation, DEBIAN) == normalize(observation, DEBIAN)
    assert normalize(observation, DEBIAN) == normalize(observation, DEBIAN)


def test_identical_input_yields_an_identical_fact():
    first = normalize(_observation(), DEBIAN)
    second = normalize(_observation(), DEBIAN)
    assert first == second
    assert first.scope == second.scope
    assert first.provenance == second.provenance


def test_normalization_is_the_only_fact_path():
    observation = _observation()
    fact = normalize(observation, DEBIAN)
    assert isinstance(fact.provenance, Provenance)
    assert fact.provenance.collector == observation.collector
    assert fact.provenance.collected_at == observation.collected_at
    assert isinstance(fact.confidence, ConfidenceSource)


def test_normalize_attaches_provenance_at_normalization():
    observation = _observation()
    fact = normalize(observation, DEBIAN)
    assert fact.provenance.observation is not None
    assert fact.provenance.collector.name == "kernel"
    assert fact.provenance.collector.version == "1"
    assert fact.provenance.collected_at == COLLECTED_AT


def test_normalize_never_mutates_the_observation():
    observation = _observation()
    before = (
        observation.raw_output.output,
        observation.collector.name,
        observation.collected_at,
        observation.exit_status,
    )
    normalize(observation, DEBIAN)
    assert (
        observation.raw_output.output,
        observation.collector.name,
        observation.collected_at,
        observation.exit_status,
    ) == before


def test_normalize_returns_an_immutable_fact():
    fact = normalize(_observation(), DEBIAN)
    assert dataclasses.is_dataclass(fact)
    with pytest.raises(dataclasses.FrozenInstanceError):
        fact.status = FactStatus.UNKNOWN


def test_normalize_failed_run_yields_unknown():
    fact = normalize(_observation(exit_status=1), DEBIAN)
    assert fact.status == FactStatus.UNKNOWN
    assert fact.scope.value.value == "unknown"


def test_normalize_empty_output_yields_unknown():
    fact = normalize(_observation(output=""), DEBIAN)
    assert fact.status == FactStatus.UNKNOWN
    assert fact.scope.value.value == "unknown"


def test_normalize_unrecognized_collector_yields_unknown():
    fact = normalize(_observation(collector_name="firmware"), DEBIAN)
    assert fact.status == FactStatus.UNKNOWN
    assert fact.scope.value.value == "unknown"


def test_unknown_names_the_collector_as_confidence_source():
    fact = normalize(
        _observation(collector_name="package-state", exit_status=2), DEBIAN
    )
    assert fact.status == FactStatus.UNKNOWN
    assert fact.confidence.name == "package-state@1"


def test_normalize_distro_accepts_only_canonical_families():
    debian = normalize(_observation("distro", "debian"), DEBIAN)
    assert debian.status == FactStatus.OBSERVED
    assert debian.scope.subject.name == "machine"
    assert debian.scope.property.name == "distribution-family"
    assert debian.scope.value.value == "DEBIAN"
    unknown = normalize(_observation("distro", "Ubuntu 24.04"), DEBIAN)
    assert unknown.status == FactStatus.UNKNOWN


def test_normalize_package_state_requires_a_native_ecosystem():
    fact = normalize(_observation("package-state", "apt 2.7.14"), DEBIAN)
    assert fact.status == FactStatus.OBSERVED
    assert fact.scope.subject.name == "package"
    assert fact.scope.property.name == "installed"
    assert fact.scope.value.value == "apt 2.7.14"


def test_normalize_package_state_is_distro_independent():
    debian_fact = normalize(_observation("package-state", "apt 2.7.14"), DEBIAN)
    red_hat_fact = normalize(_observation("package-state", "apt 2.7.14"), RED_HAT)
    assert debian_fact == red_hat_fact
    assert debian_fact.status == FactStatus.OBSERVED
