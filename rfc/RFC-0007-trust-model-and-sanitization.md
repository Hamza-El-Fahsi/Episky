# RFC-0007 — Trust Model, Data Trust, Sanitization and Injection Defense

**Status:** Draft
**Date:** 2026-08-01
**Scope:** What information the system may trust, under what conditions, and how
that trust evolves; how untrusted text is classified, contained, sanitized, and
transported; how prompt-injection attempts are neutralized
**Audience:** Future maintainers
**Supersedes:** Nothing
**Depends on:** RFC-0001 (accepted), RFC-0002 (accepted), RFC-0003 (accepted),
RFC-0004 (accepted). RFC-0021 is referenced for the machine's subsystem model
but is itself a Draft and is not a dependency.

**Roadmap note:** This is RFC-0000's "RFC-0007 — Trust Model, Sanitization &
Injection Defense" (Security, Required), the third document in the safety spine
(RFC-0000 §4, §7); it turns RFC-0001's trust boundaries and data-flow rules into
a concrete, testable specification.

**BREAKING:** No. This RFC adds normative content about how untrusted
information is handled. It does not weaken any Principle, Boundary, Invariant,
or canonical Definition in an accepted RFC; it operationalizes RFC-0001 §7–§8
and RFC-0002 invariants 4 and 5.

---

## 0. Preamble

RFC-0001 drew the trust boundaries and the rules of data flow across them
(RFC-0001 §7); RFC-0002 made two of them runtime invariants (RFC-0002
invariants 4 and 5); RFC-0004 separated **trust** from **authority** (RFC-0004
§2). This RFC answers the question those documents deliberately left open:

> **What information can the system trust, under what conditions, and how does
> trust evolve?**

**Trust is a property of information. Authority is a property of actors. Never
mix the two.** Authority — who may observe, propose, infer, verify, approve,
execute, refuse, persist, or explain — is defined by RFC-0004, and this RFC adds
nothing to it. This RFC is about *information*: its origin, its classification,
its journey through the system, and the only operations that change how much of
it may be believed.

**Reading notes.** Normative content uses the canonical vocabulary of RFC-0003
Part I; new terms are flagged for RFC-0003 in §18. "Untrusted" is RFC-0001's
sense — *data, never authority*: how the system must treat information, not a
judgment of malice. §13's invariants are the normative core; §14's abuse
analysis makes them believable. Where a topic belongs to another RFC, this
document defers instead of partially specifying it (RFC-0003 Part II §1).

---

## 1. Purpose

This RFC specifies the data-trust model of Episky. It answers one question:

**What information can the system trust, under what conditions, and how does
trust evolve?**

It makes RFC-0001's trust boundaries and data-flow rules concrete and testable:

- which **inputs** are untrusted, and in which **trust domain** each originates
  (§4);
- the finite **trust classes** at which information may be held and the only
  operations that move it between them (§5, §8, §9);
- how the system's information is **categorized** and what may become of each
  category (§6);
- the **trust flow** through the reasoning and execution pipeline (§7);
- the **prompt-injection model** — how untrusted text tries to become an
  instruction and why each attempt fails structurally (§10);
- the **sanitization principles** every mechanism must honor (§11);
- the **Provider View** — the only representation an external provider ever
  receives (§12);
- the **trust invariants** that make these rules enforceable (§13);
- a per-domain **abuse analysis** (§14) and the system's **failure behaviour**
  when trust cannot be determined or enforced (§15).

The result: no amount of eloquence, formatting, urgency, repetition, or claimed
authority in any information can, by itself, make it trusted. Trust increases
only through deterministic verification.

---

## 2. Scope

This RFC is about **information**, not actors. In scope: trust domains (§4);
trust classes (§5); information categories (§6); trust evolution — promotion
(§8), demotion (§9), and the flow through the pipeline (§7); containment and
sanitization, in principle, without algorithms (§10, §11); the Provider View
(§12); and trust invariants, abuse analysis, and failure behaviour (§13–§15).

This RFC is **architecture only**: it fixes rules, guarantees, and invariant
properties; it specifies no APIs, no pseudocode, no algorithms, no programming
language, no shell commands, and no data formats. Every normative statement
here remains valid regardless of implementation language. Mechanisms are owned
by the later RFCs listed in §3.

---

## 3. Non-Scope

The following topics belong to other RFCs. Whenever this RFC would otherwise
need them, it defers rather than partially specifying.

- **Authority, actors, ownership, delegation, and the authority matrix** —
  RFC-0004. This RFC adds no authority to any actor and removes none.
- **The Fact Model and diagnostics mechanics** — RFC-0005: the canonical fact
  model, provenance storage, normalization details, collector contracts, and
  output-size bounds. This RFC fixes the *rules* facts must satisfy; RFC-0005
  fixes *how* facts are built and stored.
- **Verification and rollback semantics** — RFC-0006: what counts as verified,
  when verification is impossible, and how unverified work is labeled. This RFC
  fixes *that* trust upgrades only by verification; RFC-0006 fixes *what
  verification is*.
- **The Approval and Policy Engine** — RFC-0008: risk taxonomy, classification
  rules, approval gates, standing approvals, and fail-closed policy behaviour.
  This RFC fixes the trusted/untrusted frame the engine operates within.
- **Secrets, privacy, and sensitive-data lifecycle** — RFC-0009: secret
  taxonomy, storage, redaction mechanics, and retention. This RFC fixes the
  boundary property ("no secret crosses outward"); RFC-0009 fixes how secrets
  are handled.
- **Provider contract and adapters** — RFC-0010. **Skill contract and
  ecosystem** — RFC-0011. **Context and memory mechanics** — RFC-0012.
  **Audit and transcript mechanics** — RFC-0013.
