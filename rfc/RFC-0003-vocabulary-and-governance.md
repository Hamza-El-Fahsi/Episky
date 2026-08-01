# RFC-0003 — Project Vocabulary and Governance

**Status:** Accepted
**Date:** 2026-08-01
**Scope:** The canonical meaning of every project term; the process by which architecture is decided
**Audience:** Future maintainers
**Supersedes:** Nothing
**Depends on:** RFC-0000, RFC-0001, RFC-0002 (all accepted)

---

## 0. Preamble

This RFC has two parts, and both serve the same goal: **removing ambiguity so
that the project's documents can mean exactly one thing.**

- **Part I** is the project's dictionary: the single, authoritative meaning of
  every core term. All RFCs — accepted and future — are written against these
  definitions. A term used in a sense other than this RFC's is a defect in that
  document.
- **Part II** is the project's constitution: how architecture is proposed,
  reviewed, accepted, amended, and changed. It defines what requires an RFC,
  what does not, and how conflicts are resolved.

RFC-0000 reserved RFC-0003 as the governance document. This RFC deliberately
expands that scope to include the vocabulary, because governance cannot function
when the documents it governs use the same words for different things. The
vocabulary is not decoration; it is the precondition for every other rule in
this document. This expansion is made by the author before acceptance and is
itself subject to the process Part II defines.

No part of this RFC contains implementation details, APIs, or code.

**Reading notes.**
- Part I entries follow a fixed shape: *Definition* (what it is), *Is not*
  (what it is not), *Relates to* (how it connects to other terms).
- "Is not" entries are not optional commentary; they are normative exclusions.
- Where a term already had a definition in RFC-0001 or RFC-0002, this RFC
  consolidates, clarifies, and — where necessary — sharpens it. In any conflict
  with the vocabulary here, the vocabulary wins, because it is the later, more
  precise expression of the same intent.

---

# PART I — CANONICAL VOCABULARY

## 1. Rules Governing the Vocabulary

1. **One meaning only.** Each term has exactly one canonical meaning, defined
   here. There are no dialectical uses within the project.
2. **Binding on all documents.** Every RFC must use these terms in these senses.
   Introducing a *new* term is allowed only if the RFC defines it explicitly and
   flags it for inclusion here (see Part II §11).
3. **Scope discipline.** These definitions describe *architecture*, not
   implementation. Where a term has a popular technical meaning outside the
   project (e.g., "process," "command," "thread"), that meaning is irrelevant
   here unless this RFC says otherwise.
4. **The dictionary is the reference.** When two documents appear to disagree,
   the vocabulary resolves the disagreement: if both are using terms in their
   canonical senses, the documents genuinely conflict and Part II governs.

### Index

| Term | Section |
|---|---|
| Action | 2.6 |
| Approval | 2.6 |
| Approval Token | 2.6 |
| Assistant | 2.1 |
| Audit | 2.8 |
| Boundary | 2.9 |
| Collector | 2.4 |
| Context | 2.8 |
| Diagnosis | 2.5 |
| Evidence | 2.4 |
| Fact | 2.4 |
| Failure | 2.8 |
| Goal | 2.3 |
| Hypothesis | 2.5 |
| Inspection | 2.4 |
| Invariant | 2.9 |
| Machine | 2.2 |
| Machine Identity | 2.2 |
| Machine State | 2.2 |
| Memory | 2.8 |
| Mode | 2.3 |
| Observation | 2.4 |
| Operator | 2.1 |
| Outcome | 2.3 |
| Plan | 2.6 |
| Policy | 2.7 |
| Post-condition | 2.5 |
| Principle | 2.9 |
| Proposal | 2.6 |
| Provider | 2.1 |
| Provider View | 2.8 |
| Recovery | 2.8 |
| Resume Marker | 2.3 |
| Risk | 2.7 |
| Session | 2.3 |
| Skill | 2.7 |
| Step | 2.6 |
| Symptom | 2.3 |
| Transcript | 2.8 |
| Verification | 2.6 |

## 2. The Vocabulary

### 2.1 Actors and System

**Assistant**
- **Definition:** The composite system the Operator interacts with: the
  orchestration core, the deterministic layers (diagnostics, approval,
  execution, audit, context), and whatever providers and skills are in use. It
  is the whole product as experienced.
