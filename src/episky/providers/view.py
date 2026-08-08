"""Provider View consumer, capability model, lifecycle, and failure
classification (RFC-0010 §3, §5, §6, §7, §8; RFC-0002 §4.3; RFC-0012 §13,
§27; RFC-0007 T3; RFC-0009 SC3; RFC-0005 F6).

Owner: RFC-0010 §3 (Provider Inputs), §5 (Capability Model), §6 (Capability
    Negotiation), §7 (Provider Lifecycle), §8 (Failure Model); RFC-0002 §4.3
    (provider events).
Responsibility: the deterministic mechanics the Core uses to drive a
    provider — consume exactly the Provider View built by `context`
    (Iteration 9) and nothing else (PR14; RFC-0002 invariant 4; RFC-0012
    §13/§27); the §5 capability vocabulary and declaration (no capability
    implies permission, §5.4, PR12); the deterministic §6 negotiation
    adaptation; the §7 lifecycle mechanics (registration, activation,
    removal), each transition deterministic and fail-closed; and the §8
    failure classification into the RFC-0002 §4.3 event vocabulary so a
    failure degrades, never crashes (PR11) and degradation is honest
    (PR16, no recommendation fabricated). Validation is deterministic
    (RFC-0007 S7).
Forbidden responsibility: never creates or stores Facts (F6; RFC-0010 PR3);
    never executes, approves, or verifies (RFC-0010 §2; PR1/PR2/PR6); no
    vendor selection, profiles, or fallback chains — those are RFC-0016's
    (RFC-0010 §15 OQ1); no consultation wiring — that is `core`'s (RFC-0002
    §5/§6); never holds a secret value (SC3; PR8); imports no vendor (no
    HTTP/REST/SDK; RFC-0010 §0); no I/O, no network call, no subprocess, no
    clock read, no randomness, no serialization, no hidden state.
"""

from dataclasses import dataclass
from enum import Enum, auto

from episky.context.provider_view import ProviderView

__all__ = [
    "CapabilityDeclaration",
    "Consumption",
    "ConsumptionDisposition",
    "ConsumptionRefusal",
    "LifecycleDisposition",
    "LifecycleOutcome",
    "LifecycleRefusal",
    "Negotiation",
    "ProviderCapability",
    "ProviderEvent",
    "ProviderFailure",
    "ProviderLifecycle",
    "ProviderStage",
    "RequestKind",
    "activate",
    "classify",
    "consume",
    "declare",
    "negotiate",
    "register",
    "remove",
]


class ProviderCapability(Enum):
    """The eight declared §5 capabilities, in the table's order.

    Capabilities are declared at registration (RFC-0010 §5) — never
    assumed — and validated against observed behaviour. No capability
    implies permission (§5.4; PR12): a declaration grants nothing here.

    Members:
        REASONING: Reason over the Provider View into Proposals and
            Explanations — the minimum every provider must have.
        TOOL_PLANNING: Produce multi-step Plans of proposed Actions.
        STREAMING: Deliver reasoning incrementally.
        STRUCTURED_RESPONSES: Return the finite §4 output forms reliably.
        LONG_CONTEXT: Reason over a large Provider View.
        IMAGE_UNDERSTANDING: Reason over image evidence.
        OFFLINE: Runs without network access.
        LOCAL: Runs on the Operator's machine (RFC-0007 §4.7).
    """

    REASONING = auto()
    TOOL_PLANNING = auto()
    STREAMING = auto()
    STRUCTURED_RESPONSES = auto()
    LONG_CONTEXT = auto()
    IMAGE_UNDERSTANDING = auto()
    OFFLINE = auto()
    LOCAL = auto()


class ProviderStage(Enum):
    """The §7 lifecycle stages this package owns (RFC-0010 §7).

    Registration, activation, and removal are the mechanics built here
    (DN-77, Q3); §7 Selection is RFC-0016's, the Use/consultation wiring
    and the failure reaction are `core`'s (RFC-0002 §5/§6/§10), and a
    provider cannot insert itself into its lifecycle (RFC-0010 §7 rule 4).

    Members:
        REGISTERED: Declared to the Core with its capabilities — the
            declaration is not trusted until validated (§7 rule 1).
        ACTIVATED: Initialized and verified usable (§7).
        REMOVED: Withdrawn; nothing depends on a specific provider and
            no residue is left (RFC-0010 §7 rule 5).
    """

    REGISTERED = auto()
    ACTIVATED = auto()
    REMOVED = auto()


