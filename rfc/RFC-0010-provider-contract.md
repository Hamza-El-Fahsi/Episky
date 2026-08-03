# RFC-0010 — Provider Contract

**Status:** Draft
**Date:** 2026-08-02
**Scope:** The single canonical contract between the Core and every LLM
provider: what the Core expects of a provider, provider responsibilities,
inputs and outputs, the capability model and negotiation, provider lifecycle,
the failure model, multi-provider coexistence, the security and context
boundaries, provider replacement, and the Provider invariants
**Audience:** Future maintainers
**Supersedes:** Nothing
**Depends on:** RFC-0001, RFC-0002, RFC-0003, RFC-0004, RFC-0005, RFC-0006,
RFC-0007, RFC-0008 (accepted in this series). RFC-0009 is referenced for the
no-secrets-to-providers boundary but is a Draft and is not a dependency.
RFC-0021 is referenced for the machine vocabulary but is a Draft and is not a
dependency.

**Roadmap note:** This is RFC-0000's "RFC-0010 — Provider Contract & LLM
Adapter" (Extension, Required), the document that makes providers replaceable
components and fixes the provider-agnostic internal representation (RFC-0000
§5, §6). It answers the coverage rows RFC-0000 §8 assigns to it: RFC-0001 Q16
(provider variance and minimum capability), Q17 (the provider-agnostic
internal representation), Q18 (outages, refusals, degraded UX), Q26 (cost
controls); RFC-0002 Q11 (degraded-mode scope). It also fixes the "provider
output is untrusted" boundary that RFC-0007 leaves for this contract
(RFC-0007 §6.5).

**BREAKING:** No. This RFC specifies the Provider Contract that RFC-0001,
RFC-0002, RFC-0004, RFC-0005, RFC-0006, RFC-0007, and RFC-0008 already assume —
that providers translate through one internal, provider-agnostic representation
(RFC-0001 §5.4), that provider output is untrusted data (RFC-0001 §7, RFC-0004
A1, RFC-0007 §4.6), and that the Provider View is the only representation an
external provider ever sees (RFC-0007 §2). It does not weaken any Principle,
Boundary, Invariant, or canonical Definition in an accepted RFC.

---

## 0. Purpose

The Core must never know which provider it is talking to. It knows one thing:
**the Provider Contract.** A provider is anything that implements that contract
faithfully; nothing else about it matters.

This RFC answers one question:

> **What does the Core expect from an LLM provider, and what may a provider
> never do?**

Providers are **replaceable components**. The Assistant's value does not come
from any single model; it comes from the deterministic Core that surrounds the
model — the fact model, the approval gate, the verification, the context
discipline. The model is a reasoning service that the Core consults. When the
model changes, the Core must not change.

Three consequences flow from that:

1. **The Core depends only on the Provider Contract.** No vendor name, no
   vendor-specific behavior, no vendor's vocabulary enters the Core. A provider
   that fails to implement the contract is unusable; a provider that implements
   it is interchangeable.
2. **Providers are strong or weak, not good or bad.** Providers differ in
   capability. The Core adapts to those differences through negotiation (§6),
   never by treating a provider's limitation as a failure of the product or by
   special-casing a vendor.
3. **Provider output is untrusted.** A provider proposes; the Core disposes.
   Everything a provider returns is advisory data. It is never a Fact, never an
   approval, never a command, never policy (RFC-0004 A1; RFC-0007 §6.5).

This RFC is architecture only. It defines no HTTP, no REST, no SDKs, no vendor
APIs, no JSON schemas, no implementation. It defines the contract those things
must serve.

---

## 1. Design Principles

These principles govern every design decision in this RFC.

1. **Provider independence.** The Core holds no knowledge of any specific
   provider. The contract is the entire interface between them.
2. **Capability-based design.** The Core plans with what a provider can do, as
   declared by the provider and validated by the Core. A provider's abilities
   are facts the Core reasons over; they are not promises to trust blindly.
3. **Deterministic Core.** Everything the Core does around a provider — the
   Provider View it sends, the validation of what returns, the routing of
   results — is deterministic. The only nondeterminism in the system is inside
   the provider, and it is contained (§8).
4. **Provider output is untrusted.** Model text is data, never authority, never
   command, never evidence of itself (RFC-0001 §7, RFC-0004 A1, RFC-0007).
