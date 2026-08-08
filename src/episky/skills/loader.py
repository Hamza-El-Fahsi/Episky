"""Skill Registry: deterministic load-and-authenticate boundary (RFC-0011 §3,
§22; RFC-0002 §4.7; RFC-0001 §11.2/§11.3/§11.5; RFC-0007 §6.11).

Owner: RFC-0011 §3 (the Skill Registry's authentication role), §22 (loading:
    read the declared surface; authenticate signature and provenance;
    validate the declaration; check Policy before activation; register with
    the Core), §19 (version and signature ride the manifest); §11 (bundled
    Collectors validated against the collectors registry, RFC-0005 §2);
    §12/§13 (declared Preconditions/Postconditions, RFC-0001 §11.3);
    RFC-0002 §4.7 (an unauthenticated Skill is never loaded, never
    substituted); RFC-0001 §11.2 (the Core enumerates what is registered),
    §11.3 (every extension declares its surface up front), §11.5 (ships
    unsafe by default — a Skill is untrusted until its declared intent is
    verified and within Policy); RFC-0008 §6 (the declared risk maps to a
    gate by class).
Responsibility: the deterministic mechanics the Skill Registry uses to turn a
    Skill's packaged content into a validated contract instance — read and
    validate the declared surface (targets, privileges, risk, capabilities,
    dependencies, or explicit precondition/postcondition and verification
    declaration), verify signature and provenance through an injected
    verifier (unauthenticated Skills are never loaded or substituted, RFC-0002
    §4.7), validate bundled Collectors against the `collectors` registry
    (RFC-0011 §11 — a Skill never inspects the machine itself), and check
    Policy before activation (RFC-0008) — with no side effects and no LLM
    judgment (RFC-0011 §22). Loading registers what the Core enumerates
    (RFC-0001 §11.2); nothing else changes. It is value-free: a loaded Skill
    carries its declared surface and nothing else; no capability implies
    permission (RFC-0011 §8), and nothing here is a Fact, an approval, or an
    execution surface (RFC-0011 §4; RFC-0005 F6).
Forbidden responsibility: never authenticates on its own (the signing
    scheme is RFC-0017/RFC-0020's, RFC-0011 §30 OQ1; the verifier is always
    injected, the DN-55 precedent of an injected primitive — no crypto, no
    key management here); never interprets the fact-model declaration (that
    is RFC-0006/RFC-0008's mechanics) or executes anything; no I/O, no
    network, no filesystem, no clock, no randomness, no serialization, no
    hidden state, no `secrets`, `audit`, `executor` (RFC-0011 §15; blueprint
    §4.2). Deterministic: the identical inputs always produce the identical
    LoadOutcome and every refusal is loud and disclosed (RFC-0011 §10).
"""

from collections.abc import Callable, Mapping
from dataclasses import dataclass
from enum import Enum, auto

from episky.collectors.registry import COLLECTOR_SPECS, CollectorSpec
from episky.policy.classify import RiskClass

__all__ = [
    "AuthenticationVerdict",
    "LoadDisposition",
    "LoadOutcome",
    "LoadRefusal",
    "PolicyVerdict",
    "Skill",
    "SkillCapability",
    "SkillDependency",
    "SkillManifest",
    "SkillStage",
    "load",
]


class SkillCapability(Enum):
    """The six declared §8 capabilities, in the table's order (RFC-0011 §8).

    A Skill's capabilities are declared at load and never widen its
    boundaries (§8). No capability implies permission: declaring one here
    grants nothing (RFC-0010 §5.4 precedent).

    Members:
        DIAGNOSTICS: Bundles Collectors producing Observations.
        EXPLANATION: Produces human-readable material.
        PROPOSAL: Produces Proposals for the gate.
        PLANNING: Produces multi-step Plans of Actions.
        VERIFICATION_APPROACH: Declares how success is checked; never
            performs it (RFC-0011 §14).
        DETERMINISTIC_OPERATION: Runs without a Provider; usable in
            degraded mode (RFC-0010 §7.3).
    """

    DIAGNOSTICS = auto()

    EXPLANATION = auto()

    PROPOSAL = auto()

    PLANNING = auto()

    VERIFICATION_APPROACH = auto()

    DETERMINISTIC_OPERATION = auto()


