"""Sanctioned Action runner (RFC-0004 §4.9; RFC-0002 §2.8, §6.2; I-1, I-5,
I-11, I-13; RFC-0008 §8/§9/§10; RFC-0013 §7/§21; DN-55, DN-56, DN-57,
DN-58, DN-61).

Owner: RFC-0004 §4.9 (the sole Execute authority); RFC-0002 §2.8 (the
    Executing boundary's behavior); RFC-0002 I-1/I-11 (no execution without
    approval; tokens scoped and consumable); RFC-0008 §8/§10 (the token is
    the only permission; independent enforcement).
Responsibility: a deterministic decision boundary that runs one approved
    Action under a valid, unexpired, state-consistent token. It re-validates
    the token locally (valid / unexpired / not-consumed / Action-identity /
    session, DN-56) and consumes the machine-state + precondition
    re-validation as an explicit boundary input (DN-57), refusing on any
    uncertainty (fail closed). It derives an argv-structured descriptor from
    the sanctioned Action structure only and never a shell string (I-5,
    DN-58); executes through an injected run primitive (DN-55 — the package
    performs no I/O and no subprocess spawn); writes the execution-start
    record before the run and the end record after, through `audit` (I-13,
    RFC-0013 §7 cat. 6), and a failed pre-write blocks the run and is
    disclosed (AU8, DN-61); and reports completion for Verification, never a
    success verdict (I-2).
Forbidden responsibility: no authority creation — the runner never mints,
    grants, or infers approval; it runs only under a presented token (I-1,
    RFC-0004 A2). No verification, no policy evaluation, no classification,
    no reasoning, no provider call. No clock (time is an explicit argument),
    no randomness, no cryptography, no identifier generation — record
    identities are explicit inputs. No hidden state: everything the decision
    needs is an explicit input and every output is an immutable value.
"""

from collections.abc import Callable
from dataclasses import dataclass
from datetime import datetime
from enum import Enum

from episky.audit.records import ExecutionPhase, ExecutionRecord, RecordCategory
from episky.audit.store import AuditStore, StoreStatus
from episky.schema.action import Action

__all__ = [
    "BoundaryVerdict",
    "Refusal",
    "RefusalReason",
    "RunOutcome",
    "RunPrimitive",
    "RunResult",
    "TokenHandoff",
    "run",
]


class RefusalReason(Enum):
    """The deterministic reason a run is refused (RFC-0008 §9; RFC-0002 I-1).

    Every refusal is a disclosed, deterministic outcome — the runner never
    silently refuses and never guesses (RFC-0001 §8.12; RFC-0013 §21).

    Members:
        NOT_APPROVED: No approved Action is bound to the presented token —
            nothing to authorize (I-1, RFC-0004 A2).
        CONSUMED: The presented token is already spent; replay is refused
            (I-11, RFC-0008 §13 P7).
        INVALIDATED: The presented token was killed and never resurrected
            (I-11, RFC-0008 §13 P8).
        EXPIRED: The presented token is past its per-class lifetime (RFC-0008
            §8; §13 P8).
        ACTION_MISMATCH: The presented Action is not the approved Action
            (RFC-0008 §9).
        SNAPSHOT_MISMATCH: The boundary machine-state reference does not
            match the token's (RFC-0008 §9; RFC-0002 I-11).
        SESSION_MISMATCH: The boundary session does not match the token's
            (RFC-0008 §8).
        STATE_UNCERTAIN: The boundary state-consistency verdict is not
            certain — fail closed (RFC-0008 §9; RFC-0002 §2.8).
        STORE_DEGRADED: The audit store cannot record; the consequence it
            precedes is blocked and disclosed (AU8, RFC-0013 §21).
    """

    NOT_APPROVED = "not-approved"
    CONSUMED = "consumed"
    INVALIDATED = "invalidated"
    EXPIRED = "expired"
    ACTION_MISMATCH = "action-mismatch"
    SNAPSHOT_MISMATCH = "snapshot-mismatch"
    SESSION_MISMATCH = "session-mismatch"
    STATE_UNCERTAIN = "state-uncertain"
    STORE_DEGRADED = "store-degraded"


