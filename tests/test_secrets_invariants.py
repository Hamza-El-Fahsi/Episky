"""The complete layer-enforceable secrets invariants (RFC-0009 §28 SC1–SC16;
design review §7 oracle).

Transcribes the normative SC table into layer-enforceable behavioral tests
plus the cross-layer invariants of this iteration: custody and the single
materialization point (SC1), the secret-free default across derived
artifacts (SC2–SC5), one-way consumption at the named boundary (SC6),
purpose-scoping (SC7), the exactly-one owner/custody split (SC8), the
value-free records the Audit may later hold (SC4/SC15), timely and
complete destruction (SC12), determinism and testability (SC13), fail
closed with the Operator told (SC14), exposure = compromise (SC15), and
privacy parity with demotion only by explicit Operator mark (SC16). The
enforcement points for SC9 (no Action carries a secret), SC10 (elevation
exposes nothing), and SC11 (retention by consent) live at
`policy`/`executor`/`audit`; this layer holds their boundaries by
construction — no Action-bearing surface, no display path outside
`consume`, no persistence — and the tests below assert those boundaries
(DN-43). Cross-layer: the trust class is preserved on a crossing (S1, T9)
and becomes Hostile only on a ratified fail-closed withhold; redaction
never re-classifies; metadata never carries a value; and the store refuses
every out-of-scope request with a non-empty reason.
"""

import re
from datetime import date

import pytest

from episky.secrets.classify import (
    NonSecretDesignation,
    SecrecyClass,
    SecretDatum,
    SecretMetadata,
    SecretOrigin,
    classify,
)
from episky.secrets.redact import (
    REDACTION_MARKER,
    RedactionStatus,
    redact,
)
from episky.secrets.store import (
    OPERATOR_OWNER,
    SECURE_STORE_CUSTODIAN,
    Consumer,
    SecureStore,
    StoreStatus,
)
from episky.trust.classes import TrustClass

ALL_CLASSES = tuple(TrustClass)

# Synthetic, obviously-fake token material only (design review §9 #5); the
# sk- prefix matches the prefixed-api-key catalogue shape.
TOKEN = "sk-abcdefghijklmnopqrstuvwxyz0123456789"
PLAIN = "log line about disk usage"
HANDLE = "provider-key"
PURPOSE = "authenticate the provider view"
PROVISIONED_ON = date(2026, 8, 6)
CONSUMED_ON = date(2026, 8, 6)
INVALIDATED_ON = date(2026, 8, 6)
DESTROYED_ON = date(2026, 8, 6)


def _classified(content, origin=SecretOrigin.CAPTURED, designation=None):
    return classify(
        SecretDatum(content=content, origin=origin, designation=designation)
    )


def _secret():
    return _classified(TOKEN, origin=SecretOrigin.PROVISIONED)


def _hostile():
    return _classified(PLAIN, origin=SecretOrigin.CAPTURED)


def _adjacent(content=TOKEN):
    return _classified(content, origin=SecretOrigin.CAPTURED)


def _non_secret():
    return _classified(
        "api-key: this is a public label",
        origin=SecretOrigin.CAPTURED,
        designation=NonSecretDesignation.MECHANISM,
    )


def _store_with(handle=HANDLE, value=TOKEN, purpose=PURPOSE):
    store = SecureStore()
    provision = store.provision(handle, value, purpose, PROVISIONED_ON)
    return store, provision


# --- SC1 — secrets are segregated -----------------------------------------


def test_sc1_provision_holds_the_value_in_custody_only():
    store, provision = _store_with()
    assert provision.status is StoreStatus.OK
    assert TOKEN not in repr(store)
    assert TOKEN not in repr(provision)
    assert TOKEN not in repr(provision.record)
    assert TOKEN not in repr(store.records())


def test_sc1_only_consume_materializes_the_value():
    store, _provision = _store_with()
    consumed = store.consume(HANDLE, Consumer.PROVIDER_ADAPTER, PURPOSE, CONSUMED_ON)
    assert consumed.status is StoreStatus.OK
    assert consumed.value == TOKEN
    assert TOKEN not in repr(store.records())


def test_sc1_the_value_never_leaves_the_boundary_in_any_other_form():
    store, _provision = _store_with()
    invalidated = store.invalidate(HANDLE, "suspected exposure (SC15)", INVALIDATED_ON)
    destroyed = store.destroy(HANDLE, "purpose lapsed (SC12)", DESTROYED_ON)
    for artifact in (invalidated, destroyed):
        assert TOKEN not in repr(artifact)


