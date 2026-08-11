"""Recovery rules conformance (RFC-0002 §8, §10; RFC-0008 §11, §15).

Behavioral tests for Iteration C4 (`core/recovery.py`): the fixed
recovery order — determinism → disclosure → decision → action (DN-90) —
and the decisions for provider failure (the bounded pure reducer, Q6 /
DN-90), action failure, collector failure, policy failure, partial
execution, and interruption. Every function is deterministic and
I/O-free: budgets, backoff schedules, and fallback chains are
caller-supplied data (RFC-0020 content), and backoff delays are data,
never a clock. The module performs no state-machine transition and
never invents what it cannot establish (I-8, I-9).
"""

import ast
import pathlib
from datetime import timedelta

import pytest

from episky.core.recovery import (
    ActionFailureKind,
    ActionRecovery,
    CollectorFailureKind,
    CollectorRecovery,
    InterruptRecovery,
    PartialRecovery,
    PolicyFailureKind,
    PolicyRecovery,
    ProviderFailureKind,
    ProviderReaction,
    ProviderRecoveryState,
    RecoveryStep,
    backoff_delay,
    decide_provider_reaction,
    on_action_failure,
    on_collector_failure,
    on_interrupt,
    on_partial,
    on_policy_failure,
    on_provider_failure,
    recover,
    recovery_order,
    reduce_provider_failure,
)

RECOVERY_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "core"
    / "recovery.py"
)

BACKOFF = (timedelta(seconds=1), timedelta(seconds=4), timedelta(seconds=10))
FALLBACKS = ("fallback-a", "fallback-b")


def _state(**overrides):
    base = {
        "retry_budget": 2,
        "backoff": BACKOFF,
        "fallback_chain": FALLBACKS,
        "degraded_allowed": True,
    }
    base.update(overrides)
    return ProviderRecoveryState(**base)


# --- the recovery order (RFC-0002 §8; DN-90) ------------------------------


def test_recovery_order_is_fixed_and_in_order():
    assert recovery_order() == (
        RecoveryStep.DETERMINISM,
        RecoveryStep.DISCLOSURE,
        RecoveryStep.DECISION,
        RecoveryStep.ACTION,
    )


def test_recover_applies_the_fixed_order_to_any_decision():
    decisions = [
        on_provider_failure(
            (ProviderFailureKind.TIMEOUT,),
            retry_budget=1,
            backoff=BACKOFF,
            fallback_chain=(),
            degraded_allowed=True,
        ),
        on_action_failure(ActionFailureKind.STEP_FAILED, executor_healthy=True),
        on_collector_failure(CollectorFailureKind.CRITICAL),
        on_policy_failure(PolicyFailureKind.TOKEN_INVALID),
        on_partial(("a", "b"), ("c",)),
        on_interrupt(machine_touching=True),
    ]
    for decision in decisions:
        assert recover(decision) == recovery_order()


# --- provider failure: the bounded pure reducer (Q6; DN-90) ---------------


def test_provider_transient_within_budget_retries_with_scheduled_delay():
    decision = on_provider_failure(
        (ProviderFailureKind.TIMEOUT,),
        retry_budget=2,
        backoff=BACKOFF,
        fallback_chain=FALLBACKS,
        degraded_allowed=True,
    )
    assert decision.reaction is ProviderReaction.RETRY
    assert decision.delay == BACKOFF[0]
    assert decision.state.retries_used == 1
    assert decision.state.current_index == 0


def test_provider_retry_consumes_the_next_backoff_slot():
    state = reduce_provider_failure(
        reduce_provider_failure(_state(), ProviderFailureKind.TIMEOUT),
        ProviderFailureKind.TIMEOUT,
    )
    assert state.retries_used == 2
    assert state.retries_used <= state.retry_budget
    assert decide_provider_reaction(state) is ProviderReaction.RETRY
    assert backoff_delay(state) == BACKOFF[1]