5. **Graceful degradation.** The system loses a provider and still works —
   honestly and usefully — at reduced capability. Degradation is a designed
   state, not a crash (RFC-0002 degraded mode).
6. **No vendor-specific assumptions.** No principle, boundary, or invariant in
   the system may depend on which vendor is attached. A behavior that works
   only for one vendor is a defect, not a feature.
7. **The contract is minimal.** The contract says only what every provider must
   agree on. Extra capabilities are declared, not assumed; they never change
   what a minimally capable provider must do.
8. **Safety is not negotiable by capability.** No negotiation weakens a safety
   invariant. A weak provider simply does less; it does not do unsafe things
   more easily (§6).
9. **The Core is the only route.** There is exactly one channel between Core
   and provider — the Provider View out, structured results back. No side
   channels, no out-of-band influence (§10, §11).
10. **Replacement is the test.** If swapping the provider requires changing the
    Core, the contract has failed (§12).

---

## 2. Provider Responsibilities

A provider has a bounded, normative set of responsibilities. It is a reasoning
service; it is not a participant in the machine's governance.

**What every provider must do:**

| Responsibility | What it means |
|---|---|
| **Receive the Provider View** | Accept the sanitized, purpose-limited representation assembled by the Core (§3), and reason only over it |
| **Generate Proposals** | Produce proposed Actions (or a plan of proposed Actions) from the Provider View, when the Core requests reasoning about what to do |
| **Generate Explanations** | Produce human-readable justification for its Proposals, comprehensible to the Operator |
| **Return structured results** | Return its reasoning in the contract's internal form, not as free-form text the Core must guess at (§4) |
| **Answer questions** | Respond to the Core's questions about the goal, the evidence, or the machine |
| **Signal inability** | Say plainly when it cannot do what was asked — unknown, unsupported, refused — rather than improvising (§8) |

**What no provider may do (normative, reinforced by invariants in §13):**

| Never | Why |
|---|---|
| **Execute** | The Provider boundary has no execution path. Model output can at most become a Proposal (RFC-0004 A1) |
| **Classify authority** | Risk classification, gates, and approval are deterministic Core/Policy work (RFC-0008). The provider never assigns a risk class or decides what is approvable |
| **Create Facts** | Facts are produced only by the deterministic normalization of Observations (RFC-0005). A provider's sentence is never a Fact (RFC-0005 F6) |
| **Verify** | Verification is state-based comparison of Facts (RFC-0006). The provider never confirms success (RFC-0006 V1) |
| **Approve** | Only the Operator approves. The provider never grants, extends, or confirms authorization (RFC-0004 §7) |
| **Escalate authority** | The provider cannot widen its own or anyone's authority, and it cannot ask for authority by reframing (RFC-0004 A8) |
| **Store secrets** | A provider never receives secrets, and never persists anything it did receive (RFC-0009; §11) |
| **Modify policy** | Policy is Operator-owned and Policy-Engine-administered (RFC-0004). The provider never influences, extends, or bypasses it |

Everything a provider produces remains **advisory**. A Proposal is a
suggestion for the Operator to approve; an Explanation is content to read; a
refusal is a report. None of them changes the machine. Only the Executor,
under a valid Approval Token, changes the machine (RFC-0004 A2, RFC-0008).

---

## 3. Provider Inputs

The Core gives a provider exactly one thing: **the Provider View**. The
Provider View is the assembled, sanitized, purpose-limited representation of
what the provider may reason over (RFC-0001 §9; RFC-0004 §3.1 Context Manager;
RFC-0007 §2). It is built from Facts and history, never from raw machine output.

**What the Provider View contains (conceptually):**

| Element | What it is |
|---|---|
| **Operator Goal** | The goal the Operator asked for, in the session's terms |
| **Provider View (evidence)** | The selected Evidence Sets and context the Core has decided the provider may see (§11) |
| **Allowed Context** | The bounded, purpose-limited context assembled from Facts (RFC-0005 §2 Context; RFC-0002 §2.4) |
| **Conversation State** | The structured record of the current reasoning thread, as the Core represents it |
| **Capability Declaration** | The provider's own declared capabilities, echoed back so the Core reasons over them (§5) |

**Nothing else.** The Provider View is the *only* input. In particular:

