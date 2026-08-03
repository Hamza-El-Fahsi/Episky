# RFC-0013 — Audit, Transcript & Accountability Model

**Status:** Draft
**Date:** 2026-08-02
**Scope:** The single canonical model for what the system records: what Audit
and Transcript are and the distinction between them; every category of each;
what is recorded and never recorded; Audit ownership, authority, lifecycle,
visibility, trust, and the integrity, completeness, privacy, export, retention,
deletion, failure, and recovery philosophies; interaction with the Runtime,
Context, Facts, Verification, Approval, Providers, Skills, Diagnostics,
Secrets, and future extensions; and the audit invariants AU1–AU16.
**Audience:** Future maintainers
**Supersedes:** Nothing
**Depends on:** RFC-0001, RFC-0002, RFC-0003, RFC-0004, RFC-0005, RFC-0006,
RFC-0008, RFC-0009, RFC-0012 (accepted in this series). RFC-0007, RFC-0010,
and RFC-0011 are referenced for the boundaries they already state; all three
are Drafts and are not dependencies.

**Roadmap note:** This is RFC-0000's "RFC-0013 — Audit & Transcript
Architecture" (Runtime, Required), because audit is an accepted invariant the
MVP must satisfy (RFC-0000 §5). Its purpose is to fix what is recorded and when
(proposals, classifications, approvals, overrides, executions, verifications,
outcomes), the ordering guarantee (recorded *before* the consequence), what may
be retained and for how long, tamper-resistance expectations, and the honest
framing that the audit is transparency, not forensics (RFC-0001 risk 8). It
implements the Audit System's responsibilities, authority, and invariants A7
and A10 (RFC-0004 §4.12, §10), the audit boundary (RFC-0002 invariant 13), and
records the gate (RFC-0008 §3, P13). It owns the deferred mechanics assigned to
it: RFC-0005 §15 OQ2, RFC-0006 §15 OQ5 (evidence retention and verification
feed), RFC-0007 §16 OQ1 (audit and transcript mechanics), RFC-0008 §3 (the
record), RFC-0011 §16 (Skill events and format), and the Context-to-Audit
boundary (RFC-0012 §13). It has no open-question rows in RFC-0000 §8.

**BREAKING:** No. This RFC specifies the accountability model that RFC-0001,
RFC-0002, RFC-0004, RFC-0005, RFC-0006, RFC-0008, RFC-0009, and RFC-0012
already assume and cite: Audit is the durable, append-only, tamper-evident
record of consequential events, written before each consequence (RFC-0003
§2.8; RFC-0002 invariant 13), and its purpose is transparency, not forensics
(RFC-0001 risk 8). It does not weaken any Principle, Boundary, Invariant, or
canonical Definition in an accepted RFC.

---

## 0. Purpose

> **What did we do and why? How does the system guarantee that the answer is
> complete, honest, and written before each consequence — while the Audit never
> becomes authority and the Transcript never becomes evidence?**

Three binary guarantees fix everything below:

1. **The Audit records, it does not decide.** No component treats the Audit as
   authority, a Fact source, or a decision input (RFC-0004 §4.12).
2. **The Transcript presents, it does not prove.** It is the Operator-facing
   account, derived from the record, and never evidence: Facts remain the only
   evidence model (RFC-0003 §2.8; RFC-0005 §3).
3. **Every consequence is recorded before it happens.** The record exists at the
   boundary, never after the fact, and is never silently edited (RFC-0002
   invariant 13).

---

## 1. What is Audit

**Audit** is the durable, append-only, tamper-evident record of consequential
events — proposals, classifications, approvals, overrides, executions,
verifications, and outcomes — written *before* each consequence is allowed to
proceed (RFC-0003 §2.8; RFC-0002 invariant 13). Its purpose is transparency,
not forensics (RFC-0001 risk 8).

1. **The authoritative record.** When Audit and anything else disagree about
   what happened, the Audit is the record of record (RFC-0003 §2.8; RFC-0002
   invariant 13).
2. **Written at the boundary.** Recording happens before the consequence it
   describes is allowed to proceed (RFC-0002 invariant 13; RFC-0004 A10).
3. **Append-only and tamper-evident** (RFC-0001 §8.10; RFC-0004 A7). No actor
   edits or erases a prior record.
4. **Never authority.** Audit has Persist and Explain authority only; it
   proposes, approves, executes, observes, and verifies nothing (RFC-0004
   §4.12; AU1).

---

## 2. What is Transcript

**Transcript** is the human-readable account of the session as experienced —
the dialogue and the actions — derived from the record (RFC-0003 §2.8). It is
the Operator-facing view of what happened.

