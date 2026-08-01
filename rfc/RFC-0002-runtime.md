# RFC-0002 — Runtime Architecture and Session State Machine

**Status:** Accepted
**Date:** 2026-08-01
**Scope:** Runtime behavior during a live troubleshooting session
**Audience:** Future maintainers
**Supersedes:** Nothing
**Depends on:** RFC-0001 (accepted)

---

## 0. Preamble

This RFC specifies how the Assistant behaves *while it is working*: the states a
session can be in, the events that move it between states, the order in which
subsystems participate, and the invariants that hold at every instant. It is a
**behavioral** specification. It deliberately contains no code, no interfaces, no
data schemas, and no directory structure.

It is written for the people who will later specify and implement the runtime.
Where this document conflicts with RFC-0001, RFC-0001 wins and this document must
be amended through the RFC process.

Terminology follows RFC-0001: **Assistant** and **Operator**. Additional concepts
introduced here:

- **Goal** — a single troubleshooting objective the Operator has asked the
  Assistant to pursue. A session holds exactly one goal at a time (see Open
  Questions for the confirmation of this stance).
- **Provider view** — the sanitized, purpose-limited, size-bounded, secret-free
  representation of facts, history, and goal that is the *only* thing an LLM
  ever receives (RFC-0001 §7 rule 4).
- **Approval token** — the durable record that the Operator approved a specific,
  risk-classified action. It is scoped (to the action, the time, and the machine
  state it was approved against) and consumable.
- **Mode** — the runtime is either **online** (a provider is usable) or
  **degraded** (no provider; facts-only). Modes cut across states; they are not
  states themselves.
- **Resume marker** — a durable note that a session ended mid-goal (reboot,
  crash, or exit) so it can be resumed safely.

Reading note: Sections 2, 3, and 4 are normative. The diagram in §3 is normative
to the extent it matches §§2 and 4; where a drawn edge is ambiguous, the written
definitions in §§2 and 4 win.

One conceptual frame governs everything: **the AI talks, the tool gathers facts,
the user approves actions** (RFC-0001 §3.12). Every state below is a point on
that loop.

---

## 1. Session Lifecycle

A session is one continuous run of the Assistant, from startup to exit. Its full
arc:

1. **Startup.** The runtime begins in **Session Initialization**: configuration
   is loaded; providers and skills are resolved and authenticated; the durable
   audit store is opened; the runtime verifies its own prerequisites (elevation
   availability, machine fingerprint, audit writability); and it checks for a
   resume marker. Per RFC-0001 §8 (fail closed), if any safety-critical
   subsystem cannot initialize, the runtime refuses to enter service, reports
   why, and exits.
2. **Rest.** On success the runtime moves to **Idle**: no goal is active, and the
   Assistant waits for the Operator to state a goal, exit, or be told by the
   (read-only) watchdog that the machine changed.
3. **Goal.** Initiating a goal (OP_GOAL) enters the **goal lifecycle** — the
   loop from RFC-0001 §4: *gather → plan → propose → approve → act → verify*.
   - **Machine Inspection** gathers deterministic, read-only facts about the
     machine (a context-free baseline first, targeted diagnostics later).
   - **Context Building** renders facts, history, and goal into a safe provider
     view.
   - **Diagnosis** interprets the evidence, forms hypotheses, and decides the
     next move: more evidence, a clarifying question, or a plan.
   - **Planning** turns a grounded hypothesis into a plan of discrete, discrete
     proposed actions.
   - **Awaiting Approval** is the human gate: the classified plan is presented
     for an explicit decision.
   - **Executing** runs approved actions, one at a time, under the executor's
     guardrails.
   - **Verification** deterministically confirms each change took effect.
   - **Replanning** revises the plan when evidence, decisions, or failures
     require it.
4. **Outcome.** The goal ends in one of three outcomes: **Completed** (verified),
   **Failed** (cannot proceed safely), or **Cancelled** (the Operator abandoned
   it). The runtime returns to Idle, where the Operator may start a new goal or
   exit.

Two states exist to protect the "never assume — verify" principle and have no
obvious counterpart in the list a casual reader would write:

- **Awaiting Input** — an active goal paused on a *free-text* question (a
  clarification, a choice, an acknowledgment). It is deliberately distinct from
  **Awaiting Approval**, which awaits a *gated decision* on a concrete proposal.
- **Interrupted** — machine-touching work was halted with outcome unknown
  (killed action, timeout, Ctrl+C mid-run). Because we cannot know what happened,
  nothing continues until the machine's actual state has been re-established
  deterministically.

The lifecycle is single-goal and serial: no second goal runs while one is active,
and state-changing actions never run in parallel. See Open Questions for the
boundaries of this stance.

---

## 2. Runtime States

States are grouped as: **resting** (Initialization, Idle), **goal-lifecycle**
(Inspection, Context Building, Diagnosis, Planning, Approval, Executing,
Verification, Replanning), **interaction pauses** (Awaiting Input, Awaiting
Approval), **halt** (Interrupted), and **goal outcomes** (Completed, Failed,
Cancelled).

For every state: purpose, entry conditions, exit conditions, allowed
transitions.

### 2.1 Session Initialization

- **Purpose.** Bring the runtime to a trustworthy starting state: load
  configuration; resolve and authenticate providers and skills; open the durable
  audit store; confirm the runtime's own prerequisites; detect a resume marker.
- **Entry conditions.** Process start. Also, after a machine reboot, when a
  resume marker is found.
- **Exit conditions.** All checks pass → Idle (fresh session) or directly into
  re-orientation (resume path, see §8). Any safety-critical failure → the
  runtime refuses to enter service, reports, and exits (Operator may retry).
- **Allowed transitions.** → Idle; → Machine Inspection (resume path); → END
  (fail-closed abort).

### 2.2 Idle

- **Purpose.** Resting; no goal active. The Assistant awaits the Operator's
  next instruction.
- **Entry conditions.** From Session Initialization; from Completed, Failed, or
  Cancelled when the Operator chooses to start a new goal.
- **Exit conditions.** OP_GOAL → Machine Inspection (a goal record is created,
  the goal statement is audited, fresh context is opened). OP_EXIT → END. A
  watchdog-detected machine change does not leave Idle but invalidates cached
  facts (see §4).
- **Allowed transitions.** → Machine Inspection; → END.

### 2.3 Machine Inspection

