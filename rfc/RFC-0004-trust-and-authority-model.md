# RFC-0004 — Trust and Authority Model

**Status:** Draft
**Date:** 2026-08-01
**Scope:** Who may do what: authority, ownership, and trust boundaries across every actor
**Audience:** Future maintainers
**Supersedes:** Nothing
**Depends on:** RFC-0000 (as amended by this RFC's roadmap change), RFC-0001, RFC-0002, RFC-0003 (all accepted)

**Roadmap note:** This RFC replaces the subject originally reserved in RFC-0000 as
"RFC-0004 — System Model & Supported Platforms." That subject is renumbered to
**RFC-0021** and remains Required. The reassignment is recorded as an amendment
to RFC-0000 (§8 of this document records the intent; the actual amendment is in
RFC-0000's amendment log).

**BREAKING:** No. This RFC adds normative content and reassigns a reserved
roadmap number; it does not weaken any Principle, Boundary, Invariant, or
canonical Definition in an accepted RFC.

---

## 0. Preamble

RFC-0001 established the architecture's safety principles; RFC-0002 fixed the
runtime state machine and its invariants; RFC-0003 fixed the vocabulary and the
process. None of them answered the question this RFC answers, completely and
centrally:

> **WHO may do WHAT?**

Concretely, this RFC specifies:

- who **owns** each consequential thing (the machine, the session, truth, the
  permissions, execution, policy, memory, risk classification);
- every **actor** and what authority it holds;
- the **authority levels** that structure all decision-making;
- that authority **flows downward** and that nothing may grant itself authority
  upward;
- the separation between **trust** and **authority** (an untrusted actor may
  still hold bounded authority; a trusted actor may still be forbidden from
  deciding);
- an **Authority Matrix** stating, for every actor and every authority, whether
  it is **Allowed**, **Forbidden**, or **Conditional**;
- the **architectural invariants** that make these grants enforceable, not
  aspirational;
- a per-actor **abuse-case analysis**: what happens if an actor is malicious,
  compromised, or fails, and why the architecture stays safe anyway.

This RFC is the *authority model only*. It deliberately does **not** specify the
mechanics that other RFCs own: data-flow and sanitization (RFC-0007), the risk
taxonomy and approval gates (RFC-0008), secrets (RFC-0009), the provider
contract (RFC-0010), the skill contract (RFC-0011), context and memory
(RFC-0012), or audit (RFC-0013). Where this RFC and a later RFC would both own
the same question, the earlier-accepted document wins (RFC-0003 Part II §1).

**Reading notes.**

- Normative content uses the canonical vocabulary of RFC-0003 Part I. Any new
  term introduced here is defined at first use and flagged in §11 for inclusion
  in RFC-0003.
- The Authority Matrix (§7) is the normative core. The abuse-case analysis (§9)
  is what makes the matrix *believable*.
- Cells in the matrix are abbreviated; the legend is in §7.

---

## 1. The Authority Model in One Page

### 1.1 Ownership at a glance

| Thing | Owned by | How exercised |
|---|---|---|
| **Machine** | The **Operator** | Ultimate authority; everything the Assistant does is a delegation from the Operator's ownership. |
| **Session** | The **Operator** | The Operator starts, resumes, and ends it; the Orchestrator manages it. |
| **Truth** (Facts) | The **Fact Layer** | Facts are the only claims treated as "known"; they are never LLM-authored, never Operator-authored. |
| **Permissions** | The **Operator**, through the **Policy Engine** | The Operator sets Policy; the Policy Engine applies it deterministically. |
| **Execution** (changing Machine State) | The **Executor** | The *only* actor with the Execute authority. |
| **Policy** | The **Policy Engine** | Deterministic, never LLM-authored. |
| **Memory** | The **Operator**, through the **Context Manager** | Durable only by explicit Operator consent. |
| **Risk classification** | The **Policy Engine** | Deterministic; never the LLM's self-assessment. |
| **Proposals / Plans** | The **Orchestrator** | The Orchestrator normalizes and owns the Plan presented for Approval. |
| **Actions** | The **Executor**, once approved | A Proposal becomes an Action the Executor may run only when an Approval Token binds it. |
| **Verification** | The **Fact Layer** | State-based, deterministic; never the LLM's assessment. |
| **Failure / Recovery** | The **Orchestrator** | Defined response in a fixed order; never assumed, never hidden. |
| **Rollback** | The **Operator**, through the **Executor** | Rollback is an Action requiring its own Approval. |

### 1.2 Authority levels at a glance

The nine authorities, in the order they must be *exercised* in a session:

**Observe → Propose → Infer → Verify → Approve → Execute → Refuse → Persist → Explain**

- **Observe** — gather Observations from the Machine (read-only).
- **Propose** — offer a candidate Proposal, Plan, Step, or Hypothesis.
- **Infer** — form Hypotheses from Evidence.
- **Verify** — confirm, deterministically, that an executed Action produced its
  Post-condition.
- **Approve** — grant the Operator's authorization for an Action or Plan.
- **Execute** — change Machine State.
- **Refuse** — decline to proceed; the fail-safe floor.
- **Persist** — write durable records (Memory, Audit, Context).
- **Explain** — account for a decision or a piece of Evidence to the Operator.

### 1.3 The three sentences

1. **Authority flows downward.** Operator → Policy → Approval → Execution. A
   grant flows from a higher authority to a lower one, never the reverse, and no
   actor may extend its own authority.
2. **Trust and authority are separate axes.** The LLM is trusted for nothing but
   *is allowed to propose*; the Fact Layer is trusted for truth *but may decide
   nothing*. Neither axis licenses the other.
3. **The blast radius of any single actor is bounded.** No actor can both invent
   an action and execute it. The matrix (§7) and invariants (§8) make that
   bounding structural.

---

## 2. Definitions

The following terms are defined here because RFC-0003 does not define them (or,
for **Authority** and **Trust**, because the project's sense must be sharpened
beyond their everyday use). All are flagged for RFC-0003 Part I (§11).

**Actor**
- **Definition:** Any entity that holds authority, exercises authority, or
  produces untrusted input in the system: the Operator, the Assistant, and the
  Assistant's components (Orchestrator, Provider, Diagnostics Layer, Fact Layer,
  Policy Engine, Approval Engine, Executor, Skills, Context Manager, Audit
  System).
- **Is not:** A role a person plays on a forum; not a privilege group in an OS.
- **Relates to:** Authority, the Authority Matrix.

**Authority**
- **Definition:** The sanctioned capacity to do a specific thing — observe,
  propose, infer, verify, approve, execute, refuse, persist, or explain — held
  by an Actor and expressed in this RFC's matrix. Authority is always a
  *delegation*: it originates at the Operator and is granted downward. Authority
  without a grant is a violation (an invariant).
- **Is not:** Knowledge; a capability a component happens to have; permission to
  do anything; the trustworthiness of the holder.
- **Relates to:** Operator, delegation, the Authority Matrix, Invariant A4.

**Trust**
- **Definition:** The decision to treat an Actor's output as input to a
  deterministic check without independently re-deriving it. Trust is the *opposite
  of verification*: you trust what you do not re-check. It is always scoped to a
  specific kind of output (e.g., "trust the Fact Layer for Facts") and always
  revocable by design.
- **Is not:** Authority; a relationship; an assumption of benevolence; a
  default. RFC-0001's default posture is *untrusted until proven otherwise*.
- **Relates to:** Provider (untrusted), Fact Layer (trusted for Facts),
  Sanitization (RFC-0007).

**Ownership**
- **Definition:** For each consequential thing (Machine, Session, truth,
  permissions, execution, policy, memory, risk classification, Plans, Actions,
  Verification, Failure, Rollback), the Actor accountable for it. Ownership is a
  *responsibility*; authority is the *tool* that lets the owner discharge it. A
  thing has exactly one owner (§1.1).
- **Is not:** Possession in the legal sense; the thing itself; authority by
  itself.
- **Relates to:** Authority, the ownership table (§1.1).

**Delegation**
- **Definition:** The downward grant of authority from a higher authority to a
  lower one. Delegation is always bounded (by Policy, by an Approval Token, by a
  Contract) and always recorded (Audit).
- **Is not:** Abandonment of accountability; a permanent transfer; an upward
  grant.
- **Relates to:** Authority, Operator, Approval Token.

**Orchestrator** (new)
- **Definition:** The deterministic component that runs the session: it owns the
  Goal, consults the other components in the RFC-0002 order, assembles and
  normalizes Plans from Proposals, requests classification and Approval,
  schedules approved Actions through the Executor, and drives Replanning,
  Failure, and Recovery. It is the Assistant's executive loop.
- **Is not:** The LLM; a source of Facts; a source of Hypotheses; the Executor.
- **Relates to:** Session, Goal, Plan, Step, Replanning, Recovery, RFC-0002.

**Provider**
- **Definition:** RFC-0003 §2.1 — the adapter to one LLM backend. The source of
  model output; model output is untrusted data.
- **Is not:** The model itself (but colloquial "the AI" maps here); an authority
  (see §7: it may Propose and Infer, nothing else).
- **Relates to:** Provider View, Context Manager, RFC-0010.

**Diagnostics Layer**
- **Definition:** The deterministic, read-only capability that runs Collectors
  against the Machine and produces Observations. It is the *only* actor that
  inspects the Machine (besides the Operator). RFC-0005 owns its collector
  contract.
- **Is not:** A source of Facts (Observations are untrusted until normalized); a
  source of Hypotheses; a mutation path.
- **Relates to:** Collector, Observation, Inspection, RFC-0005.

**Fact Layer**
- **Definition:** The deterministic component that normalizes Observations into
  Facts, checks provenance and staleness, holds the current Machine State, and
  performs Verification by state comparison. It is the *owner of truth*: the
  only place factual claims about the Machine are established.
- **Is not:** A decision-maker; an interpreter of meaning (Diagnosis is LLM and
  Skill work); a source of Hypotheses.
- **Relates to:** Observation, Fact, Machine State, Verification, RFC-0005,
  RFC-0006.

**Policy Engine**
- **Definition:** The deterministic component that classifies proposed Actions
  into Risk classes and gates (auto-permitted, confirm, confirm-with-warning,
  blocked), and applies Policy — default-deny, allowlists, elevation limits,
  standing-approval bounds. It decides what *may* be proposed onward. RFC-0008
  owns the taxonomy.
- **Is not:** The Approver (the Operator is); the LLM's judgment; an execution
  path.
- **Relates to:** Policy, Risk, Approval, RFC-0008.

**Approval Engine**
- **Definition:** The deterministic component that administers Approval: it
  presents the classified Proposal to the Operator, captures the Operator's
  decision, mints the scoped Approval Token, and re-validates it at the
  execution gate. It is the Operator's administrative arm for approval, never
  the decision-maker.
- **Is not:** The Approver; a decision-maker; a policy author.
- **Relates to:** Approval, Approval Token, Operator, RFC-0008, RFC-0002
  (Awaiting Approval, invariant 11).

**Executor**
- **Definition:** The component that runs approved Actions against the Machine —
  the *only* actor with Execute authority and the only path that changes Machine
  State. It executes only Actions bound to a valid, unexpired, state-consistent
  Approval Token, and never invents Actions.
- **Is not:** A planner; a verifier; a decision-maker; a shell that runs
  arbitrary strings.
- **Relates to:** Action, Approval Token, Execution, Verification (which it does
  not perform), RFC-0002 (Executing state, invariants 2 and 11).

**Context Manager**
- **Definition:** The deterministic component that builds Context from Facts and
  history, applies sanitization and purpose-limits, enforces the "no secrets to
  providers" boundary (RFC-0009), assembles the Provider View, and manages
  Memory under Operator consent.
- **Is not:** A source of Facts; a source of Hypotheses; a decision-maker.
- **Relates to:** Context, Provider View, Memory, RFC-0001 §9, RFC-0009,
  RFC-0012.

**Audit System**
- **Definition:** The deterministic, append-only, tamper-evident record of
  consequential events, written *before* each consequence is allowed to proceed
  (RFC-0002 invariant 13). Its purpose is transparency, not forensics.
- **Is not:** A decision-maker; a source of Facts for reasoning; a log of
  everything the model said.
- **Relates to:** Audit, Transcript, RFC-0013.

**Skills**
- **Definition:** RFC-0003 §2.7 — packaged, versioned, authenticated procedures:
  diagnostics, explanations, and gated Action sequences. Untrusted by default
  until authenticated and within Policy.
- **Is not:** Core behavior; an authority above Policy.
- **Relates to:** Collector, Plan, Approval, RFC-0011.

---

## 3. What Each Actor Owns

This section is the normative version of §1.1. "Owns" means: the owner is
accountable for the thing; the owner either holds the authority to act on it or
holds it through a named delegation. **Exactly one owner per row.**

| Thing | Owner | Delegated through | Never owned by |
|---|---|---|---|
| Machine | Operator | — | Everyone else |
| Session | Operator | Orchestrator (management) | Provider, Skills, Diagnostics, Fact Layer, Policy Engine, Approval Engine, Executor, Context Manager, Audit System |
| Truth (Facts) | Fact Layer | — | LLM, Provider, Skills, Orchestrator, Operator, Context Manager |
| Permissions | Operator | Policy Engine (policy), Approval Engine (tokens) | LLM, Provider, Skills, Executor |
| Execution | Executor | — | Provider, Skills, Policy Engine, Approval Engine, Diagnostics, Fact Layer, Orchestrator |
| Policy | Policy Engine | — | LLM, Provider, Skills, Operator (who sets but does not administer), Executor |
| Memory | Operator (consent) + Context Manager (custody) | Context Manager | Provider, Skills, Diagnostics, Fact Layer, Policy Engine, Approval Engine, Executor |
| Risk classification | Policy Engine | — | LLM, Provider, Skills, Operator (who sets policy bounds, not the per-action class) |
| Proposals / Plans | Orchestrator | — | Provider and Skills *originate* Proposals; only the Orchestrator *owns* the normalized Plan |
| Actions (after Approval) | Executor | Approval Token | Everyone else |
| Verification | Fact Layer | — | LLM, Provider, Skills, Executor, Operator |
| Failure / Recovery | Orchestrator | — | Provider, Skills, Executor (who may report, never define the response) |
| Rollback | Operator (decision) | Executor (execution) | Provider, Skills, Policy Engine, Approval Engine |

Two ownership rules follow:

1. **Ownership is not delegable into self-extension.** An owner may use a
   delegated authority within its bounds but may never widen its own grant
   (Invariant A4).
2. **Ownership of truth and ownership of decisions never coincide.** The actor
   that establishes what is true (Fact Layer) decides nothing; the actor that
   decides what to do (Operator, Orchestrator) is not a source of Facts. This is
   the project's answer to "who may say both what is and what should be."

---

## 4. The Actors: Full Profiles

Each actor below lists: **Definition** (where already in RFC-0003, summarized;
otherwise as §2), **Responsibilities**, **Authority** (the levels it may hold,
with the matrix cell), **May decide**, **May never decide**, **Trusts**,
**Does not trust**, **Depends on**.

### 4.1 Operator (the human)
- **Definition:** RFC-0003 §2.1 — the human who runs the Assistant on their own
  machine and holds ultimate authority over it.
- **Responsibilities:** Owns the Machine and the Session; sets Goals; sets
  Policy bounds; reviews Evidence and Proposals; grants or withholds Approval;
  consents to durable Memory; reads Audit and Transcript at any time; is the
  final actor on the machine regardless of the Assistant's state.
- **Authority:** All nine levels, as **Conditional** — every one is a human
  decision, exercised *through* the Assistant's presentation. The Operator does
  not hold a bypass: the Assistant may decline (Refuse) what violates Policy or
  an invariant (see §9.1).
- **May decide:** whether to approve; whether to override a warning (within the
  bounds RFC-0008 defines); whether the Assistant may remember; whether to
  inspect anything on the machine; whether to stop the session.
- **May never decide:** what is *true* (Facts); what a Risk class is; that an
  unverified Action is verified; that an invariant is waived.
- **Trusts:** the Assistant to present honestly; the Audit to be accurate about
  what was done.
- **Does not trust:** the LLM's statements as Facts; Skills by default.
- **Depends on:** the Assistant's deterministic layers for normalized,
  trustworthy Evidence and safe presentation.

### 4.2 Assistant (the composite)
- **Definition:** RFC-0003 §2.1 — the whole product: orchestration core,
  deterministic layers, and the providers and skills in use.
- **Responsibilities:** Present the combined capability to the Operator; route
  decisions to the right owner; enforce the invariants of RFC-0002 and this RFC.
- **Authority:** *No authority of its own.* The Assistant is the sum of its
  components' authorities (§7); it holds no authority the components do not. Its
  "capabilities" are the composed, bounded authorities of its parts.
- **May decide:** nothing beyond what its components may decide (i.e., nothing).
- **May never decide:** Facts, Risk, Approval, Execution, Verification — by
  construction, these live in specific components, never in "the Assistant as a
  whole."
- **Trusts:** its deterministic components within their contracts; neither
  Providers nor Skills by default.
- **Does not trust:** anything untrusted (RFC-0001 §7).
- **Depends on:** its components.

### 4.3 Orchestrator
- **Definition:** §2. The session's executive loop.
- **Responsibilities:** Run the RFC-0002 state machine; own the Goal; consult
  components in order; normalize Proposals into Plans/Steps; present Plans and
  Evidence for Approval; schedule approved Actions; drive Replanning, Failure,
  and Recovery in the fixed order (establish state, disclose, obtain decision,
  act on approval).
- **Authority:** Propose (owns the Plan), Refuse (may halt the session), Explain
  (presents status and Evidence). It does **not** Observe the machine, Infer,
  Verify, Approve, Execute, or Persist on its own.
- **May decide:** when to consult which component; whether a Plan is complete and
  coherent enough to present; whether to replan; whether to halt on a Failed
  invariant (Fail-safe).
- **May never decide:** Facts (Fact Layer); Risk classification (Policy Engine);
  Approval (Operator); what to execute (Executor); that Verification passed
  (Fact Layer).
- **Trusts:** Fact Layer (Facts), Policy Engine (classification), Audit System
  (record).
- **Does not trust:** Provider output, Skill output (until processed and
  classified).
- **Depends on:** RFC-0002 (the loop it runs), Fact Layer, Policy Engine,
  Approval Engine, Executor, Context Manager, Audit System.

### 4.4 Provider (and the LLM behind it)
- **Definition:** RFC-0003 §2.1, §2.1 LLM.
- **Responsibilities:** Translate Context (as Provider View) into model output:
  Hypotheses, explanations, and proposed Actions. It is the *only* source of
  reasoning (besides Skills).
- **Authority:** Propose, Infer, Explain. Nothing else. In particular it may not
  Observe the machine, Verify, Approve, Execute, or Persist.
- **May decide:** what it proposes and infers (as untrusted candidates).
- **May never decide:** that its output is true (Facts are Fact Layer's); that
  its output is safe (Policy Engine's); that it may run (Executor's); that it
  was approved (Operator's).
- **Trusts:** nothing about the machine — it never sees it.
- **Does not trust:** (n/a — it is the untrusted source.)
- **Depends on:** Provider View (from Context Manager).

### 4.5 Diagnostics Layer
- **Definition:** §2.
- **Responsibilities:** Run Collectors deterministically, read-only; produce
  Observations with provenance; enforce output bounds (RFC-0005).
- **Authority:** Observe (the machine), Verify (as the re-observation arm of
  Verification). Nothing else: no Propose, no Infer, no Approve, no Execute, no
  Persist.
- **May decide:** what a Collector measures, within its declared contract.
- **May never decide:** what an Observation *means* (that is Diagnosis, an Infer
  activity); whether the machine should change; to mutate anything.
- **Trusts:** Collector definitions (from the skill/core contract).
- **Does not trust:** its own Observations until normalized (they are untrusted
  data until the Fact Layer checks them).
- **Depends on:** RFC-0005 (collector contract), Fact Layer (normalization).

### 4.6 Fact Layer
- **Definition:** §2.
- **Responsibilities:** Normalize Observations into Facts; enforce provenance and
  staleness bounds; maintain Machine State; perform Verification by state
  comparison (before/after).
- **Authority:** Verify (owns Verification), Observe (as the consumer of
  Observations). It does **not** Infer, Propose, Approve, Execute, or Persist.
- **May decide:** what is a Fact, and whether a Post-condition was met.
- **May never decide:** what to do; what the Facts mean (interpretation is
  Infer); whether to change the machine.
- **Trusts:** Observations only after deterministic checks (it is the checker,
  so it trusts the check, not the input).
- **Does not trust:** LLM statements, Hypotheses, Skill claims — none of these
  are Facts (RFC-0001 §3.5).
- **Depends on:** Diagnostics Layer (Observations), RFC-0005, RFC-0006.

### 4.7 Policy Engine
- **Definition:** §2.
- **Responsibilities:** Classify every proposed Action into a Risk class and gate;
  apply default-deny, allowlists, elevation limits, standing-approval bounds;
  fail closed on errors (RFC-0008).
- **Authority:** Refuse (the blocked gate is a refusal), Propose (procedurally,
  as a Policy decision) — narrowly. It does **not** Approve, Execute, Observe
  the machine, Infer, or Persist.
- **May decide:** an Action's Risk class and gate.
- **May never decide:** whether the Operator approves; what is true; to execute.
- **Trusts:** Facts (as inputs to classification).
- **Does not trust:** the LLM's risk self-assessment (Risk is never the LLM's
  estimate, RFC-0003 §2.7).
- **Depends on:** RFC-0008 (taxonomy), Fact Layer (facts it classifies against).

### 4.8 Approval Engine
- **Definition:** §2.
- **Responsibilities:** Present classified Proposals and Evidence to the
  Operator; capture the decision; mint the Approval Token; re-validate it at the
  execution gate (RFC-0002 invariant 11); invalidate it on state change, reboot,
  interrupt, or policy reload.
- **Authority:** Approve — **as the Operator's instrument only** (the matrix
  cell is Conditional: it carries the Operator's decision; it never decides).
  It does not Propose, Infer, Execute, or Persist.
- **May decide:** token validity (deterministic).
- **May never decide:** whether to approve; policy content; to extend a token's
  scope.
- **Trusts:** Policy Engine's classification, the Operator's decision.
- **Does not trust:** the LLM's assertion that an Action is needed.
- **Depends on:** RFC-0008, RFC-0002 (Awaiting Approval, invariant 11), Audit
  System (records the Approval).

### 4.9 Executor
- **Definition:** §2.
- **Responsibilities:** Run approved Actions against the Machine; execute only
  against a valid, unexpired, state-consistent Approval Token; never invent
  Actions; report completion for Verification.
- **Authority:** Execute (the sole Execute cell in the matrix). It does not
  Observe broadly, Propose, Infer, Approve, Verify, or Persist.
- **May decide:** how to run an approved Action within its declared bounds.
- **May never decide:** what to run (that was decided upstream); whether the
  result was correct (Verification is Fact Layer's); to chain unapproved
  Actions.
- **Trusts:** the Approval Token (it re-validates it; trust is limited to
  "the token is what the Approval Engine says it is").
- **Does not trust:** Proposals, LLM output, Skill content — it only ever sees
  approved, token-bound Actions.
- **Depends on:** Approval Engine (tokens), RFC-0002 (Executing, invariant 2 and
  11).

### 4.10 Skills
- **Definition:** RFC-0003 §2.7.
- **Responsibilities:** Provide packaged diagnostics (Collectors), explanations,
  and gated Action sequences with declared targets, privileges, risk, and
  verification.
- **Authority:** Propose, Infer, Explain (all as *candidates*). It does not
  Observe the machine itself, Verify, Approve, Execute, or Persist.
- **May decide:** what its packaged content proposes.
- **May never decide:** to bypass Policy (invariant S1); to execute; that its
  claims are Facts; that its procedures are safe.
- **Trusts:** the Facts its Collectors consume (via the Fact Layer).
- **Does not trust:** (n/a — untrusted by default until authenticated.)
- **Depends on:** RFC-0011 (contract), RFC-0008 (its Actions pass the same
  gate), RFC-0005 (it consumes Facts).

### 4.11 Context Manager
- **Definition:** §2.
- **Responsibilities:** Build Context from Facts; sanitize; enforce
  purpose-limits and size bounds; assemble Provider Views with **no secrets**
  (RFC-0009); manage Memory only by Operator consent.
- **Authority:** Observe (as a consumer of Facts), Persist (durable Context and
  Memory, under consent). It does not Propose, Infer, Approve, Execute, or
  Verify.
- **May decide:** what enters Context and the Provider View, within the bounds
  RFC-0009 and RFC-0012 set.
- **May never decide:** what is true; what to do; to include a secret; to
  persist without consent.
- **Trusts:** Fact Layer (Facts), Operator (consent).
- **Does not trust:** raw Observations, Provider output, Skill material (all
  sanitized before use).
- **Depends on:** RFC-0009, RFC-0012, RFC-0001 §9.

### 4.12 Audit System
- **Definition:** §2.
- **Responsibilities:** Record consequential events before their consequences;
  preserve append-only, tamper-evident history; expose Audit and Transcript to
  the Operator.
- **Authority:** Persist (it is the owner of durable record), Explain (it
  presents the record). It does not Propose, Infer, Approve, Execute, Observe
  the machine, or Verify.
- **May decide:** the format and ordering of the record (within RFC-0013).
- **May never decide:** to omit an event; to alter history; what an event means.
- **Trusts:** nothing about correctness (it records, it does not judge).
- **Does not trust:** any actor to be right — it records regardless.
- **Depends on:** RFC-0013, RFC-0002 invariant 13.

---

## 5. Authority Levels (Normative)

Each authority has an exact meaning. A cell in the matrix (§7) grants or
forbids exactly this.

| Level | Means | Owned by | Never held by |
|---|---|---|---|
| **Observe** | Run or drive read-only Inspection; gather Observations from the Machine. | Diagnostics Layer (runner), Fact Layer (consumer), Operator | Provider, Skills, Policy Engine, Approval Engine, Executor, Orchestrator, Context Manager |
| **Propose** | Offer a candidate Proposal/Plan/Step/Hypothesis for the pipeline. | Orchestrator (owns the Plan), Provider and Skills (originate), Policy Engine (procedural) | Diagnostics, Fact Layer, Approval Engine, Executor, Context Manager, Audit System, Operator (in-session) |
| **Infer** | Form Hypotheses from Evidence. | Provider, Skills | Fact Layer, Diagnostics, Policy Engine, Approval Engine, Executor, Orchestrator, Context Manager, Audit System |
| **Verify** | Confirm deterministically that a Post-condition holds, by state comparison. | Fact Layer (owns), Diagnostics (re-observation arm) | LLM, Provider, Skills, Executor, Orchestrator, Operator, Policy Engine, Approval Engine |
| **Approve** | Grant the Operator's authorization, recorded as a scoped Approval Token. | Operator (decision); Approval Engine (instrument) | LLM, Provider, Skills, Policy Engine, Executor, Orchestrator, Diagnostics, Fact Layer, Context Manager, Audit System |
| **Execute** | Change Machine State. | Executor (sole) | Everyone else, including the Operator *through the Assistant* (the Operator's own hands on the machine are outside the Assistant) |
| **Refuse** | Decline to proceed: the fail-safe floor. | Policy Engine (blocked gate), Orchestrator (halt), Operator (withhold), Executor (fail-closed), Approval Engine (won't mint) | Provider, Skills, Diagnostics, Fact Layer, Context Manager, Audit System |
| **Persist** | Write durable records. | Audit System (record), Context Manager (Context/Memory under consent) | Provider, Skills, Diagnostics, Fact Layer, Policy Engine, Approval Engine, Executor, Orchestrator |
| **Explain** | Account for decisions and Evidence to the Operator. | Orchestrator, Provider, Skills, Audit System, Fact Layer (provenance), Policy/Approval (rationale), Diagnostics (collection) | Executor (it reports, it does not explain), Context Manager (it assembles, not explains) |

---

## 6. The Flow of Authority (Normative)

Authority is a downward delegation. The canonical chain, each link narrower
than the last:

```
        Operator  (owns the Machine; the source of all authority)
           │  sets the bounds (Policy, consent)
           ▼
     Policy Engine  (what may even be proposed onward)
           │  classifies every Proposal
           ▼
     Approval Engine  (presents; mints the token on Operator's decision)
           │  a valid, scoped, state-consistent Approval Token
           ▼
        Executor  (runs the approved Action against the Machine)
           │
           ▼
     Fact Layer  (verifies the Post-condition)  →  Audit System records all of it
```

Rules that make the flow enforceable (each is an Invariant in §8):

1. **Downward only.** Authority moves from a higher authority to a lower one. A
   lower authority may not grant anything to a higher one (the Executor cannot
   grant the Operator permission; the Provider cannot grant itself Facts).
2. **No self-grant.** No actor may extend its own authority. The Policy Engine
   cannot approve what it classifies; the Executor cannot approve what it runs;
   the Approval Engine cannot widen a token.
3. **Approval is the gate between Propose and Execute.** Nothing executes that
   did not pass Policy classification, Operator approval, and token validation.
4. **Verification is downstream of execution, owned by a different actor.** The
   actor that changed the machine never confirms the change.
5. **Every consequence is preceded by its record.** The Audit System writes
   before the consequence proceeds (RFC-0002 invariant 13), so the downward flow
   is always traceable.

---

## 7. The Authority Matrix (Normative)

Legend: **A** = Allowed (unconditional within the actor's contract); **F** =
Forbidden (a violation if it happens — an invariant); **C** = Conditional
(allowed only when the stated condition holds). The matrix is the normative
statement of who may do what. Any real-world act that contradicts a cell is a
design defect (RFC-0001 §0), not an acceptable behavior.

| Actor | Observe | Propose | Infer | Verify | Approve | Execute | Refuse | Persist | Explain |
|---|---|---|---|---|---|---|---|---|---|
| **Operator** | A | C¹ | A | C¹ | **A** | C² | A | C³ | A |
| **Assistant** | C⁴ | C⁴ | C⁴ | C⁴ | F | F | C⁴ | C⁴ | A |
| **Orchestrator** | F | **A** | F | F | F | F | **A** | F | **A** |
| **Provider** | F | **A** | **A** | F | F | F | F | F | **A** |
| **Diagnostics Layer** | **A** | F | F | C⁵ | F | F | F | F | C⁶ |
| **Fact Layer** | C⁷ | F | F | **A** | F | F | F | F | C⁸ |
| **Policy Engine** | F | C⁹ | F | F | F | F | **A** | F | C¹⁰ |
| **Approval Engine** | F | F | F | F | C¹¹ | F | C¹² | F | C¹³ |
| **Executor** | F | F | F | F | F | **A** | C¹⁴ | F | C¹⁵ |
| **Skills** | F | **A** | **A** | F | F | F | F | F | **A** |
| **Context Manager** | C¹⁶ | F | F | F | F | F | F | C¹⁷ | C¹⁸ |
| **Audit System** | F | F | F | F | F | F | F | **A** | **A** |

### Conditions (the "C" cells)

1. **Operator / Propose:** the Operator may state Goals and wishes; those become
   Proposals through the Orchestrator's normalization, not as raw commands.
2. **Operator / Execute:** the Operator's own actions on the machine, outside
   the Assistant, are unrestricted by the Assistant (they are the Operator's
   machine). *Through* the Assistant, the Operator may only Execute approved
   Actions; the Assistant never provides an unapproved execution path.
3. **Operator / Persist:** durable Memory only by the Operator's own consent
   (RFC-0001 §9).
4. **Assistant / (all):** the Assistant acts *only through its components*. Each
   C cell inherits the underlying component's condition; the composite itself
   has no independent authority.
5. **Diagnostics / Verify:** performs the re-observation that Verification
   compares; it does not render the verdict (Fact Layer does).
6. **Diagnostics / Explain:** may explain how an Observation was collected
   (provenance), not what it means.
7. **Fact Layer / Observe:** consumes Observations from the Diagnostics Layer;
   it does not run Collectors itself.
8. **Fact Layer / Explain:** may explain a Fact's provenance and staleness.
9. **Policy Engine / Propose:** procedural only — its output is a
   classification/gate, not a candidate Action.
10. **Policy Engine / Explain:** must be able to state why a gate was applied.
11. **Approval Engine / Approve:** *as the Operator's instrument only*; it
    mints tokens on the Operator's decision and never decides itself.
12. **Approval Engine / Refuse:** it will not mint a token for a blocked or
    expired request; it does not decide policy.
13. **Approval Engine / Explain:** may explain what a token covers and why it was
    granted, never why the Operator *should* approve.
14. **Executor / Refuse:** fail-closed: it refuses to execute when the token is
    invalid, expired, or state-inconsistent (RFC-0002 invariant 11).
15. **Executor / Explain:** reports *what* was executed and its result for
    Verification; it does not interpret.
16. **Context Manager / Observe:** consumes Facts for Context; does not inspect
    the machine.
17. **Context Manager / Persist:** durable Context/Memory only under Operator
    consent and purpose-limits.
18. **Context Manager / Explain:** may show what entered/exited Context and why
    (the sanitization record), not a machine account.

### Reading the matrix

- **The Execute column has exactly one A.** Everything else in that column is F.
  There is no second path that changes Machine State.
- **The Approve column has exactly one A (the Operator) and one C (the
  instrument).** Nobody else may approve anything.
- **The Verify column has exactly one A (Fact Layer) plus a C arm
  (Diagnostics).** Verification is never delegated to the LLM, the Executor, or
  the Orchestrator.
- **The Infer column is entirely A-or-F with no C:** it is held only by Provider
  and Skills, the two untrusted sources of reasoning, and by no deterministic
  component. Deterministic layers never form Hypotheses.
- **The Persist column's A cells are the Audit System (record) and the Context
  Manager (consent-bound Context/Memory).** Durable write is always recorded,
  always consent-bound, never the LLM's or a Skill's.

---

## 8. Architectural Invariants (Normative)

These invariants make the authority model structural. They join RFC-0002 §9 as
invariants no implementation may violate and no later RFC may weaken except by
amendment (RFC-0003 Part II §1). Each is named for reference.

- **A1 — Provider never executes.** The Provider boundary has no execution path
  (RFC-0001 §7, §8). Model output can at most become a Proposal; it can never
  become a command. *Blast radius:* the worst an LLM can do is propose.
- **A2 — Executor never invents Actions.** The Executor runs only Actions bound
  to a valid, unexpired, state-consistent Approval Token (RFC-0002 invariants 2
  and 11). It has no Propose authority and no shell of its own.
- **A3 — Skill never bypasses Policy.** Every Skill Action passes the same
  classification and Approval gate as any other Action (RFC-0001 §11, RFC-0008).
  A Skill has no authority to propose around the gate, and no execution path.
- **A4 — Diagnostics never mutates.** The Diagnostics Layer is read-only by
  construction; it has no Execute authority and no write path to the Machine.
- **A5 — Verification never assumes success.** Verification is state-based
  re-observation and comparison (RFC-0002 invariant 2). It is never "the command
  exited zero" and never the LLM's assessment (RFC-0003 §2.6 Verification).
- **A6 — Policy never executes commands.** The Policy Engine classifies and
  gates; it has no execution authority and no shell. (Reinforces A1.)
- **A7 — Audit never changes history.** The Audit System is append-only and
  tamper-evident (RFC-0002 invariant 13). No actor may edit or erase a prior
  record.
- **A8 — Authority flows downward; nothing grants itself authority upward.**
  Every grant originates at the Operator and narrows downward. No actor may
  extend its own authority, and no lower actor may grant authority to a higher
  one. The matrix is closed: authority not granted by the matrix does not exist.
- **A9 — The gate is the only path to execution.** State-changing work exists
  only through Proposal → Policy classification → Operator Approval (token) →
  Executor → Verification. No shortcut, no background mode, no implied consent
  (RFC-0002 invariant 11).
- **A10 — Approval is recorded before it is spent.** The Approval Token's
  issuance is written to the Audit before execution proceeds (RFC-0002 invariant
  13), so the downward flow is always traceable.

---

## 9. Abuse-Case Analysis

This section asks, for each actor, what happens if it is **malicious**,
**compromised**, or **fails**, and why the architecture remains safe. The
analysis is explanatory but load-bearing: if any case shows an unbounded blast
radius, the matrix or an invariant is wrong and must be amended, not patched in
implementation.

### 9.1 Operator
- **Malicious / compromised:** the Operator is the source of authority and the
  owner of the machine. The model does not defend the machine *from* the
  Operator — that is the Operator's machine (RFC-0001 §8.3).
- **Why safe anyway:** the Assistant's duty is to not *hide* or *facilitate
  bypasses*: the Assistant may refuse (Refuse) to execute an Action that fails
  Policy or an invariant even when the Operator asks; it never provides an
  unapproved execution path, and it records everything (A10). The guarantee is
  transparency and refusal, not control over the Operator.
- **Failure:** a mistaken Approval grants a token to a harmful Action.
- **Why safe anyway:** Verification (A5) still checks the Post-condition; the
  Audit (A7) records the Approval and its consequence; Recovery discloses the
  actual state and obtains a fresh decision (RFC-0002 §10). A single mistaken
  Approval does not authorize everything.

### 9.2 Assistant (composite)
- **Malicious/compromised/failed:** "the Assistant" cannot act independently of
  its components (it holds no authority of its own, §4.2).
- **Why safe anyway:** the blast radius is already decomposed into the
  components below; the composite is not a decision point. If the composite is
  compromised, the question reduces to "which component," and each component's
  case applies.

### 9.3 Orchestrator
- **Malicious / compromised (e.g., prompt-injected via a Proposal):** it might
  try to skip a component or reorder the pipeline.
- **Why safe anyway:** skipping the gate cannot produce execution — the Executor
  (A2) and Approval Engine (invariant 11) independently require a valid token;
  the Orchestrator has no Execute authority (A8). Reordering consultations does
  not change Facts, Risk, or Approval, which other owners hold. Drift is caught
  by the watchdog (RFC-0002).
- **Failure (crash mid-session):** session management is deterministic; the
  runtime's Failure/Recovery path (RFC-0002 §10) establishes actual state,
  discloses, and re-obtains a decision. The Orchestrator owns Failure, so a
  failed Orchestrator is itself a Failure handled by the same rules.

### 9.4 Provider (LLM)
- **Malicious / compromised (prompt injection, a hostile model, a data leak):**
  the worst it can produce is untrusted text — a malicious Proposal or
  Hypothesis.
- **Why safe anyway:** A1 (no execution path), A5 (its success claims are never
  trusted), the Fact Layer's exclusivity over truth (it cannot author Facts,
  RFC-0001 §3.5), Context Manager sanitization and the no-secrets boundary
  (RFC-0009), and the Policy/Approval gate on everything it proposes (A9). Its
  only reach is Propose, Infer, Explain.
- **Failure (outage, degraded mode):** Mode is part of the runtime (RFC-0002);
  facts-only operation continues without it.

### 9.5 Diagnostics Layer
- **Malicious / compromised (a malicious Collector definition):** it could
  produce Observations that mislead.
- **Why safe anyway:** Observations are untrusted until the Fact Layer
  normalizes and checks them (A4, Fact Layer authority); a malicious Observation
  cannot become a Fact on its own, and it cannot mutate the machine (A4).
- **Failure (collector error, timeout, garbage output):** "fact unknown" is a
  legitimate Fact (RFC-0003 §2.4); failures are disclosed, never papered over
  (RFC-0001 §10).

### 9.6 Fact Layer
- **Malicious / compromised:** if truth itself is corrupted, downstream reasoning
  is corrupted.
- **Why safe anyway:** this is the one component whose compromise is dangerous,
  and the model bounds it structurally: the Fact Layer *cannot act* — it has no
  Execute, no Propose, no Approve authority (A8). A corrupted Fact set can
  mislead Proposals, but those still pass Policy and Approval, and Verification
  (A5) still re-observes actual state rather than trusting stored state.
  Compromise of the Fact Layer is therefore a *reasoning* compromise, not an
  *execution* compromise; it is surfaced by the Audit's independence (A7) and
  by state re-observation.
- **Failure (staleness, normalization error):** staleness bounds and
  provenance are its own enforced contracts (RFC-0005); a stale Fact is
  detected by re-observation during Verification.

### 9.7 Policy Engine
- **Malicious / compromised (a malicious Policy):** the gates could be loosened.
- **Why safe anyway:** Policy is deterministic and local, and the Operator sets
  its bounds; the Approval Engine and Executor independently enforce the token
  gate (invariant 11, A2). A loosened policy still cannot bypass the Operator's
  Approval or the Executor's token validation, and policy reloads invalidate
  outstanding tokens. The Fail-safe principle (RFC-0008) is an invariant the
  Policy Engine itself enforces: on policy errors it blocks, it does not loosen.
- **Failure:** fail closed (A6, RFC-0008): an unclassifiable Action is blocked,
  never auto-permitted.

### 9.8 Approval Engine
- **Malicious / compromised (tries to mint a token without the Operator):**
  token issuance is recorded before it is spent (A10) and tokens are bound to a
  specific Action and Machine State (invariant 11).
- **Why safe anyway:** a forged token cannot survive re-validation at the
  execution gate, and the Audit record of issuance is independent of the Approval
  Engine. The Executor's fail-closed refusal (A2) is the last check.
- **Failure (token expiry, state change, reboot):** invariant 11 invalidates the
  token; the flow re-presents and re-approves (RFC-0002 §8). Never a silent
  continuation.

### 9.9 Executor
- **Malicious / compromised (tries to run something unapproved):** it is the
  last line of execution.
- **Why safe anyway:** it runs only token-bound Actions (A2, A9); it has no
  Propose authority and no way to invent (A2); its executions are recorded before
  they proceed (A10) and verified by a different actor (A5). Even a compromised
  Executor can only execute what a token covers, and a token covers one Action
  at one Machine State.
- **Failure (partial execution, orphaned process):** Recovery (RFC-0002 §10)
  establishes actual state deterministically, discloses, and re-decides; the
  orphaned-action reconciliation is RFC-0014's subject.

### 9.10 Skills
- **Malicious / compromised (hostile skill content, prompt injection):** a Skill
  is untrusted by default (RFC-0001 §11).
- **Why safe anyway:** its Actions pass the *same* Policy and Approval gate as
  anything else (A3); its Collectors run inside the Diagnostics contract (A4);
  its text is sanitized by the Context Manager before any Provider view; it has
  no execution path. The worst a malicious Skill can do is propose, and Proposals
  are classified, approved, and verified.
- **Failure (broken procedure, wrong target):** its declared targets and
  verification method are part of its contract (RFC-0011); a failing Skill
  produces a Failed Action, which is disclosed and recovered, not silently
  bypassed.

### 9.11 Context Manager
- **Malicious / compromised (exfiltrating data into the Provider View):**
  the no-secrets boundary is the core privacy guarantee (RFC-0009).
- **Why safe anyway:** the boundary is enforced at the Context Manager, which is
  deterministic and itself has no authority to decide anything (it assembles).
  The sanitization enforcement point (RFC-0001 §9, RFC-0012) is a required
  invariant, and the Audit records what entered Context. Durable Memory exists
  only under Operator consent (A-Persist).
- **Failure (overflow, corruption):** context bounds and consolidation
  (RFC-0012) are enforced invariants; a corrupted Context degrades reasoning,
  never execution, and is re-observable via Verification.

### 9.12 Audit System
- **Malicious / compromised (tries to hide or rewrite history):** this is the
  transparency guarantee.
- **Why safe anyway:** the Audit is append-only and tamper-evident (A7,
  RFC-0002 invariant 13). The model does not promise forensics (RFC-0001 risk 8)
  — it promises that the record is written *before* each consequence and cannot
  be silently edited by the actor whose consequence it records. The Audit System
  has no authority over any decision (its matrix row is Persist/Explain only).
- **Failure (disk full, write error):** a failed audit write must block the
  consequence it precedes (fail-closed, invariant 13) rather than proceeding
  unrecorded.

### 9.13 Summary of the safety pattern

Across all cases, the same three structural facts recur:

1. **No actor both invents and executes.** (Provider/Skills invent; Executor
   executes; Orchestrator assembles; nobody does two of these.)
2. **The un-verify-able is the un-approvable.** Anything that cannot be
   verified deterministically cannot be executed without an explicit human
   Approval, and Approval is always token-scoped and recorded.
3. **Trust is never co-located with action.** The trusted actor (Fact Layer)
   cannot act; the acting actor (Executor) does not decide; the deciding actor
   (Operator) is the one being served. This is why a compromise at any one point
   degrades safety gradually rather than collapsing it.

---

## 10. Relationship to Later RFCs

- **RFC-0007 (Trust Model, Sanitization & Injection Defense):** owns the
  *data-flow* mechanics this RFC assumes — what "untrusted" means operationally,
  how untrusted text is contained. This RFC grants authority; RFC-0007 describes
  the untrusted material's journey.
- **RFC-0008 (Approval & Policy Engine):** owns the *taxonomy and mechanics* of
  the gates this RFC names (auto-permitted / confirm / confirm-with-warning /
  blocked), the risk classes, standing approvals, and elevation. This RFC fixes
  *who* may approve (the Operator) and the flow; RFC-0008 fixes *how*.
- **RFC-0010 (Provider Contract):** implements the Provider's matrix row (A
  for Propose/Infer/Explain, F everywhere else).
- **RFC-0011 (Skill Contract):** implements the Skill's matrix row and A3.
- **RFC-0012 (Context & Memory):** implements the Context Manager's Persist and
  the consent model.
- **RFC-0013 (Audit & Transcript):** implements the Audit System row and A7/A10.
- **RFC-0021 (System Model & Supported Platforms):** the renumbered subject of
  the original RFC-0004 reservation; orthogonal to this RFC (it models the
  machine, not the authority over it).

---

## 11. New Terms for RFC-0003 (flagged for inclusion in Part I)

The following terms are defined in §2 and must be added to RFC-0003 Part I by
additive amendment: **Actor**, **Authority**, **Trust**, **Ownership**,
**Delegation**, **Orchestrator**, **Diagnostics Layer**, **Fact Layer**,
**Policy Engine**, **Approval Engine**, **Executor**, **Context Manager**,
**Audit System**.

---

## 12. Open Questions

1. **Operator Execute, in-session.** The matrix marks the Operator's in-Assistant
   Execute as Conditional (condition 2). Whether the Assistant ever exposes an
   explicit "run this raw command as the Operator" path (vs. only approved
   Actions) is a boundary RFC-0008/0015 must settle.
2. **Executor's re-observation.** Whether the Executor may trigger re-observation
   for Verification, or must hand off to the Diagnostics Layer, is a mechanical
   question for RFC-0005/0006.
3. **Skill-originated Proposals.** Whether Skills may propose *Plans* directly or
   only *Actions* is owned by RFC-0011; this RFC only fixes that whatever they
   propose passes the same gate.
4. **Authority of "Explain."** Whether a *right to explanation* imposes
   retention requirements on the Context Manager is owned by RFC-0012/RFC-0013.
5. **Compromise of the Fact Layer.** §9.6 treats this as the most dangerous
   single-component compromise. Whether the project wants a stronger guarantee
   (e.g., cross-checked fact collection) is an open decision for RFC-0005.

---

*End of RFC-0004. Normative: sections 1 (as summary of 3–8), 3, 5, 6, 7, 8.
Explanatory and load-bearing: sections 2, 4, 9, 10, 11, 12. Any change to a
matrix cell, a flow rule, or an invariant A1–A10 is a BREAKING change and must
be made by amendment (RFC-0003 Part II).*
