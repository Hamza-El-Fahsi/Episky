# RFC-0000 — Architectural Roadmap (Index)

**Status:** Accepted (living index — amended as RFCs move status)
**Date:** 2026-08-01
**Scope:** The complete set of architecture documents required before implementation
**Audience:** Future maintainers
**Supersedes:** Nothing
**Depends on:** RFC-0001, RFC-0002 (both accepted)

---

## 0. Preamble

This document is the roadmap for the entire project: every architecture document
that must exist before production code is written, in the order they should be
written. It is deliberately *not* an architecture document itself. It contains no
implementation details, no APIs, and no design decisions beyond "what must be
decided, and in what order."

RFC-0001 and RFC-0002 are accepted and will not be rewritten; everything below
is planned. This index is a living document: when an RFC is drafted or accepted,
this file is updated to reflect it.

Two rules govern this roadmap:

1. **An RFC may be written only when its dependencies are accepted.** Writing
   against an unaccepted dependency risks building on sand.
2. **An RFC that would weaken an invariant or boundary in an accepted RFC is
   forbidden from doing so silently** — it must instead propose an amendment
   through the process defined in RFC-0003.

---

## 1. Numbering and Status Conventions

- **Numbering** is sequential by *reservation*, not by writing order. RFC-0000 is
  this index. RFC-0001 and RFC-0002 are reserved and accepted. RFC-0003 and
  above are reserved for the documents listed below; numbers are never reused.
- **Status** has three values:
  - **Accepted** — approved; normative; can be amended only by the process in
    RFC-0003.
  - **Draft** — being written; not yet normative.
  - **Planned** — reserved, not yet written.
- **Gate** has two values:
  - **Required** — must be **Accepted** before any production code is written.
  - **Post-MVP** — explicitly postponed; the project commits to *not needing it*
    for the minimum viable product, and to a review gate before writing it.

The MVP itself is not yet defined; it is defined by RFC-0019. The Required/Post-MVP
classification in this document is therefore the *current* best estimate and is
ratified when RFC-0019 is accepted.

---

## 2. Categories

| Category | Purpose | RFCs |
|---|---|---|
| **Foundations** | The constitution: what the project is and how its documents are governed. | 0001, 0003 |
| **Runtime** | How the Assistant behaves while working, and what it records. | 0002, 0012, 0013, 0014 |
| **Domain** | What the tool knows about Linux systems: the model of a machine, its facts, and what "fixed" means. | 0004, 0005, 0006 |
| **Security** | Trust, risk, authorization, and sensitive data. The safety spine. | 0007, 0008, 0009 |
| **Extension System** | How the project grows: providers and skills. | 0010, 0011 |
| **Infrastructure** | The operational shell: interface, configuration, compatibility, distribution. | 0015, 0016, 0017, 0018 |
| **Implementation** | The gate before code: what the MVP is and how it is built. | 0019, 0020 |

---

## 3. Roadmap Overview

| # | Title | Category | Status | Gate |
|---|---|---|---|---|
| 0001 | Architecture & Design Foundations | Foundations | Accepted | Required |
| 0002 | Runtime Architecture & Session State Machine | Runtime | Accepted | Required |
| 0003 | RFC Governance & Document Process | Foundations | Planned | Required |
| 0004 | System Model & Supported Platforms | Domain | Planned | Required |
| 0005 | Fact Model & Diagnostics Architecture | Domain | Planned | Required |
| 0006 | Verification & Rollback Semantics | Domain | Planned | Required |
| 0007 | Trust Model, Sanitization & Injection Defense | Security | Planned | Required |
| 0008 | Approval & Policy Engine | Security | Planned | Required |
| 0009 | Secrets, Privacy & Sensitive Data | Security | Planned | Required |
| 0010 | Provider Contract & LLM Adapter | Extension | Planned | Required |
| 0011 | Skill System Contract & Ecosystem | Extension | Planned | Required |
| 0012 | Context & Memory Architecture | Runtime | Planned | Required |
| 0013 | Audit & Transcript Architecture | Runtime | Planned | Required |
| 0014 | Session Persistence, Resume & Recovery | Runtime | Planned | Post-MVP |
| 0015 | Operator Interface & Interaction Contract | Infrastructure | Planned | Required |
| 0016 | Configuration & Defaults | Infrastructure | Planned | Post-MVP |
| 0017 | Compatibility & Versioning Policy | Infrastructure | Planned | Post-MVP |
| 0018 | Deployment & Distribution | Infrastructure | Planned | Post-MVP |
| 0019 | MVP Definition & Milestone Plan | Implementation | Planned | Required |
| 0020 | Implementation Blueprint & Build Order | Implementation | Planned | Required |