- **Is not:** The LLM or model alone; not a synonym for "provider"; not a
  remote service; not a person.
- **Relates to:** Contains Providers and Skills as *components*. It is the
  Operator's counterpart. RFC-0001 defines it as "the whole product as the user
  experiences it."

**Operator**
- **Definition:** The human who runs the Assistant on their own machine and
  holds ultimate authority over it. The Operator is the authorization service:
  no state-changing action occurs without their decision (RFC-0001 §8.3).
- **Is not:** The LLM; not an automated agent; not the project's maintainers
  (do not confuse "the Operator of the machine" with "the operators of the
  project"); not a script.
- **Relates to:** Owns the Machine; grants Approvals; is the Assistant's
  counterpart.

**Machine**
- **Definition:** The local Linux system the Assistant is authorized to inspect
  and change — the system whose processes, configuration, and installed
  software the session acts upon. It may be a physical host, a virtual machine,
  or a container environment, determined by where the Assistant runs.
- **Is not:** A fleet or network of machines (RFC-0001 non-goal 6); not the
  cloud account; not the distro's servers; not the Operator's broader
  infrastructure.
- **Relates to:** Described by Facts and Machine State; owned by the Operator;
  the scope of every Inspection and Action.

**Machine Identity**
- **Definition:** The verifiable set of Facts that identify one specific Machine
  across time, used to decide whether a resumed Session is facing the same
  machine. The precise contents are owned by RFC-0014; the concept is canonical.
- **Is not:** Machine State (state changes continuously; identity is meant to
  persist); not a serial number requirement; not a security assertion about the
  machine's health.
- **Relates to:** Machine, Session, Resume Marker, audit continuity.

**Machine State**
- **Definition:** The description of the Machine at a moment in time, expressed
  as the current set of verified Facts together with the known unknowns (facts
  not yet collected, or failed to collect). Always a snapshot; always
  potentially stale.
- **Is not:** The machine itself; not a "should-be" configuration; not a
  permanent record; not a goal.
- **Relates to:** Facts (its substance), Verification (before/after comparison),
  Approval Token scoping, Context/Memory (staleness invalidation).

**Provider**
- **Definition:** The adapter that connects the Core to one LLM backend —
  a vendor service or a local model runtime — through the uniform provider
  contract. It is the *source of model output*, and model output is untrusted
  data (RFC-0001 §7).
- **Is not:** The model itself; not "the AI"; not the Provider View; not a
  person making decisions.
- **Relates to:** Assistant (component), Provider View (what it consumes),
  Mode (availability), RFC-0010 (the contract).

**LLM (the model)**
- **Definition:** The external language model accessed through a Provider. The
  colloquial "the AI" refers to this. It is not a distinct architectural
  component beyond the Provider; the Assistant contains it only through the
  Provider boundary.
- **Is not:** The Assistant; not an authority; not a source of Facts.
- **Relates to:** Provider, untrusted output, RFC-0001 §3.6.

### 2.2 (reserved by the Index layout above — see 2.1 for Machine-family terms)

### 2.3 Session Concepts

**Session**
- **Definition:** One continuous run of the Assistant, from Session
  Initialization to the runtime's end (RFC-0002). It is the container for at
  most one active Goal and for the Session's records: Context, Audit,
  Transcript.
- **Is not:** A terminal window; not a single conversation turn; not the
  provider's chat history; not a "project folder."
- **Relates to:** Goal (at most one), Mode, Resume Marker, Audit/Transcript
  scope, Context lifetime.

**Mode**
- **Definition:** The runtime's provider-availability state: **online** (a
  Provider is usable) or **degraded** (no Provider; facts-only). Modes cut
  across states; they are not states themselves (RFC-0002).
- **Is not:** A user preference; not a property of the Machine; not a skill
  setting.
- **Relates to:** Provider, Diagnosis/Planning (LLM consultation), Failure,
  Recovery, RFC-0002 §2.

**Goal**
- **Definition:** A single troubleshooting objective the Operator asks the
  Assistant to pursue within a Session. A Session holds exactly one active Goal
  at a time (RFC-0002).
- **Is not:** A standing instruction; a background task; an unstated wish; a
  hypothesis.
- **Relates to:** Session, Symptom (its origin), Plan (which serves it),
  Outcome (its termination).

