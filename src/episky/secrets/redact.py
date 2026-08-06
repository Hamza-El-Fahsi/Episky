"""Fail-closed redaction.

Owner: RFC-0009 §11 (redaction philosophy), §13 (failure: determinism
    first, then disclosure), §28 (SC13 — deterministic and testable,
    SC14 — fails closed); ratified decision note DN-42 (the deterministic
    redaction framework now; the exact catalogue remains
    RFC-0020/RFC-0012's).
Responsibility: the deterministic, pure, in-memory redaction of content
    crossing a boundary — a secret-classifier-gated transformation
    (consuming the C1 SecretClassification) that replaces secret-shaped
    spans at the boundary (RFC-0009 §11.3 detection, via the mechanical,
    explicitly non-exhaustive SECRET_SHAPES catalogue), then contains the
    result with trust.sanitize's bound/quote primitives (RFC-0007 S8/S4),
    and fails closed to WITHHELD when the no-secret property cannot be
    established (SC14). The trust class never changes on a crossing
    (S1, T9) and becomes Hostile when content is withheld (§15.5, §15.6).
    trust primitives are consumed, never re-implemented (DN-42).
Forbidden responsibility: never a guess (RFC-0009 §3 rule 5), never
    infers or reconstructs a missing value (the fixed REDACTION_MARKER
    replaces a span; nothing is re-derived), never rewrites semantics,
    never summarizes, never re-implements trust.sanitize or the C1
    classifier, never classifies (RFC-0009 §3 is classify.py's), never
    grants or denies authority (RFC-0004 §7), never executes, never
    reads or writes anything (no I/O, no mutation, no persistence), never
    depends on runtime state, and never imports a forbidden package.
    Deterministic (SC13; RFC-0007 S7): the same inputs always yield the
    same redaction.
"""

from dataclasses import dataclass
from enum import Enum

from episky.secrets.classify import SECRET_SHAPES, SecrecyClass, SecretClassification
from episky.trust.classes import TrustClass
from episky.trust.sanitize import DEFAULT_LIMIT, bound, quote

__all__ = [
    "REDACTION_MARKER",
    "Redaction",
    "RedactionStatus",
    "redact",
]

REDACTION_MARKER = "[REDACTED]"
"""The fixed marker replacing a secret-shaped span (RFC-0009 §11).

Deterministic and value-free: the span's content is never revealed, and
nothing is inferred in its place. The exact presentation of redacted
content is RFC-0015's; this is the mechanical default.
"""


class RedactionStatus(Enum):
    """Whether redaction produced a form safe to cross the boundary (SC14).

    Members:
        OK: The no-secret property was established — a fixed §2
            non-secret, or secret-shaped spans replaced and the result
            contained; the text may cross.
        WITHHELD: The no-secret property cannot be established — a secret
            value, or unclassifiable data; nothing crosses and the reason
            tells the Operator why (SC14; RFC-0001 §8.12).
    """

    OK = "ok"
    WITHHELD = "withheld"


@dataclass(frozen=True, slots=True)
class Redaction:
    """The deterministic result of redacting a datum's content (DN-42).

    The rich result record: the redacted, contained text plus the label
    it travels with — the status, the reason, the trust class (never
    upgraded, S1/T9; Hostile when withheld), the preserved secrecy
    classification, and the names of the shapes whose spans were
    replaced. Frozen and slot-based: immutable and in-memory only.

    Attributes:
        text: The redacted, bounded, quoted crossing form; empty when the
            content is withheld (nothing crosses).
        status: OK, or WITHHELD when the no-secret property cannot be
            established (SC14).
        reason: Why the text is in this state; non-empty, so a
            withholding is never silent (RFC-0001 §8.12).
        trust_class: The datum's trust class, unchanged from the input on
            a crossing (S1, T9), or Hostile when withheld (§15.5).
        classification: The SecretClassification the redaction was gated
            on, preserved — the secrecy label and provenance travel with
            the text (RFC-0009 §1, §15).
        replaced_shapes: The names of the catalogue shapes whose spans
            were replaced with REDACTION_MARKER; empty when none.
    """

    text: str
    status: RedactionStatus
    reason: str
    trust_class: TrustClass
    classification: SecretClassification
    replaced_shapes: tuple[str, ...]


