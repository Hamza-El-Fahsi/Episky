"""The complete layer-enforceable Trust model invariants (RFC-0007 §11, §13).

Transcribes RFC-0007's S-principles (S1, S3–S8) and the layer-enforceable
T-invariants (T8, T9, T10, T11, T12; design review §3: the remainder —
T1–T7 — are construction/execution-side and enforced at `core`) plus the
ratified decision notes. What is fixed here: sanitization never upgrades
(S1, T9); the meet rule is monotonic and the composite is never above its
least-trusted part (S2 as transcribed in the Iteration 5 task, §5.1, T8);
content survives neutralization in a form that cannot be read as
direction (S3); the quoted form is contained and visible (S4); secrets
are never classified or inferred — content is never judged (S5, RFC-0009
owns the mechanics); failure fails closed to Hostile with the Operator
told (S6, T11); everything is deterministic (S7); bounding is always
explicitly marked (S8); the label and provenance travel together (T8);
demotion and contagion only go downward (T10, T12); Hostile quarantine
excludes runtime/provider context unconditionally (T11, §15.5); and
Hostile is produced only by the ratified fail-closed paths (DN-39) —
classify on lost provenance of an Observation, and sanitize on lost
provenance — never manufactured by quarantine or contagion.
"""

import pytest

from episky.trust.classes import (
    CATEGORY_DEFAULTS,
    PROVENANCE_LOSS_DEMOTION,
    Classification,
    Datum,
    ProvenanceState,
    TrustCategory,
    TrustClass,
    TrustDomain,
    classify,
    downgrade,
    join,
    meet,
)
from episky.trust.hostile import DisclosureState, Quarantine, contaminate, quarantine
from episky.trust.sanitize import (
    Sanitization,
    SanitizationStatus,
    bound,
    neutralize_control,
    quote,
    sanitize,
    strip_ansi,
    tame_unicode,
)

ALL_CLASSES = tuple(TrustClass)
NON_HOSTILE = tuple(c for c in ALL_CLASSES if c is not TrustClass.HOSTILE)
ALL_CATEGORIES = tuple(TrustCategory)
ALL_PROVENANCE = tuple(ProvenanceState)
ALL_DOMAINS = tuple(TrustDomain)

# RFC-0007 §6.10 (Secrets → RFC-0009): one owner per name (DN-36).
EXPECTED_CATEGORIES = (
    "OBSERVATION",
    "FACT",
    "EVIDENCE",
    "HYPOTHESIS",
    "PROVIDER_OUTPUT",
    "USER_INPUT",
    "CONFIGURATION",
    "LOGS",
    "METADATA",
)


def _datum(
    category=TrustCategory.LOGS,
    content="payload",
    provenance=ProvenanceState.ESTABLISHED,
    origin=TrustDomain.MACHINE,
):
    return Datum(
        category=category, content=content, provenance=provenance, origin=origin
    )


def _quarantine(reason="unclassifiable (RFC-0007 §15.5)"):
    return quarantine(_datum(), TrustClass.HOSTILE, reason)


# --- S1 / T9: sanitization never upgrades; the class is preserved ---


@pytest.mark.parametrize("category", ALL_CATEGORIES)
@pytest.mark.parametrize("trust_class", ALL_CLASSES)
def test_sanitize_never_upgrades_the_trust_class(category, trust_class):
    result = sanitize(
        _datum(category=category, provenance=ProvenanceState.ESTABLISHED),
        trust_class,
    )
    assert result.status is SanitizationStatus.OK
    assert result.trust_class is trust_class


@pytest.mark.parametrize("trust_class", ALL_CLASSES)
def test_sanitize_class_is_at_or_below_the_input_class(trust_class):
    result = sanitize(_datum(provenance=ProvenanceState.ESTABLISHED), trust_class)
    assert result.trust_class.value <= trust_class.value