**Symptom**
- **Definition:** The problem as initially reported by the Operator — or
  observed by the Assistant — stated in the Operator's terms. The starting point
  of a Goal.
- **Is not:** The cause; not the Diagnosis; not necessarily technically
  accurate; not evidence.
- **Relates to:** Goal, Diagnosis, Evidence (which tests explanations of it).

**Outcome**
- **Definition:** The terminal result of a Goal: **Completed**, **Failed**, or
  **Cancelled**, as defined in RFC-0002.
- **Is not:** A per-action result (that is an Action's own result, established
  by Verification); not a grade of the Operator's skill.
- **Relates to:** Goal, Verification, Failure, Audit (the outcome is audited).

**Resume Marker**
- **Definition:** A durable record that a Session ended mid-Goal (reboot,
  crash, or exit) so that the Session can be resumed safely under the rules of
  RFC-0002 §8: re-inspect, re-present, re-approve.
- **Is not:** A snapshot of Machine State; not an Approval Token; not a license
  to continue without approval.
- **Relates to:** Session, Machine Identity, Memory, Audit (which the resume
  re-presents).

### 2.4 Knowledge and Evidence

**Collector**
- **Definition:** A deterministic, read-only inspection procedure that produces
  Observations. Each Collector answers one specific question and carries
  declared inputs and provenance behavior.
- **Is not:** An Action (it does not change state); not an LLM-generated
  ad-hoc command; not a "fix."
- **Relates to:** Inspection (runs it), Observation (output), the Fact model
  (RFC-0005), Skills (may bundle collectors).

**Inspection**
- **Definition:** The activity of running Collectors against the Machine;
  always read-only. It is the only activity that produces Observations and,
  through them, Facts.
- **Is not:** Execution; not mutation; not interpretation (interpreting is
  Diagnosis).
- **Relates to:** the Machine Inspection runtime state (RFC-0002), Collector,
  Observation, Verification.

**Observation**
- **Definition:** The raw, timestamped output of one Collector run, carrying
  provenance: which Collector, when, exit status. Untrusted until normalized
  into Facts.
- **Is not:** A Fact (Facts are normalized and checked); not Evidence by
  itself; not a hypothesis.
- **Relates to:** Collector (producer), Fact (normalized form), Evidence,
  Verification (re-observation).

**Fact**
- **Definition:** A normalized, deterministic claim about the Machine, derived
  from Observations, expressed in the canonical fact model, carrying provenance
  and a staleness bound. Facts are the only claims the system treats as
  "known," and they are never LLM-authored (RFC-0001 §3.5).
- **Is not:** An LLM statement; a hypothesis; raw output; an assumption. A
  failed collection produces "fact unknown," which is a Fact in its own right.
- **Relates to:** Observation (source), Evidence (Facts in use), Machine State,
  Context, Verification (re-checked state).

**Evidence**
- **Definition:** The body of Facts — and, where policy permits, raw
  Observations — considered relevant to the current Goal or Hypothesis.
- **Is not:** Everything ever collected; not the LLM's belief; not a verdict.
- **Relates to:** Diagnosis, Hypothesis, Fact, Context.

### 2.5 Interpretation

**Hypothesis**
- **Definition:** A candidate explanation of a Symptom, proposed by the LLM or a
  Skill, to be tested against Evidence. It carries no authority until confirmed
  by deterministic evidence.
- **Is not:** A Fact; not a Diagnosis; not an instruction to act; not a plan.
- **Relates to:** Evidence, Diagnosis, Plan (a grounded Hypothesis becomes the
  basis for a Plan), Verification.

**Diagnosis**
- **Definition:** The process of explaining a Symptom by interpreting Evidence
  into Hypotheses. Its outcome — informally "a diagnosis" — is a set of
  evidence-grounded Hypotheses. Diagnosis is always provisional; it is not a
  fact about the Machine.
- **Is not:** Certainty; a statement of Machine State (Facts are that); an
  Action; a promise.
- **Relates to:** Goal, Symptom, Evidence, Hypothesis, Plan, RFC-0002 (the
  Diagnosis state).

**Post-condition**
- **Definition:** The expected state, expressed as Facts, that an executed
  Action should produce; the target of Verification.
- **Is not:** The Action's exit code; not a guess; not the LLM's description of
  success.
- **Relates to:** Step, Action, Verification.

