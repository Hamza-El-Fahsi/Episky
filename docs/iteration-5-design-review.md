# Iteration 5 — Design Review (Trust Layer)

> **Document type:** Implementation design review, at the same rigor as
> Iterations 2–4. **Not an RFC, not code.**
> **Read this first:** This document **defines no new architecture, modifies no
> RFC, invents no behavior, and writes no production code.** It translates the
> frozen corpus (RFC-0000–0013, RFC-0021, the decision traceability matrix,
> `docs/architecture-implementation-blueprint.md`, and the ratified
> `docs/implementation-decision-notes.md` DN-1…DN-34) into an implementation
> plan for the **Trust Layer — the `trust` package** (blueprint §8.3, *trust
> half*; DN-7). Where the corpus does not decide something, this document
> **reports** it as an ambiguity or a question; it does not resolve it.
>
> **Status of sources.** RFC-0007 is **Draft** (not Accepted). Per RFC-0003 Part
> II §1.1 Draft RFCs are not normative and must not be relied upon by
> implementation; yet the blueprint (a translation, §0) targets the Drafts'
> *invariants* as the conformance oracle (blueprint §9 #2). Iteration 5 inherits
> Iterations 1–4's posture: it conforms to RFC-0007's Draft wording knowingly,
> accepting the rework risk that a Draft change carries. Blueprint §8.0 gate
> stands — production code begins only after RFC-0015/0019/0020 and the Drafts
> are Accepted; this iteration builds the translation scaffold. The load-bearing
> dependencies this layer rests on — RFC-0001, RFC-0002 invariants 4 and 5, and
> RFC-0004's Trust definition — are all **Accepted**, which bounds the rework
> risk. RFC-0009/RFC-0011/RFC-0012 (which own parts of RFC-0007's §16 surface)
> are Draft and are explicitly not built here (Q5, Q7).
>
> **Scope decision (reported — Q1).** Blueprint §8.6 assigns `secrets`
> (RFC-0009) to Iteration 5; the `trust` half of blueprint §8.3 was deferred by
> DN-7 "to its own iteration". This task's scope implements `trust` at Iteration
> 5, postponing `secrets`. The re-order is dependency-safe — `trust` is Layer 1
> (blueprint §4.1) and `secrets` imports it — but it changes the roadmap's
> iteration numbering and defers the RFC-0009 boundary work (blueprint §8.6,
> Risk #9). The re-order requires ratification before C0 (Q1).

---

## 1. Scope

### 1.1 Scope (blueprint §8.3, *trust half*, transcribed)

| Item | Value |
|---|---|
| Goal | The trust spine |
| Work | Trust classes (T-classes and lattice), sanitizer (S1–S8), Hostile quarantine |
| Definition of Done | Sanitize-never-upgrades tests (T9); fail-to-Hostile tests (T11/T12) |
| RFC basis | RFC-0007 §10, §11, §15 |

Blueprint §7 (test oracle) does not carry a `trust` row; the package-level
conformance row for `trust` lives in blueprint §5 (the Layer-1 matrix). The §8.3
*Work* wording reads "trust classes T1–T12, sanitizer S1–S8, Hostile
quarantine". Per RFC-0007 the invariant families are structured as follows; the
blueprint's "T1–T12" label is a shorthand for *the T-classes + the trust
invariants*, and the wording tension is already resolved by RFC-0007 itself
(§5 = classes, §13 = invariants) — reported, cosmetic (§7).

### 1.2 Out of scope (recorded, not dropped)

Each of these is owned elsewhere and is **not** built in Iteration 5:

| Item | Owned by | Blueprint gate |
|---|---|---|
| Provider View construction and assembly | RFC-0012 §12; `context`, Iteration 8 | blueprint §8.9 |
| Exact sanitization mechanics (control-strip tables, Unicode taming, summarization algorithms) | RFC-0012 §16.1; `context` | RFC-0007 §16.1; Q5 |
| Output-size bounds | RFC-0005 §16.2 | RFC-0007 §16.2 |
| Redaction mechanics and the Secure Store interface | RFC-0009 §16.3, §11; `secrets` (Iteration 5, per Q1) | blueprint §8.6 |
| Hostile *presentation* to the Operator | RFC-0015; `cli` | RFC-0007 §16.4 |
| Skill-metadata trust | RFC-0011 §4, §22, §23; `skills` | RFC-0007 §16.5; blueprint §8.10 |
| Detection stance (positive adversarial-signal detection) | RFC-0012 §16.6; `context` | RFC-0007 §16.6; Q7 |
| Secret/secret-adjacent classification | RFC-0009 §6.10; `secrets` | RFC-0007 §6.10; Q2 |
| Trust-upgrade wiring into `factlayer`/`verification` | RFC-0005 (Observation→Fact), RFC-0006 (confirmation) | T6; Q4 |
| Durable audit recording of a Hostile admission | RFC-0013 §7–§22; `audit`, Iteration 7 | RFC-0002 invariant 13; Q8 |
| Signatures / package naming | RFC-0020 (future) | DN-1 |

### 1.3 Ownership (package owner)

`trust` is owned by RFC-0007 — one owner per row, no delegation (RFC-0004 §3;
blueprint §10). Module-level ownership:

| Module | Owning RFC sections | Protected by |
|---|---|---|
| `trust/classes.py` | RFC-0007 §4, §5, §6, §9 | T1–T12 (conformance oracle) |
| `trust/sanitize.py` | RFC-0007 §10, §11 | S1–S8; T8, T9 |
| `trust/hostile.py` | RFC-0007 §15 | T11, T12; RFC-0002 invariants 4, 5 |

**Two-owner check.** `hostile.py`'s Hostile class is touched by RFC-0009
(secrets classify *to* Hostile) and by RFC-0007 — the *class and quarantine
semantics* are RFC-0007's; RFC-0009's classifier merely *produces* that class as
an outcome of its own classification. Distinct properties, distinct owners (the
blueprint's precedent: `executor` = RFC-0004 profile + RFC-0002 state). T6's
promotion is likewise split: the *trust rule* is RFC-0007's, the *mechanism* is
RFC-0005/RFC-0006's.

### 1.4 Authority boundaries

The authority matrix (RFC-0004 §7) grants the `trust` package **no authority** —
no F cell. It is an information-handling layer, like `systemmodel`. It holds
none of Observe/Propose/Approve/Execute/Act; it classifies, labels, and
quarantines data, and it must never be the LLM's or a Skill's assessment (its
classification is deterministic). Because it holds no authority, nothing in this
layer can "grant" trust to a datum; at most it *records* the trust class a datum
already has per RFC-0007's rules. This is a boundary fact the tests must
preserve (no path that upgrades outside the two named mechanisms, Q4).

---

## 2. Architectural review

### 2.1 Package ownership (blueprint §3, transcribed)

| Package | Owner | Responsibility |
|---|---|---|
| `trust` | RFC-0007 | Trust classes T1–T12 (§10), sanitization S1–S8 (§11), Hostile quarantine and fail-closed failure behavior (§15) |

Consumed by **every** boundary toward the LLM, the Operator terminal, and any
interpreter (RFC-0007 §1); it is built with no consumers today, exactly like
`systemmodel` in Iteration 2.

### 2.2 Module set (fixed)

One package, four modules — **fixed** by blueprint §2 and
`tests/test_packages.py::test_tree_matches_blueprint_exactly`:

| Module | Responsibility |
|---|---|
| `trust/__init__.py` | Package facade; exports the public surface |
| `trust/classes.py` | Trust classes, lattice, classification (RFC-0007 §5, §6, §9) |
| `trust/sanitize.py` | Deterministic sanitization primitives (RFC-0007 §10, §11) |
| `trust/hostile.py` | Hostile quarantine, fail-closed behavior (RFC-0007 §15) |

Adding or renaming a module breaks the tree test.

### 2.3 Allowed imports

`ALLOWED["trust"] = {"schema"}` (blueprint §4.1) plus the sanctioned stdlib
subset. The `trust → schema` edge may be **used** (classification over
`schema.Fact`, Q3a) or remain **latent** (classification over an abstract
datum, Q3b) — this is the same situation the `verification → systemmodel` edge
held in Iteration 4. Whether the edge is exercised is a ratification matter
(Q3), not an architecture change: the edge is already declared.

### 2.4 Forbidden imports

Everything not in `ALLOWED["trust"]`: `systemmodel` (Layer-1 sibling — no
cross-sibling import), `collectors`, `factlayer`, `verification`, `secrets`,
`policy`, `context`, `providers`, `skills`, `audit`, `executor`, `core`, `cli`.
None of these exist yet (with the partial exceptions of `systemmodel`,
`verification`, `factlayer`, `secrets`, `policy`), and `trust` must not
anticipate them. Enforced by `tests/test_dependency_rules.py` (the allowed-graph
test covers the trust row transitively; no FORBIDDEN row is needed).

### 2.5 Layer placement

Layer 1 (blueprint §4.1), beside `systemmodel`. Neither Layer-1 sibling imports
the other. `trust` is a leaf: everything that will consume it (collectors,
factlayer, secrets, policy, context, providers, skills, core, cli) sits at
higher layers and does not yet exist. The downward edge `schema → trust` never
exists (schema is Layer 0).

### 2.6 Acyclicity and single-typing

No cycle: all edges point downward. Each type is defined in exactly one module:
`TrustClass` and the classification/result records in `classes.py`, sanitizer
results in `sanitize.py`, the quarantine record in `hostile.py`. No type is
shared or re-defined across modules; the sanitizer result carries the trust
class (as a value, from `classes.py`) rather than re-declaring it (Q6).

---

## 3. RFC traceability

| RFC | Section | Implemented as | Status in layer |
|---|---|---|---|
| RFC-0007 | §5 Trust Classes | `TrustClass`: Trusted > Conditional > Untrusted > Hostile; §5.1 meet/join (most-restrictive wins) | Implemented (C1) |
| RFC-0007 | §6 Information Categories | Category vocabulary + default-posture data | Per Q2 |
| RFC-0007 | §8 Trust Promotion | Declared-only rule: the only upward moves are Observation→Fact (RFC-0005) and Verification confirmation (RFC-0006); no promotion path in this package | Per Q4 |
| RFC-0007 | §9 Trust Demotion | Deterministic downgrade operations; reason preserved; provenance loss downgrades (§9.6) | Implemented (C1) |
| RFC-0007 | §10 Prompt Injection Model | Two-channel containment model as the sanitizer's contract; no detection | Implemented (C2) |
| RFC-0007 | §11 Sanitization | S1–S8 as deterministic primitives; S5 (no secret through sanitization) enforced as a boundary test, mechanics owned by RFC-0009 | Per Q5/Q6 |
| RFC-0007 | §13 T1–T12 | Conformance oracle; T8/T9/T11/T12 enforced in this layer; the remainder are construction/execution-side and enforced elsewhere | Oracle (C4) |
| RFC-0007 | §15 Failure Behaviour | Fail-closed to Hostile; quarantine; disclosure/withheld semantics | Implemented (C3) |
| RFC-0002 | invariants 4, 5 | Made *testable* at the sanitize/containment layer; runtime enforcement is `core`'s | Test-visible (C3/C4) |
| RFC-0004 | §2 Trust (definition) | The layer operationalizes the definition; adds no authority | Implemented (C1) |

**Already resolved by the corpus (not re-opened here):**

- The trust-class **set** is exactly four values — Trusted, Conditional,
  Untrusted, Hostile — with the ordering Trusted > Conditional > Untrusted >
  Hostile (RFC-0007 §5). Not a question.
- **Meet/join semantics**: the meet (most restrictive) dominates; the join is
  the least restrictive of the two (§5.1). A Conditional and an Untrusted datum
  meet at Untrusted. Not a question.
- **Sanitization never upgrades**: a sanitized datum stays at its input class or
  drops to Hostile; never up (T9, S1, §11.4). Not a question — enforced in C4.
- **Fail-closed direction**: failure → Hostile (T11, S6, §15.5). Not a question.
- **No secret may pass through sanitization** (S5): the layer's sanitizer
  asserts this as an invariant boundary; the *redaction mechanics* are RFC-0009
  (`secrets`). Not a question.
- **Provider View ownership**: RFC-0012 §12/§16, `context`, Iteration 8. The
  trust layer must not build a Provider View. Not a question.
- **Signatures**: RFC-0020's, not invented here (DN-1). Not a question.

---

## 4. Public surface

The planned public surface is **reported**, not ratified; final signatures are
RFC-0020's (DN-1). The shape below is what C1–C3 will build.

`trust/classes.py`

- `TrustClass` — four-member enum (Trusted, Conditional, Untrusted, Hostile).
- `meet(a, b)` / `join(a, b)` — lattice operations, most-restrictive rule.
- `downgrade(class, reason)` — deterministic demotion, reason preserved.
- Classification entry: `classify(datum)` → a `Classification` record (trust
  class + label/reason + provenance state). The concrete input type (schema.Fact
  vs abstract datum) is Q3.
- Category/domain vocabulary + default postures (RFC-0007 §4, §6) — per Q2.
- Promotion: absent or declared-only — per Q4.

`trust/sanitize.py`

- Sanitization entry (name per RFC-0020) → a `Sanitization` record: sanitized
  text + class (unchanged or Hostile) + status + provenance/label + reason.
- `SanitizationStatus` — OK / FAILED (FAILED → Hostile).
- Neutralization primitives for control characters, ANSI escapes, and Unicode
  taming (S3); quoting/labeling of contained form (S4); bounding/truncation
  (S8). Concrete algorithm scope — per Q5.

`trust/hostile.py`

- Quarantine record: the datum + class + reason + withheld/disclosed state.
- Admission/exclusion semantics and the excluded-from-Context/Provider-View
  invariant (RFC-0007 §15.5) — in-memory only, per Q8.

Nothing else is exported. The facade re-exports only the owned vocabulary.

---

## 5. Ambiguities and blocking questions

Per Iterations 2–4, ambiguities are **reported**, never resolved here; each is
ratified as a decision note before its commit begins. Each question names its
owning RFC, why it blocks, and the possible interpretations. The recommended
reading is marked, mirroring how DN-8–DN-34 were settled.

**Q1 — Iteration scope and roadmap re-ordering.** Blueprint §8.6 assigns
`secrets` (RFC-0009) to Iteration 5; this task's scope implements `trust`
(blueprint §8.3 trust half, deferred by DN-7), postponing `secrets`. The re-order
is dependency-safe (`trust` Layer 1; `secrets` imports it), but the blueprint's
Risk #9 (secret leakage at the Context/Provider join) was mitigated by "secrets
precedes context (Iteration 8)", which the postponement does not break. Owning
documents: blueprint §8.3/§8.6; DN-7; RFC-0009 §16.3 (redaction consumes
RFC-0007 sanitization). **Blocks: every commit.** Interpretations: (a) trust now,
secrets next (as scoped); (b) defer trust again to preserve blueprint numbering.
**Recommended: (a)**, ratified as a decision note (DN-7 precedent).

**Q2 — `classes.py` surface: categories and domains in scope?** RFC-0007 §4
defines twelve trust domains with default postures; §6 defines twelve
information categories each with a default trust class. Does `trust/classes.py`
enumerate `TrustDomain`/`TrustCategory` as vocabulary + default-posture data
(like `systemmodel`'s platform table), or only the four-class `TrustClass` +
lattice operations, leaving category/domain semantics to consumers (factlayer
for Facts, secrets for secrets, skills for skills)? Note several categories'
mechanics are owned elsewhere (§6.10 secrets → RFC-0009; §16.5 skills →
RFC-0011; §16.2 size → RFC-0005). Owning documents: RFC-0007 §4, §6, §6.10.
**Blocks: C1.** Interpretations: (a) full 12+12 vocabulary as data; (b) TrustClass
+ lattice only; (c) the categories whose mechanics are not yet owned as data, the
owned-elsewhere categories deferred. **Recommended: (c)**.

**Q3 — Classification input: what is a "datum"?** To classify, what does the
classifier operate on: a `schema.Fact` (importing `schema`, using the declared
edge), a raw string, or an abstract datum record (category + content +
provenance state + origin domain)? Does classification require the origin
`TrustDomain` as an input (RFC-0007 §4: every datum originates in exactly one
domain)? Owning documents: RFC-0007 §4/§5/§6; blueprint §4.1 (trust→schema edge).
**Blocks: C1, C4.** Interpretations: (a) operate on schema types (edge used); (b)
operate on an internal abstract datum (edge latent); (c) a general entry plus a
`schema.Fact` adapter. **Recommended: (b)** — it keeps the layer type-free, the
same choice that kept `verification → systemmodel` latent in Iteration 4.

**Q4 — Promotion (T6): declared-only or absent?** The only upward moves are
Observation→Fact (RFC-0005, Iteration 6) and Verification confirmation
(RFC-0006, Iteration 4). Neither has a `trust` consumer today (DN-13 excluded
the trust→factlayer edge in Iteration 3). Does `classes.py` expose a narrow
declared upgrade path (unused until factlayer/verification consume it), or no
upgrade operation at all — with "the only upgrades are the two named paths"
held as a documented invariant + test? Owning documents: RFC-0007 §8, T6;
RFC-0005; RFC-0006. **Blocks: C1.** Interpretations: (a) no upgrade operation;
the rule lives as an invariant test; (b) a declared `promote()` guarded to the
two paths, with no caller. **Recommended: (a)** — no dead code, and the
invariant is enforced where it is decided.

**Q5 — Sanitizer scope vs RFC-0012's ownership.** RFC-0007 §16.1 makes the
exact sanitization mechanics (control-strip tables, Unicode taming, escaping,
summarizing) RFC-0012's/Context Manager's; blueprint §8.3 DoD and §5 contract
require a sanitizer now. How much concrete behavior does `sanitize.py`
implement — only the S3-named neutralization primitives (control/ANSI/Unicode)
plus quoting/labeling (S4) and bounding (S8), with summarization algorithms,
Provider-View assembly, and detection deferred — or only a deterministic
interface + test harness with all mechanics deferred? Owning documents: RFC-0007
§11, §16.1, §16.6; RFC-0009 §16.3; RFC-0012 (future). **Blocks: C2.** 
Interpretations: (a) implement the concrete S3 neutralization primitives now
(they are the invariant-bearing core of the §8.3 DoD); (b) interface-only,
mechanics deferred to RFC-0012. **Recommended: (a)**.

**Q6 — Sanitize result contract.** What does sanitize() return? Sanitized text
is still Untrusted and still carries provenance (S1, T8); failure → Hostile (S6,
T9); never upgrades. A bare-string return would lose the label → breaks T8's
"label travels with text". The concrete carrier: a record (sanitized text +
class + status + provenance/label + reason), mirroring Iteration 4's
`OutcomeRecord` (DN-34). Owning documents: RFC-0007 §11 S1/S6, §13 T8/T9, §15.6;
RFC-0002 invariant 10. **Blocks: C2.** Interpretations: (a) rich result record;
(b) plain string + separate classification (breaks T8). **Recommended: (a)**.

**Q7 — Hostile production paths in this layer.** Within the trust layer, Hostile
is reachable only by: unclassifiable → Hostile (T11, §15.5); sanitization
failure → Hostile (S6, T9); provenance loss → Untrusted or Hostile (§9.6).
Detection of a *positive adversarial signal* (§5) is RFC-0012's stance (§16.6).
Confirm: this layer implements no detection heuristics; Hostile is produced only
by the fail-closed/neutralization-failure paths. Owning documents: RFC-0007 §5,
§9.6, §15, §16.6; RFC-0012. **Blocks: C2/C3.** Interpretations: (a) no detection
(containment-only, per §16.6); (b) minimal structural signals passed in by a
detector owned elsewhere. **Recommended: (a)** — detection is explicitly not
this layer's stance.

**Q8 — Quarantine container scope.** RFC-0007 §15.5: quarantined content is
excluded from Context and Provider View and disclosed; §15.8: an injection
attempt is *recorded* (RFC-0002 invariant 13). Does `hostile.py` implement an
in-memory quarantine record (the datum + reason + withheld/disclosed state + the
excluded-from semantics as an invariant), with durable recording deferred to
RFC-0013/`audit` (Iteration 7, DN-34 precedent)? Owning documents: RFC-0007
§15.5–§15.8; RFC-0013; RFC-0002 invariant 13. **Blocks: C3.** Interpretations:
(a) in-memory record only; (b) also write an audit placeholder (would violate
no-persistence-before-RFC-0013). **Recommended: (a)**.

---

## 6. Atomic implementation plan

Each commit is <300 production LOC, single responsibility, test-visible, on
`iteration/5-trust`. Commit order follows ratification of the questions it
depends on. EST. = estimated LOC (impl / test / docs).

| Commit | Message | Content | Est. (impl/test) | Depends on | Deliverable |
|---|---|---|---|---|---|
| C0 | `docs: ratify Iteration 5 questions Q1–Q8 and trust scope` | Decision notes for Q1–Q8 (DN-35…), design review record, consistency-report note | — / — / ~790 | Q1–Q8 ratified | Ratified plan; all questions answered |
| C1 | `feat(trust): trust-class lattice and classification (RFC-0007 §5, §6, §9)` | `TrustClass` enum; meet/join; `downgrade` (reason-preserving); classification entry + `Classification` record; category/domain data per Q2; promotion per Q4 | ~210 / ~260 | Q2, Q3, Q4 | Lattice + classification |
| C2 | `feat(trust): deterministic sanitization primitives (RFC-0007 §10, §11)` | Control/ANSI/Unicode neutralization; quoting/labeling; bounding/truncation; fail-closed; result record per Q6; never-upgrades | ~230 / ~320 | Q5, Q6, Q7 | Sanitizer |
| C3 | `feat(trust): Hostile quarantine and fail-closed behaviour (RFC-0007 §15)` | In-memory quarantine record; admission/exclusion; withheld/disclosed; contagion-down | ~130 / ~220 | Q7, Q8 | Hostile quarantine |
| C4 | `test(trust): Layer-1 conformance and T-invariant suite` | Conformance (allowed imports only stdlib+schema, no I/O at import, no forbidden stdlib, public surface == owned vocabulary, frozen/slotted, no top-level logic, package tree, schema never imports trust); invariant tests T8/T9/T11/T12 + meet rule + fail-closed + S5 boundary | 0 / ~360 | C1–C3 | Conformance oracle |
| C5 | `docs: record Iteration 5 completion and trust conformance` | Consistency report + decision notes completion | — / — / ~200 | C4 | Completion record |

Production total ≈ **570**; test total ≈ **1,160**. Test LOC may exceed the
300-LOC cap per-commit, as in Iteration 4 C3 (1,030 test lines); the cap applies
to implementation lines.

---

## 7. Definition of Done (per commit)

| Commit | Definition of Done |
|---|---|
| C0 | Q1–Q8 each answered and recorded as decision notes; scope re-order ratified; this review's readiness flips to READY |
| C1 | `TrustClass` has exactly four members in the §5 order; meet/join tables correct (most-restrictive); `downgrade` is monotonic and reason-preserving; unclassifiable → Hostile (T11); promotion absent or declared-only per Q4; no authority granted |
| C2 | S1: never upgrades (T9); S3: content preserved through neutralization; S4: output is a contained, labeled form; S6: failure → Hostile; S7: deterministic (same input, same output); S8: bounding applied; T8: label travels with text; S5: no secret passes — enforced as a boundary test |
| C3 | T11: fail-closed; T12: suspicion is contagious *downward*; §15.5: quarantined datum excluded from Context/Provider-View semantics; §15.6/§15.7: the boundary holds closed; nothing persisted |
| C4 | Blueprint §5 Layer-1 trust row and §8.3 DoD (sanitize-never-upgrades; fail-to-Hostile) pass; every layer-enforceable T-invariant has a test; full suite green |
| C5 | Consistency report reflects Iteration 5; no orphaned decision notes |

**Overall DoD (blueprint §8.3):** sanitize-never-upgrades tests (T9) and
fail-to-Hostile tests (T11/T12) pass; `pytest` full suite, `ruff check`, `ruff
format --check`, `python -m build` all green; `tests/test_dependency_rules.py`
and `tests/test_packages.py` still green (tree and edges unchanged).

---

## 8. Validation strategy

Same gates as Iterations 1–4: `pytest` (baseline 632 tests), `ruff check`,
`ruff format --check`, `python -m build`, and `pre-commit run --all-files`.
Conformance is enforced by the existing `tests/test_dependency_rules.py` and
`tests/test_packages.py`, extended by C4's new `test_trust_conformance.py` and
`test_trust_invariants.py`. Because C0–C5 touch neither `rfc/` nor `tools/`, the
RFC-reference validator is not a gate for this iteration (CI still runs it; the
known pre-existing RFC-0001 S1 error is unrelated to this iteration).

---

## 9. Risk assessment

| # | Risk | Grounding | Severity | Mitigation |
|---|---|---|---|---|
| 1 | RFC-0007 is Draft; T-invariants/S-principles may change → rework | RFC-0003 Part II §1.1; blueprint §9 #2 | High | This layer rests on Accepted RFC-0001/0002 (invariants 4, 5)/0004 §2; conformance re-run at each Draft revision; no production dependence on Draft wording until acceptance |
| 2 | Sanitization theater — the sanitizer mistaken for safety itself (T1/T2 hold regardless of sanitizer quality) | RFC-0007 §13; blueprint §9 | Medium | T1/T2 are construction/execution-side invariants, enforced at `core` (Iteration 10); the layer's docs and tests state clearly that sanitization is containment, not a trust grant |
| 3 | Label drift — T8's "label travels with text" broken by a bare-string sanitize result | RFC-0007 §13 T8; Q6 | Medium | Result record carries class + provenance (Q6); C2 tests assert the label survives |
| 4 | Boundary creep toward RFC-0012 mechanics (summarization, detection) | RFC-0007 §16.1/§16.6; Q5/Q7 | Medium | Commits implement only the S3-named primitives; RFC-0012-owned behavior deferred and named in §1.2 |
| 5 | Hostile over/under-labeling | RFC-0007 §15 | Medium | Fail direction is *toward* Hostile (T11); T12 makes suspicion contagious downward, the safe side |
| 6 | Signature invention before RFC-0020 | DN-1 | Medium | Surface reported in §4 is provisional; final naming is RFC-0020's |
| 7 | Redaction leaking into this iteration | RFC-0009 §16.3; blueprint §8.6 | Medium | S5 asserted as a boundary test only; mechanics belong to `secrets` (per Q1) |
| 8 | Cross-package wiring (e.g., promoting into factlayer/verification) before ratification | T6; DN-13 | Medium | Q4; no promotion path or caller in this layer without a ratified consumer |

---

## 10. Readiness verdict

**Status: BLOCKED** pending ratification of Q1–Q8 (recorded as decision notes
before C0), exactly as Iterations 1–4 began. The highest-leverage questions are
**Q5** (sanitizer scope vs RFC-0012), **Q3** (datum type and the `schema` edge),
and **Q7** (Hostile production paths). Once Q1–Q8 are ratified, the layer is
**READY** and commits execute in order C0→C5, each satisfying its §7 DoD before
the next begins.

---

## Consistency review against the Blueprint and governing RFCs

**Consistent.** Module set `trust/{__init__,classes,sanitize,hostile}.py` fixed
by blueprint §2; dependency rules (`ALLOWED["trust"] = {"schema"}` + stdlib,
Layer 1) honored by §2.3–§2.5; one-owner discipline (RFC-0004 §3) honored by
§1.3; the scaffold gate (blueprint §8.0) stands; DN-7's deferral is now
executed; DN-1 (signatures) honored; DN-13 (no trust→factlayer edge) honored in
Q4.

**Reported tensions (not violations):**

1. Blueprint §2 writes "trust classes T1–T12 (§10)" — RFC-0007 §10 is the
   sanitization/principles section and T1–T12 are §13 invariants. Already
   resolved by RFC-0007 itself; cosmetic (§1.1).
2. Blueprint §8.6 vs this task's scope re-ordering (Q1) — needs ratification.
3. Blueprint §8.3 DoD requires a sanitizer now while RFC-0007 §16.1 defers
   mechanics to RFC-0012 (Q5) — needs ratification.

**Verdict.** This plan is a faithful translation of the frozen corpus into
trust-layer scaffold; no new architecture is proposed, and every ambiguity is
elevated to a blocking question. Proceed to ratification.
