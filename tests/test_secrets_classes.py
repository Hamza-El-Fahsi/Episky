"""Deterministic secret classification (RFC-0009 §1, §2, §3, §7, §14).

Behavioral tests for Iteration 6 Commit C1 (`secrets/classify.py`): the
four-class secrecy predicate in the blueprint §5 order (DN-44), the
three §7 origins, the six fixed §2 non-secret classes, the six §3 rules
(each deterministic and tested; rule 5 = no LLM/statistical path,
enforced as a property; rule 6 = testable), the mechanical, explicitly
non-exhaustive shape catalogue, the fail-closed-to-Hostile guarantee
(rule 4), the §14 demotion path, and the §1 value/metadata split as
separate result kinds — a value-free SecretClassification whose only
exportable facet is SecretMetadata.
"""

import ast
import importlib
import pathlib
import sys

import pytest

from episky.secrets.classify import (
    SECRET_SHAPES,
    NonSecretDesignation,
    SecrecyClass,
    SecretClassification,
    SecretDatum,
    SecretMetadata,
    SecretOrigin,
    SecretShape,
    classify,
)

CLASSIFY_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "secrets"
    / "classify.py"
)

# Blueprint §5 outputs, in order.
FOUR_CLASSES = (
    SecrecyClass.SECRET,
    SecrecyClass.NON_SECRET,
    SecrecyClass.SECRET_ADJACENT,
    SecrecyClass.HOSTILE,
)

# RFC-0009 §7 order, transcribed.
THREE_ORIGINS = (
    SecretOrigin.PROVISIONED,
    SecretOrigin.MARKED,
    SecretOrigin.CAPTURED,
)

# RFC-0009 §2 order, transcribed.
SIX_NON_SECRETS = (
    NonSecretDesignation.PUBLIC_MACHINE_FACT,
    NonSecretDesignation.NO_CAPABILITY_AGGREGATE,
    NonSecretDesignation.MECHANISM,
    NonSecretDesignation.SANITIZED_TEXT,
    NonSecretDesignation.OPERATOR_PREFERENCE,
    NonSecretDesignation.MARKED_PUBLIC,
)

# The owned public surface of classify.py.
EXPECTED_PUBLIC_SURFACE = {
    "NonSecretDesignation",
    "SECRET_SHAPES",
    "SecretClassification",
    "SecretDatum",
    "SecretMetadata",
    "SecretOrigin",
    "SecretShape",
    "SecrecyClass",
    "classify",
}


def _datum(content, origin, designation=None, provider=None):
    return SecretDatum(
        content=content,
        origin=origin,
        designation=designation,
        provider=provider,
    )


# --- Vocabulary: completeness and ordering (blueprint §5; RFC-0009 §2, §7) ---


def test_secrecy_class_has_exactly_four_members_in_blueprint_five_order():
    assert tuple(SecrecyClass) == FOUR_CLASSES


def test_secrecy_class_member_values_are_mutually_exclusive():
    values = [member.value for member in SecrecyClass]
    assert len(set(values)) == len(values) == len(FOUR_CLASSES)


def test_secret_origin_has_exactly_the_three_section_seven_origins():
    assert tuple(SecretOrigin) == THREE_ORIGINS


def test_non_secret_designation_has_exactly_the_six_section_two_classes():
    assert tuple(NonSecretDesignation) == SIX_NON_SECRETS


# --- Rule 1: provisioned values are secrets (§3 rule 1) ---


@pytest.mark.parametrize(
    "content",
    [
        "",
        "plain text",
        "Authorization: Bearer 4f4c1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a",
        "-----BEGIN RSA PRIVATE KEY-----",
    ],
)
def test_rule_1_provisioned_values_are_secrets_regardless_of_content(content):
    result = classify(_datum(content, SecretOrigin.PROVISIONED))
    assert result.secrecy_class is SecrecyClass.SECRET
    assert "rule 1" in result.reason


def test_rule_1_provisioned_rejects_a_non_secret_designation():
    with pytest.raises(ValueError):
        classify(
            _datum(
                "x",
                SecretOrigin.PROVISIONED,
                designation=NonSecretDesignation.PUBLIC_MACHINE_FACT,
            )
        )


def test_rule_1_provisioned_never_fails_closed():
    result = classify(_datum("x", SecretOrigin.PROVISIONED))
    assert result.secrecy_class is SecrecyClass.SECRET
    assert result.secrecy_class is not SecrecyClass.HOSTILE


# --- Rule 2: Operator-marked values are secrets (§3 rule 2) ---


def test_rule_2_marked_values_are_secrets():
    result = classify(_datum("some private content", SecretOrigin.MARKED))
    assert result.secrecy_class is SecrecyClass.SECRET
    assert "rule 2" in result.reason


