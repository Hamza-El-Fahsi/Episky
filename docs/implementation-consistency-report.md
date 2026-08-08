# Implementation Consistency Report

Tracks each implemented iteration against the frozen corpus: what was built,
which RFC owns each type, which ambiguities were ratified, and what remains
deferred. Iteration 0 bootstrapped the repository skeleton; Iteration 1
implemented the `schema` package; Iteration 2 implemented the `systemmodel`
layer plus the ratified `schema` change (DN-9); Iteration 3 implemented the
`factlayer` + `collectors` pipeline (blueprint §8.4); Iteration 4 implemented
the `verification` layer (blueprint §8.5, DN-25…DN-34); Iteration 5 implemented
the `trust` layer (blueprint §8.3 trust half, RFC-0007, DN-35…DN-39); Iteration
6 implemented the `secrets` layer (RFC-0009; blueprint §8.6 re-ordered by
DN-35/DN-40; DN-40…DN-44). This
report is updated at the end of each iteration and verified against
`docs/architecture-implementation-blueprint.md`, the design reviews, and the
decision notes.

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

## Iteration 2 — the `systemmodel` layer plus the `schema.FactCategory` change

Iteration 2 implements the **System Model layer** (`systemmodel`, RFC-0021) plus
an additive `schema` change (DN-9). Scope, DoD, and RFC basis are transcribed
from blueprint §8.3 (systemmodel half; `trust` is deferred per DN-7). The full
design review is `docs/iteration-2-design-review.md`; the ratified decisions are
DN-7…DN-12 in `docs/implementation-decision-notes.md`. Plan Commit 7b
(`CATEGORY_SUBSYSTEMS` / `CATEGORY_STATE_DOMAINS` mapping data) remains
unimplemented and is recorded under "Remaining deferred items" below.

### Commits

| Commit | Content | RFC basis |
|---|---|---|
| `e6ef5e7` | Docs ratification: design review answers (Q1–Q6), DN-7…DN-12, decision notes | design review §17; DN-7…DN-12 |
| `7dcd1c5` | `FamilyStatus` (5, DN-8), `DistributionFamily` (8), `FAMILY_STATUS` | RFC-0021 §2.1, §2.2 |
| `9b81f45` | `PackageEcosystem` (8), `EcosystemStatus` (4), `ECOSYSTEM_STATUS` | RFC-0021 §5.1, §5.2 |
| `70bf2a4` | `FamilyProfile` (frozen) + `FAMILY_PROFILES` (Supported/Planned only) | RFC-0021 §2.3, §3.1, §5, §6.2/§6.4, §7 (DN-12) |
| `b6dcb5c` | Profile string fix: four conservative values → `"not stated (RFC-0021)"` | RFC-0021 §2.3 (per-field values not stated) |
| `3c90535` | `MachineSubsystem` (12) | RFC-0021 §4.1, §4.2–§4.13 |
| `00fd904` | `SUBSYSTEM_DEPENDENCIES` (immutable mapping) | RFC-0021 §4.2–§4.13 |
| `aaa1999` | `StateDomain` (7) + `StateRepresentation` (frozen) + `SUBSYSTEM_STATE_REPRESENTATION` | RFC-0021 §6.2–§6.8, §6.10 |
| `3fed706` | `FactCategory` enum in `schema/fact.py` (12; type only) | RFC-0005 §10; DN-9, DN-10 |
| `c78d3b5` | Layer-1 conformance + ownership-boundary tests | blueprint §4.1, §4.2, §8.2, §10; design review §11, plan Commit 8 |
| (this commit) | Iteration 2 consistency report completion | plan Commit 9 |

### Final type → owning RFC mapping

| Type | Module | Owning RFC section(s) | Protected by |
|---|---|---|---|
| `FamilyStatus` | `systemmodel/profiles` | RFC-0021 §2.1, §2.2 (DN-8) | supported-platform promise (§1.3) |
| `DistributionFamily` | `systemmodel/profiles` | RFC-0021 §2.2 | supported-platform promise (§1.3) |
| `FamilyProfile` | `systemmodel/profiles` | RFC-0021 §2.3 (DN-12) | supported-platform promise (§1.3) |
| `FAMILY_STATUS`, `FAMILY_PROFILES` | `systemmodel/profiles` | RFC-0021 §2.2, §2.3 | supported-platform promise (§1.3) |
| `PackageEcosystem`, `EcosystemStatus`, `ECOSYSTEM_STATUS` | `systemmodel/profiles` | RFC-0021 §5.1, §5.2 | ecosystem statuses |
| `MachineSubsystem` | `systemmodel/subsystems` | RFC-0021 §4.1–§4.13 | subsystem boundaries |
| `SUBSYSTEM_DEPENDENCIES` | `systemmodel/subsystems` | RFC-0021 §4.2–§4.13, §4.14 | subsystem boundaries |
| `StateDomain` | `systemmodel/subsystems` | RFC-0021 §6.2–§6.8 | no two-owner representation rule |
| `StateRepresentation`, `SUBSYSTEM_STATE_REPRESENTATION` | `systemmodel/subsystems` | RFC-0021 §6.10 | no two-owner representation rule |
| `FactCategory` (enum) | `schema/fact` | RFC-0005 §10 (type only; DN-9) | category set per DN-10 |

### Final public API surface of systemmodel

Each module's `__all__` is exactly the canonical vocabulary its owning RFC
assigns (design review §11; enforced by
`tests/test_systemmodel_conformance.py`).

| Module | Public surface |
|---|---|
| `profiles` | `DistributionFamily`, `ECOSYSTEM_STATUS`, `EcosystemStatus`, `FAMILY_PROFILES`, `FAMILY_STATUS`, `FamilyProfile`, `FamilyStatus`, `PackageEcosystem` |
| `subsystems` | `MachineSubsystem`, `SUBSYSTEM_DEPENDENCIES`, `SUBSYSTEM_STATE_REPRESENTATION`, `StateDomain`, `StateRepresentation` |

Enumerations: `FamilyStatus` (5: Supported, Planned, Experimental, Unsupported,
Out of Scope); `DistributionFamily` (8: Debian, Red Hat, Arch, openSUSE,
Immutable, Other distros, Non-Linux, Android); `PackageEcosystem` (8: apt/dpkg,
dnf/rpm, pacman, zypper, nix, flatpak, snap, appimage); `EcosystemStatus` (4:
Native, Secondary, Experimental, Unsupported); `MachineSubsystem` (12: Hardware,
Boot, Kernel, Users, Services, Storage, Filesystems, Packages, Networking,
Security, Logs, Applications); `StateDomain` (7: Package, Service, Configuration,
Filesystem, Network, User, Security). `schema.FactCategory` (12) is documented
in the Iteration 1 surface table (module `fact`).

### Ownership boundaries

- `profiles.py` owns only RFC-0021 §2/§5 profile vocabulary.
- `subsystems.py` owns only §4/§6 subsystem/State-Domain vocabulary.
- `schema` owns the `FactCategory` **type**; RFC-0021/`systemmodel` owns every
  category **meaning** (mapping data; DN-9). No name is owned by two modules
  (enforced by `test_systemmodel_conformance.py`).
- `StateRepresentation` is the frozen in-memory carrier for the §6.10 mapping,
  owned by `subsystems.py` like its sibling types.

### Layer-1 conformance summary

- Every `systemmodel` module imports only stdlib + the allowed `schema` edge
  (blueprint §4.1; `ALLOWED["systemmodel"] = {"schema"}`).
- No logic beyond vocabulary, immutable data types, and module-level data-table
  constants: no functions, control flow, comprehensions, parsing, serialization,
  or validation (AST no-logic scan; `test_systemmodel_conformance.py`).
- Data tables are module-level constants: `FAMILY_STATUS`, `FAMILY_PROFILES`,
  `ECOSYSTEM_STATUS` are dicts; `SUBSYSTEM_DEPENDENCIES` and
  `SUBSYSTEM_STATE_REPRESENTATION` are immutable (`MappingProxyType`).
- Dataclasses (`FamilyProfile`, `StateRepresentation`) are `frozen=True,
  slots=True`.

### Dependency graph confirmation

- Package graph unchanged and acyclic — `tests/test_dependency_rules.py` (§4.1
  allowed edges, §4.2 forbidden edges, declared + observed acyclicity) stays
  green.
- No reverse dependency: `schema` never imports `systemmodel` (explicit test in
  `tests/test_systemmodel_conformance.py`).
- The subsystem dependency graph (`SUBSYSTEM_DEPENDENCIES`) is model data, never
  imported (design review §12). It is a DAG per RFC-0021 §4.14; no traversal or
  acyclicity logic is encoded (data only, per the Commit 5 execution rules).

### Ratified decisions (DN-7 … DN-12)

| Note | Decision | Resolves | Embodied in |
|---|---|---|---|
| DN-7 | Iteration 2 = `systemmodel` only; `trust` deferred to its own review | §16 A10 / Q1 | scope of this iteration |
| DN-8 | `FamilyStatus` five-valued, incl. Experimental | §16 A1 / Q2 | `7dcd1c5` |
| DN-9 | `FactCategory` type in `schema`; semantics owned by `systemmodel`; amends DN-3 | §16 A4 / Q3 | `3fed706` (type); Commit 7b (meaning, deferred) |
| DN-10 | Category set = RFC-0005 §10's 12; reconciliation via mapping | §16 A2 / Q5 | `3fed706`; Commit 7b (mapping, deferred) |
| DN-11 | `systemmodel` uses the `schema` import edge | §16 A5 / Q4 | Commit 7b (deferred; edge allowed by blueprint §4.1) |
| DN-12 | `FamilyProfile` carries the full §2.3 descriptive set | §16 A3 / Q6 | `70bf2a4` |

### Implementation status of every planned commit

Plan Commits 1–9 of the design review §16/§18, with status:

| Plan | Commit | Status |
|---|---|---|
| Docs ratification | `e6ef5e7` | Done |
| 1 family/status vocabulary | `7dcd1c5` | Done |
| 2 ecosystem vocabulary | `9b81f45` | Done |
| 3 Family Profile + data | `70bf2a4`, `b6dcb5c` (fix) | Done |
| 4 machine subsystem vocabulary | `3c90535` | Done |
| 5 subsystem dependency graph | `00fd904` | Done (data table; no acyclicity logic) |
| 6 State Domain vocabulary + mapping | `aaa1999` | Done |
| 7 `FactCategory` enum | `3fed706` | Done |
| 7b category→subsystem/domain mapping | — | **Not implemented** (deferred; see below) |
| 8 Layer-1 conformance | `c78d3b5` | Done |
| 9 consistency report completion | this commit | Done |

### Remaining deferred items

| Deferred item | Owning future RFC / iteration | Notes |
|---|---|---|
| `CATEGORY_SUBSYSTEMS`, `CATEGORY_STATE_DOMAINS` mapping data keyed by `schema.FactCategory` | Plan Commit 7b; `systemmodel` | DN-9/DN-10/DN-11 ratified; the mapping is the semantic half of FactCategory and was not part of the implemented commit sequence |
| `Scope` category binding | Iteration 3+ (fact-model binding) | RFC-0005 §10 binding, not a type; DN-9 defers it |
| §6.9 independence/influence encoding | RFC-0021 (Draft); §16 A6 | explanatory, not normative; deliberately not encoded |
| §4.14 vs §4.2–§4.13 graph reconciliation | RFC-0021 (Draft); §16 A7 | consistency item, open |
| Class-vs-family members (Immutable, Other distros) | RFC-0021 (Draft); §16 A8 | open |
| Draft rework risk | RFC-0021 acceptance / amendment; §16 A9 | all Iteration 2 types against Draft wording |
| `trust` layer (T1–T12, S1–S8, Hostile) | RFC-0007; its own design review | DN-7 |
| Iteration 1 deferred items (MachineIdentity RFC-0014, Observation model, RFC-0020 signatures, etc.) | as recorded in the Iteration 1 section | unchanged |

### Known limitations

- `SUBSYSTEM_DEPENDENCIES` and `SUBSYSTEM_STATE_REPRESENTATION` are declared
  immutable at runtime (`MappingProxyType`), while the `profiles.py` data tables
  (`FAMILY_STATUS`, `FAMILY_PROFILES`, `ECOSYSTEM_STATUS`) are plain dicts —
  consistent with their design-review status as module-level constants (DN-1).
- The four `FAMILY_PROFILES` string values that the RFC does not state
  (`release_model` for Debian/Red Hat/openSUSE, `init_contract` for Arch) are
  recorded as `"not stated (RFC-0021)"` rather than inferred (`b6dcb5c`).
- The pre-existing validator error (RFC-0004 §470 `'S1'`) from Iteration 0/1 is
  unchanged and unrelated to Iteration 2.
- No commit in this iteration modifies any RFC; RFC-0005 and RFC-0021 remain
  Draft.

### Conformance verification

- **Tree** matches blueprint §2 exactly — `test_packages.py`.
- **Dependency rules** (§4.1/§4.2) hold; declared and observed graphs acyclic —
  `test_dependency_rules.py`.
- **`systemmodel` is Layer 1**: stdlib/`schema` imports only, no logic beyond
  vocabulary + data — `test_systemmodel_conformance.py`.
- **Ownership boundaries** (blueprint §10) enforced: public surface equals the
  design-review §11 map, defined by the owning module, no overlap —
  `test_systemmodel_conformance.py`.
- **Vocabulary conformance**: family (§2), ecosystem (§5), profile (§2.3),
  subsystem (§4.1), dependencies (§4.2–§4.13), State Domains (§6.2–§6.8), §6.10
  mapping — `tests/test_systemmodel_*.py`.
- **`schema.FactCategory`** (12, type only) — `tests/test_schema_fact_category.py`.
- **Full suite:** 396 tests pass; ruff, format, build, and pre-commit clean.

No RFC was modified, no production code outside `systemmodel`/`schema` was
touched, and no architecture was added beyond the ratified decisions. The
`systemmodel` layer is complete per blueprint §8.3 (systemmodel half) and the
design review, with the ratified Commit 7b mapping data deferred as recorded
above.

---

## Iteration 3 — the Fact Layer + Collectors pipeline

Iteration 3 implements the **Fact Layer + Collectors pipeline** (`factlayer` +
`collectors`, blueprint §8.4) — the Layer-2 implementation half of the
iteration. The full design review is `docs/iteration-3-design-review.md`; the
ratified decisions are DN-13…DN-24 in
`docs/implementation-decision-notes.md` (DN-13…DN-23 ratified at the
pre-implementation review; DN-24 recorded with the implementation review for
the C7 Scenario 30 realization). The pipeline is a **read-only scaffold**:
deterministic collection of Observations (C1–C3), deterministic normalization
into canonical Facts with provenance attached and freshness bookkeeping
(C4–C5), and an in-memory Fact store with supersession and invalidation (C6),
closed by a Layer-2 conformance and F-invariant suite (C7).

### Commits

| Commit | Content | RFC basis |
|---|---|---|
| `0f72345` | `CollectorSpec` + `COLLECTOR_SPECS` (baseline: distro, kernel, package-state) | RFC-0003 §2.4; RFC-0005 §2; DN-17 |
| `ed50971` | `RawOutput`, `Observation` (bounded output, truncation marker) | RFC-0005 §2; DN-18 |
| `e921133` | `collect()` — read-only run → Observation | RFC-0004 §4.5; RFC-0005 §2; A4 |
| `f726d20` | `normalize()` — deterministic Observation → Fact | RFC-0005 §2, §4, §5; F5; DN-16 |
| `5aa7071` | `build_provenance`, `freshness_state` | RFC-0005 §5, §12; F10; DN-21 |
| `71244a8` | `FactStore`, `record`, supersession + invalidation | RFC-0005 §6, §7, §13, §14; DN-19, DN-20, DN-22, DN-23 |
| `5061d59` | Layer-2 conformance + F-invariant suite (incl. Scenario 30 status) | design review §9.2, §9.3; F1/F5/F7/F8/F10/F11/F14/F15/F16; DN-24 |
| (this commit) | Iteration 3 consistency report completion | plan Commit C8 |

### 1. Iteration 3 implementation summary

Exactly what was implemented — no implementation beyond C7.

**Collectors** (`collectors/registry.py`)
- `CollectorSpec` — the frozen, slot-based Collector contract (RFC-0003 §2.4):
  one question, declared inputs, provenance behavior, declared output.
- `COLLECTOR_SPECS` — the read-only baseline registry (`MappingProxyType`):
  exactly three Collectors — distro, kernel, package-state (DN-17); it never
  constructs a `schema` type.

**Fact layer** (`factlayer/`)
- `RawOutput` — the bounded raw utterance of one Collector run (frozen).
- `Observation` — the timestamped, provenance-carrying record of one run
  (frozen): raw output, Collector identity, `collected_at`, exit status, and
  the truncation marker; a failed or inconclusive run still records (RFC-0002
  §4.2).
- `collect()` — the read-only entry point (A4): from a `CollectorSpec` + raw
  result + timestamp, build the immutable Observation, bounded with the
  truncation marker (DN-18); performs no system command and persists nothing.
- `normalize()` — the F1 gate: pure, deterministic, per-Observation
  Observation → Fact (F5); the Family Profile absorbs distro variance (F7);
  the only construction path to a Fact's components (DN-2); status reached per
  RFC-0005 §4 — Observed, Unknown (failed/unparseable, DN-16), Unsupported
  (not-supported family/ecosystem, DN-24).
- provenance — `build_provenance()` attaches provenance at normalization
  (F10; DN-23), answering the five §5 questions via the reference-only
  `ObservationReference` marker (DN-15).
- freshness computation — `freshness_state()` with the placeholder default
  bound (DN-14, DN-18): Current / Possibly stale / Stale; unknown freshness is
  never Current (F15).
- Fact Store — `FactStore` + `record()`: the in-memory current set for one
  machine (DN-19); supersession on RFC-0005 §6 component identity when fresher
  and at-least-as-strong evidence (DN-20); rule-violating Facts Invalid and
  disclosed, never admitted (F10, F12, F16); the four pipeline statuses
  Observed/Unknown/Unavailable/Unsupported supported and never collapsed (F11).

### 2. Type ownership table

Exact ownership (blueprint §10; enforced by `tests/test_factlayer_conformance.py`).

| Owner | Owns |
|---|---|
| `collectors` | `CollectorSpec`, `COLLECTOR_SPECS` |
| `factlayer.collect` | `RawOutput`, `Observation`, `collect` |
| `factlayer.normalize` | `normalize`, the canonical definitions (`CANONICAL_DEFINITIONS`) |
| `factlayer.provenance` | `build_provenance`, `freshness_state` |
| `factlayer.store` | `FactStore`, `StoreRecord`, the supersession rules (with `FactIdentity`, `RetiredFact`, `StoreOutcome`, and the reason constants) |
| `schema` (unchanged) | `Fact`, `Collector`, `Provenance`, `Scope`, `FactStatus`/`FreshnessState`, `Freshness`, `ObservationReference` marker |
| `systemmodel` (unchanged) | `FamilyProfile`, `MachineSubsystem`, `StateDomain`, and the other Iteration 2 vocabulary |

No name is owned by two modules; each public name is defined by its owning
module; the internal placeholders (`MachineIdentity`, `ObservationReference`,
`DEFAULT_OUTPUT_BOUND`, `DEFAULT_FRESHNESS_BOUND`) never appear in a public
surface (DN-15, DN-18).

### 3. Architectural conformance

Iteration 3 satisfies:

