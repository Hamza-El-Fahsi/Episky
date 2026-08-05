"""Provenance and freshness computation.

Owner: RFC-0005 §5, §12.
Responsibility: provenance construction (attached at normalization,
    F10) and freshness state computation (RFC-0005 §12; F14, F15).
Forbidden responsibility: never loses provenance (F10), never treats
    unknown freshness as current (F15); no verification, no timers, no
    persistence.
"""

from datetime import datetime, timedelta

from episky.factlayer.collect import Observation
from episky.schema.fact import (
    FreshnessState,
    ObservationReference,
    Provenance,
)

__all__ = [
    "build_provenance",
    "freshness_state",
]

# Placeholder default freshness bound (RFC-0005 §12): the authoritative
# per-category bound values are RFC-0020 policy (DN-14); this constant
# is the scaffold's default, set conservatively.
DEFAULT_FRESHNESS_BOUND: timedelta = timedelta(hours=24)

# Placeholder fraction of the bound past which a Fact is "near the bound"
# and therefore Possibly stale (RFC-0005 §12). The concrete threshold is
# RFC-0020 policy.
_POSSIBLY_STALE_AFTER: float = 0.8

# The shared opaque Observation reference marker (DN-15): schema owns the
# type, factlayer instantiates it as the reference a Fact was normalized
# from. A single instance is reused (F5: identical input → identical
# Fact), as in normalize.py.
_OBSERVATION_REFERENCE = ObservationReference()


def build_provenance(observation: Observation) -> Provenance:
    """Build the Provenance of a Fact normalized from an Observation.

    RFC-0005 §5: provenance answers where (the Observation the Fact was
    normalized from), who (the exact Collector identity that ran the
    inspection), when (the collection timestamp), and how the run is
    reproduced. This is the construction; the *attachment* happens at
    normalization (F10; DN-23), never later. The observation reference is
    the Layer-0 marker (DN-15). A fresh normalization has no
    re-collection, so ``re_collected_at`` stays empty. Pure,
    deterministic, immutable.

    Args:
        observation: The Observation the Fact was normalized from.

    Returns:
        The Provenance naming that Observation, its Collector, and its
        collection timestamp.
    """
    return Provenance(
        observation=_OBSERVATION_REFERENCE,
        collector=observation.collector,
        collected_at=observation.collected_at,
    )


def freshness_state(
    collected_at: datetime,
    now: datetime,
    bound: timedelta | None = DEFAULT_FRESHNESS_BOUND,
) -> FreshnessState:
    """Compute a Fact's RFC-0005 §12 freshness state deterministically.

    A pure function of the collected timestamp, the evaluation time, and
    the freshness bound; the caller supplies ``now`` — there is no clock,
    no timer, and no runtime state. When the bound cannot be computed, or
    the timing is inconsistent (``now`` before ``collected_at``), the
    state is Unknown freshness, which is never treated as Current (F15;
    RFC-0005 §13). Past the bound the Fact is Stale and must be
    re-collected before any use as current evidence (F14); near the bound
    it is Possibly stale (RFC-0005 §12). Bound values are RFC-0020 policy
    (DN-14); ``DEFAULT_FRESHNESS_BOUND`` is the placeholder.

    Args:
        collected_at: When the underlying Observation was collected.
        now: The time at which freshness is evaluated.
        bound: The freshness bound, or None when it cannot be computed.

    Returns:
        The deterministic freshness state.
    """
    if bound is None or now < collected_at:
        return FreshnessState.UNKNOWN_FRESHNESS
    age = now - collected_at
    if age >= bound:
        return FreshnessState.STALE
    if age >= bound * _POSSIBLY_STALE_AFTER:
        return FreshnessState.POSSIBLY_STALE
    return FreshnessState.CURRENT
