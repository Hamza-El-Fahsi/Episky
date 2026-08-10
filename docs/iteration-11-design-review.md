# Iteration 11 — Design Review (Orchestration Core Layer)

> **Document type:** Implementation design review, at the same rigor as
> Iterations 2–10. **Not an RFC, not code.**
> **Read this first:** This document **defines no new architecture, modifies no
> RFC, invents no behavior, and writes no production code.** It translates the
> frozen corpus (RFC-0000–0013, RFC-0021, the decision traceability matrix,
> `docs/architecture-implementation-blueprint.md`, the two walkthroughs, and the
> ratified `docs/implementation-decision-notes.md` DN-1…DN-84) into an
> implementation plan for the **Orchestration Core layer — the `core` package**
> (blueprint §8.11, "Iteration 10 — `core` (the loop)", re-ordered to Iteration
> 11 by DN-45 and so labeled by the Iterations 9 and 10 closeouts and the
> consistency-report "Readiness for Iteration 11"). Where the corpus does not
> decide something, this document **reports** it as an ambiguity or a question;
> it does not resolve it.
>
> **Status of sources.** Only RFC-0000, RFC-0001, RFC-0002, RFC-0003, RFC-0004
> are **Accepted**. RFC-0005 through RFC-0013 and RFC-0021 remain **Draft**
> (verified against every header, 2026-08-06), exactly as they were for
> Iterations 9–10. Among the Drafts `core` transcribes heavily — RFC-0008 (the
> approval-token discipline) and RFC-0013 (the audit write points) — the
> Iteration-10 posture still applies: conformance to the invariants, rework risk
> recorded, none of them re-opened here. Blueprint §8.0's gate stands —
> production code begins only after RFC-0015/0019/0020 and the Drafts are
> Accepted; this iteration keeps the scaffold posture of Iterations 1–10.
>
> **Scope decision (reported — Q1).** Blueprint §8.11 still reads "Iteration 10
> — `core` (the loop)" while DN-45 re-ordered the build so that `providers` +
> `skills` own Iteration 10 and `core` follows at Iteration 11; the consistency
> report records that "The next iteration is `core` (Layer 6; blueprint §8.11,
> re-ordered by DN-45), followed by `cli`." Iteration 10 executed the identical
> supersession for §8.10; this task does the same for §8.11 (Q1). The re-order is
> dependency-safe: `core` imports all lower layers (blueprint §4.1) and `cli`
> (Layer 7) is the only importer of `core`.

---

## 1. Architectural consistency review

### 1.1 Scope (blueprint §8.11, transcribed)

| Item | Value |
|---|---|
| Goal | The runtime that composes every package |
| Work | State machine, event loop, consultation router, replanning, recovery |
| Definition of Done | **State-machine conformance**: only RFC-0002 §3 transitions reachable; invariants 1–15 hold in every state; recovery ordering is determinism→disclosure→decision→action (§10); a full-loop integration test mirrors `docs/core-execution-walkthrough.md` §2/§3 and all 31 failure scenarios mirror `docs/failure-injection-walkthrough.md` §3 |
| RFC basis | RFC-0002 §1–§10 |

Blueprint §3 (responsibilities): "*Own the session loop and state transitions;
enforce the decision rules (RFC-0001 §5 Orchestration Core); keep the provider
world separate from the machine world; degrade gracefully; consult components
per §6; run failure recovery per §10.*" Blueprint §5 (public contract): "*the
session: start/stop, goal loop, state transitions, events, recovery — the only
entry point the `cli` uses* (RFC-0002 §1–§10)." Blueprint §7 (test oracle) row
for `core`: "**State-machine conformance**: only the transitions of RFC-0002 §3
are reachable; invariants 1–15 hold in every state; interruption → re-assessment
(I-8); no terminal outcome while work is in flight (I-14); no approval survives
a boundary (I-15); recovery ordering is determinism→disclosure→decision→action
(§10)." Blueprint §10 coverage row: `core` = RFC-0002, §1–§10, invariants 1–15.

**The enforcement halves this layer inherits (DoD of this iteration, never
deferred again).** Iterations 5–10 recorded, not dropped, every runtime-half
that binds `core`; each becomes a Definition of Done item here:

1. The session lifecycle and goal loop (RFC-0002 §1, §4.1; RFC-0004 §4.3),
   including the goal record (RFC-0013 §7 cat. 1) and the history/turn producers
   (RFC-0012 §6 cat. 3).
2. The complete event model of RFC-0002 §4 (§4.1–§4.7), typed and audited at the
   boundary before its consequence (I-13).
3. The state machine — only the transitions of RFC-0002 §2/§4 are reachable; no
   invented move (the walkthrough §6.1 impossible-transition table).
4. **The gate routing**: every provider-originated and Skill-originated Proposal
   and every Action passes the full classify → gate → token → re-validate →
   Executor path (RFC-0008 §5/§8; RFC-0004 A3).
5. **The audit writes at the runtime boundaries** — goal adoption, proposal,
   classification, approval, override, execution start/end, verification,
   outcome — plus the provider/skill-boundary events (loading, activation,
   failure, trust revocation) and the cat-9 context-boundary record, each written
   before its consequence (RFC-0013 §23; RFC-0002 invariant 13; RFC-0004 §9.11).
6. **The provider-world/machine-world separation in time** (RFC-0002 §1):
   `core` is the only place a Provider output or Skill Proposal ever travels
   toward a machine step, and that travel is only the gate and the Executor
   under a re-validated token.

**Constraint (dependency).** `core` may import every package (the conductor row,
blueprint §4.1) and is imported only by `cli`. Its C1–C4 *fill* the seven
Iteration-0 scaffolds (`session`, `state_machine`, `events`, `loop`,
`consultation`, `replan`, `recovery`) with **no new module** and **no change to
the allowed/forbidden graph** — the dependency test already sanctions
`ALLOWED["core"] = {all packages}` and the acyclicity test already passes.

### 1.2 Out of scope (recorded, not dropped)

