# Implementation Consistency Report

Tracks each implemented iteration against the frozen corpus: what was built,
which RFC owns each type, which ambiguities were ratified, and what remains
deferred. Iteration 0 bootstrapped the repository skeleton; Iteration 1
implemented the `schema` package. This report is updated at the end of each
iteration and verified against `docs/architecture-implementation-blueprint.md`
and `docs/iteration-1-design-review.md`.

---

## Iteration 0 — Repository bootstrap

Scope: Repository bootstrap (`docs/architecture-implementation-blueprint.md`
§8.1). Every file below is docstring-only scaffold; no production code (gate
statement, blueprint §8.0). This report maps each generated file to its
architectural owner and normative source.

### Package skeleton (src/episky/)

The tree is a translation of RFC-0001 §5 components plus cross-cutting packages
(blueprint §2). Package-level ownership:

| Package | Owning RFC(s) | Modules |
|---|---|---|
| `schema` | RFC-0005 §3/§4/§5/§12; RFC-0003 §2; RFC-0006 §7 | `fact`, `action`, `outcome` |
| `systemmodel` | RFC-0021 | `profiles`, `subsystems` |
| `trust` | RFC-0007 | `classes`, `sanitize`, `hostile` |
| `collectors` | RFC-0005 §2; RFC-0003 §2.4; RFC-0021 | `registry` |
| `factlayer` | RFC-0005 | `collect`, `normalize`, `provenance`, `store` |
| `verification` | RFC-0006 | `compare`, `outcome` |
| `secrets` | RFC-0009 | `classify`, `redact`, `store` |
| `policy` | RFC-0008 | `classify`, `gates`, `tokens`, `policy` |
| `executor` | RFC-0004 §4.9; RFC-0002 §2.8 | `runner`, `guards`, `elevation` |
| `audit` | RFC-0013 | `records`, `store`, `transcript` |
| `context` | RFC-0012 | `assemble`, `boundaries`, `memory`, `provider_view` |
| `providers` | RFC-0010 | `contract`, `view`, `adapters` |
| `skills` | RFC-0011 | `loader`, `activation`, `runtime` |
| `core` | RFC-0002; RFC-0004 §4.3 | `session`, `state_machine`, `events`, `loop`, `consultation`, `replan`, `recovery` |
| `cli` | RFC-0001 §5; RFC-0015 (future) | `render`, `collect`, `expose` |

Count: 64 files (16 package `__init__.py` + 47 modules + root `__init__.py`),
matching blueprint §2 exactly. No module exists outside the blueprint tree, and
every file the blueprint requires exists — verified by
`tests/test_packages.py::test_tree_matches_blueprint_exactly`.

### Docstring-only scaffold

Each file carries a module docstring stating its owning RFC, its
responsibility, and its forbidden responsibility (blueprint §3, §10). No
signatures, no behavior, no TODOs. Signatures are owned by RFC-0020 and will be
introduced in later iterations.

### Tooling & conformance harness

| File | Purpose | Normative basis |
|---|---|---|
| `pyproject.toml` | packaging (setuptools src layout), ruff + pytest config | RFC-0020 (implementation); blueprint §2 |
| `.pre-commit-config.yaml` | ruff lint/format + repo hygiene hooks | blueprint §8.1 (tooling) |
| `.github/workflows/ci.yml` | CI: lint, test, build, RFC validator gate | blueprint §8.1; AGENTS.md; tools/README.md |
| `.gitignore` | Python/venv/build artifact excludes | infra |
| `tests/test_packages.py` | imports every package/module; enforces blueprint §2 tree | blueprint §2, §10 |
| `tests/test_dependency_rules.py` | import-lint: §4.1 allowed edges, §4.2 forbidden edges | blueprint §4.1, §4.2; RFC-0004 §7 |

Dependency rules are transcribed verbatim from blueprint §4.1/§4.2. The §4.2
authority qualifiers (e.g. `policy (decision)`, `factlayer (create)`,
`secrets (values)`) are *use* restrictions, not import bans; those targets
remain import-allowed per §4.1 (see test file comment).

### Test mapping (blueprint §7)

| Test focus | Implemented in |
|---|---|
| Whole-repo: validator exits 0 after `rfc/`/`tools/` change | CI job `rfc-validation` |
| Import smoke (package tree exists and imports) | `tests/test_packages.py` |
| Cross-cutting dependency boundary (forbidden edges, §4.2) | `tests/test_dependency_rules.py` |
| Invariant conformance tests (state machine, F/V/I/A/SC/SK/PR/CM invariants) | deferred to iterations 1+ per §7 table |

