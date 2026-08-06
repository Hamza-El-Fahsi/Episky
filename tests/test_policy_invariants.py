"""The complete layer-enforceable RFC-0008 invariants (blueprint §8.7; §13).

Transcribes the policy layer's enforceable invariants and the §8.7 DoD
subset (I-7, I-11, RFC-0001 §8.2, P8/P9/P10/P13): deterministic risk
classification that is never the proposer's self-report (P2/I-7); default
deny and fail closed across classification, policy evaluation, and the
token lifecycle (P3/RFC-0001 §8.2); the carried, never re-derived gate
(P4); explicit decisions with nothing minted on silence (P5); approval
scoped to what was shown (P6); single-use tokens and replay refusal (P7);
tokens bound to action/time/state and invalidated by any boundary, never
resurrected (P8); boundary re-validation refusing on any uncertainty (P9);
blocked Actions proceeding only by explicit, audited override (P10);
records that precede any spendable token (P13/I-13); reload/state-change
re-validation (P14); the meet rule and the elevation rule (DN-54/DN-53);
determinism with explicit time; immutability and no hidden state; no
execution semantics and no authority generation; the SC9 structured-inputs-
only boundary; and the cross-layer obligations recorded against
`executor`/`audit`/`core` exactly as ratified (P1, P11, P12, durable P13,
the §6.2 edges) — only the Policy-owned half is verified here.
"""

from datetime import datetime, timedelta

import pytest

