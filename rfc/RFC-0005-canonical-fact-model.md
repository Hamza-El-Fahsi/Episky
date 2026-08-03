# RFC-0005 — Canonical Fact Model

**Status:** Draft
**Date:** 2026-08-02
**Scope:** The single canonical representation of machine knowledge inside the
Assistant: what a Fact is, how Observations become Facts, Fact status,
provenance, identity, lifetime, relationships, Evidence Sets, categories,
machine identity, freshness, and the Fact invariants
**Audience:** Future maintainers
**Supersedes:** Nothing
**Depends on:** RFC-0001 (accepted), RFC-0002 (accepted), RFC-0003 (accepted),
RFC-0004 (accepted). RFC-0021 is referenced for the machine's subsystem and
State-Domain vocabulary but is itself a Draft and is not a dependency.

**Roadmap note:** This is RFC-0000's "RFC-0005 — Fact Model & Diagnostics
Architecture" (Domain, Required), the spine of every runtime consumer — the
fact model is the domain foundation everything else consumes (RFC-0000 §5,
§6). It answers the coverage rows RFC-0000 §8 assigns to it: RFC-0001 Q6 (fact
normalization across distros), Q8 (diagnostic output bounds), Q9 (fact
staleness), Q24 (concurrent diagnostics); RFC-0002 Q5 (idle/awaiting drift,
with RFC-0014), Q15 (concurrent collection), Q17 (watchdog scope).

**BREAKING:** No. This RFC specifies the fact model that RFC-0001, RFC-0002,
RFC-0003, RFC-0004, RFC-0007, and RFC-0008 already assume — a Fact is
"normalized, deterministic, provenance-carrying, staleness-bounded, never
LLM-authored" (RFC-0003 §2.4). It does not weaken any Principle, Boundary,
Invariant, or canonical Definition in an accepted RFC; it makes the canonical
definition concrete.

---

## 0. Purpose

This RFC answers one question:

> **After Diagnostics inspects the machine, what exactly exists inside the
> Assistant?**

The answer is: **Facts**. A Fact is the only unit of machine knowledge the
Assistant treats as "known." Everything else the system sees — raw output, a
command's text, a provider's sentence — is not knowledge; it is material from
which knowledge is produced.

**Raw command output must never become internal state.** Raw output is
distro-specific text emitted by a tool the Assistant does not control. If raw
output became state, then:

- the Assistant's beliefs would be written in the distro's dialect, not in the
  project's canonical vocabulary, so every consumer would re-parse the machine
  in its own way (RFC-0001 Q6);
- the Assistant's beliefs would inherit the output's untrustworthiness —
  output is untrusted until normalized (RFC-0004 §4.5; RFC-0007 T5), so state
  built directly from it would be state built from untrusted text (RFC-0002
  invariant 5);
- nothing would bound how much raw text enters reasoning, and unbounded,
  unnormalized text reaching the model violates the provider-view boundary
  (RFC-0002 invariant 4; RFC-0001 §9);
- the Assistant could never compare "before" and "after," because each
  re-collection would produce a differently-worded blob instead of the same
  canonical claim (RFC-0002 invariant 2).

So the boundary is absolute: **raw output enters the Assistant only as input
to normalization, and the only thing that crosses that boundary is a Fact.**
The internal language of the Assistant is Facts; everything else — a command,
a parser, a Collector, an LLM's proposal — is merely a way to produce Facts.

This RFC is **not** about: command execution (RFC-0001, RFC-0002, RFC-0008);
providers or prompts (RFC-0010); context persistence (RFC-0012); approval
(RFC-0008); verification logic (RFC-0006); or implementation. Those belong to
their owning RFCs; this RFC is architecture only and defers rather than
partially specifies (RFC-0003 Part II §1).

---

## 1. Design Principles

Facts are governed by ten principles. Each is load-bearing; §13's invariants
are their enforceable form.

| Principle | Meaning |
|---|---|
| **Facts are deterministic** | Same machine, same Collector, same inputs → same Fact. A Fact is a pure function of its inputs (RFC-0001 §3.5). No randomness, no model, no opinion. |
| **Facts are provider-independent** | No Fact is defined by, or varies with, which LLM/provider is attached. Providers consume Facts; they never produce them (RFC-0004 A1). |
| **Facts are distro-independent** | A Fact is expressed in the project's canonical vocabulary, never in a distro's dialect. Normalization absorbs distro variance (RFC-0021 §2.3; RFC-0001 Q6). |
| **Facts are immutable observations** | A Fact, once recorded, is not edited. A change in reality produces a new Fact that supersedes the old one (§6, §7). |
| **Facts never contain authority** | A Fact asserts what is; it grants nothing. Authority is RFC-0004's subject; a Fact carries no permission, no role, no grant (RFC-0004 §2). |
| **Facts are versioned** | Every Fact is expressed against a version of the fact model and, where applicable, the Collector and Family Profile that produced it, so consumers can tell which model a claim was made in. |
| **Facts always carry provenance** | Every Fact can answer where it came from, who collected it, when, and how (§5). An unprovenanced claim is not a Fact (RFC-0007 §9). |
| **Unknown is different from False** | "Not known" is a status, not a value. Absence of evidence is not evidence of absence (RFC-0001 §10.2). |
| **Missing is different from Unsupported** | The Collector did not run (Missing) is not the capability does not exist (Unsupported). They are distinct statuses with distinct consequences (§4). |
| **Stale is different from Current** | A Fact past its freshness bound is stale regardless of what it once said. Freshness is a property of time, not of truth (RFC-0002 invariant 10). |

