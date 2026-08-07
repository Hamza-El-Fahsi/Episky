# Iteration 10 — Design Review (Providers & Skills Layer)

> **Document type:** Implementation design review, at the same rigor as
> Iterations 2–9. **Not an RFC, not code.**
> **Read this first:** This document **defines no new architecture, modifies no
> RFC, invents no behavior, and writes no production code.** It translates the
> frozen corpus (RFC-0000–0013, RFC-0021, the decision traceability matrix,
> `docs/architecture-implementation-blueprint.md`, and the ratified
> `docs/implementation-decision-notes.md` DN-1…DN-74) into an implementation
> plan for the **Providers & Skills layer — the `providers` and `skills`
> packages** (blueprint §8.10, re-ordered to Iteration 10 by DN-45, and so
> labeled by the Iteration 9 closeout). Where the corpus does not decide
> something, this document **reports** it as an ambiguity or a question; it does
> not resolve it.
>
> **Status of sources.** RFC-0010 and RFC-0011 are both **Draft** (2026-08-02;
> not Accepted; the provider contract's normative sections 1–13 and the skill
> contract's normative sections 1–28 may change before acceptance). Per RFC-0003
> Part II §1.1 Draft RFCs are not normative and must not be relied upon by
> implementation; yet the blueprint (a translation, §0) targets the Drafts'
> *invariants* as the conformance oracle (blueprint §9 #2). Iteration 10 inherits
> Iterations 1–9's posture: it conforms to RFC-0010's and RFC-0011's Draft
> wording knowingly, accepting the rework risk that a Draft change carries.
> Blueprint §8.0 gate stands — production code begins only after RFC-0015/0019/
> 0020 and the Drafts are Accepted; this iteration builds the translation
> scaffold. The load-bearing dependencies this layer rests on — RFC-0001 §5
> (Providers; Skills), §7 (untrusted output), §11 (the two extension axes);
> RFC-0002 §4.3 (provider events), §5 (the session loop), §6 (consultation
> rules), §9 invariants 4, 5, 7, §10 (provider failure); RFC-0004 §4.4
> (Provider profile), §4.10 (Skills profile), §7 (the authority matrix), A1,
> A3, A8, A9; RFC-0007 T4 (§4.6, §6.5), §4.8; RFC-0008 §5 (the gate's input);
> RFC-0012 §13/§27 and RFC-0010 PR14 (the View is the only channel, built by
> `context`, Iteration 9); RFC-0009 SC3/SC5 (no secrets to extensions) — are
> **Accepted**, which bounds the rework risk.
>
> **Scope decision (reported — Q1).** DN-45 re-ordered the build so that
> `providers` + `skills` (blueprint §8.10) follow `context` (Iteration 9), and
> the Iteration 9 closeout (`docs/iteration-9-design-review.md` §17; the
> consistency-report "Readiness for Iteration 10") records that "The next
> iteration is the `providers` + `skills` layer (blueprint §8.10, re-ordered by
> DN-45 to Iteration 10)." Blueprint §8.10 still reads "Iteration 9 — `providers`
> + `skills`"; the label was never renumbered (mirroring how §8.7/§8.8/§8.9 were
> left standing). This task's scope implements `providers` + `skills` at
> Iteration 10, which continues the recorded supersession of the numbering (Q1).
> The re-order is dependency-safe — `providers` (Layer 5, imports `context`)
> and `skills` (Layer 5) precede `core`/`cli` (Layers 6–7), preserving the
> safety spine (RFC-0000 §6 items 1, 3) and blueprint Risk #9's mitigation
> (secrets, Layer 2, precedes context and providers).

---

## 1. Architectural consistency review

### 1.1 Scope (blueprint §8.10, transcribed)

| Item | Value |
|---|---|
| Goal | The extension axes, gated |
| Work | Uniform provider interface, structured-output validation, one vendor adapter; Skill loader/authenticator/activator wired to the gate |
| Definition of Done | PR11 (malformed degrades, never crashes), PR14 (View is only channel), F6 (never a Fact); SK4 (every Skill Action passes the gate), SK5 (untrusted until authenticated), SC5 (no secret) — all pass |
| RFC basis | RFC-0010 §2–§8; RFC-0011 §4, §22, §23 |

Blueprint §7 (test oracle) carries the rows: `providers` — "View is the only
input (PR14); structured outputs only (RFC-0010 §4); malformed → degrade, never
crash (PR11); output never a Fact (F6); provider never executes (RFC-0010 §2)" —
oracle RFC-0010 §2–§4, §8, PR1–PR16; `skills` — "Every Skill Action passes the
gate (SK4); no unit approval; Skill cannot execute/verify/approve (RFC-0011 §4);
no secret reaches a Skill (SC5); untrusted until authenticated (SK5)" — oracle
RFC-0011 §4, §28; SC5. Blueprint §5 exposes the package contracts: `providers`
— "Consume a Provider View; return one of the finite structured outputs;
validate and route them; never accept secrets" (RFC-0010 §3, §4, §8; PR1–PR16);
`skills` — "Load/authenticate a Skill package; activate; expose its bundled
Collectors and candidate Plans through the gate" (RFC-0011 §22, §23, §4;
SK1–SK16). Blueprint §10 coverage rows: `providers/*` = RFC-0010, §2–§8, oracle
PR1–PR16; F6; SC3; `skills/*` = RFC-0011, §4, §22, §23, oracle SK1–SK16; SC5.
Blueprint §3 names the responsibilities: "Providers (RFC-0001 §5; RFC-0004 §4.4)
— Uniform adapter interface, structured output validation, first vendor
adapter"; "Skills (RFC-0001 §5; RFC-0004 §4.10) — Loader/authenticator,
activation, gate wiring".

**Layer-enforceable now vs. cross-component.** The §8.10 DoD set is PR11, PR14,
F6, SK4, SK5, SC5. The layer can satisfy the DoD set **at its own surface** as
deterministic mechanics plus layer-boundary tests; the parts whose enforcement
points do not exist yet — the consultation wiring (when Diagnosis/Planning/
Replanning call a provider, and when Diagnosis/Planning/Machine Inspection call
a Skill; RFC-0002 §5, §6), provider selection and fallback chains (RFC-0016,
Post-MVP; RFC-0010 §15 OQ1), the provider-failure reaction (retry with backoff →
fallback chain → degraded mode; RFC-0002 §10), the `core`-side routing of
provider outputs to the Policy/Approval gate and of Skill Actions to
classification (RFC-0008 §5), the audit writes of provider/skill events
(RFC-0013 §23; RFC-0011 §16), the packaging format and signing scheme
(RFC-0017/RFC-0020; RFC-0011 §30 OQ1), the sandboxing mechanics (RFC-0020;
RFC-0011 §30 OQ2), and the skill enablement/selection configuration (RFC-0016) —
are recorded as the owning packages' DoD (RFC-0002 → `core`, Iteration 11;
RFC-0016; RFC-0020; RFC-0017), mirroring how Iteration 9 recorded the Context
Building state wiring, the history/skill-material producers, and the cat-9 audit
write against `core`/`providers`/`skills`, and how Iterations 7–8 recorded the
§6.2 edges against `core`.

**The enforcement halves this layer inherits.** Iteration 9 recorded, not
dropped: the history/turn producers (Provider replies as History material) and
skill material production are **this** iteration's DoD (RFC-0012 §6 cat. 3/5;
RFC-0011 §26; consistency report "Deferred item" rows naming `providers` +
`skills`, Iteration 10). RFC-0009 SC3 (no secret in the Provider View) and SC5
(no secret reaches a Skill) are the blueprint §8.10 DoD of **this** iteration:
providers never receives secrets and never receives the Audit (PR14; RFC-0010
§10, §11), and a Skill never receives or stores secrets (RFC-0011 §15). Each is
a **Definition of Done item of this iteration**, not an optional follow-up.
RFC-0001 §5's "Report provider errors and refusals honestly to the Core" is the
§8/PR11 DoD of this iteration.

### 1.2 Out of scope (recorded, not dropped)

Each of these is owned elsewhere and is **not** built in Iteration 10:

| Item | Owned by | Blueprint gate |
|---|---|---|
| The consultation wiring: when Diagnosis/Planning/Replanning consult a Provider, and when Diagnosis/Planning/Machine Inspection consult a Skill, each after a fresh Context Building | RFC-0002 §5, §6; `core`, Iteration 11 | RFC-0002 §5, §6 |
| Provider selection, preference order, fallback chains, profiles, and cost controls | RFC-0016 (Post-MVP); RFC-0010 §15 OQ1/OQ4 | RFC-0010 §15 OQ1 |
| The provider-failure reaction: retry with backoff, fallback chain, degraded mode → Awaiting Input (facts-only) | RFC-0002 §10; RFC-0010 §8 | RFC-0002 §10 |
| The routing of provider-originated and Skill-originated Proposals into the Policy/Approval gate and the Executor | RFC-0008 §5, RFC-0004 A3; `core`, Iteration 11 | RFC-0008 §5 |
| The audit writes of provider/skill events (loading, activation, execution, failure, trust revocation) | RFC-0013 §23; RFC-0002 invariant 13; `core`, Iteration 11 | RFC-0011 §16; RFC-0013 §23 |
| The first vendor adapter (HTTP/SDK translation), the packaging format, the signing scheme, and the version encoding | RFC-0020 (implementation); RFC-0017 (compatibility); RFC-0010 §15 OQ6; RFC-0011 §19/§30 OQ1 | RFC-0010 §15 OQ6; RFC-0011 §19 |
| Skill sandboxing mechanics (isolated environments, capability declarations, or both) | RFC-0020; RFC-0011 §17/§30 OQ2 (RFC-0001 Q21) | RFC-0011 §30 OQ2 |
| The skill review process and trust ratings (declared vs. actual risk) | The skill ecosystem work, finalized post-MVP (RFC-0000 §5); RFC-0001 Q20/Q22 | RFC-0011 §30 OQ3 |
| The skill registry/distribution, marketplace, and fetching under default-deny | The ecosystem work; RFC-0008's network policy (RFC-0001 Q23) | RFC-0011 §30 OQ4 |
| Skill enablement/preference configuration and cost controls | RFC-0016 | RFC-0011 §30 OQ6 |
| Cross-version migration across skill/fact-model/provider contracts | RFC-0017 | RFC-0011 §30 OQ7 |
| The RFC-0010 §17 / RFC-0011 §32 vocabulary additions to RFC-0003 Part I (Provider Contract, Provider Capability, Capability Declaration, Capability Negotiation, Provider Lifecycle, Fallback Chain, Provider Refusal, Provider Failure, Degraded Mode (contract sense); Skill Contract, Skill Manifest, Skill Capability, Skill Dependency, Skill Precondition, Skill Postcondition, Skill Verification Approach, Skill Isolation, Skill Composition, Skill Registry) | RFC-0003 Part II amendment process; a docs change, not this scaffold | RFC-0010 §17; RFC-0011 §32 |

### 1.3 What exists already

