# Iteration 9 — Design Review (Context & Memory Layer)

> **Document type:** Implementation design review, at the same rigor as
> Iterations 2–8. **Not an RFC, not code.**
> **Read this first:** This document **defines no new architecture, modifies no
> RFC, invents no behavior, and writes no production code.** It translates the
> frozen corpus (RFC-0000–0013, RFC-0021, the decision traceability matrix,
> `docs/architecture-implementation-blueprint.md`, and the ratified
> `docs/implementation-decision-notes.md` DN-1…DN-64) into an implementation
> plan for the **Context & Memory layer — the `context` package**
> (blueprint §8.9, re-ordered to Iteration 9 by DN-45, and so labeled by the
> Iteration 8 closeout). Where the corpus does not decide something, this
> document **reports** it as an ambiguity or a question; it does not resolve it.
>
> **Status of sources.** RFC-0012 is **Draft** (not Accepted; the context
> model's normative sections 1–35 may change before acceptance) and RFC-0013 is
> **Draft** (2026-08-02). Per RFC-0003 Part II §1.1 Draft RFCs are not normative
> and must not be relied upon by implementation; yet the blueprint (a
> translation, §0) targets the Drafts' *invariants* as the conformance oracle
> (blueprint §9 #2). Iteration 9 inherits Iterations 1–8's posture: it conforms
> to RFC-0012's and RFC-0013's Draft wording knowingly, accepting the rework
> risk that a Draft change carries. Blueprint §8.0 gate stands — production code
> begins only after RFC-0015/0019/0020 and the Drafts are Accepted; this
> iteration builds the translation scaffold. The load-bearing dependencies this
> layer rests on — RFC-0001 §5 (Context & Memory), §9 (Context Philosophy);
> RFC-0002 §2.4 (Context Building), §4.2 (state-change invalidation), §9
> invariants 4, 8, 13; RFC-0004 §4.11 (Context Manager), §9.11 (corruption
> blast-radius); RFC-0005 §7 (Fact storage), §12 (freshness); RFC-0007 S1–S8,
> §12 (Provider View); RFC-0009 SC2, SC3, SC16; RFC-0010 §3 (Provider Inputs),
> §11 (Context Boundary), PR14 — are **Accepted**, which bounds the rework risk.
> RFC-0006 §14 (Evidence as Context material) is a forward reference whose
> owning RFC is not yet written (reported as Q10). RFC-0021 §4/§11 (machine
> subsystems as the Subject vocabulary of carried Facts) is Draft and is
> **referenced, not a dependency** (RFC-0012 §36), exactly as the RFC says.
>
> **Scope decision (reported — Q1).** DN-45 re-ordered the build so that
> `context` (blueprint §8.9) follows `policy` (Iteration 7) and `executor` +
> `audit` (Iteration 8), and the Iteration 8 closeout
> (`docs/iteration-8-design-review.md` §16) records that "The next iteration is
> the `context` layer (RFC-0012)." Blueprint §8.9 still reads "Iteration 8 —
> `context`"; the label was never renumbered (mirroring how §8.7/§8.8 were left
> standing for Iteration 7 and §8.8 for Iteration 8). This task's scope
> implements `context` at Iteration 9, which continues the recorded supersession
> of the numbering (Q1). The re-order is dependency-safe — `context` (Layer 4)
> precedes `providers` (Layer 5, which imports `context`) and `core`/`cli`
> (Layers 6–7, which import `context`), preserving the safety spine (RFC-0000 §6
> items 1, 3) and blueprint Risk #9's mitigation (secrets, Layer 2, precedes
> context and providers).

---

## 1. Architectural consistency review

### 1.1 Scope (blueprint §8.9, transcribed)

| Item | Value |
|---|---|
| Goal | Bounded, secret-free reasoning material and the Provider View |
| Work | Deterministic assembly (§12); boundary enforcement (§13); consented Memory; Provider View builder |
| Definition of Done | CM1–CM16 conformance; the Provider View is the only outward channel (PR14); no secret in Context (SC2); re-assembly on loss (CM13) |
| RFC basis | RFC-0012 §12, §13, §21; RFC-0010 §3 |

Blueprint §7 (test oracle) carries the row: `context` — "Assembly deterministic
and bounded (§12); secret-free (SC2); Provider View is the only outward channel
(PR14); re-assembly never restore (CM13)" — oracle RFC-0012 §12, §13, §21;
RFC-0002 §2.4. Blueprint §5 exposes the package contract: `context` — "Assemble
a bounded, secret-free Context from Facts/Goal/history/Skill material; produce
the Provider View (the only outward channel)" (RFC-0012 §12, §13; RFC-0010 §3;
SC2). Blueprint §10 coverage row: `context/*` = RFC-0012, §12, §13, §21, oracle
CM1–CM16; SC2; PR14. Blueprint §3 names the responsibilities: "Context & Memory
(RFC-0001 §5; RFC-0004 §4.11) — Assembly rules §12, boundary enforcement §13,
consented Memory, Provider View builder".

**Layer-enforceable now vs. cross-component.** The §8.9 DoD set is CM1–CM16,
PR14, SC2, CM13. The layer can satisfy the DoD set **at its own surface** as
deterministic mechanics plus layer-boundary tests; the parts whose enforcement
points do not exist yet — the Context Building state wiring and its exits toward
Diagnosis/Planning (RFC-0002 §2.4/§6), the STATE_CHANGED_DETECTED event emission
and re-inspection trigger (RFC-0002 §4.2), the producers of conversation history
(`core`/`providers`), the producers of skill material (`skills`/`providers`),
the audit write of the context-boundary record (RFC-0013 §23), the presentation
*form* of the View (RFC-0015), and the durable backing of Memory (RFC-0020) —
are recorded as the owning packages' DoD (RFC-0002 → `core`, Iteration 11;
RFC-0011/RFC-0010 → `providers` + `skills`, Iteration 10; RFC-0013/RFC-0002 →
`core`; RFC-0015 → `cli`; RFC-0020), mirroring how Iteration 7 made P1/P11/P12
and the durable half of P13 testable as layer-boundary obligations
(DN-45/DN-50/DN-53) and how Iteration 8 recorded the §6.2 edges and the Executing
exits against `core`.

**The enforcement halves this layer inherits.** Iteration 6 recorded, not
dropped: the SC2–SC5 half of the blueprint §8.6 DoD is satisfied at the secrets
layer as boundary tests, and **cross-component enforcement is the owning
packages' DoD** (DN-43). RFC-0009 SC2 (Context is secret-free), SC3 (no secret
in the Provider View), and SC16 (privacy parity) are the blueprint §8.9 DoD of
**this** iteration: the Context Manager is "the enforcement point and may never
decide to include a secret" (RFC-0004 §4.11; DN-43 grounding). Each is a
**Definition of Done item of this iteration**, not an optional follow-up.
RFC-0001 §5's "Enforce redaction of secrets before anything leaves a session"
and "Provide the Operator a complete, exportable view of what is remembered" are
the §18/§14 visibility DoD of this iteration.

### 1.2 Out of scope (recorded, not dropped)

Each of these is owned elsewhere and is **not** built in Iteration 9:

| Item | Owned by | Blueprint gate |
|---|---|---|
| The Context Building state wiring: entry conditions from Machine Inspection/Awaiting Input/Replanning, re-entry on staleness/consolidation/fallback, and the exits → Diagnosis / Planning (a failed build → Awaiting Input, never an LLM consultation) | RFC-0002 §2.4, §6; `core`, Iteration 11 | RFC-0002 §2.4 |
| STATE_CHANGED_DETECTED event emission and the re-inspection trigger that marks the set Stale and re-collects Facts before the next decision | RFC-0002 §4.2; RFC-0005 §12; `core` + `factlayer` | RFC-0002 §4.2; RFC-0005 §12 |
| The producers of conversation/turn history (Operator input, Provider replies, proposals presented, decisions taken) | RFC-0012 §6 category 3; `core` (session) + `providers`, Iterations 10–11 | RFC-0012 §6 |
| Skill material and its pre-entry sanitization (content enters sanitized and bounded; code never enters) | RFC-0011 §26, SK13; `skills` + `providers`, Iteration 10 | RFC-0011 §26; RFC-0007 §6.12 |
| The Provider View presentation *form* (how the derived View is rendered to the Operator or consumed by the provider) | RFC-0010 §3; RFC-0015 (future); `cli` | RFC-0010 §15 OQ3; RFC-0001 §5 Presentation |
| Concrete size bounds, per-category freshness bounds, and the sanitization catalogue at the enforcement point | RFC-0012 §37 OQ1–OQ3; RFC-0020 (values; placeholder default, DN-18 precedent) | RFC-0012 §37; RFC-0020 |
| The durable backing of Memory: storage mechanics, retention, deletion, export, and what survives a resume | RFC-0012 §37 OQ4/OQ5; RFC-0014; RFC-0020 | RFC-0012 §37; RFC-0014 |
| The context-boundary audit *record* (category 9): the audit write that "material entered Context or Memory" — written at the runtime boundary, never the material itself | RFC-0013 §7 cat. 9, §23; RFC-0004 §9.11; `core`, Iteration 11 | RFC-0013 §23; RFC-0002 I-13 |
| The Operator consent *collection* (the UI that grants or withholds Memory promotion and wipe) | RFC-0001 §9.2, §9.5; `cli`/RFC-0015 | RFC-0001 §9.2/§9.5 |
| The RFC-0021 Subject vocabulary (machine subsystems) as the vocabulary of carried Facts | RFC-0021 §4, §11 (Draft); referenced, not a dependency (RFC-0012 §36) | RFC-0012 §36 |
| Signatures / package naming | RFC-0020 (future) | DN-1 |
| The RFC-0012 §39 vocabulary additions to RFC-0003 Part I (Context Category, Memory Category, Context Assembly, Routing State, Consolidation) | RFC-0003 Part II amendment process; a docs change, not this scaffold | RFC-0012 §39; RFC-0003 Part II |

### 1.3 What exists already