# --- SC2 — the default is secret-free -------------------------------------


def test_sc2_classification_never_carries_the_value():
    classification = _secret()
    assert TOKEN not in repr(classification)
    assert TOKEN not in repr(classification.metadata)
    with pytest.raises(AttributeError):
        classification.content  # noqa: B018


def test_sc2_metadata_has_no_value_facet():
    assert set(SecretMetadata.__dataclass_fields__) == {
        "existence",
        "provider",
        "provisioned_on",
        "last_used_on",
        "invalidated_on",
    }


def test_sc2_no_derived_artifact_reveals_the_token():
    classification = _adjacent()
    result = redact(TOKEN, classification, TrustClass.UNTRUSTED)
    assert TOKEN not in repr(classification)
    assert TOKEN not in repr(result)
    assert TOKEN not in result.text


# --- SC3 — no secret enters a Provider View -------------------------------


def test_sc3_secret_value_never_crosses_the_boundary():
    for classification in (_secret(), _hostile()):
        result = redact(TOKEN, classification, TrustClass.UNTRUSTED)
        assert result.status is RedactionStatus.WITHHELD
        assert result.text == ""


def test_sc3_secret_adjacent_spans_are_replaced_not_revealed():
    result = redact(TOKEN, _adjacent(), TrustClass.UNTRUSTED)
    assert result.status is RedactionStatus.OK
    assert REDACTION_MARKER in result.text
    assert TOKEN not in result.text


# --- SC4 — no secret enters the Audit -------------------------------------


def test_sc4_records_are_metadata_only_through_the_lifecycle():
    store, provision = _store_with()
    store.consume(HANDLE, Consumer.PROVIDER_ADAPTER, PURPOSE, CONSUMED_ON)
    store.invalidate(HANDLE, "lifecycle", INVALIDATED_ON)
    store.destroy(HANDLE, "lifecycle", DESTROYED_ON)
    assert TOKEN not in repr(provision)
    assert TOKEN not in repr(store.records())


def test_sc4_the_record_carries_only_the_metadata_facets():
    _store, provision = _store_with()
    record = provision.record
    assert set(record.__dataclass_fields__) == {
        "handle",
        "purpose",
        "owner",
        "custodian",
        "classification",
        "provisioned_on",
        "last_used_on",
        "invalidated_on",
    }


# --- SC5 — no secret reaches an extension ---------------------------------


def test_sc5_the_consumer_set_is_exactly_the_provider_adapter():
    assert tuple(Consumer) == (Consumer.PROVIDER_ADAPTER,)


def test_sc5_any_other_consumer_is_refused():
    store, _provision = _store_with()
    refused = store.consume(HANDLE, None, PURPOSE, CONSUMED_ON)
    assert refused.status is StoreStatus.REFUSED
    assert refused.value == ""
    assert refused.reason


# --- SC6 — secrets cross boundaries one way only --------------------------


def test_sc6_consume_is_the_only_value_bearing_operation():
    store, provision = _store_with()
    assert not hasattr(provision, "value")
    assert not hasattr(provision.record, "value")
    destruction = store.destroy(HANDLE, "purpose lapsed (SC12)", DESTROYED_ON)
    assert not hasattr(destruction, "value")


def test_sc6_refused_consumption_crosses_nothing():
    store, _provision = _store_with()
    refused = store.consume(
        "unknown-handle", Consumer.PROVIDER_ADAPTER, PURPOSE, CONSUMED_ON
    )
    assert refused.status is StoreStatus.REFUSED
    assert refused.value == ""


# --- SC7 — every secret is purpose-scoped ---------------------------------


def test_sc7_purpose_is_bound_at_provisioning():
    _store, provision = _store_with()
    assert provision.record.purpose == PURPOSE


def test_sc7_consumption_for_an_unstated_purpose_is_refused():
    store, _provision = _store_with()
    refused = store.consume(
        HANDLE, Consumer.PROVIDER_ADAPTER, "some other purpose", CONSUMED_ON
    )
    assert refused.status is StoreStatus.REFUSED
    assert refused.value == ""
    assert refused.reason
    assert store.records()[0].purpose == PURPOSE


