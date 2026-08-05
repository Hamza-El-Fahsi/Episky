"""Trust classes, lattice, and deterministic classification.

Owner: RFC-0007 §4 (trust domains), §5 (trust classes, lattice), §6
    (information categories), §9 (demotion); ratified decision notes
    DN-36 (category/domain vocabulary) and DN-37 (abstract datum
    classification).
Responsibility: the trust vocabulary and its data — the four trust
    classes in the §5 total order, the twelve trust domains with their
    §4 default postures, the nine in-scope information categories with
    their §6 default classes — and the deterministic, pure operations
    over them: meet/join (most-restrictive rule, §5.1), downgrade
    (reason-preserving demotion, §9), and classify (a datum's class from
    its category default and provenance state, DN-37). Hostile is
    reachable only by the fail-closed paths the layer owns (§15.5; T11;
    DN-39): here, a datum whose provenance is lost is demoted per
    RFC-0007 §6/§9.6 — Hostile for Observation, Untrusted otherwise.
Forbidden responsibility: never promotes (T6; the only upward moves are
    RFC-0005 normalization and RFC-0006 confirmation, owned elsewhere —
    Q4), never grants authority (RFC-0004 §7 grants this package none),
    never sanitizes, never detects (RFC-0012 §16.6), never reads or
    writes anything (no I/O, no mutation, no persistence), never
    depends on runtime state, and never imports `schema` this iteration
    (the declared edge stays latent, DN-37). Deterministic (S7): the
    same datum always classifies the same way.
"""

from collections.abc import Mapping
from dataclasses import dataclass
from enum import Enum
from types import MappingProxyType

__all__ = [
    "CATEGORY_DEFAULTS",
    "CATEGORY_ORIGINS",
    "Classification",
    "Datum",
    "Demotion",
    "PROVENANCE_LOSS_DEMOTION",
    "ProvenanceState",
    "TRUST_DOMAIN_POSTURES",
    "TrustCategory",
    "TrustClass",
    "TrustDomain",
    "classify",
    "downgrade",
    "join",
    "meet",
]


class TrustClass(Enum):
    """The finite trust classes at which information is held (RFC-0007 §5).

    Exactly four classes, in the §5 total order. ``value`` encodes the
    order: higher is more trusted, and the most restrictive class is the
    lowest (Hostile). A class is a property of *information*, never an
    actor (RFC-0004 §2): nothing here grants trust, it only records the
    class a datum holds per RFC-0007's rules.

    Members:
        TRUSTED: Accepted without independent re-derivation, within a
            declared scope (§5).
        CONDITIONAL: Accepted only after a deterministic check passes
            (§5).
        UNTRUSTED: Data, never authority; contained, never executed,
            never evidence of itself (§5).
        HOSTILE: Untrusted plus a positive signal of adversarial intent;
            quarantined, excluded from Context and the Provider View
            (§5, §15.5).
    """

    TRUSTED = 4
    CONDITIONAL = 3
    UNTRUSTED = 2
    HOSTILE = 1


class TrustDomain(Enum):
    """The trust domains in which information originates (RFC-0007 §4).

    The twelve §4 domains, in the table's order. Every datum originates
    in exactly one domain (§4); the domain's default posture is carried
    as data in TRUST_DOMAIN_POSTURES. A domain is not an actor and not a
    component (RFC-0004 §2).

    Members:
        OPERATOR: Goal, Symptom, replies, pasted content (§4.1).
        CORE: Orchestrator, Fact Layer, Policy Engine, Executor,
            Context Manager, Audit (§4.2).
        DIAGNOSTICS: Collectors and normalization (§4.3).
        POLICY_ENGINE: Classification and gating (§4.4).
        ACTION_EXECUTOR: Execution of approved Actions (§4.5).
        PROVIDER: Model text, Proposals, Hypotheses (§4.6).
        LOCAL_MODEL: A model on the Operator's machine (§4.7).
        COMMUNITY_SKILLS: Manifest, text, code (§4.8).
        MACHINE: Command output, logs, service state (§4.9).
        FILESYSTEM: File contents, config files, metadata (§4.10).
        EXTERNAL_NETWORK: Fetched docs, packages, remote content
            (§4.11).
        EXTERNAL_DOCUMENTATION: Man pages, distro docs, wikis (§4.12).
    """

    OPERATOR = "operator"
    CORE = "core"
    DIAGNOSTICS = "diagnostics"
    POLICY_ENGINE = "policy-engine"
    ACTION_EXECUTOR = "action-executor"
    PROVIDER = "provider"
    LOCAL_MODEL = "local-model"
    COMMUNITY_SKILLS = "community-skills"
    MACHINE = "machine"
    FILESYSTEM = "filesystem"
    EXTERNAL_NETWORK = "external-network"
    EXTERNAL_DOCUMENTATION = "external-documentation"