---

## 2. Observation → Fact Pipeline

The pipeline is normative. Every stage has a defined input, a defined
transformation, and a defined output; nothing skips a stage, and no stage's
output is treated as knowledge before the next stage has run.

```
Raw Output → Observation → Normalization → Canonical Fact → Evidence Set → Context
```

| Stage | Input | Transformation | Output |
|---|---|---|---|
| **Raw Output** | What the Collector's deterministic inspection actually emitted (text, exit status, timing) | Nothing yet — this is the tool's utterance, still distro-specific and untrusted | The raw bytes the Collector returned |
| **Observation** | Raw Output plus the Collector's identity and run metadata | Record the output together with which Collector ran, when, and the exit status (RFC-0003 §2.4) | A timestamped, provenance-carrying record of one Collector run |
| **Normalization** | An Observation, a Canonical Definition, and the Family Profile (RFC-0021 §2.3) | Deterministically parse the Observation into a canonical claim using the Canonical Definition; reject, mark Unknown, or truncate-with-marker when it cannot be parsed | A **Canonical Fact** (§3) |
| **Canonical Fact** | The normalized claim | Attach status, provenance, freshness, machine identity, and scope (§3–§5, §11–§12) | The complete Fact, ready to be carried |
| **Evidence Set** | One or more Facts produced by this and related Observations | Group related Facts with their relationships (§8) so a diagnosis can cite a coherent body of evidence (§9) | An Evidence Set — the unit in which Facts travel |
| **Context** | Selected Evidence Sets, bounded by purpose, size, and secrecy rules | Sanitize, bound, and assemble what reasoning may see (RFC-0002 §2.4; RFC-0003 §2.8) | The Provider View or reasoning context |

Normative rules of the pipeline:

- **Observations are not Facts.** An Observation is the record of one Collector
  run; it becomes a Fact only by normalization (RFC-0004 §4.5; RFC-0007 T6).
- **Normalization is the only gate between machine and knowledge.** Raw output
  and Observations are untrusted; the Fact is the first trusted form
  (RFC-0007 §7). Normalization is the trust-upgrade step and the only one —
  it never runs on LLM output and never consults the model (RFC-0001 §3.5;
  RFC-0002 §6.2).
- **Normalization is deterministic and per-Observation.** Each Observation is
  normalized independently of the others, so concurrent collection cannot
  change any resulting Fact (RFC-0002 Q15; RFC-0001 Q24). Re-normalizing the
  same Observation always yields the same Fact.
- **Normalization is lossy by design.** Distro-specific wording, headers, and
  formatting are discarded; only the canonical claim survives. Loss is the
  point: it is how distros stop leaking into internal state (RFC-0001 Q6).
- **Output is bounded before it is used.** Every Collector's output has a
  size bound. Output beyond the bound is truncated and the Observation records
  the truncation; it is never silently dropped, and it never enters Context
  unmarked (RFC-0001 Q8). Redaction of secrets inside output is RFC-0009's
  concern, applied at the Observation boundary before normalization.
- **What cannot be normalized is a Fact about not knowing.** A Collector that
  fails, times out, or produces unparseable output does not disappear; it
  produces an **Unknown** Fact (§4), never a guessed value and never nothing
  (RFC-0001 §10.3; RFC-0002 §4.2).
- **No stage reads LLM output.** Providers propose and explain; they never
  supply a stage of this pipeline (RFC-0004 A1; RFC-0002 §6.2).

---

## 3. Canonical Fact

A Fact is the project's canonical claim about the Machine: a normalized,
deterministic statement, expressed in the canonical vocabulary, carrying
provenance, status, freshness, and machine identity (§1, §0). Conceptually,
every Fact has the following components. **No schemas and no data formats are
specified here** — these are concepts every Fact must be able to express, in
whatever form implementation chooses (RFC-0003 Part II §1).

