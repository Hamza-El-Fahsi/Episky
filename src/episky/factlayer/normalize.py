"""Observation → Fact.

Owner: RFC-0005 §2 (F5).
Responsibility: deterministic normalization of Observations into
    canonical Facts.
Forbidden responsibility: provider-independent (F6),
    distro-independent (F7); never LLM-authored (F1).
"""

from collections.abc import Mapping

from episky.factlayer.collect import Observation
from episky.factlayer.provenance import build_provenance
from episky.schema.fact import (
    ConfidenceSource,
    Fact,
    FactStatus,
    Freshness,
    FreshnessState,
    MachineIdentity,
    Property,
    Scope,
    Subject,
    Value,
)
from episky.systemmodel.profiles import (
    DistributionFamily,
    EcosystemStatus,
    FamilyProfile,
)

__all__ = [
    "normalize",
]

# The scaffold's Canonical Definitions for the baseline Collectors
# (RFC-0005 §2 — the normalization input "a Canonical Definition"). Each
# maps a baseline Collector to the canonical claim its question answers:
# the canonical Subject and Property, in RFC-0021 §4/§6 vocabulary
# (design review §8.2). The authoritative Canonical Definition format and
# the parsing of distro-specific output are RFC-0020's (DN-1); this
# table is the scaffold realization for the ratified baseline only.
CANONICAL_DEFINITIONS: Mapping[str, tuple[str, str]] = {
    "distro": ("machine", "distribution-family"),  # RFC-0021 §2
    "kernel": ("kernel", "version"),  # RFC-0021 §4.4
    "package-state": ("package", "installed"),  # RFC-0021 §6.2
}

# The shared opaque placeholder carried by every normalized Fact: the
# Machine Identity marker (RFC-0014). It is deliberately empty, so a
# single instance is reused; sharing the marker keeps F5 determinism
# exact — identical input yields an identical Fact — without inventing
# identity semantics before its owner defines them. The Observation
# reference marker is owned by provenance.py (DN-15).
_MACHINE_IDENTITY = MachineIdentity()


def normalize(observation: Observation, family_profile: FamilyProfile) -> Fact:
    """Normalize one Observation into a canonical Fact (RFC-0005 §2; F5).

    The only gate between machine and knowledge: a pure, deterministic,
    per-Observation function that turns a single Observation into exactly
    one canonical Fact (RFC-0002 Q15; design review §6.4). Re-normalizing
    the same Observation always yields the same Fact (F5); the Family
    Profile absorbs distro variance, so the same claim normalizes the
    same way on every family (F7).

    The gate (design review §6.4): when the Observation cannot be
    normalized — a failed run, empty output, an unrecognized Collector,
    or output that is not canonical content — the result is an **Unknown**
    Fact (RFC-0005 §4; RFC-0002 §4.2 "fact unknown"; F11), never a
    guessed value and never nothing. Per DN-16 the Unknown Fact's
    ConfidenceSource names the Collector that was attempted.

    The behavioral F1 gate (DN-2): this function is the **only**
    construction path to a Fact's components — status, provenance,
    confidence, and scope all derive from the supplied Observation. The
    Fact's provenance is attached here, at normalization (F10; DN-23);
    no timing field exists (DN-21). Freshness is attached minimally as
    current — a freshly normalized claim — while freshness **bookkeeping**
    (bounds, staleness) is provenance.py's (C5, RFC-0005 §12). The
    Machine Identity is the opaque placeholder (RFC-0014). Normalization
    consults no model, performs no verification, assigns no trust, and
    attaches nothing beyond the claim, status, confidence, provenance,
    freshness, and identity (RFC-0004 §4.6; design review §6.5).

    Args:
        observation: The run to normalize; never mutated.
        family_profile: The machine's Family Profile (RFC-0021 §2.3).

    Returns:
        An immutable canonical Fact: status Observed with the canonical
        claim, or status Unknown with the attempted claim marked not
        established (DN-16).
    """
    definition = CANONICAL_DEFINITIONS.get(observation.collector.name)
    output = observation.raw_output.output.strip()
    name = observation.collector.name
    value = None
    if definition is not None and observation.exit_status == 0:
        if name == "distro" and output.upper() in {
            member.name for member in DistributionFamily
        }:
            value = output.upper()
        elif output and (
            name == "kernel"
            or (
                name == "package-state"
                and any(
                    ecosystem_status == EcosystemStatus.NATIVE
                    for ecosystem_status in family_profile.package_ecosystems.values()
                )
            )
        ):
            value = output

    if value is None:
        subject, property_name = definition or ("machine", "unknown")
        value = "unknown"
        status = FactStatus.UNKNOWN
    else:
        subject, property_name = definition
        status = FactStatus.OBSERVED

    return Fact(
        scope=Scope(
            subject=Subject(name=subject),
            property=Property(name=property_name),
            value=Value(value=value),
        ),
        status=status,
        confidence=ConfidenceSource(
            name=f"{observation.collector.name}@{observation.collector.version}"
        ),
        provenance=build_provenance(observation),
        freshness=Freshness(state=FreshnessState.CURRENT),
        machine_identity=_MACHINE_IDENTITY,
    )