1. **No raw machine output.** Unnormalized text never reaches the provider
   (RFC-0005). Raw output is normalized to Facts first; only those Facts may
   appear in the Provider View.
2. **No Audit records.** The Audit System is invisible to providers (§11).
3. **No secrets.** Credentials, personal data, and anything RFC-0009 classifies
   as secret never enter the Provider View (§11).
4. **No provider identity.** The Core does not shape the Provider View
   differently for different vendors. A vendor that needs more or different
   input to work well is not a vendor the Core serves differently; it is a
   vendor whose capability model is different (§5, §6).
5. **No machine identity beyond what reasoning needs.** The Provider View
   contains the machine context that reasoning requires, not the Assistant's
   internals.

The Provider View is assembled by the Context Manager under RFC-0007's
sanitization and RFC-0009's secrecy rules. This RFC does not define its shape —
no schemas — but defines its boundary: this, and only this, may go out.

---

## 4. Provider Outputs

A provider returns one of a finite set of structured results. The Core
validates the result against the contract; anything that does not conform is
malformed (§8).

| Output | What it is |
|---|---|
| **Proposal** | A proposed Action or plan of proposed Actions, each carrying what it is, why, and its expected effect — for the Core to classify, present, and gate (RFC-0008) |
| **Explanation** | Human-readable justification of a Proposal, for the Operator |
| **Questions** | Requests for information the provider needs to continue reasoning |
| **Clarifications** | Restatements of the goal or evidence, checking that the provider understood |
| **Alternative Plans** | One or more distinct courses of action, presented for the Operator to choose among |
| **Refusal** | A plain statement that the provider will not do the asked-for thing |
| **Failure** | A report that the provider could not complete the request |
| **Need More Evidence** | A request for additional Facts or inspection before it can reason further |

**Nothing else.** A provider's output that is none of these — raw text the
Core must interpret, a claim presented as fact, an instruction to act — is not
a valid output. It is treated as malformed or adversarial (§8, §10).

**Rules over outputs:**

1. **Outputs are structured.** The provider returns its reasoning in the
   contract's internal form, so the Core can route it deterministically. The
   provider does not decide the format; the contract does.
2. **A Proposal carries its expected effect.** A Proposal is not complete
   without the expected Post-condition it claims to produce (RFC-0006 §5,
   RFC-0008 §9). Without it, the Core cannot classify or verify, and the
   Proposal is incomplete (§8).
3. **Output is advisory, always.** No output has authority. A Proposal is not
   an approval; an Explanation is not a Fact; a Refusal is not a verdict. The
   Core routes each output to its deterministic consumer, and nothing else
   happens (§2).
4. **Inability is a first-class output.** Saying "I cannot" is a valid, valued
   output; improvising a wrong answer is not (RFC-0001 §10.8). The Core treats
   Refusal and Failure as legitimate results, not defects (§8).
5. **Nothing is executed from output.** No string from a provider is ever
   executed (RFC-0001 §7.3). A Proposal is turned into an Action only by the
   deterministic Core, only through approval (RFC-0008).

---

## 5. Capability Model

Providers differ. The Capability Model is how the Core reasons about those
differences without naming any vendor.

**Capabilities are declared, not assumed.** Each provider declares, at
registration (§7), which capabilities it has. The Core stores these as facts
about the provider and validates them against observed behaviour. A declared
capability that the provider demonstrably lacks is reclassified (§8,
unsupported capability).

| Capability | Meaning |
|---|---|
| **Reasoning** | Can reason over the Provider View to produce Proposals and Explanations. The minimum any provider must have |
| **Tool Planning** | Can produce multi-step Plans of proposed Actions, including expected effects, rather than single Proposals |
| **Streaming** | Can deliver its reasoning incrementally |
| **Structured Responses** | Can reliably return output in the contract's structured form (§4) |
| **Long Context** | Can reason over a large Provider View |
| **Image Understanding** | Can reason over image evidence, if the domain uses it |
| **Offline** | Runs without network access |
| **Local** | Runs on the Operator's machine (RFC-0007 §4.7: localness grants no trust) |

**No capability implies permission.** A capability describes what a provider
*could* do with the inputs it is given. It grants nothing:

1. A provider with Tool Planning does not get to execute its plan; the plan
   still passes the full classification and approval gate (RFC-0008).
2. A provider with Image Understanding does not get to see images the context
   boundary excludes (§11).
