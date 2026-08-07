"""Append-only, tamper-evident audit store (RFC-0013 §1, §11, §12, §21, §22;
RFC-0002 invariant 13; RFC-0004 A7, §9.12; AU4, AU5, AU8, AU13; DN-62).

Owner: RFC-0013 §1 (durable, append-only, tamper-evident record), §11/§12
    (the lifecycle and its legal transitions), §21 (fail closed, fail
    loud), §22 (reconciliation, never rewrite); RFC-0002 invariant 13
    (recorded before the consequence); RFC-0004 A7, §9.12; ratified
    decision note DN-62.
Responsibility: an in-memory, append-only, deterministic record store.
    Prior records are immutable and never edited or erased (AU4); a
    deterministic structural chain binds each record to its predecessor so
    any silent edit is detectable (RFC-0001 §8.10 tamper-evidence); the §11
    lifecycle (Empty → Recording → Degraded → Recovering) with the §12 legal
    transitions — Degraded → consequence proceeds is illegal (RFC-0004
    §9.12); a failed or refused write moves the store to Degraded and is
    disclosed (AU8); recovery is reconciliation — a lost write is recorded
    as failed-to-record, never invented, and deleted records never return
    (AU13, §22). ``append`` returns a new immutable store (AU5): identical
    events yield identical, reproducible records, in deterministic order.
Forbidden responsibility: no durable backing, filesystem, database,
    retention, deletion, or export mechanics — those are RFC-0020's (DN-62;
    design review §1.2); no deletion or overwrite of any record; no clock —
    time is an argument on the record, never a side effect; no randomness
    and no cryptographic hashing (the policy/secrets precedent): the chain
    is a deterministic structural encoding — tamper-evidence, not
    tamper-proofing (RFC-0013 §14.3); no policy or execution logic; no
    secret value ever enters the store (SC4/AU7); no hidden state — the
    store is a frozen, slotted, in-memory value with every field public.
"""

from collections.abc import Iterator
from dataclasses import dataclass, fields
from enum import Enum

from episky.audit.records import AuditRecord, RecordCategory

__all__ = ["AuditStore", "StoreStatus"]


class StoreStatus(Enum):
    """The §11 lifecycle states this layer implements (RFC-0013 §11; DN-62).

    Exported / Retained / Deleted are durable-storage states and arrive
    with RFC-0020 (design review §1.2).

    Members:
        EMPTY: No records yet; the store awaits opening and a writability
            verification (RFC-0002 §2.1).
        RECORDING: The normal state; events are appended before their
            consequences (RFC-0002 invariant 13).
        DEGRADED: A write failed or was refused; the consequence it
            precedes is blocked (RFC-0004 §9.12).
        RECOVERING: A failed or partial write is being reconciled
            (RFC-0013 §22).
    """

    EMPTY = "empty"
    RECORDING = "recording"
    DEGRADED = "degraded"
    RECOVERING = "recovering"


def _chain_value(previous: str, record: AuditRecord) -> str:
    """The deterministic value binding `record` to its predecessor.

    A canonical structural encoding of the record's type and every field in
    declaration order, chained to the previous value. Any silent edit to a
    prior record changes every subsequent chain value, so ``verify``
    detects it. Deliberately not a cryptographic digest (no hashing or
    crypto — the policy/secrets precedent): tamper-evidence, not
    tamper-proofing (RFC-0013 §14.3). Opaque references chain by their
    ``repr`` — stable within a process, as references are not reproducible
    across runs.
    """
    body = "|".join(
        f"{field.name}={getattr(record, field.name)!r}" for field in fields(record)
    )
    return f"{type(record).__module__}.{type(record).__qualname__}|{previous}|{body}"