---

## 4. Detailed RFC Entries

For every RFC: number, title, purpose, dependencies, and why it occupies this
position.

### RFC-0001 — Architecture & Design Foundations (Accepted)
- **Category:** Foundations
- **Purpose:** Goals, non-goals, principles, high-level architecture, system and
  trust boundaries, security principles, context and failure philosophy,
  extensibility philosophy, and the initial risks. The constitution every other
  RFC derives from.
- **Dependencies:** none.
- **Why here:** Everything depends on it. It is the document every later RFC
  cites and must not contradict.

### RFC-0002 — Runtime Architecture & Session State Machine (Accepted)
- **Category:** Runtime
- **Purpose:** The complete behavioral specification of a live session: states,
  transitions, events, the session loop, component consultation rules,
  replanning, interruption, invariants, and failure recovery.
- **Dependencies:** RFC-0001.
- **Why here:** It fixes the runtime behavior — especially the invariants — that
  the safety, domain, and extension RFCs must design *within*. Writing it after
  RFC-0001 and before everything else prevents later RFCs from inventing
  incompatible runtime semantics.

### RFC-0003 — RFC Governance & Document Process
- **Category:** Foundations
- **Purpose:** How RFCs are written, reviewed, numbered, accepted, and amended;
  what authority resolves contradictions; how a document becomes normative; how
  amendments to accepted RFCs work. A small, process-only document.
- **Dependencies:** RFC-0001 (its own numbering and standing assume the
  constitutional frame).
- **Why here:** It is the first document to write because every *other* remaining
  RFC needs a defined way to become normative. It has no technical content and
  can be written immediately without waiting on anything.

### RFC-0004 — System Model & Supported Platforms
- **Category:** Domain
- **Purpose:** Define the abstract model of "a Linux system" that the Assistant
  reasons about: the parts it understands (distro, package manager, init system,
  services, files, users, boot) and the parts it treats as opaque. Fix the
  initial support matrix (distro families, releases), how immutable/atomic
  systems are modeled, and what "supported" means for a skill or diagnostic.
- **Dependencies:** RFC-0001 (system boundaries).
- **Why here:** It is the domain foundation. The fact model (0005) and
  verification semantics (0006) both reason *about* the thing this RFC defines.
  It must precede them.

### RFC-0005 — Fact Model & Diagnostics Architecture
- **Category:** Domain
- **Purpose:** Define the canonical fact model: what a fact is, its provenance,
  its staleness bound, how distro-specific output is normalized into it, the
  collector contract, output limits, and the rules for collecting facts in
  parallel. It is the specification for RFC-0001's "the only source of factual
  claims about the machine."
- **Dependencies:** RFC-0001, RFC-0002 (Inspection and Verification roles),
  RFC-0004 (the system model the facts describe).
- **Why here:** Facts are the spine of the entire runtime: providers, skills,
  context, verification, and the TUI all consume them. It must be defined before
  providers and skills specify anything about what they see.

### RFC-0006 — Verification & Rollback Semantics
- **Category:** Domain
- **Purpose:** Define what counts as "verified": state-based verification (before/
  after fact comparison), when verification is impossible, and how the runtime
  must label unverified work. Define what, if anything, the project *promises*
  about rollback, and how catastrophic cases (e.g., system fails to boot after a
  change) are surfaced to a beginner who may be outside the TUI.
- **Dependencies:** RFC-0001, RFC-0002 (verification invariants), RFC-0005 (the
  facts that state-based verification compares).
- **Why here:** It comes after the fact model because verification is expressed
  in facts, and before the extension contracts because providers and skills must
  state how their own outputs are verified. RFC-0001 names weak verification as a
  top risk; this RFC is that risk's answer.

### RFC-0007 — Trust Model, Sanitization & Injection Defense
- **Category:** Security
- **Purpose:** Turn RFC-0001's trust boundaries and data-flow rules into a
  concrete, testable specification: exactly which inputs are untrusted, how
  untrusted text is sanitized and contained, the operational meaning of "no
  untrusted text is ever executed," and how prompt-injection attempts via machine
  output, provider output, and skill content are neutralized.