3. A provider that is Local and Offline is not more trusted; the Provider
   boundary is a trust boundary regardless of network distance (RFC-0007 §4.7,
   §6.5).
4. Capabilities never widen the Provider View. The View is bounded by purpose
   and secrecy; a capability changes how the Core *uses* a provider, never what
   it is *allowed* to see.
5. Capabilities never weaken an invariant. "It cannot do structured responses"
   changes how the Core requests from it; it never changes what the Core
   accepts as valid authority.

---

## 6. Capability Negotiation

The Core adapts to a provider's declared capabilities. Negotiation is a
deterministic Core activity; it is not a conversation with the provider.

**Adapting to weak providers:**

1. **Simplify the request.** A provider without Tool Planning is asked for a
   Proposal, not a plan. The Core composes steps itself from the Proposal and
   the Evidence Set.
2. **Ask for structured output, expect less.** A provider without Structured
   Responses is asked again or differently; if its output is still not
   structured, it is treated as malformed (§8) and the Core degrades to a
   simpler request.
3. **Break the task down.** A weak provider gets a smaller Provider View and
   simpler questions, with the Core doing the composition work the provider
   cannot.
4. **Never pretend.** The Core never presents a weak provider's output as
   stronger than it is. An unstructured answer is never interpreted into a
   confident structure.

**Adapting to strong providers:**

1. **Use the capability.** A provider with Tool Planning and Structured
   Responses is asked for plans and expected effects directly.
2. **Hold it to the same contract.** A strong provider is still validated the
   same way. Its Proposals still get classified, gated, and verified. Strength
   is a capacity, not an exemption.
3. **Never shape behavior by vendor.** Negotiation keys off declared
   capabilities, never off which vendor it is.

**The Core never exposes vendor logic upward.** Nothing upstream — the
Operator, the plan, the approval UX — may look different because of which
vendor is attached. Degradation is expressed in the terms of capability
("no provider available", "this provider cannot plan"), not in vendor terms.
The Operator sees what the Assistant can do, never the vendor's name as a
reason (RFC-0002 degraded mode).

---

## 7. Provider Lifecycle

A provider moves through a defined lifecycle. The Core owns the lifecycle; a
provider cannot insert itself into it.

| Stage | What happens | Normative requirement |
|---|---|---|
| **Registration** | A provider is declared to the Core with its capabilities | The declaration is stored as facts; nothing is trusted from it until validated |
| **Selection** | The Core chooses a provider for a request, using configuration and policy | Selection is deterministic and capability-aware; cost and policy limits apply (RFC-0001 Q26) |
| **Activation** | The provider is initialized and verified usable | A provider that cannot activate is a Failure (§8), not a crash |
| **Use** | The provider receives a Provider View and returns a structured result | Every use is validated against the contract (§4) |
| **Failure** | The provider fails during use | The Core reacts per the Failure Model (§8); fallback chains may engage |
| **Replacement** | Another provider is selected in its place | The Core's behavior is unchanged by the swap (§12) |
| **Removal** | A provider is withdrawn from the system | Removal is safe: nothing in the Core depends on a specific provider |

**Rules:**

1. **Registration declares, validation confirms.** Capabilities are validated
   against observed behaviour. A provider that claims Tool Planning but cannot
   produce a valid plan has its capability revoked for the session and is
   treated as unsupported (§8).
2. **Fallback chains are Core-side.** The Core may keep a chain of providers in
   preference order (RFC-0000's "fallback chains"). On failure, the Core tries
   the next provider; when none remains, it degrades (RFC-0002 degraded mode).
3. **Degraded mode is a designed outcome.** With no usable provider, the
   Assistant runs facts-only: inspections, Facts, deterministic skills. It
   reports facts and offers options; it does not fabricate recommendations
   (RFC-0002 Q11; RFC-0002 §2.5).
4. **A provider never bypasses its lifecycle.** A provider cannot re-register,
   self-select, or keep itself active. Selection and removal are Core
   decisions.
5. **Removal leaves no residue.** The Core must hold no vendor-specific state
   that outlives the provider's use (RFC-0001 §11.4, additive
   non-destructive).

---

## 8. Failure Model

A provider can fail in bounded ways. Each failure has a defined Core reaction.
The Core never crashes because of a provider.

