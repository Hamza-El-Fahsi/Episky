"""Fail-closed redaction (RFC-0009 §11, §13; SC13, SC14; DN-42).

Behavioral tests for Iteration 6 Commit C2 (`secrets/redact.py`): the
secret-classifier-gated redaction entry (consuming the C1
SecretClassification), the layered strategy of RFC-0009 §11.3 —
detection at the boundary (secret-shaped spans replaced with the fixed
marker) plus containment via trust.sanitize bound/quote (S8/S4) — the
fail-closed WITHHELD path when the no-secret property cannot be
established (SC14), the never-upgrade guarantee (S1, T9), determinism
(SC13), provenance/classification preservation, and the ownership,
dependency, immutability, and no-forbidden-behaviour contracts.
"""

import ast
import importlib
import pathlib
import sys

import pytest

from episky.secrets.classify import (
    SecrecyClass,
    SecretClassification,
    SecretMetadata,
    SecretOrigin,
)
from episky.secrets.redact import REDACTION_MARKER, Redaction, RedactionStatus, redact
from episky.trust.classes import TrustClass
from episky.trust.sanitize import DEFAULT_LIMIT

REDACT_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "secrets"
    / "redact.py"
)

ALL_CLASSES = tuple(TrustClass)

# A synthetic JWT whose three segments are all long enough to match the
# json-web-token shape.
JWT = (
    "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
    "eyJzdWIiOiIxMjM0NTY3ODkwIn0."
    "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c"
)

# The owned public surface of redact.py.
EXPECTED_PUBLIC_SURFACE = {
    "REDACTION_MARKER",
    "Redaction",
    "RedactionStatus",
    "redact",
}


def _classification(
    secrecy_class,
    origin=SecretOrigin.CAPTURED,
    shape=None,
    designation=None,
):
    return SecretClassification(
        secrecy_class=secrecy_class,
        origin=origin,
        reason="test classification",
        metadata=SecretMetadata(
            existence=secrecy_class is not SecrecyClass.NON_SECRET,
            provider=None,
        ),
        shape=shape,
        designation=designation,
    )


def _adjacent(shape):
    return _classification(SecrecyClass.SECRET_ADJACENT, shape=shape)


def _non_secret():
    return _classification(SecrecyClass.NON_SECRET)


# --- Status vocabulary (SC14) ---


def test_redaction_status_has_exactly_ok_and_withheld():
    assert tuple(RedactionStatus) == (RedactionStatus.OK, RedactionStatus.WITHHELD)


# --- NON_SECRET: the no-secret property is established (§2) ---


def test_non_secret_content_crosses_contained():
    result = redact("log line", _non_secret(), TrustClass.UNTRUSTED)
    assert result.status is RedactionStatus.OK
    assert result.text == "«log line»"
    assert result.replaced_shapes == ()
    assert result.reason


def test_non_secret_is_bounded_by_the_default_limit():
    result = redact("x" * (DEFAULT_LIMIT * 2), _non_secret(), TrustClass.UNTRUSTED)
    assert len(result.text) == DEFAULT_LIMIT + 3  # bound + marker + « »


def test_non_secret_respects_an_explicit_limit():
    result = redact("x" * 100, _non_secret(), TrustClass.UNTRUSTED, limit=10)
    assert result.text == "«" + "x" * 10 + "…»"


@pytest.mark.parametrize("cls", ALL_CLASSES)
def test_non_secret_preserves_the_trust_class(cls):
    result = redact("log line", _non_secret(), cls)
    assert result.status is RedactionStatus.OK
    assert result.trust_class is cls


def test_non_secret_reason_records_established_non_secret():
    result = redact("log line", _non_secret(), TrustClass.UNTRUSTED)
    assert "non-secret" in result.reason


# --- Detection is gated on the classification (DN-42) ---


def test_detection_is_gated_on_the_classification():
    content = "api_key = a1b2c3d4e5f6a1b2c3d4e5f6"
    adjacent = redact(content, _adjacent("secret-assignment"), TrustClass.UNTRUSTED)
    non_secret = redact(content, _non_secret(), TrustClass.UNTRUSTED)
    assert adjacent.replaced_shapes == ("secret-assignment",)
    assert "a1b2c3d4e5f6a1b2c3d4e5f6" not in adjacent.text
    assert "a1b2c3d4e5f6a1b2c3d4e5f6" in non_secret.text


# --- SECRET_ADJACENT: detection at the boundary (§11.3; SC13/SC14) ---


@pytest.mark.parametrize(
    ("content", "shape_name", "leaked"),
    [
        (
            "Authorization: Bearer 4f4c1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a",
            "bearer-token",
            "4f4c1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a",
        ),
        ("sk-" + "A" * 24, "prefixed-api-key", "A" * 24),
        ("ghp_" + "B" * 24, "prefixed-api-key", "B" * 24),
        ("AKIA" + "A1B2C3D4E5F6G7H8", "prefixed-api-key", "A1B2C3D4E5F6G7H8"),
        (JWT, "json-web-token", "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9"),
        ("-----BEGIN RSA PRIVATE KEY-----", "private-key-block", "RSA PRIVATE KEY"),
        (
            "api_key = a1b2c3d4e5f6a1b2c3d4e5f6",
            "secret-assignment",
            "a1b2c3d4e5f6a1b2c3d4e5f6",
        ),
    ],
)
def test_secret_adjacent_spans_are_replaced_and_no_value_crosses(
    content, shape_name, leaked
):
    result = redact(content, _adjacent(shape_name), TrustClass.UNTRUSTED)
    assert result.status is RedactionStatus.OK
    assert shape_name in result.replaced_shapes
    assert leaked not in result.text
    assert REDACTION_MARKER in result.text


