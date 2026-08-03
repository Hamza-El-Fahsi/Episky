"""Type-level conformance tests for the RFC-0005 §4/§12 type surface.

Transcribes the F11 structural distinctions (RFC-0005 §13) and the
freshness-state enumeration (§12) as type-level assertions: members are
distinct, never silently converted or collapsed, and the surface is a
pure, behavior-free type declaration. No behavior is tested — there is
none yet (blueprint §8.2: type-level invariant conformance tests only).
"""

import dataclasses
from datetime import datetime

import pytest

from episky.schema.fact import (
    Collector,
    ConfidenceSource,
    Fact,
    FactStatus,
    Freshness,
    FreshnessState,
    MachineIdentity,
    ObservationReference,
    Property,
    Provenance,
    Scope,
    Subject,
    Value,
)


def test_fact_status_has_exactly_eight_members():
    assert len(FactStatus) == 8


def test_fact_status_members_match_rfc_0005_section_4():
    expected = {
        "OBSERVED",
        "VERIFIED",
        "UNKNOWN",
        "UNAVAILABLE",
        "UNSUPPORTED",
        "CONTRADICTED",
        "STALE",
        "INVALID",
    }
    assert {member.name for member in FactStatus} == expected


def test_f11_unknown_unavailable_unsupported_stale_are_distinct():
    distinct = {
        FactStatus.UNKNOWN,
        FactStatus.UNAVAILABLE,
        FactStatus.UNSUPPORTED,
        FactStatus.STALE,
    }
    assert len(distinct) == 4


def test_f11_statuses_are_never_collapsed():
    assert FactStatus.UNKNOWN is not FactStatus.UNAVAILABLE
    assert FactStatus.UNKNOWN is not FactStatus.UNSUPPORTED
    assert FactStatus.UNKNOWN is not FactStatus.STALE
    assert FactStatus.UNAVAILABLE is not FactStatus.UNSUPPORTED
    assert FactStatus.UNAVAILABLE is not FactStatus.STALE
    assert FactStatus.UNSUPPORTED is not FactStatus.STALE


def test_f11_no_silent_status_conversion():
    assert FactStatus.UNKNOWN != FactStatus.UNAVAILABLE
    assert FactStatus.UNKNOWN != FactStatus.UNSUPPORTED
    assert FactStatus.UNKNOWN != FactStatus.STALE
    assert FactStatus.OBSERVED != FactStatus.VERIFIED
    assert FactStatus.OBSERVED is not FactStatus.VERIFIED


def test_freshness_state_has_exactly_five_members():
    assert len(FreshnessState) == 5


def test_freshness_state_members_match_rfc_0005_section_12():
    expected = {
        "CURRENT",
        "POSSIBLY_STALE",
        "STALE",
        "EXPIRED",
        "UNKNOWN_FRESHNESS",
    }
    assert {member.name for member in FreshnessState} == expected


def test_freshness_state_members_are_distinct():
    assert len(set(FreshnessState)) == 5
    assert FreshnessState.CURRENT is not FreshnessState.STALE
    assert FreshnessState.STALE is not FreshnessState.EXPIRED
    assert FreshnessState.UNKNOWN_FRESHNESS is not FreshnessState.CURRENT


def test_freshness_carries_state():
    freshness = Freshness(state=FreshnessState.CURRENT)
    assert freshness.state is FreshnessState.CURRENT


def test_freshness_is_immutable():
    freshness = Freshness(state=FreshnessState.CURRENT)
    with pytest.raises(AttributeError):
        freshness.state = FreshnessState.STALE


def _provenance():
    return Provenance(
        observation=ObservationReference(),
        collector=Collector(name="package-state", version="1"),
        collected_at=datetime(2026, 8, 3, 12, 0, 0),
    )


def test_collector_identity_requires_name_and_version():
    with pytest.raises(TypeError):
        Collector(name="package-state")
    with pytest.raises(TypeError):
        Collector(version="1")
    collector = Collector(name="package-state", version="1")
    assert collector.name == "package-state"
    assert collector.version == "1"


def test_collector_identity_is_immutable():
    collector = Collector(name="package-state", version="1")
    with pytest.raises(AttributeError):
        collector.name = "other"


def test_confidence_source_is_a_named_check_only():
    source = ConfidenceSource(name="dpkg-query--status")
    assert source.name == "dpkg-query--status"


def test_confidence_source_has_no_numeric_field():
    annotations = ConfidenceSource.__annotations__
    assert set(annotations) == {"name"}
    assert annotations["name"] is str


def test_confidence_source_is_immutable():
    source = ConfidenceSource(name="dpkg-query--status")
    with pytest.raises(AttributeError):
        source.name = "other"


def test_observation_reference_carries_no_data():
    ObservationReference()
    assert ObservationReference.__slots__ == ()
    with pytest.raises(TypeError):
        ObservationReference("payload")


def test_provenance_components_are_mandatory():
    collector = Collector(name="package-state", version="1")
    with pytest.raises(TypeError):
        Provenance(collector=collector, collected_at=datetime(2026, 8, 3))
    with pytest.raises(TypeError):
        Provenance(
            observation=ObservationReference(),
            collected_at=datetime(2026, 8, 3),
        )
    with pytest.raises(TypeError):
        Provenance(observation=ObservationReference(), collector=collector)


def test_provenance_carries_observation_reference():
    provenance = _provenance()
    assert provenance.observation is not None
    assert provenance.collector == Collector(name="package-state", version="1")
    assert provenance.collected_at == datetime(2026, 8, 3, 12, 0, 0)
    assert provenance.re_collected_at == ()


