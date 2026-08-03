# RFC-0012 — Context & Memory Architecture

**Status:** Draft
**Date:** 2026-08-02
**Scope:** The single canonical model for every piece of information carried
through a session: what Context is and what Memory is; the distinction between
them; every Context and Memory category; what enters Context and what never
does; Context ownership, authority, lifecycle and legal transitions,
composition, boundaries, isolation, propagation, freshness, invalidation,
visibility, trust, destruction, and recovery; the persistence, minimization,
and privacy philosophies; Context interaction with Facts, Verification,
Providers, Skills, Diagnostics, Approval, Audit, Secrets, the Runtime, and
future extensions; and the Context invariants CM1–CM16.
**Audience:** Future maintainers
**Supersedes:** Nothing
**Depends on:** RFC-0001, RFC-0002, RFC-0003, RFC-0004, RFC-0005, RFC-0006,
RFC-0007, RFC-0008, RFC-0009 (accepted in this series). RFC-0010 and RFC-0011
are referenced for the boundaries they already state; both are Drafts and are
not dependencies.

**Roadmap note:** This is RFC-0000's "RFC-0012 — Context & Memory Architecture"
(Runtime, Required), the document that fixes what may be remembered before the
MVP (RFC-0000 §5). It answers the coverage rows RFC-0000 §8 assigns to it:
RFC-0001 Q13 (the exact persistence model) and RFC-0002 Q12 (how replies route
against an outstanding question). It also owns the mechanics deferred to it:
RFC-0007 §16 OQ1 (exact sanitization mechanics at the enforcement point) and
OQ6 (the detection-vs-containment stance), RFC-0010 §15 OQ3 (how Context and
Memory assemble the Provider View), and RFC-0011 §26 rule 5 (Context
assembly). It implements the Context Manager's Persist authority and consent
model (RFC-0004 §10).

**BREAKING:** No. This RFC specifies the model that RFC-0001, RFC-0002,
RFC-0004, RFC-0005, RFC-0006, RFC-0007, RFC-0008, RFC-0009, RFC-0010, and
RFC-0011 already assume and cite — Context is the sanitized, purpose-limited,
size-bounded, secret-free material a Provider receives as a Provider View
(RFC-0003 §2.8); Context Building is the only place LLM input is assembled
(RFC-0002 §2.4); Facts remain the only source of truth (RFC-0004 §4.6);
Memory exists only under Operator consent (RFC-0001 §9.5); and no secret ever
enters Context (RFC-0009 SC2, RFC-0007 T10). It does not weaken any Principle,
Boundary, Invariant, or canonical Definition in an accepted RFC.

---

## 0. Purpose

> **What is Context, what is Memory, and how does the system guarantee that
> the only thing a Provider ever sees is a purpose-limited, bounded,
> secret-free representation of the current reasoning state — while Facts stay
> the only source of truth and durable Memory exists only by consent?**

Three binary guarantees fix everything below:

1. **Context is assembled, never authoritative.** No component treats Context
   as a source of truth, because the Fact Layer is the only one (RFC-0004 §4.6).
2. **Memory is a consented subset, never an authority.** Durable Memory is a
   promotion from Context material that exists only by Operator consent and
   decides nothing.
3. **Context is the only channel outward.** The Provider receives exactly the
   Provider View, assembled from Context by Context Building, and nothing else
   (RFC-0002 §2.4; RFC-0007 T3).

---

## 1. What is Context

**Context** is the sanitized, purpose-limited, size-bounded, secret-free set
of Facts, history, Goal, and skill material the runtime holds for reasoning
(RFC-0003 §2.8). It is the working set of the current step and the only thing
a Provider ever receives, delivered as a Provider View (RFC-0002 §2.4).

1. **Assembled, never inherited.** Produced only by Context Building (RFC-0002
   §2.4), from Facts, bounded history, the Goal, skill material, and evidence.
2. **A cache of evidence, not a claim** (RFC-0001 §9.4). It asserts nothing; it
   carries material for reasoning about the Goal.
3. **Session-scoped by default** (RFC-0001 §9.5). It dies with the session
   unless promoted to Memory by consent.
4. **Never a source of truth.** Context consumes Facts; it never authors them
   (RFC-0004 §4.6; CM1).

---

## 2. What is Memory

**Memory** is the portion of Context the runtime is authorized to retain
beyond immediate need — the durable subset — kept only by explicit Operator
consent and subject to purpose-limits (RFC-0003 §2.8; RFC-0001 §9.5).

1. **A promotion, not a separate store.** What becomes Memory is first Context
   material; consent moves it across the session boundary. No unconsented
   second collection exists.
2. **For reasoning, not for record.** Memory feeds future Context Building; the
   recorded history of events is the Audit's (RFC-0003 §2.8).
3. **Reversible.** Consent can be withdrawn; a wipe removes the promoted
   material (RFC-0001 §9.2).
4. **Never authority.** Memory may be re-assembled into future Context but
   never Proposes, Approves, Executes, Verifies, or decides what is true (CM2).

---

## 3. Context vs Memory