- **Machine subsystem and state-domain modeling** — RFC-0021. This RFC treats
  the machine as a source of untrusted text and references RFC-0021 only for
  its subsystem vocabulary (logs, packages, networking, configuration state).

---

## 4. Trust Domains

Every piece of information that enters the Assistant originates in exactly one
Trust Domain — the operational form of RFC-0001 §7's trusted/untrusted split,
sharpened so a rule can attach to each. A domain carries a **default posture**
that the information originating there inherits (§5); it is not an actor
(RFC-0004 §2) and not a component.

| Domain | Originates | Default posture | Key rule |
|---|---|---|---|
| **4.1 Operator** | Goal, Symptom, replies, pasted content | Trusted for intent; untrusted as literal text | The *decision* is authority (RFC-0004); the *words* are text, can carry an injection (§10.3), and get the same containment as any other text |
| **4.2 Core** | Orchestrator, Fact Layer, Approval and Policy Engine, Executor, Context Manager, Audit (RFC-0004 §4) | Trusted within scope (RFC-0001 §7) | Scoped, never a blank check (RFC-0004 §2) |
| **4.3 Diagnostics** | Collectors; normalization of Observations into Facts (RFC-0004 §4.5, §4.6) | Trusted for its output contract; untrusted in its raw reading | The *input* belongs to Machine/Filesystem (§4.9, §4.10) and is untrusted until normalized; the layer is trusted, the machine is not |
| **4.4 Policy Engine** | Classification and gating (RFC-0004 §4.7) | Trusted within scope | Classifies Proposals and gates Actions; never classifies against raw untrusted text (T2); its decisions are the baseline (RFC-0004 A6) |
| **4.5 Action Executor** | Execution of approved Actions (RFC-0004 §4.9) | Trusted within scope | Runs only Actions bound to a valid, unexpired, state-consistent Approval Token (RFC-0004 A2); never reads untrusted text to build commands (T1, T2) |
| **4.6 Provider** | Model text, Proposals, Hypotheses, explanations, refusals | Untrusted (RFC-0001 §7) | Model text is data, never authority, never commands; eloquent, wrong, or malicious, the system behaves identically (RFC-0004 A1) |
| **4.7 Local Model** | A model on the Operator's machine | Untrusted, same as any Provider | Localness grants no trust; the Provider boundary is a trust boundary regardless of network distance (§6.5) |
| **4.8 Community Skills** | Manifest, explanatory text, step descriptions, embedded code | Untrusted by default | Untrusted until authenticated and policy-reviewed, then executed under the same gates (RFC-0001 §7, §11; RFC-0004 A3); code never enters the LLM path (§6.12); text is untrusted text like any other (§6.11) |
| **4.9 Machine** | Command output, log streams, service state, system-state text | Untrusted | A compromised machine can emit hostile text (RFC-0001 §7) — RFC-0001's injection-via-the-machine risk (RFC-0001 §13 risk 2); becomes a Fact only by the Fact Layer's deterministic normalization |
| **4.10 Filesystem** | File contents: config files, package metadata, documents | Untrusted | File contents are machine text under another name; a config file or document can carry an injection payload (§10.1) and is data, never instructions; reading is Inspection, changing is a gated Action (RFC-0004 A4) |
| **4.11 External Network** | Fetched docs, packages, skill registries, remote content (RFC-0001 §7, §8.9) | Untrusted | Integrity and authenticity checked, content still untrusted after authentication (RFC-0001 §8.9); consulted under default-deny only when policy permits (RFC-0001 Q23 → RFC-0008) |
| **4.12 External Documentation** | Man pages, distro docs, package documentation, upstream wikis | Untrusted as text; consulted as information | Never executed, never a source of Facts, never policy; can inform a Hypothesis, never grant authority, change a Fact, or become an Action |

---

## 5. Trust Classes

Information is held at a **Trust Class** — a finite, totally ordered set. The
binary Trusted/Untrusted split is deliberately avoided: a four-class lattice
gives the system somewhere to put information that is *more than* untrusted
(suspected hostile) and information that is *not yet* trusted (conditional).
Each class defines what it means, who may produce it, how it may be consumed,
and how it may change.

| Class | Meaning | May be produced by | Consumed as | May change |
|---|---|---|---|---|
| **Trusted** | Accepted without independent re-derivation, *within a declared scope* (RFC-0004 §2) | Fact Layer (Facts), Operator (decisions), deterministic Core | Basis for reasoning, decisions, Provider Views, within scope and staleness | Downward only (§9) |
| **Conditional** | Accepted *only after* a deterministic check passes | Fact Layer (normalized but unconfirmed), authenticated-and-policy-checked skill declarations | Input only after the check; never as a Fact | Up to Trusted by verification (§8); down on failed checks (§9) |
| **Untrusted** | Data, never authority; contained, never executed, never evidence of itself | All Provider/Local Model output, all Machine/Filesystem/Network/skill/documentation text, unnormalized Observations | Quoted as content; normalized into Facts; summarized into Provider Views | Up only by verification (§8); down to Hostile (§9) |
| **Hostile** | Untrusted *plus* a positive signal of adversarial intent | Any domain whose content is quarantined | Quarantined; excluded from Context and Provider View; shown contained or withheld | Never above "suspicious"; re-verified only if source re-established |

### 5.1 The lattice
The classes form a total order — **Trusted > Conditional > Untrusted >
Hostile** — which is a lattice under two operations: **meet (∧)** — a composite
takes the **most restrictive** class of its parts (Untrusted + Trusted =
Untrusted; Hostile + anything = Hostile); and **join (∨)** — the least
restrictive class all parts share, which is *not* an upgrade path (§8). The
only permitted transitions are **downgrade** (always permitted) and **upgrade**
(only by deterministic verification, §8). Every non-verification operation
moves information down or keeps it level; the sole upward operations are the
Fact Layer's normalization and Verification's state-based confirmation.

