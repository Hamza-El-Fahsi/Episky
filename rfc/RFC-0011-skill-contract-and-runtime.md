# RFC-0011 — Skill Contract & Runtime

**Status:** Draft
**Date:** 2026-08-02
**Scope:** The single canonical contract between the Core and every Skill: what
a Skill is and is not, why Skills exist, the Skill lifecycle, ownership,
authority, trust class, boundaries, responsibilities, capabilities,
dependencies, preconditions, postconditions, verification responsibilities,
interaction with the Core and every other component, the loading, activation,
execution, failure, isolation, composition, versioning, compatibility, and
deprecation philosophies, and the Skill invariants
**Audience:** Future maintainers
**Supersedes:** Nothing
**Depends on:** RFC-0001, RFC-0002, RFC-0003, RFC-0004, RFC-0005, RFC-0006,
RFC-0007, RFC-0008, RFC-0010 (accepted in this series). RFC-0009 is referenced
for the no-secrets boundary and RFC-0021 for distro targeting; both are Drafts
and are not dependencies.

**Roadmap note:** This is RFC-0000's "RFC-0011 — Skill System Contract &
Ecosystem" (Extension, Required), the document that fixes the skill *contract*
— what a procedure looks like and how it is gated — which is required before
code, while the *ecosystem* half (registry, review, trust ratings) is finalized
after the MVP (RFC-0000 §5, §6). It answers the coverage rows RFC-0000 §8
assigns to it: RFC-0001 Q19 (packaging, versioning, signing), Q20 (review), Q21
(sandboxing), Q22 (audit of declared vs. actual risk). It also answers RFC-0006
§15 OQ7 (skill-declared Postconditions) and RFC-0010 §15 OQ5 (skill-provider
interaction).

**BREAKING:** No. This RFC specifies the Skill Contract that RFC-0001, RFC-0002,
RFC-0004, RFC-0005, RFC-0006, RFC-0007, RFC-0008, and RFC-0010 already assume —
that Skills are packaged, versioned, authenticated procedures that declare
their surface up front (RFC-0001 §11.3), that a Skill is a candidate like any
LLM output (RFC-0003 §2.7), that Skill Actions pass the same gate as any Action
(RFC-0004 A3), that Skill content is untrusted until authenticated and reviewed
(RFC-0007 §4.8), and that Skills never execute outside the Approval gate
(RFC-0007 §6.12). It does not weaken any Principle, Boundary, Invariant, or
canonical Definition in an accepted RFC.

---

## 0. Purpose

This RFC answers one question:

> **What is a Skill, and how does the Core safely run one?**

A **Skill** is a packaged, versioned, authenticated troubleshooting procedure:
diagnostics, explanations, and gated Action sequences, bundled with declared
targets, privileges, risk, and verification (RFC-0003 §2.7). A Skill extends
what the Assistant can *do* (RFC-0001 §11.2); it never extends what the machine
*permits*.

The Core and a Skill are separated by a contract, exactly as the Core and a
Provider are. A Skill that implements the contract is usable; a Skill that
violates it is refused. The Core never needs to know *which* skill is running
to keep the machine safe: safety comes from the deterministic gate that
surrounds every Skill Action (RFC-0004 A3, RFC-0008), not from the Skill's
identity. This RFC defines the Skill Contract and the Skill Runtime's place in
the architecture — no implementation, no file formats, no schemas, no
serialization, no algorithms; those belong to RFC-0020 (implementation
blueprint) and the ecosystem documents.

---

## 1. What is a Skill

A Skill is a **procedure**, not a program:

| A Skill is | A Skill is not |
|---|---|
| A packaged, versioned, authenticated procedure (RFC-0003 §2.7) | Core behavior (RFC-0004 §3.1 Skills) |
| A bundle of diagnostics, explanations, and gated Action sequences | A Provider, a mode, or a forum post (RFC-0003 §2.7) |
| A candidate for approval, like any LLM output (RFC-0003 §2.7) | An authority above Policy (RFC-0004 §3.1) |
| An extension of what the Assistant can do (RFC-0001 §11.2) | An extension of what the machine permits |
| A set of declared intent — targets, privileges, risk, verification (RFC-0001 §11.3) | Untrusted content that trusts itself |

**What is not a Skill:**

1. **A Provider.** A Provider is a reasoning service the Core consults
   (RFC-0010). A Skill is a procedure the Core executes under a gate. They are
   different extension axes (RFC-0001 §11.2) with different contracts.
2. **A diagnostic command alone.** A single Collector is a component a Skill
   may bundle (RFC-0003 §2.1); it is not itself a Skill.
