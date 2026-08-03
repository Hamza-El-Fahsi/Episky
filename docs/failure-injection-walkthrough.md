# Failure Injection Walkthrough — Architectural Stress Proof

> **Document type:** Consistency proof, not an RFC.
> **Read this first:** This document **defines nothing new**. It injects
> failures into the architecture defined by the accepted RFC series
> (RFC-0000–RFC-0013) and records, for each, how the architecture already
> handles it. It introduces no component, no rule, no authority, no algorithm,
> no API, and no recovery behavior that is not already inside the RFC corpus.
> Where the corpus cannot resolve a failure, this document records a **Gap** —
> it does not invent a fix.

---

## 0. Purpose

1. **This document introduces no architecture.** Every statement below is a
   claim about what the existing RFCs already require.
2. **Every conclusion must be traceable to existing RFCs.** Each scenario cites
   the owning RFC, section, event, and invariant that governs the outcome. A
   claim without a citation is a defect in this document.
3. **Any missing behavior must be reported as an architectural gap rather than
   invented.** If a failure cannot be resolved from RFC-0001–RFC-0013, §6
   records the gap with its owning RFC, severity, reason, and impact. Nothing is
   added to the architecture to close it.
4. The companion document `docs/core-execution-walkthrough.md` proves the
   architecture is *consistent in the happy path*; this document proves it is
   *consistent under failure* — that no failure permanently breaks an invariant,
   that the system always returns to a valid state, and that failure never
   grants what the happy path forbids.

**Method.** A failure is *injected* as an event or condition at the boundary
where the RFC series says it can occur. The walkthrough then follows the RFC
defined reaction. If the RFCs define no reaction, the result is a Gap, never a
solution.

---

## 1. Failure Philosophy

The architecture's stance on failure is stated across the corpus. It is
summarized here, every clause cited:

1. **Fail closed.** Any error in a safety mechanism — unparseable policy,
   unknown risk class, failed verification, failed sanitization, failed audit
   write, unavailable store — blocks the affected consequence and tells the
   Operator; it never proceeds "because the check was unavailable" (RFC-0001
   §8.12; RFC-0002 §10 policy failure; RFC-0007 §15.7; RFC-0009 §13; RFC-0013
   §21; RFC-0004 §9.12; RFC-0008 §15).
2. **Determinism first.** Recovery always follows the order *determinism,
   disclosure, decision, action*: establish what is true, tell the Operator,
   let the Operator decide, then act on approval (RFC-0002 §10; RFC-0008 §15;
   RFC-0009 §13).
3. **Verify rather than assume.** Success is never inferred; it is determined
   from observed Facts (RFC-0006 §1; V1, V2, V5). Unknown is a first-class,
   honest outcome (RFC-0006 §1 rule 5). The runtime never fabricates (RFC-0002
   invariant 9).
4. **Authority never widens.** No actor grants itself authority upward; the
   authority matrix is closed (RFC-0004 A8). Failure does not create a shortcut
   to execution (RFC-0004 A9; RFC-0002 invariant 1).
5. **Secrets never leak.** A secret value exists only where it must, only when
   it must, and never enters Context, Provider View, output summaries, Audit,
   telemetry, or extensions (RFC-0009 §0; SC2–SC5). Unclassifiable data is
   Hostile and quarantined (RFC-0009 §2; RFC-0007 §15.5). Suspected exposure is
   compromise (RFC-0007 §6.10; RFC-0009 SC15).
6. **Audit before consequence.** Approvals, overrides, executions,
   verifications, and outcomes are recorded at the boundary, before the
   consequence, and never silently edited (RFC-0002 invariant 13; RFC-0013 §7;
   RFC-0004 A10; RFC-0008 P13).
7. **Provider output is untrusted.** Provider output is data, never authority;
   it can at most become a Proposal (RFC-0007 T4; RFC-0010 §2; RFC-0004 A1).
   A hallucination cannot corrupt the machine model (RFC-0010 §8).
8. **The runtime always returns to a valid state.** After any halt, timeout,
   partial execution, or reboot, no further machine action occurs until actual
   state has been re-established deterministically (RFC-0002 invariant 8); no
   terminal outcome is reached while machine work is in flight (RFC-0002
   invariant 14); no approval survives a boundary (RFC-0002 invariant 15).

---

## 2. Failure Categories

The taxonomy below is a *classification of the ways the system can fail*. Each
category names its owner RFC, the components affected, the expected behavior,
the forbidden behavior, and who owns recovery. Recovery ownership follows
RFC-0002 §10's pattern: the deterministic machinery re-establishes truth; the
Operator decides; the Executor acts only under a fresh approval.