| Dimension | Context | Memory |
|---|---|---|
| Role | Working set of the current step | Durable subset for future steps |
| Lifetime | Session-scoped by default | Outlives the session, by consent |
| Entrance | Assembled by Context Building | Promoted from Context by consent |
| Exit | Destroyed at session end | Wiped or purpose-lapsed |
| Channel | → Provider View (the only channel) | → future Context Building (re-assembly) |
| Source of truth | Never (CM1) | Never (CM2) |
| Record | Never (Context is not the Audit) | Never (Memory is not the Audit) |

The distinction is **lifetime and consent**, not content type: the same kind
of material may be Context now and Memory later. What never varies is that
neither decides anything and neither is truth.

---

## 4. Context Ownership

Every thing has exactly one owner per responsibility (RFC-0004 §3):

| Thing | Owner | Delegated through | Never owned by |
|---|---|---|---|
| Context assembly and custody | Context Manager | — | Operator, Providers, Skills, Diagnostics, Fact Layer, Policy Engine, Approval Engine, Executor, Orchestrator, Audit System |
| Durability decision | Operator | Context Manager (custody under consent) | Context Manager (cannot persist without consent), everyone else |
| Memory custody | Context Manager | — | Providers, Skills, Diagnostics, Fact Layer, Policy Engine, Approval Engine, Executor, Audit System |

- **The Context Manager owns assembly:** builds Context from Facts and history,
  applies sanitization and purpose-limits, enforces the no-secrets boundary,
  and assembles the Provider View (RFC-0004 §2, §4.11).
- **The Operator owns durability:** nothing persists without explicit consent;
  the Operator can always see, export, and wipe (RFC-0001 §9.2; RFC-0004 §3
  Memory row).
- **No other component owns, writes, or decides about Context.** The Fact Layer
  supplies Facts; the Context Manager decides what enters Context within the
  bounds RFC-0009 and RFC-0012 set (RFC-0004 §4.11).

---

## 5. Context Authority

Authority is the tool that lets an owner discharge responsibility (RFC-0004
§6). The Context Manager's authority is narrow and enumerated:

1. **Assemble** — build Context and the Provider View from approved material.
   The Context Manager alone (RFC-0004 §4.11).
2. **Filter and sanitize** — apply purpose-limits, size bounds, and
   sanitization (RFC-0007 S1–S8) before material enters Context or a View.
3. **Persist durable** — promote Context material to Memory, **only under
   Operator consent** (RFC-0004 §4.11, §3 Memory row).
4. **Observe** — consume Facts as a reader; never produce or edit them
   (RFC-0004 §5 Observe row).

No component holds authority to: decide what is true (RFC-0004 §4.6), include
a secret (RFC-0004 §4.11), persist without consent (RFC-0004 §4.11), or treat
Context or Memory as an execution or approval input. These are not privileges
withheld from most components but ones held by none.

---

## 6. Context Categories

Context has exactly six categories of material for reasoning; none is truth,
record, or authority.

