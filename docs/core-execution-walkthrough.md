# Core Execution Walkthrough — One Request, End to End

> **Document type:** Consistency proof, not an RFC.
> **Read this first:** This document **defines nothing new**. It simulates a
> single request through the architecture defined by the accepted RFC series
> (RFC-0000–RFC-0013), tracing every stage to the RFC that owns it. Where
> anything appears here that is not backed by an RFC citation, that is a bug in
> this document, not a feature to implement.
>
> **Scope:** One goal, one distro, one package. The request is deliberately
> small so the walkthrough can be complete.
>
> **Normative authorities:** The RFCs named in each stage. This document adds no
> stage, no boundary, and no invariant.

---

## 0. Purpose and Standing

The RFC series is normative and cross-references itself. This walkthrough exists
to prove the whole is consistent: that a request can move through the system,
that every authority transfer is named and lawful (RFC-0004 §1.2, §8), that no
stage can be skipped (RFC-0005 §2), and that every boundary in the series is
observed by the pipeline as a whole.

Three things this document will not do:

1. **Invent architecture.** Every claim cites an existing RFC, section, or
   invariant. No new component, gate, record, or rule appears here.
2. **Decide open questions.** Where the RFCs explicitly leave a decision open
   (for example RFC-0014 resume semantics, RFC-0015 presentation specifics), the
   walkthrough marks the dependence and does not resolve it.
3. **Bind future RFCs.** Nothing in this document constrains RFC-0014–RFC-0020
   beyond what their dependency RFCs already require.

**The canonical vocabulary is binding** (RFC-0003 §2). The words *goal*, *fact*,
*observation*, *action*, *step*, *proposal*, *approval*, *approval token*,
*post-condition*, and *verification* are used exactly as defined there. When
this document says *command*, it means a possible implementation of an Action,
never a first-class architectural term (RFC-0003 §2.6 Action).

---

## 1. The Request and Its Setting

```
Operator:  "Update nginx to the latest package version."
```

**Setting.** A fresh session on a Linux host. The session has initialized
(RFC-0002 §2.1), the runtime is in **Idle** (RFC-0002 §2.2), and the goal loop
`gather → plan → propose → approve → act → verify` is armed (RFC-0002 §1).

**What the request is.** An **OP_GOAL** event (RFC-0002 §2.2): the Operator
adopts a Goal. The goal is a statement of desired machine state, expressed in
the session's terms (RFC-0003 §2.6 Goal). It is *not* a command, not a list of
steps, and not a Fact. The string "Update nginx…" carries no machine authority;
it is material for the Orchestration Core to interpret (RFC-0001 §5
Conversation/Orchestration Core), not a string for the Executor (RFC-0002
invariant 5).

**What the request is not.** It does not name a package version, a repository, a
distro family, or a method. None of those are known yet. The first duty of the
pipeline is to *establish* what "nginx", "latest", and "package version" mean on
this machine, as Facts, before anything is proposed (RFC-0002 §2.3, §2.5).

---

## 2. Lifecycle at a Glance

The request is walked over the RFC-0002 state machine (§2, §3). Stages in the
pipeline below are numbered for readability; the **RFC-0002 state** column is
the authoritative mapping and governs all transitions.

| Pipeline stage (§3) | RFC-0002 state (§2) | What happens |
|---|---|---|
| 1. Operator request | Idle → (OP_GOAL) → Machine Inspection | Goal adopted |
| 2. Runtime initialization | Session Initialization (§2.1) | Session boot, prerequisite check, audit open |
| 3. Context assembly | Context Building (§2.4) | Provider View assembled, secret-free |
| 4. Provider interaction | Diagnosis (§2.5) | Provider reasons over the View only |
| 5. Proposal creation | Planning (§2.6) | Plan normalized into discrete Actions |
| 6. Approval generation | Planning → (edge) → Awaiting Approval | Policy classification + gate |
| 7. Approval verification | Awaiting Approval (§2.7) → Executing (§2.8) | Operator decision, token minted, re-validation at boundary |
| 8. Skill participation | Diagnosis / Planning (§2.5, §2.6) | Optional structured Plan source, same gate |
| 9. Fact normalization | Machine Inspection / Verification (§2.3, §2.9) | Observation → Fact by deterministic rules |
| 10. Verification planning | Planning (§2.6) | Postconditions declared with the Proposal |
| 11. Machine execution | Executing (§2.8) | Executor runs one approved Action |
| 12. Post-execution inspection | Verification (§2.9, Collect) | Read-only re-observation |
| 13. Fact comparison | Verification (§2.9, Compare) | Facts vs. Postconditions, deterministic |
| 14. Outcome classification | Verification (§2.9) → Completed (§2.13) | Outcome named, honestly |
| 15. Audit creation | Every boundary (§4, §6) | Written before the consequence |
| 16. Transcript generation | Completed (§2.13) | Derived, read-only view of the record |
| 17. Return to Idle | Completed → Idle (§2.13) | Ready for the next goal |

Stages 8–10 are **concurrent or interleaved** in the real flow (a Skill may
participate in Diagnosis or Planning; Postconditions are declared *during*
Planning, not after). They are separated here so each owner is clear.

---

## 3. The Seventeen Stages

Each stage names: the component responsible, the RFC that owns it, the inputs
and outputs, the pre- and post-conditions, the invariants enforced, the
authority held (and the authority explicitly *not* held), and the authority
transfer that exits the stage.

> **Invariant shorthand used throughout.** RFC-0002 invariant N is written
> **I-N**; RFC-0004 invariant is **A-N**; RFC-0008 is **P-N**; RFC-0005 is
> **F-N**; RFC-0006 is **V-N**; RFC-0007 is **S-N** and trust class **T-N**;
> RFC-0009 is **SC-N**; RFC-0012 is **CM-N**; RFC-0011 is **SK-N**. Full text is
> in the owning RFC; this document cites them, it does not restate them as new
> rules.

---

### Stage 1 — Operator request

| Field | Value |
|---|---|
| RFC-0002 state | Idle → Machine Inspection |
| Component | Presentation; Conversation/Orchestration Core (RFC-0001 §5) |
| RFC owner | RFC-0002 §2.2 (OP_GOAL), §3 |
| Inputs | Operator's typed goal; session identity |
| Outputs | An adopted Goal; OP_GOAL event; transition to Machine Inspection |
| Preconditions | Session Initialized (§2.1); runtime Idle; audit store open (RFC-0013 §11) |
| Postconditions | Goal adopted; Inspection armed; nothing on the machine has changed |
| Invariants | (none triggered yet — no authority has been exercised) |
| May not decide | The Core may not yet classify, propose, or act on the goal |

**Authority at this stage.** The Operator holds all authority. The goal is a
statement of intent, not a grant. The Core holds authority only to *interpret*
the goal (RFC-0004 §1.2, first authority: Observe — and not even that, until
the Core dispatches Collectors).