| Concept | What it means |
|---|---|
| **Identifier** | A stable reference to this Fact across its lifetime, so the same claim can be recognized when re-collected and so relationships can name it (§6, §8). |
| **Subject** | What the Fact is about — a machine, a subsystem, a State Domain, a device, a package, a service (RFC-0021 §4, §6). |
| **Property** | The attribute of the Subject being asserted — e.g., installed-version, running-state, mount-point. Together Subject + Property name the claim; Value and Status say what is claimed. |
| **Value** | The asserted content of the Property, in canonical, distro-independent terms. |
| **Status** | Where the claim sits in the status lattice (§4). |
| **Confidence Source** | *Why* the value is believed — a named deterministic check, a re-observation, a Collector — **never a percentage and never an LLM estimate**. A Fact's grounds, not a score. |
| **Timestamp** | When the underlying Observation was collected. |
| **Collector** | Which deterministic inspection produced the Observation that this Fact was normalized from (§5). |
| **Provenance** | The chain that answers "where did this come from, and can it be reproduced?" (§5). |
| **Freshness** | The staleness bound and the current freshness state of the claim (§12). |
| **Machine Identity** | The identity of the machine the Fact describes, so a Fact is never attributed to the wrong machine (§11). |
| **Scope** | What the Fact does and does not assert — the boundaries of the claim, so a Fact about one package never reads as a Fact about all packages. |

Rules over the components:

- **Value and Status are distinct.** "The service is *stopped*" (a Value) is not
  "the service's state is *unknown*" (a Status). Never conflate what is claimed
  with how confidently it is known (§4).
- **Status is not a Value.** A Fact is about the machine, not about the
  pipeline: "not yet collected" describes knowledge, not the machine.
- **Confidence is a source, never a number.** Where a check produced an
  unambiguous result, the confidence source names the check. Where it did not,
  the Fact is Unknown — it is never a 70% claim.
- **Scope is explicit.** A Fact asserts exactly its Subject, Property, and
  Value; everything else is out of scope and must not be inferred from it.
- **Every component is about the machine or about evidence of it.** None
  contains authority (§1), none executes anything (§13 F3), and none is written
  by the model (§13 F1).

---

## 4. Fact Status

Every Fact carries exactly one status. Status is decided by the Fact Layer from
evidence, never by rhetoric, and it is part of the Fact (§3). The statuses:

| Status | Meaning | How it is reached | What it permits |
|---|---|---|---|
| **Observed** | The claim was normalized from a successful Observation and is believed current | Normalization produced a value from a current, successful Collector run | Use as a current fact; re-observation or time will move it |
| **Verified** | The claim was independently re-confirmed after the event it describes — the strongest status | State-based re-observation and comparison (RFC-0002 invariant 2; RFC-0006) | Use as settled evidence; the target of Verification |
| **Unknown** | The claim could not be established: the Collector failed, timed out, or produced unparseable output | A failed or inconclusive Observation (§2); never a guessed value | Do not assume it is False; treat as "not known" (RFC-0001 §10.2) |
| **Unavailable** | The check could not run at all — permission, tool absent, watchdog active | The Collector could not be invoked on this machine | Distinguish from "the value is X"; it may be retried later |
| **Unsupported** | The machine does not have the capability the check would describe | Normalization matched a "not present" or "not supported" family/ecosystem case (RFC-0021 §2.4, §5) | Distinguish from Missing: the capability genuinely does not exist here |
| **Contradicted** | Fresh evidence says something else; the old claim is invalidated and the fresh evidence wins | A newer, fresher Fact conflicts with this one (§6, RFC-0002 invariant 10) | Never use as truth; surface the contradiction and re-evaluate (§6) |
| **Stale** | The Fact is past its freshness bound and may no longer describe the machine | Time or a detected state change expired it (§12; RFC-0002 §4.2) | Re-collect before use; stale truth is old text (RFC-0007 §9) |
| **Invalid** | The Fact fails its own requirements — provenance lost, identity mismatch, status uncomputable | A canonical-rule violation (§13 F10, F12, F16) | Treat as if it never existed; disclose why |

Status transitions are one-way toward less certainty except through fresh
evidence: Observed → Verified by verification; Observed → Contradicted or Stale
by newer evidence or time; any → Invalid by rule failure. **Unknown, Missing,
and Unsupported are three different things** (RFC-0001 §5): *Unknown* means the
check did not establish the value; *Missing* (recorded as Unavailable) means
the check did not run; *Unsupported* means the machine lacks the capability.
They are never collapsed into one (§13 F11).

---

## 5. Provenance

Every Fact must be able to answer five questions. Provenance is not optional
metadata; it is what makes a claim a Fact rather than an assertion (RFC-0007
§9.6), and its loss is itself a reason to distrust (RFC-0007 §9).

| Question | What the answer must contain |
|---|---|
| **Where did this come from?** | The Observation the Fact was normalized from, and the Raw Output that Observation recorded (§2). |
| **Who collected it?** | The exact Collector identity — a name and version — that ran the inspection. |
| **When?** | The collection timestamp and, if re-collected, every re-collection timestamp. |
| **Using what deterministic inspection?** | Enough about the Collector's procedure (inputs, canonical definition used, Family Profile) that the run is reproducible. |
| **Can it be reproduced?** | Yes, by re-running the same Collector under the same conditions; the Fact records what reproduction requires. |