| Category | Owner RFC | Affected components | Expected behavior | Forbidden behavior | Recovery owner |
|---|---|---|---|---|---|
| **Provider failures** | RFC-0010 §8; RFC-0002 §4.3, §10 | Provider adapters, Core | Bounded reactions: timeout→fallback/degrade, unavailable→fallback chain, malformed→reject/degrade, refusal→honored, no infinite retry; disclosed and audited | Interpreting malformed output into validity; crashing; silent provider substitution; deriving a Fact from non-conforming text | Core (degrade); Operator (decision); fallback chain |
| **Runtime failures** | RFC-0002 §8, §10, §9 invariants | Orchestration Core, Executor | Determinism first, then disclosure, then decision, then action; re-establish state before further action; never fabricate | Resuming in-flight work; claiming an outcome over unknown state; continuing on assumptions | Core (state re-establishment); Operator (decision) |
| **Approval failures** | RFC-0008 §8, §10, §15; RFC-0002 invariants 11–13 | Approval & Policy Engine, Executor, Audit | Token scoped/consumable/invalidated on state change, interrupt, reboot, policy reload; expiry disclosed; re-present for fresh decision | Reusing a token; silently extending expiry; resurrecting an invalidated token; execution without a recorded approval | Core (re-present); Operator (fresh decision) |
| **Verification failures** | RFC-0006 §6, §7, §8; RFC-0002 §2.9 | Fact Layer, Diagnostics | Collect→Normalize→Facts→Compare→Outcome; Unknown when evidence missing; Contradicted when Facts conflict; no silent skip | Claiming success without fresh Facts; letting confidence upgrade an Outcome; picking a winner between conflicting Facts; verification mutating the machine | Fact Layer (re-collect/re-compare); Core (replan); Operator |
| **Context failures** | RFC-0012 §12, §13, §21; RFC-0005 §2 | Context Manager, Fact Layer | Re-assembly, never restore; rebuild from Facts/Audit/consented Memory; re-orient before proceeding | Resurrecting a stale snapshot; injecting unconsented material; secret entering Context | Context Manager (re-assembly); Core (re-orient); Operator (consent) |
| **Fact failures** | RFC-0005 §13 (F1–F16), §4, §7; RFC-0002 invariant 10 | Fact Layer, Collectors | A failed/unknown Fact is a Fact; F11/F15/F16; provenance and expiry; fail closed on rule failure | Editing a Fact; using a stale Fact; treating an LLM claim as a Fact; proceeding on an invalid Fact | Fact Layer (invalidate/retire); re-observation |
| **Skill failures** | RFC-0011 §4, §15, §16, SK4/SK5; RFC-0002 §4.7 | Skill Runtime, Executor, Audit | SKILL_UNAVAILABLE→revise plan or ask; Skill Actions pass the gate; skill failure is a candidate-source failure, not a system failure; audited | A Skill bypassing approval; a Skill executing or verifying; a Skill receiving a secret (SC5) | Core (revise plan); Skill Registry (trust revocation); Operator |
| **Audit failures** | RFC-0013 §21, §22, AU8; RFC-0002 invariant 13; RFC-0004 §9.12 | Audit System, Core | Fail closed: failed write blocks its consequence; fail loud: Operator told; degraded never silent; reconciliation, never rewrite | Proceeding unrecorded; fabricating a lost record; resurrecting deleted records | Core (block consequence); Audit System (reconcile) |
| **Secret handling failures** | RFC-0009 §13, §14, §15; RFC-0007 §6.10, §15 | Secure Store, redaction, boundaries | Withhold, quarantine, disclose, invalidate, destroy, record; store fails→release nothing; consumer misbehaves→incident | Releasing an unverifiable value; leaking to Context/View/Audit; automatic demotion; regenerating a secret | Operator (re-provision); boundary (hold closed); incident handling |
| **Persistence failures** | RFC-0012 §20, §21; RFC-0013 §22; RFC-0009 §27 | Context Manager, Memory, Audit System, Secure Store | Session-scoped defaults; re-assembly over restore; writability check at session start; retention never outlives purpose | Restoring an unconsented snapshot; durable secret artifacts; recovery resurrecting what was destroyed | Core (re-assembly); Operator (consent); destruction on lapse |
| **Environment failures** | RFC-0021 §2, §3; RFC-0002 §2.1 | Core, Collectors, Fact Layer | Supported families only; system assumptions verified at session start; fail closed if assumptions unmet | Guessing behavior on an unsupported platform; fabricating a Family Profile | Core (refuse/ask); Operator (choose supported platform) |
| **Operator failures** | RFC-0004 §9.1; RFC-0001 §8.3 | Core, Approval Engine, Audit | The Operator is not defended *from*; the Assistant does not hide or facilitate; refusal and transparency are guaranteed; disconnect→no approval | Approving on the Operator's behalf; "always yes"; hiding withheld material | Operator (reconnect); Core (state-hold); presentation |
| **Unknown failures** | RFC-0001 §10; RFC-0007 §15.5; RFC-0002 invariant 9 | Core, boundaries | Unclassifiable→Hostile/quarantine/disclose; runtime never fabricates; unknown is a first-class outcome | Assigning a guess; silently continuing; classing an unknown as benign | Core (disclose); boundary (hold closed); Operator |

---

## 3. Failure Scenarios

Thirty-one injected failures. Each scenario records the failure, the detection
point (where the architecture first notices), the responsible component, the
governing RFCs, the invariants at risk and how they hold, the authority owner,
the expected outcome, the recovery path, why no authority leak occurs, and why
no shortcut is permitted.

> **Notation.** RFC-0002 invariant N = **I-N**; RFC-0004 = **A-N**; RFC-0008 =
> **P-N**; RFC-0005 = **F-N**; RFC-0006 = **V-N**; RFC-0007 = **S-N**, trust
> class **T-N**; RFC-0009 = **SC-N**; RFC-0012 = **CM-N**; RFC-0011 = **SK-N**.

---

### Scenario 1 — Provider returns malformed output

| Field | Value |
|---|---|
| Failure | Provider returns text that is not a valid contract output (§4 of RFC-0010) |
| Detection point | Core output validation at the provider boundary (RFC-0010 §4 "Nothing else", §8) |
| Responsible component | Conversation/Orchestration Core |
| Relevant RFCs | RFC-0010 §4, §8; RFC-0002 §4.3 |
| Invariants | I-4 (LLM only via Provider View); PR11 (provider failure degrades, never crashes) |
| Authority owner | Core (routing); no authority was granted to the provider (RFC-0010 §2) |
| Expected outcome | Output rejected as malformed; re-request or degrade to Failure; disclosed and audited |
| Recovery path | Re-request once, else fallback/degrade to facts-only presentation (RFC-0010 §8; RFC-0002 §4.3) |
| No authority leak | The malformed text is never interpreted into validity, never becomes a Proposal worth executing, and never becomes a Fact (RFC-0010 §8 rule 3; F11) |
| No shortcut | The gate is unchanged: even a well-formed re-request must be classified and approved (RFC-0004 A9; RFC-0002 invariant 1) |

---

### Scenario 2 — Provider hallucinates

| Failure | Provider asserts a claim that contradicts known Facts |
| Detection point | The claim is checked against Facts; it is not a Fact by construction |
| Responsible component | Fact Layer (verification); Core (Proposal routing) |
| Relevant RFCs | RFC-0010 §8 (hallucination row); RFC-0005 F1/F6; RFC-0006 V1 |
| Invariants | F1 (a Fact never originates from an LLM); V1 (verification never trusts provider output) |
| Authority owner | Provider holds Propose only; Facts are owned by the Fact Layer (RFC-0004 §1.1) |
| Expected outcome | The assertion gains no authority. If it drives a Proposal, the Proposal is ordinary output, gated and verified against Facts |
| Recovery path | The gate rejects or the Compare contradicts it; either way the plan re-opens with the false claim as non-fact (RFC-0006 §7 Contradicted) |
| No authority leak | A hallucinated sentence can never mutate the machine (RFC-0010 §8 rule 2; RFC-0004 A1) |
| No shortcut | There is no path from provider text to the machine that skips the gate (RFC-0004 A9) |

---

### Scenario 3 — Provider times out

| Failure | No reply within the phase bound |
| Detection point | Phase timer at the provider boundary (RFC-0002 §4.3 PROVIDER_TIMEOUT) |
| Responsible component | Core |
| Relevant RFCs | RFC-0010 §8 (timeout row); RFC-0002 §4.3, §10; RFC-0001 §10.7 |
| Invariants | I-9 (never fabricate); PR11 (degrade, never crash) |
| Authority owner | Core (degrade); Operator (decision) |
| Expected outcome | Treat as Failure; try fallback or degrade; disclose the timeout; audited |
| Recovery path | Backoff → fallback chain → degraded mode → facts-only Awaiting Input (RFC-0002 §10 provider failure) |
| No authority leak | Degradation grants nothing; degraded mode is facts-only, no recommendations (RFC-0002 §4.3) |
| No shortcut | Machine work already in flight is unaffected, and nothing new runs without approval (RFC-0002 §10) |

---

### Scenario 4 — Provider unavailable

| Failure | Provider cannot be reached at all |
| Detection point | Connection failure at the boundary (PROVIDER_UNAVAILABLE) |
| Responsible component | Core |
| Relevant RFCs | RFC-0010 §8; RFC-0002 §4.3, §10 |
| Invariants | I-9; PR11 |
| Authority owner | Core; Operator |
| Expected outcome | Fallback chain or degraded mode; the outage is an event, not a crash (RFC-0001 §10.7) |
| Recovery path | PROVIDER_FALLBACK_OK → continue; PROVIDER_FALLBACK_FAILED → degraded mode → Awaiting Input (RFC-0002 §4.3) |
| No authority leak | A missing provider is not an authorization; nothing is granted by absence (RFC-0004 A9) |
| No shortcut | The runtime never substitutes a guessed reply for the missing provider (I-9; RFC-0002 §10) |