- **Dependencies:** RFC-0001 (§7 trust boundaries, §8 security principles).
- **Why here:** It is the first new document to write because *every* component
  that touches untrusted input (all of them) must be designed against its rules.
  Writing the safety spine before the domain and extension RFCs means those RFCs
  are born compliant rather than retrofitted.

### RFC-0008 — Approval & Policy Engine
- **Category:** Security
- **Purpose:** Specify the risk taxonomy and classification rules, the approval
  gates (auto-permitted / confirm / confirm-with-warning / blocked), approval
  granularity (per action vs. per plan), standing approvals and their expiry,
  the read-only allowlist, elevation semantics, retry policy, blocked-action
  overrides, and fail-closed behavior on policy errors.
- **Dependencies:** RFC-0001 (human-approval and default-deny principles),
  RFC-0002 (Awaiting Approval and execution-gate invariants), RFC-0007 (the
  trusted/untrusted frame the engine operates within).
- **Why here:** It is the heart of the project's safety model and has the
  widest blast radius (see §6). It must be written early, while the domain and
  extension RFCs can still be shaped around its decisions.

### RFC-0009 — Secrets, Privacy & Sensitive Data
- **Category:** Security
- **Purpose:** Specify how secrets and personal data are segregated, stored,
  redacted, and bounded; the guarantee that no secret enters a provider view;
  retention defaults; and the telemetry/privacy posture (what is collected, if
  anything, and under what opt-in).
- **Dependencies:** RFC-0001 (§8.7, §9 context), RFC-0007 (data-flow rules).
- **Why here:** Before the Provider Contract (0010) can state that no secrets
  travel to a provider, the redaction and segregation contract must exist. It
  also precedes Context & Memory (0012), which must enforce the same rules.

### RFC-0010 — Provider Contract & LLM Adapter
- **Category:** Extension
- **Purpose:** Define the provider-agnostic internal representation (the
  "provider view" and the uniform interface all vendors implement), the minimum
  capability a provider must have to be supported, how tool-calling variance is
  absorbed, degraded mode, fallback chains, outage behavior, and cost controls.
- **Dependencies:** RFC-0001, RFC-0002 (when the LLM is consulted), RFC-0007
  (provider output is untrusted), RFC-0009 (no secrets to providers).
- **Why here:** The MVP cannot run without its first provider, and no provider
  adapter can be written until this contract exists. It comes after the safety
  spine so that the untrusted boundary is specified before the adapter is.

### RFC-0011 — Skill System Contract & Ecosystem
- **Category:** Extension
- **Purpose:** Define the skill packaging format, capability declarations,
  versioning, validation, lifecycle, the registry, the runtime isolation
  (sandboxing) for skill execution, and the trust/review process for anything
  shipped or recommended as trusted. It also fixes the boundary between the
  ecosystem and the runtime (RFC-0001 §11).
- **Dependencies:** RFC-0001 (extensibility), RFC-0004 (targeting distros),
  RFC-0005 (skills declare and consume facts), RFC-0007 (skill content is
  untrusted), RFC-0008 (skill actions pass the same gate).
- **Why here:** Skills are a core goal but the *full* ecosystem is not an MVP
  need. The skill **contract** (what a procedure looks like and how it is gated)
  is required before code; the **ecosystem** half (registry, review, trust
  ratings) is finalized after the MVP. Placed after the safety and domain spine
  so skills are born compliant with the gate.

### RFC-0012 — Context & Memory Architecture
- **Category:** Runtime
- **Purpose:** Specify the persistence model: what is session-scoped, what is
  durable, the consent flow for durable memory, context bounds and consolidation
  on overflow, the Operator's visibility/export/wipe capabilities, and the
  enforcement point at which all provider-bound input passes through sanitization.
- **Dependencies:** RFC-0001 (§9 context philosophy), RFC-0002 (Context Building
  state), RFC-0005 (facts are what context carries), RFC-0009 (secrets/privacy
  rules the memory enforces).
- **Why here:** Context is assembled from facts and constrained by privacy, so it
  must follow 0005 and 0009. It must precede the MVP because every session's
  behavior depends on what may be remembered.

