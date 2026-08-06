"""Deterministic Policy Token machinery (RFC-0008 §8, §9, §10; §13 P5–P10,
P13, P14; RFC-0002 invariant 11).

Behavioral tests for Iteration 7 Commit C3 (`policy/tokens.py`): the token
record and its deterministic lifecycle — explicit-decision mint (P5/DN-49),
allowlist-gated AUTO_PERMIT and Blocked-only OVERRIDE (P10), single-use
consumption (P7), boundary-event invalidation never resurrected (P8/I-15),
deterministic Action-identity/Fact/state/session re-validation (P6/P9/Q4),
policy-reload re-validation (P14), the in-memory issuance/override/
auto-permit/rejection records (P13/DN-50), the plan-envelope presented Step
set (Q10/DN-54), recorded elevation bounds (Q9/DN-53), deterministic per-
class expiry (P8), determinism and immutability, no hidden state, the owned
public surface, and the dependency rule (stdlib + `episky.schema` +
`episky.policy.classify`/`gates`/`policy` only; no I/O, no clocks, no
randomness, no identifiers, no execution semantics).
"""

import ast
import importlib
import pathlib
import sys
from datetime import datetime, timedelta

import pytest

from episky.policy.classify import (
    Gate,
    RiskClass,
    classify,
    classify_plan,
)
from episky.policy.policy import ElevationBound, load
from episky.policy.tokens import (
    EXPIRY_WINDOWS,
    Decision,
    InvalidationReason,
    RecordKind,
    TokenStatus,
    consume,
    expiry_for,
    invalidate,
    mint,
    revalidate,
    validate,
)
from episky.schema.action import Action, Plan, PostCondition, Step
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

TOKENS_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "policy"
    / "tokens.py"
)

# The owned public surface of tokens.py (design review §6; DN-49/50/53/54).
EXPECTED_PUBLIC_SURFACE = {
    "EXPIRY_WINDOWS",
    "Decision",
    "InvalidationReason",
    "MintOutcome",
    "RecordKind",
    "Token",
    "TokenRecord",
    "TokenStatus",
    "consume",
    "expiry_for",
    "invalidate",
    "mint",
    "revalidate",
    "validate",
}

NOW = datetime(2026, 8, 6, 12, 0, 0)

# Shared binding references: tokens minted by the ``_mint`` helper carry the
# same session and snapshot so determinism tests can compare equal outcomes.
# A test that needs a distinct reference creates one with ``_session()``.
SESSION = object()
SNAPSHOT = object()


def _fact(value="running"):
    return Fact(
        scope=Scope(
            subject=Subject(name="systemd"),
            property=Property(name="running-state"),
            value=Value(value=value),
        ),
        status=FactStatus.OBSERVED,
        confidence=ConfidenceSource(name="systemctl-is-active"),
        provenance=Provenance(
            observation=ObservationReference(),
            collector=Collector(name="systemd-state", version="1"),
            collected_at=datetime(2026, 8, 6, 11, 0, 0),
        ),
        freshness=Freshness(state=FreshnessState.CURRENT),
        machine_identity=MachineIdentity(),
    )


def _action(*props, description="an Action"):
    return Action(
        description=description,
        risk_properties=tuple(props),
        verification_criteria=(),
    )


def _postcondition():
    return PostCondition(
        subject=Subject(name="systemd"),
        property=Property(name="running-state"),
        expected_value=Value(value="running"),
        freshness=Freshness(state=FreshnessState.CURRENT),
    )


def _step(*props, description="a Step"):
    return Step(
        action=_action(*props, description=description),
        preconditions=(),
        postcondition=_postcondition(),
        verification_method="re-observe",
    )


def _plan(*props_lists):
    return Plan(steps=tuple(_step(*props) for props in props_lists))


def _classification(*props, description="an Action", facts=()):
    return classify(_action(*props, description=description), facts)


def _session():
    return object()


def _snapshot():
    return object()


# --- Enum completeness and ordering (§8, §13) ---


def test_decision_has_exactly_the_four_explicit_decisions():
    assert tuple(Decision) == (
        Decision.APPROVE,
        Decision.AUTO_PERMIT,
        Decision.OVERRIDE,
        Decision.REJECT,
    )
    assert len({d.value for d in Decision}) == 4


