"""Deterministic transcript derivation from the record (RFC-0013 §2, §5, §8;
AU2; DN-64).

Owner: RFC-0013 §8 (the transcript categories) and §5 (the Audit System owns
    transcript derivation); ratified decision note DN-64 (Q10: derivation
    from the record only).
Responsibility: render each audit record this layer writes into its §8
    transcript category — the execution record (cat. 6) as actions and
    outcomes, the approval / auto-permit / rejection and override records
    (cat. 4/5) as decisions and their grounds, and the secret-metadata
    record (cat. 10) as a disclosure — from the record *only*, with stable,
    deterministic text (AU5): identical records render identical entries.
    ``render`` is a pure function; the presentation *form* (how a beginner
    sees it) is RFC-0015's.
Forbidden responsibility: no content the record does not hold (AU2) — the
    transcript never reconstructs or infers missing information; no parsing,
    no serialization format, no JSON/Markdown/YAML, no logging, no I/O, no
    persistence, no clock, no randomness, no cryptography; the opaque
    machine-state reference is never rendered (it is never interpreted and
    may hold material, RFC-0013 §10); no verification or reasoning path
    consumes a rendering (AU2). Unknown record types fail closed.
"""

from dataclasses import dataclass
from enum import Enum

from episky.audit.records import (
    ApprovalDecision,
    ApprovalRecord,
    AuditRecord,
    ExecutionPhase,
    ExecutionRecord,
    OverrideRecord,
    SecretMetadataRecord,
)

__all__ = [
    "TranscriptCategory",
    "TranscriptEntry",
    "render",
]


class TranscriptCategory(Enum):
    """The closed §8 transcript categories (RFC-0013 §8; DN-64).

    The Transcript presents exactly these five categories, each derived from
    the record only (AU2). This layer's records render into
    actions-and-outcomes, decisions-and-grounds, and disclosures; dialogue
    and recovery-context arrive with the session, proposal, and verification
    records at their owning write points — recorded, not dropped, and never
    invented (AU13).

    Members:
        DIALOGUE: The Operator-facing conversation, from session, proposal,
            and approval records (RFC-0013 §8 cat. 1).
        ACTIONS_AND_OUTCOMES: What was run, approved, verified, and the
            outcome (RFC-0013 §8 cat. 2; RFC-0002 §10).
        DECISIONS_AND_GROUNDS: Classifications, approvals, refusals, and
            overrides with stated reasons (RFC-0013 §8 cat. 3; RFC-0008 P13).
        DISCLOSURES: Anything redacted or withheld, disclosed as withheld
            (RFC-0013 §8 cat. 4; RFC-0009 §15).
        RECOVERY_CONTEXT: What the record re-presents after an interrupt or
            reboot (RFC-0013 §8 cat. 5; RFC-0012 §21; RFC-0002 §10).
    """

    DIALOGUE = "dialogue"
    ACTIONS_AND_OUTCOMES = "actions-and-outcomes"
    DECISIONS_AND_GROUNDS = "decisions-and-grounds"
    DISCLOSURES = "disclosures"
    RECOVERY_CONTEXT = "recovery-context"


@dataclass(frozen=True, slots=True)
class TranscriptEntry:
    """One deterministic rendering of one audit record (RFC-0013 §8; AU2).

    The unit the Transcript is made of: a §8 category, the immutable
    identity of the record it was derived from (traceability back to the
    record — "re-rendered from the record", RFC-0013 §3), and the stable
    text. Frozen and slot-based (DN-34): an entry is immutable and in-memory
    only (DN-1).

    Attributes:
        category: The §8 transcript category this record renders as.
        record_id: The immutable identity of the record this entry was
            derived from; every entry traces to exactly one record.
        text: The deterministic, stable textual rendering of the record's
            semantic content — never more than the record holds (AU2).
    """

    category: TranscriptCategory
    record_id: str
    text: str


def render(record: AuditRecord) -> TranscriptEntry:
    """Render one record into one deterministic transcript entry.

    Pure and deterministic (AU5): the entry derives from the record only
    (AU2) — identical records render identical entries. Each record type
    renders into its §8 category with its own stable format: the execution
    record as actions and outcomes (argv in its sanitized, argv-structured
    form, never a shell string); the approval / auto-permit / rejection and
    override records as decisions and their grounds; the secret-metadata
    record as a disclosure (metadata only, never a value, SC4). The opaque
    machine-state reference is never rendered (never interpreted; RFC-0013
    §10). Unknown record types fail closed: a bare ``AuditRecord``, an
    unknown subclass, or a non-record raises ``TypeError`` rather than
    inventing a rendering.

    Args:
        record: The immutable audit record to render.

    Returns:
        The single transcript entry for ``record``.
    """
    if isinstance(record, ExecutionRecord):
        return TranscriptEntry(
            category=TranscriptCategory.ACTIONS_AND_OUTCOMES,
            record_id=record.record_id,
            text=_execution_text(record),
        )
    if isinstance(record, SecretMetadataRecord):
        return TranscriptEntry(
            category=TranscriptCategory.DISCLOSURES,
            record_id=record.record_id,
            text=_secret_text(record),
        )
    if isinstance(record, ApprovalRecord):
        return TranscriptEntry(
            category=TranscriptCategory.DECISIONS_AND_GROUNDS,
            record_id=record.record_id,
            text=_approval_text(record),
        )
    if isinstance(record, OverrideRecord):
        return TranscriptEntry(
            category=TranscriptCategory.DECISIONS_AND_GROUNDS,
            record_id=record.record_id,
            text=_override_text(record),
        )
    raise TypeError(
        f"no transcript rendering for {type(record).__name__}; unknown record "
        "types fail closed (RFC-0013 §8; AU2)"
    )


def _execution_text(record: ExecutionRecord) -> str:
    verbs = {ExecutionPhase.START: "started", ExecutionPhase.END: "ended"}
    verb = verbs[record.phase]
    return f"action {record.action_id} {verb}; argv {record.argv!r}"


def _approval_text(record: ApprovalRecord) -> str:
    verbs = {
        ApprovalDecision.APPROVAL: "approved",
        ApprovalDecision.AUTO_PERMIT: "auto-permitted",
        ApprovalDecision.REJECTION: "rejected",
    }
    stem = f"action {record.action_id} {verbs[record.decision]}"
    return _decision_text(stem, record.risk_class, record.gate)


def _override_text(record: OverrideRecord) -> str:
    stem = f"action {record.action_id} overridden; reason {record.reason}"
    return _decision_text(stem, record.risk_class, record.gate)


def _decision_text(stem: str, risk_class: str | None, gate: str | None) -> str:
    parts = [stem]
    if risk_class is not None:
        parts.append(f"risk {risk_class}")
    if gate is not None:
        parts.append(f"gate {gate}")
    return "; ".join(parts)


def _secret_text(record: SecretMetadataRecord) -> str:
    text = f"secret {record.handle} {record.event.value} (metadata only)"
    if record.metadata.provider is not None:
        text += f"; provider {record.metadata.provider}"
    return text
