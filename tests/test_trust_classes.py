"""Trust classes, lattice, and classification (RFC-0007 §4, §5, §6, §9).

Behavioral tests for Iteration 5 Commit C1 (`trust/classes.py`): the
four-class vocabulary in the §5 order (DN-36), the twelve §4 domains and
their postures, the nine in-scope §6 categories and their default
classes, the §5.1 lattice (meet/join, most-restrictive), the
reason-preserving `downgrade` (§9), and deterministic `classify` over
the abstract datum (DN-37) — fail-closed to Hostile on the layer's
provenance-loss path (T11, DN-39), never upgrading above the category
default (T6, Q4), and granting no authority (RFC-0004 §7).
"""

import ast
import importlib
import pathlib
import sys

import pytest

from episky.trust.classes import (
    CATEGORY_DEFAULTS,
    CATEGORY_ORIGINS,
    PROVENANCE_LOSS_DEMOTION,
    TRUST_DOMAIN_POSTURES,
    Classification,
    Datum,
    Demotion,
    ProvenanceState,
    TrustCategory,
    TrustClass,
    TrustDomain,
    classify,
    downgrade,
    join,
    meet,
)

CLASSES_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "trust"
    / "classes.py"
)

# RFC-0007 §5 order, top to bottom.
FIVE_CLASSES = (
    TrustClass.TRUSTED,
    TrustClass.CONDITIONAL,
    TrustClass.UNTRUSTED,
    TrustClass.HOSTILE,
)

# RFC-0007 §4 order, transcribed.
FOURTEEN_DOMAINS = (
    TrustDomain.OPERATOR,
    TrustDomain.CORE,
    TrustDomain.DIAGNOSTICS,
    TrustDomain.POLICY_ENGINE,
    TrustDomain.ACTION_EXECUTOR,
    TrustDomain.PROVIDER,
    TrustDomain.LOCAL_MODEL,
    TrustDomain.COMMUNITY_SKILLS,
    TrustDomain.MACHINE,
    TrustDomain.FILESYSTEM,
    TrustDomain.EXTERNAL_NETWORK,
    TrustDomain.EXTERNAL_DOCUMENTATION,
)

# RFC-0007 §6.1–§6.9 order, transcribed.
NINE_CATEGORIES = (
    TrustCategory.OBSERVATION,
    TrustCategory.FACT,
    TrustCategory.EVIDENCE,
    TrustCategory.HYPOTHESIS,
    TrustCategory.PROVIDER_OUTPUT,
    TrustCategory.USER_INPUT,
    TrustCategory.CONFIGURATION,
    TrustCategory.LOGS,
    TrustCategory.METADATA,
)

# The §6 "Default" column, transcribed exactly (EVIDENCE: the §5.1 meet
# identity; USER_INPUT: the literal-text class).
EXPECTED_DEFAULTS = {
    TrustCategory.OBSERVATION: TrustClass.UNTRUSTED,
    TrustCategory.FACT: TrustClass.TRUSTED,
    TrustCategory.EVIDENCE: TrustClass.TRUSTED,
    TrustCategory.HYPOTHESIS: TrustClass.UNTRUSTED,
    TrustCategory.PROVIDER_OUTPUT: TrustClass.UNTRUSTED,
    TrustCategory.USER_INPUT: TrustClass.UNTRUSTED,
    TrustCategory.CONFIGURATION: TrustClass.UNTRUSTED,
    TrustCategory.LOGS: TrustClass.UNTRUSTED,
    TrustCategory.METADATA: TrustClass.UNTRUSTED,
}

# The §4 "Default posture" column, transcribed exactly.
EXPECTED_POSTURES = {
    TrustDomain.OPERATOR: "Trusted for intent; untrusted as literal text",
    TrustDomain.CORE: "Trusted within scope (RFC-0001 §7)",
    TrustDomain.DIAGNOSTICS: (
        "Trusted for its output contract; untrusted in its raw reading"
    ),
    TrustDomain.POLICY_ENGINE: "Trusted within scope",
    TrustDomain.ACTION_EXECUTOR: "Trusted within scope",
    TrustDomain.PROVIDER: "Untrusted (RFC-0001 §7)",
    TrustDomain.LOCAL_MODEL: "Untrusted, same as any Provider",
    TrustDomain.COMMUNITY_SKILLS: "Untrusted by default",
    TrustDomain.MACHINE: "Untrusted",
    TrustDomain.FILESYSTEM: "Untrusted",
    TrustDomain.EXTERNAL_NETWORK: "Untrusted",
    TrustDomain.EXTERNAL_DOCUMENTATION: ("Untrusted as text; consulted as information"),
}

