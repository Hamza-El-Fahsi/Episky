"""Expose — the on-demand audit log and context view (RFC-0001 §5).

Owner: RFC-0001 §5 (Presentation).
Responsibility: present the audit log as §8 transcript entries (RFC-0013 §8;
    via ``audit.transcript.render``) and the context view as the §13 Provider
    View outcome (RFC-0012 §13; via ``context.provider_view.derive``) — on
    demand, read-only, secret-free (DN-100; SC3/SC4).
Forbidden responsibility: never reads the audit store or the Context directly
    — the presentation derives from an injected record sequence and an
    already-derived outcome (DN-100); never a value, never the opaque
    machine-state reference, never the Context material (RFC-0013 §10; PR14);
    never invents a view or a refusal (I-9; AU2); no I/O, no clock, no
    randomness (DN-55/DN-103).
Layer 7 (blueprint §4.1). Imports: audit, context.
"""

from collections.abc import Iterable
from dataclasses import dataclass

from episky.audit.records import AuditRecord
from episky.audit.transcript import TranscriptEntry, render
from episky.context.provider_view import (
    ProviderView,
    ProviderViewOutcome,
    ViewDisposition,
    ViewRefusal,
)

__all__ = ["PresentedLog", "PresentedView", "audit_log", "context_view"]


@dataclass(frozen=True, slots=True)
class PresentedLog:
    """The on-demand audit log: the §8 transcript entries, in record order.

    Each entry derives from its record only (RFC-0013 §8; AU2) and is
    metadata-only (SC4): never a value, never the opaque machine-state
    reference (RFC-0013 §10). Deterministic (AU5) and read-only.
    """

    entries: tuple[TranscriptEntry, ...]


@dataclass(frozen=True, slots=True)
class PresentedView:
    """The on-demand context view: the Provider View or its disclosed refusal.

    The CLI's owned presentation of the derive() outcome (RFC-0012 §13):
    the secret-free Provider View (SC3; PR14) when derived, or the honest
    disclosure of why none was derived (I-9) — never invented, never the
    Context material.
    """

    view: ProviderView | None
    disposition: ViewDisposition
    refusal: ViewRefusal | None
    reason: str


def audit_log(records: Iterable[AuditRecord]) -> PresentedLog:
    """The audit log presented from an injected record sequence.

    Each record renders into exactly one §8 transcript entry via
    ``audit.transcript.render`` (DN-100), in record order. Read-only: never
    appends; the store read is the caller's (this layer never holds a store).
    """
    return PresentedLog(tuple(render(record) for record in records))


def context_view(outcome: ProviderViewOutcome) -> PresentedView:
    """The context view presented from the injected ``derive()`` outcome.

    Carries the secret-free Provider View or the disclosed refusal exactly as
    `context` derived it (RFC-0012 §13) — the CLI never re-derives, never
    invents, and never touches the Context material (DN-100; PR14).
    """
    return PresentedView(
        view=outcome.view,
        disposition=outcome.disposition,
        refusal=outcome.refusal,
        reason=outcome.reason,
    )
