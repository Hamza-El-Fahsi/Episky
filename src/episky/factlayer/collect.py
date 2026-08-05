"""Run Collectors.

Owner: RFC-0005 §2; RFC-0004 §4.5.
Responsibility: run Collectors to produce Observations.
Forbidden responsibility: never mutates the machine — read-only
    (RFC-0003 §2.4); no mutation in any Collect (A4).
"""

from dataclasses import dataclass
from datetime import datetime

from episky.collectors.registry import CollectorSpec
from episky.schema.fact import Collector

__all__ = [
    "Observation",
    "RawOutput",
    "collect",
]

# Placeholder default bound for Collector output (DN-18): output beyond
# the bound is truncated and the Observation records the truncation. The
# authoritative bound value is RFC-0020 policy; this constant is a
# placeholder only and is not a per-Collector limit.
DEFAULT_OUTPUT_BOUND: int = 4096


@dataclass(frozen=True, slots=True)
class RawOutput:
    """The bounded raw utterance of one Collector run (RFC-0005 §2).

    The raw bytes/text the Collector's deterministic inspection actually
    emitted — still distro-specific and untrusted, before any
    normalization (RFC-0005 §2, stage 1). This type is the utterance
    only: which Collector ran, when, and the exit status belong to the
    Observation record (design review §6.1), and RFC-0005 §2 "timing"
    is not a field (DN-21).

    Bounded by the truncation mechanism (DN-18): output past the bound
    is truncated and the Observation records the truncation; the bound
    value is RFC-0020 policy and is not represented here. Frozen and
    slot-based: an utterance does not change (F8).

    Attributes:
        output: The raw text the Collector returned.
    """

    output: str


@dataclass(frozen=True, slots=True)
class Observation:
    """A timestamped, provenance-carrying record of one Collector run.

    RFC-0005 §2 (stage 2) and RFC-0003 §2.4: the Observation records one
    Collector's raw output together with which Collector ran, when, and
    the exit status — the normalized recording boundary. It is **not** a
    Fact: Observations are not Facts, and a Fact is made only by
    normalization (RFC-0004 §4.5). A failed or inconclusive run still
    produces an Observation — the record that it failed — so a failure
    never disappears (RFC-0002 §4.2).

    Provenance timing is ``collected_at``; there is no separate
    execution-duration field (DN-21). Truncation is recorded here, never
    silently dropped and never unmarked (RFC-0005 §2; DN-18); the bound
    value is RFC-0020 policy. The Observation model is
    ``factlayer``-internal (DN-15): ``schema.Provenance.observation``
    keeps the Layer-0 marker, and this type is not exposed by ``schema``.
    Frozen and slot-based: a record of a run does not change (F8).

    Attributes:
        raw_output: The bounded raw utterance the Collector returned.
        collector: The Collector identity that ran the inspection
            (RFC-0005 §5).
        collected_at: When the run was collected (RFC-0005 §5).
        exit_status: The run's exit status (RFC-0005 §2; RFC-0002 §4.2).
        truncated: Truncation marker — True when output past the bound
            was truncated (RFC-0005 §2; DN-18).
    """

    raw_output: RawOutput
    collector: Collector
    collected_at: datetime
    exit_status: int
    truncated: bool = False


def collect(
    spec: CollectorSpec,
    output: str,
    exit_status: int = 0,
    *,
    collected_at: datetime,
) -> Observation:
    """Run one Collector and record the Observation of its run (RFC-0005 §2).

    The collection stage of the Observation → Fact pipeline: from a
    CollectorSpec and the raw result its deterministic inspection actually
    emitted, build the immutable Observation record — the Collector's
    identity (RFC-0005 §5), the ``collected_at`` timestamp (DN-21), the
    exit status, and the bounded raw output with the truncation marker
    (DN-18; never silently dropped, RFC-0005 §2).

    The entry point is read-only — RFC-0004 §4.5 Observe, A4: it executes
    no system command, mutates no machine state, and persists nothing.
    The raw result is supplied to the stage; the stage only records it
    under the Collector's declared identity. A non-zero ``exit_status``
    still yields the Observation — the record that it failed — so a
    failure never disappears (RFC-0002 §4.2).

    This is the scaffold signature; the authoritative public signature is
    RFC-0020's (DN-1; blueprint §5).

    Args:
        spec: The CollectorSpec whose declared identity names the run.
        output: The raw bytes/text the Collector returned, unbounded.
        exit_status: The run's exit status (default: success).
        collected_at: When the run was collected (RFC-0005 §5).

    Returns:
        The immutable Observation of the run, with ``truncated`` set when
        ``output`` exceeded the placeholder bound.
    """
    truncated = len(output) > DEFAULT_OUTPUT_BOUND
    bounded = output[:DEFAULT_OUTPUT_BOUND] if truncated else output
    return Observation(
        raw_output=RawOutput(output=bounded),
        collector=Collector(name=spec.name, version=spec.version),
        collected_at=collected_at,
        exit_status=exit_status,
        truncated=truncated,
    )
