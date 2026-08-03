# Iteration 1 — Design Review

> **Document type:** Implementation design review, not an RFC.
> **Read this first:** This document **defines no new architecture, modifies no
> RFC, invents no behavior, and writes no production code.** It translates the
> frozen corpus (RFC-0000–0013, RFC-0021, the two walkthroughs, the decision
> traceability matrix, and `docs/architecture-implementation-blueprint.md`) into
> an implementation plan for Iteration 1 — the `schema` package. Where the
> corpus does not decide something, this document **reports** it as an
> ambiguity or a question; it does not resolve it.
>
> **Status of sources.** RFC-0005 and RFC-0006 are **Draft** (not Accepted);
> RFC-0003 is Accepted. Per RFC-0003 Part II §1, Draft RFCs are not normative
> and must not be relied upon by implementation — yet the blueprint (itself a
> translation, §0) targets the Drafts' *invariants* as the conformance oracle
> (blueprint §0, §9 #2). Iteration 1 therefore conforms to Draft invariants
> knowingly, accepting the rework risk that a Draft change carries (blueprint
> §9 #2). This is the blueprint's own stated posture; this review inherits it.

---

## 1. Scope of Iteration 1

Blueprint §8.2 defines Iteration 1 as **the `schema` package only**.

| Item | Value |
|---|---|
| Goal | Canonical types as the shared vocabulary |
| Work | Fact/Action/Step/Proposal/Plan/Outcome types; conformance tests for F1–F3, F10 |
| Definition of Done | Type-level invariant tests pass; `schema` has **zero imports beyond stdlib** |
| RFC basis | RFC-0005 §3–§5, §12; RFC-0003 §2; RFC-0006 §7 |

Scope boundary: Iteration 1 produces **types and their type-level conformance
tests only**. It produces no normalization logic, no collection, no
verification, no serialization, no policy, and no runtime behavior. It is the
translation scaffold for the shared vocabulary (blueprint §8.0: iterations
0–10 build scaffold + conformance, not the product).

**Gate posture.** Iteration 1 does not write production code: the types it
defines are the canonical vocabulary made concrete, which the blueprint
explicitly assigns to the scaffold (blueprint §2 `schema` row, §6.2, §8.2).
Production begins only after RFC-0015/0019/0020 and the Drafts are Accepted
(blueprint §8.0, §8.12; RFC-0000 §5).

---

## 2. Which RFC sections are implemented

Iteration 1 implements the *type surfaces* named by these sections. **Type
surface** here means: the canonical types and enumerations that express the
section's vocabulary, with no behavior. Exact constructor and method
signatures are RFC-0020's to define (blueprint §5, §11.2 #4) and are **not**
specified by this review.

| RFC | Section | Implemented as (type surface) |
|---|---|---|
| RFC-0005 | §3 Canonical Fact | The `Fact` type composing Identifier, Subject, Property, Value, Status, Confidence Source, Timestamp, Collector, Provenance, Freshness, Machine Identity, Scope |
| RFC-0005 | §4 Fact Status | The `FactStatus` enumeration — Observed, Verified, Unknown, Unavailable, Unsupported, Contradicted, Stale, Invalid |
| RFC-0005 | §5 Provenance | The `Provenance` type answering where / who / when / how / reproducible |
| RFC-0005 | §12 Freshness | The `Freshness` type: freshness bound + freshness state (Current, Possibly stale, Stale, Expired, Unknown freshness) |
| RFC-0003 | §2.6 | The `Action`, `Step`, `Proposal`, `Plan` types |
| RFC-0006 | §7 Outcome model | The `Outcome` vocabulary (see §16 for a reported enumeration inconsistency) |
| RFC-0005 | §13 F1–F3, F10 | **Conformance tests only** (type-level enforcement of never-LLM-authored, no-permissions, never-executes, mandatory provenance) |

Supporting types needed to express the above without importing other packages
(RFC-0005 §3, §11): `Subject`, `Property`, `Value`, `ConfidenceSource`,
`Collector` identity, `MachineIdentity` (opaque), `Scope`, `FactCategory`
(see §16 for the RFC-0021 binding ambiguity), and a reference to the
`Observation` that produced the Fact (see §16, ambiguity 6).

---

## 3. Which RFC sections are intentionally NOT implemented

Iteration 1 deliberately leaves the following to later iterations or to RFCs
that own them. None is silently dropped; each is recorded here.

| RFC | Section | Why not implemented now | Deferred to |
|---|---|---|---|
| RFC-0005 | §2 Observation→Fact pipeline (Raw Output, Observation, Normalization) | Behavior; needs Collectors + normalization; `Observation` type ownership is ambiguous (§16 #6) | Iteration 3 (`factlayer` + `collectors`) |
| RFC-0005 | §6 Fact Identity (same-claim/supersede/contradict) | Comparison behavior; not a type | Iteration 4 (`verification`), factlayer |
| RFC-0005 | §7 Fact Lifetime | Behavior (creation/update/retirement) | Iteration 3 |
| RFC-0005 | §8 Fact Relationships | Behavior + relationship set | Iteration 3 |
| RFC-0005 | §9 Evidence Sets | Unit of travel, built by factlayer | Iteration 3 |
| RFC-0005 | §10 Fact Categories (data) | Categories map to RFC-0021 vocabulary; schema must not import `systemmodel` (DoD). See §16 #4 | Iteration 2 (`systemmodel`) |
| RFC-0005 | §11 Machine Identity contents | Contents owned by RFC-0014 (does not exist); schema carries an opaque identity only | RFC-0014 |
| RFC-0005 | §12 Freshness bound *values* | Concrete staleness windows are policy content | RFC-0020 |
| RFC-0005 | §13 F4–F9, F11–F16 | Behavioral conformance, enforced when behavior lands | Iterations 3–4 |
| RFC-0003 | §2.5 Post-condition | `Step` references it; the *type* ownership is ambiguous (§16 #5) | RFC-0006 / Iteration 4 |
| RFC-0006 | §1–§6, §8–§12, V1–V16 (except §7 vocabulary) | Compare/Outcome determination behavior | Iteration 4 |
| RFC-0006 | §12 Verification Confidence | Not in Iteration 1's RFC basis | Iteration 4 |
| RFC-0000 | §4 (RFC-0020 build units) | Build order is RFC-0020's to ratify | RFC-0020 |
| RFC-0002 | invariants 1–15 enforcement | Runtime behavior | Iteration 10 (`core`) |

---

## 4. Complete package list affected

| Package | Change in Iteration 1 |
|---|---|
| `schema` | **The only package implemented in Iteration 1.** `fact.py`, `action.py`, `outcome.py` gain their type surfaces and enums. |
| `systemmodel`, `trust`, `collectors`, `factlayer`, `verification`, `secrets`, `policy`, `executor`, `audit`, `context`, `providers`, `skills`, `core`, `cli` | **No change.** They are Iteration 1's *future importers* of `schema`, but none is built or modified here (blueprint §8.3–§8.11). |

No new package is created. The module set `schema/{__init__,fact,action,outcome}`
already exists from Iteration 0 (verified by `tests/test_packages.py`).

---

## 5. Public interfaces to be introduced

Blueprint §5 states the RFCs specify **behavior, not schemas or APIs**, and that
exact signatures are RFC-0020's. Iteration 1 therefore introduces a *type
surface* — the exported names and their invariants — not method signatures.

| Module | Public type surface (exported) | Normative source |
|---|---|---|
| `schema/fact.py` | `Fact`, `FactStatus`, `Provenance`, `Freshness`, `FreshnessState`, `MachineIdentity`, `ConfidenceSource`, `Subject`, `Property`, `Value`, `Scope`, `Collector`, `FactCategory` | RFC-0005 §3, §4, §5, §12; §11 (identity), §10 (category) |
| `schema/action.py` | `Action`, `Step`, `Proposal`, `Plan` | RFC-0003 §2.6 |
| `schema/outcome.py` | `Outcome` | RFC-0006 §7 |

Invariants of the type surface (these are the *architectural* contract; exact
APIs are RFC-0020's):

- `Fact` cannot be constructed from LLM/provider/untrusted text (F1); it has
  **no** field that names or confers a permission/role/authority (F2); it is a
  pure data record with no execution capability (F3); its provenance is
  **mandatory** (F10).
- `FactStatus` preserves the F11 distinctions structurally: `Unknown` ≠
  `Unavailable` (Missing) ≠ `Unsupported` ≠ `Stale`.
- `Outcome` is exhaustive and mutually exclusive for a single comparison
  (RFC-0006 §7 rules 1–2).
- `Step` positions an `Action` in sequence with preconditions, expected
  Post-condition, and verification method (RFC-0003 §2.6).

---

## 6. Internal interfaces

Within the `schema` package there is **one** intra-package relationship under
consideration:

- `Step` (in `action.py`) references an expected Post-condition, which is
  "expressed as Facts" (RFC-0003 §2.5) — i.e. a Fact-shaped expectation
  (Subject + Property + expected Status + freshness bound, RFC-0006 §5).
  Whether `action.py` imports the `Fact` type from `fact.py`, and whether a
  distinct `Postcondition` type is introduced, is **ambiguous** (see §16 #5)
  and is left open by this review.

All other modules in `schema` are mutually independent. There are no internal
package dependencies in Iteration 1: the dependency rule
`ALLOWED["schema"] = ∅` (enforced by `tests/test_dependency_rules.py`) and the
DoD "zero imports beyond stdlib" together mean `schema` imports nothing but the
standard library.

---

## 7. Data types to be created

Conceptual types (name and normative content; representation is RFC-0020's):

| Type | Normative content |
|---|---|
| `Fact` | Identifier, Subject, Property, Value, Status, Confidence Source, Timestamp, Collector, Provenance, Freshness, Machine Identity, Scope (RFC-0005 §3) |
| `FactStatus` | 8 values: Observed, Verified, Unknown, Unavailable, Unsupported, Contradicted, Stale, Invalid (RFC-0005 §4) |
| `Provenance` | Observation reference, Collector identity (name+version), collection timestamp + every re-collection timestamp, reproducible procedure (RFC-0005 §5) |
| `Freshness` / `FreshnessState` | Bound + state: Current, Possibly stale, Stale, Expired, Unknown freshness (RFC-0005 §12) |
| `MachineIdentity` | Opaque identity reference; contents are RFC-0014's (RFC-0005 §11) |
| `ConfidenceSource` | A **named deterministic check** — never a percentage, never an LLM estimate (RFC-0005 §3) |
| `Subject`, `Property`, `Value` | The claim's naming components, canonical and distro-independent (RFC-0005 §3) |
| `Scope` | Exactly the Subject/Property/Value claimed; carries the category (RFC-0005 §3, §10) |
| `Collector` | Deterministic read-only inspection identity (RFC-0003 §2.4) |
| `Action` | Atomic unit of work: description, risk-relevant properties, verification criteria (RFC-0003 §2.6) |
| `Step` | Action in sequence + preconditions + expected Post-condition + verification method (RFC-0003 §2.6) |
| `Proposal` | Candidate Action or Plan, not yet classified/approved/executed (RFC-0003 §2.6) |
| `Plan` | Goal-scoped, ordered set of Steps (RFC-0003 §2.6) |
| `Outcome` | One of the verification Outcomes (RFC-0006 §7; see §16 #2 for an 8-vs-5 discrepancy) |

---

## 8. Ownership of every type

Blueprint §10 fixes ownership; this review transcribes it and does not add
owners. No type has two owners.

| Type | Owning RFC | Owning section(s) | Protected by |
|---|---|---|---|
| `Fact` and all components in `fact.py` (Status, Provenance, Freshness, Machine Identity, Scope, Confidence Source) | RFC-0005 | §3, §4, §5, §12 | F1–F16 |
| `FactCategory` | RFC-0005 (concept) / RFC-0021 (vocabulary) | RFC-0005 §10 | category rule "follows RFC-0021" (§16 #4) |
| `Action`, `Step`, `Proposal`, `Plan` | RFC-0003 | §2.6 | (vocabulary) |
| `Outcome` | RFC-0006 | §7 | V5–V7, V9, V15 |
| `Observation` reference used by Provenance | RFC-0005 | §2, §5 | (definition; type deferred per §16 #6) |
| `MachineIdentity` contents | RFC-0014 | (does not exist) | opaque in Iteration 1 |

Cross-cutting note from blueprint §10: where a type is touched by two RFCs, the
properties are split by owner (e.g., `Fact`'s *status* semantics are RFC-0005's;
its *consumption* by verification is RFC-0006's). No single property has two
owners.

---

## 9. Dependency graph

Package-level, per blueprint §4.1/§4.3 (Layer 0 → higher):

```
schema   ← imports: (none — stdlib only; ALLOWED[schema] = ∅)
             importers: every other package (systemmodel, trust, collectors,
             factlayer, verification, secrets, policy, executor, audit,
             context, providers, skills, core, cli) — none built in Iteration 1
```

- `schema` is Layer 0; it depends on nothing.
- The dependency-rule tests (`tests/test_dependency_rules.py`) already encode
  `ALLOWED["schema"] = set()`; Iteration 1 must keep that green.
- No dependency on `systemmodel` (RFC-0021) is permitted in Iteration 1, even
  though RFC-0005's Subject/Category vocabulary references RFC-0021 — this
  tension is reported at §16 #4.

---

## 10. Import graph

At the module level inside `schema`:

```
schema/__init__.py  →  re-exports the three public modules
schema/fact.py      →  stdlib only
schema/action.py    →  stdlib only (possibly fact.py — see §16 #5, open)
schema/outcome.py   →  stdlib only
```

- No module in `schema` imports any `episky.*` package (DoD).
- No module in Iteration 1 has import-time side effects; imports are
  side-effect free type definitions.
- CI gates that must remain green: `tests/test_dependency_rules.py`
  (no forbidden edge, all edges allowed), `tests/test_packages.py`
  (tree matches blueprint §2 exactly), plus a new stdlib-only gate (see §12).

---

## 11. Initialization order

- **Build order (iteration level):** `schema` is built first, before
  `systemmodel`/`trust` (Iteration 2), because every later package imports it
  (blueprint §8.2 precedes §8.3; RFC-0000 §7 mirrors this as the vocabulary
  foundation). This review does not change the iteration order; RFC-0020
  retains the authoritative final word (blueprint §1).
- **Within Iteration 1:** there is no runtime initialization. Import order is
  irrelevant because no module executes code at import time. The only ordering
  constraint is *definitional*: `action.py` may reference types from `fact.py`
  if the §16 #5 ambiguity is resolved toward such a reference.
- **No module imports, loads, or reads any external resource.** There is no
  configuration, no I/O, no environment access in the `schema` package.

---

## 12. Test strategy

Blueprint §7 (`schema` row) and §8.2 DoD fix the Iteration 1 test strategy:
**type-level invariant conformance tests** for F1–F3 and F10, and a guarantee
that `schema` has zero imports beyond stdlib.

| Test | Enforces | Oracle |
|---|---|---|
| `Fact` has no field that can name/confer a permission, role, or authority; construction is provenance-mandatory | F2, F10 | RFC-0005 §3, §4, §5, §13 |
| `Fact` has no execution capability (pure data record) | F3 | RFC-0005 §13; RFC-0002 invariant 5 |
| `Fact` cannot be built from LLM/provider/untrusted text | F1 | RFC-0005 §13; RFC-0004 A1 |
| `FactStatus` distinctness: Unknown ≠ Unavailable ≠ Unsupported ≠ Stale, never silently converted | F11 (type-level) | RFC-0005 §4, §13 |
| `Outcome` exhaustive + mutually exclusive for one comparison | RFC-0006 §7 rules 1–2 | RFC-0006 §7 |
| `Schema` imports only stdlib modules | §8.2 DoD | blueprint §8.2 |
| Package tree still matches blueprint §2 exactly | blueprint §2 | `tests/test_packages.py` |
| Dependency rules still hold (no new edges from `schema`) | §4.1/§4.2 | `tests/test_dependency_rules.py` |

Deferred tests (blueprint §7, cross-cutting policy): the 31 failure scenarios
and the full-loop integration test belong to the iterations that own the
responsible behavior; nothing is tested here beyond the type surface.

---

## 13. Future extension points

Recorded so the type surface is not built in a dead end:

1. **`schema` as the consumed vocabulary** — every later package imports these
   types; the type surface must remain stable and additive.
2. **Serialization / data formats** — RFC-0005 §3 "no schemas" holds until
   RFC-0020 defines formats; the type surface is the substrate for it.
3. **`Fact` relationships, lifetime, Evidence Sets** (RFC-0005 §6–§9) —
   Iteration 3 (`factlayer`) builds on the `Fact`/`Provenance` types.
4. **`FactCategory` binding to RFC-0021** — Iteration 2 (`systemmodel`) supplies
   the authoritative category/subject vocabulary; `schema` must be able to
   adopt it without a redesign (§16 #4).
5. **`Postcondition` type** — Iteration 4 (`verification`) may define the
   concrete expected-state type that `Step` references (§16 #5).
6. **Goal-level `Outcome`** (Completed/Failed/Cancelled, RFC-0003 §2.3) — a
   distinct concept from the verification `Outcome` (RFC-0006 §7); owned by
   `core`/Iteration 10 (§16 #3).
7. **`MachineIdentity` contents** — RFC-0014 fills the opaque reference.
8. **Freshness bound values** — RFC-0020 supplies per-category policy values.

---

## 14. Explicit non-goals

Iteration 1 **does not**:

- write production behavior, algorithms, or business logic of any kind;
- define serialization formats, wire formats, or storage schemas (RFC-0005 §3);
- implement normalization, collection, or the Observation→Fact pipeline;
- implement verification, Compare, or Outcome determination;
- implement trust classes, secrets, policy, execution, audit, or context;
- implement the state machine or any runtime behavior;
- bind `schema` to `systemmodel`/RFC-0021 vocabulary (DoD forbids the import;
  the binding is Iteration 2's);
- define concrete API/method signatures (RFC-0020's);
- add TODO markers (blueprint never authorizes them);
- resolve any ambiguity listed in §16 — it reports them instead.

---

## 15. Risks

| # | Risk | Grounding | Severity | Mitigation |
|---|---|---|---|---|
| 1 | **Draft RFCs change before acceptance** — RFC-0005/0006 are Draft; Iteration 1 conforms to their invariants, which may move | blueprint §9 #2; RFC-0003 Part II §1 | High | Conformance tests are re-run at each Draft revision; no production code depends on Draft wording |
| 2 | **The type/signature boundary is fuzzy** — RFC-0005 §3 says "no schemas," yet Iteration 1 defines types | RFC-0005 §3; blueprint §5, §11.2 #4 | Medium | Iteration 1 defines *types*, not *schemas/formats/APIs*; exact signatures deferred to RFC-0020; the boundary is reported (§16 #1) |
| 3 | **Outcome enumeration mismatch** — RFC-0006 §7 lists 8 Outcomes; blueprint §8.5 and the Iteration-0 docstring list 5 | RFC-0006 §7 vs blueprint §8.5 | Medium | Reported (§16 #2), not silently resolved; the RFC is the normative oracle |
| 4 | **F1 "never LLM-authored" undermined at construction** — a permissive constructor could later become an LLM-authoring path | RFC-0005 F1; RFC-0004 A1 | High | Type-level F1 test blocks any non-Observation construction path |
| 5 | **Empty/opaque references** (Machine Identity, Observation) tempt stringly-typed substitutes that erode safety | RFC-0005 §11; RFC-0002 invariant 15 | Medium | Opaque identity references with documented owners; contents deferred to RFC-0014 |
| 6 | **DoD stdlib-only tempts duplicated vocabulary** — e.g., redefining RFC-0021 categories inside `schema` to avoid the import | RFC-0005 §10; blueprint §8.2 | Medium | Reported (§16 #4); categories deferred to Iteration 2 rather than duplicated |

---

## 16. Ambiguities discovered

Each is reported, not resolved. Each names the corpus silence that forces the
report and the RFC/decision that owns the answer.

| # | Ambiguity | Why it cannot be resolved here | Owning RFC / decision |
|---|---|---|---|
| 1 | **"No schemas" (RFC-0005 §3) vs. "define canonical types" (Iteration 1).** Where is the line between a *type* (allowed) and a *schema/API signature* (RFC-0020's)? | RFC-0005 §3 and blueprint §5 explicitly defer schemas/signatures; the blueprint §8.2 simultaneously asks for types | RFC-0020 / an RFC-0003 decision note |
| 2 | **Outcome enumeration: 8 vs 5.** RFC-0006 §7 defines eight Outcomes (Verified Success, Verified Failure, Partially Successful, No Observable Change, Unknown, Contradicted, Interrupted, Expired). Blueprint §8.5 and the Iteration-0 `schema/outcome.py` docstring name five (Verified Success / Partial / Unknown / Contradicted / Expired). | The blueprint is a translation and may abbreviate; RFC-0006 is Draft and may change; the docstring is scaffold | RFC-0006 (Draft) acceptance; the RFC is the oracle |
| 3 | **Two distinct "Outcome" senses.** RFC-0003 §2.3 defines Outcome = Goal terminal result (Completed, Failed, Cancelled); RFC-0006 §7 defines Outcome = verification result (eight values). The `schema/outcome.py` module maps to RFC-0006 §7 (blueprint §10). Where does the Goal-level Outcome live? | RFC-0003 §2.3 and RFC-0006 §7 use the same word with different scopes; no RFC reconciles them | RFC-0003 (vocabulary) / RFC-0006 |
| 4 | **FactCategory / Subject vocabulary requires RFC-0021, but `schema` cannot import `systemmodel`** (DoD: stdlib only; RFC-0021 is Draft, Iteration 2). Does Iteration 1 define a placeholder category enum (risk: pre-empts RFC-0021), or defer categories entirely? | RFC-0005 §10 says categories "follow RFC-0021"; blueprint §8.2 forbids the import | RFC-0021 (Draft) / Iteration 2; RFC-0020 |
| 5 | **`Postcondition` type ownership.** `Step` requires "expected Post-condition" (RFC-0003 §2.6), and Post-conditions are Fact-shaped (RFC-0006 §5) — but RFC-0006 §5 is Iteration 4 (`verification`) territory, and blueprint §10 assigns `schema/action.py` to RFC-0003 §2.6 only. Does Iteration 1 define `Postcondition` in `schema`, or leave a reference for Iteration 4? | No RFC assigns the type; blueprint §10 does not list it | RFC-0006 / Iteration 4; RFC-0020 |
| 6 | **`Observation` reference inside `Provenance`.** Provenance must name the Observation (RFC-0005 §5), but the `Observation` type belongs to the pipeline (RFC-0005 §2, Iteration 3). Does Iteration 1 define a minimal `Observation` reference, or leave a placeholder? | RFC-0005 §2/§5 vs §3 "no schemas"; Iteration 3 owns the pipeline | Iteration 3 / RFC-0020 |
| 7 | **`MachineIdentity` representation.** Iteration 1 carries an opaque identity (RFC-0005 §11), but "the precise contents are RFC-0014's." Is the opaque form acceptable as a type? | RFC-0014 does not exist | RFC-0014 |
| 8 | **Freshness bound representation.** §12 fixes the *mechanism* (bound + state) but not bound *values* (RFC-0020 policy) or whether the bound is a scalar or a policy reference | RFC-0005 §12; RFC-0020 | RFC-0020 |
| 9 | **Fact Identifier format.** §3/§6 require a stable reference, but its form/generation is implementation | RFC-0005 §3, §6 | RFC-0020 |
| 10 | **F1 construction path.** A Fact must derive only from a normalized Observation (RFC-0005 §2, §13), but no Observation→Fact behavior exists yet. Is the type-level F1 test (no untrusted-text constructor) sufficient for Iteration 1, or does it overreach into behavior? | RFC-0005 §13 F1 test wording assumes a pipeline that does not exist yet | RFC-0020 / Iteration 3 |

---

## 17. Questions that require architectural clarification

These need an answer before the ambiguous items in §16 are resolved during
implementation. They are questions, not decisions.

1. **Outcome cardinality (from §16 #2):** should the Iteration 1 `Outcome` type
   carry all eight RFC-0006 §7 values, or the five named by the blueprint?
   (This affects `schema/outcome.py`'s content immediately.)
2. **Goal-level Outcome (from §16 #3):** is the RFC-0003 §2.3 Outcome
   (Completed/Failed/Cancelled) a distinct type to be introduced now, later
   (`core`), or should the two senses be distinguished by naming?
3. **Category binding (from §16 #4):** may Iteration 1 introduce a placeholder
   `FactCategory` enum, or must categories wait for Iteration 2?
4. **Postcondition (from §16 #5):** is `Postcondition` defined in `schema`
   (Iteration 1) or in `verification` (Iteration 4)? If the former, does
   `action.py` import the `Fact` type?
5. **Observation reference (from §16 #6):** does `Provenance` need a concrete
   `Observation` type in Iteration 1, or a reference placeholder?
6. **F1 test scope (from §16 #10):** is the type-level F1 test (no untrusted
   constructor) the agreed Iteration 1 reading of F1?
7. **Type/signature boundary (from §16 #1):** is the "type surface, not
   signatures" framing the agreed boundary until RFC-0020?

---

## 18. Mapping: RFC section → Type → Interface → Future implementation

| RFC section | Type | Interface (type surface) | Future implementation |
|---|---|---|---|
| RFC-0005 §3 (canonical model) | `Fact` + components | Exported from `schema/fact.py`; F1/F2/F3/F10 by construction | Iteration 3 normalizes Observations into it; every consumer imports it |
| RFC-0005 §4 (status) | `FactStatus` | Enum; F11 distinctness | Iteration 3 status transitions; Iteration 4 Outcome determination reads it |
| RFC-0005 §5 (provenance) | `Provenance` | Mandatory on `Fact`; F10 | Iteration 3 attaches at normalization (RFC-0007 T6); RFC-0007 demotion consumes it |
| RFC-0005 §12 (freshness) | `Freshness`, `FreshnessState` | Bound + state on `Fact`; F14/F15 | RFC-0020 sets bound values; Iteration 10 watchdog invalidates on state change |
| RFC-0005 §11 (machine identity) | `MachineIdentity` (opaque) | On `Fact`; never mixed (F12) | RFC-0014 fills contents; Iteration 10 enforces identity change invalidation |
| RFC-0005 §10 (categories) | `FactCategory` (deferred, §16 #4) | Part of `Scope` | Iteration 2 (`systemmodel`) supplies authoritative vocabulary |
| RFC-0005 §13 F1–F3, F10 | conformance tests | Type-level tests in `tests/` | Re-run and extended at each Draft revision; behavioral forms land Iterations 3–4 |
| RFC-0003 §2.6 | `Action`, `Step`, `Proposal`, `Plan` | Exported from `schema/action.py` | Iteration 6 (`policy`) classifies; Iteration 7 (`executor`) runs; Iteration 10 (`core`) normalizes proposals into Plans |
| RFC-0006 §7 | `Outcome` | Exported from `schema/outcome.py`; exhaustive + exclusive | Iteration 4 (`verification`) maps Compare results to it; Iteration 7 (`audit`) records it |

---

# Consistency review against the Blueprint and governing RFCs

This review was checked against the blueprint and RFC-0000–0013, RFC-0021, the
two walkthroughs, and the decision traceability matrix.

**Consistent (passes):**

- **Module set.** `schema/{fact,action,outcome}` matches blueprint §2 and §10
  exactly; `tests/test_packages.py` already enforces the tree.
- **Dependency rules.** `schema` stays at Layer 0 with `ALLOWED[schema] = ∅`;
  no allowed edge in the blueprint §4.1 graph gives `schema` an importer
  dependency; no forbidden edge concerns `schema`.
- **Iteration scope and RFC basis.** Scope, work, DoD, and RFC basis (§1 above)
  are transcribed verbatim from blueprint §8.2.
- **Test focus.** F1–F3, F10 (§12) match blueprint §7 `schema` row exactly.
- **Ownership.** Every type in §8 has exactly one owner per blueprint §10;
  no two-owner property is introduced.
- **Gate.** Iteration 1 produces no production code; the type surface is
  scaffold (blueprint §8.0), consistent with RFC-0000 §5.
- **Walkthroughs.** The core-execution walkthrough's Stages 5/9/10/13/14
  (Proposal creation, Fact normalization, Fact comparison, Outcome
  classification) consume exactly the types Iteration 1 defines; the
  failure-injection walkthrough's Fact/Verification rows are served by later
  iterations, not Iteration 1. No contradiction found.
- **Initialization order.** `schema`-first matches blueprint §8.2→§8.3 and
  RFC-0000 §7 (vocabulary foundation).

**Inconsistent / requires attention (reported, not resolved):**

1. **Outcome enumeration (8 vs 5).** RFC-0006 §7 defines eight Outcomes;
   blueprint §8.5 names five, and the Iteration-0 `schema/outcome.py` docstring
   names five. The RFC is the normative oracle; the blueprint's list is an
   abbreviation. Recorded as ambiguity §16 #2 and question §17 #1.
2. **Two "Outcome" senses.** RFC-0003 §2.3 (Goal terminal) vs RFC-0006 §7
   (verification) are both canonical vocabulary; `schema/outcome.py` is mapped
   to RFC-0006 §7. The vocabulary collision is recorded (§16 #3).
3. **Category vocabulary vs DoD.** RFC-0005 §10 binds categories to RFC-0021,
   which `schema` may not import in Iteration 1. Recorded (§16 #4) rather than
   worked around by duplicating vocabulary.

**Verdict.** The design review **passes** as a translation: it adds no
architecture, invents no behavior, respects the gate, and reports every
ambiguity to its owning document instead of resolving it (blueprint §0, §11).
Three recorded items (§16 #2, #3, #4 / §17 #1, #2, #3) affect Iteration 1
content directly and should be clarified before or during the commits that
touch `outcome.py` and category handling; none blocks the `fact.py` core.

---

# Iteration 1 implementation plan (atomic commits, <300 LOC each)

Precondition: the design review above passes, and the three content-affecting
clarifications (§17 #1–#3) are answered. Where a commit depends on a
clarification, it is marked **C#**. Each commit keeps CI green (ruff, pytest,
dependency rules, package-tree test) and adds its conformance tests.

1. **`feat(schema): add FactStatus and freshness type surface (RFC-0005 §4, §12)`**
   — `FactStatus` (8 values) and `Freshness`/`FreshnessState` in
   `schema/fact.py`; type-level F11 distinctness tests. ~120 LOC.
2. **`feat(schema): add provenance and confidence type surface (RFC-0005 §5)`**
   — `Provenance`, `Collector`, `ConfidenceSource` (named check, never
   numeric); F10 mandatory-provenance tests. **Depends on §16 #6 (Observation
   reference form).** ~140 LOC.
3. **`feat(schema): add subject/property/value/scope/machine-identity types (RFC-0005 §3, §11)`**
   — `Subject`, `Property`, `Value`, `Scope`, opaque `MachineIdentity`;
   F2/F12/F13 type-level tests. ~130 LOC.
4. **`feat(schema): add canonical Fact type (RFC-0005 §3, §13)`**
   — the composed `Fact` record; F1 (no untrusted-text constructor), F2 (no
   permission field), F3 (no execution capability), F10 (provenance mandatory)
   by construction + tests. **Depends on §16 #1/#10 boundary answer.** ~150 LOC.
5. **`feat(schema): add FactCategory enum (RFC-0005 §10)`**
   — placeholder category enumeration; tests for the "category is part of
   Scope, never a claim" rule. **Depends on §16 #4 / §17 #3.** ~60 LOC.
6. **`feat(schema): add Action/Step/Proposal/Plan types (RFC-0003 §2.6)`**
   — the four decision/action types; Step references preconditions,
   Post-condition, verification method. **Depends on §16 #5 (Postcondition
   ownership).** ~150 LOC.
7. **`feat(schema): add Outcome vocabulary (RFC-0006 §7)`**
   — `Outcome` per the agreed cardinality (8 per the RFC, or 5 per the
   blueprint as clarified). **Depends on §16 #2 / §17 #1.** ~50 LOC.
8. **`test(schema): enforce stdlib-only and package-tree invariants`**
   — a test asserting every `schema` module imports stdlib only (DoD), plus
   re-verification of §2 tree and dependency rules. ~80 LOC.
9. **`docs: record Iteration 1 clarifications and conformance mapping`**
   — update `docs/implementation-consistency-report.md` with the type→owner
   map, the answered clarifications, and any remaining open questions. ~120 LOC.

Suggested atomic order: 1 → 2 → 3 → 4 → 5 → 6 → 7 → 8 → 9. Commits 5 and 7
are the only ones blocked on architectural clarification; commits 1–4, 6, 8–9
can proceed once the type/signature boundary (§17 #7) is confirmed.

**Execution is intentionally not performed.** Per the task, nothing is
committed, pushed, or opened as a PR. This document awaits approval.
