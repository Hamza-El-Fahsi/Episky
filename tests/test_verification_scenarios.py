"""Verification outcome precedence and scenario coverage (RFC-0006 §7, §9).

End-to-end mapping of Compare results to the RFC-0006 §7 Outcomes across
the ratified precedence — Contradicted > Verified Failure > Unknown >
Partially Successful > Verified Success (§7 rule 2) — and the design
review §10 C3 scenario set: fully satisfied, partially satisfied,
contradictory evidence, stale facts excluded, unsupported/unavailable/
unknown facts, empty comparison, multiple Postconditions, and
deterministic ordering.
"""

from datetime import UTC, datetime

import pytest

from episky.schema.action import PostCondition
from episky.schema.fact import (
    Collector,
    ConfidenceSource,
    Fact,
    FactStatus,
    Freshness,
    FreshnessState,
    ObservationReference,
    Property,
    Provenance,
    Scope,
    Subject,
    Value,
)
from episky.schema.outcome import VerificationOutcome
from episky.verification.compare import compare
from episky.verification.outcome import determine

COLLECTED_AT = datetime(2026, 8, 5, 12, 0, tzinfo=UTC)
_MACHINE_IDENTITY = type("_MI", (), {"__slots__": ()})()


def _fact(
    subject,
    prop,
    value,
    status=FactStatus.OBSERVED,
    freshness=FreshnessState.CURRENT,
):
    return Fact(
        scope=Scope(Subject(subject), Property(prop), Value(value)),
        status=status,
        confidence=ConfidenceSource(name=f"check-{prop}"),
        provenance=Provenance(
            observation=ObservationReference(),
            collector=Collector(name="collect", version="1"),
            collected_at=COLLECTED_AT,
        ),
        freshness=Freshness(state=freshness),
        machine_identity=_MACHINE_IDENTITY,
    )


def _postcondition(subject, prop, value, freshness=FreshnessState.CURRENT):
    return PostCondition(
        subject=Subject(subject),
        property=Property(prop),
        expected_value=Value(value),
        freshness=Freshness(state=freshness),
    )


def _run(facts, postconditions):
    return determine(compare(facts, postconditions))


# --- §7 rule 2 precedence, exactly as ratified -----------------------------


def test_precedence_contradicted_over_verified_failure():
    record = _run(
        [
            _fact("nginx", "version", "1.22"),
            _fact("nginx", "version", "1.24"),
            _fact("systemd", "unit", "disabled"),
        ],
        [
            _postcondition("nginx", "version", "1.24"),
            _postcondition("systemd", "unit", "running"),
        ],
    )
    assert record.outcome is VerificationOutcome.CONTRADICTED


def test_precedence_contradicted_over_unknown():
    record = _run(
        [
            _fact("nginx", "version", "1.22"),
            _fact("nginx", "version", "1.24"),
            _fact("systemd", "unit", "running", status=FactStatus.UNKNOWN),
        ],
        [
            _postcondition("nginx", "version", "1.24"),
            _postcondition("systemd", "unit", "running"),
        ],
    )
    assert record.outcome is VerificationOutcome.CONTRADICTED


def test_precedence_contradicted_over_partial_and_success():
    partial = _run(
        [
            _fact("nginx", "version", "1.24"),
            _fact("nginx", "version", "1.25"),
            _fact("systemd", "unit", "disabled"),
            _fact("apache", "running", "true"),
        ],
        [
            _postcondition("nginx", "version", "1.24"),
            _postcondition("systemd", "unit", "running"),
            _postcondition("apache", "running", "true"),
        ],
    )
    success = _run(
        [
            _fact("nginx", "version", "1.24"),
            _fact("nginx", "version", "1.25"),
            _fact("systemd", "unit", "running"),
        ],
        [
            _postcondition("nginx", "version", "1.24"),
            _postcondition("systemd", "unit", "running"),
        ],
    )
    assert partial.outcome is VerificationOutcome.CONTRADICTED
    assert success.outcome is VerificationOutcome.CONTRADICTED


def test_precedence_verified_failure_over_unknown():
    record = _run(
        [
            _fact("nginx", "version", "1.22"),
            _fact("systemd", "unit", "running", status=FactStatus.UNKNOWN),
        ],
        [
            _postcondition("nginx", "version", "1.24"),
            _postcondition("systemd", "unit", "running"),
        ],
    )
    assert record.outcome is VerificationOutcome.VERIFIED_FAILURE