3. **An explanation alone.** Notes without the packaging contract — no declared
   targets, privileges, risk, or verification — are not a Skill (RFC-0003
   §2.7).
4. **Core logic.** Anything that would require editing the Core's decision
   rules to ship is a Core change, needing its own RFC, not a Skill (RFC-0001
   §11).
5. **A set of shell commands.** A Skill's Actions are gated Proposals, never
   raw commands (RFC-0004 A3).

---

## 2. Why Skills Exist

Skills give the Assistant **capability without modification**:

1. **Reproducibility.** A community-authored procedure runs reproducibly across
   the distro families it declares (RFC-0001 §1.5).
2. **Safety by contract.** A Skill that declares its surface up front — what it
   reads, changes, and how its success is verified — is safe to *consider*
   (RFC-0001 §11.3).
3. **Separation of ecosystem and runtime.** Distribution, review, and trust
   rating are ecosystem concerns that must not couple to execution (RFC-0001
   §11.6).
4. **Extension by registry, not branching.** Skills register; the Core
   enumerates what is registered and knows each entry only through its declared
   contract (RFC-0001 §11.2).
5. **A deterministic source of Proposals.** Where the LLM is weak or
   unavailable, a Skill provides structured, deterministic Plans (RFC-0002
   §2.6, §6.2; RFC-0010 §7.3 degraded mode).

Skills do not exist to bypass anything. If a procedure cannot live within the
contract, it does not become a Skill; it becomes a Core change.

---

## 3. Skill Ownership

Every responsibility has exactly one owner (RFC-0004 §3). The Skill's place:

| Thing | Owner |
|---|---|
| The Skill's content and declared surface | The Skill's author |
| Authentication of a Skill | The Skill Registry (authentication role) |
| Review of declared vs. actual risk | The Skill review process (RFC-0001 Q20, Q22) |
| Policy decisions about a Skill | Policy Engine (RFC-0008) |
| Execution of Skill Actions | Executor (RFC-0004 A2) |
| The Skill's lifecycle within a session | Orchestrator / Skill Runtime (this RFC) |

**No one owns a Skill as a unit of authority.** A Skill is never approved as a
unit; only its individual Actions are classified and approved (RFC-0008 §5).

---

## 4. Skill Authority

A Skill has **no authority**:

1. **Cannot execute.** Skill Actions run only through the Executor under a
   valid Approval Token (RFC-0004 A2, A3; RFC-0007 §6.12).
2. **Cannot approve.** Only the Operator approves (RFC-0004 §7).
3. **Cannot create Facts.** Facts come only from normalized Observations
   (RFC-0005). A Skill's Collector output is Observation material, not Fact
   (RFC-0007 §6.11).
4. **Cannot verify.** Verification is deterministic Fact comparison (RFC-0006).
   A Skill *declares* its verification approach; it cannot *perform* the
   verification.
5. **Cannot escalate.** A Skill cannot widen its own or any other actor's
   authority (RFC-0004 A8).
6. **Cannot modify policy.** Policy is Operator-owned (RFC-0004).
7. **Cannot reach the machine directly.** Every Skill Action passes the gate
   (RFC-0001 §8.4, RFC-0004 A3).

**The Skill's only output is a Proposal.** A Skill proposes — diagnostics to
run, Actions to take, explanations to show — and the deterministic Core
decides. Everything a Skill produces is advisory (RFC-0007 §4.8), exactly like
Provider output.

---

## 5. Skill Trust Class

Trust in a Skill is **conditional** (RFC-0007 §4.11, §6.11):

1. **Untrusted by default.** Until authenticated and within Policy, a Skill is
   untrusted (RFC-0007 §4.8; RFC-0001 §11.5).
2. **Conditional after authentication.** Authenticated-and-policy-checked Skill
   declarations are Conditional: accepted only after the checks pass (RFC-0007
   §4.11). Authentication proves provenance, not correctness.
3. **Metadata is Conditional; code stays Untrusted.** The declared surface is
   trusted only for what it declares. The Skill's runtime behaviour never gains
   the trust of its metadata (RFC-0007 §6.11).
4. **Skill code never gains Trusted.** Skill code executes only as Actions
   bound to a valid Approval Token (RFC-0007 §6.12).
5. **Declared-vs-actual mismatch → Untrusted.** Deviation revokes trust
   (RFC-0007 §6.11; RFC-0001 Q22).

**Localness grants no trust** (RFC-0007 §4.7 spirit). A Skill on the Operator's
machine is not more trusted than a fetched one; the boundary is the contract,
not the distance.

---

## 6. Skill Boundaries