class TrustCategory(Enum):
    """The information categories RFC-0007 owns outright (RFC-0007 §6).

    The nine §6.1–§6.9 categories whose semantics this layer owns
    (DN-36), in the table's order. Each carries its §6 default class in
    CATEGORY_DEFAULTS and the §4 domains that originate it in
    CATEGORY_ORIGINS. The categories whose mechanics belong to later
    RFCs — Secrets (§6.10 → RFC-0009), Skill Manifest (§6.11 → RFC-0011),
    Skill Code (§6.12 → RFC-0011) — are deliberately not named here
    (one owner per name, RFC-0004 §3; DN-36).

    Members:
        OBSERVATION: Raw Collector output with provenance (§6.1).
        FACT: A normalized claim about the Machine, never LLM-authored
            (§6.2).
        EVIDENCE: Facts and permitted Observations relevant to the Goal
            (§6.3).
        HYPOTHESIS: A candidate explanation to be tested (§6.4).
        PROVIDER_OUTPUT: Everything the LLM returns (§6.5).
        USER_INPUT: Goal, Symptom, replies, pasted content (§6.6).
        CONFIGURATION: Machine config files and settings (§6.7).
        LOGS: Machine log streams (§6.8).
        METADATA: Package/service metadata, timestamps, sizes (§6.9).
    """

    OBSERVATION = "observation"
    FACT = "fact"
    EVIDENCE = "evidence"
    HYPOTHESIS = "hypothesis"
    PROVIDER_OUTPUT = "provider-output"
    USER_INPUT = "user-input"
    CONFIGURATION = "configuration"
    LOGS = "logs"
    METADATA = "metadata"


class ProvenanceState(Enum):
    """Whether a datum's provenance can be established (RFC-0007 §9.6).

    Members:
        ESTABLISHED: The datum's origin is established; its class comes
            from its category default (§6).
        LOST: Provenance is lost; the datum is demoted per §6/§9.6 and
            DN-39 — Hostile for Observation, Untrusted otherwise.
    """

    ESTABLISHED = "established"
    LOST = "lost"


TRUST_DOMAIN_POSTURES: Mapping[TrustDomain, str] = MappingProxyType(
    # The §4 "Default posture" column, transcribed exactly. Data only:
    # postures are descriptive metadata; the concrete class a datum is
    # held at comes from its category default (CATEGORY_DEFAULTS).
    {
        TrustDomain.OPERATOR: "Trusted for intent; untrusted as literal text",
        TrustDomain.CORE: "Trusted within scope (RFC-0001 §7)",
        TrustDomain.DIAGNOSTICS: (
            "Trusted for its output contract; untrusted in its raw reading"
        ),
        TrustDomain.POLICY_ENGINE: "Trusted within scope",
        TrustDomain.ACTION_EXECUTOR: "Trusted within scope",
        TrustDomain.PROVIDER: "Untrusted (RFC-0001 §7)",
        TrustDomain.LOCAL_MODEL: "Untrusted, same as any Provider",
        TrustDomain.COMMUNITY_SKILLS: "Untrusted by default",
        TrustDomain.MACHINE: "Untrusted",
        TrustDomain.FILESYSTEM: "Untrusted",
        TrustDomain.EXTERNAL_NETWORK: "Untrusted",
        TrustDomain.EXTERNAL_DOCUMENTATION: (
            "Untrusted as text; consulted as information"
        ),
    }
)