def test_multiple_secret_shaped_spans_are_all_replaced():
    content = (
        "Authorization: Bearer 4f4c1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a "
        "and api_key = a1b2c3d4e5f6a1b2c3d4e5f6"
    )
    result = redact(content, _adjacent("bearer-token"), TrustClass.UNTRUSTED)
    assert result.replaced_shapes == ("bearer-token", "secret-assignment")
    assert "4f4c1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a" not in result.text
    assert "a1b2c3d4e5f6a1b2c3d4e5f6" not in result.text


def test_replaced_span_is_a_fixed_marker_never_a_guess():
    content = "Authorization: Bearer 4f4c1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a"
    result = redact(content, _adjacent("bearer-token"), TrustClass.UNTRUSTED)
    assert result.text == "«Authorization: [REDACTED]»"


@pytest.mark.parametrize("cls", ALL_CLASSES)
def test_adjacent_preserves_the_trust_class(cls):
    content = "Authorization: Bearer 4f4c1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a"
    result = redact(content, _adjacent("bearer-token"), cls)
    assert result.status is RedactionStatus.OK
    assert result.trust_class is cls
    assert "4f4c1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a" not in result.text


# --- SECRET: a secret value never crosses (§1, §19, §23) ---


def test_secret_value_never_crosses():
    result = redact("hunter2", _classification(SecrecyClass.SECRET), TrustClass.TRUSTED)
    assert result.status is RedactionStatus.WITHHELD
    assert result.text == ""
    assert result.reason
    assert result.replaced_shapes == ()


@pytest.mark.parametrize("cls", ALL_CLASSES)
def test_secret_withhold_sets_the_trust_class_hostile(cls):
    result = redact("hunter2", _classification(SecrecyClass.SECRET), cls)
    assert result.trust_class is TrustClass.HOSTILE


# --- HOSTILE: fail closed when the no-secret property cannot be established (SC14) ---


def test_hostile_is_withheld_and_nothing_crosses():
    result = redact(
        "unclassifiable content",
        _classification(SecrecyClass.HOSTILE),
        TrustClass.UNTRUSTED,
    )
    assert result.status is RedactionStatus.WITHHELD
    assert result.text == ""
    assert result.reason


@pytest.mark.parametrize("cls", ALL_CLASSES)
def test_hostile_withhold_sets_the_trust_class_hostile(cls):
    result = redact("x", _classification(SecrecyClass.HOSTILE), cls)
    assert result.trust_class is TrustClass.HOSTILE


def test_withheld_reason_is_non_empty_and_informative():
    result = redact("x", _classification(SecrecyClass.HOSTILE), TrustClass.UNTRUSTED)
    assert result.reason
    assert "no-secret" in result.reason or "SC14" in result.reason


def test_withheld_output_never_carries_the_value():
    result = redact(
        "top secret material", _classification(SecrecyClass.SECRET), TrustClass.TRUSTED
    )
    assert "top secret material" not in result.text


# --- The trust class never upgrades (S1, T9) ---


@pytest.mark.parametrize("cls", ALL_CLASSES)
@pytest.mark.parametrize(
    "secrecy_class", [SecrecyClass.NON_SECRET, SecrecyClass.SECRET_ADJACENT]
)
def test_redaction_never_upgrades_the_trust_class(cls, secrecy_class):
    result = redact("log line", _classification(secrecy_class), cls)
    assert result.trust_class.value <= cls.value
    assert result.trust_class is cls


def test_withheld_is_the_only_class_change_and_it_is_a_demotion():
    for cls in ALL_CLASSES:
        result = redact("x", _classification(SecrecyClass.HOSTILE), cls)
        assert result.trust_class is TrustClass.HOSTILE
        assert result.trust_class.value <= cls.value


def test_hostile_input_stays_hostile_on_a_crossing():
    result = redact("x", _non_secret(), TrustClass.HOSTILE)
    assert result.status is RedactionStatus.OK
    assert result.trust_class is TrustClass.HOSTILE


# --- Provenance and classification preservation (RFC-0009 §1, §15) ---


def test_classification_is_preserved():
    classification = _adjacent("bearer-token")
    result = redact("token", classification, TrustClass.UNTRUSTED)
    assert result.classification is classification


def test_provenance_origin_is_preserved_with_the_text():
    classification = _classification(
        SecrecyClass.NON_SECRET, origin=SecretOrigin.CAPTURED
    )
    result = redact("x", classification, TrustClass.UNTRUSTED)
    assert result.classification.origin is SecretOrigin.CAPTURED
    assert result.classification is classification