def test_sc7_consumption_for_the_stated_purpose_is_allowed():
    store, _provision = _store_with()
    consumed = store.consume(HANDLE, Consumer.PROVIDER_ADAPTER, PURPOSE, CONSUMED_ON)
    assert consumed.status is StoreStatus.OK
    assert consumed.value == TOKEN


# --- SC8 — every secret has exactly one owner -----------------------------


def test_sc8_every_record_has_exactly_one_owner_and_custodian():
    store = SecureStore()
    for index in range(3):
        store.provision(f"k-{index}", TOKEN, PURPOSE, PROVISIONED_ON)
    for record in store.records():
        assert record.owner == OPERATOR_OWNER
        assert record.custodian == SECURE_STORE_CUSTODIAN


def test_sc8_owner_and_custodian_are_fixed_constants():
    assert OPERATOR_OWNER == "operator"
    assert SECURE_STORE_CUSTODIAN == "secure-store"
    assert OPERATOR_OWNER != SECURE_STORE_CUSTODIAN
    assert Consumer.PROVIDER_ADAPTER.value not in (
        OPERATOR_OWNER,
        SECURE_STORE_CUSTODIAN,
    )


# --- SC9 — no Action carries a secret -------------------------------------


def test_sc9_the_public_surface_carries_no_action_surface():
    from episky.secrets.classify import __all__ as classify_all
    from episky.secrets.redact import __all__ as redact_all
    from episky.secrets.store import __all__ as store_all

    names = set(classify_all) | set(redact_all) | set(store_all)
    assert not {"Action", "Plan", "Proposal"} & names
    assert not any(
        re.search(r"\b(?:action|plan|proposal)\b", name.lower()) for name in names
    )


# --- SC10 — elevation exposes nothing -------------------------------------


def test_sc10_the_value_appears_nowhere_outside_consume():
    store, _provision = _store_with()
    store.consume(HANDLE, Consumer.PROVIDER_ADAPTER, PURPOSE, CONSUMED_ON)
    assert TOKEN not in repr(store)
    assert TOKEN not in repr(store.records())


# --- SC11 — retention is by consent, not by default -----------------------


def test_sc11_the_store_exposes_no_durable_surface():
    store = SecureStore()
    public_methods = {name for name in dir(store) if not name.startswith("_")}
    assert public_methods == {
        "provision",
        "consume",
        "invalidate",
        "destroy",
        "records",
    }


def test_sc11_destroy_leaves_nothing_in_memory():
    store, _provision = _store_with()
    store.destroy(HANDLE, "purpose lapsed (SC12)", DESTROYED_ON)
    assert store.records() == ()


# --- SC12 — destruction is timely and complete ----------------------------


def test_sc12_destroy_removes_value_and_record():
    store, _provision = _store_with()
    destroyed = store.destroy(HANDLE, "purpose lapsed (SC12)", DESTROYED_ON)
    assert destroyed.status is StoreStatus.OK
    assert store.records() == ()
    refused = store.consume(HANDLE, Consumer.PROVIDER_ADAPTER, PURPOSE, CONSUMED_ON)
    assert refused.status is StoreStatus.REFUSED
    assert refused.value == ""


def test_sc12_destruction_records_metadata_never_the_value():
    store, _provision = _store_with()
    destroyed = store.destroy(HANDLE, "purpose lapsed (SC12)", DESTROYED_ON)
    assert destroyed.destroyed_on == DESTROYED_ON
    assert destroyed.reason
    assert TOKEN not in repr(destroyed)


def test_sc12_destroy_of_an_unknown_handle_is_refused():
    destroyed = SecureStore().destroy("ghost", "why", DESTROYED_ON)
    assert destroyed.status is StoreStatus.REFUSED
    assert destroyed.reason


# --- SC13 — redaction is deterministic and testable -----------------------


def test_sc13_classify_is_deterministic():
    datum = SecretDatum(content=TOKEN, origin=SecretOrigin.CAPTURED)
    assert classify(datum) == classify(datum)


def test_sc13_redact_is_deterministic():
    first = redact(TOKEN, _adjacent(), TrustClass.UNTRUSTED)
    second = redact(TOKEN, _adjacent(), TrustClass.UNTRUSTED)
    assert first == second
    assert first.text == second.text