The Skill boundary is a **security boundary** (RFC-0001 §7, RFC-0007 §4.8).
There is no path from a Skill to the machine except through the deterministic
Core, the gate, and the Executor.

| Boundary | What a Skill never crosses |
|---|---|
| Execution | No Skill content executes outside the Approval gate (RFC-0004 A3) |
| Truth | No Skill content becomes a Fact without normalization (RFC-0005) |
| Authority | No Skill content grants, extends, or confirms authority (RFC-0004 A8) |
| Verification | No Skill content confirms success (RFC-0006) |
| Secrets | No Skill content receives or stores secrets (RFC-0009; §15) |
| Policy | No Skill content modifies Policy (RFC-0004) |
| LLM path | Skill code never enters the Provider View or the LLM path (RFC-0007 §6.12) |
| Audit | A Skill cannot edit or erase audit records (RFC-0004 A7; §16) |

**Inside the boundary:** a Skill can only *do* what its Actions declare and the
gate permits; it can only *read* what its Collectors declare and Policy allows
(RFC-0001 §11.3). The boundary is enforced by construction — the Skill has no
other channels.

---

## 7. Skill Responsibilities

A Skill is a packaged procedure, not a participant in governance:

| Responsibility | What it means |
|---|---|
| **Declare its surface up front** | State targets, privileges, risk class, what it reads, what it changes, and how its success is verified (RFC-0001 §11.3) |
| **Bundle diagnostics** | Provide Collectors that produce Observations (RFC-0003 §2.1; §11) |
| **Bundle explanations** | Provide human-readable material for the Operator |
| **Bundle gated Actions** | Provide Action sequences that pass the same gate as any Action (RFC-0004 A3) |
| **Declare Preconditions** | State what must be true before its Actions may run (§12) |
| **Declare Postconditions** | State the expected machine state its Actions claim to produce (§13) |
| **Declare its verification approach** | State how its success is to be verified; never verify itself (§14) |
| **Stay within its declared surface** | Deviation is a trust violation (§5.5) |
| **Signal inability** | Fail loudly rather than improvising (§10) |

**Not responsible for:** policy, approval, verification, Fact creation,
authority, secrets, audit. Each has a deterministic owner (RFC-0004 §3).

---

## 8. Skill Capabilities

Skills declare capabilities, like Providers declare theirs (RFC-0010 §5).
**No capability implies permission** (RFC-0010 §5.4):

| Capability | Meaning |
|---|---|
| **Diagnostics** | Bundles Collectors that produce Observations |
| **Explanation** | Produces human-readable material |
| **Proposal** | Produces Proposals for the gate |
| **Planning** | Produces multi-step Plans of Actions |
| **Verification approach** | Declares how its success is checked (never performs it) |
| **Deterministic operation** | Runs without a Provider (usable in degraded mode) |

**Rules:** capabilities are declared, validated, and revoked on mismatch
(§5.5); they never widen boundaries (§6) or weaken invariants; a deterministic
Skill may run diagnostics and present Facts in degraded mode but may not
recommend (RFC-0002 Q11; RFC-0010 §7.3).

---

## 9. Skill Dependencies

Dependencies are declared, directional, and never circular.

**May depend on:** the Skill Contract; the fact model and its Facts/Evidence
Sets (RFC-0005); Collectors (RFC-0003 §2.1); the machine vocabulary (RFC-0021);
other Skills — declared, version-pinned, acyclic (§18).

**May never depend on:** another Skill's runtime state (§17); a specific
Provider (RFC-0010 §12); a specific Operator session; Core internals (RFC-0001
§11.1).