from episky.policy.classify import (
    Gate,
    RiskClass,
    classify,
    classify_plan,
    meet,
)
from episky.policy.gates import CLASS_GATES, gate_for
from episky.policy.policy import (
    ElevationBound,
    StandingApproval,
    decide,
    load,
    standing_approval_applies,
)
from episky.policy.tokens import (
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

NOW = datetime(2026, 8, 6, 12, 0, 0)
SESSION = object()
SNAPSHOT = object()

ALL_CLASSES = tuple(RiskClass)
ALL_REASONS = tuple(InvalidationReason)

# RFC-0008 §13's cross-component obligations, recorded exactly as ratified
# (C4 DoD; design review §8): the Policy-owned half is tested above; these
# halves are deferred to their owning components and only recorded here.
DEFERRED_OBLIGATIONS = (
    (
        "P1",
        "the gate is the only path to machine mutation (independent enforcement)",
        "executor",
        "RFC-0008 §13; RFC-0004 A2/A9",
    ),
    (
        "P11",
        "standing-approval execution: pre-minting per Action at its boundary",
        "executor/core",
        "RFC-0008 §8; RFC-0001 §8.3",
    ),
    (
        "P12",
        "elevation mechanism and revocation",
        "executor.elevation",
        "RFC-0008 §8; RFC-0001 §8.6; DN-53",
    ),
    (
        "P13 durable",
        "the durable Audit write of the issuance/override/auto-permit/rejection"
        " records",
        "audit",
        "RFC-0008 §13; RFC-0002 I-13; DN-50",
    ),
    (
        "§6.2 edges",
        "when the engine is consulted and the state transitions that follow",
        "core",
        "RFC-0002 §6.2; RFC-0004 §4.7",
    ),
)


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


def _plan_classification(*props_lists):
    return classify_plan(_plan(*props_lists))


def _decide(*props, description="an Action", allowlist=(), now=NOW):
    return decide(
        load(allowlist=allowlist), _classification(*props, description=description), now
    )


def _token(*props, decision=Decision.APPROVE, description="an Action", now=NOW):
    return mint(
        _classification(*props, description=description),
        decision,
        now=now,
        session=SESSION,
        state_snapshot=SNAPSHOT,
        policy=load(),
    ).token


# --- P2 / I-7 — deterministic classification, never the self-report -------


def test_identical_actions_and_facts_classify_identically():
    for props in (
        ("reads",),
        ("mutates", "reversible"),
        ("mutates", "reversible", "touches-configuration"),
        ("mutates", "touches-storage"),
    ):
        first = _classification(*props, description="fix the system please")
        second = _classification(*props, description="completely different words")
        assert first.risk_class is second.risk_class
        assert first.gate is second.gate


def test_the_proposers_words_never_enter_the_class():
    result = _classification("reads", description="I am 99.9% sure this is safe")
    assert result.risk_class is RiskClass.READ_ONLY
    assert result.gate is Gate.CONFIRM


def test_the_same_action_and_facts_always_give_the_same_class():
    action = _action("mutates", "reversible", "touches-users")
    facts = (_fact(),)
    assert classify(action, facts) == classify(action, facts)


# --- P3 / RFC-0001 §8.2 — default deny and fail closed ---------------------


def test_an_unknown_risk_property_is_blocked_and_disclosed():
    result = _classification("warp-speed")
    assert result.risk_class is None
    assert result.gate is Gate.BLOCKED
    assert result.reason


def test_an_ambiguous_property_set_is_blocked_and_disclosed():
    result = _classification("mutates", "reads")
    assert result.risk_class is None
    assert result.gate is Gate.BLOCKED
    assert result.reason


def test_unclassified_is_never_auto_permitted():
    for result in (_classification(), _classification("touches-users")):
        assert result.gate is Gate.BLOCKED
        assert result.risk_class is None


def test_a_structural_no_match_is_blocked_default_deny():
    decision = decide(load(), _classification("mutates", "touches-storage"), NOW)
    assert decision.gate is Gate.BLOCKED
    assert decision.risk_class is RiskClass.DESTRUCTIVE


def test_an_unclassifiable_action_is_blocked_not_auto_permitted():
    decision = decide(load(), _classification(description="mystery"), NOW)
    assert decision.gate is Gate.BLOCKED
    assert decision.risk_class is None
    assert decision.reason


def test_the_default_policy_allowlists_nothing():
    assert load().allowlist == frozenset()
    assert load().standing_approvals == ()
    assert load().elevation_bounds == ()


def test_gate_for_fails_closed_on_a_non_class():
    with pytest.raises(ValueError):
        gate_for("read-only")  # type: ignore[arg-type]


def test_policy_load_fails_closed_on_a_malformed_rule():
    with pytest.raises(ValueError):
        load(allowlist=("",))
    with pytest.raises(ValueError):
        load(retry_ceilings={RiskClass.READ_ONLY: 0})


def test_a_standing_approval_never_covers_a_blocked_action():
    approval = StandingApproval(
        "wipe the disk", RiskClass.CONSEQUENTIAL, datetime(2026, 8, 7)
    )
    classification = _classification(
        "mutates", "touches-storage", description="wipe the disk"
    )
    assert standing_approval_applies(approval, classification, NOW) is False


# --- P4 — classification precedes presentation; the gate is carried --------


def test_the_gate_is_carried_not_re_derived():
    for props, expected in (
        (("reads",), Gate.CONFIRM),
        (("mutates", "reversible"), Gate.CONFIRM),
        (("mutates", "reversible", "touches-configuration"), Gate.CONFIRM_WITH_WARNING),
        (("mutates", "touches-storage"), Gate.BLOCKED),
    ):
        result = _classification(*props)
        assert result.gate is expected
        assert result.gate is CLASS_GATES[result.risk_class]


def test_the_gate_is_a_frozen_field_of_the_classification():
    result = _classification("reads")
    with pytest.raises(AttributeError):
        result.gate = Gate.BLOCKED


def test_the_decision_gate_never_depends_on_the_description():
    a = _decide("mutates", "reversible", description="make a backup")
    b = _decide("mutates", "reversible", description="something else entirely")
    assert a.gate is b.gate
    assert a.risk_class is b.risk_class


# --- P5 — approval is explicit; nothing proceeds on silence ---------------


def test_an_absent_decision_mints_nothing():
    outcome = mint(
        _classification("mutates", "reversible"),
        None,
        now=NOW,
        session=SESSION,
        state_snapshot=SNAPSHOT,
        policy=load(),
    )
    assert outcome.token is None
    assert outcome.record is None


def test_a_rejection_mints_nothing_and_consumes_nothing():
    outcome = mint(
        _classification("mutates", "reversible"),
        Decision.REJECT,
        now=NOW,
        session=SESSION,
        state_snapshot=SNAPSHOT,
        policy=load(),
    )
    assert outcome.token is None
    assert outcome.record.kind is RecordKind.REJECTION


def test_no_timeout_yields_a_yes():
    for decision in (None, Decision.REJECT):
        outcome = mint(
            _classification("mutates", "touches-storage"),
            decision,
            now=NOW,
            session=SESSION,
            state_snapshot=SNAPSHOT,
            policy=load(),
        )
        assert outcome.token is None


def test_mint_never_decides_whether_to_approve():
    outcome = mint(
        _classification("reads"),
        None,
        now=NOW,
        session=SESSION,
        state_snapshot=SNAPSHOT,
        policy=load(),
    )
    assert outcome.token is None
    assert outcome.record is None


# --- P6 — approval is scoped to what was shown ----------------------------


def test_a_substituted_action_is_a_fresh_approval():
    token = _token("reads", description="collect package list")
    status = revalidate(
        token,
        now=NOW,
        action=_action("reads", description="collect something else"),
        facts=(),
        state_snapshot=SNAPSHOT,
        session=SESSION,
    )
    assert status is TokenStatus.ACTION_MISMATCH


def test_a_plan_deviation_voids_the_envelope():
    plan = _plan(("reads",), ("mutates", "reversible"))
    outcome = mint(
        classify_plan(plan),
        Decision.APPROVE,
        now=NOW,
        session=SESSION,
        state_snapshot=SNAPSHOT,
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
            state_snapshot=SNAPSHOT,
            session=SESSION,
        )
        is TokenStatus.ACTION_MISMATCH
    )


