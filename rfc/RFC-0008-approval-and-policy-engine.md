# RFC-0008 — Approval & Policy Engine

**Status:** Draft
**Date:** 2026-08-02
**Scope:** When the Assistant is allowed to modify the user's machine: risk
classification and gates, approval granularity and plan approval, approval
tokens and their lifecycle, preconditions and TOCTOU protection, standing
approvals and elevation, the read-only allowlist, overrides, retry policy, and
fail-closed behavior on policy errors
**Audience:** Future maintainers
**Supersedes:** Nothing
**Depends on:** RFC-0001, RFC-0002, RFC-0003, RFC-0004, RFC-0007 (accepted).
RFC-0021 is referenced for the machine's subsystem and state-domain vocabulary
but is itself a Draft and is not a dependency.

**Roadmap note:** This is RFC-0000's "RFC-0008 — Approval & Policy Engine"
(Security, Required), the fourth document in the safety spine and the single
highest-blast-radius document in the corpus (RFC-0000 §5, §6). It answers the
coverage rows RFC-0000 §8 assigns to it: RFC-0001 Q1–Q5, Q23; RFC-0002 Q1–Q4,
Q7, Q13.

**BREAKING:** No. This RFC specifies the taxonomy and mechanics RFC-0001,
RFC-0002, RFC-0004, and RFC-0007 already assume — the gates, risk classes,
tokens, standing approvals, elevation, allowlist, and override. It does not
weaken any Principle, Boundary, Invariant, or canonical Definition in an
accepted RFC.

---

## 0. Preamble

RFC-0001 set the principle — human approval before risky action, no standing
authorization — and named the risk classes and gates it left for this RFC to fix
(RFC-0001 §3 principle 2, §5, §8.3, Q1–Q5). RFC-0002 made the gate a runtime
invariant and fixed where the Approval & Policy Engine is consulted (RFC-0002
invariants 1, 6, 7, 11–13, 15; §6.2). RFC-0004 fixed *who* may approve (the
Operator) and the flow — Proposal → Policy classification → Approval → token →
Executor → Verification — delegating the gates' *taxonomy and mechanics* here
(RFC-0004 §10). RFC-0007 fixed the trusted/untrusted frame (RFC-0007 §4.4).
This RFC answers the question those documents left open:

> **When is the Assistant allowed to modify the user's machine?**

It defines approval; it does **not** define authority (RFC-0004), trust
(RFC-0007), facts (RFC-0005), verification (RFC-0006), secrets (RFC-0009),
provider contracts (RFC-0010), or the skill format (RFC-0011), deferring to
each owning RFC (RFC-0003 Part II §1).

---

## 1. Purpose

This RFC specifies the constitutional approval system of the project. It
answers one question only:

**When is the Assistant allowed to modify the user's machine?**

It makes the accepted documents' approval rules concrete and testable — the
approval philosophy (§4), the approval unit (§5), deterministic risk classes and
gates (§6), the Policy Engine (§7), the Approval Token lifecycle (§8),
preconditions (§9), TOCTOU protection (§10), plan approval (§11), the mandatory
content of approval presentation (§12), the enforceable invariants (§13), and
per-attack abuse analysis (§14) and failure behaviour (§15).

The result is one constitutional sentence: *the human decides what changes the
machine; the engine makes that decision meaningful, scoped, and honest.*

---

## 2. Scope

This RFC is about the **approval decision and its enforcement**, not about the
actors who hold authority, the trust of the information involved, or the
mechanics of the machine.

In scope: the approval unit and plan approval (§5, §11); risk classification
and gates (§6); the Policy Engine's responsibilities (§7); approval tokens and
their lifecycle (§8); preconditions and TOCTOU protection (§9–§10); the
mandatory content of approval presentation (§12); the approval invariants
(§13); abuse analysis and failure behaviour (§14–§15).

Out of scope by construction, each detailed in §3: who may approve and the
authority flow (RFC-0004); the trust of information (RFC-0007); facts and
verification (RFC-0005, RFC-0006); secrets (RFC-0009); provider and skill
contracts (RFC-0010, RFC-0011); context assembly (RFC-0012); the audit record
(RFC-0013); session persistence and resume (RFC-0014); the approval interface
(RFC-0015).

This RFC is **architecture only**: it fixes rules, guarantees, and invariant
properties. It specifies no APIs, no pseudocode, no algorithms, no programming
language, no shell commands, no JSON, no YAML, no UI mockups, and no data
formats. Every normative statement remains valid regardless of implementation
language. It does not name an elevation *mechanism* — the machine's own
mechanism is assumed by RFC-0021 §3.3 — it specifies elevation *semantics*.

---

## 3. Non-Scope

The following topics belong to other RFCs. Whenever this RFC would otherwise
need them, it defers rather than partially specifying.

- **Authority, actors, ownership, the authority matrix, and who may approve** —
  RFC-0004. The Operator is the Approver; the engine is the Operator's
  instrument (RFC-0004 §4.8).
- **The fact model and diagnostics** — RFC-0005: how Observations become Facts,
  provenance, staleness. This RFC only consumes Facts as classification inputs
  and as the state preconditions and verification compare against.
- **Verification and rollback semantics** — RFC-0006: what counts as verified
  and what the project promises about rollback. Approval and verification are
  separate gates in sequence; RFC-0006 fixes what verification is.
- **Secrets, privacy, sensitive-data lifecycle** — RFC-0009: how secrets are
  stored and redacted. This RFC fixes that no Action may carry a secret into a
  provider view and that elevation never exposes secrets.