1. **Derived, not primary.** The Transcript is rendered from the Audit record;
   it is not a separate store and has no independent authority (RFC-0003 §2.8).
2. **For the Operator.** The Transcript answers "what did we do and why" in the
   Operator's terms (RFC-0001 §5 Audit & Transcript).
3. **Never evidence.** The Transcript is a presentation, not proof; it cannot be
   verified and never feeds a decision (AU2).
4. **Complete in what it shows, honest about what it omits.** The Transcript
   shows what the record holds; anything redacted or withheld is disclosed, not
   dropped (RFC-0009 §15).

---

## 3. Audit vs Transcript

| Dimension | Audit | Transcript |
|---|---|---|
| Role | Authoritative record of consequential events | Operator-facing account derived from the record |
| Write time | Before each consequence (RFC-0002 invariant 13) | Rendered on demand (RFC-0003 §2.8) |
| Authority | Persist, Explain only (RFC-0004 §4.12) | None; presents only (AU2) |
| Evidence | Never; not a Fact source (RFC-0004 §4.12) | Never; Facts are the only evidence model (AU2; RFC-0005 §3) |
| Editing | Append-only, tamper-evident (RFC-0004 A7) | Re-rendered from the record; never alters it |
| Visibility | Operator at any time (RFC-0002 §6) | Operator-facing by construction (RFC-0003 §2.8) |

The distinction is **purpose and form**, not content: the Audit is what is
true-of-what-happened in machine terms; the Transcript is the same record told
to a human. Neither decides anything and neither is evidence.

---

## 4. Audit Ownership

Every thing has exactly one owner per responsibility (RFC-0004 §3):

| Thing | Owner | Delegated through | Never owned by |
|---|---|---|---|
| Durable record of events | Audit System | — | Provider, Skills, Diagnostics, Fact Layer, Policy Engine, Approval Engine, Executor, Orchestrator, Context Manager, Operator (who reads, never writes) |
| Record format and ordering | Audit System | — | Every other component (RFC-0004 §4.12 "May decide") |
| Transcript presentation | Audit System | Operator-facing rendering (RFC-0015) | Providers, Skills, Diagnostics, Fact Layer, Policy Engine, Approval Engine, Executor |
| Audit retention and deletion | Audit System | Operator consent bounds | Every other component |

- **The Audit System owns the record.** It decides format and ordering within
  RFC-0013, records every consequential event before its consequence, and
  exposes Audit and Transcript to the Operator (RFC-0004 §4.12).
- **The Operator owns the bounds.** Retention and deletion follow the
  Operator's purpose and consent (RFC-0001 §9.5); the Operator reads, exports,
  and wipes, and never writes.
- **No other component owns, writes, or decides about the record.** Components
  are recorded *about*; none is recorded *by*.

---

## 5. Transcript Ownership

1. **The Audit System owns Transcript derivation.** The Transcript is a
   rendering of the record the Audit System owns; no other component composes
   it (RFC-0004 §4.12).
2. **RFC-0015 owns the presentation form.** How the Transcript is shown to a
   beginner is the interface contract's (RFC-0001 §5 Presentation; RFC-0008
   §12); this RFC fixes what must be shown, never how.
3. **No component owns a private transcript.** Providers, Skills, Diagnostics,
   and the Fact Layer hold no transcript of their own; the Transcript is the
   single derived account (RFC-0004 §4.12).

---

## 6. Audit Authority

Authority is the tool that lets an owner discharge responsibility (RFC-0004
§6). The Audit System's authority is narrow and enumerated:

1. **Persist** — the owner of the durable record; records consequential events
   before their consequences (RFC-0004 §4.12; RFC-0002 invariant 13).
2. **Explain** — presents the record to the Operator (RFC-0004 §5 Explain
   row).

