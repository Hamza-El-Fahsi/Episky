"""Deterministic structured-output validation (RFC-0010 §4, §8; RFC-0008 §5;
RFC-0010 PR1, PR2, PR3, PR6, PR11, PR13; RFC-0005 F6; RFC-0007 S7).

Behavioral tests for Iteration 10 Commit C1 (`providers/contract.py`): the
finite RFC-0010 §4 structured outputs (Proposal, Explanation, Questions,
Clarifications, Alternative Plans, Refusal, Failure, Need More Evidence) as
deterministic validators over the `schema` types, with the expected-effect
rule — a Proposal is incomplete without its expected Post-condition and is
rejected (RFC-0008 §5; PR13), never interpreted into validity, never a Fact
(F6), never an instruction, never authority (PR2/PR3/PR6), never executed
(PR1), never verified (PR6). Deterministic (S7): the same value always yields
the same outcome. Fail-closed (PR13): a value that is none of the finite §4
outputs is rejected with no result; any unexpected input degrades, never
crashes (PR11). The package performs no I/O, no vendor call, no clock read,
no randomness, no serialization, and imports only `schema` (blueprint §4.1;
DN-76, DN-78, DN-83).
"""

import ast
import importlib
import pathlib
from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

from episky.providers.contract import (
    AlternativePlans,
    Clarifications,
    Explanation,
    Failure,
    NeedMoreEvidence,
    ProviderOutputKind,
    Questions,
    Refusal,
    ValidationDisposition,
    ValidationOutcome,
    ValidationRefusal,
    validate,
)
from episky.schema.action import Action, Plan, PostCondition, Proposal, Step
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
from episky.schema.outcome import VerificationOutcome

CONTRACT_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "providers"
    / "contract.py"
)

NOW = datetime(2026, 8, 7, 12, 0, 0)

MACHINE_IDENTITY = MachineIdentity()

EXPECTED_PUBLIC_SURFACE = {
    "AlternativePlans",
    "Clarifications",
    "Explanation",
    "Failure",
    "NeedMoreEvidence",
    "ProviderOutputKind",
    "Questions",
    "Refusal",
    "ValidationDisposition",
    "ValidationOutcome",
    "ValidationRefusal",
    "validate",
}

CARRIERS = (
    Explanation,
    Questions,
    Clarifications,
    AlternativePlans,
    Refusal,
    Failure,
    NeedMoreEvidence,
)

CARRIER_FIELDS = {
    "AlternativePlans": {"alternatives"},
    "Clarifications": {"statements"},
    "Explanation": {"text"},
    "Failure": {"report"},
    "NeedMoreEvidence": {"request"},
    "Questions": {"questions"},
    "Refusal": {"reason"},
}


def _postcondition():
    return PostCondition(
        subject=Subject(name="package"),
        property=Property(name="installed-version"),
        expected_value=Value(value="1.2.3"),
        freshness=Freshness(state=FreshnessState.CURRENT),
    )


def _action(verification_criteria=None):
    return Action(
        description="install the package",
        risk_properties=("packages",),
        verification_criteria=(
            _postcondition() if verification_criteria is None else verification_criteria
        ),
    )


def _step():
    return Step(
        action=_action(),
        preconditions=(),
        postcondition=_postcondition(),
        verification_method="re-observation",
    )


def _plan(steps=None):
    return Plan(steps=(_step(),) if steps is None else steps)


def _proposal(candidate=None):
    return Proposal(candidate=_action() if candidate is None else candidate)


def _fact():
    return Fact(
        scope=Scope(
            subject=Subject(name="systemd"),
            property=Property(name="running-state"),
            value=Value(value="running"),
        ),
        status=FactStatus.OBSERVED,
        confidence=ConfidenceSource(name="systemctl-is-active"),
        provenance=Provenance(
            observation=ObservationReference(),
            collector=Collector(name="systemd-state", version="1"),
            collected_at=NOW,
        ),
        freshness=Freshness(state=FreshnessState.CURRENT),
        machine_identity=MACHINE_IDENTITY,
    )


def _carrier(cls):
    if cls is Explanation:
        return cls(text="because the package is outdated")
    if cls is Questions:
        return cls(questions=("which mirror is configured?",))
    if cls is Clarifications:
        return cls(statements=("the goal is to repair the boot",))
    if cls is AlternativePlans:
        return cls(alternatives=(_proposal(),))
    if cls is Refusal:
        return cls(reason="I will not do that")
    if cls is Failure:
        return cls(report="the request could not be completed")
    if cls is NeedMoreEvidence:
        return cls(request="I need the current service state")
    raise AssertionError(f"unhandled carrier {cls}")


# --- Public surface and structure ---