CATEGORY_DEFAULTS: Mapping[TrustCategory, TrustClass] = MappingProxyType(
    # The §6 "Default" column. EVIDENCE's default is the §5.1 meet
    # identity — the class of an empty composite; any admitted member
    # lowers the set (T8, §7), so a composite is never above its
    # least-trusted member (§6.3). USER_INPUT's default is the *literal
    # text* class: the words remain contained text while the intent is
    # the Operator's authority, RFC-0004's (§4.1, §6.6).
    {
        TrustCategory.OBSERVATION: TrustClass.UNTRUSTED,
        TrustCategory.FACT: TrustClass.TRUSTED,
        TrustCategory.EVIDENCE: TrustClass.TRUSTED,
        TrustCategory.HYPOTHESIS: TrustClass.UNTRUSTED,
        TrustCategory.PROVIDER_OUTPUT: TrustClass.UNTRUSTED,
        TrustCategory.USER_INPUT: TrustClass.UNTRUSTED,
        TrustCategory.CONFIGURATION: TrustClass.UNTRUSTED,
        TrustCategory.LOGS: TrustClass.UNTRUSTED,
        TrustCategory.METADATA: TrustClass.UNTRUSTED,
    }
)

PROVENANCE_LOSS_DEMOTION: Mapping[TrustCategory, TrustClass] = MappingProxyType(
    # The §9.6 demotion target on loss of provenance, per category, as
    # ratified by DN-39 path (3): provenance loss the layer must treat
    # as suspicious → Hostile, otherwise → Untrusted. RFC-0007 §6.1
    # makes Observation's loss explicitly suspicious (→ Hostile); the
    # remaining categories demote to Untrusted (DN-39; §6.2 Fact's
    # "Conditional/Untrusted" range).
    {
        TrustCategory.OBSERVATION: TrustClass.HOSTILE,
        TrustCategory.FACT: TrustClass.UNTRUSTED,
        TrustCategory.EVIDENCE: TrustClass.UNTRUSTED,
        TrustCategory.HYPOTHESIS: TrustClass.UNTRUSTED,
        TrustCategory.PROVIDER_OUTPUT: TrustClass.UNTRUSTED,
        TrustCategory.USER_INPUT: TrustClass.UNTRUSTED,
        TrustCategory.CONFIGURATION: TrustClass.UNTRUSTED,
        TrustCategory.LOGS: TrustClass.UNTRUSTED,
        TrustCategory.METADATA: TrustClass.UNTRUSTED,
    }
)

CATEGORY_ORIGINS: Mapping[TrustCategory, tuple[TrustDomain, ...]] = MappingProxyType(
    # The §4 trust domains that originate each in-scope category,
    # transcribed from the §4/§6 tables. Vocabulary data only: the
    # mapping is carried for consumers and tests; classify() does not
    # reject on mismatch (the origin is a required datum field, DN-37).
    {
        TrustCategory.OBSERVATION: (TrustDomain.DIAGNOSTICS,),
        TrustCategory.FACT: (TrustDomain.CORE,),
        TrustCategory.EVIDENCE: (TrustDomain.CORE,),
        TrustCategory.HYPOTHESIS: (TrustDomain.PROVIDER,),
        TrustCategory.PROVIDER_OUTPUT: (
            TrustDomain.PROVIDER,
            TrustDomain.LOCAL_MODEL,
        ),
        TrustCategory.USER_INPUT: (TrustDomain.OPERATOR,),
        TrustCategory.CONFIGURATION: (
            TrustDomain.FILESYSTEM,
            TrustDomain.MACHINE,
        ),
        TrustCategory.LOGS: (TrustDomain.MACHINE,),
        TrustCategory.METADATA: (
            TrustDomain.MACHINE,
            TrustDomain.FILESYSTEM,
            TrustDomain.EXTERNAL_NETWORK,
        ),
    }
)


@dataclass(frozen=True, slots=True)
class Datum:
    """The internal abstract datum classify() operates on (DN-37).

    Not a ``schema.Fact`` and not a bare string: category, content,
    provenance state, and origin domain. The origin domain is a required
    input — every datum originates in exactly one domain (RFC-0007 §4).
    Frozen and slot-based: immutable, in-memory only (DN-1, DN-37).

    Attributes:
        category: The datum's information category (§6); it determines
            the default class (DN-37).
        content: The datum's text content, carried as-is; parseability
            is RFC-0012's detection stance, not this layer's (§16.6).
        provenance: Whether provenance can be established (§9.6).
        origin: The single trust domain the datum originates in (§4).
    """

    category: TrustCategory
    content: str
    provenance: ProvenanceState
    origin: TrustDomain