class ProviderFailure(Enum):
    """The seven bounded §8 failure modes, in the table's order (RFC-0010 §8).

    Members:
        TIMEOUT: No reply within the phase budget.
        UNAVAILABLE: The provider cannot be reached at all.
        MALFORMED_OUTPUT: Not a valid contract output (§4).
        INCOMPLETE_PROPOSAL: Lacks its expected effect (§4 rule 2).
        UNSUPPORTED_CAPABILITY: Claims a capability it cannot actually use.
        HALLUCINATION: Asserts something that contradicts known facts.
        REFUSAL: States it will not do the asked-for thing.
    """

    TIMEOUT = auto()
    UNAVAILABLE = auto()
    MALFORMED_OUTPUT = auto()
    INCOMPLETE_PROPOSAL = auto()
    UNSUPPORTED_CAPABILITY = auto()
    HALLUCINATION = auto()
    REFUSAL = auto()


class ProviderEvent(Enum):
    """The RFC-0002 §4.3 provider-event vocabulary.

    Members:
        PROVIDER_RESPONSE: A valid, parseable reply was returned and
            consumed in the cognitive phase.
        PROVIDER_REFUSAL: The provider declined or produced unusable
            output (RFC-0002 §4.3).
        PROVIDER_UNAVAILABLE: A connection or service failure.
        PROVIDER_TIMEOUT: No reply within the phase bound.
        PROVIDER_FALLBACK_OK: A fallback provider is usable.
        PROVIDER_FALLBACK_FAILED: No provider is usable (`core` degrades).
    """

    PROVIDER_RESPONSE = auto()
    PROVIDER_REFUSAL = auto()
    PROVIDER_UNAVAILABLE = auto()
    PROVIDER_TIMEOUT = auto()
    PROVIDER_FALLBACK_OK = auto()
    PROVIDER_FALLBACK_FAILED = auto()


class ConsumptionDisposition(Enum):
    """Whether an input was consumed as the Provider View or refused.

    Members:
        CONSUMED: The value was the Provider View type — the only
            accepted input (PR14).
        REFUSED: Nothing was made usable; nothing else is a channel.
    """

    CONSUMED = auto()
    REFUSED = auto()


class ConsumptionRefusal(Enum):
    """Why a value was not admitted as a Provider View (fail-closed, loud).

    Members:
        NOT_A_PROVIDER_VIEW: The value is not the exact `ProviderView`
            type built by `context` — a presumed Audit record, a
            secret-shaped value, raw output, or provider identity is
            none of a channel (PR14; SC3).
    """

    NOT_A_PROVIDER_VIEW = auto()


class LifecycleDisposition(Enum):
    """Whether a lifecycle transition happened or was refused.

    Members:
        TRANSITIONED: The deterministic transition applied.
        REFUSED: The transition is illegal or unusable; no state change.
    """

    TRANSITIONED = auto()
    REFUSED = auto()


class LifecycleRefusal(Enum):
    """The deterministic lifecycle refusal reasons (fail-close, loud).

    Members:
        ILLEGAL_TRANSITION: The transition is not a legal §7 move.
        MALFORMED_DECLARATION: The declared set is empty — a provider
            with no capabilities is unusable from the start.
        UNUSABLE: The declared capabilities cannot be used — the
            minimum Reasoning capability is absent (RFC-0010 §5).
    """

    ILLEGAL_TRANSITION = auto()
    MALFORMED_DECLARATION = auto()
    UNUSABLE = auto()


class RequestKind(Enum):
    """The deterministic §6 request vocabulary for one provider.

    Members:
        PROPOSAL: Ask for a single Proposal — the simplified request for
            a provider without Tool Planning (the Core composes the plan
            itself; RFC-0010 §6).
        PLAN: Ask for a plan with expected effects directly — a provider
            that declared Tool Planning and Structured Responses
            (RFC-0010 §6).
    """

    PROPOSAL = auto()
    PLAN = auto()


