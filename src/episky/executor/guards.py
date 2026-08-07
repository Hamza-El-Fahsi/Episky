"""Guardrails for the sanctioned run (RFC-0001 §5, §8.8, §8.12; RFC-0002
§2.8; RFC-0009 SC8/SC10; DN-59).

Owner: RFC-0001 §5 (Action Execution: "scoping, timeouts, output
    capture, no secret leakage"); RFC-0002 §2.8 (the approved action
    runs "under the executor's guardrails"); RFC-0001 §8.8 (output is
    limited — bounded, redacted, truncated rather than dumped);
    RFC-0009 SC8/SC10 (no secret in output summaries; elevation exposes
    nothing).
Responsibility: the deterministic guardrail envelope around an injected
    run primitive — scoping the run to the one approved Action, a
    deterministic timeout decision with a placeholder default bound, and
    bounded, truncated output capture redacted via ``secrets`` before it
    crosses (DN-59; RFC-0001 §8.8). Any guardrail error fails closed and
    is disclosed (RFC-0001 §8.12). The mechanism is built now; concrete
    budgets and ceilings are RFC-0020's (RFC-0002 §11 Q3; DN-59).
Forbidden responsibility: no I/O, no subprocess spawn, no shell string —
    the wrapped primitive is injected at the boundary (DN-55) and the
    package performs none itself. No clock: every time is an explicit
    argument; the timeout decision is pure over explicit inputs, and the
    wall-clock observation that produces ``now`` is the boundary's
    (RFC-0020). No secret value ever crosses: output is redacted via
    ``secrets`` and a datum that cannot be proven non-secret is withheld
    (SC14), never guessed. Never classifies by judgment: classification
    is ``secrets``' own (RFC-0009 §3 rule 5) and the guard only gates the
    crossing on it. Never grants or denies authority, never mints or
    approves (RFC-0004 §7; I-1). No hidden state: everything the
    decision needs is an explicit input and every output is an immutable
    value.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import Enum

from episky.executor.runner import RunResult, TokenHandoff
from episky.schema.action import Action
from episky.secrets.classify import (
    SecretClassification,
    SecretDatum,
    SecretOrigin,
    classify,
)
from episky.secrets.redact import RedactionStatus, redact

__all__ = [
    "DEFAULT_OUTPUT_BOUND",
    "DEFAULT_TIMEOUT_BOUND",
    "GuardedPrimitive",
    "GuardedResult",
    "GuardrailFailure",
    "GuardrailReason",
    "guard",
]

# Placeholder default bounds (DN-18 precedent; RFC-0002 §11 Q3). The
# authoritative values are RFC-0020 policy content; these constants are
# deterministic placeholders only, never per-Action ceilings.
DEFAULT_OUTPUT_BOUND: int = 4096
DEFAULT_TIMEOUT_BOUND: int = 30


class GuardrailReason(Enum):
    """The deterministic reason a guardrail refused or withheld (RFC-0001
    §8.12; DN-59).

    Every guardrail event is a disclosed, deterministic outcome — the
    guard never fails silently and never guesses (RFC-0013 §21).

    Members:
        SCOPING: The run is not within the token's named scope — nothing
            beyond the one approved Action is ever run (RFC-0004 §4.9;
            P12).
        TIMEOUT: The run's budget is exhausted — the outcome is unknown
            (RFC-0002 §2.8 → Interrupted at ``core``).
        REDACTION: A captured output line could not be proven non-secret
            and was withheld — nothing crosses (RFC-0009 SC14).
    """

    SCOPING = "scoping"
    TIMEOUT = "timeout"
    REDACTION = "redaction"


@dataclass(frozen=True, slots=True)
class GuardrailFailure:
    """The fail-loud disclosure of one guardrail event (RFC-0001 §8.12).

    Frozen and slot-based (DN-34): an immutable, in-memory value. The
    ``message`` is derived from the decision inputs only, so the same
    inputs always fail with the same disclosure.

    Attributes:
        reason: The deterministic guardrail reason.
        message: The fail-loud disclosure for the Operator (RFC-0001
            §8.12; RFC-0013 §21).
    """

    reason: GuardrailReason
    message: str


@dataclass(frozen=True, slots=True)
class GuardedResult:
    """One guarded-run outcome: the sanitized result plus disclosures.

    The guard never lies about the run (I-2): when the run proceeded,
    ``result.exit_status`` reports what the primitive reported and the
    output carries the bounded, truncated, redacted lines. When a
    blocking guardrail failed (scoping or timeout), ``result`` is the
    outcome-unknown report and nothing ran. ``failures`` is non-empty
    exactly when a guardrail failed closed and must be disclosed.
    ``truncated`` is the DN-18 marker: output past the bound was dropped,
    never silently. Frozen and slot-based (DN-34): an immutable,
    in-memory value with no hidden state.

    Attributes:
        result: The sanitized completion report; outcome-unknown
            (exit_status None, empty output) when a blocking guardrail
            failed.
        truncated: Whether output past the placeholder bound was
            truncated (RFC-0001 §8.8; DN-18) — never silently dropped.
        failures: The guardrail failures that failed closed and were
            disclosed; empty when no guardrail event occurred.
    """

    result: RunResult
    truncated: bool
    failures: tuple[GuardrailFailure, ...]


GuardedPrimitive = Callable[[Action, tuple[str, ...], datetime], GuardedResult]


def _classify_captured(line: str) -> SecretClassification:
    """Classify one captured output line as ``secrets`` would (RFC-0009
    §7 rule 3).

    Run output is captured machine output — the only honest origin for
    it is CAPTURED, classified by content under ``secrets``' mechanical,
    non-exhaustive catalogue (§3 rules 3–4). The guard never guesses a
    designation: an unclassified line fails closed to HOSTILE and is
    withheld.
    """
    return classify(SecretDatum(content=line, origin=SecretOrigin.CAPTURED))


def guard(
    primitive: Callable[[Action, tuple[str, ...]], RunResult],
    *,
    token: TokenHandoff,
    started_at: datetime,
    timeout_bound: int = DEFAULT_TIMEOUT_BOUND,
    output_bound: int = DEFAULT_OUTPUT_BOUND,
    classify_output: Callable[[str], SecretClassification] = _classify_captured,
    trust_class: object,
) -> GuardedPrimitive:
    """Wrap an injected run primitive in the guardrail envelope (DN-59).

    Returns a deterministic ``GuardedPrimitive`` — a pure decision
    boundary over explicit inputs. On each invocation ``(action, argv,
    now)`` it decides, in order:

    1. **Scoping.** ``action`` must be the token's one approved Action;
       anything else fails closed (SCOPING) and nothing runs (RFC-0004
       §4.9; P12).
    2. **Timeout.** ``now`` at/after the deadline (``started_at`` plus
       the placeholder ``timeout_bound``) is a timed-out run — the
       outcome is unknown and nothing runs (RFC-0002 §2.8 → Interrupted
       at ``core``). The wall-clock observation producing ``now`` is the
       boundary's (RFC-0020); the decision here is deterministic.
    3. **Run.** The wrapped primitive runs (DN-55); a primitive that
       cannot report yields the outcome-unknown report (I-8).
    4. **Capture and redact.** Output is truncated to the placeholder
       ``output_bound`` lines with the DN-18 marker (never silently
       dropped), each kept line is classified via ``secrets`` and
       redacted via ``secrets.redact`` (SC8); a line that cannot be
       proven non-secret is withheld and disclosed (SC14; RFC-0001
       §8.12).

    ``started_at`` and ``now`` are explicit time inputs — the package
    reads no clock. ``trust_class`` is the datum's current trust class
    (the boundary's ``TrustClass``), carried through the crossing
    unchanged (S1, T9) and never interpreted here. Concrete budgets and
    ceilings are RFC-0020's (RFC-0002 §11 Q3; DN-59).

    Args:
        primitive: The injected run primitive (DN-55); the package
            performs no I/O and no subprocess spawn.
        token: The approval token's public fields, carrying the one
            approved Action the run is scoped to (RFC-0008 §8).
        started_at: When the run was budgeted to start — an explicit
            time input, never a clock read.
        timeout_bound: The placeholder default time bound, in seconds
            (DN-18 precedent); the authoritative value is RFC-0020's.
        output_bound: The placeholder default output ceiling, in lines
            (RFC-0001 §8.8; DN-18); the authoritative value is
            RFC-0020's.
        classify_output: The output classification provider; defaults to
            ``secrets``' CAPTURED-origin classification (RFC-0009 §7
            rule 3). The guard never classifies by judgment.
        trust_class: The boundary's ``TrustClass`` for the captured
            output, carried through a crossing unchanged (S1, T9).

    Returns:
        A ``GuardedPrimitive`` yielding the sanitized ``GuardedResult``
        for each ``(action, argv, now)`` invocation.

    Raises:
        ValueError: If ``timeout_bound`` or ``output_bound`` is not
            positive.
    """
    if timeout_bound <= 0:
        raise ValueError("timeout_bound must be positive (RFC-0001 §8.12)")
    if output_bound <= 0:
        raise ValueError("output_bound must be positive (RFC-0001 §8.12)")

    deadline = started_at + timedelta(seconds=timeout_bound)

    def guarded(action: Action, argv: tuple[str, ...], now: datetime) -> GuardedResult:
        if action is not token.action:
            return GuardedResult(
                result=RunResult(exit_status=None, output=()),
                truncated=False,
                failures=(
                    GuardrailFailure(
                        GuardrailReason.SCOPING,
                        "the run is not within the token's named scope; "
                        "nothing beyond the one approved Action is run (RFC-0004 §4.9)",
                    ),
                ),
            )
        if now >= deadline:
            return GuardedResult(
                result=RunResult(exit_status=None, output=()),
                truncated=False,
                failures=(
                    GuardrailFailure(
                        GuardrailReason.TIMEOUT,
                        "the run's deterministic time bound is exhausted; "
                        "outcome unknown (RFC-0002 §2.8 → Interrupted)",
                    ),
                ),
            )
        try:
            result = primitive(action, argv)
        except Exception:
            result = RunResult(exit_status=None, output=())
        truncated, kept = _capture(result.output, output_bound)
        lines, failures = _sanitize(kept, classify_output, trust_class)
        return GuardedResult(
            result=RunResult(exit_status=result.exit_status, output=lines),
            truncated=truncated,
            failures=failures,
        )

    return guarded


def _capture(
    output: tuple[str, ...], output_bound: int
) -> tuple[bool, tuple[str, ...]]:
    """Bound output capture: truncate rather than dump (RFC-0001 §8.8).

    The DN-18 marker: ``truncated`` is True exactly when output past the
    placeholder bound was dropped — never silently, never unmarked.
    """
    if len(output) <= output_bound:
        return False, output
    return True, output[:output_bound]


def _sanitize(
    lines: tuple[str, ...],
    classify_output: Callable[[str], SecretClassification],
    trust_class: object,
) -> tuple[tuple[str, ...], tuple[GuardrailFailure, ...]]:
    """Redact each captured line via ``secrets`` (SC8/SC10; DN-59).

    Each line is classified and redacted through ``secrets.redact``; a
    redaction that cannot establish the no-secret property is withheld
    and disclosed (SC14), never guessed. The crossing lines are the
    contained, quoted forms ``secrets`` produced.
    """
    kept: list[str] = []
    failures: list[GuardrailFailure] = []
    for index, line in enumerate(lines):
        redaction = redact(line, classify_output(line), trust_class)
        if redaction.status is RedactionStatus.OK:
            kept.append(redaction.text)
        else:
            failures.append(
                GuardrailFailure(
                    GuardrailReason.REDACTION,
                    f"output line {index} withheld: {redaction.reason}",
                )
            )
    return tuple(kept), tuple(failures)