| Item | Owned by | Gate |
|---|---|---|
| Durable resume markers, their storage/lifetime/garbage collection; interrupted-action reconciliation | RFC-0002 §2.1/§8/§10 | RFC-0014 |
| Concrete phase budgets, retry counts, grace windows, per-domain staleness bounds | RFC-0002 §11 OQ 2/3 | RFC-0020 / RFC-0002 |
| Concurrent read-only collection | RFC-0002 §11 OQ 15 | RFC-0020 |
| The read-only allowlist and its owner | RFC-0002 §11 OQ 4 | RFC-0008 |
| Multi-goal coexistence / queue / split | RFC-0002 §11 OQ 10 | RFC-0002 / RFC-0020 |
| The watchdog's concrete watch set and false-positive heuristics | RFC-0002 §11 OQ 17 | RFC-0020 |
| Real vendor adapters, skill fetch, sandbox | RFC-0020 | RFC-0020 |
| The TUI interaction contract | RFC-0015 | RFC-0015 |
| The RFC-0002 event-vocabulary additions to RFC-0003 Part I | RFC-0003 Part II | RFC-0003 |

### 1.3 What exists already

The `core` package (`{__init__,session,state_machine,events,loop,consultation,
replan,recovery}.py`) was scaffolded in Iteration 0 with ownership docstrings
only (blueprint §2). `tests/test_packages.py` already imports and docstring-
checks it; `tests/test_dependency_rules.py` already carries the `core` row =
all packages (allowed) with no `FORBIDDEN["core"]`, and the graph-cycling test
already passes — so the tree/edge tests stay green from C1's first import
onward. The happy path is fixed by `docs/core-execution-walkthrough.md` §2/§3
(the stages ↔ RFC-0002 states table and the seventeen stages) and the failure
oracle by `docs/failure-injection-walkthrough.md` §3 (31 scenarios) and §4
(stress matrix). Baseline: **2530 tests, green**, branch
`iteration/10-providers-skills`, HEAD `557242b` (Iteration 10 closeout), working
tree clean; branch `iteration/11-core` derives from `557242b`.

---

## 2. RFC consistency review

| RFC | Section | Implemented as | Status in layer |
|---|---|---|---|
| RFC-0002 | §0 Purpose | A behavioral spec — no code/interfaces/schemas; `core` is its translation | Consumer (transcribed) |
| RFC-0002 | §1 Session Lifecycle | One serial run: Startup → Idle → goal lifecycle → Outcome → Idle; single-goal; the resume marker is a boundary event (RFC-0014's) | Implemented (C2) |
| RFC-0002 | §2.1–§2.15 States | Each state's purpose, entry/exit conditions, and allowed transitions as pure transition data | Implemented (C1) |
| RFC-0002 | §3 State-machine diagram | Only §2/§4 reachable; the diagram's drawn/implied edges resolve to §2/§4 (Q2) | Implemented (C1; conformance C5) |
| RFC-0002 | §4.1–§4.7 Events | The typed event catalog (operator, machine, provider, plan, execution, verification, system) | Implemented (C1) |
| RFC-0002 | §5 The Session Loop | The 10-step conductor loop; where Executor/Approval/LLM participate | Implemented (C3) |
| RFC-0002 | §6 Component Consultation Rules | When each subsystem is consulted and never consulted | Implemented (C3: `loop` + `consultation`) |
| RFC-0002 | §2.10, §7 Replanning | A first-class state: when, evidence reuse, plan reversal, no carried approval | Implemented (C4) |
| RFC-0002 | §8 Interruption | Cancel / Ctrl+C / provider loss / reboot-request / resume; the theory (I-8, I-14, I-15) | Implemented (C1/C3/C4) |
| RFC-0002 | §9 Invariants 1–15 | The normative suite | Implemented (conformance C5) |
| RFC-0002 | §10 Failure Recovery | Order determinism→disclosure→decision→action; provider/executor/policy/collector | Implemented (C4) |
| RFC-0002 | §11 Open Questions | Each names its owner; not resolved here | Recorded (§9/Q) |
| RFC-0001 | §5 Orchestration Core | The session loop, the decision rules | Implemented (C3) |
| RFC-0001 | §7 untrusted output; §8 gate; §8.1 fail-safe; §8.3 consent | Every action through the gate; degrade; never commands from LLM | Implemented (C3) |
| RFC-0004 | §2 Orchestrator; §4.3 profile | Propose/Refuse/Explain only; routes, never decides | Implemented (C3) |
| RFC-0004 | §7 authority matrix | The Orchestrator row (Observe F, Propose A, Infer F, Verify F, Approve F, Execute F, Refuse A, Persist F, Explain A) | Conformance (C5) |
| RFC-0008 | §5 Approval Unit; §8 Tokens; §11 Re-planning | Plan envelope / one token per Action; class → gate; re-approval on change | Implemented (C3/C4) |
| RFC-0013 | §21/§23 (audit store, runtime writes) | The write points at runtime boundaries; before-consequence doctrine | Implemented (C3/C4; `audit` as recordkeeper) |
| RFC-0009 | SC2–SC4 | Never a secret value in the View/Context/Audit | Consumed (SC4; I-4) |
| RFC-0007 | §10/§11 | Trust classes; sanitize-never-upgrades | Consumed |
| RFC-0012 | §13 View; §7/§21 | The Provider View is the only channel (I-4; PR14); re-assemble, not restore | Consumed (via `context`) |
| RFC-0005/0006 | F-/V- families | The Inspection/Verification wiring | Invoked |
| RFC-0021 | §2/§6 | The machine-identity realm of a session | Invoked |
| RFC-0010/0011 | §§ (consumed) | The two extension axes resolved by `core` per §6 | Consumer (Draft-rework recorded) |
| Walkthroughs | execution §2/§3; failure §3/§4 | The two conformance oracles for C5 | Oracle |

**Resolved by the corpus (not re-opened here):**

- **The Orchestrator profile** (RFC-0004 §4.3): Propose (owns the Plan), Refuse
  (may halt the session), Explain (presents status and Evidence). It trusts the
  Fact Layer (Facts), the Policy Engine (classification), and the Audit System
  (record); it distrusts Provider output and Skill output "until processed and
  classified." It may decide only when to consult which component, whether a Plan
  is complete/coherent enough to present, whether to replan, and whether to halt
  on a Failed invariant; it may never decide Facts, risk classification,
  approval, what to execute, or that Verification passed. Not a question.
- **The reachable transition set.** RFC-0002 §0: the diagram "is normative to
  the extent it matches §§2 and 4; where a drawn edge is ambiguous, the written
  definitions in §§2 and 4 win." The set to build is exactly the "Allowed
  transitions" lists of §2.1–§2.15, plus the §3 shortcut box (OP_CANCEL →
  Cancelled from any non-terminal state; OP_INTERRUPT → Interrupted/Awaiting
  Input, second press → END; ACTION_TIMEOUT / ACTION_INTERRUPTED → Interrupted;
  provider loss with no fallback → degraded mode → Awaiting Input; approved
  REBOOT → write resume marker → END; STATE_CHANGED_DETECTED → invalidate facts
  → Machine Inspection), plus the noted *Verification → Executing (next approved
  step)* edge of §2.9. Nothing else is reachable (Q2).