The 31 failure-injection scenarios and the happy-path integration test
(blueprint §7 cross-cutting policy) are deferred to the iterations that own the
responsible packages, per `docs/failure-injection-walkthrough.md` and
`docs/core-execution-walkthrough.md`.

---

## Iteration 1 — the `schema` package (blueprint §8.2)

Scope: canonical types as the shared vocabulary — `schema` only. Definition of
Done: type-level invariant tests pass and `schema` has zero imports beyond
stdlib (blueprint §8.2). No behavior, no serialization, no APIs; exact
signatures are RFC-0020's (DN-1).

### Commits

The design-review plan's Commit 5 was **cancelled** (DN-3); Commits 6 and 7
merged into one atomic commit (Decisions 3–6).

| Commit | Content | RFC basis |
|---|---|---|
| `38eee86` | `FactStatus`; `Freshness`/`FreshnessState` | RFC-0005 §4, §12 |
| `552f77d` | `Provenance`, `Collector`, `ConfidenceSource`, `ObservationReference` | RFC-0005 §5 |
| `7580ba8` | `Subject`, `Property`, `Value`, `Scope`, `MachineIdentity` | RFC-0005 §3, §11 |
| `880bd47` | `Fact` (the composition); F1/F2/F3/F10 type-level tests | RFC-0005 §3, §13 |
| — | Commit 5 (`FactCategory`) **cancelled** — no code | DN-3 |
| `3c91e1d` | `Action`, `Step`, `Proposal`, `Plan`, `PostCondition`, `VerificationOutcome` | RFC-0003 §2.6; RFC-0006 §5, §7 |
| `528b65c` | Conformance harness: stdlib-only, Layer 0, no-logic, ownership, acyclicity | blueprint §8.2, §4.1 |

### Public type surface

Each module's `__all__` is exactly the canonical vocabulary its owning RFC
assigns (blueprint §10; enforced by `tests/test_schema_conformance.py`).

| Module | Public surface |
|---|---|
| `fact` | `Collector`, `ConfidenceSource`, `Fact`, `FactStatus`, `Freshness`, `FreshnessState`, `Property`, `Provenance`, `Scope`, `Subject`, `Value` |
| `action` | `Action`, `Plan`, `PostCondition`, `Proposal`, `Step` |
| `outcome` | `VerificationOutcome` |

Enumerations: `FactStatus` (8: Observed, Verified, Unknown, Unavailable,
Unsupported, Contradicted, Stale, Invalid); `FreshnessState` (5: Current,
Possibly stale, Stale, Expired, Unknown freshness); `VerificationOutcome` (8:
Verified Success, Verified Failure, Partially Successful, No Observable Change,
Unknown, Contradicted, Interrupted, Expired).

### Internal placeholder types and future owners

Deliberately excluded from `__all__`; internal Iteration 1 markers only.

| Type | Module | Purpose | Future owner |
|---|---|---|---|
| `MachineIdentity` | `fact` | opaque machine identity reference; contents never defined here (RFC-0005 §11) | RFC-0014 (does not exist) |
| `ObservationReference` | `fact` | reference to the Observation a Provenance names (RFC-0005 §5) | RFC-0005 §2 pipeline / Iteration 3 (`factlayer`) |

### Type → owning RFC section mapping

| Type | Module | Owning RFC section(s) |
|---|---|---|
| `Collector` | `fact` | RFC-0005 §5; RFC-0003 §2.4 |
| `ConfidenceSource` | `fact` | RFC-0005 §3 |
| `Fact` | `fact` | RFC-0005 §3, §13 |
| `FactStatus` | `fact` | RFC-0005 §4 |
| `Freshness`, `FreshnessState` | `fact` | RFC-0005 §12 |
| `Property` | `fact` | RFC-0005 §3 |
| `Provenance` | `fact` | RFC-0005 §5 |
| `Scope` | `fact` | RFC-0005 §3 (category, §10: deferred, DN-3) |
| `Subject`, `Value` | `fact` | RFC-0005 §3 |
| `Action` | `action` | RFC-0003 §2.6; RFC-0008 §5 |
| `Plan` | `action` | RFC-0003 §2.6 |
| `PostCondition` | `action` | RFC-0006 §5; RFC-0003 §2.5 (DN-4) |
| `Proposal` | `action` | RFC-0003 §2.6 |
| `Step` | `action` | RFC-0003 §2.6; RFC-0008 §5; RFC-0006 §4 |
| `VerificationOutcome` | `outcome` | RFC-0006 §7 |

### Ratified implementation decisions (DN-1 … DN-6)

Full text in `docs/implementation-decision-notes.md`; summary:

