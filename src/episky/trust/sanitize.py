"""Deterministic sanitization primitives.

Owner: RFC-0007 §10 (the two-channel prompt-injection model this
    containment operationalizes), §11 (sanitization principles S1–S8);
    ratified decision notes DN-38 (the S3 neutralization primitives now,
    exact mechanics remain RFC-0012's), DN-39 (Hostile is produced only
    by the fail-closed paths), and Q6 (the rich result record; DN-34
    precedent).
Responsibility: the deterministic, pure, in-memory sanitization of text
    crossing a boundary toward the LLM, the Operator's terminal, or any
    interpreter — neutralizing control characters, ANSI escapes, and
    Unicode tricks (S3), quoting the contained form (S4), bounding size
    (S8), never changing the trust class (S1, T9), carrying provenance
    with the text (S1, T8), and failing closed to Hostile when the
    text's identity cannot be established (S6, T9, T11; DN-39 path 2).
    The primitives apply uniformly to every datum: containment, never
    discrimination.
Forbidden responsibility: never promotes (T6), never grants authority
    (RFC-0004 §7), never detects a hostile signal (DN-39; detection is
    RFC-0012 §16.6), never classifies or redacts secrets (S5; RFC-0009
    owns the mechanics), never summarizes, never rewrites meaning, never
    invokes runtime policy, never imports a forbidden package, never
    reads or writes anything, and never persists. Deterministic (S7):
    the same input always yields the same output.
"""

import re
from dataclasses import dataclass
from enum import Enum

from episky.trust.classes import Datum, ProvenanceState, TrustClass, TrustDomain

__all__ = [
    "DEFAULT_LIMIT",
    "Sanitization",
    "SanitizationStatus",
    "bound",
    "neutralize_control",
    "quote",
    "sanitize",
    "strip_ansi",
    "tame_unicode",
]

DEFAULT_LIMIT = 2000
"""Provisional default output bound for :func:`sanitize` (S8).

Provisional: RFC-0005 owns the exact output-size bounds (RFC-0007
§16.2); this constant makes the default deterministic and overridable
now, and the final ceiling is RFC-0005's.
"""

# A CSI (Control Sequence Introducer) sequence: ESC [ parameter bytes,
# optional intermediate bytes, final byte (RFC-0007 §10.1 #7; S3).
_ANSI_CSI = re.compile(r"\x1b\[[0-?]*[ -/]*[@-~]")

# OSC/DCS/PM/SOS/APC string sequences: ESC ] P X ^ _ ... terminated by
# BEL, ST (ESC \), or end of input (RFC-0007 §10.1 #7; S3).
_ANSI_STRING = re.compile(r"\x1b[\x5d\x50\x58\x5e\x5f][^\x07\x1b]*(?:\x07|\x1b\\|$)")

# The C0 controls (excluding TAB and NEWLINE, which are layout the
# Operator may need; S3 preserve content) plus DEL and the C1 controls.
# CR is escaped: a carriage return can overwrite a terminal line.
_CONTROLS_TO_ESCAPE = frozenset(
    chr(code) for code in range(0x00, 0x20) if code not in (0x09, 0x0A)
) | frozenset(chr(code) for code in range(0x7F, 0xA0))
_CONTROL_ESCAPES = {ord(char): f"\\x{ord(char):02x}" for char in _CONTROLS_TO_ESCAPE}

# The Unicode format/control characters a payload can hide behind:
# bidirectional overrides, LRM/RLM/ALM, zero-width characters, the word
# joiner, the soft hyphen, and the byte-order mark (RFC-0007 §10.1 #8).
# Tamed — shown as their \uXXXX form — never deleted (S3).
_UNICODE_TRICKS = frozenset(
    "\u200b\u200c\u200d\u200e\u200f\u202a\u202b\u202c\u202d\u202e"
    "\u2060\u2066\u2067\u2068\u2069\u061c\u00ad\ufeff"
)
_UNICODE_TAMED = {ord(char): f"\\u{ord(char):04x}" for char in _UNICODE_TRICKS}


class SanitizationStatus(Enum):
    """Whether sanitization established the text's contained form (S6).

    Members:
        OK: The text was neutralized, bounded, and quoted; its class is
            preserved (S1, T9).
        FAILED: The text's identity could not be established; it is
            Hostile and must not cross the boundary (S6, T9, T11).
    """

    OK = "ok"
    FAILED = "failed"


@dataclass(frozen=True, slots=True)
class Sanitization:
    """The deterministic result of sanitizing a datum (Q6; DN-34).

    The rich result record: the sanitized text plus the label it
    travels with — the class (unchanged or Hostile, T9), the status,
    and the provenance — so T8's "label travels with the text" and S1's
    "still carries its provenance" hold structurally. Frozen and
    slot-based: immutable and in-memory only.

    Attributes:
        text: The neutralized, bounded, quoted contained form (S3, S4,
            S8).
        trust_class: The datum's class, unchanged from the input, or
            Hostile when sanitization failed (S6, T9).
        status: OK, or FAILED when the content may not cross the
            boundary.
        provenance: The datum's provenance state, carried through
            unchanged (S1, T8).
        origin: The datum's origin trust domain, carried through
            unchanged (S1, T8; RFC-0007 §4).
        reason: Why the text is at this class and status.
    """

    text: str
    trust_class: TrustClass
    status: SanitizationStatus
    provenance: ProvenanceState
    origin: TrustDomain
    reason: str