@dataclass(frozen=True, slots=True)
class Classification:
    """The deterministic result of classifying a datum.

    The trust class plus the provenance the label travels with (T8:
    "the label travels with the text"). Frozen and slot-based: the
    record is immutable and in-memory only.

    Attributes:
        trust_class: The class the datum is held at.
        category: The datum's category, kept with the label.
        origin: The datum's origin domain, kept with the label.
        provenance: The provenance state the classification was made
            under (§9.6).
        reason: Why the datum is held at this class — the category
            default (§6) or the provenance-loss demotion (§9.6, DN-39).
    """

    trust_class: TrustClass
    category: TrustCategory
    origin: TrustDomain
    provenance: ProvenanceState
    reason: str


@dataclass(frozen=True, slots=True)
class Demotion:
    """The result of a downgrade: the demoted class and its reason.

    Reason-preserving (§9): the reason a datum was downgraded stays
    attached to the result, so it remains visible to the Audit
    (RFC-0002 invariant 13).

    Attributes:
        trust_class: The demoted class.
        reason: The reason the datum was downgraded, unchanged.
    """

    trust_class: TrustClass
    reason: str


def meet(a: TrustClass, b: TrustClass) -> TrustClass:
    """The meet (∧) of two trust classes — the most restrictive (§5.1).

    A composite takes the most restrictive class of its parts
    (Untrusted + Trusted = Untrusted; Hostile + anything = Hostile),
    which is invariant T8.

    Args:
        a: A trust class.
        b: A trust class.

    Returns:
        The more restrictive of ``a`` and ``b``.
    """
    return a if a.value <= b.value else b


def join(a: TrustClass, b: TrustClass) -> TrustClass:
    """The join (∨) of two trust classes — the least restrictive (§5.1).

    The least restrictive class all parts share. Join is not an upgrade
    path (§8, Q4): it never invents a class the parts do not already
    hold, and it grants no trust — the composite rule is the meet (T8).

    Args:
        a: A trust class.
        b: A trust class.

    Returns:
        The less restrictive of ``a`` and ``b``.
    """
    return a if a.value >= b.value else b


def downgrade(trust_class: TrustClass, reason: str) -> Demotion:
    """Demote a trust class deterministically, preserving the reason (§9).

    Demotion is always permitted (§9). This is the layer's one-step
    primitive: exactly one class toward Hostile in the §5 order
    (Trusted → Conditional → Untrusted → Hostile), with Hostile as the
    floor. Monotonic: the result is never above the input. The per-cause
    targets of §9.1–§9.8 (staleness, provenance loss, sanitization
    failure) are built on this primitive in classify() and in the
    sanitization/Hostile layers; this function demotes by the single
    step the corpus always permits.

    Args:
        trust_class: The class to demote.
        reason: Why the datum is demoted; must be non-empty so no
            downgrade is silent (§9: the reason stays visible in the
            Audit).

    Returns:
        The Demotion record carrying the demoted class and the reason.

    Raises:
        ValueError: If ``reason`` is empty.
    """
    if not reason:
        raise ValueError("a downgrade must carry a non-empty reason")
    demoted = max(trust_class.value - 1, TrustClass.HOSTILE.value)
    return Demotion(trust_class=TrustClass(demoted), reason=reason)


def classify(datum: Datum) -> Classification:
    """Classify a datum deterministically (DN-37; RFC-0007 §4, §6, §9).

    Pure and deterministic (S7): the same datum always yields the same
    Classification, with no I/O, mutation, or runtime state. The
    category determines the default class (§6; DN-37); the provenance
    state decides whether that default stands. When provenance is
    established the datum is held at its category default; when
    provenance is lost the datum is demoted per §9.6 as ratified by
    DN-39 — Observation to Hostile (the layer's fail-closed path, T11,
    §15.5), every other category to Untrusted. Nothing here grants
    authority or upgrades a datum above its category default (T6;
    RFC-0004 §7).

    Args:
        datum: The internal abstract datum to classify.

    Returns:
        The Classification: the held class plus the category, origin,
        provenance state, and reason, so the label travels with the
        datum (T8).
    """
    if datum.provenance is ProvenanceState.ESTABLISHED:
        trust_class = CATEGORY_DEFAULTS[datum.category]
        reason = f"category default (RFC-0007 §6.{datum.category.name})"
    else:
        trust_class = PROVENANCE_LOSS_DEMOTION[datum.category]
        reason = "loss of provenance (RFC-0007 §9.6; DN-39)"
    return Classification(
        trust_class=trust_class,
        category=datum.category,
        origin=datum.origin,
        provenance=datum.provenance,
        reason=reason,
    )