### RFC-0013 — Audit & Transcript Architecture
- **Category:** Runtime
- **Purpose:** Specify what is recorded and when (proposals, classifications,
  approvals, overrides, executions, verifications, outcomes), the ordering
  guarantee (recorded *before* the consequence), what may be retained and for
  how long, tamper-resistance expectations, and the honest framing that the audit
  is transparency, not forensics (RFC-0001 risk 8).
- **Dependencies:** RFC-0001 (§5 audit), RFC-0002 (invariant 13, the audit
  boundary), RFC-0008 (approvals are the most important audited events).
- **Why here:** Audit is an accepted invariant that the MVP must satisfy, so its
  specification is Required. It comes after the policy engine because the audit's
  most critical records are policy decisions.

### RFC-0014 — Session Persistence, Resume & Recovery
- **Category:** Runtime
- **Purpose:** Specify resume markers and session stores, crash and reboot
  recovery, interrupted-action reconciliation (orphaned processes, held locks,
  partial writes), attended vs. unattended execution, multi-goal policy, and the
  watchdog's drift detection.
- **Dependencies:** RFC-0001, RFC-0002 (interruption and resume rules it
  formalizes), RFC-0012 (what memory survives a resume), RFC-0013 (what the
  resume re-presents from the audit).
- **Why here:** **Post-MVP.** The MVP can be useful without surviving exits or
  reboots; the *invariants* that protect interrupted execution already live in
  RFC-0002. However, because this RFC is likely to amend runtime behavior (see
  §6), its core semantics should be agreed as a short decision record early even
  though the full RFC is deferred.

### RFC-0015 — Operator Interface & Interaction Contract
- **Category:** Infrastructure
- **Purpose:** Define the interaction architecture of the TUI: how states,
  evidence, and approvals are presented *semantically* (not visually), the
  approval experience against the "beginner with root power" contradiction
  (RFC-0001 risk 3), degraded-mode presentation, and progress/status semantics.
  It is the contract between the runtime and any presentation surface.
- **Dependencies:** RFC-0001, RFC-0002 (states and gates to render), RFC-0008
  (what an approval decision must communicate), RFC-0010 (degraded mode).
- **Why here:** The MVP is unusable without a way to present evidence and
  collect approvals. It must precede the MVP definition (0019) so the MVP's scope
  can include a defined interaction contract.

### RFC-0016 — Configuration & Defaults
- **Category:** Infrastructure
- **Purpose:** Specify what is configurable, the default posture (default-deny,
  minimal surface), provider selection, profiles, how Operator preferences
  integrate with policy, and the boundary between configuration and policy.
- **Dependencies:** RFC-0001 (operator-owns-the-machine), RFC-0008 (policy vs.
  config), RFC-0009 (secret storage for provider keys).
- **Why here:** **Post-MVP.** The MVP needs only a minimal provider selection
  and key storage, which is an implementation detail; the *configuration
  architecture* can grow with the product. The default-deny posture it would
  otherwise establish is already fixed by RFC-0001 and RFC-0008.

### RFC-0017 — Compatibility & Versioning Policy
- **Category:** Infrastructure
- **Purpose:** Specify how the skill format, fact model, provider contract, and
  RFC statuses are versioned; stability guarantees; and migration of skills and
  sessions across versions.
- **Dependencies:** RFC-0004, RFC-0005, RFC-0010, RFC-0011 (the things that get
  versioned).
- **Why here:** **Post-MVP.** Until the project has shipped, there is nothing to
  be compatible with. It must be written *before* the first public release, but
  not before the MVP exists. It depends on the contracts it will version, which
  is another reason it cannot come earlier.

### RFC-0018 — Deployment & Distribution
- **Category:** Infrastructure
- **Purpose:** Specify how the project ships: packaging and distribution
  channels, supported host OS releases, update mechanics, release cadence, and
  the boundary between our packaging and the distro's own packaging (RFC-0001
  non-goal 9).
- **Dependencies:** RFC-0001 (non-goals), RFC-0004 (host platform), RFC-0009
  (telemetry posture, if any).
- **Why here:** **Post-MVP.** The mechanics of shipping are decided during
  implementation; this RFC formalizes the *commitments* (support matrix, cadence,
  update safety) that a public release must honor, so it is written before the
  first public release but after the MVP is proven.