def strip_ansi(text: str) -> str:
    """Strip ANSI/VT escape sequences from ``text`` (S3).

    Removes complete CSI sequences and OSC/DCS/PM/SOS/APC string
    sequences (including an unterminated one at end of input). Content
    between sequences is preserved. A bare ESC left after stripping is
    a control character and is neutralized by :func:`neutralize_control`.

    Args:
        text: The text to strip.

    Returns:
        The text with ANSI escape sequences removed.
    """
    return _ANSI_STRING.sub("", _ANSI_CSI.sub("", text))


def neutralize_control(text: str) -> str:
    """Neutralize control characters by escaping, preserving content (S3).

    Every C0 control except TAB and NEWLINE, and every DEL/C1 control,
    is replaced by its visible ``\\xHH`` hex form — escaped, never
    deleted, so the content the Operator may need survives in a form
    that cannot be read as direction. CR is escaped: it can spoof a
    terminal line. TAB and NEWLINE are preserved as layout.

    Args:
        text: The text to neutralize.

    Returns:
        The text with control characters escaped to visible forms.
    """
    return text.translate(_CONTROL_ESCAPES)


def tame_unicode(text: str) -> str:
    """Tame Unicode format/control tricks, preserving content (S3).

    Bidirectional overrides, LRM/RLM/ALM, zero-width characters, the
    word joiner, the soft hyphen, and the byte-order mark are replaced
    by their visible ``\\uXXXX`` forms — tamed, never deleted (S3).
    Homoglyph confusion is a detection concern and is not this layer's
    (DN-39; RFC-0012 §16.6).

    Args:
        text: The text to tame.

    Returns:
        The text with Unicode trick characters made visible.
    """
    return text.translate(_UNICODE_TAMED)


def bound(text: str, limit: int) -> str:
    """Bound ``text`` to ``limit`` characters with an explicit marker (S8).

    Truncation is explicit and labeled, never silent (RFC-0007 §12.5):
    when the input exceeds the bound, the first ``limit`` characters are
    kept and the truncation is marked with an ellipsis.

    Args:
        text: The text to bound.
        limit: The maximum number of content characters.

    Returns:
        ``text`` unchanged when it fits, otherwise the bounded prefix
        with an explicit truncation marker.

    Raises:
        ValueError: If ``limit`` is not positive.
    """
    if limit < 1:
        raise ValueError("a size bound must be positive")
    if len(text) <= limit:
        return text
    return text[:limit] + "…"


def quote(text: str) -> str:
    """Wrap ``text`` in the visible quoted contained form (S4).

    Quoted text is visibly data being shown, not an instruction being
    given — the text channel's carriage (RFC-0007 §10.2, §11 S4). The
    exact framing is RFC-0012's; this is the deterministic S4 primitive.

    Args:
        text: The text to quote.

    Returns:
        The text visibly wrapped as quoted content.
    """
    return f"«{text}»"


def sanitize(
    datum: Datum,
    trust_class: TrustClass,
    limit: int = DEFAULT_LIMIT,
) -> Sanitization:
    """Sanitize a datum's content deterministically (DN-38, Q6).

    Pure and deterministic (S7): the same datum, class, and bound always
    yield the same record, with no I/O, mutation, or runtime state. The
    text is stripped of ANSI sequences, control characters are escaped,
    Unicode tricks are tamed (S3), the result is bounded (S8), and the
    contained form is quoted (S4). The class never changes (S1, T9): it
    is preserved from the input unless sanitization fails.

    Sanitization fails closed when the text's identity cannot be
    established — here, when the datum's provenance is lost: without
    provenance the label cannot travel with the text (T8, S1), so the
    content may not cross the boundary and is Hostile (S6, T9, T11;
    DN-39 path 2). Classification and sanitization answer different
    questions: classify demotes a lost-provenance datum's held class to
    Untrusted (DN-39 path 3, C1); sanitize decides whether its content
    may cross a boundary *labeled* — it may not, and fails closed. No
    content is ever judged (no detection, no secret classification, no
    redaction): every datum is contained uniformly.

    Args:
        datum: The internal abstract datum whose content is sanitized
            (DN-37).
        trust_class: The datum's held class, preserved in the result
            unless sanitization fails (T9).
        limit: The output bound (S8); defaults to DEFAULT_LIMIT.

    Returns:
        The Sanitization record: the contained text, the class
        (unchanged or Hostile), the status, the provenance, and the
        reason.
    """
    contained = _contain(datum.content, limit)
    if datum.provenance is ProvenanceState.LOST:
        return Sanitization(
            text=contained,
            trust_class=TrustClass.HOSTILE,
            status=SanitizationStatus.FAILED,
            provenance=datum.provenance,
            origin=datum.origin,
            reason=(
                "loss of provenance: the label cannot travel with the text "
                "(RFC-0007 §15.6, S6, T9; DN-39)"
            ),
        )
    return Sanitization(
        text=contained,
        trust_class=trust_class,
        status=SanitizationStatus.OK,
        provenance=datum.provenance,
        origin=datum.origin,
        reason="neutralized, bounded, and quoted (RFC-0007 §11 S3, S4, S8)",
    )


def _contain(text: str, limit: int) -> str:
    """The contained form: neutralized, bounded, then quoted (S2–S4, S8).

    Stripping ANSI first consumes complete escape sequences; escaping
    then neutralizes any remaining control character; Unicode tricks are
    tamed; the content is bounded to size; and the contained form is
    quoted as visible content (S4). Bounding after neutralization caps
    what actually crosses the boundary (S8).
    """
    neutralized = tame_unicode(neutralize_control(strip_ansi(text)))
    return quote(bound(neutralized, limit))
