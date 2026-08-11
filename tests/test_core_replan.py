"""Replanning rules conformance (RFC-0002 §2.10, §4.7, §7; RFC-0008 §11).

Behavioral tests for Iteration C4 (`core/replan.py`): when a plan
re-opens (the trigger mapping), the provenance-reuse rules (RFC-0005
§12 F14/F15; RFC-0006 §7), targeted revision versus rebuild (RFC-0002
§4.7), the fixed re-entry sequence, and that no approval ever carries
across a changed plan (I-6, I-11, I-15). The module is deterministic
and I/O-free; ``now`` and the freshness bound are caller-supplied data.
It performs no state-machine transition: every decision's ``next_phase``
is a §2.13 successor of REPLANNING (single state-machine rule; DN-86),
and the module never calls ``evolve``/``session.apply``.
"""

import ast
import pathlib
from datetime import datetime, timedelta

import pytest

from episky.core.events import EventKind
from episky.core.replan import (
    FactReuse,
    ReentryStage,
    ReplanDecision,
    ReplanTrigger,
    RevisionScope,
    approval_carries,
    reentry_sequence,
    reopen,
    reuse_fact,
    revise_scope,
    trigger_from_event,
)
from episky.core.state_machine import SECTION2_ALLOWED, State
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

REPLAN_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "core"
    / "replan.py"
)

NOW = datetime(2026, 8, 6, 12, 0)
COLLECTED_AT = NOW  # freshly collected
_MACHINE_IDENTITY = type("_MI", (), {"__slots__": ()})()


def _fact(
    status=FactStatus.OBSERVED,
    freshness=FreshnessState.CURRENT,
    collected_at=None,
):
    return Fact(
        scope=Scope(Subject("nginx"), Property("version"), Value("1.22")),
        status=status,
        confidence=ConfidenceSource(name="check-version"),
        provenance=Provenance(
            observation=ObservationReference(),
            collector=Collector(name="collect", version="1"),
            collected_at=collected_at or COLLECTED_AT,
        ),
        freshness=Freshness(state=freshness),
        machine_identity=_MACHINE_IDENTITY,
    )


ALL_TRIGGER_EVENTS = (
    EventKind.VERIFICATION_FAILED,
    EventKind.VERIFICATION_INCONCLUSIVE,
    EventKind.ACTION_FAILED,
    EventKind.PLAN_REJECTED,
    EventKind.PLAN_REFINED,
    EventKind.STATE_CHANGED_DETECTED,
    EventKind.ACTION_BLOCKED,
)


# --- when to replan (RFC-0002 §2.10; RFC-0008 §11) ------------------------


@pytest.mark.parametrize(
    ("kind", "expected"),
    [
        (EventKind.VERIFICATION_FAILED, ReplanTrigger.VERIFICATION_FAILED),
        (EventKind.VERIFICATION_INCONCLUSIVE, ReplanTrigger.VERIFICATION_INCONCLUSIVE),
        (EventKind.ACTION_FAILED, ReplanTrigger.ACTION_FAILED),
        (EventKind.PLAN_REJECTED, ReplanTrigger.PLAN_REJECTED),
        (EventKind.PLAN_REFINED, ReplanTrigger.PLAN_REFINED),
        (EventKind.STATE_CHANGED_DETECTED, ReplanTrigger.PRECONDITIONS_CHANGED),
        (EventKind.ACTION_BLOCKED, ReplanTrigger.BLOCKED_NOT_OVERRIDDEN),
    ],
)
def test_trigger_from_event_maps_the_replanning_events(kind, expected):
    assert trigger_from_event(kind) is expected


@pytest.mark.parametrize(
    "kind",
    [
        kind
        for kind in EventKind
        if kind not in ALL_TRIGGER_EVENTS
        and kind not in (EventKind.OP_VIEW, EventKind.ACTION_STARTED)
    ],
)
def test_trigger_from_event_is_none_for_non_replanning_events(kind):
    assert trigger_from_event(kind) is None


def test_trigger_mapping_is_total_over_the_catalog():
    mapped = {trigger_from_event(k) for k in EventKind}
    assert mapped == set(ReplanTrigger) | {None}


# --- targeted revision vs rebuild (RFC-0002 §4.7) -------------------------


def test_revise_scope_is_targeted_by_default():
    assert revise_scope(ReplanTrigger.VERIFICATION_FAILED) is RevisionScope.TARGETED


def test_revise_scope_rebuilds_when_hypothesis_is_undermined():
    assert (
        revise_scope(ReplanTrigger.VERIFICATION_FAILED, hypothesis_undermined=True)
        is RevisionScope.REBUILD
    )


def test_revise_scope_rebuilds_when_preconditions_changed():
    assert (
        revise_scope(ReplanTrigger.ACTION_FAILED, preconditions_changed=True)
        is RevisionScope.REBUILD
    )


def test_revise_scope_rebuild_is_trigger_independent():
    for trigger in ReplanTrigger:
        assert (
            revise_scope(trigger, hypothesis_undermined=True) is RevisionScope.REBUILD
        )


# --- provenance-reuse rules (F14, F15; RFC-0006 §7) -----------------------


@pytest.mark.parametrize(
    "status",
    [FactStatus.OBSERVED, FactStatus.VERIFIED],
)
def test_reuse_fact_reuses_observed_or_verified_current_facts(status):
    assert reuse_fact(_fact(status=status), now=NOW) is FactReuse.REUSE


