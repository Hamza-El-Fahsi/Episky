"""Type-level conformance tests for the RFC-0003 §2.6 type surface.

Each type is pure, immutable, behavior-free data; a Step carries an
Action with preconditions (Facts, RFC-0006 §4), expected Post-condition,
and verification method; a Proposal is a candidate Action or Plan.
"""

import dataclasses

import pytest

from episky.schema.action import Action, Plan, PostCondition, Proposal, Step
from episky.schema.fact import Fact, Freshness, FreshnessState, Property, Subject, Value


def _postcondition():
    return PostCondition(
        subject=Subject(name="systemd"),
        property=Property(name="running-state"),
        expected_value=Value(value="running"),
        freshness=Freshness(state=FreshnessState.CURRENT),
    )


def _action():
    return Action(
        description="Start the systemd service",
        risk_properties=("service",),
        verification_criteria=(_postcondition(),),
    )


def _step():
    return Step(
        action=_action(),
        preconditions=(),
        postcondition=_postcondition(),
        verification_method="re-observation and comparison",
    )


def _plan():
    return Plan(steps=(_step(),))


def test_postcondition_carries_fact_vocabulary():
    postcondition = _postcondition()
    assert postcondition.subject == Subject(name="systemd")
    assert postcondition.property == Property(name="running-state")
    assert postcondition.expected_value == Value(value="running")
    assert postcondition.freshness == Freshness(state=FreshnessState.CURRENT)


def test_action_requires_all_components():
    with pytest.raises(TypeError):
        Action(description="Start the systemd service")
    with pytest.raises(TypeError):
        Action(description="Start the systemd service", risk_properties=("service",))


def test_action_surface_and_verification_criteria():
    assert set(Action.__annotations__) == {
        "description",
        "risk_properties",
        "verification_criteria",
    }
    assert "command" not in Action.__annotations__
    assert Action.__annotations__["verification_criteria"] == tuple[PostCondition, ...]
    assert _action().verification_criteria == (_postcondition(),)


def test_step_carries_action_in_sequence_with_its_components():
    step = _step()
    assert set(Step.__annotations__) == {
        "action",
        "preconditions",
        "postcondition",
        "verification_method",
    }
    assert Step.__annotations__["preconditions"] == tuple[Fact, ...]
    assert step.action == _action()
    assert step.postcondition == _postcondition()
    assert step.verification_method == "re-observation and comparison"


def test_plan_is_an_ordered_set_of_steps():
    step = _step()
    assert set(Plan.__annotations__) == {"steps"}
    assert Plan(steps=(step, step)).steps == (step, step)


def test_proposal_is_a_candidate_never_an_approval():
    assert set(Proposal.__annotations__) == {"candidate"}
    assert Proposal(candidate=_action()).candidate == _action()
    assert Proposal(candidate=_plan()).candidate == _plan()
    assert set(Proposal.__annotations__).isdisjoint(
        {"approved", "classified", "executed", "token", "permission"}
    )


def test_action_types_are_frozen_immutable_pure_data():
    for cls in (PostCondition, Action, Step, Plan, Proposal):
        assert dataclasses.is_dataclass(cls)
        assert cls.__slots__
    with pytest.raises(AttributeError):
        _postcondition().subject = Subject(name="other")
    with pytest.raises(AttributeError):
        _action().description = "other"
    with pytest.raises(AttributeError):
        _step().action = _action()
    with pytest.raises(AttributeError):
        _plan().steps = ()
    with pytest.raises(AttributeError):
        Proposal(candidate=_action()).candidate = _plan()
