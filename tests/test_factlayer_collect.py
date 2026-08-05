"""Behavioral tests for the collection stage (RFC-0005 §2; RFC-0004 §4.5).

Transcribes the C3 contract: run one CollectorSpec, bound its raw output
with the truncation marker (DN-18), record the exit status and collected
timestamp, and return the immutable Observation — read-only (A4), never
mutating the machine or its inputs. A failed run still yields the
Observation (RFC-0002 §4.2). The authoritative bound value is RFC-0020
policy (DN-18); these tests use the placeholder default.
"""

import dataclasses
from datetime import datetime

import pytest

from episky.collectors.registry import COLLECTOR_SPECS
from episky.factlayer.collect import (
    DEFAULT_OUTPUT_BOUND,
    Observation,
    RawOutput,
    collect,
)
from episky.schema.fact import Collector

COLLECTED_AT = datetime(2026, 8, 5, 12, 0, 0)


def _run(spec=None, output="OK", exit_status=0, collected_at=COLLECTED_AT):
    return collect(
        spec or COLLECTOR_SPECS["distro"],
        output=output,
        exit_status=exit_status,
        collected_at=collected_at,
    )


def test_collect_successful_run_returns_an_observation():
    observation = _run(output="6.8.12-arch1-1")
    assert isinstance(observation, Observation)
    assert observation.raw_output.output == "6.8.12-arch1-1"
    assert observation.truncated is False


def test_collect_records_the_required_metadata():
    observation = _run(
        spec=COLLECTOR_SPECS["kernel"],
        output="6.8.12-arch1-1",
        exit_status=0,
        collected_at=COLLECTED_AT,
    )
    assert isinstance(observation.raw_output, RawOutput)
    assert isinstance(observation.collector, Collector)
    assert observation.collector.name == "kernel"
    assert observation.collector.version == "1"
    assert observation.collected_at == COLLECTED_AT
    assert observation.exit_status == 0


def test_collect_failure_still_returns_an_observation():
    observation = _run(output="", exit_status=1)
    assert isinstance(observation, Observation)
    assert observation.exit_status == 1
    assert observation.raw_output.output == ""


def test_collect_marks_and_bounds_output_past_the_bound():
    output = "x" * (DEFAULT_OUTPUT_BOUND + 1)
    observation = _run(output=output)
    assert observation.truncated is True
    assert observation.raw_output.output == "x" * DEFAULT_OUTPUT_BOUND


def test_collect_at_the_bound_is_not_flagged():
    output = "x" * DEFAULT_OUTPUT_BOUND
    observation = _run(output=output)
    assert observation.truncated is False
    assert observation.raw_output.output == output


def test_collect_within_the_bound_is_unchanged():
    observation = _run(output="short")
    assert observation.truncated is False
    assert observation.raw_output.output == "short"


def test_collect_returns_an_immutable_observation():
    observation = _run()
    assert dataclasses.is_dataclass(observation)
    with pytest.raises(dataclasses.FrozenInstanceError):
        observation.exit_status = 9


def test_collect_is_deterministic():
    first = _run(output="6.8.12-arch1-1")
    second = _run(output="6.8.12-arch1-1")
    assert first == second
    assert first.raw_output == second.raw_output


def test_collect_has_no_mutation_semantics():
    spec = COLLECTOR_SPECS["package-state"]
    output = "apt 2.7.14"
    observation = _run(spec=spec, output=output)
    assert spec.name == "package-state"
    assert spec.question
    assert COLLECTOR_SPECS["package-state"] is spec
    assert observation.collector.name == spec.name


def test_collect_performs_no_system_io(monkeypatch):
    def _forbidden(*args, **kwargs):
        raise AssertionError("collection must not touch the system")

    monkeypatch.setattr("builtins.open", _forbidden)
    monkeypatch.setattr("subprocess.run", _forbidden)
    observation = _run(output="read-only")
    assert observation.raw_output.output == "read-only"