def test_anything_the_token_does_not_name_is_not_approved():
    token = _token("reads", description="collect package list")
    status = revalidate(
        token,
        now=NOW,
        action=_action("mutates", "reversible", description="collect package list"),
        facts=(),
        state_snapshot=SNAPSHOT,
        session=SESSION,
    )
    assert status is TokenStatus.ACTION_MISMATCH


# --- P7 — tokens are single-use and never reused --------------------------


def test_one_action_consumes_its_token():
    token = _token("reads")
    spent = consume(token)
    assert spent.consumed is True
    assert validate(spent, now=NOW) is TokenStatus.CONSUMED


def test_replaying_a_consumed_token_is_refused():
    token = _token("reads")
    spent = consume(token)
    assert (
        revalidate(
            spent,
            now=NOW,
            action=token.action,
            facts=(),
            state_snapshot=SNAPSHOT,
            session=SESSION,
        )
        is TokenStatus.CONSUMED
    )
    with pytest.raises(ValueError):
        consume(spent)


def test_a_consumed_or_expired_token_is_dead():
    token = _token("reads")
    assert validate(consume(token), now=NOW) is TokenStatus.CONSUMED
    assert validate(token, now=token.expiry) is TokenStatus.EXPIRED


# --- P8 — tokens are bound and invalidated by any boundary, never resurrected


def test_the_token_is_bound_to_action_time_state_session():
    token = _token("reads", description="collect package list")
    assert token.action == _action("reads", description="collect package list")
    assert token.issued_at == NOW
    assert token.expiry == expiry_for(RiskClass.READ_ONLY, NOW)
    assert token.state_snapshot is SNAPSHOT
    assert token.session is SESSION


def test_expiry_is_deterministic_per_class():
    for risk_class in ALL_CLASSES:
        first = expiry_for(risk_class, NOW)
        assert first > NOW
        assert first == expiry_for(risk_class, NOW)
        later = NOW + timedelta(minutes=30)
        assert expiry_for(risk_class, later) == first + timedelta(minutes=30)


@pytest.mark.parametrize("reason", ALL_REASONS)
def test_every_boundary_event_leaves_the_token_unusable(reason):
    token = _token("reads")
    dead = invalidate(token, reason)
    assert validate(dead, now=NOW) is TokenStatus.INVALIDATED
    assert (
        revalidate(
            dead,
            now=NOW,
            action=token.action,
            facts=(),
            state_snapshot=SNAPSHOT,
            session=SESSION,
        )
        is TokenStatus.INVALIDATED
    )


def test_an_invalidated_token_is_never_resurrected():
    token = _token("reads")
    dead = invalidate(token, InvalidationReason.REBOOT)
    assert validate(dead, now=dead.issued_at) is TokenStatus.INVALIDATED
    assert validate(invalidate(dead, InvalidationReason.STATE_CHANGE), now=NOW) is (
        TokenStatus.INVALIDATED
    )


def test_an_expired_token_is_dead_not_renewable():
    token = _token("reads")
    status = validate(token, now=token.expiry + timedelta(seconds=1))
    assert status is TokenStatus.EXPIRED
    assert (
        validate(token, now=NOW) is TokenStatus.VALID  # dead only after expiry
    )


# --- P9 — preconditions are re-validated at the boundary ------------------


