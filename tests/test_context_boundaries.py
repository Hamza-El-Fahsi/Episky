"""Secret-free boundary enforcement (RFC-0012 §9, §13, §19, §23, §24, §32;
RFC-0009 SC2, SC16; RFC-0007 S1–S8).

Behavioral tests for Iteration 9 Commit C2 (`context/boundaries.py`): the
deterministic enforcement point every input crosses before it may enter
Context or a View (DN-67) — secret-shaped values fail closed (SC2, CM4,
T10), hostile/quarantined content is excluded (RFC-0012 §9 rule 4; T11),
untrusted text is neutralized and contained (S1–S8), personal data is
secret until an explicit Operator demotion (SC16), nothing enters without
a stated purpose (CM5), malformed or uncertain inputs are refused
explicitly, and the boundary is value-free — refused material never
crosses and admitted material crosses only in its contained form. The
classification and sanitization are delegated to `trust` and `secrets`;
the boundary itself classifies nothing (S7: the same input always yields
the same decision). No I/O, no provider call, no `audit` import (CM15).
"""

import ast
import importlib
import pathlib
from dataclasses import FrozenInstanceError

import pytest

from episky.context.boundaries import (
    DEFAULT_BOUNDARY_LIMIT,
    BoundaryDecision,
    BoundaryDisposition,
    BoundaryInput,
    BoundaryRefusal,
    BoundaryReport,
    admit,
    admit_all,
)
from episky.secrets.classify import (
    NonSecretDesignation,
    SecretOrigin,
)
from episky.trust.classes import (
    ProvenanceState,
    TrustCategory,
    TrustClass,
    TrustDomain,
)
from episky.trust.hostile import Quarantine

BOUNDARIES_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "context"
    / "boundaries.py"
)

PURPOSE = "diagnose boot failure"

EXPECTED_PUBLIC_SURFACE = {
    "BoundaryDecision",
    "BoundaryDisposition",
    "BoundaryInput",
    "BoundaryRefusal",
    "BoundaryReport",
    "DEFAULT_BOUNDARY_LIMIT",
    "admit",
    "admit_all",
}


def _datum(
    content="the machine fails to boot",
    category=TrustCategory.USER_INPUT,
    origin=TrustDomain.OPERATOR,
    provenance=ProvenanceState.ESTABLISHED,
    purpose=PURPOSE,
    designation=NonSecretDesignation.SANITIZED_TEXT,
    secret_origin=SecretOrigin.CAPTURED,
    provider=None,
):
    return BoundaryInput(
        content=content,
        category=category,
        origin=origin,
        provenance=provenance,
        purpose=purpose,
        designation=designation,
        secret_origin=secret_origin,
        provider=provider,
    )


# --- Public surface and structure ---


def test_boundaries_public_surface_is_exactly_the_owned_vocabulary():
    mod = importlib.import_module("episky.context.boundaries")
    assert set(mod.__all__) == EXPECTED_PUBLIC_SURFACE


def test_every_owned_type_is_a_frozen_slotted_dataclass():
    for cls in (BoundaryDecision, BoundaryInput, BoundaryReport):
        params = cls.__dataclass_params__
        assert params.frozen, f"{cls.__name__} is not frozen"
        assert params.slots, f"{cls.__name__} is not slot-based"


def test_boundary_input_is_immutable():
    datum = _datum()
    with pytest.raises(FrozenInstanceError):
        datum.content = "other"


def test_disposition_enum_is_exactly_admitted_and_refused():
    assert tuple(BoundaryDisposition) == (
        BoundaryDisposition.ADMITTED,
        BoundaryDisposition.REFUSED,
    )


def test_refusal_enum_is_the_fixed_fail_closed_reasons():
    assert tuple(BoundaryRefusal) == (
        BoundaryRefusal.UNPURPOSEFUL,
        BoundaryRefusal.MALFORMED,
        BoundaryRefusal.HOSTILE,
        BoundaryRefusal.SECRET,
        BoundaryRefusal.SECRET_ADJACENT,
        BoundaryRefusal.UNCLASSIFIABLE,
        BoundaryRefusal.UNPROVENANCED,
    )


# --- Admission: S1–S8 neutralization and containment ---