def test_record_kind_has_exactly_the_four_record_kinds():
    assert tuple(RecordKind) == (
        RecordKind.ISSUANCE,
        RecordKind.AUTO_PERMIT,
        RecordKind.OVERRIDE,
        RecordKind.REJECTION,
    )


def test_invalidation_reason_covers_every_boundary_event():
    assert set(InvalidationReason) == {
        InvalidationReason.STATE_CHANGE,
        InvalidationReason.INTERRUPT,
        InvalidationReason.REBOOT,
        InvalidationReason.SESSION_RESTART,
        InvalidationReason.POLICY_RELOAD,
        InvalidationReason.REVOCATION,
    }


def test_token_status_has_the_alive_and_dead_states():
    assert set(TokenStatus) == {
        TokenStatus.VALID,
        TokenStatus.CONSUMED,
        TokenStatus.EXPIRED,
        TokenStatus.INVALIDATED,
        TokenStatus.ACTION_MISMATCH,
        TokenStatus.FACT_CHANGED,
        TokenStatus.STATE_CHANGED,
        TokenStatus.SESSION_MISMATCH,
    }


# --- Deterministic per-class expiry (P8; §8; §16) ---


def test_expiry_windows_cover_exactly_the_four_classes():
    assert set(EXPIRY_WINDOWS) == set(RiskClass)
    assert len(EXPIRY_WINDOWS) == 4


def test_expiry_windows_are_positive_and_never_open_ended():
    for risk_class in RiskClass:
        assert EXPIRY_WINDOWS[risk_class] > timedelta(0)


def test_a_more_restrictive_class_never_outlives_a_less_restrictive_one():
    assert EXPIRY_WINDOWS[RiskClass.READ_ONLY] > EXPIRY_WINDOWS[RiskClass.BENIGN]
    assert EXPIRY_WINDOWS[RiskClass.BENIGN] > EXPIRY_WINDOWS[RiskClass.CONSEQUENTIAL]
    assert (
        EXPIRY_WINDOWS[RiskClass.CONSEQUENTIAL] > EXPIRY_WINDOWS[RiskClass.DESTRUCTIVE]
    )


def test_expiry_windows_is_immutable():
    with pytest.raises(TypeError):
        EXPIRY_WINDOWS[RiskClass.READ_ONLY] = timedelta(0)


def test_expiry_for_is_deterministic_per_class():
    for risk_class in RiskClass:
        assert expiry_for(risk_class, NOW) == NOW + EXPIRY_WINDOWS[risk_class]
        assert expiry_for(risk_class, NOW) == expiry_for(risk_class, NOW)


def test_expiry_for_fails_closed_on_a_non_class():
    with pytest.raises(ValueError):
        expiry_for("read-only", NOW)  # type: ignore[arg-type]


def test_expiry_derives_from_issued_at_not_a_clock():
    later = NOW + timedelta(hours=1)
    for risk_class in RiskClass:
        assert expiry_for(risk_class, later) == expiry_for(risk_class, NOW) + timedelta(
            hours=1
        )


# --- Token record: immutability, equality, binding ---


def test_token_is_frozen_and_slot_based():
    token = _mint(_classification("reads"), Decision.APPROVE).token
    with pytest.raises(AttributeError):
        token.consumed = True
    assert hasattr(token, "__slots__")


def test_token_binds_action_class_gate_time_state_session():
    action = _action("reads", description="collect package list")
    session = _session()
    snapshot = _snapshot()
    outcome = mint(
        _classification("reads", description="collect package list"),
        Decision.APPROVE,
        now=NOW,
        session=session,
        state_snapshot=snapshot,
        policy=load(),
    )
    token = outcome.token
    assert token.action == action
    assert token.risk_class is RiskClass.READ_ONLY
    assert token.gate is Gate.CONFIRM
    assert token.issued_at == NOW
    assert token.expiry == expiry_for(RiskClass.READ_ONLY, NOW)
    assert token.session is session
    assert token.state_snapshot is snapshot


def test_token_carries_the_facts_it_was_approved_against():
    fact = _fact()
    token = _mint(_classification("reads", facts=(fact,)), Decision.APPROVE).token
    assert token.facts == (fact,)


def test_token_is_equal_exactly_for_equal_inputs():
    session, snapshot = _session(), _snapshot()
    first = mint(
        _classification("reads"),
        Decision.APPROVE,
        now=NOW,
        session=session,
        state_snapshot=snapshot,
        policy=load(),
    )
    second = mint(
        _classification("reads"),
        Decision.APPROVE,
        now=NOW,
        session=session,
        state_snapshot=snapshot,
        policy=load(),
    )
    assert first == second
    assert first.token == second.token
    assert first.record == second.record