**Rules:** dependencies are declared (part of RFC-0001 §11.3's surface),
versioned, acyclic, and loud on failure — an unavailable or unauthenticated
dependency refuses the Skill (RFC-0002 SKILL_UNAVAILABLE; §10).

---

## 10. Skill Failure Philosophy

Failure is a designed outcome, never a crash and never a silent degradation.

| Failure | Core reaction |
|---|---|
| **Unavailable** | Cannot load or authenticate → SKILL_UNAVAILABLE; revise the plan without it, or ask (RFC-0002 §4.7) |
| **Invalid** | Declared surface fails validation → refused; never loaded |
| **Failed execution** | A Skill Action fails → failure event; plan re-opened (RFC-0002 §2.10) |
| **Trust violation** | Behavior contradicts declaration → trust revoked (§5.5); refused for the session |
| **Incomplete** | Proposal lacks expected effects or Preconditions → rejected (RFC-0008 §5) |

**Philosophy:** fail loud, fail small, fail safe (RFC-0001 §10.6); no
unauthenticated substitution (RFC-0002 §4.7); bounded retry (RFC-0002 Q2);
failure is audited (§16); the machine is the judge — a Skill's own claim about
its success is never the verification (§14, RFC-0006).

---

## 11. Skill Interaction with Diagnostics

1. **A Skill bundles Collectors** (RFC-0003 §2.1). A Collector is a
   deterministic, read-only diagnostic that produces Observations.
2. **The Diagnostics Layer runs Collectors.** It is the *only* actor that
   inspects the Machine besides the Operator (RFC-0004 §3.1). A Skill supplies
   Collectors; it never inspects the Machine itself.
3. **Observations become Facts in the Fact Layer** (RFC-0005 §2). The Skill
   consumes Facts; it never produces them (RFC-0005 F6).
4. **Ownership is clear:** the Diagnostics Layer owns *collection* (RFC-0004
   A4, read-only); the Fact Layer owns *normalization and truth* (RFC-0004
   §3.1); a Skill owns only the *bundle* of Collectors it declares.

**Rule:** a Skill's diagnostic text is sanitized before any Provider View
(RFC-0007 §6.11, §11). Skill text is untrusted text like any other.

---

## 12. Skill Preconditions

A Skill declares the Preconditions of its Actions — the Facts that must be true
before an Action may run (RFC-0006 §4; RFC-0008 §9).

**Rules:**

1. Preconditions are declared with the Action (RFC-0001 §11.3), in the fact
   model's vocabulary (RFC-0005).
2. Preconditions are **revalidated at the execution gate**; the Core re-observes
   the Facts, the Skill does not (RFC-0006 §4; RFC-0008 §9 TOCTOU).
3. A Skill **cannot waive its own Preconditions**. If a declared Precondition
   does not hold, the Action does not run (RFC-0002 §2.10).
4. Unmet Preconditions are **disclosed, not papered over** (RFC-0001 §10.8).

The Precondition *mechanism* belongs to RFC-0006 and RFC-0008; this RFC only
requires that a Skill declare Preconditions up front, deterministically.

---

## 13. Skill Postconditions

A Skill declares the Postconditions its Actions claim to produce — the expected
machine state after execution, in the fact model's vocabulary (RFC-0006 §5).

**Rules:**

1. Postconditions are declared **before execution**, never invented after
   (RFC-0006 V10).
2. A Proposal is **not complete without them** (RFC-0008 §5; RFC-0006 V10).
3. Postconditions are **state, not implementation** (RFC-0006 §5).
4. Postconditions **drive verification**; the Skill declares the target, never
   the verdict (RFC-0006).

This answers RFC-0006 §15 OQ7: the *contract* by which a Skill declares its
Postconditions and verifiable scope is fixed here, in the fact model's
vocabulary; the *mechanics* of comparison remain RFC-0006/RFC-0020.

---

## 14. Skill Verification Responsibilities

A Skill's verification responsibility is limited to **declaring its
verification approach**. It never performs verification.

**What a Skill does:** declares how its success should be checked — which
Postconditions, in which scopes (RFC-0006 §5, §11); declares which of its
states are unverifiable and must be labeled Unknown (RFC-0006 §11.3); supplies
Collectors that produce the Facts verification compares (§11).

**What a Skill never does:** confirms its own success (RFC-0006 V1); produces a
Verification Outcome (RFC-0006 §7); reuses its own claim as evidence (RFC-0007
§6.12).

**Rule:** verification of a Skill Action is indistinguishable from verification
of any Action (RFC-0006). The Skill's declaration is the *expectation*;
RFC-0006's process is the *judge*.

---

## 15. Skill Interaction with Secrets

A Skill never receives secrets, and never persists what it sees (RFC-0009;
RFC-0010 §11).

1. **No secrets in Skill content** — no embedded credentials or personal data
   (RFC-0007 §6.10; RFC-0001 §8.7).
2. **No secrets to Skills** — the no-secrets boundary applies to Skills as it
   does to Providers (RFC-0010 §11).
3. **No path to the Operator's secret store** — secret lifecycle is RFC-0009's.
4. **Skill output is sanitized before Context** — and can be quarantined as
   Hostile (RFC-0007 §6.11, §4.8).

---

## 16. Skill Interaction with Audit

A Skill is an audit *subject*, never an audit *editor*.

1. **Every Skill event is recorded** — loading, activation, execution, failure,
   refusal, trust revocation (RFC-0002 invariant 13; RFC-0004 A7).
2. **A Skill cannot edit or erase history** — Audit is append-only and
   tamper-evident (RFC-0004 A7).
3. **Skill identity is recorded** — version, signature, declared surface.
4. **Declared-vs-actual audit** (RFC-0001 Q22) is itself an audit record and a
   trust input (§5.5).

Audit *format and retention* belong to RFC-0013; this RFC fixes that Skill
activity is audited, not how it is stored.
---

## 17. Skill Isolation Philosophy

Isolation is architectural before it is technical (RFC-0001 Q21):

1. Skills **never touch Core rules**; they operate through contracts (RFC-0001
   §11.4).
2. Skills **never see each other's runtime** (RFC-0001 §11.4 spirit).
3. Skills **never reach the machine un-gated**; isolation is not a license to
   run freely (RFC-0007 §6.12).
4. Isolation is a **boundary, not a privilege** — it makes a Skill containable,
   not trusted (§5).
5. **Mechanics are RFC-0020's** (isolated environments, capability
   declarations, or both — RFC-0001 Q21); the *requirement* that a Skill is
   isolated from the Core and other Skills is this RFC's.

