"""Behavioral tests for the Fact store (RFC-0005 §4, §6, §7; DN-19, DN-20).

Transcribes the C6 contract: `record(FactStore, Fact) -> StoreRecord` is
the in-memory current set of Facts for one machine (RFC-0003 §2.1) —
Facts are recorded without ever being mutated (F8), a newer Fact
supersedes an older one of the same RFC-0005 §6 component identity when
it is fresher and its evidence is at least as strong, with the older
retired and its successor recorded (DN-20), the four pipeline statuses
(Observed/Unknown/Unavailable/Unsupported) are supported and never
collapsed (F11), and a rule-violating Fact is Invalid and disclosed,
never admitted (F10, F12, F16). Deterministic and pure throughout.
"""

import dataclasses
from datetime import datetime, timedelta

import pytest

from episky.factlayer.store import (
    REASON_MACHINE_MISMATCH,
    REASON_NOT_SUPERSEDING,
    REASON_PROVENANCE_LOST,
    REASON_STATUS_UNESTABLISHED,
    FactIdentity,
    FactStore,
    StoreOutcome,
    record,
)
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

MACHINE = MachineIdentity()
OTHER_MACHINE = MachineIdentity()
OBSERVATION = ObservationReference()
COLLECTED_AT = datetime(2026, 8, 5, 12, 0, 0)


def _store(machine=MACHINE):
    return FactStore(machine_identity=machine)


def _fact(
    subject="kernel",
    property="version",
    value="6.8.12-arch1-1",
    status=FactStatus.OBSERVED,
    collected_at=COLLECTED_AT,
    machine=MACHINE,
    collector_name="kernel",
    collector_version="1",
):
    return Fact(
        scope=Scope(
            subject=Subject(name=subject),
            property=Property(name=property),
            value=Value(value=value),
        ),
        status=status,
        confidence=ConfidenceSource(name=f"{collector_name}@{collector_version}"),
        provenance=Provenance(
            observation=OBSERVATION,
            collector=Collector(name=collector_name, version=collector_version),
            collected_at=collected_at,
        ),
        freshness=Freshness(state=FreshnessState.CURRENT),
        machine_identity=machine,
    )


def _identity(subject="kernel", property="version"):
    return FactIdentity(
        machine_identity=MACHINE,
        subject=Subject(name=subject),
        property=Property(name=property),
    )


def test_record_admits_a_fresh_fact_into_the_current_set():
    store = _store()
    fact = _fact()
    result = record(store, fact)
    assert result.outcome == StoreOutcome.ADMITTED
    assert result.reason == ""
    assert result.store.current[_identity()] == fact
    assert result.store.retired == {}


@pytest.mark.parametrize(
    "status",
    [
        FactStatus.OBSERVED,
        FactStatus.UNKNOWN,
        FactStatus.UNAVAILABLE,
        FactStatus.UNSUPPORTED,
    ],
)
def test_record_supports_each_pipeline_status(status):
    store = _store()
    result = record(store, _fact(status=status))
    assert result.outcome == StoreOutcome.ADMITTED
    assert result.store.current[_identity()].status is status


def test_record_never_converts_a_distinct_failure_status():
    store = _store()
    store = record(
        store, _fact(status=FactStatus.UNKNOWN, collected_at=COLLECTED_AT)
    ).store
    result = record(
        store,
        _fact(
            status=FactStatus.UNAVAILABLE,
            collected_at=COLLECTED_AT + timedelta(hours=1),
        ),
    )
    assert result.outcome == StoreOutcome.REJECTED
    assert result.reason == REASON_NOT_SUPERSEDING
    assert result.store.current[_identity()].status is FactStatus.UNKNOWN


def test_fresher_fact_of_the_same_identity_supersedes():
    store = _store()
    store = record(
        store, _fact(value="6.8.12-arch1-1", collected_at=COLLECTED_AT)
    ).store
    result = record(
        store,
        _fact(value="6.8.12-arch2-1", collected_at=COLLECTED_AT + timedelta(hours=1)),
    )
    assert result.outcome == StoreOutcome.SUPERSEDED
    assert result.retired == _fact(value="6.8.12-arch1-1", collected_at=COLLECTED_AT)
    assert result.store.current[_identity()].scope.value.value == "6.8.12-arch2-1"


def test_superseded_fact_is_retired_with_its_successor():
    store = _store()
    old = _fact(value="6.8.12-arch1-1", collected_at=COLLECTED_AT)
    store = record(store, old).store
    newer = _fact(
        value="6.8.12-arch2-1", collected_at=COLLECTED_AT + timedelta(hours=1)
    )
    result = record(store, newer)
    (retired,) = result.store.retired[_identity()]
    assert retired.fact == old
    assert retired.successor == newer
    assert retired.reason == "superseded"


def test_observed_supersedes_a_not_established_fact():
    store = _store()
    store = record(
        store, _fact(status=FactStatus.UNKNOWN, collected_at=COLLECTED_AT)
    ).store
    result = record(
        store,
        _fact(
            status=FactStatus.OBSERVED, collected_at=COLLECTED_AT + timedelta(hours=1)
        ),
    )
    assert result.outcome == StoreOutcome.SUPERSEDED
    assert result.store.current[_identity()].status is FactStatus.OBSERVED


def test_a_weaker_fact_does_not_supersede_the_current_claim():
    store = _store()
    store = record(
        store, _fact(status=FactStatus.OBSERVED, collected_at=COLLECTED_AT)
    ).store
    result = record(
        store,
        _fact(
            status=FactStatus.UNKNOWN, collected_at=COLLECTED_AT + timedelta(hours=1)
        ),
    )
    assert result.outcome == StoreOutcome.REJECTED
    assert result.reason == REASON_NOT_SUPERSEDING
    assert result.store.current[_identity()].status is FactStatus.OBSERVED