def test_ordinary_text_is_admitted_in_contained_form():
    decision = admit(_datum())
    assert decision.disposition is BoundaryDisposition.ADMITTED
    assert decision.refusal is None
    assert decision.text == "«the machine fails to boot»"


def test_admitted_decision_carries_the_held_trust_class():
    decision = admit(_datum())
    assert decision.trust_class is TrustClass.UNTRUSTED


def test_trusted_category_admits_at_its_class():
    decision = admit(
        _datum(
            content="systemd is running",
            category=TrustCategory.FACT,
            origin=TrustDomain.CORE,
            designation=NonSecretDesignation.PUBLIC_MACHINE_FACT,
        )
    )
    assert decision.disposition is BoundaryDisposition.ADMITTED
    assert decision.trust_class is TrustClass.TRUSTED


@pytest.mark.parametrize(
    "designation",
    [
        NonSecretDesignation.PUBLIC_MACHINE_FACT,
        NonSecretDesignation.NO_CAPABILITY_AGGREGATE,
        NonSecretDesignation.MECHANISM,
        NonSecretDesignation.SANITIZED_TEXT,
        NonSecretDesignation.OPERATOR_PREFERENCE,
    ],
)
def test_every_fixed_non_secret_designation_is_admitted(designation):
    decision = admit(_datum(designation=designation))
    assert decision.disposition is BoundaryDisposition.ADMITTED


def test_admitted_text_is_quoted_and_neutralized():
    decision = admit(_datum(content="hello\x1b[31mred\x1b[0m\x07world\u200b"))
    text = decision.text
    assert text.startswith("«") and text.endswith("»")
    assert "\x1b" not in text
    assert "\\x07" in text
    assert "\\u200b" in text


def test_admitted_text_is_bounded_with_an_explicit_marker():
    decision = admit(_datum(content="a" * 3000))
    assert decision.text == "«" + "a" * DEFAULT_BOUNDARY_LIMIT + "…»"


def test_admitted_text_respects_a_custom_bound():
    decision = admit(_datum(content="a" * 3000), limit=8)
    assert decision.text == "«aaaaaaaa…»"


def test_admitted_decision_reports_no_secret_existence():
    decision = admit(_datum())
    assert decision.metadata is not None
    assert decision.metadata.existence is False


def test_provider_flows_into_the_value_free_metadata():
    decision = admit(_datum(provider="openai"))
    assert decision.metadata.provider == "openai"


# --- SC2: secret-shaped values fail closed ---


def test_bearer_token_is_refused():
    decision = admit(_datum(content="Bearer ABCD1234abcd1234WXYZ", designation=None))
    assert decision.disposition is BoundaryDisposition.REFUSED
    assert decision.refusal is BoundaryRefusal.SECRET_ADJACENT


@pytest.mark.parametrize(
    "token",
    [
        "sk-abcdefghijklmnopqrstuvwxyz123456",
        "ghp_ABCDEFGHIJKLMNOPQRSTUVWXYZ123456",
        "AKIAABCDEFGHIJKLMNOP",
    ],
)
def test_prefixed_api_key_is_refused(token):
    decision = admit(_datum(content=token, designation=None))
    assert decision.disposition is BoundaryDisposition.REFUSED
    assert decision.refusal is BoundaryRefusal.SECRET_ADJACENT


def test_json_web_token_is_refused():
    token = (
        "eyJhbGciOiJIUzI1NiJ9."
        "eyJzdWIiOiIxMjM0NTY3ODkwIn0."
        "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
    )
    decision = admit(_datum(content=token, designation=None))
    assert decision.disposition is BoundaryDisposition.REFUSED
    assert decision.refusal is BoundaryRefusal.SECRET_ADJACENT


def test_private_key_block_is_refused():
    decision = admit(
        _datum(content="-----BEGIN RSA PRIVATE KEY-----", designation=None)
    )
    assert decision.disposition is BoundaryDisposition.REFUSED
    assert decision.refusal is BoundaryRefusal.SECRET_ADJACENT


def test_secret_assignment_is_refused():
    decision = admit(_datum(content="api_key = AbC12345", designation=None))
    assert decision.disposition is BoundaryDisposition.REFUSED
    assert decision.refusal is BoundaryRefusal.SECRET_ADJACENT