# The §9.6 demotion on loss of provenance, per DN-39 path (3).
EXPECTED_PROVENANCE_LOSS = {
    TrustCategory.OBSERVATION: TrustClass.HOSTILE,
    TrustCategory.FACT: TrustClass.UNTRUSTED,
    TrustCategory.EVIDENCE: TrustClass.UNTRUSTED,
    TrustCategory.HYPOTHESIS: TrustClass.UNTRUSTED,
    TrustCategory.PROVIDER_OUTPUT: TrustClass.UNTRUSTED,
    TrustCategory.USER_INPUT: TrustClass.UNTRUSTED,
    TrustCategory.CONFIGURATION: TrustClass.UNTRUSTED,
    TrustCategory.LOGS: TrustClass.UNTRUSTED,
    TrustCategory.METADATA: TrustClass.UNTRUSTED,
}

# The owned public surface of classes.py.
EXPECTED_PUBLIC_SURFACE = {
    "CATEGORY_DEFAULTS",
    "CATEGORY_ORIGINS",
    "Classification",
    "Datum",
    "Demotion",
    "PROVENANCE_LOSS_DEMOTION",
    "ProvenanceState",
    "TRUST_DOMAIN_POSTURES",
    "TrustCategory",
    "TrustClass",
    "TrustDomain",
    "classify",
    "downgrade",
    "join",
    "meet",
}


def _datum(category, provenance, origin=TrustDomain.MACHINE, content="text"):
    return Datum(
        category=category, content=content, provenance=provenance, origin=origin
    )


# --- Vocabulary: completeness and ordering (DN-36) ---


def test_trust_class_has_exactly_four_members_in_section_five_order():
    assert tuple(TrustClass) == FIVE_CLASSES


def test_trust_class_values_encode_the_section_five_total_order():
    assert (
        TrustClass.TRUSTED.value
        > TrustClass.CONDITIONAL.value
        > TrustClass.UNTRUSTED.value
        > TrustClass.HOSTILE.value
    )


def test_trust_domain_has_exactly_the_twelve_section_four_domains():
    assert tuple(TrustDomain) == FOURTEEN_DOMAINS


def test_trust_category_has_exactly_the_nine_in_scope_categories():
    assert tuple(TrustCategory) == NINE_CATEGORIES


def test_owned_elsewhere_categories_are_not_defined_here():
    names = {c.name for c in TrustCategory}
    assert "SECRETS" not in names
    assert "SKILL_MANIFEST" not in names
    assert "SKILL_CODE" not in names


# --- Vocabulary data (DN-36): defaults, postures, origins ---


def test_category_defaults_match_section_six_exactly():
    assert dict(CATEGORY_DEFAULTS) == EXPECTED_DEFAULTS


def test_domain_postures_match_section_four_exactly():
    assert dict(TRUST_DOMAIN_POSTURES) == EXPECTED_POSTURES


def test_provenance_loss_demotion_matches_dn_39():
    assert dict(PROVENANCE_LOSS_DEMOTION) == EXPECTED_PROVENANCE_LOSS
    assert PROVENANCE_LOSS_DEMOTION[TrustCategory.OBSERVATION] is (TrustClass.HOSTILE)


def test_every_category_has_an_origin_domain():
    assert set(CATEGORY_ORIGINS) == set(TrustCategory)
    for category, origins in CATEGORY_ORIGINS.items():
        assert origins, f"{category.name} has no origin domain"
        for origin in origins:
            assert isinstance(origin, TrustDomain)


def test_fact_is_never_llm_authored():
    assert TrustDomain.PROVIDER not in CATEGORY_ORIGINS[TrustCategory.FACT]
    assert TrustDomain.LOCAL_MODEL not in CATEGORY_ORIGINS[TrustCategory.FACT]


def test_provider_output_originates_in_provider_domains_only():
    origins = set(CATEGORY_ORIGINS[TrustCategory.PROVIDER_OUTPUT])
    assert origins == {TrustDomain.PROVIDER, TrustDomain.LOCAL_MODEL}


# --- Lattice: meet/join (§5.1, T8) ---


