"""Secure Store abstraction.

Owner: RFC-0009 §4–§12 (ownership, authority, lifecycle, consumption,
    persistence, sharing, destruction), §15 (audit records metadata,
    never values), §28 (SC1, SC6, SC7, SC8, SC12, SC15); ratified
    decision note DN-41 (the abstraction over in-memory, metadata-only
    records now; the OS-secret-store mechanics remain RFC-0020's).
Responsibility: the Secure Store interface contract — provision (a
    value enters the store bound to its stated purpose, SC7),
    consume-at-boundary (the single, purpose-scoped crossing to the
    named Provider-adapter consumer, SC6/SC8), invalidate (refused at
    every boundary), and destroy (the value and every materialization,
    SC12) — over in-memory records that are metadata only (DN-41).
    A value is held only in the store's custody and materializes only
    at the consume boundary (SC1); it never appears in a record, is
    never re-displayed (RFC-0009 §9, §15, §23), and consumption is
    recorded as metadata only. Every operation is deterministic —
    identifiers and dates are explicit parameters; nothing is
    generated, sampled, or read from a clock — and fails closed: an
    unknown, destroyed, invalidated, mis-scoped, or wrong-consumer
    request is refused with a non-empty reason (RFC-0009 §13;
    RFC-0001 §8.12); nothing is ever silently succeeded or fabricated.
Forbidden responsibility: never exposes a value outside consume, never
    re-displays or persists a value (RFC-0009 §9, §23; DN-41 — nothing
    durable is written), never generates an identifier, date, or random
    value (determinism; the system never creates a secret, §7/§14),
    never grants or denies authority (RFC-0004 §7), never decides what
    a secret is for or who may use it (custody is not ownership, §4),
    never consults the LLM (RFC-0002 invariant 4), never imports a
    forbidden package, and never holds global mutable state.
"""

from dataclasses import dataclass
from datetime import date
from enum import Enum

from episky.secrets.classify import (
    SecretClassification,
    SecretDatum,
    SecretOrigin,
    classify,
)

__all__ = [
    "Consumer",
    "Consumption",
    "Destruction",
    "OPERATOR_OWNER",
    "Provision",
    "SECURE_STORE_CUSTODIAN",
    "SecretRecord",
    "SecureStore",
    "StoreStatus",
]

OPERATOR_OWNER = "operator"
"""The single owner of every secret (RFC-0009 §4; SC8).

Ownership stays with the Operator — the provisioner — under the
bring-your-own-key origin (RFC-0001 §2). Never a parameter and never
delegated: every secret has exactly one owner (SC8; RFC-0004 §3).
"""

SECURE_STORE_CUSTODIAN = "secure-store"
"""The single custody holder of every secret (RFC-0009 §4; SC8).

The Secure Store holds the value under the Operator's grant and
releases it only at a named consumption boundary; it never decides
what the secret is for or who may use it (custody is not ownership).
"""


class Consumer(Enum):
    """The closed consumer set for secret values (RFC-0009 §8).

    Exactly one member: the Provider adapter, at the provider boundary,
    for the secret's stated purpose. Nothing else consumes secret
    values — not Skills (RFC-0011 §15), not Diagnostics, the Fact
    Layer, Context, Verification, the Approval Engine, or the Audit
    System (RFC-0009 §8). Consuming with anything else is refused:
    secrets cross boundaries one way only (SC6).

    Members:
        PROVIDER_ADAPTER: The single scoped consumer, at the provider
            boundary (RFC-0009 §8, §16).
    """

    PROVIDER_ADAPTER = "provider-adapter"


class StoreStatus(Enum):
    """Whether a store operation discharged its boundary (RFC-0009 §13).

    Members:
        OK: The operation discharged; for consume, the value is
            materialized at the named boundary for the named consumer.
        REFUSED: The boundary held closed — the secret is unknown,
            invalidated, mis-scoped, or the consumer is outside the
            closed set; nothing is released and the reason tells the
            Operator why (RFC-0001 §8.12). Never a silent success.
    """

    OK = "ok"
    REFUSED = "refused"