@dataclass(frozen=True, slots=True)
class Refusal:
    """The deterministic disclosure of a refused run (RFC-0008 §9; AU8).

    Frozen and slot-based (DN-34): an immutable, in-memory outcome value. The
    ``message`` is derived from the decision inputs only, so the same inputs
    always refuse with the same disclosure.

    Attributes:
        reason: The deterministic refusal reason.
        message: The fail-loud disclosure for the Operator (RFC-0001 §8.12;
            RFC-0013 §21).
    """

    reason: RefusalReason
    message: str


@dataclass(frozen=True, slots=True)
class RunResult:
    """The completion report handed to Verification (RFC-0001 §5; I-2).

    The runner reports what the injected primitive reported and never decides
    success — Verification is the only judge (RFC-0002 I-2; RFC-0004 §4.9).
    Frozen and slot-based (DN-34): an immutable, in-memory value.

    Attributes:
        exit_status: What the primitive reported (``0``/``1``/...), or
            ``None`` when the outcome is unknown — the primitive could not
            report (a raised or timed-out run, RFC-0002 §2.8 → Interrupted).
        output: The sanitized, bounded output lines as reported; never a
            shell string.
    """

    exit_status: int | None
    output: tuple[str, ...]


@dataclass(frozen=True, slots=True)
class RunOutcome:
    """One run decision: at most one refusal or result, plus the final store.

    ``run`` is pure, so the outcome is built entirely from its explicit
    inputs: a refusal (with the store unchanged or disclosed as Degraded) or
    a completion result with the two execution records written around the
    run (I-13). Frozen and slot-based (DN-34): an immutable, in-memory value
    with no hidden state.

    Attributes:
        refusal: The deterministic refusal, or None when the run proceeded.
        result: The completion report handed to Verification, or None when
            the run was refused.
        store: The audit store after the boundary — it carries the execution
            records in write order.
        start_record: The execution-start record, written before the run
            (I-13), when the run proceeded.
        end_record: The execution-end record, written after the run (I-13),
            when the run proceeded.
    """

    refusal: Refusal | None = None
    result: RunResult | None = None
    store: AuditStore | None = None
    start_record: ExecutionRecord | None = None
    end_record: ExecutionRecord | None = None


@dataclass(frozen=True, slots=True)
class TokenHandoff:
    """The token's public fields as a carried value (DN-56).

    The approval token crosses the boundary structurally: its public fields
    are read as a plain, schema-shaped record and re-validated locally,
    without importing ``policy`` (RFC-0008 §10 layer 3 — independent
    enforcement; blueprint §4.2 keeps the edge forbidden). ``session`` and
    ``state_snapshot`` are opaque, caller-supplied references, carried for
    the binding and compared by identity on re-validation (RFC-0008 §8;
    DN-48). ``risk_class``, ``gate``, ``issued_at``, ``elevation_bounds``,
    and ``override`` are carried, never interpreted here (elevation is
    ``guards``/``elevation``, Iteration 8 Commit C4). Frozen and slot-based
    (DN-34): an immutable, in-memory value.

    Attributes:
        action_id: The immutable identity of the approved Action, supplied
            by the caller — what the execution records carry (RFC-0013 §7
            cat. 6).
        action: The approved Action itself; None for a plan envelope, which
            this runner refuses (I-1).
        risk_class: The canonical risk-class name at mint time.
        gate: The carried gate name at mint time.
        issued_at: When the token was minted (an explicit-time input).
        expiry: The deterministic per-class expiry (RFC-0008 §8).
        session: The producing session's identity reference, compared by
            identity on re-validation.
        state_snapshot: The machine-state snapshot reference the Action was
            approved against, compared by identity (RFC-0008 §9).
        elevation_bounds: The elevation bounds declared at mint (carried,
            never interpreted here).
        override: Whether the token was minted through an override.
        consumed: Whether the token's one use has been spent (I-11).
        invalidated: Whether a boundary event killed it (I-11).
    """

    action_id: str
    action: Action | None
    risk_class: str
    gate: str
    issued_at: datetime
    expiry: datetime
    session: object
    state_snapshot: object
    elevation_bounds: tuple[object, ...] = ()
    override: bool = False
    consumed: bool = False
    invalidated: bool = False