No component holds authority to: decide what is true (RFC-0004 §4.6), approve
or execute (RFC-0004 §4.12), omit an event (RFC-0004 §4.12 "May never
decide"), alter history (RFC-0004 A7), or treat the record as a decision input
(AU1). These are privileges held by none.

---

## 7. Audit Record Categories

The Audit holds exactly these categories of records. Each is a set of events
written at its boundary before the consequence (RFC-0002 invariant 13).

1. **Session records** — goal adoption and outcome, session lifecycle (RFC-0002 §2).
2. **Proposal records** — proposals, plans, hypotheses, rejections as produced (RFC-0002 §6).
3. **Classification records** — risk classifications and grounds, before the gate outcome (RFC-0008 P1; P2).
4. **Approval records** — approvals, refusals, auto-permissions, standing grants, issuance, before the token is spent (RFC-0004 A10; RFC-0008 P13; RFC-0002 §2.7).
5. **Override records** — blocked-action overrides, with their own warning before execution (RFC-0002 invariant 12; RFC-0008 P10).
6. **Execution records** — action start/end, commands in sanitized form, machine state at the boundary (RFC-0002 §6).
7. **Verification records** — verification attempts, their Outcomes, evidence references (RFC-0006 §14; RFC-0006 §15 OQ5).
8. **Fact-lifecycle records** — creation, replacement, retirement, deletion, contradiction, with reason (RFC-0005 §7; RFC-0005 §15 OQ2).
9. **Context-boundary records** — material entered Context or Memory, never the material itself (RFC-0012 §13; RFC-0004 §9.11).
10. **Secret-metadata records** — provisioning, use, invalidation, destruction, exposure, visibility requests — metadata only, never values (RFC-0009 §15, SC4).
11. **Skill-event records** — loading, activation, execution, failure, refusal, trust revocation, declared-vs-actual audit (RFC-0011 §16; RFC-0001 Q22).
12. **Operator-visibility records** — view, export, wipe requests and outcomes (RFC-0001 §9.2).

---

## 8. Transcript Record Categories

The Transcript is derived from the Audit and presents exactly these categories:

1. **Dialogue** — the Operator-facing conversation, from session, proposal, and approval records.
2. **Actions and outcomes** — what was run, approved, verified, and the outcome (RFC-0002 §10).
3. **Decisions and their grounds** — classifications, approvals, refusals, overrides with stated reasons (RFC-0008 P13).
4. **Disclosures** — anything redacted or withheld, disclosed as withheld (RFC-0009 §15).
5. **Recovery context** — what the record re-presents after an interrupt or reboot (RFC-0012 §21; RFC-0002 §10).

The Transcript is always renderable from the record; it never holds material
the record does not.

---

## 9. What is Recorded

The Audit records every event in the twelve categories of §7, at its boundary,
before its consequence (RFC-0001 principle 9; RFC-0002 invariant 13). Nothing
consequential is exempt by virtue of who caused it, including the Operator.

"Consequential" means the event changes what the machine holds, what was
decided, or what the Operator can verify happened; the §7 categories enumerate
the boundaries where this applies.

---

## 10. What is Never Recorded

Fixed exclusions, not judgment calls:

1. **Secret values, in any form** (RFC-0009 SC4). The Audit records metadata,
   never enough material to reconstruct a value.
2. **Raw, unbounded machine output** (RFC-0001 §9). Only normalized, bounded
   material is recorded.
3. **The contents of Context or Memory.** A record that material entered, never
   the material itself (RFC-0012 §13; RFC-0004 §9.11).
4. **Provider View content.** What was *sent* to a provider is not the record;
   the proposal it answered is (RFC-0007 §12).
5. **Hypothesis without its evidence.** The Audit records what and when;
   explanations live with the proposal they explain.
6. **Anything without a stated purpose** (RFC-0001 §9). If the runtime cannot
   say why a record exists, it must not exist.

---

## 11. Audit Lifecycle

The Audit moves through a deterministic lifecycle driven by the runtime's
events (RFC-0002 §4):

| State | Meaning |
|---|---|
| **Empty** | No records yet; the store is opened and verified writable (RFC-0002 §2.1). |
| **Recording** | The normal state; events are appended before their consequences (RFC-0002 invariant 13). |
| **Degraded** | A write is failing or was refused; the consequence it precedes is blocked (RFC-0004 §9.12). |
| **Recovering** | A failed or partial write is reconciled and re-verified (RFC-0004 §9.12). |
| **Exported** | A full or partial snapshot was handed to the Operator (§18). |
| **Retained** | Records kept past the session under the retention policy (§19). |
| **Deleted** | Records destroyed under the deletion policy (§20). |

---

## 12. Legal Transitions

Every legal transition is listed; anything not listed is illegal (default
deny, RFC-0001 §8.2).

| From | To | Trigger | Who |
|---|---|---|---|
| Empty | Recording | Session start; store verified writable | Runtime (RFC-0002 §2.1) |
| Recording | Recording | Append of a consequential event | Audit System (RFC-0002 invariant 13) |
| Recording | Degraded | Write failure or write refusal | Audit System (RFC-0004 §9.12) |
| Degraded | Recording | Write reconciled and re-verified | Audit System (RFC-0004 §9.12) |
| Recording | Retained | Retention policy keeps records past session | Audit System under retention policy (§19) |
| Recording / Retained | Exported | Operator export request | Audit System + Operator (§18) |
| Retained | Deleted | Retention lapse or Operator wipe | Audit System under deletion policy (§20) |

**Illegal:** Recording → Deleted without a retention/wipe event (§20);
Degraded → consequence proceeds (RFC-0004 §9.12); any state → a record edit
(append-only, RFC-0004 A7); Deleted → Restored (destruction is irreversible,
RFC-0001 §9.1).

---

## 13. Audit Visibility

Visibility is the Operator's window into what happened (RFC-0001 §9.2):

1. **Always readable.** The Operator can read the Audit at any time, with no
   state transition required (RFC-0002 §6).
2. **Plain and honest.** Records say what was proposed, decided, run, verified,
   and with what outcome — labeled by category (RFC-0007 §12).
3. **No hidden retention.** Nothing the Operator cannot see and remove may be
   retained (RFC-0001 §9.2; AU14).
4. **Disclosure over silence.** Anything withheld from the Transcript is shown
   as withheld (RFC-0009 §15); a failed write is shown as a failure, never as a
   gap (RFC-0004 §9.12).

---

## 14. Audit Trust

Trust is a property of information (RFC-0004 §2); the Audit's trustworthiness
is exactly its completeness and honesty, never more.

1. **Audit adds no truth.** Recording does not make a claim true; the Audit is
   true-of-what-was-recorded, bounded by what was consequential (RFC-0004
   §4.12).
2. **Audit is not a Fact source.** Nothing in the Audit is consumed as a Fact
   for reasoning; Facts come only from the Fact Layer (RFC-0004 §4.6; AU1).
3. **Tamper-evidence, not tamper-proofing.** The record resists silent editing
   (RFC-0004 A7); it is no security control against the Operator (RFC-0001 risk
   8).
4. **Failed writes fail closed.** A consequence never proceeds unrecorded
   (RFC-0004 §9.12; RFC-0008 P13).

---

## 15. Audit Integrity Philosophy

Integrity is the guarantee that the record is what happened, written before
each consequence, and unchanged since.

1. **Record before the consequence** (RFC-0002 invariant 13; RFC-0004 A10).
   The ordering is the integrity mechanism.
2. **Append-only and tamper-evident** (RFC-0004 A7; RFC-0001 §8.10). Prior
   records are never edited or erased by any actor.
3. **Deterministic format and ordering** — within RFC-0013 the Audit System
   decides (RFC-0004 §4.12 "May decide"), so the record is reproducible.
4. **Honest by construction.** A failed write is a blocked consequence, not a
   gap (RFC-0004 §9.12).

---

## 16. Audit Completeness Philosophy

Completeness is the guarantee that every consequential event is recorded,
with no actor exempt.

1. **Every consequential boundary is a write point** (RFC-0002 §6; RFC-0001
   principle 9). The write happens before the consequence proceeds.
2. **No actor is exempt.** Provider, Skills, Diagnostics, the Policy Engine,
   the Approval Engine, the Executor, the Orchestrator, the Context Manager,
   and the Operator are all recorded (RFC-0004 §4.12).
3. **Auto-permitted actions are still recorded** (RFC-0002 §2.7; RFC-0008
   P1).
4. **Failure to record is a failure of the consequence.** A write failure
   blocks the consequence it precedes (RFC-0004 §9.12); completeness is
   structural, not aspirational.
5. **Unknown is recorded as unknown.** An unverifiable outcome is recorded as
   unverifiable, never as success (RFC-0002 §9.14).

---

## 17. Audit Privacy Philosophy

Privacy is enforced at the record's edge, not after:

1. **Metadata, never values** (RFC-0009 §15, SC4). The Audit holds the shape of
   secrets, never their substance.
2. **No Context or Memory dumps** (RFC-0012 §13; RFC-0004 §9.11). The record
   says material entered, not what it was.
3. **Personal data is governed like secrets** unless the Operator explicitly
   demotes it (RFC-0009 SC16).
4. **No record telemetry.** Audit contents are never part of telemetry or crash
   reports (RFC-0009 §26).
5. **Transparency is the mechanism.** The Operator sees what is recorded and
   can remove it (RFC-0001 §9.2).

---

## 18. Audit Export Philosophy

Export is the Operator's right to take the record out (RFC-0001 §9.2):

1. **Export is complete and honest.** A full export contains every record the
   Operator could read; a partial export says it is partial (§13).
2. **Export is at the record's fidelity.** The Transcript renders; the Audit is
   what is exported. Both are exportable (RFC-0001 §9.2).
3. **Export never reveals a secret.** The export boundary obeys the same
   no-value rule as the record itself (RFC-0009 SC4).
4. **Export is an audited event** (RFC-0009 §15 "Operator visibility requests"),
   recorded before it is delivered.

---

## 19. Audit Retention Philosophy

Retention is persistence philosophy applied over time (RFC-0009 §27; RFC-0001
§9.5):

1. **Retained only under a stated purpose.** Records survive the session only
   under the retention policy; "might be useful" is not a purpose (RFC-0001
   §9).
2. **Never a secret value.** No retention rule may preserve a value; retention
   preserves metadata and records, never secrets (RFC-0009 §27 rule 4).
3. **Retention is bounded and explicit.** Concrete periods and per-category
   bounds are policy content (RFC-0020), within the mechanics this RFC fixes.
4. **Retention lapses are deletion events** (RFC-0009 §27 rule 5). Nothing is
   retained past its purpose.

---

## 20. Audit Deletion Philosophy

Deletion is the mirror of recording — complete, irreversible, and itself
recorded (RFC-0001 §9.1, §9.2):

1. **Delete when the purpose lapses** — retention expiry, session end for
   session-scoped records, or Operator request.
2. **Delete on Operator request** — anytime, immediately, including wipe of
   retained records (RFC-0001 §9.2).
3. **Delete irreversibly.** There is no trash can for the Audit; destruction
   is complete and cannot be resurrected (§12 "illegal").
4. **Deletion is itself recorded, without recording the deleted material.** The
   deletion event survives as metadata, never the content (RFC-0002 invariant
   13; RFC-0009 §31).
5. **Deletion never destroys the accountability claim silently.** If records
   must be retained for a stated compliance purpose, that purpose is itself
   audited (RFC-0001 §9.1).

---

## 21. Audit Failure Philosophy

Failure of the Audit is failure of the consequence it protects:

1. **Fail closed.** A failed audit write blocks the consequence it precedes
   (RFC-0004 §9.12; RFC-0008 P13). Nothing proceeds unrecorded.
2. **Fail loud.** The Operator is told a write failed, never left to discover a
   gap (RFC-0001 §10; RFC-0004 §9.12).
3. **Degraded mode is never silent.** If the store is unwritable, the runtime
   refuses the next consequential step (RFC-0002 §2.1; RFC-0004 §9.12).
4. **A gap is never patched by invention.** If a write was lost, recovery
   records that a write failed; it does not fabricate the record (AU8).

---

## 22. Audit Recovery Philosophy

Recovery of a failed or partial record is **reconciliation, never rewrite**:

1. **Re-establish writability first.** The runtime's writability check at
   session start (RFC-0002 §2.1) is the recovery gate; recovery restores
   recording, not history.
2. **Reconcile the failed write.** The record is re-verified; a genuinely lost
   event is recorded as failed-to-record, never invented (§21; AU8).
3. **Re-present from the record.** After interrupt or reboot, the Operator is
   re-oriented from the record (RFC-0012 §21; RFC-0002 §10 "re-orient").
4. **Recovery never resurrects deleted records** (§12 "illegal").
5. **Recovery is re-assembly, not restore** — the same stance RFC-0012 CM13
   takes for Context (RFC-0012 §21).

---

## 23. Audit Interaction with Runtime

1. **The write points are runtime boundaries.** Goal adoption, proposal,
   classification, approval, override, execution start/end, verification, and
   outcome are all audited before their consequences (RFC-0002 §6).
2. **The audit store is a startup prerequisite.** The runtime opens and checks
   audit writability before proceeding (RFC-0002 §2.1).
3. **Recovery is runtime-driven.** Interrupt and reboot re-orientation use the
   record (RFC-0012 §21; RFC-0002 §10).
4. **OP_VIEW renders, never mutates.** Viewing Audit or Context changes no
   state (RFC-0002 §2.12).

---

## 24. Audit Interaction with Context

1. **Context is not the Audit.** Context is for reasoning and is ephemeral;
   the Audit is for record and is durable (RFC-0003 §2.8; RFC-0012 CM15).
2. **Crossings are recorded, contents never** (RFC-0012 §13; RFC-0004 §9.11).
3. **Recovery re-presents from the record.** A lost working set is re-assembled
   from Facts and consented Memory; the record re-presents what happened
   (RFC-0012 §21).
4. **Memory is not the Audit** (RFC-0003 §2.8). No Memory retention is a record,
   and no audit retention rule may preserve Context or Memory material (RFC-0009
   §27).

---

## 25. Audit Interaction with Facts

1. **The Audit records Fact lifecycle, never Fact truth.** Creation,
   replacement, retirement, and deletion are recorded with reason; the Facts
   belong to the Fact Layer (RFC-0005 §7; RFC-0005 §15 OQ2).
2. **Facts are the only evidence model.** The Audit is a record, not evidence;
   verification and reasoning consume Facts (RFC-0005 §3; AU2).
3. **Fact deletion does not delete the record.** The current set forgets a Fact;
   the Audit still holds the record (RFC-0005 §5; RFC-0002 invariant 13).
4. **Facts are never edited, so the record is honest** (RFC-0005 §13 F8).

---

## 26. Audit Interaction with Verification

1. **Verification attempts are audit records** (RFC-0006 §14). Every
   verification, including failed and inconclusive ones, is recorded.
2. **Evidence retention is owned here.** How long verification evidence and
   Outcomes are retained, and how they feed audit, is this RFC's (RFC-0006 §15
   OQ5).
