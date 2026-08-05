"""Run Collectors.

Owner: RFC-0005 §2; RFC-0004 §4.5.
Responsibility: run Collectors to produce Observations.
Forbidden responsibility: never mutates the machine — read-only
    (RFC-0003 §2.4).
"""

from dataclasses import dataclass
from datetime import datetime

from episky.schema.fact import Collector

__all__ = [
    "Observation",
    "RawOutput",
]


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