def test_provenance_is_immutable():
    provenance = _provenance()
    with pytest.raises(AttributeError):
        provenance.collector = Collector(name="other", version="1")


def test_subject_property_value_are_named_canonical_components():
    subject = Subject(name="systemd")
    prop = Property(name="running-state")
    value = Value(value="running")
    assert subject.name == "systemd"
    assert prop.name == "running-state"
    assert value.value == "running"


def test_claim_components_are_immutable():
    subject = Subject(name="systemd")
    with pytest.raises(AttributeError):
        subject.name = "other"
    value = Value(value="running")
    with pytest.raises(AttributeError):
        value.value = "stopped"


def test_scope_requires_subject_property_value():
    with pytest.raises(TypeError):
        Scope(
            subject=Subject(name="systemd"),
            property=Property(name="running-state"),
        )
    with pytest.raises(TypeError):
        Scope(
            property=Property(name="running-state"),
            value=Value(value="running"),
        )
    with pytest.raises(TypeError):
        Scope(
            subject=Subject(name="systemd"),
            value=Value(value="running"),
        )


def test_scope_carries_subject_property_value():
    scope = Scope(
        subject=Subject(name="systemd"),
        property=Property(name="running-state"),
        value=Value(value="running"),
    )
    assert scope.subject == Subject(name="systemd")
    assert scope.property == Property(name="running-state")
    assert scope.value == Value(value="running")


def test_scope_is_immutable():
    scope = Scope(
        subject=Subject(name="systemd"),
        property=Property(name="running-state"),
        value=Value(value="running"),
    )
    with pytest.raises(AttributeError):
        scope.subject = Subject(name="other")


def test_f13_scope_asserts_exactly_the_claim():
    assert set(Scope.__annotations__) == {"subject", "property", "value"}


def test_f2_no_permission_field_in_claim_types():
    claim_types = (Subject, Property, Value, Scope)
    fields = set().union(*(set(t.__annotations__) for t in claim_types))
    forbidden = {
        "permission",
        "role",
        "authority",
        "capability",
        "privilege",
        "grant",
    }
    assert fields.isdisjoint(forbidden)


def test_f12_machine_identity_is_an_opaque_placeholder():
    MachineIdentity()
    assert MachineIdentity.__slots__ == ()
    assert not issubclass(MachineIdentity, str)
    with pytest.raises(TypeError):
        MachineIdentity("payload")


def _fact():
    return Fact(
        scope=Scope(
            subject=Subject(name="systemd"),
            property=Property(name="running-state"),
            value=Value(value="running"),
        ),
        status=FactStatus.OBSERVED,
        confidence=ConfidenceSource(name="systemctl-is-active"),
        provenance=_provenance(),
        freshness=Freshness(state=FreshnessState.CURRENT),
        machine_identity=MachineIdentity(),
    )


def test_fact_is_a_composition_of_canonical_types():
    fact = _fact()
    assert fact.scope.subject == Subject(name="systemd")
    assert fact.scope.property == Property(name="running-state")
    assert fact.scope.value == Value(value="running")
    assert fact.status is FactStatus.OBSERVED
    assert fact.confidence == ConfidenceSource(name="systemctl-is-active")
    assert fact.provenance.collector == Collector(name="package-state", version="1")
    assert fact.provenance.collected_at == datetime(2026, 8, 3, 12, 0, 0)
    assert fact.freshness == Freshness(state=FreshnessState.CURRENT)
    assert fact.machine_identity is not None


def test_fact_components_are_mandatory():
    kwargs = {
        "scope": Scope(
            subject=Subject(name="systemd"),
            property=Property(name="running-state"),
            value=Value(value="running"),
        ),
        "status": FactStatus.OBSERVED,
        "confidence": ConfidenceSource(name="systemctl-is-active"),
        "provenance": _provenance(),
        "freshness": Freshness(state=FreshnessState.CURRENT),
        "machine_identity": MachineIdentity(),
    }
    for missing in kwargs:
        partial = {k: v for k, v in kwargs.items() if k != missing}
        with pytest.raises(TypeError):
            Fact(**partial)


def test_fact_is_immutable():
    fact = _fact()
    with pytest.raises(AttributeError):
        fact.status = FactStatus.VERIFIED


def test_f1_fact_has_no_raw_text_field():
    raw_text = (str, bytes, bytearray)
    component_types = {
        Scope,
        FactStatus,
        ConfidenceSource,
        Provenance,
        Freshness,
        MachineIdentity,
    }
    assert set(Fact.__annotations__.values()) == component_types
    for field_type in Fact.__annotations__.values():
        assert field_type not in raw_text


def test_f2_fact_has_no_permission_field():
    forbidden = {
        "permission",
        "role",
        "authority",
        "capability",
        "privilege",
        "grant",
        "approval",
        "token",
        "policy",
    }
    assert set(Fact.__annotations__).isdisjoint(forbidden)


def test_f3_fact_is_a_pure_immutable_data_record():
    assert dataclasses.is_dataclass(Fact)
    assert Fact.__slots__
    component_types = {
        Scope,
        FactStatus,
        ConfidenceSource,
        Provenance,
        Freshness,
        MachineIdentity,
    }
    assert set(Fact.__annotations__.values()) == component_types


def test_f10_provenance_is_mandatory_on_fact():
    partial = {
        "scope": Scope(
            subject=Subject(name="systemd"),
            property=Property(name="running-state"),
            value=Value(value="running"),
        ),
        "status": FactStatus.OBSERVED,
        "confidence": ConfidenceSource(name="systemctl-is-active"),
        "freshness": Freshness(state=FreshnessState.CURRENT),
        "machine_identity": MachineIdentity(),
    }
    with pytest.raises(TypeError):
        Fact(**partial)