- **Every execution passes the gate** (I-1; RFC-0004 A3; RFC-0008 §5/§8): the
  one path from a Proposal to the machine is classify → gate → token →
  re-validate → Executor (I-11); no background mode, no implied consent
  (RFC-0008 §4), no auto-rollback (RFC-0002 §10), no auto-retry of a failed step
  (RFC-0008 §11). Not a question.
- **The LLM is only ever consulted through a Provider View** (I-4; RFC-0010
  §3/PR14), after a fresh Context Building (RFC-0002 §6), never with raw output
  or secrets. Its instantiation is Q9.
- **Provider and Skill output are untrusted until processed and classified**
  (RFC-0004 §4.3; RFC-0001 §7; I-7): `core` routes what they propose, never
  executes it, never verifies with it, never classifies by it. Not a question.
- **Verification always follows execution** (I-2, I-14): no terminal outcome
  over an unknown state; no unverified success. Not a question.
- **Failure recovery is a fixed order** — determinism, then disclosure, then
  decision, then action (RFC-0002 §10); provider failure degrades, never
  fabricates (I-9; PR16). The no-I/O mechanics are Q6.
- **The audit is before the consequence** (RFC-0013 §23; I-13; AU8), never
  edited; the writer placement at each boundary is Q4.
- **The session is single-goal and serial** (RFC-0002 §1); anything beyond that
  is §11 OQ 10/15. Not a question.

---

## 3. Layer placement

`core` is **Layer 6** (blueprint §4.1), directly above `providers`/`skills`
(Layer 5) and below only `cli` (Layer 7). It imports all lower layers and is
imported only by `cli`. Blueprint §4.2's `core` row forbids nothing structurally
— "must never *re-implement* a forbidden authority (e.g. classify, verify,
approve); it routes (RFC-0002 §5; RFC-0004 §4.3)" — so the C5 conformance
enforces the matrix by **use-restriction** rather than by import for this single
package.

- **`core → context`**: the Provider View edge. `core` orders Context Building
  and consumes the View type built by `context` (Iteration 9), enforcing I-4
  (the LLM gets only the View) and the cat-9 context-boundary write (I-13).
- **`core → providers` / `skills`**: the consultation edges. Consulted per §6
  (Provider in Diagnosis/Planning/Replanning; Skill in Diagnosis/Planning/
  Machine Inspection); every Proposal that returns is routed into
  classification. This is where the two extension axes meet the conductor
  (RFC-0001 §11).
- **`core → policy`**: classification of every proposed Action (the Planning →
  Awaiting Approval edge) and token re-validation (the Awaiting Approval →
  Executing edge; RFC-0008 §6/§8) — without `core` itself classifying (I-7).
- **`core → executor`**: run the Action in Executing, only under a re-validated
  token (RFC-0002 §2.8; RFC-0004 §4.9).
- **`core → audit`** (and `secrets` metadata): the record at the boundaries
  (RFC-0013; SC4 — never a secret value).
- **`core → factlayer` / `verification`**: re-order the re-inspection and the
  Compare; `core` never computes a Fact and never produces an Outcome.
- **No `core → cli`** edge; **no `core →` real I/O** (vendor/skill/sandbox/
  resume/watchdog I/O is injected and reserved for RFC-0014/0020).

**Behavioral conformance surface (C5).** `core`'s authority cell set is tested
by `test_core_authority`: `core` never invokes classification, verification,
approval, or execution logic of its own; it only routes to the owned entry
points of `policy`/`verification`/`executor`. This is the enforcement machinery
for I-1, I-7, I-11, I-12 and the §8 authority table.

---

## 4. Ownership map