3. **Verification never reads the Audit.** Compare operates on Facts and
   machine state, deterministically (RFC-0006 §3, V8).
4. **Outcomes are recorded, not judged.** The record holds the Outcome and its
   evidence references; meaning is the Fact Layer's (RFC-0004 §4.6).

---

## 27. Audit Interaction with Approval

1. **Approval is recorded before it is spent.** Issuance, override, rejection,
   auto-permission, and standing-approval grants are written before execution
   (RFC-0004 A10; RFC-0008 P13).
2. **The gate's records are the most important** — classification, decision,
   issuance are the record the Operator checks (RFC-0008 P1).
3. **Blocked actions are recorded with their overrides** (RFC-0002 invariant
   12; RFC-0008 P10).
4. **The Audit is a visible record against rubber-stamping** (RFC-0008 §15,
   risk "safety theater"); visibility is the mitigation.

---

## 28. Audit Interaction with Providers

1. **Providers never receive the Audit.** The Provider View is the only channel
   to a provider; the record never crosses it (RFC-0010 PR14; RFC-0007 §12).
2. **Provider activity is recorded, not sent.** Provider calls and the proposals
   they produced are Audit material (RFC-0010 §11).
3. **Provider output is never the record.** Provider returns are untrusted data;
   the record holds the proposal answered (RFC-0007 §12).