def test_a_secret_shaped_value_appears_nowhere_in_the_decision():
    token = "sk-abcdefghijklmnopqrstuvwxyz123456"
    decision = admit(_datum(content=token, designation=None))
    assert token not in repr(decision)
    assert token not in decision.reason


def test_operator_marked_private_is_refused_as_secret():
    decision = admit(_datum(designation=None, secret_origin=SecretOrigin.MARKED))
    assert decision.disposition is BoundaryDisposition.REFUSED
    assert decision.refusal is BoundaryRefusal.SECRET


def test_provisioned_origin_is_refused_as_secret():
    decision = admit(_datum(designation=None, secret_origin=SecretOrigin.PROVISIONED))
    assert decision.disposition is BoundaryDisposition.REFUSED
    assert decision.refusal is BoundaryRefusal.SECRET


def test_refused_secret_decision_carries_value_free_metadata():
    decision = admit(_datum(content="Bearer ABCD1234abcd1234WXYZ", designation=None))
    assert decision.metadata is not None
    assert decision.metadata.existence is True
    assert decision.metadata.provider is None


def test_refused_secret_decision_never_carries_text():
    decision = admit(_datum(content="Bearer ABCD1234abcd1234WXYZ", designation=None))
    assert decision.text == ""


# --- SC16: personal data is secret until an explicit demotion ---


def test_personal_data_without_demotion_is_refused():
    decision = admit(
        _datum(content="contact me at alice@example.com", designation=None)
    )
    assert decision.disposition is BoundaryDisposition.REFUSED
    assert decision.refusal is BoundaryRefusal.UNCLASSIFIABLE


def test_personal_data_is_admitted_after_explicit_demotion():
    decision = admit(
        _datum(
            content="contact me at alice@example.com",
            designation=NonSecretDesignation.MARKED_PUBLIC,
        )
    )
    assert decision.disposition is BoundaryDisposition.ADMITTED
    assert decision.text == "«contact me at alice@example.com»"


def test_demotion_requires_a_stated_purpose():
    decision = admit(
        _datum(
            content="contact me at alice@example.com",
            purpose="  ",
            designation=NonSecretDesignation.MARKED_PUBLIC,
        )
    )
    assert decision.disposition is BoundaryDisposition.REFUSED
    assert decision.refusal is BoundaryRefusal.UNPURPOSEFUL


def test_personal_data_metadata_reports_no_secret_after_demotion():
    decision = admit(
        _datum(
            content="contact me at alice@example.com",
            designation=NonSecretDesignation.MARKED_PUBLIC,
        )
    )
    assert decision.metadata.existence is False


# --- Trust boundary: hostile and unprovenanced content ---


def test_hostile_content_is_refused_and_quarantined():
    decision = admit(
        _datum(
            category=TrustCategory.OBSERVATION,
            provenance=ProvenanceState.LOST,
            designation=None,
        )
    )
    assert decision.disposition is BoundaryDisposition.REFUSED
    assert decision.refusal is BoundaryRefusal.HOSTILE
    assert decision.trust_class is TrustClass.HOSTILE
    assert isinstance(decision.quarantine, Quarantine)


def test_quarantined_content_is_excluded_by_definition():
    decision = admit(
        _datum(
            category=TrustCategory.OBSERVATION,
            provenance=ProvenanceState.LOST,
            designation=None,
        )
    )
    assert decision.quarantine.excluded is True


def test_unprovenanced_content_is_refused():
    decision = admit(
        _datum(
            content="service restarted",
            category=TrustCategory.FACT,
            origin=TrustDomain.CORE,
            provenance=ProvenanceState.LOST,
            designation=NonSecretDesignation.SANITIZED_TEXT,
        )
    )
    assert decision.disposition is BoundaryDisposition.REFUSED
    assert decision.refusal is BoundaryRefusal.UNPROVENANCED
    assert decision.text == ""


# --- Purpose and malformed-input gates ---


def test_blank_purpose_is_refused():
    decision = admit(_datum(purpose=""))
    assert decision.disposition is BoundaryDisposition.REFUSED
    assert decision.refusal is BoundaryRefusal.UNPURPOSEFUL


def test_whitespace_purpose_is_refused():
    decision = admit(_datum(purpose="   \n\t"))
    assert decision.disposition is BoundaryDisposition.REFUSED
    assert decision.refusal is BoundaryRefusal.UNPURPOSEFUL