- **Blueprint §4.1** — Layer 2 edges only: `collectors` → {`schema`,
  `systemmodel`}; `factlayer` → {`collectors`, `schema`, `systemmodel`} (+ each
  package's own modules); the declared allowed graph and the observed import
  graph are both acyclic.
- **Blueprint §4.2** — no forbidden import: no `providers`, `executor`,
  `policy`, `skills`, `context`, `audit`, `secrets`, `trust`, or `verification`
  anywhere in the pipeline.
- **Blueprint §8.4** — scope is `factlayer` + `collectors` only.
- **Blueprint ownership map** — each module's public surface is exactly the
  vocabulary its owning RFC assigns; no ownership drift (design review §10 #7).
- **DN-13 … DN-24** — all ratified decisions honored (decision table above;
  DN-24 in the decision notes).
- **Layer boundaries** — `schema` and `systemmodel` never import the pipeline
  (no reverse edge; Layer 0/1 never depend on Layer 2).
- **Allowed imports** — stdlib + the authorized Layer-2 edges only; no
  I/O-, concurrency-, or persistence-capable stdlib is imported.
- **No forbidden imports** — none present.
- **No trust** — RFC-0007 T6 is consumed by normalization (the pipeline's only
  trust-upgrade step); no `trust` import (DN-7, DN-13).
- **No verification** — RFC-0006 stays blueprint §8.5 (Iteration 4; DN-13).
- **No persistence** — the store is the in-memory current set (DN-19); no
  filesystem/network/socket/sqlite imports; no `open`/`print`/`subprocess`
  calls at any scope (A4).
- **No authority leakage** — neither package holds Propose/Infer/Approve/
  Execute/Refuse/Persist; `collectors` holds Observe (RFC-0004 §4.5), `factlayer`
  holds Observe-as-consumer + Normalize (RFC-0004 §4.6).
- **No new dependency edges** — the package graph is unchanged and acyclic.

### 4. RFC traceability

| Commit | Content | RFC section(s) |
|---|---|---|
| C1 `0f72345` | `CollectorSpec`, `COLLECTOR_SPECS` | RFC-0003 §2.4; RFC-0005 §2 |
| C2 `ed50971` | `RawOutput`, `Observation` | RFC-0005 §2 |
| C3 `e921133` | `collect()` | RFC-0004 §4.5; RFC-0005 §2 |
| C4 `f726d20` | `normalize()` | RFC-0005 §2, §4, §5 |
| C5 `5aa7071` | provenance, freshness | RFC-0005 §5, §12 |
| C6 `71244a8` | Fact Store | RFC-0005 §6, §7, §13, §14 |
| C7 `5061d59` | Layer conformance + invariants | F1, F5, F7, F8, F10, F11, F14, F15, F16 |

### 5. Remaining deferred work

Recorded only; nothing is invented. Everything below belongs to later
iterations:

- **Iteration 4** — Verification (RFC-0006).
- **Iteration 5+** — Trust (RFC-0007).
- **RFC-0020 policy values** — output bounds, freshness-per-category bounds,
  signatures, formats, Fact Identifier (DN-1, DN-14, DN-18, DN-20).
- **Persistence** — durability and storage formats (DN-19; RFC-0012, RFC-0013).
- **Real orchestration** — the pipeline as a runtime path (session
  initialization prerequisites, core-execution Stage 9).
- **Real collectors** — executable, machine-facing inspectors.
- **Scheduler** — RFC-0002 runtime scheduling.
- **Execution engine** — RFC-0004 §4.9; Iteration 6+.
- **Core decisions** — the fail-closed disclose/ask decision on critical
  failure (DN-22) and the Scenario 30 refusal/ask decision (RFC-0002 §2.3).

### 6. Completion verdict

- Iteration 3 implementation is **complete**.
- **Layer 2 Definition of Done is satisfied** (blueprint §8.4; design review §9).
- **C1–C8 are complete.**
- Remaining work belongs to later iterations only.

### Conformance verification

- **Tree** matches blueprint §2 exactly — `test_packages.py`.
- **Dependency rules** (§4.1/§4.2) hold; declared and observed graphs acyclic —
  `test_dependency_rules.py`.
- **Layer-2 conformance** — imports, no I/O at import, no forbidden
  packages/stdlib, public surface == owned vocabulary, no placeholder leaks,
  frozen/slotted dataclasses, only `normalize` constructs a `Fact` —
  `test_factlayer_conformance.py`.
- **Behavioral invariants** — F1/F5/F7/F8/F10/F11/F14/F15/F16 and Scenario 30
  at the status level — `test_factlayer_invariants.py` and the C1–C6 suites
  (`tests/test_factlayer_*.py`, `tests/test_collectors_registry.py`).
- **Full suite:** 558 tests pass; ruff, format, build, and pre-commit are
  clean.

No RFC was modified, no production code outside `factlayer`/`collectors` was
touched (and within them only the C7-exposed Unsupported path in
`normalize.py`), and no architecture was added beyond the ratified decisions.
The `factlayer` + `collectors` pipeline is complete per blueprint §8.4 and the
design review.

---

## Iteration 4 — the Verification layer

Iteration 4 implements the **Verification Layer** (`verification`, blueprint
§8.5): deterministic Compare + Outcome semantics over already-normalized Facts,
closed by a Layer-2 conformance and V-invariant suite. The full design review
is `docs/iteration-4-design-review.md`; the ratified decisions are DN-25…DN-34
in `docs/implementation-decision-notes.md`. **The ratification unblocked
implementation**: none of the ten design-review questions (Q1–Q10) required an
RFC amendment, a `schema`/`systemmodel`/`factlayer`/`collectors` change, a new
module, or a new dependency edge, and all four planned commits (C1–C4) shipped.
The layer is a **pure, read-only scaffold** (V8, DN-27): it performs no Collect,
writes nothing to any store, and holds the Verify authority (RFC-0004 §4.6)
only.

### Commits

| Commit | Content | RFC basis |
|---|---|---|
| `866dbf5` | Docs ratification: design review answers (Q1–Q10), DN-25…DN-34, decision notes | design review §8, §9; DN-25…DN-34 |
| `bc3c4dd` | `compare` — per-Postcondition verdicts | RFC-0006 §6, §9 |
| `ac6da1d` | `outcome` — strictest-wins classification | RFC-0006 §7 |
| `a5fdf1a` | Layer-2 conformance + V-invariant suite | RFC-0006 §6, §7, §8, §13 |
| (this commit) | Iteration 4 consistency report completion | plan Commit C4 |

### 1. Implementation summary

Exactly what was implemented — no implementation beyond the plan.

**Compare** (`verification/compare.py`)
- `PostconditionVerdict` — the per-Postcondition verdict set (HELD /
  NOT_HELD / UNKNOWN / CONTRADICTED), exhaustive and mutually exclusive for
  one Postcondition (RFC-0006 §9).
- `PostconditionResult` — the verdict for one declared Postcondition plus the
  Facts that determined it (V11 evidence; empty when UNKNOWN); frozen,
  slot-based.
- `CompareResult` — one `PostconditionResult` per declared Postcondition in
  declared order (V6, V10); frozen, slot-based.
- `compare()` — the pure, deterministic Compare step (RFC-0006 §6, §9; V3):
  Facts are canonical-sorted; each Postcondition is evaluated over exactly the
  Facts in its scope — the same Subject and Property (§9.7, DN-28). A Fact is
  comparable only when its status is Observed or Verified (DN-26) and its
  freshness state is Current — factlayer's own determination (V4, F14/F15,
  DN-32); `PostCondition.freshness` is the declared bound (RFC-0006 §5). No
  comparable evidence → UNKNOWN (V9, V14). Contradiction is a
  comparison-level rule: a Contradicted-status Fact wins, else conflicting
  comparable values over the same Subject+Property → CONTRADICTED (DN-33, V7).

**Outcome** (`verification/outcome.py`)
- `OutcomeRecord` — the in-memory Outcome result (RFC-0006 §7 rule 4): the
  Outcome plus the Facts that determined it (V11, DN-34); fields exactly
  `outcome` + `evidence`; no confidence field (DN-30); frozen, slot-based.
- `determine()` — the pure Outcome step (RFC-0006 §7): exactly one of the
  eight `VerificationOutcome` values by the strictest-wins precedence (§7
  rule 2) — Contradicted > Verified Failure > Unknown > Partially Successful
  > Verified Success; reported verbatim, no silent upgrade (§7 rule 3); empty
  Compare → Unknown (V14, fail-closed); never success without fresh Facts (V5,
  V9); partial success is a distinct Outcome (V6); no confidence changes the
  Outcome (V15, DN-30); never produces Interrupted or Expired (DN-31); no
  store write (V8, DN-27).

### 2. Type ownership table

Exact ownership (blueprint §10; enforced by
`tests/test_verification_conformance.py`).

| Owner | Owns |
|---|---|
| `verification.compare` | `PostconditionVerdict`, `PostconditionResult`, `CompareResult`, `compare` |
| `verification.outcome` | `OutcomeRecord`, `determine` |
| `verification` | package surface (`compare`/`outcome`); RFC-0006 §6 process contract |
| `schema` (unchanged) | `PostCondition`, `VerificationOutcome`, `Fact`/`FactStatus`/`Freshness` (DN-4, DN-5) |

No name is owned by two modules; each public name is defined by its owning
module. The DN-4/DN-5 two-owner boundary is honored: `schema` owns the
`PostCondition`/`VerificationOutcome` types, `verification` owns the Compare
evaluation and the Outcome classification semantics.

### 3. Architectural conformance

- **Blueprint §4.1** — Layer-2 edges only: `verification` → {`factlayer`,
  `schema`, `systemmodel`} (+ stdlib); the declared allowed graph and the
  observed import graph are both acyclic. In practice only the `schema` edge
  is used today (DN-28 makes scope implicit; DN-27 forbids the store) — the
  `factlayer`/`systemmodel` edges are allowed but not required.
- **Blueprint §4.2** — no forbidden import: no `providers`, `executor`,
  `policy`, `skills`, `context`, `audit`, `secrets`, `trust`, `core`, `cli`
  anywhere in the layer (V3; never the LLM's or a Skill's assessment; the
  Executor never verifies itself, RFC-0004 §4.9).
- **Blueprint §8.5** — scope is `verification` only (DN-25): Compare + Outcome
  semantics over normalized Facts; no Collect invocation, no Precondition
  modeling, no orchestration.
- **No I/O, no persistence, no mutation** — no filesystem/network/socket/
  sqlite stdlib imports; no `open`/`print`/`exec`/`subprocess` calls at any
  scope; frozen, slot-based results; Compare/Outcome are pure (V8, DN-27).
- **No authority leakage** — `verification` holds Verify (RFC-0004 §4.6)
  only; never Propose/Infer/Approve/Execute/Refuse/Persist.
- **Package tree** — exactly `verification/{__init__,compare,outcome}.py`
  (blueprint §2); no new module (`test_packages.py` unchanged).

### 4. RFC traceability

| RFC | Section | Implemented as |
|---|---|---|
| RFC-0006 | §5 Postconditions | Consumes `schema.PostCondition` (DN-4) as the fixed expected state (V10); `PostCondition.freshness` is the declared bound (DN-32) |
| RFC-0006 | §6 Verification Process | The Compare→Outcome steps as pure functions over normalized Facts; Collect/Normalize are `factlayer`'s (DN-25) |
| RFC-0006 | §7 Outcome Model | Deterministic mapping to the eight `VerificationOutcome` values; strictest-wins (§7 rule 2); verbatim, no silent upgrade (§7 rule 3) |
| RFC-0006 | §8 Contradictions | Comparison-level conflict rule (DN-33); Contradicted stops the path (V7) |
| RFC-0006 | §9 Evidence Comparison | Facts not text (§9.1–§9.5); scope follows the Postcondition (§9.7, DN-28); missing ≠ success (V9) |
| RFC-0006 | §13 V1–V16 | V3, V4, V5, V6, V7, V8, V9, V10, V14, V15 enforced here; V2/V12/V13/V16 owned by the runtime (`core`) and flagged |
| RFC-0002 | invariant 2 | Made *possible* (Compare exists); the runtime obligation is `core`'s |

### 5. Implemented V-invariants

| Invariant | Enforcement |
|---|---|
| V3 deterministic | canonical Fact sort in `compare`; pure `determine`; input-order reversal tests |
| V4 no stale | Current-only freshness gate; non-Current Facts → UNKNOWN, never determine an Outcome |
| V5 no false success | success requires every Postcondition HELD on fresh comparable Facts (V9) |
| V6 partial distinct | per-Postcondition verdicts in declared order; PARTIALLY_SUCCESSFUL a distinct Outcome |
| V7 contradiction wins | Contradicted-status Fact or conflicting values → CONTRADICTED; strictest-wins precedence |
| V8 read-only | no store write, no mutation, no I/O; frozen/slotted results; inputs never modified |
| V9 missing ≠ success | no comparable evidence → UNKNOWN; UNKNOWN beats PARTIALLY_SUCCESSFUL |
| V10 fixed Postconditions | declared Postconditions consumed unchanged, one verdict each, never invented |
| V11 evidence carried | every PostconditionResult/OutcomeRecord carries the determining Facts |
| V14 never skip | empty/invalid input fail-closed to UNKNOWN; never absent, never assumed success |
| V15 no confidence | no confidence field/computation (DN-30); outcome determination is confidence-free |

### Short architectural consistency review

The ratified Iteration 4 decisions were checked against the frozen corpus. The
result is **consistent**: no RFC is modified, Layer-0/1/2 constraints hold, and
no ownership changes beyond what the ratification assigns.

- **Scope (DN-25).** Iteration 4 = `verification` Compare + Outcome semantics
  over already-normalized Facts only. Collect/Normalize stay `factlayer`'s
  (RFC-0005 §2); the runtime obligation (RFC-0002 invariant 2; V2) and
  Precondition revalidation (RFC-0006 §4; RFC-0008 P9/P10/P14) are `core`'s /
  RFC-0008's. Blueprint §2 (module set) and §8.5 (RFC basis §5–§8) are honored.
  No new package, no new module beyond the blueprint §2 tree.
- **Comparable evidence (DN-26).** A Fact is comparable only when its status is
  Observed or Verified (RFC-0005 §4); Unknown/Unavailable/Unsupported →
  Unknown (RFC-0006 V9/V14), Contradicted → Contradicted (V7), Stale → excluded
  (V4), Invalid → excluded (F16). Statuses stay distinct (F11).
- **No store write (DN-27).** `verification` never imports the `factlayer`
  store for writing; Compare/Outcome are pure (V8). The `Verified`-status write
  and Outcome recording are runtime obligations (RFC-0002 §2.9).
- **Scope implicit (DN-28).** No Verification Scope type; scope = the
  Postcondition Subjects/Properties (RFC-0006 V10, §9.7). No
  `systemmodel`-bound type.
- **Single snapshot (DN-29).** `compare` consumes after-Facts + Postconditions;
  before/after delta (RFC-0006 §9.1) deferred to the runtime. Consequence
  recorded: No Observable Change is not producible from one snapshot.
- **No confidence (DN-30).** Confidence computation is RFC-0020's (RFC-0006
  §15 OQ1); V15 honored by never-upgrading.
- **Outcome producers (DN-31).** The layer produces the Fact-determined
  Outcomes; Interrupted is orchestration (RFC-0002 §2.9); Expired maps to
  re-collect-or-Unknown (V4).
- **Staleness (DN-32).** Compare trusts the Facts' freshness state (RFC-0005
  §12, F14/F15); `PostCondition.freshness` is the declared bound. No
  re-derivation (DN-4).
- **Contradiction (DN-33).** Comparison-level rule in `compare.py` (same
  Subject+Property, differing values, same freshness → Contradicted; RFC-0006
  §7 rule 2, V7). RFC-0005 §8 relationship mechanics stay deferred (reported).
- **Evidence record (DN-34).** In-memory OutcomeRecord (RFC-0006 V11/V12);
  durable record/retention is RFC-0013's.
- **Authority.** `verification` holds Verify (RFC-0004 §4.6) only — never
  Propose/Infer/Approve/Execute/Refuse/Persist; the Executor never verifies
  itself (RFC-0004 §4.9). No authority leak; V8 (read-only) stays a DoD item
  and a test.
- **Gates.** No production behavior is introduced before the implementation
  commits; `verification` stays Layer 2; the package-tree and dependency-rule
  tests remain green.