---

## 29. Audit Interaction with Skills

A Skill is an audit *subject*, never an audit *editor* (RFC-0011 §16):

1. **Every Skill event is recorded** — loading, activation, execution, failure,
   refusal, trust revocation (RFC-0011 §16; RFC-0002 invariant 13).
2. **A Skill cannot edit or erase history** (RFC-0011 §16; RFC-0004 A7;
   RFC-0011 SK14).
3. **Skill identity is recorded** — version, signature, declared surface
   (RFC-0011 §16).
4. **Declared-vs-actual audit is itself a record and a trust input** (RFC-0011
   §16; RFC-0001 Q22).
5. **Audit format and retention are owned here** (RFC-0011 §16).

---

## 30. Audit Interaction with Diagnostics

1. **Diagnostics never write the Audit.** They produce Observations; the Fact
   Layer normalizes them into Facts; only Facts and lifecycle records enter
   (RFC-0002 §6; RFC-0005 §2).
2. **Collector events are recorded.** What was collected, when, and whether it
   succeeded is audit material; the raw output is never (RFC-0005 §2; RFC-0001
   §9).
3. **Failed collectors are "fact unknown."** A failed inspection yields Unknown
   freshness and is recorded as failed — never fabricated (RFC-0002 §4.2;
   RFC-0005 §13 F14).