@dataclass(frozen=True, slots=True)
class AuditStore:
    """The immutable, append-only audit store (RFC-0013 §1; DN-62).

    A frozen value: every transition method returns a new ``AuditStore``
    and never mutates the receiver. Prior records are immutable (AU4), the
    record list can only be appended to, the chain grows with each record,
    and no deletion or overwrite surface exists. State is public and
    explicit — there is no hidden state.

    Attributes:
        status: The §11 lifecycle state.
        records: The ordered, append-only record list, in write order.
        chain: One deterministic chain value per record, binding it to its
            predecessor (tamper-evidence).
        disclosure: The fail-loud note set when a write fails or is refused
            (AU8); never cleared — a failed write is recorded as
            failed-to-record, never invented (AU13, §22).
    """

    status: StoreStatus = StoreStatus.EMPTY
    records: tuple[AuditRecord, ...] = ()
    chain: tuple[str, ...] = ()
    disclosure: str | None = None

    def begin_recording(self) -> "AuditStore":
        """Empty → Recording: open and verify writable (RFC-0013 §12, §2.1).

        The only path into the normal recording state. The startup call is
        the runtime's (Iteration 10); the mechanism exists here.

        Returns:
            A new store in Recording, ready to append.

        Raises:
            ValueError: If the store is not Empty — an unlisted transition
                is illegal (default deny, RFC-0013 §12).
        """
        if self.status is not StoreStatus.EMPTY:
            raise ValueError("only an Empty store can begin recording (RFC-0013 §12)")
        return AuditStore(
            status=StoreStatus.RECORDING,
            records=self.records,
            chain=self.chain,
        )

    def append(self, record: AuditRecord) -> "AuditStore":
        """Record an event before its consequence (RFC-0013 §9; I-13).

        Appends only while Recording, only for a real ``AuditRecord`` with
        a fresh ``record_id``. Any refusal is a failed write: the returned
        store is Degraded with a disclosure (AU8), and the consequence it
        preceded is blocked. Pure and deterministic: the same store and
        record always yield the same successor (AU5).

        Args:
            record: The immutable, category-carrying record to append.

        Returns:
            A new store in Recording with the record chained, or a new
            store in Degraded with a disclosure when the write is refused.
        """
        if self.status is not StoreStatus.RECORDING:
            return self._refused(
                f"audit write refused: store is {self.status.value}, not "
                "Recording (RFC-0013 §11/§12; AU8)"
            )
        if not isinstance(record, AuditRecord):
            return self._refused(
                "audit write refused: not an AuditRecord (RFC-0013 §9; AU8)"
            )
        if any(existing.record_id == record.record_id for existing in self.records):
            return self._refused(
                f"audit write refused: record_id {record.record_id!r} is already "
                "recorded (RFC-0013 §15.3)"
            )
        previous = self.chain[-1] if self.chain else ""
        return AuditStore(
            status=StoreStatus.RECORDING,
            records=self.records + (record,),
            chain=self.chain + (_chain_value(previous, record),),
            disclosure=self.disclosure,
        )

    def fail(self, message: str) -> "AuditStore":
        """Report a failed write: Recording → Degraded, disclosed (AU8).

        The boundary reports a write failure here; the store fails closed —
        Degraded is never silent (RFC-0004 §9.12) and the next consequence
        is refused.

        Args:
            message: The fail-loud disclosure for the Operator.

        Returns:
            A new store in Degraded carrying the disclosure.

        Raises:
            ValueError: If the store is not Recording, or the message is
                empty — a write cannot fail outside Recording.
        """
        if self.status is not StoreStatus.RECORDING:
            raise ValueError("only a Recording store can fail a write (RFC-0013 §12)")
        if not isinstance(message, str) or not message.strip():
            raise ValueError("a failed write must be disclosed (RFC-0013 §21)")
        return AuditStore(
            status=StoreStatus.DEGRADED,
            records=self.records,
            chain=self.chain,
            disclosure=message,
        )

    def recover(self) -> "AuditStore":
        """Degraded → Recovering: begin reconciliation (RFC-0013 §22).

        Returns:
            A new store in Recovering; the failure disclosure is retained.

        Raises:
            ValueError: If the store is not Degraded.
        """
        if self.status is not StoreStatus.DEGRADED:
            raise ValueError("only a Degraded store can begin recovery (RFC-0013 §22)")
        return AuditStore(
            status=StoreStatus.RECOVERING,
            records=self.records,
            chain=self.chain,
            disclosure=self.disclosure,
        )

    def reconcile(self) -> "AuditStore":
        """Recovering → Recording: finish reconciliation (§22; AU13).

        The failed write stays recorded as failed-to-record (the retained
        disclosure); nothing is invented, and deleted records never return
        (AU13).

        Returns:
            A new store in Recording, still carrying the honest failure
            disclosure, with the record list unchanged.

        Raises:
            ValueError: If the store is not Recovering.
        """
        if self.status is not StoreStatus.RECOVERING:
            raise ValueError("only a Recovering store can be reconciled (RFC-0013 §22)")
        return AuditStore(
            status=StoreStatus.RECORDING,
            records=self.records,
            chain=self.chain,
            disclosure=self.disclosure,
        )

    def _refused(self, disclosure: str) -> "AuditStore":
        """A refused write: the store moves to Degraded and is disclosed."""
        return AuditStore(
            status=StoreStatus.DEGRADED,
            records=self.records,
            chain=self.chain,
            disclosure=disclosure,
        )

    def verify(self) -> bool:
        """Whether the chain still binds the records (RFC-0001 §8.10; AU4).

        Re-derives the expected chain from the current records and compares
        it to the stored chain. A silent edit to any prior record changes
        the expected chain, so this returns False — tamper-evidence, not
        tamper-proofing (RFC-0013 §14.3).

        Returns:
            True when no edit is detected; False when the chain and the
            records disagree.
        """
        expected = ()
        previous = ""
        for record in self.records:
            previous = _chain_value(previous, record)
            expected += (previous,)
        return expected == self.chain

    def __len__(self) -> int:
        """The number of records appended so far."""
        return len(self.records)

    def __iter__(self) -> Iterator[AuditRecord]:
        """Iterate the records in append order."""
        return iter(self.records)

    def record_at(self, index: int) -> AuditRecord:
        """The record at `index`, in append order (RFC-0013 §13.1).

        Raises:
            IndexError: If `index` is out of range.
        """
        return self.records[index]

    def by_id(self, record_id: str) -> AuditRecord | None:
        """The record with the immutable `record_id`, or None.

        Well-defined because the store refuses a duplicate ``record_id``.
        """
        for record in self.records:
            if record.record_id == record_id:
                return record
        return None

    def by_category(self, category: RecordCategory) -> tuple[AuditRecord, ...]:
        """The records of one §7 category, in append order (RFC-0013 §7)."""
        return tuple(record for record in self.records if record.category is category)

    def latest(self) -> AuditRecord | None:
        """The most recently appended record, or None when empty."""
        return self.records[-1] if self.records else None