- **Purpose.** Gather deterministic, read-only facts about the machine, each with
  provenance (which collector, when, exit status) — RFC-0001 §5 (Diagnostics).
  Runs baseline probes at goal start, targeted diagnostics on request,
  verification re-checks, and state re-assessment after interruption or reboot.
  **Inspection never mutates the machine.**
- **Entry conditions.** From Idle (baseline); from Diagnosis (targeted); from
  Planning (a plan step depends on a fact not yet known); from Verification
  (a re-check is itself inspection); from Interrupted (state re-assessment);
  from Replanning; on resume (post-reboot re-orientation).
- **Exit conditions.**
  - Facts collected — fully or partially. A failed collector is recorded as
    "fact unknown," never as a guessed value (RFC-0001 §10.3) → Context
    Building.
  - Critical collector failure (e.g., cannot even establish the distro) → the
    runtime discloses and asks the Operator how to proceed → Awaiting Input; if
    hopeless → Failed.
  - Interrupted mid-collection → Interrupted.
- **Allowed transitions.** → Context Building; → Awaiting Input; → Failed; →
  Interrupted.

### 2.4 Context Building

- **Purpose.** Construct the provider view: the sanitized, purpose-limited,
  size-bounded, secret-free input that the LLM is allowed to see (RFC-0001 §9).
  Folds in relevant verified facts (with provenance), bounded conversation
  history, applicable skill content, and the goal statement. This is the *only*
  place LLM input is assembled, and it is the enforcement point for redaction and
  truncation. It touches neither the machine nor the provider.
- **Entry conditions.** From Machine Inspection (new facts); from Awaiting Input
  (new Operator input); from Replanning (revised situation); re-entered whenever
  the provider view is stale — new facts, a new reply, context consolidation, or
  degraded fallback.
- **Exit conditions.** Provider view ready → Diagnosis or Planning. If no usable
  view can be built (e.g., degraded mode with no facts), the caller discloses to
  Awaiting Input rather than consulting the LLM.
- **Allowed transitions.** → Diagnosis; → Planning.

### 2.5 Diagnosis

- **Purpose.** Interpret evidence against the goal; generate and test
  hypotheses; decide the next move — more evidence, a clarifying question, or a
  plan. Diagnosis is *cognitive*: it may consult the LLM or a skill. **It never
  touches the machine and never executes anything.**
- **Entry conditions.** From Context Building; from Awaiting Input (a reply
  supplies new information); from Replanning (evidence demands re-interpretation).
- **Exit conditions.**
  - Hypothesis sufficiently grounded → Planning.
  - More evidence needed → Machine Inspection, with a *requested diagnostic set*.
    Any request that would mutate the system is rejected by construction.
  - Ambiguity, or missing Operator input → Awaiting Input (clarifying question).
  - Out of depth, or unable to diagnose safely → Awaiting Input (disclose
    uncertainty, offer options) or Failed if genuinely hopeless.
  - Provider unavailable with no fallback → degraded mode → Awaiting Input
    (facts-only report; no recommendations in degraded mode).
  - The goal is diagnostic-only (the Operator asked to understand, not to act)
    and the interpretation is complete → Completed.
- **Allowed transitions.** → Planning; → Machine Inspection; → Awaiting Input; →
  Completed; → Failed.

### 2.6 Planning

- **Purpose.** Convert a grounded hypothesis into a concrete plan of discrete
  proposed actions. Each proposed action carries: what it is, why, what it
  reads or changes, risk-relevant properties, and how its success will be
  verified. Plans may originate from a skill (structured) or the LLM
  (synthesized); the Core normalizes *any* plan into discrete proposed actions.
  **Planning never executes.**