1. **Goal** — the active Goal statement and its scope. One active Goal per
   session (RFC-0002 §2.3; multi-goal policy is RFC-0014's).
2. **Facts** — current, provenance-carrying, freshness-bounded Facts relevant
   to the Goal, held under RFC-0005. The only category trusted as Fact
   (RFC-0007 §9).
3. **History** — bounded conversation and turn history: Operator input,
   Provider replies, proposals presented, decisions taken. Material, never
   Facts; proposals and hypotheses are labeled (RFC-0007 §12).
4. **Evidence** — verification Outcomes and their evidence (RFC-0006 §14
   forward reference). Outcomes enter as Facts or labeled evidence, never as
   verification power.
5. **Skill material** — applicable Skill content, sanitized and bounded
   (RFC-0011 §26); Skill code never enters Context (RFC-0007 §6.12).
6. **Routing state** — the minimal state to route the next input: the
   outstanding-question marker and the current decision pointer. Answers
   RFC-0002 Q12 (§33). Process state, never evidence, never truth.

---

## 7. Memory Categories

Memory has exactly three categories. All are promotions from Context under
consent; none may hold a secret, raw output, or personal data without explicit
Operator demotion (RFC-0009 SC16).

1. **Preference Memory** — Operator preferences: verbosity, provider choice,
   skill selection (RFC-0001 §9). The Operator's own decisions about behavior.
2. **Machine Memory** — high-signal Facts about the machine, *collected, not
   guessed*, retained across sessions under consent (RFC-0001 §9).
3. **Durable Context** — anything the Operator explicitly asked to be
   remembered beyond the session, purpose-scoped and reversible (RFC-0001 §9).

Never a Memory category: secret values (RFC-0009), raw unbounded command
output (RFC-0001 §9), the Audit record (RFC-0003 §2.8), and content marked
private without an explicit demotion (RFC-0009 §14).

---

## 8. What Enters Context

Only what serves the current Goal's purpose may enter, and only through the
Context Manager (RFC-0004 §4.11):

1. **Facts** — from the Fact Layer, at their trust class and freshness state
   (RFC-0005 §3, §12). Never raw Observations.
2. **The Goal** — the active goal statement and scope.
3. **Bounded history** — labeled, sanitized conversation and turn material
   (RFC-0007 §12).
4. **Evidence and Outcomes** — verification results as Facts or labeled
   evidence (RFC-0006).
5. **Skill material** — sanitized and bounded (RFC-0011 §26).
6. **Routing state** — the outstanding-question marker and current pointer.

Everything enters purpose-filtered, sanitized, and size-bounded; nothing
enters as a dump (RFC-0001 §9; RFC-0007 S8).

---

## 9. What Never Enters Context

Fixed exclusions, not judgment calls:

1. **Secret values, in any form** (RFC-0009 SC2; RFC-0007 T10). No exception
   for derived artifacts.
2. **Raw, unbounded machine output** (RFC-0001 §9). Only normalized Facts
   enter.
3. **Unprovenanced claims.** A claim without provenance is not a Fact and
   cannot enter as one (RFC-0005 §13 F10).
4. **Hostile or quarantined content** (RFC-0007 §15.5).
5. **Skill code** (RFC-0007 §6.12).
6. **Personal data not required for the task** (RFC-0001 §9), unless the
   Operator explicitly marks or demotes it (RFC-0009 SC16).
7. **Anything without a stated purpose** (RFC-0001 §9). If the runtime cannot
   say why material is in Context, it must not be.

---

## 10. Context Lifecycle

Context moves through a deterministic lifecycle driven by the runtime's events
(RFC-0002 §4):

| State | Meaning |
|---|---|
| **Empty** | No Context yet. |
| **Assembling** | Context Building is constructing the working set (RFC-0002 §2.4). |
| **Current** | A valid working set is ready; a Provider View can be built. |
| **Stale** | A carried Fact lapsed or a state change invalidated the set (RFC-0005 §12; RFC-0002 §4.2). |
| **Consolidated** | Overflow forced bounding and consolidation (RFC-0001 §9.3); Current in content, smaller. |
| **Promoted** | Portions moved to Memory by consent (§22). |
| **Destroyed** | The working set is gone — session end, purpose lapse, or wipe (§20). |

---

## 11. Legal Transitions

Every legal transition is listed; anything not listed is illegal (default
deny, RFC-0001 §8.2).

| From | To | Trigger | Who |
|---|---|---|---|
| Empty | Assembling | New Goal, or resume re-orient | Context Manager (RFC-0002 §2.4) |
| Assembling | Current | A valid working set was built | Context Manager |
| Current | Assembling | New facts, new reply, replanning, stale, consolidation | Context Manager (RFC-0002 §2.4) |
| Current | Stale | STATE_CHANGED_DETECTED, freshness lapse, reboot/interrupt | Runtime (RFC-0002 §4.2; invariant 8) |
| Stale | Assembling | Re-inspection then rebuild | Context Manager (RFC-0005 §12) |
| Current | Consolidated | Overflow past the size bound | Context Manager (RFC-0001 §9.3) |
| Current | Promoted | Operator consent to retain | Operator + Context Manager (§22) |
| Any | Destroyed | Session end, purpose lapse, Operator wipe | Context Manager (RFC-0001 §9.1, §9.2) |

**Illegal:** Assembling → Provider directly (the View is built only at the
Context Building exit, RFC-0002 §2.4); Stale → Current without re-inspection
(RFC-0005 §12); any state → Promoted without consent; Destroyed → Current
(Context is rebuilt, never resurrected, §21).

---

## 12. Context Composition

Composition is the deterministic rule for what a valid working set contains
and in what order it is assembled (RFC-0002 §2.4). Owned by the Context
Manager, not by any producer of material.

1. **Facts first, with provenance.** Relevant, fresh Facts enter with
   provenance and status; stale Facts are re-collected or excluded (RFC-0005
   §5, §12).
2. **Goal and scope next.** The Goal statement and its purpose bound what else
   may enter (RFC-0001 §9.1).
3. **Bounded history after**, sanitized and labeled (RFC-0007 §12).
4. **Skill material last**, through the sanitization enforcement point
   (RFC-0011 §26; RFC-0007 §16 OQ1).
5. **Routing state folded in** (§6 category 6; §33).
6. **Bounds applied at assembly, not after.** Purpose-limits, size bounds, and
   the no-secrets rule apply during assembly so nothing needs post-hoc
   scrubbing (RFC-0001 §9).

Composition is deterministic and testable (RFC-0007 S7): given the same
inputs, purpose, and bounds, the same Context results.

---

## 13. Context Boundaries

A Context boundary is a point where material changes holder, purpose, or form:

| Boundary | What may cross | What never crosses | Enforcement |
|---|---|---|---|
| Machine → Observation → Fact → Context | Normalized Facts (RFC-0005 §2, §3) | Raw output; secret-shaped values (RFC-0009 §18) | Fact Layer; redaction before Context (RFC-0009 §11) |
| Skill → Context | Sanitized, bounded Skill material (RFC-0011 §26) | Skill code; secrets (RFC-0011 §15) | Context Manager sanitization point |
| Provider reply → History → Context | Labeled proposals and hypotheses (RFC-0007 §12) | Provider output as Fact | Context Building labels; Fact Layer never reads Provider output |
| Context → Provider View | Sanitized, secret-free material (RFC-0002 §2.4) | Secret values (RFC-0009 SC3); unprovenanced claims | Context Building, the only channel (RFC-0007 T3) |
| Context → Memory | Consented material (RFC-0001 §9.5) | Secrets; raw output; unconsented content | Operator consent gate (§22) |
| Context → Audit | A record that material entered (RFC-0004 §9.11) | Context itself as a record (RFC-0009 §31) | Audit System (RFC-0013) |

Every boundary is one-way: material enters Context only by assembly and leaves
only as a Provider View, a consent promotion, or destruction.

---

## 14. Context Isolation

Context is isolated by construction; there is one Context per session and no
component holds a second one.

1. **No cross-session Context.** Session A's working set never merges into
   Session B's. Cross-session re-entry is only Memory under consent (§22) or
   the Audit (RFC-0014).
2. **One active Goal.** The working set is scoped to the single active Goal
   (RFC-0002 §2.3); multi-goal separation is RFC-0014's.
3. **No component-side Context.** Providers, Skills, Diagnostics, and the Audit
   System carry no Context of their own; they see only what the Context Manager
   hands them (RFC-0004 §4.11).
4. **Isolation is not secrecy's job.** Even without secrets, no component
   accumulates a private reasoning set; the Context Manager is the only
   assembler (CM3).

---

## 15. Context Propagation

Context travels through exactly four paths, and no others:

1. **Context → Provider View.** The only outward channel; built per Provider
   call (RFC-0002 §2.4; RFC-0007 T3).
2. **Context → next Context Building.** The working set carries forward through
   re-assembly within a session (RFC-0002 §2.4).
3. **Context → Memory.** A consent promotion across the session boundary (§22).
4. **Memory → Context.** Consented material re-enters by re-assembly, never by
   injection (RFC-0002 §2.4).

No other propagation exists: no store copies Context wholesale, no extension
receives Context, and the Audit receives records about Context, not Context
(RFC-0009 §31).

---

## 16. Context Freshness

Context has no independent freshness; it inherits the freshness of the Facts
it carries (RFC-0005 §12). There is deliberately no second freshness model.

1. **Context is Current only while its carried Facts are Current.** A working
   set containing a Stale, Expired, or Unknown-freshness Fact is itself Stale
   (RFC-0005 §12).
2. **Stale Context is rebuilt, never patched.** The next decision that consumes
   the Fact re-inspects first (RFC-0002 §4.2; RFC-0005 §12).
3. **Freshness bounds belong to RFC-0005.** This RFC fixes only that Context
   must respect them; per-category bounds are RFC-0020's (§37 OQ1).

---

## 17. Context Invalidation

Invalidation is deterministic and precedes use:

1. **State change detected** — the read-only watchdog observed external change;
   dependent Facts are invalidated and Context is marked stale (RFC-0002 §4.2).
2. **Freshness lapse** — a carried Fact passed its bound (RFC-0005 §12).
3. **Interruption, reboot, or machine-identity change** — Context is
   re-established, never trusted across the gap (RFC-0002 invariant 8).
4. **Contradiction or provenance loss** — content falls to a lower trust class
   and is re-collected before further use (RFC-0007 §9; RFC-0002 invariant 10).

Invalidation marks the set Stale and forces re-assembly; it is not destruction
(§20) and it is recorded (RFC-0002 invariant 13). A corrupted Context degrades
reasoning, never execution, and is re-observable via Verification (RFC-0004
§9.11; RFC-0006).

---

## 18. Context Visibility

Visibility is the Operator's window into what the runtime holds (RFC-0001
§9.2):