### 2.6 Decision and Action

**Proposal**
- **Definition:** A candidate Action or Plan offered by the LLM, a Skill, or the
  Core for consideration. It is not yet classified, not yet approved, and not
  yet executed.
- **Is not:** An approved Action; not a command; not an instruction the machine
  must obey.
- **Relates to:** Plan, Action, Approval, Provider View (proposals travel from
  the untrusted side through the gate).

**Plan**
- **Definition:** A goal-scoped, ordered set of Steps proposed to achieve a
  Goal, normalized into discrete proposed Actions, subject to classification
  and Approval. Planning never executes (RFC-0002 invariant 3).
- **Is not:** The Goal; not executable on its own; not the LLM's raw text
  (plans are normalized by the Core); not a preference.
- **Relates to:** Goal, Step, Action, Approval, Verification, Replanning.

**Step**
- **Definition:** One element of a Plan: an Action positioned in sequence,
  together with its preconditions, expected Post-condition, and verification
  method.
- **Is not:** An Action in the abstract. An Action is the reusable capability;
  a Step is that Action's specific use in a particular Plan.
- **Relates to:** Plan, Action, Post-condition, Verification.

**Action**
- **Definition:** The atomic unit of work the Executor can run, carrying a
  description, risk-relevant properties, and verification criteria. It is the
  unit of Approval and of Execution. The word "command" is not a first-class
  architectural term; a command is one possible *implementation* of an Action.
- **Is not:** A shell string; not a Plan; not a Step by itself; not a
  recommendation.
- **Relates to:** Step, Proposal, Approval, Risk, Executor, Verification,
  Post-condition.

**Verification**
- **Definition:** The deterministic confirmation that an executed Action
  produced its expected Post-condition, obtained by re-observation and
  state comparison (RFC-0002 invariant 2). Verification is never the LLM's
  assessment and never "the command exited zero."
- **Is not:** An opinion; optional after Execution; a claim that the Goal is
  wise (it confirms state, not intent); a synonym for "testing."
- **Relates to:** Post-condition, Observation, Fact, Replanning, the
  Verification runtime state.

**Approval**
- **Definition:** The Operator's explicit authorization of a specific Action or
  Plan, granted after the Approval & Policy Engine has classified it, and
  recorded as an Approval Token. Approval is a decision; the Token is its
  scoped, consumable record.
- **Is not:** Silence; an "always yes"; the LLM's permission; the Project's
  permission. A standing approval is a Policy construct that still expires and
  never becomes blanket authority (RFC-0001 §8.3).
- **Relates to:** Policy (which decides the gate), Risk, Action, Executor,
  Audit, the Awaiting Approval state.

**Approval Token**
- **Definition:** The durable, scoped, consumable record of an Approval: bound
  to its Action, its time, and the Machine State it was approved against. It is
  invalidated by a state change, an interrupt, a reboot, or a policy reload
  (RFC-0002 invariant 11).
- **Is not:** A license for arbitrary actions; a reusable pass; a memory of
  intent.
- **Relates to:** Approval, Executing (the boundary re-validates it), Policy,
  Invariant 11.

### 2.7 Governance of Behavior

**Policy**
- **Definition:** The deterministic rules governing what may be done: risk
  classification, default-deny, allowlists, elevation limits, standing-approval
  bounds. Policy is local, deterministic, and never LLM-authored (RFC-0001 §8.5).
- **Is not:** An Approval (a per-case human decision); not a recommendation;
  not the LLM's opinion; not Configuration in general (Configuration sets
  preferences; Policy sets limits — the boundary is specified by RFC-0008/0016).
- **Relates to:** Risk, Approval, the Approval & Policy Engine (RFC-0008),
  default-deny.

**Risk**
- **Definition:** The classification of a proposed Action, assigned
  deterministically by the Approval & Policy Engine, into a risk class and its
  associated gate (e.g., auto-permitted, confirm, confirm-with-warning,
  blocked). The exact taxonomy is owned by RFC-0008; the concept is canonical.
- **Is not:** The LLM's self-assessment; subjective "danger"; probability of
  harm as estimated by the model.
- **Relates to:** Policy, Approval, Action, Gate.