**Authority transfer (exit).** The Operator delegates *interpretation* to the
Orchestration Core. No machine authority is granted by typing the request
(RFC-0004 §9.1: the Operator is not defended against — but the request itself
authorizes nothing; only the gate authorizes).

---

### Stage 2 — Runtime initialization

| Field | Value |
|---|---|
| RFC-0002 state | Session Initialization (§2.1) |
| Component | Orchestration Core; Audit System |
| RFC owner | RFC-0002 §2.1; RFC-0013 §11 (audit lifecycle) |
| Inputs | Configuration; provider and skill declarations; resume marker (if any) |
| Outputs | A live session: configured, bounded, audit-backed |
| Preconditions | A configured, valid session environment |
| Postconditions | Providers and Skills resolved; audit store opened; prerequisites verified; Idle reached |
| Invariants | I-4 (LLM only ever consulted through a Provider View), I-9 (never fabricates), I-15 (no standing authorization across a boundary) |
| May not decide | The runtime may not adopt assumptions; a resume marker may only *continue at re-orient* (RFC-0002 §2.1, §3), never resume in-flight machine work (I-8) |

**Placement note.** In the RFC-0002 lifecycle, initialization strictly precedes
Idle and therefore precedes OP_GOAL (Stage 1). It is listed second here for
readability of the pipeline; the state machine's ordering is authoritative
(RFC-0002 §1, §3). On a *resume*, §2.1 routes through the resume marker and the
re-orient path — the details of what survives a resume belong to RFC-0014
(RFC-0000 §4), which is Post-MVP and out of scope here.

**Authority at this stage.** Configuration grants the Core its *session
authority*: the ability to run the goal loop. It grants no per-Action authority
(I-15). Opening the audit store creates the boundary where every later
authority use will be recorded before its consequence (RFC-0002 invariant 13).

**Authority transfer (exit).** The runtime hands the loop to Idle. Authority to
*begin observing the machine* is now exercised only in response to an OP_GOAL.

---

### Stage 3 — Context assembly

| Field | Value |
|---|---|
| RFC-0002 state | Context Building (§2.4) |
| Component | Diagnostics & Fact Layer; Context Manager (RFC-0001 §5, §9) |
| RFC owner | RFC-0012 §12 (composition), §13 (boundaries), §9 (what never enters); RFC-0005 §2 (Context); RFC-0007 §11 (sanitization); RFC-0009 §3 (classification) |
| Inputs | Fresh, provenanced Facts (from Machine Inspection); the Goal; bounded session history; routing state |
| Outputs | The Provider View — the one thing a provider may see (RFC-0010 §3) |
| Preconditions | Facts present and fresh (F-4, F-5); nothing stale reused (I-10) |
| Postconditions | A secret-free, purpose-limited, size-bounded Provider View (RFC-0010 §3, PR14); nothing else can leave |
| Invariants | S1 (sanitize is not trust), S2 (contain first, sanitize second), S3 (neutralize control, preserve content); T7 (secrets one-way), T9 (sanitization never upgrades), T10 (Context secret-free/bounded); SC2 (default secret-free), SC3 (no secret in a Provider View); CM1–CM15 (composition, bounds, freshness) |
| May not decide | The Context Manager may never include a secret (RFC-0004 §4.11); may never include raw output (RFC-0005 §2); may never post-hoc scrub instead of assembling within bounds (RFC-0012 §12 rule 6) |

**What is in this View for our request.** Facts from Stage 9 (below): distro
family, configured repository, current nginx package version, availability of a
newer version. The Goal. Bounded history of the current reasoning thread.
Nothing else. No audit records, no secrets, no raw package-manager output
(RFC-0010 §3 rules 1–3).

**Authority at this stage.** The Context Manager holds *selection authority*:
what the provider may reason over. This is the authority that makes the no-
secrets guarantee real (RFC-0009 §0 guarantee 2). The LLM has none of it.

**Authority transfer (exit).** A sanitized, secret-free Provider View crosses
the trust boundary toward the provider (RFC-0001 §7; RFC-0007 §11). This is the
*only* channel (PR14). Whatever is in the View is all the provider will ever
see; whatever is not in it is unreachable by the provider.

---

### Stage 4 — Provider interaction

| Field | Value |
|---|---|
| RFC-0002 state | Diagnosis (§2.5) |
| Component | Providers (LLM adapters) (RFC-0001 §5); Conversation/Orchestration Core |
| RFC owner | RFC-0010 §2 (responsibilities), §3 (inputs), §4 (outputs), §5 (capability model); RFC-0002 §4.3 (provider events) |
| Inputs | The Provider View (Stage 3); the Goal |
| Outputs | Structured provider outputs: Proposal, Explanation, Questions, Clarifications, Alternative Plans, Refusal, Failure, or Need More Evidence (RFC-0010 §4) |
| Preconditions | A valid Provider View (Stage 3); a provider that can reason over it |
| Postconditions | Structured output routed to its deterministic consumer; nothing executed; no Fact created |
| Invariants | I-4 (LLM only via Provider View); I-9 (never fabricates); F1/F6 (a provider sentence is never a Fact); PR11 (provider failure degrades, never crashes); PR14 (View is the only channel) |
| May not decide | The provider may not execute (RFC-0010 §2), classify authority (§2), create Facts (F6), verify (V1), approve (§2), escalate (A8), store secrets (§2, §11), or modify policy (§2) |

**Malformed output is handled, not honored.** Any provider output that is not
one of the finite structured results — raw text, a claim presented as fact, an
instruction to act — is malformed and degrades the interaction (RFC-0010 §4
"Nothing else", §8; PR11; RFC-0002 §4.3: a structurally non-compliant reply is
treated as refusal).

**For our request.** The provider reads the View: nginx is installed at version
X; the configured repository offers version Y; the machine is a supported distro
family. It returns a Proposal: *upgrade package nginx to version Y from the
configured repository*, with an expected Post-condition (Stage 10). That
Proposal is a *suggestion* (RFC-0010 §2: everything a provider produces is
advisory).

**Authority at this stage.** The provider holds **Propose** and **Infer**
authority (RFC-0004 §1.2, §4.10 for Skills by analogy; RFC-0010 §2) — as a
*candidate*, never final. It holds nothing else. Its output has no authority
(RFC-0010 §2: "None of them changes the machine").

**Authority transfer (exit).** The Core receives the Proposal as *candidate
material*. Authority to decide what is approvable has never left the Core/Policy
side; it now returns fully to the deterministic machinery (RFC-0004 §1.2:
Observe → Propose → Infer → Verify order).

---

### Stage 5 — Proposal creation