def test_contract_public_surface_is_exactly_the_owned_vocabulary():
    mod = importlib.import_module("episky.providers.contract")
    assert set(mod.__all__) == EXPECTED_PUBLIC_SURFACE


def test_every_owned_type_is_a_frozen_slotted_dataclass():
    for cls in (*CARRIERS, ValidationOutcome):
        params = cls.__dataclass_params__
        assert params.frozen, f"{cls.__name__} is not frozen"
        assert params.slots, f"{cls.__name__} is not slot-based"


def test_output_kind_enum_is_the_finite_rfc_0010_s4_set_in_table_order():
    assert tuple(ProviderOutputKind) == (
        ProviderOutputKind.PROPOSAL,
        ProviderOutputKind.EXPLANATION,
        ProviderOutputKind.QUESTIONS,
        ProviderOutputKind.CLARIFICATIONS,
        ProviderOutputKind.ALTERNATIVE_PLANS,
        ProviderOutputKind.REFUSAL,
        ProviderOutputKind.FAILURE,
        ProviderOutputKind.NEED_MORE_EVIDENCE,
    )


def test_disposition_enum_is_exactly_conforms_and_rejected():
    assert tuple(ValidationDisposition) == (
        ValidationDisposition.CONFORMS,
        ValidationDisposition.REJECTED,
    )


def test_refusal_enum_is_the_fixed_fail_closed_reasons():
    assert tuple(ValidationRefusal) == (
        ValidationRefusal.MALFORMED,
        ValidationRefusal.INCOMPLETE_PROPOSAL,
    )


def test_carrier_fields_are_exactly_the_declared_surface():
    for name, fields in CARRIER_FIELDS.items():
        cls = globals()[name]
        assert set(cls.__dataclass_fields__) == fields


def test_no_carrier_carries_a_fact_or_authority_field():
    forbidden_names = {
        "fact",
        "status",
        "approved",
        "approval",
        "authority",
        "token",
        "permission",
        "verdict",
        "verified",
        "success",
        "command",
        "shell",
    }
    all_fields = {
        name
        for cls in (*CARRIERS, ValidationOutcome)
        for name in cls.__dataclass_fields__
    }
    assert not forbidden_names & all_fields


def test_every_carrier_is_immutable():
    for cls in CARRIERS:
        instance = _carrier(cls)
        with pytest.raises(FrozenInstanceError):
            setattr(instance, next(iter(cls.__dataclass_fields__)), None)


# --- The finite §4 outputs conform with the right kind ---


@pytest.mark.parametrize(
    "value,kind",
    [
        (_proposal(), ProviderOutputKind.PROPOSAL),
        (
            Explanation(text="because the package is outdated"),
            ProviderOutputKind.EXPLANATION,
        ),
        (
            Questions(questions=("which mirror?",)),
            ProviderOutputKind.QUESTIONS,
        ),
        (
            Clarifications(statements=("the goal is to repair the boot",)),
            ProviderOutputKind.CLARIFICATIONS,
        ),
        (
            AlternativePlans(alternatives=(_proposal(),)),
            ProviderOutputKind.ALTERNATIVE_PLANS,
        ),
        (Refusal(reason="I will not do that"), ProviderOutputKind.REFUSAL),
        (Failure(report="could not complete"), ProviderOutputKind.FAILURE),
        (
            NeedMoreEvidence(request="I need the service state"),
            ProviderOutputKind.NEED_MORE_EVIDENCE,
        ),
    ],
)
def test_each_finite_output_conforms_with_its_kind(value, kind):
    outcome = validate(value)
    assert outcome.disposition is ValidationDisposition.CONFORMS
    assert outcome.kind is kind
    assert outcome.refusal is None
    assert outcome.output is value
    assert outcome.reason


def test_validation_outcome_fields_are_exactly_kind_output_disposition_refusal_reason():
    assert set(ValidationOutcome.__dataclass_fields__) == {
        "kind",
        "output",
        "disposition",
        "refusal",
        "reason",
    }


# --- The expected-effect rule (RFC-0010 §4 rule 2; RFC-0008 §5; PR13) ---


def test_a_proposal_with_a_complete_action_conforms():
    proposal = _proposal()
    outcome = validate(proposal)
    assert outcome.disposition is ValidationDisposition.CONFORMS
    assert outcome.kind is ProviderOutputKind.PROPOSAL
    assert outcome.output is proposal


def test_a_proposal_without_an_expected_effect_is_rejected_as_incomplete():
    incomplete = _proposal(candidate=_action(verification_criteria=()))
    outcome = validate(incomplete)
    assert outcome.disposition is ValidationDisposition.REJECTED
    assert outcome.refusal is ValidationRefusal.INCOMPLETE_PROPOSAL
    assert outcome.kind is ProviderOutputKind.PROPOSAL
    assert outcome.output is None
    assert outcome.reason