1. **Always visible.** The Operator can see what Context the session reasons
   over and what Memory exists, in plain form.
2. **Export is complete** (RFC-0001 §9.2).
3. **Wipe is always available** — Context, Memory, or both, immediately
   (RFC-0001 §9.2; RFC-0009 §23 analog).
4. **Honest about provenance.** Facts are labeled Facts, history is history,
   hypotheses are hypotheses (RFC-0007 §12).
5. **No hidden retention.** Nothing the Operator cannot see and remove may be
   retained (RFC-0001 §9.2; CM14).

---

## 19. Context Trust

Trust is a property of information (RFC-0004 §2); Context's trustworthiness is
exactly the trustworthiness of its contents, never more.

1. **Context adds no truth.** Assembly does not upgrade a claim's trust class;
   sanitization makes text unable to carry a payload, not trustworthy (RFC-0007
   S1).
2. **Each category is trusted at its own class.** Facts at their trust class
   (RFC-0007 §9); history and hypotheses labeled, never Facts (RFC-0007 §12);
   Skill material sanitized and bounded (RFC-0007 §6.11).
3. **Context is not an execution input.** Nothing in Context is interpolated
   into a command (RFC-0002 invariant 5).
4. **The stance is containment.** Detection of injection is a defense-in-depth
   bonus; containment is the guarantee (RFC-0007 §16 OQ6; §15.8).
5. **Corrupted Context degrades reasoning, never execution** (RFC-0004 §9.11),
   and Verification re-establishes ground truth (RFC-0006).

---