| Note | Decision | Answers §17 |
|---|---|---|
| DN-1 | In-memory domain types only; RFC-0020 exclusively owns formats, serialization, and API signatures | #7 |
| DN-2 | F1 enforced structurally in Iteration 1, behaviorally in Iteration 3; complementary, never substitutes | #6 |
| DN-3 | No `FactCategory` in Iteration 1; RFC-0021 is the sole owner; `Scope` stays category-free; no placeholders | #3 |
| DN-4 | `PostCondition` is a `schema` pure data type; verification owns semantics only | #4 |
| DN-5 | `VerificationOutcome` carries all eight RFC-0006 §7 values; five-value blueprint wording superseded | #1 |
| DN-6 | Only `VerificationOutcome` in Iteration 1; no `GoalOutcome` | #2 |

### §17 ambiguity resolutions

All seven design-review §17 questions are ratified; none remains open.

| §17 Q | Subject | Resolution |
|---|---|---|
| 1 | Outcome cardinality (8 vs 5) | All eight RFC-0006 §7 values (DN-5) |
| 2 | Goal-level Outcome sense | Only `VerificationOutcome`; Goal-level deferred to `core` (DN-6) |
| 3 | Category binding / `FactCategory` | Deferred to Iteration 2; RFC-0021 sole owner; no placeholder (DN-3) |
| 4 | Postcondition ownership | `PostCondition` in `schema/action.py`, pure data (DN-4) |
| 5 | Observation reference form | `ObservationReference` placeholder in `552f77d`; reference, never the pipeline's Observation model |
| 6 | F1 test scope | Type-level structural F1 test agreed for Iteration 1 (DN-2) |
| 7 | Type/signature boundary | Type surface only; RFC-0020 owns signatures (DN-1) |

### Deferred items and future owners

None is silently dropped; each is recorded with its owner (already fixed by the
corpus — nothing new is decided here).

