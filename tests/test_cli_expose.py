"""C3 expose tests — the on-demand audit log and context view (RFC-0001 §5).

Iteration 12 Commit C3. Asserts the ratified readings of design-review §14 C3:
the audit log is presented as §8 transcript entries derived via
``audit.transcript.render`` (RFC-0013 §8; AU2), read-only and metadata-only
(SC4) — never a value, never the opaque machine-state reference (RFC-0013
§10); the context view is the §13 Provider View outcome (RFC-0012 §13; DN-100)
carried exactly as `context` derived it (SC3; PR14; I-9); deterministic
(RFC-0007 S7); the CLI never reads the store or the Context directly (DN-100).
"""

from datetime import datetime

from episky.audit.records import (
    ApprovalDecision,
    ApprovalRecord,
    ExecutionPhase,
    ExecutionRecord,
    RecordCategory,
    SecretEvent,
    SecretMetadataRecord,
)
from episky.audit.store import AuditStore
from episky.audit.transcript import TranscriptCategory
from episky.cli.expose import PresentedLog, PresentedView, audit_log, context_view
from episky.context.provider_view import (
    ProviderView,
    ProviderViewOutcome,
    ViewDisposition,
    ViewRefusal,
)
from episky.secrets.classify import SecretMetadata

NOW = datetime(2026, 8, 11, 12, 0, 0)


def _execution(record_id="rec-1", phase=ExecutionPhase.START):
    return ExecutionRecord(
        record_id=record_id,
        recorded_at=NOW,
        category=RecordCategory.EXECUTION,
        phase=phase,
        action_id="action-1",
        argv=("apt", "install", "--yes", "nvidia-driver"),
        machine_state="snapshot-1",
    )


def _approval(record_id="rec-2"):
    return ApprovalRecord(
        record_id=record_id,
        recorded_at=NOW,
        category=RecordCategory.APPROVAL,
        decision=ApprovalDecision.APPROVAL,
        action_id="action-1",
        risk_class="consequential",
        gate="confirm",
    )


def _secret(record_id="rec-3"):
    return SecretMetadataRecord(
        record_id=record_id,
        recorded_at=NOW,
        category=RecordCategory.SECRET_METADATA,
        event=SecretEvent.USED,
        handle="provider-key",
        metadata=SecretMetadata(existence=True, provider="ollama"),
    )


def _view():
    from episky.context.assemble import GoalValue, RoutingMarker

    return ProviderView(
        goal=GoalValue(statement="repair the boot", scope="boot configuration"),
        facts=(),
        history=(),
        evidence=(),
        routing=RoutingMarker(outstanding_question=None, current_decision="d1"),
    )


def _derived_outcome():
    return ProviderViewOutcome(
        view=_view(),
        disposition=ViewDisposition.DERIVED,
        refusal=None,
        reason="derived",
    )


def _refused_outcome():
    return ProviderViewOutcome(
        view=None,
        disposition=ViewDisposition.REFUSED,
        refusal=ViewRefusal.MALFORMED,
        reason="blank goal statement",
    )


# ---------------------------------------------------------------------------
# The audit log (RFC-0013 §8; AU2; SC4)
# ---------------------------------------------------------------------------


def test_log_renders_each_record_to_one_entry_in_order():
    log = audit_log([_execution(), _approval(), _secret()])
    assert isinstance(log, PresentedLog)
    assert [e.record_id for e in log.entries] == ["rec-1", "rec-2", "rec-3"]
    assert all(hasattr(e, "text") and e.text for e in log.entries)


def test_entries_carry_the_expected_transcript_categories():
    log = audit_log([_execution(), _approval(), _secret()])
    assert log.entries[0].category is TranscriptCategory.ACTIONS_AND_OUTCOMES
    assert log.entries[1].category is TranscriptCategory.DECISIONS_AND_GROUNDS
    assert log.entries[2].category is TranscriptCategory.DISCLOSURES


def test_machine_state_reference_is_never_rendered():
    # The opaque machine-state reference "may hold material" (RFC-0013 §10)
    # and is never interpreted or rendered.
    (entry,) = audit_log([_execution()]).entries
    assert "snapshot-1" not in entry.text


def test_secret_record_is_metadata_only():
    (entry,) = audit_log([_secret()]).entries
    # The handle is metadata (SC4): a name that identifies, never a value.
    assert entry.category is TranscriptCategory.DISCLOSURES
    assert "provider-key" in entry.text


def test_log_is_read_only_and_deterministic():
    store = AuditStore()
    store.append(_execution())
    store.append(_approval())
    records = tuple(store)
    size_before = len(store)
    first = audit_log(records)
    second = audit_log(records)
    assert len(store) == size_before
    assert first == second
    assert first.entries == second.entries


# ---------------------------------------------------------------------------
# The context view (RFC-0012 §13; DN-100; I-9)
# ---------------------------------------------------------------------------


def test_derived_view_is_carried_as_is():
    outcome = _derived_outcome()
    presented = context_view(outcome)
    assert isinstance(presented, PresentedView)
    assert presented.view is outcome.view
    assert presented.disposition is ViewDisposition.DERIVED
    assert presented.refusal is None
    assert presented.reason == "derived"


def test_refusal_is_disclosed_not_invented():
    outcome = _refused_outcome()
    presented = context_view(outcome)
    assert presented.view is None
    assert presented.disposition is ViewDisposition.REFUSED
    assert presented.refusal is ViewRefusal.MALFORMED
    assert presented.reason == "blank goal statement"


def test_context_view_is_deterministic():
    outcome = _derived_outcome()
    assert context_view(outcome) == context_view(outcome)
