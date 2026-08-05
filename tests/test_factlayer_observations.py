"""Type-level conformance tests for the RawOutput and Observation records.

Transcribes RFC-0005 §2 (the Raw Output and Observation stages) and the
ratified decisions DN-15 (the Observation model is ``factlayer``-internal),
DN-18 (truncation is recorded in the Observation, never silently dropped),
and DN-21 (no timing field; provenance keeps ``collected_at``). No behavior
is tested — there is none (design review plan Commit 2).
"""

import dataclasses
from datetime import datetime

import pytest

from episky.factlayer.collect import Observation, RawOutput
from episky.schema.fact import Collector, ObservationReference


def _sample_observation(**overrides):
    defaults = {
        "raw_output": RawOutput(output="2.6.32-754.el6.x86_64"),
        "collector": Collector(name="distro", version="1"),
        "collected_at": datetime(2026, 8, 5, 12, 0, 0),
        "exit_status": 0,
    }
    defaults.update(overrides)
    return Observation(**defaults)


def test_raw_output_is_an_immutable_dataclass():
    assert dataclasses.is_dataclass(RawOutput)
    with pytest.raises(dataclasses.FrozenInstanceError):
        RawOutput(output="a").output = "b"


def test_observation_is_an_immutable_dataclass():
    assert dataclasses.is_dataclass(Observation)
    with pytest.raises(dataclasses.FrozenInstanceError):
        _sample_observation().exit_status = 1


def test_raw_output_carries_the_raw_utterance_only():
    assert {f.name for f in dataclasses.fields(RawOutput)} == {"output"}


def test_observation_is_the_run_record():
    assert {f.name for f in dataclasses.fields(Observation)} == {
        "raw_output",
        "collector",
        "collected_at",
        "exit_status",
        "truncated",
    }


def test_no_timing_field_on_either_record():
    names = {f.name for f in dataclasses.fields(RawOutput)}
    names |= {f.name for f in dataclasses.fields(Observation)}
    assert "timing" not in names
    assert "duration" not in names
    assert "collected_at" in names


def test_observation_carries_the_schema_collector_identity():
    observation = _sample_observation()
    assert isinstance(observation.collector, Collector)


def test_observation_carries_a_datetime_and_exit_status():
    observation = _sample_observation()
    assert isinstance(observation.collected_at, datetime)
    assert isinstance(observation.exit_status, int)


def test_truncation_marker_mechanism_only():
    untruncated = _sample_observation()
    assert untruncated.truncated is False
    truncated = _sample_observation(truncated=True)
    assert truncated.truncated is True


def test_a_failed_run_still_produces_an_observation():
    failed = _sample_observation(exit_status=1)
    assert failed.exit_status == 1
    assert failed.raw_output.output == "2.6.32-754.el6.x86_64"


def test_observation_is_factlayer_owned():
    assert Observation.__module__ == "episky.factlayer.collect"
    assert RawOutput.__module__ == "episky.factlayer.collect"


def test_observation_is_not_leaked_into_schema():
    import episky.schema.fact as fact

    assert not hasattr(fact, "Observation")
    assert ObservationReference.__module__ == "episky.schema.fact"