---

## 6. Information Categories

Every datum is categorized; the category determines its default Trust Class and
the promotion and demotion rules that apply. A category may be carried at a
*lower* class than its default (demotion, §9), never higher except by the §8
path. Where a category's mechanics belong to another RFC, that RFC is named.

| Category | Default | Promotion | Demotion |
|---|---|---|---|
| **6.1 Observation** — raw Collector output with provenance (RFC-0003 §2.4) | Untrusted | normalized into a Fact (RFC-0005) | provenance loss → Hostile (§9.6) |
| **6.2 Fact** — normalized claim about the Machine, never LLM-authored (RFC-0003 §2.4) | Trusted within scope and staleness | none — Facts top the lattice; re-verification refreshes | expiry, contradiction, or provenance loss → Conditional/Untrusted (§9) |
| **6.3 Evidence** — Facts and permitted Observations relevant to the Goal (RFC-0003 §2.4) | meet of its members (§5.1) | never above its least-trusted member | a newly admitted Untrusted member lowers the set |
| **6.4 Hypothesis** — candidate explanation to be tested (RFC-0003 §2.5) | Untrusted | only by deterministic verification (RFC-0006) | contradiction → discarded or downgraded |
| **6.5 Provider Output** — everything the LLM returns | Untrusted | never — Proposal/Hypothesis at most, never Fact, policy, or command (RFC-0004 A1) | suspected injection → Hostile |
| **6.6 User Input** — Goal, Symptom, replies, pasted content | Trusted for intent; Untrusted as literal text | the intent becomes the Goal (authority, RFC-0004); the words remain text | relayed hostile output is literal untrusted text (§10.3) |
| **6.7 Configuration** — machine config files and settings (RFC-0021 §6.4, §6.8) | Untrusted | normalized into Facts | contradicted by observed state → re-read before use (§9.4) |
| **6.8 Logs** — machine log streams (RFC-0021 §4.12) | Untrusted | extracted and normalized into Facts or Evidence | injection indicators → Hostile |
| **6.9 Metadata** — package/service metadata, timestamps, sizes | Untrusted | normalized into Facts | contradicted by observation → re-checked before use |
| **6.10 Secrets** — credentials and personal data (RFC-0001 §8.7) | never exported | none — never in a Provider View, machine output summaries, or the Audit (RFC-0002 invariant 4) | suspected exposure = compromised; RFC-0009 owns the lifecycle |
| **6.11 Skill Manifest** — declared surface: targets, privileges, risk classes (RFC-0003 §2.7) | Conditional — after authentication and policy review | to Conditional on authentication and review (RFC-0011) | declared vs. actual mismatch → Untrusted (RFC-0001 Q22) |
| **6.12 Skill Code** — executable procedures (Actions, Collectors) | Untrusted; executed only as Actions bound to a valid Approval Token (RFC-0004 A2, A3) | never — never enters the LLM path, never executes outside the gate | suspicious content → Hostile; execution stays gated |

---

## 7. Trust Flow

Information moves through the system in a canonical pipeline. Trust does not
change on every hop; it changes only where the rules say it may.

```
Observation ──admitted as relevant material──▶ Evidence
     ──deterministic normalization (TRUST INCREASES)──▶ Fact
     ──selected into the decision basis──▶ Decision
     ──approval grants authority, not data trust (RFC-0004)──▶ Action
```

- **Observation → Evidence:** a raw Observation is admitted to the working set
  if relevant (RFC-0003 §2.4). Admission does **not** raise trust: if the
  Observation is raw, the set is at least Untrusted (meet rule, §5.1).
- **Evidence → Fact:** the Fact Layer deterministically normalizes admissible
  Observations into Facts (RFC-0005 owns the mechanics). **This is the only
  point in the pipeline where trust increases without execution.**
- **Fact → Decision:** Trusted Facts (within scope and staleness) form the basis
  of Diagnosis and Planning. Trust does not change; selection does.
- **Decision → Action:** Approval grants *authority* to act (RFC-0004); it does
  not raise the trust of any premise. The Action is built from sanctioned
  structures, never from untrusted text (T1, T2). Execution is followed by
  Verification, which re-observes state and confirms the Post-condition
  (RFC-0002 invariant 2) — the second place trust may increase (the confirmed
  *state* is raised; the Action itself is not).

Trust may decrease at any hop: stale Facts expire, Evidence is contradicted,
state changes invalidate a Decision's basis, and Verification failure downgrades
the claim of success. §8 and §9 fix the complete set of permitted changes.

---

## 8. Trust Promotion

**Trust may increase only through deterministic verification.** This is the
single most important rule in this RFC, and it is invariant T6. The complete
list of permitted upward moves:

1. **Observation → Fact.** A raw Observation is normalized and checked by the
   Fact Layer into a Fact with provenance (RFC-0001 §3.5; RFC-0004 A4). This is
   the canonical upgrade: from Untrusted material to a Trusted claim about the
   machine.
2. **Post-condition confirmation.** Verification confirms, by re-observation
   and state comparison, that an executed Action produced its expected
   Post-condition (RFC-0002 invariant 2; RFC-0003 §2.6). The *confirmed state*
   is raised to Trusted; the Action itself is not.
3. **Authenticated-and-checked skill metadata.** A Skill's declared metadata
   moves from Untrusted to Conditional only after authentication and policy
   review (RFC-0011 owns the mechanics). Authentication raises *admission*,
   never the trust of the Skill's runtime behavior.

