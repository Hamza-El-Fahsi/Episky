"""Collector contract and baseline registry.

Owner: RFC-0003 §2.4 (Collector); RFC-0005 §2, §5.
Responsibility: the Collector contract — one question, declared inputs,
    provenance behavior, declared output — and the baseline Collector
    declarations (distro, kernel, package-state), read-only.
Forbidden responsibility: never executes, never mutates the machine,
    never produces instructions (RFC-0004 A4; Inspection is always
    read-only).
"""

from collections.abc import Mapping
from dataclasses import dataclass
from types import MappingProxyType

from episky.systemmodel.profiles import (
    ECOSYSTEM_STATUS,
    FAMILY_PROFILES,
    DistributionFamily,
    PackageEcosystem,
)
from episky.systemmodel.subsystems import MachineSubsystem, StateDomain

__all__ = [
    "COLLECTOR_SPECS",
    "CollectorSpec",
]


@dataclass(frozen=True, slots=True)
class CollectorSpec:
    """The Collector contract: one question, declared inputs and provenance.

    RFC-0003 §2.4: a Collector is a deterministic, read-only inspection
    procedure that produces Observations, answers one specific question,
    and carries declared inputs and provenance behavior. This type is the
    declaration of that contract; it carries no behavior and performs no
    I/O (RFC-0003 §2.4; RFC-0005 §2; DN-1). Frozen and slot-based: a
    declaration does not change.

    ``name`` and ``version`` form the Collector identity that
    ``schema.Collector`` carries (RFC-0005 §5, "who collected it?"); the
    runtime identity is built from them at collection time (design review
    §6.1) — this module never constructs a ``schema`` type.

    ``declared_output`` names the RFC-0005 §2 **Observation** stage. The
    concrete Observation type is ``factlayer``-internal (DN-15) and a
    Layer-2 ``collectors`` module may not import it, so the field is the
    canonical stage name, not the type.

    Attributes:
        name: The Collector's identity name (RFC-0005 §5).
        version: The Collector's identity version (RFC-0005 §5).
        question: The one specific question this Collector answers;
            exactly one per Collector (RFC-0003 §2.4).
        inputs: The canonical ``schema``/``systemmodel`` vocabulary this
            Collector reads — the vocabulary its Observation material is
            expressed over (RFC-0003 §2.4; design review §6.3).
        provenance_behavior: The declared provenance behavior — which
            Family Profile / canonical definition the Collector uses, how
            the claim is canonicalized, and how the Observation is
            reproduced (RFC-0005 §5).
        declared_output: The declared output: the RFC-0005 §2 Observation
            stage name.
    """

    name: str
    version: str
    question: str
    inputs: tuple[object, ...]
    provenance_behavior: str
    declared_output: str


COLLECTOR_SPECS: Mapping[str, CollectorSpec] = MappingProxyType(
    {
        # Blueprint §8.4 baseline set, ratified DN-17: exactly three
        # Collectors — distro, kernel, package-state. Each answers one
        # question (RFC-0003 §2.4) and declares an Observation output.
        "distro": CollectorSpec(
            name="distro",
            version="1",
            question="Which distribution family is this machine?",
            inputs=(DistributionFamily, FAMILY_PROFILES),
            provenance_behavior=(
                "canonicalizes the claim over the DistributionFamily "
                "vocabulary and the Family Profile (RFC-0021 §2.2, §2.3); "
                "reproduced by re-running this Collector (RFC-0005 §5)."
            ),
            declared_output="Observation",
        ),
        "kernel": CollectorSpec(
            name="kernel",
            version="1",
            question="What is the running kernel and its parameters?",
            inputs=(MachineSubsystem.KERNEL, StateDomain.CONFIGURATION),
            provenance_behavior=(
                "states the claim over the Kernel subsystem vocabulary "
                "(RFC-0021 §4.4); kernel state is represented in the "
                "Configuration State Domain (§6.10); reproduced by "
                "re-running this Collector (RFC-0005 §5)."
            ),
            declared_output="Observation",
        ),
        "package-state": CollectorSpec(
            name="package-state",
            version="1",
            question=(
                "What is installed, at what version, in the machine's "
                "Native package ecosystems?"
            ),
            inputs=(PackageEcosystem, ECOSYSTEM_STATUS, StateDomain.PACKAGE),
            provenance_behavior=(
                "reads Package State (RFC-0021 §6.2) over the Native "
                "ecosystems only — apt/dpkg and dnf/rpm (§5.2; DN-17); "
                "the per-family native map comes from the Family Profile "
                "(§2.3); Secondary and Experimental ecosystems are out "
                "of the baseline (Unsupported, never Unavailable — F11); "
                "reproduced by re-running this Collector (RFC-0005 §5)."
            ),
            declared_output="Observation",
        ),
    }
)