- **Provider contract and adapters** — RFC-0010. **Skill contract and
  ecosystem** — RFC-0011. Skills propose Actions that pass the same gate
  (RFC-0004 A3); the skill *format* is RFC-0011's.
- **Context, memory, and sanitization mechanics** — RFC-0012. This RFC fixes
  what the gate is; RFC-0012 fixes where sanitized Context is assembled.
- **Audit and transcript mechanics** — RFC-0013. This RFC fixes the approval
  events that must be recorded before their consequences.
- **Session persistence and resume** — RFC-0014 (Post-MVP). Reboot and
  interrupt invalidate approvals here; RFC-0014 fixes how the session resumes.
- **The approval interface / UX** — RFC-0015: how the mandatory content of §12
  is presented. This RFC fixes what must be shown.
- **Machine subsystem and state-domain modeling** — RFC-0021: the vocabulary
  (packages, services, configuration, network, users, storage, security state)
  that risk-relevant Action properties describe.

---

## 4. Approval Philosophy

Six theses define what approval is in this system. Each is load-bearing; the
invariants in §13 are their enforceable form.

1. **The human remains the final authority.** Only the Operator approves
   state-changing work, and approval is a decision, not a ceremony. The Approval
   Engine is the Operator's instrument, never the decision-maker (RFC-0004
   §4.8), and no mechanism substitutes for the Operator's decision (RFC-0001
   §8.3).
2. **Approval is explicit.** Nothing proceeds on silence, absence, or implied
   consent. Approval is a positive, recorded act over a specific proposal —
   never "no answer after ten seconds means yes." The friction of deciding is a
   feature: the Operator must make the decision they are asked to make.
3. **Approval is contextual.** An approval is a decision *about this machine,
   this moment, this plan*, bound to the Action, the machine state it was shown
   against, and the time it was given (RFC-0002 invariant 11).
4. **Approval is revocable.** The Operator may cancel, reject, refuse, or
   override at any point (RFC-0001 principle 11). Revocation before execution
   invalidates the token; revocation during execution halts what can be halted
   and re-assesses the rest (RFC-0002 §8).
5. **Approval is consumable.** Approval is spent by use. A token covers one
   Action (or one approved plan envelope, §11); it is consumed by execution or
   by expiry, and it is never reused (RFC-0002 invariant 11). There is no
   standing approval for "whatever is needed" (RFC-0001 §8.3).
6. **Approval never implies trust.** Approving an Action says nothing about the
   truth of the facts behind it, the honesty of the proposer, or the safety of
   the proposing actor (RFC-0004 §2: Trust and Authority are separate). The
   proposing LLM or Skill gains no trust, no authority, and no power from a
   single approval (RFC-0007 §8).

---

## 5. Approval Unit

Approval is never granted to a raw command, a role, a session, or a skill. It
is granted to exactly one of two objects, called the **Approval Unit**:

**The Action — the atomic approval unit.** An Action is the unit of Approval
and of Execution (RFC-0003 §2.6): a structured object with a description,
risk-relevant properties, and verification criteria, bound to one change to the
machine. A command is not an approval unit — a command is one possible
*implementation* of an Action, and the Operator never approves a shell string
(RFC-0003 §2.6; RFC-0007 T1, T2).

**The Plan — the composable approval unit.** A Plan is an ordered set of Steps,
each Step being one Action with its preconditions, expected Post-condition, and
verification method (RFC-0003 §2.5). A Plan may be approved as a whole envelope
(§11). Envelope approval is *not* approval of the Steps one by one at a
distance; it is a single judgment over a fully shown, ordered, classified set
of Steps, and every Step still passes the gate and re-validates at its own
execution boundary (§9).

What is not an Approval Unit:

- **A single command** — commands are implementations of Actions, never
  approved directly (RFC-0007 T1).
- **A logical action spanning several machine changes** — if the intended
  change needs more than one atomic machine change, it is a Plan of Actions;
  each change is separately classified.
- **An execution step in isolation** — a Step is approved as part of the
  envelope or, after a deviation, as its own Action (§11).
- **A Skill** — a Skill is never approved as a unit; only its individual
  Actions pass the gate, the same as any other (RFC-0004 A3).
- **A rollback operation** — reverting is itself a state-changing Action and
  requires its own approval (RFC-0002 §10).
- **A session or a goal** — there is no approval "for this goal" or "for this
  session" (RFC-0001 §8.3).

**Why this architecture.** The Action is the unit the accepted RFCs already
assume (RFC-0003 §2.6; RFC-0002 invariant 1; RFC-0004 A9), the smallest object
classifiable deterministically, and the object the Executor runs. Making the
Plan an *envelope* — not a delegation — keeps the rubber-stamp risk in view: the
Operator judges a fix once, as a whole (RFC-0001 §13 risk 1), but no Step
escapes classification, re-validation, or verification (RFC-0002 invariants 1,
2, 6). This answers RFC-0001 Q2: granularity is per-Action and per-Plan-envelope,
never per-session.

---

## 6. Risk Classification

Every proposed Action is assigned exactly one **Risk Class** and one **gate** by
the Policy Engine, deterministically, from the Action's structured description
and the Facts it is built on — never from the proposing actor's
characterization (RFC-0002 invariant 7; RFC-0001 §8.5). The LLM does not grade
its own actions. Classification is **per-Action** (RFC-0001 Q1); a Plan's class
is the **meet of its Steps' classes** — the most restrictive among them
(RFC-0007 §5.1).