**What is never an upgrade:** LLM confidence (the LLM cannot author Facts,
RFC-0001 §3.5, nor grade its own output, RFC-0002 invariant 7); repetition (a
claim is not more true because it is said twice); provider agreement (agreement
is not verification); popularity; ratings (they can inform admission policy,
not raise trust); approval (it grants authority to act, RFC-0004 §1.3, not trust
to premises); and formatting, eloquence, or authority of the text itself (an
instruction found in machine output cannot grant itself permission, RFC-0001 §7
rule 3). Only a deterministic check moves information upward; everything else
leaves it where it is or moves it down.

---

## 9. Trust Demotion

Trust decreases when the grounds for holding information at its current class
weaken. Demotion is **always permitted and often automatic.** Trust decreases
when:

1. **Stale information.** A Fact past its staleness bound drops below Trusted
   and must be re-collected before use (RFC-0002 invariant 10). Stale truth is
   not truth; it is old text.
2. **Inconsistent evidence.** A Fact contradicted by fresh evidence is
   invalidated and the fresh evidence wins (RFC-0002 invariant 10). The
   invalidated claim is downgraded to "disputed hypothesis at best."
3. **Provider disagreement.** When providers disagree about a claim that is not
   independently verifiable, the claim is not "half trusted"; it is downgraded
   to Untrusted until a deterministic check decides. Disagreement is not a
   promotion signal.
4. **Machine state changed.** If the machine state an Observation, Fact, or
   Approval Token was based on has changed, the stale basis is downgraded and
   re-established deterministically (RFC-0002 invariants 8 and 11).
5. **Failed verification.** A claim or outcome that fails verification is
   downgraded: an unverified outcome is never presented as success (RFC-0002
   invariant 9), and a failed Post-condition is disclosed and recovered
   (RFC-0002 §10).
6. **Loss of provenance.** If a datum's origin can no longer be established, it
   is downgraded to Untrusted (or Hostile if the loss itself is suspicious). An
   unprovenanced claim is a claim to distrust.
7. **Source compromise.** A domain or component that shows signs of compromise
   downgrades everything recently received from it. Compromise is presumed
   contagious until re-verified (T12).
8. **Sanitization failure.** Content that cannot be sanitized is downgraded to
   Hostile and quarantined (§11 S6; T9, T11).

Demotion preserves the label: a downgraded datum still carries its provenance
and the record of why it was downgraded, so the reason stays visible in the
Audit (RFC-0002 invariant 13).

---

## 10. Prompt Injection Model

RFC-0001 risk 2 is binary: *either no untrusted text ever flows into action
construction, or the project does not work* (RFC-0001 §13 risk 2). This section
enumerates how untrusted text attempts to become an instruction so the
invariants (§13) and layers (§11, §12) can be checked against each — principles
only, no implementation.

An **injection attempt** is untrusted text that attempts to become an
instruction, aimed at three readers: the **LLM** (persuade the model to propose
a harmful Action or reveal its instructions), the **Operator** (persuade the
human to approve a harmful Action), or the **system itself** (trick a
deterministic component into treating text as a command). The system neutralizes
all three reads structurally: untrusted text has no channel that turns text into
action (T1, T2), no channel to the LLM except a sanitized Provider View (T3),
and no channel to the Operator except contained presentation (S4).

### 10.1 Attack sources (enumerated)

1. **Shell output.** Raw byte streams of executed Actions or probes, including
   stderr and prompts. *Neutralized:* output is Observation (Untrusted) until
   normalized; never interpolated into a command (T2).
2. **journalctl / system logs.** Attacker-controlled strings in log streams
   (RFC-0021 §4.12). *Neutralized:* Logs category (§6.8); contained before
   entering Context; bounded extracts only.
3. **Package descriptions.** Package metadata consulted during diagnosis
   (RFC-0021 §4.9). *Neutralized:* machine text (§6.9); never an instruction;
   contained before any Provider View.
4. **Config files.** Machine configuration text (§6.7), including files an
   attacker wrote. *Neutralized:* read as data; quoted or normalized into Facts;
   exact text never drives an Action without the gate.
5. **Markdown / formatted text files.** Documents whose formatting or link
   syntax carries hidden instructions. *Neutralized:* documentation class
   (§4.12); stripped to content; never rendered as action.
6. **HTML / web content.** Fetched pages with markup and hidden content
   (RFC-0021 §4.10). *Neutralized:* Network domain (§4.11); parsed as data,
   never executed; markup is never a command.
7. **ANSI escape sequences.** Control sequences that manipulate terminals, hide
   text, or spoof output. *Neutralized:* sanitization neutralizes control
   characters before rendering or summarization (§11 S3).
8. **Unicode tricks.** Bidirectional overrides, homoglyphs, zero-width
   characters. *Neutralized:* the same sanitization; displayed text is not
   trusted byte-for-byte; the Operator sees the contained form (§11 S3, S4).
9. **Terminal output.** Anything rendered to the Operator's terminal that can
   spoof the screen or hide a payload. *Neutralized:* the Operator's screen is
   a boundary too (§11 S4); quoted machine text is visibly quoted.
10. **Malicious repositories.** A hostile repo consulted for code, packages, or
    documentation. *Neutralized:* Network domain; integrity and authenticity
    checked, content still untrusted after authentication (RFC-0001 §8.9);
    nothing executes without the gate.
11. **Malicious documentation.** A doc that instructs, a man page with hostile
    content. *Neutralized:* External documentation (§4.12); contained and
    quoted, never executed, never a source of Facts.