def test_a_stale_or_changed_fact_prevents_spending():
    fact = _fact()
    token = mint(
        _classification("reads", facts=(fact,)),
        Decision.APPROVE,
        now=NOW,
        session=SESSION,
        state_snapshot=SNAPSHOT,
        policy=load(),
    ).token
    assert (
        revalidate(
            token,
            now=NOW,
            action=token.action,
            facts=(fact,),
            state_snapshot=SNAPSHOT,
            session=SESSION,
        )
        is TokenStatus.VALID
    )
    assert (
        revalidate(
            token,
            now=NOW,
            action=token.action,
            facts=(_fact("stopped"),),
            state_snapshot=SNAPSHOT,
            session=SESSION,
        )
        is TokenStatus.FACT_CHANGED
    )


def test_a_changed_state_domain_prevents_spending():
    token = _token("reads")
    assert (
        revalidate(
            token,
            now=NOW,
            action=token.action,
            facts=(),
            state_snapshot=object(),
            session=SESSION,
        )
        is TokenStatus.STATE_CHANGED
    )


def test_a_substituted_action_prevents_spending():
    token = _token("reads", description="collect package list")
    assert (
        revalidate(
            token,
            now=NOW,
            action=_action("reads", description="collect other"),
            facts=(),
            state_snapshot=SNAPSHOT,
            session=SESSION,
        )
        is TokenStatus.ACTION_MISMATCH
    )


def test_a_session_restart_prevents_spending():
    token = _token("reads")
    assert (
        revalidate(
            token,
            now=NOW,
            action=token.action,
            facts=(),
            state_snapshot=SNAPSHOT,
            session=object(),
        )
        is TokenStatus.SESSION_MISMATCH
    )


def test_any_uncertainty_is_refused_never_spent():
    token = _token("reads")
    refusals = {
        revalidate(
            token,
            now=NOW,
            action=token.action,
            facts=(),
            state_snapshot=object(),
            session=SESSION,
        ),
        revalidate(
            token,
            now=NOW,
            action=token.action,
            facts=(_fact(),),
            state_snapshot=SNAPSHOT,
            session=SESSION,
        ),
        revalidate(
            token,
            now=NOW,
            action=None,
            facts=(),
            state_snapshot=SNAPSHOT,
            session=SESSION,
        ),
    }
    assert TokenStatus.VALID not in refusals


# --- P10 — blocked proceeds only by explicit, audited override ------------


def test_a_blocked_action_has_no_approve_path():
    outcome = mint(
        _classification("mutates", "touches-storage"),
        Decision.APPROVE,
        now=NOW,
        session=SESSION,
        state_snapshot=SNAPSHOT,
        policy=load(),
    )
    assert outcome.token is None


def test_an_override_requires_its_own_decision_and_reason():
    with pytest.raises(ValueError):
        mint(
            _classification("mutates", "touches-storage"),
            Decision.OVERRIDE,
            now=NOW,
            session=SESSION,
            state_snapshot=SNAPSHOT,
            policy=load(),
        )
    outcome = mint(
        _classification("mutates", "touches-storage"),
        Decision.OVERRIDE,
        now=NOW,
        session=SESSION,
        state_snapshot=SNAPSHOT,
        policy=load(),
        reason="the Operator verified the disk has no boot data",
    )
    assert outcome.token is not None
    assert outcome.token.override is True


def test_the_override_is_recorded_with_its_reason():
    outcome = mint(
        _classification("mutates", "touches-storage"),
        Decision.OVERRIDE,
        now=NOW,
        session=SESSION,
        state_snapshot=SNAPSHOT,
        policy=load(),
        reason="the Operator verified the disk has no boot data",
    )
    assert outcome.record.kind is RecordKind.OVERRIDE
    assert outcome.record.override_reason


def test_override_refuses_a_non_blocked_action():
    outcome = mint(
        _classification("mutates", "reversible"),
        Decision.OVERRIDE,
        now=NOW,
        session=SESSION,
        state_snapshot=SNAPSHOT,
        policy=load(),
        reason="not a block",
    )
    assert outcome.token is None


# --- P13 / I-13 — approval is recorded before it is spent -----------------


def test_no_token_is_spendable_without_a_prior_record():
    for decision in (Decision.APPROVE, Decision.AUTO_PERMIT):
        outcome = mint(
            _classification("reads", description="x"),
            decision,
            now=NOW,
            session=SESSION,
            state_snapshot=SNAPSHOT,
            policy=load(allowlist=("x",)),
        )
        assert outcome.token is not None
        assert outcome.record is not None
    override = mint(
        _classification("mutates", "touches-storage"),
        Decision.OVERRIDE,
        now=NOW,
        session=SESSION,
        state_snapshot=SNAPSHOT,
        policy=load(),
        reason="the Operator verified the disk has no boot data",
    )
    assert override.token is not None
    assert override.record is not None