class SkillStage(Enum):
    """The registry stage after a successful load (RFC-0011 §22).

    Members:
        REGISTERED: Listed in the Core's enumeration of available Skills,
            awaiting the per-session lifecycle (the activation mechanics of
            §23). Being Registered grants nothing (§4, §5).
    """

    REGISTERED = "registered"


class AuthenticationVerdict(Enum):
    """The injected authentication verdict (RFC-0011 §22; RFC-0002 §4.7).

    Members:
        AUTHENTICATED: Signature and provenance were verified by the
            external verifier; the Skill may proceed to validation.
        UNAUTHENTICATED: Verification failed or was not performed; the
            Skill must not be loaded.
    """

    AUTHENTICATED = "authenticated"

    UNAUTHENTICATED = "unauthenticated"


class PolicyVerdict(Enum):
    """The injected Policy decision for the declared surface (RFC-0008).

    Members:
        PERMITTED: The declared surface is within Policy; activation is
            later Policy-gated per session (§23).
        REFUSED: Policy declines the declared surface; loading is refused.
    """

    PERMITTED = "permitted"

    REFUSED = "refused"


class LoadDisposition(Enum):
    """Whether the Skill was loaded or refused.

    Members:
        LOADED: Verified and validated; registered with the Core.
        REFUSED: The Skill was refused; nothing is sketched, nothing is
            substituted (RFC-0002 §4.7).
    """

    LOADED = "loaded"

    REFUSED = "refused"


class LoadRefusal(Enum):
    """The deterministic refusal reasons of the load boundary (fail-closed).

    Members:
        UNAUTHENTICATED: No authenticated signature/provenance; never loaded.
        MALFORMED_SURFACE: The value is not a declared SkillSurface.
        INVALID_DECLARATION: A declared element (targets, privileges, risk,
            capabilities, dependencies, Preconditions, Postconditions,
            verification approach) fails deterministic validation (RFC-0011
            §22; RFC-0001 §11.3).
        INVALID_DEPENDENCY: A dependency is unpinned or self-referential
            (RFC-0011 §9).
        UNKNOWN_COLLECTOR: A bundled Collector is not in the `collectors`
            registry (RFC-0011 §11).
        POLICY_DENIED: The injected Policy decision refused the declared
            surface (RFC-0008; §22 "check Policy before activation").
    """

    UNAUTHENTICATED = "unauthenticated"

    MALFORMED_SURFACE = "malformed-surface"

    INVALID_DECLARATION = "invalid-declaration"

    INVALID_DEPENDENCY = "invalid-dependency"

    UNKNOWN_COLLECTOR = "unknown-collector"

    POLICY_DENIED = "policy-denied"


@dataclass(frozen=True, slots=True)
class SkillDependency:
    """A declared, version-pinned dependency of a Skill (RFC-0011 §9).

    Pure declared vocabulary: what this Skill requires, declared up front,
    version-pinned (immutable, §19) and acyclic — a dependency never points
    back at the Skill itself (§9.3). Dependency *resolution* (fetching,
    satisfying versions) is the Core's obligation, not this module's.

    Attributes:
        name: The dependency's identity name.
        version: The pinned, immutable version requested (§19).
    """

    name: str
    version: str


@dataclass(frozen=True, slots=True)
class SkillManifest:
    """The declared surface value a packaged Skill provides (RFC 0011 §7).

    This is the manifest: the declared, signed intent the Skill offers
    before it can be considered (RFC-0001 §11.3). It is pure, frozen,
    slot-based declared data: nothing here trusts, executes, or instructs.
    The version and signature ride the manifest, and versions are immutable
    (§19).

    Attributes:
        name: The Skill's identity name (RFC-0003 §2.7).
        version: The immutable version of the Skill (§19).
        signature: The signature carried on the manifest. The concrete
            signing scheme is RFC-0017/RFC-0020's (§30 OQ1); the injected
            verifier checks it, never this module.
        targets: The distro families / versions the Skill is for
            (§7 responsibility "declare its surface up front"; RFC-0001
            §11.3); declared up front and validated structurally here.
            Distro vocabulary is RFC-0021's.
        privileges: The declared privileges it requires (RFC-0001 §11.3) —
            what it needs to read; a declaration, never a grant.
        risk: The declared risk class the Skill's Actions address
            (RFC-0008 §6). Barely stated = no gate decision is made here;
            per-Action classification is the gate's (RFC-0011 §24).
        capabilities: The declared §8 capability set (non-empty).
        dependencies: Declared, version-pinned dependencies (§9); acyclic.
        collectors: The bundled Collector names, validated against the
            `collectors` registry (§11); the Skill never inspects the
            machine itself.
        preconditions: The declared Preconditions, in the fact model's
            vocabulary, that must hold before the Skill's Actions may run
            (§12; RFC-0006 §4).
        postconditions: The declared expected Postconditions the Skill's
            Actions claim to produce, before execution (§13; RFC-0006 §5).
        verification: The declared verification approach — how success is
            checked; the Skill never performs it (§14; RFC-0006 §3).
    """

    name: str
    version: str
    signature: str
    targets: tuple[str, ...]
    privileges: tuple[str, ...]
    risk: RiskClass
    capabilities: frozenset[SkillCapability]
    dependencies: tuple[SkillDependency, ...]
    collectors: tuple[str, ...]
    preconditions: tuple[object, ...]
    postconditions: tuple[object, ...]
    verification: str


