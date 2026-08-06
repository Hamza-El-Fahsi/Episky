"""Deterministic secret classification.

Owner: RFC-0009 §1 (what is a secret), §2 (what is not), §3 (the six
    classification rules), §7 (the three origins), §14 (the one demotion
    path); ratified decision note DN-44 (internal abstract input, the
    value/metadata split, the latent schema edge).
Responsibility: the secrecy vocabulary and its data — the four-class
    secrecy predicate (secret / non-secret / secret-adjacent / Hostile,
    blueprint §5), the three §7 origins, the six fixed §2 non-secret
    classes, and the mechanical, explicitly non-exhaustive shape
    catalogue for §3 rule 3 — and the deterministic, pure classify()
    operation over them: rules 1–4 (provisioned and Operator-marked
    values are secrets; secret-shaped captured values are secret-adjacent
    until proven otherwise; unclassifiable data fails closed to Hostile),
    with rule 5 (the LLM never classifies) enforced as a property of this
    module (stdlib-only, no I/O, no network, no statistical path) and
    rule 6 (classification is testable) by this module's tests. The §1
    value/metadata split is structural: classify() returns a value-free
    SecretClassification whose only exportable facet is the
    SecretMetadata record (existence, provider, dates); the value itself
    never leaves the boundary and never appears in a derived artifact.
Forbidden responsibility: never a guess (RFC-0009 §3 rule 5; RFC-0001
    §8.5 by analogy), never claims the shape catalogue is complete
    (RFC-0009 §30 OQ2 defers the exact catalogue), never grants or denies
    authority (RFC-0004 §7; custody is not ownership, RFC-0009 §4), never
    sanitizes or redacts (RFC-0009 §11 is redact.py's), never reads or
    writes anything (no I/O, no mutation, no persistence), never depends
    on runtime state, and never imports `schema` or `trust` this
    iteration — both declared edges stay latent (DN-44; the DN-37
    precedent); the correspondence of HOSTILE to `TrustClass.HOSTILE`
    (RFC-0007 §15.5) is documented, not imported. Deterministic (RFC-0007
    S7; RFC-0009 §3 rule 6): the same datum always classifies the same
    way.
"""

import re
from dataclasses import dataclass
from datetime import date
from enum import Enum

__all__ = [
    "NonSecretDesignation",
    "SECRET_SHAPES",
    "SecretClassification",
    "SecretDatum",
    "SecretMetadata",
    "SecretOrigin",
    "SecretShape",
    "SecrecyClass",
    "classify",
]


class SecrecyClass(Enum):
    """The four secrecy classes a datum can hold (blueprint §5; RFC-0009 §3).

    Exactly the four blueprint §5 outputs, mutually exclusive and
    exhaustive: every datum is classified exactly once into one of them.
    HOSTILE is the outcome class corresponding to ``TrustClass.HOSTILE``
    (RFC-0007 §15.5: quarantined, excluded from Context and the Provider
    View) as the *secrecy* predicate's result — distinct from trust
    classification (Q5, DN-44) — and is reached only by the fail-closed
    path of §3 rule 4.

    Members:
        SECRET: A value whose holding grants a capability the Operator
            did not intend to expose (RFC-0009 §1); reached by §3 rules
            1–2 (provisioned or Operator-marked).
        NON_SECRET: A fixed §2 non-secret, established by explicit
            designation, never by judgment (RFC-0009 §2).
        SECRET_ADJACENT: Secret-shaped captured data, classified
            secret-adjacent until proven otherwise (§3 rule 3).
        HOSTILE: Unclassifiable data, failed closed — quarantined and
            excluded (§3 rule 4; RFC-0007 §15.5).
    """

    SECRET = "secret"
    NON_SECRET = "non-secret"
    SECRET_ADJACENT = "secret-adjacent"
    HOSTILE = "hostile"