---

## 31. Audit Interaction with Secrets

The secret boundary is enforced at the record's edge (RFC-0009 §15):

1. **Metadata, never values** (RFC-0009 SC4). The Audit answers "what secret
   was stored, when used, was it destroyed" without holding a value (RFC-0009
   §15 rule 3).
2. **Recorded:** provisioning, consumption, invalidation, destruction, exposure,
   visibility requests (RFC-0009 §15).
3. **Never recorded:** secret values or enough material to reconstruct one
   (RFC-0009 §15; SC4).
4. **Retention never preserves a value** (RFC-0009 §20, §27).
5. **Suspected exposure is recorded, then the secret is destroyed** (RFC-0009
   SC15); the record keeps the metadata, never the value.

---

## 32. Audit Interaction with Future Extensions

1. **New consequential events are additive amendments.** Adding an audited
   event changes the record's categories, which are normative here (RFC-0003
   Part II).
2. **No extension owns or edits the Audit.** The Audit System is the single
   owner (§4); extensions are recorded *about* (RFC-0004 §4.12).
3. **RFC-0014 re-presents from the record** (resume); RFC-0015 presents the
   Transcript (form); RFC-0020 sets retention and freshness bounds (policy);
   RFC-0016/0017/0018 do not touch the record.
4. **Any future RFC adding a consequential boundary must re-check RFC-0002
   invariant 13** — write-before-consequence is not optional for new events.