@dataclass(frozen=True, slots=True)
class BoundaryVerdict:
    """The machine-state + precondition re-validation (DN-57).

    Computed by the Awaiting Approval → Executing edge handler / runtime
    (RFC-0002 §6.2; RFC-0008 §9) and consumed as an explicit input — the
    runner never re-derives the State-Domain compare itself (RFC-0021, Draft;
    DN-48). Frozen and slot-based (DN-34).

    Attributes:
        session: The session the boundary handler re-validated against —
            compared by identity to the token's (RFC-0008 §8).
        state_snapshot: The machine-state reference the boundary handler
            re-validated against — compared by identity to the token's
            (RFC-0008 §9).
        state_consistent: Whether the boundary re-validation held. Anything
            uncertain is False, and the runner refuses (fail closed,
            RFC-0008 §9).
    """

    session: object
    state_snapshot: object
    state_consistent: bool


RunPrimitive = Callable[[Action, tuple[str, ...]], RunResult]


def run(
    action: Action,
    token: TokenHandoff,
    verdict: BoundaryVerdict,
    *,
    now: datetime,
    store: AuditStore,
    primitive: RunPrimitive,
    start_record_id: str,
    end_record_id: str,
) -> RunOutcome:
    """Run one approved Action under a valid, unexpired, state-consistent token.

    Pure and deterministic (AU5): the decision depends only on the explicit
    inputs — identical inputs yield identical refusals, records, and results.
    The boundary, in order:

    1. The store is made writable (Empty is opened); a Degraded or Recovering
       store refuses the run (AU8).
    2. The token is re-validated locally — no token-bound Action (I-1),
       consumed (replay), invalidated, expired, Action-identity mismatch,
       snapshot mismatch, session mismatch, or uncertain boundary verdict
       refuses with a disclosed, deterministic reason (I-11, RFC-0008 §9).
    3. The argv-structured descriptor is derived from the sanctioned Action
       structure only; no shell string is ever constructed (I-5, DN-58).
    4. The execution-start record is written BEFORE the run (I-13); a refused
       pre-write blocks the run and is disclosed (AU8, DN-61).
    5. The injected primitive runs the consequence (DN-55); a primitive that
       cannot report yields an outcome-unknown result (I-8).
    6. The execution-end record is written AFTER the run (I-13), and the
       completion report is returned for Verification — never a success
       verdict (I-2).

    Args:
        action: The Action to run; must be the approved, token-bound Action.
        token: The approval token's public fields as a structural handoff
            value (DN-56).
        verdict: The boundary machine-state + precondition re-validation
            (DN-57).
        now: The current time — an explicit argument, never a clock read.
        store: The audit store the boundary records into.
        primitive: The injected run primitive (DN-55); the package performs
            no I/O and no subprocess spawn.
        start_record_id: The caller-supplied identity of the execution-start
            record — the runner never generates an identifier.
        end_record_id: The caller-supplied identity of the execution-end
            record — the runner never generates an identifier.

    Returns:
        A ``RunOutcome`` carrying the deterministic refusal (with the store
        unchanged or disclosed) or the completion result with the two
        execution records written in order (I-13).
    """
    store, refusal = _writable(store)
    if refusal is not None:
        return RunOutcome(refusal=refusal, store=store)

    refusal = _validate(action, token, verdict, now=now)
    if refusal is not None:
        return RunOutcome(refusal=refusal, store=store)

    argv = _argv(action)

    start = _execution_record(start_record_id, now, token, ExecutionPhase.START, argv)
    store = store.append(start)
    if store.status is not StoreStatus.RECORDING:
        return RunOutcome(
            refusal=_refuse(
                RefusalReason.STORE_DEGRADED,
                f"the execution-start write was refused; {store.disclosure}",
            ),
            store=store,
        )

    try:
        result = primitive(action, argv)
    except Exception:
        result = RunResult(exit_status=None, output=())

    end = _execution_record(end_record_id, now, token, ExecutionPhase.END, argv)
    store = store.append(end)

    return RunOutcome(
        result=result,
        store=store,
        start_record=start,
        end_record=end,
    )