The Orchestrator *authority* (RFC-0004 §4.3) and the *behavioral contract*
(RFC-0002 §§1–§10) are two properties of one package, each with one owner
(blueprint §10's two-owner check). Module ownership:

| Module | Owning RFC sections | Protected by |
|---|---|---|
| `core/session.py` | RFC-0002 §1, §2.1–§2.2, §4.1; RFC-0013 §7 | single-goal, serial; the goal-adoption and outcome records; outcome → Idle only |
| `core/state_machine.py` | RFC-0002 §2, §3, §4 | only §2/§4 transitions; I-8, I-14, I-15; the impossible-transition table (walkthrough §6.1) |
| `core/events.py` | RFC-0002 §4 | the §4.1–§4.7 catalog; every consequential event audited before its effect (I-13) |
| `core/loop.py` | RFC-0002 §5 | the 10-step loop; where the Executor/Approval/LLM participate; the conductor |
| `core/consultation.py` | RFC-0002 §6 | the consult matrix (consulted vs never); the fresh-Context-Building rule (Q9) |
| `core/replan.py` | RFC-0002 §2.10, §7 | §7's reuse/revise/re-present rules; I-6 |
| `core/recovery.py` | RFC-0002 §8, §10 | the fixed order; provider-failure reaction; partial execution; I-8/I-15 |
| `audit` (invoked) | RFC-0013 §21/§23 | the record at the boundaries; metadata-only (SC4) |

**Authority table (RFC-0004 §7, Orchestrator row).** Observe **F**, Propose **A**,
Infer **F**, Verify **F**, Approve **F**, Execute **F**, Refuse **A**, Persist
**F**, Explain **A**. `core` decides *routing* (when to consult which component,
whether a Plan is presentable, whether to replan, whether to halt on a Failed
invariant) and *refusal*; everything else is delegated and unreachable from its
own code (C5).

**Two-owner checks.** (a) *Authority vs contract:* RFC-0004 §4.3 owns the
authority; RFC-0002 owns the states/events/recovery — two properties, one owner
each. (b) *The runtime-boundary audit write vs the record:* `core` writes
(RFC-0013 §2; the write points are runtime boundaries, §23), the `audit` package
owns the record's append-only integrity and non-editability (RFC-0013 §21) — Q4.
(c) *Provider-failure reaction vs selection:* `core` runs the reaction (RFC-0002
§10); RFC-0016 owns the *selection* of the fallback chain (RFC-0010 §15 OQ1) —
recorded, not implemented (Q6).

---

## 5. Dependency analysis

The allowed set is `core = {all packages}` (blueprint §4.1); the import test
already sanctions it. The one edge to *forbid* on purpose is "besides `cli`,
nothing may import `core`" — asserted by the C5 AST test and consistent with
blueprint §4.1 (`cli` = {core, audit, context, schema}).

**Use-limits, not import-limits.** Because `policy`, `executor`, `verification`,
`factlayer`, `secrets`, and `audit` are all *allowed* for `core`, the §4.2
"never re-implement" doctrine is enforced behaviorally (C5): every call `core`
makes on those packages goes through their public, owner-named entry points
(`policy.classify`, `policy.validate_token`, `executor.run`, `verification.
compare`, `factlayer.inspect`, `audit.append`) and never "calls around" them.

**The conductor edges that become live.** `core → providers`, `core → skills`,
and `core → context` were recorded as deferred obligations in Iterations 9–10;
this iteration wires them. Their use is consultation-only, with the View-only
rule (I-4) and the no-downstream-leak rule (I-5) enforced at the seam. The
injected `provider_reply`/`skill_plan`/`executor_run` facades exist only in the
tests (DN-55 precedent); production `core` files perform no I/O.

---

## 6. Public surface analysis

Reported, not ratified — final signatures are RFC-0020's (DN-1). The C1–C4 shapes:

- `core/session.py` — `start` (initialization prerequisites), `stop`, the
  one-goal lifecycle; `adopt_goal` (with its record, I-13); the outcome
  terminals → Idle.
- `core/state_machine.py` — a pure transition table: each state's "Allowed
  transitions" of §2; a `permitted(from, to)` predicate; `evolve(state, event)`
  → the new state or a refusal; the §3 shortcut edges and the Verification →
  Executing (next step) edge of §2.9.
- `core/events.py` — the typed §4 catalog with a per-event dispatch so the
  event → transition relation is declared once; the transition-less,
  information-only events (OP_VIEW, ACTION_STARTED, ACTION_CLASSIFIED) emit
  audited notes and change no state.
- `core/loop.py` — the 10-step conductor; the injection points (`inspect`,
  `assemble`, `provider_reply`, `skill_plan`, `classify_and_gate`, `run_executor`,
  `verify`, `record`); it is the only surface a provider reply or Skill Proposal
  ever passes on its way toward an action path.
- `core/consultation.py` — the §6 rules as data (consulted vs never; the LLM-
  only-after-fresh-Context-Building rule; the Skill/Collector when).
- `core/replan.py` — the §7 rule set; `replan` decides targeted revision vs
  rebuild and forces re-approval (I-6).
- `core/recovery.py` — the deterministic ordering; `on_provider_failure`,
  `on_action_failure`, `on_collector_failure`, `on_policy_failure`, `on_partial`.

The surface is deterministic, I/O-free (injected), serial, and authority-
bounded; it adds no authority cell beyond RFC-0004's Orchestrator grant.

---

## 7. Boundary analysis

- **The machine-safe seam.** Provider-derived objects (a reply, a Skill
  Proposal/Plan) are never converted to a command by `core`; an Action exists
  only as the normalized Proposal → classification → token → the Executor (I-5).
  A C5 test asserts no provider string can reach the `executor` seam.
- **The right to degrade.** `providers.PROVIDER_FALLBACK_FAILED` → degraded mode:
  `core` discloses and presents facts-only, with no recommendations (RFC-0002
  §8/§10; RFC-0010 PR16; I-9), as an Awaiting Input transition.
- **Audit before consequence.** Each boundary (goal adoption, proposal,
  classification, approval/override, execution start/end, verification outcome,
  provider/Skill event) writes its record via `audit` before the consequence; a
  failed write blocks and is disclosed (I-13; AU8).
- **TOCTOU.** The Awaiting Approval → Executing edge re-validates the token
  against the injected current state and current policy (RFC-0008 P9; I-11); the
  token is scoped, consumable, and never reused (Q5).
- **Hold vs halt.** Awaiting Input keeps the goal alive and routes replies by the
  outstanding-question table (context-routing, RFC-0002 §2.11); a reply that
  implies the machine changed re-enters Machine Inspection before any decision.
- **Secret seam.** The `audit` records metadata only (SC4); the View is
  assembled secret-free by `context` (SC2/SC3); `core` never routes a secret
  outward.

---

## 8. Required invariants

Blueprint §7 makes `core` the *enforcer* of the whole 1–15 set; the §8.11 DoD is
all fifteen. The table records the source, `core`'s method, and the lower-layer
machinery owner (recorded where the machinery lives, not a deferral).

| Invariant | Normative source | `core`'s method | Machinery owner |
|---|---|---|---|
| I-1 — No execution without approval | RFC-0002 §9; RFC-0004 A3 | The only path to `executor` is classify → gate → token → re-validate | `policy`, `executor` |
| I-2 — Verification always follows execution | RFC-0002 §9 | Executing's only non-halt exits are toward Verification | `verification` |
| I-3 — Planning/Diagnosis/Replanning execute nothing | RFC-0002 §9 | The loop never runs an Action in the cognitive states | `executor` (gate) |
| I-4 — LLM only through a Provider View | RFC-0002 §9; RFC-0010 PR14 | The consultation rule + View-only seam | `context`, `providers` |
| I-5 — No untrusted text interpolated into a command | RFC-0002 §9 | Actions are sanctioned structures, never shell strings | all |
| I-6 — Deviation requires fresh approval | RFC-0002 §9; RFC-0008 §11 | Replan re-presents; no carried approval | `policy` |
| I-7 — Risk classification deterministic, never LLM self-report | RFC-0002 §9 | `core` never classifies; `policy` does (C5) | `policy` |
| I-8 — Any halt → re-assessment | RFC-0002 §9, §10 | Interrupt/timeout/partial → re-inspect before continue | `factlayer` |
| I-9 — The runtime never fabricates | RFC-0002 §9 | Degraded/partial/unknown are disclosed, never filled | `audit` |
| I-10 — Facts carry provenance and expire | RFC-0002 §9 | Only fresh, attributed facts are consumed | `factlayer` |
| I-11 — Tokens scoped and consumable | RFC-0002 §9; RFC-0008 §8 | Boundary re-validation; consume by use/expiry/state change | `policy`, `audit` |
| I-12 — Blocked action only via audited override | RFC-0002 §9 | OP_OVERRIDE mints a fresh, recorded approval | `policy`, `audit` |
| I-13 — Audit written before the consequence | RFC-0002 §9; RFC-0013 §23 | Boundary writers; fail-closed | `audit` |
| I-14 — No terminal outcome while in flight | RFC-0002 §9 | Completed/Failed/Cancelled only after Verification or a verified halt | `verification` |
| I-15 — No standing authorization across a boundary | RFC-0002 §9 | Every boundary (reboot, exit, interrupt, reload) clears approvals | `policy` |
| AU8 — A failed write blocks and is disclosed | RFC-0013 §21 | Write failure → block the consequence, tell the Operator | `audit` |

The C5 invariant suite runs each invariant in **every** reachable state, per the
RFC-0002 §9 preamble ("hold at all times, in every state, without exception").

---

## 9. Ambiguities

Each is reported, not resolved; each names the corpus silence that forces the
report and the owner that answers it. "Blocking?" marks whether it elevates to a
blocking question in §10.

| # | Subject | RFC §/location | Open question | Alternative readings | Owner | Blocking? |
|---|---|---|---|---|---|---|
| A1 | Iteration scope / renumbering | blueprint §8.11; DN-45 | Blueprint §8.11 reads "Iteration 10 — `core`" while DN-45 and the closeouts place `core` at Iteration 11. | (a) implement at Iteration 11, recording the supersession (b) stop and renumber the blueprint | DN-45; blueprint §8.11 | **Yes (Q1)** |
| A2 | The reachable transition set | RFC-0002 §0, §2, §3 | The diagram is normative only where it matches §§2/4. Which edges are the definitive set for conformance? | (a) the §2.1–§2.15 "Allowed transitions" lists + the §3 shortcut box + the §2.9 next-step edge; nothing else (b) also ratify the diagram's drawn edges verbatim | RFC-0002 | **Yes (Q2)** |
| A3 | The event-set fidelity | RFC-0002 §4 | Some §4 events (OP_VIEW, ACTION_STARTED, ACTION_CLASSIFIED) are described as informational. Is the catalog a uniform type set? | (a) all §4.1–§4.7 events are typed; the informational ones emit audited notes and change no state (b) model only transition-bearing events | RFC-0002 | **Yes (Q3)** |
| A4 | The audit writer at the runtime boundary | RFC-0013 §2/§21/§23; RFC-0004 §9.11 | RFC-0013 §23 names the write points but not who invokes them; Iteration 9 recorded "the cat-9 audit write is `core`'s." | (a) `core` co-locates the write at each boundary, receiving emitted boundary events from the lower packages (which never write) (b) each lower package writes its own records | RFC-0013; RFC-0002 I-13 | **Yes (Q4)** |
| A5 | The token re-validation input | RFC-0002 §2.8; RFC-0008 P9 | "Re-validated at the execution boundary" — against what, exactly? | (a) the token's declared preconditions vs the injected current machine snapshot and current policy (b) a token-validity check alone | RFC-0008; RFC-0002 | **Yes (Q5)** |
| A6 | No-I/O retries | RFC-0002 §4.3, §10 | Provider retry-with-backoff and fallback involve waiting and timing, i.e. I/O. How does an I/O-free `core` run them? | (a) a pure, bounded reducer over injected failure/time events, with the back-off value as data; no clock import (b) real sleeping in `core` | RFC-0002; DN-55 | **Yes (Q6)** |
| A7 | Degraded-mode scope | RFC-0002 §11 OQ 11; RFC-0011 §20 | What may a facts-only session do without a provider? | (a) baseline inspection, raw Facts presentation, and deterministic (non-LLM) Skills; no recommendations (b) raw Facts only | RFC-0002/RFC-0020 | **Yes (Q7)** |
| A8 | Phase-budget/timeout semantics | RFC-0002 §11 OQ 2/3 | No concrete budgets exist. Does `core` model timeouts at all? | (a) a deadline is an injected primitive; TIMEOUT becomes a core event with its §4.7 reaction; numeric bounds to RFC-0020 (b) omit timeouts | RFC-0002/RFC-0020 | **Yes (Q8)** |
| A9 | The "fresh Context Building" rule | RFC-0002 §6 | "Only after a fresh Context Building" — fresh per consultation? | (a) every cognitive consult re-enters Context Building with the current facts unless the immediate previous CB already covered them (b) one CB per cognitive phase | RFC-0002 | **Yes (Q9)** |
| A10 | Loop testability at zero I/O | blueprint §7; walkthrough oracles | The DoD demands a full-loop integration test and the 31-scenario mirror, but `core` is I/O-free. | (a) inject deterministic fake provider/skill/executor responders in the tests (b) build a real adapter now | DN-55; blueprint §7 | **Yes (Q10)** |

---

## 10. Blocking questions

| Q | Question | Owner (RFC §) | Blocks | Sev. | Recommended resolution |
|---|---|---|---|---|---|
| Q1 | Iteration scope / renumbering (A1) | DN-45; blueprint §8.11 | C0 | Med | **`core` is Iteration 11.** Implement per DN-45's re-order; record the supersession of the §8.11 label (as §8.7–§8.10 were); the blueprint text stands until RFC-0020 |
| Q2 | The reachable transition set (A2) | RFC-0002 §0/§2/§3 | C1 | High | **Text wins.** The set is the §2.1–§2.15 "Allowed transitions" lists + the §3 shortcut box + the §2.9 next-step edge; the diagram defers to §§2/4; nothing else is reachable |
| Q3 | The event-set fidelity (A3) | RFC-0002 §4 | C1 | High | **The full catalog.** All §4.1–§4.7 events exist as types; the informational ones (OP_VIEW, ACTION_STARTED, ACTION_CLASSIFIED) emit audited notes and change no state |
| Q4 | The audit writer (A4) | RFC-0013 §23; RFC-0002 I-13 | C3/C5 | High | **`core` writes at the boundary.** Lower packages emit deterministic boundary events; `core` (the session owner) invokes `audit` before the consequence, metadata-only, fail-closed (AU8); satisfies the recorded cat-9 write |
| Q5 | Token re-validation (A5) | RFC-0008 P9; RFC-0002 §2.8 | C3 | Med | **Snapshot + policy.** Re-validate the token against its declared preconditions and the injected current machine state plus current policy (P9; I-11) |
| Q6 | No-I/O retry/fallback (A6) | RFC-0002 §4.3/§10; DN-55 | C4 | High | **Pure reducer.** Retry/backoff/fallback is a bounded sequence over injected events with back-off as data; no clock import in `core`; the fallback-chain *selection* is RFC-0016's |
| Q7 | Degraded-mode scope (A7) | RFC-0002 §11 OQ 11; RFC-0011 §20 | C3 | Med | **Facts-only + deterministic tools.** Baseline inspection, raw Facts, and deterministic (non-LLM) Skills run; no recommendations (I-9); the product-vs-fallback scope to RFC-0019 |
| Q8 | Timeout/budget events (A8) | RFC-0002 §11 OQ 2/3 | C1/C3/C4 | Med | **Injected deadlines.** A deadline is a primitive; TIMEOUT is a core event with the §4.7 reaction (cognitive → disclose; machine → Interrupted); numeric bounds to RFC-0020 |
| Q9 | Fresh Context Building (A9) | RFC-0002 §6 | C3 | Med | **Re-enter before each consult.** A cognitive consultation is allowed only when the current Provider View covers the current facts; otherwise re-enter Context Building first |
| Q10 | Loop testability (A10) | blueprint §7; DN-55 | C5 | Low | **Fake deterministic responders.** The integration suite injects deterministic provider/skill/executor responders; no production I/O anywhere |

**Status: BLOCKED.** Q1–Q10 await Operator ratification. Once ratified each is
recorded as **DN-85…DN-94** in `docs/implementation-decision-notes.md` before
C0, exactly as Iterations 1–10; the design review §16 readiness flips to READY.

---

## 11. Proposed Decision Notes (DN-85…DN-94)

Proposals for Operator ratification; none took effect by this review. To be
ratified in the established table form (Status / Date / Resolves / Grounding /
Embodied in / Decision), mirroring DN-1…DN-84.

| DN | Resolves | Proposal |
|---|---|---|
| DN-85 | Q1 | `core` executes at Iteration 11 per DN-45's re-order; the blueprint §8.11 "Iteration 10 — `core`" label is superseded and stands until RFC-0020 |
| DN-86 | Q2 | The transition set is exactly the §2.1–§2.15 "Allowed transitions" lists + the §3 shortcut edges + the §2.9 next-step edge; the diagram defers to §§2/4; nothing else is reachable |
| DN-87 | Q3 | All §4.1–§4.7 events exist as typed events; the informational ones (OP_VIEW, ACTION_STARTED, ACTION_CLASSIFIED) are audited notes with no state change |
| DN-88 | Q4 | `core` is the single runtime writer at every boundary (goal, proposal, classification, approval, override, execution, verification, outcome, provider/skill/context events); it invokes `audit` before the consequence, metadata-only, fail-closed (AU8) |
| DN-89 | Q5 | At the Awaiting Approval → Executing edge the token is re-validated against its declared preconditions and the injected current machine state and policy (P9; I-11) |
| DN-90 | Q6 | Provider retry/backoff/fallback is a pure bounded reducer over injected events; back-off is data, never a sleep; no clock import in `core`; the chain's selection is RFC-0016's |
| DN-91 | Q7 | Degraded mode is facts-only with deterministic (non-LLM) Skills; no recommendations (I-9); the product-vs-fallback scope remains RFC-0019's |
| DN-92 | Q8 | Timeouts are injected-deadline primitives; TIMEOUT is a core event with the §4.7 reaction; numeric budgets are RFC-0020's |
| DN-93 | Q9 | Every cognitive consultation requires a fresh Provider View over the current facts; otherwise Context Building is re-entered first |
| DN-94 | Q10 | The loop's integration tests inject deterministic fake provider/skill/executor responders (DN-55); production `core` files perform no I/O |

---

## 12. Atomic implementation plan

Each commit is <300 production LOC, single responsibility, test-visible, on a
branch derived from `557242b` (`iteration/11-core`). Commit order follows
ratification of the questions it depends on. C1–C4 **fill** the seven
Iteration-0 scaffolds (`session`, `state_machine`, `events`, `loop`,
`consultation`, `replan`, `recovery` — already present with ownership
docstrings; the tree test stays green); C5 enforces the layer's conformance; C6
closes the record.

| Commit | Message | Content | Est. (impl/test) | Depends on | Deliverable |
|---|---|---|---|---|---|
| C0 | `docs: ratify Iteration 11 questions Q1–Q10 and core scope` | Decision notes for Q1–Q10 (DN-85…DN-94), design review record, renumbering note (Q1), consistency-report note | — / — / ~800 | Q1–Q10 ratified | Ratified plan; all questions answered |
| C1 | `feat(core): the RFC-0002 state machine and event model (RFC-0002 §2, §3, §4; RFC-0013 §7)` | `state_machine.py`: the fifteen states, the §2 "Allowed transitions" as a pure table, `permitted`/`evolve`, the §3 shortcut edges, the §2.9 next-step edge; `events.py`: the typed §4.1–§4.7 catalog, per-event dispatch, the audited information-only events (Q3), the deadline event (Q8) | ~270 / ~330 | Q2, Q3, Q8 | State/event model |
| C2 | `feat(core): session lifecycle and goal adoption (RFC-0002 §1, §2.1–§2.2, §4.1; RFC-0013 §7)` | `session.py`: start (prerequisite checks), the single-goal serial lifecycle, goal adoption with its record (I-13), the outcome terminals → Idle | ~230 / ~320 | Q2 | Session lifecycle |
| C3 | `feat(core): the session loop, consultation router, and gate wiring (RFC-0002 §5, §6; RFC-0008 §5/§8; RFC-0004 A3)` | `loop.py` + `consultation.py`: the 10-step conductor, the provider/skill consult rules and the fresh-View rule (Q9), the classify → gate → token → re-validate → Executor path (I-1/I-11), the audit writes at the boundaries (Q4), degraded-mode reaction (Q7) | ~300 / ~380 | Q4, Q5, Q7, Q9 | The conductor |
| C4 | `feat(core): replanning and failure recovery (RFC-0002 §2.10, §7, §8, §10)` | `replan.py`: when to replan, provenance-reuse rules, targeted revision vs rebuild, re-normalize/re-classify/re-present, no carried approval (I-6); `recovery.py`: the determinism→disclosure→decision→action order; provider-failure reducer (Q6); executor/collector/policy failures; partial execution; interruption | ~280 / ~330 | Q6, Q8 | Replanning + recovery |
| C5 | `test(core): Layer-6 conformance, invariants 1–15, authority, and walkthrough integration` | the reachable-transition suite (Q2), the invariant suite run in every state, the impossible-transition table (walkthrough §6.1), the authority/use-limit suite (I-1/I-7/I-11/I-12), imports conformance (only `cli → core`); the full-loop happy path mirrors `core-execution-walkthrough.md` §2/§3 (17 stages) and all 31 scenarios mirror `failure-injection-walkthrough.md` §3, each ending at its core transition/record, with injected fake responders (Q10) | 0 / ~620 | C1–C4 | Conformance oracle |
| C6 | `docs: record Iteration 11 completion and core conformance` | Consistency report + decision notes completion + deferred-items table | — / — / ~220 | C5 | Completion record |

---

## 13. Validation strategy

Same gates as Iterations 1–10: `pytest` (baseline **2530 tests**), `ruff check`,
`ruff format --check`, `python -m build`, `pre-commit run --all-files`.
Because the allowed graph is already correct, the new conformance tests add:

- `test_core_imports.py` — `core` imports only sanctioned packages; only `cli`
  imports `core` (AST).
- `test_core_state_machine.py` — every applied transition is a §2/§4 edge; every
  "Allowed transitions" list is reachable.
- `test_core_invariants.py` — I-1…I-15 and AU8 run in every reachable state
  (the RFC-0002 §9 preamble).
- `test_core_authority.py` — `core` never invokes classification/verification/
  approval/execution logic itself (the §4.2 "never re-implement" doctrine);
  authority cells per RFC-0004 §7.
- `test_core_loop.py` (C5) — the full-loop and 31-scenario integration with the
  injected deterministic responders (Q10).

Determinism is asserted by property-style tests (same input → same transitions,
RFC-0007 S7); the I/O-free posture is conformance-enforced (no clock, no
network, no filesystem, no subprocess imports in `core`; DN-55). Because C0–C6
touch neither `rfc/` nor `tools/`, the RFC-reference validator is not a gate for
this iteration (CI still runs it; the pre-existing RFC-0004 §470 `'S1'` error is
unrelated and unchanged).

---

## 14. Definition of Done (per commit)

| Commit | Definition of Done |
|---|---|
| C0 | Q1–Q10 each answered and recorded as decision notes (DN-85…DN-94); the renumbering tension (Q1) recorded; this review's readiness flips to READY |
| C1 | `state_machine.py` permits exactly the §2.1–§2.15 transition sets + the §3 shortcut edges + the §2.9 next-step edge (Q2); any other transition is refused; I-8/I-14/I-15 hold in every reachable state; `events.py` exposes the full §4.1–§4.7 catalog (Q3); every consequential event is audited before its effect (I-13); the informational events change no state |
| C2 | `session.py` implements the single-goal, serial lifecycle; goal adoption writes its record before the consequence (I-13); the outcome terminals lead only to Idle; no parallel goal |
| C3 | `loop.py` + `consultation.py` run the 10-step loop with injected responders; the LLM is consulted only through a fresh Provider View (I-4; Q9); the only path to the Executor is classify → gate → token → re-validate (I-1/I-11); the boundary audit writes precede the consequence (I-13; Q4); degraded mode is facts-only with no recommendations (I-9; Q7) |
| C4 | `replan.py` reuses facts only when their provenance is still valid, decides targeted revision vs rebuild, re-normalizes/re-classifies/re-presents, and carries no approval across a changed plan (I-6); `recovery.py` applies the determinism→disclosure→decision→action order; provider failure degrades via the bounded pure reducer (Q6); executor/collector/policy failures fail closed or re-assess (I-8); partial execution is accounted honestly; the runtime never fabricates (I-9) |
| C5 | Every invariant 1–15 (and AU8) has a test that runs in every reachable state; the reachable set is exactly the Q2 set; the impossible-transition table passes; the authority/use-limit suite passes; the full-loop integration test mirrors `core-execution-walkthrough.md` §2/§3; all 31 scenarios mirror `failure-injection-walkthrough.md` §3, each ending at its core transition/record; no production I/O in any `core` file; full suite green |
| C6 | Consistency report reflects Iteration 11; no orphaned decision notes; the deferred-items table names every owner |

**Overall DoD (blueprint §8.11):** state-machine conformance (only §2/§3/§4
transitions reachable); invariants 1–15 hold in every state; recovery ordering is
determinism→disclosure→decision→action; the full-loop integration test mirrors
the execution walkthrough and the 31 failure scenarios mirror the failure
walkthrough; `pytest`, `ruff check`, `ruff format --check`, `python -m build`,
and `pre-commit` all green; the tree and edges unchanged.

---

## 15. LOC estimates

| Commit | impl | test | docs | Notes |
|---|---|---|---|---|
| C0 | — | — | ~800 | Ratification |
| C1 | ~270 | ~330 | — | State machine + event model |
| C2 | ~230 | ~320 | — | Session lifecycle |
| C3 | ~300 | ~380 | — | Loop + consultation + gate wiring |
| C4 | ~280 | ~330 | — | Replanning + recovery |
| C5 | 0 | ~620 | — | Conformance + invariants + walkthrough mirror |
| C6 | — | — | ~220 | Closeout |
| **Total** | **~1,080** | **~1,980** | ~1,020 | |

Production total ≈ **1,080**; test total ≈ **1,980**. Test LOC exceeds the
300-LOC cap per-commit, as in Iterations 3–10 (the cap applies to implementation
lines). C1 (state machine + event model) and C3 (loop + gate wiring) carry the
conformance weight (the reachable-set oracle and I-1/I-4/I-11/I-13); C4 carries
recovery (I-8/I-9/I-15); C5 is the invariant/authority/walkthrough oracle.

---

## 16. Readiness assessment

**Status: BLOCKED** pending ratification of Q1–Q10 (to be recorded as decision
notes DN-85…DN-94 before C0), exactly as Iterations 1–10 began. The
highest-leverage questions are **Q2** (the reachable transition set that fixes
the conformance oracle), **Q4** (the audit-writer seam that satisfies I-13),
**Q6** (the no-I/O provider-reaction reducer), and **Q9** (the fresh-View rule
that makes I-4 hold). Once Q1–Q10 are ratified, the layer is **READY** and
commits execute in order C0→C6, each satisfying its §14 DoD before the next
begins. The dominant residual risk is broader but unchanged in kind from Iteration
10 — the Draft status of RFC-0005…RFC-0013 and RFC-0021, of which `core`
transcribes RFC-0008 (the approval-token discipline) and RFC-0013 (the audit
write points) most heavily — and is bounded by the scaffold posture and by the
fact that `core`'s load-bearing spine is Accepted (RFC-0001, RFC-0002,
RFC-0004; the RFC-0002 §1–§10 basis of blueprint §8.11).