---

## 33. Audit Rules (Normative)

| ID | Statement | Rationale | Test |
|---|---|---|---|
| AU1 | **Audit is never authority.** No component treats the Audit as a decision input, a source of Facts, or permission to act. | RFC-0004 §4.12: Audit holds Persist/Explain only; RFC-0004 §4.6: Facts are the only truth. | Record an event; verify no reasoning or approval step reads the record as input. |
| AU2 | **Transcript is never evidence.** The Transcript presents; Facts remain the only evidence model. | RFC-0003 §2.8: Transcript is the Operator-facing account; RFC-0005 §3: Facts are canonical. | Verify no verification or reasoning path consumes a Transcript rendering. |
| AU3 | **Every consequential event is recorded before its consequence.** | RFC-0002 invariant 13; RFC-0001 principle 9. | Trace a full goal; verify each consequential boundary has a prior record. |
| AU4 | **The Audit is append-only and tamper-evident.** No actor edits or erases a prior record. | RFC-0004 A7; RFC-0001 §8.10. | Attempt an edit of a prior record; verify refusal and no silent change. |
| AU5 | **Recording is deterministic.** Format and ordering are fixed by the Audit System within this RFC. | RFC-0004 §4.12 "May decide"; RFC-0007 S7. | Write the same event twice; verify identical, reproducible records. |
| AU6 | **No actor is exempt from being recorded.** Every consequential event is recorded regardless of source. | RFC-0004 §4.12; RFC-0002 §6. | Generate a consequential event from every actor; verify each is recorded. |
| AU7 | **No secret value ever enters the Audit.** The record holds metadata only. | RFC-0009 SC4; RFC-0001 §7.6. | Run a secret lifecycle; verify no value appears in the record or transcript. |
| AU8 | **A failed write blocks its consequence and is disclosed.** Nothing proceeds unrecorded; nothing is invented. | RFC-0004 §9.12; RFC-0002 invariant 13; RFC-0001 §10. | Block the store; verify the next consequence is refused and the Operator is told. |
| AU9 | **The Audit is complete by construction.** Auto-permitted, overridden, and Operator actions are recorded. | RFC-0002 §2.7; RFC-0008 P1; RFC-0001 principle 9. | Auto-permit a read-only action and override a block; verify both are recorded. |
| AU10 | **The Audit is visible and exportable to the Operator at any time.** | RFC-0001 §9.2; RFC-0002 §6. | Read, list, and export the record mid-session; verify complete honest output. |
| AU11 | **Deletion is irreversible, complete, and itself recorded.** | RFC-0001 §9.1, §9.2; RFC-0002 invariant 13. | Wipe records; verify no content remains and the deletion event is recorded. |
| AU12 | **Retention exists only under a stated purpose and is bounded.** | RFC-0001 §9.5, §9; RFC-0009 §27. | Attempt to retain without a purpose; verify refusal and no durable artifact. |
| AU13 | **Recovery is reconciliation, never rewrite.** A lost write is recorded as failed; deleted records never return. | RFC-0004 §9.12; RFC-0001 §9.1; RFC-0012 §21. | Simulate a failed write and a wipe; verify honest reconciliation, no invention, no restore. |
| AU14 | **No hidden retention.** Nothing the Operator cannot see and remove may be retained. | RFC-0001 §9.2; RFC-0003 §2.8 Memory-vs-Audit. | Enumerate retained records; verify every record is visible and removable. |
| AU15 | **The Audit is never Memory and never Context.** No audit retention is a reasoning store. | RFC-0003 §2.8; RFC-0012 CM15; RFC-0009 §27. | Verify no reasoning path consumes Audit records as Context or Memory. |
| AU16 | **The Audit carries no permissions.** Possession of a record grants no authority; records never widen a grant. | RFC-0004 A8; RFC-0001 §8.2 default deny. | Hold a record containing an approval; verify it grants no execution capability. |

---

## 34. Interaction with other RFCs

- **RFC-0001** — principle 9 (everything consequential is audited), RFC-0001
  §5 (Audit & Transcript), §8.10 (append-only and honest), risk 8 (transparency
  not forensics), §9.1–§9.5 (retention, visibility, wipe).
- **RFC-0002** — invariant 13 (recorded before the consequence), RFC-0002 §2.1
  (writability), §2.7 (auto-permitted audited), §6 (write points), §9.14
  (unknown as unknown), §10 (recovery re-orients).