# --- Determinism (SC13; RFC-0007 S7) ---


def test_redact_is_deterministic():
    content = "Authorization: Bearer 4f4c1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a"
    first = redact(content, _adjacent("bearer-token"), TrustClass.UNTRUSTED)
    second = redact(content, _adjacent("bearer-token"), TrustClass.UNTRUSTED)
    assert first == second
    assert first.reason == second.reason


@pytest.mark.parametrize("secrecy_class", SecrecyClass)
def test_redact_is_deterministic_for_every_class(secrecy_class):
    classification = _classification(secrecy_class)
    assert redact("x", classification, TrustClass.UNTRUSTED) == redact(
        "x", classification, TrustClass.UNTRUSTED
    )


def test_shape_replacement_is_deterministic():
    content = "sk-" + "A" * 24 + " and " + "ghp_" + "B" * 24
    first = redact(content, _adjacent("prefixed-api-key"), TrustClass.UNTRUSTED)
    second = redact(content, _adjacent("prefixed-api-key"), TrustClass.UNTRUSTED)
    assert first == second
    assert first.replaced_shapes == second.replaced_shapes


# --- Containment uses trust.sanitize bound/quote, not a re-implementation (DN-42) ---


def test_output_is_the_quoted_contained_form():
    result = redact("log line", _non_secret(), TrustClass.UNTRUSTED)
    assert result.text.startswith("«") and result.text.endswith("»")


def test_containment_uses_the_trust_bound_with_an_explicit_marker():
    result = redact("x" * 50, _non_secret(), TrustClass.UNTRUSTED, limit=5)
    assert result.text == "«xxxxx…»"


def test_redact_rejects_a_non_positive_limit():
    with pytest.raises(ValueError):
        redact("x", _non_secret(), TrustClass.UNTRUSTED, limit=0)
    with pytest.raises(ValueError):
        redact("x", _non_secret(), TrustClass.UNTRUSTED, limit=-1)


# --- Result contract and immutability ---


def test_redaction_record_carries_exactly_the_result_contract():
    fields = tuple(f.name for f in Redaction.__dataclass_fields__.values())
    assert fields == (
        "text",
        "status",
        "reason",
        "trust_class",
        "classification",
        "replaced_shapes",
    )


def test_redaction_is_frozen_and_slotted():
    assert Redaction.__dataclass_params__.frozen
    assert Redaction.__dataclass_params__.slots


def test_redaction_cannot_be_mutated():
    result = redact("x", _non_secret(), TrustClass.UNTRUSTED)
    with pytest.raises(AttributeError):
        result.text = "changed"
    with pytest.raises(AttributeError):
        result.trust_class = TrustClass.TRUSTED


# --- No forbidden runtime behaviour ---


def test_redact_has_no_io_no_random_no_runtime_state():
    src = REDACT_PATH.read_text(encoding="utf-8")
    for token in (
        "import os",
        "import socket",
        "import urllib",
        "import requests",
        "import random",
        "import statistics",
        "open(",
        "datetime.now",
    ):
        assert token not in src


def test_redact_has_no_forbidden_responsibility_surface():
    tree = ast.parse(REDACT_PATH.read_text(encoding="utf-8"))
    identifiers = {
        node.id
        for node in ast.walk(tree)
        if isinstance(node, ast.Name) and isinstance(node.id, str)
    }
    assert identifiers.isdisjoint(
        {
            "classify",
            "sanitize",
            "detect",
            "summari",
            "promote",
            "quarantine",
            "provider",
            "executor",
            "runtime",
            "collect",
            "store",
            "persist",
        }
    ), "redact.py names a responsibility it does not own"


# --- Public surface and ownership (blueprint §10) ---


def test_public_surface_is_exactly_the_owned_vocabulary():
    module = importlib.import_module("episky.secrets.redact")
    assert set(module.__all__) == EXPECTED_PUBLIC_SURFACE


def test_public_names_are_defined_by_redact_py():
    module = importlib.import_module("episky.secrets.redact")
    for name in EXPECTED_PUBLIC_SURFACE:
        value = getattr(module, name)
        if hasattr(value, "__module__"):
            assert value.__module__ == "episky.secrets.redact"
        else:
            assert name in module.__dict__


def test_module_ownership_docstring_names_rfc_0009():
    doc = importlib.import_module("episky.secrets.redact").__doc__
    assert "RFC-0009" in doc
    assert "never a guess" in doc
    assert "deterministic" in doc.lower()


# --- Dependency rules (blueprint §4.1; DN-42) ---


def test_redact_imports_only_stdlib_secrets_classify_and_trust():
    tree = ast.parse(REDACT_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] in sys.stdlib_module_names
        elif isinstance(node, ast.ImportFrom):
            if node.level:
                continue
            parts = node.module.split(".")
            if parts[0] == "episky":
                assert parts[1] in ("secrets", "trust")
                if parts[1] == "secrets":
                    assert parts[2:] == ["classify"]
                else:
                    assert parts[2:] in (["classes"], ["sanitize"])
            else:
                assert parts[0] in sys.stdlib_module_names