@dataclass(frozen=True, slots=True)
class SecretRecord:
    """The metadata-only account of a provisioned secret (RFC-0009 §15).

    Value-free: it names the secret's handle, its bound purpose,
    exactly one owner and one custody holder (SC8), and the lifecycle
    dates — everything the Operator and the future Audit may know
    without the value (RFC-0009 §1, §15, §23). It never carries the
    value and never reconstructs one.

    Attributes:
        handle: The opaque caller-supplied identifier the secret is
            keyed on; never a backend ID (DN-41).
        purpose: The purpose the secret was bound to at provisioning;
            never silently widened (SC7).
        owner: The exactly-one owner — the Operator (RFC-0009 §4).
        custodian: The exactly-one custody holder — the Secure Store
            (§4; custody is not ownership).
        classification: The C1 value-free classification (SECRET,
            provisioned), carrying the SecretMetadata existence and
            provider facets.
        provisioned_on: When the value entered the store.
        last_used_on: The last consumption date; None until then.
        invalidated_on: The invalidation date; None until then. An
            invalidated secret is refused at every boundary (§6).
    """

    handle: str
    purpose: str
    owner: str
    custodian: str
    classification: SecretClassification
    provisioned_on: date
    last_used_on: date | None = None
    invalidated_on: date | None = None


@dataclass(frozen=True, slots=True)
class Provision:
    """The value-free result of provisioning a secret (RFC-0009 §5.1, §7).

    Attributes:
        handle: The opaque identifier the secret is keyed on.
        record: The metadata-only SecretRecord entered for the secret.
        status: OK, or REFUSED when provisioning failed closed.
        reason: Why the record is in this state; non-empty, so a
            refusal is never silent.
    """

    handle: str
    record: SecretRecord
    status: StoreStatus
    reason: str


@dataclass(frozen=True, slots=True)
class Consumption:
    """The result of consuming a secret at its named boundary (SC1, SC6).

    The store's only value-bearing artifact (design review §4): the
    value is materialized at the consume boundary for the named
    consumer and purpose and is re-displayed nowhere else. On a
    refused consumption nothing crosses — the value field is empty and
    the reason tells the Operator why. The materialization is
    transient: the store records only metadata (RFC-0009 §8.4, §15)
    and never re-displays the value (§12.4).

    Attributes:
        handle: The opaque identifier consumed.
        value: The materialized value at the boundary; empty when the
            consumption is refused (nothing crosses).
        status: OK (value materialized) or REFUSED (boundary held
            closed).
        consumer: The named consumer — the Provider adapter, the
            closed set (RFC-0009 §8).
        purpose: The purpose the value is consumed for; must be the
            provisioned purpose (SC7).
        consumed_on: When the consumption occurred (metadata only).
        reason: Why the consumption is in this state; non-empty.
    """

    handle: str
    value: str
    status: StoreStatus
    consumer: Consumer
    purpose: str
    consumed_on: date
    reason: str


@dataclass(frozen=True, slots=True)
class Destruction:
    """The value-free result of invalidating or destroying a secret.

    Records which secret, when, and why — never the value (RFC-0009
    §12.5, §15).

    Attributes:
        handle: The opaque identifier invalidated or destroyed.
        status: OK, or REFUSED when the operation failed closed.
        reason: Why the secret was invalidated/destroyed, or why the
            operation was refused; non-empty.
        invalidated_on: When the secret was invalidated; None if not.
        destroyed_on: When the secret was destroyed; None if not.
    """

    handle: str
    status: StoreStatus
    reason: str
    invalidated_on: date | None = None
    destroyed_on: date | None = None


