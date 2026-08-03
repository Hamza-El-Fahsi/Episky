# Decision Traceability Matrix — The Architectural Dependency Map

> **Document type:** Traceability map, not an RFC.
> **Read this first:** This document **defines nothing**, introduces no
> architecture, and modifies nothing. It is a map of decisions that already
> exist, extracted from RFC-0000 through RFC-0013 and the architecture review
> documents (`docs/core-execution-walkthrough.md`,
> `docs/failure-injection-walkthrough.md`). Every claim here is traceable to a
> source document; where a relationship cannot be proven from the corpus, it is
> reported as **Unknown**, never invented.

---

## 0. Purpose

This document is the **architectural dependency map** of the project. Its single
purpose is to make every architectural decision traceable across the RFC corpus:
what was decided, by which document, why, and what changes if it does.

Every decision in this map has exactly four properties, and this document
records all four:

1. **Exactly one owner.** One RFC (or one section of it) is the normative owner
   of each decision. Ownership follows RFC-0004 §3: one owner per row, no
   delegation into self-extension (RFC-0004 A8).
2. **Explicit dependents.** Every document that consumes the decision is named,
   with the relationship (hard, soft, reference-only, or future).
3. **Explicit rationale.** Why the decision exists — cited to the owning
   document, not restated here.
4. **Explicit change impact.** What changing the decision costs: the amendment
   process that governs it (RFC-0003 Part II §4–§5) and its blast radius.

**Sources.** RFC-0000 (roadmap, categories, blast-radius and writing-order
analysis, open-question ownership), RFC-0001–RFC-0013, RFC-0021 (Draft),
and the two review documents. Where the review documents restate a decision,
the underlying RFC remains the owner; the review documents are never cited as
owners.

---

## 1. Decision Catalogue

Each decision row records: **ID**, short name, owner RFC, owner section,
purpose, depends-on, used-by, invariants that protect it, whether it can be
changed, and — if changeable — the amendment owner and blast radius.

> **Amendment process note.** All normative changes go through RFC-0003 Part II
> §4 (editorial vs. normative amendment), §5 (BREAKING changes are labeled,
> enumerated, reviewed longer, and default to rejection), and §6 (what requires
> a new RFC). "Amendment owner" below is therefore always one of: the owning
> RFC's amendment log, the RFC that would supersede it, or a new BREAKING RFC.
> None of this is this document's decision; it is RFC-0003's.

### D-01 Authority ownership

| Field | Value |
|---|---|
| Decision ID | D-01 |
| Short name | Authority ownership |
| Owner RFC | RFC-0004 |
| Owner section | §1.1 (ownership table), §3, §4 (profiles), §7 (the Authority Matrix), §8 (A1–A10) |
| Purpose | Every authority (Observe…Explain) is owned by exactly one actor; the matrix is the normative statement of who may do what; authority flows downward and nothing grants itself authority upward (RFC-0004 §8 A8) |
| Depends on | RFC-0001 (principles §8, roles §5); RFC-0003 (vocabulary); RFC-0002 (runtime that exercises the authorities) |
| Used by | Every later RFC: RFC-0005 (Fact Layer truth role §4.6), RFC-0006 (verification authority A5), RFC-0007 (A1–A6, A9), RFC-0008 (gate A9), RFC-0009 (Secrets ownership row, §4), RFC-0010 (Provider Propose-only), RFC-0011 (Skills Propose-only), RFC-0012 (Context Manager profile §4.11, Persist authority), RFC-0013 (Audit System §4.12, A7/A10) |
| Protected by invariants | A1–A10 (RFC-0004 §8); RFC-0002 invariants 1, 6, 11, 12, 13, 15 |
| Can be changed? | Yes — but a change to the matrix or any A-invariant is BREAKING (RFC-0003 Part II §5), binding every component |
| Amendment owner | A BREAKING RFC enumerating before/after of the changed cells (RFC-0003 Part II §5 rule 2); recorded in the RFC-0004 amendment log |
| Blast radius | Critical — every component's contract and every security mechanism (RFC-0000 §6 item 2: RFC-0004 forces later RFCs to specify gates within fixed authority bounds) |

### D-02 Approval gate

| Field | Value |
|---|---|
| Decision ID | D-02 |
| Short name | Approval gate |
| Owner RFC | RFC-0008 (the gate); RFC-0004 (the A9 invariant it realizes) |
| Owner section | RFC-0008 §5 (approval unit), §7 (Policy Engine), §8 (tokens), §11 (plan approval); RFC-0004 §8 A9 |
| Purpose | The gate is the only path from Proposal to execution: classification → gate → Operator decision → token → Executor → verification (RFC-0004 A9) |
| Depends on | RFC-0004 (authority matrix, A9); RFC-0005 (Facts for classification/preconditions); RFC-0002 (Awaiting Approval state §2.7, invariant 1) |
| Used by | RFC-0002 (execution gate), RFC-0010 (provider Actions pass the same gate), RFC-0011 (Skill Actions, no unit approval), RFC-0013 (approval records P13), RFC-0006 (TOCTOU outcome side) |
| Protected by invariants | P1–P14 (RFC-0008); A9, A10 (RFC-0004); RFC-0002 invariants 1, 11, 12, 13 |
| Can be changed? | Yes — approval granularity and retry semantics are open questions (RFC-0002 §11 items 1–2), but the gate itself is a binding A9 invariant |
| Amendment owner | RFC-0008 amendments; any change to the gate's *existence* is BREAKING and touches RFC-0002, RFC-0010, RFC-0011, RFC-0013 |
| Blast radius | Critical — RFC-0000 §6 item 1 names RFC-0008 the single highest-blast-radius document |

### D-03 Fact normalization

| Field | Value |
|---|---|
| Decision ID | D-03 |
| Short name | Fact normalization |
| Owner RFC | RFC-0005 |
| Owner section | §2 (Observation→Fact pipeline), §3 (canonical model), §13 (F1–F16) |
| Purpose | Raw machine output becomes canonical, provenanced, bounded Facts through deterministic normalization; nothing skips a stage; Facts are never LLM-authored (F1) |
| Depends on | RFC-0002 (Machine Inspection, invariant 10); RFC-0004 (Fact Layer truth role); RFC-0021 (Family Profile §2.3) — referenced, not a dependency |
| Used by | RFC-0006 (verification consumes Facts), RFC-0007 (trust-upgrade path T6), RFC-0008 (classification/preconditions), RFC-0010 (providers consume, never produce Facts F6), RFC-0011 (Skills bundle Collectors), RFC-0012 (Context carries Facts), RFC-0013 (fact-lifecycle records) |
| Protected by invariants | F1–F16 (RFC-0005); RFC-0002 invariant 10; A1, A4 |
| Can be changed? | Yes — but the pipeline's stage discipline (RFC-0005 §2) and F1/F5/F6 are binding; a change to the fact model ripples through every consumer (RFC-0000 §6 item 3) |
| Amendment owner | RFC-0005 amendment log; BREAKING if F1–F16 change |
| Blast radius | Critical — providers, skills, context, verification, interface all consume Facts |

### D-04 Verification model