| Field | Value |
|---|---|
| RFC-0002 state | Planning (§2.6) |
| Component | Orchestration Core; Approval & Policy Engine (classification) |
| RFC owner | RFC-0003 §2.6 (Proposal, Plan, Step, Action); RFC-0002 §2.6 (Planning), §6 (component consultation); RFC-0008 §9 (Action carries its expected effect) |
| Inputs | Provider/Skill Proposal (advisory); grounded Hypotheses (RFC-0003 §2.5); Facts |
| Outputs | A normalized Plan of discrete Steps; each Step = Action + preconditions + expected Post-condition + verification method (RFC-0003 §2.6 Step) |
| Preconditions | Grounded evidence; no contradiction blocking (RFC-0006 §8) |
| Postconditions | A Plan that names exactly what runs, and what state it will produce; nothing executed (I-3) |
| Invariants | I-3 (Planning never executes), I-5 (Actions built from sanctioned structures, never shell strings), I-6 (deviation requires fresh approval), V10 (Postconditions fixed before Compare) |
| May not decide | Planning may not skip classification, may not merge two Actions into one unclassified unit, may not invent post-hoc Postconditions (V10) |

**For our request.** One Plan, one Step: **Action** = *upgrade the `nginx`
package to the version available in the configured repository*; **Preconditions**
= nginx is installed, repository is reachable, no package-management lock is
held (Facts); **expected Post-condition** = the `nginx` package version equals Y;
**verification method** = re-inspect the package version (a Collector), compare
to Y. The word "upgrade" is the Action's description; the Executor's sanctioned
implementation is what runs (RFC-0003 §2.6 Action).

**Authority at this stage.** The Core holds **Propose** authority (RFC-0004
§1.2). The Plan is a proposal, nothing more (RFC-0003 §2.6 Plan). It changes
nothing.

**Authority transfer (exit).** The Plan is handed to the Approval & Policy
Engine. Authority to *classify* it passes to deterministic Policy (RFC-0004
§1.2: Policy Engine owns Risk classification, never the LLM — I-7).

---

### Stage 6 — Approval generation

| Field | Value |
|---|---|
| RFC-0002 state | Planning → (classification edge) → Awaiting Approval (§2.6, §2.7) |
| Component | Approval & Policy Engine; Presentation (gate presentation) |
| RFC owner | RFC-0008 §6 (risk classification), §7 (gates), §8 (tokens); RFC-0004 §4.8 (Approval Engine), §8 A9/A10; RFC-0002 §4.4 (PLAN_READY, ACTION_CLASSIFIED) |
| Inputs | The Plan (Stage 5) |
| Outputs | A classified Plan: each Step carries its risk class and gate; presentation to the Operator |
| Preconditions | A complete Plan with declared Postconditions (RFC-0008 §9; RFC-0010 §4 rule 2) |
| Postconditions | Classification recorded before the gate outcome (RFC-0013 §7 category 3); Operator presented with the exact proposed scope (RFC-0008 §4: bound to what is shown) |
| Invariants | I-7 (risk classification deterministic, never LLM self-report); A9 (the gate is the only path to execution); RFC-0001 §8.2 (default deny), §8.5 (deterministic risk) |
| May not decide | The Policy Engine may not classify by the LLM's characterization (I-7); may not loosen policy on its own (RFC-0004 §9.7, fail-closed P3); the engine decides *the gate*, never *the answer* |

**For our request.** Upgrading a system package changes the `nginx` service and
package state, so it is classified **Consequential** (RFC-0008 §6 example
domain: toggling a system service, changing installed packages) and gated at
**Confirm-with-warning**. This is a Policy Engine determination over the
Action's structured risk-relevant properties (RFC-0001 §8.5), not a provider
self-report (I-7). Presentation shows: the Step, its Action, the risk class, the
gate, preconditions, expected Post-condition, and verification method (RFC-0008
§11 plan envelope presentation).

**Authority at this stage.** The Policy Engine holds **Risk classification**
authority only. It does not approve; it *gates* (RFC-0004 §4.8). Approval
authority remains with the Operator.

**Authority transfer (exit).** The classified, gated plan moves to **Awaiting
Approval**. The decision now belongs to the human — there is no other approver
in the system (RFC-0004 §7; RFC-0008 §4: the Approval Engine is the Operator's
instrument, never the decision-maker).

---

### Stage 7 — Approval verification

| Field | Value |
|---|---|
| RFC-0002 state | Awaiting Approval (§2.7) → Executing (§2.8) |
| Component | Presentation (collects the decision); Approval & Policy Engine (token mint); Executor (boundary re-validation) |
| RFC owner | RFC-0008 §8 (tokens), §10 (TOCTOU), §13 P8/P9/P13; RFC-0002 §2.7, §2.8, §9 invariants 11–13; RFC-0004 A10 |
| Inputs | The presented plan (Stage 6); the Operator's explicit decision |
| Outputs | An Approval Token (or a refusal); a revalidated, executable Action |
| Preconditions | Plan presented in full (RFC-0008 §11); Operator explicitly decides |
| Postconditions | Token issuance written to the Audit *before* the token is spent (I-13, A10, P13); token scoped to exactly what was shown; re-validation at the execution boundary |
| Invariants | I-11 (tokens scoped/consumable/invalidated), I-12 (blocked actions only via explicit audited override), I-13 (audit before consequence), I-15 (no standing authorization); A10 (approval recorded before spent); P8 (token invalidation never resurrected), P9 (preconditions re-validated at the boundary) |
| May not decide | No "always yes" (RFC-0008 §4; RFC-0001 §8.3); no silent approval (RFC-0008 §4); the token is single-use for a single Action or one approved plan envelope (RFC-0008 §4) |

**For our request.** The Operator sees: *"Upgrade nginx from X to Y
(Consequential, Confirm)."* They approve. The engine mints a token bound to this
Action, this time, and the machine state shown (I-11), and writes the approval
to the Audit *before* the Executor can spend it (A10, P13, I-13).

**The TOCTOU gap is closed from both sides.** Between approval and execution the
machine is not frozen. RFC-0008 refuses to execute on stale preconditions (P9,
§10), and RFC-0006 refuses to verify outcomes reached without fresh
preconditions (RFC-0006 §4). At the boundary the Executor re-observes the
precondition Facts, checks the token is unexpired, unspent, state-consistent,
and re-reads the Action scope (RFC-0002 §2.8, invariant 11). Any change — a
state change (I-11, P8), a policy reload (P8), an interrupt, a reboot (I-15) —
leaves the token unusable; the plan re-opens (Stage 17 note / Replanning,
RFC-0002 §2.10).

**Authority transfer (exit).** The Operator's explicit decision, embodied in the
token, is the *only* grant of execution authority (A9). Authority to run *this*
Action, *within the declared bounds*, passes to the Executor. The Executor may
decide only *how* within those bounds — never *what* to run, correctness, or
chaining (RFC-0004 §4.9).