---

## 18. Skill Composition Philosophy

Skills may compose, but composition is declared, version-pinned, and acyclic:

1. **Composition is declared** — a Skill that uses another lists it as a
   dependency, with a version (§9).
2. **Composition is additive** — the whole is the sum of the declared parts
   (RFC-0001 §11.4).
3. **Composition never merges authority** — each Action of each Skill passes
   the same gate.
4. **Composition never creates a new Skill silently** — if it changes the
   declared surface, it is a new version, reviewed as such (§19).
5. **Composition is acyclic and bounded** — no cycles (§9.3); depth/breadth
   limits are RFC-0020 policy values.

---

## 19. Skill Versioning, Compatibility, and Deprecation Philosophy

Architectural commitments; concrete formats are RFC-0020's.

**Versioning:** every Skill is versioned (RFC-0003 §2.7; RFC-0001 Q19);
versions are immutable — a change is a new version; versions carry a signature
(RFC-0007 §6.11).

**Compatibility:** compatibility lives with the Core's contracts, not with the
Skill (RFC-0001 §11.4); the Core's contracts are stable unless amended
(RFC-0003 Part II); compatibility is declared per target distro (RFC-0021).

**Deprecation:** deprecation is a Core-visible state recorded in Audit;
deprecated is not untrusted — the Skill still passes the same gate; removal is
clean, leaving no Core residue (§9, RFC-0001 §11.2). Concrete version format,
signing scheme, and migration rules are owned by RFC-0017 (compatibility) and
RFC-0020 (implementation).

---

## 20. Skill Interaction with Providers

Skills and Providers are separate extension axes (RFC-0001 §11.2). Answers
RFC-0010 §15 OQ5.

1. **A Skill consumes the Provider Contract, never a vendor** (RFC-0010 §12,
   PR10).
2. **A deterministic Skill does not need a Provider** — it runs in degraded
   mode (RFC-0010 §7.3; §8).
3. **Skill content never enters the LLM path except sanitized** — code never
   goes to a Provider; text is sanitized before any Provider View (RFC-0007
   §6.11, §6.12).
4. **No bidirectional trust** — a Provider does not trust a Skill, and vice
   versa; both are untrusted to the Core (§5; RFC-0010 §1).
5. **The Provider View a Skill may request is the same bounded View any request
   gets** (RFC-0010 §11).

---

## 21. Skill Interaction with the Core

The Core and a Skill meet at exactly one point: the **Skill Contract**.

| Interaction | Owner (Core side) |
|---|---|
| **Loading** | Skill Runtime (§22) |
| **Activation** | Skill Runtime (§23) |
| **Diagnosis** | Orchestrator (RFC-0002 §2.5, §6.2) |
| **Planning** | Orchestrator (RFC-0002 §2.6) |
| **Approval** | Approval Engine (RFC-0008) |
| **Execution** | Executor (RFC-0004 A2) |
| **Verification** | Fact Layer (RFC-0006) |
| **Context** | Context Manager (RFC-0004 §3.1) |
| **Audit** | Audit System (RFC-0004 A7) |

**The Core's rules never bend for a Skill.** There is no "Skill-specific"
approval, verification, or policy; a Skill that cannot live within the exact
rules of the whole system gets refused, not special rules.

---

## 22. Skill Loading

Loading deterministically turns a Skill's packaged content into a validated
contract instance.

**Steps (normative):** read the declared surface; authenticate signature and
provenance (RFC-0001 Q19) — unauthenticated Skills are never loaded (RFC-0002
§4.7); validate the declaration (targets, privileges, risk, capabilities,
dependencies, Preconditions, Postconditions, verification approach; RFC-0001
§11.3); check Policy before activation (RFC-0008); register with the Core.
**Rules:** validation is deterministic — loading never depends on LLM judgment;
a Skill that fails validation is refused and audited (§16); loading has no side
effects — it changes nothing but the Core's enumeration of available Skills
(RFC-0001 §11.4).