def test_an_older_fact_does_not_supersede():
    store = _store()
    store = record(
        store,
        _fact(value="6.8.12-arch2-1", collected_at=COLLECTED_AT + timedelta(hours=1)),
    ).store
    result = record(store, _fact(value="6.8.12-arch1-1", collected_at=COLLECTED_AT))
    assert result.outcome == StoreOutcome.REJECTED
    assert result.store.current[_identity()].scope.value.value == "6.8.12-arch2-1"


def test_a_fresher_same_status_failure_updates_the_known_unknown():
    store = _store()
    store = record(
        store, _fact(status=FactStatus.UNKNOWN, collected_at=COLLECTED_AT)
    ).store
    result = record(
        store,
        _fact(
            status=FactStatus.UNKNOWN, collected_at=COLLECTED_AT + timedelta(hours=2)
        ),
    )
    assert result.outcome == StoreOutcome.SUPERSEDED
    assert result.store.retired[_identity()][0].reason == "superseded"


def test_a_different_subject_is_an_independent_claim():
    store = _store()
    store = record(store, _fact(subject="kernel", property="version")).store
    result = record(
        store,
        _fact(subject="machine", property="distribution-family", value="DEBIAN"),
    )
    assert result.outcome == StoreOutcome.ADMITTED
    assert len(result.store.current) == 2
    assert result.store.retired == {}


def test_a_different_property_is_an_independent_claim():
    store = _store()
    store = record(store, _fact(property="version")).store
    result = record(store, _fact(property="running", value="running"))
    assert result.outcome == StoreOutcome.ADMITTED
    assert len(result.store.current) == 2


def test_identity_is_the_component_identity_not_the_wording():
    base = _identity()
    assert (
        FactIdentity(
            machine_identity=MACHINE,
            subject=Subject(name="kernel"),
            property=Property(name="version"),
        )
        == base
    )
    assert (
        FactIdentity(
            machine_identity=OTHER_MACHINE,
            subject=Subject(name="kernel"),
            property=Property(name="version"),
        )
        != base
    )
    assert (
        FactIdentity(
            machine_identity=MACHINE,
            subject=Subject(name="machine"),
            property=Property(name="distribution-family"),
        )
        != base
    )


def test_replacement_is_deterministic():
    def run():
        store = _store()
        store = record(store, _fact(value="v1", collected_at=COLLECTED_AT)).store
        store = record(
            store, _fact(value="v2", collected_at=COLLECTED_AT + timedelta(hours=1))
        ).store
        return record(
            store,
            _fact(
                status=FactStatus.UNKNOWN,
                collected_at=COLLECTED_AT + timedelta(hours=2),
            ),
        )

    first = run()
    second = run()
    assert first.outcome is second.outcome
    assert first.store == second.store


def test_recording_never_mutates_a_stored_fact():
    store = _store()
    original = _fact(value="6.8.12-arch1-1", collected_at=COLLECTED_AT)
    first = record(store, original)
    superseding = _fact(
        value="6.8.12-arch2-1", collected_at=COLLECTED_AT + timedelta(hours=1)
    )
    second = record(first.store, superseding)
    identity = _identity()
    assert first.store.current[identity] is original
    assert second.store.current[identity] == superseding
    assert second.retired == original
    assert original.scope.value.value == "6.8.12-arch1-1"


def test_stored_facts_are_immutable():
    store = _store()
    fact = _fact()
    result = record(store, fact)
    assert dataclasses.is_dataclass(fact)
    with pytest.raises(dataclasses.FrozenInstanceError):
        result.store.current[_identity()].status = FactStatus.UNKNOWN


def test_the_store_exposes_read_only_views():
    result = record(_store(), _fact())
    identity = _identity()
    with pytest.raises(TypeError):
        result.store.current[identity] = _fact()
    with pytest.raises(TypeError):
        result.store.retired[identity] = ()


def test_record_never_mutates_the_input_store():
    store = _store()
    result = record(store, _fact())
    assert store.current == {}
    assert store.retired == {}
    assert result.store is not store


def test_a_fact_with_lost_provenance_is_invalid_and_disclosed():
    store = _store()
    result = record(store, _fact(collector_name="", collector_version=""))
    assert result.outcome == StoreOutcome.INVALID
    assert result.reason == REASON_PROVENANCE_LOST
    assert result.store is store
    assert result.store.current == {}


def test_a_fact_for_another_machine_is_invalid_and_disclosed():
    store = _store()
    result = record(store, _fact(machine=OTHER_MACHINE))
    assert result.outcome == StoreOutcome.INVALID
    assert result.reason == REASON_MACHINE_MISMATCH
    assert result.store.current == {}


@pytest.mark.parametrize(
    "status",
    [
        FactStatus.VERIFIED,
        FactStatus.CONTRADICTED,
        FactStatus.STALE,
        FactStatus.INVALID,
    ],
)
def test_a_status_the_store_cannot_establish_fails_closed(status):
    store = _store()
    result = record(store, _fact(status=status))
    assert result.outcome == StoreOutcome.INVALID
    assert result.reason == REASON_STATUS_UNESTABLISHED
    assert result.store.current == {}


def test_an_invalid_fact_never_displaces_a_current_claim():
    store = _store()
    store = record(
        store, _fact(status=FactStatus.OBSERVED, collected_at=COLLECTED_AT)
    ).store
    result = record(
        store,
        _fact(status=FactStatus.STALE, collected_at=COLLECTED_AT + timedelta(hours=1)),
    )
    assert result.outcome == StoreOutcome.INVALID
    assert result.store.current[_identity()].status is FactStatus.OBSERVED