| Failure | What it is | Core reaction |
|---|---|---|
| **Timeout** | The provider did not respond within the phase budget (RFC-0002 Q3) | Treat as Failure; try the next fallback or degrade; disclose the timeout |
| **Unavailable** | The provider cannot be reached at all | Fallback chain or degraded mode; the outage is an event, not a crash (RFC-0001 §10.7) |
| **Malformed output** | The provider returned something that is not a valid contract output (§4) | Reject it; if it persists, re-request or treat as Failure; never interpret it into validity |
| **Incomplete proposal** | A Proposal lacks its expected effect or is otherwise not classifiable | Reject as incomplete; request again or degrade; never approve a half-formed proposal (RFC-0008) |
| **Unsupported capability** | A provider cannot actually do a capability it declared | Revoke the capability; renegotiate (§6); the provider is used at its real capability |
| **Hallucination** | The provider asserts a claim that contradicts known Facts | The assertion is not a Fact and gains no authority; if it drives a Proposal, the Proposal is treated as ordinary output and verified against Facts (RFC-0006) |
| **Refusal** | The provider states it will not do the asked thing | Honor it as a first-class output; present it; offer alternatives; never pressure, and never substitute a different provider's judgment silently |

**Rules:**

1. **Provider failures are Core events.** Every failure is reported through the
   runtime's event model (RFC-0002 §4, PROVIDER_FALLBACK_FAILED), disclosed to
   the Operator honestly, and recorded in Audit. No failure is silent.
2. **Hallucination is contained by construction.** Because provider output is
   advisory and never creates Facts, a hallucination cannot corrupt the
   machine model. Its worst effect is a bad Proposal, which the gate and
   verification catch (RFC-0004 A1, RFC-0006).
3. **A malformed output is not a Fact.** The Core never derives a Fact from
   text that failed to conform to the contract. Unknown is preferable to
   interpreting garbage (RFC-0005 F11).
4. **No infinite retry.** Failures are bounded by retry policy (RFC-0002 Q2).
   Persistent failure means fallback or degraded mode, not a loop.
5. **Refusal is respected, not worked around.** If a provider refuses, the
   Core does not silently ask another provider to do the refused thing without
   telling the Operator why. Refusal is disclosed.

---

## 9. Multi-provider Philosophy

The Assistant is designed so multiple providers may coexist. This is
architecture, not implementation: the contract, not any adapter, makes
coexistence possible.

**Why multiple providers may coexist:**

1. **Resilience.** A provider outage degrades, never disables, the Assistant
   (§8, fallback chains).
2. **Choice.** The Operator selects providers by preference and policy
   (RFC-0000 §5, provider selection; RFC-0001 Q26 cost controls).
3. **Capability fit.** Different tasks may be served by providers with
   different capabilities — one for planning, one for local offline use.
4. **No lock-in.** The Operator is never held hostage to one vendor (§12).
5. **Auditable independence.** Provider disagreement is a first-class signal
   in the trust model: when providers disagree about a claim that is not
   directly verifiable, the Assistant surfaces the disagreement rather than
   picking a favorite (RFC-0007 §6.3).

**Architecture-only.** This RFC does not define how providers are wired,
configured, or profiled (RFC-0016 owns provider selection and profiles, and is
Post-MVP). It defines the property those mechanisms must preserve: the Core
treats each provider as an interchangeable implementation of one contract.

**Rules:**

1. **Coexistence is transparent.** Upstream behavior does not change based on
   how many providers exist or which one served a request.
2. **Providers never see each other.** There is no channel between providers;
   they are all separate from the Core and from each other (§10).
3. **One contract, many implementations.** Every provider implements the same
   contract. A provider is not "more integrated"; it is merely another
   implementation.

---

## 10. Security Boundary

The Provider boundary is a security boundary. Everything on the provider side
of it is untrusted (RFC-0001 §7, RFC-0004 §3.1, RFC-0007 §4.6). The boundary
is structural, not advisory: there is no code path from the provider to the
machine except through the deterministic Core, the gate, and the Executor.

**The provider cannot:**