@dataclass(frozen=True, slots=True)
class Skill:
    """A validated, registered Skill instance (RFC-0011 §22).

    Produced only when the declared surface passed verification and
    deterministic validation and Policy stood (or was injected) as PERMITTED.
    It carries the validated manifest and the stage; it grants nothing and
    carries no execution surface (§4).

    Attributes:
        manifest: The validated declared surface.
        stage: The registration stage (REGISTERED at load).
    """

    manifest: SkillManifest
    stage: SkillStage


@dataclass(frozen=True, slots=True)
class LoadOutcome:
    """The deterministic result of a load attempt (fail-loud, RFC-0011 §10).

    Attributes:
        skill: The registered Skill when loaded; None when refused.
        disposition: LOADED or REFUSED.
        refusal: The refusal reason when refused; None when loaded.
        reason: Why the load applied or was refused.
    """

    skill: Skill | None
    disposition: LoadDisposition
    refusal: LoadRefusal | None
    reason: str


def _validate_manifest(manifest: SkillManifest) -> LoadRefusal | None:
    """Deterministic declaration checks; first refusal wins (RFC-0011 §22).

    The declared surface must be usable before the Core enumerates it:
    identity, targets, privileges, and risk are non-empty; the capability set
    is non-empty and inside the fixed §8 vocabulary; dependencies are pinned
    and acyclic (not self-referential); Preconditions, Postconditions, and
    the verification approach are declared — present, yet their content is
    never judged here. Returns the refusal reason or None when valid.
    """
    if not manifest.name or not manifest.version:
        return LoadRefusal.MALFORMED_SURFACE
    if not manifest.targets or not manifest.privileges:
        return LoadRefusal.INVALID_DECLARATION
    if not isinstance(manifest.risk, RiskClass):
        return LoadRefusal.INVALID_DECLARATION
    if not manifest.capabilities:
        return LoadRefusal.INVALID_DECLARATION
    if not manifest.capabilities <= set(SkillCapability):
        return LoadRefusal.INVALID_DECLARATION
    if not manifest.preconditions or not manifest.postconditions:
        return LoadRefusal.INVALID_DECLARATION
    if not manifest.verification.strip():
        return LoadRefusal.INVALID_DECLARATION
    return None


def _validate_dependencies(manifest: SkillManifest) -> LoadRefusal | None:
    for dep in manifest.dependencies:
        if not dep.name.strip() or not dep.version.strip():
            return LoadRefusal.INVALID_DEPENDENCY
        if dep.name == manifest.name:
            return LoadRefusal.INVALID_DEPENDENCY
    return None


def _validate_collectors(
    manifest: SkillManifest,
    collector_specs: Mapping[str, CollectorSpec],
) -> LoadRefusal | None:
    for name in manifest.collectors:
        if name not in collector_specs:
            return LoadRefusal.UNKNOWN_COLLECTOR
    return None


