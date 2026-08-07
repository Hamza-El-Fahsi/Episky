"""Secret-free boundary enforcement (RFC-0012 §9, §13, §19, §23, §24, §32;
RFC-0009 SC2, SC16; RFC-0007 S1–S8).

Owner: RFC-0012 §13 (Context Boundaries); RFC-0004 §4.11 (the enforcement
    point).
Responsibility: the deterministic enforcement point every input crosses
    before it may enter Context or a View (DN-67): trust classification
    and hostile exclusion through `trust` (RFC-0012 §9 rule 4; T11),
    secret classification and fail-closed exclusion through the `secrets`
    classifier (SC2, T10; RFC-0012 §32 rule 1), personal data held secret
    until an explicit Operator demotion (SC16; RFC-0009 §14), and S1–S8
    neutralization and containment through `trust.sanitize`. Every
    refusal is disclosed, never silent; nothing is invented; malformed or
    uncertain inputs are refused explicitly; and the boundary is
    value-free — refused material never crosses and admitted material
    crosses only in its contained form. The per-source catalogue (which
    treatment for which source) is RFC-0020's (Q3); this module is the
    mechanism now, with a placeholder-default bound (DN-18).
Forbidden responsibility: no classification, sanitization, or redaction
    logic of its own — the module delegates to `trust` and `secrets` and
    never re-implements them; never reads a secret value into Context
    (SC2 construction); no I/O, no provider call, no live session state;
    never the Audit (CM15); never a truth verdict (CM1) or authority
    (CM16).
"""

from dataclasses import dataclass
from enum import Enum

from episky.secrets.classify import (
    NonSecretDesignation,
    SecrecyClass,
    SecretDatum,
    SecretMetadata,
    SecretOrigin,
)
from episky.secrets.classify import (
    classify as classify_secret,
)
from episky.trust.classes import (
    Datum,
    ProvenanceState,
    TrustCategory,
    TrustClass,
    TrustDomain,
)
from episky.trust.classes import (
    classify as classify_trust,
)
from episky.trust.hostile import Quarantine, quarantine
from episky.trust.sanitize import SanitizationStatus, sanitize

__all__ = [
    "BoundaryDecision",
    "BoundaryDisposition",
    "BoundaryInput",
    "BoundaryRefusal",
    "BoundaryReport",
    "DEFAULT_BOUNDARY_LIMIT",
    "admit",
    "admit_all",
]

DEFAULT_BOUNDARY_LIMIT = 2000
"""Provisional default bound for admitted text (DN-18; RFC-0007 S8).

Provisional: the concrete per-source sanitization catalogue and bounds
are RFC-0020's (RFC-0012 §37 OQ3; Q3); this constant makes the default
deterministic and overridable now, following the DN-18 placeholder
precedent.
"""


class BoundaryDisposition(Enum):
    """Whether a datum is admitted to Context or refused at the boundary.

    Members:
        ADMITTED: The material crossed in its contained, secret-free
            form.
        REFUSED: The material failed closed and did not cross; the
            refusal is disclosed, never silent.
    """

    ADMITTED = "admitted"
    REFUSED = "refused"


class BoundaryRefusal(Enum):
    """The deterministic refusal reasons, disclosed not silent (RFC-0001 §8.12).

    Each maps to one of the fixed RFC-0012 §9 exclusions or a fail-closed
    classification path; when several apply, the first in the boundary's
    fixed order is disclosed.

    Members:
        UNPURPOSEFUL: No stated purpose — nothing enters without one
            (RFC-0012 §9 rule 7; CM5).
        MALFORMED: The input is structurally invalid and cannot be
            classified (fail-closed).
        HOSTILE: Hostile or quarantined content (RFC-0012 §9 rule 4;
            T11).
        SECRET: A provisioned or Operator-marked secret value (RFC-0009
            §3 rules 1–2; SC2).
        SECRET_ADJACENT: Secret-shaped captured data, unproven (RFC-0009
            §3 rule 3; fail-closed).
        UNCLASSIFIABLE: Unprovable captured data, failed closed
            (RFC-0009 §3 rule 4; RFC-0007 §15.5).
        UNPROVENANCED: Provenance lost — the label cannot travel with the
            text (RFC-0007 S6; RFC-0012 §9 rule 3).
    """

    UNPURPOSEFUL = "unpurposeful"
    MALFORMED = "malformed"
    HOSTILE = "hostile"
    SECRET = "secret"
    SECRET_ADJACENT = "secret-adjacent"
    UNCLASSIFIABLE = "unclassifiable"
    UNPROVENANCED = "unprovenanced"