def test_a_proposal_with_a_plan_of_steps_conforms():
    outcome = validate(_proposal(candidate=_plan()))
    assert outcome.disposition is ValidationDisposition.CONFORMS
    assert outcome.kind is ProviderOutputKind.PROPOSAL


def test_a_proposal_with_an_empty_plan_is_rejected_as_incomplete():
    outcome = validate(_proposal(candidate=_plan(steps=())))
    assert outcome.disposition is ValidationDisposition.REJECTED
    assert outcome.refusal is ValidationRefusal.INCOMPLETE_PROPOSAL
    assert outcome.output is None


def test_a_proposal_whose_candidate_is_neither_action_nor_plan_is_malformed():
    outcome = validate(_proposal(candidate="not an action or a plan"))
    assert outcome.disposition is ValidationDisposition.REJECTED
    assert outcome.refusal is ValidationRefusal.MALFORMED
    assert outcome.output is None


def test_an_alternative_plan_whose_alternative_is_incomplete_is_rejected():
    alternatives = AlternativePlans(
        alternatives=(
            _proposal(),
            _proposal(candidate=_action(verification_criteria=())),
        )
    )
    outcome = validate(alternatives)
    assert outcome.disposition is ValidationDisposition.REJECTED
    assert outcome.refusal is ValidationRefusal.INCOMPLETE_PROPOSAL
    assert outcome.kind is ProviderOutputKind.ALTERNATIVE_PLANS
    assert outcome.output is None


def test_an_alternative_plan_whose_alternative_is_not_a_proposal_is_malformed():
    alternatives = AlternativePlans(alternatives=("not a proposal",))
    outcome = validate(alternatives)
    assert outcome.disposition is ValidationDisposition.REJECTED
    assert outcome.refusal is ValidationRefusal.MALFORMED
    assert outcome.output is None


# --- PR13: malformed is rejected, never interpreted, never coerced ---


@pytest.mark.parametrize(
    "value",
    [
        "free-form text the Core must not guess at",
        "sudo rm -rf /",
        "the service is running and was verified",
        None,
        42,
        3.14,
        ["a", "list"],
        {"kind": "proposal", "candidate": "x"},
        _action(),  # an Action alone is not a Proposal — not a valid §4 output
        _plan(),
        _fact(),
        VerificationOutcome.VERIFIED_SUCCESS,
        VerificationOutcome.CONTRADICTED,
    ],
)
def test_a_malformed_value_yields_no_result_and_never_raises(value):
    outcome = validate(value)
    assert outcome.disposition is ValidationDisposition.REJECTED
    assert outcome.refusal is ValidationRefusal.MALFORMED
    assert outcome.output is None
    assert outcome.kind is None
    assert outcome.reason


def test_a_raw_string_is_never_coerced_into_a_carrier():
    outcome = validate("a plain refusal, maybe")
    assert outcome.disposition is ValidationDisposition.REJECTED
    assert outcome.output is None


def test_uniterable_alternatives_degrade_not_crash():
    outcome = validate(AlternativePlans(alternatives=123))
    assert outcome.disposition is ValidationDisposition.REJECTED
    assert outcome.refusal is ValidationRefusal.MALFORMED
    assert outcome.output is None


# --- PR11: any unexpected input degrades, never crashes ---


@pytest.mark.parametrize(
    "value",
    [
        None,
        object(),
        _carrier(AlternativePlans),
        _carrier(Explanation),
        0,
        "",
        b"bytes",
        (Explanation(text="nested"),),
    ],
)
def test_unexpected_inputs_degrade_never_crash(value):
    validate(value)


def test_a_command_carrying_output_is_data_never_an_instruction():
    outcome = validate(Failure(report="run: rm -rf /"))
    assert outcome.disposition is ValidationDisposition.CONFORMS
    assert outcome.output.report == "run: rm -rf /"
    raw = validate("sudo rm -rf /")
    assert raw.disposition is ValidationDisposition.REJECTED
    assert raw.output is None


def test_validation_never_creates_authority():
    class _ApprovalClaim:
        def __init__(self):
            self.approved = True
            self.token = "grant"

    outcome = validate(_ApprovalClaim())
    assert outcome.disposition is ValidationDisposition.REJECTED
    assert outcome.output is None


def test_validation_never_produces_a_fact():
    outcome = validate(_fact())
    assert outcome.disposition is ValidationDisposition.REJECTED
    assert not isinstance(outcome.output, Fact)
    conforming = validate(_proposal())
    assert not isinstance(conforming.output, Fact)


def test_validation_never_records_a_verification_verdict():
    outcome = validate(VerificationOutcome.VERIFIED_SUCCESS)
    assert outcome.disposition is ValidationDisposition.REJECTED
    assert outcome.output is None
    conforming = validate(_proposal())
    assert conforming.output is not None
    assert not isinstance(conforming.output, VerificationOutcome)