---

## 17. Final verdict

This plan is a faithful translation of the frozen corpus into the core-loop
scaffold: **no new architecture is proposed** — no new state, no new event, no
new authority. Every piece it builds is the corpus's own: the RFC-0002 §2/§3/§4
states, transitions, and events; the RFC-0004 §4.3 Orchestrator profile; the
RFC-0008 gate and token discipline; the RFC-0013 write points; the RFC-0001 §5
decision rules; the §10 recovery ordering. Every ambiguity the corpus leaves —
the transition-set fidelity, the event-set fidelity, the audit-writer seam, the
token re-validation input, the no-I/O retry mechanics, the degraded-mode scope,
the timeout semantics, the fresh-View rule, and the testability of an I/O-free
loop — is elevated to a blocking question (Q1–Q10) for ratification rather than
resolved here. The inherited Iteration 5–10 `core`-ward obligations (the
consultation wiring, the gate routing, the audit writes at the boundaries, the
provider-failure reaction, the provider-world/machine-world separation) are now
Definition of Done items, not deferred again. The parts whose concrete I/O or
durable surfaces do not exist yet — resume persistence, phase budgets, the
watchdog, multi-goal, real adapters/sandbox, the TUI — are named against
RFC-0014/RFC-0015/RFC-0020 in §1.2, never dropped. **Pending ratification:
Q1–Q10 are to be recorded as DN-85…DN-94; the layer is READY for C1.**