class SecureStore:
    """The Secure Store abstraction: custody and lifecycle over metadata.

    In-memory, metadata-only (DN-41). Values are held in the store's
    custody (SC1) and materialize only at the consume boundary;
    records are metadata only. Provisioning binds a value to its
    stated purpose (SC7); consumption is the single, one-way crossing
    to the named Provider-adapter consumer (SC6, SC8); invalidation
    refuses the secret at every boundary; destruction removes the
    value and the record (SC12). The operations are deterministic —
    handles and dates are explicit inputs, never generated here — and
    fail closed: unknown, invalidated, mis-scoped, or wrong-consumer
    requests are refused with a non-empty reason (RFC-0009 §13),
    never silently succeeded, never fabricated.

    The real OS-secret-store mechanics — which store, its interface,
    encryption, and key management — are RFC-0020's (RFC-0009 §30
    OQ1; DN-41) and are not implemented here; this abstraction is the
    contract, and it records metadata only.
    """

    def __init__(self) -> None:
        self._records: dict[str, SecretRecord] = {}
        self._values: dict[str, str] = {}

    def provision(
        self,
        handle: str,
        value: str,
        purpose: str,
        provisioned_on: date,
        provider: str | None = None,
    ) -> Provision:
        """Provision a secret into the store, bound to its purpose (SC7).

        Deterministic: nothing is generated, sampled, or read from a
        clock; every input is explicit. The value is classified
        (provisioned values are SECRET, RFC-0009 §3 rule 1) so the
        record carries a value-free label, then held in custody (SC1)
        while only metadata is recorded (RFC-0009 §15). Malformed
        requests fail closed: an empty handle, value, or purpose, or a
        duplicate handle, is rejected outright (RFC-0009 §13) — the
        store never silently overwrites or fabricates.

        Args:
            handle: The opaque caller-supplied identifier the secret
                is keyed on; never a backend ID (DN-41).
            value: The secret value entering the store; held in
                custody, never recorded or re-displayed.
            purpose: The stated purpose the secret is bound to;
                consumption for any other purpose is refused (SC7).
            provisioned_on: The provisioning date (metadata only).
            provider: Optional provider/context the secret is
                associated with; carried into the classification's
                SecretMetadata (value-free).

        Returns:
            The value-free Provision result: the entered metadata
            record, the status, and the reason.

        Raises:
            ValueError: If ``handle``, ``value``, or ``purpose`` is
                empty, or a secret is already provisioned under
                ``handle``.
        """
        if not handle:
            raise ValueError("a secret must be provisioned under a non-empty handle")
        if not value:
            raise ValueError("a secret value must be non-empty")
        if not purpose:
            raise ValueError(
                "a secret must be provisioned for a stated purpose "
                "(RFC-0009 §5, §7; SC7)"
            )
        if handle in self._records:
            raise ValueError(
                f"a secret is already provisioned under {handle!r} — "
                "exactly one secret per handle (RFC-0009 §4; SC8)"
            )
        classification = classify(
            SecretDatum(
                content=value,
                origin=SecretOrigin.PROVISIONED,
                provider=provider,
            )
        )
        record = SecretRecord(
            handle=handle,
            purpose=purpose,
            owner=OPERATOR_OWNER,
            custodian=SECURE_STORE_CUSTODIAN,
            classification=classification,
            provisioned_on=provisioned_on,
        )
        self._records[handle] = record
        self._values[handle] = value
        return Provision(
            handle=handle,
            record=record,
            status=StoreStatus.OK,
            reason=(
                "provisioned and bound to its purpose (RFC-0009 §3 rule 1, "
                "§5.1, §7; SC7)"
            ),
        )

    def consume(
        self,
        handle: str,
        consumer: Consumer,
        purpose: str,
        consumed_on: date,
    ) -> Consumption:
        """Consume a secret at its named boundary (SC1, SC6, SC8).

        The store's only value-bearing operation: on discharge the
        value is materialized at the consume boundary for the named
        consumer and purpose, and consumption is recorded as metadata
        (last use) only (RFC-0009 §8, §15). The boundary holds closed
        and nothing crosses when the secret is unknown or invalidated,
        the consumer is outside the closed set (RFC-0009 §8), or the
        purpose differs from the provisioned one (SC7) — each refusal
        carries a non-empty reason (RFC-0009 §13; RFC-0001 §8.12).

        Args:
            handle: The opaque identifier to consume.
            consumer: The named consumer; only the Provider adapter is
                in the closed set (RFC-0009 §8).
            purpose: The purpose of this consumption; must equal the
                purpose bound at provisioning (SC7).
            consumed_on: The consumption date, recorded as metadata.

        Returns:
            The Consumption result: the materialized value at the
            boundary (empty when refused) plus the metadata label.
        """
        record = self._records.get(handle)
        if record is None:
            return Consumption(
                handle=handle,
                value="",
                status=StoreStatus.REFUSED,
                consumer=consumer,
                purpose=purpose,
                consumed_on=consumed_on,
                reason=(
                    "no secret is provisioned under this handle — unknown fails closed"
                ),
            )
        if record.invalidated_on is not None:
            return Consumption(
                handle=handle,
                value="",
                status=StoreStatus.REFUSED,
                consumer=consumer,
                purpose=purpose,
                consumed_on=consumed_on,
                reason=(
                    "the secret is invalidated — refused at every "
                    "boundary (RFC-0009 §6)"
                ),
            )
        if consumer is not Consumer.PROVIDER_ADAPTER:
            return Consumption(
                handle=handle,
                value="",
                status=StoreStatus.REFUSED,
                consumer=consumer,
                purpose=purpose,
                consumed_on=consumed_on,
                reason=(
                    "the consumer set is closed: the Provider adapter alone "
                    "(RFC-0009 §8; SC6)"
                ),
            )
        if purpose != record.purpose:
            return Consumption(
                handle=handle,
                value="",
                status=StoreStatus.REFUSED,
                consumer=consumer,
                purpose=purpose,
                consumed_on=consumed_on,
                reason=(
                    "consumption is single-purpose and scoped: this purpose "
                    "differs from the provisioned one (RFC-0009 §5.2, §6, §8; SC7)"
                ),
            )
        value = self._values.get(handle)
        if value is None:
            return Consumption(
                handle=handle,
                value="",
                status=StoreStatus.REFUSED,
                consumer=consumer,
                purpose=purpose,
                consumed_on=consumed_on,
                reason=(
                    "the store holds no value in custody for this handle — fail closed"
                ),
            )
        self._records[handle] = SecretRecord(
            handle=record.handle,
            purpose=record.purpose,
            owner=record.owner,
            custodian=record.custodian,
            classification=record.classification,
            provisioned_on=record.provisioned_on,
            last_used_on=consumed_on,
            invalidated_on=record.invalidated_on,
        )
        return Consumption(
            handle=handle,
            value=value,
            status=StoreStatus.OK,
            consumer=consumer,
            purpose=purpose,
            consumed_on=consumed_on,
            reason=(
                "consumed at the provider boundary for the stated purpose "
                "(RFC-0009 §5.2, §6, §8; SC6, SC7)"
            ),
        )

    def invalidate(
        self,
        handle: str,
        reason: str,
        invalidated_on: date,
    ) -> Destruction:
        """Invalidate a secret — refused at every boundary (RFC-0009 §6).

        The Operator revokes, or the system does as a fail-closed duty
        on suspected exposure (SC15). The invalidation is recorded as
        metadata; the value is never released again. Fail-closed: an
        unknown handle or an already-invalidated secret is refused
        with a non-empty reason — never silently succeeded, never
        fabricated.

        Args:
            handle: The opaque identifier to invalidate.
            reason: Why the secret is invalidated; non-empty, so the
                invalidation is never silent (RFC-0009 §15;
                RFC-0001 §8.12).
            invalidated_on: The invalidation date, recorded as
                metadata.

        Returns:
            The value-free Destruction result carrying the
            invalidation metadata.

        Raises:
            ValueError: If ``reason`` is empty.
        """
        if not reason:
            raise ValueError("an invalidation must carry a non-empty reason")
        record = self._records.get(handle)
        if record is None:
            return Destruction(
                handle=handle,
                status=StoreStatus.REFUSED,
                reason=(
                    "no secret is provisioned under this handle — unknown fails closed"
                ),
            )
        if record.invalidated_on is not None:
            return Destruction(
                handle=handle,
                status=StoreStatus.REFUSED,
                reason=(
                    "the secret is already invalidated — not silently re-invalidated"
                ),
                invalidated_on=record.invalidated_on,
            )
        self._records[handle] = SecretRecord(
            handle=record.handle,
            purpose=record.purpose,
            owner=record.owner,
            custodian=record.custodian,
            classification=record.classification,
            provisioned_on=record.provisioned_on,
            last_used_on=record.last_used_on,
            invalidated_on=invalidated_on,
        )
        return Destruction(
            handle=handle,
            status=StoreStatus.OK,
            reason=reason,
            invalidated_on=invalidated_on,
        )

    def destroy(
        self,
        handle: str,
        reason: str,
        destroyed_on: date,
    ) -> Destruction:
        """Destroy a secret: the value and the record (SC12).

        Removes the value from custody and the metadata record from
        the store; afterwards the handle is unknown and every
        operation on it is refused (RFC-0009 §12, §13). The
        destruction is recorded in the result — which secret, when,
        and why — never the value (§12.5, §15). Destruction is not
        undoable; recovery is re-provisioning by the Operator (§14).
        Fail-closed: an unknown handle is refused, never silently
        succeeded.

        Args:
            handle: The opaque identifier to destroy.
            reason: Why the secret is destroyed; non-empty.
            destroyed_on: The destruction date, recorded as metadata.

        Returns:
            The value-free Destruction result carrying the
            destruction metadata.

        Raises:
            ValueError: If ``reason`` is empty.
        """
        if not reason:
            raise ValueError("a destruction must carry a non-empty reason")
        record = self._records.get(handle)
        if record is None:
            return Destruction(
                handle=handle,
                status=StoreStatus.REFUSED,
                reason=(
                    "no secret is provisioned under this handle — unknown fails closed"
                ),
            )
        self._values.pop(handle, None)
        del self._records[handle]
        return Destruction(
            handle=handle,
            status=StoreStatus.OK,
            reason=reason,
            invalidated_on=record.invalidated_on,
            destroyed_on=destroyed_on,
        )

    def records(self) -> tuple[SecretRecord, ...]:
        """The Operator's value-free view of the store (RFC-0009 §15, §23).

        Every provisioned-but-not-destroyed secret's metadata record,
        sorted by handle for determinism. Never a value: records are
        metadata only and cannot reconstruct one (RFC-0009 §1, §15).

        Returns:
            A tuple of the store's current metadata records.
        """
        return tuple(sorted(self._records.values(), key=lambda record: record.handle))