| Field | Value |
|---|---|
| Decision ID | D-04 |
| Short name | Verification model |
| Owner RFC | RFC-0006 |
| Owner section | §1 (principles), §6 (process: Execute→Collect→Normalize→Facts→Compare→Outcome), §7 (Outcome model), §8 (contradictions), V1–V16 |
| Purpose | Deterministic, mandatory-after-execution verification against declared Postconditions; Unknown is first-class; contradiction wins; never the LLM's assessment |
| Depends on | RFC-0005 (Facts compared, contradiction representation §8); RFC-0004 (verification authority A5); RFC-0002 (Verification state, invariant 2); RFC-0008 (TOCTOU outcome side) |
| Used by | RFC-0002 (Verification→Replanning/Completed), RFC-0008 (Postconditions), RFC-0010 (providers never verify), RFC-0011 (Skills declare, never perform, verification), RFC-0012 (Outcomes are Context material), RFC-0013 (verification records) |
| Protected by invariants | V1–V16 (RFC-0006); RFC-0002 invariants 2, 9, 14 |
| Can be changed? | Yes — comparison algorithms and freshness-bound policy are deferred to RFC-0020 (RFC-0006 §15); the model's determinism (V3) and never-skip (V14) are binding |
| Amendment owner | RFC-0006 amendments; BREAKING if V1–V16 change |
| Blast radius | High — RFC-0000 §6 item 7 (definition of "verified" constrains runtime invariants and fact staleness) |

### D-05 Provider boundary

| Field | Value |
|---|---|
| Decision ID | D-05 |
| Short name | Provider boundary |
| Owner RFC | RFC-0010 |
| Owner section | §2 (responsibilities), §3 (inputs — the Provider View is the only channel), §4 (outputs), §5 (capability model), §8 (failure model), §11 (Context boundary), PR1–PR16 |
| Purpose | A provider is a reasoning service with Propose-only authority; it receives exactly the sanitized Provider View; its output is advisory and structured; it never executes, classifies, creates Facts, verifies, approves, or stores secrets |
| Depends on | RFC-0004 (Propose-only), RFC-0005 (Facts consumed, never produced), RFC-0007 (sanitization, Provider View), RFC-0008 (same gate) |
| Used by | RFC-0009 (no-secrets-to-providers PR8/PR14), RFC-0011 (Skills consume the Provider Contract), RFC-0012 (Context assembles the Provider View), RFC-0013 (providers never receive the Audit, PR14) |
| Protected by invariants | PR1–PR16; F6; V1, V6; A1, A2, A3, A8 |
| Can be changed? | Yes — but the Provider View as the only channel (PR14) and Propose-only authority are binding |
| Amendment owner | RFC-0010 amendments; BREAKING if the contract's joint (the internal representation) changes (RFC-0000 §6 item 5) |
| Blast radius | High — every vendor adapter and the orchestration rules that consume provider output |

### D-06 Skill boundary

| Field | Value |
|---|---|
| Decision ID | D-06 |
| Short name | Skill boundary |
| Owner RFC | RFC-0011 |
| Owner section | §1 (what a Skill is), §3 (ownership), §4 (no authority), §14 (verification responsibilities), §15 (secrets), §16 (audit), SK1–SK16 |
| Purpose | A Skill is a packaged, versioned, authenticated procedure — a candidate source of Proposals and Collectors; it has no authority: it cannot execute, approve, create Facts, verify, escalate, or reach the machine directly; never approved as a unit |
| Depends on | RFC-0004 (Propose-only, A2/A3/A8), RFC-0005 (Facts consumed, Collectors bundled), RFC-0010 (consumes the Provider Contract), RFC-0007 (conditional trust), RFC-0008 (per-Action gate) |
| Used by | RFC-0002 (SKILL_UNAVAILABLE §4.7, degraded mode), RFC-0009 (no-secrets SC5), RFC-0012 (sanitized Skill material), RFC-0013 (Skill-event records SK14) |
| Protected by invariants | SK1–SK16; P2; F6; V1, V10; SC5 |
| Can be changed? | Yes — format/packaging is RFC-0020; trust tiering is RFC-0011's open question (RFC-0007 §16 item 5). The no-authority core (SK4, RFC-0011 §4) is binding |
| Amendment owner | RFC-0011 amendments; BREAKING if the Skill surface or no-authority rule changes |
| Blast radius | High — diagnostics, execution, approval, and interface all consume the Skill format (RFC-0000 §6 item 6) |

### D-07 Secrets boundary

