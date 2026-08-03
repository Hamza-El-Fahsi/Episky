"""Type-level conformance tests for the RFC-0005 §4/§12 type surface.

Transcribes the F11 structural distinctions (RFC-0005 §13) and the
freshness-state enumeration (§12) as type-level assertions: members are
distinct, never silently converted or collapsed, and the surface is a
pure, behavior-free type declaration. No behavior is tested — there is
none yet (blueprint §8.2: type-level invariant conformance tests only).
"""

import pytest

from episky.schema.fact import FactStatus, Freshness, FreshnessState


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