def test_sanitize_failure_never_upgrades_even_a_trusted_input():
    result = sanitize(_datum(provenance=ProvenanceState.LOST), TrustClass.TRUSTED)
    assert result.trust_class is TrustClass.HOSTILE
    assert result.status is SanitizationStatus.FAILED


# --- S2 / §5.1: the meet rule is monotonic and dominates ---


def test_meet_is_the_most_restrictive_of_the_two():
    for a in ALL_CLASSES:
        for b in ALL_CLASSES:
            result = meet(a, b)
            assert result.value <= a.value
            assert result.value <= b.value


def test_join_is_the_least_restrictive_of_the_two():
    for a in ALL_CLASSES:
        for b in ALL_CLASSES:
            result = join(a, b)
            assert result.value >= a.value
            assert result.value >= b.value


@pytest.mark.parametrize("a", ALL_CLASSES)
@pytest.mark.parametrize("b", ALL_CLASSES)
def test_meet_is_monotonic_in_each_argument(a, b):
    assert meet(a, b).value <= a.value
    assert meet(a, b).value <= b.value
    for c in ALL_CLASSES:
        assert meet(a, c).value <= meet(join(a, b), c).value


def test_meet_is_idempotent_commutative_and_associative():
    for a in ALL_CLASSES:
        for b in ALL_CLASSES:
            for c in ALL_CLASSES:
                assert meet(a, a) is a
                assert meet(a, b) is meet(b, a)
                assert meet(a, meet(b, c)) is meet(meet(a, b), c)


def test_meet_identity_is_trusted_and_absorbing_is_hostile():
    for a in ALL_CLASSES:
        assert meet(a, TrustClass.TRUSTED) is a
        assert meet(a, TrustClass.HOSTILE) is TrustClass.HOSTILE


def test_join_is_idempotent_commutative_and_associative():
    for a in ALL_CLASSES:
        for b in ALL_CLASSES:
            for c in ALL_CLASSES:
                assert join(a, a) is a
                assert join(a, b) is join(b, a)
                assert join(a, join(b, c)) is join(join(a, b), c)


def test_join_identity_is_hostile_and_absorbing_is_trusted():
    for a in ALL_CLASSES:
        assert join(a, TrustClass.HOSTILE) is a
        assert join(a, TrustClass.TRUSTED) is TrustClass.TRUSTED


def test_meet_and_join_satisfy_absorption_and_order_duality():
    for a in ALL_CLASSES:
        for b in ALL_CLASSES:
            assert meet(a, join(a, b)) is a
            assert join(a, meet(a, b)) is a
            assert meet(a, b).value <= join(a, b).value


# --- S3: neutralize control, preserve content ---


def test_strip_ansi_removes_only_escape_sequences():
    assert strip_ansi("before\x1b[31mred\x1b[0mafter") == "beforeredafter"
    assert strip_ansi("plain text") == "plain text"


def test_neutralize_control_escapes_but_never_deletes():
    assert neutralize_control("bell\x07after") == "bell\\x07after"


def test_neutralize_control_preserves_tab_and_newline_layout():
    assert neutralize_control("a\tb\nc") == "a\tb\nc"


def test_tame_unicode_tames_but_never_deletes():
    assert tame_unicode("rev\u202e") == "rev\\u202e"
    assert tame_unicode("zwj\u200dok") == "zwj\\u200dok"


def test_sanitize_preserves_plain_content():
    assert sanitize(_datum(content="hello world"), TrustClass.UNTRUSTED).text == (
        "«hello world»"
    )


def test_sanitize_content_is_neutralized_then_bounded_then_quoted():
    result = sanitize(
        _datum(content="x" * 5000, provenance=ProvenanceState.ESTABLISHED),
        TrustClass.UNTRUSTED,
        limit=100,
    )
    inner = result.text[1:-1]
    assert inner.endswith("…")
    assert len(inner) <= 100 + 1


# --- S4: the quoted representation is contained and visible ---


