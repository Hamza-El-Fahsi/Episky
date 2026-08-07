"""Deterministic transcript derivation from the record (RFC-0013 §2, §5, §8;
AU2, AU5; DN-64).

Behavioral tests for Iteration 8 Commit C2 (`audit/transcript.py`): the
deterministic derivation function transcript = render(record) producing the
§8 categories (RFC-0013 §8) from the record *only* — never material the
record does not hold (AU2). Each record type renders into its §8 category
with a stable, category-specific format: the execution record (cat. 6) as
actions and outcomes (argv in its sanitized, argv-structured form, never a
shell string), the approval / auto-permit / rejection and override records
(cat. 4/5) as decisions and their grounds, and the secret-metadata record
(cat. 10) as a disclosure (metadata only, never a value; SC4). Rendering is
pure and deterministic (AU5): identical records render identical entries,
and render is a one-record-to-one-entry function whose output never depends
on object identity, a clock, or a random source. Unknown record types fail
closed. The presentation *form* is RFC-0015's (DN-64); the derived entry
itself is frozen and slot-based (DN-34).
"""

import pathlib
from dataclasses import FrozenInstanceError
from datetime import datetime

import pytest

import episky.audit.transcript as transcript_module
from episky.audit.records import (
    ApprovalDecision,
    ApprovalRecord,
    AuditRecord,
    ExecutionPhase,
    ExecutionRecord,
    OverrideRecord,
    RecordCategory,
    SecretEvent,
    SecretMetadataRecord,
)
from episky.audit.transcript import TranscriptCategory, TranscriptEntry, render
from episky.secrets.classify import SecretMetadata

TRANSCRIPT_PATH = (
    pathlib.Path(__file__).resolve().parents[1]
    / "src"
    / "episky"
    / "audit"
    / "transcript.py"
)

NOW = datetime(2026, 8, 7, 12, 0, 0)


def _execution(
    record_id="rec-1",
    phase=ExecutionPhase.START,
    argv=("ls", "-l"),
    machine_state="snapshot-1",
):
    return ExecutionRecord(
        record_id=record_id,
        recorded_at=NOW,
        category=RecordCategory.EXECUTION,
        phase=phase,
        action_id="action-1",
        argv=argv,
        machine_state=machine_state,
    )


def _approval(
    decision=ApprovalDecision.APPROVAL,
    risk_class=None,
    gate=None,
    record_id="rec-2",
):
    return ApprovalRecord(
        record_id=record_id,
        recorded_at=NOW,
        category=RecordCategory.APPROVAL,
        decision=decision,
        action_id="action-1",
        risk_class=risk_class,
        gate=gate,
    )


def _override(
    record_id="rec-3",
    reason="operator confirmed the risk",
    risk_class=None,
    gate=None,
):
    return OverrideRecord(
        record_id=record_id,
        recorded_at=NOW,
        category=RecordCategory.OVERRIDE,
        action_id="action-1",
        reason=reason,
        risk_class=risk_class,
        gate=gate,
    )


def _secret(event=SecretEvent.PROVISIONED, provider=None, record_id="rec-4"):
    return SecretMetadataRecord(
        record_id=record_id,
        recorded_at=NOW,
        category=RecordCategory.SECRET_METADATA,
        event=event,
        handle="handle-1",
        metadata=SecretMetadata(existence=True, provider=provider),
    )


def test_transcript_owns_exactly_the_transcript_vocabulary():
    assert set(transcript_module.__all__) == {
        "TranscriptCategory",
        "TranscriptEntry",
        "render",
    }


def test_transcript_categories_are_exactly_the_five_8_categories_in_order():
    assert list(TranscriptCategory) == [
        TranscriptCategory.DIALOGUE,
        TranscriptCategory.ACTIONS_AND_OUTCOMES,
        TranscriptCategory.DECISIONS_AND_GROUNDS,
        TranscriptCategory.DISCLOSURES,
        TranscriptCategory.RECOVERY_CONTEXT,
    ]


def test_transcript_entry_is_frozen_and_slotted():
    params = TranscriptEntry.__dataclass_params__
    assert params.frozen and params.slots
    entry = TranscriptEntry(
        TranscriptCategory.DISCLOSURES,
        "rec-4",
        "secret handle-1 provisioned (metadata only)",
    )
    with pytest.raises(FrozenInstanceError):
        entry.text = "changed"