class SecretOrigin(Enum):
    """The three origins through which secrets enter (RFC-0009 §7).

    Every secret-bearing datum arrives through exactly one of them; the
    classifier keys rules 1–4 off it.

    Members:
        PROVISIONED: The Operator brings a key or token into the Secure
            Store for a stated purpose (§7 rule 1) — the only origin
            producing a governed secret; secret by definition (§3 rule 1).
        MARKED: The Operator marks content private, promoting it into the
            secret class (§7 rule 2); secret by definition (§3 rule 2),
            demotable only along the §14 path.
        CAPTURED: Machine output or configuration contains a
            secret-shaped value (§7 rule 3) — discovery, classified by
            content (§3 rules 3–4); never adopted, contained and
            discarded.
    """

    PROVISIONED = "provisioned"
    MARKED = "marked"
    CAPTURED = "captured"


class NonSecretDesignation(Enum):
    """The six fixed non-secret classes (RFC-0009 §2).

    Fixed classes, not judgment calls (§2). Each is established only by
    explicit designation carried in the datum's provenance/origin context
    — recognized deterministically, never inferred by content guessing
    (this classifier has no heuristics; §3 rule 5).

    Members:
        PUBLIC_MACHINE_FACT: distro, kernel, package lists, service
            states (§2 rule 1).
        NO_CAPABILITY_AGGREGATE: a derived value that cannot become a
            credential or authorization (§2 rule 2).
        MECHANISM: the fact that secrets are stored, the names of the
            boundaries (§2 rule 3).
        SANITIZED_TEXT: a log line with its secret fields removed
            (§2 rule 4).
        OPERATOR_PREFERENCE: verbosity, provider choice, skill selection
            (§2 rule 5).
        MARKED_PUBLIC: personal data the Operator explicitly marks
            public — the one demotion path (§2 rule 6; RFC-0009 §14).
    """

    PUBLIC_MACHINE_FACT = "public-machine-fact"
    NO_CAPABILITY_AGGREGATE = "no-capability-aggregate"
    MECHANISM = "mechanism"
    SANITIZED_TEXT = "sanitized-text"
    OPERATOR_PREFERENCE = "operator-preference"
    MARKED_PUBLIC = "marked-public"


@dataclass(frozen=True, slots=True)
class SecretShape:
    """A mechanical secret-shape recognition rule (§3 rule 3).

    One named, compiled regular expression with a description naming the
    RFC-0009 §1 class it instantiates. The catalogue it belongs to
    (SECRET_SHAPES) is mechanical and explicitly non-exhaustive: it never
    claims completeness (RFC-0009 §30 OQ2 defers the exact catalogue to
    RFC-0020/RFC-0012). A shape adds one more mechanical recognition
    path; nothing here proves a datum non-secret (rule 3's "until proven
    otherwise" is satisfied by an explicit §2 designation, never by a
    failed match).

    Attributes:
        name: The shape's stable name, carried in the classification's
            ``shape`` field.
        regex: The compiled, deterministic pattern.
        description: The §1 class the shape instantiates.
    """

    name: str
    regex: re.Pattern
    description: str


SECRET_SHAPES: tuple[SecretShape, ...] = (
    SecretShape(
        name="bearer-token",
        regex=re.compile(r"(?i)\bbearer\s+[A-Za-z0-9._~+/=-]{12,}"),
        description="Bearer authentication scheme plus token (RFC-0009 §1 rule 2)",
    ),
    SecretShape(
        name="prefixed-api-key",
        regex=re.compile(
            r"\b(sk-[A-Za-z0-9]{20,}|gh[pousr]_[A-Za-z0-9]{20,}|AKIA[0-9A-Z]{16})\b"
        ),
        description="Common prefixed API-key shape (RFC-0009 §1 rule 2)",
    ),
    SecretShape(
        name="json-web-token",
        regex=re.compile(
            r"\beyJ[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\.[A-Za-z0-9_-]{8,}\b"
        ),
        description="JOSE-format JSON Web Token (RFC-0009 §1 rule 2)",
    ),
    SecretShape(
        name="private-key-block",
        regex=re.compile(r"-----BEGIN [A-Z0-9 ]*PRIVATE KEY-----"),
        description="PEM private-key block begin marker (RFC-0009 §1 rule 3)",
    ),
    SecretShape(
        name="secret-assignment",
        regex=re.compile(
            r"(?i)\b(api[_-]?key|access[_-]?key|secret[_-]?key|secret|password|passwd|auth[_-]?token)\b\s*[:=]\s*[A-Za-z0-9._~+/=-]{8,}"
        ),
        description="Secret-named assignment in configuration (RFC-0009 §1 rule 4)",
    ),
)