The `providers` package (`{__init__,contract,view}.py` + `adapters/`) and the
`skills` package (`{__init__,loader,activation,runtime}.py`) were scaffolded in
Iteration 0 with ownership docstrings only (blueprint §2); `tests/test_packages.py`
already imports and docstring-checks them (the `providers` module list is
`["contract", "view", "adapters"]`; the `skills` module list is `["loader",
"activation", "runtime"]`), so the tree test stays green throughout — C1–C4
**fill** the stubs, they do not create modules. `tests/test_dependency_rules.py`
already declares `ALLOWED["providers"] = {"schema", "trust", "context"}`,
`ALLOWED["skills"] = {"schema", "collectors", "trust", "policy", "factlayer"}`,
`FORBIDDEN["providers"] = {"factlayer", "executor", "policy", "verification",
"audit", "secrets"}`, and `FORBIDDEN["skills"] = {"executor", "verification",
"audit", "secrets"}` plus the use-restriction qualifiers (skills imports
`policy`/`factlayer` *types* only — "policy (decision)" and "factlayer (create)"
are use limits, not import bans). The `context` package (Iteration 9) already
builds the Provider View (`provider_view.py`) that `providers` imports and
consumes (blueprint §4.1; PR14). Baseline suite: **2285 tests, green**, branch
`iteration/9-context`, HEAD `f921d60` (Iteration 9 closeout), working tree
clean; branch `iteration/10-providers-skills` created from `f921d60`.

---

## 2. RFC consistency review