The gate set is the four gates RFC-0000, RFC-0002, and RFC-0004 name:
**auto-permitted, confirm, confirm-with-warning, blocked**. RFC-0001 §5's
"silent (read-only)" and "notify" are the two *presentation* faces of the
auto-permitted gate for allowlisted read-only Actions — such Actions run
without a per-case decision but are still classified and audited (RFC-0002
§2.7).

| Risk Class | What it means | Gate |
|---|---|---|
| **Read-only (Inspection)** | Observes machine state; changes nothing; runs through the Diagnostics contract (RFC-0004 A4) | Auto-permitted if inside the read-only allowlist; otherwise Confirm |
| **Benign** | Mutates state recoverably and narrowly: within one user-owned or session-relevant surface; reversible; deterministic verification available | Confirm |
| **Consequential** | Mutates state that affects system behavior broadly, or is slow or uncertain to reverse: system-wide configuration, services, network, boot-affecting, or anything requiring elevation | Confirm-with-warning |
| **Destructive** | Irrecoverable or security-critical: erasure, boot or security-state damage, mass package removal, anything that can strand or lock out the system | Blocked (proceeds only by explicit, audited override) |

The class is read from **deterministic properties of the Action**, drawn from
its structured description and referenced Facts, using RFC-0021 §6's State
Domains as the vocabulary: whether the Action mutates a State Domain or only
reads it; which subsystems it touches — packages, services, configuration,
network, users, storage, security state (RFC-0021 §4, §6); whether it uses the
machine's elevation mechanism (RFC-0021 §3.3); whether the change is reversible
and how verification confirms it (RFC-0006); and whether a wrong execution
could prevent the machine from booting, authenticating, or reaching the
Operator.

No rule uses a percentage, a probability, a severity score, or the proposer's
words. A class is a membership test over these properties; class boundaries are
fixed by Policy, adjustable only within the Operator's authority (RFC-0004 §3).

**The read-only allowlist** is the set of read-only Actions Policy pre-approves
as auto-permitted. The project ships a default allowlist (the deterministic
Inspections and Collectors of the Diagnostics contract); the Operator may widen
or narrow it within their authority (RFC-0004 §3). This answers RFC-0001 Q4 and
RFC-0002 Q4: default-deny applies to read-only work too; the allowlist is the
explicit pre-approved set.

**The override.** A Blocked Action is not executable by default. The Operator
may override a Block, because the Operator owns the machine (RFC-0001 principle
11), but the override is itself a decision: presented with its own warning,
recorded, and scoped to the one Action (RFC-0002 invariant 12; §13 P10). Policy
may declare specific Actions **absolutely blocked** — overridable only by
changing Policy itself, never by a per-case override. This answers RFC-0002
Q13: a Policy-classification block is reversible within a session; a block
declared absolute by the Operator's own Policy is reversible only by changing
that Policy.

Examples (illustrative, not exhaustive):

| Class | Examples |
|---|---|
| Read-only | collecting a package list, reading a service status, checking disk usage (inside the allowlist); reading a non-allowlisted config (Confirm). |
| Benign | installing a package from the configured repository, restarting a user service, editing a user-level configuration file. |
| Consequential | changing system-wide configuration, toggling a system service, modifying network settings, editing boot configuration, any elevated Action. |
| Destructive | removing packages the system depends on, erasing or formatting, modifying security state (accounts, credentials, firewall) so as to lock out the Operator, rolling back system packages. |

The gate is **decided before presentation** and is never re-derived by the
presentation or by the Operator's response (RFC-0007 §4.4; §13 P4).

---

## 7. Policy Engine

The Policy Engine is the deterministic component that decides what *may* be
proposed onward (RFC-0004 §4.7): it classifies every proposed Action into a
Risk class and gate, and applies Policy — default-deny, allowlists, elevation
limits, standing-approval bounds. It has no Approve, no Execute, and no Observe
authority (RFC-0004 A6): it never executes, never reads raw untrusted text to
classify against (RFC-0007 T2), and never decides whether the Operator approves.
The Approval concern (risk classification) and the Policy concern (default-deny,
elevation, scope, standing approvals) are two faces of this one deterministic
engine, always applied together (RFC-0002 §6.2).

Three responsibilities, and nothing else:

| Responsibility | What it does |
|---|---|
| **Policy evaluation** | Turn Policy (RFC-0003 §2.7) — the deterministic rules the project ships and the Operator sets within their authority — into a decision about a specific Action: which class, which gate, whether allowlisted, whether elevation is permitted and to what bound, whether a standing approval applies and is in scope and unexpired. Consumes only the Action's structured description and Facts; never provider output, skill content, or the proposer's claim. |
| **Policy decision** | Produce exactly one outcome: a Risk class and gate, with warning grounds (confirm-with-warning) or reason (blocked). Where no rule matches, the decision is **blocked** — default deny and fail closed (RFC-0001 §8.2, §8.12). A deterministic function of its inputs; never consults the LLM. |
| **Policy enforcement** | Make the decision stick at both edges where RFC-0002 consults the engine (§6.2): Planning → Awaiting Approval (every proposed Action is classified and gated) and Awaiting Approval → Executing (the token is re-validated against current policy, elevation, and machine state). Re-validates outstanding approvals on configuration reload (RFC-0002 §4.7). The engine refuses to let anything it did not classify and gate reach the Executor — and the Executor independently refuses anything not carrying a valid token (RFC-0004 A2; RFC-0002 invariant 11). |

The engine never loosens the Operator's bounds on its own; on any error it
blocks rather than loosens (fail closed, §13 P3; RFC-0004 §9.7).

---

## 8. Approval Tokens