@dataclass(frozen=True, slots=True)
class SecretDatum:
    """The internal abstract input classify() operates on (DN-44).

    Not a ``schema.Fact`` (Facts are secret-free by construction,
    RFC-0009 §21) and not a bare string: content plus the
    provenance/origin context that decides the class. Frozen and
    slot-based: immutable, in-memory only (DN-1). The datum is the
    value-bearing side of the §1 split — it carries the material and
    never crosses a boundary; classify() returns only value-free labels.

    Attributes:
        content: The datum's text content, carried as-is; secret shapes
            are matched against it mechanically (§3 rule 3).
        origin: The §7 origin the datum arrived through; rules 1–4 key
            off it.
        designation: Optional explicit evidence the datum is one of the
            fixed §2 non-secret classes. Established only by explicit
            context, never by content guessing (§3 rule 5).
        provider: Optional provider/context the datum is associated with,
            carried into SecretMetadata.provider (value-free).
    """

    content: str
    origin: SecretOrigin
    designation: NonSecretDesignation | None = None
    provider: str | None = None


@dataclass(frozen=True, slots=True)
class SecretMetadata:
    """The value-free account of a classified datum (RFC-0009 §1).

    What can be said without revealing the value: existence, provider,
    and lifecycle dates — the only exportable facet of a classification
    (the Audit's and the Operator's window, RFC-0009 §15, §23). Never
    carries content or any material sufficient to reconstruct a value.
    classify() fills existence and provider; the date fields are the
    lifecycle stages' to fill (provisioning and use records, C3) and are
    None at classification time.

    Attributes:
        existence: Whether a secret exists here — True for SECRET and
            SECRET_ADJACENT, and for HOSTILE (unprovable data is treated
            as containing secret material, fail closed); False only for
            NON_SECRET.
        provider: The provider/context the datum is associated with, if
            the origin context named one.
        provisioned_on: The provisioning date (C3), None until then.
        last_used_on: The last consumption date (C3), None until then.
        invalidated_on: The invalidation/destruction date (C3), None
            until then.
    """

    existence: bool
    provider: str | None
    provisioned_on: date | None = None
    last_used_on: date | None = None
    invalidated_on: date | None = None


@dataclass(frozen=True, slots=True)
class SecretClassification:
    """The deterministic, value-free result of classifying a datum.

    The four-class label plus the context that produced it and the
    metadata view. Value-bearing by subject (it classifies a value), but
    value-free in substance: it never carries the datum's content and
    never lets a value be re-displayed or exported beyond its boundary —
    only the ``metadata`` facet may cross (RFC-0009 §1, §15).

    Attributes:
        secrecy_class: The class the datum holds.
        origin: The §7 origin, preserved from the datum (provenance
            travels with the label).
        reason: Why the datum holds this class — the §3 rule, the §2
            fixed class, or the §14 demotion.
        metadata: The value-free SecretMetadata view of this
            classification.
        shape: The matched catalogue shape's name, for SECRET_ADJACENT.
        designation: The §2 fixed class, for NON_SECRET.
    """

    secrecy_class: SecrecyClass
    origin: SecretOrigin
    reason: str
    metadata: SecretMetadata
    shape: str | None = None
    designation: NonSecretDesignation | None = None


def _matches_any_shape(content: str) -> str | None:
    """Return the name of the first catalogue shape matching `content`, or None.

    Mechanical and deterministic (§3 rule 3): iterates the catalogue in
    declaration order and returns the first match. The catalogue is
    explicitly non-exhaustive — no match never proves a datum non-secret.
    """
    for shape in SECRET_SHAPES:
        if shape.regex.search(content):
            return shape.name
    return None


