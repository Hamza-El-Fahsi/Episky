"""Verification V-invariants (RFC-0006 §13; design review §10 C3, §12).

Behavioral conformance of the Compare→Outcome pipeline against the
ratified invariants that live in this layer: V3 determinism, V4 the
freshness gate (DN-32), V5 Verified Success only on fresh matching
Facts, V6 Partially Successful as a distinct outcome, V7 contradiction
always wins (DN-33), V8 verification never mutates the store (DN-27),
V9 missing evidence is never success (DN-26), V10 Postconditions fixed
before Compare, V11 every outcome carries its determining evidence
(DN-34), V14 never silently skips / fail closed, and V15 no confidence
generation (DN-30).
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
from episky.verification.compare import PostconditionVerdict, compare
from episky.verification.outcome import OutcomeRecord, determine

COLLECTED_AT = datetime(2026, 8, 5, 12, 0, tzinfo=UTC)
_MACHINE_IDENTITY = type("_MI", (), {"__slots__": ()})()

# Every freshness state that must be excluded as evidence (V4; F14/F15).
NON_CURRENT_FRESHNESS = (
    FreshnessState.POSSIBLY_STALE,
    FreshnessState.STALE,
    FreshnessState.EXPIRED,
    FreshnessState.UNKNOWN_FRESHNESS,
)


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


def _compare(facts, postconditions):
    return compare(facts, postconditions)


def _determine(facts, postconditions):
    return determine(_compare(facts, postconditions))


# --- V3 — determinism ------------------------------------------------------


def test_v3_compare_is_deterministic_across_input_order():
    facts = [
        _fact("nginx", "version", "1.22"),
        _fact("nginx", "version", "1.24"),
        _fact("systemd", "unit", "enabled"),
    ]
    postconditions = [
        _postcondition("nginx", "version", "1.24"),
        _postcondition("systemd", "unit", "running"),
    ]
    first = _compare(facts, postconditions)
    second = _compare(list(reversed(facts)), postconditions)
    assert [r.verdict for r in first.results] == [r.verdict for r in second.results]
    assert first.results[0].evidence == second.results[0].evidence


def test_v3_outcome_is_deterministic_across_input_order():
    facts = [
        _fact("nginx", "version", "1.22"),
        _fact("nginx", "version", "1.24"),
        _fact("systemd", "unit", "enabled"),
    ]
    postconditions = [
        _postcondition("nginx", "version", "1.24"),
        _postcondition("systemd", "unit", "running"),
    ]
    first = _determine(facts, postconditions)
    second = _determine(list(reversed(facts)), postconditions)
    assert first.outcome is second.outcome
    assert first.evidence == second.evidence


# --- V4 — freshness gate (DN-32) ------------------------------------------


@pytest.mark.parametrize("state", NON_CURRENT_FRESHNESS, ids=lambda s: s.name)
def test_v4_non_current_facts_are_excluded_as_unknown(state):
    result = _compare(
        [_fact("nginx", "version", "1.24", freshness=state)],
        [_postcondition("nginx", "version", "1.24")],
    )
    assert result.results[0].verdict is PostconditionVerdict.UNKNOWN
    assert result.results[0].evidence == ()
    assert (
        _determine(
            [_fact("nginx", "version", "1.24", freshness=state)],
            [_postcondition("nginx", "version", "1.24")],
        ).outcome
        is VerificationOutcome.UNKNOWN
    )


def test_v4_stale_facts_never_determine_the_outcome():
    stale_one = _fact("nginx", "version", "1.22", freshness=FreshnessState.STALE)
    stale_two = _fact("nginx", "version", "1.24", freshness=FreshnessState.STALE)
    result = _compare(
        [stale_one, stale_two], [_postcondition("nginx", "version", "1.24")]
    )
    assert result.results[0].verdict is PostconditionVerdict.UNKNOWN


def test_v4_stale_facts_are_excluded_when_current_evidence_exists():
    current = _fact("nginx", "version", "1.24")
    stale_conflict = _fact("nginx", "version", "1.22", freshness=FreshnessState.STALE)
    result = _compare(
        [current, stale_conflict], [_postcondition("nginx", "version", "1.24")]
    )
    assert result.results[0].verdict is PostconditionVerdict.HELD


# --- V5 — Verified Success -------------------------------------------------


def test_v5_all_postconditions_held_is_verified_success():
    facts = [
        _fact("nginx", "version", "1.24"),
        _fact("systemd", "unit", "running"),
    ]
    postconditions = [
        _postcondition("nginx", "version", "1.24"),
        _postcondition("systemd", "unit", "running"),
    ]
    record = _determine(facts, postconditions)
    assert record.outcome is VerificationOutcome.VERIFIED_SUCCESS
    assert len(record.evidence) == 2


def test_v5_success_is_never_claimed_without_fresh_facts():
    stale = _fact("nginx", "version", "1.24", freshness=FreshnessState.STALE)
    unknown = _fact("nginx", "version", "1.24", status=FactStatus.UNKNOWN)
    for facts in ([stale], [unknown], []):
        outcome = _determine(
            facts, [_postcondition("nginx", "version", "1.24")]
        ).outcome
        assert outcome is not VerificationOutcome.VERIFIED_SUCCESS


# --- V6 — Partially Successful ---------------------------------------------


def test_v6_partial_success_is_a_distinct_outcome():
    record = _determine(
        [
            _fact("nginx", "version", "1.24"),
            _fact("systemd", "unit", "enabled"),
        ],
        [
            _postcondition("nginx", "version", "1.24"),
            _postcondition("systemd", "unit", "running"),
        ],
    )
    assert record.outcome is VerificationOutcome.PARTIALLY_SUCCESSFUL
    assert record.outcome is not VerificationOutcome.VERIFIED_SUCCESS
    assert record.outcome is not VerificationOutcome.VERIFIED_FAILURE


# --- V7 — Contradiction always wins (DN-33) --------------------------------


def test_v7_conflicting_facts_resolve_to_contradicted():
    result = _compare(
        [_fact("nginx", "version", "1.22"), _fact("nginx", "version", "1.24")],
        [_postcondition("nginx", "version", "1.24")],
    )
    assert result.results[0].verdict is PostconditionVerdict.CONTRADICTED
    assert (
        _determine(
            [_fact("nginx", "version", "1.22"), _fact("nginx", "version", "1.24")],
            [_postcondition("nginx", "version", "1.24")],
        ).outcome
        is VerificationOutcome.CONTRADICTED
    )


def test_v7_contradiction_wins_over_a_matching_fact_elsewhere():
    record = _determine(
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
    assert record.outcome is VerificationOutcome.CONTRADICTED


def test_v7_a_contradicted_status_fact_is_contradicted():
    record = _determine(
        [_fact("nginx", "version", "1.24", status=FactStatus.CONTRADICTED)],
        [_postcondition("nginx", "version", "1.24")],
    )
    assert record.outcome is VerificationOutcome.CONTRADICTED


# --- V8 — verification never mutates (DN-27) -------------------------------


def test_v8_compare_and_determine_leave_inputs_unchanged():
    facts = [
        _fact("nginx", "version", "1.24"),
        _fact("systemd", "unit", "enabled"),
    ]
    postconditions = [
        _postcondition("nginx", "version", "1.24"),
        _postcondition("systemd", "unit", "running"),
    ]
    facts_before = tuple(facts)
    postconditions_before = tuple(postconditions)
    _compare(facts, postconditions)
    record = _determine(facts, postconditions)
    assert tuple(facts) == facts_before
    assert tuple(postconditions) == postconditions_before
    assert record.outcome is VerificationOutcome.PARTIALLY_SUCCESSFUL


def test_v8_outcome_record_is_immutable():
    record = _determine(
        [_fact("nginx", "version", "1.24")],
        [_postcondition("nginx", "version", "1.24")],
    )
    with pytest.raises(AttributeError):
        record.outcome = VerificationOutcome.UNKNOWN
    with pytest.raises(AttributeError):
        record.evidence = ()


# --- V9 — missing evidence is never success (DN-26) ------------------------


def test_v9_missing_evidence_is_unknown_never_success():
    record = _determine(
        [
            _fact("nginx", "version", "1.24"),
            _fact("systemd", "unit", "running", status=FactStatus.UNKNOWN),
        ],
        [
            _postcondition("nginx", "version", "1.24"),
            _postcondition("systemd", "unit", "running"),
        ],
    )
    assert record.outcome is VerificationOutcome.UNKNOWN


def test_v9_absent_expected_fact_is_unknown():
    record = _determine(
        [_fact("nginx", "version", "1.24")],
        [_postcondition("systemd", "unit", "running")],
    )
    assert record.outcome is VerificationOutcome.UNKNOWN


def test_v9_verified_failure_beats_unknown():
    record = _determine(
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


# --- V10 — Postconditions are fixed before Compare -------------------------


def test_v10_compare_reads_the_declared_postcondition():
    facts = [_fact("nginx", "version", "1.24")]
    held = _compare(facts, [_postcondition("nginx", "version", "1.24")])
    not_held = _compare(facts, [_postcondition("nginx", "version", "1.22")])
    assert held.results[0].verdict is PostconditionVerdict.HELD
    assert not_held.results[0].verdict is PostconditionVerdict.NOT_HELD


def test_v10_postconditions_are_not_mutated_by_compare():
    postcondition = _postcondition("nginx", "version", "1.24")
    before = (
        postcondition.subject,
        postcondition.property,
        postcondition.expected_value,
    )
    _compare([_fact("nginx", "version", "1.24")], [postcondition])
    assert (
        postcondition.subject,
        postcondition.property,
        postcondition.expected_value,
    ) == before


# --- V11 — every outcome carries its evidence (DN-34) ----------------------


@pytest.mark.parametrize(
    "facts,postconditions,expected",
    [
        pytest.param(
            [_fact("nginx", "version", "1.24")],
            [_postcondition("nginx", "version", "1.24")],
            VerificationOutcome.VERIFIED_SUCCESS,
            id="success",
        ),
        pytest.param(
            [_fact("nginx", "version", "1.22")],
            [_postcondition("nginx", "version", "1.24")],
            VerificationOutcome.VERIFIED_FAILURE,
            id="failure",
        ),
        pytest.param(
            [_fact("nginx", "version", "1.22"), _fact("nginx", "version", "1.24")],
            [_postcondition("nginx", "version", "1.24")],
            VerificationOutcome.CONTRADICTED,
            id="contradicted",
        ),
        pytest.param(
            [
                _fact("nginx", "version", "1.24"),
                _fact("systemd", "unit", "enabled"),
            ],
            [
                _postcondition("nginx", "version", "1.24"),
                _postcondition("systemd", "unit", "running"),
            ],
            VerificationOutcome.PARTIALLY_SUCCESSFUL,
            id="partial",
        ),
    ],
)
def test_v11_outcome_carries_determining_evidence(facts, postconditions, expected):
    record = _determine(facts, postconditions)
    assert record.outcome is expected
    assert len(record.evidence) > 0


def test_v11_unknown_outcome_carries_no_evidence():
    record = _determine([], [_postcondition("nginx", "version", "1.24")])
    assert record.outcome is VerificationOutcome.UNKNOWN
    assert record.evidence == ()


def test_v11_compare_result_carries_per_postcondition_evidence():
    result = _compare(
        [_fact("nginx", "version", "1.24")],
        [_postcondition("nginx", "version", "1.24")],
    )
    assert len(result.results[0].evidence) == 1
    assert result.results[0].evidence[0].scope.value.value == "1.24"


# --- V14 — never silently skips / fail closed ------------------------------


def test_v14_empty_comparison_fails_closed_as_unknown():
    assert _determine([_fact("nginx", "version", "1.24")], []).outcome is (
        VerificationOutcome.UNKNOWN
    )
    assert _determine([], []).outcome is VerificationOutcome.UNKNOWN


def test_v14_invalid_status_fails_closed_as_unknown():
    record = _determine(
        [_fact("nginx", "version", "1.24", status=FactStatus.INVALID)],
        [_postcondition("nginx", "version", "1.24")],
    )
    assert record.outcome is VerificationOutcome.UNKNOWN


# --- V15 — no confidence generation (DN-30) --------------------------------


def test_v15_outcome_record_carries_no_confidence():
    assert set(OutcomeRecord.__dataclass_fields__) == {"outcome", "evidence"}
    assert "confidence" not in OutcomeRecord.__dataclass_fields__


def test_v15_no_confidence_type_is_public():
    from episky.verification import compare as compare_module
    from episky.verification import outcome as outcome_module

    public = set(compare_module.__all__) | set(outcome_module.__all__)
    assert not {"confidence", "Confidence"} & public