def _writable(store: AuditStore) -> tuple[AuditStore, Refusal | None]:
    """Bring the store to Recording, or refuse the run (AU8)."""
    if store.status is StoreStatus.EMPTY:
        return store.begin_recording(), None
    if store.status is StoreStatus.RECORDING:
        return store, None
    return store, _refuse(
        RefusalReason.STORE_DEGRADED,
        f"the audit store is {store.status.value}; the consequence is blocked",
    )


def _validate(
    action: Action,
    token: TokenHandoff,
    verdict: BoundaryVerdict,
    *,
    now: datetime,
) -> Refusal | None:
    """The independent local re-validation (I-1, I-11, RFC-0008 §9; DN-56)."""
    if token.action is None:
        return _refuse(
            RefusalReason.NOT_APPROVED, "no approved Action is bound to the token"
        )
    if token.consumed:
        return _refuse(
            RefusalReason.CONSUMED, "the token is already spent; replay is refused"
        )
    if token.invalidated:
        return _refuse(RefusalReason.INVALIDATED, "the token is invalidated")
    if now >= token.expiry:
        return _refuse(RefusalReason.EXPIRED, "the token is past its per-class expiry")
    if action != token.action:
        return _refuse(
            RefusalReason.ACTION_MISMATCH,
            "the presented Action is not the approved Action",
        )
    if verdict.state_snapshot is not token.state_snapshot:
        return _refuse(
            RefusalReason.SNAPSHOT_MISMATCH,
            "the boundary machine-state reference does not match the token",
        )
    if verdict.session is not token.session:
        return _refuse(
            RefusalReason.SESSION_MISMATCH,
            "the boundary session does not match the token",
        )
    if verdict.state_consistent is not True:
        return _refuse(
            RefusalReason.STATE_UNCERTAIN,
            "the boundary state-consistency verdict is not certain; fail closed",
        )
    return None


def _argv(action: Action) -> tuple[str, ...]:
    """The argv-structured descriptor from the sanctioned Action structure.

    Deterministic whitespace tokenization of the Action's own description —
    the only command-shaped field the sanctioned Action carries (RFC-0003:
    a command is one possible implementation of an Action; the Action itself
    is never a shell string). The result is a tuple of inert data tokens
    passed as structured values to the injected primitive; no shell string
    is ever constructed, so untrusted text is never interpolated into a
    command (I-5, RFC-0001 §8.4 rule 4; DN-58).
    """
    return tuple(action.description.split())


def _execution_record(
    record_id: str,
    now: datetime,
    token: TokenHandoff,
    phase: ExecutionPhase,
    argv: tuple[str, ...],
) -> ExecutionRecord:
    """The execution record at this boundary (RFC-0013 §7 cat. 6)."""
    return ExecutionRecord(
        record_id=record_id,
        recorded_at=now,
        category=RecordCategory.EXECUTION,
        phase=phase,
        action_id=token.action_id,
        argv=argv,
        machine_state=token.state_snapshot,
    )


def _refuse(reason: RefusalReason, detail: str) -> Refusal:
    """A deterministic, disclosed refusal (RFC-0008 §9; RFC-0013 §21)."""
    return Refusal(reason=reason, message=f"run refused: {reason.value}: {detail}")