def test_sc13_store_lifecycle_is_deterministic():
    first_store = SecureStore()
    second_store = SecureStore()
    for store in (first_store, second_store):
        store.provision(HANDLE, TOKEN, PURPOSE, PROVISIONED_ON)
        store.consume(HANDLE, Consumer.PROVIDER_ADAPTER, PURPOSE, CONSUMED_ON)
        store.invalidate(HANDLE, "lifecycle", INVALIDATED_ON)
    assert first_store.records() == second_store.records()


# --- SC14 — redaction fails closed ----------------------------------------


def test_sc14_unclassifiable_content_is_withheld_with_a_reason():
    result = redact(PLAIN, _hostile(), TrustClass.TRUSTED)
    assert result.status is RedactionStatus.WITHHELD
    assert result.text == ""
    assert result.reason
    assert "withheld" in result.reason.lower() or "no-secret" in result.reason.lower()


def test_sc14_a_secret_value_is_withheld_with_a_reason():
    result = redact(TOKEN, _secret(), TrustClass.TRUSTED)
    assert result.status is RedactionStatus.WITHHELD
    assert result.text == ""
    assert result.reason


def test_sc14_every_refusal_carries_a_non_empty_reason():
    store, _provision = _store_with()
    refusals = [
        store.consume("ghost", Consumer.PROVIDER_ADAPTER, PURPOSE, CONSUMED_ON),
        store.consume(HANDLE, None, PURPOSE, CONSUMED_ON),
        store.consume(HANDLE, Consumer.PROVIDER_ADAPTER, "other", CONSUMED_ON),
        store.invalidate("ghost", "why", INVALIDATED_ON),
        store.destroy("ghost", "why", DESTROYED_ON),
    ]
    assert all(refusal.status is StoreStatus.REFUSED for refusal in refusals)
    assert all(refusal.reason for refusal in refusals)


# --- SC15 — exposure is compromise ----------------------------------------


def test_sc15_suspected_exposure_invalidates_immediately():
    store, _provision = _store_with()
    store.invalidate(HANDLE, "suspected exposure (SC15)", INVALIDATED_ON)
    refused = store.consume(HANDLE, Consumer.PROVIDER_ADAPTER, PURPOSE, CONSUMED_ON)
    assert refused.status is StoreStatus.REFUSED
    assert refused.value == ""


def test_sc15_invalidation_is_recorded_as_metadata():
    store, _provision = _store_with()
    destruction = store.invalidate(HANDLE, "suspected exposure (SC15)", INVALIDATED_ON)
    assert destruction.status is StoreStatus.OK
    assert destruction.invalidated_on == INVALIDATED_ON
    assert TOKEN not in repr(destruction)
    assert store.records()[0].invalidated_on == INVALIDATED_ON


def test_sc15_an_invalidated_secret_is_refused_at_every_boundary():
    store, _provision = _store_with()
    store.invalidate(HANDLE, "suspected exposure (SC15)", INVALIDATED_ON)
    for _ in range(2):
        refused = store.consume(HANDLE, Consumer.PROVIDER_ADAPTER, PURPOSE, CONSUMED_ON)
        assert refused.status is StoreStatus.REFUSED


# --- SC16 — privacy parity ------------------------------------------------


def test_sc16_marked_content_stays_secret_without_an_explicit_demotion():
    classification = _classified(PLAIN, origin=SecretOrigin.MARKED)
    assert classification.secrecy_class is SecrecyClass.SECRET


def test_sc16_demotion_requires_an_explicit_operator_mark():
    demoted = _classified(
        PLAIN,
        origin=SecretOrigin.MARKED,
        designation=NonSecretDesignation.MARKED_PUBLIC,
    )
    assert demoted.secrecy_class is SecrecyClass.NON_SECRET
    assert demoted.designation is NonSecretDesignation.MARKED_PUBLIC


def test_sc16_no_other_designation_demotes_a_marked_value():
    for designation in tuple(NonSecretDesignation):
        if designation is NonSecretDesignation.MARKED_PUBLIC:
            continue
        with pytest.raises(ValueError):
            _classified(PLAIN, origin=SecretOrigin.MARKED, designation=designation)


def test_sc16_captured_content_is_never_adopted_as_secret():
    classification = _classified(TOKEN, origin=SecretOrigin.CAPTURED)
    assert classification.secrecy_class is SecrecyClass.SECRET_ADJACENT