| Cannot | Because |
|---|---|
| **Execute** | The Provider boundary has no execution path (RFC-0004 A1) |
| **Approve** | Only the Operator approves (RFC-0004 §7) |
| **Verify** | Verification is deterministic Fact comparison (RFC-0006) |
| **Create Facts** | Facts come only from normalized Observations (RFC-0005) |
| **Escalate authority** | Authority flows downward only (RFC-0004 A8) |
| **Store secrets** | Secrets never leave, and the provider never persists what it sees (RFC-0009; §11) |
| **Modify policy** | Policy is Operator-owned (RFC-0004) |
| **Bypass approval** | Every Action passes the same gate (RFC-0008; RFC-0004 A3 spirit) |
| **Reach the machine directly** | The Core mediates every exchange (RFC-0001 §8.4) |

**Everything remains advisory.** The provider's entire output — Proposals,
Explanations, refusals — is data. It influences the machine only by being
routed through deterministic Core processing, classification, approval, and
execution. There is no output from a provider that, by itself, changes the
machine.

**Prompt injection is contained by design.** A provider that returns
instructions, embedded commands, or reframed goals is still just producing
advisory output. Suspected injection is handled at the trust boundary: the
output is contained or quarantined and never treated as an instruction
(RFC-0007 §6.5, §7). The Core's deterministic handling does not change because
a provider tried to act as an agent.

---

## 11. Context Boundary

The Context Boundary fixes exactly what a provider may receive. It is a
normative limit; no capability, no negotiation, and no provider request widens
it.

**The provider receives only the Provider View** (§3). It never receives:

1. **Audit records.** The Audit System is invisible to providers. Nothing from
   the audit trail is offered as context (§2, §3).
2. **Secrets.** Credentials, tokens, personal data, and everything RFC-0009
   classifies as secret never enter the Provider View (RFC-0007 §6.10).
3. **Raw machine output, unless explicitly normalized.** Raw output is
   distro-specific text. It is normalized into Facts by RFC-0005 before it may
   appear in the Provider View. The only way raw output reaches a provider is
   as part of an allowed, normalized representation — and even that must pass
   RFC-0007 sanitization first.
4. **Anything outside the purpose limit.** The Provider View is
   purpose-limited (RFC-0001 §9): it contains what the current reasoning task
   needs, and nothing more. It is assembled per request, not streamed broadly.

**References.** This boundary is implemented using RFC-0005's fact pipeline
(raw output → Observation → Normalization → Fact → Evidence Set → Context;
RFC-0005 §2) and RFC-0007's sanitization and trust classes (the Provider View
is the *only* representation an external provider ever sees; RFC-0007 §2, §6).
RFC-0009 owns the secrecy half of the boundary; this RFC states the boundary
the contract must honor.

**Rules:**

1. **The View is assembled, not forwarded.** The Core builds the Provider View
   from Facts and history through the Context Manager. It does not forward raw
   data (RFC-0004 §3.1).
2. **Minimal by default.** The Provider View contains the least the reasoning
   task requires. Bounds are enforced by purpose and size (RFC-0005 Q8).
3. **Boundary never widens for capability.** A provider that can handle "more"
   never receives more than the boundary allows. Capability is about how the
   Core uses a provider, not what it is allowed to see (§5.4).
4. **Leakage is a security incident.** Any path by which Audit, secrets, or
   raw output reaches a provider is a breach of the boundary and is handled as
   such (RFC-0007 §6.10; RFC-0009).

---

## 12. Provider Replacement

The test of this RFC is replacement: **swapping one provider for another must
require zero Core changes.**

Why replacing OpenAI with Claude (or any vendor with any vendor) should change
nothing in the Core:

1. **The Core knows no vendor.** No Core component references a provider by
   name, behavior, or vocabulary. The contract is the entire interface.
2. **Capabilities are abstract.** The Core reasons over declared capabilities
   (§5), not over vendor-specific features. A different vendor with the same
   capabilities is, to the Core, the same provider.
3. **Inputs and outputs are contract-shaped.** The Provider View out and the
   structured results back (§3, §4) are identical regardless of vendor. The
   vendor's translation work happens behind the contract, in the adapter.
4. **Lifecycle is Core-owned.** Registration, selection, activation, and
   removal are Core mechanics (§7). Replacing a provider is re-registering a
   different implementation of the same contract.
5. **Security and context boundaries are fixed.** The provider cannot reach
   beyond its boundary (§10, §11). A different vendor is confined the same way,
   so the swap changes nothing about what the machine permits.

**What a replacement does change:** the adapter — the piece that translates
between a vendor's own interface and the Provider Contract. That is
implementation, owned by the adapter, and is exactly what this RFC makes
isolated.