- **RFC-0003** — RFC-0003 §2.8 canonical Audit/Transcript definitions; Part II
  process for the §37 additions.
- **RFC-0004** — RFC-0004 §4.12 Audit System profile, invariants A7/A10;
  implements the Audit System row and A7/A10 (§10).
- **RFC-0005** — RFC-0005 §7 Fact lifecycle records, §13 F8, §15 OQ2 (Fact
  persistence records owned here).
- **RFC-0006** — RFC-0006 §14 verification attempts are audit records; §15 OQ5
  (evidence retention owned here).
- **RFC-0007** — RFC-0007 §16 OQ1 mechanics owned here; §12 View boundary.
  Draft; not a dependency.
- **RFC-0008** — P13 (approval recorded before spent), P10 (overrides audited),
  P1 (classification/decision/issuance in the record); RFC-0008 §3 the audit
  record owned here.
- **RFC-0009** — SC4 (no secret in the Audit), RFC-0009 §15 (metadata-only),
  §20, §26, §27 (retention bounded); SC16 (personal-data parity).
- **RFC-0010** — RFC-0010 §11 and PR14 (the Audit never crosses the provider
  boundary). Draft; not a dependency.
- **RFC-0011** — RFC-0011 §16 Skill events recorded, SK14 (Skill cannot modify
  Audit). Draft; not a dependency.
- **RFC-0012** — CM15 (Context is never the Audit), RFC-0012 §13
  Context-to-Audit boundary, §21 recovery re-presents from the record.
- **RFC-0021** — subsystem vocabulary execution/verification records describe
  (RFC-0021 §4, §11). Referenced, not a dependency.

Forward references: RFC-0014 (resume re-presents from the record); RFC-0015
(Transcript presentation form); RFC-0020 (retention and freshness-bound policy
values); RFC-0000 §8 (no open-question rows assigned here).

---

## 35. Open Questions

Each names its owner. None blocks the accountability model's core guarantees.

1. **Concrete retention periods** per record category — RFC-0020.
2. **Evidence-retention mechanics.** How long verification evidence is kept and
   in what form (RFC-0006 §15 OQ5 mechanics) — RFC-0020.
3. **Transcript presentation form.** How the Operator-facing account is
   rendered (collapsible, searchable, exportable) — RFC-0015.
4. **Resume re-presentation.** Exactly what the record re-presents on resume
   and in what order — RFC-0014.
5. **Export fidelity.** The exact fidelity and shape of a full export — RFC-0015
   (interface) and RFC-0020 (policy).

---

## 36. Risks

| Risk | Mitigation |
|---|---|
| **Audit treated as authority** | Audit is Persist/Explain only; never a decision input (AU1; RFC-0004 §4.12) |
| **Transcript treated as evidence** | Facts are the only evidence model; Transcript presents (AU2; RFC-0005 §3) |
| **Consequence proceeding unrecorded** | Write-before-consequence ordering; failed writes block (AU3, AU8; RFC-0002 invariant 13) |
| **Record edited after the fact** | Append-only, tamper-evident (AU4; RFC-0004 A7) |
| **Secret value in the record** | Metadata-only audit (AU7; RFC-0009 SC4) |
| **Retention outliving purpose** | Purpose-limited, bounded retention; lapse is deletion (AU12; RFC-0009 §27) |
| **Deletion being a silent gap** | Deletion is irreversible, recorded, and complete (AU11; RFC-0002 invariant 13) |
| **Rubber-stamp approvals invisible** | The gate's records are the most important; visible by default (AU9; RFC-0008 P13) |
| **Recovery fabricating a lost record** | Reconciliation, never rewrite; failed writes are recorded as failed (AU8, AU13) |
| **Extension adding a silent event** | New consequential events are amendments; invariant 13 applies (AU3; §32) |

---

## 37. Vocabulary Additions for RFC-0003

The following terms are defined in this RFC and must be added to RFC-0003 Part
I by additive amendment: **Audit Record Category**, **Transcript Record
Category**, **Audit Boundary**, **Consequential Event**, **Reconciliation** —
defined at first use in §7, §8, §9, §16, and §22. Audit, Transcript, Fact,
Outcome, Verification, Approval, Override, Secret, Context, and Memory already
exist in RFC-0003 Part I and are used here with their canonical meanings.

---

*End of RFC-0013. Normative: sections 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31,
32, 33. Explanatory and load-bearing: sections 0, 34, 35, 36, 37. Any change
to an Audit or Transcript category, ownership, authority, transition,
retention rule, deletion rule, integrity rule, or an invariant AU1–AU16 is a
BREAKING change and must be made by amendment (RFC-0003 Part II).*