| Field | Value |
|---|---|
| Decision ID | D-07 |
| Short name | Secrets boundary |
| Owner RFC | RFC-0009 |
| Owner section | §0 (three binary guarantees), §1–§3 (what is/isn't a secret; classification), §4 (ownership), §11–§15 (redaction, destruction, failure, recovery, audit), §27 (retention), SC1–SC16 |
| Purpose | A secret exists only where and when it must; never in Context, Provider View, output summaries, Audit, telemetry, or extensions; unguaranteeable secrecy holds the boundary closed |
| Depends on | RFC-0004 (Secrets ownership row §4; Context Manager may never decide to include a secret §4.11), RFC-0007 (binary no-secret property T7, redaction failure modes), RFC-0010 (no-secrets-to-providers), RFC-0011 (no-secrets-to-Skills) |
| Used by | RFC-0012 (secret-free Context SC2), RFC-0013 (metadata-only Audit SC4), RFC-0005 (secret-free Facts), RFC-0006 (secrets never verification evidence) |
| Protected by invariants | SC1–SC16; T7, T10; PR8, PR14; SK8 |
| Can be changed? | Yes — redaction catalogue and Secure Store mechanics are RFC-0020; the guarantees in RFC-0009 §0 are binding |
| Amendment owner | RFC-0009 amendments; BREAKING if any SC invariant changes |
| Blast radius | High — the no-secrets property is a core privacy guarantee binding every boundary (RFC-0009 §0) |

### D-08 Audit-before-consequence

| Field | Value |
|---|---|
| Decision ID | D-08 |
| Short name | Audit-before-consequence |
| Owner RFC | RFC-0002 (invariant 13); specified in RFC-0013 |
| Owner section | RFC-0002 §9 invariant 13; RFC-0013 §7 (record categories), §21 (failure philosophy), §22 (recovery), AU1–AU16 |
| Purpose | Proposals, approvals, overrides, executions, verifications, and outcomes are recorded at the boundary, before the consequence, and never silently edited; a failed write blocks its consequence (AU8) |
| Depends on | RFC-0004 (Audit System profile §4.12, A7/A10); RFC-0008 (P13) |
| Used by | Every boundary in the runtime; RFC-0013 §7 categories are the write points |
| Protected by invariants | RFC-0002 invariant 13; A7, A10; P13; AU1–AU16; SC4 |
| Can be changed? | No — audit-before-consequence is a runtime invariant (RFC-0002 invariant 13), binding in every state |
| Amendment owner | BREAKING amendment to RFC-0002 (invariant 13), which must also amend RFC-0013 |
| Blast radius | Critical — removing it would permit unrecorded consequences, violating the transparency guarantee |

### D-09 Context assembly

| Field | Value |
|---|---|
| Decision ID | D-09 |
| Short name | Context assembly |
| Owner RFC | RFC-0012 |
| Owner section | §12 (composition), §13 (boundaries), §8/§9 (what enters / never enters), §21 (recovery), CM1–CM16 |
| Purpose | Context is deterministically assembled from Facts, Goal, bounded history, and Skill material — secret-free, purpose-limited, size-bounded; re-assembled, never restored |
| Depends on | RFC-0005 (Facts carried), RFC-0007 (sanitization S1–S8), RFC-0009 (secret-free SC2), RFC-0004 (Context Manager profile §4.11) |
| Used by | RFC-0010 (Provider View assembly owned here), RFC-0011 (Skill material sanitized here), RFC-0002 (Context Building §2.4), RFC-0013 (Context-to-Audit boundary) |
| Protected by invariants | CM1–CM16; S1–S8; SC2–SC4, SC9; T3, T10 |
| Can be changed? | Yes — composition mechanics evolve, but the no-secrets and re-assembly rules (CM13) are binding |
| Amendment owner | RFC-0012 amendments; BREAKING if CM invariants change |
| Blast radius | Medium — Context is the joint through which all reasoning material flows |

### D-10 Memory model

| Field | Value |
|---|---|
| Decision ID | D-10 |
| Short name | Memory model |
| Owner RFC | RFC-0012 |
| Owner section | §1–§3 (Context vs Memory), §7 (Memory categories), §18–§22 (visibility, persistence, destruction, recovery) |
| Purpose | Memory is durable only by explicit Operator consent (RFC-0001 §9.5); recovery is re-assembly, never restore; Memory survives per RFC-0014 |
| Depends on | RFC-0001 (§9.5 retention by consent); RFC-0004 (Memory ownership row, Persist authority); RFC-0009 (SC11 consent retention) |
| Used by | RFC-0013 (Context-boundary records, CM15), RFC-0014 (resume survival — future) |
| Protected by invariants | CM invariants; SC11; RFC-0001 §9.5 |
| Can be changed? | Yes — what survives a resume is RFC-0014's decision (RFC-0012 §21 rule 4) |
| Amendment owner | RFC-0012 amendments; RFC-0014 will own resume-specific semantics |
| Blast radius | Medium — persistence semantics interact with privacy (RFC-0009 §27) |

### D-11 Outcome model

| Field | Value |
|---|---|
| Decision ID | D-11 |
| Short name | Outcome model |
| Owner RFC | RFC-0006 |
| Owner section | §7 (Outcome model: Verified Success, Partially Successful, Unknown, Contradicted, Expired), §9 (comparison rules) |
| Purpose | Every executed state-changing action resolves to one named, honest Outcome; confidence never upgrades an Outcome (V15); Unknown is first-class |
| Depends on | RFC-0005 (Facts compared), RFC-0002 (Verification→terminal state routing, invariant 14) |
| Used by | RFC-0002 (Completed/Failed/Cancelled entry conditions), RFC-0008 (replanning after failure), RFC-0013 (verification records V11) |
| Protected by invariants | V5–V7, V9, V15, V16; RFC-0002 invariants 2, 9, 14 |
| Can be changed? | Yes — Outcome presentation is RFC-0015's; the taxonomy itself is normative (RFC-0006 §7) |
| Amendment owner | RFC-0006 amendments; BREAKING if the taxonomy changes |
| Blast radius | Medium — the honest-outcome guarantee is the foundation of the trust relationship |

### D-12 Trust model

| Field | Value |
|---|---|
| Decision ID | D-12 |
| Short name | Trust model |
| Owner RFC | RFC-0007 |
| Owner section | §6 (information categories), §10 (trust classes T1–T12), §11 (sanitization S1–S8), §12 (Provider View), §15 (failure behavior) |
| Purpose | Every datum carries a trust class; sanitization never upgrades a class (T9); provider output is data, never authority (T4); failure degrades to Hostile (T11/T12); no shell interpolation of untrusted text |
| Depends on | RFC-0001 (§7 trust boundaries, §8.4 no shell interpolation); RFC-0004 (A1–A6, A9); RFC-0005 (trust-upgrade via Facts T6) |
| Used by | RFC-0010 (View is the only sanitized channel), RFC-0011 (conditional Skill trust), RFC-0012 (sanitization enforcement), RFC-0009 (redaction failure modes), RFC-0002 (no untrusted text into commands, invariant 5) |
| Protected by invariants | T1–T12; S1–S8 |
| Can be changed? | Yes — mechanics are delegated (RFC-0007 §16), but the class discipline (T9) and no-interpolation rule are binding |
| Amendment owner | RFC-0007 amendments; BREAKING if T-invariants or S-principles change |
| Blast radius | High — RFC-0000 §6 item 4: a change to untrusted-text handling changes provider contract, skill contract, context, and audit simultaneously |

### D-13 Transcript model

| Field | Value |
|---|---|
| Decision ID | D-13 |
| Short name | Transcript model |
| Owner RFC | RFC-0013 |
| Owner section | §2 (what is Transcript), §8 (transcript record categories), §16 (completeness) |
| Purpose | The Transcript is derived from the Audit and never holds material the record does not; it presents dialogue, actions/outcomes, decisions/grounds, disclosures, recovery context |
| Depends on | RFC-0002 (invariant 13 — the record), RFC-0004 (Audit System Persist/Explain), RFC-0009 (disclosures, SC4) |
| Used by | RFC-0015 (presentation form — future) |
| Protected by invariants | AU1–AU16; RFC-0002 invariant 13; SC4 |
| Can be changed? | Yes — presentation form is RFC-0015's; the derive-from-record rule (RFC-0013 §8) is binding |
| Amendment owner | RFC-0013 amendments; presentation owned by RFC-0015 |
| Blast radius | Low — a render change affects only the presentation layer |

### D-14 Provider contract

| Field | Value |
|---|---|
| Decision ID | D-14 |
| Short name | Provider contract |
| Owner RFC | RFC-0010 |
| Owner section | §4 (structured outputs), §5 (capability model), §6 (capability negotiation), PR1–PR16 |
| Purpose | A provider returns one of a finite set of structured results; nothing else; outputs are advisory, carry their expected effect, and are never executed |
| Depends on | RFC-0002 (phase budgets, degraded mode), RFC-0004 (Propose-only), RFC-0007 (untrusted output) |
| Used by | RFC-0001 §5 (uniform provider abstraction), RFC-0011 (Skills consume it), RFC-0009 (no-secrets boundary PR8) |
| Protected by invariants | PR1–PR16; F6; V1, V6 |
| Can be changed? | Yes — but the structured-output rule (RFC-0010 §4) and View-only-input rule (PR14) are binding |
| Amendment owner | RFC-0010 amendments; BREAKING if the contract's internal form changes (RFC-0000 §6 item 5) |
| Blast radius | High — every adapter and the orchestration that consumes provider output |

### D-15 Skill contract

| Field | Value |
|---|---|
| Decision ID | D-15 |
| Short name | Skill contract |
| Owner RFC | RFC-0011 |
| Owner section | §5–§13 (declared surface, packaging, lifecycle), §14 (verification responsibilities), SK1–SK16 |
| Purpose | A Skill declares its targets, privileges, risk, and verification approach up front; it is a candidate source, never an authority; registered, not branched |
| Depends on | RFC-0004 (Propose-only), RFC-0005 (Collectors, Fact vocabulary), RFC-0007 (conditional trust), RFC-0008 (per-Action gate), RFC-0010 (Provider Contract) |
| Used by | RFC-0002 (Diagnosis/Planning participation, degraded mode), RFC-0012 (sanitized material), RFC-0013 (Skill-event records) |
| Protected by invariants | SK1–SK16; P2; F6; SC5 |
| Can be changed? | Yes — packaging/sandboxing is RFC-0020; trust tiering is RFC-0011's own open question |
| Amendment owner | RFC-0011 amendments |
| Blast radius | Medium — ecosystem-facing, interacts with the security spine (RFC-0000 §6 item 6) |

### D-16 Canonical facts

| Field | Value |
|---|---|
| Decision ID | D-16 |
| Short name | Canonical facts |
| Owner RFC | RFC-0005 |
| Owner section | §3 (canonical model), §4 (Fact Status), §5 (provenance), §12 (freshness), §13 (F1–F16) |
| Purpose | Facts are the only claims treated as known; they carry status, provenance, freshness, machine identity, scope; they never execute and never imply actions |
| Depends on | RFC-0021 (Family Profile, referenced); RFC-0004 (Fact Layer truth role) |
| Used by | Everything that reasons about the machine: RFC-0006, RFC-0008, RFC-0010, RFC-0011, RFC-0012, RFC-0013 |
| Protected by invariants | F1–F16 |
| Can be changed? | Yes — but F1 (never LLM-authored), F5 (deterministic), F6 (provider-independent) are binding |
| Amendment owner | RFC-0005 amendments; BREAKING if F-invariants change |
| Blast radius | Critical — RFC-0000 §6 item 3 (the fact model ripples through all consumers) |

### D-17 Runtime state machine

| Field | Value |
|---|---|
| Decision ID | D-17 |
| Short name | Runtime state machine |
| Owner RFC | RFC-0002 |
| Owner section | §2 (states), §3 (state machine diagram), §4 (events), §9 (invariants 1–15) |
| Purpose | The session's lifecycle: Idle → Inspection → Context Building → Diagnosis → Planning → Awaiting Approval → Executing → Verification → Completed/Replanning/Awaiting Input/Interrupted, with fixed transitions and 15 invariants |
| Depends on | RFC-0001 (principles), RFC-0003 (vocabulary), RFC-0004 (authorities it exercises) |
| Used by | Every RFC that names a state or transition: RFC-0005 (Inspection/Context), RFC-0006 (Verification state), RFC-0008 (Awaiting Approval), RFC-0013 (lifecycle events), RFC-0012 (Context Building) |
| Protected by invariants | Invariants 1–15 (RFC-0002 §9) |
| Can be changed? | Yes — RFC-0014 is expected to amend the interruption/resume semantics (RFC-0000 §6 item 8); other transitions change only by BREAKING amendment |
| Amendment owner | RFC-0002 amendment log; RFC-0014 likely amends it (RFC-0000 §6 item 8) |
| Blast radius | Critical — every state-naming RFC and every invariant consumer depends on it |

### D-18 Skill participation in runtime

| Field | Value |
|---|---|
| Decision ID | D-18 |
| Short name | Skill participation |
| Owner RFC | RFC-0002 (states); RFC-0011 (contract) |
| Owner section | RFC-0002 §2.5/§2.6 (Diagnosis/Planning), §4.7 (SKILL_UNAVAILABLE); RFC-0011 §3–§4 |
| Purpose | Skills participate in Diagnosis and Planning as candidate sources; SKILL_UNAVAILABLE revises the plan without them; degraded mode uses deterministic Skills |
| Depends on | RFC-0002 (runtime states), RFC-0011 (contract) |
| Used by | RFC-0012 (Skill material sanitization), RFC-0013 (Skill-event records) |
| Protected by invariants | RFC-0002 invariant 3 (planning never executes); SK4 |
| Can be changed? | Yes — how Skills enter the loop is evolvable within the states |
| Amendment owner | RFC-0011 (contract); RFC-0002 (if transitions change) |
| Blast radius | Low–Medium |

### D-19 Provider degradation

| Field | Value |
|---|---|
| Decision ID | D-19 |
| Short name | Provider degradation |
| Owner RFC | RFC-0002 (§10, §4.3); RFC-0010 (§8) |
| Owner section | RFC-0002 §10 (provider failure), §4.3 (provider events); RFC-0010 §8 (failure model) |
| Purpose | Timeout → fallback chain → degraded mode → facts-only Awaiting Input; machine work in flight is unaffected; the runtime never fabricates a reply (invariant 9) |
| Depends on | RFC-0002 (invariants 8, 9), RFC-0010 (failure model) |
| Used by | RFC-0011 (deterministic Skills serve degraded mode), RFC-0012 (facts-only presentation material) |
| Protected by invariants | RFC-0002 invariants 8, 9; PR11 |
| Can be changed? | Yes — degraded-mode scope is RFC-0002 §11 item 11 |
| Amendment owner | RFC-0002 (or RFC-0010) amendments |
| Blast radius | Medium |

### D-20 Preconditions / Postconditions

| Field | Value |
|---|---|
| Decision ID | D-20 |
| Short name | Preconditions / Postconditions |
| Owner RFC | RFC-0008 (preconditions §9, TOCTOU §10); RFC-0006 (postconditions §5) |
| Owner section | RFC-0008 §9–§10; RFC-0006 §4–§5 |
| Purpose | Preconditions must be fresh and true at execution time (re-validated at the boundary, P9); Postconditions are state expressed as Facts, fixed before Compare (V10) |
| Depends on | RFC-0005 (Fact vocabulary), RFC-0006 (Postconditions), RFC-0008 (Preconditions) |
| Used by | RFC-0010 (a Proposal carries its expected effect), RFC-0011 (Steps declare Postconditions) |
| Protected by invariants | P9, P10, P14; V10; RFC-0002 invariants 8, 11 |
| Can be changed? | Yes — but re-validation (P9) and fixed-before-Compare (V10) are binding |
| Amendment owner | RFC-0008 / RFC-0006 amendments |
| Blast radius | Medium |

---

## 2. Dependency Graph

Edges are the relationships the RFCs themselves declare (their "Interaction with
other RFCs" sections and RFC-0000 §4/§6). Legend: **H** = Hard dependency
(consumes normative content; a change breaks the consumer), **S** = Soft
dependency (consumes structure or principles; resilient to minor change),
**R** = Reference only (cited; not consumed normatively), **F** = Future
dependency (a planned RFC the document constrains), **P** = Potential cycle
(reported if found).

| RFC | H | S | R | F |
|---|---|---|---|---|
| **RFC-0000** | — | — | RFC-0001…0021 (the whole corpus is its subject) | — |
| **RFC-0001** | — | — | RFC-0003 (vocabulary), RFC-0002 | — |
| **RFC-0002** | RFC-0001 (principles, invariants), RFC-0003 (vocabulary), RFC-0004 (authorities) | RFC-0005 (Fact model), RFC-0006 (Outcomes) | RFC-0007, RFC-0008 | RFC-0014 (resume — expected to amend it), RFC-0015 (interface) |
| **RFC-0003** | — | — | all RFCs (process document) | — |
| **RFC-0004** | RFC-0001 (principles §8), RFC-0003 (vocabulary) | RFC-0002 (runtime) | RFC-0005 | RFC-0009 (adds the Secrets ownership row by additive amendment, RFC-0009 §4) |
| **RFC-0005** | RFC-0004 (Fact Layer truth role), RFC-0002 (inspection/invariants), RFC-0003 | RFC-0007 (trust-upgrade T6), RFC-0008 (consumes Facts) | RFC-0021 (§2.3 Family Profile, §4, §6 — "Referenced, not a dependency") | RFC-0006, RFC-0009, RFC-0012, RFC-0013, RFC-0014, RFC-0015, RFC-0017, RFC-0020 |
| **RFC-0006** | RFC-0005 (Facts), RFC-0004 (A5), RFC-0002 (Verification state, invariant 2) | RFC-0008 (TOCTOU outcome side), RFC-0007 (demotion forces re-verification) | RFC-0021 (§11, §12 "Can verify" — referenced) | RFC-0009, RFC-0012, RFC-0013, RFC-0014, RFC-0015, RFC-0017, RFC-0020 |
| **RFC-0007** | RFC-0001 (§7, §8.4), RFC-0004 (A1–A6, A9) | RFC-0005 (trust-upgrade path) | RFC-0008 (T1/T2/T11 referenced) | RFC-0009, RFC-0011, RFC-0012, RFC-0015 (delegated mechanics) |
| **RFC-0008** | RFC-0004 (A9, matrix), RFC-0002 (invariants 1, 11–13) | RFC-0005 (Facts for classification/preconditions), RFC-0006 (outcome side), RFC-0007 (T classes) | — | RFC-0009 (elevation boundaries), RFC-0011, RFC-0015 (approval UX), RFC-0013 (records) |
| **RFC-0009** | RFC-0004 (ownership, A8), RFC-0007 (T7, redaction failure), RFC-0010 (PR8/PR14), RFC-0011 (SK8) | RFC-0001 (§8.7–8.12, §9), RFC-0002 (invariant 4, §10), RFC-0005 (secret-free Facts), RFC-0006 (V1, V8) | RFC-0021 (§4.11 — "this RFC's subject") | RFC-0012, RFC-0013, RFC-0015, RFC-0016, RFC-0017, RFC-0020 |
| **RFC-0010** | RFC-0004 (Propose-only), RFC-0007 (sanitization), RFC-0008 (gate) | RFC-0001 (§5, §7, §11), RFC-0002 (degraded mode, phase budgets), RFC-0005 (Facts consumed, F6), RFC-0006 (V1, V6) | — | RFC-0009, RFC-0011, RFC-0012, RFC-0015, RFC-0016, RFC-0020 |
| **RFC-0011** | RFC-0004 (Propose-only, A2/A3/A8), RFC-0008 (gate, P2), RFC-0010 (Provider Contract) | RFC-0001 (§11), RFC-0002 (§2.5/§2.6, §4.7), RFC-0005 (F6), RFC-0006 (V1, V10), RFC-0007 (conditional trust) | — | RFC-0009, RFC-0012, RFC-0013, RFC-0015, RFC-0016, RFC-0017, RFC-0020 |
| **RFC-0012** | RFC-0004 (Context Manager profile, Persist authority), RFC-0005 (Facts), RFC-0007 (S1–S8), RFC-0009 (SC2), RFC-0002 (invariants 8, 10) | RFC-0001 (§9, §11), RFC-0006 (Outcomes as Context material), RFC-0008 (gate consumes Facts, not Context), RFC-0010 (no-secrets), RFC-0011 (Skill material) | RFC-0021 (§4, §11 — referenced) | RFC-0014, RFC-0015, RFC-0020 |
| **RFC-0013** | RFC-0004 (A7/A10, §4.12), RFC-0002 (invariant 13, §2.1 writability), RFC-0008 (P1/P10/P13) | RFC-0001 (§5, §8.10, §9.1–9.5), RFC-0005 (fact-lifecycle records), RFC-0006 (verification records), RFC-0009 (SC4), RFC-0012 (CM13/CM15) | RFC-0007, RFC-0010, RFC-0011 ("Draft; not a dependency"), RFC-0021 (§4, §11 — referenced) | RFC-0014, RFC-0015, RFC-0020 |
| **RFC-0021** | RFC-0004 (A4/A5 referenced) | — | RFC-0005, RFC-0006, RFC-0009, RFC-0012, RFC-0013 (all "Referenced, not a dependency") | RFC-0017, RFC-0020 (compatibility/implementation) |

**Potential cycles.** The graph is layered by authority: foundations (0001, 0003)
→ runtime (0002) → security spine (0004, 0007, 0008, 0009) → domain (0005,
0006, 0021) → extensions (0010, 0011) → context/audit (0012, 0013). Every
normative edge points from a consumer to a producer that was accepted earlier in
the roadmap (RFC-0000 §4 dependency ordering). **No circular architectural
ownership exists**: no two RFCs normatively own each other's decisions. The
closest structural recurrences are mutual *references* (RFC-0007↔RFC-0012,
RFC-0008↔RFC-0006, RFC-0009↔RFC-0010/0011), all of which are one-directional
normative consumption with the reverse direction being reference or delegation
(verified in each document's "Interaction with other RFCs" section). If a cycle
is later introduced, RFC-0003 Part II §4/§5 requires the amending RFC to
resolve it.

---

## 3. Invariant Coverage

Rows: RFCs. Columns: invariant families. Cells show **Defines** (the family's
normative home), **Uses** (references the family of another RFC), **Depends**
(the family is a hard prerequisite), **References** (cited without normative
consumption). Families registered in `tools/validate_rfc_refs.py`:
A (RFC-0004), T + S (RFC-0007), P (RFC-0008), F (RFC-0005), V (RFC-0006), SC
(RFC-0009), CM (RFC-0012), AU (RFC-0013), PR (RFC-0010), SK (RFC-0011), plus
RFC-0002's numeric invariants 1–15.

| RFC \ Family | 1–15 (0002) | A (0004) | T/S (0007) | P (0008) | F (0005) | V (0006) | SC (0009) | CM (0012) | AU (0013) | PR (0010) | SK (0011) |
|---|---|---|---|---|---|---|---|---|---|---|---|
| **RFC-0001** | Depends (principles realize them) | References | References | — | — | — | — | — | — | — | — |
| **RFC-0002** | **Defines** (invariants 1–15, §9) | Uses (A1–A10 referenced in §7/§8 context) | Uses | Uses | Uses | Uses | Uses | — | — | — | — |
| **RFC-0003** | — | — | — | — | — | — | — | — | — | — | — |
| **RFC-0004** | Uses (invariants 1, 6, 11–13, 15) | **Defines** (A1–A10, §8) | Uses | — | Uses (F1 via A1) | — | — | — | — | — | — |
| **RFC-0005** | Uses (invariants 2, 4, 5, 8, 10, 13, 15) | Uses (A1, A4) | Uses (T1–T6, T11) | Uses (P9, P14) | **Defines** (F1–F16, §13) | References | References | — | — | — | — |
| **RFC-0006** | Uses (invariants 2, 9, 14) | Uses (A1, A5) | Uses (demotion forces re-verify) | Uses (P9, P10, P14) | Uses (F13, F15) | **Defines** (V1–V16, §13) | References | — | — | — | — |
| **RFC-0007** | Uses (invariants 4, 5, 8, 13, 15) | Uses (A1–A6, A9) | **Defines** (T1–T12, §10; S1–S8, §11) | References (T1/T2/T11 used by 0008) | References | References | — | — | — | — | — |
| **RFC-0008** | Depends (invariants 1, 11–13, 15) | Uses (A1–A6, A8–A10) | Uses (T1, T2, T11) | **Defines** (P1–P14, §13) | Depends (Facts consumed) | Depends (outcome side) | — | — | — | — | — |
| **RFC-0009** | Uses (invariants 4, 13) | Uses (A1, A8) | Uses (T7, T10) | Uses | Uses (secret-free Facts) | Uses (V1, V8) | **Defines** (SC1–SC16, §28) | — | — | Uses (PR8, PR14) | Uses (SK8) |
| **RFC-0010** | Uses (invariants 4, 5, 9) | Uses (A1, A2, A3, A8) | Uses (View sanitized) | Uses (same gate) | Uses (F6, F11) | Uses (V1, V6) | References | — | — | **Defines** (PR1–PR16, §13) | — |
| **RFC-0011** | Uses (invariant 3; §9 never bypassed) | Uses (A2, A3, A4, A7, A8) | Uses (conditional trust) | Uses (P2, same gate) | Uses (F6) | Uses (V1, V10) | References (SC5) | — | — | Uses (PR10) | **Defines** (SK1–SK16, §28) |
| **RFC-0012** | Uses (invariants 8, 10) | Uses (A1, A8) | Uses (S1–S8, T3, T10) | Uses | Uses (F1, F10, F14) | Uses (V8) | Uses (SC2–SC4, SC9, SC15, SC16) | **Defines** (CM1–CM16, §35) | References | Uses (PR14) | Uses (SK8) |
| **RFC-0013** | Depends (invariant 13) | Uses (A7, A8, A10) | References | Uses (P1, P2, P10, P13) | Uses (F8, F14) | Uses (V8) | Uses (SC4, SC15, SC16) | Uses (CM13, CM15) | **Defines** (AU1–AU16, §33) | Uses (PR14) | Uses (SK14) |
| **RFC-0021** | — | References (A4, A5) | — | — | — | — | — | — | — | — | — |

*Coverage notes.* Every family is defined exactly once and consumed by its
dependents — no family has two normative homes (verified against the validator's
single-registry model and each RFC's own invariant section). The most consumed
family is A (RFC-0004), referenced by nine documents; the least consumed is S
(RFC-0007's sanitization principles), used chiefly by RFC-0012 and the
delegated mechanics. RFC-0003 defines no invariants — it is the process that
governs all of them.

---

## 4. Authority Ownership Matrix

Authorities from RFC-0004 §1.2 (Observe → Propose → Infer → Verify → Approve →
Execute → Refuse → Persist → Explain) plus two additional surfaces the corpus
names explicitly: **Remember** (RFC-0004 §4.11 Memory, §10; RFC-0012) and
**Normalize** (RFC-0005 §2 — the deterministic transformation that is the Fact
Layer's core act; RFC-0004 §1.1 "Truth (Facts)"). **Audit** is the Persist +
Explain pair restricted to the Audit System (RFC-0004 §4.12, §7). The matrix
below is derived from RFC-0004 §7; cell values are its own.

| Authority | Owner (RFC) | Who may request | Who may never own it | Transfer rules | Relevant RFCs |
|---|---|---|---|---|---|
| **Observe** | Diagnostics Layer (A in matrix, RFC-0004 §7; §4.5) | Orchestrator (dispatch); Operator (ask) | Provider, Skills, Orchestrator, Approval Engine, Executor, Audit (all F in matrix) | Read-only; Observations flow to the Fact Layer for normalization; no mutation (RFC-0004 §4.5; A4) | RFC-0004 §4.5, §7; RFC-0005 §2; RFC-0003 §2.4 Collector/Inspection |
| **Infer** | Provider (A); Skills (A) — hypothesis formation (RFC-0004 §7) | Orchestrator (requests reasoning) | Orchestrator, Diagnostics, Fact Layer, Policy Engine, Approval Engine, Executor, Context Manager, Audit (F) | Hypothesis carries no authority until confirmed by deterministic evidence (RFC-0003 §2.5); confirmed by Fact Layer, not by the inferrer | RFC-0004 §7; RFC-0003 §2.5; RFC-0006 |
| **Verify** | Fact Layer (A in matrix, RFC-0004 §4.6) | Orchestrator (after execution); every action | Provider, Skills, Orchestrator, Executor, Audit (all F) | Deterministic Compare only; never the LLM's assessment (V3); cannot be delegated (RFC-0004 §7) | RFC-0004 §4.6, §7; RFC-0006 V1–V16; RFC-0002 invariant 2 |
| **Approve** | Operator (A in matrix; RFC-0004 §7) | Approval Engine (presents the gate) | Assistant (F), Provider (F), Skills (F), Policy Engine (F), Approval Engine (C only — presents, never decides) | Only the Operator approves; token minted by the Approval Engine after classification + gate + explicit decision (RFC-0008 §8); recorded before spent (P13) | RFC-0004 §7; RFC-0008 §4, §8; RFC-0002 invariants 1, 13 |
| **Execute** | Executor (A in matrix; RFC-0004 §4.9) | Only under a valid Approval Token | Operator (through the Assistant, C² only), Provider, Skills, Orchestrator, Fact Layer, Audit (all F) | Token-bound; scoped; single-use; may decide only *how* within declared bounds (RFC-0004 §4.9) | RFC-0004 §4.9, §7; RFC-0008 §8; RFC-0002 invariant 11 |
| **Persist** | Context Manager (Memory, RFC-0004 §4.11, §10); Audit System (Audit, §4.12) | Operator (Memory consent); every boundary (Audit writes) | Provider (F), Skills (F), Orchestrator (F in matrix for Persist), Fact Layer (F) | Memory only by Operator consent (RFC-0001 §9.5); Audit records before consequence (RFC-0002 invariant 13) | RFC-0004 §4.11, §4.12, §7; RFC-0012; RFC-0013; RFC-0002 invariant 13 |
| **Explain** | Orchestrator, Provider, Skills, Audit System (A; RFC-0004 §7) | Operator | — (broadly allowed, but each is scoped to its own output) | Explain is the accountability surface; the Audit's Explain is Persist+Explain-only (RFC-0004 §4.12) | RFC-0004 §7; RFC-0013 §2 |
| **Refuse** | Orchestrator (A), Policy Engine (A), Approval Engine (C¹²); Executor (C¹⁴) (RFC-0004 §7) | Any component detecting a safety condition | Provider (F for the machine's behalf — refusal is a report, not a verdict), Skills (F) | The fail-safe floor; no refusals are overridden except by explicit, audited Operator decision (RFC-0008 P10) | RFC-0004 §7; RFC-0008 P10; RFC-0002 invariant 12 |
| **Remember** | Context Manager, on behalf of the Operator (RFC-0004 §4.11, §10) | Operator (consent) | Provider, Skills, Fact Layer, Audit System (none may choose to remember) | Durable only by explicit Operator consent (RFC-0001 §9.5); re-assembled, never restored (RFC-0012 §21) | RFC-0004 §4.11; RFC-0012 §1–§3, §21; RFC-0001 §9.5 |
| **Normalize** | Fact Layer (RFC-0005 §2; RFC-0004 §1.1 Truth) | Diagnostics Layer (supplies Observations) | Provider, Skills, Orchestrator, Operator (F1: never LLM- or Operator-authored) | Deterministic, per-Observation, pure function (F5); the only path Observation→Fact | RFC-0005 §2, F1, F5; RFC-0004 §1.1 |
| **Audit** | Audit System (Persist + Explain only; RFC-0004 §4.12, §7) | Every boundary (each writes its own records) | Provider (never receives it, PR14), Skills (may not modify it, SK14), every other actor (F) | Append-only, tamper-evident, written before consequence (RFC-0002 invariant 13; A7); reconciled, never rewritten (RFC-0013 §22) | RFC-0004 §4.12, §7; RFC-0013; RFC-0002 invariant 13 |

---

## 5. Blast Radius Analysis

Suppose each RFC disappeared. For every RFC: what breaks, what survives, whether
the architecture can continue, and severity.

| RFC | What breaks | What survives | Can the architecture continue? | Severity |
|---|---|---|---|---|
| **RFC-0000** | The roadmap, category assignment, open-question ownership tables (§8), and amendment log | Every RFC still states its own invariants | Yes — documents remain normative, but coordination (who owns each open question) is lost | Medium |
| **RFC-0001** | The constitution: principles §7/§8, context philosophy §9, extensibility §11, failure philosophy §10 | Lower-level invariants still textually exist but lose their rationale | Not coherently — every RFC cites RFC-0001's principles as its justification | **Critical** |
| **RFC-0002** | The state machine and invariants 1–15; every state-naming RFC (0005, 0006, 0008, 0013) loses its runtime grounding | Authority matrix, fact model, contracts still specify their own rules | No — the loop that ties everything together is gone | **Critical** |
| **RFC-0003** | Governance: amendment process, BREAKING-change rules, vocabulary discipline | All architecture, but ungoverned (anyone could change anything) | Yes, but anarchically — change management collapses | High |
| **RFC-0004** | The authority matrix, ownership tables, A1–A10 | Individual contracts (0010, 0011, 0012) would still exist but lose their binding authority | Not safely — without the matrix, nothing fixes who may do what | **Critical** |
| **RFC-0005** | Facts: the model every reasoning document consumes | Verification (0006), approval (0008), context (0012), audit (0013) would have no canonical data to operate on | Not coherently — the shared vocabulary of "what is known" is gone | **Critical** |
| **RFC-0006** | Verification process and Outcomes, V1–V16 | Runtime would still execute and approve but could not honestly confirm anything | Yes but unsafe — "success" would be unverifiable | **Critical** |
| **RFC-0007** | Trust classes, sanitization, no-shell-interpolation; the untrusted-data spine | Provider/Skill contracts would still exist but lose their boundary discipline | Not safely — untrusted text would have no defined treatment | **Critical** |
| **RFC-0008** | The approval gate, tokens, policy engine, P1–P14 | Authority matrix still says who *may* approve; nothing would enforce the gate | Not safely — execution without the gate is the architecture's cardinal violation | **Critical** |
| **RFC-0009** | Secrets: classification, boundaries, SC1–SC16 | Other RFCs still reference SC invariants but lose the specification | Not safely — the privacy guarantee would be undefined | High |
| **RFC-0010** | Provider contract, Provider View, PR1–PR16 | Skills (0011) reference it; runtime would still function with degraded mode | Yes — degraded mode and deterministic Skills can continue; the vendor abstraction is lost | Medium |
| **RFC-0011** | Skill contract, SK1–SK16 | Everything else remains; Skills would have no safe way to be third-party | Yes — the core can run with no Skills | Low |
| **RFC-0012** | Context assembly, Memory, CM1–CM16 | Facts (0005) and secrets (0009) still exist; Context would be ungoverned | Yes, but reasoning material would be unbounded and unsanitized | High |
| **RFC-0013** | Audit/Transcript, AU1–AU16 | Runtime invariants still demand recording (invariant 13) but the record's structure is undefined | Yes, but accountability collapses | High |
| **RFC-0021** | Family Profile, supported-platform promise | Everything else stands; Facts promise fewer guarantees on unsupported families | Yes — supported platforms just lose their test baseline (already the case for unsupported ones) | Medium |

**Summary.** Four RFCs are singly-fatal (0001, 0002, 0004, 0005, 0006, 0007,
0008 — the foundations/runtime/domain/security spine); the loss of any one makes
the architecture incoherent or unsafe. The extension and record RFCs (0010,
0011, 0012, 0013, 0021) are survivable individually because the core can
degrade. No RFC's removal is harmless.

---

## 6. Amendment Cost

Ranked by amendment cost — a composite of RFC-0000 §6 (RFCs Likely to Change
Others), the dependency counts of §2, the invariant families of §3, and the
review burden implied by RFC-0003 Part II §5 (BREAKING changes get a longer
review window and default to rejection).

| Rank | RFC | Est. architectural impact | No. of dependent RFCs (H+S) | Risk | Expected review effort | Why |
|---|---|---|---|---|---|---|
| 1 | **RFC-0008** | Very high — the gate is the single decision point | 6+ (0002, 0004, 0005, 0006, 0010, 0011, 0013) | High | Very long | RFC-0000 §6 item 1: the single highest-blast-radius document; approval granularity/retry are its open questions; touching the gate forces rework in the runtime, skills, interface, and audit |
| 2 | **RFC-0004** | Very high — every component's authority | 9+ (all) | High | Very long | RFC-0000 §6 item 2: the Authority Matrix binds every contract; A-invariants are the most consumed family (§3) |
| 3 | **RFC-0005** | High — every consumer reasons over Facts | 8+ (0006, 0008, 0010, 0011, 0012, 0013, 0002, 0007) | High | Long | RFC-0000 §6 item 3: the fact model ripples through providers, skills, context, verification, interface |
| 4 | **RFC-0007** | High — untrusted-data spine | 7+ (0002, 0008, 0010, 0011, 0012, 0013, 0009) | High | Long | RFC-0000 §6 item 4: a change to untrusted-text handling changes provider contract, skill contract, context, and audit simultaneously |
| 5 | **RFC-0002** | Very high — the state machine | 6+ (0005, 0006, 0008, 0010, 0012, 0013) | High | Long | 15 invariants, every state-naming RFC depends on it; RFC-0014 is expected to amend it (RFC-0000 §6 item 8) |
| 6 | **RFC-0010** | High — the vendor joint | 5+ (0009, 0011, 0012, 0013, 0001) | Medium-High | Long | RFC-0000 §6 item 5: the internal representation is the joint between Core and every vendor |
| 7 | **RFC-0006** | High — the definition of "verified" | 6+ (0002, 0008, 0010, 0011, 0012, 0013) | Medium-High | Long | RFC-0000 §6 item 7: directly constrains runtime invariants and fact staleness |
| 8 | **RFC-0011** | Medium-High — ecosystem contract | 5+ (0002, 0009, 0012, 0013, 0007) | Medium-High | Long | RFC-0000 §6 item 6: consumed by diagnostics, execution, approval, interface; interacts with the security spine |
| 9 | **RFC-0009** | Medium-High — privacy spine | 4+ (0007, 0010, 0011, 0012, 0013) | Medium-High | Long | 16 SC invariants binding every boundary; redaction mechanics delegated to 0020 |
| 10 | **RFC-0012** | Medium | 4+ (0010, 0011, 0013, 0002) | Medium | Medium | Assembly and Memory semantics are evolvable; re-assembly and no-secrets rules are binding |
| 11 | **RFC-0013** | Medium | 3+ (0002, 0008, 0009) | Medium | Medium | Record structure is defined here, but the obligation (invariant 13) lives in RFC-0002 |
| 12 | **RFC-0001** | Very high *if* amended | all | High | Very long — but amendment is rare | The constitution is amended only by BREAKING process (RFC-0003 §5); its changes cascade by principle, not by text |
| 13 | **RFC-0003** | Low-Medium (process only) | all (as governing process) | Low | Short | Process changes touch every document's governance but no architecture |
| 14 | **RFC-0021** | Low (Draft) | 0 H (referenced only) | Low | Short | Referenced, not a dependency; changing it affects the promise of Facts on supported platforms, not the architecture |
| 15 | **RFC-0000** | Low | all (as coordination) | Low | Short | A roadmap change is coordination, not architecture |

---

## 7. Architectural Stability

| Question | Answer | Support |
|---|---|---|
| **Most central RFC** | **RFC-0004 (Trust & Authority Model)** | Its Authority Matrix (§7) and A1–A10 are consumed by nine documents (§3 coverage); every contract (0010, 0011, 0012, 0013) implements a profile it defines (§4); RFC-0000 §6 item 2 confirms it forces later RFCs to specify gates within fixed authority bounds. RFC-0002 is a close second (the runtime every state-naming RFC uses). |
| **Most isolated RFC** | **RFC-0021 (System Model & Supported Platforms)** | Declared "Referenced, not a dependency" by every document that mentions it (RFC-0005 §14, RFC-0006 §14, RFC-0009 §29, RFC-0012 §36, RFC-0013 §34); it has no hard dependents and is a Draft. |
| **Highest coupling** | **RFC-0004** (out-degree) and **RFC-0005** (in-degree) | RFC-0004's authority model is consumed by all nine later RFCs; RFC-0005's Facts are consumed by 0006/0008/0010/0011/0012/0013 (§2, §3). RFC-0000 §6 items 2–3 name both among the top blast-radius documents. |
| **Lowest coupling** | **RFC-0000** and **RFC-0003** | RFC-0003 defines no invariants and is consumed only as process; RFC-0000 is coordination. Neither has a normative consumer that breaks on its change. |
| **Greatest authority concentration** | **RFC-0004** | It concentrates the definition of all eleven authorities (§4) in one document; every actor's permissible behavior is a cell of its matrix (§7). |
| **Greatest dependency concentration** | **RFC-0002** and **RFC-0008** | RFC-0002: six hard dependents and 15 invariants; RFC-0008: the single highest-blast-radius document (RFC-0000 §6 item 1) at the execution decision point. |
| **Weakest area** | **RFC-0014 (resume semantics) and the open quantity questions** | RFC-0014 is Post-MVP yet the one deferred RFC most likely to amend RFC-0002 (RFC-0000 §6 item 8); timeouts/retry/allowlist values are open (RFC-0002 §11); degraded-mode scope is open (item 11). These are the only places the corpus defers behavior rather than fixes it. |
| **Strongest area** | **The security spine (RFC-0004 + RFC-0008 + RFC-0009 + RFC-0007)** | The gate (A9), authority closure (A8), secret containment (SC1–SC16), and trust classes (T1–T12) are mutually reinforcing, each with its own invariant family (§3), and RFC-0000 §4 assigns them the "safety spine" category. The two review documents confirm no failure path bypasses them. |

---

## 8. Final Verdict

Each answer is supported by the corpus.

**Q1. Is the architecture internally consistent?**

Yes. The RFCs declare their dependencies explicitly (§2), each invariant family
has exactly one normative home (§3), and the roadmap's category/dependency
ordering (RFC-0000 §2, §4) is acyclic. The two review documents
(`docs/core-execution-walkthrough.md`, `docs/failure-injection-walkthrough.md`)
trace a full request and thirty-one failures through the corpus without
inventing behavior, which corroborates consistency but is not the source of it —
the source is each RFC's own invariant section and interaction table.

**Q2. Does every authority have exactly one owner?**

Yes. RFC-0004 §3 requires one owner per row, and §7's matrix assigns each
authority to exactly one actor as its normative owner (all others are F or C).
RFC-0009 §4 extends the same rule to Secrets ("exactly one owner … no delegation
into self-extension"). The one structural note is that the Secrets ownership row
is added by RFC-0009 into RFC-0004's table by additive amendment (RFC-0009 §4) —
an addition that "alters no existing row and weakens no invariant," so it
preserves the one-owner property.

**Q3. Can every decision be traced?**

Yes. Every major decision in §1 carries its owner RFC, owner section, purpose,
dependents, and change process, all drawn from the corpus. Each RFC's
"Interaction with other RFCs" section declares what it consumes and what it
constrains (§2). Open decisions are explicitly owned: RFC-0000 §8 tables say
where every open question is answered, and the remaining deferrals are recorded
in §6 of this document as owned by their future RFCs.

**Q4. Are there hidden dependencies?**

No hidden hard dependencies were found. Every normative edge in §2 is declared
in the consuming RFC's interaction section. The only dependencies that could be
called "implicit" are the reverse-direction references — for example RFC-0004
and RFC-0005 reference each other's concepts (A1 references F1; RFC-0005 §14
says "supports A1") — but in every case one direction is normative and the other
is reference/delegation, and both are stated. **Unknown:** whether any *future*
RFC (0014–0020) introduces an undeclared dependency cannot be proven from the
current corpus; §2 marks those as F (future) rather than assuming them resolved.

**Q5. Are there circular ownership chains?**

No. The dependency graph (§2) is layered: foundations → runtime → security
spine → domain → extensions → context/audit, matching RFC-0000 §4's dependency
ordering and the accepted-then-planned sequence. The structural recurrences
(0007↔0012, 0008↔0006, 0009↔0010/0011) are mutual *references*, never mutual
*normative ownership* — each pair's normative direction is one-way and stated.
No two RFCs normatively own each other's decisions.

**Q6. Can future contributors understand why each decision exists?**

Yes, with one caveat. Each decision's rationale lives in its owning document
(§1 "Purpose" columns cite it), its amendment process is defined (RFC-0003 Part
II §4–§5), and RFC-0000 §4 explains why each RFC occupies its position. The
caveat is the same deferral as Q4/Q6 of the review documents: the *rationale
records* for decisions that belong to future RFCs (especially RFC-0014's likely
amendment of RFC-0002, RFC-0000 §6 item 8) do not exist yet. Until those RFCs
land, contributors must read the open-question sections (RFC-0002 §11, RFC-0006
§15, RFC-0007 §16, RFC-0010 §15, RFC-0011 §30, RFC-0009 §30, RFC-0012 §37,
RFC-0013 §35) to see what is undecided and who owns it.

---

## End State

Every architectural decision in RFC-0001–RFC-0013 is now traceable: one owner,
named dependents, cited rationale, and a defined change impact. The authority
matrix is closed (RFC-0004 §7), every invariant family has one normative home
(§3), the dependency graph is acyclic and explicitly declared (§2), and the
deferrals are recorded as owned by their future RFCs rather than invented here.
This document adds nothing; it maps.