---

## Consistency review against the Blueprint and governing RFCs

**Consistent.** Module set `core/{__init__,session,state_machine,events,loop,
consultation,replan,recovery}.py` fixed by blueprint §2 (scaffolds already
present); the dependency rule `ALLOWED["core"] = {all packages}` and the
"only `cli` imports `core`" inversion honored (§3/§5); the RFC-0004 §7
Orchestrator row honored by §4 and the C5 authority suite; one-owner discipline
honored by the two-owner checks (authority vs contract; the audit write vs the
record; the provider-failure reaction vs RFC-0016's selection); blueprint §8.0's
scaffold gate stands; DN-45's re-order is continued (`core` = Iteration 11);
DN-55's injected-primitive precedent is the Q6/Q8/Q10 reading; DN-70/DN-71's
cat-9 context-boundary write is a DoD item (Q4); RFC-0013 §23's write points are
transcribed (§2/§7); RFC-0001 §5's Orchestration Core responsibility set is the
layer's charter; the two walkthroughs define the C5 oracle.

**Reported tensions (not violations):**

1. Blueprint §8.11 numbering vs DN-45's re-order — §8.11 still reads "Iteration
   10 — `core`" while this iteration implements it at Iteration 11 (Q1), exactly
   as §8.10's label was superseded at Iteration 10.
2. RFC-0005…0013 and RFC-0021 are Draft — `core` transcribes two of them heavily
   (RFC-0008, the approval-token discipline; RFC-0013, the audit write points),
   so the rework risk is here wider than in Iterations 9–10; it is accepted under
   the same posture and bounded by the Accepted spine (RFC-0001, RFC-0002,
   RFC-0004).
3. RFC-0013 §2's "every record is written at a boundary by the component whose
   consequence it precedes" vs the Iteration-9 record "the cat-9 audit write is
   `core`'s" — reconciled by Q4: the lower packages emit boundary events, `core`
   (as the session owner) invokes the write at the consequence, satisfying both
   the boundary doctrine and the recorded ownership.
4. RFC-0008's plan-as-envelope vs the per-change re-approval — resolved by the
   corpus itself (RFC-0002 §2.8/§4.5: approved steps continue under the same
   envelope, deviation re-presents; RFC-0008 §11), recorded here, not reopened.

**Verdict.** This plan is a faithful translation of the frozen corpus into the
core-loop scaffold; no new architecture is proposed, and every ambiguity the
corpus does not decide is elevated to a blocking question for ratification rather
than resolved here.

*End of design review. To be ratified as DN-85…DN-94 before C0.*