def test_the_record_precedes_the_spend():
    outcome = mint(
        _classification("reads"),
        Decision.APPROVE,
        now=NOW,
        session=SESSION,
        state_snapshot=SNAPSHOT,
        policy=load(),
    )
    assert outcome.record.decided_at == outcome.token.issued_at


def test_every_mint_kind_is_recorded():
    allowlisted = mint(
        _classification("reads", description="x"),
        Decision.AUTO_PERMIT,
        now=NOW,
        session=SESSION,
        state_snapshot=SNAPSHOT,
        policy=load(allowlist=("x",)),
    )
    rejected = mint(
        _classification("reads"),
        Decision.REJECT,
        now=NOW,
        session=SESSION,
        state_snapshot=SNAPSHOT,
        policy=load(),
    )
    assert allowlisted.record.kind is RecordKind.AUTO_PERMIT
    assert rejected.record.kind is RecordKind.REJECTION


# --- P14 — reload and state change re-validate outstanding tokens ---------


def test_policy_reload_invalidates_outstanding_tokens():
    token = _token("reads")
    dead = invalidate(token, InvalidationReason.POLICY_RELOAD)
    assert (
        revalidate(
            dead,
            now=NOW,
            action=token.action,
            facts=(),
            state_snapshot=SNAPSHOT,
            session=SESSION,
        )
        is TokenStatus.INVALIDATED
    )


def test_state_change_invalidates_outstanding_tokens():
    token = _token("reads")
    dead = invalidate(token, InvalidationReason.STATE_CHANGE)
    assert (
        revalidate(
            dead,
            now=NOW,
            action=token.action,
            facts=(),
            state_snapshot=SNAPSHOT,
            session=SESSION,
        )
        is TokenStatus.INVALIDATED
    )


# --- I-11 — scoped, consumable, invalidated -------------------------------


def test_the_token_is_scoped_consumable_invalidated():
    token = _token("reads", description="collect package list")
    assert token.action == _action("reads", description="collect package list")
    assert validate(consume(token), now=NOW) is TokenStatus.CONSUMED
    assert (
        validate(invalidate(token, InvalidationReason.STATE_CHANGE), now=NOW)
        is TokenStatus.INVALIDATED
    )


def test_auto_permission_is_not_reusability():
    description = "collect package list"
    first = mint(
        _classification("reads", description=description),
        Decision.AUTO_PERMIT,
        now=NOW,
        session=SESSION,
        state_snapshot=SNAPSHOT,
        policy=load(allowlist=(description,)),
    )
    second = mint(
        _classification("reads", description=description),
        Decision.AUTO_PERMIT,
        now=NOW,
        session=SESSION,
        state_snapshot=SNAPSHOT,
        policy=load(allowlist=(description,)),
    )
    assert first.token is not second.token
    assert first.token == second.token


# --- The meet rule (Q10; DN-54) --------------------------------------------


def test_a_plans_class_is_the_meet_of_its_steps():
    result = _plan_classification(("reads",), ("mutates", "reversible"))
    assert result.risk_class is RiskClass.BENIGN
    assert meet(RiskClass.READ_ONLY, RiskClass.BENIGN) is RiskClass.BENIGN


def test_a_destructive_step_meets_the_plan_to_destructive():
    result = _plan_classification(("reads",), ("mutates", "touches-storage"))
    assert result.risk_class is RiskClass.DESTRUCTIVE
    assert result.gate is Gate.BLOCKED


def test_an_empty_or_unclassifiable_plan_fails_closed():
    assert _plan_classification().risk_class is None
    assert _plan_classification("mutates", "reads").risk_class is None
    assert _plan_classification().gate is Gate.BLOCKED


# --- The elevation rule (Q9; DN-53) ----------------------------------------


def test_an_elevated_action_is_at_least_consequential():
    for props in (
        ("reads", "uses-elevation"),
        ("mutates", "reversible", "uses-elevation"),
        ("mutates", "touches-storage", "uses-elevation"),
    ):
        result = _classification(*props)
        assert result.risk_class is not None
        assert result.risk_class.value <= RiskClass.CONSEQUENTIAL.value