---

### Stage 8 — Skill participation (if any)

| Field | Value |
|---|---|
| RFC-0002 state | Diagnosis / Planning (§2.5, §2.6) |
| Component | Skill Runtime (RFC-0001 §5 Skills; RFC-0011) |
| RFC owner | RFC-0011 §1 (what a Skill is), §3 (ownership), §4 (authority), §16 (audit interaction); RFC-0002 §4.7 (SKILL_UNAVAILABLE) |
| Inputs | A Skill's declared surface; a Collector bundle it provides; its structured Plan template |
| Outputs | Observations (from bundled Collectors) and/or a candidate Plan — both *candidate material* |
| Preconditions | Skill authenticated and registered (RFC-0011 §3); declared targets/privileges/risk/verification reviewed (RFC-0001 §11.3) |
| Postconditions | Skill material enters only via the sanitization enforcement point (RFC-0012 §13; RFC-0011 §26); its Actions pass the gate like any other Proposal |
| Invariants | SK4 (every Skill Action passes the full gate; no unit approval), SK5 (a Skill is untrusted until authenticated and within Policy); RFC-0011 §4 (Skill Actions run only through the Executor under a valid token); A9 (no bypass of the gate); RFC-0001 §8.9 (supply chain defended, treated untrusted even after authentication); SC5 (no secret reaches an extension) |
| May not decide | A Skill cannot execute (RFC-0011 §4), approve (§4), create Facts (§4, RFC-0007 §6.11: Collector output is Observation, not Fact), verify (§4: it *declares* its verification approach, it cannot *perform* verification), escalate (§4), modify policy (§4), or reach the machine directly (§4, RFC-0001 §8.4) |

**For our request.** A *package-update* Skill may contribute a bundled Collector
that reads the repository state more precisely, and a structured Plan template.
That Plan is treated exactly like the provider's Proposal: normalized, gated,
classified (Stage 5–6). The Skill's own verification *declaration* becomes
input to Verification *planning* (Stage 10), not to the Verify step itself.

**Authority at this stage.** The Skill holds **Propose/Infer/Explain** as a
*candidate* (RFC-0004 §4.10), and nothing else. No Skill is ever approved as a
unit; only its individual Actions are classified and approved (RFC-0011 §3).

**Authority transfer (exit).** Skill material is folded into the same
deterministic pipeline. No new authority is granted by the Skill's existence
(RFC-0011 §4).

---

### Stage 9 — Fact normalization

| Field | Value |
|---|---|
| RFC-0002 state | Machine Inspection (§2.3); re-observed in Verification (§2.9) |
| Component | Diagnostics & Fact Layer; Collectors (RFC-0003 §2.4 Collector) |
| RFC owner | RFC-0005 §2 (the Observation→Fact pipeline), §3 (canonical model), §13 (F1–F8); RFC-0003 §2.4 (Observation, Fact); RFC-0007 §10 (trust classes) |
| Inputs | Raw Output (tool utterance, distro-specific, untrusted) |
| Outputs | Observations → normalized Canonical Facts (status, provenance, freshness, machine identity, scope) |
| Preconditions | Inspection is read-only (RFC-0002 invariant 3; RFC-0003 §2.4) |
| Postconditions | Facts with provenance and staleness bounds; a failed collection produces a "fact unknown" Fact, never an assumption (RFC-0003 §2.4; RFC-0002 §10) |
| Invariants | F1 (Fact never originates from the LLM), F2 (Facts never contain permissions), F3 (Facts never execute), F4 (Facts never imply actions), F5 (deterministic normalization, a pure function), F6 (provider-independent), F7 (distro-independent), F8 (immutable observations); I-10 (Facts carry provenance and expire) |
| May not decide | The Fact Layer never mutates, never consumes secrets into long-term context (RFC-0001 §5), never lets a failed collector block the pipeline with a guess (RFC-0002 §10 collector failure) |

**For our request (the full pipeline):**

| Form | Content | Responsible RFC |
|---|---|---|
| **Raw Output** | `apt-get`/dnf-style listing: package name, installed version, candidate version, distro strings — raw bytes, untrusted | RFC-0005 §2; RFC-0003 §2.4 |
| **Observation** | Raw Output + Collector identity + run metadata (timestamped, provenance-carrying) | RFC-0005 §2; RFC-0003 §2.4 (Observation) |
| **Normalization** | Observation + Canonical Definition + Family Profile; deterministic parse; reject/Unknown/truncate-with-marker | RFC-0005 §2; RFC-0003 §2.4 (Fact); RFC-0021 §2.3 (Family Profile) |
| **Canonical Fact** | `nginx`: installed=version X; `nginx`: candidate=version Y; distro family; repository reachable | RFC-0005 §3 |
| **Evidence Set** | Grouped, related Facts — the unit in which Facts travel (RFC-0005 §9) | RFC-0005 §9 |
| **Context** | Selected Evidence Sets, bounded by purpose/size/secrecy, sanitized → Provider View | RFC-0005 §2; RFC-0012 §12–§13; RFC-0009 |

*Nothing skips a stage, and no stage's output is knowledge before the next has
run* (RFC-0005 §2).

**Authority at this stage.** The Fact Layer holds the **Observe** and
**normalize** authority (RFC-0004 §1.1: Truth/Facts owned by the Fact Layer,
never LLM- or Operator-authored). It is the only producer of Facts (F1).

**Authority transfer (exit).** Facts leave the machine world as canonical,
provenanced claims. They may now enter Context (Stage 3) and Verification
(Stage 13), and nothing else may call a machine claim a Fact (F1, F6).

---

### Stage 10 — Verification planning