**Skill**
- **Definition:** A packaged, versioned, authenticated troubleshooting
  procedure: diagnostics, explanations, and gated Action sequences, bundled with
  declared targets, privileges, risk, and verification. Untrusted by default
  until authenticated and within Policy; a candidate like any LLM output
  (RFC-0001 §11).
- **Is not:** Core behavior; a Provider; a "mode"; a forum post or a set of
  notes without the packaging contract.
- **Relates to:** Collector, Plan, Approval, the extension system (RFC-0011).

### 2.8 Memory and Record

**Context**
- **Definition:** The sanitized, purpose-limited, size-bounded, secret-free set
  of Facts, history, Goal, and skill material that the runtime holds for
  reasoning. It is the only thing a Provider ever receives, delivered as a
  Provider View (RFC-0002).
- **Is not:** Everything collected; raw output; durable by default; the audit.
- **Relates to:** Fact, Evidence, Provider View, Memory, Context Building,
  RFC-0001 §9.

**Provider View**
- **Definition:** The specific, sanitized representation of Context assembled
  for a single Provider call. It is produced only by Context Building and
  contains no secrets (RFC-0002).
- **Is not:** Raw Context; a transcript dump; the Provider's own chat state.
- **Relates to:** Provider, Context, Context Building, RFC-0009 (no secrets).

**Memory**
- **Definition:** The portion of Context the runtime is authorized to retain
  beyond immediate need — the durable subset — kept only by explicit Operator
  consent and subject to purpose-limits (RFC-0001 §9).
- **Is not:** Everything said; the Audit (Memory is for reasoning; Audit is for
  record); a cache of raw output.
- **Relates to:** Context, Consent, RFC-0012.

**Audit**
- **Definition:** The durable, append-only, tamper-evident record of
  consequential events — proposals, classifications, approvals, overrides,
  executions, verifications, outcomes — written *before* each consequence is
  allowed to proceed (RFC-0002 invariant 13). Its purpose is transparency, not
  forensics (RFC-0001 risk 8).
- **Is not:** The Transcript; a security evidence chain; Memory; a log of
  everything the model said.
- **Relates to:** Approval, Action, Verification, Outcome, Transcript, the
  Operator (who may read it at any time).

**Transcript**
- **Definition:** The human-readable account of the Session as experienced: the
  dialogue and the actions, derived from the record. It is the Operator-facing
  view of what happened.
- **Is not:** The authoritative record by itself (the Audit is authoritative);
  not a diagnostic artifact.
- **Relates to:** Audit, Operator, Session.

### 2.8.1 Failure and Recovery

**Failure**
- **Definition:** Any event or outcome that is not the intended one: a failed
  Action, a failed Collector, an unavailable Provider, a failed Verification,
  an unreachable Goal. A Failure is a reportable fact — never hidden, and never
  papered over with a guess (RFC-0001 §10).
- **Is not:** A state of the Machine; a judgment of the Operator; a reason to
  fabricate.
- **Relates to:** Recovery, Replanning, Outcome, Verification.

**Recovery**
- **Definition:** The runtime's defined response to a Failure, in a fixed order:
  establish the actual state deterministically, disclose it to the Operator,
  obtain the Operator's decision, then act on approval. Recovery never starts
  from an assumption (RFC-0002 §10).
- **Is not:** Automatic rollback (rollback is itself an Action requiring
  Approval); "try something and hope"; pretending nothing happened.
- **Relates to:** Failure, Replanning, Verification, the Interrupted state.

### 2.9 Constitutional Terms (used by Part II)

**Principle**
- **Definition:** A ranked rule from RFC-0001 §3 that states what the project
  values and how conflicts between values are decided.
- **Is not:** A preference; an implementation note.
- **Relates to:** The decision hierarchy in Part II §8.

**Boundary**
- **Definition:** A line drawn by RFC-0001 §6 or §7 stating what is inside the
  project, what is outside, and what is trusted or untrusted.
- **Is not:** A cosmetic border; a convention.
- **Relates to:** The decision hierarchy, breaking changes.

**Invariant**
- **Definition:** A rule in an accepted RFC that no implementation may violate
  and no later RFC may weaken except by amendment (the principal set is
  RFC-0002 §9).
- **Is not:** A guideline; a performance note.
- **Relates to:** The decision hierarchy, breaking changes.

---

# PART II — GOVERNANCE

## 1. Normative Status and Precedence