## 20. Context Destruction

Destruction is a first-class lifecycle step (RFC-0001 §9.1):

1. **Destroy when the purpose lapses** — session end, abandoned Goal, or a
   purpose that no longer justifies the material.
2. **Destroy on Operator request** — anytime, immediately, including wipe of
   Memory (RFC-0001 §9.2).
3. **Destroy without resurrection** — a destroyed working set is rebuilt, never
   restored; there is no trash can for Context or Memory (§21).
4. **Destroy completely and record it.** Every copy is gone; the Audit records
   that destruction happened, never the destroyed material (RFC-0002 invariant
   13; RFC-0009 §31).

---

## 21. Context Recovery

Recovery of a lost or corrupted working set is **re-assembly, never restore**:

1. **Rebuild from Facts, Audit, and consented Memory.** Ground truth is
   re-collected (RFC-0005 §12), the Audit re-presents what happened (RFC-0013),
   and consented Memory may re-enter; no stale snapshot is resurrected.
2. **Re-orient before proceeding.** After interrupt, reboot, or identity
   change, actual state is re-established deterministically before further
   machine action (RFC-0002 invariant 8).
3. **Recovery is a feature.** Because Context is assembled, losing it costs
   only re-assembly; nothing irreplaceable was ever in it.
4. **Memory survives per RFC-0014.** Which Memory survives a resume is
   RFC-0014's; whatever survives is consented and re-assembled, never injected
   (RFC-0000 §4 RFC-0014 dependency).

---

## 22. Context Persistence Philosophy

This section answers RFC-0001 Q13: the exact persistence model, what is
session-only, what is durable, and the consent flow.

1. **Session-scoped by default.** Everything the session materializes is gone
   when the session ends (RFC-0001 §9.5; RFC-0009 §27).
2. **Durable only by explicit, reversible consent.** The single promotion path
   is Context → Memory, gated on a stated purpose (RFC-0001 §9.1, §9.5). The
   Operator grants it; the Context Manager executes it (RFC-0004 §4.11).
3. **Nothing persists without a stated purpose** (RFC-0001 §9). "Might be
   useful later" is not a purpose.
4. **Retention is by consent, not by default** (RFC-0001 §9.5). Every durable
   artifact is an exception the Operator made.
5. **No second store.** There is no unconsented background collection; the
   Audit is record, not Memory, and never a Memory backdoor (RFC-0003 §2.8).

---

## 23. Context Minimization Philosophy

Context holds the least material that serves the current purpose:

1. **Purpose-limited.** Material enters only in service of the Goal or a stated
   future need (RFC-0001 §9.1).
2. **Bounded.** There is a ceiling on how much Context is carried; on overflow
   the Context Manager consolidates or drops, transparently, never silently
   growing (RFC-0001 §9.3).
3. **Consolidation is a sanitization.** Bounding and truncation are explicit
   (RFC-0007 S8, T10) and operate on already-secret-free material, so they
   cannot reveal a secret (RFC-0009 §19).
4. **Never collect "for later."** Diagnostic output enters as Facts on demand;
   the machine is not watched or scraped (RFC-0001 §2 non-goal 4).
5. **Every element justifies its place** (RFC-0001 §9).

---

## 24. Context Privacy Philosophy

Privacy is enforced at the Context boundary, not after:

1. **Secret-free by construction** (RFC-0009 SC2; RFC-0007 T10). The Context
   Manager is the enforcement point (RFC-0009 §19; §32).
2. **Privacy parity for personal data.** Personal data is governed by the same
   boundaries as secrets unless the Operator explicitly demotes it (RFC-0009
   SC16).
3. **Consent governs durability.** Nothing is retained beyond the session
   without consent (§22); nothing marked private persists (RFC-0001 §9).
4. **No Context telemetry.** Context values are never part of any telemetry or
   crash report (RFC-0009 §26).
5. **Transparency is the mechanism.** The Operator sees what is held and can
   wipe it (RFC-0001 §9.2); privacy is auditable, not a promise about
   internals.

---

## 25. Context Interaction with Facts

1. **Context carries Facts; it never produces them.** The Fact Layer owns truth
   (RFC-0004 §4.6); Context holds Fact material for reasoning (RFC-0005 §3).
2. **Fact storage is Context's.** Where and how Facts are stored belongs to
   this RFC and RFC-0013; RFC-0005 fixes only what each lifecycle step means
   (RFC-0005 §7).
3. **Fact lifecycle drives Context.** Creation, replacement, expiration, and
   retirement of a Fact invalidate or refresh the Context that carries it
   (RFC-0005 §7; §17).
4. **Context never contradicts a Fact.** If Context and a fresh Fact differ,
   the fresh Fact wins and Context is rebuilt (RFC-0001 §9.4; RFC-0002
   invariant 10).

---

## 26. Context Interaction with Verification

1. **Verification never reads Context.** Compare operates on Facts and machine
   state, deterministically (RFC-0006 §3, V8).
2. **Outcomes and evidence are Context material.** Verification Outcomes enter
   Context as Facts or labeled evidence (RFC-0006 §14 forward reference).