| Field | Value |
|---|---|
| RFC-0002 state | Planning (§2.6) |
| Component | Orchestration Core (Plan authoring) |
| RFC owner | RFC-0006 §5 (Postconditions), §4 (Preconditions); RFC-0003 §2.6 (Step: preconditions, expected Post-condition, verification method) |
| Inputs | The proposed Action; known Facts |
| Outputs | The Step's declared Postconditions (state, not implementation) and verification method |
| Preconditions | A Proposal must carry its expected effect or it is incomplete (RFC-0010 §4 rule 2; RFC-0008 §9) |
| Postconditions | Postconditions fixed before any Compare (V10); verification method named at planning time |
| Invariants | V10 (Postconditions fixed before Compare — never invented after), V1 (verification never trusts raw output or exit status alone), V13 (a diagnostic-only goal verifies completeness of evidence, not a change) |
| May not decide | Verification planning may not decide the *outcome* (that is Compare's); may not add a step after execution to match observed state (V10) |

**For our request.** The Postcondition is a **Fact-shaped expectation**:
Subject = `nginx` package; Property = installed version; Status = Y; freshness
bound = the window within which the check is valid (RFC-0006 §5; RFC-0005 §11).
This is *state*, not "we ran the upgrade command" (RFC-0006 §5: "The file
contains the new value" is a Postcondition; "we ran the edit command" is an
execution record). The verification method is: re-run the package-version
Collector, then Compare.

**Authority at this stage.** Plan authoring authority (Propose). The expected
state is *declared*, not observed.

**Authority transfer (exit).** The declared Postconditions bind the later
Compare. From this point, success is defined as "the machine matches Y" — the
LLM does not get to redefine it later (V10).

---

### Stage 11 — Machine execution

| Field | Value |
|---|---|
| RFC-0002 state | Executing (§2.8) |
| Component | Executor (RFC-0001 §5 Action Execution) |
| RFC owner | RFC-0004 §4.9 (Executor profile), §8 A9/A10; RFC-0002 §2.8; RFC-0008 §10 (TOCTOU) |
| Inputs | A valid, unexpired, state-consistent Approval Token bound to one Action (I-11) |
| Outputs | The Action runs against the machine within its declared bounds; start/end recorded |
| Preconditions | Token revalidated at the boundary: fresh Precondition Facts match declared state; no invalidating change (RFC-0006 §4; P9) |
| Postconditions | Exactly the approved Action ran; nothing else; audit records written at the boundary (RFC-0013 §7 category 6) |
| Invariants | I-1 (execution never starts without approval), I-2 (verification always follows), I-5 (no untrusted text interpolated — sanctioned structures only), I-8 (any halt → re-assess), I-11 (token consumable, single-use), I-13 (audit before consequence) |
| May not decide | The Executor may not decide *what* to run, correctness, or chaining (RFC-0004 §4.9); may not run a second Action under the same token (I-11); may not retry a failed step automatically (RFC-0008 §11) |

**For our request.** The Executor runs the sanctioned `nginx` upgrade
implementation under the token. If the Action requires elevation, elevation is
explicit, scoped, re-authenticated, and only for the approved Action (RFC-0001
§8.6; SC10: elevation exposes nothing). If the Action fails mid-way, the
Executor does not retry; it reports, and the state is treated as uncertain
(RFC-0002 §10 partial execution; RFC-0008 §11).

**Authority at this stage.** The Executor holds the **Execute** authority — the
only actor that does (RFC-0004 §4.9, A2). It holds it *only* under the token and
only within declared bounds.

**Authority transfer (exit).** Execution authority is spent. The moment the
Action ends, verification authority takes over (I-2). The Executor may not
verify its own work (RFC-0004 §4.9; RFC-0006 V1).

---

### Stage 12 — Post-execution inspection

| Field | Value |
|---|---|
| RFC-0002 state | Verification (§2.9), Collect |
| Component | Diagnostics & Fact Layer (Collectors) |
| RFC owner | RFC-0006 §6 (verification process: Collect); RFC-0002 §2.9 |
| Inputs | The executed Action's identity; the Postconditions to check |
| Outputs | Fresh post-execution Observations |
| Preconditions | The Action has ended; no terminal outcome is claimed yet (I-14) |
| Postconditions | Fresh Facts about the actual post-attempt state; the machine world re-observed |
| Invariants | V8 (verification never mutates — Collect is read-only), V12 (re-verification follows every trust-lapse trigger), I-2 (verification always follows execution) |
| May not decide | Collect may not assume success (V2); may not reuse pre-execution Facts as if fresh (V4, V12) |

**For our request.** The package-version Collector runs again, read-only. The
result is normalized into fresh Facts (Stage 9 pipeline). These Facts are the
*actual* state, whatever it is.

**Authority at this stage.** Observe. Same Fact Layer authority as Stage 9, now
in its verification role (RFC-0006 §6).

**Authority transfer (exit).** Fresh Facts pass to Compare. Nothing has decided
the outcome yet.

---

### Stage 13 — Fact comparison

| Field | Value |
|---|---|
| RFC-0002 state | Verification (§2.9), Compare |
| Component | Diagnostics & Fact Layer (deterministic Compare) |
| RFC owner | RFC-0006 §6 (Compare), §8 (contradictions); RFC-0005 §8 (Contradicted Fact representation) |
| Inputs | Fresh post-execution Facts; declared Postconditions (Stage 10) |
| Outputs | An Outcome determination (Stage 14) |
| Preconditions | Facts fresh (V4); Postconditions fixed (V10) |
| Postconditions | Facts compared, not interpreted; nothing mutated (V8) |
| Invariants | V3 (deterministic — identical Facts, identical Outcomes), V4 (never stale Facts), V7 (contradiction always wins), V9 (missing evidence is not evidence of success), V10 (Postconditions fixed before Compare) |
| May not decide | Compare may not consult the LLM (V3, RFC-0004 §1.1: verification is never the LLM); may not pick a winner between conflicting Facts (V7, RFC-0006 §8) |

**For our request.** Compare checks: does the observed `nginx` version equal Y,
on fresh Facts? If yes → Verified Success. If the observed version is X (unchanged) →
Verified Failure. If the Collect failed or Facts went stale → Unknown. If two
Facts conflict → Contradicted. Compare does not "explain away" a mismatch (V7).

**Authority at this stage.** The Fact Layer holds verification authority:
state-based, deterministic, never LLM (RFC-0004 §1.1).

**Authority transfer (exit).** The determination — not the interpretation of it
— is handed to Outcome classification.

---

### Stage 14 — Outcome classification

| Field | Value |
|---|---|
| RFC-0002 state | Verification → Completed / Replanning / Awaiting Input (§2.9, §2.13) |
| Component | Orchestration Core (routing); Fact Layer (deterministic Compare result) |
| RFC owner | RFC-0006 §7 (Outcomes); RFC-0002 §2.9, §2.10, §2.13, §2.14 |
| Inputs | The Compare result (Stage 13) |
| Outputs | A named, honest Outcome; routing to the next state |
| Preconditions | Compare completed (V14: never silently skips) |
| Postconditions | The Outcome is reported with its evidence and provenance (V11); success is never claimed without fresh Facts (V5) |
| Invariants | V5 (Unknown preferable to false success), V6 (partial success is distinct), V11 (evidence + Outcome recorded), V14 (never silently skip), V15 (confidence never changes the Outcome), V16 (catastrophic cases surfaced); I-14 (no terminal outcome while machine work is in flight) |
| May not decide | Outcome classification may not call Unknown "success" (V5), may not collapse partial success (V6), may not let confidence upgrade an Outcome (V15) |

**For our request.** Outcome = **Verified Success**: the machine's observed state
matches the declared Postconditions, on fresh Facts (RFC-0006 §7). The outcome,
the Facts compared, and the evidence references are recorded (V11; RFC-0013 §7
category 7). The runtime reports the verified state, what was done, and any
caveats (RFC-0002 §2.13). Completed is entered — but note its entry conditions
are met only *because* verification passed; an unverified outcome stays in
Verification or Awaiting Input, or is Completed-with-caveat and honestly labeled
(RFC-0002 §2.13).

**Authority transfer (exit).** The goal loop hands back to the Operator: the
outcome is reported and the authority to choose next steps (a new goal, a
rollback *proposal*, or exit) returns to the human (RFC-0002 §2.13; RFC-0006 §7:
reverting is a *proposal*, never an automatic undo).

---

### Stage 15 — Audit creation

| Field | Value |
|---|---|
| RFC-0002 state | Every boundary (§4, §6) |
| Component | Audit System (RFC-0001 §5 Audit & Transcript) |
| RFC owner | RFC-0013 §7 (record categories), §9 (what is recorded), §10 (what is never recorded), §33 (rules); RFC-0002 invariant 13; RFC-0004 A10, §4.12 |
| Inputs | Each boundary event as it happens: session, proposal, classification, approval, override, execution, verification, fact-lifecycle, context-boundary, secret-metadata, skill-event, operator-visibility records (RFC-0013 §7) |
| Outputs | An append-only, honest, provenance-carrying record, written *before* each consequence (I-13) |
| Preconditions | Audit store open (Stage 2); record categories defined (RFC-0013 §7) |
| Postconditions | Every authority use recorded at the boundary; no record silently edited (I-13); no secret value ever recorded (SC4, RFC-0001 §7.6) |
| Invariants | I-13 (audit written before the consequence), I-12 (overrides recorded); A10 (approval recorded before spent); SC4 (no secret enters the Audit); RFC-0013 AU1–AU16 |
| May not decide | The Audit System may not *decide* anything (RFC-0004 §4.12: Persist + Explain only); it holds no execution, approval, or policy authority |

**For our request, the records written are:** session record (goal adoption,
outcome) · proposal record (the upgrade Plan as produced) · classification
record (Consequential, with grounds, before the gate outcome) · approval record
(the Operator's approval, before the token is spent) · execution record (action
start/end, sanitized command form, machine state at the boundary) · verification
record (Collect + Compare + Outcome + evidence references) · fact-lifecycle
records (creation, and any retirement of the pre-upgrade Facts) · context-
boundary record (that material entered Context — never the material itself,
RFC-0013 §7 category 9) · secret-metadata record only if a secret was used in
elevation (metadata, never the value, RFC-0009 §15; SC4).

**Authority at this stage.** The Audit holds Persist + Explain authority, and is
*the* accountability surface (RFC-0013 §0). It is invisible to providers
(RFC-0010 §3 rule 2) and to Skills' decisions (RFC-0011 §16: interaction is
unidirectional).