An Approval Token is the durable, scoped, consumable record of an Approval: a
decision plus a specific right to spend it, bound to its Action, its time, and
the Machine State it was approved against (RFC-0003 §2.6; RFC-0002 invariant
11). It is the only thing that carries permission to the Executor (RFC-0004
A2).

**Creation.** The Approval Engine mints the token only after (a) the Policy
Engine has classified and gated the Action, and (b) the Operator has made an
explicit decision — approve, auto-permit (an allowlisted read-only Action), or
override (a blocked Action). Issuance is written to the Audit before execution
may proceed (RFC-0002 invariant 13; RFC-0004 A10).

**Ownership.** The token is issued on the Operator's authority; the Approval
Engine administers it (RFC-0004 §4.8). The Operator may revoke it at any time
before it is spent (RFC-0001 principle 11). No other actor owns, transfers, or
extends a token; it cannot be reassigned to a different Action or session
(RFC-0004 A8).

**Scope.** A token binds exactly what was shown: the approved Action, or — for
a plan envelope — the set of Steps as presented (§11). It carries its risk
class, gate, the machine state snapshot it was approved against, its elevation
bounds (if any), and the identity of the session that produced it. Anything the
token does not name is not approved (RFC-0002 invariant 6).

**Lifetime and expiration.** A token lives from issuance until the earlier of
execution (consumption), expiry, or invalidation. Expiry is a time bound fixed
by Policy per risk class — short, never open-ended (the answer to RFC-0002 Q3's
timeout question for the approval side) — and deterministic: a token that
exceeds its lifetime is dead, and executing under a dead token is a fresh
approval, not a renewal. The expiry window is part of the token's audit record.

**Invalidation.** A token is invalidated, and never resurrected, by any of: a
change to the Machine State it was approved against — any State Domain it
depends on (RFC-0021 §6); an interrupt or partial execution (RFC-0002 invariant
8); a reboot (RFC-0002 invariant 15); a session restart or exit; a policy
reload (RFC-0002 §4.7); or revocation by the Operator. A reboot invalidates them
— no standing authorization crosses one, and the plan is re-presented after
state is re-established (RFC-0002 §8). A session restart invalidates them — a
new session holds no memory of a previous session's approvals (RFC-0002
invariant 15). A machine state change invalidates them — the approval no longer
describes the situation it was given against (RFC-0002 invariant 11; §9).
**Single-use vs. reusable.** Tokens are single-use for Actions: one Action, one
token, consumed by that execution, never reused. Plan envelopes are not reusable
either: an envelope is consumed as its Steps run, and a Step whose token was
consumed by a failed attempt is re-approved before retry (RFC-0002 §7).
Auto-permission is not reusability: each allowlisted read-only Action receives
its own token at its own execution boundary; the allowlist permits
*classification to auto-permitted*, it does not grant a reusable pass (RFC-0001
§8.3).

**Retries.** A retry is a new execution of the same Action, bounded by Policy
per risk class (a small, explicit ceiling, not an open loop) and always
re-presented for approval for state-changing Actions — the previous token was
consumed by the attempt. An allowlisted read-only Action may simply run again
under a fresh auto-permit token. This answers RFC-0002 Q2.

**Standing approvals.** A standing approval is a Policy construct that pre-mints
a narrowly scoped, expiring authorization for a *class* of Actions within a
defined scope and a risk-class ceiling (RFC-0001 §8.3; RFC-0003 §2.6). It is
still a token: it expires, is invalidated by any of the boundary events above,
is bound to state, and never becomes blanket authority. A standing approval
never raises a class ceiling, never covers a Blocked Action, and is always
visible in the presentation and the Audit. This answers RFC-0001 Q5: it is
represented as a scoped, expiring Policy grant; "approve all" habits are
prevented by the ceiling, the expiry, the scope, and the audit.

**Elevation.** Elevation is the use of the machine's own privilege-escalation
mechanism (RFC-0021 §3.3) to run an approved Action with the authority it
needs. It is explicit, per-action, scoped, and re-authenticated (RFC-0001
§8.6): an elevated Action is at least Consequential (§6), its elevation bounds
are part of the token, and the elevation is revoked at the end of that Action
or on any invalidation. Elevation never persists, never covers unapproved
work, and never forms a standing root session (RFC-0001 §8.6). This RFC fixes
these semantics; the mechanism is the machine's own and is not named here.

---

## 9. Preconditions

Approval is a promise about a machine state. **Preconditions** are the checkable
statements that make that promise honest: the assumptions the approval was
shown against, verified deterministically before the Action may execute.

The engine verifies three families at the execution boundary — the same place
RFC-0002 consults it (Awaiting Approval → Executing, §6.2):

1. **The assumptions still hold.** Every Fact the Action's classification and
   plan were built on is re-checked for provenance and staleness (RFC-0002
   invariant 10). A stale Fact is re-collected, not assumed; an assumption that
   cannot be re-established is treated as not holding.
2. **The machine state has not changed.** The State Domains the Action touches
   (RFC-0021 §6) are compared against the snapshot the token was approved
   against. If any has changed, the token is invalid and the plan is re-presented
   (RFC-0002 §2.7). This is the state-consistency half of RFC-0002 invariant 11.
3. **The requested action still matches the approved action.** The Action at the
   execution boundary is structurally identical to the one shown, classified,
   and approved: same Action identity, same parameters within scope, same
   target, same risk class. A change is a deviation requiring fresh approval
   (RFC-0002 invariant 6).