def test_token_differs_when_an_input_differs():
    session, snapshot = _session(), _snapshot()
    base = mint(
        _classification("reads"),
        Decision.APPROVE,
        now=NOW,
        session=session,
        state_snapshot=snapshot,
        policy=load(),
    )
    other_action = mint(
        _classification("reads", description="other"),
        Decision.APPROVE,
        now=NOW,
        session=session,
        state_snapshot=snapshot,
        policy=load(),
    )
    other_now = mint(
        _classification("reads"),
        Decision.APPROVE,
        now=NOW + timedelta(hours=1),
        session=session,
        state_snapshot=snapshot,
        policy=load(),
    )
    assert other_action.token != base.token
    assert other_now.token != base.token


def test_record_is_frozen_and_slot_based():
    record = _mint(_classification("reads"), Decision.REJECT).record
    with pytest.raises(AttributeError):
        record.gate = Gate.BLOCKED
    assert hasattr(record, "__slots__")


def test_mint_outcome_is_frozen_and_slot_based():
    outcome = _mint(_classification("reads"), Decision.APPROVE)
    with pytest.raises(AttributeError):
        outcome.token = None
    assert hasattr(outcome, "__slots__")


# --- mint: explicit decision, nothing on silence (P5; DN-49) ---


def _mint(
    classification,
    decision,
    *,
    now=NOW,
    steps=(),
    bounds=(),
    reason=None,
    allowlist=(),
    session=SESSION,
    snapshot=SNAPSHOT,
):
    return mint(
        classification,
        decision,
        now=now,
        session=session,
        state_snapshot=snapshot,
        policy=load(allowlist=allowlist),
        steps=steps,
        elevation_bounds=bounds,
        reason=reason,
    )


def test_absent_decision_mints_nothing_and_records_nothing():
    outcome = _mint(_classification("reads"), None)
    assert outcome.token is None
    assert outcome.record is None


def test_reject_mints_nothing_and_records_a_rejection():
    outcome = _mint(_classification("mutates", "reversible"), Decision.REJECT)
    assert outcome.token is None
    assert outcome.record is not None
    assert outcome.record.kind is RecordKind.REJECTION
    assert outcome.record.gate is Gate.CONFIRM


def test_reject_is_deterministic():
    first = _mint(_classification("reads"), Decision.REJECT)
    second = _mint(_classification("reads"), Decision.REJECT)
    assert first == second


def test_approve_mints_a_token_with_an_issuance_record():
    outcome = _mint(_classification("reads"), Decision.APPROVE)
    assert outcome.token is not None
    assert outcome.token.override is False
    assert outcome.token.consumed is False
    assert outcome.token.invalidated is False
    assert outcome.record is not None
    assert outcome.record.kind is RecordKind.ISSUANCE
    assert outcome.record.decided_at == NOW


def test_approve_mints_for_confirm_with_warning():
    outcome = _mint(
        _classification("mutates", "reversible", "touches-configuration"),
        Decision.APPROVE,
    )
    assert outcome.token is not None
    assert outcome.token.gate is Gate.CONFIRM_WITH_WARNING
    assert outcome.record.kind is RecordKind.ISSUANCE


def test_approve_refuses_a_blocked_action():
    outcome = _mint(_classification("mutates", "touches-storage"), Decision.APPROVE)
    assert outcome.token is None
    assert outcome.record is None


def test_auto_permit_mints_only_for_an_allowlisted_read_only_action():
    description = "collect package list"
    allowlisted = _mint(
        _classification("reads", description=description),
        Decision.AUTO_PERMIT,
        allowlist=(description,),
    )
    assert allowlisted.token is not None
    assert allowlisted.token.gate is Gate.AUTO_PERMITTED
    assert allowlisted.record.kind is RecordKind.AUTO_PERMIT


def test_auto_permit_refuses_without_allowlist_membership():
    outcome = _mint(_classification("reads"), Decision.AUTO_PERMIT)
    assert outcome.token is None
    assert outcome.record is None


def test_auto_permit_refuses_a_non_read_only_action_even_if_allowlisted():
    description = "make a backup"
    outcome = _mint(
        _classification("mutates", "reversible", description=description),
        Decision.AUTO_PERMIT,
        allowlist=(description,),
    )
    assert outcome.token is None
    assert outcome.record is None