**Authority transfer (exit).** The record is complete and honest. From it, the
Transcript can be derived (Stage 16). The record is not the Operator's memory
nor a knowledge store (RFC-0013 §1); it is the answer to "what did we do and
why".

---

### Stage 16 — Transcript generation

| Field | Value |
|---|---|
| RFC-0002 state | Completed (§2.13) |
| Component | Audit System / Presentation |
| RFC owner | RFC-0013 §2 (what is Transcript), §8 (transcript record categories), §5 (ownership) |
| Inputs | The Audit record (Stage 15) |
| Outputs | The Operator-facing transcript: dialogue, actions and outcomes, decisions and their grounds, disclosures, recovery context (RFC-0013 §8) |
| Preconditions | The record exists; the record is the sole source (RFC-0013 §8: "never holds material the record does not") |
| Postconditions | A readable account of the session; nothing in the transcript that is not in the record |
| Invariants | RFC-0013 AU rules on transparency and completeness; SC4 (no secret value); RFC-0002 invariant 13 (honesty) |
| May not decide | Transcript generation may not invent, may not editorialize, may not add material (RFC-0013 §8) |

**For our request.** The transcript presents: the dialogue (the Operator's
request, the presented proposal, the approval) · the actions and outcomes (the
upgrade ran; outcome Verified Success) · decisions and their grounds (the
classification Consequential, the approval, with stated reason) · disclosures
(anything withheld, disclosed as withheld, e.g. if elevation used a secret:
metadata only, RFC-0009 §15) · recovery context if any (RFC-0013 §8 category 5).

**Authority at this stage.** Explain, derived from Persist (RFC-0004 §4.12).
No decision authority.

**Authority transfer (exit).** The Operator reads the account. The session can
now return to Idle (Stage 17).

---

### Stage 17 — Return to Idle

| Field | Value |
|---|---|
| RFC-0002 state | Completed → Idle (§2.13) |
| Component | Orchestration Core |
| RFC owner | RFC-0002 §2.13, §3 (Completed → Idle is the sole transition) |
| Inputs | A verified, reported outcome |
| Outputs | Idle, armed for the next OP_GOAL |
| Preconditions | Outcome honestly reached (I-14: no terminal outcome while machine work is in flight) |
| Postconditions | No in-flight work; no standing authorization remains (I-15); the session is ready for a new goal or OP_EXIT |
| Invariants | I-14, I-15 (each boundary event ends every approval; a new goal needs fresh approval) |
| May not decide | The runtime may not assume the *next* goal is this one; Idle grants nothing |

**Authority at this stage.** None. Idle is the state with no outstanding
authority (RFC-0002 §2.2).

**Authority transfer (exit).** The loop returns to its origin: the Operator may
adopt a new goal, and the entire pipeline runs again from Stage 1. Each new goal
re-enters at Idle and earns every authority it needs fresh (I-15).

---

## 4. Authority Transfers, in Sequence

The authorities move in the fixed order established by RFC-0004 §1.2
(Observe → Propose → Infer → Verify), and every hand-off is one-way and
recorded (I-13). Compressed for this request:

1. **Operator → Core:** interpretation of the goal. No machine authority.
2. **Core → Fact Layer:** Observe — dispatch read-only Collectors (Stage 3/9).
3. **Context Manager → Provider:** a sanitized Provider View; nothing else can
   cross (PR14). Selection authority stays with Context Manager.
4. **Provider → Core:** Proposal, advisory only. No authority granted to the
   provider (RFC-0010 §2; RFC-0004 §1.2).
5. **Core → Policy Engine:** classification of the Plan (I-7; RFC-0004 §4.8).
6. **Policy Engine → Operator:** the gate defers the decision to the human
   (RFC-0004 §7; RFC-0008 §4).
7. **Operator → Executor (via token):** the only execution grant (A9). Scoped,
   consumable, recorded before spent (I-13, A10, P13).
8. **Executor → Fact Layer:** verification re-observes and Compares (I-2; V3).
9. **Fact Layer → Core → Operator:** the outcome, reported honestly (V5; §2.13).
10. **All boundaries → Audit:** the record of each authority use, before its
    consequence (I-13; RFC-0013 §7).

