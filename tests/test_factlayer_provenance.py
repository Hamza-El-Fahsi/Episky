"""Behavioral tests for provenance and freshness (RFC-0005 §5, §12; F10, F14, F15).

Transcribes the C5 contract: provenance answers the five questions —
where (the Observation the Fact was normalized from), who (the exact
Collector identity), when (the collection timestamp), how, and how it is
reproduced — and is attached at normalization, never later (F10; DN-23).
Freshness bookkeeping computes the RFC-0005 §12 state deterministically
from the collected timestamp, the evaluation time, and the bound, with no
clock, timer, or runtime state; unknown freshness is never treated as
current (F15) and a stale Fact must be re-collected (F14). Bound values
are RFC-0020 policy (DN-14); these tests use the placeholder default.
"""

import dataclasses
from datetime import datetime, timedelta

import pytest

from episky.factlayer.collect import Observation, RawOutput
from episky.factlayer.normalize import normalize
from episky.factlayer.provenance import (
    DEFAULT_FRESHNESS_BOUND,
    build_provenance,
    freshness_state,
)
from episky.schema.fact import (
    Collector,
    FactStatus,
    FreshnessState,
    Provenance,
)
from episky.systemmodel.profiles import FAMILY_PROFILES, DistributionFamily

COLLECTED_AT = datetime(2026, 8, 5, 12, 0, 0)
DEBIAN = FAMILY_PROFILES[DistributionFamily.DEBIAN]


def _observation(collector_name="kernel", output="6.8.12-arch1-1", exit_status=0):
    return Observation(
        raw_output=RawOutput(output=output),
        collector=Collector(name=collector_name, version="1"),
        collected_at=COLLECTED_AT,
        exit_status=exit_status,
    )


def test_build_provenance_names_the_observation():
    provenance = build_provenance(_observation())
    assert isinstance(provenance, Provenance)
    assert provenance.observation is not None


def test_build_provenance_records_the_collector_identity():
    provenance = build_provenance(_observation())
    assert isinstance(provenance.collector, Collector)
    assert provenance.collector.name == "kernel"
    assert provenance.collector.version == "1"


def test_build_provenance_records_the_collection_timestamp():
    provenance = build_provenance(_observation())
    assert provenance.collected_at == COLLECTED_AT


def test_build_provenance_answers_the_five_questions():
    observation = _observation()
    provenance = build_provenance(observation)
    assert provenance.observation is not None
    assert provenance.collector == observation.collector
    assert provenance.collected_at == observation.collected_at
    assert provenance.re_collected_at == ()


def test_build_provenance_is_deterministic():
    assert build_provenance(_observation()) == build_provenance(_observation())


def test_build_provenance_returns_an_immutable_record():
    provenance = build_provenance(_observation())
    assert dataclasses.is_dataclass(provenance)
    with pytest.raises(dataclasses.FrozenInstanceError):
        provenance.collected_at = datetime(2026, 1, 1)


def test_freshness_current_within_the_bound():
    state = freshness_state(COLLECTED_AT, COLLECTED_AT)
    assert state == FreshnessState.CURRENT


def test_freshness_possibly_stale_near_the_bound():
    near_bound = COLLECTED_AT + DEFAULT_FRESHNESS_BOUND * 0.8
    state = freshness_state(COLLECTED_AT, near_bound)
    assert state == FreshnessState.POSSIBLY_STALE


def test_freshness_stale_past_the_bound():
    past_bound = COLLECTED_AT + DEFAULT_FRESHNESS_BOUND + timedelta(seconds=1)
    state = freshness_state(COLLECTED_AT, past_bound)
    assert state == FreshnessState.STALE


def test_freshness_stale_at_the_bound():
    at_bound = COLLECTED_AT + DEFAULT_FRESHNESS_BOUND
    state = freshness_state(COLLECTED_AT, at_bound)
    assert state == FreshnessState.STALE


def test_freshness_unknown_when_the_bound_cannot_be_computed():
    state = freshness_state(COLLECTED_AT, COLLECTED_AT, bound=None)
    assert state == FreshnessState.UNKNOWN_FRESHNESS


def test_freshness_unknown_when_the_timing_is_inconsistent():
    state = freshness_state(COLLECTED_AT, COLLECTED_AT - timedelta(seconds=1))
    assert state == FreshnessState.UNKNOWN_FRESHNESS


def test_unknown_freshness_is_never_current():
    assert freshness_state(COLLECTED_AT, COLLECTED_AT, bound=None) != (
        FreshnessState.CURRENT
    )
    assert (
        freshness_state(COLLECTED_AT, COLLECTED_AT - timedelta(seconds=1))
        != FreshnessState.CURRENT
    )


def test_freshness_is_deterministic():
    now = COLLECTED_AT + timedelta(hours=12)
    assert freshness_state(COLLECTED_AT, now) == freshness_state(COLLECTED_AT, now)


def test_normalize_attaches_the_provenance_built_from_the_observation():
    observation = _observation()
    fact = normalize(observation, DEBIAN)
    assert fact.provenance == build_provenance(observation)


def test_normalize_preserves_provenance_on_unknown_facts():
    observation = _observation(exit_status=1)
    fact = normalize(observation, DEBIAN)
    assert fact.status == FactStatus.UNKNOWN
    assert fact.provenance == build_provenance(observation)