def test_provider_budget_exhausted_falls_back_to_the_next_provider():
    events = (
        ProviderFailureKind.TIMEOUT,
        ProviderFailureKind.TIMEOUT,
        ProviderFailureKind.TIMEOUT,
    )
    decision = on_provider_failure(
        events,
        retry_budget=2,
        backoff=BACKOFF,
        fallback_chain=FALLBACKS,
        degraded_allowed=True,
    )
    assert decision.reaction is ProviderReaction.FALLBACK
    assert decision.fallback == "fallback-a"
    assert decision.state.current_index == 1


def test_provider_refusal_is_never_auto_retried():
    decision = on_provider_failure(
        (ProviderFailureKind.REFUSAL,),
        retry_budget=2,
        backoff=BACKOFF,
        fallback_chain=FALLBACKS,
        degraded_allowed=True,
    )
    assert decision.reaction is ProviderReaction.FALLBACK
    assert decision.fallback == "fallback-a"
    assert decision.state.retries_used == 0


def test_provider_refusal_then_timeout_retries_the_fallback():
    decision = on_provider_failure(
        (ProviderFailureKind.REFUSAL, ProviderFailureKind.TIMEOUT),
        retry_budget=2,
        backoff=BACKOFF,
        fallback_chain=FALLBACKS,
        degraded_allowed=True,
    )
    assert decision.reaction is ProviderReaction.RETRY
    assert decision.state.current_index == 1


def test_provider_all_fallbacks_gone_degrades_with_disclosure():
    decision = on_provider_failure(
        (ProviderFailureKind.TIMEOUT,) * 7,
        retry_budget=1,
        backoff=BACKOFF,
        fallback_chain=FALLBACKS,
        degraded_allowed=True,
    )
    assert decision.state.degraded is True
    assert decision.reaction is ProviderReaction.DEGRADE
    assert decision.disclosures and "degraded mode" in decision.disclosures[0]


def test_provider_degrade_forbidden_halts_and_still_discloses():
    decision = on_provider_failure(
        (ProviderFailureKind.TIMEOUT,) * 7,
        retry_budget=1,
        backoff=BACKOFF,
        fallback_chain=FALLBACKS,
        degraded_allowed=False,
    )
    assert decision.state.halted is True
    assert decision.reaction is ProviderReaction.DEGRADE
    assert any("not permitted" in line for line in decision.disclosures)


def test_provider_reducer_is_bounded_over_arbitrary_failure_sequences():
    state = _state()
    kinds = list(ProviderFailureKind)
    for _ in range(200):
        state = reduce_provider_failure(state, kinds[_ % len(kinds)])
        assert state.retries_used <= state.retry_budget
        assert state.current_index <= len(FALLBACKS)
        if state.terminal:
            break
    assert state.terminal


def test_provider_recovery_is_deterministic():
    events = (
        ProviderFailureKind.TIMEOUT,
        ProviderFailureKind.REFUSAL,
        ProviderFailureKind.UNAVAILABLE,
    )
    kwargs = {
        "retry_budget": 3,
        "backoff": BACKOFF,
        "fallback_chain": FALLBACKS,
        "degraded_allowed": True,
    }
    first = on_provider_failure(events, **kwargs)
    second = on_provider_failure(events, **kwargs)
    assert first == second


def test_backoff_delay_is_data_not_a_clock():
    state = reduce_provider_failure(_state(), ProviderFailureKind.TIMEOUT)
    assert backoff_delay(state) == timedelta(seconds=1)
    moved = reduce_provider_failure(_state(), ProviderFailureKind.REFUSAL)
    assert backoff_delay(moved) is None


# --- action failure (RFC-0008 §11; I-8) -----------------------------------


def test_action_step_failed_with_healthy_executor_verifies_then_replans():
    decision = on_action_failure(ActionFailureKind.STEP_FAILED, executor_healthy=True)
    assert decision.recovery is ActionRecovery.VERIFY_THEN_REPLAN