Preconditions are checked by deterministic comparison — Facts against Facts,
Action description against Action description — never by re-deriving the
Operator's judgment and never by asking the LLM. If any precondition is
uncertain, the gate treats it as not holding: fail closed, disclose, re-present
(RFC-0002 §2.8; RFC-0007 T11).

---

## 10. TOCTOU Protection

The approval-to-execution gap is the classic **time-of-check / time-of-use**
hazard — RFC-0002 §6.2 names it explicitly. Between approval and execution the
machine can change, policy can change, or the Action can be substituted. TOCTOU
protection makes approval un-reusable across such a change: an approval obtained
for one Action, one state, one time cannot be spent on a different Action, a
changed state, or a later time.

The protection has four layers:

| Layer | Guarantee |
|---|---|
| **Binding** | The token is bound to its Action, its time, and its Machine State snapshot (RFC-0002 invariant 11; RFC-0003 §2.6) — part of the token itself and of the check that precedes execution, not a property of the Operator's memory or the interface. |
| **Re-validation at the boundary** | The Approval & Policy Engine is consulted again at Awaiting Approval → Executing (§9): preconditions are re-checked, the Action is compared to the approved Action, and the token is verified valid, unexpired, and state-consistent (RFC-0002 §2.8; RFC-0004 §4.8). |
| **Independent enforcement** | The Executor does not trust the re-validation by word; it independently refuses to run anything not carrying a valid, unexpired, state-consistent token (RFC-0004 A2). The gate is enforced in two components so that a compromise of either still leaves the other refusing. |
| **Consumption and invalidation** | A token is consumed by its one use; a state change, interrupt, reboot, session restart, or policy reload invalidates it (§8). There is no "valid but stale" token and no reuse path. |

**Why approvals cannot be reused after state changes.** An approval is a
decision about *this machine at this moment* (RFC-0001 principle 2). The only
honest reading of "the Operator approved it" is "against the state shown." If
the state changed, the approval no longer refers to the situation that exists,
and spending it would execute a decision the Operator never made. Invalidation
is therefore not a convenience trade-off; it is what keeps an approval true to
what was approved.

---

## 11. Plan Approval

A Plan is approved as an **envelope** (§5): one holistic Operator judgment over
a fully shown, ordered, classified set of Steps (RFC-0002 §2.7). Envelope
approval exists to answer RFC-0001's rubber-stamp risk — judge a fix once, as a
whole (RFC-0001 §13 risk 1) — without ever delegating a Step's gate (RFC-0002
§2.8).

**How a plan is presented.** Before any decision, the Operator sees the ordered
plan: each Step's Action, its risk class and gate, its preconditions, its
expected Post-condition, and its verification method (§12). A Plan whose Steps
span classes is presented with the Plan class — the meet of its Steps' classes
(§6) — and with each Step's own class and gate shown. A Plan containing a
Blocked Step is presented as containing one; the Operator may approve the rest
or override the Blocked Step separately (§7, §13 P10).

**How modifications invalidate approval.** Approval is scoped to what was shown
(RFC-0002 invariant 6). Any of the following is a deviation that voids the
envelope and requires fresh approval (RFC-0002 §7: a changed plan is
re-normalized, re-classified, re-presented): a Step is inserted, removed, or
reordered; a Step's Action, parameters, or preconditions change — state changed,
or a Fact is invalidated; a Step's risk class or gate changes; the Goal changes.

**Partial execution.** If a batch stops partway (cancel or interrupt), the
envelope is consumed up to the last completed step; what did not run is never
assumed to have run (RFC-0002 §2.8, §10). Continuation is a new decision: the
remaining Steps are re-presented after state is re-established (RFC-0002
invariant 8).

**Failed steps.** A Step that fails verification is not retried automatically.
The plan returns to Replanning with the failure as new fact (RFC-0002 §2.9);
the revised plan — including any retry of the failed Step — is re-presented
(RFC-0002 §7; §8 single-use). There is no "the plan was approved, so keep
going."

**Skipped steps.** A Step can be skipped only by the Operator, and only by
re-presenting the plan without it. Skipping is a deviation; it is never
inferred because a Step failed — failure is not skipping (RFC-0002 invariant 9).

**Inserted steps.** A Step proposed after the envelope was approved is not part
of the envelope. It is classified, gated, and presented on its own, or the plan
is re-presented with it inserted. No inserted Step inherits the envelope's
approval.

The net rule, in one sentence: **the envelope approves exactly the Steps that
were shown; everything else — change, failure, insertion, or omission — returns
through the gate.**

---

## 12. Human Interaction

Before the Operator approves anything, the Approval Engine presents the
proposal through the interface. RFC-0015 owns the form; this RFC fixes the
content. The following are **always** shown, for every Action and every Plan
envelope, before any decision is requested — including for auto-permitted
read-only Actions, which are classified and audited even when no decision is
requested (RFC-0002 §2.7):

| Element | Requirement |
|---|---|
| **What will be done (Purpose)** | The Action's description, in language proportionate to the risk (RFC-0001 principle 3): the riskier the Action, the more the Operator must be told before deciding. |
| **Expected outcome** | What the Post-condition is supposed to be after the Action, stated as a checkable result (RFC-0003 §2.6). |
| **Potential risks** | The risk class and gate, the specific warning grounds for confirm-with-warning, and the concrete harms the Action could cause. |
| **Affected subsystems** | Which subsystems and State Domains the Action touches — packages, services, configuration, network, users, storage, security state (RFC-0021 §4, §6). |
| **Rollback availability** | Whether the change is reversible, and how — with the honest statement that a rollback is itself an approved Action, not a promise (RFC-0002 §10). Where reversal is not possible, that is stated explicitly. |
| **Verification method** | How the Post-condition will be deterministically confirmed after execution (RFC-0006), or an explicit statement that it cannot be and what that means. |