---

### Scenario 5 — Provider refuses

| Failure | Provider states it will not do the asked thing |
| Detection point | A first-class Refusal output (RFC-0010 §4) |
| Responsible component | Core |
| Relevant RFCs | RFC-0010 §8 (refusal row); RFC-0002 §4.3 (structural non-compliance = refusal) |
| Invariants | I-9; I-7 (risk classification is never the provider's self-report) |
| Authority owner | Core (present); Operator (decide) |
| Expected outcome | Refusal honored and presented; alternatives offered; no pressure; no silent substitution of another provider's judgment |
| Recovery path | Present refusal → Operator chooses alternative or new approach |
| No authority leak | A refusal is a report, not a verdict (RFC-0010 §2) |
| No shortcut | The Core does not quietly route around a refusal; substitution is disclosed (RFC-0010 §8 rule 5) |

---

### Scenario 6 — Approval expires

| Failure | Token lifetime elapses before execution |
| Detection point | Token lifetime check at the execution boundary (RFC-0002 §2.8; RFC-0008 §8) |
| Responsible component | Approval & Policy Engine; Executor |
| Relevant RFCs | RFC-0008 §8, §15; RFC-0002 invariant 11 |
| Invariants | I-11 (tokens scoped and consumable; invalidated by expiry); P8 (never resurrected) |
| Authority owner | Operator (fresh decision) |
| Expected outcome | Token is dead; nothing runs under it; lapse disclosed; Action re-presented for a fresh decision (RFC-0008 §15) |
| Recovery path | Disclose lapse → re-establish state if changed → re-present → fresh approval |
| No authority leak | An expired token authorizes nothing; it is not extended (RFC-0008 §15) |
| No shortcut | Re-execution requires a new explicit decision (RFC-0008 §8; I-15) |

---

### Scenario 7 — Approval reused

| Failure | Attempt to spend a consumed token again |
| Detection point | Token state check at the execution boundary (RFC-0002 §2.8) |
| Responsible component | Executor |
| Relevant RFCs | RFC-0002 invariant 11; RFC-0008 §4 (consumable), §8 |
| Invariants | I-11 (consumed token is never reused); P8 |
| Authority owner | Executor (refusal); Operator |
| Expected outcome | Second use refused; the token is single-use; nothing runs |
| Recovery path | Re-present the Action; a fresh token is issued only on a fresh decision |
| No authority leak | The consumed token grants nothing (P8) |
| No shortcut | One token = one Action or one plan envelope; no standing pass (RFC-0008 §4, P11) |

---

### Scenario 8 — Approval forged

| Failure | An attacker constructs a token without the Operator's decision |
| Detection point | Token validation: scope, time, machine-state binding, issuance record (RFC-0008 §8; RFC-0002 invariant 13) |
| Responsible component | Approval & Policy Engine; Executor; Audit |
| Relevant RFCs | RFC-0008 §8, P13; RFC-0002 invariants 11, 13; RFC-0004 A10 |
| Invariants | I-13 (issuance recorded before the token can be spent); A10; P13 |
| Authority owner | Approval Engine (mint); Executor (validate) |
| Expected outcome | A token with no matching pre-spend approval record or a mismatched machine-state binding is invalid; the Action is refused |
| Recovery path | Refused execution → disclose → Audit records the attempt |
| No authority leak | Only the Approval Engine mints tokens, only after classification, gate, and an explicit Operator decision (RFC-0008 §8; RFC-0004 A9) |
| No shortcut | The gate is the only path to execution; a forged object cannot satisfy the boundary re-validation (RFC-0002 §2.8; P9) |

---

### Scenario 9 — Fact normalization fails

| Failure | A Collector's output cannot be parsed into a canonical Fact |
| Detection point | Deterministic normalization step (RFC-0005 §2) |
| Responsible component | Diagnostics & Fact Layer |
| Relevant RFCs | RFC-0005 §2, F11/F16; RFC-0003 §2.4 |
| Invariants | F5 (deterministic normalization), F11 (Unknown is not False), F16 (fail closed on rule failure) |
| Authority owner | Fact Layer (only producer of Facts, RFC-0004 §1.1) |
| Expected outcome | The output is rejected/Unknown or truncated-with-marker; no guessed value substitutes (RFC-0002 §10 collector failure) |
| Recovery path | Re-collect, or carry "fact unknown" with provenance; partial Facts flow marked partial |
| No authority leak | A failed normalization creates a Fact of its failure, never a permission, never an action (F2, F4) |
| No shortcut | Raw text never skips normalization into Context or a Provider View (RFC-0005 §2) |

---

### Scenario 10 — Collector truncates output

| Failure | A diagnostic returns partial output |
| Detection point | Normalization, which marks truncation (RFC-0005 §2) |
| Responsible component | Diagnostics & Fact Layer |
| Relevant RFCs | RFC-0005 §2; RFC-0002 §4.2 (FACTS_COLLECTED, partial); RFC-0001 §8.8 (output limited) |
| Invariants | F10/F13 (provenance and scope); I-10 (Facts expire); RFC-0001 §8.8 (truncate rather than dump) |
| Authority owner | Fact Layer |
| Expected outcome | Truncated output is marked; Facts are partial; downstream decisions see "fact unknown" for the missing part |
| Recovery path | Critical baseline failure → Awaiting Input (disclose) or Failed (RFC-0002 §4.2) |
| No authority leak | Partiality is a Fact status, not a permission (F2) |
| No shortcut | Context Building never completes a truncated Fact by assumption (RFC-0002 §10 collector failure) |

---

### Scenario 11 — Verification contradicts expectation

| Failure | Observed Facts contradict the declared Postcondition |
| Detection point | Compare step (RFC-0006 §6) |
| Responsible component | Fact Layer |
| Relevant RFCs | RFC-0006 §7 (Verified Failure/Contradicted), §8; RFC-0002 §2.9 |
| Invariants | V7 (contradiction always wins), V10 (Postconditions fixed before Compare), V15 (confidence never changes the Outcome) |
| Authority owner | Fact Layer (determine); Core (replan); Operator |
| Expected outcome | Outcome is Verified Failure or Contradicted; the path stops; no friendlier interpretation is chosen |
| Recovery path | State re-established deterministically; the failure becomes a new Fact; plan returns through the gate (RFC-0002 §2.10; RFC-0008 §15) |
| No authority leak | The verdict is a state determination, not a decision (RFC-0004 §1.1) |
| No shortcut | No auto-retry, no auto-rollback; a revised Step is re-presented (RFC-0008 §11; RFC-0002 §10) |

---

### Scenario 12 — Inspection unavailable

| Failure | Collect cannot produce the needed Facts (collector fails or times out) |
| Detection point | COLLECTOR_FAILED event (RFC-0002 §4.2) |
| Responsible component | Diagnostics & Fact Layer |
| Relevant RFCs | RFC-0002 §4.2, §10; RFC-0005 §4 (Fact Status Unknown/Unavailable); RFC-0006 V14 |
| Invariants | V14 (verification never silently skips), V16 (catastrophic cases surfaced); I-9 |
| Authority owner | Fact Layer; Core; Operator |
| Expected outcome | Outcome is Unknown, never success; a critical baseline failure asks rather than assumes |
| Recovery path | Re-collect, or disclose and await input/Failed (RFC-0002 §4.2) |
| No authority leak | Missing evidence is not evidence of success (V9) and grants nothing |
| No shortcut | An unverifiable result is never reported as success (V5; RFC-0002 §2.13) |

---

### Scenario 13 — Machine state changes during execution

| Failure | External change (service flip, lock appears) mid-flow |
| Detection point | Read-only watchdog (RFC-0002 §4.2 STATE_CHANGED_DETECTED) |
| Responsible component | Core; Fact Layer |
| Relevant RFCs | RFC-0002 §4.2, §8; RFC-0008 §10, P8/P9 |
| Invariants | I-8 (halt → re-assess), I-11 (token invalidated by state change), P8 |
| Authority owner | Core; Operator |
| Expected outcome | Dependent Facts invalidated; in Awaiting Approval the approval is invalidated → Machine Inspection; elsewhere Context marked stale and the next consuming decision re-inspects first |
| Recovery path | Re-inspection → re-plan/re-present → fresh decision |
| No authority leak | A state change is a fact event, not an authorization (F4) |
| No shortcut | Preconditions are re-validated at the execution boundary regardless (P9; RFC-0006 §4) |

---

### Scenario 14 — Context corrupted

| Failure | The working set is lost or corrupted |
| Detection point | Context Manager integrity check at next assembly (RFC-0012 §21) |
| Responsible component | Context Manager |
| Relevant RFCs | RFC-0012 §21, §13; RFC-0005 §2; RFC-0002 §2.4 |
| Invariants | CM13 (re-assembly over restore); RFC-0002 invariant 8 (re-orient) |
| Authority owner | Context Manager (re-assembly); Operator (consent) |
| Expected outcome | Context is re-assembled from Facts, Audit, and consented Memory; no stale snapshot resurrected |
| Recovery path | Re-collect ground truth (RFC-0005 §12) → re-orient → proceed |
| No authority leak | Re-assembly draws only from authorized sources (RFC-0012 §21) |
| No shortcut | Nothing is injected into Context without assembly rules (RFC-0012 §12) |

---

### Scenario 15 — Memory unavailable

| Failure | Consented Memory cannot be read or was never consented |
| Detection point | Context Manager at assembly time (RFC-0012 §8, §13) |
| Responsible component | Context Manager |
| Relevant RFCs | RFC-0012 §8, §13, §21; RFC-0001 §9.5 |
| Invariants | CM rules on consent (RFC-0012 §22); SC11 (retention by consent) |
| Authority owner | Context Manager; Operator (consent) |
| Expected outcome | Unavailable or unconsented Memory simply does not enter Context; the session continues on Facts |
| Recovery path | Re-assembly without Memory; no gap is invented |
| No authority leak | Consent gates every promotion into Memory and Context (RFC-0012 §13 Context→Memory) |
| No shortcut | Memory is never a fallback source of truth; Facts are (RFC-0012 §21) |

---

### Scenario 16 — Secret detected unexpectedly

| Failure | A secret-shaped value appears in captured data |
| Detection point | Deterministic classification (RFC-0009 §3) / quarantine (RFC-0007 §15.5) |
| Responsible component | Diagnostics & Fact Layer; boundaries |
| Relevant RFCs | RFC-0009 §3, SC13/SC14; RFC-0007 §15.5, §6.10 |
| Invariants | SC2 (default secret-free), SC3 (no secret in a Provider View), SC4 (no secret in the Audit); S3 |
| Authority owner | Boundary (hold closed); Operator (disclose) |
| Expected outcome | Secret-shaped value classified secret-adjacent until proven otherwise; Hostile if unclassifiable; excluded from Context and Provider View; disclosed |
| Recovery path | Withhold → disclose → continue on what was safely contained (RFC-0007 §15) |
| No authority leak | No value crosses a boundary (SC6); failure degrades to Hostile, never to "probably not a secret" (RFC-0009 §2) |
| No shortcut | Redaction is applied before anything leaves the session, deterministically (SC13) |

---

### Scenario 17 — Audit storage unavailable

| Failure | The Audit store cannot be written (disk full, write error) |
| Detection point | Audit write at the boundary (RFC-0013 §21; RFC-0002 invariant 13) |
| Responsible component | Audit System; Core |
| Relevant RFCs | RFC-0013 §21, AU8; RFC-0004 §9.12; RFC-0008 §15 |
| Invariants | I-13 (audit before consequence); AU8 (a failed write blocks its consequence and is disclosed) |
| Authority owner | Core (block); Operator (told) |
| Expected outcome | The consequence the failed write precedes is blocked; nothing proceeds unrecorded; the Operator is told loudly |
| Recovery path | Restore writability (RFC-0013 §22 recovery gate) → reconcile → re-present |
| No authority leak | A blocked consequence is a denial, not an authorization |
| No shortcut | Degraded mode is never silent; the next consequential step is refused (RFC-0013 §21) |

---

### Scenario 18 — Transcript generation fails

| Failure | The Transcript cannot be rendered from the record |
| Detection point | Presentation at Completed (RFC-0013 §8) |
| Responsible component | Audit System / Presentation |
| Relevant RFCs | RFC-0013 §8 (transcript derives from the record), §16 (completeness); RFC-0004 §4.12 |
| Invariants | RFC-0013 AU rules (the transcript never holds material the record does not) |
| Authority owner | Audit System (Persist/Explain only, RFC-0004 §4.12) |
| Expected outcome | The record still stands; a render failure does not affect the record's integrity; the Operator is told a render failed |
| Recovery path | Re-render from the record; no material is invented to fill the gap |
| No authority leak | The Transcript has no authority; its failure cannot grant any (RFC-0004 §4.12) |
| No shortcut | The Transcript cannot substitute for the record (RFC-0013 §8) |

---

### Scenario 19 — Skill crashes

| Failure | A Skill procedure fails or refuses mid-use |
| Detection point | SKILL_UNAVAILABLE event (RFC-0002 §4.7) |
| Responsible component | Skill Runtime |
| Relevant RFCs | RFC-0011 §3, §16; RFC-0002 §4.7, §10 |
| Invariants | SK4 (every Skill Action passes the gate), SK5 (untrusted until authenticated); I-2 (verification follows execution) |
| Authority owner | Core (revise plan); Skill Registry (trust); Operator |
| Expected outcome | The plan is revised without the Skill, or the Operator is asked; the Skill's failure is a candidate-source failure |
| Recovery path | Revise plan → re-normalize → re-present (RFC-0002 §4.7) |
| No authority leak | A failing Skill cannot bypass the gate, execute, verify, or receive secrets (RFC-0011 §4; SC5) |
| No shortcut | The plan re-enters the pipeline at Planning/Replanning, not mid-execution (RFC-0002 §4.7) |

---

### Scenario 20 — Skill violates declared capabilities

| Failure | A Skill attempts more than its declared surface |
| Detection point | Gate and declared-surface check at the Skill boundary (RFC-0011 §1, §3) |
| Responsible component | Skill Runtime; Approval & Policy Engine |
| Relevant RFCs | RFC-0011 §1, §3, §4; RFC-0001 §11.3 (declared intent); RFC-0008 |
| Invariants | SK4 (no bypass), SK5 (conditional trust); A9; RFC-0001 §8.9 (untrusted even after authentication) |
| Authority owner | Policy Engine (gate); Skill Registry (review) |
| Expected outcome | The out-of-surface Action is blocked at the gate or refused classification; declared-vs-actual is audited (RFC-0011 §16) |
| Recovery path | Trust revocation (RFC-0011 SK), plan revision |
| No authority leak | A Skill cannot widen its own authority (A8) or reach the machine directly (RFC-0011 §4) |
| No shortcut | Its Actions are Proposals like any other, gated per-Action (RFC-0008 §5) |

---

### Scenario 21 — Runtime interrupted

| Failure | Machine work is halted by an interrupt |
| Detection point | OP_INTERRUPT / OP_CANCEL (RFC-0002 §8) |
| Responsible component | Orchestration Core |
| Relevant RFCs | RFC-0002 §8, §9 invariants 8, 14, 15; RFC-0008 §15 |
| Invariants | I-8 (halt → re-assess), I-14 (no terminal outcome while work is in flight), I-15 (approval ends at the boundary) |
| Authority owner | Core (record); Operator (decision) |
| Expected outcome | Running action stops; the ran/not-ran set is recorded; actual state is re-established; no unverified claims |
| Recovery path | Re-inspect → record exactly what ran → present → Operator decides (RFC-0002 §10 partial execution) |
| No authority leak | An interrupt is not an authorization; nothing resumes without fresh approval (I-15) |
| No shortcut | No silent continuation; continuation is a new decision after re-orient (RFC-0008 §11) |

---

### Scenario 22 — Power loss

| Failure | The machine loses power mid-session |
| Detection point | On restart: resume marker, session init (RFC-0002 §2.1) |
| Responsible component | Orchestration Core; Context Manager; Audit System |
| Relevant RFCs | RFC-0002 §2.1, §9 invariants 8, 15; RFC-0012 §21; RFC-0013 §22 |
| Invariants | I-8, I-15; CM13 (re-assembly over restore); RFC-0013 §22 (re-present from the record) |
| Authority owner | Core (re-orient); Operator |
| Expected outcome | No approval survives the boundary; actual state is re-established before any machine action; in-flight work is treated as unknown state |
| Recovery path | Resume at re-orient → re-establish state → re-present → fresh approval (RFC-0002 §2.1, §3) |
| No authority leak | Power loss grants nothing; every approval ends at the boundary (I-15) |
| No shortcut | No state-changing continuation runs without a fresh decision (RFC-0008 §15 reboot row) |

---

### Scenario 23 — Reboot

| Failure | The system reboots (e.g., after a package change) |
| Detection point | Session initialization on restart; resume marker (RFC-0002 §2.1) |
| Responsible component | Orchestration Core |
| Relevant RFCs | RFC-0002 §2.1, §9 invariant 15; RFC-0008 §15 (reboot row); RFC-0006 V12 |
| Invariants | I-15 (no standing authorization across a boundary); V12 (re-verification after reboot) |
| Authority owner | Core; Operator |
| Expected outcome | Every approval ends; state re-established; a pre-approved read-only assessment may run automatically; no state-changing continuation without a fresh decision |
| Recovery path | Re-orient → re-verify actual state (V12) → present |
| No authority leak | Reboot is a boundary; nothing survives it (I-15) |
| No shortcut | Rebooted continuation is a new decision, never a resume (RFC-0002 §3) |

---

### Scenario 24 — Resume after reboot

| Failure | A resumed session must reconstruct where it was |
| Detection point | Resume marker (RFC-0002 §2.1) |
| Responsible component | Orchestration Core; Context Manager; Audit System |
| Relevant RFCs | RFC-0002 §2.1, §3; RFC-0012 §21; RFC-0013 §22 |
| Invariants | I-8 (continue at re-orient, not at the interrupted step); CM13; RFC-0013 §22 rule 3 |
| Authority owner | Core (re-orient); Operator |
| Expected outcome | The session resumes by re-orienting: actual state re-established, Context re-assembled, record re-presented |
| Recovery path | Re-assembly → re-present recovery context (RFC-0013 §8 category 5) → Operator decides |
| No authority leak | Resume restores orientation, not authority (I-15) |
| No shortcut | The runtime never "resumes" in-flight machine work (I-8; RFC-0008 §15) |

---

### Scenario 25 — Operator revokes approval

| Failure | The Operator cancels or revokes an in-flight or pending decision |
| Detection point | OP_CANCEL / revoke at Awaiting Approval or Executing (RFC-0002 §8) |
| Responsible component | Orchestration Core; Executor; Audit |
| Relevant RFCs | RFC-0002 §8, §2.15; RFC-0008 §8 (tokens revocable); RFC-0013 §7 (approval records) |
| Invariants | I-13 (revocation recorded); P8 (token never resurrected) |
| Authority owner | Operator (sole approver, RFC-0004 §7) |
| Expected outcome | The action stops; the token is invalidated; the ran/not-ran set is recorded; the Operator is given the honest partial state |
| Recovery path | Record → re-inspect → present → Operator chooses next |
| No authority leak | Revocation is the Operator's own authority exercised; nothing is delegated (RFC-0004 §8) |
| No shortcut | A revoked token cannot be spent (P8); no silent continuation (RFC-0002 §2.15) |

---

### Scenario 26 — Operator disconnects

| Failure | The Operator's interface drops mid-decision |
| Detection point | Presentation link loss (RFC-0015 is out of scope; the runtime's holding behavior governs) |
| Responsible component | Orchestration Core; Audit |
| Relevant RFCs | RFC-0002 §2.7 (Awaiting Approval holds), §8; RFC-0004 §9.1 |
| Invariants | I-1 (no execution without approval), I-14 (no terminal outcome while work is in flight) |
| Authority owner | Operator (approval); Core (hold state) |
| Expected outcome | Awaiting Approval holds; no action runs without the Operator; state is held and disclosed on return |
| Recovery path | Reconnect → re-present current state → Operator decides |
| No authority leak | The system never approves on the Operator's behalf (RFC-0004 §7; RFC-0008 §4) |
| No shortcut | Absence is not consent; there is no "always yes" (RFC-0001 §8.3) |

---

### Scenario 27 — Package manager crashes

| Failure | The package manager fails during the Action |
| Detection point | Execution record; post-execution Collect (RFC-0006 §6) |
| Responsible component | Executor; Fact Layer |
| Relevant RFCs | RFC-0002 §10 (executor failure, partial execution); RFC-0006 V14/V16 |
| Invariants | I-8 (halt → re-assess); V16 (catastrophic cases surfaced); RFC-0002 §10 (orphaned effects never assumed away) |
| Authority owner | Core; Operator |
| Expected outcome | The Action is treated as failed; actual state re-established; exactly what ran is recorded; nothing is assumed |
| Recovery path | Verification → Replanning with the failure as new fact (RFC-0002 §10) |
| No authority leak | A crash grants nothing; state is re-established by observation (RFC-0002 invariant 8) |
| No shortcut | No auto-retry; a revised Step is re-presented (RFC-0008 §11) |

---

### Scenario 28 — Filesystem becomes read-only

| Failure | The target filesystem is read-only at execution time |
| Detection point | Execution failure / post-execution Collect mismatch |
| Responsible component | Executor; Fact Layer |
| Relevant RFCs | RFC-0002 §10; RFC-0006 §7 (Verified Failure); RFC-0001 §8.12 |
| Invariants | I-8; V14 |
| Authority owner | Core; Operator |
| Expected outcome | Outcome is Verified Failure (the Postcondition was not met); state re-established; no silent success |
| Recovery path | Re-inspect → disclose → Operator decides (remount, manual, or abandon) |
| No authority leak | Read-onlyness is a state fact, not an authorization (F4) |
| No shortcut | The runtime does not "retry harder"; escalation is a fresh, approved decision (RFC-0008 §12; RFC-0001 §8.6) |

---

### Scenario 29 — Permission denied

| Failure | The Action cannot obtain the privilege it was approved for |
| Detection point | Execution boundary / elevation (RFC-0001 §8.6) |
| Responsible component | Executor; Approval & Policy Engine |
| Relevant RFCs | RFC-0001 §8.6 (elevation explicit, scoped, re-authenticated); RFC-0008 P12 (elevation revoked); SC10 (elevation exposes nothing) |
| Invariants | I-1; P12; SC10 |
| Authority owner | Operator (elevation decision) |
| Expected outcome | The Action fails closed; the Operator is told; no workaround is attempted with widened scope |
| Recovery path | Disclose → Operator decides (fix permission, elevate explicitly, or abandon) |
| No authority leak | Denied permission is not circumvented; elevation never leaks beyond the approved scope (P12) |
| No shortcut | No privileged backdoor exists; every elevated Action is at least Consequential and re-approved (RFC-0008 §6, P12) |

---

### Scenario 30 — Unknown environment / unsupported platform

| Failure | The machine is not a supported distro family, or a system assumption is unmet |
| Detection point | Session initialization prerequisites (RFC-0002 §2.1); Family Profile lookup (RFC-0021 §2.3) |
| Responsible component | Core; Diagnostics & Fact Layer |
| Relevant RFCs | RFC-0021 §2 (status words), §3 (system assumptions); RFC-0002 §2.1; RFC-0005 F7 |
| Invariants | F7 (Facts are distro-independent); RFC-0021 §2.3 (descriptive Family Profile); RFC-0001 §8.12 (fail closed) |
| Authority owner | Core (refuse/ask); Operator |
| Expected outcome | Unsupported families have no Family Profile, no test baseline, no promised Facts (RFC-0021 §2.2); the session fails closed rather than guessing |
| Recovery path | Refuse or ask; the Operator may choose a supported platform |
| No authority leak | An unsupported machine grants nothing; Facts are not promised where no baseline exists (RFC-0021 §2.1) |
| No shortcut | The runtime never fabricates a Family Profile for an unknown family (RFC-0021 §2.3; I-9) |

---

### Scenario 31 — Unexpected machine mutation

| Failure | The machine mutates in a way no approved Action caused (external actor, bug, or tampering) |
| Detection point | Read-only watchdog (RFC-0002 §4.2 STATE_CHANGED_DETECTED) or verification mismatch |
| Responsible component | Core; Fact Layer; Audit |
| Relevant RFCs | RFC-0002 §4.2; RFC-0006 §7 (Contradicted); RFC-0001 §10.4 |
| Invariants | I-8 (re-assess), I-10 (Facts invalidated by contradiction); V7 (contradiction always wins) |
| Authority owner | Core (record); Operator |
| Expected outcome | Dependent Facts invalidated; the path stops; the contradiction is surfaced; nothing proceeds on stale assumptions |
| Recovery path | Re-inspect → disclose → Operator decides; the mutation is audited as fact-lifecycle/execution records |
| No authority leak | An external mutation is a fact event, not an authorization (F4); nothing inherits approval from it |
| No shortcut | Contradiction is a hard stop, not a tie-breaker (RFC-0001 §10.4; RFC-0006 §8) |

---

## 4. Stress Matrix

Rows are the major components; columns are the failure categories of §2. A cell
marks how the architecture treats a failure of that category at that component:
**H** = Handles (defined reaction in the corpus), **E** = Escalates (the
component escalates to the Operator or a higher authority), **D** = Defers
(decided by another component/Operator, per ownership), **C** = Cannot occur
(structurally impossible per the corpus).

| Component \ Failure | Provider | Runtime | Approval | Verification | Context | Fact | Skill | Audit | Secret | Persistence | Environment | Operator | Unknown |
|---|---|---|---|---|---|---|---|---|---|---|---|---|---|
| **Presentation** | D (RFC-0010 §8) | E (RFC-0002 §10) | D (RFC-0004 §7) | E (RFC-0006 §7) | D (RFC-0012 §21) | E (RFC-0005 F11) | E (RFC-0002 §4.7) | E (RFC-0013 §21) | E (RFC-0009 §13) | E (RFC-0012 §21) | E (RFC-0021 §2) | E (RFC-0004 §9.1) | E (RFC-0007 §15.5) |
| **Orchestration Core** | H (RFC-0010 §8; RFC-0002 §4.3) | H (RFC-0002 §10) | D (RFC-0008 §15) | E (RFC-0002 §2.9) | H (RFC-0012 §21) | H (RFC-0005 §2) | H (RFC-0002 §4.7) | H (RFC-0013 §21) | E (RFC-0009 §13) | H (RFC-0012 §21) | E (RFC-0021 §2) | D (RFC-0004 §9.1) | E (RFC-0007 §15.5) |
| **Providers** | C (RFC-0010 §8 — provider failures are Core events, not provider-internal) | C (RFC-0010 §2 — provider cannot act on runtime) | C (RFC-0010 §2 — provider never approves) | C (RFC-0010 §2 — provider never verifies) | C (RFC-0010 §3 — provider receives only the View) | C (RFC-0005 F1 — provider never creates Facts) | C (RFC-0010 §2 — provider never executes) | C (RFC-0010 §3 rule 2 — no audit records to providers) | C (RFC-0010 §3 rule 3 — no secrets reach a provider) | C (RFC-0010 §2 — provider persists nothing) | C (RFC-0010 §5 — capability model) | C (RFC-0010 §2 — provider never approves) | C (RFC-0010 §8 — provider output is advisory) |
| **Diagnostics & Fact Layer** | C (RFC-0005 F6 — Facts are provider-independent) | H (RFC-0002 §4.2 collector failure) | C (RFC-0004 §1.1 — Fact Layer holds no approval authority) | H (RFC-0006 §6) | C (RFC-0012 §13 — Fact Layer feeds, not assembles Context) | H (RFC-0005 F16) | C (RFC-0011 §4 — skill output is Observation, not Fact) | C (RFC-0004 §4.12 — Audit persists, Fact Layer produces Facts) | C (RFC-0009 §1 — Fact Layer has no secret surface; SC6) | C (RFC-0012 §13 — Fact Layer never persists Context) | H (RFC-0005 F7; RFC-0021 §2.3) | C (RFC-0004 §1.1 — Facts never Operator-authored) | H (RFC-0007 §15.5 — Hostile quarantine) |
| **Executor** | C (RFC-0004 §4.9 — Executor runs only token-bound Actions) | H (RFC-0002 §10 executor failure) | H (RFC-0008 §8 — boundary re-validation; P8/P9) | D (RFC-0006 V2 — Executor may not verify its own work) | C (RFC-0012 §13 — Executor has no Context surface) | C (RFC-0004 §4.9 — Executor never decides what to run) | C (RFC-0011 §4 — Skill Actions run through the Executor under a token) | C (RFC-0002 invariant 13 — Executor writes to Audit, cannot fail it silently) | C (SC9 — no Action carries a secret; SC10 — elevation exposes nothing) | C (RFC-0004 §4.9 — Executor holds no persistence authority) | E (RFC-0001 §8.6 elevation) | D (RFC-0004 §4.9 — may decide *how*, never *what*) | C (RFC-0004 §4.9 — Executor never decides) |
| **Approval & Policy Engine** | C (RFC-0002 I-7 — classification never the LLM's self-report) | D (RFC-0008 §15 policy failure → fail closed) | H (RFC-0008 §8 tokens; P8/P13) | C (RFC-0008 — engine gates, it does not verify) | C (RFC-0008 — engine reads the Action's structured properties, not Context) | C (RFC-0008 P3 — policy is deterministic, not fact-driven) | C (RFC-0008 §5 — per-Action classification) | H (RFC-0002 invariant 13 — approval recorded before spent) | C (RFC-0008 §3 — no Action carries a secret) | C (RFC-0008 — policy is Operator-owned, not persisted session state) | E (RFC-0008 §6 — classification over structured properties) | D (RFC-0008 §4 — engine is the Operator's instrument) | E (RFC-0008 §15 — unknown class is fail-closed) |
| **Context Manager** | C (RFC-0010 §3 — provider output never enters Context raw) | C (RFC-0012 §12 — Context Manager is not the runtime) | C (RFC-0012 §13 — no approval surface) | C (RFC-0012 §26 — verification interacts, does not enter Context) | H (RFC-0012 §21 re-assembly) | D (RFC-0012 §13 — Fact Layer feeds Context) | H (RFC-0011 §26 — sanitization enforcement point) | C (RFC-0013 §7 — Context-boundary *records*, never Context itself) | H (RFC-0012 §13 — secret-free by construction; SC2) | H (RFC-0012 §21 — re-assembly over restore) | D (RFC-0012 §12 — composition over Facts) | C (RFC-0012 §8 — consent gate) | H (RFC-0007 §15.5 — Hostile excluded) |
| **Skill Runtime** | C (RFC-0011 §1 — a Skill is not a Provider) | C (RFC-0011 §4 — Skill holds no runtime authority) | C (RFC-0011 §4 — Skill never approves) | C (RFC-0011 §4 — Skill declares, never performs verification) | C (RFC-0011 §26 — Skill material enters via sanitization) | C (RFC-0011 §4 — Collector output is Observation, not Fact) | H (RFC-0011 §3, §16; RFC-0002 §4.7) | C (RFC-0011 §16 — audit interaction is unidirectional) | C (SC5 — no secret reaches a Skill) | C (RFC-0011 — Skill is loaded per-session) | E (RFC-0011 §2 — declared distro families) | D (RFC-0011 §3 — lifecycle owned by Orchestrator) | E (RFC-0011 §1 — unknown Skill is untrusted) |
| **Audit System** | C (RFC-0013 §28 — providers are invisible to the Audit) | H (RFC-0013 §11 — lifecycle driven by runtime events) | H (RFC-0013 §7 category 4 — recorded before spent) | H (RFC-0013 §7 category 7 — verification records) | C (RFC-0013 §7 category 9 — a record that material entered, never the material) | H (RFC-0013 §7 category 8 — fact-lifecycle records) | H (RFC-0013 §7 category 11 — skill-event records) | H (RFC-0013 §21, §22 — fail closed, reconcile) | C (RFC-0013 §31; SC4 — metadata only, never values) | H (RFC-0013 §19, §22 — retention, recovery) | C (RFC-0013 — Audit records, it does not interpret environment) | H (RFC-0013 §7 category 12 — operator-visibility records) | H (RFC-0013 §21 — AU8: a failed write is recorded as failed, never invented) |

---

## 5. Architecture Survivability

Every survivability claim below is the *reason* a failure cannot permanently
break the architecture. Each is cited.

1. **No failure creates authority.** Authority is owned (RFC-0004 §3), flows
   downward only (A8), and is exercised only through the gate (A9). A failure
   produces denial, degrade, or escalate — never a grant. Evidence: provider
   failure degrades without recommendations (RFC-0002 §4.3); policy failure
   blocks (RFC-0002 §10; P3); a forged token is refused (RFC-0008 §8); an
   expired token is dead (P8).
2. **No failure creates facts.** Facts come only from deterministic
   normalization of Observations (RFC-0005 §2; F1). Failure produces Unknown or
   Unavailable Fact status (RFC-0005 §4), Unknown outcomes (RFC-0006 V14), and
   Hostile quarantine (RFC-0007 §15.5) — never a fabricated claim. The runtime
   never fabricates (RFC-0002 invariant 9).
3. **No failure bypasses approval.** The gate is the only path to execution
   (RFC-0004 A9; RFC-0002 invariant 1). Every retry, revised step, and
   continuation is re-presented and re-approved (RFC-0008 §11; RFC-0002 §7,
   §8). A failure that blocks the gate blocks the action (RFC-0008 §15).
4. **No failure bypasses verification.** Verification always follows execution
   (RFC-0002 invariant 2), never skips (V14), and never trusts raw output
   (V1). A failed collect yields Unknown, never success (V5, V9).
5. **No failure exposes secrets.** The no-secrets boundary is three binary
   guarantees that hold closed on failure (RFC-0009 §0, §13): values exist only
   where they must; they never enter Context/View/Audit/extensions (SC2–SC5);
   unguaranteeable secrecy holds the boundary closed (SC14; RFC-0007 §15.7).
6. **No failure skips audit.** The audit is written before the consequence
   (RFC-0002 invariant 13); a failed audit write blocks its consequence and is
   disclosed (AU8; RFC-0004 §9.12). Nothing proceeds unrecorded.
7. **No failure skips normalization.** Raw output never reaches Context or a
   Provider View (RFC-0005 §2; RFC-0010 §3 rule 1). A normalization failure
   yields a marked Unknown, not a pass-through (F11, F16).
8. **No failure invents context.** Context is assembled under deterministic
   composition and bounds (RFC-0012 §12), re-assembled on loss (RFC-0012 §21),
   and never restored from an unconsented snapshot (RFC-0012 §21; RFC-0001
   §9.5). A gap is re-collected, not guessed (RFC-0002 §10).

---

## 6. Gap Analysis

If a failure cannot be resolved using the current RFC corpus, this section
records it as a gap. Nothing is invented to close it. As of the current corpus
(RFC-0000–RFC-0013), the injected failures in §3 all resolve to an existing
reaction. The gaps below are the *known, deliberate* deferrals the corpus itself
declares — they are recorded here so that an implementer does not mistake a
deferral for a defect, and so that a future RFC knows what it must own.

| Architectural Gap | Owning RFC | Severity | Reason | Impact |
|---|---|---|---|---|
| **Session persistence and resume semantics** (what survives a reboot beyond the resume marker; which Memory survives) | RFC-0014 (Planned, Post-MVP) | Medium | RFC-0002 §2.1/§3 route resume through the marker and "re-orient," but the durable-state contract is deferred to RFC-0014 (RFC-0000 §4; RFC-0012 §21 rule 4) | Until RFC-0014, resume behavior beyond re-orient is not fully specified; failure injection for deep resume relies on RFC-0002 invariants 8 and 15 alone |
| **Operator interface specifics** (exact disconnect/present semantics) | RFC-0015 (Planned, Required) | Medium | RFC-0002 §2.7 holds at Awaiting Approval, but the presentation contract is deferred (RFC-0000 §4) | Scenario 26 resolves to holding behavior from RFC-0002/RFC-0004 §9.1; the detailed interface contract is RFC-0015's |
| **Implementation ordering and build gates** | RFC-0020 (Planned, Required) | Low | The MVP build order is deferred (RFC-0000 §4) | Does not affect the architecture's failure behavior, only its construction order |
| **MVP definition** (which failure tests must exist) | RFC-0019 (Planned) | Low | Test baseline for Supported families is deferred (RFC-0021 §2.1) | The operational test surface for each failure scenario is RFC-0019's |
| **Phase budgets and retry policy values** | RFC-0002 §11 (open questions 2, 3) | Low | Timeout bounds and retry counts are referenced (RFC-0010 §8) but their values are open (RFC-0002 §11) | Scenario 3/4 behavior is structurally defined; the numeric budget is an implementation decision, not an architectural gap |

**Resolution rule.** None of the above is resolved by this document. Each is a
placeholder owned by the named future RFC. Until that RFC lands, the failure
behavior described in §3 — which rests on the invariants of RFC-0002, RFC-0008,
RFC-0012, and RFC-0013 — remains the defined behavior.

---

## 7. Final Consistency Verdict

Each verdict is answered from the RFC corpus alone.

**Q1. Can the architecture always return to a valid state?**

Yes. Recovery is determinism-first in every case (RFC-0002 §10; RFC-0008 §15):
re-establish truth by observation, disclose, let the Operator decide, act only
on fresh approval. No failure path requires the runtime to continue on
assumptions (RFC-0002 invariant 8); no terminal outcome is reached while work
is in flight (RFC-0002 invariant 14). The state machine's only exits are Idle,
END, and honest terminal states reached after Verification (RFC-0002 §2.13,
§2.14, §2.15, §3). The one exception is a permanent operator-external condition
(e.g., unsupported platform, Scenario 30), which fails closed to Failed or
Awaiting Input — itself a valid, honest state (RFC-0002 §2.14, §2.11).

**Q2. Can any failure permanently violate architecture?**

No. Every injected failure resolves to a defined reaction (RFC-0010 §8;
RFC-0008 §15; RFC-0013 §21; RFC-0009 §13), and every invariant that could be
touched is held at a boundary: tokens invalidate rather than persist (P8, I-11),
Context re-assembles rather than restores (RFC-0012 §21), the Audit reconciles
rather than rewrites (RFC-0013 §22), secrets invalidate rather than leak (SC15).
The corpus's invariants are "without exception, in every state" (RFC-0002 §9).
Failures that the corpus does not specify are recorded in §6 as gaps, not
silently defined.

**Q3. Can authority escape its owner?**

No. Authority is matrixed and closed: exactly one owner per row (RFC-0004 §3),
nothing grants itself authority upward (A8), and the gate is the only path to
execution (A9). Failure degrades or blocks; it never transfers authority to a
provider (RFC-0010 §2), a Skill (RFC-0011 §4), the Fact Layer (RFC-0004 §1.1),
or the Audit (RFC-0004 §4.12). An interrupted or rebooted system holds no
authority at all (I-15).

**Q4. Can secrets escape containment?**

No. The containment is three binary guarantees that hold closed on failure
(RFC-0009 §0, §13): a value exists only where and when it must; it never enters
Context, Provider View, output summaries, the Audit, telemetry, or extensions
(SC2–SC5); and when secrecy cannot be guaranteed, the boundary holds closed
(SC14; RFC-0007 §15.7). Suspected exposure is treated as compromise and
destroyed (SC15; RFC-0007 §6.10). No failure path relaxes a guarantee — a
failure of redaction withholds rather than releases (RFC-0009 §13).

**Q5. Can verification be bypassed?**

No. Verification always follows execution (RFC-0002 invariant 2), never skips
(V14), never runs without fresh Facts (V4), and never accepts a provider's or
Executor's self-report (V1; RFC-0004 §4.9). Unknown is preferable to false
success (V5). A failure of Collect yields Unknown, not a pass (RFC-0006 V14,
V16). There is no path from Executing to Completed that omits the
Collect→Compare→Outcome sequence (RFC-0006 §6; RFC-0002 invariant 2, I-14).

**Q6. Can audit be bypassed?**

No. The audit is written at each boundary before its consequence (RFC-0002
invariant 13); a write failure blocks the consequence (AU8; RFC-0004 §9.12) and
is disclosed loudly (RFC-0013 §21). Recovery reconciles, it never rewrites
(RFC-0013 §22). Nothing in the corpus permits a consequence to proceed
unrecorded, and failure makes this stricter, not looser.

**Q7. Can provider output become trusted?**

No. Provider output is data, never authority (RFC-0007 T4); it can at most
become a Proposal (RFC-0004 A1) and never a Fact (RFC-0005 F1, F6; RFC-0010 §2,
§8). There is no mechanism by which a provider's sentence gains facthood,
executability, or approval authority. Hallucination is contained by construction
(RFC-0010 §8 rule 2). The trust class of provider output cannot be upgraded by
any failure (RFC-0007 T9: sanitization never upgrades; failure degrades to
Hostile).

---

## End State

Thirty-one failures injected; every one resolves within the RFC corpus. The
architecture survives failure the same way it executes the happy path: by
determinism, by the gate, by verification, by audit-before-consequence, and by
fail-closed boundaries — none of which a failure can switch off. Where the
corpus has not yet spoken (RFC-0014, RFC-0015, RFC-0019, RFC-0020, and the
open quantity questions of RFC-0002), this document records the deferral as a
Gap and adds nothing.