def test_action_ambiguous_halt_interrupts():
    for kind in (ActionFailureKind.STEP_TIMEOUT, ActionFailureKind.STEP_PARTIAL):
        decision = on_action_failure(kind, executor_healthy=True)
        assert decision.recovery is ActionRecovery.HALT_INTERRUPTED
        assert any("state uncertain" in line for line in decision.disclosures)


def test_action_executor_unhealthy_fails_closed():
    decision = on_action_failure(ActionFailureKind.STEP_FAILED, executor_healthy=False)
    assert decision.recovery is ActionRecovery.HALT_INTERRUPTED
    assert any("fail closed" in line for line in decision.disclosures)


# --- collector failure (RFC-0002 §4.2; RFC-0006 §6) -----------------------


def test_collector_non_critical_carries_unknown_with_provenance():
    decision = on_collector_failure(CollectorFailureKind.NON_CRITICAL)
    assert decision.recovery is CollectorRecovery.FACT_UNKNOWN


def test_collector_critical_discloses_and_asks():
    decision = on_collector_failure(CollectorFailureKind.CRITICAL)
    assert decision.recovery is CollectorRecovery.DISCLOSE_AND_ASK


def test_collector_hopeless_fails():
    decision = on_collector_failure(CollectorFailureKind.HOPELESS)
    assert decision.recovery is CollectorRecovery.FAIL


# --- policy failure (RFC-0008 §8, §10, §15; RFC-0013 §21) ----------------


def test_policy_invalid_token_reopens_and_represents():
    decision = on_policy_failure(PolicyFailureKind.TOKEN_INVALID)
    assert decision.recovery is PolicyRecovery.RE_OPEN_AND_RE_PRESENT
    assert any("never reused" in line for line in decision.disclosures)


def test_policy_blocked_discloses_and_asks():
    decision = on_policy_failure(PolicyFailureKind.PLAN_BLOCKED)
    assert decision.recovery is PolicyRecovery.DISCLOSE_AND_ASK


def test_policy_unrecorded_execution_is_refused():
    decision = on_policy_failure(PolicyFailureKind.EXECUTION_UNRECORDED)
    assert decision.recovery is PolicyRecovery.REFUSE


# --- partial execution (RFC-0002 §10; I-8, I-9, I-15) ---------------------


def test_partial_execution_records_exactly_what_ran():
    decision = on_partial(("step-1", "step-2"), ("step-3",))
    assert decision.recovery is PartialRecovery.RE_ESTABLISH_THEN_PRESENT
    assert decision.ran == ("step-1", "step-2")
    assert decision.not_ran == ("step-3",)
    assert any("no automatic rollback" in line for line in decision.disclosures)


# --- interruption (RFC-0002 §10; I-15) ------------------------------------


def test_interrupt_machine_touching_reassesses():
    decision = on_interrupt(machine_touching=True)
    assert decision.recovery is InterruptRecovery.RE_ASSESS
    assert any("fresh approval" in line for line in decision.disclosures)


def test_interrupt_cognitive_cancels_the_call():
    decision = on_interrupt(machine_touching=False)
    assert decision.recovery is InterruptRecovery.CANCEL_CALL


def test_interrupt_second_press_ends_the_session():
    decision = on_interrupt(machine_touching=True, second_press=True)
    assert decision.recovery is InterruptRecovery.END


# --- structural: no state-machine transitions from this module ------------


def test_recovery_module_never_performs_a_transition():
    src = RECOVERY_PATH.read_text(encoding="utf-8")
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if (
            isinstance(node, ast.ImportFrom)
            and node.module
            and "session" in node.module
        ):
            pytest.fail("recovery.py must not import the session")
        if isinstance(node, ast.Call):
            func = node.func
            if getattr(func, "id", None) == "evolve":
                pytest.fail("recovery.py must not call state_machine.evolve")
            if isinstance(func, ast.Attribute) and func.attr in {"apply", "evolve"}:
                pytest.fail("recovery.py must not call session.apply / evolve")