3. **Corrupted Context degrades reasoning, not verification.** A broken working
   set cannot corrupt an Outcome; Verification re-observes ground truth
   (RFC-0004 §9.11; RFC-0006 V8).
4. **Context is re-observable via Verification.** Suspicion that Context is
   wrong is resolved by fresh Facts, never by trusting Context (RFC-0002
   invariant 10).

---

## 27. Context Interaction with Providers

1. **The View is the only channel** (RFC-0007 T3; RFC-0010 PR14). Providers
   never receive Context raw.
2. **Provider replies are material, not Facts.** Model output is untrusted data
   (RFC-0004 A1); it enters History labeled as proposals or hypotheses and
   never becomes a Fact through Context (RFC-0007 §12; RFC-0005 F1).
3. **Providers never read Memory.** Durability is a Core concern; providers
   have no Memory surface (RFC-0004 §4.11).
4. **Assembly is owned here.** How Context and Memory assemble the View from
   Facts and history is this RFC's and RFC-0015's (RFC-0010 §15 OQ3).

---

## 28. Context Interaction with Skills

1. **Skill content enters sanitized and bounded.** Applicable Skill content is
   Context material only after the sanitization enforcement point (RFC-0011
   §26; RFC-0007 §16 OQ1).
2. **Skill text is not a Fact** — material, normalized into Facts only through
   RFC-0005 (RFC-0007 §6.11; RFC-0011 §26).
3. **Skill code never enters Context** (RFC-0007 §6.12; RFC-0011 §26).
4. **Skills have no Context surface.** A Skill receives input through the
   runtime's sanctioned channel and persists nothing (RFC-0011 §15, SK8).

---

## 29. Context Interaction with Diagnostics

1. **Diagnostics never write Context.** They produce Observations; the Fact
   Layer normalizes them into Facts (RFC-0005 §2); only Facts enter Context
   (§8).
2. **Raw Observations never enter Context** — untrusted machine text until
   normalized (RFC-0007 §4; RFC-0005 §2).
3. **Secret-adjacent Observations are quarantined before Context** (RFC-0009
   §18), never adopted, never Facts.
4. **Failed collectors are "fact unknown."** A failed inspection yields Unknown
   freshness, never a fabricated Context entry (RFC-0002 §4.2; RFC-0005 §13
   F14).

---

## 30. Context Interaction with Approval

1. **The gate never reads raw Context.** Classification and Approval consume
   normalized Proposals and Facts (RFC-0001 §8.5; RFC-0008 §6).
2. **Context carries no permissions.** Possession of Context or Memory grants
   no authority to act (RFC-0004 §5 Approve; RFC-0008).
3. **No Action carries Context.** Proposals and Actions are normalized
   structures (RFC-0003 §2.8), secret-free by construction (RFC-0009 SC9).
4. **Memory never widens a grant.** Durable material is reasoning material; it
   cannot upgrade an Action's risk class or bypass a gate (CM16; RFC-0004 A8).

---

## 31. Context Interaction with Audit

1. **Audit records that material entered Context** (RFC-0004 §9.11), never the
   material itself (RFC-0009 SC4).
2. **Context is not the Audit.** Context is ephemeral and for reasoning; Audit
   is durable and for record (RFC-0003 §2.8).
3. **Memory is not the Audit.** No Memory retention is a record, and no audit
   retention rule may preserve Context or Memory material (RFC-0009 §27).
4. **Ordering is shared.** The Audit records before the consequence (RFC-0002
   invariant 13); Context destruction is likewise recorded before it completes
   (§20).

---

## 32. Context Interaction with Secrets

1. **Context is secret-free by construction** (RFC-0009 SC2; RFC-0007 T10).
   The Context Manager may never decide to include a secret (RFC-0004 §4.11).
2. **The rule is RFC-0009's; the mechanics are this RFC's** (RFC-0009 §19).
   RFC-0009 classifies and redacts; this RFC specifies the enforcement point.
3. **Truncation and consolidation cannot reveal a secret** because they operate
   on already-secret-free material (RFC-0009 §19; §23).
4. **No secret enters a Provider View** (RFC-0009 SC3; RFC-0010 §11).
5. **Suspected exposure invalidates, never rehydrates.** A suspected-compromise
   secret is destroyed; Context is re-assembled from clean Facts, never from
   material that touched the secret (RFC-0009 SC15; RFC-0007 §6.10).

---

## 33. Context Interaction with Runtime

1. **Context Building is the only assembler** and is a runtime state (RFC-0002
   §2.4); every provider consultation follows a fresh Context Building.
2. **State change invalidates Context.** STATE_CHANGED_DETECTED marks the
   working set stale and forces re-inspection before the next decision
   (RFC-0002 §4.2).
3. **Answer to RFC-0002 Q12 (context-routing of replies).** The outstanding-
   question marker is Context's Routing-state category (§6 category 6). A reply
   routes against the last outstanding question. If the Operator answers with a
   *new question*, the new question supersedes the marker: the superseded
   question is disclosed as superseded (never silently dropped) and the new
   question becomes active, re-entering Context Building. This is how Awaiting
   Input routes without a second store.