@dataclass(frozen=True, slots=True)
class CapabilityDeclaration:
    """The §5 declared capabilities of a provider.

    A frozen, slot-based record of the declaration at registration. It
    is a pure value: the declaration grants nothing (RFC-0010 §5.4;
    PR12) and is only *validated* later against observed behaviour — a
    declared capability that the provider demonstrably lacks is revoked
    (§7 rule 1; §8, unsupported capability).
    """

    capabilities: frozenset[ProviderCapability]


@dataclass(frozen=True, slots=True)
class ProviderLifecycle:
    """The immutable lifecycle state of one registered provider (§7).

    Frozen and slot-based: no hidden mutable state; a transition returns
    a new ProviderLifecycle. The declaration is the pure §5 vocabulary
    carried through the stages; the stage is where in §7 the provider is.
    It grants nothing at any stage (RFC-0010 §5.4).

    Attributes:
        stage: The current stage (REGISTERED/ACTIVATED/REMOVED).
        declaration: The declared capability vocabulary.
    """

    stage: ProviderStage
    declaration: CapabilityDeclaration


@dataclass(frozen=True, slots=True)
class Consumption:
    """The deterministic result of a provider-boundary admission (PR14).

    Attributes:
        disposition: CONSUMED when exactly the Provider View type was
            admitted, else REFUSED.
        refusal: The deterministic refusal reason, None when consumed.
        reason: Why the value was consumed or refused (fail-loud).
    """

    disposition: ConsumptionDisposition
    refusal: ConsumptionRefusal | None
    reason: str


@dataclass(frozen=True, slots=True)
class LifecycleOutcome:
    """The deterministic result of a lifecycle transition (fail-loud).

    Attributes:
        state: The state after the transition, or None when refused.
        disposition: TRANSITIONED or REFUSED.
        refusal: The deterministic refusal reason, None when transitioned.
        reason: Why the transition applied or was refused.
    """

    state: ProviderLifecycle | None
    disposition: LifecycleDisposition
    refusal: LifecycleRefusal | None
    reason: str


@dataclass(frozen=True, slots=True)
class Negotiation:
    """The deterministic §6 capability adaptation for one provider.

    The adaptation keys off the declared capabilities, never off the
    vendor (RFC-0010 §6). It produces the *kind of request* the Core
    composes with the provider — PROPOSAL or PLAN — plus whether
    structured output is expected in return. The use of the Negotiation
    (the actual request composition and the consultation) is `core`'s
    (RFC-0002 §6; DN-79).

    Attributes:
        request_kind: PROPOSAL or PLAN as derived deterministically.
        expects_structured: Whether a structured §4 reply form is
            expected in return (§6, Structured Responses).
    """

    request_kind: RequestKind
    expects_structured: bool


def consume(value: object) -> Consumption:
    """Consume the provider boundary: exactly the Provider View (PR14).

    The only thing a provider may ever receive is the ProviderView built
    by `context` (RFC-0010 §3; RFC-0002 invariant 4; RFC-0012 §13, §27).
    Any value that is not exactly that type — an Audit record, a
    secret-shaped value, raw output, or a provider identity — is refused
    because none of it may cross (RFC-0010 §3 elements 1–5; SC3). The
    actual provider request (who is called and when) is `core`'s
    (RFC-0002 §5).

    Args:
        value: The object offered to a provider.

    Returns:
        The Consumption: CONSUMED when the value is the Provider View
        type, or the explicit refusal disclosing why nothing else can
        cross the boundary.
    """
    if isinstance(value, ProviderView):
        return Consumption(
            disposition=ConsumptionDisposition.CONSUMED,
            refusal=None,
            reason="exactly the Provider View type (PR14)",
        )
    return Consumption(
        disposition=ConsumptionDisposition.REFUSED,
        refusal=ConsumptionRefusal.NOT_A_PROVIDER_VIEW,
        reason="only the Provider View crosses the provider boundary (PR14)",
    )