def load(
    manifest: object,
    verifier: Callable[[SkillManifest], AuthenticationVerdict] | None = None,
    policy: Callable[[SkillManifest], PolicyVerdict] | None = None,
    collector_specs: Mapping[str, CollectorSpec] = COLLECTOR_SPECS,
) -> LoadOutcome:
    """Load a Skill through the Registry's load-and-authenticate boundary.

    The deterministic, side-effect-free pipeline of RFC-0011 §22: read (the
    value's DN) the declared surface; authenticate signature and provenance
    through the injected ``verifier`` — an unauthenticated Skill is never
    loaded and never substituted (RFC-0002 §4.7; §5); validate the
    declaration deterministically (targets, privileges, risk, capabilities,
    dependencies, and Preconditions/Postconditions/verification) — never an
    LLM (RFC-0011 §22); check the bundled Collectors against the `collectors`
    registry (§11); check Policy before activation (RFC-0008; injected as
    ``policy``); and, only then, register with the Core (RFC-0001 §11.2).

    Both externals are injected — the verifier embodies the concrete
    RFC-0017/RFC-0020 signing scheme (DN-1, DN-55), and the Policy decision
    is the Policy engine's own (RFC-0008 §7), never judged here — so this
    module authenticates nothing by itself and decides no Policy. When
    either is absent the load fails closed: a missing verifier refuses
    UNAUTHENTICATED and a missing or refused Policy decision refuses
    POLICY_DENIED — an unverified declared intention is refused, ships
    unsafe by default (§5; RFC-0001 §11.5).

    Args:
        manifest: The declared surface value to load. Anything that is not
            a SkillManifest is refused MALFORMED_SURFACE.
        verifier: The injected signature/provenance verifier returning
            AUTHENTICATED or UNAUTHENTICATED. If omitted, the load is
            refused UNAUTHENTICATED (an identity never checked is
            unauthenticated; fail closed).
        policy: The injected Policy gate returning PERMITTED or REFUSED for
            the declared surface. If omitted, the load is refused
            POLICY_DENIED (unverified Policy, fail closed).
        collector_specs: The Collector registry (name -> spec) bundled
            names are checked against; default the baseline COLLECTOR_SPECS.

    Returns:
        A LoadOutcome: the registered Skill (LOADED) or an explicit,
        deterministic refusal with its disclosed reason.
    """
    if not isinstance(manifest, SkillManifest):
        return LoadOutcome(
            skill=None,
            disposition=LoadDisposition.REFUSED,
            refusal=LoadRefusal.MALFORMED_SURFACE,
            reason="only a Skill manifest is loaded (RFC-0011 §22)",
        )

    if not manifest.signature:
        return LoadOutcome(
            skill=None,
            disposition=LoadDisposition.REFUSED,
            refusal=LoadRefusal.UNAUTHENTICATED,
            reason="a manifest without a durable signature artifact is "
            "unauthenticated — never loaded (SK5; RFC-0002 §4.7; §19)",
        )

    if verifier is None:
        return LoadOutcome(
            skill=None,
            disposition=LoadDisposition.REFUSED,
            refusal=LoadRefusal.UNAUTHENTICATED,
            reason="an unauthenticated Skill is never loaded (RFC-0002 §4.7)",
        )

    if verifier(manifest) is not AuthenticationVerdict.AUTHENTICATED:
        return LoadOutcome(
            skill=None,
            disposition=LoadDisposition.REFUSED,
            refusal=LoadRefusal.UNAUTHENTICATED,
            reason="an unauthenticated Skill is never loaded (RFC-0002 §4.7)",
        )

    refusal = _validate_manifest(manifest)
    if refusal is None:
        refusal = _validate_dependencies(manifest)
    if refusal is None:
        refusal = _validate_collectors(manifest, collector_specs)
    if refusal is not None:
        return LoadOutcome(
            skill=None,
            disposition=LoadDisposition.REFUSED,
            refusal=refusal,
            reason="declared surface failed deterministic validation (RFC-0011 §22)",
        )

    if policy is None:
        return LoadOutcome(
            skill=None,
            disposition=LoadDisposition.REFUSED,
            refusal=LoadRefusal.POLICY_DENIED,
            reason="the declared surface is not permitted under Policy "
            "before activation (RFC-0008; RFC-0011 §22)",
        )

    if policy(manifest) is not PolicyVerdict.PERMITTED:
        return LoadOutcome(
            skill=None,
            disposition=LoadDisposition.REFUSED,
            refusal=LoadRefusal.POLICY_DENIED,
            reason="the declared surface is not permitted under Policy "
            "before activation (RFC-0008; RFC-0011 §22)",
        )

    return LoadOutcome(
        skill=Skill(manifest=manifest, stage=SkillStage.REGISTERED),
        disposition=LoadDisposition.LOADED,
        refusal=None,
        reason="verified, validated, and registered with the Core (RFC-0011 §22)",
    )