- **Entry conditions.** From Diagnosis (grounded); from Context Building
  (straight-to-plan when the goal is already understood); from Replanning
  (revised plan); from Awaiting Input (the Operator answered a "what would you
  do" question).
- **Exit conditions.**
  - Plan ready → Awaiting Approval. Risk classification happens on this edge:
    the Approval & Policy Engine classifies every proposed action and assigns
    its gate before presentation.
  - A plan step depends on an unknown fact → Machine Inspection.
  - No safe plan can be formed → Awaiting Input (explain why; offer options) or
    Failed.
  - Plan is empty (diagnostic-only goal) → the goal is reported → Completed.
  - Provider unavailable, no fallback → degraded mode → Awaiting Input.
- **Allowed transitions.** → Awaiting Approval; → Machine Inspection; →
  Awaiting Input; → Completed; → Failed.

### 2.7 Awaiting Approval

- **Purpose.** The human gate (RFC-0001 §8.3). The classified plan is presented:
  per-action explanation, risk class, warning level, and — if any — a blocked
  classification. The Operator decides. Read-only actions inside the policy
  allowlist may be marked as "auto-permitted" in the presentation, but every
  action, including those, is classified and audited. Standing approvals, where
  permitted, are governed by policy and always expire.
- **Entry conditions.** From Planning, with a classified plan. A blocked
  classification still enters this state — presented as blocked, requiring an
  explicit Operator override to proceed.
- **Exit conditions.**
  - Approve (or override a block) → Executing. The approval token is created,
    scoped, and audited.
  - Reject → Replanning (the rejection reason is folded in as evidence).
  - Refine → Replanning.
  - Cancel the goal → Cancelled.
  - Interrupt → Interrupted.
  - Machine state change detected while awaiting → the approval is invalidated;
    preconditions may no longer hold → Machine Inspection.
- **Allowed transitions.** → Executing; → Replanning; → Cancelled; → Interrupted;
  → Machine Inspection.

### 2.8 Executing

- **Purpose.** Run the approved action (or the serialized, approved batch) under
  the executor's guardrails: scoping, timeouts, output capture, secret-free
  handling, elevation per action (RFC-0001 §8). Each action runs only with a
  valid, unexpired approval token that is **re-validated at the execution
  boundary** — the machine may have changed since the approval was given
  (see Invariants).
- **Entry conditions.** From Awaiting Approval (approve or override), token
  re-validated. From Verification, when the just-verified step was not the last
  step of an already-approved plan and the next step continues under the same
  approval envelope.
- **Exit conditions.**
  - Action succeeded → Verification (mandatory; there is no other exit for
    success).
  - Action failed → Verification (mandatory, to establish the actual state
    before anything else) — never directly to Replanning.
  - Action timed out or was interrupted → Interrupted (outcome unknown; state
    uncertain).
  - Batch stopped by the Operator (cancel) → Cancelled, with partial-execution
    accounting (exactly which steps ran, which did not, what is unverified).
  - The approved plan requires a reboot → the runtime writes a resume marker,
    then hands off to the reboot (runtime ends). See §8.
- **Allowed transitions.** → Verification; → Interrupted; → Cancelled; → END
  (reboot handoff).

### 2.9 Verification

- **Purpose.** Deterministically confirm that the executed action produced the
  expected post-condition (RFC-0001 §10.5). Uses read-only re-inspection and
  state comparison. Never a guess; never skipped for an action that ran.
- **Entry conditions.** From Executing (success or failure); from Interrupted
  (state assessment after a halt); on resume (post-reboot check of a step that
  was pre-approved for verification).
- **Exit conditions.**
  - Passed, and all plan steps are complete → Completed.
  - Passed, but approved steps remain → Executing (the next step).
  - Failed (post-condition not met) → Replanning (the failure evidence is new
    fact).
  - Inconclusive (the state cannot be observed) → Awaiting Input; the runtime
    does **not** claim success.
  - Interrupted → Interrupted.
- **Allowed transitions.** → Completed; → Executing; → Replanning; → Awaiting
  Input; → Interrupted.

### 2.10 Replanning

- **Purpose.** Decide what to do when the current plan is invalidated: failed
  verification, rejected or refined approval, new evidence, changed
  preconditions, or exhausted actions. The Core determines the response: a
  bounded retry, a revised plan, more evidence, or giving up. Replanning may
  consult the LLM (with fresh evidence, through a fresh Context Building) or a
  skill. **Replanning is analysis; it executes nothing.**
- **Entry conditions.** From Verification (failed or inconclusive); from Awaiting
  Approval (rejected or refined); from Interrupted (the Operator chooses
  "revise").
- **Exit conditions.**
  - Revised plan → Planning (which re-normalizes, re-classifies, and re-presents
    — approval never carries over from a changed plan).
  - Bounded retry of the same action → Planning (re-presented for approval;
    preconditions must be verified unchanged; retries bounded by policy).
  - More evidence needed → Diagnosis or Machine Inspection.
  - Cannot proceed (attempts exhausted, no safe path, block not overridden) →
    Failed.
  - The Operator's input is needed → Awaiting Input.
- **Allowed transitions.** → Planning; → Diagnosis; → Machine Inspection; →
  Awaiting Input; → Failed.

### 2.11 Awaiting Input

- **Purpose.** An active goal paused on a free-text question: a clarification, a
  choice between options, acknowledgment of uncertainty, or a disclosure in
  degraded mode. Distinct from Awaiting Approval, which awaits a gated decision
  on a concrete proposal. The Core remembers which question is outstanding and
  routes the reply accordingly.
- **Entry conditions.** From Diagnosis (clarify / out of depth / degraded); from
  Planning (no safe plan); from Verification (inconclusive — disclosure); from
  Interrupted (after state re-assessment, the decision is handed to the
  Operator); from critical collector failure; from a cognitive phase interrupted
  without machine uncertainty.
- **Exit conditions.**
  - Reply → Diagnosis or Planning, context-routed (a clarifying answer goes back
    to Diagnosis; an answer to "what should we do" goes to Planning).
  - New goal statement → Diagnosis (the goal is revised).
  - Cancel → Cancelled.
  - Second interrupt or explicit exit → END.
- **Allowed transitions.** → Diagnosis; → Planning; → Cancelled; → END.

### 2.12 Interrupted

- **Purpose.** The halt state for machine-touching work whose outcome is
  unknown: a killed action, a timed-out action, a killed probe, or an interrupt
  during a machine-touching phase. Nothing about the machine's state may be
  assumed; it must be re-established deterministically before anything proceeds
  (RFC-0001 §10). A single Ctrl+C during a *cognitive* phase does not enter this
  state — it cancels the provider call and returns to Awaiting Input.
- **Entry conditions.** From Executing (timeout or interrupt); from Machine
  Inspection (interrupt); from Awaiting Approval (interrupt while presenting);
  from Verification (interrupt). A repeated interrupt from this state → END.
- **Exit conditions.** After re-assessment (via Machine Inspection), findings are
  presented and the Operator decides:
  - Continue → Awaiting Approval (remaining actions are re-presented for fresh
    approval) or Executing (if the remaining work is only read-only
    verification).
  - Revise → Replanning.
  - Abandon → Cancelled.
- **Allowed transitions.** → Machine Inspection; → Awaiting Approval; →
  Replanning; → Cancelled; → END.

### 2.13 Completed

- **Purpose.** The goal was achieved and verified. The runtime reports the
  outcome, the verified state, what was done, and any caveats, and offers next
  steps.
- **Entry conditions.** From Verification (all steps passed); from Diagnosis or
  Planning (diagnostic-only goals that needed no action). An *unverified*
  outcome is not Completed: it stays in Verification or Awaiting Input unless
  the Operator explicitly accepts it, in which case it is Completed-with-caveat
  and honestly labeled as unverified.
- **Exit conditions.** New goal → Idle; exit → END.
- **Allowed transitions.** → Idle; → END.

### 2.14 Failed

- **Purpose.** The goal cannot be reached within this project's safety rules. The
  runtime stops escalating, reports what is known and what could not be done, and
  hands the remainder to the human (RFC-0001 §10.9).
- **Entry conditions.** From Planning or Replanning (no safe path, attempts
  exhausted); from Diagnosis (hopeless); from Awaiting Approval (blocked, not
  overridden, no alternative); from Verification (irrecoverable); from Machine
  Inspection (fatal collector failure).
- **Exit conditions.** New goal → Idle; exit → END.
- **Allowed transitions.** → Idle; → END.

### 2.15 Cancelled

- **Purpose.** The Operator deliberately abandoned the goal. The runtime captures
  the partial state honestly — what ran, what is unverified — reports it, and
  returns control.
- **Entry conditions.** OP_CANCEL from any active state; reject-all at Awaiting
  Approval; abandon at Interrupted.
- **Exit conditions.** New goal → Idle; exit → END.
- **Allowed transitions.** → Idle; → END.

---

## 3. State Machine Diagram

ASCII diagram of the complete state machine. Where the drawing is ambiguous, the
written definitions in §2 and the event rules in §4 win.

```
           ┌─────────────────────────────┐
           │   Session                   │
           │   Initialization            │
           └─────────────┬───────────────┘
                         │ init ok
                         │ (resume marker present: continue at ▼re-orient)
                         ▼
           ┌─────────────────────────────┐          ┌──────────┐
           │           Idle              │──OP_EXIT─▶│   END    │
           └─────────────┬───────────────┘          └──────────┘
                         │ OP_GOAL
                         ▼
           ┌─────────────────────────────┐
           │      Machine Inspection     │◀───────────────┐
           └──────┬──────────────┬──────┘                │ needs more
                  │ facts        │ interrupt             │ facts
                  ▼              ▼                       │
     ┌─────────────────────┐  ┌──────────────┐           │
     │   Context Building  │  │  Interrupted │           │
     └──────────┬──────────┘  └──────┬───────┘           │
                │ provider view      │ re-assess         │
                ▼                    ▼ (via Inspection)  │
     ┌─────────────────────┐  ┌────────────────────────┐ │
     │       Diagnosis     │  │    Awaiting Input      │ │
     └───┬───────────┬─────┘  └───────────┬────────────┘ │
 grounded│           │ clarify/reply      │ reply        │
         │           │◀───────────────────┘ (context-    │
         ▼           │                    │  routed)     │
     ┌─────────────────────┐             │              │
     │      Planning       │──no safe────┘              │
     └────────┬────────────┘    plan                    │
              │ plan ready (classified by Approval &    │
              │ Policy Engine on this edge)             │
              ▼                                         │
     ┌─────────────────────┐                            │
     │  Awaiting Approval  │                            │
     └───┬─────────────┬───┘                            │
  approve│             │reject / refine                 │
 /override│             ▼                               │
         ▼     ┌─────────────────────┐                  │
     ┌─────────────────────┐         │                  │
     │      Executing      │         │                  │
     └───┬─────────────────┘         │                  │
    done │                           │                  │
         ▼                           │                  │
     ┌─────────────────────┐         │                  │
     │     Verification    │         │                  │
     └───┬─────────────┬───┘         │                  │
   pass  │             │ fail /      │                  │
 (all)   │             │ inconclusive│                  │
         ▼             ▼             │                  │
     ┌─────────────────────┐   ┌────────────────────┐   │
     │      Completed      │   │    Replanning      │   │
     └─────────────────────┘   └─┬─────┬─────┬──────┘   │
                        revised  │     │     │ cannot   │
                        plan ────┘     │     │ proceed  │
                       more evidence ──┘     ▼          │
                        (→ Diagnosis)  ┌─────────────┐  │
                                       │   Failed    │  │
                                       └─────────────┘  │
   ┌────────────────────────────────────────────────────┘
   │ Shortcut edges (normative; apply from any non-terminal state):
   │   OP_CANCEL     → Cancelled
   │   OP_INTERRUPT  → Interrupted (machine-touching work)
   │                  or Awaiting Input (cognitive work);
   │                  second press → END
   │   ACTION_TIMEOUT / ACTION_INTERRUPTED → Interrupted
   │   provider loss, no fallback → degraded mode → Awaiting Input
   │   REBOOT (approved) → write resume marker → END
   │        ──machine reboots──▶ Session Initialization (resume path)
   │   STATE_CHANGED (external watchdog) → invalidate facts
   │        → Machine Inspection (or back to Awaiting Approval path)
   │   OP_EXIT → END (mid-goal: run interrupt protocol first,
   │        write resume marker if a goal is unfinished)
   └────────────────────────────────────────────────────────────

   Interrupted ──re-assess──▶ Machine Inspection ──▶ Awaiting Input
       ├──continue──▶ Awaiting Approval (fresh approval of remaining actions)
       │              or Executing (read-only remainder only)
       ├──revise────▶ Replanning
       └──abandon───▶ Cancelled

   Completed / Failed / Cancelled ──new goal──▶ Idle ──▶ new goal lifecycle
   Completed / Failed / Cancelled ──OP_EXIT──▶ END
```

Note: **Verification → Executing** (next approved step) is implied by "pass" when
steps remain; it is part of the same transition class and not drawn as a
separate edge to keep the diagram legible.

---

## 4. Events

An **event** is the stimulus that triggers a transition. Events are grouped by
source. For each: what it is, and how the runtime responds.

### 4.1 Operator events

- **OP_GOAL** — the Operator states or revises a goal. In Idle: begins a goal →
  Machine Inspection (baseline). In Awaiting Input: folds the new statement in →
  Diagnosis (goal revised). In Completed/Failed/Cancelled: begins a new goal →
  Idle.
- **OP_REPLY** — a free-text answer to an outstanding question. In Awaiting
  Input: routed to the state that asked — Diagnosis for a clarification, Planning
  for a direction decision.
- **OP_APPROVE** — the Operator approves the presented actions. In Awaiting
  Approval: an approval token is created, the action is audited → Executing.
- **OP_OVERRIDE** — the Operator explicitly overrides a *blocked* classification.
  In Awaiting Approval: audited as an override with its own warning; → Executing.
  It is the only way a blocked action proceeds, and it is always recorded.
- **OP_REJECT** — the Operator rejects the presented actions. In Awaiting
  Approval: the reason becomes evidence → Replanning.
- **OP_REFINE** — the Operator requests plan changes. In Awaiting Approval: →
  Replanning.
- **OP_CANCEL** — the Operator abandons the goal. From any active state: →
  Cancelled. Partial execution is accounted honestly (what ran, what is
  unverified).
- **OP_INTERRUPT** — Ctrl+C or interrupt signal. First press: if machine-touching
  work is in flight, the action or probe is terminated → Interrupted; if only
  cognitive work is in flight, the provider call is cancelled → Awaiting Input.
  Second press within the grace window: → END (and, if a goal is unfinished, a
  resume marker is written first).
- **OP_EXIT** — the Operator leaves the runtime. From Idle or a goal outcome: →
  END. From an active state: the interrupt protocol runs first (state is
  accounted, resume marker written if a goal is unfinished), then → END.
- **OP_VIEW** — informational only. Renders context or audit on demand; no state
  transition.

### 4.2 Machine events

- **FACTS_COLLECTED** — an inspection returned facts, fully or partially. →
  Context Building. Failed collectors are carried as "fact unknown."
- **COLLECTOR_FAILED** — a diagnostic failed or timed out. Recorded as "fact
  unknown." If the failure is critical (baseline cannot be established): → Awaiting
  Input (disclose) or Failed.
- **STATE_CHANGED_DETECTED** — the read-only watchdog observed that machine state
  changed externally (e.g., a service flipped, a lock appeared). Effect:
  dependent facts are invalidated. If in Awaiting Approval → the approval is
  invalidated → Machine Inspection. Elsewhere → context is marked stale; the next
  decision that consumes facts re-inspects first.

### 4.3 Provider events

- **PROVIDER_RESPONSE** — the LLM returned a valid, parseable reply. Consumed in
  Diagnosis, Planning, or Replanning. A structurally non-compliant reply is
  treated as PROVIDER_REFUSAL.
- **PROVIDER_REFUSAL** — the provider declined or produced unusable output.
  Bounded retry with the provider, then fallback.
- **PROVIDER_UNAVAILABLE** — connection or service failure. Retry with backoff
  (bounded), then the fallback provider chain.
- **PROVIDER_TIMEOUT** — no reply within the phase bound. Treated as
  PROVIDER_UNAVAILABLE after backoff.
- **PROVIDER_FALLBACK_OK** — a fallback provider is usable. → continue the
  cognitive phase with a fresh Context Building.
- **PROVIDER_FALLBACK_FAILED** — no provider is usable. → degraded mode →
  Awaiting Input (facts-only presentation; no recommendations).

### 4.4 Plan and approval events

- **PLAN_READY** — a plan was normalized into discrete proposed actions. →
  classification on the edge into Awaiting Approval.
- **ACTION_CLASSIFIED** — the Approval & Policy Engine assigned a risk class and
  gate to an action. Internal; determines how it is presented (auto-permitted,
  confirm, confirm-with-warning, blocked).
- **ACTION_BLOCKED** — an action was classified as blocked. It is presented in
  Awaiting Approval as blocked; it proceeds only through OP_OVERRIDE.
- **PLAN_REJECTED / PLAN_REFINED** — outcomes of OP_REJECT / OP_REFINE; → 
  Replanning.

### 4.5 Execution events

- **ACTION_STARTED** — internal; audited.
- **ACTION_SUCCEEDED** — exit status and deterministic signal indicate success →
  Verification.
- **ACTION_FAILED** — nonzero exit or error → Verification (mandatory, to
  establish actual state), then → Replanning.
- **ACTION_TIMEOUT** — the watchdog killed the action → Interrupted (state
  unknown).
- **ACTION_INTERRUPTED** — the action was killed mid-run → Interrupted.
- **ACTION_PARTIAL** — a batch stopped partway (cancel or interrupt) →
  Interrupted or Cancelled, with exact accounting of which steps ran.

### 4.6 Verification events

- **VERIFICATION_PASSED** — post-condition confirmed → Completed (if no steps
  remain) or Executing (next approved step).
- **VERIFICATION_FAILED** — post-condition not met → Replanning.
- **VERIFICATION_INCONCLUSIVE** — the state cannot be observed → Awaiting Input;
  no success is claimed.

### 4.7 System events

- **SKILL_UNAVAILABLE** — a skill referenced by the plan or diagnosis cannot be
  loaded or authenticated. Its material is refused; → Planning (revise without
  it) or Awaiting Input. An unauthenticated skill is never substituted.
- **CONTEXT_FULL** — the context ceiling was reached. → consolidation (drop or
  summarize, per RFC-0001 §9), transparently, then → Context Building.
- **TIMEOUT** — a generic phase watchdog fired (stalled phase). If cognitive →
  Awaiting Input (disclose). If machine-touching → Interrupted.
- **REBOOT_REQUESTED** — the approved plan includes a reboot. → write a resume
  marker → END (machine reboots).
- **REBOOT_DETECTED** — the runtime is starting after a reboot. → resume path:
  Session Initialization → Machine Inspection (re-orient). See §8.
- **CONFIG_CHANGED** — configuration or policy was reloaded. Informational;
  outstanding approvals are re-validated against the new policy.

---

## 5. The Session Loop

The session loop is the ordered sequence in which subsystems participate. The
Core is always the conductor: it decides the order and enforces the rules. The
canonical order for a goal that requires action:

1. **Machine Inspection** — the Diagnostics & Fact Layer gathers baseline facts.
   *No other subsystem touches the machine here.*
2. **Context Building** — the Core sanitizes, bounds, and redacts facts, history,
   and goal into a provider view. *Context & Memory is consulted; no provider, no
   machine.*
3. **Diagnosis** — a Provider (LLM) or a Skill interprets the provider view and
   proposes a diagnostic set, a clarifying question, or a hypothesis. Steps 1–3
   iterate until the hypothesis is grounded: Diagnosis requests facts →
   Inspection → Context Building → Diagnosis again.
4. **Planning** — a Provider or a Skill produces a plan; the Core normalizes it
   into discrete proposed actions.
5. **Classification and gating** — the Approval & Policy Engine classifies every
   proposed action (risk class + gate) and applies policy (default-deny,
   elevation, scope).
6. **Presentation and decision** — the TUI presents the classified plan; the
   Operator decides (approve, reject, refine, override, cancel).
7. **Execution** — the Executor runs the approved action (or the next step of the
   approved batch) under its guardrails, one action at a time.
8. **Verification** — the Diagnostics & Fact Layer re-inspects deterministically;
   the post-condition is confirmed or refuted.
9. **Continuation or replanning** — if steps remain, return to 7. If verification
   failed, or the plan was rejected or refined, enter Replanning, which returns
   to 3 or 4.
10. **Outcome** — the goal reaches Completed, Failed, or Cancelled and the
    runtime returns to Idle.

Components that must **not** participate at a given step are as important as
those that do: the Executor never appears before step 7; the Approval & Policy
Engine never appears in steps 1–4 (it does not design plans or interpret
evidence); the LLM never appears in steps 1, 2, 7, or 8.

---

## 6. Component Consultation Rules

Exactly when each component is consulted, and when it is never consulted.

### LLM (via Providers)
- **Consulted** in Diagnosis, Planning, and Replanning — and only *after* a
  fresh Context Building has produced a provider view.
- **Never** in Machine Inspection, Context Building, Awaiting Approval, Executing,
  or Verification. **Never** with raw, unbounded machine output or with secrets.
- Its output is treated as untrusted data: it proposes; it never commands
  (RFC-0001 §7).

### Deterministic tools (Diagnostics & Fact Layer)
- **Consulted** in Machine Inspection (collection), Verification (re-check), and
  state re-assessment after interruption, reboot, or external change.
- This is the **only** subsystem that reads the machine.
- **Never** consulted to design a plan, classify risk, or interpret conversation.

### Approval & Policy Engine
- **Consulted** at (a) the Planning → Awaiting Approval edge — every proposed
  action is classified and gated; (b) the Awaiting Approval → Executing edge —
  the token is re-validated against current policy, elevation, and machine state
  (the approval-to-execution gap is the classic time-of-check/time-of-use
  hazard); (c) startup and configuration reload — the read-only allowlist and
  default-deny policy are established; (d) whenever CONFIG_CHANGED requires
  re-validation of outstanding approvals.
- **Never** consulted to design a plan or to interpret evidence. It is the part
  that must never be surprised (RFC-0001 §5).
- The Approval concern (risk classification) and the Policy concern
  (default-deny, elevation, scope, standing approvals) are two faces of this one
  deterministic engine; they are always applied together at the same two edges.

### Executor (Action Execution)
- **Consulted** only in Executing, and only with a valid, re-validated approval
  token. Never elsewhere.

### Skills
- **Consulted** in Diagnosis (knowledge and diagnostic steps), Planning (plan
  templates), and Machine Inspection (collectors).
- A skill is a *candidate*: it is authenticated before use and its actions go
  through the same Approval & Policy Engine as everything else. A skill can
  never bypass the gate.

### Context & Memory
- **Consulted** by Context Building (assembly), by Verification of staleness, and
  by the Operator (view/export).
- **Never** feeds the LLM directly; always through Context Building.

### Audit & Transcript
- **Written** at every consequential boundary: goal adoption, proposal,
  classification, approval, override, execution start and end, verification, and
  outcome. Written before the consequence is allowed to proceed.
- **Never edited.** Readable by the Operator at any time (no transition).

### Presentation (TUI)
- **Always present.** Renders state, evidence, and approvals; collects input.
- **Never** decides policy, classifies risk, or executes anything.

---

## 7. Replanning

Replanning is the runtime's answer to *"the plan we had no longer describes the
situation."* It is a first-class state, not an error path.

### When replanning happens
- Verification failed or was inconclusive.
- An action failed (after Verification established the actual state).
- The Operator rejected or refined the proposed plan.
- New evidence contradicts a hypothesis the plan was built on.
- Preconditions the plan depended on changed.
- A blocked action was not overridden and no alternative exists within the plan.

### Reusing previous evidence
Deterministic facts are reused **only if their provenance is still valid**: the
machine identity is unchanged, the facts are within their staleness bound, and
they are not contradicted by the failure that triggered the replanning. The
failure's evidence is *added* to the fact set, not discarded. Anything the LLM
interpreted is never reused as a fact — interpretations are re-derived against
the (re-validated) evidence.

### Discarding the previous plan
The previous plan is **input to revision, not a directive**. Two cases:
- **Preconditions unchanged, single step failed** — a targeted revision is
  allowed: the failed step is replaced or retried (bounded) without rebuilding
  the whole plan.
- **Preconditions changed, or the failure undermines the hypothesis** — the plan
  is rebuilt from Planning, and if the hypothesis itself is in doubt, replanning
  returns to Diagnosis first.

Approval never carries over across a revised plan. A changed plan is
re-normalized, re-classified, and re-presented. Even a *retry* of an identical
action is re-presented for approval, because its previous approval token was
consumed by the attempt.

### Replanning always starts from certainty
Because Replanning is entered after Verification, the runtime already knows the
actual post-attempt state. It never plans against an assumed state.

---

## 8. Interruption Behavior

### The Operator cancels (OP_CANCEL)
From any active state, the goal is abandoned → Cancelled. If execution was in
flight, the running action is stopped (or its completion is awaited only when
stopping would itself be unsafe), the exact set of ran/not-ran steps is recorded,
and the outcome is reported honestly with no unverified claims.

### Ctrl+C (OP_INTERRUPT)
- First press: if machine-touching work is in flight, the action or probe is
  terminated → **Interrupted**; if only cognitive work is in flight, the provider
  call is cancelled → **Awaiting Input**.
- In Interrupted, nothing is assumed: the machine is re-inspected, findings are
  presented, and the Operator chooses continue / revise / abandon.
- Second press within the grace window → END, with a resume marker written if a
  goal is unfinished.

### Provider disconnects
The runtime distinguishes machine-touching work from cognitive work. A provider
loss never interrupts machine work that is already running: the Executor and the
Diagnostics layer are independent of the LLM. Provider loss affects only
LLM-dependent phases: Diagnosis, Planning, Replanning. Those phases retry with
backoff, try the fallback chain, and only then enter degraded mode → Awaiting
Input (facts-only, no recommendations). The runtime never pretends the provider
replied.

### Reboot requested (as an approved step)
A reboot step is presented and approved like any other action. Executing it means
the runtime will be gone when the machine comes back. Before handing off, the
runtime writes a **resume marker** describing where the session was, what was
done, and what remains. The marker is written *before* the reboot is triggered,
so a crash between the write and the reboot is still recoverable.

### Reboot happens (unexpectedly)
The runtime is gone; nothing to do in-process. On next start, Session
Initialization finds the resume marker, and the runtime re-orients: it
re-inspects the machine (the world changed — nothing is assumed), presents the
Operator with the pre-reboot state from the audit trail, and asks what they find
themselves in front of.

### Session resumes (normal)
A resume never means "keep going as if nothing happened." The rules:
1. Re-inspect deterministically (baseline) — the machine is assumed different
   until proven otherwise.
2. Re-orient: present the pre-reboot/pre-exit state from the audit trail.
3. Ask the Operator to confirm continuation. Read-only verification steps that
   were pre-approved may run to assess the post-reboot state; **no
   state-changing action resumes without fresh approval**. There is no standing
   authorization across a reboot (RFC-0001 §8.3).

### General rule
Any interruption that leaves the outcome of a machine-touching operation unknown
is followed by a deterministic re-assessment before any further machine action.
The runtime's first instinct after an interruption is never "assume it didn't
happen"; it is "find out what actually happened."

---

## 9. Runtime Invariants

These hold at all times, in every state, without exception. A design or
implementation that requires weakening one of these is a violation of this RFC.

1. **Execution never starts without approval.** An action runs only after the
   Approval & Policy Engine has classified and gated it **and** the Operator has
   approved it (or it is inside the policy's pre-approved read-only allowlist).
   There is no path from a proposal to the machine that skips the gate.
2. **Verification always follows execution.** Every executed action is followed
   by deterministic Verification before any success is claimed or any next step
   is taken. The only exits from Executing are toward Verification or toward a
   halt that itself re-establishes state.
3. **Planning never executes.** Planning, Diagnosis, and Replanning produce
   proposals and interpretations; they run nothing. Machine Inspection is always
   read-only.
4. **The LLM is only ever consulted through a provider view.** The LLM never
   receives raw, unbounded machine output, secrets, or credentials (RFC-0001
   §8.7).
5. **No untrusted text is ever interpolated into a command.** Nothing from the
   LLM, from machine output, or from a skill is executed as a shell string
   (RFC-0001 §7 rule 1). Actions are built from sanctioned structures only.
6. **Deviation from the approved plan requires fresh approval.** A step not in
   the approved plan, or an approved step whose preconditions changed, is
   re-presented. Approval is scoped to what was shown.
7. **Risk classification is deterministic and never the LLM's self-report.** The
   LLM does not grade its own actions; the Approval & Policy Engine does.
8. **Any halt of machine-touching work is followed by re-assessment.** After an
   interrupt, a timeout, a partial execution, or a reboot, no further machine
   action occurs until the actual state has been re-established deterministically.
9. **The runtime never fabricates.** On provider failure, on collector failure,
   on inconclusive verification, the runtime discloses. An unverified outcome is
   never presented as success.
10. **Facts carry provenance and expire.** Every fact is attributed, and no fact
    is used past its staleness bound without re-collection. A fact contradicted
    by fresh evidence is invalidated, and the fresh evidence wins.
11. **Approval tokens are scoped and consumable.** A token is bound to its
    action, its time, and the machine state it was approved against. It is
    consumed by use or expiry, and it is invalidated by a state change, an
    interrupt, a reboot, or a policy reload. A consumed token is never reused.
12. **A blocked action proceeds only via an explicit, audited override.** The
    override is presented with its own warning and is always recorded.
13. **The audit trail is written before the consequence.** Proposals,
    approvals, overrides, executions, verifications, and outcomes are recorded
    at the boundary, not after the fact, and are never silently edited.
14. **No terminal outcome is reached while machine work is in flight.** A goal
    cannot move to Completed, Failed, or Cancelled until in-flight machine work
    has passed through Verification or Interrupted. You cannot declare an
    outcome over an unknown state.
15. **No standing authorization across a boundary.** A reboot, an exit, a
    crash, an interrupt, or a policy reload ends every approval. Continuation
    requires fresh, explicit approval.

---

## 10. Failure Recovery

Recovery always follows the same order: **determinism first, then disclosure,
then decision, then action.** The runtime first establishes what is true, then
tells the Operator, then lets the Operator decide, then acts on approval.

### Provider failure
Retry with backoff (bounded) → fallback provider chain → degraded mode →
Awaiting Input with a facts-only presentation. Machine work already in flight is
unaffected. The runtime never fabricates a reply.

### Executor failure
- An individual action failed → Verification (actual state) → Replanning.
- The Executor itself is broken (cannot launch or supervise any action) → this is
  a safety-critical failure → no further actions are attempted → Interrupted,
  findings presented, and the Operator is handed the remainder (Failed or manual
  takeover).
- Orphaned or lingering effects of a half-run action are treated as uncertain
  state and are *never* assumed away.

### Policy failure
Policy that cannot be parsed, an unknown risk class, or any internal error in the
Approval & Policy Engine is **fail-closed** (RFC-0001 §8.12): the action is
blocked, the Operator is told why, and the session moves to Awaiting Input or
Failed. The runtime never proceeds because "the policy check was unavailable."

### Collector failure
A failed or timed-out diagnostic becomes a "fact unknown" with provenance
(RFC-0001 §10.3). Partial facts still flow into Context Building, marked partial.
If a *critical* collector fails (the baseline cannot be established), the runtime
discloses and asks rather than proceeding on assumptions. It never substitutes a
guessed value for a missing fact.

### Partial execution
When a batch stops partway, or an action is interrupted, the runtime:
1. Marks the state as uncertain.
2. Re-establishes the actual state (Verification/Inspection).
3. Records exactly which steps ran and which did not (audit).
4. Presents the result and options to the Operator.
Rollback is never automatic: reverting anything is itself a state-changing action
requiring its own approval. The runtime's job at this moment is to not make it
worse, to know what happened, and to hand the decision to the Operator.

### Recovery ordering principle
Every recovery path starts from *known* state, states the *uncertainty* to the
Operator, and only then offers *approved* next steps. No recovery path starts
from an assumption.

---

## 11. Open Questions

Runtime-specific questions that must be answered before implementation. They are
deliberately distinct from RFC-0001's open questions, though a few inherit from
them (marked *).

1. **Approval granularity.** When a plan is approved as a whole, may subsequent
   steps run after the previous step verifies, without re-approval? Or must each
   step be re-confirmed? What does "deviation" mean precisely, and who decides
   whether a change counts as a deviation? (inherits RFC-0001 Q2)
2. **Retry semantics.** How many retries are permitted for a failed action, over
   what window, and is a retry always re-presented for approval, or only when
   preconditions changed?
3. **Timeouts.** What is the per-phase time budget (provider call, action,
   verification, inspection)? What is the grace window between first and second
   Ctrl+C? What happens when a budget expires in each phase?
4. **Read-only allowlist.** What exactly may run without per-action approval, and
   who defines it — the project, the distro, or the Operator? Can the Operator
   widen or narrow it? (inherits RFC-0001 Q4)
5. **Idle and awaiting drift.** How does the runtime detect that the machine
   changed while it waited (in Idle, Awaiting Input, Awaiting Approval)? What is
   the staleness bound per fact domain, and what does the watchdog cost? When the
   Operator is away, is there an idle timeout, and what does it do to an
   outstanding approval?
6. **Resume lifetime.** How long does a resume marker remain valid? Are old
   sessions garbage-collected? What if the machine identity changed between runs
   (different distro, different machine)? What if the user runs the tool inside a
   container now?
7. **Attended vs. unattended execution.** What does "attended" mean for the
   Executor? May an Operator walk away during a long approved action (e.g., a
   package install)? If the Operator must be present, how is presence
   established?
8. **Reboot-resume verification.** May the pre-approved read-only verification
   steps run automatically on resume, or does even read-only work require the
   Operator to be present at resume? (This RFC leans toward automatic read-only
   assessment with no state-changing continuation.)
9. **Interrupted-action reconciliation.** How are half-killed actions reconciled:
   orphaned processes, held locks, partial file writes, transaction states in the
   package manager? What is the runtime's responsibility, and what must it refuse
   to touch?
10. **Multiple goals.** Is single-goal-per-session the correct stance? Can a
    diagnostic-only goal coexist with an action goal? Can the Operator ask a new
    question while a goal is active (queue, cancel, or split)?
11. **Degraded mode scope.** Is degraded (facts-only) mode a product feature or a
    graceful-failure path? How much can it do without an LLM — run baseline
    inspections, present raw facts, run skills that are fully deterministic?
12. **Context-routing of replies.** How does Awaiting Input remember which
    question is outstanding so replies route correctly? What happens if the
    Operator answers with a new question instead of an answer?
13. **Blocked-action lifecycle.** Is a block ever irreversible within a session?
    May an Operator override any block, or are some blocks absolute? Who decides
    the difference?
14. **Input during execution.** What does the runtime do with an OP_GOAL or
    OP_REPLY arriving while Executing or Verifying — queue it, reject it, or
    treat it as an interrupt?
15. **Concurrent collection.** May read-only inspections run in parallel for
    speed? (State-changing execution is serial by design.) What are the bounds?
16. **Diagnostic-only goals.** The RFC admits Completed reached from Diagnosis or
    Planning for informational goals. What is the minimum evidence bar for a
    "diagnosis complete" claim, and how is it labeled when it is really a
    hypothesis?
17. **Watchdog scope.** What is the minimal read-only watch set, and how are
    false "state changed" triggers avoided (e.g., a counter that ticks on its
    own)?

---

## 12. Architectural Risks

Risks specific to *runtime behavior*. They supplement RFC-0001's risk list;
several are its runtime expression. Roughly ordered by severity.

1. **Plan-level rubber stamp at runtime.** RFC-0001 risk #1 warned of approval
   as theater. Its runtime form is concrete: the Operator approves a plan once,
   at a moment of low comprehension, and the runtime then executes a *chain* of
   steps semi-autonomously (each individually verified, but the *sequence* never
   reconsidered as a whole). If per-step gates are too permissive, the runtime
   becomes exactly the unattended remediator the project refuses to be. The
   design must decide — and this is Open Question 1 — how much of the chain may
   run on one approval, and how the sequence itself stays re-approvable.

2. **The approval-to-execution gap (TOCTOU).** Between "approve" and "run," the
   machine can change: a service the plan assumed stopped may have started, a
   package may have been upgraded. Executing the approved action against the new
   state is the classic time-of-check/time-of-use hazard, and it is lethal on a
   system being actively used. Re-validation at the execution boundary
   (Invariant 11) mitigates it, but only if the re-validation is *real* — a
   shallow check is worse than none because it produces false confidence.

3. **Interruption is where machines get damaged.** The most dangerous single
   instant in the runtime is the interrupt of a machine-touching action: a
   half-written config, a held package lock, an orphaned process. The risk is
   that Interrupted handling assumes "it didn't run" and the Operator resumes on
   a false premise. This is why Invariant 8 exists; the implementation risk is
   that it is treated as a nicety rather than a hard rule.

4. **Silence and deadlock.** A provider that never replies, an action that hangs
   forever, a verification that cannot observe its own inputs: each can stall the
   session in a state the Operator cannot recover from without killing the
   runtime. Every phase needs a timeout budget and an escalation path (Open
   Question 3), or the runtime fails by *waiting*, which is a silent, invisible
   failure mode.

5. **Resume-into-a-changed-world.** After a reboot the world is different, and
   the runtime's greatest temptation is to continue the plan as if nothing
   happened. This RFC forbids it (Invariant 15, §8), but the risk is
   *drift*: a resume path that technically re-inspects but functionally
   "just continues." The resume path must be built as a re-orientation, not a
   resumption.

6. **Verification theater at runtime.** RFC-0001 risk #10, given shape: "exit
   code 0" is treated as verification. A package manager can return 0 while the
   symptom persists; a service can be "active" but broken. The runtime's
   verification rules must be *state-based* (compare before/after facts) and must
   know when it *cannot* verify rather than declaring victory on a weak signal.

7. **Deterministic-facts starvation.** The whole runtime depends on the
   Diagnostics & Fact Layer being able to observe state. On a broken system —
   a half-booted machine, a failing disk, a corrupted package DB — verification
   and re-assessment become impossible, and every safety rule that depends on
   them quietly stops working. The runtime must recognize when it is
   "observation-blind" and escalate to the Operator (manual recovery) instead of
   pretending to know.

8. **State-machine completeness illusion.** Real machines refuse to fit clean
   states: package transactions half-apply, services die mid-restart, and
   "failed" commands leave the system better or worse in ways the machine can't
   tell us. The risk is that implementers trust the diagram and build a runtime
   that assumes recoverability. Every transition must be built to tolerate the
   machine being messier than the state machine, with re-assessment as the
   default response.

9. **Watchdog cost and noise.** Detecting external state change (Invariant
   discussion, §4.2) is expensive and noisy. A watchdog that is too aggressive
   invalidates facts constantly and degrades the session into perpetual
   re-inspection; one that is too lazy lets decisions run on stale facts. This is
   an open question (17) but also a runtime-quality risk: the balance is where
   "never assume — verify" becomes either unusable or false.

10. **Degraded-mode drift into advice.** In degraded mode (no LLM), the risk is
    that the facts-only presentation slowly starts *recommending* — static,
    context-blind advice that contradicts the very facts it shows. The
    Invariant-9 discipline ("the runtime never fabricates") must cover degraded
    mode explicitly: facts-only means facts only, and silence is safer than
    generic advice.

---

*End of RFC-0002. Normative sections: 2, 3, 4, 9. The remaining sections are
explanatory or forward-looking. Any proposed weakening of an invariant in §9 or a
transition in §2 requires a new RFC or an amendment to this one.*