1. **Accepted** RFCs are normative. Draft and Planned RFCs are not normative
   and must not be relied upon by implementation.
2. **Decision hierarchy.** When documents conflict, this order decides, highest
   first:
   1. **Principle** (RFC-0001 §3)
   2. **Boundary** (RFC-0001 §6–7)
   3. **Invariant** (RFC-0002 §9 and invariants in later RFCs)
   4. **Definition** (this RFC, Part I)
   5. **Contract** (later RFCs: fact model, approval engine, provider contract,
      skill contract, etc.)
   A lower document must conform to a higher one. Changing a higher document is
   always a breaking change (see §5).
3. **Later-is-not-stronger.** An RFC is not allowed to contradict an earlier
   accepted RFC merely because it is newer. It may contradict an earlier RFC
   *only* by explicitly amending or superseding it, with that amendment accepted
   through this same process (§4). Otherwise the earlier RFC stands.
4. **Silent violation is a design defect.** If a contradiction is discovered
   after acceptance, the RFC Editor rules, the resolution is recorded, and a
   clarifying amendment is issued. It is never resolved by "the implementers
   will sort it out" (RFC-0001 §0).

## 2. Statuses and Lifecycle

An RFC passes through these statuses:

- **Planned** — a number is reserved and a title/purpose is recorded in
  RFC-0000. Not normative.
- **Draft** — being written. Not normative. A Draft may be revised, withdrawn,
  or promoted.
- **Accepted** — approved and normative. It is the reference for everything
  that depends on it.
- **Amended** — Accepted, with one or more recorded normative amendments (§4).
  Still normative in its amended form; the amendment log is part of the
  document.
- **Superseded** — replaced by a later RFC that explicitly takes its place.
  Retained for history; its content is no longer normative to the extent
  superseded.
- **Withdrawn** — was a Draft (or Planned) and was retracted before
  acceptance. Retained in the index as history; never normative.

Lifecycle: reserved in RFC-0000 (Planned) → written (Draft) → reviewed →
Accepted → maintained (Amended) → possibly Superseded.

## 3. How an RFC Is Accepted

**Roles.** The **RFC Editor** maintains RFC-0000 and the vocabulary, shepherds
Drafts, rules on borderline cases, and records decisions. **Reviewers** are the
project's maintainers, joined for open-source by a community review window.
**Decision** rests with the maintainers; the Editor ensures the process is
followed and records the rationale. Anyone may author a Draft.

**Process.**
1. **Reserve.** The author requests a number from the Editor; RFC-0000 is
   updated to Planned.
2. **Draft.** The author writes the RFC. It must:
   - depend only on Accepted RFCs (no speculation on Drafts);
   - use the canonical vocabulary of this RFC, or define any new terms and flag
     them for inclusion;
   - separate normative from non-normative sections;
   - name its dependencies;
   - enumerate its open questions;
   - state whether it is **BREAKING** (§5).
3. **Review.** The Draft is announced with a review window. The window is
   longer for BREAKING changes. Reviewers check:
   - consistency with all Accepted RFCs (through the decision hierarchy);
   - vocabulary compliance;
   - absence of scope drift (RFCs specify architecture, not implementation);
   - whether the open questions are honest;
   - for BREAKING changes, whether the enumerated impact is complete.
4. **Decision.** The maintainers accept, reject, or return the Draft for
   revision. Objections must be either resolved or recorded as risks or open
   questions — acceptance does not require unanimity, but it does require that
   unresolved objections be visible.
5. **Record.** RFC-0000 is updated (status, gate). The acceptance rationale and
   any recorded objections are stored with the document.

**Rejection is a valid outcome** and is recorded with reasons. A rejected RFC
may be revised and resubmitted.

## 4. How an RFC Is Amended

**Editorial amendment** — changes to wording that do not alter meaning (typos,
formatting, clarification that restates the same intent). No process beyond the
Editor's edit; no status change.

**Normative amendment** — changes the meaning of an Accepted RFC: a definition,
an invariant, a boundary, a contract guarantee, or a transition rule. It
requires:
1. An **amendment RFC** (or an amendment section within a new RFC), which must:
   - quote the original text it changes;
   - state the replacement text;
   - explain why the change does not violate higher documents, or amend them in
     the same change;
   - be labeled **BREAKING** if it weakens an Invariant or a Definition (see §5).