def test_rule_2_marked_secret_ignores_content_shapes():
    result = classify(_datum("plain text", SecretOrigin.MARKED))
    assert result.secrecy_class is SecrecyClass.SECRET


@pytest.mark.parametrize("designation", SIX_NON_SECRETS[:5])
def test_rule_2_marked_rejects_a_designation_other_than_public(designation):
    with pytest.raises(ValueError):
        classify(_datum("x", SecretOrigin.MARKED, designation=designation))


def test_rule_6_section_14_demotion_marked_public_is_non_secret():
    result = classify(
        _datum(
            "private content",
            SecretOrigin.MARKED,
            designation=NonSecretDesignation.MARKED_PUBLIC,
        )
    )
    assert result.secrecy_class is SecrecyClass.NON_SECRET
    assert result.designation is NonSecretDesignation.MARKED_PUBLIC
    assert "rule 6" in result.reason


# --- Rule 3: secret-shaped captured values are secret-adjacent (§3 rule 3) ---


@pytest.mark.parametrize(
    ("content", "expected_shape"),
    [
        (
            "Authorization: Bearer 4f4c1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a",
            "bearer-token",
        ),
        ("sk-" + "A" * 24, "prefixed-api-key"),
        ("ghp_" + "B" * 24, "prefixed-api-key"),
        ("AKIA" + "A1B2C3D4E5F6G7H8", "prefixed-api-key"),
        (
            "eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9."
            "eyJzdWIiOiIxMjM0NTY3ODkwIn0."
            "SflKxwRJSMeKKF2QT4fwpMeJf36POk6yJV_adQssw5c",
            "json-web-token",
        ),
        ("-----BEGIN RSA PRIVATE KEY-----", "private-key-block"),
        ("-----BEGIN OPENSSH PRIVATE KEY-----", "private-key-block"),
        ("api_key = a1b2c3d4e5f6a1b2c3d4e5f6", "secret-assignment"),
        ("password: f1e2d3c4b5a6f1e2d3c4b5a6", "secret-assignment"),
    ],
)
def test_rule_3_secret_shaped_captured_values_are_secret_adjacent(
    content, expected_shape
):
    result = classify(_datum(content, SecretOrigin.CAPTURED))
    assert result.secrecy_class is SecrecyClass.SECRET_ADJACENT
    assert result.shape == expected_shape
    assert "rule 3" in result.reason


def test_rule_3_secret_adjacent_until_proven_otherwise():
    datum = _datum(
        "Authorization: Bearer 4f4c1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a",
        SecretOrigin.CAPTURED,
    )
    assert classify(datum).secrecy_class is SecrecyClass.SECRET_ADJACENT
    proven = SecretDatum(
        content=datum.content,
        origin=SecretOrigin.CAPTURED,
        designation=NonSecretDesignation.SANITIZED_TEXT,
    )
    assert classify(proven).secrecy_class is SecrecyClass.NON_SECRET


def test_rule_3_a_failed_shape_match_proves_nothing():
    result = classify(_datum("ordinary prose", SecretOrigin.CAPTURED))
    assert result.secrecy_class is not SecrecyClass.NON_SECRET


# --- The shape catalogue: mechanical and explicitly non-exhaustive ---


def test_shape_catalogue_is_mechanical():
    assert SECRET_SHAPES
    for shape in SECRET_SHAPES:
        assert isinstance(shape, SecretShape)
        assert shape.name
        assert shape.regex.pattern
        assert shape.description
    assert len({shape.name for shape in SECRET_SHAPES}) == len(SECRET_SHAPES)


def test_shape_catalogue_is_immutable():
    with pytest.raises(TypeError):
        SECRET_SHAPES[0] = SECRET_SHAPES[0]


def test_shape_catalogue_is_explicitly_non_exhaustive():
    module = importlib.import_module("episky.secrets.classify")
    assert "non-exhaustive" in module.__doc__
    assert "non-exhaustive" in SecretShape.__doc__


def test_every_shape_description_names_its_section_one_class():
    for shape in SECRET_SHAPES:
        assert "RFC-0009 §1" in shape.description


# --- Rule 4: unclassifiable data fails closed to Hostile (§3 rule 4) ---


@pytest.mark.parametrize(
    "content",
    ["", "plain prose with no secret shape", "kernel 6.6.0", "uptime 3 days"],
)
def test_rule_4_unclassifiable_captured_data_fails_closed_to_hostile(content):
    result = classify(_datum(content, SecretOrigin.CAPTURED))
    assert result.secrecy_class is SecrecyClass.HOSTILE
    assert "rule 4" in result.reason