| Deferred item | Owning future RFC / iteration |
|---|---|
| `FactCategory` and category binding | RFC-0021 (Draft); Iteration 2 (`systemmodel`) — DN-3 |
| `MachineIdentity` contents | RFC-0014 |
| Real `Observation` model | RFC-0005 §2 pipeline; Iteration 3 (`factlayer`) |
| Fact Identifier form/generation | RFC-0020 (design review §16 #9) |
| Freshness-bound values and representation | RFC-0020 (design review §16 #8) |
| Fact Identity, lifetime, relationships, Evidence Sets (RFC-0005 §6–§9) | Iteration 3 (`factlayer`) |
| Goal-level Outcome (RFC-0003 §2.3) | `core`; later iteration — DN-6 |
| Verification semantics: PostCondition evaluation, Compare, Outcome determination (RFC-0006 §6, §9, §12) | Iteration 4 (`verification`) — DN-4 |
| Preconditions re-validation and risk classification (RFC-0008 §6, §9) | Iterations 6/10 (`policy`, `core`) |
| Behavioral enforcement of F1–F3, F10 | Iterations 3–4 (DN-2) |
| Serialization, wire/persistence formats, builders, factories, API signatures | RFC-0020 (DN-1) |

### Conformance verification

The implementation still matches the blueprint and the design review:

- **Tree** matches blueprint §2 exactly — `test_packages.py` (unchanged).
- **Dependency rules** (§4.1/§4.2) hold; the declared allowed graph and the
  observed import graph are both acyclic — `test_dependency_rules.py`.
- **`schema` is Layer 0** with zero imports beyond stdlib and intra-package
  modules (blueprint §8.2 DoD) — `test_schema_conformance.py`.
- **`schema` carries no implementation logic** — only type declarations
  (blueprint §2 "No behavior") — `test_schema_conformance.py`.
- **Ownership boundaries** (blueprint §10) enforced: each module's public
  surface is exactly its owning RFC's vocabulary, defined by that module —
  `test_schema_conformance.py`; ownership docstrings — `test_packages.py`.
- **Type-level invariant conformance**: F1/F2/F3/F10/F12/F13 and F11
  distinctness (RFC-0005 §13) — `test_schema_fact.py`; Action/Step/Proposal/
  Plan/PostCondition surface (RFC-0003 §2.6) — `test_schema_action.py`;
  Outcome exhaustive + exclusive, no GoalOutcome (RFC-0006 §7) —
  `test_schema_outcome.py`.
- **Full suite:** 320 tests pass; ruff, format, build, and pre-commit are
  clean.

No RFC was modified, no production code outside `schema` was touched, and no
architecture was added. The `schema` package is complete per blueprint §8.2
and the design review.

---

## Iteration 2 — ratification and consistency review (pre-implementation)

Iteration 2 implements the **System Model layer** (`systemmodel`, RFC-0021) plus
an additive `schema` change (DN-9). Scope, DoD, and RFC basis are transcribed
from blueprint §8.3 (systemmodel half). The full design review is
`docs/iteration-2-design-review.md`; the ratified decisions are DN-7…DN-12 in
`docs/implementation-decision-notes.md`.

### Short architectural consistency review

The ratified Iteration 2 decisions were checked against the frozen corpus. The
result is **consistent**: no RFC is modified, Layer-0 constraints hold, and no
ownership changes beyond what the ratification assigns.

- **Scope (DN-7).** Iteration 2 = `systemmodel` only; `trust` is deferred to its
  own design review. Blueprint §4.1 (layers), §7 (trust DoD), and the `trust`
  package are untouched. The blueprint §8.3 iteration pairing is a scheduling
  statement, not an architecture rule; splitting the iteration changes no
  dependency edge and no ownership.
- **FamilyStatus (DN-8).** Five values including Experimental. Consistent with
  RFC-0021 §2.2 (Immutable row), §2.4, and §5.1; the §2.1 four-word table is
  read as supplemented, not contradicted. No §2.1 meaning is weakened.
- **FactCategory type/semantics split (DN-9, amends DN-3).** The enum type lives
  in `schema` (Layer 0, stdlib-only, type only); `systemmodel` owns the
  category→subsystem and category→state-domain mappings and the meaning. This
  satisfies RFC-0005 §10 ("category membership follows RFC-0021"), preserves
  DN-3's "RFC-0021 sole owner" for semantics, keeps `Scope` category-free
  (the §10 "part of Scope" binding is deferred), and keeps Layer 0 intact
  (an enum needs no imports). No Accepted RFC is modified (RFC-0005/0021 Draft).
- **Import edge (DN-11).** `systemmodel`→`schema` is an authorized blueprint
  §4.1 edge; using it for `schema.FactCategory` adds no new dependency.
- **Category set (DN-10).** RFC-0005 §10's 12 categories; the
  Users↔Configuration reconciliation is mapping data, not an RFC change.
- **Profile (DN-12).** The full §2.3 five-dimension set as descriptive data;
  matches blueprint §7 ("profile data only") and §8.3 DoD (profile lookup for
  Supported families).
- **Gates.** No production behavior is introduced; vocabulary + data only
  (blueprint §8.0). `systemmodel` stays Layer 1; its modules stay
  `[profiles, subsystems]`; dependency-rule and package-tree tests remain green.

**Residual open items (reported, not resolved):** A6 (encoding §6.9
independence as data), A7 (§4.14 summary graph vs §4.2–§4.13 clauses), A8
(class-vs-family members: Immutable, Other distros), A9 (Draft rework risk).
These are owned by RFC-0021 (Draft) and do not block Iteration 2.

### Ratified decisions (DN-7 … DN-12)

| Note | Decision | Resolves |
|---|---|---|
| DN-7 | Iteration 2 = `systemmodel` only; `trust` deferred to its own review | §16 A10 / Q1 |
| DN-8 | `FamilyStatus` five-valued, incl. Experimental | §16 A1 / Q2 |
| DN-9 | `FactCategory` type in `schema`; semantics owned by `systemmodel`; amends DN-3 | §16 A4 / Q3 |
| DN-10 | Category set = RFC-0005 §10's 12; reconciliation via mapping | §16 A2 / Q5 |
| DN-11 | `systemmodel` uses the `schema` import edge | §16 A5 / Q4 |
| DN-12 | `FamilyProfile` carries the full §2.3 descriptive set | §16 A3 / Q6 |

### Conformance verification

- Baseline unchanged and green before implementation: **320 tests pass**; ruff,
  format, build, and pre-commit clean.
- No source or test file changes accompany this ratification record; the
  implementation commits follow, one atomic commit at a time.

---

## Known limitation

Blueprint §8.1 Definition of Done requires the validator to "exit 0 on the
current corpus". The validator currently reports one pre-existing error in the
frozen corpus:

```
rfc/RFC-0004-trust-and-authority-model.md:470: ERROR unknown invariant identifier 'S1'
```

RFC-0004 is Accepted and normative; fixing it requires an RFC-0003 amendment,
so it is out of scope for Iteration 0 and Iteration 1 (no edits to accepted
RFCs, per AGENTS.md hard rule 1). The validator is wired into CI as-is; the CI
gate is expected to fail until the corpus is amended. It is unrelated to the
`schema` package and to Iteration 1.