### RFC-0019 — MVP Definition & Milestone Plan
- **Category:** Implementation
- **Purpose:** Define the minimum viable product precisely: the smallest safe
  core loop (one provider, baseline diagnostics, a minimal fact model, a small
  set of built-in procedures, plan approval, execution, verification, audit,
  minimal context and config) and, just as explicitly, everything it excludes.
  Ratify the Required/Post-MVP classification from this document.
- **Dependencies:** RFC-0003 through RFC-0013 and RFC-0015 (all Required RFCs
  before it).
- **Why here:** It is the first *scoping* document and can only be written once
  the Required architecture exists to scope. It is the gate that makes
  "before production code" meaningful.

### RFC-0020 — Implementation Blueprint & Build Order
- **Category:** Implementation
- **Purpose:** Specify the mapping from accepted architecture to build units, the
  runtime's concurrency model (single-goal, serial state-changing execution), the
  architectural testing philosophy (state-machine conformance, invariant checks),
  and the build order in which each stage is demonstrable and verifiable. This is
  the final document before production code.
- **Dependencies:** RFC-0001 through RFC-0019 (every Required RFC, plus the MVP
  definition).
- **Why here:** It is deliberately last: its entire content is *how to build the
  thing the prior RFCs define*. Writing it earlier would either speculate about
  unaccepted decisions or duplicate them.

---

## 5. RFCs Absolutely Required Before Production Code

These must be **Accepted** before a single line of production code is written.
Without them, either the MVP cannot be specified, or it would be built against
undecided safety or domain semantics.

**Required (18):** RFC-0001, RFC-0002, RFC-0003, RFC-0004, RFC-0005, RFC-0006,
RFC-0007, RFC-0008, RFC-0009, RFC-0010, RFC-0011, RFC-0012, RFC-0013, RFC-0015,
RFC-0019, RFC-0020.

Rationale, grouped:

- **Safety spine (0007, 0008, 0009).** The gate, the trust rules, and the secret
  handling are the reasons the project exists and the reasons it is safe to run
  at all. Code written before these exist would violate RFC-0001 invariants by
  construction.
- **Domain spine (0004, 0005, 0006).** The system model, the fact model, and
  verification are what the runtime *does*. Verification, in particular, is
  called out by RFC-0001 as a prerequisite; building the executor before
  verification semantics exist would produce exactly the "verification theater"
  risk RFC-0001 names.
- **Extension contracts (0010, 0011).** The MVP needs its first provider and a
  minimal way to encode procedures. These RFCs define the internal representation
  and the skill contract; no adapter or procedure can be written without them.
- **Runtime support (0012, 0013).** Context policy and audit are accepted
  invariants that even the MVP must satisfy; their specifications are therefore
  required.
- **Interaction contract (0015).** The MVP must present evidence and collect
  approvals; the semantic contract for doing so is required.
- **Process and scope (0003, 0019, 0020).** The process by which everything is
  ratified, the definition of the MVP, and the build blueprint are the gates that
  make "start coding" a defined moment.

**Post-MVP (4):** RFC-0014, RFC-0016, RFC-0017, RFC-0018.

Rationale:

- **RFC-0014 (Resume/Recovery)** — the MVP can be session-scoped and may lose
  state on exit; its interruption *invariants* are already normative in RFC-0002.
  Caveat: this RFC is likely to amend RFC-0002, so its core decisions should be
  recorded early (see §6).
- **RFC-0016 (Configuration)** — the MVP needs only trivial provider selection;
  the full configuration architecture grows with the product. The default-deny
  posture is already fixed upstream.
- **RFC-0017 (Compatibility)** — nothing to be compatible with before the first
  release; but it must be written *before the first public release*.
- **RFC-0018 (Deployment)** — shipping mechanics are implementation; the release
  commitments are formalized before the first public release.

Note: RFC-0011 and RFC-0009 are "Required" in their *core* scope only. RFC-0011's
ecosystem half (registry, review, trust ratings) and RFC-0009's telemetry half
are explicitly deferred to the post-MVP phase; their deferred parts are recorded
inside the RFCs so nothing is silently dropped.

---

## 6. RFCs Likely to Change Others

These RFCs have the widest blast radius: decisions they make will force
amendments or rework in other documents. They should be written early and
treated as high-stakes reviews.