@dataclass(frozen=True, slots=True)
class BoundaryInput:
    """The structured boundary input for one datum (DN-67).

    A pure value describing material about to cross into Context: its
    content, the trust category and domain it originates in, whether its
    provenance is established, the stated purpose (CM5), and the optional
    explicit RFC-0009 §2 designation that proves it non-secret. The one
    demotion path — an Operator mark that personal data is public for a
    stated purpose (SC16; RFC-0009 §14) — is carried as
    ``designation=NonSecretDesignation.MARKED_PUBLIC``.

    Attributes:
        content: The datum's text content, carried as-is for the
            classifiers.
        category: The RFC-0007 §6 information category.
        origin: The RFC-0007 §4 trust domain the datum originates in.
        provenance: Whether the datum's provenance is established
            (RFC-0007 §9.6).
        purpose: The stated purpose (CM5); a blank purpose refuses.
        designation: The optional fixed §2 non-secret designation,
            established by explicit context (RFC-0009 §2).
        secret_origin: The RFC-0009 §7 origin the datum arrived through;
            CAPTURED for boundary material, MARKED for Operator-marked
            values (SC16), PROVISIONED for Secure-Store values (SC2).
        provider: The optional provider/context name carried into the
            value-free SecretMetadata (RFC-0009 §1).
    """

    content: str
    category: TrustCategory
    origin: TrustDomain
    provenance: ProvenanceState
    purpose: str
    designation: NonSecretDesignation | None = None
    secret_origin: SecretOrigin = SecretOrigin.CAPTURED
    provider: str | None = None


@dataclass(frozen=True, slots=True)
class BoundaryDecision:
    """The deterministic outcome of the enforcement point for one datum.

    Frozen and slot-based: an immutable record. When ADMITTED, ``text``
    is the contained, neutralized, bounded form that crosses — the label
    travels with it (T8). When REFUSED, ``text`` is empty: the raw value
    never crosses and the refusal is disclosed, never silent. All fields
    are value-free with respect to secrets (RFC-0009 §1).

    Attributes:
        disposition: Whether the datum crossed or was refused.
        refusal: The deterministic refusal reason, None when admitted.
        text: The contained form when admitted; empty when refused.
        trust_class: The held trust class (T9), or None when refused
            before classification.
        reason: Why the datum holds this disposition (fail-loud).
        metadata: The value-free SecretMetadata facet when a secrecy
            classification ran (RFC-0009 §1).
        quarantine: The Hostile quarantine record when content was
            quarantined (RFC-0007 §15.5).
    """

    disposition: BoundaryDisposition
    refusal: BoundaryRefusal | None
    text: str
    trust_class: TrustClass | None
    reason: str
    metadata: SecretMetadata | None = None
    quarantine: Quarantine | None = None


@dataclass(frozen=True, slots=True)
class BoundaryReport:
    """The ordered outcome of processing a set of inputs (RFC-0007 S7).

    Processed in input order so the report is deterministic: the same
    inputs always yield the same report. Admitted items carry their
    contained form; refused items carry their disclosure and empty text.
    """

    decisions: tuple[BoundaryDecision, ...]


def _refuse(
    refusal: BoundaryRefusal,
    reason: str,
    *,
    trust_class: TrustClass | None = None,
    metadata: SecretMetadata | None = None,
    quarantine_record: Quarantine | None = None,
) -> BoundaryDecision:
    """Build the fail-closed decision: no text crosses, the reason does."""
    return BoundaryDecision(
        disposition=BoundaryDisposition.REFUSED,
        refusal=refusal,
        text="",
        trust_class=trust_class,
        reason=reason,
        metadata=metadata,
        quarantine=quarantine_record,
    )


def _secret_datum(datum: BoundaryInput) -> SecretDatum:
    """Map the boundary input to the secrets classifier's datum (DN-67).

    Only the mapping is here — the classification itself is the `secrets`
    layer's. The one demotion path (RFC-0009 §14) keys off MARKED_PUBLIC;
    everything else is classified at the datum's carried origin.
    """
    origin = (
        SecretOrigin.MARKED
        if datum.designation is NonSecretDesignation.MARKED_PUBLIC
        else datum.secret_origin
    )
    return SecretDatum(
        content=datum.content,
        origin=origin,
        designation=datum.designation,
        provider=datum.provider,
    )