Beyond these six, three presentation rules are fixed here and are not
negotiable by the interface (RFC-0015 may add to them, never remove from them):

- **Nothing is approved by silence.** Every approval is a positive act. There
  is no "accept after timeout" (RFC-0001 §8.3).
- **Friction is proportional to risk.** Read-only asks the least, Destructive
  asks the most; the interface never compresses a confirm-with-warning or a
  Blocked override into a "yes" of the same weight as a plain confirm
  (RFC-0001 §13 risk 3: the beginner-with-root-power contradiction is designed
  against, not papered over).
- **What is shown is what is approved.** The presentation is the contract: a
  token covers exactly the presented Steps and the presented content (§8, §11).
  The presentation cannot show less and approve more (RFC-0002 invariant 6).

---

## 13. Approval Invariants (Normative)

These invariants make the approval model structural. They join RFC-0002 §9 and
RFC-0004 §8: no implementation may violate them and no later RFC may weaken
them except by amendment (RFC-0003 Part II §1).

- **P1 — The gate is the only path to machine mutation.** No state-changing
  Action executes without, in order: classification, its required gate, an
  explicit Operator decision (approve, auto-permit, or override), a minted
  token, boundary re-validation, execution, and verification. (RFC-0002
  invariant 1; RFC-0004 A9.) *Test: every state change in any trace is preceded
  in the audit by a classification, a decision, and an issuance.*
- **P2 — Risk classification is deterministic and never the proposer's
  self-report.** The class is computed from the Action's structured description
  and Facts; the proposer's words, the LLM's confidence, and any percentage or
  score are ignored. (RFC-0002 invariant 7; RFC-0001 §8.5.) *Test: two Actions
  with identical descriptions and Facts get the same class regardless of how
  they are described.*
- **P3 — Default deny and fail closed.** An unclassified Action, a
  classification error, an unparseable policy rule, or an unknown risk class is
  blocked and disclosed, never auto-permitted. (RFC-0001 §8.2, §8.12; RFC-0002
  §10.) *Test: injecting an unknown or malformed rule yields a blocked outcome,
  never an execution.*
- **P4 — Classification precedes presentation and is not re-derived by it.**
  The gate is decided before the Operator sees anything; the interface renders
  it, never recomputes it, and the Operator's response cannot change it.
  *Test: the presented gate equals the engine's decision.*
- **P5 — Approval is explicit; nothing proceeds on silence or implied
  consent.** Every state-changing execution traces to a positive recorded
  decision over the specific Action or envelope. (RFC-0001 §8.3; RFC-0002
  invariant 1.) *Test: an unanswered request consumes no token and runs
  nothing; no timeout yields a "yes."*
- **P6 — Approval is scoped to what was shown.** A token covers exactly the
  presented Action, or the presented Step set of the envelope; any deviation is
  a fresh approval. (RFC-0002 invariant 6.) *Test: altering any presented
  parameter or Step fails the Action-identity check and requires a new
  decision.*
- **P7 — Tokens are single-use and never reused.** One Action consumes its
  token; a consumed or expired token is dead. A retry of a state-changing
  Action is re-presented; an allowlisted read-only Action re-runs only under a
  fresh token. (RFC-0002 invariants 11; §7.) *Test: replaying a consumed token
  yields a refusal.*
- **P8 — Tokens are bound to action, time, and machine state, and invalidated
  by any boundary.** A state change, interrupt, reboot, session restart, policy
  reload, or revocation invalidates the token; it is never resurrected.
  (RFC-0002 invariants 11 and 15.) *Test: each boundary event leaves the token
  unusable.*
- **P9 — Preconditions are re-validated at the execution boundary.** The engine
  re-checks assumptions, machine state, and Action identity; if any is
  uncertain or changed, the token is not spent. (RFC-0002 §2.8; §9, §10.)
  *Test: a stale Fact, a changed State Domain, or a substituted Action each
  prevent execution.*
- **P10 — Blocked actions proceed only by explicit, audited override.** An
  override is presented with its own warning, requires its own decision, and is
  written to the Audit before execution. (RFC-0002 invariant 12; RFC-0004 A10.)
  *Test: no blocked Action executes without an override record preceding it.*
- **P11 — Standing approvals are scoped, bounded, expiring, and never
  blanket.** A standing approval has a defined scope, a risk-class ceiling, an
  expiry, and is invalidated like any token; it never covers a Blocked Action
  and never raises a ceiling. (RFC-0001 §8.3.) *Test: an Action outside its
  scope, above its ceiling, or after its expiry is not auto-approved.*
- **P12 — Elevation is explicit, per-action, scoped, and revoked.** Any use of
  the machine's elevation mechanism is bound to the approved Action, presented,
  and revoked at the end of that Action or on invalidation. (RFC-0001 §8.6.)
  *Test: an elevated Action's token carries its elevation bound; after the
  Action or any invalidation, no elevated capability remains.*
- **P13 — Approval is recorded before it is spent.** Issuance, override,
  auto-permit, rejection, and standing-approval grants are written to the Audit
  before their consequence proceeds. (RFC-0002 invariant 13; RFC-0004 A10.)
  *Test: for every execution, the issuance and decision records exist and
  predate it.*
- **P14 — Policy reload and machine-state change re-validate every outstanding
  decision.** On a configuration reload or on any State-Domain change relevant
  to an outstanding token, the engine re-validates or invalidates; nothing
  approved under an older policy or older state runs without re-check.
  (RFC-0002 §4.7, invariant 15.) *Test: after a reload or state change, no
  outstanding token executes without passing boundary re-validation.*