def declare(capabilities: frozenset[ProviderCapability]) -> CapabilityDeclaration:
    """Build a §5 capability declaration value.

    A declaration is pure vocabulary — the eight §5 capabilities are
    declared by the provider, and holding them grants nothing (RFC-0010
    §5.4; PR12). An empty declaration is returned as-is here (a pure
    value); whether it is usable is decided at registration (`register`)
    and activation (`activate`).

    Args:
        capabilities: The declared capability set.

    Returns:
        A frozen CapabilityDeclaration carrying exactly those members.
    """
    return CapabilityDeclaration(capabilities=frozenset(capabilities))


def register(capabilities: frozenset[ProviderCapability]) -> LifecycleOutcome:
    """Register a provider with its declared capabilities (§7).

    Registration stores the declaration as a pure value; nothing in it
    is trusted until validated (§7 rule 1: "the declaration is stored
    as facts; nothing is trusted from it until validated"). An empty
    declaration is refused with MALFORMED_DECLARATION because a provider
    with no declared capabilities is unusable from the start.

    Args:
        capabilities: The capability set the provider declares.

    Returns:
        The LifecycleOutcome: a ProviderLifecycle in the REGISTERED
        stage carrying the declaration, or the explicit refusal.
    """
    if not capabilities:
        return LifecycleOutcome(
            state=None,
            disposition=LifecycleDisposition.REFUSED,
            refusal=LifecycleRefusal.MALFORMED_DECLARATION,
            reason="a declaration needs at least the minimum capabilities "
            "(RFC-0010 §5)",
        )
    return LifecycleOutcome(
        state=ProviderLifecycle(
            stage=ProviderStage.REGISTERED,
            declaration=declare(capabilities),
        ),
        disposition=LifecycleDisposition.TRANSITIONED,
        refusal=None,
        reason="registered with the declared §5 capabilities",
    )


def activate(state: ProviderLifecycle | None) -> LifecycleOutcome:
    """Activate a registered provider after a deterministic usable-check.

    Activation is the §7 "initialized and verified usable" mechanics.
    The usable-check is structural and deterministic: a provider whose
    declaration lacks the minimum Reasoning capability (§5) cannot be
    verified usable, and a provider that is not REGISTERED cannot be
    activated. A refused activation is a failure, never a crash
    (RFC-0010 §8; PR11): the outcome is a refusal, not an exception.

    Args:
        state: The provider to activate (None is refused).

    Returns:
        The LifecycleOutcome: the ACTIVATED state, or the refusal.
    """
    if state is None or state.stage is not ProviderStage.REGISTERED:
        return LifecycleOutcome(
            state=state,
            disposition=LifecycleDisposition.REFUSED,
            refusal=LifecycleRefusal.ILLEGAL_TRANSITION,
            reason="activation requires a REGISTERED provider (RFC-0010 §7)",
        )
    if ProviderCapability.REASONING not in state.declaration.capabilities:
        return LifecycleOutcome(
            state=state,
            disposition=LifecycleDisposition.REFUSED,
            refusal=LifecycleRefusal.UNUSABLE,
            reason="a provider without the minimum Reasoning capability "
            "cannot be activated (RFC-0010 §5)",
        )
    return LifecycleOutcome(
        state=ProviderLifecycle(
            stage=ProviderStage.ACTIVATED,
            declaration=state.declaration,
        ),
        disposition=LifecycleDisposition.TRANSITIONED,
        refusal=None,
        reason="initialized and verified usable (RFC-0010 §7)",
    )


def remove(state: ProviderLifecycle | None) -> LifecycleOutcome:
    """Remove a provider; the removal leaves no residue (§7 rule 5).

    Removal is safe regardless of the stage — nothing outside the
    dedicated state depends on a specific provider (RFC-0010 §12;
    RFC-0001 §11.4). An already-removed provider refuses (fail-close),
    and the REMOVED state grants nothing; it is the end of the lifecycle.

    Args:
        state: The provider to remove, or None when none is held.

    Returns:
        The LifecycleOutcome: the REMOVED state, or the refusal when
        the transition is illegal.
    """
    if state is None or state.stage is ProviderStage.REMOVED:
        return LifecycleOutcome(
            state=state,
            disposition=LifecycleDisposition.REFUSED,
            refusal=LifecycleRefusal.ILLEGAL_TRANSITION,
            reason="only a registered or activated provider is removed "
            "(RFC-0010 §7 rule 5)",
        )
    return LifecycleOutcome(
        state=ProviderLifecycle(
            stage=ProviderStage.REMOVED,
            declaration=state.declaration,
        ),
        disposition=LifecycleDisposition.TRANSITIONED,
        refusal=None,
        reason="removed; nothing depends on a specific provider (RFC-0010 §7)",
    )