def _replace_shapes(content: str) -> tuple[str, tuple[str, ...]]:
    """Replace every secret-shaped span with REDACTION_MARKER (RFC-0009 §11.3).

    Iterates the mechanical catalogue in declaration order and replaces
    every match of every shape. The marker is inert (matches no shape),
    so replacement order does not affect the result. Deterministic: the
    same content always yields the same redacted text and shape names.

    Args:
        content: The content to redact.

    Returns:
        The content with every secret-shaped span replaced, and the names
        of the shapes whose spans were replaced.
    """
    redacted = content
    replaced: list[str] = []
    for shape in SECRET_SHAPES:
        if shape.regex.search(redacted):
            redacted = shape.regex.sub(REDACTION_MARKER, redacted)
            replaced.append(shape.name)
    return redacted, tuple(replaced)


def redact(
    content: str,
    classification: SecretClassification,
    trust_class: TrustClass,
    limit: int = DEFAULT_LIMIT,
) -> Redaction:
    """Redact content deterministically for the boundary (RFC-0009 §11, §13).

    Pure and deterministic (SC13; RFC-0007 S7): the same content,
    classification, class, and bound always yield the same record, with
    no I/O, mutation, or runtime state. The transformation is gated on
    the C1 SecretClassification (DN-42) and layered per RFC-0009 §11.3:
    detection at the boundary replaces secret-shaped spans; containment
    bounds and quotes the residual via trust.sanitize (RFC-0007 S8/S4).

    - NON_SECRET: the fixed §2 class establishes the no-secret property;
      the content crosses contained (bounded, quoted), spans untouched.
    - SECRET_ADJACENT: every secret-shaped span is replaced with
      REDACTION_MARKER (detection), then the result is contained; no
      value crosses.
    - SECRET: a secret value never crosses a boundary (§1, §19, §23);
      the content is withheld.
    - HOSTILE: unclassifiable — the no-secret property cannot be
      established (§3 rule 4, §13.1); the content is withheld (SC14).

    The trust class never upgrades (S1, T9): it is preserved unchanged on
    a crossing, and becomes Hostile when content is withheld (§15.5,
    §15.6) — redaction is not trust, and it never promotes. Nothing is
    inferred, rewritten, or summarized in place of a removed value; the
    marker is fixed and the residual is contained, never reconstructed.

    Args:
        content: The content crossing the boundary, to be redacted.
        classification: The C1 classification the redaction is gated on;
            preserved in the result (provenance travels with the text).
        trust_class: The datum's current trust class, preserved unless the
            content is withheld (S1, T9).
        limit: The containment bound (S8), applied via trust.sanitize's
            ``bound``; defaults to trust's DEFAULT_LIMIT.

    Returns:
        The Redaction record: the redacted, contained crossing text (or
        empty when withheld), the status, the reason, the trust class,
        the preserved classification, and the replaced shape names.

    Raises:
        ValueError: If ``limit`` is not positive (from trust's ``bound``).
    """
    if classification.secrecy_class is SecrecyClass.HOSTILE:
        return Redaction(
            text="",
            status=RedactionStatus.WITHHELD,
            reason=(
                "unclassifiable: the no-secret property cannot be "
                "established (RFC-0009 §3 rule 4, §13.1; SC14) — content "
                "withheld, nothing crosses"
            ),
            trust_class=TrustClass.HOSTILE,
            classification=classification,
            replaced_shapes=(),
        )
    if classification.secrecy_class is SecrecyClass.SECRET:
        return Redaction(
            text="",
            status=RedactionStatus.WITHHELD,
            reason=(
                "a secret value never crosses a boundary (RFC-0009 §1, "
                "§19.1, §23.2; SC14) — withheld, nothing crosses"
            ),
            trust_class=TrustClass.HOSTILE,
            classification=classification,
            replaced_shapes=(),
        )
    if classification.secrecy_class is SecrecyClass.SECRET_ADJACENT:
        redacted, replaced = _replace_shapes(content)
        return Redaction(
            text=quote(bound(redacted, limit)),
            status=RedactionStatus.OK,
            reason=(
                "secret-shaped spans replaced and contained (RFC-0009 "
                "§3 rule 3, §11; RFC-0007 S8/S4)"
            ),
            trust_class=trust_class,
            classification=classification,
            replaced_shapes=replaced,
        )
    return Redaction(
        text=quote(bound(content, limit)),
        status=RedactionStatus.OK,
        reason="established non-secret and contained (RFC-0009 §2; RFC-0007 S8/S4)",
        trust_class=trust_class,
        classification=classification,
        replaced_shapes=(),
    )