---

## 23. Skill Activation

Activation makes a validated Skill usable within a session, per Policy.

**Rules:** activation is per-session and reversible (RFC-0002 §2.2);
activation is Policy-gated (RFC-0008; §5); activation grants no authority — an
activated Skill still proposes (§4); an unauthenticated Skill is never
substituted (RFC-0002 §4.7); activation is audited (§16).

---

## 24. Skill Interaction with Approval Engine

Skill Actions pass the **exact same** classification and approval gate as any
Action (RFC-0004 A3; RFC-0008).

1. **No unit approval** — a Skill is never approved as a whole (RFC-0008 §5).
2. **No skill-based shortcut** — trust changes consideration, never the gate
   (RFC-0007 §6.11).
3. **Classification uses structure, not Skill content** (RFC-0008 §7; P2).
4. **The proposing Skill gains no trust, authority, or power from proposing**
   (RFC-0008 §5; RFC-0004 A3).
5. **Blocked Actions follow the same override rules** as any Action (RFC-0008
   §13; RFC-0002 Q13).

---

## 25. Skill Interaction with Verification

Skill Actions are verified exactly like any Action (RFC-0006):

1. **Verification compares Facts to declared Postconditions** (RFC-0006 §9;
   §13).
2. **A Skill never performs the comparison** (§14; RFC-0006 V1).
3. **Verification of a Skill Action produces a normal Outcome** (RFC-0006 §7).
4. **A Skill Action's failure is new Fact** and re-opens planning (RFC-0002
   §2.9, §2.10).
5. **Re-verification triggers apply** (RFC-0006 §10).

---

## 26. Skill Interaction with Context

Skill material enters Context only after RFC-0007 sanitization, and never
unbounded.

1. **Skill text is untrusted text** — sanitized, contained, or quarantined
   (RFC-0007 §6.11, §4.8).
2. **Skill text is not a Fact** — it is material, normalized into Facts only
   through RFC-0005 (RFC-0007 §6.11).
3. **Skill content is bounded** — Context is purpose-limited (RFC-0001 §9;
   RFC-0005 Q8).
4. **Skill code never enters Context or the Provider View** (RFC-0007 §6.12).
5. **Context assembly** is owned by RFC-0012 (Context & Memory) and RFC-0015.

---

## 27. Skill Interaction with Future Extensions

The Skill Contract is itself an extension point; future extensions must not
couple to Skills in a way that bypasses the contract.

1. **New diagnostic domains** attach through the same extension mechanism
   without altering Core rules (RFC-0001 §11).
2. **The ecosystem** (registry, review, trust ratings) is separate from the
   runtime (RFC-0001 §11.6) and is finalized post-MVP (RFC-0000 §5).
3. **A Skill cannot be a channel for a future extension to reach the machine
   outside the gate.** Every future extension that changes the machine is a
   Core-tracked change (RFC-0001 §11).
4. **Cross-contract compatibility** is owned by RFC-0017 (RFC-0000 §8;
   RFC-0001 Q27).

---

## 28. Skill Rules (Normative)

The following invariants are normative for the entire project. Each has a
Statement, a Rationale, and a Test. They extend, never weaken, RFC-0001's
principles, RFC-0002's §9 invariants, RFC-0004's A-invariants, RFC-0005's
F-invariants, RFC-0006's V-invariants, RFC-0007's T-invariants, and RFC-0010's
PR-invariants.