def test_quote_wraps_content_in_the_visible_contained_form():
    assert quote("apt update") == "«apt update»"
    assert quote("") == "«»"


@pytest.mark.parametrize("category", ALL_CATEGORIES)
def test_sanitize_output_is_always_quoted(category):
    result = sanitize(_datum(category=category), TrustClass.UNTRUSTED)
    assert result.text.startswith("«") and result.text.endswith("»")


# --- S5: secrets are never classified or inferred ---


def test_trust_category_names_no_secret_category():
    names = tuple(c.name for c in ALL_CATEGORIES)
    assert names == EXPECTED_CATEGORIES
    assert all("SECRET" not in name and "CREDENTIAL" not in name for name in names)


def test_classify_is_content_blind():
    a = _datum(content="apt update", category=TrustCategory.LOGS)
    b = _datum(content="sk-abc123 secret", category=TrustCategory.LOGS)
    assert classify(a) == classify(b)


def test_sanitize_is_content_blind_uniform_containment():
    for content in (
        "apt update",
        "sk-abcdefghij123456",
        "password=hunter2",
        "BEGIN RSA PRIVATE KEY-----",
        "AKIAIOSFODNN7EXAMPLE",
    ):
        result = sanitize(_datum(content=content), TrustClass.UNTRUSTED)
        assert result.trust_class is TrustClass.UNTRUSTED
        assert result.status is SanitizationStatus.OK


def test_no_public_surface_names_a_secret_concern():
    from episky.trust.classes import __all__ as classes_all
    from episky.trust.hostile import __all__ as hostile_all
    from episky.trust.sanitize import __all__ as sanitize_all

    names = set(classes_all) | set(sanitize_all) | set(hostile_all)
    assert all("secret" not in name.lower() for name in names)


# --- S6 / T11: failure fails closed to Hostile, and the Operator is told ---


@pytest.mark.parametrize("category", ALL_CATEGORIES)
def test_classify_never_treats_lost_provenance_as_benign(category):
    result = classify(_datum(category=category, provenance=ProvenanceState.LOST))
    assert result.trust_class is not TrustClass.TRUSTED
    assert result.trust_class is not TrustClass.CONDITIONAL


@pytest.mark.parametrize("trust_class", ALL_CLASSES)
def test_sanitize_fails_closed_to_hostile_on_lost_provenance(trust_class):
    result = sanitize(_datum(provenance=ProvenanceState.LOST), trust_class)
    assert result.status is SanitizationStatus.FAILED
    assert result.trust_class is TrustClass.HOSTILE
    assert "provenance" in result.reason.lower()


def test_sanitize_failure_is_quarantinable():
    result = sanitize(_datum(provenance=ProvenanceState.LOST), TrustClass.TRUSTED)
    record = quarantine(
        _datum(provenance=ProvenanceState.LOST), result.trust_class, result.reason
    )
    assert record.trust_class is TrustClass.HOSTILE
    assert record.reason  # the Operator is told why


# --- S7: determinism ---


def test_classify_is_deterministic():
    datum = _datum(category=TrustCategory.OBSERVATION, provenance=ProvenanceState.LOST)
    assert classify(datum) == classify(datum)


def test_sanitize_is_deterministic():
    datum = _datum(content="a\x1b[31mb\x07c")
    first = sanitize(datum, TrustClass.UNTRUSTED)
    second = sanitize(datum, TrustClass.UNTRUSTED)
    assert first == second
    assert first.text == second.text
    assert first.trust_class is second.trust_class


def test_downgrade_quarantine_and_contaminate_are_deterministic():
    assert downgrade(TrustClass.TRUSTED, "why") == downgrade(TrustClass.TRUSTED, "why")
    record = _quarantine()
    assert quarantine(record.datum, TrustClass.HOSTILE, record.reason) == record
    assert contaminate(record, TrustClass.TRUSTED) == contaminate(
        record, TrustClass.TRUSTED
    )