**What never transfers.** Nobody grants *itself* upward authority (A8). The
provider never gains execution, classification, verification, or approval. The
Skill never gains any authority beyond candidate Propose/Infer. The Audit never
gains decision authority (RFC-0004 §4.12). The matrix is closed (RFC-0004 §8
A8/A9).

---

## 5. The Information Pipeline

One pipeline, two directions, six forms. Outbound (to the provider) and inbound
(from the machine) both pass through the same deterministic Fact layer.

| Form | What it is | Produced by | Trust status | Responsible RFC |
|---|---|---|---|---|
| **Raw Output** | Tool utterance, distro-specific, raw bytes | the machine | Untrusted; never executed (F3, T4 analog for provider text) | RFC-0005 §2; RFC-0003 §2.4 |
| **Observation** | Raw Output + Collector identity + run metadata | Collector | Untrusted until normalized | RFC-0005 §2; RFC-0003 §2.4 |
| **Canonical Fact** | Normalized, provenanced, bounded claim | Fact Layer (deterministic) | Trusted *as a fact*, never as a command (F3) | RFC-0005 §3; RFC-0003 §2.4 |
| **Evidence Set** | Grouped related Facts; the unit Facts travel in | Fact Layer | Trusted, bounded by relevance (RFC-0005 §9) | RFC-0005 §9 |
| **Context** | Selected Evidence Sets, bounded by purpose/size/secrecy, sanitized | Context Manager | Sanitized; secret-free; purpose-limited | RFC-0005 §2; RFC-0012 §12–§13; RFC-0009 |
| **Provider View** | The one thing a provider may reason over | Context Building | Sanitized; no secrets (SC3); no raw output | RFC-0010 §3; PR14 |

The pipeline is a *boundary discipline*: **"nothing skips a stage, no stage's
output is knowledge before the next has run"** (RFC-0005 §2). For this request,
that discipline is what prevents "apt said the candidate is Y" from ever being
executed as a string, and what prevents the provider's sentence "upgrade to Y"
from ever being treated as a Fact (F1, F6).

---

## 6. Boundary Audit

Eight audits. Each names the boundary, the transition or shortcut the
architecture makes impossible, and the RFC that forbids it.

### 6.1 Impossible transitions (the state machine never allows)

| From → To | Why impossible | Forbidding authority |
|---|---|---|
| Planning/Diagnosis → Executing | No path from proposal to machine that skips the gate | RFC-0002 invariant 1; RFC-0004 A9; RFC-0008 §8 |
| Idle → Executing | Execution requires a classified, gated, approved Action | RFC-0002 §3 (Idle exits only via OP_GOAL); invariant 1 |
| Executing → Completed | No terminal outcome while machine work is in flight; Verification always follows Execution | RFC-0002 invariants 2, 14 |
| Awaiting Approval → Executing without a token | The gate is the only path; no implied consent; no background mode | RFC-0004 A9; RFC-0008 §4 |
| Awaiting Approval → Completed (diagnostic goals excepted) | Only Verification passes or Awaiting Input exits honestly | RFC-0002 §2.13 entry conditions |
| Interrupted → Executing | Any halt is followed by re-assessment; no resume in-flight | RFC-0002 invariants 8, 15 |
| Verification → Completed with Unknown | Unknown is never success | RFC-0006 V5; RFC-0002 §2.13 (unverified stays or Completed-with-caveat) |

### 6.2 Forbidden shortcuts

| Shortcut | Forbidden by |
|---|---|
| Background/automated execution of an unapproved Action | RFC-0004 A9 ("no background mode, no implied consent") |
| "Whatever is needed" blanket approval | RFC-0008 §4 (one token = one Action or one plan envelope; P11 standing approvals scoped/bounded/expiring); RFC-0001 §8.3 |
| Executing a provider string | RFC-0001 §8.4; RFC-0002 invariant 5; RFC-0007 T1 |
| Auto-retry of a failed step | RFC-0008 §11 (failed step → Replanning, no auto-retry) |
| Automatic rollback | RFC-0002 §10 (rollback is a proposal, never automatic) |
| LLM self-grading its own risk | RFC-0002 invariant 7; RFC-0001 §8.5 |
| Post-hoc Postconditions | RFC-0006 V10 |
| Skill/Provider declaring its own success | RFC-0006 V1; RFC-0004 §4.9 |
| Skipping a Fact pipeline stage | RFC-0005 §2 |

### 6.3 Authority leaks (what no actor can widen)

| Leak | Closed by |
|---|---|
| Provider/Skill escalating itself | RFC-0004 A8 (no actor grants itself authority upward) |
| Provider classifying risk | RFC-0010 §2; RFC-0002 invariant 7 |
| Provider/Skill creating Facts | RFC-0005 F1/F6; RFC-0011 §4; RFC-0007 §6.11 |
| Provider/Skill verifying | RFC-0010 §2; RFC-0011 §4; RFC-0006 V3 |
| Operator not defended against (malicious operator) | RFC-0004 §9.1; RFC-0001 §8.3 (refusal guarantee, transparency) |
| Policy Engine loosening policy on its own | RFC-0004 §9.7 (fails closed P3) |
| Audit deciding anything | RFC-0004 §4.12 (Persist + Explain only) |

### 6.4 Trust boundary

The machine world (deterministic facts, gated actions) is kept separate from the
provider world (text stream, untrusted) at every point (RFC-0001 §5). Every
crossing requires sanitization (RFC-0007 S1–S3); sanitization never upgrades a
trust class (T9); failure degrades to Hostile (T9) and fail-closed (T11: a
trust failure quarantines and tells the Operator).

### 6.5 TOCTOU (approval-to-execution gap)

Closed from both sides: RFC-0008 refuses to execute on stale preconditions and
invalidates the token on any state change (P8, P9, §10; RFC-0002 invariant 11);
RFC-0006 refuses to verify an outcome reached without fresh precondition Facts
(RFC-0006 §4) and re-observes at the execution boundary (V12). The same gap is
re-closed at the execution boundary itself by re-validation (Stage 7).

### 6.6 Secret boundary

Six one-way crossings, each with an SC invariant: Context (SC2), Provider View
(SC3), Audit (SC4), extensions (SC5), elevation (SC10), retention (SC11). Every
crossing is one-way and scoped (SC6); redaction is deterministic and testable
(SC13) and fails closed (SC14); exposure is compromise (SC15); a datum that
cannot be classified is Hostile and quarantined (RFC-0009 §2; RFC-0007 §15.5).

### 6.7 Provider boundary