@pytest.mark.parametrize(
    "status",
    [
        FactStatus.UNKNOWN,
        FactStatus.UNAVAILABLE,
        FactStatus.UNSUPPORTED,
        FactStatus.CONTRADICTED,
        FactStatus.STALE,
        FactStatus.INVALID,
    ],
)
def test_reuse_fact_recollects_non_evidence_statuses(status):
    assert reuse_fact(_fact(status=status), now=NOW) is FactReuse.RECOLLECT


@pytest.mark.parametrize(
    "freshness",
    [
        FreshnessState.POSSIBLY_STALE,
        FreshnessState.STALE,
        FreshnessState.EXPIRED,
        FreshnessState.UNKNOWN_FRESHNESS,
    ],
)
def test_reuse_fact_recollects_anything_not_current(freshness):
    assert reuse_fact(_fact(freshness=freshness), now=NOW) is FactReuse.RECOLLECT


def test_reuse_fact_uses_the_caller_supplied_time_and_bound():
    old = _fact(collected_at=datetime(2020, 1, 1))
    assert reuse_fact(old, now=NOW) is FactReuse.RECOLLECT
    assert (
        reuse_fact(
            _fact(collected_at=NOW),
            now=NOW,
            bound=timedelta(hours=1),
        )
        is FactReuse.REUSE
    )


def test_reuse_is_decided_not_automatic():
    assert reuse_fact(_fact(status=FactStatus.UNKNOWN), now=NOW) is FactReuse.RECOLLECT
    assert (
        reuse_fact(_fact(freshness=FreshnessState.STALE), now=NOW)
        is FactReuse.RECOLLECT
    )


# --- no carried approval (I-6, I-11, I-15) --------------------------------


def test_approval_never_carries_across_a_revision():
    assert approval_carries() is False
    assert approval_carries(RevisionScope.TARGETED) is False
    assert approval_carries(RevisionScope.REBUILD) is False


def test_reopen_always_clears_approval():
    decision = reopen(
        ReplanTrigger.VERIFICATION_FAILED,
        (_fact(),),
        now=NOW,
    )
    assert decision.approval_cleared is True


# --- re-entry order (RFC-0002 §4.7) ---------------------------------------


def test_reentry_sequence_is_normalize_classify_present():
    assert reentry_sequence() == (
        ReentryStage.RE_NORMALIZE,
        ReentryStage.RE_CLASSIFY,
        ReentryStage.RE_PRESENT,
    )


# --- the decision (RFC-0002 §2.10, §4.7) ----------------------------------


def test_reopen_partitions_facts_into_reuse_and_recollect():
    good = _fact()
    stale = _fact(freshness=FreshnessState.STALE)
    contradicted = _fact(status=FactStatus.CONTRADICTED)
    decision = reopen(
        ReplanTrigger.ACTION_FAILED,
        (good, stale, contradicted),
        now=NOW,
    )
    assert decision.reuse == (good,)
    assert set(decision.recollect) == {stale, contradicted}


def test_reopen_rebuild_reenters_diagnosis_when_hypothesis_is_undermined():
    decision = reopen(
        ReplanTrigger.VERIFICATION_FAILED,
        (_fact(),),
        now=NOW,
        hypothesis_undermined=True,
    )
    assert decision.scope is RevisionScope.REBUILD
    assert decision.next_phase is State.DIAGNOSING


def test_reopen_rebuild_reenters_diagnosis_when_preconditions_changed():
    decision = reopen(
        ReplanTrigger.ACTION_FAILED,
        (_fact(),),
        now=NOW,
        preconditions_changed=True,
    )
    assert decision.scope is RevisionScope.REBUILD
    assert decision.next_phase is State.DIAGNOSING


def test_reopen_targeted_revision_reenters_planning():
    decision = reopen(
        ReplanTrigger.VERIFICATION_FAILED,
        (_fact(),),
        now=NOW,
    )
    assert decision.scope is RevisionScope.TARGETED
    assert decision.next_phase is State.PLANNING


@pytest.mark.parametrize(
    "trigger",
    [ReplanTrigger.PLAN_REJECTED, ReplanTrigger.BLOCKED_NOT_OVERRIDDEN],
)
def test_reopen_operator_gated_triggers_await_input(trigger):
    decision = reopen(trigger, (_fact(),), now=NOW)
    assert decision.next_phase is State.AWAITING_INPUT


@pytest.mark.parametrize("trigger", list(ReplanTrigger))
@pytest.mark.parametrize(
    "undermined",
    [False, True],
)
def test_reopen_next_phase_is_always_a_replanning_successor(trigger, undermined):
    """Single state-machine rule (DN-86): every decision is reachable."""
    decision = reopen(
        trigger,
        (_fact(),),
        now=NOW,
        hypothesis_undermined=undermined,
    )
    assert decision.next_phase in SECTION2_ALLOWED[State.REPLANNING]


def test_reopen_is_deterministic_and_immutable():
    facts = (
        _fact(),
        _fact(status=FactStatus.CONTRADICTED),
        _fact(freshness=FreshnessState.STALE),
    )
    first = reopen(ReplanTrigger.ACTION_FAILED, facts, now=NOW)
    second = reopen(ReplanTrigger.ACTION_FAILED, facts, now=NOW)
    assert first == second
    assert isinstance(first, ReplanDecision)


# --- structural: no state-machine transitions from this module ------------


def test_replan_module_never_performs_a_transition():
    src = REPLAN_PATH.read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module
            and "session" in node.module
        ):
            pytest.fail("replan.py must not import the session")
        if isinstance(node, ast.Call):
            func = node.func
            if getattr(func, "id", None) == "evolve":
                pytest.fail("replan.py must not call state_machine.evolve")
            if isinstance(func, ast.Attribute) and func.attr in {"apply", "evolve"}:
                pytest.fail("replan.py must not call session.apply / evolve")