def test_hostile_is_quarantined_never_probably_not_a_secret():
    names = {member.name for member in SecrecyClass}
    assert len(names) == 4
    assert "PROBABLY_NOT_A_SECRET" not in names


def test_no_class_is_hostile_by_origin_alone_for_provisioned_or_marked():
    for origin in (SecretOrigin.PROVISIONED, SecretOrigin.MARKED):
        result = classify(_datum("x", origin))
        assert result.secrecy_class is not SecrecyClass.HOSTILE


# --- Section 2: the six fixed non-secret classes ---


@pytest.mark.parametrize("designation", SIX_NON_SECRETS)
def test_section_two_fixed_non_secrets_are_non_secret(designation):
    result = classify(
        _datum("some captured text", SecretOrigin.CAPTURED, designation=designation)
    )
    assert result.secrecy_class is SecrecyClass.NON_SECRET
    assert result.designation is designation


@pytest.mark.parametrize("designation", SIX_NON_SECRETS)
def test_non_secret_reason_names_the_section_two_class(designation):
    result = classify(
        _datum("some captured text", SecretOrigin.CAPTURED, designation=designation)
    )
    assert "RFC-0009 §2" in result.reason
    assert designation.name in result.reason


# --- Section 1: every by-construction secret class is classified as secret ---


def test_every_section_one_secret_class_is_classified_as_secret():
    # §1 rule 1: credentials (Operator-marked).
    assert classify(_datum("hunter2", SecretOrigin.MARKED)).secrecy_class is (
        SecrecyClass.SECRET
    )
    # §1 rule 2: tokens and API keys (provisioned, and shape-matched when captured).
    assert (
        classify(_datum("ghp_" + "A" * 24, SecretOrigin.PROVISIONED)).secrecy_class
        is SecrecyClass.SECRET
    )
    assert (
        classify(_datum("sk-" + "A" * 24, SecretOrigin.CAPTURED)).secrecy_class
        is SecrecyClass.SECRET_ADJACENT
    )
    # §1 rule 3: private keys.
    assert (
        classify(
            _datum("-----BEGIN OPENSSH PRIVATE KEY-----", SecretOrigin.CAPTURED)
        ).secrecy_class
        is SecrecyClass.SECRET_ADJACENT
    )
    # §1 rule 4: secret-shaped captured data.
    assert (
        classify(
            _datum("secret: f1e2d3c4b5a6f1e2d3c4b5a6", SecretOrigin.CAPTURED)
        ).secrecy_class
        is SecrecyClass.SECRET_ADJACENT
    )
    # §1 rule 5: personal data (Operator-marked private).
    assert (
        classify(_datum("identity document content", SecretOrigin.MARKED)).secrecy_class
        is SecrecyClass.SECRET
    )


# --- Exhaustiveness and mutual exclusivity of the predicate ---


def test_predicate_is_exhaustive_and_every_input_yields_exactly_one_class():
    samples = [
        _datum("x", SecretOrigin.PROVISIONED),
        _datum("x", SecretOrigin.MARKED),
        _datum(
            "x",
            SecretOrigin.MARKED,
            designation=NonSecretDesignation.MARKED_PUBLIC,
        ),
        _datum(
            "Authorization: Bearer 4f4c1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a",
            SecretOrigin.CAPTURED,
        ),
        _datum(
            "x",
            SecretOrigin.CAPTURED,
            designation=NonSecretDesignation.PUBLIC_MACHINE_FACT,
        ),
        _datum("x", SecretOrigin.CAPTURED),
    ]
    for datum in samples:
        result = classify(datum)
        assert result.secrecy_class in SecrecyClass
    classes = {classify(datum).secrecy_class for datum in samples}
    assert classes == set(FOUR_CLASSES)
    for datum in samples:
        assert type(classify(datum).secrecy_class) is SecrecyClass


# --- Rule 5: the LLM never classifies — enforced as a property ---


def test_rule_5_classify_py_imports_only_the_standard_library():
    tree = ast.parse(CLASSIFY_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] in sys.stdlib_module_names
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "no relative imports"
            assert node.module.split(".")[0] in sys.stdlib_module_names


def test_rule_5_no_llm_or_io_surface_exists():
    src = CLASSIFY_PATH.read_text(encoding="utf-8")
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


def test_rule_6_classify_is_deterministic():
    datum = _datum(
        "Authorization: Bearer 4f4c1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a",
        SecretOrigin.CAPTURED,
    )
    assert classify(datum) == classify(datum)
    assert classify(datum).reason == classify(datum).reason
    for origin in SecretOrigin:
        d = _datum("x", origin)
        assert classify(d) == classify(d)


# --- The value/metadata split (§1; DN-44) ---