| ID | Statement | Rationale | Test |
|---|---|---|---|
| SK1 | **A Skill never executes.** No Skill content becomes a command; every Skill Action runs only through the Executor under a valid Approval Token. | Skills are procedures, not authorities; the gate is the only execution path (RFC-0004 A2, A3). | Deliver a Skill Action to execution without a valid token; verify it is blocked. |
| SK2 | **A Skill never creates authority.** Skill content grants, extends, or confirms no authorization. | Authority flows downward from the Operator only (RFC-0004 A8). | Deliver Skill content claiming approval; verify no authority changes. |
| SK3 | **A Skill never creates Facts.** Skill output becomes a Fact only through RFC-0005 normalization of Observations. | The Fact Layer is the sole owner of truth (RFC-0004 §3.1; RFC-0005). | Deliver Skill output asserting a machine fact; verify no Fact is created. |
| SK4 | **A Skill never bypasses Approval.** Every Skill Action passes the full classification and approval gate; no unit approval exists. | Approval is per-Action; a Skill is never approved as a unit (RFC-0008 §5). | Route a Skill Action past the gate; verify it is blocked. |
| SK5 | **A Skill is never trusted by default.** A Skill is untrusted until authenticated and within Policy; trust is conditional. | Third-party content is untrusted until proven (RFC-0001 §11.5; RFC-0007 §4.8). | Load an unauthenticated Skill; verify it is refused. |
| SK6 | **A Skill never verifies.** A Skill declares its verification approach; it never confirms success. | Verification is deterministic Fact comparison (RFC-0006 V1). | Deliver a Skill claiming its own success; verify no Outcome is recorded. |
| SK7 | **A Skill never modifies Policy.** Skill content changes no rule, gate, allowlist, or elevation bound. | Policy is Operator-owned (RFC-0004). | Deliver Skill content attempting a policy change; verify Policy is unchanged. |
| SK8 | **A Skill never stores secrets.** A Skill receives no secrets and persists nothing. | The no-secrets boundary applies to all extensions (RFC-0009; RFC-0010 §11). | Offer a secret-adjacent token to a Skill; verify it never arrives and nothing is persisted. |
| SK9 | **A Skill is isolated from the Core and other Skills.** No Skill touches Core rules or another Skill's runtime. | Additive, non-destructive extension (RFC-0001 §11.4). | Instrument two Skills and the Core; verify no cross-touch. |
| SK10 | **A Skill's actual behavior must match its declared surface.** Declared-vs-actual mismatch revokes trust. | Declared, reviewable intent is the safety basis (RFC-0001 Q22; RFC-0007 §6.11). | Present a Skill whose Actions exceed its declared risk; verify trust revocation. |
| SK11 | **A Skill's Actions carry declared Preconditions and Postconditions.** No Action is complete without them. | The gate and verification need declared expectations (RFC-0006 §5, V10; RFC-0008 §9). | Submit a Skill Action with no declared expected effect; verify rejection. |
| SK12 | **A Skill cannot waive its own Preconditions or Postconditions.** The Core revalidates; the Skill does not. | TOCTOU and verification are Core-owned (RFC-0006 §4). | Let a Skill bypass a Precondition check; verify the Action is refused. |
| SK13 | **Skill content never enters the Provider View or the LLM path unless sanitized.** Skill code never does; text only after sanitization. | Skill code is execution material, never prompt material (RFC-0007 §6.12). | Feed Skill code to the Provider path; verify it is blocked. |
| SK14 | **A Skill cannot modify Audit.** Audit is append-only; a Skill is a subject, never an editor. | Audit integrity is invariant (RFC-0004 A7; RFC-0002 invariant 13). | Deliver a Skill attempting an audit edit; verify it is refused. |
| SK15 | **Skill failure never crashes the Core.** Unavailable, invalid, failed, or trust-violated Skills degrade, never crash. | Fail safe, fail loud, fail small (RFC-0001 §10.6). | Force each Skill failure mode; verify the runtime degrades, never exits. |
| SK16 | **Replacing or removing a Skill requires no Core change.** The Core enumerates what is registered; it depends on none. | Extension by registry (RFC-0001 §11.2). | Remove every Skill; verify the Core's invariants and behavior are unchanged. |

---

## 29. Interaction with other RFCs

This RFC specifies the Skill Contract for the whole project. Only references
follow; no duplication (RFC-0003 Part II §1).

| RFC | Relationship | What RFC-0011 says here |
|---|---|---|
| **RFC-0001** | Architecture and principles | Implements RFC-0001 §11 (contracts, registry, declared surface, additive, unsafe-by-default, ecosystem separation); answers Q19–Q22. |
| **RFC-0002** | Runtime states and invariants | Consumes RFC-0002 §2.5/§2.6 (Skills in Diagnosis and Planning), §2.10 (Replanning), §4.7 (SKILL_UNAVAILABLE), degraded mode; Skills never bypass §9 invariants. |
| **RFC-0003** | Vocabulary and governance | Uses Skill canonically (RFC-0003 §2.7); §32 flags new terms for Part I. |
| **RFC-0004** | Authority model | Implements the Skills component's untrusted status and Propose-only authority (RFC-0004 §3.1); reinforces A2, A3, A7, A8. |
| **RFC-0005** | Canonical Fact Model | Skills consume Facts and bundle Collectors; never produce Facts (F6); Preconditions/Postconditions are expressed in the fact model. |
| **RFC-0006** | Verification & Outcome Model | Skills declare Postconditions and a verification approach; verification is RFC-0006's, never the Skill's (V1, V10); answers RFC-0006 §15 OQ7. |
| **RFC-0007** | Trust and sanitization | Skill content is untrusted/conditional (RFC-0007 §4.8, §6.11), sanitized before Context, quarantined when needed; code never enters the LLM path (§6.12). |
| **RFC-0008** | Approval & Policy Engine | Skill Actions pass the same gate; no unit approval; classification uses structure, not Skill content (P2). |
| **RFC-0010** | Provider Contract | Skills consume the Provider Contract, never a vendor; deterministic Skills serve degraded mode; answers RFC-0010 §15 OQ5. |