4. **Interrupted work re-establishes Context.** After interruption or reboot,
   the working set is rebuilt from Facts and consented Memory before any
   further machine action (RFC-0002 invariant 8; §21).

---

## 34. Context Interaction with Future Extensions

1. **Any future RFC that adds content to Context must re-check RFC-0007 §12**
   — a new untrusted source routed into the View unlabeled returns the binary
   risk of RFC-0001 risk 2 (RFC-0007 §16 risk 3).
2. **New Context categories are additive amendments.** Adding a category
   changes composition and bounds, which are normative here (RFC-0003 Part II).
3. **No extension owns Context or Memory.** The Context Manager is the single
   owner (§4); extensions are consumers or producers through contracts.
4. **RFC-0014 uses this model** (what Memory survives a resume); RFC-0015 uses
   it (presentation); RFC-0020 implements it (storage and freshness bounds,
   §37 OQ1–OQ2).

---

## 35. Context Rules (Normative)

| ID | Statement | Rationale | Test |
|---|---|---|---|
| CM1 | **Context is never a source of truth.** Facts remain the only source of truth; Context is their consumer. | RFC-0004 §4.6: Fact Layer owns truth; RFC-0001 §9.4: Context is a cache of evidence. | Build Context; verify no reasoning result is accepted as a Fact without Fact-Layer provenance. |
| CM2 | **Memory is never authority.** Durable Memory decides, proposes, approves, executes, or verifies nothing. | RFC-0003 §2.8: Memory is for reasoning; RFC-0004 §5 authority rows exclude Context/Memory. | Promote material to Memory; verify no authority decision reads it as input. |
| CM3 | **Only the Context Manager assembles Context.** No other component writes Context, Memory, or a Provider View. | RFC-0004 §4.11: Context Manager builds Context; RFC-0002 §2.4: the only assembly point. | Instrument every component; verify only the Context Manager constructs the working set. |
| CM4 | **Context is secret-free by construction.** No secret value ever enters Context in any form. | RFC-0009 SC2; RFC-0007 T10; RFC-0004 §4.11. | Feed a known token through assembly; verify it appears nowhere in Context or its View. |
| CM5 | **Context is purpose-limited.** Nothing enters Context without a stated purpose in service of the Goal. | RFC-0001 §9.1: purpose-limited; RFC-0001 §9: nothing without a purpose is kept. | Request material unrelated to the Goal; verify it is excluded and refused. |
| CM6 | **Context is bounded.** Size bounds are enforced and overflow is consolidated, never silently grown. | RFC-0001 §9.3: bounded; RFC-0007 S8, T10: bounding is a sanitization. | Overload Context past its bound; verify transparent consolidation, never unbounded growth. |
| CM7 | **Context is fresh or rebuilt.** Stale material is re-collected before use as current evidence. | RFC-0005 §12: stale truth is not truth; RFC-0002 §4.2. | Age a carried Fact past its bound; verify the next decision re-inspects first. |
| CM8 | **Context invalidation is deterministic and precedes use.** State change and freshness lapse invalidate dependent material. | RFC-0002 §4.2; RFC-0005 §12; RFC-0002 invariant 13. | Trigger STATE_CHANGED_DETECTED; verify dependent Context is marked Stale and recorded before any use. |
| CM9 | **Context is session-isolated.** One working set per session; no cross-session merge without consent. | RFC-0002 §2.3 single Goal; §14 isolation. | Run two sessions; verify no material from one appears in the other except by Memory promotion. |
| CM10 | **Context propagates only by assembly.** The Provider View is the only outward channel; nothing copies Context. | RFC-0002 §2.4; RFC-0007 T3; RFC-0010 PR14. | Instrument all copies; verify the View is the only material leaving Context. |
| CM11 | **Durable Memory exists only by explicit, reversible consent.** No promotion without a stated purpose. | RFC-0001 §9.5: consent, not default; RFC-0004 §4.11 Persist under consent. | Attempt a promotion without consent; verify refusal and no durable artifact. |
| CM12 | **Context destruction is complete and recorded.** Purpose lapse, session end, or wipe destroys every copy. | RFC-0001 §9.1, §9.2; RFC-0002 invariant 13. | Wipe Context and Memory; verify no copy remains and destruction is in the Audit. |
| CM13 | **Context recovery is re-assembly, never restore.** No stale or destroyed snapshot is resurrected. | RFC-0002 invariant 8; §21 recovery. | Simulate a lost working set; verify rebuild from Facts, never from a snapshot. |
| CM14 | **Context is visible, exportable, and wipable by the Operator.** | RFC-0001 §9.2; §18 visibility. | List, export, and wipe the retained set; verify complete and honest output. |
| CM15 | **Context is never the Audit.** The Audit records about Context; Context and Memory are never records. | RFC-0003 §2.8; RFC-0009 §31; RFC-0004 §9.11. | Verify the Audit holds no Context or Memory dump and no secret value. |
| CM16 | **Context and Memory carry no permissions.** Possession grants no authority; Memory never widens a grant. | RFC-0004 A8: no actor extends its own grant; RFC-0001 §8.2 default deny. | Hold Context containing a credential-like value; verify it grants no execution or approval capability. |