# --- S8: bounding always marks truncation ---


def test_bound_marks_truncation_with_an_explicit_marker():
    assert bound("x" * 20, 5) == "xxxxx…"


def test_bound_returns_short_text_unchanged():
    assert bound("short", 10) == "short"
    assert bound("exactly", 7) == "exactly"


def test_bound_rejects_a_non_positive_limit():
    with pytest.raises(ValueError):
        bound("text", 0)


def test_sanitize_bounds_and_marks_when_content_overflows():
    result = sanitize(_datum(content="y" * 300), TrustClass.UNTRUSTED, limit=10)
    assert result.text == "«yyyyyyyyyy…»"


# --- T8: the trust label and provenance travel together ---


def test_classify_carries_category_origin_provenance_and_reason():
    datum = _datum(category=TrustCategory.LOGS, provenance=ProvenanceState.ESTABLISHED)
    result = classify(datum)
    assert isinstance(result, Classification)
    assert result.category is datum.category
    assert result.origin is datum.origin
    assert result.provenance is datum.provenance
    assert result.reason


def test_sanitize_carries_the_label_and_provenance():
    datum = _datum(category=TrustCategory.LOGS, origin=TrustDomain.MACHINE)
    result = sanitize(datum, TrustClass.UNTRUSTED)
    assert isinstance(result, Sanitization)
    assert result.provenance is datum.provenance
    assert result.origin is datum.origin
    assert result.trust_class is TrustClass.UNTRUSTED
    assert result.reason


def test_classify_sanitize_quarantine_preserves_provenance_through_the_chain():
    datum = _datum(
        category=TrustCategory.OBSERVATION,
        content="unverifiable output",
        provenance=ProvenanceState.LOST,
        origin=TrustDomain.DIAGNOSTICS,
    )
    classification = classify(datum)
    assert classification.trust_class is TrustClass.HOSTILE
    sanitization = sanitize(datum, classification.trust_class)
    assert sanitization.provenance is datum.provenance
    assert sanitization.origin is datum.origin
    assert sanitization.trust_class is TrustClass.HOSTILE
    record = quarantine(datum, sanitization.trust_class, sanitization.reason)
    assert record.datum == datum
    assert record.datum.provenance is datum.provenance


# --- T10: demotion is monotonic ---


@pytest.mark.parametrize("trust_class", ALL_CLASSES)
def test_downgrade_never_upgrades(trust_class):
    result = downgrade(trust_class, "stale")
    assert result.trust_class.value <= trust_class.value


def test_downgrade_steps_one_class_down_to_the_hostile_floor():
    assert downgrade(TrustClass.TRUSTED, "r").trust_class is TrustClass.CONDITIONAL
    assert downgrade(TrustClass.CONDITIONAL, "r").trust_class is TrustClass.UNTRUSTED
    assert downgrade(TrustClass.UNTRUSTED, "r").trust_class is TrustClass.HOSTILE
    assert downgrade(TrustClass.HOSTILE, "r").trust_class is TrustClass.HOSTILE


def test_downgrade_preserves_the_reason():
    assert downgrade(TrustClass.TRUSTED, "expired").reason == "expired"


def test_downgrade_rejects_an_empty_reason():
    with pytest.raises(ValueError):
        downgrade(TrustClass.TRUSTED, "")


def test_repeated_downgrade_reaches_and_stays_at_hostile():
    for start in ALL_CLASSES:
        result = start
        for _ in range(5):
            result = downgrade(result, "repeat").trust_class
        assert result is TrustClass.HOSTILE


def test_downgrade_is_monotonic_in_its_input():
    for a in ALL_CLASSES:
        for b in ALL_CLASSES:
            if a.value <= b.value:
                assert (
                    downgrade(a, "r").trust_class.value
                    <= downgrade(b, "r").trust_class.value
                )