def test_auto_permit_is_never_a_reusable_pass():
    description = "collect package list"
    first = _mint(
        _classification("reads", description=description),
        Decision.AUTO_PERMIT,
        allowlist=(description,),
    )
    second = _mint(
        _classification("reads", description=description),
        Decision.AUTO_PERMIT,
        allowlist=(description,),
    )
    assert first.token is not second.token
    assert first.token == second.token


def test_override_mints_only_for_a_blocked_action():
    outcome = _mint(
        _classification("mutates", "touches-storage"),
        Decision.OVERRIDE,
        reason="the Operator verified the disk has no boot data",
    )
    assert outcome.token is not None
    assert outcome.token.override is True
    assert outcome.token.gate is Gate.BLOCKED
    assert outcome.record is not None
    assert outcome.record.kind is RecordKind.OVERRIDE
    assert outcome.record.override_reason


def test_override_refuses_a_non_blocked_action():
    outcome = _mint(
        _classification("mutates", "reversible"),
        Decision.OVERRIDE,
        reason="not a block",
    )
    assert outcome.token is None
    assert outcome.record is None


def test_override_requires_an_explicit_reason():
    with pytest.raises(ValueError):
        _mint(_classification("mutates", "touches-storage"), Decision.OVERRIDE)


def test_override_reason_on_a_non_override_is_rejected():
    with pytest.raises(ValueError):
        _mint(_classification("reads"), Decision.APPROVE, reason="why?")


def test_mint_refuses_a_non_classification():
    with pytest.raises(ValueError):
        mint(
            "not a classification",
            Decision.APPROVE,  # type: ignore[arg-type]
            now=NOW,
            session=_session(),
            state_snapshot=_snapshot(),
            policy=load(),
        )


def test_mint_never_decides_on_its_own_authority():
    outcome = _mint(_classification("reads"), None)
    assert outcome.token is None
    assert outcome.record is None


# --- mint: plan envelope, presented Step set (Q10; DN-54) ---


def _plan_classification(*props_lists):
    return classify_plan(_plan(*props_lists))


def test_plan_token_carries_the_presented_step_set():
    plan = _plan(("reads",), ("mutates", "reversible"))
    outcome = mint(
        classify_plan(plan),
        Decision.APPROVE,
        now=NOW,
        session=_session(),
        state_snapshot=_snapshot(),
        policy=load(),
        steps=plan.steps,
    )
    assert outcome.token is not None
    assert outcome.token.action is None
    assert outcome.token.steps == plan.steps
    assert outcome.token.risk_class is RiskClass.BENIGN
    assert outcome.record.kind is RecordKind.ISSUANCE


def test_plan_token_requires_the_presented_step_set():
    with pytest.raises(ValueError):
        mint(
            _plan_classification(("reads",)),
            Decision.APPROVE,
            now=NOW,
            session=_session(),
            state_snapshot=_snapshot(),
            policy=load(),
        )


def test_single_action_token_never_carries_a_step_set():
    with pytest.raises(ValueError):
        _mint(_classification("reads"), Decision.APPROVE, steps=(_step("reads"),))


def test_auto_permit_never_applies_to_a_plan_envelope():
    plan = _plan(("reads",))
    outcome = mint(
        classify_plan(plan),
        Decision.AUTO_PERMIT,
        now=NOW,
        session=_session(),
        state_snapshot=_snapshot(),
        policy=load(allowlist=("a Step",)),
        steps=plan.steps,
    )
    assert outcome.token is None
    assert outcome.record is None


def test_plan_revalidation_matches_the_presented_step_set():
    plan = _plan(("reads",), ("mutates", "reversible"))
    outcome = mint(
        classify_plan(plan),
        Decision.APPROVE,
        now=NOW,
        session=_session(),
        state_snapshot=_snapshot(),
        policy=load(),
        steps=plan.steps,
    )
    token = outcome.token
    assert (
        revalidate(
            token,
            now=NOW,
            steps=plan.steps,
            facts=(),
            state_snapshot=token.state_snapshot,
            session=token.session,
        )
        is TokenStatus.VALID
    )