The `context` package (`{__init__,assemble,boundaries,memory,provider_view}.py`)
was scaffolded in Iteration 0 with ownership docstrings only (blueprint §2);
`tests/test_packages.py` already imports and docstring-checks them, so the tree
test stays green throughout — C1–C4 **fill** the stubs, they do not create
modules. `tests/test_dependency_rules.py` already declares
`ALLOWED["context"] = {"schema", "factlayer", "trust", "secrets", "systemmodel"}`
and the forbidden-source rows (no package may import `context` except
`providers`, `cli`, `core` per blueprint §4.1/§4.2). The `context` forbidden
edge set is already declared: `FORBIDDEN["context"] = {"providers", "policy",
"executor", "audit"}` (blueprint §4.2; the `secrets (values)` restriction is a
*use* limit, not an import ban — context imports `secrets` classifier types
only, per the blueprint §4.2 qualifier). Baseline suite: **1965 tests, green**,
branch `iteration/8-executor`, HEAD `388053e` (Iteration 8 closeout), working
tree clean; branch `iteration/9-context` created from `388053e`.

---

## 2. RFC consistency review

| RFC | Section | Implemented as | Status in layer |
|---|---|---|---|
| RFC-0012 | §0 Purpose | Three binary guarantees: Context is assembled, never authoritative; Memory is a consented subset, never authority; Context is the only channel outward (RFC-0002 §2.4; RFC-0007 T3) | Implemented (C1–C4, DoD) |
| RFC-0012 | §1 What is Context | The working set: assembled (CM3), a cache of evidence (CM1), session-scoped by default, never a source of truth | Implemented (C1) |
| RFC-0012 | §2/§3 What is Memory / vs Context | A consented promotion, not a separate store; for reasoning, reversible, never authority (CM2); lifetime + consent distinguish it from Context | Implemented (C3) |
| RFC-0012 | §4 Context Ownership | Assembly/custody → Context Manager; durability decision → Operator; Memory custody → Context Manager; no other component owns, writes, or decides about Context | Implemented (C1/C3, structural) |
| RFC-0012 | §5 Context Authority | Assemble; Filter and sanitize (RFC-0007 S1–S8); Persist durable only under consent; Observe Facts as a reader; no component decides truth, includes a secret, persists without consent, or treats Context/Memory as an execution/approval input | Implemented (C1–C4, structural) |
| RFC-0012 | §6 Context Categories | Exactly six categories: Goal, Facts, History, Evidence, Skill material, Routing state — types now, producers at their owning iterations (Q9) | Implemented (C1, Q9) |
| RFC-0012 | §7 Memory Categories | Exactly three: Preference Memory, Machine Memory, Durable Context; never secret values, raw output, the Audit record, or private content without demotion (SC16) | Implemented (C3) |
| RFC-0012 | §8/§9 What enters / never enters | Only the six categories through the Context Manager; fixed exclusions (secrets any form, raw unbounded output, unprovenanced claims, hostile/quarantined, skill code, personal data not required, anything without a stated purpose) | Implemented (C1/C2, DoD) |
| RFC-0012 | §10/§11 Lifecycle + Legal Transitions | Empty → Assembling → Current → Stale → Consolidated → Promoted → Destroyed; anything not listed is illegal (default deny); Stale → Current without re-inspection and Destroyed → Current are illegal | Implemented (C1); the event triggers are `core`'s (Q8) |
| RFC-0012 | §12 Context Composition | Deterministic, ordered assembly: Facts first with provenance, Goal and scope, bounded history, skill material last, routing state folded in, bounds applied at assembly; same inputs → same Context (S7) | Implemented (C1, DoD) |
| RFC-0012 | §13 Context Boundaries | Six one-way boundaries: Machine→Fact→Context; Skill→Context; Provider reply→History→Context; Context→Provider View; Context→Memory; Context→Audit | Implemented (C2/C3/C4, boundary tests) |
| RFC-0012 | §14 Context Isolation | One working set per session; no component-side Context; one active Goal (RFC-0002 §2.3); multi-goal is RFC-0014's | Boundary (C1: no cross-session merge in the package; session ownership is `core`'s) |
| RFC-0012 | §15 Context Propagation | Exactly four paths: → Provider View; → next Context Building; → Memory; Memory → Context by re-assembly, never injection | Implemented (C1/C3/C4) |
| RFC-0012 | §16/§17 Freshness + Invalidation | Context inherits Fact freshness (RFC-0005 §12); stale is rebuilt never patched; state change/freshness lapse/interrupt/contradiction mark Stale and force re-assembly; per-category bounds are RFC-0020's | Boundary (C1: deterministic freshness gates + mark-stale function; the events are `core`'s, Q8) |
| RFC-0012 | §18 Context Visibility | Always visible, export complete, wipe always available, honest about provenance, no hidden retention (CM14) | Implemented (C3/C4 as the surface; the *view* is `cli`'s) |
| RFC-0012 | §19 Context Trust | Context adds no truth; each category at its own trust class; Context is not an execution input; containment stance; corrupted Context degrades reasoning, never execution | Implemented (C1/C2, boundary tests) |
| RFC-0012 | §20/§21 Destruction + Recovery | Destroy on purpose lapse / Operator request / session end, complete and recorded; recovery is re-assembly, never restore (CM13) | Implemented (C1/C3); the destruction *record* is the cat-9 audit event (Q6) |
| RFC-0012 | §22 Persistence Philosophy | Session-scoped by default; durable only by explicit reversible consent; nothing without a stated purpose; retention by consent, not default; no second store; answers RFC-0001 Q13 | Implemented (C3, CM11, DoD) |
| RFC-0012 | §23/§24 Minimization + Privacy | Purpose-limited, bounded, consolidation is a sanitization, never collect for later; secret-free by construction (SC2), privacy parity (SC16), consent governs durability, no Context telemetry, transparency is the mechanism | Implemented (C1/C2, DoD) |
| RFC-0012 | §25 Context ↔ Facts | Context carries, never produces Facts; Fact storage is Context's (with RFC-0013); Fact lifecycle drives Context; a fresh Fact always wins | Implemented (C1); the Fact *store* remains factlayer's (DN-19/DN-20), Q3-adjacent |
| RFC-0012 | §26 Context ↔ Verification | Verification never reads Context; Outcomes/evidence are Context material, never verification power (RFC-0006 §14 forward reference, Q10) | Implemented (C1, Q10) |
| RFC-0012 | §27 Context ↔ Providers | The View is the only channel (PR14); provider replies are labeled material, never Facts; providers never read Memory; assembly is owned here + RFC-0015 (RFC-0010 §15 OQ3) | Implemented (C4); the provider consultation is `core`'s |
| RFC-0012 | §28 Context ↔ Skills | Skill content sanitized and bounded at the enforcement point; text is not a Fact; code never enters; skills have no Context surface | Boundary (C2: the enforcement point now, catalogue RFC-0020's, Q3; producers are `skills`, Iteration 10) |
| RFC-0012 | §29 Context ↔ Diagnostics | Diagnostics never write Context; raw Observations never enter; secret-adjacent Observations quarantined; failed collectors are "fact unknown" | Consumed (C1: Facts arrive normalized from `factlayer`; the collector behavior is `collectors`') |
| RFC-0012 | §30 Context ↔ Approval | The gate never reads raw Context; Context carries no permissions (CM16); no Action carries Context; Memory never widens a grant | Implemented (C1/C3, structural) |
| RFC-0012 | §31 Context ↔ Audit | Audit records that material entered Context, never the material; Context/Memory are not the Audit; destruction recorded before it completes | Boundary (C1/C3 emit the cat-9 event; the write is `core`'s, Q6) |
| RFC-0012 | §32 Context ↔ Secrets | Context is secret-free by construction (SC2); the rule is RFC-0009's, the mechanics this RFC's; truncation/consolidation cannot reveal; no secret in a View (SC3); suspected exposure invalidates, never rehydrates | Implemented (C2, SC2/SC3/SC16, DoD) |
| RFC-0012 | §33 Context ↔ Runtime | Context Building is the only assembler and is a runtime state; state change invalidates; **answers RFC-0002 Q12** (routing-state category, supersede-disclose semantics); interrupted work re-establishes | Boundary (C1 carries routing state + supersede semantics, Q7; the routing transitions and state wiring are `core`'s) |
| RFC-0012 | §34 Context ↔ Extensions | New sources re-check RFC-0007 §12; new categories are additive amendments; no extension owns Context/Memory; RFC-0014/0015/0020 consume this model | Recorded (C1, Q9) |
| RFC-0012 | §35 CM1–CM16 | The normative invariant suite — the package's conformance oracle | Oracle (C5) |
| RFC-0001 | §5 Context & Memory | Hold only §9 permits; track session history and facts-known; complete exportable view; enforce redaction of secrets before anything leaves the session | Implemented (C1–C4, DoD) |
| RFC-0001 | §9 Context Philosophy | Purpose-limited, visible/exportable, bounded, never authoritative, retention by consent; never persist secrets/raw output/private content/anything without a purpose | Implemented (C1–C4, DoD) |
| RFC-0002 | §2.4 Context Building | The only place LLM input is assembled; the enforcement point for redaction and truncation; touches neither machine nor provider; exit → Diagnosis/Planning (no usable view → Awaiting Input) | Boundary (C1/C4: the assembler + View builder exist; the state wiring is `core`'s, §1.2) |
| RFC-0002 | §4.2 Machine events | FACTS_COLLECTED / STATE_CHANGED_DETECTED mark the set stale and force re-inspection | Boundary (C1: a mark-stale function consumes the event; the event is `core`'s, Q8) |
| RFC-0002 | §9 invariants 4, 8, 13 | LLM only through a provider view (I-4); halt → re-assessment (I-8); recorded before the consequence (I-13) | I-4/I-8 at C1/C4 (boundary); I-13's cat-9 write is `core`'s (Q6) |
| RFC-0004 | §4.11 Context Manager | Build Context from Facts; sanitize; enforce purpose-limits and size bounds; assemble Views with no secrets; Memory only by consent; authority Observe + Persist under consent; trusts Fact Layer + Operator consent; does not trust raw Observations / Provider output / Skill material | Implemented (C1–C4, the package's profile) |
| RFC-0004 | §9.11 Context Manager (failure) | Deterministic assembler with no decision authority; sanitization enforcement point is a required invariant; Audit records what entered Context; Durable Memory only under consent; corrupted Context degrades reasoning, never execution | Implemented (C1/C2/C3); the cat-9 audit write is `core`'s (Q6) |
| RFC-0005 | §7 Fact Lifetime | Fact *storage* belongs to RFC-0012 (Context/Memory) and RFC-0013 (Audit); RFC-0005 fixes only what each lifecycle step means | Boundary (C1: Context carries Facts; the Fact current-set store is factlayer's, DN-19/DN-20) |
| RFC-0005 | §12 Freshness | Context inherits Fact freshness; a Stale/Expired/Unknown-freshness Fact makes the set Stale | Implemented (C1, CM7) |
| RFC-0007 | S1–S8; §12 Provider View | Sanitization applied at the enforcement point (mechanism now, catalogue RFC-0020's, Q3); the View is built never forwarded, secret-free, labeled, neutralized, size-bounded, purpose-limited, disposable | Implemented (C2/C4); per-source catalogue deferred (Q3) |
| RFC-0007 | T3, T7, T10 | The View is the only representation a provider sees; no secret in the View; no secret in Context, in any form | Implemented (C2/C4, boundary tests) |
| RFC-0008 | §2, §6 | The gate consumes Facts and Proposals, never Context; Context carries no permissions (CM16) | Consumed (C1/C3, structural; the gate is `policy`, Iteration 7) |
| RFC-0009 | SC2, SC3, SC16 | Context secret-free by construction; no secret enters a Provider View; privacy parity | Implemented (C2/C4, boundary tests, DoD) |
| RFC-0010 | §3 Provider Inputs | The View carries exactly: Operator Goal, evidence/Allowed Context, Conversation State, routing state — nothing else (no Audit, no secrets, no raw output, no provider identity) | Implemented (C4); the View's *shape* is reported (Q4) |
| RFC-0010 | §11 Context Boundary | The View is assembled, not forwarded; minimal by default; the boundary never widens for capability; leakage is a security incident | Implemented (C4, PR14, DoD) |
| RFC-0010 | §13 PR14 | The Provider View is the only channel | Implemented (C4, DoD) |
| RFC-0010 | §15 OQ3 | Context assembly mechanics are owned by RFC-0012 and RFC-0015 | Implemented (C1/C4: the RFC-0012 half; the RFC-0015 form deferred) |
| RFC-0011 | §15, §26, SK13 | No secret to a Skill; skill material enters sanitized and bounded; skill text is not a Fact; skill code never enters Context or the View; Context assembly owned here + RFC-0015 | Boundary (C2 enforcement point; SK13 asserted at the boundary; producers are `skills`, Iteration 10) |
| RFC-0013 | §7 cat. 9 | Context-boundary records: material entered Context or Memory, never the material itself | Boundary (C1/C3 emit the event; the write is `core`'s, Q6) |
| RFC-0013 | §23 | The write points are runtime boundaries | Recorded (Q6, §1.2) |
| RFC-0021 | §4, §11 | Machine subsystems as the Subject vocabulary of carried Facts | Referenced, not a dependency (RFC-0012 §36); latent edge (Q2, DN-44 precedent) |

**Already resolved by the corpus (not re-opened here):**

- **The Context Manager is the sole assembler.** Only the Context Manager
  builds Context, Memory, and the Provider View (CM3; RFC-0004 §4.11; RFC-0002
  §2.4 "the only place"). No component writes a second working set. Not a
  question.
- **Context is never a source of truth.** The Fact Layer owns truth (RFC-0004
  §4.6); Context is a cache of evidence (RFC-0001 §9.4); a fresh Fact always
  wins over Context (RFC-0002 invariant 10). Not a question.
- **Context is secret-free by construction.** No secret value enters Context or
  the Provider View in any form, no exception for derived artifacts (SC2/SC3;
  RFC-0007 T10; RFC-0004 §4.11 "May never decide: to include a secret"). Not a
  question — the *enforcement mechanism* is the Q3 resolution.
- **Durable Memory exists only by explicit, reversible Operator consent.** No
  promotion without a stated purpose; retention by consent, not default
  (CM11; RFC-0001 §9.5; RFC-0004 §4.11 Persist under consent). Not a question.
- **Context and Memory carry no permissions.** Possession grants no authority;
  Memory never widens a grant (CM16; RFC-0004 A8; RFC-0008 §6). Not a question.
- **Context and Memory are never the Audit.** The Audit records about Context;
  Context/Memory are never records (CM15; RFC-0013 §7 cat. 9; RFC-0009 §31).
  Not a question — the *write point* is the Q6 resolution.
- **The Provider View is the only channel outward.** The provider receives
  exactly the View and nothing else (PR14; RFC-0010 §3, §11; RFC-0007 T3;
  RFC-0002 invariant 4). Not a question.
- **Raw Observations never enter Context; only normalized Facts do.** The Fact
  pipeline is raw output → Observation → Normalization → Fact → Evidence Set →
  Context (RFC-0005 §2); raw machine output and unprovenanced claims are fixed
  exclusions (RFC-0012 §9). Not a question.
- **Skill code never enters Context or the Provider View** (RFC-0007 §6.12;
  RFC-0011 §26); skill text enters only sanitized and bounded. Not a question.
- **Context Building is a runtime state; the View is built per consultation and
  is disposable** (RFC-0002 §2.4; RFC-0007 §12). The assembly *function* is this
  layer's; the *state wiring* is `core`'s. Not a question.
- **Context freshness is inherited, not independent.** There is deliberately no
  second freshness model (RFC-0012 §16; RFC-0005 §12). Not a question.
- **Context recovery is re-assembly, never restore** (CM13; RFC-0012 §21;
  RFC-0002 invariant 8). Not a question.
- **Context destruction is complete and recorded; a destroyed set is rebuilt,
  never resurrected** (CM12; RFC-0012 §20; RFC-0002 I-13). Not a question — the
  audit *record* of the destruction is the Q6 write point.
- **Multi-goal Context separation is RFC-0014's** (RFC-0012 §37 OQ5; §14 rule 2);
  this layer enforces one active Goal per working set. Not a question.

---

## 3. Layer placement

`context` sits at **Layer 4** (blueprint §4.1), beside `executor` and `audit`.
Its imports reach only downward to Layers 0–3; nothing below Layer 4 imports it
except the qualified readers in blueprint §4.2 (`providers` imports `context`;
`cli` imports `context`, `audit`, `core`, `schema`; `core` imports everything,
per §4.1). `context` consumes `schema`, `factlayer`, `trust`, `secrets`
(classifier types only), and `systemmodel` (latent).

- **`context → factlayer`** is the Facts edge: the assembly reads the Fact
  current set at its trust class and freshness state (RFC-0012 §8 rule 1;
  RFC-0004 §4.11 "Trusts: Fact Layer"). Facts are the only category trusted as
  Fact (RFC-0007 §9); context never normalizes, never verifies (RFC-0002 §2.4
  touches neither machine nor provider).
- **`context → trust`** is the sanitization edge: the enforcement point applies
  RFC-0007 S1–S8 to untrusted text before it enters Context or a View
  (RFC-0012 §5 authority 2; RFC-0004 §4.11 "all sanitized before use"). The
  per-source catalogue (which treatment for which source) is RFC-0020's (Q3).
- **`context → secrets` (classifier types only)** is the SC2/SC3 edge: the
  boundary classifies secret-shaped values and fail-closes before anything
  enters Context or a View (RFC-0009 SC2/SC3; blueprint §4.2's "classifier types
  only" qualifier, mirroring Iteration 8's `audit → secrets` metadata-only edge).
- **`context → systemmodel` (latent).** RFC-0021 §4/§11 supplies the machine
  subsystem vocabulary of carried Facts, but RFC-0012 §36 says it is
  "Referenced, not a dependency" — the declared-but-unused case, mirroring
  DN-9/DN-37/DN-44 and Iteration 8's latent `systemmodel` note (Q2).
- **No `context → providers` edge.** The View is the only outward channel; the
  provider is a consumer of the View type, never a producer of Context material
  (RFC-0010 §3, PR14; blueprint §4.2 "assembly is owned by the Context Manager,
  not providers").
- **No `context → policy`/`executor` edge.** The gate consumes Facts and
  Proposals, never Context (RFC-0008 §2, §6); Context carries no permissions
  (CM16) and is never an execution input (RFC-0002 invariant 5; RFC-0012 §19
  rule 3).
- **No `context → audit` edge.** Context is never the Audit (CM15); the
  context-boundary *record* is written at the runtime boundary by `core` (Q6),
  because context may not import `audit` and the Audit holds records, never the
  material (RFC-0013 §7 cat. 9).

---

## 4. Ownership map

Each package has exactly one owner per row (RFC-0004 §3; blueprint §10): the
*authority* is owned by RFC-0004 §4.11 (Context Manager profile) and the
*assembly/model* by RFC-0012 (Context & Memory model) — two distinct properties,
one owner each, exactly as blueprint §10's two-owner check describes. Module-level
ownership:

| Module | Owning RFC sections | Protected by |
|---|---|---|
| `context/assemble.py` | RFC-0012 §8, §10–§12, §16, §17 | CM3 (only assembler), CM1 (never truth), CM5 (purpose-limited), CM6 (bounded), CM7 (fresh or rebuilt), CM9 (session-isolated), CM10 (propagates only by assembly), CM13 (re-assembly, never restore); RFC-0002 §2.4 |
| `context/boundaries.py` | RFC-0012 §9, §13, §19, §23, §24, §32; RFC-0009 SC2/SC16; RFC-0007 S1–S8 | CM4 (secret-free by construction), SC2, SC16, T10; RFC-0004 §4.11 (enforcement point, never decides to include a secret) |
| `context/memory.py` | RFC-0012 §7, §18–§22 | CM2 (never authority), CM11 (durable only by consent), CM12 (destruction complete and recorded), CM14 (visible/exportable/wipable); RFC-0001 §9.2/§9.5; RFC-0004 §4.11 (Persist under consent) |
| `context/provider_view.py` | RFC-0012 §13; RFC-0010 §3, §11 | PR14 (the only outward channel), SC3 (no secret in the View), CM10; RFC-0007 §12 (built, labeled, size-bounded, disposable); RFC-0002 invariant 4 |

**Two-owner checks.** (a) *Context authority vs. assembly model:* RFC-0004 §4.11
owns the *authority* (Observe + Persist under consent; May decide what enters
within RFC-0009/0012 bounds); RFC-0012 owns the *model* (§6 categories, §8/§9
entry rules, §10/§11 lifecycle, §12 composition, §13 boundaries, §35 CM1–CM16) —
one package, two properties, one owner each (blueprint §10's `context` = RFC-0004
profile + RFC-0012 model). (b) *Memory custody vs. durability decision:* RFC-0012
§4 owns *custody* (Context Manager); RFC-0001 §9.5 + RFC-0004 §3 Memory row own
the *durability decision* (the Operator; the Context Manager executes it under
consent) — the promotion gate is here, the consent is the Operator's (CM11).
(c) *Sanitization mechanics vs. catalogue:* RFC-0012 §32 owns the *mechanics*
("the rule is RFC-0009's; the mechanics are this RFC's"); RFC-0020 owns the
*per-source catalogue* (§37 OQ3) — mechanism now, values later (Q3, DN-18
precedent). (d) *Context-boundary records vs. who writes them:* the record
*format* is RFC-0013's (§7 cat. 9); the *write point* is the runtime boundary
(RFC-0013 §23) — the Context Manager emits the deterministic event (what entered,
what was destroyed, never the material), `core` writes it (Q6).

**Authority boundaries.** This layer holds **Observe** (as a consumer of Facts)
and **Persist** (Context and Memory, under consent) — and nothing else. The
Context Manager never Proposes, Infers, Approves, Executes, or Verifies
(RFC-0004 §4.11; RFC-0002 invariant 3); it "may never decide: what is true; what
to do; to include a secret; to persist without consent". The layer assembles and
sanitizes; it decides neither truth nor action (CM1, CM16).

---

## 5. Dependency analysis

**Allowed** (blueprint §4.1; already enforced by `tests/test_dependency_rules.py`):

| Edge | Why allowed |
|---|---|
| `context → schema` | The canonical vocabulary the working set carries (Goal value, Fact, VerificationOutcome, Action/Plan labels for history) (RFC-0013 §7; RFC-0003 Part I) |
| `context → factlayer` | Facts enter at their trust class and freshness state from the Fact Layer (RFC-0012 §8; RFC-0004 §4.11 "Trusts: Fact Layer"); context reads, never produces or edits Facts (RFC-0012 §25; RFC-0005 F1) |
| `context → trust` | The sanitization enforcement point applies RFC-0007 S1–S8 to untrusted text before it enters Context or a View (RFC-0012 §5; RFC-0004 §4.11) |
| `context → secrets` (classifier types only) | Secret-shaped values are classified and fail-closed before entering Context or a View (RFC-0009 SC2/SC3/SC16); blueprint §4.2's "classifier types only" qualifier |
| `context → systemmodel` (latent) | RFC-0021 §4/§11 Subject vocabulary of carried Facts — referenced, not a dependency (RFC-0012 §36); declared-but-unused (Q2, DN-44 precedent) |

**Forbidden** (blueprint §4.2): `context` may not import `providers` (assembly
is the Context Manager's, RFC-0012 §12; the View is the only outward channel,
PR14), `policy` (the gate consumes Facts, never Context, RFC-0008 §2/§6),
`executor` (Context is not an execution input, RFC-0002 invariant 5; CM16), or
`audit` (Context is never the Audit, CM15; the Audit holds records, never the
material, RFC-0013 §7 cat. 9), and it may not import `secrets` *values* (only
classifier types; SC2 construction is fail-closed, never value-reading).
Notably: no `context → providers` edge even though `providers` imports `context`
— the direction is the provider consuming the View type, never the reverse;
no `context → audit` edge even though RFC-0004 §9.11 says "the Audit records what
entered Context" — the record is written by `core` at the runtime boundary (Q6).

**Latent edges.** `systemmodel`/RFC-0021 is the declared-but-unused case,
mirroring DN-9/DN-37/DN-44 and Iteration 8's latent note: the Subject vocabulary
is carried *by* the Facts context consumes, so the package needs no second
import; RFC-0012 §36 marks it "Referenced, not a dependency". `verification` is
exercised *by* this layer (VerificationOutcome enters as Evidence material,
RFC-0006 §14) but never imported — the Outcome type is `schema`'s, and Evidence
enters as Facts or labeled evidence, never verification power (RFC-0012 §6
category 4).

---

## 6. Public surface analysis

The planned public surface is **reported**, not ratified; final signatures are
RFC-0020's (DN-1). The shape below is what C1–C4 will build. The package is
value-free and import-safe beyond its own surface; assembly and View building
are pure functions that perform no I/O, no provider call, and no subprocess —
determinism and the boundary tests run against supplied material and the
factlayer current set (the run-primitive precedent of Iteration 8, Q1).

`context/assemble.py`

- The deterministic assembly function over explicit inputs (Q2): a Goal value
  (statement + scope; the Goal is the Core's per RFC-0003 §2.3, carried as a
  schema-shaped value), the Fact current set (from `factlayer`, filtered to
  relevance + freshness, RFC-0012 §12 rule 1), bounded labeled history (a
  supplied, already-sanitized turn record), sanitized skill material (a supplied
  bounded input), and the routing-state marker (RFC-0012 §33) — plus a stated
  purpose that bounds what may enter (CM5).
- Composition order is fixed (§12): Facts first with provenance, Goal and scope,
  bounded history, skill material last, routing state folded in; bounds applied
  at assembly, not after. Same inputs, purpose, and bounds → the same Context
  (RFC-0007 S7).
- Lifecycle mechanics (§10/§11): an assembled working set is Current; a
  consumed state-change/freshness event marks it Stale (Q8); overflow past the
  bound consolidates transparently, never silently grows (CM6, placeholder
  default, Q9); destruction is complete and rebuild-only (CM12/CM13).
- Never returns a truth verdict (CM1); never admits a raw Observation, an
  unprovenanced claim, or a secret (RFC-0012 §9; enforced through `boundaries`).

`context/boundaries.py`

- The enforcement point (RFC-0004 §4.11): every input is classified and
  sanitized before it may enter Context or a View — secret-shaped values are
  fail-closed excluded (SC2), untrusted text is neutralized and contained
  (RFC-0007 S1–S8), personal data is treated as secret until an explicit
  demotion (SC16), hostile/quarantined content is excluded (RFC-0012 §9 rule 4).
- The per-source sanitization catalogue (which treatment for which source) is
  RFC-0020's (§37 OQ3); the mechanism is this layer's (Q3).
- No value crosses: the boundary is value-free and fail-closed, never
  value-reading (SC2 construction; the `secrets` classifier-type-only import).

`context/memory.py`

- The consented promotion gate (CM11): Context material moves to Memory **only**
  with an explicit consent carrying a stated purpose; anything else is refused
  and produces no durable artifact (RFC-0001 §9.5; RFC-0004 §4.11).
- Exactly the three §7 categories (Preference Memory, Machine Memory, Durable
  Context), all promotions under consent; never secret values, raw output, the
  Audit record, or private content without demotion (SC16).
- Visibility, export, and wipe are first-class (CM14): the Operator can always
  list, export, and wipe what is held (RFC-0001 §9.2). Wipe is complete and
  irreversible; there is no restore path (CM12/CM13).
- The durable backing (storage, retention, deletion, what survives a resume) is
  deferred to RFC-0014/RFC-0020 (§1.2); the in-memory mechanic is built now
  (Q5, DN-50/DN-62 precedent).
- Memory never decides anything (CM2): no decision, approval, or truth path
  reads it.

`context/provider_view.py`

- The View builder: a deterministic derivation from the assembled Context to
  the Provider View — the only outward channel (PR14) — carrying exactly the
  RFC-0010 §3 elements (Operator Goal, the selected evidence/Allowed Context,
  Conversation State, and the Capability Declaration echoed back) and nothing
  else (no Audit, no secrets, no raw output, no provider identity, no machine
  identity beyond reasoning needs). The routing-state marker (RFC-0012 §33) is
  carried as part of the Conversation State the View presents, per RFC-0010 §3's
  "the structured record of the current reasoning thread".
- Secret-free by construction (SC3), size-bounded per call (RFC-0007 §12 rule 5),
  purpose-limited (rule 6), labeled (claims vs. hypotheses vs. quotes, RFC-0007
  §12 rule 3), and disposable (rule 7). Built, never forwarded (RFC-0010 §11
  rule 1).
- The View's *shape* is reported, not ratified (Q4): RFC-0010 §3 says "This RFC
  does not define its shape — no schemas — but defines its boundary"; the
  RFC-0015 presentation form and RFC-0020 signatures are deferred (DN-1).

Nothing else is exported. The facade re-exports only the owned vocabulary
(blueprint §3); the package surface carries no decision path (CM1/CM2/CM16), no
execution surface (RFC-0002 invariant 3), and no I/O.

---

## 7. Boundary analysis

- **Downstream of the Fact pipeline.** The assembly consumes Facts from the
  Fact Layer at their trust class and freshness state (RFC-0012 §8; RFC-0004
  §4.11); it never reads raw machine output, never normalizes (RFC-0005 §2), and
  a failed collector's "fact unknown" never becomes a fabricated Context entry
  (RFC-0012 §29 rule 4).
- **Upstream of the Provider.** The Provider View is the only outward channel
  (PR14): assembled per call, secret-free (SC3), labeled, and disposable
  (RFC-0007 §12). The provider consumes the View type (Iteration 10); this layer
  never calls a provider and never shapes the View per vendor (RFC-0010 §3 rule
  4; PR10).
- **The secret boundary.** The enforcement point at `boundaries.py` fail-closes
  secret-shaped values before anything enters Context or a View (SC2/SC3; RFC-0004
  §4.11 "May never decide: to include a secret"); personal data is secret until
  explicit demotion (SC16). All three are boundary tests, not unit tests
  (RFC-0009 §0; DN-43's "SC2–SC5 are boundary tests, not unit tests" precedent).
- **The consent boundary.** The Context → Memory promotion is the only durable
  path, gated on a stated purpose (CM11; RFC-0001 §9.5). The consent input
  arrives from the Operator through `core`/`cli` (Iterations 10–11); the gate
  mechanics are here.
- **The audit boundary.** The Audit records that material entered Context or
  Memory, never the material itself (RFC-0013 §7 cat. 9; RFC-0004 §9.11). The
  context package emits the deterministic boundary event; `core` writes the
  record before the material is used (RFC-0013 §23; RFC-0002 I-13) — the Q6
  resolution.
- **The sanitization boundary.** Untrusted text (skill material, provider
  replies as history) is neutralized and contained at the enforcement point
  before it enters Context or a View (RFC-0007 S1–S8, §12 rule 4); the View is
  "a representation, never raw state" (RFC-0007 §12).
- **The authority boundary.** Context and Memory carry no permissions; nothing
  in the package is an execution, approval, or truth input (CM16; RFC-0008 §6;
  RFC-0002 invariants 3, 5). The gate reads Facts, never Context.

---

## 8. Required invariants

Each invariant's normative source, whether the layer can make it hold at its
own surface now, and where the remainder is enforced (mirroring the
layer-boundary precedent of Iterations 5–8).

| Invariant | Normative source | Layer-enforceable now | Enforcement point for the rest |
|---|---|---|---|
| CM1 — Context is never a source of truth | RFC-0012 §35; RFC-0004 §4.6; RFC-0001 §9.4 | **Yes** (C1/C4: assembly and the View never upgrade a claim's trust class; Facts enter with provenance; a boundary test proves no reasoning result becomes a Fact without Fact-Layer provenance) | — |
| CM2 — Memory is never authority | RFC-0012 §35; RFC-0003 §2.8 | **Yes** (C3: memory.py exposes no decision/approval/truth path; a boundary test proves no authority decision reads it) | — |
| CM3 — only the Context Manager assembles | RFC-0012 §35; RFC-0004 §4.11; RFC-0002 §2.4 | **Yes** (C1: assemble.py is the only constructor; no other module writes a working set; an instrumentation test verifies only assemble constructs) | — |
| CM4 — Context is secret-free by construction | RFC-0012 §35; RFC-0009 SC2; RFC-0007 T10; RFC-0004 §4.11 | **Yes** (C2: the enforcement point fail-closes secret-shaped values; a boundary test feeds a known token and verifies it appears nowhere in Context or its View) | — |
| CM5 — Context is purpose-limited | RFC-0012 §35; RFC-0001 §9.1 | **Yes** (C1: assembly requires a stated purpose; unrelated material is excluded and refused) | — |
| CM6 — Context is bounded | RFC-0012 §35; RFC-0001 §9.3; RFC-0007 S8/T10 | **Yes, as mechanism** (C1: a size bound + transparent consolidation with a placeholder default, DN-18; concrete values are RFC-0020's, §37 OQ1) | RFC-0020 (values) |
| CM7 — Context is fresh or rebuilt | RFC-0012 §35; RFC-0005 §12; RFC-0002 §4.2 | **Yes, as the gate** (C1: assembly excludes Stale/Expired Facts or marks the set Stale; the next decision re-inspects — the re-inspection trigger is `core`'s, §4.2) | `core` (re-inspection), Iteration 11 |
| CM8 — invalidation is deterministic and precedes use | RFC-0012 §35; RFC-0002 §4.2; RFC-0002 I-13 | **Yes, as a function** (C1: a mark-stale function consumes the state-change/freshness event and marks the set Stale, recorded as an event; the event emission is `core`'s) | `core` (STATE_CHANGED_DETECTED), Iteration 11 |
| CM9 — Context is session-isolated | RFC-0012 §35; RFC-0002 §2.3 | Boundary (C1: one working set per assembly, one active Goal, no cross-session merge in the package) | `core` (session ownership), Iteration 11; RFC-0014 (multi-goal) |
| CM10 — Context propagates only by assembly | RFC-0012 §35; RFC-0002 §2.4; RFC-0007 T3; RFC-0010 PR14 | **Yes** (C4: the Provider View is the only outward surface; an instrumentation test proves nothing else exports Context material) | — |
| CM11 — durable Memory only by explicit consent | RFC-0012 §35; RFC-0001 §9.5; RFC-0004 §4.11 | **Yes** (C3: the promotion gate requires consent + stated purpose; a promotion without consent is refused with no durable artifact) | — |
| CM12 — destruction is complete and recorded | RFC-0012 §35; RFC-0001 §9.1/§9.2; RFC-0002 I-13 | **Yes, as mechanism** (C1/C3: destroy removes every copy; no restore path; the destruction *record* is the cat-9 event `core` writes, Q6) | `core` (the cat-9 audit write), Iteration 11 |
| CM13 — recovery is re-assembly, never restore | RFC-0012 §35; RFC-0002 I-8; §21 | **Yes** (C1: a lost set is rebuilt from Facts, never from a snapshot; memory.py has no restore path) | — |
| CM14 — Context/Memory are visible, exportable, wipable | RFC-0012 §35; RFC-0001 §9.2 | **Yes, as the surface** (C3: list/export/wipe on Context and Memory; the *view* rendered to the Operator is `cli`'s) | `cli`/RFC-0015 (presentation) |
| CM15 — Context/Memory are never the Audit | RFC-0012 §35; RFC-0003 §2.8; RFC-0009 §31; RFC-0004 §9.11 | **Yes** (C1/C3: no audit import; the package never holds or emits the material as a record; the cat-9 record is `core`'s write, Q6) | — |
| CM16 — Context/Memory carry no permissions | RFC-0012 §35; RFC-0004 A8; RFC-0001 §8.2 | **Yes** (C1/C3: no policy/executor import; a credential-like value in Context grants nothing; a boundary test proves no capability) | — |
| SC2 — the default is secret-free | RFC-0009 SC2; RFC-0012 §32; RFC-0004 §4.11 | **Yes** (C2: boundary fail-close; no secret in Context in any form) | — |
| SC3 — no secret enters a Provider View | RFC-0009 SC3; RFC-0010 §11; RFC-0007 T7 | **Yes** (C4: the View is secret-free by construction) | — |
| SC16 — privacy parity | RFC-0009 SC16; RFC-0012 §24 | **Yes** (C2: personal data is secret until an explicit Operator demotion, consumed at the boundary) | `cli`/`core` (demotion collection), Iterations 10–11 |
| PR14 — the View is the only channel | RFC-0010 §13; RFC-0007 T3 | **Yes** (C4: the View is the only outward surface; no Audit, secret, or raw output crosses) | — |
| I-4 — LLM only through a provider view | RFC-0002 §9; RFC-0007 §12 | **Yes, as the surface** (C4: the View is the only representation this layer hands outward; the provider consultation edge is `core`'s) | `core` (§6.2), Iteration 11 |
| I-13 — recorded before the consequence | RFC-0002 §9; RFC-0013 §23; RFC-0004 §9.11 | **Yes, as the event** (C1/C3: the context-boundary event precedes the material's use; the audit write is `core`'s) | `core` (the cat-9 write), Iteration 11 |
| S7 — sanitization is deterministic | RFC-0007 §13; RFC-0012 §12 | **Yes** (C2: identical inputs → identical sanitized output) | — |
| T10 — secrets never appear in any form | RFC-0007 §13; RFC-0009 SC2 | **Yes** (C2/C4: no secret in Context or the View, in any form) | — |

DoD subset (blueprint §8.9): **CM1–CM16, PR14, SC2, CM13** — all
layer-enforceable per the table (CM7/CM8/CM9/CM12 as deterministic mechanics
with the runtime event and audit write recorded against `core`), plus the
blueprint §7 oracle's SC3, SC16, and the enforcement-point mechanism. The
package's blueprint §10 coverage row (`context/*` = RFC-0012, §12, §13, §21,
CM1–CM16/SC2/PR14) is satisfied across the layer + the recorded cross-component
obligations (§1.2).

---

## 9. Ambiguities

Each is **reported, not resolved** here; each names the corpus silence that
forces the report and the RFC/decision that owns the answer. Column
"Blocking?" marks whether it elevates to a blocking question in §10.

| # | Subject scope | RFC §/location | Open question | Alternative readings | Governing RFC / note | Blocking? |
|---|---|---|---|---|---|---|
| A1 | Iteration scope / renumbering | blueprint §8.9; DN-45 | Blueprint §8.9 still reads "Iteration 8 — `context`" while DN-45 re-ordered `context` to Iteration 9 (after `executor` + `audit`). This task implements `context` at Iteration 9; the label is never renumbered (as §8.7/§8.8/§8.8 were). | (a) implement `context` at Iteration 9, recording the supersession as a continuation of DN-45 (b) stop and renumber the blueprint (the blueprint text stands until RFC-0020, the authoritative build order) | DN-45; blueprint §8.9; Iteration 7/8 closeouts | **Yes (Q1)** |
| A2 | Assembly input contract | RFC-0012 §8, §12; RFC-0002 §2.4; RFC-0003 §2.3 | Context Building is a runtime state (RFC-0002 §2.4) whose producers — conversation history (`core`/`providers`), skill material (`skills`/`providers`), the Goal (the Core's, RFC-0003 §2.3), routing state (`core`) — are future iterations and, for providers/skills, forbidden edges. What does `assemble.py` consume so it is deterministic and testable now? | (a) explicit **boundary inputs**: a schema-shaped Goal value, a bounded already-labeled history turn record, sanitized skill material, and the routing-state marker, plus the Fact current set read from `factlayer`; the package performs no I/O and no provider call; the runtime wiring is `core`'s (b) the package reads a live session store or imports the producers (forbidden edges; not testable here) | RFC-0012 §8/§12; RFC-0002 §2.4; RFC-0003 §2.3; Iteration 8 Q1/Q2 (run-primitive + structural-handoff precedent); DN-44 (latent schema edge) | **Yes (Q2)** |
| A3 | Sanitization enforcement point | RFC-0012 §5, §32; RFC-0012 §37 OQ3; RFC-0007 S1–S8 | RFC-0012 §32 says the rule is RFC-0009's and "the mechanics are this RFC's"; §37 OQ3 says the *catalogue* (which treatment for which source) is RFC-0020's. How much mechanism is built now, when SC2/CM4 must hold at this layer (RFC-0004 §4.11)? | (a) the **mechanism now**: `boundaries.py` applies `trust` S1–S8 and the `secrets` classifier fail-closed at the enforcement point (SC2/SC16), with a placeholder-default policy; the concrete per-source catalogue is RFC-0020's (b) defer the enforcement point wholesale to RFC-0020 (would make SC2/CM4/T10 untestable here, violating DN-43's assignment) | RFC-0012 §5/§32/§37 OQ3; RFC-0007 S1–S8; RFC-0004 §4.11; DN-18 (placeholder defaults); DN-43 (SC2 is the owning packages' DoD) | **Yes (Q3)** |
| A4 | Provider View shape | RFC-0010 §3, §11; RFC-0012 §13, §27; RFC-0015 (future); RFC-0020 | RFC-0010 §3 lists the View's elements but says "This RFC does not define its shape — no schemas — but defines its boundary"; the assembly mechanics are RFC-0012's and RFC-0015's (RFC-0010 §15 OQ3), and final signatures are RFC-0020's (DN-1). What does `provider_view.py` build now? | (a) the **derivation/assembly now**: a deterministic, schema-shaped, secret-free View carrying the §3 elements, so PR14/SC3/CM10 are testable here; the *presentation form* (RFC-0015) and final signatures (RFC-0020) deferred (b) defer `provider_view.py` wholesale to RFC-0015 (would leave PR14/SC3/CM10 untested) | RFC-0010 §3/§11; RFC-0012 §13/§27; RFC-0010 §15 OQ3; DN-1; Iteration 8 Q10 (derivation-now precedent) | **Yes (Q4)** |
| A5 | Memory store mechanics | RFC-0012 §7, §22; RFC-0004 §4.11; RFC-0014; RFC-0020 | RFC-0012 §22 makes Memory durable by consent, but storage mechanics, retention, deletion, and what survives a resume are RFC-0014/RFC-0020's (§37 OQ4/OQ5). The scaffold posture has been in-memory with durable mechanics deferred (DN-19/DN-27/DN-34/DN-50/DN-62). What does `memory.py` build now? | (a) an **in-memory consented store now**: the promotion gate (consent + stated purpose), the three §7 categories, list/export/wipe, no-restore (CM13); durable backing/retention/survival deferred to RFC-0014/RFC-0020 (b) a real durable backend now (needs storage mechanics + retention policy, RFC-0014/RFC-0020's) | RFC-0012 §7/§22/§37 OQ4-OQ5; RFC-0001 §9.5; DN-19/DN-27/DN-34/DN-50/DN-62 (in-memory precedent); RFC-0020 | **Yes (Q5)** |
| A6 | Context-boundary audit write | RFC-0013 §7 cat. 9, §23; RFC-0004 §9.11; RFC-0002 I-13; blueprint §4.2 | RFC-0004 §9.11 says "the Audit records what entered Context" and RFC-0013 §7 cat. 9 defines the record — but `context` may NOT import `audit` (blueprint §4.2; CM15), and RFC-0013 §23 says write points are runtime boundaries. Who writes the cat-9 record, and how is I-13 testable here? | (a) **context emits, `core` writes**: `context` produces deterministic boundary events (category, size, identity, entered/destroyed — never the material, SC4-compatible) as outputs; `core` (the runtime boundary) persists them as cat-9 records before the material's use (RFC-0013 §23; I-13) (b) context imports `audit` (forbidden edge) or holds records itself (CM15 violation) | RFC-0013 §7 cat. 9, §23; RFC-0004 §9.11; RFC-0002 I-13; blueprint §4.2; Iteration 8 Q7 (record-before-consequence precedent, inverted because of the forbidden edge) | **Yes (Q6)** |
| A7 | Routing-state scope | RFC-0012 §6 cat. 6, §33; RFC-0002 §2.5/§2.6; RFC-0014 | RFC-0012 §33 answers RFC-0002 Q12 (routing via the outstanding-question marker, supersede-disclose semantics), but the *routing decision* is the runtime's (RFC-0002 §2.5/§2.6) and cross-interrupt persistence is RFC-0014's (§37 OQ4). What does this layer build? | (a) **the category now**: `assemble.py` carries the routing-state marker and implements the supersede-disclose semantics as a deterministic value; the routing transitions are `core`'s; persistence is RFC-0014's (b) defer routing state to `core`/RFC-0014 (would leave the §33 Q12 answer untested) | RFC-0012 §6/§33/§37 OQ4; RFC-0002 §2.5/§2.6, §10 Q12; RFC-0014 | **Yes (Q7)** |
| A8 | Freshness/invalidation events | RFC-0012 §16, §17; RFC-0005 §12; RFC-0002 §4.2 | CM7/CM8 require stale Context to be rebuilt and invalidation to precede use, driven by STATE_CHANGED_DETECTED and freshness lapse (RFC-0002 §4.2; RFC-0005 §12) — events emitted by the runtime. What is this layer's deterministic half? | (a) **deterministic gates + mark-stale function**: assembly excludes Stale/Expired Facts or marks the set Stale; a mark-stale function consumes the state-change/freshness event as an input; the event emission and re-inspection are `core`'s (b) defer CM7/CM8 to `core` (would leave them untested here) | RFC-0012 §16/§17; RFC-0005 §12; RFC-0002 §4.2; Iteration 8 I-8 boundary precedent | **Yes (Q8)** |
| A9 | Context categories in scope | RFC-0012 §6, §8; RFC-0012 §37 OQ5 | RFC-0012 §6 fixes exactly six Context categories; RFC-0012 §34 rule 2 makes adding one an amendment. But only some producers exist now (Facts from `factlayer`; Evidence from `schema.VerificationOutcome`; Goal/history/skill/routing from future iterations). Does this iteration implement all six as types? | (a) **all six categories as types now**: Facts, Goal, History, Evidence, Skill material, Routing state — the ones without producers tested at the boundary with supplied material, so the §6 category closure is fixed before the producers land (b) implement only Facts + Goal now (would leave the §6 closure untested and force a later category amendment) | RFC-0012 §6/§8/§34; RFC-0006 §14 (Evidence forward reference); Iteration 8 Q9 (categories in scope precedent) | **Yes (Q9)** |
| A10 | Evidence category basis | RFC-0012 §6 cat. 4, §26; RFC-0006 §14 (forward reference); RFC-0005 §3 | RFC-0012 §6 category 4 makes Verification Outcomes and evidence Context material "as Facts or labeled evidence, never as verification power", citing RFC-0006 §14 — a forward reference whose owning RFC is not yet written. `schema.VerificationOutcome` exists (Iteration 4). What does the category carry now? | (a) **build on `schema.VerificationOutcome`**: Evidence enters as labeled material carrying the Outcome's canonical form, never as verification power or a decision input; the §14 forward reference's write boundary stays `verification`'s (b) defer Evidence until RFC-0006 §14 is written (would leave category 4 dangling) | RFC-0012 §6 cat. 4, §26; RFC-0006 §14 (forward); RFC-0005 §3; Iteration 8 Q9/Q10 precedent | **Yes (Q10)** |
| A11 | Goal shape at the boundary | RFC-0003 §2.3; RFC-0012 §6 cat. 1; schema/action.py | The Goal is "the Core's" (schema/action.py) and RFC-0003 §2.3 fixes one active Goal per session; `schema` deliberately has no Goal type (RFC-0020 defines signatures, DN-1). What does the assembly consume as the Goal? | (a) a **plain schema-shaped boundary value** (statement + scope) supplied at assembly; a canonical Goal schema is RFC-0020's (b) `context` defines a Goal type (ownership violation — the Goal is the Core's) | RFC-0003 §2.3; RFC-0012 §6 cat. 1; DN-1; RFC-0020 | **Part of Q2** |

---

## 10. Blocking questions

| Q | Question | Owner (RFC §) | Blocks | Sev. | Recommended resolution |
|---|---|---|---|---|---|
| Q1 | Iteration scope / renumbering vs blueprint §8.9 (A1) | DN-45; blueprint §8.9 | C0 | Med | **`context` is Iteration 9.** Implement the context package at Iteration 9 per DN-45's re-order; record the renumbering as a continuation of DN-45's supersession note (as §8.7/§8.8/§8.8 were); the blueprint text stands until RFC-0020 |
| Q2 | Assembly input contract (A2/A11) | RFC-0012 §8/§12; RFC-0002 §2.4; RFC-0003 §2.3 | C1 | High | **Explicit boundary inputs.** `assemble()` consumes a schema-shaped Goal value, the Fact current set from `factlayer` (filtered to relevance + freshness), a bounded already-labeled history record, sanitized skill material, and the routing-state marker — no I/O, no provider call, deterministic and testable; the runtime wiring is `core`'s (Iteration 11), mirroring Iteration 8's run-primitive + structural-handoff precedents |
| Q3 | Sanitization enforcement point (A3) | RFC-0012 §5/§32/§37 OQ3; RFC-0004 §4.11; DN-43 | C2 | High | **Mechanism now, catalogue later.** `boundaries.py` applies `trust` S1–S8 and the `secrets` classifier fail-closed at the enforcement point (SC2/SC16), with a placeholder-default policy (DN-18); the concrete per-source catalogue is RFC-0020's (§37 OQ3). Without it SC2/CM4/T10 are untestable at their enforcement point (DN-43) |
| Q4 | Provider View shape (A4) | RFC-0010 §3/§11; RFC-0012 §13/§27; RFC-0010 §15 OQ3 | C4 | Med | **Derivation now.** `provider_view.py` deterministically derives a schema-shaped, secret-free View carrying the §3 elements so PR14/SC3/CM10 are testable here; the presentation *form* is RFC-0015's and final signatures RFC-0020's (DN-1), mirroring Iteration 8's transcript-derivation-now reading |
| Q5 | Memory store mechanics (A5) | RFC-0012 §7/§22/§37 OQ4-OQ5; RFC-0014; RFC-0020 | C3 | High | **In-memory consented store now.** `memory.py` builds the promotion gate (consent + stated purpose), the three §7 categories, list/export/wipe, and no-restore (CM13); durable backing, retention, deletion, and resume-survival defer to RFC-0014/RFC-0020 (DN-50/DN-62 in-memory precedent) |
| Q6 | Context-boundary audit write (A6) | RFC-0013 §7 cat. 9, §23; RFC-0004 §9.11; RFC-0002 I-13 | C1/C3 | High | **Context emits, `core` writes.** `context` emits deterministic boundary events (category, size, identity, entered/destroyed — never the material) as outputs; `core` persists them as cat-9 records at the runtime boundary before the material's use (RFC-0013 §23; I-13). No `context → audit` edge (CM15; blueprint §4.2) |
| Q7 | Routing-state scope (A7) | RFC-0012 §6/§33/§37 OQ4; RFC-0002 §2.5/§2.6; RFC-0014 | C1 | Med | **The category now.** `assemble.py` carries the routing-state marker and implements the §33 supersede-disclose semantics deterministically (a new question supersedes; the superseded one is disclosed, never silently dropped); the routing transitions are `core`'s; cross-interrupt persistence is RFC-0014's |
| Q8 | Freshness/invalidation events (A8) | RFC-0012 §16/§17; RFC-0005 §12; RFC-0002 §4.2 | C1 | Med | **Deterministic gates + mark-stale function.** Assembly excludes Stale/Expired Facts or marks the set Stale; a mark-stale function consumes the state-change/freshness event as an input; the event emission and re-inspection are `core`'s (Iteration 11), mirroring Iteration 8's I-8 boundary |
| Q9 | Context categories in scope (A9) | RFC-0012 §6/§8/§34; RFC-0006 §14 | C1 | Med | **All six as types now.** Facts, Goal, History, Evidence, Skill material, and Routing state are implemented as types; the ones without live producers are tested at the boundary with supplied material, fixing the §6 closure before the producers land (Iteration 8's Q9 precedent) |
| Q10 | Evidence category basis (A10) | RFC-0012 §6 cat. 4, §26; RFC-0006 §14 (forward) | C1 | Med | **Build on `schema.VerificationOutcome`.** Evidence enters as labeled material carrying the Outcome's canonical form, never as verification power or a decision input; the §14 forward reference's write boundary stays `verification`'s |

**Status: BLOCKED.** Q1–Q10 await Operator ratification. Once ratified, each is
recorded as **DN-65…DN-74** in `docs/implementation-decision-notes.md` before
C0, exactly as Iterations 1–8; the design review §16 readiness flips to READY.

---

## 11. Proposed Decision Notes (DN-65…DN-74)

Proposals for Operator ratification; none took effect by this review. **To be
ratified as DN-65…DN-74 in `docs/implementation-decision-notes.md`** in the
established table form — Status (Ratified, Operator, Iteration 9 ratification) /
Date / Resolves (design review §10 Qn) / Grounding (RFC sections + DN
precedents) / Embodied in (commit) / Decision — mirroring DN-40…DN-64.

| DN | Resolves | Proposal |
|---|---|---|
| DN-65 | Q1 | `context` executes at Iteration 9 per DN-45's re-order; the blueprint §8.9 "Iteration 8 — `context`" label is superseded and stands until RFC-0020 |
| DN-66 | Q2 | `assemble()` consumes explicit boundary inputs — a schema-shaped Goal value, the Fact current set from `factlayer`, bounded labeled history, sanitized skill material, and the routing-state marker — with no I/O and no provider call; the runtime wiring is `core`'s (Iteration 11) |
| DN-67 | Q3 | `boundaries.py` implements the sanitization enforcement point now (`trust` S1–S8 + `secrets` classifier, fail-closed, SC2/SC16) with placeholder-default policy; the concrete per-source catalogue is RFC-0020's (§37 OQ3) |
| DN-68 | Q4 | `provider_view.py` deterministically derives a schema-shaped, secret-free View carrying the RFC-0010 §3 elements (PR14/SC3/CM10 testable here); the presentation form is RFC-0015's and final signatures RFC-0020's (DN-1) |
| DN-69 | Q5 | `memory.py` is an in-memory consented store now — promotion gate (consent + stated purpose), three §7 categories, list/export/wipe, no-restore (CM13); durable backing/retention/survival defer to RFC-0014/RFC-0020 |
| DN-70 | Q6 | `context` emits deterministic context-boundary events (category, size, identity, entered/destroyed, never the material); `core` writes them as RFC-0013 §7 cat. 9 records at the runtime boundary before the material's use (I-13) |
| DN-71 | Q7 | `assemble.py` carries the routing-state marker and implements the RFC-0012 §33 supersede-disclose semantics; routing transitions are `core`'s; cross-interrupt persistence is RFC-0014's |
| DN-72 | Q8 | Assembly enforces deterministic freshness gates (excludes Stale/Expired Facts, marks the set Stale) and a mark-stale function consumes the state-change/freshness event; the event emission and re-inspection are `core`'s |
| DN-73 | Q9 | All six §6 Context categories are implemented as types now (Facts, Goal, History, Evidence, Skill material, Routing state); categories without live producers are tested at the boundary with supplied material |
| DN-74 | Q10 | Evidence enters Context as labeled material built on `schema.VerificationOutcome`, never as verification power; the RFC-0006 §14 forward reference's write boundary stays `verification`'s |

---

## 12. Atomic implementation plan

Each commit is <300 production LOC, single responsibility, test-visible, on a
branch derived from `iteration/8-executor` (`iteration/9-context`). Commit order
follows ratification of the questions it depends on. Est. = estimated LOC
(impl / test / docs). C1–C4 **fill the Iteration 0 scaffold stubs**
(`assemble.py`, `boundaries.py`, `memory.py`, `provider_view.py` already exist
with ownership docstrings; the tree test stays green).

| Commit | Message | Content | Est. (impl/test) | Depends on | Deliverable |
|---|---|---|---|---|---|
| C0 | `docs: ratify Iteration 9 questions Q1–Q10 and context scope` | Decision notes for Q1–Q10 (DN-65…DN-74), design review record, renumbering note (Q1), consistency-report note | — / — / ~800 | Q1–Q10 ratified | Ratified plan; all questions answered |
| C1 | `feat(context): deterministic bounded assembly (RFC-0012 §8, §10–§12, §16, §17; CM1, CM3, CM5, CM6, CM7, CM9, CM10, CM13)` | `assemble.py`: the pure assembly function over the boundary inputs (Q2); fixed composition order (§12); purpose-limit (CM5); size bound + transparent consolidation with a placeholder default (CM6); freshness gates + mark-stale function (CM8); one-Goal working set, no cross-session merge (CM9); rebuild-not-restore (CM13); all six §6 categories as types (Q9); Evidence on `schema.VerificationOutcome` (Q10); routing-state marker + §33 supersede-disclose semantics (Q7); emits deterministic context-boundary events (Q6) | ~280 / ~380 | Q2, Q6, Q7, Q8, Q9, Q10 | Deterministic assembly |
| C2 | `feat(context): secret-free boundary enforcement (RFC-0012 §9, §13, §19, §23, §24, §32; RFC-0009 SC2, SC16; RFC-0007 S1–S8; CM4)` | `boundaries.py`: the sanitization enforcement point — `trust` S1–S8 + the `secrets` classifier applied fail-closed before material enters Context or a View (SC2/SC16, T10); hostile/quarantined excluded; personal data secret until demotion (SC16); placeholder-default policy (Q3); no value crosses | ~180 / ~300 | Q3 | Boundary enforcement |
| C3 | `feat(context): consented Memory (RFC-0012 §7, §18–§22; RFC-0001 §9.2/§9.5; CM2, CM11, CM12, CM14)` | `memory.py`: in-memory consented store — promotion gate (consent + stated purpose, CM11), the three §7 categories (never secret values / raw output / Audit record / private content), list/export/wipe (CM14), no-restore (CM13), never authority (CM2); emits the promotion/destruction boundary events (Q6); durable backing deferred (Q5) | ~180 / ~260 | Q5, Q6 | Consented Memory |
| C4 | `feat(context): the Provider View (RFC-0010 §3, §11; RFC-0012 §13; PR14, SC3, CM10; RFC-0007 §12)` | `provider_view.py`: the deterministic View derivation from the assembled Context — the only outward channel (PR14); carries the §3 elements (Goal, evidence/Allowed Context, Conversation State, routing state) and nothing else; secret-free (SC3), size-bounded, purpose-limited, labeled, disposable (RFC-0007 §12); shape reported, form RFC-0015's, signatures RFC-0020's (Q4) | ~160 / ~260 | Q4 | Provider View builder |
| C5 | `test(context): Layer-4 conformance and CM/SC/PR invariant suite` | Conformance (imports limited to `schema`/`factlayer`/`trust`/`secrets`(classifier)/`systemmodel` + sanctioned stdlib, no I/O/no provider call/no forbidden stdlib, public surface == owned vocabulary, package tree unchanged); invariant tests CM1–CM16, SC2/SC3/SC16, PR14, I-4, S7, T10; boundary tests: SC2 no-token-in-Context/View, SC16 privacy parity, CM4 fail-close, PR14 only-channel, CM5 purpose-refusal, CM6 transparent consolidation, CM7 stale-exclusion, CM8 mark-stale, CM13 no-restore, CM11 no-consent-refusal, I-13 event-before-use; cross-component obligations (state wiring, event emission, the cat-9 audit write, View form, Memory durability) recorded against `core`/RFC-0014/RFC-0015/RFC-0020 | 0 / ~520 | C1–C4 | Conformance oracle |
| C6 | `docs: record Iteration 9 completion and context conformance` | Consistency report + decision notes completion + deferred-items table | — / — / ~220 | C5 | Completion record |

---

## 13. Validation strategy

Same gates as Iterations 1–8: `pytest` (baseline **1965 tests**), `ruff check`,
`ruff format --check`, `python -m build`, and `pre-commit run --all-files`.
Conformance is enforced by the existing `tests/test_dependency_rules.py` (the
`context` row is already declared: `ALLOWED["context"] = {"schema", "factlayer",
"trust", "secrets", "systemmodel"}` and `FORBIDDEN["context"] = {"providers",
"policy", "executor", "audit"}`, plus the `secrets (values)` use restriction and
the forbidden-source rows) and `tests/test_packages.py` (already green — the
four modules exist as stubs), extended by C5's new `test_context_conformance.py`
and the CM/SC/PR invariant suites. Because C0–C6 touch neither `rfc/` nor
`tools/`, the RFC-reference validator is not a gate for this iteration (CI still
runs it; the known pre-existing RFC-0004 §470 `'S1'` error is unrelated and
unchanged). Determinism is asserted by property-style tests: the same Goal +
Facts + history + skill material + routing state + bounds → the same Context and
the same View (RFC-0007 S7); the secret-free property (SC2/SC3) is asserted by
feeding known tokens and verifying they appear nowhere in Context or the View;
the boundary properties (CM4 fail-close, CM5 purpose-refusal, CM6 transparent
consolidation, CM7 stale-exclusion, CM13 no-restore, CM11 no-consent-refusal,
CM14 wipe-complete) are asserted by direct injection.

---

## 14. Definition of Done (per commit)

| Commit | Definition of Done |
|---|---|
| C0 | Q1–Q10 each answered and recorded as decision notes (DN-65…DN-74); the renumbering tension (Q1) recorded; this review's readiness flips to READY |
| C1 | The assembly function is deterministic — same inputs, purpose, and bounds → the same Context (S7, CM6); it consumes only the boundary inputs (Q2) and reads Facts from `factlayer` at their trust class and freshness (RFC-0012 §8); composition order is exactly §12 (Facts first with provenance, Goal and scope, bounded history, skill material last, routing state folded in); it refuses anything without a stated purpose (CM5); overflow consolidates transparently, never silently grows (CM6); Stale/Expired Facts are excluded or mark the set Stale (CM7); the mark-stale function marks and records invalidation (CM8); the working set holds one Goal and never merges across sessions (CM9); a lost set is rebuilt, never restored (CM13); it emits the deterministic context-boundary events (Q6); all six §6 categories are present as types, Evidence on `schema.VerificationOutcome` (Q9/Q10); the routing-state marker and §33 supersede-disclose semantics hold (Q7) |
| C2 | The enforcement point fail-closes secret-shaped values before anything enters Context or a View (SC2/CM4/T10); untrusted text is neutralized and contained (S1–S8); personal data is secret until an explicit demotion (SC16); hostile/quarantined content is excluded (RFC-0012 §9 rule 4); no value crosses the boundary (SC2 construction); sanitization is deterministic (S7); the per-source catalogue is recorded as RFC-0020's (Q3) |
| C3 | The promotion gate refuses any promotion without consent carrying a stated purpose, with no durable artifact (CM11); the three §7 categories are implemented, never secret values / raw output / the Audit record / private content without demotion (SC16); list/export/wipe are complete and irreversible, with no restore path (CM14/CM12/CM13); Memory decides nothing (CM2); promotion/destruction boundary events are emitted (Q6); durable backing is recorded as RFC-0014/RFC-0020's (Q5) |
| C4 | The View is the only outward channel — an instrumentation test proves nothing else exports Context material (PR14/CM10); it carries exactly the §3 elements and nothing else (no Audit, no secrets, no raw output, no provider identity); it is secret-free (SC3), size-bounded, purpose-limited, labeled, and disposable (RFC-0007 §12); the shape is reported, the form RFC-0015's, signatures RFC-0020's (Q4) |
| C5 | Blueprint §7 context row and §8.9 DoD (CM1–CM16, PR14, SC2, CM13) pass; every layer-enforceable invariant in §8 has a test; conformance: imports limited to the declared allowed sets + sanctioned stdlib, no I/O, no provider call, no forbidden stdlib, public surface == owned vocabulary, package tree unchanged; the SC2 no-token, SC16 parity, CM4 fail-close, PR14 only-channel, CM5 purpose-refusal, CM6 consolidation, CM7 stale-exclusion, CM13 no-restore, CM11 no-consent-refusal, and I-13 event-before-use boundary tests pass; cross-component obligations (state wiring, event emission, the cat-9 audit write, View form, Memory durability) recorded against `core`/RFC-0014/RFC-0015/RFC-0020; full suite green |
| C6 | Consistency report reflects Iteration 9; no orphaned decision notes; the deferred-items table names every §1.2 owner |

**Overall DoD (blueprint §8.9):** CM1–CM16 conformance; the Provider View is the
only outward channel (PR14); no secret in Context (SC2); re-assembly on loss
(CM13); `pytest` full suite, `ruff check`, `ruff format --check`, `python -m
build` all green; `tests/test_dependency_rules.py` and `tests/test_packages.py`
still green (tree and edges unchanged).

---

## 15. LOC estimates

| Commit | impl | test | docs | Notes |
|---|---|---|---|---|
| C0 | — | — | ~800 | Ratification |
| C1 | ~280 | ~380 | — | Deterministic assembly |
| C2 | ~180 | ~300 | — | Boundary enforcement |
| C3 | ~180 | ~260 | — | Consented Memory |
| C4 | ~160 | ~260 | — | Provider View builder |
| C5 | 0 | ~520 | — | Conformance + invariants |
| C6 | — | — | ~220 | Closeout |
| **Total** | **~800** | **~1,720** | ~1,020 | |

Production total ≈ **800**; test total ≈ **1,720**. Test LOC may exceed the
300-LOC cap per-commit, as in Iterations 4–8 (the cap applies to implementation
lines). C1 (assembly) and C2 (boundary enforcement) carry the DoD's conformance
weight (CM1–CM10 and SC2/CM4/T10 respectively).

---

## 16. Readiness assessment

**Status: BLOCKED** pending ratification of Q1–Q10 (to be recorded as decision
notes DN-65…DN-74 before C0), exactly as Iterations 1–8 began. The
highest-leverage questions are **Q2** (the assembly input contract that makes
Context Building deterministic and testable without `core`), **Q3** (the
sanitization enforcement point that makes SC2/CM4/T10 hold at their owner), **Q5**
(the in-memory consented Memory that satisfies CM11/CM13/CM14 now with
durability deferred), and **Q6** (the context-boundary audit write that
reconciles RFC-0004 §9.11's "Audit records what entered Context" with the
forbidden `context → audit` edge). Once Q1–Q10 are ratified, the layer is
**READY** and commits execute in order C0→C6, each satisfying its §14 DoD before
the next begins. The dominant residual risk is the Draft status of RFC-0012
itself (§17 risk 1); the layer's load-bearing dependencies are all Accepted,
which bounds it.

---

## 17. Final verdict

This plan is a faithful translation of the frozen corpus into a
context-and-memory-layer scaffold: **no new architecture is proposed**, every
ambiguity is reported and elevated to a blocking question, no RFC is modified,
no module is invented beyond the scaffolded four, the allowed/forbidden
dependency graph is honored, the two authority rows (Observe; Persist under
consent) are observed without overlap, and every layer-enforceable invariant
(CM1–CM16; SC2/SC3/SC16; PR14; I-4; S7; T10) maps to a deterministic mechanism
and a test. The cross-component obligations (the Context Building state wiring,
the STATE_CHANGED_DETECTED event and re-inspection, the history/skill-material
producers, the cat-9 audit write, the View presentation form, the durable Memory
backing) are named against `core`/`providers`/`skills`/RFC-0014/RFC-0015/RFC-0020
rather than dropped. The enforcement halves Iteration 6 recorded (SC2/SC3/SC16
cross-component enforcement) are now DoD items of this iteration (Q3/Q6), not
deferred again. **Pending ratification: Q1–Q10 are to be recorded as
DN-65…DN-74; the layer is READY for C1.**

---

## Consistency review against the Blueprint and governing RFCs

**Consistent.** Module set `context/{__init__,assemble,boundaries,memory,
provider_view}.py` fixed by blueprint §2 (scaffolds already present); dependency
rules (`ALLOWED["context"] = {"schema", "factlayer", "trust", "secrets",
"systemmodel"}`, `FORBIDDEN["context"] = {"providers", "policy", "executor",
"audit"}`, `secrets` classifier-types-only, + stdlib, Layer 4) honored by §3/§5;
one-owner discipline (RFC-0004 §3) honored by §4 and the two-owner checks
(authority vs model; custody vs durability decision; mechanics vs catalogue;
records vs write point); the scaffold gate (blueprint §8.0) stands; DN-45's
re-order is now executed (`context` = Iteration 9); DN-43's SC2/SC16 boundary
assignment is a DoD item (Q3); DN-50/DN-62's in-memory precedent is the Q5
reading; DN-18's placeholder-default precedent is the Q3/Q4 reading; DN-44's
latent-edge precedent is the Q2 reading; RFC-0010 §15 OQ3's assembly ownership
is recorded (§2), with the RFC-0015 form deferred; RFC-0013 §7 cat. 9 and §23
write-point ownership are recorded as `core`'s obligation (Q6), never invoked
here.

**Reported tensions (not violations):**

1. Blueprint §8.9 numbering vs DN-45's re-order — §8.9 still reads "Iteration 8
   — `context`" while this iteration implements it at Iteration 9 (Q1). Needs
   ratification as a continuation of DN-45's recorded supersession.
2. RFC-0012 is Draft; its normative sections 1–35 may change before acceptance —
   the rework risk is accepted (DN posture of Iterations 1–8) and the layer's
   Accepted-RFC dependencies bound it.
3. RFC-0013 is Draft (2026-08-02); its cat. 9 definition and §23 write-point
   wording may change — same accepted rework risk; the cat-9 write is `core`'s
   either way (Q6).
4. RFC-0004 §9.11's "the Audit records what entered Context" vs the forbidden
   `context → audit` edge (Q6) — needs ratification of the context-emits/
   core-writes reading (DN-70), so CM15 and I-13 both hold.
5. RFC-0010 §3's "no schemas — but defines its boundary" vs the View builder
   this layer builds (Q4) — needs ratification of the derivation-now reading
   (DN-68), mirroring Iteration 8's transcript-derivation-now reading (DN-64).
6. RFC-0012 §37 OQ1–OQ3's bounds/catalogue vs this layer's enforcement mechanism
   (Q3/Q8/Q9) — needs ratification of the mechanism-now/values-later readings
   (DN-67/DN-72), mirroring DN-18's placeholder precedent and DN-59's Q5
   reading.
7. RFC-0006 §14's Evidence forward reference (Q10) — the category is built on
   `schema.VerificationOutcome` now (DN-74), with the §14 write boundary staying
   `verification`'s; flagged so RFC-0006's author resolves the forward reference
   against this reading.
8. RFC-0002 §2.4's Context Building is a runtime state with entry/exit
   conditions, while `core` is Iteration 11 — the assembly *function* is here,
   the *state wiring* is `core`'s, recorded in §1.2 (Q2), exactly as RFC-0002
   §2.8/§6.2's consultation edges were recorded for Iteration 8.

**Verdict.** This plan is a faithful translation of the frozen corpus into a
context-and-memory-layer scaffold; no new architecture is proposed, and every
ambiguity that the corpus does not decide is elevated to a blocking question for
ratification rather than resolved here.

**Post-implementation status (Iteration 9 closeout).** C1–C5 implemented and
tested the layer, and this closeout records its completion. The `context`
package (`assemble.py`, `boundaries.py`, `memory.py`, `provider_view.py`)
landed in C1–C4; the conformance suite (`test_context_conformance.py`) and the
CM/SC/PR invariant suite (`test_context_invariants.py`) landed in C5; the
closeout (C6) completes the iteration. **Status: Complete.** The layer is
deterministic, pure, and authority-free as designed — Observe and
Persist-under-consent in `context` — with the §1.2 deferred halves (the Context
Building state wiring, the STATE_CHANGED_DETECTED event and re-inspection, the
history/skill-material producers, the cat-9 audit write, the View presentation
form, the durable Memory backing, and the concrete bounds/catalogue) recorded
against `core`/`providers`/`skills`/RFC-0014/RFC-0015/RFC-0020 in the
consistency report. The full suite is green (2285 tests). The next iteration is
the `providers` + `skills` layer (blueprint §8.10).