12. **Malicious skills.** Skill text or content designed to steer the LLM or
    Operator (RFC-0001 §11; RFC-0004 §9.10). *Neutralized:* skill text
    sanitized before any Provider View; skill Actions pass the same gate
    (RFC-0004 A3); skill code never enters the LLM path (§6.12).
13. **Hallucinated providers.** Plausible-but-false or self-referential output
    ("I have already fixed it"). *Neutralized:* Provider output is never a Fact
    (§6.5); success claims are never trusted (RFC-0004 A5); verification is
    state-based; the runtime never fabricates (RFC-0002 invariant 9).

### 10.2 The two-channel model

The system treats every injection attempt as a **text** problem first and an
**instruction** problem second.

- **Text channel:** the payload is carried — quoted, bounded, labeled — and may be shown to the Operator or summarized to the LLM as *content*.
- **Instruction channel:** the same payload is *never* routed to an interpreter, a command, a plan constructor, or a policy decision.

An injection succeeds only if both channels ever touch the same text.
Invariants T1 and T2 keep them apart.

### 10.3 The Operator as relay

Because the Operator sees hostile machine output (a boot message, a malicious
README), an injection can be replayed through the Operator: the Operator types
the payload back into the session. The system cannot prevent the Operator from
typing anything, but it can ensure that what the Operator types is treated as
*text* with the intent of a Goal, never as a standing instruction (§4.1). This
is why User Input is "Trusted for intent, Untrusted as literal": the intent is
real, the wording is still contained.

---

## 11. Sanitization Principles

Sanitization is the deterministic transformation of untrusted text that removes
or neutralizes its ability to act as instructions — quoting, escaping, stripping
control characters, truncating, summarizing, or replacing with a structured
representation — **without changing its trust class**. Sanitized text is still
untrusted text (T9). The exact mechanisms belong to RFC-0012 and the Context
Manager's enforcement point (RFC-0004 §9.11); what is fixed here is the
philosophy every mechanism must honor.

- **What must be sanitized:** every piece of untrusted text before it crosses a
  boundary toward the LLM (into Context or the Provider View), toward the
  Operator's terminal, or toward any interpreter.
- **Where:** at the boundary to Context/Provider (RFC-0004 §9.11) and at the
  boundary to the Operator's screen (S4).
- **Why:** to keep the text channel and the instruction channel apart (§10.2) — to ensure untrusted text is *carried*, never *obeyed*.

1. **S1 — Sanitize is not trust.** Sanitization makes text *unable to act as
   instructions*; it does not make text *true*, *safe to obey*, or *upgraded*.
   A sanitized payload is still Untrusted (or Hostile) and still carries its
   provenance.
2. **S2 — Contain first, sanitize second.** Text is bounded and labeled as it
   arrives; sanitization is applied at the boundary to Context/Provider. At no
   point does sanitization substitute for verification of any claim.
3. **S3 — Neutralize control, preserve content.** Escaping, stripping ANSI,
   taming Unicode, and quoting are preferred over deletion. Content the
   Operator may need (a log line, a package description) should survive in a
   form that cannot be read as direction.
4. **S4 — The Operator's screen is a boundary too.** Text shown to the Operator
   is contained: control characters are neutralized so a hostile payload cannot
   spoof the screen, and quoted machine text is visibly *quoted* — data being
   shown, not an instruction being given.
5. **S5 — No secret passes through.** Sanitization must never pass a secret
   (§6.10). Redaction happens before anything leaves the session (RFC-0001 §9;
   RFC-0009 owns the mechanics).
6. **S6 — Fail closed, fail visible.** If sanitization cannot establish what a
   piece of text is, it is treated as **Hostile** and quarantined, and the
   Operator is told (§15). There is no "probably fine."
7. **S7 — Sanitization is deterministic and testable.** Whatever the mechanism,
   it must be checkable by a deterministic rule, so the project can test "given
   this hostile input, the output contains no executable channel."
8. **S8 — Summarization is a sanitization.** Bounding, truncating, and
   summarizing (RFC-0001 §8.8) limit what a payload can carry into a Provider
   View. Summaries are lossy on purpose and never presented as raw truth.

---

## 12. Provider View