def negotiate(declaration: CapabilityDeclaration) -> Negotiation:
    """The deterministic §6 negotiation adaptation for the declared abilities.

    RFC-0010 §6: the Core adapts to a provider's declared capabilities —
    simplify the request (a provider without Tool Planning is asked for
    a Proposal, not a plan), and use the capability of a strong provider
    (a Tool Planning + Structured Responses declaration is asked for a
    plan directly). The output keys off the declared abilities, never
    the vendor. The adaptation is only the request shape — it grants
    nothing, and the consultation use is `core`'s (RFC-0002 §6).

    Args:
        declaration: The declared capability vocabulary.

    Returns:
        The Negotiation: the request kind and whether a structured reply
        is expected, derived deterministically.
    """
    declared = declaration.capabilities
    has_planner = (
        ProviderCapability.TOOL_PLANNING in declared
        and ProviderCapability.STRUCTURED_RESPONSES in declared
    )
    expects_structured = ProviderCapability.STRUCTURED_RESPONSES in declared
    return Negotiation(
        request_kind=RequestKind.PLAN if has_planner else RequestKind.PROPOSAL,
        expects_structured=expects_structured,
    )


def classify(failure: ProviderFailure) -> ProviderEvent:
    """Classify a §8 failure mode into the RFC-0002 §4.3 event vocabulary.

    The deterministic mapping (RFC-0010 §8 → RFC-0002 §4.3):
    TIMEOUT -> PROVIDER_TIMEOUT
    UNAVAILABLE -> PROVIDER_UNAVAILABLE
    MALFORMED_OUTPUT -> PROVIDER_REFUSAL (a structurally non-compliant
        reply is treated as PROVIDER_REFUSAL, RFC-0002 §4.3)
    INCOMPLETE_PROPOSAL -> PROVIDER_REFUSAL (a proposal lacking its
        expected effect is unusable output, RFC-0002 §4.3)
    UNSUPPORTED_CAPABILITY -> PROVIDER_REFUSAL (the provider declines
        usable output for a capability it cannot actually use; the §8
        revocation is the deterministic adaptation, RFC-0010 §7 rule 1)
    HALLUCINATION -> PROVIDER_REFUSAL (the reasoning is unusable until
        re-verified against known Facts, RFC-0010 §8)
    REFUSAL -> PROVIDER_REFUSAL (the provider declined; a first-class §4
        output, RFC-0010 §4 rule 4)

    Every failure classifies to an event — never a crash (PR11); the
    classification is deterministic (RFC-0007 S7) and loud (disclosed
    honestly, PR16: no recommendation is fabricated). The reaction
    (retry with backoff, the fallback chain, degraded mode) is `core`'s
    (RFC-0002 §10), and provider selection RFC-0016's.

    Args:
        failure: A §8 failure mode.

    Returns:
        The deterministic RFC-0002 §4.3 provider event.
    """
    return {
        ProviderFailure.TIMEOUT: ProviderEvent.PROVIDER_TIMEOUT,
        ProviderFailure.UNAVAILABLE: ProviderEvent.PROVIDER_UNAVAILABLE,
        ProviderFailure.MALFORMED_OUTPUT: ProviderEvent.PROVIDER_REFUSAL,
        ProviderFailure.INCOMPLETE_PROPOSAL: ProviderEvent.PROVIDER_REFUSAL,
        ProviderFailure.UNSUPPORTED_CAPABILITY: ProviderEvent.PROVIDER_REFUSAL,
        ProviderFailure.HALLUCINATION: ProviderEvent.PROVIDER_REFUSAL,
        ProviderFailure.REFUSAL: ProviderEvent.PROVIDER_REFUSAL,
    }[failure]