Normative rules:

- **Provenance is attached at normalization, never added later.** A Fact that
  lost its provenance is downgraded or invalidated, not "re-attributed"
  (RFC-0007 §9.6; §13 F10).
- **Provenance names the deterministic check, not the model.** The "who" is
  always a Collector; it is never an LLM, a Skill's prose, or the Operator
  (RFC-0004 A1; §13 F1).
- **Provenance supports reproduction.** Any consumer must be able to re-run the
  named Collector and get the same Observation family back.
- **Provenance survives demotion.** When a Fact is downgraded — stale,
  contradicted, invalid — the reason and the original provenance stay attached,
  so the Audit can show why (RFC-0002 invariant 13; RFC-0007 §9).

---

## 6. Fact Identity

Identity answers when two Facts are the same claim. It is defined
conceptually, on the components of §3, without reference to any format.

**When are two Facts identical?** Two Facts are the same claim — the same
**Fact Identity** — when they have the same Machine Identity, the same Subject,
and the same Property (§11, §3). Value, Status, Timestamp, and Freshness may
differ; identity is what lets re-collection recognize the same claim.

**When do they supersede one another?** A newer Fact supersedes an older one
when it has the same Fact Identity, is fresher, and its evidence is at least as
strong. The newer Fact replaces the older in the current set, and the older is
retired with the newer recorded as its successor (§7, §8). Fresh evidence wins
(RFC-0002 invariant 10).

**When are they contradictory?** Two Facts are contradictory when they have
the same Machine Identity, Subject, and Property, are both believed current,
and their Values are mutually exclusive. Contradiction is a state to surface,
not to resolve silently: the runtime stops the current path and re-evaluates
(RFC-0001 §10.4). One of them wins by freshness and evidence (§4
Contradicted).

**When are they independent?** Two Facts are independent when they make
different claims — a different Subject, a different Property, or a different
Machine Identity. Independent Facts neither confirm nor contradict one another;
both may stand, and both are needed for a complete Evidence Set (§9).

**Identity is not sameness of wording.** Two normalized Facts that differ only
in distro dialect are the same claim; two that look alike but differ in
Subject or Machine Identity are not. Identity is decided on the canonical
components, never on raw text (RFC-0007 T2).

---

## 7. Fact Lifetime

A Fact's lifetime is a sequence of states driven by evidence and time. **This
section is about the Fact's lifecycle, not about persistence** — where and how
Facts are stored belongs to RFC-0012 (Context/Memory) and RFC-0013 (Audit);
this RFC fixes only what each lifecycle step *means*.

| Step | Meaning | What it does to identity |
|---|---|---|
| **Creation** | Normalization produces a new Fact from an Observation (§2). A new Fact Identity is created for a new claim, or a fresh instance for an existing one. | Assigns Identifier, Machine Identity, provenance, status (usually Observed) |
| **Update** | Re-collection establishes a new Value or Status for an existing claim. | The claim is **not edited**; a new Fact with the same identity supersedes the old (§6), and the old is retired |
| **Replacement** | A newer Fact supersedes an older one of the same identity (§6). | The successor relationship is recorded (§8); the old Fact is retired |
| **Expiration** | The Fact passes its freshness bound or a state change invalidates it (§12; RFC-0002 §4.2). | The Fact becomes Stale; it is re-collected before further use |
| **Retirement** | A Fact is superseded or contradicted and is no longer part of the current set. | It is marked retired with its successor or contradiction recorded; it does not vanish — it remains in the record with its provenance (§5) |
| **Deletion** | The Fact is removed from the current set entirely, by rule (e.g., Invalid) or by explicit Operator request. | The current set forgets it; the Audit still holds the record (RFC-0002 invariant 13; RFC-0013) |

Normative rules:

- **Facts are never edited.** An "update" is always a new Fact superseding an
  old one. Immutability is what makes verification and audit honest (§13 F8).
- **Nothing is silently dropped.** A Fact that stops being current goes through
  Retirement or Deletion with the reason recorded — expiration, contradiction,
  invalidation, or request. Silence is not a lifecycle step (RFC-0002
  invariant 13).
- **The current set is a snapshot.** Machine State is "the current set of
  verified Facts together with the known unknowns" at a moment (RFC-0003 §2.1);
  lifetime steps are what keep that snapshot honest across time (§12).

---

## 8. Fact Relationships

Facts do not stand alone in meaning; relationships say how one claim relates to
another. Relationships are recorded so an Evidence Set can carry a structure,
not just a pile of claims (§9).