**Residual open items (reported, not resolved):** none of Q1–Q10. Draft rework
risk on RFC-0006 (and its Draft dependencies) remains a recorded risk (blueprint
§9 #2), not a blocker. The pre-existing validator error (RFC-0004 §470 `'S1'`)
is unchanged and unrelated.

### Ratified decisions (DN-25 … DN-34)

| Note | Decision | Resolves |
|---|---|---|
| DN-25 | Iteration 4 = `verification` Compare + Outcome semantics only; no Collect invocation, no Precondition modeling | §8 Q1 |
| DN-26 | Comparable Fact status gate: Observed/Verified compare; failure statuses → Unknown; Contradicted → Contradicted; Stale/Invalid excluded | §8 Q2 |
| DN-27 | No store write in Iteration 4; `Verified`-status write + Outcome recording are runtime obligations | §8 Q3 |
| DN-28 | Verification Scope implicit via the Postconditions; no Scope type | §8 Q4 |
| DN-29 | `compare` consumes after-Facts + Postconditions; before/after delta deferred to the runtime | §8 Q5 |
| DN-30 | Verification Confidence computation deferred to RFC-0020; V15 by never-upgrade | §8 Q6 |
| DN-31 | Produciable Outcomes = the Fact-determined values; Interrupted is the orchestrator's; Expired = re-collect-or-Unknown | §8 Q7 |
| DN-32 | Staleness trusted from the Facts; `PostCondition.freshness` is the declared bound | §8 Q8 |
| DN-33 | Contradiction is a comparison-level rule in `compare.py`; RFC-0005 §8 stays deferred | §8 Q9 |
| DN-34 | Outcome evidence record is in-memory; durable recording deferred to RFC-0013 | §8 Q10 |

### 6. Remaining deferred work

Recorded only; nothing is invented. Each item belongs to a later iteration:

| Deferred item | Owning future RFC / iteration |
|---|---|
| Verification process invocation (execute → collect → compare → record) | `core` (RFC-0002 invariant 2, V2; RFC-0008) |
| Precondition re-validation (RFC-0006 §4) | RFC-0008 P9/P10/P14; `core` |
| Before/after delta analysis; No Observable Change | runtime passing before-state (DN-29) |
| Verification Confidence computation | RFC-0020 (DN-30) |
| Interrupted production (process cut-off) | RFC-0002 §2.9 orchestration (DN-31) |
| Expired handling (re-collect) | runtime re-collection (V4, DN-31) |
| `Verified`-status Fact write + Outcome recording in the store | runtime obligation (DN-27; RFC-0002 §2.9) |
| Durable evidence/Outcome records, retention, audit wiring | RFC-0013 (Iteration 7) |
| RFC-0005 §8 Fact-relationship mechanics (contradiction representation side) | RFC-0005 §8 (DN-33; deferred since Iteration 3) |
| Verification Scope type, if ever needed | RFC-0020 (DN-28) |
| RFC-0006 Draft rework risk | RFC-0006 acceptance / amendment (blueprint §9 #2) |

### 7. Completion verdict

- Iteration 4 implementation is **complete**.
- **Layer-2 Definition of Done is satisfied** (blueprint §8.5; design review
  §10): V3 (deterministic), V4 (no stale), V7 (contradiction wins), V10
  (Postconditions fixed), V14 (never skip) all pass, each with a test.
- **C1–C4 are complete.**
- Remaining work belongs to later iterations only.

### Conformance verification

- **Tree** matches blueprint §2 exactly — `test_packages.py`.
- **Dependency rules** (§4.1/§4.2) hold; declared and observed graphs acyclic —
  `test_dependency_rules.py`.
- **Layer-2 conformance** — allowed imports only, no forbidden packages or
  stdlib, no I/O at import, public surface == owned vocabulary, frozen/slotted
  dataclasses, no top-level logic, package tree, lower layers never import
  `verification` — `test_verification_conformance.py`.
- **Behavioral invariants** — V3–V11, V14, V15 — `test_verification_invariants.py`;
  §7 precedence + scenario mapping — `test_verification_scenarios.py`.
- **Full suite:** 632 tests pass; ruff, format, build, and pre-commit are
  clean.

No RFC was modified, no production code outside `verification` was touched, and
no architecture was added beyond the ratified decisions. The `verification`
layer is complete per blueprint §8.5 and the design review.

### Readiness for Iteration 5

Iteration 5 (the `trust` layer, blueprint §8.3 trust half; DN-7) is
**unblocked**: the verification layer is complete, the suite is green (632
tests), and no Iteration 4 item blocks it. Iteration 5 begins with its own
design review and ratification (per the Iteration 1–4 pattern) before
implementing the `trust` package (trust classes, sanitizer S1–S8, Hostile
quarantine). The deferrals above are `core`/RFC-0008/RFC-0013 obligations and
are recorded, not Iteration 5 blockers. The `secrets` package (RFC-0009,
blueprint §8.6) is postponed to the next iteration (DN-35).

---

## Iteration 5 — the `trust` layer (complete)

Iteration 5 implements the **Trust Layer** (`trust`, blueprint §8.3 trust half;
RFC-0007) — the half of the iteration that DN-7 deferred to its own review. The
full design review is `docs/iteration-5-design-review.md`; the ratified
decisions are DN-35…DN-39 in `docs/implementation-decision-notes.md`. Commit C0
was the **docs-ratification commit** (answers all eight design-review questions
Q1–Q8 — five as decision notes, three by the frozen corpus); C1–C4 implemented
and tested the layer; C5 (this commit) records its completion. No RFC is
modified, no new module exists outside the blueprint §2 tree, and no dependency
edge is added beyond the declared, latent `trust → schema` edge (DN-37).

### Commit mapping (C0–C5)

| Commit | Message | Content |
|---|---|---|
| C0 `ffe0d0a` | `docs: ratify Iteration 5 design review decisions` | Design-review ratification: Q1–Q8 resolved, DN-35…DN-39 recorded |
| C1 `70ff815` | `feat(trust): implement trust classification lattice` | `classes.py`: `TrustClass` (four members, §5 order), `TrustDomain` (twelve, §4), `TrustCategory` (nine, §6), `ProvenanceState` (§9.6), `meet`/`join` (§5.1), `downgrade` (§9), `classify` (DN-37), the vocabulary tables, and the `Datum`/`Classification`/`Demotion` records — 79 tests |
| C2 `7864f65` | `feat(trust): implement sanitization primitives` | `sanitize.py`: S3 neutralization (control characters, ANSI escapes, Unicode taming), `quote` (S4), `bound` (S8), `sanitize` fail-closed to Hostile (S6, T9, DN-39 path 2), and the `Sanitization`/`SanitizationStatus` result records (Q6) — 92 tests |
| C3 `fb5bcb9` | `feat(trust): implement hostile quarantine semantics` | `hostile.py`: in-memory `Quarantine` record with fail-closed admission and unconditional exclusion (§15.5, T11, Q8), `DisclosureState` (§15.6–§15.8), `contaminate` (T12, §9.7) — 34 tests |
| C4 `2cf85d8` | `test(trust): enforce Layer-1 conformance and trust invariants` | `test_trust_conformance.py` (42 tests) + `test_trust_invariants.py` (170 tests): Layer-1 rules, S1–S8, T8–T12, DN-39 enumeration |
| C5 `(this commit)` | `docs: record Iteration 5 completion and trust conformance` | This closeout |

### Q1–Q8 resolution summary

| §5 Q | Subject | Resolution | Governing RFC / note |
|---|---|---|---|
| Q1 | Iteration scope / roadmap re-order | `trust` is Iteration 5; `secrets` postponed to next iteration (dependency-safe; Layer 1 before Layer 3, still before `context` Iteration 8) | **DN-35**; blueprint §8.3/§8.6; DN-7; RFC-0009 §16.3 |
| Q2 | Category/domain enumeration scope | Enumerate RFC-0007-owned categories/domains (§6.1–§6.9, §4) as vocabulary + defaults; defer Secrets (→RFC-0009) and Skill Manifest/Code (→RFC-0011) | **DN-36**; RFC-0007 §4/§6/§6.10–§6.12 |
| Q3 | Classification input / `schema` edge | Internal abstract datum record (category + content + provenance state + origin domain); origin domain required (§4); `schema` edge latent (DN-28 precedent) | **DN-37**; RFC-0007 §2/§4/§5/§6/S7; DN-1; blueprint §4.1 |
| Q4 | Promotion (T6): absent vs declared | **No `promote()` in `trust`** — all three upward moves' mechanics are owned elsewhere (RFC-0005/0006/0011); join is not an upgrade; T6 enforced as an invariant test | Resolved by corpus: RFC-0007 §2, §3, §5.1, §8, §13 T6 |
| Q5 | Sanitizer scope vs RFC-0012 | Implement the S3 neutralization primitives + S4/S8 now (blueprint §8.3 DoD); no summarization, detection, or redaction mechanics | **DN-38**; RFC-0007 §11/§16.1/§16.6; RFC-0009 §16.3 |
| Q6 | Sanitize result contract | Label travels with text: result record carries class + status + provenance + reason; bare string would break T8; carrier is an in-memory type (DN-1) | Resolved by corpus: RFC-0007 §11 S1/S6, §13 T8/T9, §15.6; RFC-0002 invariant 10; DN-1 |
| Q7 | Hostile production paths | Hostile only via the fail-closed paths (unclassifiable T11/§15.5; sanitization failure S6/T9; suspicious provenance loss §9.6); no detection heuristics (RFC-0012's stance) | **DN-39**; RFC-0007 §5/§9.6/§15.5–§15.8/§16.6, T11/T12 |
| Q8 | Quarantine container scope | In-memory quarantine record (datum + reason + withheld/disclosed); durable recording deferred to RFC-0013 (Iteration 7, DN-34 precedent) | Resolved by corpus: RFC-0007 §15.5–§15.8; RFC-0002 invariant 13; RFC-0013; DN-19/DN-34 |

### Type → owner map

| Type / value | Module | Owning RFC |
|---|---|---|
| `TrustClass`, `TrustDomain`, `TrustCategory`, `ProvenanceState` | `trust/classes.py` | RFC-0007 §5, §4, §6, §9.6 |
| `Datum`, `Classification`, `Demotion` | `trust/classes.py` | RFC-0007 §4/§5/§6/§9; DN-37; DN-34 |
| `meet`, `join`, `downgrade`, `classify` | `trust/classes.py` | RFC-0007 §5.1, §9, §6; DN-37 |
| `CATEGORY_DEFAULTS`, `CATEGORY_ORIGINS`, `PROVENANCE_LOSS_DEMOTION`, `TRUST_DOMAIN_POSTURES` | `trust/classes.py` | RFC-0007 §6, §4, §9.6 (vocabulary data) |
| `Sanitization`, `SanitizationStatus`, `DEFAULT_LIMIT` | `trust/sanitize.py` | RFC-0007 §11 S1–S8; §16.2 (provisional bound); Q6 |
| `strip_ansi`, `neutralize_control`, `tame_unicode`, `bound`, `quote`, `sanitize` | `trust/sanitize.py` | RFC-0007 §10, §11; DN-38 |
| `Quarantine`, `DisclosureState` | `trust/hostile.py` | RFC-0007 §15.5–§15.8; Q8 |
| `quarantine`, `contaminate` | `trust/hostile.py` | RFC-0007 §15.5, §9.7 (T12); DN-39 |

Each type is defined in exactly one module; no type is re-defined or shared
across modules (RFC-0004 §3 one-owner rule; design review §2.6).

### Public surface map

| Module | Public surface (`__all__`) |
|---|---|
| `trust/classes.py` | `CATEGORY_DEFAULTS`, `CATEGORY_ORIGINS`, `Classification`, `Datum`, `Demotion`, `PROVENANCE_LOSS_DEMOTION`, `ProvenanceState`, `TRUST_DOMAIN_POSTURES`, `TrustCategory`, `TrustClass`, `TrustDomain`, `classify`, `downgrade`, `join`, `meet` |
| `trust/sanitize.py` | `DEFAULT_LIMIT`, `Sanitization`, `SanitizationStatus`, `bound`, `neutralize_control`, `quote`, `sanitize`, `strip_ansi`, `tame_unicode` |
| `trust/hostile.py` | `DisclosureState`, `Quarantine`, `contaminate`, `quarantine` |

The facade (`trust/__init__.py`) re-exports nothing and leaks no internal
placeholder (design review §4).

### Layer-1 conformance summary

Verified by `tests/test_trust_conformance.py` (mirrors
`test_verification_conformance.py`):

- **Imports.** Only stdlib + `trust` itself; the declared `trust → schema` edge
  (blueprint §4.1) stays **latent** — no trust module consumes it (DN-37).
- **No forbidden imports.** No authority-bearing or higher-layer package
  (collectors, factlayer, verification, secrets, policy, executor, audit,
  context, providers, skills, core, cli, systemmodel); no I/O-,
  concurrency-, or persistence-capable stdlib.
- **No dependency-edge violations.** `test_dependency_rules.py` green;
  declared and observed import graphs acyclic.
- **No forbidden runtime logic.** No top-level control flow; module-level code
  builds only constant data; no I/O, persistence, or execution calls anywhere.
- **Frozen + slots.** Every public dataclass (`Datum`, `Classification`,
  `Demotion`, `Sanitization`, `Quarantine`) is frozen and slot-based (DN-34).
- **No ownership overlap / no placeholder leaks.** `__all__` equals the
  ownership map per module; names unique across modules; no underscore-prefixed
  name exported; facade re-exports nothing.
- **Package tree unchanged.** `trust/{__init__,classes,sanitize,hostile}.py`
  matches blueprint §2 exactly (`test_packages.py`); `schema` never imports
  `trust`.

### Trust invariants coverage summary

Verified by `tests/test_trust_invariants.py`. RFC-0007 §11 (S1–S8) and the
layer-enforceable §13 T-invariants (T8, T9, T10, T11, T12; design review §3 —
T1–T7 are construction/execution-side and enforced at `core`) each have tests:

| Invariant | What is verified |
|---|---|
| S1 / T9 | Sanitization never upgrades: class preserved (4×9 matrix); lost provenance → Hostile |
| S2 (§5.1) | Meet rule is monotonic; lattice laws hold (idempotent, commutative, associative, absorption, order duals) |
| S3 | Content survives neutralization — escaped/tamed, never deleted; TAB/NEWLINE preserved |
| S4 | Quoted representation is contained and visible (`«…»`) |
| S5 | Secrets are never classified or inferred — classify/sanitize are content-blind; no `Secret` category (DN-36); no secret-named surface |
| S6 / T11 | Failure fails closed to Hostile and the Operator is told (non-empty reason) |
| S7 | Determinism: same input, same output for every public operation |
| S8 | Bounding always marks truncation (`…`); non-positive bound rejected |
| T8 | Trust label and provenance travel together — structurally and through classify→sanitize→quarantine |
| T10 | Demotion is monotonic: one step toward Hostile, reason preserved, Hostile floor |
| T12 | Contagion only downgrades, never upgrades, never manufactures Hostile |
| DN-39 | Hostile produced only by the fail-closed paths — exhaustive (category × provenance) enumeration: `classify` (lost, Observation), `sanitize` (lost); `quarantine`/`contaminate` never fabricate |

### Dependency and ownership verification

- `tests/test_dependency_rules.py` green: `trust` imports only within
  `ALLOWED["trust"] = {"schema"}` + stdlib + itself; no forbidden edge; graphs
  acyclic.
- `tests/test_packages.py` green: tree matches blueprint §2 exactly.
- One owner per name: no name whose meaning belongs to RFC-0009/0011 (Secrets,
  Skill Manifest, Skill Code) is defined here (DN-36); each type lives in
  exactly one module.
- **No authority.** `trust` holds no RFC-0004 §7 authority cell; it records the
  class a datum already holds. There is no promotion path (T6; Q4), no
  detection (DN-39; RFC-0012 §16.6), no redaction (S5; RFC-0009), and no
  persistence (DN-34; RFC-0013).

### Remaining deferred items

Recorded only; nothing is invented. Each belongs to a later iteration:

| Deferred item | Owning future iteration / RFC |
|---|---|
| `secrets` package (RFC-0009) — redaction mechanics, the S5 enforcement side | next iteration (DN-35 re-orders blueprint §8.6) |
| Exact sanitization mechanics catalogue (summarization, detection) | RFC-0012 (DN-38) |
| Durable quarantine/evidence recording, retention, audit wiring | RFC-0013 (Iteration 7; DN-34, Q8) |
| Final output-size bounds | RFC-0005 §16.2 (`DEFAULT_LIMIT` is provisional) |
| Provider View assembly / Context construction (T10) | RFC-0012 `context` (Iteration 8) |
| Runtime enforcement of RFC-0002 invariants 4/5 (Provider View mediation, no untrusted interpolation; T3) | `core` — made testable here (C4), enforced there |
| RFC-0007 Draft rework risk (and RFC-0009/0011/0012 deferred parts) | RFC acceptance / amendment (blueprint §9 #2) |

### Completion verdict

- Iteration 5 implementation is **complete**.
- **Layer-1 Definition of Done is satisfied** (blueprint §8.3 trust half; design
  review §7 C4): sanitize-never-upgrades (S1, T9) and fail-to-Hostile (S6,
  T11/T12) pass, each with a test; every layer-enforceable T-invariant has a
  test.
- **C0–C5 are complete.** The `trust` layer is complete per blueprint §8.3 and
  the design review.
- Full suite: 1049 tests pass; ruff, format, build, and pre-commit are clean.

### Readiness for Iteration 6

Iteration 6 is the **`secrets` package** (RFC-0009; blueprint §8.6, re-ordered
by DN-35 so it follows `trust` and still precedes `context`, Iteration 8). It is
**unblocked**: the trust layer is complete, the suite is green (1049 tests), and
its dependency on `trust` is preserved (blueprint §4.1: `secrets → {schema,
trust}`). Iteration 6 begins with its own design review and ratification before
implementing the `secrets` package.

---

## Iteration 6 — the `secrets` layer (complete)

Iteration 6 implements the **Secrets Layer** (`secrets`, RFC-0009; blueprint
§8.6, re-ordered by DN-35 so it follows `trust` and still precedes `context`,
Iteration 8). The full design review is `docs/iteration-6-design-review.md`;
the ratified decisions are DN-40…DN-44 in
`docs/implementation-decision-notes.md`. Commit C0 was the **docs-ratification
commit** (answers all five design-review questions Q1–Q5 as decision notes);
C1–C4 implemented and tested the layer; C5 (this commit) records its
completion. No RFC is modified, no new module exists outside the blueprint §2
tree, and no dependency edge is added beyond the declared, latent
`secrets → schema` edge (DN-44) and the `secrets → trust` edge activated by
`redact.py` (DN-42).

### Commit mapping (C0–C5)

| Commit | Message | Content |
|---|---|---|
| C0 `464d238` | `docs: ratify Iteration 6 design review decisions` | Design-review ratification: Q1–Q5 resolved, DN-40…DN-44 recorded |
| C1 `0281e13` | `feat(secrets): implement deterministic secret classification` | `classify.py`: the four-class secrecy predicate (§3), the three §7 origins, the six fixed §2 non-secret classes, the mechanical non-exhaustive `SECRET_SHAPES` catalogue, deterministic `classify` (rules 1–4, fail-closed to Hostile), the value-free `SecretMetadata`/`SecretClassification` (DN-44) — 75 tests |
| C2 `9ac2ebf` | `feat(secrets): implement fail-closed redaction primitives` | `redact.py`: classifier-gated redaction replacing secret-shaped spans (§11) and containing via `trust.sanitize` bound/quote (S8/S4); WITHHELD fail-closed (SC14); never-upgrade (S1, T9); the fixed `REDACTION_MARKER` (DN-42) — 65 tests |
| C3 `fae6dcb` | `feat(secrets): implement Secure Store abstraction` | `store.py`: provision/consume/invalidate/destroy/records over in-memory, metadata-only records (DN-41); value at the consume boundary only (SC1); purpose-scoping (SC7); closed consumer set (SC6); owner/custody split (SC8); destroy (SC12); invalidate-on-exposure (SC15) — 51 tests |
| C4 `ca3f3cb` | `test(secrets): enforce Layer-3 conformance and secret invariants` | `test_secrets_conformance.py` (44 tests) + `test_secrets_invariants.py` (49 tests): Layer-3 rules, SC1–SC16, cross-layer invariants |
| C5 `(this commit)` | `docs: record Iteration 6 completion and secrets conformance` | This closeout |

### Q1–Q5 resolution summary

| §5 Q | Subject | Resolution | Governing RFC / note |
|---|---|---|---|
| Q1 | Iteration scope / renumbering vs blueprint §8.7 | `secrets` is Iteration 6 (DN-35 executes); `policy` shifts to the following iteration; blueprint §8.6/§8.7 numbering superseded, blueprint text stands until RFC-0020 | **DN-40**; blueprint §8.6/§8.7; DN-35; RFC-0000 §4/§7 |
| Q2 | Secure Store abstraction vs real store | Abstraction/interface contract over in-memory, metadata-only records; a value exists only at the consume boundary; OS-secret-store mechanics RFC-0020's (RFC-0009 §30 OQ1) | **DN-41**; RFC-0009 §9/§30 OQ1; DN-1/DN-19/DN-34 |
| Q3 | Redaction framework vs RFC-0020 catalogue | Deterministic redaction framework + minimal non-exhaustive catalogue now, consuming `trust.sanitize` (S8/S4) and `TrustClass` (S1, T9); exact catalogue RFC-0020/RFC-0012's | **DN-42**; RFC-0009 §11/§13/§30 OQ2; RFC-0007 S5/S8; DN-38 |
| Q4 | SC2–SC5 DoD without their enforcement points | Layer-boundary tests now (value-free surface, no path outside `store.consume`); cross-component enforcement is `context`/`audit`/`providers`/`skills` DoD, recorded not dropped | **DN-43**; blueprint §8.6; RFC-0009 §28; RFC-0004 §4.11; RFC-0012 §32 |
| Q5 | Classifier input / `schema` edge | Internal abstract input record (content + provenance/origin); value/metadata split; `schema` edge latent (DN-37 precedent) | **DN-44**; RFC-0009 §1/§3/§21; blueprint §4.1; DN-37 |

### Ratified decisions (DN-40 … DN-44)

| Note | Decision | Resolves |
|---|---|---|
| DN-40 | Iteration 6 = `secrets` layer only; blueprint §8.6/§8.7 numbering superseded by DN-35's re-order; `policy` shifts; blueprint text stands until RFC-0020 | §5 Q1 |
| DN-41 | Secure Store abstraction over in-memory metadata-only records; a value exists only at the consume boundary; OS-store mechanics RFC-0020's | §5 Q2 |
| DN-42 | Redaction framework + minimal non-exhaustive catalogue now, consuming `trust.sanitize`; exact catalogue RFC-0020/RFC-0012's | §5 Q3 |
| DN-43 | SC2–SC5 satisfied as layer-boundary tests now; cross-component enforcement is the owning packages' DoD | §5 Q4 |
| DN-44 | Classifier on an internal abstract input; value/metadata split; `schema` edge latent | §5 Q5 |

### Type → owner map

| Type / value | Module | Owning RFC |
|---|---|---|
| `SecrecyClass`, `SecretOrigin`, `NonSecretDesignation` | `secrets/classify.py` | RFC-0009 §3, §7, §2 |
| `SecretShape`, `SECRET_SHAPES` | `secrets/classify.py` | RFC-0009 §3 rule 3 (§30 OQ2 catalogue) |
| `SecretDatum`, `SecretMetadata`, `SecretClassification` | `secrets/classify.py` | RFC-0009 §1 (value/metadata split); DN-44 |
| `classify` | `secrets/classify.py` | RFC-0009 §3 rules 1–6; RFC-0001 §8.5 |
| `RedactionStatus`, `Redaction`, `REDACTION_MARKER` | `secrets/redact.py` | RFC-0009 §11, §13 (SC13/SC14); DN-42 |
| `redact` | `secrets/redact.py` | RFC-0009 §11, §13; RFC-0007 S1/S5/S8/T9 |
| `Consumer`, `StoreStatus` | `secrets/store.py` | RFC-0009 §8, §13 |
| `OPERATOR_OWNER`, `SECURE_STORE_CUSTODIAN` | `secrets/store.py` | RFC-0009 §4 (SC8) |
| `SecretRecord`, `Provision`, `Consumption`, `Destruction` | `secrets/store.py` | RFC-0009 §15, §5.1, §8.4, §12.5 |
| `SecureStore` | `secrets/store.py` | RFC-0009 §4–§12 (SC1, SC6, SC7, SC8, SC12, SC15); DN-41 |

Each type is defined in exactly one module; no type is re-defined or shared
across modules (RFC-0004 §3 one-owner rule; design review §2.6).

### Public surface map

| Module | Public surface (`__all__`) |
|---|---|
| `secrets/classify.py` | `NonSecretDesignation`, `SECRET_SHAPES`, `SecretClassification`, `SecretDatum`, `SecretMetadata`, `SecretOrigin`, `SecretShape`, `SecrecyClass`, `classify` |
| `secrets/redact.py` | `REDACTION_MARKER`, `Redaction`, `RedactionStatus`, `redact` |
| `secrets/store.py` | `Consumer`, `Consumption`, `Destruction`, `OPERATOR_OWNER`, `Provision`, `SECURE_STORE_CUSTODIAN`, `SecretRecord`, `SecureStore`, `StoreStatus` |

The facade (`secrets/__init__.py`) re-exports nothing and leaks no internal
placeholder (design review §4). The trust class is carried as a *value* from
`trust` (Q6-in-Iteration-5 precedent), never re-declared (design review §2.6).

### Layer-3 conformance summary

Verified by `tests/test_secrets_conformance.py` (mirrors
`test_trust_conformance.py`):

- **Imports.** Only stdlib + `secrets` itself + the blueprint §4.1 set
  `{schema, trust}`; the declared `secrets → schema` edge stays **latent** — no
  module consumes it (DN-44); the `secrets → trust` edge is activated by
  `redact.py` only (DN-42).
- **No forbidden imports.** No higher-layer or authority-bearing package
  (collectors, factlayer, verification, runtime/core, providers, executor,
  policy, audit, context, skills, systemmodel, cli); no I/O-, concurrency-, or
  persistence-capable stdlib (SC11 — nothing durable is ever written).
- **No dependency-edge violations.** `test_dependency_rules.py` green;
  declared and observed import graphs acyclic (`secrets → {schema, trust}` →
  stdlib).
- **No forbidden runtime logic.** No top-level control flow; module-level code
  builds only constant data (the `SECRET_SHAPES` catalogue and its compiled
  regexes, the markers); no I/O, persistence, or execution calls anywhere
  (RFC-0009 §3 rule 5: the LLM never classifies).
- **Frozen + slots.** Every public dataclass (`SecretShape`, `SecretDatum`,
  `SecretMetadata`, `SecretClassification`, `Redaction`, `SecretRecord`,
  `Provision`, `Consumption`, `Destruction`) is frozen and slot-based (DN-34).
- **No ownership overlap / no placeholder leaks.** `__all__` equals the
  ownership map per module; names unique across modules; no underscore-prefixed
  name exported; facade re-exports nothing.
- **Package tree unchanged.** `secrets/{__init__,classify,redact,store}.py`
  matches blueprint §2 exactly (`test_packages.py`); `schema` and `trust` never
  import `secrets`.
- **Value-free surface (SC2–SC5 boundary).** No metadata record
  (`SecretMetadata`, `SecretClassification`, `SecretRecord`, `Provision`,
  `Destruction`) carries a `content`/`value` field; `Consumption` is the single
  materialization point (SC1).

### Secrets invariant coverage summary

Verified by `tests/test_secrets_invariants.py` against the RFC-0009 §28
SC1–SC16 oracle (design review §7). SC9/SC10/SC11 are held by layer-boundary
tests now; their enforcement points are `policy`/`executor`/`audit` (DN-43):

| Invariant | What is verified |
|---|---|
| SC1 | Segregation: a value exists only in the store's custody and materializes only at `consume`; no record or repr reveals it |
| SC2 | Default secret-free: classification and every derived artifact carry no value; metadata has no value facet |
| SC3 | No secret in a Provider View: SECRET/HOSTILE withhold (nothing crosses); secret-shaped spans are replaced, never revealed |
| SC4 | No secret in the Audit: records are metadata-only through the full lifecycle; the value is absent from every repr |
| SC5 | No secret reaches an extension: the consumer set is exactly the Provider adapter; anything else is refused |
| SC6 | One-way crossing: `consume` is the only value-bearing operation; a refused consumption crosses nothing |
| SC7 | Purpose-scoped: bound at provisioning; an unstated purpose is refused with a non-empty reason; the scope is never widened |
| SC8 | Exactly one owner: `OPERATOR_OWNER` + `SECURE_STORE_CUSTODIAN` fixed per record; never parameters |
| SC9 | No Action carries a secret (boundary): no Action/Plan/Proposal surface; enforcement at `policy`/`executor` |
| SC10 | Elevation exposes nothing (boundary): the value appears nowhere outside `consume`; enforcement at `executor` |
| SC11 | Retention by consent (boundary): no durable surface and no persistence stdlib; destroy leaves nothing in memory |
| SC12 | Destruction timely and complete: value and record removed; unknown handles refused; metadata (never the value) recorded |
| SC13 | Deterministic and testable: same input → same output for classify, redact, and the store lifecycle |
| SC14 | Fails closed: unclassifiable and secret content are WITHHELD with a non-empty reason; every refusal is non-silent |
| SC15 | Exposure is compromise: suspected exposure invalidates immediately; the invalidated secret is refused at every boundary |
| SC16 | Privacy parity: marked content stays secret without an explicit `MARKED_PUBLIC` demotion; captured content is never adopted |

Cross-layer invariants additionally enforced: the trust class is preserved on a
crossing (S1, T9) and becomes Hostile only on a ratified fail-closed withhold;
redaction never re-classifies; metadata never carries a value; and 50 repeated
classify→redact→store runs are byte-identical (determinism).

### Dependency and ownership verification

- `tests/test_dependency_rules.py` green: `secrets` imports only within
  `ALLOWED["secrets"] = {"schema", "trust"}` + stdlib + itself; no forbidden
  edge; graphs acyclic.
- `tests/test_packages.py` green: tree matches blueprint §2 exactly.
- One owner per name: the secrecy vocabulary (§3/§7/§2), the redaction results
  (§11/§13), and the store/ownership records (§4–§12, §15) are each defined in
  exactly one module; the trust class is consumed as a value, never re-declared.
- **No authority.** `secrets` holds no RFC-0004 §7 authority cell (custody is
  not ownership, RFC-0009 §4); it is the *source* of the no-secrets boundary,
  never a consumer of the components that enforce it (design review §2.4).
- **SC2–SC5 boundary satisfaction (DN-43).** The package's own surface is
  value-free and offers no path to a value-bearing artifact outside
  `store.consume`; the cross-component enforcement is recorded against its
  owning package below.

### Remaining deferred items

Recorded only; nothing is invented. Each belongs to a later iteration:

| Deferred item | Owning future iteration / RFC |
|---|---|
| Cross-component SC2/SC3 enforcement (Context secret-free; Provider View) | RFC-0012 §32 `context`; RFC-0010 §11 `providers` (DN-43) |
| Cross-component SC4 (Audit metadata-only records; retention limits) | RFC-0013 §31 `audit` (DN-43) |
| Cross-component SC5 (Skill no-secrets boundary) | RFC-0011 §15 `skills` (DN-43) |
| The "no Action carries a secret" gate (SC9) and elevation (SC10) | RFC-0008 §3 `policy`/`executor` |
| The real OS-secret-store mechanics (which store, interface, encryption) | RFC-0020 (RFC-0009 §30 OQ1; DN-41) |
| The exhaustive redaction rule catalogue (exact patterns, collection exclusion) | RFC-0020, RFC-0012 (RFC-0009 §30 OQ2; DN-42) |
| A `schema`-bound classifier adapter, if ever needed | RFC-0020 (DN-44) |
| Credential provisioning UX (how the Operator enters/re-views keys) | RFC-0015/RFC-0016 (RFC-0009 §7, §23) |
| Telemetry architecture; personal-data detection heuristics | post-MVP (RFC-0000 §5) |
| RFC-0009 Draft rework risk (and its deferred parts in RFC-0007/0011/0012) | RFC acceptance / amendment (blueprint §9 #2) |

### Completion verdict

- Iteration 6 implementation is **complete**.
- **Layer-3 Definition of Done is satisfied** (blueprint §8.6 re-ordered by
  DN-35/DN-40; design review §7 C4): SC2–SC5 (layer-boundary), SC14, and SC15
  pass, each with a test; every layer-enforceable SC1–SC16 has a test.
- **C0–C5 are complete.** The `secrets` layer is complete per the blueprint and
  the design review.
- Full suite: 1333 tests pass; ruff, format, build, and pre-commit are clean.

### Readiness for Iteration 7

---

## Iteration 7 — the `policy` layer (complete)

Iteration 7 implements the **Policy Layer** (`policy`, RFC-0008; blueprint
§8.7, re-ordered by DN-35/DN-40 so it follows `secrets` and precedes
`executor` + `audit`, Iteration 8). The full design review is
`docs/iteration-7-design-review.md`; the ratified decisions are DN-45…DN-54 in
`docs/implementation-decision-notes.md`. Commit C0 was the **docs-ratification
commit** (answers all ten design-review questions Q1–Q10 as decision notes);
C1–C4 implemented and tested the layer; C5 (this commit) records its
completion. No RFC is modified, no module exists outside the blueprint §2 tree
(the four `policy` modules were already scaffolded per blueprint §2), and no
dependency edge is added beyond the declared, partially-latent
`policy → {schema, trust, factlayer}` set (blueprint §4.1): only the `schema`
edge is exercised (DN-46); `trust` and `factlayer` stay latent (DN-47).

### Commit mapping (C0–C5)

| Commit | Message | Content |
|---|---|---|
| C0 `991da01` | `docs: ratify Iteration 7 design review decisions` | Design-review ratification: Q1–Q10 resolved, DN-45…DN-54 recorded |
| C1 `76f6476` | `feat(policy): implement deterministic risk classification` | `classify.py`: the four risk classes and four gates (§6), the canonical `RISK_PROPERTIES` vocabulary (DN-47), deterministic `classify` over `schema.Action` + Facts (P2, P3), the carried gate (P4), `meet` and `classify_plan` (DN-54), elevation to at least Consequential (DN-53) — 87 tests |
| C2 `b3e4b20` | `feat(policy): implement policy gates and deterministic policy evaluation` | `gates.py` (the fixed gate table, `gate_for`) + `policy.py` (default-deny `load`, `decide`, `allowlisted`, `retry_ceiling`, `standing_approval_applies` with `StandingApproval` (DN-52), `ElevationBound` (DN-53); DN-51) — 100 tests |
| C3 `3abe96c` | `feat(policy): implement deterministic policy token machinery` | `tokens.py`: `mint` on an explicit decision only (P5; DN-49), in-memory issuance/override/auto-permit/rejection records (P13; DN-50), the scoped single-use `Token` with its binding (action/time/state/session; P6–P8), `consume`/`invalidate`/`validate`/`revalidate` (P7–P9, P14), override-scoped tokens with their reason (P10; DN-49), plan-envelope tokens (DN-54), deterministic per-class `expiry_for` — 82 tests |
| C4 `720a20a` | `test(policy): enforce Layer-3 conformance and policy invariants` | `test_policy_conformance.py` (53 tests) + `test_policy_invariants.py` (67 tests): Layer-3 rules, P1–P14, I-11, RFC-0001 §8.2, cross-layer invariants |
| C5 `(this commit)` | `docs: record Iteration 7 completion and policy conformance` | This closeout |

### Q1–Q10 resolution summary

| §10 Q | Subject | Resolution | Governing RFC / note |
|---|---|---|---|
| Q1 | Iteration scope / renumbering vs blueprint §8.7/§8.8 | `policy` is Iteration 7; `executor`+`audit` shift to Iteration 8; blueprint §8.7/§8.8 numbering superseded, blueprint text stands until RFC-0020 | **DN-45**; DN-35/DN-40; blueprint §8.7/§8.8; RFC-0000 §4/§7 |
| Q2 | `classify` input: `schema.Action` + referenced Facts vs internal input | `schema.Action` + a referenced-Fact set; the `schema` edge is exercised (unlike DN-37/DN-44, which applied where no canonical object existed) | **DN-46**; RFC-0008 §5/§6; blueprint §4.1 |
| Q3 | Risk-property / State-Domain vocabulary without a `systemmodel` edge | Internal canonical risk-property vocabulary in `classify.py`; `systemmodel` edge latent (DN-9/DN-37/DN-44); RFC-0021 owns the name→State-Domain semantics on acceptance | **DN-47**; RFC-0008 §6/§3; RFC-0021 (Draft) §6 |
| Q4 | Machine-state snapshot / state-change detection | Opaque in-memory snapshot reference (identity + Facts); re-validation = identity + `factlayer` freshness + runtime-supplied state-change signal; the State-Domain diff is runtime-owned | **DN-48**; RFC-0008 §8/§9/§2/§3; RFC-0002 I-11 |
| Q5 | Decision-input abstraction for `mint` | `mint` requires an explicit decision input (approve/auto-permit/override/reject); no input or rejection mints nothing (P5); override only for a Blocked Action (P10) | **DN-49**; RFC-0008 §8/§12/§13; RFC-0004 §4.8 (C11) |
| Q6 | P13/I-13 records without the Audit package | In-memory issuance/override/auto-permit/rejection records + layer-boundary test now; the durable Audit write is `audit`'s DoD (DN-43 precedent) | **DN-50**; RFC-0008 §8/§13/§15; RFC-0002 I-13; RFC-0004 A10 |
| Q7 | Default-deny policy loading: mechanism vs content | Mechanism now (rule set, default-deny, empty allowlist, elevation bounds, retry ceilings, fail-closed `load`); shipped contents RFC-0020's | **DN-51**; blueprint §8.7; RFC-0008 §7/§16; RFC-0001 §8.2/§8.12 |
| Q8 | Standing-approval construct | Representation + evaluation mechanism (scope/ceiling/expiry; never covers Blocked; never raises a ceiling); no shipped defaults | **DN-52**; RFC-0008 §7/§8/§13 P11; RFC-0001 §8.3 |
| Q9 | Elevation representation | Elevation risk-property → at least Consequential; token records bounds; mechanism/revocation is `executor.elevation` (Iteration 8) | **DN-53**; RFC-0008 §8/§13 P12; RFC-0001 §8.6; RFC-0021 §3.3 |
| Q10 | Plan envelope: meet rule + envelope token | Meet rule + envelope-scoped token (presented Step set); re-presentation is `core`'s (RFC-0002 §7) | **DN-54**; RFC-0008 §6/§8/§11; RFC-0002 §7 |

### DN-45 … DN-54 implementation mapping

| Note | Decision | Embodied in | Validated by |
|---|---|---|---|
| DN-45 | Iteration 7 = `policy` layer only; blueprint §8.7/§8.8 numbering superseded by DN-35/DN-40's re-order; blueprint text stands until RFC-0020 | C0 (scope); C1–C4 | `policy` layer complete; `executor`/`audit` untouched |
| DN-46 | `classify` consumes `schema.Action` + a referenced-Fact set; the `schema` edge is exercised | C1 (`classify.py`) | `test_policy_classify.py`; exercised-edge conformance test |
| DN-47 | Internal canonical risk-property vocabulary in `classify.py`; the `systemmodel`/State-Domain edge stays latent | C1 (`RISK_PROPERTIES`) | `test_policy_classify.py`; latent-edge conformance test |
| DN-48 | Token carries an opaque in-memory machine-state snapshot reference; the State-Domain diff is runtime-owned | C3 (`tokens.py`) | `test_policy_tokens.py`; P8/P9 boundary tests |
| DN-49 | `mint` requires an explicit decision input; no input or rejection mints nothing (P5); override only for Blocked (P10) | C3 (`mint`) | `test_policy_tokens.py`; P5/P10 tests |
| DN-50 | P13/I-13 satisfied as in-memory issuance records now; the durable Audit write is `audit`'s DoD | C3 (`TokenRecord`) | `test_policy_tokens.py`; P13/I-13 tests |
| DN-51 | Default-deny policy-loading mechanism now; the shipped contents are RFC-0020's | C2 (`load`, `gates.py`) | `test_policy_gates.py`; `test_policy_evaluation.py` |
| DN-52 | Standing approvals: representation + evaluation mechanism now; no shipped defaults | C2 (`StandingApproval`) | `test_policy_evaluation.py`; P11 boundary tests |
| DN-53 | Elevation risk-property → at least Consequential; token records bounds; mechanism is `executor`'s | C1/C3 (`classify`, `Token`) | `test_policy_classify.py`; `test_policy_invariants.py` elevation tests |
| DN-54 | Plan envelope: meet rule + envelope-scoped token now; re-presentation is `core`'s | C1/C3 (`classify_plan`, `meet`, `mint`) | `test_policy_classify.py`; `test_policy_tokens.py`; `test_policy_invariants.py` meet tests |

### Module ownership map

| Type / value | Module | Owning RFC |
|---|---|---|
| `RiskClass`, `Gate` | `policy/classify.py` | RFC-0008 §6 |
| `RISK_PROPERTIES`, `Classification`, `PlanClassification` | `policy/classify.py` | RFC-0008 §6; DN-47/DN-54 |
| `classify`, `classify_plan`, `meet` | `policy/classify.py` | RFC-0008 §6/§8/§11; RFC-0002 invariant 7; DN-54 |
| `CLASS_GATES`, `ALLOWLISTED_READ_ONLY_GATE`, `gate_for` | `policy/gates.py` | RFC-0008 §6; DN-51 |
| `Policy`, `PolicyDecision`, `StandingApproval`, `ElevationBound` | `policy/policy.py` | RFC-0008 §7/§8; DN-51/DN-52/DN-53 |
| `allowlisted`, `load`, `decide`, `standing_approval_applies`, `elevation_bound_for`, `retry_ceiling` | `policy/policy.py` | RFC-0008 §7/§8/§13; RFC-0001 §8.2/§8.3 |
| `Decision`, `RecordKind`, `InvalidationReason`, `TokenStatus` | `policy/tokens.py` | RFC-0008 §8/§13; DN-49 |
| `Token`, `TokenRecord`, `MintOutcome` | `policy/tokens.py` | RFC-0008 §8/§9/§13; DN-48/DN-50/DN-54 |
| `EXPIRY_WINDOWS`, `expiry_for` | `policy/tokens.py` | RFC-0008 §8; DN-51 |
| `mint`, `consume`, `invalidate`, `validate`, `revalidate` | `policy/tokens.py` | RFC-0008 §8/§9/§10/§13 P5–P10, P13, P14 |

Each type is defined in exactly one module; no type is re-defined or shared
across modules (RFC-0004 §3 one-owner rule; design review §4).

### Public surface map

| Module | Public surface (`__all__`) |
|---|---|
| `policy/classify.py` | `Classification`, `Gate`, `PlanClassification`, `RISK_PROPERTIES`, `RiskClass`, `classify`, `classify_plan`, `meet` |
| `policy/gates.py` | `ALLOWLISTED_READ_ONLY_GATE`, `CLASS_GATES`, `gate_for` |
| `policy/policy.py` | `ElevationBound`, `Policy`, `PolicyDecision`, `StandingApproval`, `allowlisted`, `decide`, `elevation_bound_for`, `load`, `retry_ceiling`, `standing_approval_applies` |
| `policy/tokens.py` | `Decision`, `EXPIRY_WINDOWS`, `InvalidationReason`, `MintOutcome`, `RecordKind`, `Token`, `TokenRecord`, `TokenStatus`, `consume`, `expiry_for`, `invalidate`, `mint`, `revalidate`, `validate` |

The facade (`policy/__init__.py`) re-exports nothing and leaks no internal
placeholder (design review §6). The trust class and the Fact types are carried
as *values* from `schema` (Q2-in-Iteration-7 precedent), never re-declared
(design review §4).

### Layer-3 conformance summary

Verified by `tests/test_policy_conformance.py` (mirrors
`test_trust_conformance.py` and `test_secrets_conformance.py`):

- **Imports.** Only stdlib + `policy` itself + the blueprint §4.1 set
  `{schema, trust, factlayer}`; the declared `policy → trust` and
  `policy → factlayer` edges stay **latent** — no module consumes them (DN-47);
  the `policy → schema` edge is **activated** by `classify.py` (DN-46).
- **No forbidden imports.** No higher-layer or authority-bearing package
  (collectors, factlayer, trust, verification, runtime/core, providers,
  executor, secrets, audit, context, skills, systemmodel, cli); no I/O-,
  concurrency-, clock-, or persistence-capable stdlib (no `os`, `pathlib`,
  `json`, `sqlite3`, `threading`, `asyncio`, `socket`, …).
- **No dependency-edge violations.** `test_dependency_rules.py` green;
  declared and observed import graphs acyclic (`policy → schema` → stdlib).
- **No forbidden runtime logic.** No top-level control flow; module-level code
  builds only constant data (the `RISK_PROPERTIES` vocabulary, the `CLASS_GATES`
  table, the `EXPIRY_WINDOWS` map, all `MappingProxyType`/`frozenset` literals);
  no I/O, clocks, randomness, persistence, or execution calls anywhere
  (RFC-0008 §2: pure, deterministic policy evaluation).
- **Frozen + slots.** Every public dataclass (`Classification`,
  `PlanClassification`, `Policy`, `PolicyDecision`, `StandingApproval`,
  `ElevationBound`, `Token`, `TokenRecord`, `MintOutcome`) is frozen and
  slot-based (DN-34 precedent).
- **No ownership overlap / no placeholder leaks.** `__all__` equals the
  ownership map per module; names unique across modules; no underscore-prefixed
  name exported; the facade re-exports nothing.
- **Package tree unchanged.** `policy/{__init__,classify,gates,tokens,policy}.py`
  matches blueprint §2 exactly (`test_packages.py`); `schema` never imports
  `policy`.
- **SC9 boundary (carried from DN-43).** `classify` accepts only a structured
  `schema.Action`; raw text and secret-shaped strings are refused at the
  boundary and never smuggled through the pipeline.

### P-invariant coverage table

Verified by `tests/test_policy_invariants.py` against the RFC-0008 §13
P1–P14 oracle (design review §8). P1, P11, P12, the durable half of P13, and
the §6.2 edges are held by layer-boundary tests now; their enforcement points
are `executor`/`audit`/`core` (DN-45/DN-50/DN-53/DN-54):

| Invariant | What is verified |
|---|---|
| P1 | The gate is the only path to mutation (boundary): no execution surface exists on the token; `mint` never decides whether to approve; enforcement is `executor`'s (recorded, not dropped) |
| P2 / I-7 | Deterministic classification, never the self-report: identical Actions and Facts classify identically; the proposer's words and confidence are ignored; the same input always yields the same class |
| P3 | Default deny and fail closed: unknown/ambiguous/unclassifiable inputs are BLOCKED and disclosed; an empty policy allowlists nothing; `gate_for`/`load` fail closed on malformed rules; a standing approval never covers a Blocked Action |
| P4 | The gate is carried, never re-derived: the gate is a frozen field of the classification; the decision gate never depends on the description |
| P5 | Approval is explicit; nothing on silence: an absent decision mints nothing and consumes nothing; a rejection mints nothing; no timeout yields a "yes" |
| P6 | Scoped to what was shown: a substituted Action is a fresh approval; a plan deviation voids the envelope; anything the token does not name is not approved |
| P7 | Single-use, never reused: one Action consumes its token; replaying a consumed token is refused; a consumed or expired token is dead |
| P8 | Bound to action/time/state, invalidated by any boundary: each of the six `InvalidationReason`s leaves the token unusable; an invalidated token is never resurrected; expiry is deterministic per class and dead-not-renewable |
| P9 | Re-validated at the boundary: a stale/changed Fact, a changed State Domain, a substituted Action, a session restart, or any uncertainty refuses the spend |
| P10 | Blocked only by explicit, audited override: no approve path for a Blocked Action; an override requires its own decision and reason; the override is recorded with its reason; no override for a non-blocked Action |
| P11 | Standing approvals scoped/bounded/expiring (boundary): `standing_approval_applies` refuses out-of-scope/above-ceiling/expired covers; execution is `executor/core`'s (recorded, not dropped) |
| P12 | Elevation explicit and scoped (boundary): an elevated Action is at least Consequential; the token records its elevation bounds; mechanism/revocation is `executor.elevation`'s (recorded, not dropped) |
| P13 / I-13 | Recorded before it is spent: no token is spendable without a prior record; the record precedes the spend; every mint kind (issuance/auto-permit/override/rejection) is recorded; the durable Audit write is `audit`'s (recorded, not dropped) |
| P14 | Reload and state-change re-validate: a policy reload and a state change invalidate outstanding tokens and refuse revalidation |
| I-11 | The token is scoped, consumable, invalidated: bound to action/time/state/session; auto-permission is not reusability |

Cross-layer invariants additionally enforced: the meet rule (a plan's class is
the meet of its steps; a destructive step blocks the plan; an empty or
unclassifiable plan fails closed); the elevation rule; full-pipeline
determinism (50 repeated classify→decide→mint runs are byte-identical);
explicit-time `validate`/`revalidate`; every record is immutable with no hidden
state; no token exists without an explicit decision; and the SC9
structured-inputs-only boundary.

### Dependency and ownership verification

- `tests/test_dependency_rules.py` green: `policy` imports only within
  `ALLOWED["policy"] = {"schema", "trust", "factlayer"}` + stdlib + itself; no
  forbidden edge; graphs acyclic (`policy → schema` → stdlib).
- `tests/test_packages.py` green: tree matches blueprint §2 exactly.
- One owner per name: the classification vocabulary (§6), the gate table (§6),
  the policy/evaluation records (§7/§8), and the token/record machinery
  (§8/§9/§13) are each defined in exactly one module; the `schema` types are
  consumed as values, never re-declared.
- **No authority.** `policy` holds no RFC-0004 §7 authority cell; it computes
  classes, gates, decisions, and token lifecycles deterministically and
  *delegates* the state-changing enforcement, elevation, and audit halves to
  their owning components (design review §1).
- **P1/P11/P12/durable-P13 boundary satisfaction (DN-45/DN-50).** The
  package's own surface is pure (no execution, no I/O, no persistence) and
  records the deferred obligations against `executor`/`audit`/`core` below.

### Remaining deferred items

Recorded only; nothing is invented. Each belongs to a later iteration:

| Deferred item | Owning future iteration / RFC |
|---|---|
| Independent executor token enforcement (the gate is the only path to mutation, P1) | RFC-0008 §13 `executor` (Iteration 8); RFC-0004 A2/A9 |
| Standing-approval execution: pre-minting per Action at its boundary (P11) | RFC-0008 §8 `executor`/`core`; RFC-0001 §8.3 |
| Elevation mechanism and revocation; the SC10 elevation boundary | RFC-0008 §8 `executor.elevation` (Iteration 8); RFC-0001 §8.6; DN-53/DN-43 |
| The durable Audit write of the issuance/override/auto-permit/rejection records (P13) | RFC-0008 §13 `audit` (Iteration 8); RFC-0002 I-13; DN-50 |
| The RFC-0002 §6.2 consultation edges and plan re-presentation | RFC-0002 §6.2/§7 `core`; RFC-0004 §4.7 |
| The shipped policy contents: allowlist, standing approvals, expiry windows, absolute-block rules | RFC-0020 (RFC-0008 §16; DN-51) |
| The RFC-0021 State-Domain vocabulary and its diff as the State-Domain change signal | RFC-0021 (Draft), `systemmodel`/runtime (DN-47/DN-48) |
| RFC-0008 Draft rework risk (and its deferred parts in RFC-0002/0004/0007) | RFC acceptance / amendment (blueprint §9 #2) |

### Completion verdict

- Iteration 7 implementation is **complete**.
- **Layer-3 Definition of Done is satisfied** (blueprint §8.7 re-ordered by
  DN-35/DN-40; design review §14 C4): P2–P10, P13, and P14 (with P1, P11, P12,
  and the durable half of P13 held at the layer boundary and recorded against
  their owners) each have a test; every layer-enforceable P1–P14 and I-11 has a
  test.
- **C0–C5 are complete.** The `policy` layer is complete per the blueprint and
  the design review.
- Full suite: 1722 tests pass; ruff, format, build, and pre-commit are clean.

### Readiness for Iteration 8

Iteration 8 is the **`executor` + `audit`** layer (RFC-0004 §4.8–§4.10;
RFC-0013; blueprint §8.8, re-ordered by DN-45/DN-40 to follow `policy`). It
owns the recorded enforcement halves of this iteration: independent token
enforcement (P1), the elevation mechanism (P12/DN-53), and the durable Audit
write (P13/DN-50). Iteration 8 begins with its own design review and
ratification before implementation.

---

## Iteration 8 — the `executor` + `audit` layer (complete)

Iteration 8 implements the **Executor Layer** (`executor`, RFC-0004 §4.9,
RFC-0002 §2.8, RFC-0001 §5/§8.6/§8.8/§8.12, RFC-0008 §8–§10) and the **Audit
Layer** (`audit`, RFC-0013; blueprint §8.8, re-ordered by DN-45/DN-40 so it
follows `policy`). The full design review is
`docs/iteration-8-design-review.md`; the ratified decisions are DN-55…DN-64 in
`docs/implementation-decision-notes.md`. Commit C0 was the **docs-ratification
commit** (answers all ten design-review questions Q1–Q10 as decision notes);
C1–C4 implemented and tested the layer; C5 (this commit) records its
completion. No RFC is modified, no module exists outside the blueprint §2 tree
(the six `executor`/`audit` modules were already scaffolded per blueprint §2),
and no dependency edge is added beyond the declared
`executor → {schema, audit, secrets}` and `audit → {schema, secrets}`
(metadata-types-only) sets (blueprint §4.1; DN-56/DN-61).

### Commit mapping (C0–C5)

| Commit | Message | Content |
|---|---|---|
| C0 `b443b78` | `docs: ratify Iteration 8 design review decisions` | Design-review ratification: Q1–Q10 resolved, DN-55…DN-64 recorded |
| C1 `183c8d0` | `feat(audit): implement immutable audit records` | `records.py` (nine §7 boundary categories incl. execution, secret-metadata, approval/override/auto-permit/rejection; SC4/AU7; frozen+slots; no clock, no generated identifiers) + `store.py` (in-memory append-only store, deterministic tamper-evident chain, §11 lifecycle, AU8 fail-closed, §22 reconciliation; DN-62/DN-63) + `test_audit_conformance.py` — 69 tests |
| C2 `cdf1976` | `feat(audit): implement deterministic audit transcript rendering` | `transcript.py`: `render(record)` → one §8 `TranscriptEntry`, record-derived only, never material the record does not hold (AU2, AU5; DN-64) — 36 tests |
| C3 `96fec09` | `feat(executor): implement deterministic sanctioned runner` | `runner.py`: `run` under a valid, unexpired, state-consistent `TokenHandoff` (I-1/I-11), locally re-validated without `policy` (DN-56), consumed machine-state/precondition verdict (DN-57), argv-structured descriptor, no shell string (I-5, DN-58), injected run primitive (DN-55), start/end records before/after the run through `audit` (I-13, AU8; DN-61), disclosed refusals — 35 tests |
| C4 `cd01d88` | `feat(executor): guardrails and scoped elevation (RFC-0001 §5, §8.6; RFC-0008 §8; P12, SC10)` | `guards.py` (deterministic timeout with placeholder bound; bounded, redacted output capture; truncation-with-marker; SC8/SC10/SC14; DN-59) + `elevation.py` (deterministic request/revoke lifecycle; injected machine mechanism; P12, SC10; DN-60) — 51 tests |
| C5 `(this commit)` | `docs: record Iteration 8 completion and executor/audit conformance` | This closeout |

### Q1–Q10 resolution summary

| §10 Q | Subject | Resolution | Governing RFC / note |
|---|---|---|---|
| Q1 | Run primitive: injected boundary vs real subprocess | The run primitive is an injected boundary (`RunPrimitive`); `executor` performs no I/O and no subprocess spawn | **DN-55**; RFC-0004 §4.9; RFC-0002 §2.8; blueprint §4.1 |
| Q2 | Token handoff / independent re-validation without `policy` | The token crosses as a structural handoff value; the runner re-validates it locally, never importing `policy` | **DN-56**; RFC-0008 §9; RFC-0004 A2 |
| Q3 | State-consistency/precondition verdict at the boundary | The runner re-validates locally and consumes the machine-state + precondition verdict as an explicit boundary input | **DN-57**; RFC-0002 I-11 |
| Q4 | Execution command construction (I-5, no shell) | An argv-structured descriptor built from the sanctioned Action structure only; no shell string is ever constructed | **DN-58**; RFC-0002 I-5; RFC-0004 A2 |
| Q5 | Guardrail mechanism vs RFC-0020 values | Guardrail mechanism now (timeout with placeholder bound; bounded, redacted capture); concrete values are RFC-0020's | **DN-59**; RFC-0001 §8.8/§8.12; RFC-0002 §11 Q2/Q3 |
| Q6 | Elevation module: lifecycle now vs deferred | `elevation.py` implements the deterministic lifecycle; the machine mechanism is injected at the boundary | **DN-60**; RFC-0008 §8; RFC-0001 §8.6; RFC-0021 §3.3 (Draft) |
| Q7 | Record-before-consequence at the runner | The runner writes execution start/end records through `audit`; a failed pre-write blocks the run and is disclosed (AU8) | **DN-61**; RFC-0002 I-13; RFC-0004 §9.12 |
| Q8 | Audit store durability | In-memory append-only store with tamper-evidence, the §11 lifecycle, AU8 fail-closed, §22 reconciliation; durable backing deferred to RFC-0020 | **DN-62**; RFC-0013 §1/§11/§12/§21 |
| Q9 | Record categories in scope | This layer's boundaries' categories (execution, secret-metadata, approval/override/auto-permit/rejection); the remaining §7 categories arrive with their owning write points | **DN-63**; RFC-0013 §7/§9/§23 |
| Q10 | Transcript derivation scope | Derivation from the record only, producing exactly the §8 categories; the presentation form is RFC-0015's | **DN-64**; RFC-0013 §8/§5; AU2 |

### DN-55 … DN-64 implementation mapping

| Note | Decision | Embodied in | Validated by |
|---|---|---|---|
| DN-55 | Injected run primitive; `executor` performs no I/O/subprocess | C3 (`runner.py` `RunPrimitive`) | `test_executor_runner.py`; AST conformance |
| DN-56 | Token as structural handoff; local re-validation, no `policy` import | C3 (`runner.py` `TokenHandoff`, `validate_handoff`) | `test_executor_runner.py`; AST conformance |
| DN-57 | Local re-validation + consumed machine-state/precondition verdict | C3 (`BoundaryVerdict`) | `test_executor_runner.py` refusals |
| DN-58 | argv-structured descriptor; no shell string (I-5) | C3 (`runner.py` descriptor) | `test_executor_runner.py` I-5 tests |
| DN-59 | Guardrail mechanism now (timeout placeholder bound; bounded/redacted capture) | C4 (`guards.py`) | `test_executor_guards.py` |
| DN-60 | Deterministic elevation lifecycle; machine mechanism injected | C4 (`elevation.py`) | `test_executor_elevation.py` |
| DN-61 | Runner writes execution records through `audit`; failed pre-write blocks run (AU8) | C1/C3 (`store.py`, `runner.py`) | `test_audit_store.py`; `test_executor_runner.py` |
| DN-62 | In-memory append-only store, hash-chain, §11 lifecycle, §22 reconciliation | C1 (`store.py`) | `test_audit_store.py`; `test_audit_conformance.py` |
| DN-63 | This layer's boundaries' categories | C1 (`records.py`) | `test_audit_records.py`; `test_audit_conformance.py` |
| DN-64 | Transcript derivation from the record only; form is RFC-0015's | C2 (`transcript.py`) | `test_audit_transcript.py` |

### Module ownership map

| Type / value | Module | Owning RFC |
|---|---|---|
| `RunOutcome`, `RefusalReason`, `Refusal`, `BoundaryVerdict`, `TokenHandoff`, `RunPrimitive`, `RunResult`, `run` | `executor/runner.py` | RFC-0004 §4.9; RFC-0002 §2.8/§6.2; RFC-0008 §9/§10; RFC-0013 §7/§21 |
| `DEFAULT_OUTPUT_BOUND`, `DEFAULT_TIMEOUT_BOUND`, `GuardrailReason`, `GuardrailFailure`, `GuardedPrimitive`, `GuardedResult`, `guard` | `executor/guards.py` | RFC-0001 §5, §8.1/§8.8/§8.12; RFC-0002 §2.8 |
| `ElevationSignal`, `ElevationState`, `ElevationReason`, `ElevationRequest`, `ElevationOutcome`, `ElevationMechanism`, `request`, `revoke` | `executor/elevation.py` | RFC-0008 §8; RFC-0001 §8.6 |
| `RecordCategory`, `ExecutionPhase`, `SecretEvent`, `ApprovalDecision`, `AuditRecord`, `ExecutionRecord`, `SecretMetadataRecord`, `ApprovalRecord`, `OverrideRecord` | `audit/records.py` | RFC-0013 §7, §9, §10, §31 |
| `StoreStatus`, `AuditStore` | `audit/store.py` | RFC-0013 §1, §11, §12, §21 |
| `TranscriptCategory`, `TranscriptEntry`, `render` | `audit/transcript.py` | RFC-0013 §8 |

Each type is defined in exactly one module; no type is re-defined or shared
across modules (RFC-0004 §3 one-owner rule; design review §4). The `schema`
`Action`/`TrustClass` types are consumed as values, never re-declared.

### Public surface map

| Module | Public surface (`__all__`) |
|---|---|
| `executor/runner.py` | `BoundaryVerdict`, `Refusal`, `RefusalReason`, `RunOutcome`, `RunPrimitive`, `RunResult`, `TokenHandoff`, `run` |
| `executor/guards.py` | `DEFAULT_OUTPUT_BOUND`, `DEFAULT_TIMEOUT_BOUND`, `GuardedPrimitive`, `GuardedResult`, `GuardrailFailure`, `GuardrailReason`, `guard` |
| `executor/elevation.py` | `ElevationMechanism`, `ElevationOutcome`, `ElevationReason`, `ElevationRequest`, `ElevationSignal`, `ElevationState`, `request`, `revoke` |
| `audit/records.py` | `ApprovalDecision`, `ApprovalRecord`, `AuditRecord`, `ExecutionPhase`, `ExecutionRecord`, `OverrideRecord`, `RecordCategory`, `SecretEvent`, `SecretMetadataRecord` |
| `audit/store.py` | `AuditStore`, `StoreStatus` |
| `audit/transcript.py` | `TranscriptCategory`, `TranscriptEntry`, `render` |

The facades (`executor/__init__.py`, `audit/__init__.py`) re-export nothing and
leak no internal placeholder (design review §6). `executor` holds **Execute**
only; `audit` holds **Persist/Explain** only (RFC-0004 §7; AU1).

### Layer-4 conformance summary

Verified by `tests/test_audit_conformance.py` and the AST-conformance sections
inside each executor test module (mirroring the trust/secrets/policy
precedent):

- **Imports.** `executor` imports only stdlib + `schema`/`audit`/`secrets`;
  `audit` imports only stdlib + `secrets` metadata types (blueprint §4.2
  qualifier; SC4) — the declared `audit → schema` edge stays **latent** (DN-44
  precedent), the `executor → schema` edge is **activated** by consuming
  `schema.Action` as a value (DN-56/DN-58).
- **No forbidden imports.** No higher-layer or authority-bearing package
  (collectors, trust, factlayer, verification, systemmodel, policy, executor
  (in audit), context, providers, skills, core, cli); no I/O-, concurrency-,
  clock-, persistence-, randomness-, or crypto-capable stdlib (no `os`,
  `pathlib`, `json`, `sqlite3`, `threading`, `asyncio`, `socket`, `subprocess`,
  `secrets`, `random`, `hashlib`, …). The tamper-evidence chain is a
  deterministic structural encoding, never a cryptographic digest (DN-62).
- **No dependency-edge violations.** `test_dependency_rules.py` green; declared
  and observed import graphs acyclic (`executor → audit → secrets`/`schema` →
  stdlib).
- **No forbidden runtime logic.** No top-level control flow; module-level code
  builds only constant data (enums, the placeholder bounds); no I/O, clocks,
  randomness, persistence, or execution calls anywhere; the store reads no
  clock and generates no identifier — time and identifiers are caller-supplied
  (DN-62).
- **Frozen + slots.** Every public dataclass (`RunResult`, `Refusal`,
  `TokenHandoff`, `GuardedResult`, `GuardedPrimitive`, `GuardrailFailure`,
  `ElevationRequest`, all audit records, `TranscriptEntry`) is frozen and
  slot-based (DN-34 precedent).
- **No ownership overlap / no placeholder leaks.** `__all__` equals the
  ownership map per module; names unique across modules; no underscore-prefixed
  name exported; the facades re-export nothing.
- **Package tree unchanged.** `executor/{__init__,runner,guards,elevation}.py`
  and `audit/{__init__,records,store,transcript}.py` match blueprint §2 exactly
  (`test_packages.py`); Layer 0 never imports them.
- **No secret value enters the record or transcript.** Every record is
  metadata-only (SC4/AU7); no record carries a value-shaped field; the store
  never holds a secret value.
- **No authority.** The runner creates no execution authority; the guards and
  elevation modules create no authority; the audit surface never widens a
  grant (AU16).

### AU invariant coverage table

Verified against the RFC-0013 §33 AU1–AU16 oracle (design review §8). The
durable-storage halves (AU11, AU12, AU14) and the export half of AU10 are
deferred to RFC-0020/RFC-0015 and recorded below; everything the layer can
enforce in-memory has a test:

| Invariant | What is verified |
|---|---|
| AU1 | Never authority: the record is never a decision input, a Fact source, or permission (conformance: no authority imports; facade re-exports nothing) |
| AU2 | Transcript is never evidence: `render` derives presentation from the record only; no reasoning/verification path consumes a rendering |
| AU3 | Recorded before its consequence: the runner records start before the run; store ordering is write-before-consequence (I-13) |
| AU4 | Append-only and tamper-evident: `append` returns new immutable state; edits are new records, never mutations; `verify` detects a break in the chain |
| AU5 | Deterministic recording: identical arguments yield identical records; identical records render identical entries; ordering is fixed |
| AU6 | No actor is exempt (boundary): every §7 category this layer owns is representable and appendable (execution, secret-metadata, approval/override/auto-permit/rejection); the remaining §7 write points are their owners' |
| AU7 | No secret value ever enters the Audit: records carry only `secrets` metadata types; no value-shaped field; SC4 |
| AU8 | A failed write blocks its consequence and is disclosed: a refused append moves the store to `Degraded`; the runner's failed pre-write blocks the run and is disclosed |
| AU9 | Complete by construction (boundary): the approval/override/auto-permit/rejection categories are representable by `records.py`; enforcement at the owning write points (DN-63) |
| AU10 | Visible to the Operator: the store read/list surface (`record_at`, `by_id`, `by_category`, `latest`, iteration); export deferred to RFC-0015 |
| AU13 | Recovery is reconciliation, never rewrite: §22 `reconcile`/`recover` record a lost write as failed-to-record, never invent it |
| AU15 | Never Memory, never Context: no reasoning store; no path consumes records as Context or Memory (conformance) |
| AU16 | Carries no permissions: possession of a record grants no capability; records never widen a grant (conformance) |

### I / P / SC boundary enforcement table

Verified across `test_executor_runner.py`, `test_executor_guards.py`,
`test_executor_elevation.py`, `test_audit_records.py`, `test_audit_store.py`,
`test_audit_transcript.py`, and `test_audit_conformance.py` against the
RFC-0002 invariants, the RFC-0008 §13 P-oracle, and the RFC-0001 SC-boundary
tests (design review §8). The deferred halves stay recorded against their
owners below:

| Invariant | What is verified |
|---|---|
| I-1 | Execution only under an approved Action: `run` refuses a token without an approved action (refusal, disclosed) |
| I-5 | No shell string: the descriptor is argv-structured and built from the sanctioned Action structure only; no shell string is ever constructed |
| I-11 | State-consistent: a mismatched action/session/state, an expired authorization, or any uncertainty refuses the run |
| I-13 | Recorded before consequence: execution records precede the run; a failed pre-write blocks the run (AU8) |
| P9 | Independent re-validation at the boundary: `run` re-validates the handoff locally, never trusting the caller |
| P12 | Elevation explicit and scoped: an elevated Action is at least Consequential; bounds ride the request; the mechanism is injected, never built |
| SC4 | No secret value in the Audit: records/transcript carry metadata only |
| SC8 | Output is redacted before it is reported: per-line classification and redaction via `secrets`; unprovable lines are withheld and disclosed (SC14) |
| SC10 | Elevation exposes nothing: no secret handling, no persisted state, no authority creation in `elevation.py`/`guards.py` |
| SC14 | Unprovable output is withheld with disclosure: redacted lines are reported as withheld, never silently dropped and never invented |

Cross-layer invariants additionally enforced: full-pipeline determinism
(identical inputs → identical records, renderings, and results); the explicit
`now` argument (no module reads a clock); immutable outputs; every refusal is a
disclosed, deterministic outcome; and the identity-based guardrail scoping
(the guarded call accepts only the exact `Action` instance the token binds).

### Dependency and ownership verification

- `tests/test_dependency_rules.py` green: `executor` imports only within
  `ALLOWED["executor"] = {"schema", "audit", "secrets"}` and `audit` imports
  only within `ALLOWED["audit"] = {"schema", "secrets"}` + stdlib + itself; no
  forbidden edge; graphs acyclic.
- `tests/test_packages.py` green: tree matches blueprint §2 exactly.
- One owner per name: each `__all__` name is defined by exactly one module; no
  type is re-declared; the `schema` types are consumed as values (DN-56).
- **No authority overlap.** `executor` holds Execute only (RFC-0004 §4.9);
  `audit` holds Persist/Explain only (RFC-0004 §4.12; AU1); neither holds a
  decision cell. The elevation *mechanism* is injected and never implemented in
  this layer (DN-60; RFC-0021 §3.3).

### Remaining deferred items

Recorded only; nothing is invented. Each belongs to a later iteration:

| Deferred item | Owning future iteration / RFC |
|---|---|
| The §6.2 consultation edges and the Executing state exits | RFC-0002 §2.8/§6.2 `core` (Iteration 10) |
| Session Initialization: opening the durable audit store, writability, elevation availability | RFC-0002 §2.1 `core` (Iteration 10) |
| Wiring `guard` + `run` + elevation into the runtime transitions | `executor`/`core` (Iteration 10) |
| The machine's own elevation mechanism (sudo/polkit, revocation plumbing) | RFC-0021 §3.3 (Draft); injected at `executor.elevation`, never implemented in the module |
| Concrete guardrail bounds (time budgets, output ceilings, retry windows) | RFC-0020 (RFC-0002 §11 Q2/Q3; DN-59) |
| The durable backing of the audit store (storage, retention AU11/AU12/AU14, deletion, export AU10) | RFC-0020 (RFC-0013 §18–§20; DN-62) |
| The Transcript presentation form | RFC-0015 (RFC-0013 §5; DN-64) |
| The remaining §7 write points (proposal, classification, verification, fact-lifecycle, context-boundary, skill-event, operator-visibility) | their owning components (RFC-0013 §7, §23; DN-63) |
| RFC-0013/RFC-0021 Draft rework risk | RFC acceptance / amendment (blueprint §9 #2) |

### Completion verdict

- Iteration 8 implementation is **complete**.
- **Layer-4 Definition of Done is satisfied** (design review §14 C4): every
  layer-enforceable AU1–AU16, I-1/I-5/I-11/I-13, P9/P12, and SC4/SC8/SC10/SC14
  has a test; the durable and runtime-owned halves are recorded against
  `core`/RFC-0020/RFC-0021/RFC-0015 exactly as ratified.
- **C0–C5 are complete.** The `executor` + `audit` layers are complete per the
  blueprint and the design review; the executor package (`runner` + `guards` +
  `elevation`) and the audit package (`records` + `store` + `transcript`) are
  each deterministic, pure, and authority-free.
- Full suite: 1965 tests pass; ruff, format, build, and pre-commit are clean.
  Working tree is clean after C5.

## Iteration 9 — the `context` layer (complete)

Iteration 9 implements the **Context & Memory Layer** (`context`, RFC-0012;
RFC-0010 §3 Provider View and §11 Context Boundary; RFC-0009 SC2/SC3/SC16;
RFC-0007 S1–S8/T10; RFC-0002 I-4/I-13; blueprint §8.9, re-ordered by
DN-45/DN-65 so it follows `executor` + `audit`). The full design review is
`docs/iteration-9-design-review.md`; the ratified decisions are DN-65…DN-74 in
`docs/implementation-decision-notes.md`. Commit C0 was the **docs-ratification
commit** (answers all ten design-review questions Q1–Q10 as decision notes);
C1–C5 implemented and tested the layer; C6 (this commit) records its
completion. No RFC is modified, no module exists outside the blueprint §2 tree
(the four `context` modules were already scaffolded per blueprint §2), and no
dependency edge is added beyond the declared
`context → {schema, factlayer, trust, secrets, systemmodel}` set (`secrets`
classifier-types-only; blueprint §4.1/§4.2; DN-44 latent-edge precedent).

### Commit mapping (C0–C6)

| Commit | Message | Content |
|---|---|---|
| C0 `3d69943` | `docs: ratify Iteration 9 design review decisions` | Design-review ratification: Q1–Q10 resolved, DN-65…DN-74 recorded |
| C1 `1506ccb` | `feat(context): implement deterministic bounded assembly (RFC-0012 §6, §12, §16, §33; DN-66, DN-70, DN-72, DN-73, DN-74; CM5–CM9, CM13)` | `assemble.py`: the pure assembly function over the boundary inputs (DN-66), the six §6 category types (DN-73), the §12 composition order, freshness gates + mark-stale (DN-72), routing-state marker + §33 supersede-disclose (DN-71), Evidence on `schema.VerificationOutcome` (DN-74), deterministic context-boundary events (DN-70) — 62 tests |
| C2 `6d37f97` | `feat(context): implement deterministic context boundary enforcement (RFC-0012 §9, §13, §19, §23, §24, §32; RFC-0009 SC2, SC16; RFC-0007 S1–S8; CM4)` | `boundaries.py`: the sanitization enforcement point — `trust` S1–S8 + `secrets` classifier applied fail-closed before material enters Context or a View (SC2/CM4/T10), hostile/quarantined excluded, personal data secret until demotion (SC16), placeholder-default policy (DN-67) — 53 tests |
| C3 `598fc65` | `feat(context): implement deterministic consented memory (RFC-0012 §7, §18–§22; RFC-0009 SC16; DN-69, DN-70; CM2, CM11, CM12, CM13, CM14, CM15)` | `memory.py`: in-memory consented store — promotion gate (consent + stated purpose, CM11), the three §7 categories, list/export/wipe (CM14), no-restore (CM13), never authority (CM2); promotion/destruction boundary events (DN-70) — 57 tests |
| C4 `fad152c` | `feat(context): implement deterministic provider view (RFC-0010 §3, §11; RFC-0012 §13, §27; RFC-0007 §12; RFC-0002 I-4; DN-68; PR14, SC3, CM10)` | `provider_view.py`: the deterministic View derivation from the assembled Context — the only outward channel (PR14/CM10), carrying the §3 elements and nothing else, secret-free (SC3), size-bounded/purpose-limited/labeled/disposable (RFC-0007 §12; I-4) — 39 tests |
| C5 `be0ae94` | `test(context): enforce Layer-4 conformance and context invariants` | `test_context_conformance.py` (imports limited to the declared sets + sanctioned stdlib, no I/O / no provider call / no forbidden stdlib / no clock / no randomness, public surface == owned vocabulary, ownership partitions, frozen + slots, package tree unchanged) + `test_context_invariants.py` (CM1–CM16, PR14, SC2/SC3/SC16, I-4/S7/T10, boundary/memory/view guarantees, cross-component obligations recorded against `core`/RFC-0014/RFC-0015/RFC-0020) — 109 tests |
| C6 `(this commit)` | `docs: record Iteration 9 completion and context conformance` | This closeout |

### Q1–Q10 resolution summary

| §10 Q | Subject | Resolution | Governing RFC / note |
|---|---|---|---|
| Q1 | Iteration scope / renumbering vs blueprint §8.9 | `context` executes at Iteration 9 per DN-45's re-order; blueprint §8.9's label stands until RFC-0020 | **DN-65**; blueprint §8.9 |
| Q2 | Context assembly input contract | `assemble()` consumes explicit boundary inputs (Goal value, Fact set, labeled history, sanitized skill material, routing-state marker); no I/O; `core` wires the runtime | **DN-66**; RFC-0012 §8/§12; RFC-0002 §2.4 |
| Q3 | Sanitization enforcement point | Mechanism now (S1–S8 + secrets classifier, fail-closed SC2/SC16); the per-source catalogue is RFC-0020's | **DN-67**; RFC-0012 §5/§32/§37 OQ3 |
| Q4 | Provider View representation | Deterministic derivation now (RFC-0010 §3 elements, secret-free); form RFC-0015's, signatures RFC-0020's | **DN-68**; RFC-0010 §3/§11; RFC-0012 §13/§27 |
| Q5 | In-memory Memory abstraction | In-memory consented store now; durable backing RFC-0014/RFC-0020's | **DN-69**; RFC-0012 §7/§22/§37 OQ4-OQ5 |
| Q6 | Context-boundary audit write | `context` emits deterministic boundary events; `core` writes them as RFC-0013 §7 cat. 9 records before use (I-13) | **DN-70**; RFC-0013 §7 cat. 9/§23; RFC-0004 §9.11 |
| Q7 | Routing state ownership | Marker + §33 supersede-disclose now; routing decisions `core`'s, persistence RFC-0014's | **DN-71**; RFC-0012 §6/§33; RFC-0002 §2.5/§2.6 |
| Q8 | Freshness event model | Freshness gates + mark-stale function now; event emission and re-inspection `core`'s | **DN-72**; RFC-0012 §16/§17; RFC-0002 §4.2 |
| Q9 | Six context categories | All six §6 categories as explicit types now; producers arrive with their owning iterations | **DN-73**; RFC-0012 §6/§8/§34 |
| Q10 | Evidence basis | Labeled material on `schema.VerificationOutcome`; never verification power; §14 write boundary `verification`'s | **DN-74**; RFC-0012 §6 cat. 4/§26; RFC-0006 §14 |

### DN-65 … DN-74 implementation mapping

| Note | Decision | Embodied in | Validated by |
|---|---|---|---|
| DN-65 | `context` = Iteration 9 per DN-45's re-order; blueprint §8.9 label superseded, stands until RFC-0020 | C0 (scope) | design review §10 Q1 |
| DN-66 | `assemble()` consumes explicit boundary inputs; no I/O; `core` wires the runtime | C1 (`assemble.py`) | `test_context_assemble.py`; `test_context_invariants.py` |
| DN-67 | Enforcement-point mechanism now (S1–S8 + secrets classifier, fail-closed); per-source catalogue RFC-0020's | C2 (`boundaries.py`) | `test_context_boundaries.py`; AST conformance |
| DN-68 | Deterministic View derivation now; form RFC-0015's, signatures RFC-0020's | C4 (`provider_view.py`) | `test_context_provider_view.py`; AST conformance |
| DN-69 | In-memory consented store now; durable backing RFC-0014/RFC-0020's | C3 (`memory.py`) | `test_context_memory.py`; AST conformance |
| DN-70 | `context` emits deterministic boundary events; `core` writes cat-9 records before use (I-13) | C1/C3 (`assemble.py`, `memory.py`) | `test_context_assemble.py`; `test_context_memory.py` |
| DN-71 | Routing-state marker + §33 supersede-disclose now; decisions `core`'s, persistence RFC-0014's | C1 (`assemble.py`) | `test_context_assemble.py`; `test_context_invariants.py` |
| DN-72 | Freshness gates + mark-stale function now; event emission/re-inspection `core`'s | C1 (`assemble.py`) | `test_context_assemble.py`; `test_context_invariants.py` |
| DN-73 | All six §6 categories as explicit types now | C1 (`assemble.py`) | `test_context_assemble.py`; `test_context_invariants.py` |
| DN-74 | Evidence as labeled material on `schema.VerificationOutcome`; §14 write boundary `verification`'s | C1 (`assemble.py`) | `test_context_assemble.py`; `test_context_invariants.py` |

### Module ownership map

| Type / value | Module | Owning RFC |
|---|---|---|
| `Assembly`, `BoundaryEvent`, `BoundaryEventKind`, `Context`, `ContextCategory`, `ContextState`, `Disclosure`, `EvidenceLabel`, `GoalValue`, `HistoryLabel`, `RoutingMarker`, `SkillMaterialItem`, `Supersession`, `TurnRecord`, the `DEFAULT_*_BOUND` values, the `REASON_*` values, `assemble`, `mark_stale`, `supersede_question` | `context/assemble.py` | RFC-0012 §6/§8/§12/§16/§17/§33; RFC-0002 §2.4; RFC-0003 §2.3 |
| `BoundaryDecision`, `BoundaryDisposition`, `BoundaryInput`, `BoundaryRefusal`, `BoundaryReport`, `DEFAULT_BOUNDARY_LIMIT`, `admit`, `admit_all` | `context/boundaries.py` | RFC-0012 §9/§13/§19/§23/§24/§32; RFC-0009 SC2/SC16; RFC-0007 S1–S8 |
| `Memory`, `MemoryCategory`, `MemoryEntry`, `MemoryEvent`, `MemoryOutcome`, `MemoryRefusal`, `empty`, `export`, `list_entries`, `promote`, `remove`, `wipe` | `context/memory.py` | RFC-0012 §7/§18–§22; RFC-0001 §9.2/§9.5 |
| `ProviderView`, `ProviderViewOutcome`, `ViewDisposition`, `ViewRefusal`, `derive` | `context/provider_view.py` | RFC-0010 §3/§11; RFC-0012 §13/§27; RFC-0007 §12 |

Each type is defined in exactly one module; no type is re-defined or shared
across modules (RFC-0004 §3 one-owner rule; design review §4). The `schema`
`Fact`/`VerificationOutcome` and `trust`/`secrets` types are consumed as values
and never re-declared.

### Public surface map

| Module | Public surface (`__all__`) |
|---|---|
| `context/assemble.py` | `Assembly`, `BoundaryEvent`, `BoundaryEventKind`, `Context`, `ContextCategory`, `ContextState`, `DEFAULT_EVIDENCE_BOUND`, `DEFAULT_FACT_BOUND`, `DEFAULT_HISTORY_BOUND`, `DEFAULT_SKILL_BOUND`, `Disclosure`, `EvidenceLabel`, `GoalValue`, `HistoryLabel`, `REASON_OVERFLOW`, `REASON_STALE_EXCLUDED`, `REASON_UNPURPOSEFUL`, `RoutingMarker`, `SkillMaterialItem`, `Supersession`, `TurnRecord`, `assemble`, `mark_stale`, `supersede_question` |
| `context/boundaries.py` | `BoundaryDecision`, `BoundaryDisposition`, `BoundaryInput`, `BoundaryRefusal`, `BoundaryReport`, `DEFAULT_BOUNDARY_LIMIT`, `admit`, `admit_all` |
| `context/memory.py` | `Memory`, `MemoryCategory`, `MemoryEntry`, `MemoryEvent`, `MemoryOutcome`, `MemoryRefusal`, `empty`, `export`, `list_entries`, `promote`, `remove`, `wipe` |
| `context/provider_view.py` | `ProviderView`, `ProviderViewOutcome`, `ViewDisposition`, `ViewRefusal`, `derive` |

The facade (`context/__init__.py`) re-exports nothing and leaks no internal
placeholder (design review §6). `context` holds **Observe** (assembly + View)
and **Persist under consent** (Memory) only (RFC-0004 §7); it never decides
(CM2), never carries permissions (CM16), and is never the Audit (CM15).

### Layer-4 conformance summary

Verified by `tests/test_context_conformance.py` and the AST-conformance
sections inside each context test module (mirroring the trust/secrets/policy/
executor/audit precedent):

- **Imports.** `context` imports only stdlib + `schema`/`factlayer`/`trust`/
  `secrets`/`systemmodel`; the declared `context → systemmodel` edge stays
  **latent** (DN-44 precedent) and `context → secrets` is restricted to
  **classifier types only** (blueprint §4.2; SC2/SC3 construction).
- **No forbidden imports.** No higher-layer or authority-bearing package
  (collectors, verification, policy, executor, audit, providers, skills, core,
  cli); no I/O-, concurrency-, clock-, persistence-, randomness-, or
  crypto-capable stdlib (no `os`, `pathlib`, `json`, `sqlite3`, `threading`,
  `asyncio`, `socket`, `subprocess`, `secrets`, `random`, `hashlib`, …).
- **No dependency-edge violations.** `test_dependency_rules.py` green; declared
  and observed import graphs acyclic (`context → {assemble, boundaries, memory,
  provider_view}` → `schema`/`factlayer`/`trust`/`secrets` → stdlib).
- **No forbidden runtime logic.** No top-level control flow; module-level code
  builds only constant data (enums, the placeholder bounds); no I/O, clocks,
  randomness, persistence, or provider calls anywhere; time is caller-supplied
  and nothing reads a clock (determinism; RFC-0007 S7).
- **Frozen + slots.** Every public dataclass (`Context`, `Assembly`,
  `BoundaryEvent`, `Disclosure`, `TurnRecord`, `GoalValue`, `EvidenceLabel`,
  `SkillMaterialItem`, `RoutingMarker`, `Supersession`, `BoundaryInput`,
  `BoundaryDecision`, `MemoryEntry`, `MemoryEvent`, `ProviderView`, …) is
  frozen and slot-based (DN-34 precedent).
- **No ownership overlap / no placeholder leaks.** `__all__` equals the
  ownership map per module; names unique across modules; no underscore-prefixed
  name exported; the facade re-exports nothing.
- **Package tree unchanged.** `context/{__init__,assemble,boundaries,memory,
  provider_view}.py` match blueprint §2 exactly (`test_packages.py`); Layer 0
  never imports `context`.
- **No secret value enters Context, Memory, or the View.** `admit` fail-closes
  secret-shaped values (SC2/CM4/T10); a known token fed at the boundary appears
  nowhere in Context, its View, or Memory (SC2/SC3); personal data stays secret
  until an explicit Operator demotion (SC16).
- **No authority.** No decision, approval, or truth path (CM2); no permission-
  or capability-bearing value in Context or Memory (CM16); no Audit record or
  raw transcript material (CM15); the package never widens a grant.

### CM invariant coverage table

Verified against the RFC-0012 §35 CM1–CM16 oracle (design review §8). The
runtime-owned halves (CM7/CM8/CM9/CM12 event emission and audit write) are
enforced as deterministic mechanics and recorded against `core` below;
everything the layer can enforce at its own surface has a test:

| Invariant | What is verified |
|---|---|
| CM1 | Never a source of truth: Fact identity/status/provenance are never upgraded; a Fact without Fact-Layer provenance never becomes reasoning material (assembly + View) |
| CM2 | Memory is never authority: `memory.py` exposes no decision/approval/truth path; no authority reads Memory (conformance + `hasattr` checks) |
| CM3 | Only the Context Manager assembles: an AST scan proves only `assemble.py` calls `Context(`; the field order is exactly §12 |
| CM4 | Context is secret-free by construction: `admit` fail-closes secret-shaped values; a known token appears nowhere in Context (SC2/T10) |
| CM5 | Context is purpose-limited: assembly requires a stated purpose; unrelated material is excluded and refused (`REASON_UNPURPOSEFUL`) |
| CM6 | Context is bounded: size bounds hold; overflow consolidates transparently (`REASON_OVERFLOW`, disclosure count), never silently grows |
| CM7 | Fresh or rebuilt: Stale/Expired Facts are excluded or mark the set Stale (`REASON_STALE_EXCLUDED`); the re-inspection trigger is `core`'s |
| CM8 | Invalidation is deterministic and precedes use: `mark_stale` consumes the event as an input and records the invalidation as an `INVALIDATED` boundary event before any use; the event emission is `core`'s |
| CM9 | Session-isolated: one working set per assembly, one active Goal, no cross-session merge in the package |
| CM10 | Propagates only by assembly: the Provider View is the only outward surface; nothing else exports Context material (PR14) |
| CM11 | Durable Memory only by explicit consent: the promotion gate refuses promotion without consent carrying a stated purpose, with no durable artifact |
| CM12 | Destruction is complete and recorded: `remove`/`wipe` return new immutable state with the promotion/destruction event; the cat-9 record is `core`'s write |
| CM13 | Recovery is re-assembly, never restore: a lost set is rebuilt from Facts, never a snapshot; a token-level scan proves `memory.py`/the package have no restore path |
| CM14 | Visible, exportable, wipable: `list_entries`/`export`/`wipe` on Memory; removal of a missing entry is a disclosed `NOT_FOUND` refusal |
| CM15 | Never the Audit: no `episky.audit` import; the package never holds or emits the material as a record; the cat-9 write is `core`'s |
| CM16 | Carries no permissions: no policy/executor/providers import; a credential-like value in Context grants nothing; no capability-bearing field |

### PR14 coverage

The Provider View is the only outward channel (RFC-0010 §13; RFC-0012 §27;
RFC-0007 T3), verified by:

- An AST scan over the whole package proves `provider_view.py` is the **only**
  module that constructs a `ProviderView` (nothing else exports Context
  material).
- `derive(context)` is a pure projection: it carries exactly the RFC-0010 §3
  elements (Goal, Facts, History, Evidence, routing state) and nothing else —
  no Audit, no secret, no raw output, no provider identity; the projection is
  deterministic and value-preserving (`derive(c) == derive(c)`).
- The View is secret-free by construction (SC3): a known token fed at the
  boundary appears nowhere in any derived View (`test_context_provider_view.py`,
  `test_context_invariants.py`).
- The one-way flow holds: material leaves `context` only as a derived View or a
  consented Memory promotion/destruction event (CM10; I-4 surface).

### SC2 / SC3 / SC16 coverage

| Invariant | What is verified |
|---|---|
| SC2 — the default is secret-free | `admit` fail-closes secret-shaped values at the enforcement point; no secret in Context in any form (CM4/T10); a known token appears nowhere in Context or its View |
| SC3 — no secret enters a Provider View | The View is derived secret-free; a known token fed at the boundary appears nowhere in any View; `provider_view.py` has no secret/value field |
| SC16 — privacy parity | Personal data (`NonSecretDesignation`) stays secret until an explicit Operator demotion (`MARKED_PUBLIC`) consumed at the boundary; Memory holds no private content without demotion; demotion collection is `cli`/`core`'s |

### Dependency verification

- `tests/test_dependency_rules.py` green: `context` imports only within
  `ALLOWED["context"] = {"schema", "factlayer", "trust", "secrets",
  "systemmodel"}`; the forbidden set `FORBIDDEN["context"] = {"providers",
  "policy", "executor", "audit"}` holds; `secrets` is restricted to classifier
  types (no values); graphs acyclic.
- `tests/test_packages.py` green: tree matches blueprint §2 exactly.
- Enforced additionally by `test_context_conformance.py`: the exact ratified
  import set per module, forbidden packages and stdlib, no clock/randomness, no
  provider call, no top-level runtime logic.

### Ownership verification

- One owner per name: each `__all__` name is defined by exactly one module; no
  type is re-declared; the `schema`/`trust`/`secrets`/`factlayer` types are
  consumed as values (RFC-0004 §3).
- **No authority overlap.** `context` holds Observe (assembly + View) and
  Persist under consent (Memory) only; it holds no decision cell (CM2/CM16),
  never writes an Audit record (CM15), and never performs sanitization values
  handling — the enforcement point delegates classification to `secrets`
  (classifier types only; DN-67).
- The runtime halves are owned elsewhere and recorded, never implemented here:
  the cat-9 audit write is `core`'s (Q6), the routing transitions `core`'s
  (Q7), the freshness-event emission `core`'s (Q8).

### Remaining deferred items

Recorded only; nothing is invented. Each belongs to a later iteration:

| Deferred item | Owning future iteration / RFC |
|---|---|
| The Context Building state wiring (entry/exit conditions, re-entry, the exits → Diagnosis/Planning/Awaiting Input) | RFC-0002 §2.4/§6 `core` (Iteration 11) |
| STATE_CHANGED_DETECTED emission and the re-inspection trigger | RFC-0002 §4.2; RFC-0005 §12 `core` + `factlayer` (Iteration 11) |
| The history/turn producers (Operator input, Provider replies, proposals, decisions) | RFC-0012 §6 cat. 3 `core` (session) + `providers` (Iteration 10) |
| Skill material and its pre-entry sanitization (code never enters) | RFC-0011 §26/SK13 `skills` + `providers` (Iteration 10) |
| The cat-9 audit write of the context-boundary events | RFC-0013 §7 cat. 9/§23; RFC-0004 §9.11 `core` (Iteration 11) |
| The Provider View presentation form | RFC-0010 §15 OQ3; RFC-0015 `cli`/RFC-0015 |
| Concrete size/freshness bounds and the per-source sanitization catalogue | RFC-0012 §37 OQ1–OQ3 RFC-0020 (DN-18 placeholder precedent) |
| Memory durable backing (storage, retention, deletion, export, resume-survival) | RFC-0012 §37 OQ4/OQ5; RFC-0014/RFC-0020 (DN-69) |
| Routing-state persistence across interrupts | RFC-0012 §37 OQ4; RFC-0014 (DN-71) |
| The Operator consent collection (Memory promotion/wipe UI) | RFC-0001 §9.2/§9.5 `cli`/RFC-0015 |
| The Goal schema shape, final Context/View signatures, and package naming | RFC-0020 (DN-1; DN-66/DN-68) |
| The RFC-0012 §39 vocabulary additions to RFC-0003 Part I | RFC-0003 Part II amendment |
| RFC-0012/RFC-0013 Draft rework risk | RFC acceptance / amendment (blueprint §9 #2) |

### Completion verdict

- Iteration 9 implementation is **complete**.
- **Layer-4 Definition of Done is satisfied** (design review §14 overall DoD):
  every layer-enforceable CM1–CM16, PR14, SC2, and CM13 has a test; SC3/SC16
  and the I-4/S7/T10 boundary surfaces are covered; the durable and
  runtime-owned halves are recorded against
  `core`/`providers`/`skills`/RFC-0014/RFC-0015/RFC-0020 exactly as ratified.
- **C0–C6 are complete.** The `context` layer is complete per the blueprint and
  the design review; the four modules (`assemble` + `boundaries` + `memory` +
  `provider_view`) are each deterministic, pure, and authority-free.
- Full suite: **2285 tests pass** (1965 baseline + 320 new); ruff, format,
  build, and pre-commit are clean. Working tree is clean after C6.

### Readiness for Iteration 10

- The next iteration is the **`providers` + `skills`** layer (blueprint §8.10,
  re-ordered by DN-45 to Iteration 10). `context` is complete and
  conformance-enforced; `providers` and `skills` may import `context` (blueprint
  §4.2) and consume the Provider View (PR14) and skill-material sanitation
  (RFC-0011 §26) at the boundary.
- The runtime `core`-side obligations (Context Building state wiring, the
  STATE_CHANGED_DETECTED event and re-inspection, the cat-9 audit write) are
  recorded with their owners and will bind `core` at Iteration 11.
- **Ready.** Baseline 2285 green; DN-65…DN-74 are all implemented and validated
  (no open decision notes); the deferred-items table names every §1.2 owner;
  the tree and dependency edges are unchanged.

---

## Iteration 10 — the `providers` + `skills` layer (complete)

Iteration 10 implements the **Layer-5 Providers & Skills layer** (`providers`,
RFC-0010; `skills`, RFC-0011; blueprint §8.10, re-ordered by DN-45 to follow
`context`). The full design review is `docs/iteration-10-design-review.md`; the
ratified decisions are DN-75…DN-84 in `docs/implementation-decision-notes.md`.
Commit C0 was the docs-ratification commit (answers all ten design-review
questions Q1–Q10 as decision notes); C1–C5 implemented and tested the layer;
C6 (this commit) records its completion and the layer's conformance. No RFC
is modified, no module exists outside the blueprint §2 tree (the
`providers/{__init__,contract,view,adapters}.py` and
`skills/{__init__,loader,activation,runtime}.py` modules were already
scaffolded in Iteration 0 and are filled, not created), and no dependency edge
is added beyond the declared `providers → {schema, trust, context}` and
`skills → {schema, collectors, trust, policy, factlayer}` sets (blueprint
§4.1/§4.2). The layer exercises the two new meaningful edges the plan named —
`providers → context` (consumes the `context`-built Provider View, PR14) and
`skills → policy` / `skills → collectors` (types only) — and the deliberately
absent `providers ↔ skills` edge stays absent (DN-82).

### Commit mapping (C0–C6)

| Commit | Message | Content |
|---|---|---|
| C0 `6d5814b` | `docs: ratify Iteration 10 design review decisions` | Design-review ratification: Q1–Q10 resolved, DN-75…DN-84 recorded |
| C1 `b2b0dda` | `feat(providers): implement deterministic provider contracts` | `contract.py`: the finite RFC-0010 §4 structured outputs as deterministic validators over the `schema` types (Proposal, Explanation, Questions, Clarifications, Alternative Plans, Refusal, Failure, Need More Evidence), the expected-effect rule (a Proposal without its expected effect is rejected — RFC-0008 §5, PR13), nothing a Fact (F6), an instruction, or authority (PR2/PR3/PR6), nothing executes (PR1), malformed values degrade, never crash (PR11) — 70 tests |
| C2 `cb3d67c` | `feat(providers): implement provider lifecycle and capability view` | `view.py`: consume exactly the `context`-built Provider View and nothing else (PR14/SC3/PR8; RFC-0002 I-4), the §5 capability vocabulary and declaration (no capability implies permission, PR12), the deterministic §6 negotiation adaptation, the §7 lifecycle mechanics (register/activate/remove), and the §8 failure → RFC-0002 §4.3 event classification (Timeout→PROVIDER_TIMEOUT, …; PR11/PR16); selection/fallback RFC-0016's, consultation `core`'s — 47 tests |
| C3 `62fd8ef` | `feat(skills): implement the registry load-and-authenticate boundary (RFC-0011 §3, §22, §19)` | `loader.py`: read the declared surface; authenticate signature and provenance (an unauthenticated Skill is never loaded and never substituted, SK5); validate the declaration (targets, privileges, risk, capabilities, dependencies, Pre/Postconditions, verification approach) and the bundled Collectors; check Policy before activation; register with the Core enumeration; version + signature ride the manifest (§19); packaging/signing scheme RFC-0017/0020's — 47 tests |
| C4 `dc329b5` | `feat(skills): implement deterministic skill activation boundary` | `activation.py`: the per-session, reversible, Policy-gated §23 lifecycle (no unauthenticated substitution, no authority grant), with the §16 audited events carrying session and Skill identity; verification and consultation `core`'s — 43 tests |
| C5 `5c180ce` | `feat(skills): implement skill runtime gate-participation boundary` | `runtime.py`: §24 gate participation — every Skill Action passes the exact same gate as any Action (SK4), no unit approval, no skill-based shortcut, declared Pre/Postconditions ride every Action (SK11) and are never waivable (SK12), the verification approach is declaration-only (SK6), an incomplete Proposal is refused (RFC-0008 §5); consultation and session scope `core`'s — 38 tests |
| C6 `(this commit)` | `docs: record Iteration 10 completion and providers/skills conformance` | This closeout |

### Q1–Q10 resolution summary

| §10 Q | Subject | Resolution | Governing RFC / note |
|---|---|---|---|
| Q1 | Iteration scope / renumbering vs blueprint §8.10 | `providers` + `skills` execute at Iteration 10 per DN-45's re-order; blueprint §8.10's label superseded and stands until RFC-0020 | **DN-75**; blueprint §8.10 |
| Q2 | Provider contract surface | `contract.py` validates the finite RFC-0010 §4 outputs over the `schema` types now, with the expected-effect rule; per-vendor adapters are RFC-0020's and `adapters/` stays a scaffold | **DN-76**; RFC-0010 §0/§4/§8/§15 OQ6; RFC-0008 §5 |
| Q3 | Provider request lifecycle | `view.py` implements §7 lifecycle mechanics + §5 capability vocabulary + deterministic §6 negotiation now; selection/fallback RFC-0016's, consultation `core`'s | **DN-77**; RFC-0010 §5/§6/§7/§9 |
| Q4 | Provider response ownership | The provider package validates and returns contract-shaped §4 outputs; routing to the deterministic consumers is `core`'s; nothing is interpreted into validity (PR13) | **DN-78**; RFC-0010 §4/§8; RFC-0002 §6 |
| Q5 | Provider error handling | §8 failures classify into the RFC-0002 §4.3 events deterministically (PR11/PR16); retry/fallback/degraded are `core`'s | **DN-79**; RFC-0010 §8; RFC-0002 §4.3/§10 |
| Q6 | Skill registry ownership | `loader.py` is the Skill Registry's load-and-authenticate boundary (SK5/SK15, §22); version + signature ride the manifest, scheme RFC-0017/0020's | **DN-80**; RFC-0011 §3/§22/§19 |
| Q7 | Skill invocation boundary | `activation.py` §23 lifecycle + `runtime.py` §24 gate participation (SK4/SK11/SK12); consultation and session scope `core`'s | **DN-81**; RFC-0011 §23/§24; RFC-0002 §6 |
| Q8 | Provider↔skill interaction | RFC-0011 §20's rules are `core`'s obligation with no direct edge (blueprint §4.1); SK13 is asserted at the boundary | **DN-82**; RFC-0011 §20 |
| Q9 | External API boundaries | Both packages are I/O-free — no network, subprocess, filesystem, vendor, or skill-fetch I/O; everything injected (DN-55); vendor calls, skill fetch, and sandbox execution are RFC-0020's/RFC-0017's | **DN-83**; RFC-0010 §0/§15 OQ6; RFC-0011 §30 OQ2 |
| Q10 | Runtime ownership / no-vendor-knowledge | The provider package is the sole vendor-facing surface (PR10/PR15), enforced by conformance; SC3/SC5 asserted by boundary injection, no `secrets` import; runtime separation `core`'s | **DN-84**; RFC-0010 §12/§13; RFC-0009 SC3/SC5 |

### DN-75 … DN-84 implementation mapping

| Note | Decision | Embodied in | Validated by |
|---|---|---|---|
| DN-75 | `providers` + `skills` = Iteration 10 per DN-45's re-order; §8.10 label superseded | C0 | design review §10 Q1 |
| DN-76 | Finite §4 outputs over `schema` types + expected-effect rule now; adapters RFC-0020's | C1 (`contract.py`) | `test_providers_contract.py`; AST conformance |
| DN-77 | §7 lifecycle + §5 capability vocabulary + §6 negotiation now; selection RFC-0016's | C2 (`view.py`) | `test_providers_view.py`; AST conformance |
| DN-78 | Contract-shaped §4 outputs; routing `core`'s; nothing interpreted into validity | C1 (`contract.py`) | `test_providers_contract.py`; AST conformance |
| DN-79 | §8 failures → §4.3 events deterministically; reaction `core`'s | C2 (`view.py`) | `test_providers_view.py`; AST conformance |
| DN-80 | `loader.py` = load-and-authenticate boundary (SK5); version + signature ride the manifest | C3 (`loader.py`) | `test_skills_loader.py`; AST conformance |
| DN-81 | `activation.py` §23 + `runtime.py` §24 gate participation; consultation `core`'s | C4/C5 (`activation.py`, `runtime.py`) | `test_skills_activation.py`; `test_skills_runtime.py`; AST conformance |
| DN-82 | §20 provider↔skill rules `core`'s, no edge; SK13 asserted at the boundary | C1–C5 (no `skills → providers` edge) | `test_dependency_rules.py` |
| DN-83 | Both packages I/O-free; everything injected; vendor/sandbox RFC-0020/0017's | C1–C5 (I/O-free mechanics) | AST conformance in every module suite |
| DN-84 | Provider package = sole vendor-facing surface (PR10/PR15); SC3/SC5 by injection | C1/C2/C3/C5 (boundary surfaces) | `test_providers_view.py`; `test_skills_loader.py`; `test_skills_runtime.py` |

### Module ownership map

| Type / value | Module | Owning RFC |
|---|---|---|
| `ProviderOutputKind`, `ValidationDisposition`, `ValidationRefusal`, `Explanation`, `Questions`, `Clarifications`, `AlternativePlans`, `Refusal`, `Failure`, `NeedMoreEvidence`, `ValidationOutcome`, `validate` | `providers/contract.py` | RFC-0010 §4/§8; RFC-0008 §5; RFC-0003 §2.6 |
| `ProviderCapability`, `ProviderStage`, `ProviderFailure`, `ProviderEvent`, `ConsumptionDisposition`, `ConsumptionRefusal`, `LifecycleDisposition`, `LifecycleRefusal`, `RequestKind`, `CapabilityDeclaration`, `ProviderLifecycle`, `Consumption`, `LifecycleOutcome`, `Negotiation`, `consume`, `declare`, `register`, `activate`, `remove`, `negotiate`, `classify` | `providers/view.py` | RFC-0010 §3/§5/§6/§7/§8; RFC-0002 §4.3 |
| `SkillCapability`, `SkillStage`, `AuthenticationVerdict`, `PolicyVerdict`, `LoadDisposition`, `LoadRefusal`, `SkillDependency`, `SkillManifest`, `Skill`, `LoadOutcome`, `load` | `skills/loader.py` | RFC-0011 §3/§7/§8/§9/§22; RFC-0002 §4.7 |
| `ActivationStage`, `ActivationVerdict`, `ActivationEvent`, `ActivationRefusal`, `ActivationRequest`, `ActivationOutcome`, `Activation`, `activate`, `deactivate` | `skills/activation.py` | RFC-0011 §16/§23; RFC-0008; RFC-0002 §2.2/§4.7 |
| `GateDisposition`, `GateRefusal`, `SkillActionUnit`, `SkillGate`, `admit` | `skills/runtime.py` | RFC-0011 §12/§13/§14/§24; RFC-0008 §5 |

Each type is defined in exactly one module; no type is re-defined or shared
across modules (RFC-0004 §3 one-owner rule; design review §4). The `schema`
`Action`/`Plan`/`Proposal`/`Step`/`PostCondition`, the `context` `ProviderView`,
the `policy` `RiskClass`, and the `collectors` `CollectorSpec` types are
consumed as values and never re-declared.

### Public surface map

| Module | Public surface (`__all__`) |
|---|---|
| `providers/contract.py` | `ProviderOutputKind`, `ValidationDisposition`, `ValidationRefusal`, `Explanation`, `Questions`, `Clarifications`, `AlternativePlans`, `Refusal`, `Failure`, `NeedMoreEvidence`, `ValidationOutcome`, `validate` |
| `providers/view.py` | `ProviderCapability`, `ProviderStage`, `ProviderFailure`, `ProviderEvent`, `ConsumptionDisposition`, `ConsumptionRefusal`, `LifecycleDisposition`, `LifecycleRefusal`, `RequestKind`, `CapabilityDeclaration`, `ProviderLifecycle`, `Consumption`, `LifecycleOutcome`, `Negotiation`, `consume`, `declare`, `register`, `activate`, `remove`, `negotiate`, `classify` |
| `skills/loader.py` | `AuthenticationVerdict`, `LoadDisposition`, `LoadOutcome`, `LoadRefusal`, `PolicyVerdict`, `Skill`, `SkillCapability`, `SkillDependency`, `SkillManifest`, `SkillStage`, `load` |
| `skills/activation.py` | `Activation`, `ActivationEvent`, `ActivationOutcome`, `ActivationRefusal`, `ActivationRequest`, `ActivationStage`, `ActivationVerdict`, `activate`, `deactivate` |
| `skills/runtime.py` | `GateDisposition`, `GateRefusal`, `SkillActionUnit`, `SkillGate`, `admit` |

The facades (`providers/__init__.py`, `skills/__init__.py`, `adapters/__init__.py`)
re-export nothing and leak no internal placeholder (design review §6). `providers`
holds **Propose** (contract validation) and **Infer** (capability/lifecycle
mechanics) only; `skills` holds **Propose** (load/activate/gate) only
(RFC-0004 §7); neither package ever decides, approves, executes, verifies, or
creates a Fact (RFC-0010 §2; RFC-0011 §4; PR1–PR16; SK1–SK16).

### Layer-5 conformance summary

Verified by the AST-conformance sections inside each provider/skill test module
(mirroring the trust/secrets/policy/executor/audit/context precedent) and by
`tests/test_dependency_rules.py` + `tests/test_packages.py`:

- **Imports.** `providers` imports only stdlib + `schema`/`context` (`contract.py`:
  `schema.action`; `view.py`: `context.provider_view`); `skills` imports only
  stdlib + `schema`/`collectors`/`policy`/`factlayer`-types (`loader.py`:
  `collectors.registry`, `policy.classify`; `activation.py`/`runtime.py`:
  `skills.loader`, `schema.action`). The `providers → trust`/`skills → trust`
  declared edges stay **latent** (DN-44 precedent); `skills → policy`/
  `skills → collectors` are restricted to **types only** (blueprint §4.2
  "policy (decision)" / "factlayer (create)" use limits).
- **No forbidden imports.** No higher-layer or authority-bearing package
  (`executor`, `verification`, `audit`, `secrets`, `core`, `cli`) and no
  `providers ↔ skills` edge (DN-82); no I/O-, concurrency-, clock-,
  persistence-, randomness-, or crypto-capable stdlib (no `os`, `pathlib`,
  `json`, `sqlite3`, `threading`, `asyncio`, `socket`, `subprocess`, `secrets`,
  `random`, `hashlib`, …).
- **No dependency-edge violations.** `test_dependency_rules.py` green; the
  declared and observed import graphs are acyclic (`providers` → `context` →
  …; `skills` → `schema`/`collectors`/`policy` → … → stdlib).
- **No forbidden runtime logic.** No top-level control flow; module-level code
  builds only constant data (enums, the `_ADMITTED_REASON` text); no I/O,
  clocks, randomness, persistence, or provider calls anywhere; time is
  caller-supplied and nothing reads a clock (determinism; RFC-0007 S7).
- **Frozen + slots.** Every public dataclass (`ValidationOutcome`,
  `Explanation`, `Questions`, `Clarifications`, `AlternativePlans`, `Refusal`,
  `Failure`, `NeedMoreEvidence`, `CapabilityDeclaration`, `ProviderLifecycle`,
  `Consumption`, `LifecycleOutcome`, `Negotiation`, `SkillManifest`, `Skill`,
  `LoadOutcome`, `ActivationRequest`, `ActivationOutcome`, `Activation`,
  `SkillActionUnit`, `SkillGate`, …) is frozen and slot-based (DN-34
  precedent).
- **No ownership overlap / no placeholder leaks.** `__all__` equals the
  ownership map per module; names unique across modules; no underscore-prefixed
  name exported; the facades re-export nothing.
- **Package tree unchanged.** The `providers/{__init__,contract,view,adapters}.py`
  and `skills/{__init__,loader,activation,runtime}.py` files match blueprint §2
  exactly (`test_packages.py`); Layer 0 never imports either package.
- **No vendor surface leaks (PR10/PR15).** `providers` is the sole
  vendor-facing surface; a vendor-scan test proves no vendor name or branch
  appears anywhere else (`test_no_capability_leaks_a_vendor_name`).
- **No secret value crosses either boundary (SC3/SC5).** A known token fed at
  the View-consumption, Skill-loading, and gate boundaries appears nowhere in a
  consumed View, a loaded Skill, an activation, or a unit declaration
  (`test_consume_refuses_audit_and_secret_shaped_values`,
  `test_loading_does_not_register_a_secret_shaped_value`,
  `test_secret_shaped_values_never_reach_an_activation`,
  `test_secret_shaped_values_stay_out_of_the_declaration`).
- **No authority.** No decision, approval, or truth path (PR2/PR3/PR6; SK7);
  no token/permit/grant/verdict field on any owned carrier; the packages never
  widen a grant and never execute (PR1; RFC-0002 invariant 3).

### PR/SK invariant coverage table

The blueprint §8.10 overall DoD (PR11, PR14, F6, SK4, SK5, SC5) and the
layer-enforceable halves of PR1–PR16 / SK1–SK16 are each asserted by a direct
test; the runtime-owned halves are recorded against `core` below:

| Invariant | What is verified |
|---|---|
| PR11 | Malformed, uniterable, and unexpected inputs degrade to a disclosed rejection, never an exception (`test_unexpected_inputs_degrade_never_crash`, `test_uniterable_alternatives_degrade_not_crash`, `test_a_malformed_value_yields_no_result_and_never_raises`) |
| PR14 | `consume()` admits exactly the `context`-built `ProviderView` type; an Audit record, a secret-shaped value, raw output, or a provider identity is refused — the View is the only channel (RFC-0002 I-4) |
| F6 | No validation output is a Fact and no carrier has a Fact/authority field; nothing is interpreted into truth (`test_no_carrier_carries_a_fact_or_authority_field`) |
| PR13 | A value that is none of the finite §4 outputs yields no result and is never coerced into validity; an incomplete Proposal/Alternative is rejected (`test_a_malformed_value_yields_no_result_and_never_raises`, `test_a_proposal_without_an_expected_effect_is_rejected_as_incomplete`, `test_an_alternative_plan_whose_alternative_is_incomplete_is_rejected`) |
| PR16 | `classify` is total and honest: every §8 failure maps to a §4.3 event; no recommendation is fabricated (`test_classify_never_fabricates_a_recommendation`) |
| PR2/PR3/PR6 | No output is an instruction or authority/verdict; no owned carrier grants an action or a decision method (`test_no_owned_carrier_grants_authority_or_an_action`, `test_validation_never_creates_authority`) |
| PR12 | Capability declarations grant nothing; the §5 vocabulary names abilities, not authorities/actions (`test_no_capability_names_an_authority_or_action`) |
| PR1 | Nothing executes; no command/execute surface exists on any owned carrier (RFC-0010 §2) |
| SK4 | Every Skill Action passes the exact same gate as any Action; a Skill or a whole Plan is never admitted as a unit, no unit approval (`test_a_skills_plan_is_never_admitted_as_a_unit`, `test_units_carry_no_approval_token_or_authority`) |
| SK5 | An unauthenticated/failed-verifier Skill is refused with no durable artifact; a missing or refused Policy decision fails closed (`test_unauthenticated_verdict_refuses_the_load`, `test_missing_verifier_fails_closed_as_unauthenticated`, `test_unauthenticated_load_substitutes_nothing`) |
| SK6 | The verification approach is carried as a declaration only, never performed (`test_the_verification_approach_is_declared_never_performed`, `test_no_unit_carries_a_verification_verdict`) |
| SK11 | Declared Preconditions and Postconditions ride every Action/unit; an Action or Step without its expected effect is refused INCOMPLETE_EFFECT (`test_declared_preconditions_ride_the_unit`, `test_an_action_without_expected_postconditions_is_incomplete`, `test_a_plan_step_without_an_expected_effect_is_incomplete`) |
| SK12 | The declared Preconditions are attached and cannot be replaced or waived by the offering (`test_the_offering_cannot_replace_the_declared_preconditions`) |
| SK15/SK8 | Activation is per-session and reversible, never substitutes an unauthenticated Skill, and grants no authority (`test_activation_is_reversible`, `test_substituting_a_different_skill_for_a_bound_session_is_refused`, `test_activation_grants_no_authority`) |
| SC3 | A secret-shaped value never crosses into a Provider View; `consume` refuses it (`test_consume_refuses_audit_and_secret_shaped_values`) |
| SC5 | A secret-shaped value never reaches a Skill or a unit's declaration (`test_loading_does_not_register_a_secret_shaped_value`, `test_secret_shaped_values_never_reach_an_activation`, `test_secret_shaped_values_stay_out_of_the_declaration`) |
| SK13 | Skill material/code never enters an LLM path at this layer: no carrier exposes a code/command surface, and the code-never-in-LLM-path wiring is `core`'s (Iteration 11), asserted here as no `providers`/LLM edge (DN-82) |
| SK7/SK14 | No Skill content modifies Policy or Audit: no `policy` decision path and no `audit` import anywhere in `skills` (AST conformance; forbidden set) |

### Dependency verification

- `tests/test_dependency_rules.py` green: `providers` imports only within
  `ALLOWED["providers"] = {"schema", "trust", "context"}`; `skills` imports
  only within `ALLOWED["skills"] = {"schema", "collectors", "trust", "policy",
  "factlayer"}`; the forbidden sets `FORBIDDEN["providers"] = {"factlayer",
  "executor", "policy", "verification", "audit", "secrets"}` and
  `FORBIDDEN["skills"] = {"executor", "verification", "audit", "secrets"}`
  hold; the use-restriction qualifiers (skills imports `policy`/`factlayer`
  types only) are enforced; the forbidden `skills → providers` and
  `providers → skills` edges are absent (DN-82); graphs acyclic.
- `tests/test_packages.py` green: tree matches blueprint §2 exactly.
- Enforced additionally by the AST-conformance sections inside each provider/
  skill test module: the exact ratified import set per module, forbidden
  packages and stdlib, no clock/randomness, no provider/vendor call, no
  top-level runtime logic, public surface == owned vocabulary.

### Ownership verification

- One owner per name: each `__all__` name is defined by exactly one module; no
  type is re-declared; the `schema`/`context`/`policy`/`collectors` types are
  consumed as values (RFC-0004 §3).
- **No authority overlap.** `providers` holds Propose + Infer only (contract
  validation, capability/lifecycle mechanics); `skills` holds Propose only
  (load/activate/gate participation). Neither holds a decision cell, an
  approval token, a verification verdict, an Audit record, or an execution
  surface (PR1–PR16; SK1–SK16; RFC-0010 §2; RFC-0011 §4).
- The runtime-owned halves are owned elsewhere and recorded, never implemented
  here: the consultation wiring and session scope, the gate routing of
  provider- and Skill-originated Proposals, the audit writes, the failure
  reaction, and the provider-world/machine-world separation are `core`'s
  (Iteration 11); selection/fallback and skill enablement are RFC-0016's;
  packaging/signing and sandboxing are RFC-0017/RFC-0020's.

### Remaining deferred items

Recorded only; nothing is invented. Each belongs to a later iteration or RFC
and names its §1.2 owner (design review §1.2):

| Deferred item | Owning future iteration / RFC |
|---|---|
| The consultation wiring — when Diagnosis/Planning/Replanning consult a Provider, and when Diagnosis/Planning/Machine Inspection consult a Skill, each after a fresh Context Building | RFC-0002 §5/§6 `core` (Iteration 11) |
| Provider selection, preference order, fallback chains, profiles, and cost controls | RFC-0016 (Post-MVP); RFC-0010 §15 OQ1/OQ4 |
| The provider-failure reaction: retry with backoff, fallback chain, degraded mode → Awaiting Input (facts-only) | RFC-0002 §10; RFC-0010 §8 |
| The routing of provider-originated and Skill-originated Proposals into the Policy/Approval gate and the Executor | RFC-0008 §5; RFC-0004 A3 `core` (Iteration 11) |
| The audit writes of provider/skill events (loading, activation, execution, failure, trust revocation) | RFC-0013 §23; RFC-0002 invariant 13 `core` (Iteration 11) |
| The first vendor adapter (HTTP/SDK translation), the packaging format, the signing scheme, and the version encoding | RFC-0020; RFC-0017; RFC-0010 §15 OQ6; RFC-0011 §19/§30 OQ1 |
| Skill sandboxing mechanics (isolated environments, capability declarations, or both) | RFC-0020; RFC-0011 §17/§30 OQ2 |
| The skill review process and trust ratings (declared vs. actual risk) | The skill ecosystem work, post-MVP (RFC-0000 §5); RFC-0001 Q20/Q22 |
| The skill registry/distribution, marketplace, and fetching under default-deny | The ecosystem work; RFC-0001 Q23 |
| Skill enablement/preference configuration and cost controls | RFC-0016; RFC-0011 §30 OQ6 |
| Cross-version migration across skill/fact-model/provider contracts | RFC-0017; RFC-0011 §30 OQ7 |
| The RFC-0010 §17 / RFC-0011 §32 vocabulary additions to RFC-0003 Part I | RFC-0003 Part II amendment (docs change) |

### Completion verdict

- Iteration 10 implementation is **complete**.
- **Layer-5 Definition of Done is satisfied** (design review §14 overall DoD):
  PR11, PR14, F6 (providers) and SK4, SK5, SC5 (skills) all pass at the layer's
  own surface, as do the layer-enforceable halves of PR1–PR16 and SK1–SK16;
  the cross-component obligations (consultation wiring, gate routing, audit
  writes, selection/fallback, packaging/signing, sandboxing) are recorded
  against `core`/RFC-0016/RFC-0017/RFC-0020 exactly as ratified.
- **C0–C6 are complete.** The layer is complete per the blueprint and the
  design review; the five modules (`contract.py` + `view.py` + `loader.py` +
  `activation.py` + `runtime.py`) are each deterministic, pure, I/O-free, and
  authority-free; `adapters/` remains a scaffold.
- Full suite: **2530 tests pass** (2285 baseline + 245 new across the five new
  test modules); ruff, format, build, and pre-commit are clean. Working tree is
  clean after C6 (only the pre-existing untracked `HANDOFF.md` remains).

### Readiness for Iteration 11

- The next iteration is **`core`** (Layer 6; blueprint §8.11, re-ordered by
  DN-45), followed by `cli`. `core` inherits the recorded obligations of this
  layer and of Iterations 8–9: the consultation wiring (RFC-0002 §5/§6), the
  gate routing of provider- and Skill-originated Proposals (RFC-0008 §5), the
  provider-failure reaction (RFC-0002 §10), the audit writes of provider/skill
  and context events (RFC-0013 §23), and the provider-world/machine-world
  separation (RFC-0002 §1).
- The provider/skill runtime wiring, the Context Building state machine, and
  the state-transition emission are `core`'s; the `providers` and `skills`
  packages are complete, conformance-enforced, and I/O-free, ready for `core`
  to consume them.
- **Ready.** Baseline 2530 green; DN-75…DN-84 are all implemented and validated
  (no orphaned decision notes); the deferred-items table names every §1.2
  owner; the tree and dependency edges are unchanged.

---

## Known limitation

Blueprint §8.1 Definition of Done requires the validator to "exit 0 on the
current corpus". The validator currently reports one pre-existing error in the
frozen corpus:

```
rfc/RFC-0004-trust-and-authority-model.md:470: ERROR unknown invariant identifier 'S1'
```

RFC-0004 is Accepted and normative; fixing it requires an RFC-0003 amendment,
so it is out of scope for Iterations 0–3 (no edits to accepted RFCs, per
AGENTS.md hard rule 1). The validator is wired into CI as-is; the CI gate is
expected to fail until the corpus is amended. It is unrelated to the `schema`
package and to Iterations 1–3.