**Rule:** If replacing a provider requires a change to any Core invariant,
principle, or deterministic behavior — rather than only to an adapter — the
Provider Contract has failed and must be amended (RFC-0003 Part II). This is
the RFC's central, testable claim.

---

## 13. Provider Rules (Normative)

The following invariants are normative for the entire project. Each is
testable: a reviewer can check the described behaviour against the rule. They
extend, and never weaken, RFC-0001's principles, RFC-0002's §9 invariants,
RFC-0004's A-invariants, and RFC-0007's T-invariants.

| ID | Invariant | Test |
|---|---|---|
| PR1 | **Provider never executes.** No output from a provider becomes a command; there is no execution path across the Provider boundary. | Deliver an output containing a command; verify nothing executes. |
| PR2 | **Provider never creates authority.** Provider output grants, extends, or confirms no authorization. | Deliver an output claiming approval; verify no authority changes. |
| PR3 | **Provider never creates Facts.** No provider output becomes a Fact; Facts come only from normalized Observations. | Deliver an output asserting a machine fact; verify no Fact is created. |
| PR4 | **Provider never bypasses Approval.** Every provider-originated Action passes the full classification and approval gate. | Route a provider Action to execution without the gate; verify it is blocked. |
| PR5 | **Provider output is advisory.** All provider output is data; none of it changes the machine by itself. | Take any provider output; verify machine state is unchanged absent Core routing. |
| PR6 | **Provider never verifies.** The provider never confirms success; verification is deterministic Fact comparison. | Deliver an output claiming success; verify no success is recorded from it. |
| PR7 | **Provider never escalates authority.** A provider cannot widen its own or any other actor's authority. | Deliver an output demanding elevation; verify no elevation occurs. |
| PR8 | **Provider never stores secrets.** The provider never receives secrets and never persists what it saw. | Attach a secret-adjacent token; verify it never enters the Provider View and nothing is persisted. |
| PR9 | **Provider never modifies policy.** Provider output changes no policy and no gate. | Deliver an output attempting a policy change; verify policy is unchanged. |
| PR10 | **The Core knows no vendor.** No Core component depends on a specific provider's identity or behavior. | Search the Core for a vendor name or vendor-specific branch; verify none. |
| PR11 | **Provider failure never crashes the Core.** Timeout, unavailability, malformed output, and refusal all degrade, never crash. | Force each failure mode; verify the runtime degrades or handles, never exits. |
| PR12 | **No capability implies permission.** Declared capabilities grant no execution, authority, or context. | Grant a provider every capability; verify its boundary is unchanged. |
| PR13 | **Malformed output is rejected, not interpreted.** Output that does not conform to the contract yields no result. | Deliver non-contract output; verify it is rejected, never coerced into validity. |
| PR14 | **The Provider View is the only channel.** The provider receives exactly the Provider View and nothing else. | Instrument the boundary; verify no Audit, secret, or raw output crosses it. |
| PR15 | **Replacement requires no Core change.** Swapping one provider for another changes only the adapter. | Replace a provider; verify no Core file or behavior changes. |
| PR16 | **Degradation is honest.** Degraded mode reports facts and options; it fabricates no recommendations. | Remove all providers; verify the facts-only report recommends nothing. |

---

## 14. Interaction with other RFCs

This RFC specifies the Provider Contract for the whole project. Only references
follow; no duplication (RFC-0003 Part II §1).

| RFC | Relationship | What RFC-0010 says here |
|---|---|---|
| **RFC-0001** | Architecture and principles | Implements the uniform provider abstraction (§5.4), the untrusted-output principle (§7, §8.4), the extension contract (§11); answers Q16–Q18, Q26. |
| **RFC-0002** | Runtime states and invariants | Consumes the degraded mode, provider-loss events, and phase budgets (RFC-0002 §2.1, §4.6, Q3, Q11); gives providers their contract-shaped role in the loop. |
| **RFC-0003** | Vocabulary and governance | Uses Provider and Provider View canonically (§2.1, §2.8); §17 flags new terms for Part I. |
| **RFC-0004** | Authority model | Implements the Provider component's untrusted status and its Propose-only authority (§3.1, §7); reinforces A1, A8. |
| **RFC-0005** | Canonical Fact Model | Providers consume Facts and never produce them (F6); the Provider View is built from the Fact pipeline's Context stage (§2). |
| **RFC-0006** | Verification & Outcome Model | Providers never verify (V1, V6); provider-produced Proposals carry the Post-conditions verification compares. |
| **RFC-0007** | Trust and sanitization | The Provider View is the only sanitized representation a provider ever sees (§2); provider output is untrusted (§4.6, §6.5); injection is contained. |
| **RFC-0008** | Approval & Policy Engine | Provider Actions pass the same classification and gate as any Action (RFC-0004 A3 spirit); Proposals are the gate's input. |