def classify(datum: SecretDatum) -> SecretClassification:
    """Classify a datum deterministically (RFC-0009 §1, §2, §3, §7, §14).

    Pure and deterministic (S7; §3 rule 6): the same datum always yields
    the same classification, with no I/O, mutation, or runtime state.
    Rules 1–4 decide by origin and, for captured data, by designation
    then shape:

    1. Provisioned values are secrets (§3 rule 1).
    2. Operator-marked values are secrets (§3 rule 2), except the §14
       demotion: an Operator-marked datum explicitly designated
       MARKED_PUBLIC is NON_SECRET (§2 rule 6, §14).
    3. Secret-shaped captured values are SECRET_ADJACENT until proven
       otherwise (§3 rule 3; the mechanical, non-exhaustive catalogue).
    4. Unclassifiable captured data fails closed to HOSTILE (§3 rule 4;
       RFC-0007 §15.5) — never "probably not a secret" (§2).

    Rule 5 (the LLM never classifies) is a property of this module
    (stdlib-only, no I/O, no network), enforced by the conformance test.
    Contradictory inputs are rejected: a provisioned value carries no
    designation, and an Operator-marked value carries no designation
    other than MARKED_PUBLIC.

    Args:
        datum: The internal abstract datum to classify.

    Returns:
        The value-free SecretClassification, carrying the class, origin,
        reason, metadata, and (where relevant) shape or designation.

    Raises:
        ValueError: If the datum's designation contradicts its origin
            (a provisioned value designated non-secret; an
            Operator-marked value designated a non-secret other than
            MARKED_PUBLIC).
    """
    if datum.origin is SecretOrigin.PROVISIONED:
        if datum.designation is not None:
            raise ValueError(
                "a provisioned value is secret by definition (RFC-0009 §3 "
                "rule 1) and cannot carry a non-secret designation"
            )
        secrecy_class = SecrecyClass.SECRET
        reason = "provisioned into the Secure Store (RFC-0009 §3 rule 1)"
        shape = None
        designation = None
    elif datum.origin is SecretOrigin.MARKED:
        if datum.designation is NonSecretDesignation.MARKED_PUBLIC:
            secrecy_class = SecrecyClass.NON_SECRET
            reason = "Operator-marked public (RFC-0009 §2 rule 6, §14)"
            designation = NonSecretDesignation.MARKED_PUBLIC
            shape = None
        elif datum.designation is None:
            secrecy_class = SecrecyClass.SECRET
            reason = "Operator-marked value (RFC-0009 §3 rule 2)"
            designation = None
            shape = None
        else:
            raise ValueError(
                "an Operator-marked value is secret (RFC-0009 §3 rule 2); "
                "the only demotion is an explicit MARKED_PUBLIC (§14)"
            )
    else:
        if datum.designation is not None:
            secrecy_class = SecrecyClass.NON_SECRET
            reason = f"fixed non-secret (RFC-0009 §2): {datum.designation.name}"
            designation = datum.designation
            shape = None
        else:
            shape = _matches_any_shape(datum.content)
            if shape is not None:
                secrecy_class = SecrecyClass.SECRET_ADJACENT
                reason = f"secret-shaped (RFC-0009 §3 rule 3): {shape}"
                designation = None
            else:
                secrecy_class = SecrecyClass.HOSTILE
                reason = (
                    "unclassifiable — fails closed (RFC-0009 §3 rule 4; RFC-0007 §15.5)"
                )
                designation = None
                shape = None
    metadata = SecretMetadata(
        existence=secrecy_class is not SecrecyClass.NON_SECRET,
        provider=datum.provider,
    )
    return SecretClassification(
        secrecy_class=secrecy_class,
        origin=datum.origin,
        reason=reason,
        metadata=metadata,
        shape=shape,
        designation=designation,
    )