# --- Cross-layer invariants ------------------------------------------------


def test_cross_layer_trust_class_is_preserved_on_a_crossing():
    for trust_class in ALL_CLASSES:
        result = redact("log line", _non_secret(), trust_class)
        assert result.status is RedactionStatus.OK
        assert result.trust_class is trust_class


def test_cross_layer_trust_never_upgrades():
    for trust_class in ALL_CLASSES:
        result = redact(TOKEN, _adjacent(), trust_class)
        assert result.status is RedactionStatus.OK
        assert result.trust_class is trust_class
        withheld = redact(TOKEN, _secret(), trust_class)
        assert withheld.trust_class is TrustClass.HOSTILE


def test_cross_layer_hostile_only_on_a_fail_closed_withhold():
    for trust_class in ALL_CLASSES:
        for classification in (_secret(), _hostile()):
            result = redact(TOKEN, classification, trust_class)
            assert result.status is RedactionStatus.WITHHELD
            assert result.trust_class is TrustClass.HOSTILE
        for classification in (_adjacent(), _non_secret()):
            result = redact(TOKEN, classification, trust_class)
            assert result.status is RedactionStatus.OK
            assert result.trust_class is trust_class


def test_cross_layer_redaction_never_reclassifies():
    classification = _adjacent()
    result = redact(TOKEN, classification, TrustClass.UNTRUSTED)
    assert result.classification is classification


def test_cross_layer_metadata_never_carries_a_value():
    metadata = _secret().metadata
    assert TOKEN not in repr(metadata)
    assert metadata.existence is True


def test_cross_layer_the_store_returns_a_value_only_at_consume():
    store, provision = _store_with()
    assert not hasattr(provision, "value")
    assert not hasattr(provision.record, "value")
    consumed = store.consume(HANDLE, Consumer.PROVIDER_ADAPTER, PURPOSE, CONSUMED_ON)
    assert consumed.value == TOKEN
    assert TOKEN not in repr(store.records())


def test_cross_layer_consume_after_invalidate_is_refused():
    store, _provision = _store_with()
    store.invalidate(HANDLE, "suspected exposure (SC15)", INVALIDATED_ON)
    refused = store.consume(HANDLE, Consumer.PROVIDER_ADAPTER, PURPOSE, CONSUMED_ON)
    assert refused.status is StoreStatus.REFUSED
    assert refused.value == ""


def test_cross_layer_consume_after_destroy_is_refused():
    store, _provision = _store_with()
    store.destroy(HANDLE, "purpose lapsed (SC12)", DESTROYED_ON)
    refused = store.consume(HANDLE, Consumer.PROVIDER_ADAPTER, PURPOSE, CONSUMED_ON)
    assert refused.status is StoreStatus.REFUSED
    assert refused.value == ""


def test_cross_layer_every_out_of_scope_request_is_refused():
    store, _provision = _store_with()
    cases = [
        store.consume("ghost", Consumer.PROVIDER_ADAPTER, PURPOSE, CONSUMED_ON),
        store.consume(HANDLE, None, PURPOSE, CONSUMED_ON),
        store.consume(HANDLE, Consumer.PROVIDER_ADAPTER, "other", CONSUMED_ON),
        store.invalidate("ghost", "why", INVALIDATED_ON),
        store.destroy("ghost", "why", DESTROYED_ON),
    ]
    assert all(case.status is StoreStatus.REFUSED for case in cases)
    assert all(case.reason for case in cases)


# --- Determinism: identical repeated operations, byte-identical output ----


def test_determinism_repeated_runs_are_byte_identical():
    artifacts = []
    for _ in range(50):
        store = SecureStore()
        store.provision(HANDLE, TOKEN, PURPOSE, PROVISIONED_ON)
        consumed = store.consume(
            HANDLE, Consumer.PROVIDER_ADAPTER, PURPOSE, CONSUMED_ON
        )
        classification = _classified(TOKEN, origin=SecretOrigin.CAPTURED)
        redacted = redact(TOKEN, classification, TrustClass.UNTRUSTED)
        artifacts.append(
            bytes(
                repr(store.records())
                + repr(consumed)
                + repr(classification)
                + repr(redacted)
                + repr(redacted.text),
                encoding="utf-8",
            )
        )
    assert len(set(artifacts)) == 1