def test_transcript_entry_carries_only_the_owned_fields():
    entry = TranscriptEntry(TranscriptCategory.DISCLOSURES, "rec-4", "some text")
    assert entry.category is TranscriptCategory.DISCLOSURES
    assert entry.record_id == "rec-4"
    assert entry.text == "some text"


def test_transcript_entries_are_value_equal():
    e1 = TranscriptEntry(
        TranscriptCategory.DISCLOSURES,
        "rec-4",
        "secret handle-1 provisioned (metadata only)",
    )
    e2 = TranscriptEntry(
        TranscriptCategory.DISCLOSURES,
        "rec-4",
        "secret handle-1 provisioned (metadata only)",
    )
    assert e1 == e2
    assert hash(e1) == hash(e2)


def test_render_returns_exactly_one_entry_for_one_record():
    entry = render(_execution())
    assert isinstance(entry, TranscriptEntry)


def test_entry_traces_to_the_record_it_derives_from():
    assert render(_execution(record_id="rec-x")).record_id == "rec-x"
    assert render(_secret(record_id="rec-y")).record_id == "rec-y"


def test_execution_renders_as_actions_and_outcomes():
    entry = render(_execution())
    assert entry.category is TranscriptCategory.ACTIONS_AND_OUTCOMES


def test_secret_metadata_renders_as_disclosure():
    assert render(_secret()).category is TranscriptCategory.DISCLOSURES


def test_approval_renders_as_decisions_and_grounds():
    assert render(_approval()).category is TranscriptCategory.DECISIONS_AND_GROUNDS
    assert (
        render(_approval(ApprovalDecision.REJECTION)).category
        is TranscriptCategory.DECISIONS_AND_GROUNDS
    )


def test_override_renders_as_decisions_and_grounds():
    assert render(_override()).category is TranscriptCategory.DECISIONS_AND_GROUNDS


def test_this_layers_records_never_render_dialogue_or_recovery_context():
    records = [_execution(), _secret(), _approval(), _override()]
    produced = {render(r).category for r in records}
    assert produced <= {
        TranscriptCategory.ACTIONS_AND_OUTCOMES,
        TranscriptCategory.DECISIONS_AND_GROUNDS,
        TranscriptCategory.DISCLOSURES,
    }


def test_decisions_and_grounds_rendering_is_category_specific():
    approval = render(_approval())
    override = render(_override())
    assert (
        approval.category
        is override.category
        is TranscriptCategory.DECISIONS_AND_GROUNDS
    )
    assert approval.text != override.text


def test_identical_records_render_identical_entries():
    assert render(_execution()) == render(_execution())


def test_render_is_pure_identical_fields_not_object_identity():
    a = _approval(
        ApprovalDecision.APPROVAL, risk_class="consequential", gate="goal-check"
    )
    b = _approval(
        ApprovalDecision.APPROVAL, risk_class="consequential", gate="goal-check"
    )
    assert a is not b
    assert render(a) == render(b)
    assert render(a).text == render(b).text


def test_render_twice_is_stable():
    record = _secret(provider="ollama")
    assert render(record) == render(record)


def test_render_has_no_side_effects_on_the_record():
    record = _approval(ApprovalDecision.APPROVAL, risk_class="consequential")
    render(record)
    assert record == _approval(ApprovalDecision.APPROVAL, risk_class="consequential")


def test_execution_text_renders_the_record_fields_only():
    assert render(_execution()).text == "action action-1 started; argv ('ls', '-l')"


def test_execution_phase_changes_the_rendering():
    assert (
        render(_execution(phase=ExecutionPhase.END)).text
        == "action action-1 ended; argv ('ls', '-l')"
    )


def test_execution_argv_renders_as_an_argv_structured_listing_never_a_shell_string():
    argv = ("sh", "-c", "rm -rf /; echo pwned")
    entry = render(_execution(argv=argv))
    assert (
        entry.text
        == "action action-1 started; argv ('sh', '-c', 'rm -rf /; echo pwned')"
    )


def test_execution_machine_state_is_never_rendered():
    class State:
        def __repr__(self):
            return "machine-state-42"

    entry = render(_execution(machine_state=State()))
    assert "machine-state-42" not in entry.text
    assert "machine_state" not in entry.text