# --- Determinism (RFC-0007 S7) ---


@pytest.mark.parametrize(
    "value",
    [
        _proposal(),
        _proposal(candidate=_plan()),
        Explanation(text="because"),
        AlternativePlans(alternatives=(_proposal(),)),
        Failure(report="could not complete"),
        "malformed",
        _fact(),
    ],
)
def test_validate_is_deterministic(value):
    assert validate(value) == validate(value)


def test_repeated_validation_of_identical_value_is_identical():
    value = _proposal(candidate=_plan(steps=(_step(),)))
    outcomes = [validate(value) for _ in range(3)]
    assert outcomes[0] == outcomes[1] == outcomes[2]


def test_equal_values_yield_equal_outcomes():
    left = AlternativePlans(alternatives=(_proposal(), _proposal()))
    right = AlternativePlans(alternatives=(_proposal(), _proposal()))
    assert left == right
    assert validate(left) == validate(right)


# --- Immutability and no hidden state ---


def test_the_validation_outcome_is_immutable():
    outcome = validate(_proposal())
    with pytest.raises(FrozenInstanceError):
        outcome.kind = None
    with pytest.raises(FrozenInstanceError):
        outcome.reason = "other"


def test_validation_leaves_the_value_untouched():
    proposal = _proposal()
    before = repr(proposal)
    validate(proposal)
    assert repr(proposal) == before


def test_contract_keeps_no_hidden_module_state():
    mod = importlib.import_module("episky.providers.contract")
    mutable_globals = {
        name
        for name, value in vars(mod).items()
        if isinstance(value, (list, dict, set))
        and not (name.startswith("__") and name.endswith("__"))
    }
    assert not mutable_globals
    assert validate(_proposal()) == validate(_proposal())


def test_contract_holds_no_decision_methods():
    for cls in (*CARRIERS, ValidationOutcome):
        for name, attr in vars(cls).items():
            if name.startswith("__") and name.endswith("__"):
                continue
            assert not callable(attr), (
                f"{cls.__name__} exposes {name!r}: the outputs are data, "
                "not decision makers"
            )


# --- Conformance: imports, no I/O, no clock, no verification, no vendor ---


def test_contract_imports_only_the_allowed_packages():
    tree = ast.parse(CONTRACT_PATH.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    episky_imports = sorted({name for name in imported if name.startswith("episky")})
    assert episky_imports == ["episky.schema.action"]


def test_contract_calls_no_classify_verify_execute_or_provider():
    tree = ast.parse(CONTRACT_PATH.read_text(encoding="utf-8"))
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            calls.add(func.id if isinstance(func, ast.Name) else func.attr)
    forbidden = {
        "classify",
        "sanitize",
        "admit",
        "verify",
        "compare",
        "observe",
        "collect",
        "invoke",
        "request",
        "send",
        "fetch",
        "query",
        "execute",
        "run",
    }
    assert not calls & forbidden
    assert not calls & {"subprocess", "os.system", "socket", "requests", "urllib"}


def test_contract_never_reads_a_clock_or_randomness():
    src = CONTRACT_PATH.read_text(encoding="utf-8")
    for token in (
        "datetime.now",
        "utcnow",
        "datetime.today",
        "time.time",
        "time.monotonic",
        "import time",
        "import random",
        "random.",
        "os.urandom",
        "import uuid",
        "uuid4",
        "token_hex",
        "import hmac",
        "import hashlib",
    ):
        assert token not in src


def test_contract_generates_no_serialization_or_persistence():
    src = CONTRACT_PATH.read_text(encoding="utf-8")
    for token in (
        "import json",
        "json.",
        "import yaml",
        "yaml.",
        "markdown",
        "dump",
        "dumps",
        "encode",
        "pickle",
        "sqlite",
        "shelve",
        "pathlib",
        "import os",
        "open(",
    ):
        assert token not in src


def test_contract_performs_no_io_and_calls_no_forbidden_builtin():
    tree = ast.parse(CONTRACT_PATH.read_text(encoding="utf-8"))
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            calls.add(func.id if isinstance(func, ast.Name) else func.attr)
    assert calls.isdisjoint({"open", "print", "input", "exec", "eval", "breakpoint"})


def test_contract_never_imports_audit_policy_or_executor():
    tree = ast.parse(CONTRACT_PATH.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert not any(
        name.startswith(
            (
                "episky.audit",
                "episky.policy",
                "episky.executor",
                "episky.providers",
                "episky.context",
                "episky.trust",
                "episky.factlayer",
                "episky.verification",
            )
        )
        for name in imported
    )