def test_plan_deviation_from_the_presented_step_set_is_refused():
    plan = _plan(("reads",), ("mutates", "reversible"))
    outcome = mint(
        classify_plan(plan),
        Decision.APPROVE,
        now=NOW,
        session=_session(),
        state_snapshot=_snapshot(),
        policy=load(),
        steps=plan.steps,
    )
    token = outcome.token
    substituted = _plan(("reads",), ("mutates", "touches-users"))
    assert (
        revalidate(
            token,
            now=NOW,
            steps=substituted.steps,
            facts=(),
            state_snapshot=token.state_snapshot,
            session=token.session,
        )
        is TokenStatus.ACTION_MISMATCH
    )


# --- Elevation bounds on the token (Q9; DN-53; §13 P12) ---


def test_token_records_the_elevation_bounds():
    bound = ElevationBound("run pacman")
    outcome = _mint(
        _classification("mutates", "uses-elevation"), Decision.APPROVE, bounds=(bound,)
    )
    assert outcome.token is not None
    assert outcome.token.elevation_bounds == (bound,)
    assert outcome.token.risk_class is RiskClass.CONSEQUENTIAL


def test_token_records_no_elevation_bounds_by_default():
    outcome = _mint(_classification("reads"), Decision.APPROVE)
    assert outcome.token.elevation_bounds == ()


def test_mint_refuses_a_non_elevation_bound():
    with pytest.raises(ValueError):
        _mint(_classification("reads"), Decision.APPROVE, bounds=("run pacman",))  # type: ignore[arg-type]


# --- validate: alive or dead (§8; P7/P8) ---


def test_validate_returns_valid_for_a_fresh_token():
    token = _mint(_classification("reads"), Decision.APPROVE).token
    assert validate(token, now=NOW) is TokenStatus.VALID


def test_validate_is_explicit_time_and_deterministic():
    token = _mint(_classification("reads"), Decision.APPROVE).token
    assert validate(token, now=NOW) is TokenStatus.VALID
    assert validate(token, now=token.expiry - timedelta(seconds=1)) is TokenStatus.VALID
    assert validate(token, now=token.expiry) is TokenStatus.EXPIRED
    assert validate(token, now=token.expiry + timedelta(hours=1)) is TokenStatus.EXPIRED


def test_validate_refuses_a_consumed_token():
    token = consume(_mint(_classification("reads"), Decision.APPROVE).token)
    assert validate(token, now=NOW) is TokenStatus.CONSUMED


def test_validate_refuses_an_invalidated_token():
    token = invalidate(
        _mint(_classification("reads"), Decision.APPROVE).token,
        InvalidationReason.STATE_CHANGE,
    )
    assert validate(token, now=NOW) is TokenStatus.INVALIDATED


# --- revalidate: Action identity, Facts, state, session (P6/P9/Q4; §9) ---


def test_revalidate_is_valid_when_everything_matches():
    session = _session()
    snapshot = _snapshot()
    outcome = mint(
        _classification("reads", description="collect package list"),
        Decision.APPROVE,
        now=NOW,
        session=session,
        state_snapshot=snapshot,
        policy=load(),
    )
    token = outcome.token
    assert (
        revalidate(
            token,
            now=NOW,
            action=_action("reads", description="collect package list"),
            facts=(),
            state_snapshot=snapshot,
            session=session,
        )
        is TokenStatus.VALID
    )


def test_revalidate_refuses_a_substituted_action():
    session = _session()
    snapshot = _snapshot()
    outcome = mint(
        _classification("reads", description="collect package list"),
        Decision.APPROVE,
        now=NOW,
        session=session,
        state_snapshot=snapshot,
        policy=load(),
    )
    token = outcome.token
    assert (
        revalidate(
            token,
            now=NOW,
            action=_action("reads", description="collect other"),
            facts=(),
            state_snapshot=snapshot,
            session=session,
        )
        is TokenStatus.ACTION_MISMATCH
    )


def test_revalidate_refuses_changed_facts():
    session = _session()
    snapshot = _snapshot()
    fact = _fact()
    outcome = mint(
        _classification("reads", description="collect package list", facts=(fact,)),
        Decision.APPROVE,
        now=NOW,
        session=session,
        state_snapshot=snapshot,
        policy=load(),
    )
    token = outcome.token
    assert (
        revalidate(
            token,
            now=NOW,
            action=_action("reads", description="collect package list"),
            facts=(fact,),
            state_snapshot=snapshot,
            session=session,
        )
        is TokenStatus.VALID
    )
    assert (
        revalidate(
            token,
            now=NOW,
            action=_action("reads", description="collect package list"),
            facts=(_fact("stopped"),),
            state_snapshot=snapshot,
            session=session,
        )
        is TokenStatus.FACT_CHANGED
    )