Forward references (planned RFCs this contract constrains): RFC-0009 (the
no-secrets-to-providers boundary this contract honors); RFC-0011 (skills are
separate extensions but consume this contract's provider); RFC-0012 (Context
and Memory assemble the Provider View); RFC-0015 (how provider degradation and
refusals are presented); RFC-0016 (provider selection, profiles, and
preferences); RFC-0020 (implementation blueprint and adapter details).

---

## 15. Open Questions

Questions this RFC deliberately leaves open; each names its owner. None blocks
the Provider Contract's guarantees.

1. **Provider selection and profiles.** How providers are configured, chosen by
   preference, and profiled is owned by RFC-0016 (Post-MVP). This RFC fixes the
   contract they select among, not the selection mechanism.
2. **Secrets to providers.** The precise mechanism by which RFC-0009 keeps
   secrets out of Provider Views is owned by RFC-0009; this RFC states the
   boundary, not the redaction.
3. **Context assembly mechanics.** How Context and Memory assemble the Provider
   View from Facts and history is owned by RFC-0012 and RFC-0015.
4. **Cost controls.** Concrete token budgets, spend warnings, and cost policy
   for bring-your-own-key providers (RFC-0001 Q26) are owned by RFC-0016 and
   RFC-0020.
5. **Skill-provider interaction.** How skills consume the same provider
   contract, and what a skill may request of a provider, is owned by RFC-0011.
6. **Adapter implementation.** How the Provider Contract is realized for any
   specific vendor — the adapter layer — is owned by RFC-0020 (implementation
   blueprint). This RFC fixes the contract an adapter must serve.

---

## 16. Risks

| Risk | Mitigation |
|---|---|
| **Vendor lock-in** | The Core holds no vendor knowledge (PR10); the replacement test is normative (PR15, §12); adapters are isolated behind the contract |
| **Capability mismatch** | Capabilities are declared and validated (§5–§6); unsupported capability is revoked and renegotiated, never trusted (§8) |
| **Hallucinated plans** | Proposals carry expected effects and pass the full gate; verification is deterministic Fact comparison (PR3, PR6, RFC-0006) |
| **Prompt injection** | Provider output is advisory and contained; suspected injection is quarantined (PR1–PR5, RFC-0007 §6.5, §7) |
| **Context leakage** | The Provider View is the only channel; Audit, secrets, and raw output never cross (PR8, PR14, §11) |
| **Weak local models** | The Core adapts by simplifying requests and breaking tasks down (§6); weak capability is used honestly, never papered over |
| **API evolution** | Vendors change their interfaces; the adapter absorbs the change (RFC-0000 "adapter's problem"); the Core is untouched because it holds no vendor interface (PR10) |

---

## 17. Vocabulary Additions for RFC-0003

The following terms are defined in this RFC and must be added to RFC-0003 Part
I by additive amendment: **Provider Contract**, **Provider Capability**,
**Capability Declaration**, **Capability Negotiation**, **Provider Lifecycle**,
**Fallback Chain**, **Provider Refusal**, **Provider Failure**, **Degraded Mode
(contract sense)**. The definitions appear at first use in §5, §6, §7, §8, and
§0. Provider, Provider View, Proposal, Explanation, Context, Approval, Policy,
Fact, Verification, and Action already exist in RFC-0003 Part I and are used
here with their canonical meanings.

---

*End of RFC-0010. Normative: sections 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
13. Explanatory and load-bearing: sections 0, 14, 15, 16, 17. Any change to a
Provider responsibility, the Provider View boundary, an output type, a
capability, a lifecycle stage, a failure reaction, a security or context
boundary rule, or an invariant PR1–PR16 is a BREAKING change and must be made
by amendment (RFC-0003 Part II).*