def test_precedence_unknown_over_partial():
    record = _run(
        [
            _fact("nginx", "version", "1.24"),
            _fact("systemd", "unit", "disabled"),
            _fact("apache", "running", "true", status=FactStatus.UNKNOWN),
        ],
        [
            _postcondition("nginx", "version", "1.24"),
            _postcondition("systemd", "unit", "running"),
            _postcondition("apache", "running", "true"),
        ],
    )
    assert record.outcome is VerificationOutcome.UNKNOWN


def test_precedence_partial_over_success():
    partial = _run(
        [
            _fact("nginx", "version", "1.24"),
            _fact("systemd", "unit", "disabled"),
        ],
        [
            _postcondition("nginx", "version", "1.24"),
            _postcondition("systemd", "unit", "running"),
        ],
    )
    success = _run(
        [
            _fact("nginx", "version", "1.24"),
            _fact("systemd", "unit", "running"),
        ],
        [
            _postcondition("nginx", "version", "1.24"),
            _postcondition("systemd", "unit", "running"),
        ],
    )
    assert partial.outcome is VerificationOutcome.PARTIALLY_SUCCESSFUL
    assert success.outcome is VerificationOutcome.VERIFIED_SUCCESS


# --- Scenario coverage -----------------------------------------------------


def test_scenario_fully_satisfied():
    record = _run(
        [_fact("nginx", "version", "1.24")],
        [_postcondition("nginx", "version", "1.24")],
    )
    assert record.outcome is VerificationOutcome.VERIFIED_SUCCESS


def test_scenario_partially_satisfied():
    record = _run(
        [
            _fact("nginx", "version", "1.24"),
            _fact("systemd", "unit", "disabled"),
        ],
        [
            _postcondition("nginx", "version", "1.24"),
            _postcondition("systemd", "unit", "running"),
        ],
    )
    assert record.outcome is VerificationOutcome.PARTIALLY_SUCCESSFUL


def test_scenario_contradictory_evidence():
    record = _run(
        [_fact("nginx", "version", "1.22"), _fact("nginx", "version", "1.24")],
        [_postcondition("nginx", "version", "1.24")],
    )
    assert record.outcome is VerificationOutcome.CONTRADICTED


def test_scenario_stale_facts_excluded():
    record = _run(
        [_fact("nginx", "version", "1.24", freshness=FreshnessState.STALE)],
        [_postcondition("nginx", "version", "1.24")],
    )
    assert record.outcome is VerificationOutcome.UNKNOWN


@pytest.mark.parametrize(
    "status",
    (FactStatus.UNSUPPORTED, FactStatus.UNAVAILABLE, FactStatus.UNKNOWN),
    ids=lambda status: status.name,
)
def test_scenario_failed_status_facts_are_unknown(status):
    record = _run(
        [_fact("nginx", "version", "1.24", status=status)],
        [_postcondition("nginx", "version", "1.24")],
    )
    assert record.outcome is VerificationOutcome.UNKNOWN


def test_scenario_empty_comparison():
    record = _run([_fact("nginx", "version", "1.24")], [])
    assert record.outcome is VerificationOutcome.UNKNOWN


def test_scenario_multiple_postconditions_all_fail():
    record = _run(
        [
            _fact("nginx", "version", "1.22"),
            _fact("systemd", "unit", "disabled"),
            _fact("apache", "running", "false"),
        ],
        [
            _postcondition("nginx", "version", "1.24"),
            _postcondition("systemd", "unit", "running"),
            _postcondition("apache", "running", "true"),
        ],
    )
    assert record.outcome is VerificationOutcome.VERIFIED_FAILURE


def test_scenario_multiple_postconditions_partly_fail():
    record = _run(
        [
            _fact("nginx", "version", "1.24"),
            _fact("systemd", "unit", "disabled"),
            _fact("apache", "running", "false"),
        ],
        [
            _postcondition("nginx", "version", "1.24"),
            _postcondition("systemd", "unit", "running"),
            _postcondition("apache", "running", "true"),
        ],
    )
    assert record.outcome is VerificationOutcome.PARTIALLY_SUCCESSFUL


def test_scenario_deterministic_ordering():
    facts = [
        _fact("nginx", "version", "1.22"),
        _fact("nginx", "version", "1.24"),
        _fact("systemd", "unit", "disabled"),
    ]
    postconditions = [
        _postcondition("nginx", "version", "1.24"),
        _postcondition("systemd", "unit", "running"),
    ]
    forward = _run(facts, postconditions)
    reversed_input = _run(list(reversed(facts)), postconditions)
    assert forward.outcome is reversed_input.outcome
    assert forward.evidence == reversed_input.evidence