1. **RFC-0008 — Approval & Policy Engine.** Its decisions (approval granularity,
   retry policy, blocked-action overrides, standing approvals) touch the runtime
   (0002's execution gate), every skill contract (0011), the interaction contract
   (0015's approval UX), and the audit's most important records (0013). It is the
   single highest-blast-radius document.
2. **RFC-0005 — Fact Model.** Every component consumes facts: providers (0010),
   skills (0011), context (0012), verification (0006), and the interface (0015).
   A change to the fact model ripples through all of them.
3. **RFC-0007 — Trust Model.** The data-flow rules bind every component. A
   change to how untrusted text is handled changes the provider contract, the
   skill contract, context, and audit simultaneously.
4. **RFC-0010 — Provider Contract.** The internal representation is the joint
   between the Core and every vendor. Changing it requires touching every adapter
   and the orchestration rules that consume provider output.
5. **RFC-0011 — Skill System.** The skill format is consumed by diagnostics,
   execution, approval, and the interface. Ecosystem trust decisions (what is
   "trusted") interact with the security spine and may force changes there.
6. **RFC-0006 — Verification & Rollback.** Its definition of "verified" directly
   constrains the runtime invariants in 0002 and the fact model's staleness rules
   in 0005.
7. **RFC-0014 — Session Persistence, Resume & Recovery.** Although Post-MVP, it
   is the one deferred RFC most likely to **amend an accepted RFC** (0002's
   interruption/resume semantics, and possibly 0008's attended-execution policy).
   Because of this, its core semantics should be agreed as a decision record
   during the pre-MVP phase even though the full document waits.
8. **RFC-0015 — Operator Interface.** Approval-presentation decisions can force
   rework in the approval engine (0008) if the two are written without
   cross-checking; they must be developed against each other.

---

## 7. Recommended Writing Order

The exact order in which the remaining RFCs should be written. Each phase's
output unblocks the next. All RFCs in a phase may be drafted in parallel, but
must be **accepted in phase order** so dependencies are never speculative.

**Phase 0 — Process**
1. **RFC-0003** (RFC Governance) — defines how everything else is ratified.

**Phase 1 — Safety spine**
2. **RFC-0007** (Trust Model) — the frame every component obeys.
3. **RFC-0008** (Approval & Policy) — the gate; highest blast radius, so early.

**Phase 2 — Domain spine**
4. **RFC-0004** (System Model) — the thing facts describe.
5. **RFC-0005** (Fact Model) — the spine of all consumption.
6. **RFC-0006** (Verification & Rollback) — expressed in facts, so after 0005.

**Phase 3 — Provider and secrets**
7. **RFC-0009** (Secrets & Privacy) — the provider must be designed within it.
8. **RFC-0010** (Provider Contract) — the MVP's first provider adapter needs it.

**Phase 4 — Extension and runtime support**
9. **RFC-0011** (Skill Contract) — built on the gate and the fact model.
10. **RFC-0012** (Context & Memory) — assembled from facts, bounded by privacy.
11. **RFC-0013** (Audit & Transcript) — records the gate, so after 0008.

**Phase 5 — Operator and scope**
12. **RFC-0015** (Operator Interface) — the MVP's interaction contract.
13. **RFC-0019** (MVP Definition) — the first scoping document; ratifies this
    roadmap's Required/Post-MVP split.

**Phase 6 — The gate before code**
14. **RFC-0020** (Implementation Blueprint) — the final document before
    production code.

**Phase 7 — Post-MVP (written only after the MVP ships or is frozen)**
15. **RFC-0014** (Session Persistence & Resume) — core decisions recorded early
    as a decision record; full RFC after MVP.
16. **RFC-0016** (Configuration) — grows with the product.
17. **RFC-0017** (Compatibility) — required *before first public release*.
18. **RFC-0018** (Deployment) — required *before first public release*.

Writing order by RFC number, for quick reference:
**0003 → 0007 → 0008 → 0004 → 0005 → 0006 → 0009 → 0010 → 0011 → 0012 → 0013 → 0015 → 0019 → 0020** then **0014 → 0016 → 0017 → 0018**.

---

## 8. Coverage: Where Every Open Question Is Answered

Every open question raised by RFC-0001 and RFC-0002 is owned by exactly one of
the RFCs above. This appendix exists so no question is lost between documents.

### RFC-0001 open questions → owning RFC
| Q | Question | Owned by |
|---|---|---|
| 1–2 | Risk taxonomy, gates, approval granularity | RFC-0008 |
| 3 | Elevation mechanism | RFC-0008 |
| 4 | Read-only allowlist | RFC-0008 |
| 5 | Standing approvals | RFC-0008 |
| 6 | Fact normalization across distros | RFC-0005 |
| 7 | Immutable systems | RFC-0004 |
| 8 | Output bounds / truncation | RFC-0005 |
| 9 | Fact staleness | RFC-0005 |
| 10–11 | Verification definition, rollback promises | RFC-0006 |
| 12 | Catastrophic failure surfacing | RFC-0006 |
| 13 | Persistence model | RFC-0012 |
| 14 | Secret redaction | RFC-0009 |
| 15 | Telemetry / opt-in | RFC-0009 |
| 16–18 | Provider variance, representation, degraded UX | RFC-0010 |
| 19–22 | Skill packaging, review, sandboxing, audit | RFC-0011 |
| 23 | Network access policy | RFC-0008 |
| 24 | Concurrent diagnostics | RFC-0005 |
| 25 | Supported distro families | RFC-0004 |
| 26 | Cost controls | RFC-0010 |
| 27 | Compatibility policy | RFC-0017 |

### RFC-0002 open questions → owning RFC
| Q | Question | Owned by |
|---|---|---|
| 1–2 | Approval granularity, retry semantics | RFC-0008 |
| 3 | Timeouts | RFC-0008 |
| 4 | Read-only allowlist | RFC-0008 |
| 5 | Idle/awaiting drift | RFC-0005, RFC-0014 |
| 6 | Resume lifetime | RFC-0014 |
| 7 | Attended vs. unattended execution | RFC-0008, RFC-0014 |
| 8 | Reboot-resume verification | RFC-0014 |
| 9 | Interrupted-action reconciliation | RFC-0014 |
| 10 | Multiple goals | RFC-0014 |
| 11 | Degraded-mode scope | RFC-0010 |
| 12 | Context-routing of replies | RFC-0012 |
| 13 | Blocked-action lifecycle | RFC-0008 |
| 14 | Input during execution | RFC-0014 |
| 15 | Concurrent collection | RFC-0005 |
| 16 | Diagnostic-only goals evidence bar | RFC-0006 |
| 17 | Watchdog scope | RFC-0005 |

---

## 9. Risks to the Roadmap

1. **Post-MVP drift.** Four RFCs are deferred, and deferred documents tend to be
   forgotten. The mitigation is the ownership appendix (§8): every open question
   has a named home, and RFC-0019 must ratify the split so "post-MVP" is a
   reviewed decision, not a habit.
2. **RFC-0014 amending RFC-0002.** The most likely way an accepted RFC changes.
   If session persistence is specified late, its reconciliation rules may
   contradict RFC-0002's interruption semantics. Mitigation: record its core
   decisions early (see §6.7) even though the document is Post-MVP.
3. **Blast-radius RFCs written too late.** If RFC-0008 or RFC-0005 were drafted
   after the documents that depend on them, the dependent documents would be
   speculative. The writing order (§7) exists to prevent this and must be
   enforced at the review gate.
4. **The roadmap itself as a gate.** RFC-0000 is an index, not a committee. If it
   is treated as requiring approval for *every* RFC, it slows the project; it is
   meant to be amended mechanically as RFCs are accepted.
5. **MVP definition contradicting the Required set.** RFC-0019 could conclude
   that some Required RFC's subject is unnecessary for the MVP, or that a
   Post-MVP RFC is actually needed earlier. That is legitimate — but it must be a
   *ratified change* to this roadmap, not an unrecorded deviation.
6. **Category boundaries blurring.** Security, Runtime, and Domain subjects
   overlap (verification is both domain and runtime; skill trust is both security
   and extension). Each RFC names its dependencies; where two RFCs would own the
   same question, the earlier-accepted document wins and the later one references
   it rather than redecides it.

---

*End of RFC-0000. Normative for this document: sections 1–7. Sections 8–9 are
explanatory and maintained alongside. This document is amended whenever an RFC
changes status or the Required/Post-MVP split is ratified.*