def test_metadata_is_the_exportable_facet_and_is_value_free():
    result = classify(
        _datum(
            "Authorization: Bearer 4f4c1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a",
            SecretOrigin.CAPTURED,
            provider="acme",
        )
    )
    assert isinstance(result.metadata, SecretMetadata)
    assert result.metadata.existence is True
    assert result.metadata.provider == "acme"
    assert result.metadata.provisioned_on is None
    assert result.metadata.last_used_on is None
    assert result.metadata.invalidated_on is None
    assert "4f4c1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a" not in str(result.metadata)
    assert "Bearer" not in str(result.metadata)


@pytest.mark.parametrize(
    ("origin", "designation", "expected_existence"),
    [
        (SecretOrigin.PROVISIONED, None, True),
        (SecretOrigin.MARKED, None, True),
        (SecretOrigin.CAPTURED, None, True),  # unclassifiable -> treated as present
        (SecretOrigin.CAPTURED, NonSecretDesignation.PUBLIC_MACHINE_FACT, False),
        (SecretOrigin.MARKED, NonSecretDesignation.MARKED_PUBLIC, False),
    ],
)
def test_metadata_existence_reflects_the_class(origin, designation, expected_existence):
    result = classify(_datum("x", origin, designation=designation))
    assert result.metadata.existence is expected_existence


def test_classification_never_carries_the_value():
    result = classify(_datum("sk-" + "A" * 24, SecretOrigin.CAPTURED))
    assert not hasattr(result, "content")
    assert "content" not in result.__dataclass_fields__
    assert "sk-" not in str(result)
    assert "A" * 24 not in str(result)


# --- Provenance preservation ---


def test_classification_preserves_the_origin():
    for origin in SecretOrigin:
        result = classify(_datum("x", origin))
        assert result.origin is origin


def test_metadata_carries_the_provider_context():
    result = classify(_datum("x", SecretOrigin.CAPTURED, provider="acme"))
    assert result.metadata.provider == "acme"
    assert classify(_datum("x", SecretOrigin.CAPTURED)).metadata.provider is None


# --- Records are frozen and slot-based; the catalogue is immutable ---


def test_secret_datum_is_frozen_and_slotted():
    assert SecretDatum.__dataclass_params__.frozen
    assert SecretDatum.__dataclass_params__.slots


def test_secret_classification_is_frozen_and_slotted():
    assert SecretClassification.__dataclass_params__.frozen
    assert SecretClassification.__dataclass_params__.slots


def test_secret_metadata_is_frozen_and_slotted():
    assert SecretMetadata.__dataclass_params__.frozen
    assert SecretMetadata.__dataclass_params__.slots


def test_secret_shape_is_frozen_and_slotted():
    assert SecretShape.__dataclass_params__.frozen
    assert SecretShape.__dataclass_params__.slots


def test_records_cannot_be_mutated():
    datum = _datum("x", SecretOrigin.CAPTURED)
    with pytest.raises(AttributeError):
        datum.content = "changed"
    result = classify(datum)
    with pytest.raises(AttributeError):
        result.secrecy_class = SecrecyClass.HOSTILE
    with pytest.raises(AttributeError):
        result.metadata.existence = False


# --- No forbidden runtime behaviour ---


def test_classify_does_not_mutate_its_input():
    datum = _datum(
        "Authorization: Bearer 4f4c1b2c3d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a",
        SecretOrigin.CAPTURED,
        provider="acme",
    )
    before = (datum.content, datum.origin, datum.designation, datum.provider)
    classify(datum)
    assert (datum.content, datum.origin, datum.designation, datum.provider) == before


# --- Public surface and ownership (blueprint §10) ---


def test_public_surface_is_exactly_the_owned_vocabulary():
    module = importlib.import_module("episky.secrets.classify")
    assert set(module.__all__) == EXPECTED_PUBLIC_SURFACE


def test_public_names_are_defined_by_classify_py():
    module = importlib.import_module("episky.secrets.classify")
    for name in EXPECTED_PUBLIC_SURFACE:
        value = getattr(module, name)
        if hasattr(value, "__module__"):
            assert value.__module__ == "episky.secrets.classify"
        else:
            assert name in module.__dict__


def test_module_ownership_docstring_names_rfc_0009_and_the_rule():
    doc = importlib.import_module("episky.secrets.classify").__doc__
    assert "RFC-0009" in doc
    assert "never a guess" in doc
    assert "deterministic" in doc.lower()


# --- Dependency rule: the schema and trust edges stay latent (DN-44) ---


def test_classify_py_keeps_the_schema_and_trust_edges_latent():
    src = CLASSIFY_PATH.read_text(encoding="utf-8")
    assert "from episky" not in src
    assert "import schema" not in src
    assert "import trust" not in src
