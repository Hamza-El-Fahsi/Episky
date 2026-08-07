"""Canonical audit record categories (RFC-0013 §7, §9; RFC-0004 §4.12;
DN-63).

Owner: RFC-0013 §7 (the record categories), §9 (what is recorded); RFC-0004
    §4.12 (the Audit System owns the record format and ordering); ratified
    decision note DN-63 (this layer's boundaries' categories — the remaining
    §7 categories arrive with their owning write points).
Responsibility: the immutable, category-carrying, value-free record types
    for this layer's boundaries — the execution record (cat. 6: action
    start/end, commands in sanitized form, machine state at the boundary),
    the secret-metadata record (cat. 10, on `secrets` *metadata* types —
    SC4; no value-shaped field exists by construction), and the approval /
    override / auto-permit / rejection records (cat. 4/5) whose durable
    write DN-50 assigned to audit. Time is an argument, never a side
    effect: every record carries an explicit ``recorded_at`` supplied by
    the caller and an immutable, caller-supplied ``record_id``. Pure
    deterministic data (AU5): identical arguments yield identical records.
Forbidden responsibility: no record holds a secret value or a value-shaped
    field by construction (RFC-0013 §10, §31; RFC-0009 SC4; AU7); no policy
    or execution logic; no decision authority (RFC-0004 §4.12; AU1); no
    clock, no randomness, no identifier generation. The ``schema`` edge
    stays latent (the DN-44 precedent): the only cross-package import is
    ``secrets`` *metadata* types (blueprint §4.2).
"""

from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from episky.secrets.classify import SecretMetadata

__all__ = [
    "ApprovalDecision",
    "ApprovalRecord",
    "AuditRecord",
    "ExecutionPhase",
    "ExecutionRecord",
    "OverrideRecord",
    "RecordCategory",
    "SecretEvent",
    "SecretMetadataRecord",
]


class RecordCategory(Enum):
    """The §7 categories this layer's boundaries write (RFC-0013 §7; DN-63).

    Exactly the categories whose write points exist in this layer (DN-63):
    each record carries the category of the boundary it was written at.
    The remaining §7 categories arrive with their owning write points;
    nothing is orphaned before its boundary exists.

    Members:
        APPROVAL: Cat. 4 — approvals, refusals, auto-permissions, issuance,
            written before the token is spent (RFC-0008 P13).
        OVERRIDE: Cat. 5 — blocked-action overrides, with their own warning
            before execution (RFC-0002 invariant 12; RFC-0008 P10).
        EXECUTION: Cat. 6 — action start/end, commands in sanitized form,
            machine state at the boundary (RFC-0002 §6).
        SECRET_METADATA: Cat. 10 — secret provisioning/use/invalidation/
            destruction/exposure, metadata only (RFC-0013 §31; SC4).
    """

    APPROVAL = "approval"
    OVERRIDE = "override"
    EXECUTION = "execution"
    SECRET_METADATA = "secret-metadata"


class ExecutionPhase(Enum):
    """Whether an ExecutionRecord opens or closes an execution (cat. 6).

    Members:
        START: The record written before the consequence — the execution
            is about to begin (RFC-0002 invariant 13).
        END: The record written after the run, before the next boundary
            (RFC-0013 §7 cat. 6; RFC-0002 §6).
    """

    START = "start"
    END = "end"


class SecretEvent(Enum):
    """The secret-lifecycle event a cat-10 record documents (RFC-0013 §31).

    Members:
        PROVISIONED: A secret was provisioned into the Secure Store.
        USED: A secret was consumed at a boundary.
        INVALIDATED: A secret was invalidated.
        DESTROYED: A secret was destroyed.
        EXPOSED: A suspected exposure was recorded (RFC-0009 SC15).
        VISIBILITY_REQUEST: The Operator asked to see or remove a secret's
            metadata.
    """

    PROVISIONED = "provisioned"
    USED = "used"
    INVALIDATED = "invalidated"
    DESTROYED = "destroyed"
    EXPOSED = "exposed"
    VISIBILITY_REQUEST = "visibility-request"