| RFC | Section | Implemented as | Status in layer |
|---|---|---|---|
| RFC-0010 | §0 Purpose | Three consequences: the Core depends only on the Provider Contract; providers are strong or weak, never good or bad (capability negotiation, §6); provider output is untrusted data (RFC-0004 A1; RFC-0007 §6.5) | Implemented (C1/C2, structural) |
| RFC-0010 | §1 Design Principles | Nine determinism principles: provider independence, capability-based design, deterministic Core, untrusted output, graceful degradation, no vendor-specific assumptions, minimal contract, safety not negotiable by capability, Core is the only route, replacement is the test | Implemented (C1/C2/C5, DoD) |
| RFC-0010 | §2 Provider Responsibilities | Receive the View; generate Proposals/Explanations; return structured results; answer questions; signal inability. Never: execute, classify authority, create Facts, verify, approve, escalate, store secrets, modify policy | Implemented (C1/C2, structural) |
| RFC-0010 | §3 Provider Inputs | The Provider View is the *only* input — built by `context` (Iteration 9), consumed here; no raw output, no Audit, no secrets, no provider identity, no machine identity beyond need | Consumed (C2: `view.py` consumes the View type; PR14) |
| RFC-0010 | §4 Provider Outputs | The finite structured outputs (Proposal, Explanation, Questions, Clarifications, Alternative Plans, Refusal, Failure, Need More Evidence); structured, advisory always; a Proposal carries its expected effect; inability is first-class; nothing is executed from output | Implemented (C1: `contract.py` validates; Q4) |
| RFC-0010 | §5 Capability Model | Capabilities are declared, not assumed; eight capabilities; no capability implies permission | Implemented (C2: capability vocabulary + declaration, Q3) |
| RFC-0010 | §6 Capability Negotiation | The Core adapts to declared capabilities deterministically (simplify, break down, structured-responses fallback, never pretend; never shape behavior by vendor) | Implemented (C2, mechanics); the consultation use is `core`'s (Q3) |
| RFC-0010 | §7 Provider Lifecycle | Registration → Selection → Activation → Use → Failure → Replacement → Removal; registration declares, validation confirms; fallback chains are Core-side; degraded mode is designed; no bypass; removal leaves no residue | Boundary (C2: registration/activation/removal mechanics; selection + fallback RFC-0016/`core`, Q3) |
| RFC-0010 | §8 Failure Model | Seven failure modes with Core reactions; failures are Core events; hallucination contained; malformed never a Fact; no infinite retry; refusal respected | Implemented (C1/C2: deterministic classification to the §4.3 events; reactions `core`'s, Q5) |
| RFC-0010 | §9 Multi-provider Philosophy | Coexistence transparent; providers never see each other; one contract, many implementations; wiring is RFC-0016's (Post-MVP) | Recorded (Q3; RFC-0016) |
| RFC-0010 | §10 Security Boundary | The Provider boundary is a security boundary; the provider cannot execute/approve/verify/create Facts/escalate/store secrets/modify policy/bypass approval/reach the machine | Implemented (C1/C2/C5, boundary tests) |
| RFC-0010 | §11 Context Boundary | The provider receives only the Provider View; never Audit, secrets, raw output, or anything past the purpose limit; leakage is a security incident | Implemented (C2, PR14/SC3, DoD) |
| RFC-0010 | §12 Provider Replacement | Swapping a provider requires zero Core changes; a replacement changes only the adapter; the rule is testable (PR15) | Implemented (C5: PR10/PR15 conformance, Q10) |
| RFC-0010 | §13 PR1–PR16 | The normative invariant suite — the package's conformance oracle | Oracle (C5) |
| RFC-0010 | §15 OQ1 | Provider selection/profiles → RFC-0016 (Post-MVP) | Recorded (Q3) |
| RFC-0010 | §15 OQ5 | Skill-provider interaction → RFC-0011 | Recorded (Q8) |
| RFC-0010 | §15 OQ6 | Adapter implementation → RFC-0020 | Recorded (Q2/Q9) |
| RFC-0011 | §0 Purpose | A Skill is a packaged, versioned, authenticated procedure; safety comes from the gate, not the Skill's identity | Implemented (C3/C4, structural) |
| RFC-0011 | §1/§2 What is / Why Skills Exist | A procedure, not a program; capability without modification; a deterministic source of Proposals (degraded mode) | Implemented (C3/C4, structural) |
| RFC-0011 | §3 Skill Ownership | Content → the author; authentication → the Skill Registry; review → the review process; policy → Policy Engine; execution → Executor; lifecycle → Orchestrator/Skill Runtime. No one owns a Skill as a unit of authority | Implemented (C3/C4; Q6 registry role) |
| RFC-0011 | §4 Skill Authority | No authority: cannot execute/approve/create Facts/verify/escalate/modify policy/reach the machine; the only output is a Proposal | Implemented (C4, SK4, structural) |
| RFC-0011 | §5 Skill Trust Class | Untrusted by default; Conditional after authentication; metadata Conditional, code stays Untrusted; mismatch → Untrusted; localness grants no trust | Implemented (C3, SK5, DoD) |
| RFC-0011 | §6 Skill Boundaries | Execution, Truth, Authority, Verification, Secrets, Policy, LLM path, Audit — a Skill never crosses them | Implemented (C3/C4/C5, boundary tests) |
| RFC-0011 | §7 Skill Responsibilities | Declare the surface up front; bundle diagnostics/explanations/gated Actions; declare Preconditions/Postconditions/verification approach; stay within the surface; signal inability | Implemented (C3/C4, Q6) |
| RFC-0011 | §8 Skill Capabilities | Six capabilities; declared, validated, revoked on mismatch; no capability implies permission | Implemented (C3, Q6) |
| RFC-0011 | §9 Skill Dependencies | Declared, directional, never circular; may never depend on another Skill's runtime state, a specific Provider, a specific session, or Core internals | Implemented (C3/C5, structural) |
| RFC-0011 | §10 Skill Failure Philosophy | Fail loud, fail small, fail safe; SKILL_UNAVAILABLE; no unauthenticated substitution; bounded retry; audited | Implemented (C3, SK15; the reaction is `core`'s, Q7) |
| RFC-0011 | §11 Skill ↔ Diagnostics | A Skill bundles Collectors; the Diagnostics Layer runs them; Observations become Facts in the Fact Layer; the Skill owns only the bundle | Boundary (C3: validates declared Collectors against the registry; the run is `collectors`') |
| RFC-0011 | §12/§13 Pre/Postconditions | Declared up front, revalidated at the gate, never waivable; Postconditions declared before execution, drive verification, never the verdict | Implemented (C4: runtime.py rejects incomplete proposals, SK11/SK12) |
| RFC-0011 | §14 Verification Responsibilities | A Skill declares its verification approach; it never performs verification | Implemented (C4, SK6, structural) |
| RFC-0011 | §15 Skill ↔ Secrets | No secrets in Skill content; no secrets to Skills; no path to the secret store; output sanitized before Context | Implemented (C3/C5, SC5, DoD) |
| RFC-0011 | §16 Skill ↔ Audit | A Skill is an audit subject, never an editor; every Skill event recorded; identity recorded; declared-vs-actual audit is a record | Boundary (C3/C4 emit events; the write is `core`'s, RFC-0013 §23) |
| RFC-0011 | §17/§18 Isolation + Composition | Isolation is a boundary, not a privilege (mechanics RFC-0020's); composition declared, version-pinned, acyclic | Recorded (C5: no cross-touch asserted; mechanics RFC-0020's, Q9) |
| RFC-0011 | §19 Versioning/Compatibility/Deprecation | Versions immutable, signed; compatibility lives with the Core's contracts; deprecation is a Core-visible state | Boundary (C3: version + signature carried on the manifest; concrete scheme RFC-0017/0020's, Q6) |
| RFC-0011 | §20 Skill ↔ Providers | A Skill consumes the Provider Contract, never a vendor; a deterministic Skill needs no Provider; Skill code never enters the LLM path except sanitized; no bidirectional trust; the View a Skill may request is the same bounded View | Recorded (Q8; no direct edge per blueprint §4.1) |
| RFC-0011 | §21 Skill ↔ Core | The Core and a Skill meet at exactly one point: the Skill Contract; the Core's rules never bend for a Skill | Implemented (C3/C4, structural) |
| RFC-0011 | §22 Skill Loading | Read the declared surface; authenticate signature and provenance; validate the declaration; check Policy before activation; register with the Core; deterministic, no side effects | Implemented (C3, SK5, DoD) |
| RFC-0011 | §23 Skill Activation | Per-session and reversible; Policy-gated; grants no authority; unauthenticated never substituted; audited | Implemented (C3, activation lifecycle; Q7) |
| RFC-0011 | §24 Skill ↔ Approval | Skill Actions pass the exact same gate; no unit approval; no skill-based shortcut; classification uses structure; blocked Actions follow the same override rules | Implemented (C4, SK4, DoD) |
| RFC-0011 | §25 Skill ↔ Verification | Verified exactly like any Action; never the comparison; normal Outcome; failure re-opens planning | Recorded (Q7; the wiring is `core`'s) |
| RFC-0011 | §26 Skill ↔ Context | Skill text is untrusted text, sanitized and bounded before Context; code never enters Context or the View | Boundary (C3/C5; the pre-entry sanitization is `context`'s, Iteration 9) |
| RFC-0011 | §28 SK1–SK16 | The normative invariant suite — the package's conformance oracle | Oracle (C5) |
| RFC-0011 | §30 OQ1/OQ2 | Packaging/signing and sandboxing mechanics → RFC-0020/RFC-0017 | Recorded (Q6/Q9) |
| RFC-0002 | §4.3 Provider events | PROVIDER_RESPONSE / REFUSAL / UNAVAILABLE / TIMEOUT / FALLBACK_OK / FALLBACK_FAILED — the event vocabulary the provider package's failure classification produces | Implemented (C2, Q5) |
| RFC-0002 | §4.7 System events | SKILL_UNAVAILABLE — a Skill that cannot be loaded/authenticated is refused, never substituted | Implemented (C3, SK5/SK15; the event's reaction is `core`'s) |
| RFC-0002 | §5 The Session Loop | Diagnosis and Planning consult "a Provider (LLM) or a Skill"; the Core is the conductor | Boundary (C1–C4 build the mechanics; the consultation is `core`'s, §1.2) |
| RFC-0002 | §6 Component Consultation Rules | LLM (via Providers) in Diagnosis/Planning/Replanning only after a fresh Context Building, never with raw output or secrets; Skills in Diagnosis/Planning/Machine Inspection, authenticated before use, never bypassing the gate; Context never feeds the LLM directly | Boundary (C1–C4; the consultation edges are `core`'s, §1.2) |
| RFC-0002 | §9 invariants 4, 5, 7 | LLM only through a provider view (I-4); no untrusted text interpolated into a command (I-5, covers Skill content); risk classification never the LLM's self-report (I-7) | I-4 at C2 (the View is the only input, PR14); I-5/I-7 structural (C1/C4) |
| RFC-0002 | §10 Provider failure | Retry with backoff → fallback chain → degraded mode → Awaiting Input facts-only; never fabricate | Boundary (C2 classifies failures; the reaction is `core`'s, Q5) |
| RFC-0002 | §11 Q11 | Degraded-mode scope → RFC-0010 (§7.3, PR16): facts-only, deterministic skills run, no recommendations | Recorded (C2, PR16) |
| RFC-0004 | §4.4 Provider | Propose/Infer/Explain only; trusts nothing about the machine; depends on the Provider View | Implemented (C1/C2, the package's profile) |
| RFC-0004 | §4.10 Skills | Propose/Infer/Explain as candidates; never bypasses Policy (S1); depends on RFC-0011, RFC-0008, RFC-0005 | Implemented (C3/C4, the package's profile) |
| RFC-0004 | §7 matrix | Provider and Skills rows: Observe F, Propose A, Infer A, Verify F, Approve F, Execute F, Refuse F, Persist F, Explain A | Implemented (C1/C4/C5, boundary tests) |
| RFC-0004 | A1, A3, A8, A9 | Provider never executes; Skill never bypasses Policy; authority flows downward; the gate is the only path to execution | Implemented (C1/C4, DoD) |
| RFC-0001 | §5 Providers / Skills | One uniform interface; normalize and validate output; untrusted; report errors; validate/version/authenticate packages; isolate instructions; declare risk profile | Implemented (C1–C4, DoD) |
| RFC-0001 | §7, §8 | Untrusted output boundary; provider world separate from the machine world; every path through the gate | Implemented (C5, PR10/PR15, Q10) |
| RFC-0001 | §11 The two extension axes | Skills extend what the Assistant can do; Providers extend how it thinks; new providers implement the contract | Recorded (Q8, §2) |
| RFC-0001 | §12 Q16–Q18, Q26 | Provider variance/minimum capability, provider-agnostic representation, outages/refusals/degraded UX, cost controls | Answered by RFC-0010; cost controls RFC-0016's (Q3) |
| RFC-0001 | §12 Q19–Q22 | Skill packaging/versioning/signing, review, sandboxing, declared-vs-actual audit | Answered by RFC-0011; mechanics RFC-0017/0020, ecosystem post-MVP (Q6/Q9) |
| RFC-0007 | T4, §4.6, §4.8, §6.5 | Provider output and Skill content are untrusted until processed; conditional trust for Skills after authentication; injection contained | Implemented (C1/C3, boundary tests) |
| RFC-0008 | §5 | The gate's input is the Proposal; incomplete Proposals rejected; no unit approval | Implemented (C1/C4: expected-effect rule, SK11) |
| RFC-0012 | §13, §27 | The View is the only channel (PR14); provider replies are labeled material, never Facts; skill material sanitized at the enforcement point | Consumed (C2/C3; `context` owns the View and the enforcement point, Iteration 9) |
| RFC-0009 | SC3, SC5 | No secret in the Provider View; no secret reaches a Skill | Implemented (C2/C3/C5, boundary tests, DoD) |

**Already resolved by the corpus (not re-opened here):**

- **A Provider has Propose/Infer/Explain and nothing else.** Observe/Verify/
  Approve/Execute/Persist are all F in the matrix (RFC-0004 §7); there is no
  execution path across the Provider boundary (A1; RFC-0010 §2). Not a question.
- **A Skill has the same authority as a candidate.** Propose/Infer/Explain;
  never executes, never approves, never verifies (RFC-0004 §7; RFC-0011 §4).
  Not a question.
- **Every Skill Action passes the exact same gate; no unit approval exists**
  (A3; SK4; RFC-0008 §5). Classification uses structure, never Skill content.
  Not a question.
- **The Provider View is the only input a provider receives, and the only
  channel outward** (PR14; RFC-0010 §3, §11; RFC-0002 invariant 4). `context`
  builds it (Iteration 9, DN-68); `providers` consumes it. Not a question.
- **Provider output is untrusted data and never a Fact** (F6; RFC-0005; RFC-0010
  §2; PR3). A malformed output is rejected, never interpreted into validity
  (PR13). Not a question.
- **No secret ever reaches a provider or a Skill** (SC3/SC5; RFC-0010 §11;
  RFC-0011 §15; PR8/SK8), and neither package may import `secrets` (blueprint
  §4.2). The boundary is tested by injection, not by a secrets import. Not a
  question — the *mechanism* is the Q10 resolution.
- **No vendor knowledge lives in the Core** (PR10); replacing a provider changes
  only the adapter (PR15; RFC-0010 §12). The provider package is the sole
  vendor-facing surface. Not a question.
- **Skills are untrusted until authenticated; an unauthenticated Skill is never
  loaded or substituted** (SK5; RFC-0002 §4.7; RFC-0001 §11.5). Not a question.
- **Provider failure degrades, never crashes** (PR11; RFC-0002 §10): retry with
  backoff → fallback chain → degraded mode → Awaiting Input facts-only, no
  recommendations (PR16; RFC-0002 Q11 → RFC-0010 §7.3). Not a question.
- **Skills and Providers are separate extension axes with no direct package
  edge** (RFC-0001 §11.2; blueprint §4.1: `skills` allowed = {schema, collectors,
  trust, policy, factlayer}; `providers` allowed = {schema, trust, context}). A
  Skill consumes the Provider Contract, never a vendor (RFC-0011 §20.1). Not a
  question.
- **Skill code never enters the Provider View or the LLM path; skill text enters
  only sanitized** (SK13; RFC-0007 §6.12; RFC-0011 §26). Not a question.
- **The per-vendor adapter, the packaging format, the signing scheme, and the
  sandboxing mechanics are RFC-0020's/RFC-0017's, not this layer's** (RFC-0010
  §15 OQ6; RFC-0011 §30 OQ1/OQ2). Not a question — the *interfaces they serve*
  are the Q2/Q6/Q9 resolutions.

---

## 3. Layer placement

`providers` and `skills` both sit at **Layer 5** (blueprint §4.1), beside each
other and above `context`/`executor`/`audit` (Layer 4). Their imports reach only
downward to Layers 0–4; nothing below Layer 5 imports them except the qualified
readers in blueprint §4.2 (`executor` and `verification` may not import them —
those edges are forbidden; `core` imports everything, per §4.1). `providers`
consumes `schema`, `trust`, and `context`; `skills` consumes `schema`,
`collectors`, `trust`, `policy`, and `factlayer`.

- **`providers → context`** is the Provider View edge: the provider consumes the
  View type built by the Context Manager (Iteration 9, `provider_view.py`) — the
  only input (RFC-0010 §3; PR14). This is the one edge that makes Layer 5 depend
  on Layer 4 and justifies the DN-45 re-order (`providers` precedes `core`).
- **`providers → trust`** is the untrusted-data edge: provider output arrives
  with the T4 untrusted trust class and is never upgraded by the package
  (RFC-0010 §2; RFC-0007 T4; F6).
- **`providers → schema`** is the vocabulary edge: the structured outputs
  (Proposal, Explanation, Questions, Clarifications, Alternative Plans, Refusal,
  Failure, Need More Evidence) and expected-effect labels are expressed in the
  canonical types (RFC-0008 §5; RFC-0003 Part I).
- **`skills → policy`** is the gate edge (types only): every Skill Action passes
  the same classification and gate as any Action (RFC-0004 A3; SK4; RFC-0008 §5);
  the "policy (decision)" qualifier means `skills` uses the classification *types*,
  never a decision path.
- **`skills → collectors` / `factlayer`** is the Collector-bundle edge: a Skill
  bundles Collectors (RFC-0011 §11) and consumes Facts; `factlayer` types are
  referenced for Collectors, never to author Facts (RFC-0011 §4.3; F6).
- **No `providers → skills` or `skills → providers` edge.** The two extension
  axes are separate (RFC-0001 §11.2); the provider↔skill interaction (RFC-0011
  §20) is realized through `core`/`schema`/`context`, not by an import (Q8).
- **No `providers → secrets` or `skills → secrets` edge.** Neither receives a
  secret (SC3/SC5); the no-secrets boundary is asserted by injection tests, not
  by a secrets import (blueprint §4.2; Q10).
- **No `providers → policy`/`executor`/`verification`/`factlayer`/`audit`
  edge.** The provider may not classify, execute, verify, create Facts, or see
  the Audit (RFC-0010 §2, §10; PR14; RFC-0002 §6 "never consulted in
  Inspection/Executing/Verification").

---

## 4. Ownership map

Each package has exactly one owner per row (RFC-0004 §3; blueprint §10): the
*authority* is owned by RFC-0004 §4.4 (Provider profile) / §4.10 (Skills profile)
and the *contract* by RFC-0010 (Provider Contract) / RFC-0011 (Skill Contract) —
two distinct properties, one owner each, exactly as blueprint §10's two-owner
check describes. Module-level ownership:

| Module | Owning RFC sections | Protected by |
|---|---|---|
| `providers/contract.py` | RFC-0010 §4, §8; RFC-0008 §5 | PR13 (malformed rejected), PR2/PR3/PR6 (no authority/Facts/verification), PR11 (degrades, never crashes), F6; RFC-0002 invariant 4 |
| `providers/view.py` | RFC-0010 §3, §5, §7; RFC-0012 §13, §27 | PR14 (the View is the only channel), SC3 (no secret in the View), PR8 (never stores secrets), PR10 (no vendor), RFC-0002 invariant 4 |
| `providers/adapters/` | RFC-0010 §1, §12; RFC-0010 §15 OQ6 | PR15 (replacement changes only the adapter); per-vendor translation is RFC-0020's (Q2/Q9) |
| `skills/loader.py` | RFC-0011 §3, §22; RFC-0001 §11.2; RFC-0002 §4.7 | SK5 (untrusted until authenticated), SK8 (no secrets), SK15 (failure degrades), SK16 (removal needs no Core change); RFC-0011 §19 |
| `skills/activation.py` | RFC-0011 §23; RFC-0008 | SK5 (Policy-gated activation), SK9 (isolated), SK15; RFC-0002 §4.7 (no unauthenticated substitution) |
| `skills/runtime.py` | RFC-0011 §4, §12, §13, §24; RFC-0004 A3 | SK4 (every Action passes the gate), SK11 (declared Pre/Postconditions), SK12 (never waivable), SK14 (never modifies Audit); RFC-0002 invariant 5 |

**Two-owner checks.** (a) *Provider authority vs. contract:* RFC-0004 §4.4 owns
the *authority* (Propose/Infer/Explain only; the matrix row); RFC-0010 owns the
*contract* (inputs, outputs, capabilities, lifecycle, failure, PR1–PR16) — one
package, two properties, one owner each (blueprint §10's `providers` = RFC-0004
profile + RFC-0010 contract). (b) *Skill authority vs. contract:* RFC-0004 §4.10
owns the *authority* (a candidate; S1 "never bypass Policy"); RFC-0011 owns the
*contract* (surface, lifecycle, Pre/Postconditions, gate, SK1–SK16). (c)
*Lifecycle ownership vs. consultation:* RFC-0010 §7/RFC-0011 §23 own the
*lifecycle mechanics* (registration, activation, removal); RFC-0002 §5/§6 own
the *consultation* (when the loop calls a provider or a Skill) — mechanics here,
wiring in `core` (Q3/Q7). (d) *Failure classification vs. reaction:* RFC-0010 §8
owns the *classification* of the seven failure modes; RFC-0002 §10 owns the
*reaction* (retry → fallback → degraded) — classification here, reaction in
`core` (Q5).

**Authority boundaries.** Both packages hold **Propose**, **Infer**, and
**Explain** — and nothing else (RFC-0004 §7, Provider and Skills rows). Neither
package ever Observes the machine, Verifies, Approves, Executes, or Persists;
each "may never decide: what is true; what to do; to include a secret; that its
output is safe" (RFC-0010 §2; RFC-0011 §4). The layer validates, loads,
activates, and gates; it decides neither truth nor action.

---

## 5. Dependency analysis

**Allowed** (blueprint §4.1; already enforced by `tests/test_dependency_rules.py`):

| Edge | Why allowed |
|---|---|
| `providers → schema` | The canonical vocabulary the contract's structured outputs and expected effects are expressed in (Proposal, Explanation, Questions, Refusal, Failure, Need More Evidence; RFC-0008 §5; RFC-0003 Part I) |
| `providers → trust` | Provider output arrives untrusted (RFC-0007 T4, §4.6) and the package never upgrades its trust class (RFC-0010 §2; F6) |
| `providers → context` | The provider consumes the Provider View type (RFC-0010 §3; PR14); the View is the only input (RFC-0002 invariant 4; RFC-0012 §13, §27) |
| `skills → schema` | Skill Actions and Plans are expressed in the canonical types; Preconditions/Postconditions in the fact model's vocabulary (RFC-0006 §4/§5; RFC-0011 §12/§13) |
| `skills → collectors` | A Skill bundles Collectors (RFC-0011 §11); the Diagnostics Layer runs them (RFC-0004 §4.5) |
| `skills → trust` | Skill content is untrusted by default, Conditional after authentication (RFC-0007 §4.8; RFC-0011 §5) |
| `skills → policy` (types) | Every Skill Action passes the same classification and gate (RFC-0004 A3; SK4; RFC-0008 §5); `skills` uses the classification types, never a decision path (blueprint §4.2 qualifier) |
| `skills → factlayer` (types) | A Skill consumes Facts and bundles Collectors; `factlayer` types are referenced, never to author Facts (RFC-0011 §4.3; F6; blueprint §4.2 qualifier) |

**Forbidden** (blueprint §4.2): `providers` may not import `factlayer` (may not
create Facts, F1/F6), `executor` (may not execute), `policy` (may not classify
authority), `verification` (may not verify), `audit` (never receives the Audit,
PR14), or `secrets` (never receives secrets, SC3; RFC-0010 §10, §11). `skills`
may not import `executor` (may not execute), `verification` (may not verify),
`audit` (may not modify it, SK14), or `secrets` (SC5), and its `policy`/`factlayer`
imports are use-limited to types (no decision path, no Fact authorship; blueprint
§4.2). Notably: **no `providers → skills` or `skills → providers` edge** even
though RFC-0011 §20 specifies their interaction — the interaction is realized by
`core` through `schema`/`context`, never by an import (Q8); and **no `providers
→ secrets` edge** even though SC3 is a DoD item — the no-secrets property is
asserted by boundary injection, never by importing the classifier (Q10).

**Latent edges.** `skills → collectors`/`factlayer` are consumed for the
Collector-bundle validation (RFC-0011 §11) and Fact consumption; `skills → policy`
is the type-level gate edge. `providers → context` is the one new edge this
iteration exercises that Layer 4 did not import back (mirroring how `cli` and
`core` are the only other qualified readers of `context`).

---

## 6. Public surface analysis

The planned public surface is **reported**, not ratified; final signatures are
RFC-0020's (DN-1). The shape below is what C1–C4 will build. Both packages are
value-free and import-safe beyond their own surfaces; validation, lifecycle, and
gate mechanics are pure functions that perform no I/O, no network call, no
subprocess, and no provider/skill execution (the run-primitive precedent of
Iteration 8, DN-55).

`providers/contract.py`

- The structured-output validation surface (Q2): for each of the finite §4
  outputs (Proposal, Explanation, Questions, Clarifications, Alternative Plans,
  Refusal, Failure, Need More Evidence), a deterministic validator over the
  `schema` types — a Proposal is not complete without its expected effect
  (RFC-0010 §4 rule 2; RFC-0008 §5), so an incomplete proposal is rejected
  (PR13), never interpreted into validity, never classified, and never a Fact
  (F6; PR2/PR3/PR6).
- The failure-classification surface (Q5): a deterministic translator from the
  §8 failure modes (Timeout, Unavailable, Malformed output, Incomplete proposal,
  Unsupported capability, Hallucination, Refusal) to the RFC-0002 §4.3 event
  vocabulary (PROVIDER_RESPONSE / REFUSAL / UNAVAILABLE / TIMEOUT /
  FALLBACK_OK / FALLBACK_FAILED), so a failure degrades and never crashes
  (PR11); the reaction (retry/fallback/degraded) is `core`'s (§10).
- Never returns a truth verdict (PR3); never executes, approves, or verifies
  (RFC-0010 §2); never accepts instructions (RFC-0001 §7).

`providers/view.py`

- The Provider View consumer (RFC-0010 §3): consumes the View type built by
  `context` (Iteration 9) — the only input and the only channel (PR14); asserts
  at the boundary that nothing beyond the View (no Audit, no secrets, no raw
  output, no provider identity) can reach any provider-visible structure
  (SC3; PR8).
- The capability model (Q3): the eight §5 capabilities as a declared vocabulary;
  registration stores the declaration as facts; no capability implies permission
  (§5.4; PR12); negotiation is a deterministic Core adaptation (§6) whose use is
  `core`'s.
- The lifecycle surface (Q3): registration, activation, and removal mechanics
  (§7); selection, fallback chains, and profiles are RFC-0016's (§15 OQ1) and
  the consultation use is `core`'s.

`providers/adapters/`

- Stays a scaffold in Iteration 10 (Q2/Q9): the per-vendor translation between a
  vendor's interface and the Provider Contract is RFC-0020's (§15 OQ6), served
  by the injected-primitive boundary (DN-55 precedent); the package holds no
  vendor name, branch, or behavior (PR10; PR15).

`skills/loader.py`

- The registry + load/authenticate surface (Q6): the Skill Registry's
  authentication role (RFC-0011 §3) as the deterministic loader — read the
  declared surface, authenticate signature and provenance (unauthenticated
  Skills are never loaded; RFC-0002 §4.7; SK5), validate the declaration
  (targets, privileges, risk, capabilities, dependencies, Preconditions,
  Postconditions, verification approach; RFC-0001 §11.3), check Policy before
  activation (RFC-0008), register with the Core — with no side effects and no
  LLM judgment (RFC-0011 §22). The concrete packaging/signing scheme is
  RFC-0017/RFC-0020's (§30 OQ1); the version and signature are carried on the
  manifest now (§19).
- Bundled Collectors are validated against the `collectors` registry (RFC-0011
  §11); the Skill never inspects the machine itself.

`skills/activation.py`

- The activation lifecycle (Q7): per-session and reversible (RFC-0002 §2.2),
  Policy-gated (RFC-0008; SK5), grants no authority (RFC-0011 §4), never
  substitutes an unauthenticated Skill (RFC-0002 §4.7), and emits the auditable
  activation event (RFC-0011 §16; the audit write is `core`'s, RFC-0013 §23).
- An activated Skill still only proposes; activation is not a capability grant.

`skills/runtime.py`

- The gate-participation surface (Q7): every Skill Action passes the full
  classification and approval gate (SK4; RFC-0004 A3), with no unit approval and
  no skill-based shortcut (RFC-0011 §24); classification uses structure, never
  Skill content (RFC-0008 §7; P2).
- Declared Preconditions and Postconditions ride the Action (SK11): a proposal
  with no declared expected effect is rejected (RFC-0008 §5); a Skill cannot
  waive them (SK12); verification is never the Skill's (SK6; RFC-0006 V1).
- The consultation/invocation of a Skill (Diagnosis/Planning/Machine Inspection;
  RFC-0002 §6) and the session scope are `core`'s (Q7).

Nothing else is exported. Each facade re-exports only the owned vocabulary
(blueprint §3); the package surfaces carry no decision path, no execution
surface (RFC-0002 invariants 3, 5), and no I/O.

---

## 7. Boundary analysis

- **Downstream of Context.** The provider consumes the Provider View built by
  the Context Manager (Iteration 9) — the only input (RFC-0010 §3; PR14); it
  never receives raw output, Audit, or secrets (RFC-0010 §11; SC3; PR8). The
  view.py consumer asserts this at the boundary (Q3/Q10).
- **Upstream of the gate.** Provider-originated and Skill-originated Proposals
  are the gate's input, not a bypass (RFC-0008 §5; RFC-0004 A3). The provider
  package validates and returns contract-shaped results; the routing into
  Policy/Approval is `core`'s (Q4/Q7). Skill Actions pass the exact same gate as
  any Action; there is no unit approval (SK4).
- **The no-secrets boundary.** Neither package imports `secrets` (blueprint
  §4.2); SC3 (no secret in the Provider View) and SC5 (no secret reaches a
  Skill) are asserted by injecting secret-shaped values at the View-consumption
  and Skill-loading boundaries and verifying none cross — the boundary-test
  precedent of RFC-0009 §0 and DN-43 (Q10).
- **The vendor boundary.** The provider package is the sole vendor-facing
  surface (RFC-0010 §12); no vendor name, branch, or behavior exists anywhere
  else (PR10); replacement changes only the adapter (PR15). Conformance enforces
  this by scanning the Core for vendor names/branches (Q10).
- **The untrusted-content boundary.** Provider output and Skill content arrive
  untrusted (RFC-0007 T4, §4.8, §6.5) and never gain authority in this layer
  (RFC-0004 §7); Skill text is sanitized before Context by `context` (Iteration
  9) and code never enters the View or LLM path (SK13; RFC-0007 §6.12).
- **The authority boundary.** Both packages are Propose/Infer/Explain only
  (RFC-0004 §7); neither is an execution, approval, or truth input (RFC-0002
  invariants 3, 5, 7). A Skill never modifies Policy (SK7) or Audit (SK14); a
  provider never modifies Policy (RFC-0010 §2; PR9).

---

## 8. Required invariants

Each invariant's normative source, whether the layer can make it hold at its
own surface now, and where the remainder is enforced (mirroring the
layer-boundary precedent of Iterations 5–9).

| Invariant | Normative source | Layer-enforceable now | Enforcement point for the rest |
|---|---|---|---|
| PR1 — Provider never executes | RFC-0010 §13; RFC-0004 A1; RFC-0002 I-3 | **Yes** (C1: the contract surface has no execution path; a boundary test proves no output becomes a command) | — |
| PR2 — Provider never creates authority | RFC-0010 §13; RFC-0004 §7 | **Yes** (C1/C5: output claiming approval grants nothing; no authority path reads it) | — |
| PR3 — Provider never creates Facts | RFC-0010 §13; RFC-0005 F6 | **Yes** (C1: validation never upgrades output to a Fact; F6 conformance) | — |
| PR4 — Provider never bypasses Approval | RFC-0010 §13; RFC-0008 §5 | **Yes, as the surface** (C1: output is a Proposal for the gate, never a command; the gate routing is `core`'s) | `core` (gate wiring), Iteration 11 |
| PR5 — Provider output is advisory | RFC-0010 §13 | **Yes** (C1/C5: no output changes the machine by itself) | — |
| PR6 — Provider never verifies | RFC-0010 §13; RFC-0006 V1 | **Yes** (C1/C5: no success is recorded from output) | — |
| PR7 — Provider never escalates authority | RFC-0010 §13; RFC-0004 A8 | **Yes** (C5: no elevation demand is honored) | — |
| PR8 — Provider never stores secrets | RFC-0010 §13; RFC-0009 SC3 | **Yes** (C2/C5: the View consumer holds no secret and persists nothing) | — |
| PR9 — Provider never modifies policy | RFC-0010 §13; RFC-0004 | **Yes** (C5: policy is unchanged by any output) | — |
| PR10 — The Core knows no vendor | RFC-0010 §13; RFC-0001 §11 | **Yes** (C5: a scan of the Core for vendor names/branches finds none) | — |
| PR11 — Provider failure never crashes the Core | RFC-0010 §13; RFC-0002 §10 | **Yes** (C2: every §8 failure mode is classified to a §4.3 event; a failure test proves the runtime degrades, never exits) | `core` (reaction), Iteration 11 |
| PR12 — No capability implies permission | RFC-0010 §13; RFC-0010 §5 | **Yes** (C2/C5: granting every capability leaves the boundary unchanged) | — |
| PR13 — Malformed output rejected, not interpreted | RFC-0010 §13 | **Yes** (C1: non-contract output yields no result, never coerced) | — |
| PR14 — The Provider View is the only channel | RFC-0010 §13; RFC-0007 T3; RFC-0002 I-4 | **Yes** (C2: the View consumer is the only provider-visible surface; an instrumentation test proves nothing else crosses) | — |
| PR15 — Replacement requires no Core change | RFC-0010 §13; RFC-0010 §12 | **Yes, as conformance** (C5: no Core file or behavior depends on a provider identity); the adapter swap itself is RFC-0020's | RFC-0020 (adapter) |
| PR16 — Degradation is honest | RFC-0010 §13; RFC-0002 Q11 | **Yes, as the event** (C2: FALLBACK_FAILED → degraded event; no recommendation is fabricated) | `core` (degraded mode), Iteration 11 |
| SK1 — A Skill never executes | RFC-0011 §28; RFC-0004 A2/A3 | **Yes** (C4: Skill Actions run only as token-bound, gated Proposals) | — |
| SK2 — A Skill never creates authority | RFC-0011 §28; RFC-0004 A8 | **Yes** (C4/C5) | — |
| SK3 — A Skill never creates Facts | RFC-0011 §28; RFC-0005 F6 | **Yes** (C3/C5: Skill output is material, never Fact) | — |
| SK4 — A Skill never bypasses Approval | RFC-0011 §28; RFC-0004 A3; RFC-0008 §5 | **Yes** (C4: every Action passes the gate; no unit approval) | — |
| SK5 — A Skill is never trusted by default | RFC-0011 §28; RFC-0007 §4.8 | **Yes** (C3: an unauthenticated Skill is refused at load; DoD) | — |
| SK6 — A Skill never verifies | RFC-0011 §28; RFC-0006 V1 | **Yes** (C4: declares the approach, never performs the comparison) | — |
| SK7 — A Skill never modifies Policy | RFC-0011 §28 | **Yes** (C5: policy unchanged by any Skill content) | — |
| SK8 — A Skill never stores secrets | RFC-0011 §28; RFC-0009 SC5 | **Yes** (C3/C5: no secret reaches a Skill; nothing is persisted) | — |
| SK9 — A Skill is isolated from the Core and other Skills | RFC-0011 §28; RFC-0001 §11.4 | **Yes, as conformance** (C5: no cross-touch asserted); the sandbox mechanics are RFC-0020's | RFC-0020 (sandbox) |
| SK10 — Declared-vs-actual match | RFC-0011 §28; RFC-0001 Q22 | **Yes, as the check** (C3: declared surface validated; mismatch revokes trust for the session) | RFC-0020 / ecosystem (audit) |
| SK11 — Actions carry declared Pre/Postconditions | RFC-0011 §28; RFC-0006 V10; RFC-0008 §5 | **Yes** (C4: a proposal with no expected effect is rejected; DoD) | — |
| SK12 — A Skill cannot waive its Pre/Postconditions | RFC-0011 §28; RFC-0006 §4 | **Yes** (C4: revalidation is Core-owned; the Skill cannot bypass it) | `core` (gate revalidation), Iteration 11 |
| SK13 — Skill content never enters the View/LLM path unsanitized | RFC-0011 §28; RFC-0007 §6.12 | **Yes, as the assertion** (C5: Skill code fed to the provider path is blocked); the sanitization is `context`'s | `context` (Iteration 9) |
| SK14 — A Skill cannot modify Audit | RFC-0011 §28; RFC-0004 A7 | **Yes** (C5: no audit edit path) | — |
| SK15 — Skill failure never crashes the Core | RFC-0011 §28; RFC-0001 §10.6 | **Yes** (C3: each failure mode degrades; the event's reaction is `core`'s) | `core` (SKILL_UNAVAILABLE), Iteration 11 |
| SK16 — Replacing/removing a Skill needs no Core change | RFC-0011 §28; RFC-0001 §11.2 | **Yes** (C3/C5: the Core enumerates what is registered; depends on none) | — |
| F6 — Facts are provider-independent | RFC-0005; RFC-0010 PR3 | **Yes** (C1/C3: no package output becomes a Fact) | — |
| SC3 — no secret enters a Provider View | RFC-0009 SC3; RFC-0010 §11; RFC-0007 T7 | **Yes** (C2/C5: boundary injection; the View is secret-free by construction) | — |
| SC5 — no secret reaches a Skill | RFC-0009 SC5; RFC-0011 §15 | **Yes** (C3/C5: boundary injection) | — |
| I-4 — LLM only through a provider view | RFC-0002 §9; RFC-0007 §12 | **Yes** (C2: the View is the only input the provider package exposes) | `core` (§6.2), Iteration 11 |
| I-5 — no untrusted text interpolated into a command | RFC-0002 §9 | **Yes, structurally** (C1/C4: outputs and Actions are sanctioned structures, never shell strings) | — |
| I-7 — risk classification never the LLM's self-report | RFC-0002 §9; RFC-0008 | **Yes, structurally** (C1: the package never classifies risk; classification types are `policy`'s) | `policy` (Iteration 7) |

DoD subset (blueprint §8.10): **PR11, PR14, F6 (providers); SK4, SK5, SC5
(skills)** — all layer-enforceable per the table (PR11/PR16 as the failure→event
classification with the reaction recorded against `core`; SK4/SK11/SK12 as the
gate-surface mechanics with the consultation and revalidation wiring recorded
against `core`), plus the blueprint §7 oracle's PR1–PR16 and SK1–SK16 rows, SC3,
and the no-vendor/no-secrets boundary surfaces. The packages' blueprint §10
coverage rows (`providers/*` = RFC-0010, §2–§8, PR1–PR16/F6/SC3; `skills/*` =
RFC-0011, §4, §22, §23, SK1–SK16/SC5) are satisfied across the layer + the
recorded cross-component obligations (§1.2).

---

## 9. Ambiguities

Each is **reported, not resolved** here; each names the corpus silence that
forces the report and the RFC/decision that owns the answer. Column
"Blocking?" marks whether it elevates to a blocking question in §10.

| # | Subject scope | RFC §/location | Open question | Alternative readings | Governing RFC / note | Blocking? |
|---|---|---|---|---|---|---|
| A1 | Iteration scope / renumbering | blueprint §8.10; DN-45 | Blueprint §8.10 still reads "Iteration 9 — `providers` + `skills`" while DN-45 re-ordered `providers` + `skills` to Iteration 10 (after `context`). This task implements them at Iteration 10; the label is never renumbered (as §8.7/§8.8/§8.9 were). | (a) implement `providers` + `skills` at Iteration 10, recording the supersession as a continuation of DN-45 (b) stop and renumber the blueprint (the blueprint text stands until RFC-0020, the authoritative build order) | DN-45; blueprint §8.10; Iteration 8/9 closeouts | **Yes (Q1)** |
| A2 | Provider contract surface | RFC-0010 §0, §4, §8; RFC-0010 §15 OQ6; RFC-0008 §5 | RFC-0010 is architecture-only ("no HTTP, no REST, no SDKs, no vendor APIs, no JSON schemas, no implementation", §0) and the adapter implementation is RFC-0020's (§15 OQ6). Yet blueprint §8.10's DoD (PR11, PR14, F6) needs the structured-output validation to exist here. What does `contract.py` build now? | (a) the **validation mechanics now**: the finite §4 outputs as validators over `schema` types, the expected-effect rule (RFC-0008 §5), PR13 reject-malformed, PR11 degrade; the per-vendor adapters are RFC-0020's placeholder and `adapters/` stays a scaffold (b) defer validation to RFC-0020 (would leave PR13/PR11/F6 untestable at their owner, violating the blueprint §8.10 DoD) | RFC-0010 §0/§4/§8/§15 OQ6; RFC-0008 §5; DN-1; blueprint §8.10 | **Yes (Q2)** |
| A3 | Provider request lifecycle | RFC-0010 §5, §7, §9; RFC-0010 §15 OQ1; RFC-0002 §5/§6 | RFC-0010 §7 fixes the lifecycle stages and §5 the capability declaration, but §9/§15 OQ1 defer provider *selection, profiles, and wiring* to RFC-0016 (Post-MVP) and the consultation is the runtime's (RFC-0002 §5/§6). Which stages are this layer's, given the fixed module set (`contract.py`, `view.py`, `adapters/`)? | (a) the **mechanics now**: registration (capability declaration stored as facts), activation (usable-check), and removal in `view.py`, with the capability vocabulary; selection and fallback chains RFC-0016's, the Use/consultation wiring `core`'s (b) defer lifecycle wholesale to `core`/RFC-0016 (would leave §7 registration and the capability model untested) | RFC-0010 §5/§7/§9/§15 OQ1; RFC-0002 §5/§6; RFC-0016; DN-1 | **Yes (Q3)** |
| A4 | Provider response ownership | RFC-0010 §4; RFC-0008 §5; RFC-0002 §6 | RFC-0010 §4 makes provider output a finite set of structured results "the Core validates and routes"; RFC-0002 §6 routes each output to its deterministic consumer. Where is the line between provider-side validation and core-side routing? | (a) the **provider package validates** (the §4 outputs, the expected-effect rule) and returns contract-shaped results; **`core` routes** them to classification/Planning/Awaiting Input (RFC-0002 §6); nothing is interpreted into validity here (PR13) (b) the provider package also routes (a `core` responsibility; RFC-0002 §6 is runtime behavior) | RFC-0010 §4; RFC-0008 §5; RFC-0002 §6 | **Yes (Q4)** |
| A5 | Provider error handling | RFC-0010 §8; RFC-0002 §4.3, §10 | RFC-0010 §8 lists seven failure modes with Core reactions; RFC-0002 §4.3 defines the provider-event vocabulary and §10 the recovery order. PR11 (never crashes) and PR16 (honest degradation) are this iteration's DoD. What is the provider package's deterministic half vs. `core`'s reaction? | (a) **classification here, reaction in `core`**: `contract.py`/`view.py` translate the §8 failure modes into the §4.3 events deterministically (Timeout→PROVIDER_TIMEOUT, unavailable→PROVIDER_UNAVAILABLE, malformed→PROVIDER_REFUSAL, etc.); retry-with-backoff, the fallback chain, and degraded mode are `core`'s (§10) (b) the provider package runs the retry/fallback policy itself (a runtime responsibility; RFC-0002 §10) | RFC-0010 §8; RFC-0002 §4.3/§10; RFC-0002 Q3 (bounded retry) | **Yes (Q5)** |
| A6 | Skill registry ownership | RFC-0011 §3, §22; RFC-0001 §11.2; RFC-0002 §4.7; RFC-0011 §19/§30 OQ1 | RFC-0011 §3 assigns authentication to "the Skill Registry (authentication role)" and §22 the load steps, and RFC-0001 §11.2 says the Core "enumerates what is registered" — but there is **no `registry` module** in the scaffolded `skills` package (loader, activation, runtime; blueprint §2), and the concrete packaging/signing scheme is RFC-0017/RFC-0020's (§19, §30 OQ1). Who plays the registry role now? | (a) **`loader.py` is the registry**: the load-and-authenticate boundary — read the declared surface, authenticate signature/provenance (unauthenticated never loaded, RFC-0002 §4.7; SK5), validate the declaration, check Policy before activation, register; the version + signature are carried on the manifest now, the concrete scheme RFC-0017/0020's (b) defer loading to the ecosystem work (would leave SK5/SK15 untestable and §22 unserved) | RFC-0011 §3/§22/§19/§30 OQ1; RFC-0001 §11.2; RFC-0002 §4.7; blueprint §2 | **Yes (Q6)** |
| A7 | Skill invocation boundary | RFC-0011 §23, §24, §25; RFC-0002 §6 | RFC-0011 §23 makes activation per-session, reversible, Policy-gated, and audited; §24 makes Skill Actions pass the exact same gate; but the *consultation* of a Skill (Diagnosis/Planning/Machine Inspection) is the runtime's (RFC-0002 §6) and the session scope is `core`'s. What does the `skills` package build now? | (a) the **mechanics now**: `activation.py` implements the lifecycle (Policy-gated, reversible, audited-event emitting), `runtime.py` the gate participation (SK4, no unit approval, declared Pre/Postconditions, SK11/SK12); the consultation/invocation and session scope are `core`'s (b) defer activation/gate wiring to `core` (would leave SK4/SK11 untestable at their owner) | RFC-0011 §23/§24/§25; RFC-0002 §6/§2.2; RFC-0008 §5 | **Yes (Q7)** |
| A8 | Provider↔skill interaction | RFC-0011 §20; RFC-0010 §15 OQ5; blueprint §4.1 | RFC-0011 §20 answers RFC-0010 §15 OQ5 (a Skill consumes the Provider Contract, never a vendor; deterministic Skills run without a Provider; Skill code never enters the LLM path except sanitized), but there is **no direct package edge** (`skills` allowed = {schema, collectors, trust, policy, factlayer}; `providers` allowed = {schema, trust, context}). How is the interaction realized at Layer 5? | (a) **recorded as cross-component for `core`**: both axes are consumed by `core` through `schema`/`context` (RFC-0001 §11.2); the §20 rules become boundary obligations (deterministic-skill degraded mode; SK13 sanitization asserted at the boundary); no new edge, no coupling (b) create a `skills → providers` edge (not in blueprint §4.1; a new dependency is RFC-0020's to define) | RFC-0011 §20; RFC-0010 §15 OQ5; blueprint §4.1; RFC-0001 §11.2 | **Yes (Q8)** |
| A9 | External API boundaries | RFC-0010 §0; RFC-0011 §17, §30 OQ2; DN-1; DN-55 | RFC-0010 §0 defines no HTTP/REST/SDKs and RFC-0011 §30 OQ2 defers sandboxing mechanics to RFC-0020, yet the layer's DoD (PR11, PR14, SK5, SC5) is testable here. What is the external-interface posture at Layer 5? | (a) the **layer performs no I/O**: no network, no subprocess, no filesystem, no vendor call, no skill fetch — everything injected (the DN-55 run-primitive precedent); vendor calls, skill fetch, and sandbox execution are RFC-0020's (b) perform real external calls now (needs vendor SDKs and sandbox mechanics, RFC-0020/0017's) | RFC-0010 §0/§15 OQ6; RFC-0011 §17/§30 OQ2; DN-1; DN-55; RFC-0020 | **Yes (Q9)** |
| A10 | Runtime ownership / no-vendor-knowledge | RFC-0002 §1; RFC-0010 §12, PR10/PR15; blueprint §4.2 | RFC-0002 §1 says the Core must "keep the provider world separate from the machine world"; RFC-0010 §12 makes the provider package the sole vendor-facing surface (PR10) with replacement changing only the adapter (PR15). At Layer 5, with no live provider and no real adapter, how is the separation and the no-secrets DoD (SC3/SC5) enforced when neither package may import `secrets`? | (a) **conformance + boundary injection**: the provider package is the only place a vendor-facing surface may live, enforced by a vendor-scan test (PR10/PR15); SC3/SC5 are asserted by injecting secret-shaped values at the View-consumption and Skill-loading boundaries, with no `secrets` import (blueprint §4.2); the *runtime separation* (who calls the provider) is `core`'s (b) defer PR10/SC3/SC5 to `core`/RFC-0020 (would leave them untested at their owner) | RFC-0002 §1; RFC-0010 §12/PR10/PR15; blueprint §4.2; RFC-0009 SC3/SC5; DN-43 | **Yes (Q10)** |

---

## 10. Blocking questions

| Q | Question | Owner (RFC §) | Blocks | Sev. | Recommended resolution |
|---|---|---|---|---|---|
| Q1 | Iteration scope / renumbering vs blueprint §8.10 (A1) | DN-45; blueprint §8.10 | C0 | Med | **`providers` + `skills` are Iteration 10.** Implement the two packages at Iteration 10 per DN-45's re-order; record the renumbering as a continuation of DN-45's supersession note (as §8.7/§8.8/§8.9 were); the blueprint text stands until RFC-0020 |
| Q2 | Provider contract surface (A2) | RFC-0010 §0/§4/§8/§15 OQ6; RFC-0008 §5 | C1 | High | **Validation mechanics now.** `contract.py` validates the finite §4 structured outputs over `schema` types, applies the expected-effect rule (RFC-0008 §5; incomplete → reject, PR13), and degrades, never crashes (PR11); the per-vendor adapters are RFC-0020's and `adapters/` stays a scaffold (DN-1) |
| Q3 | Provider request lifecycle (A3) | RFC-0010 §5/§7/§9/§15 OQ1; RFC-0002 §5/§6; RFC-0016 | C2 | High | **Lifecycle mechanics now, selection later.** `view.py` implements registration (capability declaration stored as facts), activation (usable-check), and removal, plus the §5 capability vocabulary and the deterministic §6 negotiation adaptation; selection, profiles, fallback chains, and cost controls are RFC-0016's, the consultation use `core`'s |
| Q4 | Provider response ownership (A4) | RFC-0010 §4; RFC-0008 §5; RFC-0002 §6 | C1 | Med | **Provider validates, `core` routes.** `contract.py` returns contract-shaped results and rejects what does not conform (PR13); routing each output to its deterministic consumer (classification, Planning, Awaiting Input) is `core`'s (RFC-0002 §6) |
| Q5 | Provider error handling (A5) | RFC-0010 §8; RFC-0002 §4.3/§10 | C1/C2 | High | **Classification here, reaction in `core`.** The provider package translates the §8 failure modes into the §4.3 event vocabulary deterministically (Timeout→PROVIDER_TIMEOUT, unavailable→PROVIDER_UNAVAILABLE, malformed→PROVIDER_REFUSAL, etc.; PR11/PR16); retry with backoff, the fallback chain, and degraded mode are `core`'s (§10) |
| Q6 | Skill registry ownership (A6) | RFC-0011 §3/§22/§19/§30 OQ1; RFC-0001 §11.2; RFC-0002 §4.7 | C3 | High | **`loader.py` is the registry.** The load-and-authenticate boundary (RFC-0011 §3 authentication role): read the declared surface, authenticate signature/provenance (unauthenticated never loaded, SK5), validate the declaration, check Policy before activation, register; the version + signature ride the manifest now, the concrete packaging/signing scheme RFC-0017/RFC-0020's |
| Q7 | Skill invocation boundary (A7) | RFC-0011 §23/§24/§25; RFC-0002 §6/§2.2; RFC-0008 §5 | C3/C4 | High | **Mechanics here, invocation in `core`.** `activation.py` implements the per-session, reversible, Policy-gated, audited lifecycle; `runtime.py` implements gate participation (SK4, no unit approval, declared Pre/Postconditions, SK11/SK12); the consultation (Diagnosis/Planning/Machine Inspection) and session scope are `core`'s |
| Q8 | Provider↔skill interaction (A8) | RFC-0011 §20; RFC-0010 §15 OQ5; blueprint §4.1 | C4 | Med | **Recorded as `core`'s obligation, no edge.** The §20 rules (a Skill consumes the Provider Contract, never a vendor; deterministic Skills run without a Provider in degraded mode; skill code never enters the LLM path except sanitized, SK13) become boundary obligations asserted at the layer and wired by `core`; no `skills → providers` edge (blueprint §4.1) |
| Q9 | External API boundaries (A9) | RFC-0010 §0/§15 OQ6; RFC-0011 §17/§30 OQ2; DN-1/DN-55 | C1–C4 | High | **I/O-free layer.** Neither package performs network, subprocess, filesystem, vendor, or skill-fetch I/O — everything injected (DN-55 run-primitive precedent); vendor calls, skill fetch, and sandbox execution are RFC-0020's/RFC-0017's |
| Q10 | Runtime ownership / no-vendor-knowledge (A10) | RFC-0002 §1; RFC-0010 §12/PR10/PR15; blueprint §4.2; RFC-0009 SC3/SC5 | C5 | Med | **Conformance + boundary injection.** The provider package is the sole vendor-facing surface, enforced by a vendor-scan test (PR10/PR15); SC3/SC5 are asserted by injecting secret-shaped values at the View-consumption and Skill-loading boundaries, with no `secrets` import (blueprint §4.2); the provider-world/machine-world separation at runtime is `core`'s (Iteration 11) |

**Status: BLOCKED.** Q1–Q10 await Operator ratification. Once ratified, each is
recorded as **DN-75…DN-84** in `docs/implementation-decision-notes.md` before
C0, exactly as Iterations 1–9; the design review §16 readiness flips to READY.

---

## 11. Proposed Decision Notes (DN-75…DN-84)

Proposals for Operator ratification; none took effect by this review. **To be
ratified as DN-75…DN-84 in `docs/implementation-decision-notes.md`** in the
established table form — Status (Ratified, Operator, Iteration 10 ratification) /
Date / Resolves (design review §10 Qn) / Grounding (RFC sections + DN
precedents) / Embodied in (commit) / Decision — mirroring DN-40…DN-74.

| DN | Resolves | Proposal |
|---|---|---|
| DN-75 | Q1 | `providers` + `skills` execute at Iteration 10 per DN-45's re-order; the blueprint §8.10 "Iteration 9 — `providers` + `skills`" label is superseded and stands until RFC-0020 |
| DN-76 | Q2 | `contract.py` validates the finite RFC-0010 §4 structured outputs over `schema` types and applies the expected-effect rule (RFC-0008 §5; incomplete → reject, PR13), degrading never crashing (PR11); the per-vendor adapters are RFC-0020's and `adapters/` stays a scaffold (DN-1) |
| DN-77 | Q3 | `view.py` implements the §7 lifecycle mechanics (registration, activation, removal) and the §5 capability vocabulary with the deterministic §6 negotiation adaptation now; selection, profiles, fallback chains, and cost controls are RFC-0016's, the consultation use `core`'s |
| DN-78 | Q4 | The provider package validates and returns contract-shaped §4 outputs; routing each output to its deterministic consumer (classification, Planning, Awaiting Input) is `core`'s (RFC-0002 §6); nothing is interpreted into validity here (PR13) |
| DN-79 | Q5 | The provider package translates the §8 failure modes into the RFC-0002 §4.3 event vocabulary deterministically (PR11/PR16); retry with backoff, the fallback chain, and degraded mode are `core`'s (§10) |
| DN-80 | Q6 | `loader.py` is the Skill Registry's load-and-authenticate boundary (RFC-0011 §3/§22): read the declared surface, authenticate (unauthenticated never loaded, SK5), validate, check Policy before activation, register; version + signature ride the manifest now, the packaging/signing scheme RFC-0017/RFC-0020's |
| DN-81 | Q7 | `activation.py` implements the per-session, reversible, Policy-gated, audited §23 lifecycle; `runtime.py` implements §24 gate participation (SK4, no unit approval, declared Pre/Postconditions, SK11/SK12); the consultation and session scope are `core`'s |
| DN-82 | Q8 | RFC-0011 §20's provider↔skill interaction (answers RFC-0010 §15 OQ5) is recorded as `core`'s obligation with no direct package edge (blueprint §4.1); deterministic-skill degraded mode and SK13 sanitization are asserted at the boundary |
| DN-83 | Q9 | Both packages are I/O-free — no network, subprocess, filesystem, vendor, or skill-fetch I/O; everything injected (DN-55 precedent); vendor calls, skill fetch, and sandbox execution are RFC-0020's/RFC-0017's |
| DN-84 | Q10 | The provider package is the sole vendor-facing surface (PR10/PR15), enforced by a vendor-scan test; SC3/SC5 are asserted by boundary injection with no `secrets` import (blueprint §4.2); the runtime provider-world/machine-world separation is `core`'s (Iteration 11) |

---

## 12. Atomic implementation plan

Each commit is <300 production LOC, single responsibility, test-visible, on a
branch derived from `f921d60` (`iteration/10-providers-skills`). Commit order
follows ratification of the questions it depends on. Est. = estimated LOC
(impl / test / docs). C1–C4 **fill the Iteration 0 scaffold stubs**
(`contract.py`, `view.py`, `adapters/`; `loader.py`, `activation.py`,
`runtime.py` already exist with ownership docstrings; the tree test stays
green).

| Commit | Message | Content | Est. (impl/test) | Depends on | Deliverable |
|---|---|---|---|---|---|
| C0 | `docs: ratify Iteration 10 design review decisions` | Decision notes for Q1–Q10 (DN-75…DN-84), design review record, renumbering note (Q1), consistency-report note | — / — / ~800 | Q1–Q10 ratified | Ratified plan; all questions answered |
| C1 | `feat(providers): structured output validation (RFC-0010 §4, §8; RFC-0008 §5; PR11, PR13, F6)` | `contract.py`: the finite §4 structured outputs as deterministic validators over `schema` types (Proposal, Explanation, Questions, Clarifications, Alternative Plans, Refusal, Failure, Need More Evidence); the expected-effect rule (a Proposal is incomplete without it → reject, PR13; RFC-0008 §5); no output is a Fact (F6), an instruction, or authority (PR2/PR3/PR6); nothing executes (PR1); degrade, never crash (PR11) | ~270 / ~380 | Q2, Q4 | Structured-output validation |
| C2 | `feat(providers): the Provider View consumer and lifecycle (RFC-0010 §3, §5, §7, §8; RFC-0002 §4.3; PR14, SC3, PR11, PR16)` | `view.py`: consume exactly the Provider View type built by `context` (PR14; RFC-0002 I-4) and assert at the boundary that nothing else crosses (SC3, PR8); the §5 capability vocabulary + declaration and the deterministic §6 negotiation adaptation; the §7 lifecycle mechanics (registration, activation, removal); the §8 failure→§4.3 event classification (Timeout→PROVIDER_TIMEOUT, unavailable→PROVIDER_UNAVAILABLE, malformed→PROVIDER_REFUSAL, etc.; PR11/PR16); selection/fallback RFC-0016's, reactions `core`'s (Q3/Q5) | ~280 / ~380 | Q3, Q5 | View consumption + lifecycle |
| C3 | `feat(skills): load, authenticate, and activate (RFC-0011 §3, §22, §23; RFC-0002 §4.7; SK5, SK8, SK15)` | `loader.py`: the registry load-and-authenticate boundary — read the declared surface, authenticate signature/provenance (unauthenticated never loaded, SK5), validate the declaration (targets, privileges, risk, capabilities, dependencies, Pre/Postconditions, verification approach), check Policy before activation, register; bundled Collectors validated against `collectors`; no side effects, no LLM judgment (RFC-0011 §22); version + signature ride the manifest (§19); `activation.py`: the per-session, reversible, Policy-gated, audited lifecycle (SK5, SK15; no unauthenticated substitution); packaging/signing RFC-0017/0020's (Q6/Q9) | ~280 / ~370 | Q6, Q7 | Loader + activation |
| C4 | `feat(skills): gate participation and declared surface (RFC-0011 §4, §12, §13, §24; RFC-0004 A3; SK4, SK11, SK12)` | `runtime.py`: every Skill Action passes the full classification and approval gate (SK4), no unit approval, no skill-based shortcut (RFC-0011 §24; RFC-0008 §5, P2); declared Preconditions and Postconditions ride the Action (SK11; incomplete → rejected), never waivable (SK12), verification never the Skill's (SK6); the consultation/invocation and session scope are `core`'s (Q7); the §20 provider↔skill rules recorded as `core`'s obligation, no edge (Q8) | ~240 / ~340 | Q7, Q8 | Gate participation |
| C5 | `test(providers, skills): Layer-5 conformance and PR/SK invariant suite` | Conformance (imports limited to `schema`/`trust`/`context` for providers and `schema`/`collectors`/`trust`/`policy`/`factlayer` for skills + sanctioned stdlib, no I/O/no vendor call/no forbidden stdlib, public surface == owned vocabulary, package tree unchanged, no vendor names/branches anywhere else (PR10/PR15), no `skills → providers` edge (Q8)); invariant tests PR1–PR16, SK1–SK16, F6, SC3/SC5, I-4/I-5/I-7; boundary tests: SC3 no-token-in-View, SC5 no-secret-to-Skill, PR14 only-channel, PR11 each failure degrades, PR13 malformed-rejected, PR16 no-fabrication, SK4 gate-required, SK5 unauthenticated-refused, SK11 incomplete-rejected, SK13 code-never-in-LLM-path; cross-component obligations (consultation wiring, gate routing, audit writes, selection/fallback, packaging/signing, sandboxing) recorded against `core`/RFC-0016/RFC-0017/RFC-0020 | 0 / ~620 | C1–C4 | Conformance oracle |
| C6 | `docs: record Iteration 10 completion and providers/skills conformance` | Consistency report + decision notes completion + deferred-items table | — / — / ~220 | C5 | Completion record |

---

## 13. Validation strategy

Same gates as Iterations 1–9: `pytest` (baseline **2285 tests**), `ruff check`,
`ruff format --check`, `python -m build`, and `pre-commit run --all-files`.
Conformance is enforced by the existing `tests/test_dependency_rules.py` (the
`providers` row `ALLOWED["providers"] = {"schema", "trust", "context"}` /
`FORBIDDEN["providers"] = {"factlayer", "executor", "policy", "verification",
"audit", "secrets"}` and the `skills` row `ALLOWED["skills"] = {"schema",
"collectors", "trust", "policy", "factlayer"}` / `FORBIDDEN["skills"] =
{"executor", "verification", "audit", "secrets"}`, plus the use-restriction
qualifiers and the forbidden-source rows) and `tests/test_packages.py` (already
green — the five modules exist as stubs), extended by C5's new
`test_providers_conformance.py`, `test_skills_conformance.py`, and the PR/SK
invariant suites. Because C0–C6 touch neither `rfc/` nor `tools/`, the
RFC-reference validator is not a gate for this iteration (CI still runs it; the
known pre-existing RFC-0004 §470 `'S1'` error is unrelated and unchanged).
Determinism is asserted by property-style tests: the same View input → the same
validated result (RFC-0007 S7); the same declared surface → the same load/activate
outcome; the no-secrets properties (SC3/SC5) are asserted by injecting known
tokens and verifying they appear nowhere in any provider-visible or Skill-visible
structure; the boundary properties (PR14 only-channel, PR11 each-failure-degrades,
PR13 malformed-rejected, SK4 gate-required, SK5 unauthenticated-refused, SK11
incomplete-rejected) are asserted by direct injection. Because the layer is
I/O-free, every external surface (vendor call, skill fetch, sandbox) is injected
at the boundary (Q9; DN-55 precedent) and its absence from the packages is
conformance-enforced.

---

## 14. Definition of Done (per commit)

| Commit | Definition of Done |
|---|---|
| C0 | Q1–Q10 each answered and recorded as decision notes (DN-75…DN-84); the renumbering tension (Q1) recorded; this review's readiness flips to READY |
| C1 | `contract.py` validates exactly the finite §4 outputs over `schema` types (Q2); a Proposal without an expected effect is rejected (RFC-0008 §5; PR13); malformed output yields no result and is never interpreted into validity (PR13); no output is a Fact (F6), an instruction, or authority (PR2/PR3/PR6); nothing executes (PR1); every failure degrades, never crashes (PR11); validation is deterministic (S7) |
| C2 | `view.py` consumes exactly the Provider View type built by `context` — an instrumentation test proves nothing else crosses (PR14/SC3/PR8; RFC-0002 I-4); the §5 capability vocabulary + declaration are present and grant nothing (PR12); the §7 lifecycle mechanics (registration/activation/removal) are implemented with selection/fallback recorded as RFC-0016's (Q3); the §8 failure modes map to the §4.3 events deterministically (Q5; PR11/PR16); the consultation use is recorded as `core`'s |
| C3 | `loader.py` refuses any unauthenticated Skill with no durable artifact (SK5; RFC-0002 §4.7); the declared surface is validated deterministically (targets, privileges, risk, capabilities, dependencies, Pre/Postconditions, verification approach); bundled Collectors are validated against `collectors`; Policy is checked before activation (RFC-0008); no side effects (RFC-0011 §22); the version + signature ride the manifest (Q6); `activation.py` implements the per-session, reversible, Policy-gated, audited lifecycle with no unauthenticated substitution and no authority grant (SK5/SK15; Q7); no secret reaches a Skill (SC5/SK8); concrete packaging/signing recorded as RFC-0017/0020's (Q6/Q9) |
| C4 | `runtime.py` routes every Skill Action through the full classification and approval gate with no unit approval and no skill-based shortcut (SK4; RFC-0011 §24; RFC-0008 §5, P2); declared Preconditions and Postconditions ride every Action (SK11), never waivable (SK12), verification never the Skill's (SK6); no Skill content modifies Policy (SK7) or Audit (SK14); the consultation/invocation and session scope are recorded as `core`'s (Q7); the §20 provider↔skill rules are recorded with no direct edge (Q8) |
| C5 | Blueprint §7 providers/skills rows and §8.10 DoD (PR11, PR14, F6, SK4, SK5, SC5) pass; every layer-enforceable invariant in §8 has a test; conformance: imports limited to the declared allowed sets + sanctioned stdlib, no I/O, no vendor call, no forbidden stdlib, public surface == owned vocabulary, package tree unchanged, no vendor names/branches anywhere else (PR10/PR15), no `skills → providers` edge (Q8); the SC3 no-token, SC5 no-secret, PR14 only-channel, PR11 failure-degrades, PR13 malformed-rejected, PR16 no-fabrication, SK4 gate-required, SK5 unauthenticated-refused, SK11 incomplete-rejected, SK13 code-never-in-LLM-path boundary tests pass; cross-component obligations (consultation wiring, gate routing, audit writes, selection/fallback, packaging/signing, sandboxing) recorded against `core`/RFC-0016/RFC-0017/RFC-0020; full suite green |
| C6 | Consistency report reflects Iteration 10; no orphaned decision notes; the deferred-items table names every §1.2 owner |

**Overall DoD (blueprint §8.10):** PR11 (malformed degrades, never crashes), PR14
(View is only channel), F6 (never a Fact); SK4 (every Skill Action passes the
gate), SK5 (untrusted until authenticated), SC5 (no secret) — all pass; `pytest`
full suite, `ruff check`, `ruff format --check`, `python -m build` all green;
`tests/test_dependency_rules.py` and `tests/test_packages.py` still green (tree
and edges unchanged).

---

## 15. LOC estimates

| Commit | impl | test | docs | Notes |
|---|---|---|---|---|
| C0 | — | — | ~800 | Ratification |
| C1 | ~270 | ~380 | — | Structured-output validation |
| C2 | ~280 | ~380 | — | View consumption + lifecycle |
| C3 | ~280 | ~370 | — | Loader + activation |
| C4 | ~240 | ~340 | — | Gate participation |
| C5 | 0 | ~620 | — | Conformance + invariants |
| C6 | — | — | ~220 | Closeout |
| **Total** | **~1,070** | **~2,090** | ~1,020 | |

Production total ≈ **1,070**; test total ≈ **2,090**. Test LOC may exceed the
300-LOC cap per-commit, as in Iterations 4–9 (the cap applies to implementation
lines). C1 (output validation) and C4 (gate participation) carry the DoD's
conformance weight (PR11/PR13/F6 and SK4/SK11 respectively); C2 (View +
lifecycle) and C3 (load + activate) carry PR14/SC3/PR16 and SK5/SC5.

---

## 16. Readiness assessment

**Status: BLOCKED** pending ratification of Q1–Q10 (to be recorded as decision
notes DN-75…DN-84 before C0), exactly as Iterations 1–9 began. The
highest-leverage questions are **Q2** (the provider contract surface that makes
PR11/PR13/F6 testable without a live vendor), **Q3** (the lifecycle/capability
mechanics that serve §5/§7 before RFC-0016's selection), **Q5** (the
failure→event classification that reconciles PR11/PR16 with `core`'s §10
reaction), **Q6** (the `loader.py` registry role that makes SK5 hold without the
ecosystem), and **Q7** (the activation/gate boundary that makes SK4/SK11 hold
with the consultation in `core`). Once Q1–Q10 are ratified, the layer is
**READY** and commits execute in order C0→C6, each satisfying its §14 DoD before
the next begins. The dominant residual risk is the Draft status of RFC-0010 and
RFC-0011 themselves (§17 risk 1); the layer's load-bearing dependencies are all
Accepted, which bounds it.

---

## 17. Final verdict

This plan is a faithful translation of the frozen corpus into a
providers-and-skills-layer scaffold: **no new architecture is proposed**, every
ambiguity is reported and elevated to a blocking question, no RFC is modified,
no module is invented beyond the scaffolded five (`contract.py`, `view.py`,
`adapters/`; `loader.py`, `activation.py`, `runtime.py`), the allowed/forbidden
dependency graph is honored (including the two new meaningful edges this
iteration exercises — `providers → context` and `skills → policy` — and the
deliberately absent `providers ↔ skills` edge), the two authority rows (Propose,
Infer, Explain for each package) are observed without overlap, and every
layer-enforceable invariant (PR1–PR16; SK1–SK16; F6; SC3/SC5; I-4/I-5/I-7) maps
to a deterministic mechanism and a test. The cross-component obligations (the
consultation wiring, the gate routing of provider- and Skill-originated
Proposals, the audit writes, provider selection and fallback chains, the
packaging/signing scheme, the sandboxing mechanics, the degraded-mode reaction)
are named against `core`/RFC-0016/RFC-0017/RFC-0020 rather than dropped. The
enforcement halves Iteration 9 recorded (the history/turn producers; skill
material production) are now DoD items of this iteration (Q8/Q9), not deferred
again. **Pending ratification: Q1–Q10 are to be recorded as DN-75…DN-84; the
layer is READY for C1.**

---

## Consistency review against the Blueprint and governing RFCs

**Consistent.** Module sets `providers/{__init__,contract,view,adapters}.py` and
`skills/{__init__,loader,activation,runtime}.py` fixed by blueprint §2
(scaffolds already present); dependency rules (`ALLOWED["providers"] = {"schema",
"trust", "context"}`, `ALLOWED["skills"] = {"schema", "collectors", "trust",
"policy", "factlayer"}`, `FORBIDDEN["providers"] = {"factlayer", "executor",
"policy", "verification", "audit", "secrets"}`, `FORBIDDEN["skills"] =
{"executor", "verification", "audit", "secrets"}`, + stdlib, Layer 5) honored by
§3/§5; one-owner discipline (RFC-0004 §3) honored by §4 and the two-owner checks
(authority vs contract; lifecycle mechanics vs consultation; failure
classification vs reaction); the scaffold gate (blueprint §8.0) stands; DN-45's
re-order is now executed (`providers` + `skills` = Iteration 10); DN-43's SC3/SC5
boundary assignment is a DoD item (Q10); DN-55's injected-primitive precedent is
the Q9 reading; DN-1's signatures-are-RFC-0020's precedent is the Q2/Q6 reading;
RFC-0010 §15 OQ1/OQ6 and RFC-0011 §30 OQ1/OQ2 ownership are recorded (§1.2);
RFC-0012 §13/§27's View and skill-material edges are consumed, not rebuilt
(`context`, Iteration 9); RFC-0013 §23 write-point ownership is recorded as
`core`'s obligation (Q8), never invoked here.

**Reported tensions (not violations):**

1. Blueprint §8.10 numbering vs DN-45's re-order — §8.10 still reads "Iteration
   9 — `providers` + `skills`" while this iteration implements them at Iteration
   10 (Q1). Needs ratification as a continuation of DN-45's recorded supersession.
2. RFC-0010 and RFC-0011 are Draft; their normative sections may change before
   acceptance — the rework risk is accepted (DN posture of Iterations 1–9) and
   the layer's Accepted-RFC dependencies bound it.
3. RFC-0010 §0's "no HTTP, no REST, no SDKs, no vendor APIs" vs the adapter the
   blueprint §8.10 Work column mentions ("one vendor adapter") — resolved as
   Q2/Q9: the adapter is RFC-0020's (RFC-0010 §15 OQ6), `adapters/` stays a
   scaffold, and this layer builds the contract the adapter must serve.
4. RFC-0011 §3's "Skill Registry (authentication role)" vs the scaffolded
   module set with no `registry` module — resolved as Q6: `loader.py` plays the
   registry role, with the packaging/signing scheme RFC-0017/0020's.
5. RFC-0011 §20's provider↔skill interaction vs the forbidden `providers ↔
   skills` edge (blueprint §4.1) — resolved as Q8: the §20 rules are `core`'s
   obligation and boundary assertions, never an import (mirroring how Iteration
   9 handled RFC-0004 §9.11's audit-records-vs-forbidden-edge tension).
6. RFC-0010 §8's failure reactions ("fallback chains may engage") vs RFC-0002
   §10's recovery ordering (core) and RFC-0016's selection (Post-MVP) — resolved
   as Q5/Q3: classification here, reaction/selection in `core`/RFC-0016,
   mirroring the layer-boundary precedents of Iterations 5–9.
7. RFC-0009 SC3/SC5 (no secrets to providers/skills) vs the forbidden `secrets`
   import for both packages — resolved as Q10: the no-secrets properties are
   asserted by boundary injection, never by importing the classifier (the DN-43
   boundary-test precedent).
8. RFC-0002 §1's "keep the provider world separate from the machine world" while
   `core` is Iteration 11 — the provider package is the sole vendor-facing
   surface now (PR10/PR15, Q10); the runtime separation is `core`'s, recorded in
   §1.2 (Q3/Q7), exactly as RFC-0002 §6's consultation edges were recorded for
   Iterations 8–9.

**Verdict.** This plan is a faithful translation of the frozen corpus into a
providers-and-skills-layer scaffold; no new architecture is proposed, and every
ambiguity that the corpus does not decide is elevated to a blocking question for
ratification rather than resolved here.

*End of design review. To be ratified as DN-75…DN-84 before C0.*