@pytest.mark.parametrize("a", FIVE_CLASSES)
@pytest.mark.parametrize("b", FIVE_CLASSES)
def test_meet_is_the_most_restrictive_class(a, b):
    result = meet(a, b)
    assert result is (a if a.value <= b.value else b)
    assert result.value == min(a.value, b.value)


@pytest.mark.parametrize("a", FIVE_CLASSES)
@pytest.mark.parametrize("b", FIVE_CLASSES)
def test_join_is_the_least_restrictive_class(a, b):
    result = join(a, b)
    assert result.value == max(a.value, b.value)
    assert result in (a, b)


def test_meet_with_hostile_is_hostile():
    for cls in FIVE_CLASSES:
        assert meet(cls, TrustClass.HOSTILE) is TrustClass.HOSTILE


def test_meet_with_trusted_is_itself():
    for cls in FIVE_CLASSES:
        assert meet(cls, TrustClass.TRUSTED) is cls


def test_meet_untrusted_plus_trusted_is_untrusted():
    assert meet(TrustClass.UNTRUSTED, TrustClass.TRUSTED) is (TrustClass.UNTRUSTED)


def test_join_returns_one_of_its_operands_and_grants_nothing():
    for a in FIVE_CLASSES:
        for b in FIVE_CLASSES:
            result = join(a, b)
            assert result in (a, b)
            assert result.value <= max(a.value, b.value)


def test_join_is_not_an_upgrade_for_an_all_untrusted_composite():
    assert join(TrustClass.UNTRUSTED, TrustClass.HOSTILE) is (TrustClass.UNTRUSTED)


def test_lattice_operations_are_idempotent_and_symmetric():
    for cls in FIVE_CLASSES:
        assert meet(cls, cls) is cls
        assert join(cls, cls) is cls
    for a in FIVE_CLASSES:
        for b in FIVE_CLASSES:
            assert meet(a, b) is meet(b, a)
            assert join(a, b) is join(b, a)


# --- Demotion: downgrade (§9) ---


@pytest.mark.parametrize(
    ("cls", "expected"),
    [
        (TrustClass.TRUSTED, TrustClass.CONDITIONAL),
        (TrustClass.CONDITIONAL, TrustClass.UNTRUSTED),
        (TrustClass.UNTRUSTED, TrustClass.HOSTILE),
        (TrustClass.HOSTILE, TrustClass.HOSTILE),
    ],
)
def test_downgrade_is_the_one_step_demotion_primitive(cls, expected):
    result = downgrade(cls, "reason")
    assert isinstance(result, Demotion)
    assert result.trust_class is expected


@pytest.mark.parametrize("cls", FIVE_CLASSES)
def test_downgrade_is_monotonic(cls):
    assert downgrade(cls, "reason").trust_class.value <= cls.value


def test_downgrade_preserves_the_reason():
    reason = "stale (RFC-0007 §9.1)"
    result = downgrade(TrustClass.TRUSTED, reason)
    assert result.reason == reason


def test_downgrade_rejects_an_empty_reason():
    with pytest.raises(ValueError):
        downgrade(TrustClass.TRUSTED, "")


def test_downgrade_is_deterministic():
    for cls in FIVE_CLASSES:
        first = downgrade(cls, "reason")
        second = downgrade(cls, "reason")
        assert first == second


# --- Classification: classify (DN-37; §6, §9.6) ---


def test_classify_uses_the_category_default_when_provenance_established():
    for category in TrustCategory:
        result = classify(_datum(category, ProvenanceState.ESTABLISHED))
        assert result.trust_class is CATEGORY_DEFAULTS[category]


def test_classify_demotes_on_loss_of_provenance():
    for category in TrustCategory:
        result = classify(_datum(category, ProvenanceState.LOST))
        assert result.trust_class is PROVENANCE_LOSS_DEMOTION[category]


def test_unclassifiable_datum_fails_closed_to_hostile():
    result = classify(_datum(TrustCategory.OBSERVATION, ProvenanceState.LOST))
    assert result.trust_class is TrustClass.HOSTILE


def test_no_category_default_is_hostile():
    for category in TrustCategory:
        result = classify(_datum(category, ProvenanceState.ESTABLISHED))
        assert result.trust_class is not TrustClass.HOSTILE


def test_classify_never_upgrades_above_the_category_default():
    for category in TrustCategory:
        for provenance in ProvenanceState:
            result = classify(_datum(category, provenance))
            assert result.trust_class.value <= CATEGORY_DEFAULTS[category].value