2. The same acceptance process as a new RFC (§3).
3. Recording in the amended document's **amendment log** and in RFC-0000.

**Supersession** — a full replacement of an RFC. It is an amendment that
explicitly retires the earlier document's normative status. It follows the same
process and must be labeled BREAKING.

The default position is that amendments are **additive**: they extend an RFC
rather than rewrite it. This RFC's own vocabulary can be amended only by this
process; the vocabulary is not subject to silent revision during review of
other RFCs.

## 5. How Breaking Architectural Changes Happen

**Definition.** A change is **BREAKING** if it requires existing conforming
behavior to change: altering a Principle, a Boundary, an Invariant, or a
canonical Definition; narrowing the meaning or scope of a Contract; or
withdrawing a promise (e.g., a verification or compatibility guarantee).

**Rules.**
1. A breaking change exists only as an **explicitly labeled BREAKING RFC** (or
   BREAKING amendment). There is no breaking change by implementation, and no
   breaking change smuggled into an unrelated RFC.
2. A BREAKING RFC must enumerate, item by item: which Principles, Boundaries,
   Invariants, Definitions, and Contracts it changes, with the before/after.
3. A BREAKING RFC receives a longer review window and requires a recorded
   decision with rationale.
4. **The default bias is rejection.** The constitution is deliberately
   conservative. A BREAKING change must justify itself in the project's own
   terms — safety first, then clarity, then convenience (RFC-0001 §3).
5. A BREAKING change that is accepted must state the intended fate of existing
   conforming artifacts (skills, sessions, stored Context, configurations) even
   when the mechanics belong to later RFCs.
6. If a breaking change is rejected, the earlier behavior stands and the Draft
   must be revised against it.

## 6. What Requires a New RFC

Any of the following requires a new RFC (or an amendment RFC):

1. A change to a Principle, Boundary, Invariant, or canonical Definition.
2. A new subsystem or architectural component, or a change in how components
   relate.
3. A change to the runtime state machine: a new state, a new transition, a
   change to event semantics (RFC-0002).
4. A new or changed extension contract: the provider contract, the skill
   format, the fact model.
5. A change to approval or policy semantics: the risk taxonomy, the gates,
   elevation, standing approvals, the read-only allowlist.
6. A change to trust boundaries or data-flow rules (RFC-0001 §7; RFC-0007 once
   accepted).
7. A new persistent store, or a change to what is persisted (Context, Memory,
   Audit scope, resume markers).
8. A new Goal or Non-Goal for the project, or a change to what is inside or
   outside the project (RFC-0001 §6).
9. A new normative guarantee: a verification promise, a rollback promise, a
   compatibility promise.
10. Anything the RFC Editor judges to be load-bearing for future maintainers'
    ability to reason about the design.

The rule of thumb: **if a later maintainer would need to know it to avoid
violating design intent, it belongs in an RFC.** When in doubt, the author asks
the Editor; the Editor's ruling is recorded.

## 7. What Does Not Require a New RFC

1. Typos, formatting, and clarifying non-normative wording.
2. Implementation of an accepted contract: a new Provider adapter, a new
   Collector, a new Skill instance, a new diagnostic — instances, not the
   contracts themselves.
3. Bug fixes that restore the behavior the Accepted RFCs already specify.
4. Performance or robustness work that preserves every Invariant and every
   semantic.
5. Internal refactoring with no observable behavior change.
6. Operating parameters that this RFC delegates to the maintainers (review
   window length, quorum, Editor rotation — see §12).
7. Anything the Editor routes to a decision note instead (§8). If a decision
   note later turns out to be normative, it is promoted to an amendment.

**Fast track.** For borderline cases, the Editor may issue a **decision note**
(a dated, recorded ruling) rather than opening a full RFC. A decision note adds
no normative content by itself; it clarifies how existing Accepted content
applies. If a decision note would change meaning, it is not a decision note —
it is an amendment, and the Editor says so.

## 8. The Architectural Decision Process

1. **Full RFC** for everything in §6: normative, structural, or contract-level.
2. **Decision note** for clarification of how Accepted content applies to a new
   situation, with no change to that content.
3. **Decision hierarchy** for resolving conflicts (repeated from §1):
   Principle > Boundary > Invariant > Definition > Contract. A lower document
   found to contradict a higher one is defective and must be amended; the higher
   one stands meanwhile.