**The provider receives representations, never raw machine state.** This is the
operational form of RFC-0001 §7 rule 4 ("Provider and machine never meet
directly") and RFC-0002 invariant 4 ("The LLM is only ever consulted through a
Provider View"). The Provider View is the specific, sanitized representation of
Context assembled for a single Provider call, produced only by Context
Building, containing no secrets (RFC-0003 §2.8). Its rules:

1. **Built, never forwarded.** The View is assembled by Context Building from
   Context under these rules. No component sends raw material past it.
2. **Contains no secrets — ever.** Not in Facts, not in quotes, not in skill
   material. This is invariant T7 and the privacy spine (RFC-0009 owns the
   mechanics).
3. **Claims and content are labeled.** Facts appear as claims (with provenance
   and scope); quoted material as quoted content, visibly not claims; Hypotheses
   as hypotheses. The View never presents a Hypothesis as a Fact, or raw text
   as a Fact.
4. **Untrusted text is neutralized, not passed through.** Any untrusted text in
   the View has been sanitized (S1–S3, S8): bounded, control-neutralized, framed
   as content. A hostile payload cannot be "read as an order" because the
   framing makes it content.
5. **Size-bounded per call.** The View is assembled under the current bounds
   (RFC-0001 §8.8; RFC-0005 owns exact output bounds, RFC-0001 Q8). Truncation
   is explicit and labeled, not silent.
6. **Purpose-limited.** The View contains only what the current consultation
   needs (Goal, relevant Facts, relevant Evidence). It is not a dump of the
   session (RFC-0001 §9).
7. **Disposable and not authoritative.** The View is a representation for one
   Provider call. The model's reading of it is Hypothesis; nothing in the View,
   and nothing the model says about it, upgrades anything (RFC-0004 A1, A5; §8).

A representation is not raw state: raw bytes, unbounded output, control
characters, and secrets never appear — only the bounded, labeled, sanitized
representation does.

---

## 13. Trust Invariants (Normative)

These invariants join RFC-0002 §9 and RFC-0004 §8: no implementation may
violate them and no later RFC may weaken them except by amendment (RFC-0003
Part II §1). Each is named for reference and cited to its source.

- **T1 — Untrusted text is never executed.** Nothing from a Provider, a Skill,
  or machine output is ever interpolated into a shell command or run as a
  string (RFC-0002 invariant 5; RFC-0001 §7 rule 1). Actions are built from
  sanctioned structures only. *Blast radius:* a hostile payload can never
  become a command by itself.
- **T2 — Untrusted text never flows into action construction.** No string from
  an untrusted domain is a building block of an Action, a Step, a Plan, or a
  verification criterion (RFC-0001 §7 rule 1, §8.4). *Blast radius:* the binary
  RFC-0001 risk 2 is closed at construction, not at display.
- **T3 — The machine and the LLM never meet directly.** The Core mediates every
  exchange; the LLM receives only a Provider View (RFC-0001 §7 rule 4;
  RFC-0002 invariant 4). *Blast radius:* raw machine text cannot reach the model
  unmediated.
- **T4 — Provider output is data, never authority.** Model output can at most
  become a Proposal or Hypothesis; never a Fact, policy, or command (RFC-0001
  §7; RFC-0004 A1). *Blast radius:* the worst an LLM can do is propose.
- **T5 — Untrusted text is never trusted as evidence of itself.** The Assistant
  may quote machine output, but the LLM's interpretation of it is always
  Hypothesis until a deterministic check confirms it (RFC-0001 §7 rule 2).
  *Blast radius:* a payload cannot vouch for its own truth.
- **T6 — Trust upgrades only by deterministic verification.** The only upward
  moves in the lattice are Observation→Fact normalization and state-based
  Verification (RFC-0001 §3.5, §10.5; RFC-0002 invariant 2; RFC-0004 §2 Trust).
  Approval, eloquence, repetition, provider agreement, popularity, and ratings
  upgrade nothing (§8). *Blast radius:* no amount of persuasion raises trust.
- **T7 — Secrets cross boundaries one way only.** Credentials and API keys
  enter at the boundary they are needed and never travel into Provider context,
  machine output summaries, or the Audit (RFC-0001 §7 rule 6, §8.7; RFC-0002
  invariant 4). *Blast radius:* the privacy spine cannot leak through a payload.
- **T8 — The meet rules composition.** Any composite of information is at the
  most restrictive class of its parts, and the label travels with the text
  (§5.1; RFC-0002 invariant 10). *Blast radius:* untrusted text cannot inherit
  the trust of its neighbors.
- **T9 — Sanitization never upgrades.** Sanitized text is still untrusted and
  still traceable; sanitization that fails degrades the text to Hostile (§11
  S1, S6). *Blast radius:* "cleaning" is never mistaken for "proving."
- **T10 — Context is secret-free, bounded, and purpose-limited.** Context and
  the Provider View satisfy RFC-0001 §9 and RFC-0003 §2.8: no secrets, a
  ceiling, a purpose, full Operator visibility (§12). *Blast radius:* the
  boundary toward the LLM is never unbounded or unlabelled.
- **T11 — Fail closed on trust failure.** If the trust class of a datum cannot
  be established, or sanitization cannot run, the datum is treated as Hostile
  and quarantined, and the Operator is told (RFC-0001 §8.12; §15). *Blast
  radius:* an unclassified thing is never treated as benign.
- **T12 — Suspicion is contagious downward.** Compromise of a source, a
  detected injection attempt, or a provenance loss downgrades the source's
  recent output (§9.7). Trust is presumptively revoked until re-verified.
  *Blast radius:* a single hostile source cannot poison the whole pipeline
  quietly.

---

## 14. Abuse Analysis

Following RFC-0004 §9: for each Trust Domain, what happens if it is malicious,
compromised, or fails — and why the architecture stays safe anyway. Mirroring
RFC-0004 §9.13, three facts recur across all domains: no reader of untrusted
text can act on it directly (T1, T2); trust and verification are the only
upward path (T6); and the untrusted boundary is a label, not a wall to guess
around — unlabelable text is Hostile, quarantined, and disclosed (T11).

| Domain | Attack surface / failure mode | Why the architecture stays safe |
|---|---|---|
| **14.1 Operator** | Relay (§10.3); mistaken approval. Assumption: the Operator's decision is authority (RFC-0004) | A relayed payload re-enters as User Input — Trusted for intent, Untrusted as literal (§4.1) — and flows through the normal Proposal → Policy → Approval gate, so the worst a relay can do is propose; Verification re-observes state, the Audit records the decision (RFC-0002 invariant 13) |
| **14.2 Core** | A compromised or faulty deterministic component. Assumption: Core is trusted by construction (RFC-0001 §7) | Core cannot be driven by untrusted text by construction (T1, T2); bounded by invariants enforced in independent components (RFC-0004 §9.13) and the Audit's independence; failures are disclosed (RFC-0002 §10), and "fact unknown" is a legitimate Fact (RFC-0003 §2.4) |
| **14.3 Diagnostics** | Malicious Collector; buggy normalizer. Assumption: trusted for its output contract, raw reading is Machine text (Untrusted) | A false Fact is a *reasoning* compromise, not an *execution* one (RFC-0004 §9.6): downstream still passes Policy and Approval, and Verification re-observes actual state; a Collector cannot mutate the machine (RFC-0004 A4) |
| **14.4 Policy Engine** | Misclassified Proposal reaching the wrong gate. Assumption: classification is deterministic, never the LLM's self-report (RFC-0002 invariant 7) | The gate is the only path to execution (RFC-0004 A9); policy errors fail closed (RFC-0001 §8.12; RFC-0008 owns the exact behaviour); the engine never reads raw untrusted text to classify against (T2) |
| **14.5 Action Executor** | An Action built from untrusted text; executor overreach. Assumption: runs only approved Actions bound to a valid token (RFC-0004 A2) | Actions are built from sanctioned structures (T1, T2); every execution is followed by Verification (RFC-0002 invariant 2); partial execution is disclosed and recovered (RFC-0002 §10); the Executor has no shell of its own |
| **14.6 Provider** | Prompt injection; a hostile model; a data leak. Assumption: the worst the Provider can produce is untrusted text | T4 (no execution path), T5 (claims never evidence of themselves), A5 (success claims never trusted), the Fact Layer's exclusivity over truth, the no-secrets boundary (T7), and the gate on everything it proposes (RFC-0004 A9); on outage, facts-only operation continues (RFC-0002 §10) and the runtime never fabricates (RFC-0002 invariant 9) |
| **14.7 Local Model** | Same as any Provider. Assumption: the Provider boundary is a trust boundary regardless of network distance (§4.7) | T3, T4, T5, T7 apply identically; localness grants no trust, it only changes the transport |
| **14.8 Community Skills** | Hostile skill content; an injection payload in a skill's text. Assumption: a Skill is untrusted by default (RFC-0001 §11) | Its Actions pass the same Policy and Approval gate (RFC-0004 A3); its Collectors run inside the Diagnostics contract (A4); its text is sanitized before any Provider View (RFC-0004 §9.10; T3, T9, T10); its code never enters the LLM path and never executes outside the Executor's token gate (§6.12; A2); the worst a malicious Skill can do is propose |
| **14.9 Machine** | Hostile command output, modified state, a compromised machine. Assumption: the machine reports what it is, which is not trusting that it is healthy (RFC-0001 §7) | Machine text never leaves the Untrusted class except by Fact normalization (T6); never executed (T1), never in action construction (T2), reaches the LLM only as contained, sanitized content (T3, T10); its content cannot grant authority (RFC-0001 §7 rule 3); Verification re-observes, contradiction invalidates (RFC-0002 invariant 10) |
| **14.10 Filesystem** | Hostile config files, package metadata, documents. Assumption: file contents are machine text (§4.10) | The same containment as any machine text (T1–T5); file contents become Facts only by normalization; changing a file is a gated Action, reading is Inspection (RFC-0004 A4); skill manifests are verified against actual behavior (RFC-0001 Q22 → RFC-0011) |
| **14.11 External Network** | A hostile download, a poisoned doc, a malicious repository. Assumption: network content is untrusted even after authentication (RFC-0001 §8.9) | Integrity and authenticity are checked, content still untrusted; consulted under default-deny policy (RFC-0001 Q23 → RFC-0008); text contained and sanitized like any other (T3, T9, T10); it can inform a Hypothesis, never a command; on failure, disclosed, and the session continues on local facts (RFC-0002 §10) |
| **14.12 External Documentation** | A doc that instructs; a man page with hostile content. Assumption: documentation is consulted as information (§4.12) | Contained and quoted, never executed and never a source of Facts; its content can become a Hypothesis, which becomes a Plan only through the normalizing Core and the gate; a doc cannot grant authority or change a Fact; on failure, disclosed as "could not confirm," never guessed (RFC-0001 §10) |

---

## 15. Failure Behaviour

When trust cannot be determined or enforced, the runtime follows RFC-0002 §10's
ordering — **determinism first, then disclosure, then decision, then action** —
with these specific outcomes:

1. **Information cannot be verified.** A claim or outcome that cannot be
   verified deterministically is presented as unverified and, where execution
   is concerned, blocked or moved to an explicit confirm gate (RFC-0004 §9.13;
   RFC-0001 §10.1). "Unverifiable is unapprovable."
2. **Evidence conflicts.** The Assistant stops the current path, surfaces the
   contradiction, and re-evaluates with the Operator (RFC-0001 §10.4). It never
   proceeds on the contradicted belief; fresh evidence wins (RFC-0002 invariant
   10).
3. **Verification fails.** A failed Post-condition is disclosed, the state is
   re-established deterministically, and the Action is recovered or reversed
   per RFC-0002 §10. An unverified outcome is never presented as success
   (RFC-0002 invariant 9).
4. **Provider unavailable.** Mode is part of the runtime (RFC-0002); facts-only
   operation continues without the model; the runtime never fabricates a reply
   (RFC-0002 invariant 9). On recovery, the session re-establishes state before
   further machine action (RFC-0002 invariant 8).
5. **Unknown classification.** If the trust class of a datum cannot be
   established (no origin, no provenance, unparseable content), it is treated
   as Hostile: quarantined, excluded from Context and the Provider View, and
   disclosed to the Operator (T11; RFC-0001 §8.12).
6. **Sanitization failure.** Content that cannot be neutralized does not cross
   into Context or the Provider View (S6). The Operator is told that content
   was withheld and why. The session continues on what was safely contained.
7. **Sanitization unavailable.** The boundary holds closed until sanitization
   is available; no component may pass raw untrusted text into a Provider View
   because "the sanitizer was unavailable" (RFC-0001 §8.12).
8. **Injection attempt detected.** A recognized attempt is labeled Hostile,
   contained for the Operator to inspect, and recorded (T12, RFC-0002 invariant
   13). Detection does not require the system to argue with the payload; it
   requires it to not act on it.
9. **Expiry, contradiction, or provenance loss.** Data falls to a lower class
   automatically and is re-collected or re-verified before further use
   (RFC-0002 invariant 10; §9).
10. **A domain shows compromise.** Everything recently received from a
    compromised source is downgraded and re-verified before use (T12). The
    suspicion is disclosed to the Operator.
11. **Presentation failure.** If the contained rendering of hostile text cannot
    be produced, the Operator is told a payload was present and asked how to
    proceed; the payload is never acted on and never fed forward uncontained.

---

## 16. Open Questions

These are architectural questions this RFC deliberately leaves open; each names
its owner. None of them blocks the trust model's core guarantees.

1. **Exact sanitization mechanics.** The precise rules for stripping control
   characters, taming Unicode, escaping, and summarizing are owned by RFC-0012
   (and the Context Manager's enforcement point). This RFC fixes the philosophy
   (§11) and the invariants (§13) they must satisfy.
2. **Output-size bounds.** The precise ceilings on Context and Provider View
   size (RFC-0001 Q8) are owned by RFC-0005. This RFC fixes only that bounding
   is a sanitization (S8) and that truncation is explicit (T10).
3. **Redaction sufficiency.** RFC-0001 Q14 asks which redaction approach is
   sufficient given arbitrary secret formats; the mechanics belong to RFC-0009.
   This RFC fixes only the binary property (T7) and the failure mode when
   redaction cannot be guaranteed (§15.6).
4. **"Hostile" as a user-visible class.** Whether and how the Operator is shown
   that content was quarantined as a suspected attack (vs. merely withheld) is
   an interface question for RFC-0015. This RFC requires disclosure (§15) but
   not the presentation form.
5. **Skill metadata trust bound.** Whether authenticated-but-unreviewed skills
   hold Conditional metadata or must be Untrusted until human review is owned
   by RFC-0011 (the review/tiering process). This RFC's floor: never above
   Conditional, never trusted as Fact (§6.11).
6. **Detection vs. containment.** Whether the project attempts to *detect*
   injection attempts (and label them Hostile) or only to *contain* them is a
   stance choice owned by RFC-0012 (the sanitization enforcement point); this
   RFC requires containment as the guarantee (T1–T5) and treats detection as a
   defense-in-depth bonus (§10, §15.8).

---

## 17. Architectural Risks

Roughly ordered by severity. These are the ways the trust model could fail, and
the structural mitigation already in this RFC for each.

1. **Sanitization theater.** The risk that sanitization is treated as making
   text *safe* rather than *unable to act*. Mitigation is structural: T1 and T2
   hold regardless of sanitization quality, so even a perfect bypass cannot
   execute or construct an action. Sanitization failure degrades to Hostile
   (T9, T11), never to "proceed."
2. **Label drift.** Provenance or class labels lost in transformation would
   break T8 and §5.1. Mitigation: the label is part of the datum's contract
   (RFC-0002 invariant 10), and the Fact Model (RFC-0005) must keep it
   structural.
3. **Boundary creep toward the LLM.** The Provider View is the only channel
   (T3), but every later RFC that adds content to Context must re-check §12. If
   a future RFC routes a new untrusted source into the View unlabeled, the
   binary risk of RFC-0001 risk 2 returns. Mitigation: T10 and the meet rule
   (T8) make the View's composition auditable.
4. **Operator-relay amplification.** Because the Operator is the final
   authority, an injection that persuades the *human* is the hardest class to
   fully neutralize (§10.3). Mitigation is layered: contained presentation
   (S4), approval UX designed against the beginner-with-root-power
   contradiction (RFC-0001 §13 risk 3), and Refuse authority (RFC-0004). The
   residual risk is recorded here honestly, not hidden.
5. **False confidence in "Hostile."** Labeling content Hostile is a containment
   decision, not a fact about the payload. Mislabeling *benign* content Hostile
   only withholds content; mislabeling *hostile* content Untrusted is the
   dangerous direction. Mitigation: the invariants bind the Untrusted class
   regardless (T1–T5), and T11 fails toward Hostile.
6. **Skill-ecosystem pressure.** RFC-0001 §13 risk 4 (ecosystem trust)
   interacts with §6.11 and §8.3: a lax authentication would widen Conditional
   admission, a strict one would starve the ecosystem. This RFC sets the floor
   (never above Conditional, never trusted as Fact); the trade-off's mechanics
   are RFC-0011's.
7. **Sanitization as a single point of failure.** If all untrusted text is
   funneled through one mechanism, that mechanism becomes the target.
   Mitigation: T1 and T2 make the mechanism's failure survivable (it degrades
   to Hostile), and S7 requires it to be testable.

---

## 18. New Terms for RFC-0003 (flagged for inclusion in Part I)

The following terms are defined in this RFC and must be added to RFC-0003 Part
I by additive amendment: **Trust Domain**, **Trust Class**, **Trust Lattice**,
**Sanitization**, **Containment**, **Neutralization**. The definitions appear
at first use in §4, §5, and §11.

---

*End of RFC-0007. Normative: sections 4, 5, 6, 7, 8, 9, 10, 11, 12, 13, 15.
Explanatory and load-bearing: sections 0, 1, 2, 3, 14, 16, 17, 18. Any change
to a Trust Domain's default posture, a Trust Class transition, an information
category's rule, a sanitization principle S1–S8, an invariant T1–T12, or a
failure-behaviour rule is a BREAKING change and must be made by amendment
(RFC-0003 Part II).*