def test_approval_renders_the_decision_without_grounds_when_absent():
    assert render(_approval()).text == "action action-1 approved"
    assert (
        render(_approval(ApprovalDecision.AUTO_PERMIT)).text
        == "action action-1 auto-permitted"
    )
    assert (
        render(_approval(ApprovalDecision.REJECTION)).text == "action action-1 rejected"
    )


def test_approval_renders_grounds_when_present():
    assert (
        render(_approval(risk_class="consequential")).text
        == "action action-1 approved; risk consequential"
    )
    assert (
        render(_approval(risk_class="consequential", gate="goal-check")).text
        == "action action-1 approved; risk consequential; gate goal-check"
    )
    assert (
        render(_approval(gate="goal-check")).text
        == "action action-1 approved; gate goal-check"
    )


def test_approval_renders_the_approved_metadata_only():
    entry = render(
        _approval(
            ApprovalDecision.APPROVAL, risk_class="consequential", gate="goal-check"
        )
    )
    assert "recorded_at" not in entry.text
    assert "2026" not in entry.text
    assert entry.text == "action action-1 approved; risk consequential; gate goal-check"


def test_override_renders_the_stated_reason():
    assert (
        render(_override()).text
        == "action action-1 overridden; reason operator confirmed the risk"
    )


def test_override_renders_grounds_when_present():
    assert (
        render(_override(risk_class="high", gate="block")).text
        == "action action-1 overridden; reason operator confirmed the risk; "
        "risk high; gate block"
    )


def test_override_reason_is_rendered_verbatim_from_the_record():
    entry = render(_override(reason="  user said go ahead  "))
    assert entry.text == "action action-1 overridden; reason   user said go ahead  "


def test_secret_metadata_renders_metadata_only():
    assert render(_secret()).text == "secret handle-1 provisioned (metadata only)"


def test_secret_metadata_renders_the_provider_metadata_when_present():
    assert (
        render(_secret(provider="ollama")).text
        == "secret handle-1 provisioned (metadata only); provider ollama"
    )


def test_secret_metadata_rendering_carries_no_value_shaped_text():
    entry = render(_secret(event=SecretEvent.USED, provider="ollama"))
    assert "value" not in entry.text
    assert "content" not in entry.text
    assert entry.text == "secret handle-1 used (metadata only); provider ollama"


def test_every_secret_event_renders_deterministically():
    for event in SecretEvent:
        entry = render(_secret(event=event))
        assert entry.category is TranscriptCategory.DISCLOSURES
        assert entry.text.startswith(f"secret handle-1 {event.value} (metadata only)")


def test_bare_audit_record_fails_closed():
    bare = AuditRecord(
        record_id="rec-x", recorded_at=NOW, category=RecordCategory.APPROVAL
    )
    with pytest.raises(TypeError):
        render(bare)


def test_unknown_audit_record_subclass_fails_closed():
    class UnknownRecord(AuditRecord):
        pass

    unknown = UnknownRecord(
        record_id="rec-x", recorded_at=NOW, category=RecordCategory.EXECUTION
    )
    with pytest.raises(TypeError):
        render(unknown)


def test_non_record_fails_closed():
    for bad in (object(), "not a record", 42, None):
        with pytest.raises(TypeError):
            render(bad)


def test_rendering_a_sequence_preserves_record_order():
    records = [_approval(), _override(), _secret(), _execution()]
    entries = [render(r) for r in records]
    assert [e.record_id for e in entries] == [r.record_id for r in records]
    assert [e.category for e in entries] == [
        TranscriptCategory.DECISIONS_AND_GROUNDS,
        TranscriptCategory.DECISIONS_AND_GROUNDS,
        TranscriptCategory.DISCLOSURES,
        TranscriptCategory.ACTIONS_AND_OUTCOMES,
    ]


def test_transcript_module_reads_no_clock_and_generates_no_random_or_crypto():
    src = TRANSCRIPT_PATH.read_text(encoding="utf-8")
    for token in (
        "datetime.now",
        "utcnow",
        "time.time",
        "time.monotonic",
        "import time",
        "import random",
        "random.",
        "os.urandom",
        "import uuid",
        "uuid4",
        "import hmac",
        "import hashlib",
        "import secrets",
        "secrets.token",
        "import json",
        "import os",
    ):
        assert token not in src, f"transcript.py uses {token}"