def test_classification_carries_the_label_and_reason():
    datum = _datum(TrustCategory.FACT, ProvenanceState.ESTABLISHED)
    result = classify(datum)
    assert isinstance(result, Classification)
    assert result.category is datum.category
    assert result.origin is datum.origin
    assert result.provenance is datum.provenance
    assert "category default" in result.reason


def test_provenance_loss_reason_is_recorded():
    result = classify(_datum(TrustCategory.OBSERVATION, ProvenanceState.LOST))
    assert "loss of provenance" in result.reason


def test_classify_is_deterministic():
    datum = _datum(TrustCategory.LOGS, ProvenanceState.ESTABLISHED)
    assert classify(datum) == classify(datum)
    assert classify(datum).reason == classify(datum).reason


def test_classify_origin_does_not_change_the_class():
    for origin in TrustDomain:
        a = classify(_datum(TrustCategory.LOGS, ProvenanceState.ESTABLISHED))
        b = classify(
            _datum(TrustCategory.LOGS, ProvenanceState.ESTABLISHED, origin=origin)
        )
        assert a.trust_class is b.trust_class


# --- No promotion (T6; Q4) and no authority (RFC-0004 §7) ---


def test_no_promote_surface_exists():
    module = importlib.import_module("episky.trust.classes")
    assert not hasattr(module, "promote")
    assert "promote" not in module.__all__
    for container in (
        TrustClass,
        TrustDomain,
        TrustCategory,
        ProvenanceState,
    ):
        assert not hasattr(container, "promote")


def test_no_operation_upgrades_a_class():
    for cls in FIVE_CLASSES:
        assert meet(cls, cls).value <= cls.value
        assert downgrade(cls, "reason").trust_class.value <= cls.value
    assert join(TrustClass.UNTRUSTED, TrustClass.HOSTILE).value <= (
        TrustClass.UNTRUSTED.value
    )


# --- Records are frozen and slot-based; tables are immutable ---


def test_datum_is_frozen_and_slotted():
    assert Datum.__dataclass_params__.frozen
    assert Datum.__dataclass_params__.slots


def test_classification_is_frozen_and_slotted():
    assert Classification.__dataclass_params__.frozen
    assert Classification.__dataclass_params__.slots


def test_demotion_is_frozen_and_slotted():
    assert Demotion.__dataclass_params__.frozen
    assert Demotion.__dataclass_params__.slots


def test_records_cannot_be_mutated():
    datum = _datum(TrustCategory.FACT, ProvenanceState.ESTABLISHED)
    with pytest.raises(AttributeError):
        datum.content = "changed"
    result = classify(datum)
    with pytest.raises(AttributeError):
        result.trust_class = TrustClass.UNTRUSTED


def test_data_tables_are_immutable():
    with pytest.raises(TypeError):
        TRUST_DOMAIN_POSTURES[TrustDomain.MACHINE] = "Trusted"
    with pytest.raises(TypeError):
        CATEGORY_DEFAULTS[TrustCategory.LOGS] = TrustClass.TRUSTED
    with pytest.raises(TypeError):
        PROVENANCE_LOSS_DEMOTION[TrustCategory.LOGS] = TrustClass.TRUSTED
    with pytest.raises(TypeError):
        CATEGORY_ORIGINS[TrustCategory.LOGS] = (TrustDomain.CORE,)


# --- Public surface and ownership (blueprint §10) ---


def test_public_surface_is_exactly_the_owned_vocabulary():
    module = importlib.import_module("episky.trust.classes")
    assert set(module.__all__) == EXPECTED_PUBLIC_SURFACE


def test_public_names_are_defined_by_classes_py():
    module = importlib.import_module("episky.trust.classes")
    for name in EXPECTED_PUBLIC_SURFACE:
        value = getattr(module, name)
        if hasattr(value, "__module__"):
            assert value.__module__ == "episky.trust.classes"
        else:
            assert name in module.__dict__


# --- Dependency rule: stdlib only, the schema edge stays latent (DN-37) ---


def test_classes_py_imports_only_the_standard_library():
    tree = ast.parse(CLASSES_PATH.read_text(encoding="utf-8"))
    for node in ast.walk(tree):
        if isinstance(node, ast.Import):
            for alias in node.names:
                assert alias.name.split(".")[0] in sys.stdlib_module_names
        elif isinstance(node, ast.ImportFrom):
            assert node.level == 0, "no relative imports"
            assert node.module.split(".")[0] in sys.stdlib_module_names