Forward references (planned RFCs this contract constrains): RFC-0009 (secrets
never reach Skills); RFC-0012 (Context & Memory assemble sanitized Skill
material); RFC-0013 (Audit format and retention of Skill events); RFC-0015
(how Skills are presented); RFC-0016 (Skill enablement configuration);
RFC-0017 (compatibility across Skill, fact-model, and provider contracts);
RFC-0020 (packaging format, sandboxing mechanics, validation algorithm).

---

## 30. Open Questions

Each names its owner. None blocks the Skill Contract's guarantees.

1. **Packaging format and signing scheme.** The concrete format, signature
   scheme, and version encoding — RFC-0020 (implementation) and RFC-0017
   (compatibility).
2. **Sandboxing mechanics.** Whether isolation uses isolated environments,
   capability declarations, or both (RFC-0001 Q21) — RFC-0020. This RFC fixes
   that isolation is required (§17).
3. **Review process and trust ratings.** Review of declared-vs-actual risk
   (RFC-0001 Q20, Q22) and any trust-rating system — the Skill ecosystem work,
   finalized post-MVP (RFC-0000 §5).
4. **Registry and distribution.** The registry, marketplace, and fetching under
   default-deny (RFC-0001 Q23 → RFC-0008) — the ecosystem work and RFC-0008's
   network policy.
5. **Secret handling specifics.** The mechanism keeping secrets out of Skill
   content and input — RFC-0009; this RFC states the boundary.
6. **Enablement configuration.** How the Operator enables, disables, and
   prefers Skills — RFC-0016.
7. **Cross-version migration.** Migration when the fact model, provider
   contract, or Skill Contract changes — RFC-0017.
8. **Ecosystem-runtime separation mechanics.** Following RFC-0001 §11.6,
   finalized post-MVP (RFC-0000 §5).

---

## 31. Risks

| Risk | Mitigation |
|---|---|
| **Malicious Skills** | Untrusted, sanitized, contained (SK5, SK13; RFC-0007 §6.12); Actions pass the same gate (SK1, SK4; RFC-0004 A3) |
| **Declared-vs-actual mismatch** | Declared surface validated and audited; mismatch revokes trust (SK10; RFC-0001 Q22) |
| **Prompt injection via Skill text** | Sanitized before Context; Hostile content quarantined (SK13; RFC-0007 §6.11) |
| **Skill as approval bypass** | No unit approval; classification uses structure, never Skill content (SK4; RFC-0008 §5, P2) |
| **Skill as Fact source** | Skill output is material, never Fact; only RFC-0005 normalization creates Facts (SK3) |
| **Skill as verification** | Verification is Core-owned; a Skill never confirms success (SK6; RFC-0006) |
| **Unbounded composition** | Declared, version-pinned, acyclic (§18) |
| **Version/deprecation confusion** | Versions immutable; deprecation informs but never relaxes safety (§19) |

---

## 32. Vocabulary Additions for RFC-0003

The following terms are defined in this RFC and must be added to RFC-0003 Part
I by additive amendment: **Skill Contract**, **Skill Manifest** (the declared
surface; RFC-0007 §6.11's term), **Skill Capability**, **Skill Dependency**,
**Skill Precondition**, **Skill Postcondition**, **Skill Verification
Approach**, **Skill Isolation**, **Skill Composition**, **Skill Registry** —
defined at first use in §7, §8, §9, §12, §13, §14, §17, §18, and §22. Skill,
Collector, Observation, Fact, Action, Proposal, Plan, Approval, Policy,
Verification, and Context already exist in RFC-0003 Part I and are used here
with their canonical meanings.

---

*End of RFC-0011. Normative: sections 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28. Explanatory and
load-bearing: sections 0, 29, 30, 31, 32. Any change to a Skill responsibility,
boundary, capability, dependency, lifecycle step, failure rule, isolation or
composition rule, versioning or deprecation rule, or an invariant SK1–SK16 is a
BREAKING change and must be made by amendment (RFC-0003 Part II).*