---

## 14. Abuse Analysis

For each attack, what it tries to do and which structure stops it. The pattern
follows RFC-0004 §9: assume the attack is real and ask why the architecture
does not fall. Three structural facts recur (mirroring RFC-0004 §9.13): the
machine is mutated only through a token-bound gate (P1, P7, P8); the Operator's
decision is the only authority and the presentation is the contract (P4–P6);
and everything consequential is recorded before it happens (P13).

| Attack | What it tries to do | Why the architecture stays safe |
|---|---|
| **Approval fatigue** | Wear the Operator down until "yes" is reflex; bury a harmful Action among many safe ones | The class and gate are decided before presentation (P4); a plan is judged once as a whole so harmful Steps cannot hide among trivia (§11); friction is proportional to risk (§12), so a Destructive Step inside an approved envelope is still its own Blocked gate; "what is shown is what is approved" (P6) means burying a Step does not approve it |
| **Click-through behaviour** | The Operator approves without reading | The presentation is contractually the thing approved (P6); the presentation always carries the six mandatory elements (§12); nothing is approved by silence (P5). The honest residual is RFC-0001 risks 1 and 3; this RFC's answer is structural — tiered gates, whole-plan judgment, no silent approval — not UI persuasion alone, and the Audit keeps the record visible |
| **Prompt manipulation** | Untrusted text (machine output, a doc, a skill) instructs the Operator or the engine to act | The engine never reads raw untrusted text to classify (RFC-0007 T2; P2); classification uses structured Action descriptions and Facts; untrusted text never carries permissions (RFC-0001 §7 rule 3); the Operator's screen is a boundary too (RFC-0007 S4); a manipulated presentation still cannot change the token's scope (P6) or mint an execution (P1) |
| **Provider deception** | The LLM proposes a harmful Action and asserts it is safe, or lies about verification | The proposing actor's characterization is ignored (P2); the gate is deterministic (P1); success claims are never trusted (RFC-0004 A5); the Post-condition is confirmed by re-observation, not by the model (RFC-0002 invariant 2); the worst an LLM can do is propose (RFC-0004 A1), and proposals are classified, approved, and verified |
| **Skill deception** | A Skill declares a benign risk class for a destructive Action, or proposes Actions that appear safe | A Skill's Actions pass the same gate as anything else (RFC-0004 A3); classification reads the Action's actual structured properties, not the Skill's declaration (P2); the declaration is verified against actual behavior at install (RFC-0011); the Skill never executes anything itself (RFC-0004 A2, A3) |
| **Plan mutation** | A Step is swapped, reordered, or edited between approval and execution | The token binds the exact presented Steps (P6); the Action at the execution boundary is compared to the approved Action (§9); any difference is a deviation requiring fresh approval (§11); the Executor independently refuses anything not carrying a token for what is about to run (P1, RFC-0004 A2) |
| **Delayed execution** | An approval is held and spent later, when the state has changed or the Operator is gone | Tokens expire (P8); a state change, interrupt, reboot, session restart, or policy reload invalidates them (P8, P14); re-validation at the boundary re-checks assumptions and state (§9); there is no valid-but-stale token |
| **Replay attacks** | A captured approval or a recorded presentation is replayed to spend a token again, or to pass off a new Action as approved | Tokens are single-use and never reused (P7); consumed and expired tokens are dead; a replayed presentation cannot mint a token — only the Approval Engine can, after classification and an Operator decision (P1); a replayed Action fails the Action-identity comparison (§9) |
| **Approval token theft** | An attacker steals or forges a token and spends it on something else | A token is bound to one Action, one time, one state (P8); the Executor independently re-validates it (RFC-0004 A2); issuance is recorded before spending (P13); a forged token fails the state-consistency and Action-identity checks (§9, §10); a stolen token still cannot execute an Action the token does not name (P6) |
| **Privilege escalation** | An Action runs with more privilege than approved, or elevation leaks to unapproved work | Elevation is explicit, per-action, scoped, and revoked (P12; RFC-0001 §8.6); an elevated Action is at least Consequential (§6) and is presented and bound like any other; the Executor runs only token-bound Actions (P1); there is no blanket privilege and no persistent elevation |

---

## 15. Failure Behaviour

Every failure follows RFC-0002 §10's order — **determinism first, then
disclosure, then decision, then action** — with these specific outcomes:

| Failure | Outcome |
|---|---|
| **Approval expires** | The token is dead; nothing runs under it (P8). The session discloses the lapse, re-establishes state if it changed, and re-presents the Action for a fresh decision. An expiry is never silently extended. |
| **Verification fails** | The Post-condition was not met; state is re-established deterministically and the failure becomes new fact (RFC-0002 §2.9). The plan returns through the gate: any retry or revised Step is re-presented (§11; §8 single-use). Unverified is never success (RFC-0002 invariant 9). |
| **Execution is interrupted** | In-flight work is treated as unknown state (RFC-0002 §2.8): the token is consumed or invalidated, actual state is re-established (RFC-0002 invariant 8), exactly which Steps ran is recorded, and the remainder is re-presented (§11). No silent continuation. |
| **The system reboots** | Every approval ends at the boundary (RFC-0002 invariant 15; §8). On resume, state is re-established, and the pre-approved read-only assessment may run automatically; no state-changing continuation runs without a fresh decision (RFC-0002 Q8). |
| **The provider is replaced** | The provider is not an authority over approval (RFC-0004 A1). Swapping a provider changes nothing about outstanding tokens: they were issued against machine state and an Operator decision, not against a provider. If the plan depended on provider-proposed content, the plan is re-normalized and re-presented like any deviation (RFC-0002 §7). |
| **The plan changed** | Any change invalidates the envelope (P6, §11) and returns through the gate: re-normalize, re-classify, re-present. |
| **Policy is unavailable** | Unparseable policy, a missing rule, or an internal engine error is fail-closed: the Action is blocked, the Operator is told why, and the session moves to Awaiting Input or Failed (RFC-0002 §10 Policy failure; P3). Nothing proceeds "because the policy check was unavailable." |
| **The gate cannot be reached** | If the Approval Engine cannot present, or the Audit cannot record, the consequence it precedes is blocked (RFC-0002 invariant 13): a consequence never proceeds unrecorded or unpresented. |