# --- T11: Hostile quarantine excludes runtime/provider context ---


@pytest.mark.parametrize("trust_class", NON_HOSTILE)
def test_quarantine_accepts_only_hostile(trust_class):
    with pytest.raises(ValueError):
        quarantine(_datum(), trust_class, "reason")


def test_quarantine_exclusion_is_unconditional():
    record = _quarantine()
    assert record.excluded is True
    with pytest.raises(AttributeError):
        record.excluded = False  # frozen: no non-excluded quarantine exists


def test_quarantine_carries_no_runtime_or_provider_reference():
    record = _quarantine()
    assert isinstance(record, Quarantine)
    assert list(record.__dataclass_fields__) == [
        "datum",
        "trust_class",
        "reason",
        "disclosure",
    ]


def test_quarantined_content_is_excluded_from_context_semantics():
    record = _quarantine()
    assert record.excluded is True
    assert record.disclosure in (DisclosureState.WITHHELD, DisclosureState.DISCLOSED)


# --- T12: suspicion is contagious downward, never upward ---


@pytest.mark.parametrize("trust_class", ALL_CLASSES)
def test_contaminate_never_upgrades(trust_class):
    result = contaminate(_quarantine(), trust_class)
    assert result.trust_class.value <= trust_class.value


def test_contaminate_downgrades_by_exactly_one_step_downward():
    record = _quarantine()
    assert contaminate(record, TrustClass.TRUSTED).trust_class is TrustClass.CONDITIONAL
    assert (
        contaminate(record, TrustClass.CONDITIONAL).trust_class is TrustClass.UNTRUSTED
    )
    assert contaminate(record, TrustClass.UNTRUSTED).trust_class is TrustClass.UNTRUSTED
    assert contaminate(record, TrustClass.HOSTILE).trust_class is TrustClass.HOSTILE


@pytest.mark.parametrize("trust_class", NON_HOSTILE)
def test_contaminate_never_manufactures_hostile(trust_class):
    result = contaminate(_quarantine(), trust_class)
    assert result.trust_class is not TrustClass.HOSTILE


def test_contaminate_carries_the_source_reason():
    record = _quarantine(reason="contained attempt (RFC-0007 §15.8)")
    result = contaminate(record, TrustClass.TRUSTED)
    assert "contained attempt" in result.reason


# --- DN-39: Hostile is produced only by the ratified fail-closed paths ---


@pytest.mark.parametrize("category", ALL_CATEGORIES)
@pytest.mark.parametrize("provenance", ALL_PROVENANCE)
def test_classify_hostile_exactly_on_lost_provenance_observation(category, provenance):
    result = classify(_datum(category=category, provenance=provenance))
    expected = (
        provenance is ProvenanceState.LOST and category is TrustCategory.OBSERVATION
    )
    assert (result.trust_class is TrustClass.HOSTILE) == expected


@pytest.mark.parametrize("category", ALL_CATEGORIES)
@pytest.mark.parametrize("provenance", ALL_PROVENANCE)
def test_sanitize_hostile_exactly_on_lost_provenance(category, provenance):
    result = sanitize(
        _datum(category=category, provenance=provenance), TrustClass.TRUSTED
    )
    assert (result.trust_class is TrustClass.HOSTILE) == (
        provenance is ProvenanceState.LOST
    )


def test_quarantine_never_manufactures_hostile():
    with pytest.raises(ValueError):
        quarantine(_datum(), TrustClass.UNTRUSTED, "reason")


def test_no_public_api_assigns_hostile_outside_the_fail_closed_paths():
    for category in ALL_CATEGORIES:
        assert CATEGORY_DEFAULTS[category] is not TrustClass.HOSTILE
    for category in ALL_CATEGORIES:
        demotion = PROVENANCE_LOSS_DEMOTION[category]
        assert (demotion is TrustClass.HOSTILE) == (
            category is TrustCategory.OBSERVATION
        )