---

## 36. Interaction with other RFCs

- **RFC-0001** — context philosophy (RFC-0001 §9, §9.1–§9.5), responsibilities
  (RFC-0001 §5), extensions (RFC-0001 §11); answers Q13.
- **RFC-0002** — Context Building (RFC-0002 §2.4), events and state-change
  invalidation (RFC-0002 §4.2), invariants 8 and 10; answers Q12 (here, §33).
- **RFC-0003** — canonical vocabulary (RFC-0003 §2.8); Part II amendment process
  for the §39 additions.
- **RFC-0004** — Context Manager profile/authority (RFC-0004 §4.11), Memory
  ownership row (RFC-0004 §3), corruption blast-radius (RFC-0004 §9.11);
  implements Persist authority (RFC-0004 §10).
- **RFC-0005** — Facts are what Context carries (RFC-0005 §3, §12); Fact storage
  is this RFC's (RFC-0005 §7); freshness and provenance rules are RFC-0005's.
- **RFC-0006** — Verification consumes Facts, never Context (RFC-0006 §3);
  Outcomes and evidence are Context material (RFC-0006 §14).
- **RFC-0007** — sanitization (S1–S8), trust classes, Provider View boundary
  (RFC-0007 §12), failure modes (RFC-0007 §15); mechanics of RFC-0007 §16 OQ1
  and OQ6 are owned here.
- **RFC-0008** — the gate consumes Facts and Proposals, never Context (RFC-0008
  §6, §2); context assembly is owned here (RFC-0008 §2).
- **RFC-0009** — secret-free Context rule and enforcement point (RFC-0009 §19,
  SC2); personal-data parity (SC16); telemetry posture (RFC-0009 §26).
- **RFC-0010** — no-secrets-to-providers boundary (RFC-0010 §11); assembly
  owned here (RFC-0010 §15 OQ3).
- **RFC-0011** — no-secrets Skill boundary (RFC-0011 §15, SK8); Skill material
  sanitized and bounded (RFC-0011 §26); assembly owned here (RFC-0011 §26 rule
  5).
- **RFC-0021** — machine subsystems as the Subject vocabulary of carried Facts
  (RFC-0021 §4, §11). Referenced, not a dependency.

Forward references: RFC-0013 (Audit records what entered Context); RFC-0014
(what Memory survives a resume); RFC-0015 (presentation of evidence and
Context); RFC-0017 (compatibility of what is retained); RFC-0020 (storage
mechanics and freshness bounds).

---

## 37. Open Questions

Each names its owner. None blocks the Context model's core guarantees.

1. **Concrete size bounds and consolidation thresholds** — RFC-0020, RFC-0015.
2. **Per-category freshness bounds** behind RFC-0005 §12 — RFC-0020.
3. **Sanitization catalogue** at the enforcement point (RFC-0007 §16 OQ1
   mechanics) — RFC-0020.
4. **Routing-state persistence across interrupts** — whether the
   outstanding-question marker survives and how it is re-posed — RFC-0014.
5. **Multi-goal Context separation** (RFC-0002 Q10) — RFC-0014.

---

## 38. Risks

| Risk | Mitigation |
|---|---|
| **Context misread as truth** | Fact Layer owns truth; labeled material with provenance (CM1; RFC-0004 §4.6) |
| **Memory accumulating silently** | Consent-gated promotion only; retention by consent (CM11; RFC-0001 §9.5) |
| **Stale Context driving a decision** | Freshness inherited from Facts; stale is rebuilt (CM7; RFC-0005 §12) |
| **Cross-session leakage** | One working set per session; cross-session only by consent (CM9; §14) |
| **Unbounded Context growth** | Size bounds and transparent consolidation (CM6; RFC-0001 §9.3) |
| **Secret reaching Context or the View** | Secret-free construction at the enforcement point (CM4; RFC-0009 SC2) |
| **Context widening a grant** | Context and Memory carry no permissions (CM16; RFC-0004 A8) |
| **Future extension injecting unlabeled material into the View** | Any new source re-checks RFC-0007 §12; new categories are amendments (CM3; §34) |
| **Corrupted Context corrupting execution** | Context degrades reasoning only; Verification re-establishes ground truth (CM13; RFC-0004 §9.11) |

---

## 39. Vocabulary Additions for RFC-0003

The following terms are defined in this RFC and must be added to RFC-0003 Part
I by additive amendment: **Context Category**, **Memory Category**,
**Context Assembly**, **Routing State**, **Consolidation** — defined at first
use in §6, §7, §10, §12, and §23. Context, Memory, Provider View, Fact, Goal,
History, Evidence, Outcome, Skill, Secret, and Audit already exist in RFC-0003
Part I and are used here with their canonical meanings.

---

*End of RFC-0012. Normative: sections 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28, 29, 30, 31,
32, 33, 34, 35. Explanatory and load-bearing: sections 0, 36, 37, 38, 39. Any
change to a Context or Memory category, ownership, authority, transition,
boundary, invalidation rule, retention rule, or an invariant CM1–CM16 is a
BREAKING change and must be made by amendment (RFC-0003 Part II).*