def admit(
    datum: BoundaryInput, limit: int = DEFAULT_BOUNDARY_LIMIT
) -> BoundaryDecision:
    """Run one datum through the enforcement point (DN-67; RFC-0012 §9).

    Pure and deterministic (S7): the same input and bound always yield
    the same decision, with no I/O, mutation, or runtime state. In fixed
    order the boundary applies the stated-purpose gate (CM5), the
    malformed-input gate, the trust classification and hostile exclusion
    (RFC-0012 §9 rule 4; T11), the secrets classification and fail-closed
    exclusion (SC2, T10; RFC-0012 §32 rule 1) including the SC16
    privacy-parity rule for personal data, and the S1–S8 neutralization
    and containment (RFC-0007 §11) that produces the form that crosses.
    Refused material never crosses: its raw value appears nowhere in the
    decision.

    Args:
        datum: The structured boundary input.
        limit: The output bound for admitted text (S8); defaults to
            DEFAULT_BOUNDARY_LIMIT.

    Returns:
        The BoundaryDecision: admitted with its contained text, or
        refused with its disclosure.

    Raises:
        ValueError: If ``limit`` is not positive.
    """
    if limit < 1:
        raise ValueError("a boundary output bound must be positive (RFC-0007 S8)")
    if not datum.purpose.strip():
        return _refuse(
            BoundaryRefusal.UNPURPOSEFUL,
            "nothing enters Context without a stated purpose (RFC-0012 §9 rule 7; CM5)",
        )
    if not datum.content.strip():
        return _refuse(
            BoundaryRefusal.MALFORMED,
            "blank content is malformed and fails closed at the boundary",
        )
    trust_datum = Datum(
        category=datum.category,
        content=datum.content,
        provenance=datum.provenance,
        origin=datum.origin,
    )
    trust_classification = classify_trust(trust_datum)
    if trust_classification.trust_class is TrustClass.HOSTILE:
        record = quarantine(
            trust_datum, TrustClass.HOSTILE, trust_classification.reason
        )
        return _refuse(
            BoundaryRefusal.HOSTILE,
            trust_classification.reason,
            trust_class=TrustClass.HOSTILE,
            quarantine_record=record,
        )
    try:
        secret_classification = classify_secret(_secret_datum(datum))
    except ValueError as exc:
        return _refuse(
            BoundaryRefusal.MALFORMED,
            str(exc),
            trust_class=trust_classification.trust_class,
        )
    if secret_classification.secrecy_class is not SecrecyClass.NON_SECRET:
        refusal = {
            SecrecyClass.SECRET: BoundaryRefusal.SECRET,
            SecrecyClass.SECRET_ADJACENT: BoundaryRefusal.SECRET_ADJACENT,
            SecrecyClass.HOSTILE: BoundaryRefusal.UNCLASSIFIABLE,
        }[secret_classification.secrecy_class]
        return _refuse(
            refusal,
            secret_classification.reason,
            trust_class=trust_classification.trust_class,
            metadata=secret_classification.metadata,
        )
    sanitization = sanitize(trust_datum, trust_classification.trust_class, limit)
    if sanitization.status is SanitizationStatus.FAILED:
        return _refuse(
            BoundaryRefusal.UNPROVENANCED,
            sanitization.reason,
            trust_class=sanitization.trust_class,
        )
    return BoundaryDecision(
        disposition=BoundaryDisposition.ADMITTED,
        refusal=None,
        text=sanitization.text,
        trust_class=sanitization.trust_class,
        reason=sanitization.reason,
        metadata=secret_classification.metadata,
    )


def admit_all(
    items: tuple[BoundaryInput, ...], limit: int = DEFAULT_BOUNDARY_LIMIT
) -> BoundaryReport:
    """Process a set of inputs in order, deterministically (RFC-0007 S7).

    Each input is run through the enforcement point in input order; the
    report preserves that order so the same set always yields the same
    report. Refused items carry their disclosure and empty text; nothing
    is silently dropped.
    """
    return BoundaryReport(tuple(admit(item, limit) for item in items))