def test_revalidate_refuses_a_changed_state_snapshot():
    session = _session()
    snapshot = _snapshot()
    outcome = mint(
        _classification("reads"),
        Decision.APPROVE,
        now=NOW,
        session=session,
        state_snapshot=snapshot,
        policy=load(),
    )
    token = outcome.token
    assert (
        revalidate(
            token,
            now=NOW,
            action=_action("reads"),
            facts=(),
            state_snapshot=_snapshot(),
            session=session,
        )
        is TokenStatus.STATE_CHANGED
    )


def test_revalidate_refuses_a_different_session():
    session = _session()
    snapshot = _snapshot()
    outcome = mint(
        _classification("reads"),
        Decision.APPROVE,
        now=NOW,
        session=session,
        state_snapshot=snapshot,
        policy=load(),
    )
    token = outcome.token
    assert (
        revalidate(
            token,
            now=NOW,
            action=_action("reads"),
            facts=(),
            state_snapshot=snapshot,
            session=_session(),
        )
        is TokenStatus.SESSION_MISMATCH
    )


def test_revalidate_refuses_an_expired_token_uncertainty():
    session = _session()
    snapshot = _snapshot()
    outcome = mint(
        _classification("reads"),
        Decision.APPROVE,
        now=NOW,
        session=session,
        state_snapshot=snapshot,
        policy=load(),
    )
    token = outcome.token
    assert (
        revalidate(
            token,
            now=token.expiry + timedelta(seconds=1),
            action=_action("reads"),
            facts=(),
            state_snapshot=snapshot,
            session=session,
        )
        is TokenStatus.EXPIRED
    )


def test_revalidate_is_deterministic():
    session = _session()
    snapshot = _snapshot()
    outcome = mint(
        _classification("reads", description="collect package list"),
        Decision.APPROVE,
        now=NOW,
        session=session,
        state_snapshot=snapshot,
        policy=load(),
    )
    token = outcome.token
    kwargs = {
        "now": NOW,
        "action": _action("reads", description="collect package list"),
        "facts": (),
        "state_snapshot": snapshot,
        "session": session,
    }
    assert revalidate(token, **kwargs) == revalidate(token, **kwargs)


# --- Consumption and invalidation: single-use, never resurrected (P7/P8) ---


def test_consume_spends_the_single_use():
    original = _mint(_classification("reads"), Decision.APPROVE).token
    spent = consume(original)
    assert spent.consumed is True
    assert validate(spent, now=NOW) is TokenStatus.CONSUMED
    assert validate(original, now=NOW) is TokenStatus.VALID


def test_consume_is_replay_refused():
    original = _mint(_classification("reads"), Decision.APPROVE).token
    spent = consume(original)
    with pytest.raises(ValueError):
        consume(spent)
    assert (
        revalidate(
            spent,
            now=NOW,
            action=original.action,
            facts=(),
            state_snapshot=original.state_snapshot,
            session=original.session,
        )
        is TokenStatus.CONSUMED
    )


def test_consume_refuses_an_invalidated_token():
    token = invalidate(
        _mint(_classification("reads"), Decision.APPROVE).token,
        InvalidationReason.REBOOT,
    )
    with pytest.raises(ValueError):
        consume(token)


def test_invalidate_kills_for_every_boundary_event():
    for reason in InvalidationReason:
        token = invalidate(
            _mint(_classification("reads"), Decision.APPROVE).token, reason
        )
        assert token.invalidated is True
        assert token.invalidation_reason is reason
        assert validate(token, now=NOW) is TokenStatus.INVALIDATED
        assert (
            revalidate(
                token,
                now=NOW,
                action=token.action,
                facts=(),
                state_snapshot=token.state_snapshot,
                session=token.session,
            )
            is TokenStatus.INVALIDATED
        )


def test_invalidate_never_resurrects():
    token = _mint(_classification("reads"), Decision.APPROVE).token
    dead = invalidate(token, InvalidationReason.STATE_CHANGE)
    assert validate(dead, now=NOW) is TokenStatus.INVALIDATED
    assert validate(dead, now=dead.issued_at) is TokenStatus.INVALIDATED
    assert (
        validate(invalidate(dead, InvalidationReason.REBOOT), now=NOW)
        is TokenStatus.INVALIDATED
    )