The Provider View is the *only* channel (PR14); no raw output (RFC-0010 §3 rule
1); no audit (rule 2); no secrets (rule 3, SC3); no vendor-shaped Views (rule 4);
no machine internals beyond what reasoning needs (rule 5). Provider output is
advisory, structured, and routed deterministically (RFC-0010 §4); malformed
output degrades (PR11, RFC-0002 §4.3).

### 6.8 Verification boundary

Compare is deterministic (V3), read-only (V8), never stale (V4), never the LLM
(RFC-0004 §1.1), never skipped (V14), never overridden by confidence (V15), and
never reinterprets contradictions (V7). Postconditions are fixed before Compare
(V10). Verification records its evidence and outcome (V11).

---

## 7. Architecture Stress Review

Each failure question is answered by the RFC series, not by this document.

| Failure question | Resolution | Authority |
|---|---|---|
| What if the provider lies? | The provider's sentence can never become a Fact (F1, F6) and can never execute (RFC-0010 §2; RFC-0001 §8.4). Verification compares *observed Facts*, never provider claims (V1). The provider cannot self-grade its risk (I-7). At worst the Proposal is wrong; the gate and the verify step catch it. | RFC-0005 F1/F6; RFC-0010 §2; RFC-0006 V1; RFC-0002 invariant 7 |
| What if the provider returns malformed output? | It is malformed, treated as refusal, the Core degrades (RFC-0010 §8; RFC-0002 §4.3; PR11). It never becomes a Fact, a plan, or a command. | RFC-0010 §8; PR11; RFC-0002 §4.3 |
| What if verification fails? | Outcome is whatever Compare honestly finds: Verified Failure, Unknown, Contradicted (RFC-0006 §7). Success is never claimed (V5). The plan re-opens at Replanning with the failure as a new Fact (RFC-0002 §2.10, §10; RFC-0008 §11: failed step → Replanning). | RFC-0006 §7; V5; RFC-0002 §2.10; RFC-0008 §11 |
| What if approval expires or the state changes? | The token is invalidated and never resurrected (P8; RFC-0002 invariants 11, 15). The plan re-opens and is re-presented (RFC-0002 §2.10; RFC-0008 §11 partial execution: continuation is a new decision). | RFC-0008 P8; RFC-0002 invariants 11, 15; §2.10 |
| What if context changes mid-flight? | STATE_CHANGED_DETECTED invalidates dependent Facts and, in Awaiting Approval, invalidates the approval → Machine Inspection (RFC-0002 §4.2). The execution boundary re-validates preconditions anyway (P9). | RFC-0002 §4.2; RFC-0008 P9 |
| What if execution partially succeeds? | The envelope is consumed up to the last completed step; what did not run is never assumed (RFC-0008 §11; RFC-0002 §2.8, §10). State is re-established deterministically, then re-presented. Outcome = Partially Successful, reported exactly (RFC-0006 V6). | RFC-0008 §11; RFC-0002 §10; RFC-0006 V6 |
| What if inspection cannot observe? | A failed Collector yields "fact unknown" with provenance (RFC-0003 §2.4; RFC-0002 §10). Outcome is Unknown, never success (V14, V16). A critical baseline failure asks rather than assumes (RFC-0002 §10 collector failure). | RFC-0003 §2.4; RFC-0006 V14/V16; RFC-0002 §10 |
| What if secrets appear unexpectedly? | Unclassifiable data is Hostile and quarantined (RFC-0009 §2; RFC-0007 §15.5); redaction fails closed (SC14); exposure is treated as compromise — invalidate, destroy, disclose, record (SC15). | RFC-0009 SC13–SC15; RFC-0007 §15.5; §6.10 |
| What if the runtime is interrupted or resumes? | Machine work halts; actual state is re-established before anything else (I-8); no approval survives the boundary (I-15); Context is re-assembled, never restored (RFC-0012 §21). The audit re-presents recovery context (RFC-0013 §8 category 5). | RFC-0002 invariants 8, 15; RFC-0012 §21; RFC-0013 §8 |
| What if the Operator rejects the plan? | Reject-all at Awaiting Approval → Cancelled, or the plan is revised and re-presented; nothing runs (RFC-0002 §2.15, §3). | RFC-0002 §2.15 |
| What if the provider becomes unavailable? | Retry → fallback chain → degraded mode → facts-only presentation in Awaiting Input; machine work already in flight is unaffected (RFC-0002 §10 provider failure; §4.3). The runtime never fabricates a reply (I-9). | RFC-0002 §10, §4.3; I-9 |
| What if the machine reboots mid-flight? | Every approval ends (I-15); resume continues at re-orient (RFC-0002 §2.1, §3); re-verification follows (V12). No terminal outcome is claimed over an unknown state (I-14). | RFC-0002 invariants 14, 15; V12 |
| What if the Audit fails? | Audit failure philosophy: the record's failure is surfaced, never silent (RFC-0013 §21); and audit is written *before* consequences (I-13), so a failure is visible before it can compound. | RFC-0013 §21; RFC-0002 invariant 13 |

In every case the answer is the same shape: **determinism first, then
disclosure, then decision, then action** (RFC-0002 §10). The system never
"decides around" a failure; it re-establishes truth, tells the Operator, and
lets the human decide.

---

## 8. What This Walkthrough Proves — and What It Does Not

**Proves:**
- A single request can traverse the RFC-0002 state machine end to end using
  only existing states and transitions (§2, §3).
- Every authority transfer in the pipeline is lawful under RFC-0004 §1.2/§8 and
  every execution path passes the gate (A9) under a recorded, scoped token
  (I-11, I-13, A10, P13).
- No stage in the Fact pipeline can be skipped, and no provider/Skill output
  can become a Fact or a command (RFC-0005 §2, F1–F8).
- Verification is deterministic and mandatory after every state change
  (RFC-0006 V2, V3; RFC-0002 invariant 2), and no outcome is claimed over
  unverified state (I-14).
- The secret, provider, audit, and trust boundaries are crossed only at their
  named points, each with a named invariant (§6.4–§6.8).

**Does not prove (and does not decide):**
- Presentation specifics, resume semantics, and implementation ordering — these
  are RFC-0015, RFC-0014, and RFC-0020, respectively (RFC-0000 §4), and are
  out of scope here.
- That the classification "Consequential" is the *correct* class for a package
  upgrade in all distros — classification is a Policy Engine determination over
  Action properties (RFC-0001 §8.5), made per machine, per plan.

---

## 9. End State

The request has been adopted, grounded in Facts, proposed, classified, gated,
approved, executed under a scoped token, verified against declared
Postconditions, reported as Verified Success, audited at every boundary, and
rendered into a transcript. The session has returned to **Idle** (RFC-0002
§2.13, §3), holding no outstanding authority (I-15), ready for the next goal —
which will earn every authority it needs, fresh.

The machine is upgraded. The record is honest. The next request starts at Stage 1.
