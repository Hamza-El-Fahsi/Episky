# Iteration 8 — Design Review (Executor + Audit Layer)

> **Document type:** Implementation design review, at the same rigor as
> Iterations 2–7. **Not an RFC, not code.**
> **Read this first:** This document **defines no new architecture, modifies no
> RFC, invents no behavior, and writes no production code.** It translates the
> frozen corpus (RFC-0000–0013, RFC-0021, the decision traceability matrix,
> `docs/architecture-implementation-blueprint.md`, and the ratified
> `docs/implementation-decision-notes.md` DN-1…DN-54) into an implementation
> plan for the **Executor + Audit layer — the `executor` and `audit` packages**
> (blueprint §8.8, re-ordered to Iteration 8 by DN-45, and so labeled by the
> Iteration 7 closeout). Where the corpus does not decide something, this
> document **reports** it as an ambiguity or a question; it does not resolve it.
>
> **Status of sources.** RFC-0013 is **Draft** (not Accepted; dated 2026-08-02).
> Per RFC-0003 Part II §1.1 Draft RFCs are not normative and must not be relied
> upon by implementation; yet the blueprint (a translation, §0) targets the
> Drafts' *invariants* as the conformance oracle (blueprint §9 #2). Iteration 8
> inherits Iterations 1–7's posture: it conforms to RFC-0013's Draft wording
> knowingly, accepting the rework risk that a Draft change carries. Blueprint
> §8.0 gate stands — production code begins only after RFC-0015/0019/0020 and
> the Drafts are Accepted; this iteration builds the translation scaffold. The
> load-bearing dependencies this layer rests on — RFC-0001 §5 (Action
> Execution), §8.1–§8.12 (principles 1 least-privilege-per-action, 2 default
> deny, 4 no-shell-interpolation, 6 elevation, 7 secrets-segregated, 8
> output-limited, 10 append-only-honest-audit, 12 fail-closed); RFC-0002 §2.8,
> §6.2, §9 invariants 1, 2, 5, 8, 11, 13, 15; RFC-0004 §4.9, §4.12, §7 (A2, A7,
> A9, A10), §9.9, §9.12; RFC-0008 §8–§10, §13 P9/P12/P13; RFC-0009 SC4, SC9,
> SC10 — are **Accepted**, which bounds the rework risk. RFC-0021 §3.3 (the
> machine's own elevation mechanism) is Draft and its mechanism is **not** built
> here (Q6); the mechanism is injected, exactly as RFC-0008 §8 fixes elevation
> *semantics* while "the mechanism is the machine's own and is not named here".
>
> **Scope decision (reported — Q1).** DN-45/DN-40 re-ordered the build so that
> `executor` + `audit` (blueprint §8.8) follow `policy` (built as Iteration 7),
> and the Iteration 7 closeout (`docs/implementation-consistency-report.md`
> §Readiness for Iteration 8) records that Iteration 8 is the `executor` +
> `audit` layer. Blueprint §8.8 still reads "Iteration 7 — `executor` +
> `audit`"; the label was never renumbered (mirroring how §8.7/§8.8 were left
> standing for Iteration 7). This task's scope implements `executor` + `audit`
> at Iteration 8, which continues the recorded supersession of the numbering
> (Q1). The re-order is dependency-safe — `policy` (Layer 3) precedes
> `executor`/`audit` (Layer 4), preserving the safety spine (RFC-0000 §6 items
> 1, 3) and blueprint Risk #9's mitigation (the blast-radius RFCs' packages
> built first).

---

## 1. Architectural consistency review

### 1.1 Scope (blueprint §8.8, transcribed)

| Item | Value |
|---|---|
| Goal | Execution under a token, recorded before its consequence |
| Work | Sanctioned Action runner with guardrails and scoped elevation; append-only Audit store, record writers, transcript derivation |
| Definition of Done | I-1/I-5/I-11 (executor) and I-13/AU8 (audit) conformance; a consequence with a failed audit write is blocked and disclosed (AU8); transcript derives from the record only (RFC-0013 §8) |
| RFC basis | RFC-0004 §4.9; RFC-0002 §2.8, invariant 13; RFC-0013 §7–§22; RFC-0001 §8.6 |

Blueprint §7 (test oracle) carries the two rows: `executor` — "Never starts
without approval (I-1); token-bound and re-validated at boundary (I-11, P9);
no untrusted text interpolated (I-5); elevation scoped and revoked (P12); no
secret exposed (SC10)" — oracle RFC-0004 §4.9; RFC-0002 §2.8; RFC-0008 §10;
`audit` — "Recorded before consequence (I-13); append-only, tamper-evident
(A7); failed write blocks consequence and is disclosed (AU8); transcript
derives from record only (RFC-0013 §8); no secret value recorded (SC4)" —
oracle RFC-0013 §21, §22, §33; RFC-0002 invariant 13. Blueprint §5 exposes the
package contracts: `executor` — "Run one token-bound Action under guardrails;
report start/end and sanitized output; scoped elevation" (RFC-0004 §4.9;
RFC-0002 §2.8; RFC-0001 §5, §8.6); `audit` — "Append a record (append-only,
before-consequence); render the transcript from the record; reconcile failed
writes" (RFC-0013 §7, §8, §21, §22; AU1–AU16; RFC-0002 invariant 13).

**Layer-enforceable now vs. cross-component.** The §8.8 DoD set is
I-1/I-5/I-11 (executor) and I-13/AU8 (audit). The layer can satisfy the DoD
set **at its own surface** as deterministic mechanics plus layer-boundary
tests; the parts whose enforcement points do not exist yet — the §6.2
consultation edges and the Executing state transitions (Verification /
Interrupted / Cancelled / END-reboot-handoff), the startup opening of the
audit store (RFC-0002 §2.1), the machine's own elevation invocation
(RFC-0021 §3.3), and Verification of the executed Action (RFC-0006) — are
recorded as the owning packages' DoD (RFC-0002 §2.8/§6.2 → `core`, Iteration
10; RFC-0021 → `systemmodel`/runtime; RFC-0006 → `verification`, already
built at Iteration 4), mirroring how Iteration 7 made P1/P11/P12 and the
durable half of P13 testable as layer-boundary obligations (DN-45/DN-50/DN-53).

**The enforcement halves this layer inherits.** Iteration 7 recorded, not
dropped: P1 independent token enforcement → `executor` (DN-45); P12 elevation
mechanism + revocation + SC10 boundary → `executor.elevation` (DN-53/DN-43);
the durable P13 Audit write of the issuance/override/auto-permit/rejection
records → `audit` (DN-50). Each is a **Definition of Done item of this
iteration**, not an optional follow-up.

### 1.2 Out of scope (recorded, not dropped)

Each of these is owned elsewhere and is **not** built in Iteration 8:

| Item | Owned by | Blueprint gate |
|---|---|---|
| The §6.2 consultation edges and the Executing state exits (success/failure → Verification; timeout/interrupt → Interrupted; cancel → Cancelled; reboot → END) | RFC-0002 §2.8, §6.2; `core`, Iteration 10 | RFC-0002 §2.8/§6.2 |
| Session Initialization: opening the durable audit store, verifying audit writability, elevation availability, machine fingerprint | RFC-0002 §2.1; `core`, Iteration 10 | RFC-0002 §2.1 |
| Verification of an executed Action (state-based re-observation and Compare; never the Executor's) | RFC-0006; `verification` (Iteration 4) + `factlayer` | RFC-0002 invariant 2; RFC-0004 A5 |
| The machine's own elevation mechanism (sudo/polkit invocation, revocation plumbing) | RFC-0021 §3.3 (Draft); injected at the `executor.elevation` boundary; `systemmodel`/runtime | RFC-0008 §8; RFC-0001 §8.6 |
| Concrete guardrail bounds: per-phase time budgets, output-capture ceilings, retry windows | RFC-0002 §11 Q3, §11 Q2; RFC-0020 (values; placeholder default, DN-18 precedent) | RFC-0002 §11; RFC-0020 |
| The durable backing of the audit store (filesystem/database, retention §19, deletion §20, export §18, resume re-presentation) | RFC-0013 §18–§20; RFC-0020; RFC-0014 | RFC-0013 §19/§20; RFC-0020 |
| The Transcript presentation *form* (how the derived account is rendered to a beginner) | RFC-0013 §5; RFC-0015 (future) | RFC-0013 §5; RFC-0001 §5 Presentation |
| The §7 record categories whose write boundaries belong to other components (proposal, classification, verification, fact-lifecycle, context-boundary, skill-event, operator-visibility) | RFC-0013 §7; their owning iterations (`core`, `verification`, `factlayer`, `context`, `skills`, `cli`) | RFC-0013 §7, §16 (no actor exempt) |
| Orphaned-process and partial-execution reconciliation | RFC-0002 §10; RFC-0014 | RFC-0002 §10 |
| The RFC-0021 State-Domain vocabulary and its diff used for state-consistency at the boundary | RFC-0021 (Draft); the runtime boundary handler | RFC-0008 §9; Q3 |
| Signatures / package naming | RFC-0020 (future) | DN-1 |

### 1.3 What exists already

The `executor` package (`{__init__,runner,guards,elevation}.py`) and the `audit`
package (`{__init__,records,store,transcript}.py`) were scaffolded in Iteration
0 with ownership docstrings only (blueprint §2); `tests/test_packages.py`
already imports and docstring-checks them, so the tree test stays green
throughout — C1–C4 **fill** the stubs, they do not create modules.
`tests/test_dependency_rules.py` already declares
`ALLOWED["executor"] = {"schema", "audit", "secrets"}`,
`ALLOWED["audit"] = {"schema", "secrets"}` and the forbidden-source rows (no
package may import `executor` except `skills`, `context`, `cli`; no package
may import `audit` except `core`, `executor`, `context`, `cli` per blueprint
§4.1/§4.2). Baseline suite: **1722 tests, green**, branch `iteration/7-policy`,
HEAD `9a29f57` (Iteration 7 closeout), working tree clean; branch
`iteration/8-executor` created from `9a29f57`.

---

## 2. RFC consistency review

| RFC | Section | Implemented as | Status in layer |
|---|---|---|---|
| RFC-0004 | §4.9 Executor | The sole Execute authority: run the one approved Action under a valid, unexpired, state-consistent token; may decide only *how*, never *what*; never verifies its own work (V1); report completion for Verification | Implemented (C3); authority per §8/§5 |
| RFC-0004 | §7 matrix (Executor row) | Execute A; Refuse C14 (fail-closed: refuses on invalid/expired/state-inconsistent token); Explain C15 (reports what ran + result for Verification); no Observe/Propose/Infer/Approve/Verify/Persist | Implemented (C3/C4, structural) |
| RFC-0004 | §4.12 Audit System | Persist + Explain only; may decide format/ordering within RFC-0013; may never omit, alter history, or decide meaning; not authority (AU1) | Implemented (C1/C2); no decision surface (C4) |
| RFC-0004 | §8 A2, A7, A9, A10 | Executor never invents (A2); Audit never changes history (A7); the gate is the only path to mutation (A9); Approval recorded before spent (A10) | Implemented (C1/C3/C4, boundary tests) |
| RFC-0002 | §2.8 Executing | Guardrails (scoping, timeouts, output capture, secret-free, elevation per action); token re-validated at the boundary; exits toward Verification or a halt that re-establishes state | Implemented (C3); transitions are `core`'s (§1.2) |
| RFC-0002 | §6.2 Executor / Audit rows | Executor consulted only in Executing, only with a valid re-validated token; Audit written at every consequential boundary, before the consequence | Boundary (C3: the runner accepts only a token-bound Action; the write-point wiring is `core`'s) |
| RFC-0002 | §2.1 Session Initialization | The durable audit store is opened and writability verified at startup | Boundary (C1: the store object + writability check exist; the startup call is `core`'s) |
| RFC-0002 | §9 invariants 1, 5, 11 | No execution without approval (I-1); no untrusted text interpolated (I-5); token scoped/consumable/invalidated (I-11) | Implemented (C3/C4, DoD) |
| RFC-0002 | §9 invariants 13, 2, 8, 15 | Recorded before consequence (I-13); Verification always follows execution (I-2); halt → re-assessment (I-8); no standing authorization across a boundary (I-15) | I-13 at C1/C3 (DoD); I-2/I-8/I-15 are `core`'s (recorded, §1.2) |
| RFC-0001 | §5 Action Execution | Technical guardrails of a sanctioned action: scoping, timeouts, output capture, no secret leakage; report exit status, output, state-delta before/after, deterministically; never guess success | Implemented (C3/C4) |
| RFC-0001 | §8.4 rule 4 / §8.8 | No shell interpolation of untrusted text, ever (I-5); output limited — bounded, redacted, truncated rather than dumped | Implemented (C3/C4: argv-structured run primitive, no shell string; SC8/SC10 redaction) |
| RFC-0001 | §8.6 principle 6 | Elevation explicit, scoped, re-authenticated; only for the approved Action; Operator present | Implemented (C4: elevation lifecycle per Q6; mechanism injected, §1.2) |
| RFC-0001 | §8.10 / §8.12 | Audit append-only and honest; fail closed — any error in a safety mechanism blocks and discloses | Implemented (C1/C4) |
| RFC-0008 | §8 Approval Tokens | The token is the only thing that carries permission to the Executor; scope; expiry per class; invalidation; single-use; standing approvals; elevation semantics | Consumed (C3: structural handoff, Q2/Q3; the mint/validate machinery is `policy`, Iteration 7) |
| RFC-0008 | §9 Preconditions | Assumptions/facts, machine-state domains, Action identity re-checked at the execution boundary | Boundary (C3: the runner consumes the re-validation verdict per Q3; the compare is the boundary handler's) |
| RFC-0008 | §10 TOCTOU | Four layers: binding, boundary re-validation, independent enforcement, consumption/invalidation | Implemented (C3: the runner is the independent-enforcement layer, Q2); consumption is `policy`'s + `core`'s |
| RFC-0008 | §13 P9, P12, P13 | Preconditions re-validated at the boundary (P9); elevation explicit/per-action/scoped/revoked (P12); recorded before spent (P13) | Implemented (C3/C4); P9's machine-state half and P12's mechanism are boundary (`core`/RFC-0021) |
| RFC-0013 | §1 What is Audit | Durable, append-only, tamper-evident record of consequential events, written before each consequence; authoritative record; never authority | Implemented (C1/C4); durable backing deferred (§1.2, Q8) |
| RFC-0013 | §7 Record Categories | Exactly the §7 categories, each written at its boundary before the consequence | Implemented (C1: canonical category types per Q9; writers exercised at this layer's boundaries) |
| RFC-0013 | §8 Transcript Categories | Transcript derived from the record only; never holds material the record does not (AU2) | Implemented (C2, DoD) |
| RFC-0013 | §11/§12 Lifecycle + Legal Transitions | Empty → Recording → Degraded → Recovering; anything not listed is illegal; Degraded → consequence proceeds is illegal | Implemented (C1, Q8) |
| RFC-0013 | §21 Failure Philosophy | Fail closed (failed write blocks consequence); fail loud (Operator told); degraded never silent; a gap never patched by invention (AU8) | Implemented (C1/C4, DoD) |
| RFC-0013 | §22 Recovery Philosophy | Reconciliation, never rewrite; lost write recorded as failed-to-record; recovery re-assembles, never restores | Implemented (C1/C4, AU13) |
| RFC-0013 | §33 AU1–AU16 | The audit invariant suite — the package's conformance oracle | Oracle (C4) |
| RFC-0009 | SC4, SC10 (via DN-43) | No secret value enters the Audit (SC4); elevation exposes nothing (SC10); no Action carries a secret (SC9) | Implemented (C1/C3/C4, boundary tests) |
| RFC-0002 | §2.1/§2.8 write points | Execution start/end written at the boundary, before the consequence | Implemented (C3: the runner writes start/end through `audit`; a failed pre-write blocks the run, AU8) |

**Already resolved by the corpus (not re-opened here):**

- **The executor is the sole Execute authority.** The matrix's Execute column has
  exactly one A (RFC-0004 §7); the executor runs only Actions bound to a valid,
  unexpired, state-consistent token and never invents Actions (A2). Not a
  question.
- **The executor never verifies its own work** (V1; RFC-0004 §4.9 "May never
  decide: whether the result was correct"); Verification is the Fact Layer's
  (RFC-0004 §4.6). Not a question.
- **The executor may decide only *how*, never *what*** (RFC-0004 §4.9; RFC-0002
  §2.8; blueprint §3/§4.2). Not a question.
- **No untrusted text is ever interpolated into a command** (I-5; RFC-0001 §8.4
  rule 4). Actions are built from sanctioned structures only; nothing from the
  LLM, machine output, or a skill is executed as a shell string. Not a
  question — the *mechanism* (argv-structured, no shell) is the Q4 resolution.
- **The only exits from Executing are toward Verification or a halt that
  re-establishes state** (I-2; RFC-0002 §2.8); success and failure both go to
  Verification, never directly to Replanning; timeout/interrupt → Interrupted
  (outcome unknown). Not a question — the transitions are `core`'s (Iteration
  10), recorded at §1.2.
- **Elevation semantics are fixed**: explicit, per-action, scoped,
  re-authenticated, at least Consequential, bounds on the token, revoked at
  the end of the Action or on any invalidation, never persists, never covers
  unapproved work, never a standing root session (RFC-0008 §8; RFC-0001 §8.6).
  The *mechanism* is the machine's own (RFC-0021 §3.3, Draft). Not a question —
  the module's deterministic lifecycle is the Q6 resolution.
- **The Audit is append-only and tamper-evident; no actor edits or erases a
  prior record** (A7; AU4; RFC-0001 §8.10; RFC-0002 I-13). Not a question.
- **The Audit is recorded before the consequence, and a failed write blocks the
  consequence and is disclosed** (I-13; AU8; RFC-0004 §9.12; RFC-0008 P13). Not
  a question — the executor-boundary wiring is the Q7 resolution.
- **The Audit is never authority** — no component treats it as a decision
  input, a source of Facts, or permission to act (AU1; RFC-0004 §4.12). Not a
  question.
- **The Transcript is never evidence** and derives from the record only; Facts
  are the only evidence model (AU2; RFC-0013 §2/§8; RFC-0005 §3). Not a
  question.
- **No secret value ever enters the Audit** — metadata only (SC4; AU7;
  RFC-0013 §31); the record holds the shape of secrets, never their substance.
  Not a question — the metadata type is the Q9/Q10 resolution.
- **Auto-permitted actions are still recorded** (RFC-0002 §2.7; AU9); no actor
  is exempt (RFC-0013 §16). Not a question.
- **A consumable token is never reused; no standing authorization crosses a
  boundary** (I-11, I-15; RFC-0008 §8). Not a question — enforced at `policy`
  (Iteration 7) and re-asserted at the executor boundary (Q3).

---

## 3. Layer placement

`executor` and `audit` sit at **Layer 4** (blueprint §4.1), beside `context`.
Their imports reach only downward to Layers 0–3; nothing below Layer 4 imports
them except the qualified readers in blueprint §4.2 (`context` imports `audit`;
`core`/`cli` import both, per §4.1). `executor` consumes `schema`, `audit`,
and `secrets`; `audit` consumes `schema` and `secrets` (metadata types only).

- **`executor → audit`** is the one Layer-4 → Layer-4 edge, and it is
  deliberate: the runner writes its execution start/end records at the
  boundary it owns, because every record is written at a boundary by the
  component whose consequence it precedes (RFC-0002 invariant 13; RFC-0013 §7;
  blueprint §5's note that `audit` is not a fan-out hub). The runner is the
  component whose consequence the execution record precedes.
- **`executor → secrets`** is the SC10 boundary edge: output is bounded and
  redacted before recording and before any display (RFC-0001 §8.8), and
  elevation never exposes a value (SC10). `audit → secrets` is metadata-only
  (SC4): the secret-metadata record reuses `secrets` *classifier/metadata
  types*, never values (blueprint §4.2's "metadata types only" qualifier).
- **No `executor → policy` edge.** The token is the handoff value, not a call
  (Iteration 7 review §3; blueprint §4.2): the runner re-validates the token
  independently, never importing `policy` (RFC-0008 §10 layer 3; RFC-0004 A2).
  The structural handoff type is the Q2 resolution.
- **No `executor → verification`/`factlayer` edge.** The runner never verifies
  (V1) and never reads the machine itself; the machine-state and
  precondition verdicts are consumed as explicit inputs at the boundary (Q3),
  exactly as RFC-0002 §6.2 consults the deterministic tools only for
  Inspection/Verification and never consults the LLM in Executing.

---

## 4. Ownership map

Each package has exactly one owner per row (RFC-0004 §3; blueprint §10): the
*authority* is owned by RFC-0004 (Executor §4.9, Audit System §4.12) and the
*state/record behavior* by RFC-0002 §2.8 (executor) and RFC-0013 (audit) — two
distinct properties, one owner each, exactly as blueprint §10's two-owner check
describes. Module-level ownership:

| Module | Owning RFC sections | Protected by |
|---|---|---|
| `executor/runner.py` | RFC-0004 §4.9; RFC-0002 §2.8 | A2 (never invents), I-1 (never starts without approval), I-11/P9 (token-bound, re-validated), I-5 (no untrusted text), A10/I-13 (recorded before spent); RFC-0002 §6.2 (consulted only in Executing) |
| `executor/guards.py` | RFC-0001 §5 Action Execution | §8.1 (least privilege per action), §8.8 (output limited), SC8/SC10 (no secret leakage); fail closed (§8.12) |
| `executor/elevation.py` | RFC-0008 §8; RFC-0001 §8.6 | P12 (explicit, per-action, scoped, revoked); at least Consequential; SC10 (elevation exposes nothing); RFC-0008 §8 (never persists, never covers unapproved work) |
| `audit/records.py` | RFC-0013 §7, §9 | SC4/AU7 (metadata only, no secret value); §7 category closure; RFC-0004 A7 (append-only) |
| `audit/store.py` | RFC-0013 §1, §11, §12, §21 | AU4 (append-only, tamper-evident), AU8 (failed write blocks consequence, disclosed), AU13 (reconciliation, never rewrite); RFC-0002 I-13; RFC-0004 A7 |
| `audit/transcript.py` | RFC-0013 §8 | AU2 (derives from the record only; never evidence); §5 (form is RFC-0015's); §8 category closure |

**Two-owner checks.** (a) *Execution authority vs. execution state:* RFC-0004
§4.9 owns the *authority* (the sole Execute cell, may-decide-how); RFC-0002
§2.8 owns the *state behavior* (guardrails, boundary re-validation, the exits
toward Verification) — one package, two properties, one owner each (blueprint
§10's `executor` = RFC-0004 profile + RFC-0002 state). (b) *Audit profile vs.
record model:* RFC-0004 §4.12 owns the *profile* (Persist/Explain only, never
authority); RFC-0013 owns the *record model* (§7 categories, §8 transcript, §11
lifecycle, AU1–AU16) — blueprint §10's `audit` split. (c) *Elevation semantics
vs. mechanism:* RFC-0008 §8 owns the *semantics* (which this layer implements
as the deterministic lifecycle); RFC-0021 §3.3 (Draft) owns the *mechanism*
(injected, not built here). (d) *Execution records vs. who writes them:* the
record *format* is RFC-0013's (§7 category 6, `audit/records.py`); the *write
point* is the component whose consequence precedes it — the executor
(`executor/runner.py` calls `audit`), per RFC-0002 invariant 13 and blueprint
§5's note.

**Authority boundaries.** This layer holds Execute (executor, the sole cell)
and Persist/Explain (audit) — and nothing else. The executor never Approves,
never Observes broadly, never Infers, never Verifies, never Persists on its
own (RFC-0004 §7 row: Execute A, Refuse C14, Explain C15). The audit never
Proposes, Infers, Approves, Executes, Observes, or Verifies (RFC-0004 §7 row:
Persist A, Explain A). The audit holds no decision authority: it records, it
does not judge (RFC-0004 §4.12; AU1).

---

## 5. Dependency analysis

**Allowed** (blueprint §4.1; already enforced by `tests/test_dependency_rules.py`):

| Edge | Why allowed |
|---|---|
| `executor → schema` | The Action is the sanctioned unit (RFC-0003 §2.6); the runner consumes `schema.Action`/`schema.Step` and reports start/end for Verification |
| `executor → audit` | The runner writes execution start/end records at its boundary, before the consequence (RFC-0002 I-13; RFC-0013 §7 cat. 6); the record format is audit's (RFC-0013 §7) |
| `executor → secrets` | Output is bounded and redacted before recording (RFC-0001 §8.8); elevation exposes nothing (SC10); no secret leaks at the execution boundary (RFC-0009) |
| `audit → schema` | Records carry the canonical vocabulary (Action identity, Outcome, category names) in canonical form (RFC-0013 §7; RFC-0003 Part I) |
| `audit → secrets` (metadata types only) | The secret-metadata record carries the *shape* of secrets, never a value (RFC-0013 §7 cat. 10, §31; SC4); blueprint §4.2's "metadata types only" qualifier |

**Forbidden** (blueprint §4.2): `executor` may not import `policy`
(classification), `verification` (decide), `factlayer` (normalize), `providers`,
`skills` — "may decide only *how* within declared bounds, never *what*"
(RFC-0004 §4.9); never verifies its own work (V1); the gate is upstream
(RFC-0008). `audit` may not import `factlayer`, `providers`, `context`,
`policy`, `executor`, `secrets` (values) — "holds records, never the material"
(RFC-0013 §7 cat. 9, §10); metadata-only for secrets (SC4); no decision
authority (RFC-0004 §4.12). Notably: no `executor → policy` edge even though
the token is a `policy` type — the token crosses as a **structural handoff
value** (Q2); no `audit → executor` edge (the audit never drives execution, and
the runner is a client of the store, never the reverse); no `audit →
context`/`factlayer` edge (the audit holds records, never Context or Fact
material, RFC-0013 §24/§25).

**Latent edges.** `systemmodel`/RFC-0021 (the State-Domain diff for
state-consistency) is the declared-but-unused case, mirroring DN-9/DN-37/DN-44:
the runner consumes the machine-state and precondition verdict as an explicit
input at the boundary (Q3), and the State-Domain semantics is RFC-0021's
(Draft), left unused. `verification` is exercised *by* this layer (the runner
reports completion for Verification) but never imported — the boundary is the
exit toward Verification (RFC-0002 §2.8), which is `core`'s transition to
invoke.

---

## 6. Public surface analysis

The planned public surface is **reported**, not ratified; final signatures are
RFC-0020's (DN-1). The shape below is what C1–C4 will build. Both packages are
value-free and import-safe beyond their own surface; the runner's *run
primitive* is injected at the boundary (Q1) so the package itself performs no
I/O and no subprocess spawn.

`executor/runner.py`

- The token handoff type consumed at the boundary (Q2): a plain, schema-shaped
  record carrying the approved Action's identity, class, gate, expiry, state
  snapshot reference, session identity, consumed flag, and elevation bounds —
  the `policy.Token` public fields as a **carried value**, never the `policy`
  package (the token is "the handoff value, not a call", Iteration 7 §3).
- The run entry: requires (a) a token-bound `schema.Action`, (b) the
  independently re-validated token (valid/unexpired/not-consumed/Action-
  identity/session match — checked locally, Q2), and (c) the boundary
  re-validation verdict for preconditions + machine state, consumed as an
  explicit input (Q3). Any uncertainty → refused (fail closed, RFC-0008 §9;
  RFC-0002 §2.8).
- The injected **run primitive** (Q1): the package takes a
  `run(action, argv) -> RunResult` callable provided at the boundary; it never
  spawns a subprocess and never builds a shell string (I-5, Q4). Determinism
  and guardrail tests use a test primitive; the real machine interaction is
  `core`'s wiring at Iteration 10.
- Records: writes the execution-start record **before** the run and the
  execution-end record after, through `audit` (RFC-0013 §7 cat. 6; RFC-0002
  I-13); a failed pre-write **blocks the run and is disclosed** (AU8, Q7). The
  run result reports exit status and sanitized, bounded output for Verification
  (RFC-0001 §5) — never a success verdict (RFC-0002 I-2).
- Refuses anything not carrying a valid token (A2/I-1); no Propose surface, no
  chain-of-actions surface, no way to invent an Action (RFC-0004 §4.9).

`executor/guards.py`

- Scoping: the run is bound to the one approved Action; nothing beyond the
  token's named scope is run (RFC-0004 §4.9 "within its declared bounds").
- Timeout: a deterministic timeout mechanism over the injected run primitive,
  with a placeholder default bound (DN-18 precedent); a timed-out run yields an
  outcome-unknown result (RFC-0002 §2.8 → Interrupted at `core`) and is
  recorded as such. Concrete budgets are RFC-0020's (RFC-0002 §11 Q3).
- Output capture: bounded capture with a placeholder ceiling (RFC-0001 §8.8),
  truncated rather than dumped, and **redacted via `secrets`** before recording
  (SC8/SC10) — no secret value crosses into the execution record or any
  display (RFC-0009 SC4/SC10; DN-43).
- Fail closed: any guardrail error → refused + disclosed (RFC-0001 §8.12).

`executor/elevation.py`

- The deterministic elevation lifecycle per RFC-0008 §8: an elevation request
  bound to the one approved Action, carrying its elevation bounds (which
  `policy` already enforced as at-least-Consequential, DN-53), and a
  revocation that fires at the end of the Action or on any invalidation (Q6).
- Elevation never persists, never covers unapproved work, never forms a
  standing root session (RFC-0008 §8; RFC-0001 §8.6).
- The machine's own mechanism (RFC-0021 §3.3) is injected at the boundary, not
  built here (§1.2); the module implements the request/revoke contract and the
  SC10 no-exposure boundary (elevation never displays or records a value).

`audit/records.py`

- The canonical record categories for this layer's boundaries (Q9): the
  execution record (cat. 6: action start/end, commands in sanitized form,
  machine state at the boundary), the secret-metadata record (cat. 10, built
  on `secrets` *metadata types*, never a value), and the approval/override/
  auto-permit/rejection records (cat. 4/5) whose durable write DN-50 assigned
  to audit — plus the category *types* the boundary handler will consume at
  Iteration 10 where their write points exist.
- Each record is immutable, carries its category, and carries no secret value
  (SC4/AU7). No field of any record can hold a value-shaped artifact
  (boundary-tested).

`audit/store.py`

- The append-only, tamper-evident store (Q8): an in-memory ordered record list
  that can only be appended to; prior records are immutable (A7/AU4); a
  hash-chain binds each record to its predecessor so any silent edit is
  detectable (RFC-0001 §8.10 tamper-evidence).
- The §11 lifecycle state machine: Empty → Recording → Degraded → Recovering,
  with the legal transitions of §12; anything not listed is illegal (default
  deny); **Degraded → consequence proceeds is illegal** (RFC-0004 §9.12).
- Fail closed (AU8): a failed or refused write moves the store to Degraded and
  reports the failure; the consequence it preceded is blocked and the Operator
  is told. Recovery (§22) is reconciliation: a genuinely lost write is recorded
  as failed-to-record, never invented; deleted records never return (AU13).
- The durable backing (filesystem/database, retention, deletion, export) is
  deferred to RFC-0020 (§1.2, Q8).

`audit/transcript.py`

- The deterministic derivation function: transcript = render(record), producing
  exactly the §8 categories (dialogue, actions/outcomes, decisions/grounds,
  disclosures, recovery context) from the record **only** — the transcript
  never holds material the record does not (AU2; RFC-0013 §8; DoD). The
  presentation *form* (how it is shown to a beginner) is RFC-0015's (§5,
  §1.2).

Nothing else is exported. The facades re-export only the owned vocabulary
(blueprint §3); the executor surface carries no execution authority beyond the
sanctioned run boundary, and the audit surface carries no decision path (AU1).

---

## 7. Boundary analysis

- **Downstream of the gate.** The token is minted and validated at `policy`
  (Iteration 7); the executor is *upstream-adjacent* — it consumes the token as
  a handoff value and independently refuses anything not carrying a valid,
  unexpired, state-consistent token without importing `policy` (RFC-0008 §10
  layer 3; RFC-0004 A2). The boundary re-validation verdict (preconditions,
  machine-state domains) is consumed as an explicit input (Q3), because the
  machine-state compare is RFC-0021's (Draft) and the runtime boundary
  handler's, and the executor may not import `factlayer`/`policy`.
- **Upstream of Verification.** The runner reports completion (exit status,
  sanitized output, state-delta) for Verification; it never decides success
  (RFC-0004 §4.9; RFC-0006). The exit toward Verification is `core`'s
  transition (RFC-0002 §2.8), recorded at §1.2.
- **The write points are this layer's boundaries.** Execution start/end are
  recorded by the component whose consequence they precede — the executor —
  through `audit`, before the consequence proceeds (RFC-0002 I-13; RFC-0013
  §23). A failed pre-write blocks the run (AU8). The other §7 write points
  (goal adoption, proposal, classification, verification, outcome) belong to
  their owning components (RFC-0013 §23; §1.2).
- **The secret boundary.** Output is bounded, truncated, and redacted via
  `secrets` before it enters the record or any display (SC8/SC10); the audit
  holds metadata only (SC4). Elevation never displays or records a value
  (SC10). No Action carries a secret (SC9, asserted at `policy`). All three are
  boundary tests, not unit tests (RFC-0009 §0; blueprint §9 #9's "SC2–SC5 are
  boundary tests, not unit tests" precedent).
- **No shell, ever.** The run primitive receives a structured Action and an
  argv-shaped execution descriptor; nothing is ever interpolated into a shell
  string (I-5; RFC-0001 §8.4 rule 4). The boundary test proves no shell string
  is constructed from any untrusted input.
- **The audit is not authority.** Nothing in this layer treats the record as a
  decision input; the store exposes no verdict, the transcript feeds no
  reasoning path (AU1/AU2; RFC-0004 §4.12).
- **Degraded is never silent.** A failed write is disclosed as a failure,
  never as a gap (RFC-0004 §9.12; RFC-0013 §21); the consequence is blocked,
  and recovery is reconciliation, never invention (RFC-0013 §22; AU13).

---

## 8. Required invariants

Each invariant's normative source, whether the layer can make it hold at its
own surface now, and where the remainder is enforced (mirroring the
layer-boundary precedent of Iterations 5–7).

| Invariant | Normative source | Layer-enforceable now | Enforcement point for the rest |
|---|---|---|---|
| I-1 — execution never starts without approval | RFC-0002 §9; RFC-0004 A2/A9; RFC-0008 P1 | **Yes** (C3: the run entry requires a token-bound Action + a valid, independently re-validated token; no token → no run) | `core` (the §6.2 edges), Iteration 10 |
| I-2 — verification always follows execution | RFC-0002 §9; RFC-0004 A5 | Boundary (the runner reports completion for Verification; it never decides success) | `core` (the exit toward Verification), Iteration 10; `verification`, built |
| I-5 — no untrusted text interpolated | RFC-0002 §9; RFC-0001 §8.4 rule 4 | **Yes** (C3/C4: argv-structured run descriptor; no shell string; boundary test over LLM/machine/skill-shaped inputs) | — |
| I-8 — any halt re-assessed | RFC-0002 §9; §2.8 | Boundary (a timed-out/interrupted run yields outcome-unknown and is recorded as such) | `core` (Interrupted state), Iteration 10 |
| I-11 — tokens scoped and consumable | RFC-0002 §9; RFC-0008 §8/§10 | **Yes** (C3: the runner re-validates validity/unexpired/consumed/identity/session at the boundary, independently) | consumption bookkeeping shared with `policy` (mint/consume), `core` |
| I-13 — audit written before the consequence | RFC-0002 §9; RFC-0004 A10; RFC-0013 §1/§23 | **Yes** (C1/C3: the runner writes the execution-start record before the run; a failed write blocks the run — DoD) | the other write points, their owning components |
| I-15 — no standing authorization across a boundary | RFC-0002 §9; RFC-0008 §8 | Boundary (the token is re-validated per run; nothing persists across the boundary) | `core` (reboot/interrupt/reload events), Iteration 10 |
| AU1 — Audit is never authority | RFC-0013 §33; RFC-0004 §4.12 | **Yes** (C4: no reasoning or approval path reads the record as input; store exposes no verdict) | — |
| AU2 — Transcript is never evidence | RFC-0013 §33; RFC-0005 §3 | **Yes** (C2/C4: no verification or reasoning path consumes a transcript rendering) | — |
| AU3 — every consequential event recorded before its consequence | RFC-0013 §33; RFC-0002 I-13 | **Yes** (C3: the execution write precedes the run; a trace proves each consequential boundary has a prior record) | the other §7 boundaries, their owners |
| AU4 — append-only, tamper-evident | RFC-0013 §33; RFC-0004 A7 | **Yes** (C1: append-only store, hash-chain; an attempted edit is refused, no silent change) | — |
| AU5 — recording is deterministic | RFC-0013 §33; RFC-0004 §4.12 | **Yes** (C1: identical events → identical, reproducible records) | — |
| AU6 — no actor exempt | RFC-0013 §33 | Boundary (the executor's events are recorded; other actors recorded at their own boundaries) | the other components' write points |
| AU7 — no secret value ever enters the Audit | RFC-0013 §33; RFC-0009 SC4 | **Yes** (C1/C4: metadata-only records; no value-shaped field; boundary test) | — |
| AU8 — failed write blocks and discloses | RFC-0013 §33; RFC-0004 §9.12 | **Yes** (C1/C3: a blocked store refuses the next write; the runner refuses the run; the failure is disclosed — DoD) | `core`'s runtime refusal at Iteration 10 |
| AU9 — complete by construction | RFC-0013 §33; RFC-0002 §2.7 | **Yes** (C3: every run records start/end, including outcome-unknown) | — |
| AU10 — visible/exportable to Operator at any time | RFC-0013 §33; RFC-0002 §6 | Boundary (the store is readable/exportable; the *view* is `cli`'s, RFC-0001 §5 Presentation) | `cli`/RFC-0015 |
| AU11 — deletion irreversible, complete, recorded | RFC-0013 §33; RFC-0001 §9.1 | Boundary (deletion is illegal in this layer's state machine; the durable deletion mechanics are RFC-0020's) | RFC-0020 |
| AU12 — retention only under a stated purpose | RFC-0013 §33; RFC-0001 §9.5 | Boundary (retention policy is RFC-0020's) | RFC-0020 |
| AU13 — recovery is reconciliation, never rewrite | RFC-0013 §33; RFC-0004 §9.12 | **Yes** (C1/C4: a failed write is recorded as failed-to-record; no invention; deleted records never return) | — |
| AU14 — no hidden retention | RFC-0013 §33; RFC-0001 §9.2 | Boundary (retention mechanics are RFC-0020's; nothing retained in this layer) | RFC-0020 |
| AU15 — the Audit is never Memory/Context | RFC-0013 §33; RFC-0012 CM15 | **Yes** (C4: no reasoning path consumes audit records as Context or Memory) | — |
| AU16 — the Audit carries no permissions | RFC-0013 §33; RFC-0004 A8 | **Yes** (C4: a record grants no execution capability; possession widens nothing) | — |
| P9 — preconditions re-validated at the boundary | RFC-0008 §13; RFC-0002 §2.8 | **Yes, as the runner's local re-validation** (identity/expiry/consumed/session) + the consumed boundary verdict (Q3); the machine-state compare is the runtime's | `core` boundary handler, Iteration 10 |
| P12 — elevation explicit/scoped/revoked | RFC-0008 §13; RFC-0001 §8.6 | **Yes** (C4: per-Action elevation request, bounds, revocation on end/invalidation); the *mechanism* is injected (RFC-0021 §3.3) | mechanism injection at `core`/runtime |
| P13 — recorded before spent | RFC-0008 §13; RFC-0002 I-13 | **Yes** (C1/C3: the execution and approval records precede the run; durable write now, per DN-50) | — |
| SC4 — no secret in the Audit | RFC-0009 SC4; RFC-0013 §31 | **Yes** (C1/C4: metadata-only; value-shaped fields impossible by construction) | — |
| SC10 — elevation exposes nothing | RFC-0009 SC10; RFC-0008 §8 | **Yes** (C4: elevation never displays or records a value) | — |

DoD subset (blueprint §8.8): **I-1, I-5, I-11** (executor) and **I-13, AU8**
(audit) — all layer-enforceable per the table; plus the blueprint §7 oracle's
P9, P12, SC10 (executor) and A7, SC4 (audit). The package's blueprint §10
coverage rows (`executor/*` = RFC-0004 §4.9 / RFC-0002 §2.8, I-1/I-5/I-11/P12/
SC10; `audit/*` = RFC-0013, AU1–AU16/I-13/SC4) are satisfied across the layer +
the recorded cross-component obligations (§1.2).

---

## 9. Ambiguities

Each is **reported, not resolved** here; each names the corpus silence that
forces the report and the RFC/decision that owns the answer. Column
"Blocking?" marks whether it elevates to a blocking question in §10.

| # | Subject scope | RFC §/location | Open question | Alternative readings | Governing RFC / note | Blocking? |
|---|---|---|---|---|---|---|
| A1 | Run primitive representation | RFC-0004 §4.9; RFC-0002 §2.8; blueprint §3/§5 | The executor "runs approved Actions against the Machine" (RFC-0004 §4.9) and applies "scoping, timeouts, output capture" (RFC-0001 §5), but there is no real machine interaction in a scaffold and `executor` must not import `factlayer`/`verification`. How is "running" represented at this layer so I-1/I-5/I-11 are testable without a real subprocess? | (a) the runner takes an injected **run primitive** (`run(action, argv) -> RunResult`) supplied at the boundary; the package performs no I/O and no subprocess spawn; determinism + guardrails tested against a test primitive (b) the runner actually spawns subprocesses (I/O in the package; not conformance-testable; needs real execution semantics) | RFC-0004 §4.9; RFC-0002 §6.2 (executor consulted only in Executing); RFC-0001 §5; blueprint §3 | **Yes (Q1)** |
| A2 | Token handoff type | RFC-0008 §8/§10; RFC-0004 A2; blueprint §4.2 | The token is a `policy` type (minted at Iteration 7), but `executor` must NOT import `policy`. RFC-0008 §10 requires the Executor to independently refuse anything not carrying a valid token. What is the token's shape at the executor boundary, and what does the runner re-validate locally? | (a) a **structural handoff value** — the `policy.Token` public fields (Action identity, class, gate, expiry, state-snapshot ref, session, consumed, elevation bounds) as a plain schema-shaped record; the runner re-validates those fields deterministically (b) executor imports `policy` (forbidden edge) or duplicates the token type (ownership violation) | RFC-0008 §8/§10; RFC-0004 A2; blueprint §4.2; Iteration 7 review §3 ("the token is the handoff value, not a call") | **Yes (Q2)** |
| A3 | State-consistency/precondition verdict | RFC-0008 §9; RFC-0002 §6.2 edge (b); RFC-0002 I-11 | Re-validation at the boundary compares "State Domains the Action touches against the snapshot" and re-checks Facts for staleness (RFC-0008 §9) — but the runner may not import `factlayer`/`policy` and the State-Domain diff is RFC-0021's (Draft). How does the executor obtain "state-consistent"? | (a) the runner re-validates what it can locally (valid/expired/consumed/Action-identity/session) and consumes the **machine-state + precondition verdict as an explicit boundary input** (computed by the §6.2 edge-b handler / runtime); any uncertainty → refused (b) the runner re-derives the State-Domain compare (needs forbidden imports + Draft vocabulary) | RFC-0008 §9/§10; RFC-0021 (Draft) §6; RFC-0002 §6.2(b); DN-48 | **Yes (Q3)** |
| A4 | Execution command construction (I-5) | RFC-0002 I-5; RFC-0001 §8.4; RFC-0007 §4.4 | I-5 forbids interpolating untrusted text into a command; RFC-0001 §8.4 rule 4 is absolute. How does the runner turn a structured `schema.Action` into something a run primitive can execute, with the "no shell string, ever" guarantee enforced and testable? | (a) the runner builds an **argv-structured descriptor** (`[executable, *args]`) from the sanctioned Action structure only; no shell string is ever constructed; a boundary test feeds LLM/machine/skill-shaped text and proves no shell string results (b) the runner accepts a command string (violates I-5) | RFC-0002 I-5; RFC-0001 §8.4 rule 4; RFC-0007 §4.4; blueprint §3 | **Yes (Q4)** |
| A5 | Guardrail bounds and redaction | RFC-0001 §5, §8.8; RFC-0002 §11 Q3; SC10 | "Scoping, timeouts, output capture, no secret leakage" (RFC-0001 §5) — but concrete timeouts/output ceilings are RFC-0002 §11 Q3's open question and RFC-0020 content. How much mechanism is built now? | (a) the **mechanism** now — deterministic timeout over the run primitive with a placeholder default bound (DN-18 precedent), bounded output capture truncated rather than dumped, redaction via `secrets` (SC8/SC10); concrete values RFC-0020's (b) guardrails deferred wholesale to RFC-0020 (would make I-5/SC10 untestable here) | RFC-0001 §5/§8.8; RFC-0002 §11 Q3; DN-18; RFC-0009 SC8/SC10 | **Yes (Q5)** |
| A6 | Elevation module scope | RFC-0008 §8; RFC-0001 §8.6; RFC-0021 §3.3 | RFC-0008 §8 fixes elevation *semantics* (explicit, per-action, scoped, at least Consequential, bounds on token, revoked at end/invalidation, never persists) but names no *mechanism*; RFC-0021 §3.3 (Draft) owns the machine's mechanism. DN-53 recorded the mechanism/revocation as `executor.elevation`'s DoD. What does the module build now? | (a) the **deterministic lifecycle** — per-Action elevation request carrying bounds (which `policy` already enforced as at-least-Consequential), and revocation on end/invalidation; the machine mechanism is injected at the boundary (b) defer elevation.py wholesale to RFC-0021 acceptance (would make P12/SC10 untestable now) | RFC-0008 §8; RFC-0001 §8.6; RFC-0021 §3.3 (Draft); DN-53; blueprint §3 (elevation.py) | **Yes (Q6)** |
| A7 | Record-before-consequence wiring at the runner | RFC-0002 I-13; RFC-0013 §7 cat. 6, §21, §23; AU8; RFC-0004 A10 | Execution start/end are audited "before the consequence is allowed to proceed" (RFC-0013 §23) and a failed write blocks the consequence (AU8). Who writes the execution records, and how is the block enforced at the executor surface now (with `core` not yet built)? | (a) the **runner writes** the execution-start record through `audit` **before** the run and the end record after; a failed pre-write **blocks the run and is disclosed** (AU8) — the write point is the component whose consequence it precedes (RFC-0013 §23; blueprint §5) (b) the runner exposes record hooks and `core` wires them (would leave AU8 untestable until Iteration 10) | RFC-0002 I-13; RFC-0013 §23/§21; blueprint §5's non-hub note; DN-50 | **Yes (Q7)** |
| A8 | Audit store durability | RFC-0013 §1, §11, §12, §21, §22 | RFC-0013 §1 calls the record "durable"; §11 defines the lifecycle (Empty/Recording/Degraded/Recovering/…), §21 fail-closed, §22 reconciliation. But the scaffold posture has been in-memory with durable mechanics deferred (DN-19/DN-27/DN-34/DN-50), and RFC-0020 owns storage mechanics. What does `store.py` build now? | (a) an **in-memory append-only store** with hash-chain tamper-evidence, the §11 lifecycle + legal §12 transitions, AU8 fail-closed, and §22 reconciliation (a lost write is recorded as failed-to-record, never invented); durable backing/retention/deletion/export deferred to RFC-0020 (b) a real durable backend now (needs storage mechanics + retention policy, both RFC-0020's) | RFC-0013 §1/§11/§12/§21/§22; RFC-0002 I-13; DN-19/DN-27/DN-34/DN-50; RFC-0020 | **Yes (Q8)** |
| A9 | Record categories in scope | RFC-0013 §7 | §7 enumerates twelve record categories; the Audit System owns the record format for all, but only some write points exist in this layer (execution at the runner; secret-metadata at the store; approval/override/auto-permit/rejection durable write per DN-50). Does `records.py` implement the full §7 category set now, or the categories this layer's boundaries exercise? | (a) the **canonical category types for this layer's boundaries** (execution, secret-metadata, approval/override/auto-permit/rejection per DN-50) as the implemented, tested set; the remaining categories' types arrive with their owning write points (recorded, not dropped) (b) all twelve §7 categories as types now, with writers exercised later (orphaned until their boundaries exist) | RFC-0013 §7, §16 (no actor exempt, but each is written at *its* boundary); DN-50; blueprint §8.8 | **Yes (Q9)** |
| A10 | Transcript derivation scope | RFC-0013 §8, §5; AU2 | The Transcript is derived from the record and presents five §8 categories; its presentation *form* is RFC-0015's (§5). Does `transcript.py` implement the deterministic derivation of all five categories now? | (a) **derivation now** — transcript = render(record) producing the §8 categories, never material the record lacks (AU2; DoD); the *form* (how it is shown) is RFC-0015's (b) defer transcription until `cli`/RFC-0015 (would leave AU2 and the §8 DoD untested) | RFC-0013 §8/§5; AU2; RFC-0001 §5 Presentation; blueprint §5 | **Yes (Q10)** |
| A11 | Secret-metadata type | RFC-0013 §7 cat. 10, §31; SC4; blueprint §4.2 | The secret-metadata record answers "what secret was stored, when used, was it destroyed" without holding a value (RFC-0013 §31 rule 3). `audit` may import `secrets` metadata types only. What exactly does the record carry, and is SC4 enforced structurally? | (a) the record carries `secrets` *classifier/metadata types* (the category/classification result, timestamps, lifecycle events) and **no value-shaped field by construction**; a boundary test proves no value can enter (b) the record carries free-form strings (value-leak risk; violates SC4) | RFC-0013 §7 cat. 10, §31; RFC-0009 SC4; blueprint §4.2 | **Part of Q9** |

---

## 10. Blocking questions

| Q | Question | Owner (RFC §) | Blocks | Sev. | Recommended resolution |
|---|---|---|---|---|---|
| Q1 | Run primitive: injected boundary vs real subprocess (A1) | RFC-0004 §4.9; RFC-0002 §6.2; RFC-0001 §5 | C3 | High | **Injected run primitive.** The runner takes `run(action, argv) -> RunResult` supplied at the boundary; the package performs no I/O, no subprocess spawn, and no shell; I-1/I-5/I-11 and the guardrails are tested against a test primitive; real machine interaction is `core`'s wiring (Iteration 10) |
| Q2 | Token handoff type and local re-validation (A2) | RFC-0008 §8/§10; RFC-0004 A2; blueprint §4.2 | C3 | High | **Structural handoff value.** The token's public fields (Action identity, class, gate, expiry, state-snapshot ref, session, consumed, elevation bounds) cross as a plain schema-shaped record; the runner re-validates validity/expiry/consumed/identity/session locally, without importing `policy` (independent enforcement, RFC-0008 §10 layer 3) |
| Q3 | State-consistency/precondition verdict (A3) | RFC-0008 §9; RFC-0002 §6.2(b); RFC-0021 (Draft) | C3 | High | **Local re-validation + consumed boundary verdict.** The runner checks what it can locally and consumes the machine-state + precondition re-validation as an explicit input computed by the §6.2 edge-b handler/runtime; any uncertainty → refused (fail closed, RFC-0008 §9) |
| Q4 | Execution command construction / no-shell (A4) | RFC-0002 I-5; RFC-0001 §8.4; RFC-0007 §4.4 | C3 | High | **argv-structured descriptor, no shell string.** The runner derives `[executable, *args]` from the sanctioned Action structure only; a boundary test feeds untrusted-shaped text (LLM/machine/skill) and proves no shell string is constructed |
| Q5 | Guardrail mechanism vs RFC-0020 values (A5) | RFC-0001 §5/§8.8; RFC-0002 §11 Q3; DN-18 | C3/C4 | Med | **Mechanism now, values later.** Deterministic timeout over the run primitive (placeholder default bound, DN-18); bounded output capture, truncated not dumped; redaction via `secrets` (SC8/SC10); concrete budgets/ceilings are RFC-0020's |
| Q6 | Elevation module: lifecycle now vs deferred (A6) | RFC-0008 §8; RFC-0001 §8.6; RFC-0021 §3.3; DN-53 | C4 | Med | **Deterministic lifecycle now.** Per-Action elevation request carrying bounds (at-least-Consequential already at `policy`), revocation at end/invalidation, never persists, never covers unapproved work; the machine mechanism is injected at the boundary (RFC-0021 §3.3, Draft) |
| Q7 | Record-before-consequence at the runner (A7) | RFC-0002 I-13; RFC-0013 §23/§21; AU8; DN-50 | C1/C3 | High | **The runner writes start/end through `audit`; a failed pre-write blocks the run and is disclosed.** The write point is the component whose consequence it precedes (RFC-0013 §23; blueprint §5); AU8/I-13 are testable at this layer |
| Q8 | Audit store durability (A8) | RFC-0013 §1/§11/§12/§21/§22; DN-19/27/34/50 | C1 | High | **In-memory append-only store now.** Hash-chain tamper-evidence; §11 lifecycle + §12 legal transitions (Degraded → consequence proceeds illegal); AU8 fail-closed; §22 reconciliation (failed-to-record, never invented); durable backing/retention/deletion/export deferred to RFC-0020 |
| Q9 | Record categories in scope (A9) | RFC-0013 §7; DN-50; blueprint §8.8 | C1 | Med | **This layer's boundaries' categories.** Canonical types for execution (cat. 6), secret-metadata (cat. 10, on `secrets` metadata types, SC4), and the approval/override/auto-permit/rejection durable write (cat. 4/5, DN-50); the remaining categories' types arrive with their owning write points (recorded, not dropped) |
| Q10 | Transcript derivation scope (A10) | RFC-0013 §8/§5; AU2 | C2 | Med | **Derivation now.** transcript = render(record) producing the §8 categories, never material the record lacks (AU2, DoD); the presentation *form* is RFC-0015's |

**Status: Ratified.** Q1–Q10 were ratified by the Operator (2026-08-07) and
recorded as **DN-55…DN-64** in `docs/implementation-decision-notes.md` before
C0. Each recommended resolution was adopted as a decision note; the design
review §16 readiness flips to READY.

---

## 11. Proposed Decision Notes (DN-55…DN-64)

Proposals for Operator ratification; none took effect by this review. **Ratified
as DN-55…DN-64 in `docs/implementation-decision-notes.md`** in the established
table form — Status (Ratified, Operator, Iteration 8 ratification) / Date
(2026-08-07) / Resolves (design review §10 Qn) / Grounding (RFC sections + DN
precedents) / Embodied in (commit) / Decision — mirroring DN-40…DN-54.

| DN | Resolves | Proposal |
|---|---|---|
| DN-55 | Q1 | The runner takes an injected run primitive (`run(action, argv) -> RunResult`); the `executor` package performs no I/O and no subprocess spawn; I-1/I-5/I-11 and guardrails are tested against a test primitive |
| DN-56 | Q2 | The token crosses as a structural handoff value (its public fields as a plain schema-shaped record); the runner re-validates validity/expiry/consumed/Action-identity/session locally, without importing `policy` |
| DN-57 | Q3 | The runner re-validates what it can locally and consumes the machine-state + precondition re-validation as an explicit boundary input; any uncertainty → refused (fail closed) |
| DN-58 | Q4 | Execution uses an argv-structured descriptor built from the sanctioned Action structure only; no shell string is ever constructed (I-5), enforced by a boundary test |
| DN-59 | Q5 | Guardrail mechanism now (deterministic timeout with a placeholder default bound; bounded output capture truncated not dumped; redaction via `secrets` SC8/SC10); concrete budgets/ceilings are RFC-0020's |
| DN-60 | Q6 | `elevation.py` implements the deterministic elevation lifecycle (per-Action request with bounds, revocation at end/invalidation, never persists); the machine mechanism is injected at the boundary (RFC-0021 §3.3, Draft) |
| DN-61 | Q7 | The runner writes the execution start/end records through `audit` before/after the run; a failed pre-write blocks the run and is disclosed (AU8) |
| DN-62 | Q8 | `store.py` is an in-memory append-only store with hash-chain tamper-evidence, the §11 lifecycle + §12 legal transitions, AU8 fail-closed, and §22 reconciliation; durable backing deferred to RFC-0020 |
| DN-63 | Q9 | `records.py` implements this layer's boundaries' categories (execution, secret-metadata on `secrets` metadata types, approval/override/auto-permit/rejection per DN-50); remaining categories arrive with their write points |
| DN-64 | Q10 | `transcript.py` implements derivation from the record only, producing the §8 categories; the presentation form is RFC-0015's |

---

## 12. Atomic implementation plan

Each commit is <300 production LOC, single responsibility, test-visible, on a
branch derived from `iteration/7-policy` (e.g. `iteration/8-executor`). Commit
order follows ratification of the questions it depends on. Est. = estimated LOC
(impl / test / docs). C1–C4 **fill the Iteration 0 scaffold stubs** (`runner.py`,
`guards.py`, `elevation.py`, `records.py`, `store.py`, `transcript.py` already
exist with ownership docstrings; the tree test stays green).

| Commit | Message | Content | Est. (impl/test) | Depends on | Deliverable |
|---|---|---|---|---|---|
| C0 | `docs: ratify Iteration 8 questions Q1–Q10 and executor+audit scope` | Decision notes for Q1–Q10 (DN-55…DN-64), design review record, renumbering note (Q1), consistency-report note | — / — / ~800 | Q1–Q10 ratified | Ratified plan; all questions answered |
| C1 | `feat(audit): append-only record store and canonical categories (RFC-0013 §1, §7, §11, §12, §21, §22; AU4, AU5, AU7, AU8, AU13)` | `store.py`: in-memory append-only store, hash-chain tamper-evidence, §11 lifecycle + §12 legal transitions (Degraded → consequence proceeds illegal), AU8 fail-closed, §22 reconciliation (failed-to-record, never invented) (Q8); `records.py`: the canonical categories for this layer's boundaries — execution, secret-metadata (on `secrets` metadata types, SC4), approval/override/auto-permit/rejection durable write (DN-50) (Q9); immutable, category-carrying, value-free records | ~260 / ~340 | Q8, Q9 | Audit store + record categories |
| C2 | `feat(audit): transcript derivation from the record (RFC-0013 §8, §5; AU2)` | `transcript.py`: transcript = render(record) producing the §8 categories (dialogue, actions/outcomes, decisions/grounds, disclosures, recovery context) from the record only; never material the record lacks (AU2); the form is RFC-0015's | ~140 / ~200 | Q10 | Transcript derivation |
| C3 | `feat(executor): sanctioned runner under a valid token (RFC-0004 §4.9; RFC-0002 §2.8; I-1, I-5, I-11, I-13)` | `runner.py`: token handoff value (Q2); local re-validation (valid/expired/consumed/identity/session) + consumed boundary verdict (Q3); argv-structured run descriptor, no shell string (I-5, Q4); injected run primitive (Q1); writes execution start before the run and end after through `audit`; a failed pre-write blocks the run and is disclosed (AU8, Q7); reports completion for Verification, never a success verdict (I-2) | ~250 / ~350 | Q1, Q2, Q3, Q4, Q7 | Sanctioned runner |
| C4 | `feat(executor): guardrails and scoped elevation (RFC-0001 §5, §8.6; RFC-0008 §8; P12, SC10)` | `guards.py`: scoping to the one approved Action; deterministic timeout with placeholder bound; bounded output capture truncated not dumped; redaction via `secrets` (SC8/SC10); fail closed (Q5). `elevation.py`: the deterministic elevation lifecycle — per-Action request with bounds, revocation at end/invalidation, never persists (P12, SC10; Q6); the machine mechanism injected at the boundary | ~200 / ~300 | Q5, Q6 | Guardrails + elevation |
| C5 | `test(executor, audit): Layer-4 conformance and AU/I/P/SC invariant suite` | Conformance (imports limited to `schema`/`audit`/`secrets` for executor and `schema`/`secrets` for audit + sanctioned stdlib, no I/O/no subprocess/no forbidden stdlib, public surface == owned vocabulary, package tree unchanged); invariant tests I-1, I-5, I-11, I-13, AU1–AU16, P9/P12/P13, SC4/SC10; boundary tests: I-5 no-shell over untrusted-shaped inputs, AU8 failed-write-blocks-run, I-13 record-before-run, SC4 no-value-field, SC10 elevation-no-exposure; cross-component obligations (the §6.2 edges, the Executing exits, startup store opening, the elevation mechanism) recorded against `core`/RFC-0021 | 0 / ~480 | C1–C4 | Conformance oracle |
| C6 | `docs: record Iteration 8 completion and executor+audit conformance` | Consistency report + decision notes completion + deferred-items table | — / — / ~220 | C5 | Completion record |

---

## 13. Validation strategy

Same gates as Iterations 1–7: `pytest` (baseline **1722 tests**), `ruff check`,
`ruff format --check`, `python -m build`, and `pre-commit run --all-files`.
Conformance is enforced by the existing `tests/test_dependency_rules.py` (the
`executor` and `audit` rows are already declared:
`ALLOWED["executor"] = {"schema", "audit", "secrets"}`,
`ALLOWED["audit"] = {"schema", "secrets"}`, and their forbidden-source rows) and
`tests/test_packages.py` (already green — the six modules exist as stubs),
extended by C5's new `test_executor_conformance.py`, `test_audit_conformance.py`,
and the AU/I/P invariant suites. Because C0–C6 touch neither `rfc/` nor
`tools/`, the RFC-reference validator is not a gate for this iteration (CI
still runs it; the known pre-existing RFC-0004 §470 `'S1'` error is unrelated
and unchanged). Determinism is asserted by property-style tests: the same
token + same Action + same boundary verdict → the same acceptance, the same
records, the same transcript; the no-shell property (I-5) is asserted over
LLM/machine/skill-shaped inputs; the audit's append-only and reconciliation
properties are asserted by edit-attempt and failed-write injection tests.

---

## 14. Definition of Done (per commit)

| Commit | Definition of Done |
|---|---|
| C0 | Q1–Q10 each answered and recorded as decision notes (DN-55…DN-64); the renumbering tension (Q1) recorded; this review's readiness flips to READY |
| C1 | The store is append-only — an attempted edit or erase of a prior record is refused with no silent change (AU4); every record is immutable and carries its category (RFC-0013 §7); recording is deterministic — identical events yield identical records (AU5); no record contains a value-shaped field (SC4/AU7); a failed or refused write moves the store to Degraded and is disclosed (AU8); Degraded → consequence proceeds is illegal (§12); recovery records a lost write as failed-to-record, never invents one, and never resurrects deleted records (AU13, §22); the implemented categories are exactly the layer's boundaries' (Q9) |
| C2 | The transcript derives from the record only (AU2); it presents exactly the §8 categories and never holds material the record does not (RFC-0013 §8); no verification or reasoning path consumes a transcript rendering (AU2) |
| C3 | The runner refuses to start without a token-bound Action and a valid, independently re-validated token (I-1, I-11, A2); it re-validates validity/expiry/consumed/identity/session locally and consumes the boundary verdict (P9, Q3), refusing on any uncertainty (fail closed); it constructs an argv-structured descriptor and never a shell string (I-5, Q4); the run primitive is injected (Q1); it writes the execution-start record before the run and the end record after, through `audit` (I-13), and a failed pre-write blocks the run and is disclosed (AU8, Q7); it reports completion for Verification and never decides success (I-2) |
| C4 | Guardrails: the run is scoped to the one approved Action; a deterministic timeout with a placeholder default bound yields an outcome-unknown result; output capture is bounded, truncated not dumped, and redacted via `secrets` before recording (SC8/SC10); any guardrail error fails closed and is disclosed. Elevation: per-Action, scoped, carrying bounds, revoked at end/invalidation, never persists, never covers unapproved work (P12, SC10); the mechanism is injected, not built (RFC-0021 §3.3) |
| C5 | Blueprint §7 executor/audit rows and §8.8 DoD (I-1/I-5/I-11, I-13/AU8) pass; every layer-enforceable invariant in §8 has a test; conformance: imports limited to the declared allowed sets + sanctioned stdlib, no I/O, no subprocess, no forbidden stdlib, public surface == owned vocabulary, package tree unchanged; the I-5 no-shell, AU8 blocked-run, I-13 record-before-run, SC4 no-value, and SC10 no-exposure boundary tests pass; cross-component obligations (the §6.2 edges, the Executing exits, the startup store opening, the elevation mechanism) recorded against `core`/RFC-0021; full suite green |
| C6 | Consistency report reflects Iteration 8; no orphaned decision notes; the deferred-items table names every §1.2 owner |

**Overall DoD (blueprint §8.8):** I-1/I-5/I-11 (executor) and I-13/AU8 (audit)
conformance; a consequence with a failed audit write is blocked and disclosed
(AU8); the transcript derives from the record only (RFC-0013 §8); `pytest`
full suite, `ruff check`, `ruff format --check`, `python -m build` all green;
`tests/test_dependency_rules.py` and `tests/test_packages.py` still green
(tree and edges unchanged).

---

## 15. LOC estimates

| Commit | impl | test | docs | Notes |
|---|---|---|---|---|
| C0 | — | — | ~800 | Ratification |
| C1 | ~260 | ~340 | — | Audit store + record categories |
| C2 | ~140 | ~200 | — | Transcript derivation |
| C3 | ~250 | ~350 | — | Sanctioned runner |
| C4 | ~200 | ~300 | — | Guardrails + elevation |
| C5 | 0 | ~480 | — | Conformance + invariants |
| C6 | — | — | ~220 | Closeout |
| **Total** | **~850** | **~1,670** | ~1,020 | |

Production total ≈ **850**; test total ≈ **1,670**. Test LOC may exceed the
300-LOC cap per-commit, as in Iterations 4–7 (the cap applies to implementation
lines). C1 (store) and C3 (runner) carry the DoD's conformance weight
(AU4/AU8/I-13 and I-1/I-5/I-11 respectively).

---

## 16. Readiness assessment

**Status: BLOCKED** pending ratification of Q1–Q10 (recorded as decision notes
DN-55…DN-64 before C0), exactly as Iterations 1–7 began. The highest-leverage
questions are **Q1** (the run primitive that makes execution testable without
a real subprocess), **Q2** (the token handoff that satisfies independent
enforcement without a `policy` import), **Q3** (the state-consistency verdict
the executor cannot derive itself), **Q4** (the no-shell construction that
makes I-5 structural), **Q7** (the record-before-consequence wiring that makes
AU8/I-13 testable here), and **Q8** (the in-memory store that satisfies
append-only/tamper-evident/lifecycle now with durability deferred). Once
Q1–Q10 are ratified, the layer is **READY** and commits execute in order
C0→C6, each satisfying its §14 DoD before the next begins. The dominant
residual risk is the Draft status of RFC-0013 itself (§17 risk 1); the layer's
load-bearing dependencies are all Accepted, which bounds it.

**Post-ratification status (Iteration 8, Commit C0).** Q1–Q10 were ratified and
recorded as **DN-55…DN-64** (`docs/implementation-decision-notes.md`) before
C0, the docs-ratification commit: all ten questions answered as decision notes,
the renumbering tension (Q1) recorded as a continuation of DN-45's supersession
note, and the consistency report updated. **Status: Ratified.** The layer is
now **READY for implementation** — commits execute in order C0→C6, each
satisfying its §14 DoD before the next begins. C1–C6 (the `audit` package:
`records.py`, `store.py`, `transcript.py`; the `executor` package: `runner.py`,
`guards.py`, `elevation.py`; the conformance suite; and the closeout) remain to
be implemented per §12/§14.

---

## 17. Final verdict

This plan is a faithful translation of the frozen corpus into an
executor+audit-layer scaffold: **no new architecture is proposed**, every
ambiguity is reported and elevated to a blocking question, no RFC is modified,
no module is invented beyond the scaffolded six, the allowed/forbidden
dependency graph is honored, the two authority rows (Execute; Persist/Explain)
are observed without overlap, and every layer-enforceable invariant (I-1, I-5,
I-11, I-13; AU1–AU16; P9/P12/P13; SC4/SC10) maps to a deterministic mechanism
and a test. The cross-component obligations (the §6.2 consultation edges, the
Executing exits toward Verification/Interrupted/Cancelled/END, the startup
opening and writability check of the audit store, the machine's own elevation
mechanism, the durable backing/retention/deletion of the record, the
Transcript presentation form, and the remaining §7 write points) are named
against `core`/RFC-0021/RFC-0015/RFC-0020 rather than dropped. The enforcement
halves Iteration 7 recorded (P1 independent enforcement, P12 elevation, the
durable P13 Audit write) are now DoD items of this iteration (Q2/Q6/Q7/Q9),
not deferred again. **Ratified: Q1–Q10 are recorded as DN-55…DN-64; the layer
is READY for C1.**

---

## Consistency review against the Blueprint and governing RFCs

**Consistent.** Module set `executor/{__init__,runner,guards,elevation}.py` and
`audit/{__init__,records,store,transcript}.py` fixed by blueprint §2 (scaffolds
already present); dependency rules (`ALLOWED["executor"] = {"schema", "audit",
"secrets"}`, `ALLOWED["audit"] = {"schema", "secrets"}` + stdlib, Layer 4)
honored by §3/§5; one-owner discipline (RFC-0004 §3) honored by §4 and the
two-owner checks (authority vs state; profile vs record model); the scaffold
gate (blueprint §8.0) stands; DN-45's re-order is now executed (`executor` +
`audit` = Iteration 8); DN-50's durable-write assignment is a DoD item (Q7/Q9);
DN-53's elevation mechanism/revocation assignment is a DoD item (Q6);
DN-43's SC4/SC10 boundary precedent is the Q7/Q9/Q10 reading; DN-18's
placeholder-default precedent is the Q5 reading; DN-19/DN-27/DN-34's
in-memory precedent is the Q8 reading; RFC-0002 §6.2's consultation edges are
recorded as `core`'s obligation (§1.2), never invoked here.

**Reported tensions (not violations):**

1. Blueprint §8.8 numbering vs DN-45's re-order — §8.8 still reads "Iteration 7
   — `executor` + `audit`" while this iteration implements it at Iteration 8
   (Q1). Needs ratification as a continuation of DN-45's recorded supersession.
2. RFC-0013 is Draft (2026-08-02); its normative sections 1–33 may change
   before acceptance — the rework risk is accepted (DN posture of Iterations
   1–7) and the layer's Accepted-RFC dependencies bound it.
3. RFC-0002 §2.1's "open the durable audit store" and "audit writability" at
   startup is `core`'s session-initialization step (Iteration 10); this layer
   provides the store object and writability check, not the startup call —
   recorded in §1.2, not invoked.
4. RFC-0008 §9's machine-state precondition compare and §10's boundary
   re-validation name the engine (a `policy`/runtime concern), while the
   executor must re-validate independently without importing `policy` (Q2/Q3)
   — needs ratification of the structural-handoff + consumed-verdict reading
   (DN-56/DN-57).
5. RFC-0013 §1's "durable" word vs the scaffold's in-memory precedent (Q8) —
   needs ratification of the in-memory-now/durable-later reading (DN-62),
   mirroring DN-50 for the approval records.
6. RFC-0013 §7's twelve categories vs the boundaries that exist in this layer
   (Q9) — needs ratification of the layer-boundary reading (DN-63), so no
   category type is orphaned before its write point exists.
7. RFC-0013 §5's Transcript presentation *form* (RFC-0015, future) vs the §8
   *derivation* this layer builds (Q10) — needs ratification of the
   derivation-now reading (DN-64).

**Verdict.** This plan is a faithful translation of the frozen corpus into an
executor+audit-layer scaffold; no new architecture is proposed, and every
ambiguity is elevated to a blocking question. Proceed to ratification.