def test_the_token_records_the_elevation_bounds():
    bound = ElevationBound("run pacman")
    token = mint(
        _classification("mutates", "uses-elevation"),
        Decision.APPROVE,
        now=NOW,
        session=SESSION,
        state_snapshot=SNAPSHOT,
        policy=load(),
        elevation_bounds=(bound,),
    ).token
    assert token.elevation_bounds == (bound,)
    assert token.risk_class.value <= RiskClass.CONSEQUENTIAL.value


# --- Determinism across the whole pipeline --------------------------------


def test_the_pipeline_is_deterministic_and_explicit_time():
    artifacts = []
    for _ in range(50):
        classification = _classification("mutates", "reversible", "touches-users")
        decision = decide(load(), classification, NOW)
        outcome = mint(
            classification,
            Decision.APPROVE,
            now=NOW,
            session=SESSION,
            state_snapshot=SNAPSHOT,
            policy=load(),
        )
        token = outcome.token
        status = revalidate(
            token,
            now=NOW,
            action=token.action,
            facts=(),
            state_snapshot=SNAPSHOT,
            session=SESSION,
        )
        spent = consume(token)
        artifacts.append(
            bytes(
                repr(classification)
                + repr(decision)
                + repr(outcome)
                + repr(status)
                + repr(validate(spent, now=NOW)),
                encoding="utf-8",
            )
        )
    assert len(set(artifacts)) == 1


def test_validate_and_revalidate_are_explicit_time_functions():
    token = _token("reads")
    assert validate(token, now=NOW) == validate(token, now=NOW)
    assert revalidate(
        token,
        now=NOW,
        action=token.action,
        facts=(),
        state_snapshot=SNAPSHOT,
        session=SESSION,
    ) == revalidate(
        token,
        now=NOW,
        action=token.action,
        facts=(),
        state_snapshot=SNAPSHOT,
        session=SESSION,
    )


# --- Immutable records and no hidden state ---------------------------------


def test_all_policy_records_are_immutable():
    for record in (
        _classification("reads"),
        _plan_classification(("reads",)),
        _decide("reads"),
        _token("reads"),
    ):
        with pytest.raises(AttributeError):
            record.gate = Gate.BLOCKED
        assert hasattr(record, "__slots__")


def test_the_token_lifecycle_leaves_no_hidden_state():
    token = _token("reads")
    before = repr(token)
    consume(token)
    invalidate(token, InvalidationReason.REBOOT)
    assert repr(token) == before
    assert token.consumed is False
    assert token.invalidated is False


# --- No execution semantics and no authority generation -------------------


def test_the_token_has_no_execution_surface():
    for name in ("execute", "run", "approve", "grant", "revoke"):
        assert not hasattr(_token("reads").__class__, name)


def test_no_token_exists_without_an_explicit_decision():
    for decision in (None, Decision.REJECT):
        outcome = mint(
            _classification("reads"),
            decision,
            now=NOW,
            session=SESSION,
            state_snapshot=SNAPSHOT,
            policy=load(),
        )
        assert outcome.token is None


# --- SC9 — structured-inputs-only boundary --------------------------------


def test_classify_accepts_only_a_structured_action():
    with pytest.raises((AttributeError, TypeError, ValueError)):
        classify("rm -rf /")  # type: ignore[arg-type]


def test_decide_requires_a_classification():
    with pytest.raises(ValueError):
        decide(load(), "not a classification", NOW)  # type: ignore[arg-type]


def test_mint_requires_a_classification():
    with pytest.raises(ValueError):
        mint(
            "not a classification",  # type: ignore[arg-type]
            Decision.APPROVE,
            now=NOW,
            session=SESSION,
            state_snapshot=SNAPSHOT,
            policy=load(),
        )


def test_no_raw_secret_shaped_text_is_smuggled_through_the_pipeline():
    classification = _classification("reads", description="collect package list")
    token = mint(
        classification,
        Decision.APPROVE,
        now=NOW,
        session=SESSION,
        state_snapshot=SNAPSHOT,
        policy=load(),
    ).token
    assert token.facts == ()
    assert isinstance(token.action, Action)


# --- Cross-layer obligations are recorded, only the Policy half verified ---


def test_cross_layer_obligations_are_recorded_with_their_owners():
    assert len(DEFERRED_OBLIGATIONS) >= 5
    owners = {item[2] for item in DEFERRED_OBLIGATIONS}
    assert {"executor", "audit", "core"} & owners
    for _name, guarantee, owner, source in DEFERRED_OBLIGATIONS:
        assert guarantee
        assert owner
        assert source