4. **Escalation.** Any participant (author, reviewer, implementer) may escalate
   a disagreement to the Editor, who rules and records. A ruling that touches
   normative content is, by definition, an amendment and follows §4.
5. **No decision by silence.** An unresolved question that affects normative
   content is either answered by an RFC, deferred as an explicitly recorded open
   question, or rejected — never allowed to quietly resolve during
   implementation.

## 9. Backwards Compatibility Philosophy

1. **Accepted normative content is stable.** The default change is additive;
   the project extends rather than rewrites.
2. **Compatibility classes.**
   - **Additive** — adds capability without changing existing meaning. Always
     allowed.
   - **Compatible** — same meaning, broader application. Allowed with a normal
     RFC.
   - **Breaking** — meaning or scope narrowed, or a promise withdrawn. Only via
     the BREAKING process (§5).
3. **Compatibility is a property of contracts.** It applies to canonical
   meanings (Part I), Invariants (RFC-0002 §9), and accepted contract guarantees
   (provider, skill, fact model) — not to internal implementation.
4. **History is preserved.** RFC numbers are never reused. Withdrawn and
   Superseded RFCs remain in RFC-0000 so the reasoning trail survives.
5. **Migration intent is mandatory.** Every accepted BREAKING change states what
   happens to existing conforming artifacts, even if the mechanics are delegated.
6. **Silently violating a boundary is a design defect** (RFC-0001 §0), and a
   defect discovered after the fact is repaired by amendment, not by
   reinterpretation.

## 10. Roles and Authority

- **RFC Editor** — maintains RFC-0000 and this RFC's vocabulary; shepherds
  Drafts; rules on borderline cases; records decisions and decision notes.
  Consistency of vocabulary and index is the Editor's responsibility.
- **Maintainers** — hold the Decision authority; accept or reject RFCs and
  amendments; review BREAKING changes with recorded rationale.
- **Reviewers (community)** — review Drafts during the window; their objections
  must be resolved or recorded.
- **Authors** — anyone may author a Draft; authorship grants no authority over
  acceptance.
- **Implementers** — may not weaken Accepted content; may request amendments
  through the process. An implementer's discovery of a contradiction is an
  escalation (§8.4), never a license to deviate.

## 11. Vocabulary Governance

1. New terms introduced by any RFC must be defined at the point of use and must
   be added to Part I of this RFC by amendment (additive, normal process).
2. No RFC may use an existing term in a sense other than this RFC's canonical
   sense. A document that appears to do so is defective and returns to review.
3. The Editor is the custodian of the vocabulary: the Editor may issue
   editorial clarifications (no meaning change) without a full amendment.
4. A meaning change to any term is a BREAKING change, because every RFC that
   uses the term inherits the change.

## 12. Open Questions

These are the parameters this constitution deliberately leaves to the
maintainers to set. They are delegated, not unsettled architecture:

1. **Review window length.** What is the minimum window for a normal RFC, and
   for a BREAKING RFC? (Delegated; recorded in RFC-0000.)
2. **Decision quorum.** How many maintainers must act to accept an RFC, and
   must BREAKING changes require unanimity of the acting maintainers?
3. **Editor rotation.** Is the Editor a standing role or a rotating one? How is
   a dispute about the Editor's ruling itself resolved?
4. **Decision-note storage.** Whether decision notes live in RFC-0000, a
   separate decisions log, or inline. (This RFC assumes a decisions log under
   the Editor's custody; confirm.)
5. **Community process.** Whether community-authored RFCs require a sponsoring
   maintainer, and whether BREAKING RFCs require a community-wide review beyond
   the maintainers.
6. **The "implementers disagree" rule.** Whether an implementer may open a
   Draft amendment directly, or must first obtain a decision note. (This RFC
   allows either; the maintainers may narrow it.)

Until these are set, the default operating values are: a one-week window for
normal RFCs, two weeks for BREAKING, acceptance by a majority of acting
maintainers, and the Editor as the sole decision-note authority.

---

*End of RFC-0003. Normative: Part I in full; Part II §1–§9 and §11. Explanatory:
Part II §10, §12. Any proposal to change a meaning in Part I or a rule in Part
II §1–§9 is a BREAKING change and must be made by amendment.*