| Relationship | Direction | Meaning |
|---|---|---|
| **Parent / Child** | parent → child | The Child is a claim within the scope of the Parent (e.g., a machine's Subsystem is the parent of that subsystem's Facts; a package's Fact is a child of the Packages subsystem). |
| **Depends-on** | fact A → fact B | A's meaning or correctness rests on B: if B changes, A must be re-checked (e.g., a service's running-state depends on its package's installed-state). |
| **Derived-from** | fact A → observation or fact B | A was produced from B — a normalized Fact derived from its Observation, or a Fact derived from other Facts. The derivation chain is part of provenance (§5). |
| **Conflicts-with** | fact A ↔ fact B | A and B are contradictory (§6): same identity, both current, mutually exclusive values. |
| **Supersedes** | fact A → fact B | A is a newer instance of the same identity that replaced B (§6, §7). |
| **Equivalent** | fact A ↔ fact B | A and B assert the same claim in different words or via different Collectors (e.g., package version via two package tools). Equivalent Facts corroborate; they are still one claim for reasoning. |

Normative rules:

- **Relationships name Facts, not text.** A relationship points at a Fact
  Identity (§6), so it survives re-collection and supersession.
- **Depends-on drives invalidation.** When a depended-on Fact is invalidated or
  changed, the dependent Facts are re-checked before use — the engine never
  reasons over a Fact whose dependency went stale (RFC-0002 invariant 10;
  §12).
- **Derived-from is a provenance chain.** Derived Facts are only as strong as
  their base Facts; the chain is part of what a consumer can inspect (§5).
- **Conflicts-with must be recorded, never hidden.** A contradictory pair
  stays visible in the record even after one wins, so the resolution is
  auditable (RFC-0001 §10.4).

---

## 9. Evidence Sets

**Facts never travel alone.** A Fact leaves the Fact Layer only inside an
**Evidence Set** — a purpose-limited collection of related Facts, carrying
their relationships (§8), that supports a specific diagnosis or decision.

**Why Evidence Sets exist.** Three reasons:

- **A single Fact is usually not enough to decide.** A diagnosis rests on
  several claims — the symptom, the package state, the service state — and
  reasoning needs them together, with their relationships visible (§8).
- **Context must be bounded and coherent.** The Provider View is assembled from
  Evidence Sets, not from an unbounded fact dump (RFC-0002 §2.4; RFC-0001 §9);
  an Evidence Set is the unit that is purpose-limited and size-bounded before
  it enters Context (§2).
- **Every claim travels with its support.** Because Facts come in sets with
  relationships, a consumer can ask "what is this claim supported by?" and
  "what does this claim depend on?" instead of trusting a bare assertion.

**How incomplete evidence is represented.** An Evidence Set explicitly marks
what it does not contain. Missing observations are carried as **Unknown** or
**Unavailable** Facts (§4), never as absences, so the set records its own gaps:
a diagnosis that cannot test a hypothesis carries an Unknown Fact saying so,
and reasoning must treat the gap as a first-class part of the evidence (§13
F11). An Evidence Set may also be labeled **incomplete** when its intended
collectors have not all run; that label is part of the set, not a secret.

**How conflicting evidence is represented.** A set that contains contradictory
Facts keeps both, records the **Conflicts-with** relationship (§8), and marks
the set as **conflicted**; it does not delete the loser. The runtime surfaces
the contradiction and re-evaluates (RFC-0001 §10.4). A conflicted Evidence Set
is not a settled diagnosis; it is an open question with its options recorded.

**The Evidence Set is a carrier, not a verdict.** It asserts nothing by
itself; it carries Facts and their statuses. Interpretation — turning evidence
into a Hypothesis or Diagnosis — is Diagnosis, which is the LLM's and Skill's
work and is never itself a Fact (RFC-0003 §2.5).

---

## 10. Fact Categories

Facts are grouped into conceptual categories so that staleness, scope, and
presentation can be treated uniformly per domain (RFC-0021 §4, §6). These are
concepts, not implementations; the categories map to RFC-0021's subsystems and
State Domains.

| Category | What its Facts describe | Related to (RFC-0021) |
|---|---|---|
| **Hardware** | Devices, firmware, identity of physical components | RFC-0021 §4.2; Facts only |
| **Kernel** | Running kernel, modules, runtime parameters | RFC-0021 §4.4; Configuration State RFC-0021 §6.4 + Facts |
| **Packages** | Installed packages, versions, ecosystem, origins | RFC-0021 §4.9; Package State RFC-0021 §6.2 |
| **Filesystem** | Mounts, partitions, layout, usage | RFC-0021 §4.8; Filesystem State RFC-0021 §6.5 |
| **Services** | Service units, running-state, enabled-state | RFC-0021 §4.6; Service State RFC-0021 §6.3 |
| **Networking** | Interfaces, addresses, routes, links | RFC-0021 §4.10; Network State RFC-0021 §6.6 |
| **Storage** | Disks, volumes, logical volumes | RFC-0021 §4.7; Storage |
| **Boot** | Boot configuration, boot entries, kernel command line, boot outcome | RFC-0021 §4.3; Configuration State RFC-0021 §6.4 + Facts |
| **Logs** | Log sources, log content relevant to the Goal, journal state | RFC-0021 §4.12; Facts |
| **Security** | Accounts, credentials state, firewall, security-relevant state | RFC-0021 §4.11; Security State RFC-0021 §6.8 |
| **Configuration** | The machine's configurable settings and their current values | Configuration State RFC-0021 §6.4 |
| **Applications** | User-facing applications, versions, presence | RFC-0021 §4.13; Facts |

Normative rules:

- **A Fact belongs to exactly one category.** The category is part of the
  Fact's Scope (§3); it decides which freshness bound and which presentation
  rules apply (§12).
- **A category is not a claim.** Categories organize Facts; they never assert
  anything about the machine themselves.
- **Category membership follows RFC-0021.** Where RFC-0021 maps a subsystem to
  a State Domain or to Facts-only (RFC-0021 §6.10), Facts follow that mapping;
  this RFC
  adds no new domain of knowledge.

---

## 11. Machine Identity

Facts describe one specific machine, and they must stay attached to it.

**How Facts remain tied to one machine.** Every Fact carries the Machine
Identity of the machine its Observation was collected on (§3, §5). Machine
Identity is the verifiable set of Facts that identify one specific Machine
across time (RFC-0003 §2.1); its precise contents are RFC-0014's, but its role
here is fixed: **a Fact is only valid for the Machine Identity it names.** An
Evidence Set is assembled only from Facts of one Machine Identity, and a
reasoning context may never mix machines.

**What happens if machine identity changes.** A change in Machine Identity means
the Facts no longer describe the same machine, so:

- all cached Facts of the old identity are **invalidated** — they describe a
  machine that is no longer the one being reasoned about (RFC-0003 §2.1;
  RFC-0002 invariant 15);
- the runtime must **re-collect** under the new identity before any reasoning
  or action based on Facts proceeds;
- any approval scoped against the old Machine State is invalidated (RFC-0002
  invariant 11; RFC-0008), and session resume under a changed identity is
  RFC-0014's recovery path.

Identity is decided from Facts, and it can itself be unknown. When the
machine's identity cannot be established (a critical collector failure), the
runtime discloses and asks the Operator how to proceed rather than guessing
(RFC-0002 §2.3). Facts are never mixed across identities, even if the values
look the same (§6).

---

## 12. Freshness

Freshness answers how current a Fact is. It is a property of time and state,
not of truth: a Fact that was correct is still stale once it is old (RFC-0002
invariant 10).

A Fact carries a **freshness bound** for its category (§10) and a **freshness
state**:

| State | Meaning | Use |
|---|---|---|
| **Current** | Within its freshness bound, and no state change invalidated it | Believed; used without re-collection |
| **Possibly stale** | Near the bound, or a detected state change affects a depended-on Fact | Usable only with caution; re-check on next decision that depends on it (§8) |
| **Stale** | Past its freshness bound | Must be re-collected before any use as current evidence |
| **Expired** | The bound has passed and the claim is no longer part of the current set | Treated as retired (§7); only the record remains |
| **Unknown freshness** | The bound cannot be computed — provenance or timing is missing | Treated as stale or invalid, never as current (§13 F15) |

**When re-inspection becomes mandatory.** Re-collection is mandatory:

- before any Fact past its freshness bound is used as current evidence (Stale,
  Expired, or Unknown freshness) — stale truth is not truth (RFC-0007 §9);
- whenever a detected state change invalidates the Fact or a Fact it
  depends-on (§8; RFC-0002 §4.2);
- after any interruption, reboot, or machine-identity change (§11; RFC-0002
  invariant 8);
- on a fresh Goal, whose baseline inspection re-establishes the current set
  (RFC-0002 §2.3).

The **watchdog** is the minimal read-only watch set that detects externally
observed state changes so Facts can be invalidated between decisions (RFC-0002
Q17). Its scope is a small set of State-Domain probes (RFC-0021 §6), chosen to
avoid false "state changed" triggers; when it fires, dependent Facts are
invalidated and re-collected, and an outstanding approval is invalidated
(RFC-0002 §4.2; RFC-0008). The freshness bound per category is policy content
(RFC-0020), set conservatively by default and adjustable only within the
Operator's authority (RFC-0004 §3).

---

## 13. Canonical Rules (Normative)

These invariants make the fact model structural. They join RFC-0002 §9 and
RFC-0004 §8: no implementation may violate them and no later RFC may weaken
them except by amendment (RFC-0003 Part II §1).

- **F1 — A Fact never originates from an LLM.** No Fact is authored, edited,
  or inferred by a model; the model proposes, and proposals are not Facts
  (RFC-0001 §3.5; RFC-0004 A1). *Test: no model output ever becomes a Fact
  without normalization from an Observation.*
- **F2 — Facts never contain permissions.** A Fact asserts what is; it grants
  nothing — no authority, no role, no capability (RFC-0004 §2). *Test: no Fact
  can name or confer a permission.*
- **F3 — Facts never execute.** A Fact is data; it runs nothing and causes no
  mutation (RFC-0002 invariant 5; RFC-0007 T1). *Test: no Fact is ever
  interpolated into a command.*
- **F4 — Facts never imply actions.** A Fact asserts a state; it recommends
  nothing. Deciding what to do is Diagnosis and Planning (RFC-0002 §6.2).
  *Test: a consumer cannot read an action out of a Fact.*
- **F5 — Facts are deterministic.** Same machine, same Collector, same inputs →
  same Fact; normalization is a pure function (RFC-0001 §3.5). *Test:
  re-normalizing an Observation reproduces the Fact.*
- **F6 — Facts are provider-independent.** No Fact varies with the provider or
  model in use; providers consume, never produce (RFC-0004 A1). *Test:
  swapping providers never changes a Fact.*
- **F7 — Facts are distro-independent.** Facts are expressed in canonical
  vocabulary, never a distro dialect (RFC-0021 §2.3; RFC-0001 Q6). *Test: the
  same claim from different distros produces the same Fact.*
- **F8 — Facts are immutable observations.** A Fact is never edited; change is
  a new Fact superseding the old (§7). *Test: no Fact's recorded content
  changes after creation.*
- **F9 — Facts are versioned.** Every Fact is expressed against a version of
  the model and the Collector/Family Profile that produced it (§1). *Test:
  every Fact names the model version it conforms to.*
- **F10 — Facts always carry provenance.** A Fact can answer where, who, when,
  how, and reproducible (§5); an unprovenanced claim is not a Fact (RFC-0007
  §9). *Test: a Fact with lost provenance is invalidated, not re-attributed.*
- **F11 — Unknown is not False, Missing is not Unsupported, Stale is not
  Current.** The three distinctions are structural (§4); collapsing them is a
  violation (RFC-0001 §10.2). *Test: each status is preserved and never
  silently converted.*
- **F12 — Facts are bound to one Machine Identity.** A Fact is valid only for
  the machine it names; Evidence Sets never mix identities (§11). *Test: a
  Fact of identity X is never used as evidence for machine Y.*
- **F13 — A Fact asserts exactly its scope.** A Fact claims its Subject,
  Property, and Value; nothing more may be inferred (§3). *Test: a Fact about
  one package never reads as a claim about all packages.*
- **F14 — Facts expire.** Nothing uses a Fact past its freshness bound without
  re-collection (RFC-0002 invariant 10). *Test: a stale Fact is not used as
  current evidence.*
- **F15 — Unknown freshness is not current.** A Fact whose freshness cannot be
  computed is treated as stale or invalid, never as current (§12). *Test: an
  un-freshnessable Fact is never believed.*
- **F16 — Facts fail closed on rule failure.** A Fact that violates any of
  F1–F15 is Invalid and disclosed (§4); the system never proceeds on a claim
  whose status cannot be established (RFC-0007 T11). *Test: a rule-violating
  Fact is blocked and surfaced.*

---

## 14. Interaction with other RFCs

This RFC makes no claims owned by other documents; it specifies the fact model
they consume. Only references follow; no duplication (RFC-0003 Part II §1).

| RFC | Relationship | What RFC-0005 says here |
|---|---|---|
| **RFC-0001** | Architecture and principles | Operationalizes §3.5 (deterministic information), §5.4 (Diagnostics & Fact Layer), §9 (Context from Facts), §10 (unknown ≠ false, stop on contradiction). Answers Q6, Q8, Q9, Q24. |
| **RFC-0002** | Runtime states and invariants | Gives the Fact model behind Machine Inspection (§2.3) and Context Building (§2.4); supports invariants 2, 4, 5, 8, 10, 13, 15. Answers Q5 (with RFC-0014), Q15, Q17. |
| **RFC-0003** | Vocabulary and governance | Uses Fact, Observation, Collector, Inspection, Evidence, Machine Identity, Machine State, Context canonically; §17 flags new terms for Part I. |
| **RFC-0004** | Authority model | Implements the Fact Layer's truth role (§4.6) and the Diagnostics Layer's collection role (§4.5); supports A1 (providers never produce Facts) and A4 (diagnostics never mutate). |
| **RFC-0007** | Trust and sanitization | Implements the trust-upgrade path (Observation→Fact, T6) and the demotion triggers (staleness, contradiction, state change, provenance loss, §9); Facts are the first trusted form. |
| **RFC-0008** | Approval and policy | Supplies the Facts that classification (§6) and preconditions (§9) consume; freshness and invalidation support token re-validation (P9, P14). RFC-0008 does not define Facts; it consumes them. |
| **RFC-0021** | System model and platforms | Uses its subsystems (§4) and State Domains (§6) as the vocabulary of Subject and Category (§10); uses the Family Profile (§2.3) in normalization. Referenced, not a dependency. |

Forward references (planned RFCs this model constrains): RFC-0006 (Verification
compares Facts); RFC-0009 (secrets never enter Facts/Context); RFC-0012
(Context/Memory hold Facts); RFC-0013 (Audit records Fact lifecycle); RFC-0014
(Machine Identity contents, resume); RFC-0015 (Fact presentation); RFC-0017
(fact-model compatibility); RFC-0020 (freshness bounds as policy).

---

## 15. Open Questions

Questions this RFC deliberately leaves open; each names its owner. None blocks
the fact model's core guarantees.

1. **Machine Identity contents.** Which Facts identify a machine, and how a
   changed identity is distinguished from a changed machine — owned by RFC-0014
   (RFC-0003 §2.1 already defers to it).
2. **Fact persistence mechanics.** Where the current set, retired Facts, and
   lifecycle records are stored, and how long they are kept — owned by
   RFC-0012 (Context/Memory) and RFC-0013 (Audit).
3. **Verification comparison.** How before/after Fact sets are compared to
   decide "verified" — owned by RFC-0006 (RFC-0002 invariant 2 is the
   requirement; RFC-0006 is the semantics).
4. **Secret detection in raw output.** How secrets inside Raw Output are
   detected and redacted at the Observation boundary — owned by RFC-0009.
5. **Fact presentation.** How Facts, statuses, and freshness are shown to the
   Operator — owned by RFC-0015.
6. **Freshness-bound values.** The concrete staleness window per category —
   owned by RFC-0020 as policy content (this RFC fixes the mechanism, §12).
7. **Fact-model compatibility.** How the fact model versions and migrates
   across releases — owned by RFC-0017.

---

## 16. Risks

The ways the fact model could fail, and the structural mitigation already in
this RFC.

| Risk | Why it could fail | Structural mitigation |
|---|---|---|
| **Fact explosion** | Every observation, every re-check, every status becomes Facts, and the set grows without bound | Evidence Sets are purpose-limited and size-bounded before Context (§9); lifecycle steps retire and delete (§7); normalization is lossy by design (§2) |
| **Conflicting facts** | Two current Facts disagree and reasoning quietly picks one | Conflicts-with is recorded, sets are marked conflicted, the runtime stops and re-evaluates (§6, §8, §9; RFC-0001 §10.4) |
| **Staleness** | Old Facts are used as current truth | Freshness bound and state are mandatory (§12); watchdog invalidates on state change (§12; RFC-0002 §4.2); F14 |
| **Normalization bugs** | A parser misreads distro output and produces a wrong canonical value | Normalization is deterministic and per-Observation, with Unknown on failure (§2); F5; normalization is testable against the Family Profile (RFC-0021 §2.3) |
| **Provider leakage** | LLM output is mistaken for a Fact, or raw output reaches the model | F1; the pipeline never reads model output (§2); provider-view boundary (RFC-0002 invariant 4); RFC-0007 T3, T4 |
| **Hidden assumptions** | The model (or a consumer) infers what the Facts do not say | Scope is explicit and invariant (F13); unknown/missing/unsupported stay distinct (F11); Facts never imply actions (F4) |
| **Identity mismatch** | Facts from one machine are used for another | Machine Identity is mandatory and never mixed (§11; F12); identity change invalidates all cached Facts |
| **Provenance loss** | The chain that makes a Fact believable is dropped | Provenance is attached at normalization and never re-added later (§5; F10); loss downgrades or invalidates (RFC-0007 §9) |

---

## 17. Vocabulary Additions for RFC-0003 (flagged for inclusion in Part I)

The following terms are defined in this RFC and must be added to RFC-0003 by
additive amendment: **Canonical Fact** (or use of the existing **Fact**
definition, made concrete by this RFC), **Fact Status**, **Fact Identity**,
**Evidence Set**, **Fact Freshness** (bound and state), **Confidence Source**,
**Fact Category**. The definitions appear at first use in §3, §4, §6, §9, §12,
and §10. Observation, Collector, Inspection, Evidence, Machine Identity,
Machine State, Context, and Provider View already exist in RFC-0003 Part I and
are used here with their canonical meanings.

---

*End of RFC-0005. Normative: sections 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
13, 15. Explanatory and load-bearing: sections 0, 14, 16, 17. Any change to
the definition of a Fact, a Fact status, Fact identity, the pipeline stages,
the canonical rules F1–F16, an Evidence Set, or a Fact's freshness or machine
binding is a BREAKING change and must be made by amendment (RFC-0003 Part II).*