def test_invalidate_is_idempotent_and_preserves_consumed():
    token = _mint(_classification("reads"), Decision.APPROVE).token
    dead = invalidate(token, InvalidationReason.STATE_CHANGE)
    again = invalidate(dead, InvalidationReason.REBOOT)
    assert again is dead
    assert validate(again, now=NOW) is TokenStatus.INVALIDATED


def test_invalidate_preserves_a_consumed_token():
    spent = consume(_mint(_classification("reads"), Decision.APPROVE).token)
    assert invalidate(spent, InvalidationReason.REBOOT) is spent
    assert validate(spent, now=NOW) is TokenStatus.CONSUMED


def test_invalidate_refuses_a_non_reason():
    with pytest.raises(ValueError):
        invalidate(_mint(_classification("reads"), Decision.APPROVE).token, "reboot")  # type: ignore[arg-type]


def test_lifecycle_is_pure_no_hidden_state():
    token = _mint(_classification("reads"), Decision.APPROVE).token
    before = repr(token)
    consume(token)
    invalidate(token, InvalidationReason.REBOOT)
    assert repr(token) == before
    assert token.consumed is False
    assert token.invalidated is False


# --- Policy reload and state change re-validate (P14; §13 P8) ---


def test_policy_reload_invalidation_refuses_revalidation():
    token = invalidate(
        _mint(_classification("reads"), Decision.APPROVE).token,
        InvalidationReason.POLICY_RELOAD,
    )
    assert (
        revalidate(
            token,
            now=NOW,
            action=token.action,
            facts=(),
            state_snapshot=token.state_snapshot,
            session=token.session,
        )
        is TokenStatus.INVALIDATED
    )


def test_state_change_invalidation_refuses_revalidation():
    token = invalidate(
        _mint(_classification("reads"), Decision.APPROVE).token,
        InvalidationReason.STATE_CHANGE,
    )
    assert (
        revalidate(
            token,
            now=NOW,
            action=token.action,
            facts=(),
            state_snapshot=token.state_snapshot,
            session=token.session,
        )
        is TokenStatus.INVALIDATED
    )


# --- Records precede any spendable token (P13; I-13; DN-50) ---


def test_no_token_is_minted_without_a_prior_record():
    allowlisted = _mint(
        _classification("reads", description="x"),
        Decision.AUTO_PERMIT,
        allowlist=("x",),
    )
    assert allowlisted.token is not None
    assert allowlisted.record is not None
    approved = _mint(_classification("reads"), Decision.APPROVE)
    assert approved.token is not None
    assert approved.record is not None
    overridden = _mint(
        _classification("mutates", "touches-storage"),
        Decision.OVERRIDE,
        reason="the Operator verified the disk has no boot data",
    )
    assert overridden.token is not None
    assert overridden.record is not None


def test_every_mint_outcome_kind_matches_the_decision():
    allowlisted = _mint(
        _classification("reads", description="x"),
        Decision.AUTO_PERMIT,
        allowlist=("x",),
    )
    assert allowlisted.record.kind is RecordKind.AUTO_PERMIT
    approved = _mint(_classification("reads"), Decision.APPROVE)
    assert approved.record.kind is RecordKind.ISSUANCE
    overridden = _mint(
        _classification("mutates", "touches-storage"),
        Decision.OVERRIDE,
        reason="the Operator verified the disk has no boot data",
    )
    assert overridden.record.kind is RecordKind.OVERRIDE
    rejected = _mint(_classification("reads"), Decision.REJECT)
    assert rejected.record.kind is RecordKind.REJECTION


def test_the_override_record_carries_its_explicit_reason():
    reason = "the Operator verified the disk has no boot data"
    outcome = _mint(
        _classification("mutates", "touches-storage"),
        Decision.OVERRIDE,
        reason=reason,
    )
    assert outcome.record.override_reason == reason


def test_issuance_and_auto_permit_records_carry_no_override_reason():
    approved = _mint(_classification("reads"), Decision.APPROVE)
    assert approved.record.override_reason is None
    allowlisted = _mint(
        _classification("reads", description="x"),
        Decision.AUTO_PERMIT,
        allowlist=("x",),
    )
    assert allowlisted.record.override_reason is None


