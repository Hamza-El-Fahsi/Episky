# Iteration 3 — Design Review (Fact Layer + Collectors)

> **Document type:** Implementation design review, not an RFC.
> **Read this first:** This document **defines no new architecture, modifies no
> RFC, invents no behavior, and writes no production code.** It translates the
> frozen corpus (RFC-0000–0013, RFC-0021, the two walkthroughs, the decision
> traceability matrix, `docs/architecture-implementation-blueprint.md`, and the
> ratified `docs/implementation-decision-notes.md` DN-1…DN-12) into an
> implementation plan for the **Diagnostics & Fact Layer — the `collectors` and
> `factlayer` packages** (blueprint §8.4). Where the corpus does not decide
> something, this document **reports** it as an ambiguity or a question; it does
> not resolve it.
>
> **Status of sources.** RFC-0005 is **Draft** (not Accepted); RFC-0002 §4.2
> (COLLECTOR_FAILED) and RFC-0004 §4.5/§4.6 are Accepted. Per RFC-0003 Part II
> §1.1 Draft RFCs are not normative and must not be relied upon by
> implementation; yet the blueprint (a translation, §0) targets the Drafts'
> *invariants* as the conformance oracle (blueprint §9 #2). Iteration 3 inherits
> Iterations 1–2's posture: it conforms to RFC-0005's Draft wording knowingly,
> accepting the rework risk that a Draft change carries (blueprint §9 #2;
> RFC-0003 Part II §1).
>
> **Scope decision (reported — Q1).** Blueprint §8.4 defines Iteration 3 as
> **`factlayer` + `collectors`** in one iteration. Ratified for Iterations 1–2,
> and reported here without resolution: **Iteration 3 = the `factlayer` +
> `collectors` pipeline for the baseline only.** `verification` (RFC-0006) is
> blueprint §8.5 (Iteration 4) and is **not** in this iteration. The `trust`
> upgrade path (RFC-0007 T6, the Observation→Fact trust-upgrade) is **consumed**
> by normalization but the `trust` package itself remains deferred (DN-7).

---

## 1. Scope

Blueprint §8.4 defines Iteration 3 as:

| Item | Value |
|---|---|
| Goal | Observation→Fact pipeline for the baseline |
| Work | Baseline Collectors (distro, kernel, package state); deterministic normalization; provenance/freshness; Fact status store |
| Definition of Done | F5/F6/F7/F8/F10 conformance; a failed collection yields Unknown/Unavailable status (F11, §4); no mutation in any Collect |
| RFC basis | RFC-0005 §2, §4, §5, §12; RFC-0002 §4.2 (COLLECTOR_FAILED) |

### 1.1 Blueprint scope

Two packages, per blueprint §2/§3:

| Package | Module | Blueprint responsibility |
|---|---|---|
| `collectors` | `registry.py` | "The registry of deterministic, read-only inspection procedures; each Collector answers one question and carries declared inputs and provenance behavior" (RFC-0003 §2.4 Collector; RFC-0005 §2) |
| `factlayer` | `collect.py` | Run Collectors (RFC-0005 §2; RFC-0004 §4.5) |
| `factlayer` | `normalize.py` | Observation → Fact (RFC-0005 §2; F5) |
| `factlayer` | `provenance.py` | Provenance + freshness (RFC-0005 §5, §12) |
| `factlayer` | `store.py` | Fact storage, status, invalidation (RFC-0005 §4, §7) |

The module set `collectors/{__init__,registry}.py` and
`factlayer/{__init__,collect,normalize,provenance,store}.py` is **fixed** by
blueprint §2 and `tests/test_packages.py` — adding a module would break
`test_tree_matches_blueprint_exactly`.

### 1.2 RFC sections implemented

**Type/data surfaces** (in-memory domain types only, per DN-1):

| RFC | Section | Implemented as |
|---|---|---|
| RFC-0005 | §2 Observation stage | The `Observation` record (timestamped, provenance-carrying, one Collector run) and `RawOutput` |
| RFC-0005 | §2 Normalization stage | Deterministic per-Observation normalization: Observation + Canonical Definition + Family Profile → Canonical Fact |
| RFC-0005 | §2 output bounds | Bounded output with truncation-with-marker (never silently dropped) |
| RFC-0005 | §3 Canonical Fact | The composed `schema.Fact` (already built, Iteration 1) is the *output* of normalization |
| RFC-0005 | §4 Fact Status | Status assignment: Observed (success), Unknown (failed/timed out/unparseable), Unavailable (could not run), Unsupported (no capability) |
| RFC-0005 | §5 Provenance | Provenance attached **at normalization, never later** (F10) |
| RFC-0005 | §7 Fact Lifetime | Creation, Update (new Fact supersedes), Replacement, Retirement, Deletion of the current set |
| RFC-0005 | §12 Freshness | Freshness bound and state bookkeeping |
| RFC-0003 | §2.4 Collector | The Collector contract: one question, declared inputs, provenance behavior, declared output (Observation) |
| RFC-0021 | §2.3 Family Profile | Normalization consumes the Family Profile (already built, Iteration 2) |
| RFC-0002 | §2.3 Machine Inspection | Collection as read-only inspection; failed Collector → "fact unknown" |
| RFC-0002 | §4.2 COLLECTOR_FAILED | A failed/timed-out diagnostic → Unknown/Unavailable status |

### 1.3 Explicit exclusions

None is silently dropped; each is recorded with its owner.

| Item | Why excluded | Owner |
|---|---|---|
| `verification` (Compare/Outcome) | Blueprint §8.5, Iteration 4 | RFC-0006 |
| `trust` package import | Deferred to its own review (DN-7); normalization *is* the trust-upgrade step (RFC-0007 T6), no `trust` code is needed here | RFC-0007 (Draft) |
| Evidence Sets (§9) | The carrier that leaves the Fact Layer; consumes Context (RFC-0012 §2.4), built when the store and its consumers exist | RFC-0005 §9; Iteration 8 `context` |
| Fact Relationships (§8) | Requires Fact Identity semantics + consumers | RFC-0005 §8 |
| Persistence of the Fact store | RFC-0012 (Context/Memory) and RFC-0013 (Audit) own storage; Iteration 3 builds the in-memory current set | RFC-0005 §7 ("not about persistence") |
| Watchdog | Minimal read-only watch set (RFC-0002 §4.2, Q17) is runtime behavior; freshness invalidation *mechanics* here, trigger wiring later | RFC-0002 Q17 / `core` |
| Machine Identity contents | Opaque placeholder (RFC-0014 owns contents) | RFC-0014 (does not exist) |
| Freshness-bound concrete values | Policy content (RFC-0020) | RFC-0020 |
| Secret redaction inside output | RFC-0009 owns redaction; applied at the Observation boundary — the seam is marked, the mechanism is Iteration 5 | RFC-0009 |
| Concurrent collection | RFC-0002 §11 item 15 is open; serial read-only collection assumed | RFC-0002 / RFC-0020 |

---

## 2. Ownership analysis

Every type, module, and package has exactly one owner (RFC-0004 §3; blueprint
§10). Ownership is transcribed from blueprint §10 + RFC-0005 §14; this review
adds none.

### 2.1 Package owners

| Package | Owning RFC(s) | Responsibility |
|---|---|---|
| `collectors` | RFC-0005 §2; RFC-0003 §2.4; RFC-0021 (vocabulary) | Registry of deterministic, read-only inspection procedures (blueprint §3) |
| `factlayer` | RFC-0005 §2, §3, §4, §5, §7, §12 | Normalize Observations into canonical Facts; carry status, provenance, freshness; own Fact storage and invalidation (blueprint §3) |

### 2.2 Type owners (one owner each)

| Type | Module | Owning RFC / section | Protected by |
|---|---|---|---|
| `RawOutput` | `factlayer/collect.py` | RFC-0005 §2 (stage 1) | bounded-output rule (§2) |
| `Observation` | `factlayer/collect.py` | RFC-0005 §2 (stage 2); RFC-0003 §2.4 | observations-not-Facts rule |
| Collector contract (`CollectorSpec`) | `collectors/registry.py` | RFC-0003 §2.4; RFC-0005 §2 | read-only, one-question, declared inputs/provenance |
| Baseline Collector definitions | `collectors/registry.py` | RFC-0005 §2; RFC-0021 §2.3 | per-family profile data |
| Normalization function | `factlayer/normalize.py` | RFC-0005 §2; F5 | F5, F7, F8, F1, F11 |
| Provenance computation | `factlayer/provenance.py` | RFC-0005 §5; F10 | F10, F16 |
| Freshness computation | `factlayer/provenance.py` | RFC-0005 §12 | F14, F15 |
| Fact store / current set | `factlayer/store.py` | RFC-0005 §4, §7 | F11, F12, F14, F16 |
| `schema.Fact`, `Provenance`, `Freshness`, `FactStatus`, `Collector` (identity) | `schema/fact.py` (already built) | RFC-0005 §3, §4, §5, §12 | F1–F16 |
| `FamilyProfile`, `DistributionFamily`, ecosystem/subsystem vocab | `systemmodel/*` (already built) | RFC-0021 | supported-platform promise |

**The two-owner check.** `collectors` is the *runner* of inspection
(RFC-0004 §4.5 Observe authority) and `factlayer` is the *consumer*
(RFC-0004 §4.6 Observe-as-consumer, Normalize). No single property has two
owners: who runs Collectors is `collectors`; what an Observation *means* (the
Fact) is `factlayer`. This mirrors blueprint §10's split for `factlayer`
(truth: RFC-0004 §4.6; pipeline: RFC-0005).

**Authority (RFC-0004 §4.5/§4.6, §7).** `collectors` holds **Observe**;
`factlayer` holds **Observe** (as consumer) + **Normalize** + **Verify** (as
the re-observation arm, exercised in Iteration 4). Neither holds Propose,
Infer, Approve, Execute, Refuse, or Persist. **No authority leak:** `factlayer`
never creates a Fact from anything but a normalized Observation (F1); the
store never writes outside its own current set; no package grants an actor an
authority the matrix forbids (blueprint §1.5).

---

## 3. Dependency analysis

### 3.1 Allowed imports (blueprint §4.1, transcribed into `tests/test_dependency_rules.py`)

| From | To | Why allowed |
|---|---|---|
| `collectors` | `schema`, `systemmodel` | A Collector's output is Observation material (RFC-0005 §2), expressed over subsystem/Family vocabulary (RFC-0021) |
| `factlayer` | `collectors`, `schema`, `systemmodel` | Normalizes Observations into Facts (RFC-0005 §2); consumes Family Profile + vocabulary |

`collectors` and `factlayer` are both **Layer 2**. Blueprint §4.1 lists `trust`
as an allowed target for both, but `trust` is not built (DN-7) and normalization
*is* the trust-upgrade path (RFC-0007 T6) — no `trust` import is required or
made in this iteration.

### 3.2 Forbidden imports (blueprint §4.2)

| Package | Must NOT import | Reason |
|---|---|---|
| `factlayer` | `providers`, `policy`, `executor`, `skills`, `context`, `audit`, `secrets` | Facts are provider-independent (F6), never permissions (F2), never execute (F3); the Fact Layer has no secret surface (RFC-0009 §1, SC6) |
| `collectors` | (same set as `factlayer`, minus nothing relevant) | Collectors are read-only inspection; they touch no decision, execution, or secret machinery |

`factlayer` and `collectors` also must **not** import `verification`,
`core`, `cli`, or `trust` (trust by deferral).

### 3.3 Layer placement

```
Layer 0  schema
Layer 1  systemmodel, trust (trust deferred, DN-7)
Layer 2  collectors ─► factlayer ─► verification (verification is Iteration 4)
```

- `collectors` sits before `factlayer` (factlayer consumes collectors).
- Neither package sits below Layer 2; neither may be imported by `schema`
  (Layer 0) or `systemmodel` (Layer 1) — no reverse edge.
- `verification` (Iteration 4) will import `factlayer`; that edge is already
  in the allowed graph and stays latent.

### 3.4 Acyclic verification

- **Package graph:** `collectors` → {schema, systemmodel}; `factlayer` →
  {collectors, schema, systemmodel}. No cycle (edges point strictly
  downward in layer order). `tests/test_dependency_rules.py` asserts declared
  and observed acyclicity.
- **`systemmodel` dependency graph** (`SUBSYSTEM_DEPENDENCIES`) is model data,
  never imported.
- No circular ownership: no type is defined in two modules (§2).

---

## 4. Public API surface

Blueprint §5: the RFCs specify **behavior, not schemas or APIs**; exact
signatures are RFC-0020's. Iteration 3 therefore introduces a *type/data
surface* (the exported names and their invariants) plus the *pipeline
behavior* the RFC mandates.

### 4.1 Planned public types (per module)

| Module | Planned public surface | Normative source |
|---|---|---|
| `collectors/registry.py` | `CollectorSpec` (name, one-question description, declared inputs, provenance behavior, declared output: Observation), the baseline Collector registry/table (`distro`, `kernel`, `package-state`) | RFC-0003 §2.4; RFC-0005 §2; RFC-0021 §2.3 |
| `factlayer/collect.py` | `RawOutput`, `Observation` (identity via `schema.Collector`, collected-at, exit status, output, truncation marker), a `collect` entry point | RFC-0005 §2; RFC-0002 §4.2 |
| `factlayer/normalize.py` | deterministic `normalize(Observation, FamilyProfile) -> Fact`; Unknown on failure | RFC-0005 §2; F5 |
| `factlayer/provenance.py` | provenance construction (attached at normalization), freshness state computation | RFC-0005 §5, §12 |
| `factlayer/store.py` | the current set of Facts (in-memory), status transitions, invalidation, supersession | RFC-0005 §4, §7 |

### 4.2 Internal types

| Type | Module | Purpose |
|---|---|---|
| `CollectorSpec` internal fields | `collectors/registry.py` | declared inputs / provenance behavior the RFC-0003 §2.4 contract names |
| `RawOutput` | `factlayer/collect.py` | the Collector's raw utterance (bounded) |
| `Observation` | `factlayer/collect.py` | RawOutput + Collector identity + run metadata |
| truncation marker | `factlayer/collect.py` | recorded truncation, never silent drop (RFC-0005 §2) |
| current-set record | `factlayer/store.py` | one Fact + its status/freshness in the set |

### 4.3 Placeholders

| Name | Status | Owner |
|---|---|---|
| `schema.MachineIdentity` (opaque) | placeholder, reused unchanged | RFC-0014 |
| `schema.ObservationReference` | placeholder (Iteration 1, design review §17 #5); **Iteration 3 replaces it with the real Observation model** — see Q3 | RFC-0005 §2 |
| Freshness bound concrete values | not represented; policy content | RFC-0020 |

### 4.4 Future-owned types

| Type | Deferred to |
|---|---|
| `VerificationOutcome`, Postconditions/Compare | RFC-0006, Iteration 4 |
| Evidence Set, Fact Relationships | RFC-0005 §8/§9; Iteration 8 `context` |
| Trust classes / sanitization | RFC-0007, its own iteration |
| Secret classifier/redactor | RFC-0009, Iteration 5 |

---

## 5. Data model

Every data type in Iteration 3 is an **in-memory domain type** (DN-1); no
serialization, wire format, persistence, or public API signature is defined
(RFC-0020 owns those). No type performs behavior.

| Type | Fields (conceptual, per the RFC) | Normative source |
|---|---|---|
| `RawOutput` | the bytes/text the Collector returned, its exit status, timing | RFC-0005 §2 |
| `Observation` | RawOutput + which Collector (name+version) + when (collected_at) + exit status; a timestamped, provenance-carrying record of one Collector run | RFC-0005 §2; RFC-0003 §2.4 |
| `CollectorSpec` | one question, declared inputs, provenance behavior, declared output (Observation), read-only | RFC-0003 §2.4 |
| `Fact` (schema, reused) | scope (Subject/Property/Value), status, confidence, provenance, freshness, machine identity | RFC-0005 §3 |
| `Provenance` (schema, reused) | observation, collector, collected_at, re_collected_at | RFC-0005 §5 |
| `Freshness` (schema, reused) | state (Current/Possibly stale/Stale/Expired/Unknown freshness) | RFC-0005 §12 |
| `FactStatus` (schema, reused) | Observed/Verified/Unknown/Unavailable/Unsupported/Contradicted/Stale/Invalid | RFC-0005 §4 |

**Status mapping (RFC-0005 §4, §13 F11).** The pipeline produces exactly:

- **Observed** — a current, successful Collector run normalized to a value;
- **Unknown** — the Collector failed, timed out, or produced unparseable output
  ("fact unknown", RFC-0002 §4.2; never a guessed value);
- **Unavailable** — the check could not run at all (permission, tool absent);
- **Unsupported** — the machine lacks the capability (RFC-0021 family/ecosystem
  case).

Missing (Unavailable) and Unsupported stay distinct, never collapsed (F11).

**Value/Status distinction (RFC-0005 §3).** `Value` carries the claim
("service is stopped"); `Status` carries how confidently it is known
("unknown") — never conflated. Confidence is a named source, never a
percentage.

**No behavior in the data model.** Dataclasses are `frozen=True, slots=True`
(F8 immutability); no method performs I/O, parsing, or mutation. The *behavior*
lives in the pipeline functions (§6), not in the types.

---

## 6. Collector architecture

The pipeline is normative (RFC-0005 §2): nothing skips a stage, and no stage's
output is knowledge before the next stage ran.

```
Raw Output → Observation → Normalization → Canonical Fact → Evidence Set → Context
```

### 6.1 Observation

- **Definition (RFC-0003 §2.4 / RFC-0005 §2):** the raw, timestamped output of
  one Collector run, carrying provenance (which Collector, when, exit status).
  Untrusted until normalized into Facts.
- **Iteration 3 realization:** `factlayer/collect.py` builds an `Observation`
  from a `CollectorSpec` run: `RawOutput` + Collector identity
  (`schema.Collector`) + `collected_at` + exit status.
- **Boundary:** Observations are **not** Facts. A failed/inconclusive Collector
  run still produces an Observation (the record that it failed), which
  normalization turns into an Unknown/Unavailable Fact — it never disappears
  (RFC-0002 §4.2).

### 6.2 RawOutput

- **Definition (RFC-0005 §2):** the raw bytes the Collector returned — still
  distro-specific and untrusted.
- **Iteration 3 realization:** `factlayer/collect.py` holds it bounded; output
  beyond the bound is truncated and the Observation records the truncation
  (never silently dropped, never unmarked). The concrete bound value is
  RFC-0020 policy; the truncation *mechanism* is this iteration's.
- **Secret redaction:** RFC-0009's concern, applied at the Observation boundary
  **before** normalization. The seam is marked; the mechanism is Iteration 5
  (`secrets`). No redaction behavior is written in Iteration 3.

### 6.3 Collector

- **Definition (RFC-0003 §2.4):** a deterministic, read-only inspection
  procedure that answers one specific question and carries declared inputs and
  provenance behavior. Is not an Action, not an LLM-generated ad-hoc command.
- **Iteration 3 realization:** `collectors/registry.py` carries the baseline
  Collector declarations for the **baseline set** (blueprint §8.4: distro,
  kernel, package state). Each Collector declares:
  - the one question it answers;
  - its declared inputs (which `schema`/`systemmodel` vocabulary it reads);
  - its provenance behavior (which Family Profile / canonical definition it
    uses, RFC-0005 §5);
  - its declared output: an `Observation`.
- **Read-only:** Collectors never mutate; Inspection is always read-only
  (RFC-0004 A4). **No mutation in any Collect** is a DoD item and a test.

### 6.4 Normalization boundary

- **Definition (RFC-0005 §2):** the only gate between machine and knowledge.
  Raw output and Observations are untrusted; the Fact is the first trusted
  form (RFC-0007 T6). Normalization never runs on LLM output and never consults
  the model.
- **Iteration 3 realization:** `factlayer/normalize.py` is a pure, deterministic
  function per Observation: `normalize(Observation, FamilyProfile) -> Fact`.
  - **Deterministic** (F5): re-normalizing the same Observation yields the same
    Fact.
  - **Per-Observation** (RFC-0002 Q15): each Observation normalizes
    independently; concurrent collection cannot change any resulting Fact.
  - **Lossy by design:** distro-specific wording is discarded; only the
    canonical claim survives (RFC-0001 Q6).
  - **What cannot be normalized → Unknown** (F11), never a guess, never nothing.
  - **Provider-independent** (F6), **distro-independent** (F7): the Family
    Profile absorbs distro variance (RFC-0021 §2.3).
- **F1 (behavioral):** the only construction path to a Fact's components is a
  normalized Observation (DN-2 — Iteration 3's behavioral complement to
  Iteration 1's structural F1 test).

### 6.5 Fact creation boundary

- **Definition (RFC-0005 §3):** the complete Fact carries status, provenance,
  freshness, machine identity, and scope.
- **Iteration 3 realization:** normalization attaches status (Observed),
  provenance (the Observation it came from, §5), freshness (state bookkeeping,
  §12), machine identity (opaque `schema.MachineIdentity`), and scope (the
  Subject/Property/Value claim). The Fact is immutable (F8).
- **Boundary:** a Fact is created **only** by normalization. No other path —
  not the store, not a Collector, not the Operator (F1), and never a provider
  (F6, RFC-0004 A1).

### 6.6 Authority boundaries

| Boundary | Owner | Guarantee |
|---|---|---|
| Observe (run inspection) | `collectors` (RFC-0004 §4.5) | read-only; A4 |
| Observe (consume Observations) | `factlayer` (RFC-0004 §4.6) | never infers from raw output |
| Normalize (Observation→Fact) | `factlayer` (RFC-0005 §2; RFC-0004 §4.6) | the only trust-upgrade step (RFC-0007 T6) |
| Fact storage / current set | `factlayer` (RFC-0004 §4.6) | never fabricates, never drops silently |
| Verify (re-observation arm) | `factlayer` — exercised in Iteration 4 | RFC-0004 §4.6 |

**Never decides:** what an Observation *means* beyond the canonical claim
(interpretation is Infer — Diagnosis), whether the machine should change, or to
mutate anything (RFC-0004 §4.5/§4.6).

---

## 7. Package layout

Expected files (fixed by blueprint §2 / `tests/test_packages.py`):

```
src/episky/
├── collectors/
│   ├── __init__.py          # package surface (registry)
│   └── registry.py          # CollectorSpec + baseline Collector registry
└── factlayer/
    ├── __init__.py          # package surface
    ├── collect.py           # RawOutput, Observation, collect entry point
    ├── normalize.py         # deterministic normalize(Observation, FamilyProfile) -> Fact
    ├── provenance.py        # provenance construction, freshness computation
    └── store.py             # Fact status store, invalidation, supersession
```

Expected ownership (blueprint §3, §10 — transcribed):

| File | Owns | Forbidden |
|---|---|---|
| `collectors/registry.py` | the Collector contract + baseline declarations | any execution, any mutation, any `factlayer`/`schema` behavior |
| `factlayer/collect.py` | running Collectors → Observations | producing Facts, mutating the machine |
| `factlayer/normalize.py` | Observation → Fact | LLM output, guessing on failure |
| `factlayer/provenance.py` | provenance + freshness | losing provenance (F10), treating unknown-freshness as current (F15) |
| `factlayer/store.py` | current-set status/invalidation | permissions (F2), execution (F3), persistence (RFC-0012/0013) |

No new module, no new package, no new dependency edge.

---

## 8. Interaction with previous iterations

### 8.1 Depends on Iteration 1 (`schema`)

- The `Fact`, `Scope`, `Provenance`, `Freshness`, `FactStatus`,
  `ConfidenceSource`, `Collector` (identity), `MachineIdentity` types are the
  pipeline's data model (§5). Iteration 3 **consumes** them; it does not change
  them.
- **`ObservationReference` replacement (Q3):** `schema.Provenance.observation`
  is typed as the empty `ObservationReference` placeholder (Iteration 1 design
  review §17 #5). The placeholder's own docstring says "Iteration 3 must be
  able to replace it with the real Observation model with zero semantic
  changes to Provenance." This review **reports** (Q3) how the replacement is
  typed without `schema` importing `factlayer` (Layer-0 constraint) — options
  are a canonical `Observation` reference type in `schema`, or keeping a
  reference-only marker. **No ownership change.**
- F1 structural enforcement (Iteration 1) is **complemented** by F1 behavioral
  enforcement here (DN-2) — never a substitute.

### 8.2 Depends on Iteration 2 (`systemmodel`)

- Normalization consumes the **Family Profile** (`FAMILY_PROFILES`, RFC-0021
  §2.3) and the family/ecosystem status vocabulary (Iteration 2) to absorb
  distro variance (F7).
- Baseline Collector declarations reference subsystem/State-Domain vocabulary
  (RFC-0021 §4/§6) as the canonical Subject vocabulary.
- `systemmodel` is **not modified**; the allowed `collectors`→`systemmodel`
  and `factlayer`→`systemmodel` edges (blueprint §4.1) are **used**, not latent.
- `FactCategory` (type in `schema`, meaning in `systemmodel` — DN-9) is **not**
  consumed by Iteration 3's Facts (Scope stays category-free per DN-9; the
  §10 binding is deferred — Q2). No change to either owner.

### 8.3 No ownership change

Iteration 3 adds no new package, no new type to `schema` except the possible
`ObservationReference` replacement (Q3), and no new dependency edge beyond the
already-authorized `collectors`/`factlayer` Layer-2 edges. Every existing
owner (RFC-0005 for the fact model, RFC-0021 for the machine model, RFC-0004
for authority) is unchanged.

---

## 9. Test strategy

The corpus fixes the testing philosophy: conformance tests against invariants
(blueprint §7), invariants hold in every state without exception (RFC-0002 §9),
and failure scenarios of the walkthrough map to tests at the responsible
package.

### 9.1 Invariant → test map

| Invariant | Test | Package |
|---|---|---|
| F1 (never LLM-authored, behavioral) | only a normalized Observation can produce a Fact's components; no model output path exists | `factlayer` |
| F5 (deterministic) | re-normalizing the same Observation reproduces the Fact exactly | `factlayer` |
| F6 (provider-independent) | no `providers` import; a Fact does not vary with any provider | `factlayer` |
| F7 (distro-independent) | the same claim from different distro families produces the same Fact (given Family Profile) | `factlayer` |
| F8 (immutable) | a recorded Fact's content never changes after creation; dataclasses frozen | `factlayer` |
| F10 (provenance) | provenance is attached at normalization; a Fact with lost provenance is invalidated, not re-attributed | `factlayer` |
| F11 (Unknown ≠ Missing ≠ Unsupported) | each status preserved and never silently converted; failed collection → Unknown/Unavailable | `factlayer` / `store` |
| F12 (one machine) | a Fact of identity X is never used as evidence for machine Y | `store` |
| F14 (expire) | nothing uses a Fact past its freshness bound without re-collection | `store` |
| F15 (unknown freshness ≠ current) | an un-freshnessable Fact is never believed current | `provenance` / `store` |
| F16 (fail closed) | a rule-violating Fact is blocked and surfaced (Invalid + disclosed) | `store` |
| A4 (inspection read-only) | **no mutation in any Collect** — Collectors never write | `collectors` |
| RFC-0002 §4.2 COLLECTOR_FAILED | a failed/timed-out Collector → Unknown/Unavailable "fact unknown" | `collectors` / `factlayer` |
| RFC-0002 invariant 2 (before/after compare) | not exercised here (Verification is Iteration 4) | — |

### 9.2 Structural tests

- `tests/test_packages.py` — tree still matches blueprint §2 exactly (no new
  module).
- `tests/test_dependency_rules.py` — allowed/forbidden edges, acyclicity;
  `factlayer` imports only `collectors`/`schema`/`systemmodel` (+ stdlib).
- A new **Layer-2 conformance** test (mirroring `test_schema_conformance.py`
  and `test_systemmodel_conformance.py`): every `collectors`/`factlayer` module
  imports only stdlib + the allowed packages; no I/O at import time; no
  `providers`/`executor`/`policy`/`skills`/`context`/`audit`/`secrets`/`trust`
  imports anywhere in the pipeline.
- `test_schema_conformance.py` — updated only if Q3 changes the `schema`
  surface (ObservationReference replacement).

### 9.3 Behavioral tests

- **Determinism (F5):** the same Observation normalizes to the same Fact across
  calls.
- **Distro-independence (F7):** the same claim expressed in Debian-family vs
  Red Hat-family raw output (per `FAMILY_PROFILES`) normalizes to the same
  Fact.
- **Failure → status (F11/§4.2):** a failing, timing-out, and unparseable
  Collector each yield Unknown; a never-invoked Collector yields Unavailable;
  an unsupported family yields Unsupported — never a guess, never nothing.
- **Truncation:** output past the bound is truncated and the Observation
  records the truncation marker.
- **No mutation in any Collect (A4):** the collection path performs no write.
- **Store lifecycle (F8/F11/F14/F16):** update = new Fact superseding old
  (old retired); stale → re-collected before use; rule-violating → Invalid and
  disclosed.

Cross-cutting: the failure-injection walkthrough Scenario 30 ("unknown
environment / unsupported platform") is realized here at the *status* level —
an unsupported family produces Unsupported status Facts, and the fail-closed
*decision* is `core`'s (RFC-0002 §2.3). Core-execution walkthrough Stage 9
(Fact normalization) is the integration oracle for the normalize path.

---

## 10. Risks

| # | Risk | Grounding | Severity | Mitigation |
|---|---|---|---|---|
| 1 | **Draft rework.** RFC-0005 (Draft) may change the Observation/Fact model, status set, or pipeline before acceptance | RFC-0005 status; RFC-0003 Part II §1.1 | High | Conformance tests against the Draft invariants; no production dependency until acceptance (blueprint §9 #2) |
| 2 | **Normalization bugs.** A parser misreads distro output and produces a wrong canonical value | RFC-0005 §16 | High | Deterministic per-Observation normalization with Unknown on failure (F5, §2); tested against `FAMILY_PROFILES` |
| 3 | **F1 regression.** LLM/provider output reaches a Fact | RFC-0005 §13 F1 | Critical | Behavioral F1 test; `providers` import forbidden; normalization is the only Fact path |
| 4 | **Status collapse.** Unknown/Missing/Unsupported conflated | RFC-0005 §13 F11 | High | F11 conformance test; store never silently converts |
| 5 | **Raw output leaks into reasoning unbounded** | RFC-0005 §2; RFC-0002 invariant 4 | High | Output bound + truncation marker; raw output never becomes state |
| 6 | **Secret leakage at the Observation boundary** before `secrets` exists (Iteration 5) | RFC-0005 §2; RFC-0009 | Critical | The redaction seam is marked but **not implemented** here; no secret handling is written, so nothing leaks by construction in this iteration — the boundary is deferred to Iteration 5, and any later pipeline must apply redaction before normalization |
| 7 | **Ownership drift** — a module defining a name its owner RFC does not assign | blueprint §10 | Medium | Conformance test (public surface == owned vocabulary) |
| 8 | **Gate/trust confusion** — importing `trust` before it exists | DN-7 | Medium | No `trust` import; normalization *is* the T6 upgrade step |

---

## 11. Clarification questions

Every unresolved point is a numbered question. Each names its owning RFC, the
commit(s) it blocks, its severity, and whether a placeholder is acceptable.
**Nothing here is resolved by this review.**

| Q | Question | Owning RFC | Blocks | Severity | Placeholder acceptable? |
|---|---|---|---|---|---|
| Q1 | **Iteration scope:** blueprint §8.4 pairs `factlayer` + `collectors`; is `verification` (RFC-0006) strictly excluded from this iteration, and is `trust` strictly not imported (DN-7)? | RFC-0006 (future); RFC-0007 (Draft) | all commits | Medium | Yes — the boundary is already ratified (DN-7); a placeholder is unnecessary |
| Q2 | **FactCategory on Scope:** DN-9 deferred the RFC-0005 §10 "category is part of Scope" binding to "Iteration 3+." Does Iteration 3 bind the category to the Fact/Scope (changing `schema.Scope`), or keep Scope category-free and defer freshness-per-category to RFC-0020? | RFC-0005 §10, §12; DN-9 | store (freshness), possibly `schema` | High | Yes — keep Scope category-free; freshness-per-category deferred to RFC-0020 policy |
| Q3 | **ObservationReference replacement:** how is `schema.Provenance.observation` typed when the real `Observation` model lives in `factlayer` (Layer 2) and `schema` (Layer 0) may not import it? Canonical reference in `schema`, or an opaque reference marker, or keeping the placeholder? | RFC-0005 §2, §5; Layer-0 constraint | `collect`, `provenance` | High | Yes — a reference-only marker in `schema` preserves the dependency without a Layer-0→2 import |
| Q4 | **ConfidenceSource on failure:** what confidence source names an Unknown/Unavailable Fact? RFC-0005 §3 requires a named check, never a number; a failed check has no value. | RFC-0005 §3 | `normalize` | Medium | Yes — the Collector identity itself is the named source; no percentage |
| Q5 | **Baseline set contents:** blueprint §8.4 names "distro, kernel, package state." Is package-state limited to the two **Native** ecosystems (apt/dpkg, dnf/rpm) per RFC-0021 §5.2, and are Secondary/Experimental ecosystems excluded from the baseline Collectors? | RFC-0021 §5; RFC-0005 §2 | `collectors` (baseline declarations) | Medium | Yes — baseline = the two Native ecosystems; others Unsupported/Excluded |
| Q6 | **Collector granularity:** is each baseline question one `CollectorSpec` (distro, kernel, package-state), or are there per-ecosystem CollectorSpecs (e.g., apt package-state, dnf package-state) sharing one question? | RFC-0003 §2.4 ("answers one question") | `collectors` | Medium | Yes — one question per CollectorSpec, per-ecosystem declarations allowed under one question |
| Q7 | **Output-bound value:** the truncation *mechanism* is in scope, but the concrete size bound per Collector is RFC-0020 policy. Is a placeholder/default bound acceptable, with the value left to RFC-0020? | RFC-0005 §2; RFC-0020 | `collect` | Low | Yes — mechanism only; value is RFC-0020 policy |
| Q8 | **Store persistence:** RFC-0005 §7 fixes lifecycle meaning, not storage (RFC-0012/0013 own persistence). Is the Iteration 3 store in-memory only, with no durability? | RFC-0005 §7; RFC-0012/0013 | `store` | Low | Yes — in-memory current set; persistence later |
| Q9 | **Supersession identity:** RFC-0005 §6 says a newer Fact supersedes an older of the same identity (same Machine Identity + Subject + Property). Iteration 1 deferred the Identifier component (RFC-0020). Does Iteration 3 implement supersession on the §6 component identity, without inventing an Identifier format? | RFC-0005 §6, §7; RFC-0020 | `store` | Medium | Yes — component-based identity; no Identifier format |
| Q10 | **Timing in Observation:** RFC-0005 §2 lists "timing" in Raw Output. Is run timing a field of `Observation`/`RawOutput` in Iteration 3, or deferred? | RFC-0005 §2 | `collect` | Low | Yes — timing can be omitted/None; provenance keeps collected_at |
| Q11 | **Critical collector failure:** RFC-0002 §2.3 — a critical failure (cannot establish the distro) → disclose + ask Operator. That *decision* is `core`'s (Iteration 10). Does Iteration 3 only record the Unavailable status, leaving the disclosure/ask to `core`? | RFC-0002 §2.3 | `store` | Medium | Yes — status recorded here; decision is `core`'s |
| Q12 | **DoD "F10 conformance" reading:** the blueprint DoD names "F5/F6/F7/F8/F10 conformance" — does F10 (provenance) conformance here mean *attached at normalization* (F10's normative rule), given `schema.Provenance` is already built? | RFC-0005 §5, §13 | `provenance` | Low | Yes — attach-at-normalization + loss→Invalid is the F10 reading |

---

## 12. Commit plan

Atomic commits, <300 LOC each, one responsibility each, in dependency order,
each keeping CI green (ruff, pytest, dependency rules, package-tree test) and
adding its conformance tests. This section **records the plan; it does not
perform it.**

| # | Commit | Responsibility | Est. LOC | Blocks on |
|---|---|---|---|---|
| C1 | **`feat(collectors): add Collector contract and baseline registry (RFC-0003 §2.4; RFC-0005 §2)`** | `CollectorSpec` type + the baseline Collector declarations (distro, kernel, package-state), read-only | ~160 | Q3 (ObservationReference typing affects the declared output type), Q5, Q6 |
| C2 | **`feat(factlayer): add RawOutput and Observation records (RFC-0005 §2)`** | `RawOutput` + `Observation` + truncation marker; `ObservationReference` replacement per Q3 | ~120 | Q3, Q10 |
| C3 | **`feat(factlayer): run Collectors to produce Observations (RFC-0005 §2; RFC-0004 §4.5)`** | `collect` entry point: run a Collector, record output/exit/truncation; never mutates (A4) | ~180 | Q3, Q7 |
| C4 | **`feat(factlayer): deterministic normalization (RFC-0005 §2; F5)`** | `normalize(Observation, FamilyProfile) -> Fact`; Unknown on failure; F1 behavioral gate | ~200 | Q2 (Scope category), Q4 |
| C5 | **`feat(factlayer): provenance and freshness computation (RFC-0005 §5, §12)`** | provenance attached at normalization (F10); freshness state bookkeeping (F14, F15) | ~140 | Q3, Q2 (freshness-per-category) |
| C6 | **`feat(factlayer): Fact status store and invalidation (RFC-0005 §4, §7)`** | in-memory current set; Observed/Unknown/Unavailable/Unsupported; supersession by §6 identity; Invalid fail-closed (F11, F16) | ~220 | Q8, Q9, Q11 |
| C7 | **`test(factlayer+collectors): Layer-2 conformance and F-invariant suite`** | conformance (imports, no I/O at import, no forbidden edges) + F1/F5/F6/F7/F8/F10/F11 + A4 no-mutation + Scenario 30 status | ~220 | C1–C6 |
| C8 | **`docs: record Iteration 3 clarifications and conformance mapping`** | update `docs/implementation-consistency-report.md` (type→owner map, ratified answers, open items) | ~130 | C7 |

**Atomic order:** C1 → C2 → C3 → C4 → C5 → C6 → C7 → C8. A **docs-ratification
commit** precedes C1 once Q1–Q12 are answered and recorded as decision notes
(DN-13…, mirroring Iterations 1–2). Total pipeline LOC ≈ 1040 over 8 commits,
each <300.

---

## 13. Final readiness assessment

Per commit (design-review-only; no code is written by this review):

| Commit | Status | Reason |
|---|---|---|
| C1 | **Blocked** | Q3 (declared output typing), Q5 (baseline set), Q6 (granularity) |
| C2 | **Blocked** | Q3 (ObservationReference replacement) |
| C3 | **Blocked** | Q3, Q7 (output bound) |
| C4 | **Blocked** | Q2 (Scope category binding), Q4 (confidence on failure) |
| C5 | **Blocked** | Q3, Q2 (freshness-per-category) |
| C6 | **Blocked** | Q8 (in-memory only), Q9 (supersession identity), Q11 (critical failure) |
| C7 | **Blocked** | depends on C1–C6 |
| C8 | **Blocked** | depends on C7 |

Overall: **Blocked pending ratification of Q1–Q12** (mirroring the Iteration 1
and 2 pattern — questions are answered and recorded as decision notes before
implementation). Q3, Q2, and Q5 are the highest-leverage decisions: Q3 fixes
the `schema` surface without violating Layer 0; Q2 fixes whether `schema.Scope`
changes; Q5 fixes the baseline Collector set. None of the twelve is resolvable
from the corpus alone (each names a Draft RFC, a future RFC, or an explicit
deferral); **no ambiguity is silently resolved by this review.**

---

# Consistency review against the Blueprint and governing RFCs

This review was checked against the blueprint, RFC-0000–0013, RFC-0021, the two
walkthroughs, the decision traceability matrix, and DN-1…DN-12.

**Consistent (passes):**

- **Module set.** `collectors/{registry}` and `factlayer/{collect,normalize,
  provenance,store}` match blueprint §2/§10 exactly; `test_packages.py`
  enforces it. No new module.
- **Dependency rules.** Both packages are Layer 2; `factlayer` imports only
  `collectors`/`schema`/`systemmodel` (+ stdlib); no forbidden edge; `trust`
  not imported (DN-7); acyclic (allowed graph + observed graph).
- **Iteration scope and RFC basis.** Scope, work, DoD, and RFC basis are
  transcribed from blueprint §8.4.
- **Ownership.** Every artifact has exactly one owner (§2); the two-owner
  checks (RFC-0004 §4.5/§4.6 split; blueprint §10) hold.
- **Gate.** Iteration 3 produces the pipeline as scaffold + conformance tests;
  production code begins only after RFC-0015/0019/0020 and the Draft RFCs are
  Accepted (blueprint §8.0; RFC-0000 §5).
- **Decision notes.** DN-1 (in-memory types, no formats/APIs) honored; DN-2 (F1
  behavioral complement) implemented as the normalization gate; DN-7 (`trust`
  deferred) honored — no `trust` import; DN-9 (FactCategory type/meaning split)
  preserved — Scope stays category-free unless Q2 says otherwise.
- **Walkthroughs.** Failure-injection Scenario 30 is realized at the *status*
  level (Unsupported), with the fail-closed decision in `core` (RFC-0002 §2.3).
  Core-execution Stage 9 (Fact normalization) is the integration oracle for the
  normalize path.
- **Initialization order.** `collectors`/`factlayer`-after-`systemmodel`
  (Iteration 2), before `verification` (Iteration 4), matches blueprint
  §8.3→§8.4→§8.5 and RFC-0000 §7.

**Inconsistent / required attention (reported, not resolved):**

1. **`ObservationReference` replacement (Q3).** The Iteration 1 placeholder
   promises replacement "with zero semantic changes to Provenance," but the
   real `Observation` model is Layer 2 (`factlayer`) and `schema` is Layer 0.
   The typing of `schema.Provenance.observation` is the single structural
   question of the iteration.
2. **FactCategory/Scope binding (Q2).** DN-9 deferred it to "Iteration 3+" —
   this iteration is the natural candidate, but binding it changes `schema.Scope`
   (a Layer-0 surface), which must be ratified, not assumed.
3. **Baseline Collector set (Q5).** Blueprint §8.4 says "distro, kernel, package
   state"; RFC-0021 §5.2 constrains package-state to the two Native ecosystems.
   The exact baseline set is a ratification decision.

**Ownership conflicts found:** none beyond the reported Q3 (Observation
reference) and Q2 (Scope category) surface questions — both reported, neither
resolved. **Circular dependencies found:** none. **Authority leaks found:**
none — `collectors` holds Observe, `factlayer` holds Observe/Normalize; neither
holds any forbidden authority (RFC-0004 §7). **Hidden implementation decisions
detected and surfaced:** Q1–Q12.

**Verdict.** The design review **passes as a translation**: it adds no
architecture, invents no behavior, respects the gate, and reports every
ambiguity to its owning document (blueprint §0, §11). Implementation of
Iteration 3 is **blocked** until Q1–Q12 are answered and recorded as decision
notes, exactly as Iterations 1 and 2 were ratified before implementation.