class ApprovalDecision(Enum):
    """The cat-4 approval-gate decision a record documents (RFC-0013 §7;
    DN-50).

    Members:
        APPROVAL: An explicit approval; issuance recorded before the token
            is spent (RFC-0004 A10; RFC-0008 P13).
        AUTO_PERMIT: An allowlisted read-only Action, still recorded
            (RFC-0002 §2.7; RFC-0013 §16).
        REJECTION: A refusal; nothing was issued.
    """

    APPROVAL = "approval"
    AUTO_PERMIT = "auto-permit"
    REJECTION = "rejection"


@dataclass(frozen=True, slots=True)
class AuditRecord:
    """The common immutable fields of every audit record (RFC-0013 §7).

    The base every record carries: an immutable, caller-supplied identity,
    an explicit recorded-at time supplied by the caller (never a clock
    read), and the §7 category of the boundary the record was written at.
    Frozen and slot-based: immutable, in-memory only (DN-1). The store
    refuses a duplicate ``record_id`` so lookup stays deterministic.

    Attributes:
        record_id: The immutable, caller-supplied identity of this record.
        recorded_at: When the event happened, supplied by the caller as an
            explicit time argument.
        category: The §7 category this record belongs to (RFC-0013 §7).
    """

    record_id: str
    recorded_at: datetime
    category: RecordCategory


@dataclass(frozen=True, slots=True)
class ExecutionRecord(AuditRecord):
    """The execution record — action start/end (RFC-0013 §7 cat. 6).

    Written at the executor boundary before the consequence for START and
    after the run for END (RFC-0002 invariant 13; RFC-0013 §23). Commands
    are carried in sanitized argv form — never a shell string (RFC-0001
    §8.4 rule 4; I-5) — and the machine state at the boundary as an opaque,
    caller-supplied reference (never the material, RFC-0013 §10).

    Attributes:
        phase: START opens the execution; END closes it.
        action_id: The immutable identity of the approved Action, supplied
            by the caller.
        argv: The command descriptor in sanitized argv-structured form; no
            shell string is ever carried.
        machine_state: The machine-state reference at the boundary,
            caller-supplied and never interpreted here.
    """

    phase: ExecutionPhase
    action_id: str
    argv: tuple[str, ...]
    machine_state: object


@dataclass(frozen=True, slots=True)
class SecretMetadataRecord(AuditRecord):
    """The secret-metadata record (RFC-0013 §7 cat. 10, §31; SC4).

    Answers "what secret was stored, when used, was it destroyed" without
    holding a value (RFC-0013 §31 rule 3). Carries only the `secrets`
    *metadata* types and a handle — never enough material to reconstruct a
    value. No value-shaped field exists by construction.

    Attributes:
        event: The secret-lifecycle event being recorded.
        handle: The secret's identifier (metadata), caller-supplied.
        metadata: The value-free ``SecretMetadata`` view of the secret
            (existence, provider, lifecycle dates).
    """

    event: SecretEvent
    handle: str
    metadata: SecretMetadata


@dataclass(frozen=True, slots=True)
class ApprovalRecord(AuditRecord):
    """The approval-gate record (RFC-0013 §7 cat. 4; DN-50).

    The durable write of an issuance, auto-permit, or rejection, recorded
    before the token is spent (RFC-0004 A10; RFC-0008 P13). Carries the
    decision and the canonical policy labels (risk class, gate) as names in
    canonical string form (RFC-0013 §7; RFC-0003 Part I) — the policy
    package is never imported.

    Attributes:
        decision: APPROVAL, AUTO_PERMIT, or REJECTION.
        action_id: The immutable identity of the Action the decision was
            about, supplied by the caller.
        risk_class: The canonical risk-class name at decision time, if one
            was reached.
        gate: The canonical gate name at decision time.
    """

    decision: ApprovalDecision
    action_id: str
    risk_class: str | None = None
    gate: str | None = None


@dataclass(frozen=True, slots=True)
class OverrideRecord(AuditRecord):
    """The blocked-action override record (RFC-0013 §7 cat. 5; RFC-0008 P10).

    Written for a blocked Action that was overridden, with its explicit
    reason, before execution (RFC-0002 invariant 12). The override is the
    only path past a block and is itself recorded (RFC-0008 P10).

    Attributes:
        action_id: The immutable identity of the overridden Action,
            supplied by the caller.
        reason: The explicit reason the block was overridden (P10).
        risk_class: The canonical risk-class name, if one was reached.
        gate: The canonical gate name.
    """

    action_id: str
    reason: str
    risk_class: str | None = None
    gate: str | None = None