---

## 16. Open Questions

Architectural questions this RFC deliberately leaves open; each names its
owner. None blocks the approval model's core guarantees.
| Question | Decided here | Open for |
|---|---|---|
| **Presence mechanics for attended execution** | Execution is attended by default — the Operator is at the session, and the runtime never schedules state-changing work the Operator cannot stop (the answer to RFC-0002 Q7) | The fine-grained mechanics of "attended" (session-live vs. timeouts vs. interrupt handling) are owned by RFC-0014 |
| **The shipped policy content** | The *mechanism*: classes, gates, allowlist, standing approvals, expiry, override (P1–P14) | The *specific default contents* of the read-only allowlist, standing-approval defaults, and expiry windows are policy content for RFC-0020 |
| **The absolute-block list** | Such a list exists and how an absolute block is overridden (§6) | Which specific Actions Policy declares absolutely blocked is a Policy-content decision for RFC-0020 |
| **Override presentation** | An override is explicit, warned, and audited (P10) | The form of the override and its warning presentation belongs to RFC-0015 |
| **Whether any block is hard-coded** | "Absolute" is a Policy declaration, not a technical guarantee (RFC-0001 principle 11) | Whether the project wants a hard-coded no-override set is an MVP-scope decision for RFC-0019 |

---

## 17. Architectural Risks

Roughly ordered by severity: the ways the approval model could fail, and the
structural mitigation already in this RFC for each.

| Risk | Why it could fail | Structural mitigation in this RFC |
|---|---|---|
| **Safety theater — approval as a rubber stamp** | RFC-0001's top risk (RFC-0001 §13 risk 1) | Whole-plan judgment (§11), gates decided before presentation (P4), friction proportional to risk (§12), no silent approval (P5), Audit as visible record (P13). The residual is a product-behavior risk, fought in the interface (RFC-0015) and policy content (RFC-0020); this RFC records it rather than claiming to have eliminated it. |
| **The beginner-with-root-power contradiction** | RFC-0001 risk 3: those who need the tool most authorize the most destructive actions | "What is shown is what is approved" (P6) and §12's mandatory content keep the decision honest; elevation is per-action (P12); the usable-safe trade-off lives in RFC-0015. |
| **Class-boundary misclassification** | A Destructive Action read as Benign trades a Blocked gate for a Confirm | Classification reads only deterministic properties (P2), the meet rule governs composition (§6), verification still confirms the outcome (RFC-0002 invariant 2); a wrong class does change the gate, so the boundaries are high-stakes policy content (RFC-0020). |
| **Allowlist and standing-approval creep** | Widening the allowlist or standing-approval bounds returns to "always yes" (RFC-0001 Q5) | Every standing approval expires, is scoped, has a ceiling, and is audited (P11); auto-permission is per-Action, never a reusable pass (P7); only the Operator can widen them (RFC-0004 §3). |
| **TOCTOU residual** | Re-validation narrows but cannot zero the approval-to-execution gap | The Executor independently re-validates last (P1, RFC-0004 A2); tokens are consumed and invalidated (P7, P8); a change anywhere in the window re-presents rather than proceeds (§10). |
| **Elevation as the platform's weak point** | Elevation semantics are ours (P12); the mechanism is the machine's, outside our control (RFC-0021 §3.3) | Elevation is per-action, scoped, and revoked, so a single elevated Action cannot cascade; the project cannot promise to defend against a compromised host elevation mechanism — the platform's problem, recorded honestly. |
| **Overrides becoming routine** | If Blocked is overridden as a habit, blocks are decoration | An override is its own warned, recorded decision (P10); absolute blocks require changing Policy, not a per-case yes (§6); the Audit keeps the pattern visible; the interface must not make override the easy default. |

---

## 18. New Terms for RFC-0003 (flagged for inclusion in Part I)

The following terms are defined in this RFC and must be added to RFC-0003 Part
I by additive amendment: **Approval Unit**, **Approval Gate**, **Plan
Envelope**, **Standing Approval**, **Read-Only Allowlist**, **Override**,
**Elevation**, **Precondition**. The definitions appear at first use in §5,
§6, §7, and §8. Approval, Approval Token, Action, Plan, Step, Proposal, Policy,
Risk, and Verification already exist in RFC-0003 Part I and are used here with
their canonical meanings.

---

*End of RFC-0008. Normative: sections 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15.
Explanatory and load-bearing: sections 0, 1, 2, 3, 14, 16, 17, 18. Any change
to an Approval Unit, a Risk Class or gate, an Approval Token's lifecycle rule,
a precondition or TOCTOU rule, a plan-approval rule, a standing-approval or
elevation rule, or an invariant P1–P14 is a BREAKING change and must be made by
amendment (RFC-0003 Part II).*