# --- Determinism and repeated identical construction (§10; P2) ---


def test_mint_is_repeated_identical_construction():
    kwargs = {
        "now": NOW,
        "session": _session(),
        "state_snapshot": _snapshot(),
        "policy": load(),
    }
    first = mint(_classification("reads"), Decision.APPROVE, **kwargs)
    second = mint(_classification("reads"), Decision.APPROVE, **kwargs)
    assert first == second
    assert first.token == second.token
    assert first.record == second.record


def test_decisions_never_depend_on_hidden_state():
    first = _mint(_classification("mutates", "reversible"), Decision.APPROVE)
    for _ in range(50):
        again = _mint(_classification("mutates", "reversible"), Decision.APPROVE)
        assert again == first


# --- Public surface and ownership (blueprint §10) ---


def test_public_surface_is_exactly_the_owned_vocabulary():
    module = importlib.import_module("episky.policy.tokens")
    assert set(module.__all__) == EXPECTED_PUBLIC_SURFACE


def test_public_names_are_defined_by_tokens_py():
    module = importlib.import_module("episky.policy.tokens")
    for name in EXPECTED_PUBLIC_SURFACE:
        assert name in module.__dict__


def test_public_surface_leaks_no_private_placeholder():
    module = importlib.import_module("episky.policy.tokens")
    for name in module.__all__:
        assert not name.startswith("_")


def test_module_ownership_docstring_names_rfc_0008_and_the_guarantees():
    doc = importlib.import_module("episky.policy.tokens").__doc__
    assert "RFC-0008" in doc
    assert "deterministic" in doc.lower()
    assert "invariant 11" in doc
    assert "never" in doc


def test_the_token_surface_has_no_execution_path():
    module = importlib.import_module("episky.policy.tokens")
    for name in ("execute", "run", "approve", "grant", "revoke"):
        assert not hasattr(module.Token, name)


# --- Dependency rule: stdlib + schema + policy only; edges stay latent ---


def test_tokens_py_imports_only_stdlib_schema_and_policy():
    tree = ast.parse(TOKENS_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] in sys.stdlib_module_names
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "no relative imports"
            parts = node.module.split(".")
            if parts[0] != "episky":
                assert parts[0] in sys.stdlib_module_names
            else:
                if parts[1] == "schema":
                    continue
                assert parts[1] == "policy", "tokens.py may import only episky.policy"
                assert parts[2] in ("classify", "gates", "policy")


def test_tokens_py_keeps_the_latent_edges_latent():
    src = TOKENS_PATH.read_text(encoding="utf-8")
    for token in (
        "episky.trust",
        "episky.secrets",
        "episky.factlayer",
        "episky.verification",
        "episky.executor",
        "episky.runtime",
        "episky.audit",
        "episky.providers",
        "episky.context",
        "episky.systemmodel",
        "episky.cli",
        "episky.core",
    ):
        assert token not in src


def test_tokens_py_imports_no_io_or_persistence_stdlib():
    src = TOKENS_PATH.read_text(encoding="utf-8")
    for token in (
        "import os",
        "import pathlib",
        "import socket",
        "import urllib",
        "import random",
        "import secrets",
        "import subprocess",
        "import sqlite3",
        "import json",
        "import pickle",
        "import threading",
        "import asyncio",
        "import hashlib",
        "import uuid",
    ):
        assert token not in src


def test_tokens_py_reads_no_clock():
    src = TOKENS_PATH.read_text(encoding="utf-8")
    for token in (
        "datetime.now",
        "utcnow",
        "time.time",
        "time.monotonic",
        "perf_counter",
        "import time",
        "from time import",
    ):
        assert token not in src


def test_tokens_py_generates_no_random_or_crypto():
    src = TOKENS_PATH.read_text(encoding="utf-8")
    for token in (
        "import random",
        "random.",
        "os.urandom",
        "import uuid",
        "uuid4",
        "import hmac",
        "import hashlib",
        "import secrets",
        "secrets.token",
    ):
        assert token not in src
    assert "object" in src  # the only "identifiers" are caller-supplied refs


def test_tokens_py_calls_no_forbidden_io_builtin():
    tree = ast.parse(TOKENS_PATH.read_text(encoding="utf-8"))
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            calls.add(func.id if isinstance(func, ast.Name) else func.attr)
    assert calls.isdisjoint({"open", "print", "input", "exec", "eval", "breakpoint"})