def test_blank_content_is_refused_as_malformed():
    decision = admit(_datum(content="   "))
    assert decision.disposition is BoundaryDisposition.REFUSED
    assert decision.refusal is BoundaryRefusal.MALFORMED


def test_contradictory_designation_is_refused_as_malformed():
    decision = admit(
        _datum(
            designation=NonSecretDesignation.SANITIZED_TEXT,
            secret_origin=SecretOrigin.MARKED,
        )
    )
    assert decision.disposition is BoundaryDisposition.REFUSED
    assert decision.refusal is BoundaryRefusal.MALFORMED


# --- Determinism and ordered processing (RFC-0007 S7) ---


def test_admit_is_deterministic():
    datum = _datum(content="the machine fails to boot")
    assert admit(datum) == admit(datum)


def test_admit_all_preserves_input_order():
    datum = _datum()
    refused = _datum(content="Bearer ABCD1234abcd1234WXYZ", designation=None)
    report = admit_all((datum, refused))
    assert report.decisions[0].disposition is BoundaryDisposition.ADMITTED
    assert report.decisions[1].disposition is BoundaryDisposition.REFUSED


def test_admit_all_is_deterministic():
    items = (_datum(), _datum(content="Bearer ABCD1234abcd1234WXYZ", designation=None))
    assert admit_all(items) == admit_all(items)


def test_boundary_report_is_immutable():
    report = admit_all((_datum(),))
    with pytest.raises(FrozenInstanceError):
        report.decisions = ()
    with pytest.raises((FrozenInstanceError, TypeError)):
        report.decisions[0].text = "other"


def test_admit_all_refusals_are_disclosed_not_silent():
    secret = _datum(content="sk-abcdefghijklmnopqrstuvwxyz123456", designation=None)
    report = admit_all((secret,))
    assert report.decisions[0].refusal is BoundaryRefusal.SECRET_ADJACENT
    assert report.decisions[0].reason


# --- Validation and placeholder defaults ---


def test_non_positive_bound_raises():
    with pytest.raises(ValueError):
        admit(_datum(), limit=0)


def test_boundary_limit_is_a_positive_placeholder_default():
    assert isinstance(DEFAULT_BOUNDARY_LIMIT, int)
    assert DEFAULT_BOUNDARY_LIMIT >= 1


# --- Conformance: imports, I/O, clock, randomness, audit (CM15) ---


def test_boundaries_imports_only_allowed_packages():
    tree = ast.parse(BOUNDARIES_PATH.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    episky_imports = sorted({name for name in imported if name.startswith("episky")})
    assert sorted(episky_imports) == [
        "episky.secrets.classify",
        "episky.trust.classes",
        "episky.trust.hostile",
        "episky.trust.sanitize",
    ]


def test_boundaries_never_reads_a_clock_or_randomness():
    src = BOUNDARIES_PATH.read_text(encoding="utf-8")
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


def test_boundaries_performs_no_io_and_calls_no_forbidden_builtin():
    tree = ast.parse(BOUNDARIES_PATH.read_text(encoding="utf-8"))
    calls = set()
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            calls.add(func.id if isinstance(func, ast.Name) else func.attr)
    assert calls.isdisjoint({"open", "print", "input", "exec", "eval", "breakpoint"})
    assert not calls & {"subprocess", "os.system", "socket", "requests", "urllib"}


def test_boundaries_never_imports_audit():
    tree = ast.parse(BOUNDARIES_PATH.read_text(encoding="utf-8"))
    imported = []
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            imported.extend(alias.name for alias in node.names)
        elif isinstance(node, ast.ImportFrom) and node.module:
            imported.append(node.module)
    assert not any(
        name.startswith(
            ("episky.audit", "episky.providers", "episky.policy", "episky.executor")
        )
        for name in imported
    )


def test_boundaries_defines_no_secret_shape_catalogue_of_its_own():
    src = BOUNDARIES_PATH.read_text(encoding="utf-8")
    assert "import re" not in src
    tree = ast.parse(src)
    for node in ast.walk(tree):
        if isinstance(node, ast.Call):
            func = node.func
            name = getattr(func, "id", None) or getattr(func, "attr", None)
            assert name != "compile", (
                "the boundary must not compile its own shapes (delegation, RFC-0009 §3)"
            )
