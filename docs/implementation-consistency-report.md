# Implementation Consistency Report

Tracks each implemented iteration against the frozen corpus: what was built,
which RFC owns each type, which ambiguities were ratified, and what remains
deferred. Iteration 0 bootstrapped the repository skeleton; Iteration 1
implemented the `schema` package; Iteration 2 implemented the `systemmodel`
layer plus the ratified `schema` change (DN-9); Iteration 3 implemented the
`factlayer` + `collectors` pipeline (blueprint §8.4); Iteration 4 implemented
the `verification` layer (blueprint §8.5, DN-25…DN-34). This report is updated
at the end of each iteration and verified against
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

## Iteration 5 — the `trust` layer (ratification, Commit C0)

Iteration 5 implements the **Trust Layer** (`trust`, blueprint §8.3 trust half;
RFC-0007) — the half of the iteration that DN-7 deferred to its own review. The
full design review is `docs/iteration-5-design-review.md`; the ratified
decisions are DN-35…DN-39 in `docs/implementation-decision-notes.md`. Commit C0
is the **docs-ratification commit**: it answers all eight design-review
questions (Q1–Q8) — five as decision notes, three by the frozen corpus — and
**unblocks Iteration 5 implementation** (design review §10). No RFC is modified
and no source code, test, or `schema` change is introduced here.

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

### Ratified decisions (DN-35 … DN-39)

| Note | Decision | Resolves |
|---|---|---|
| DN-35 | Iteration 5 = `trust` layer only; `secrets` postponed to next iteration | §5 Q1 |
| DN-36 | Category/domain vocabulary: enumerate RFC-0007-owned (§6.1–§6.9); defer owned-elsewhere (secrets → RFC-0009, skill → RFC-0011) | §5 Q2 |
| DN-37 | Classification over an internal abstract datum; origin domain required; `schema` edge latent | §5 Q3 |
| DN-38 | S3 neutralization primitives + S4/S8 now; exact mechanics remain RFC-0012's | §5 Q5 |
| DN-39 | Hostile produced only by the fail-closed paths; no detection heuristics | §5 Q7 |

### Architectural consistency

- **Scope (DN-35).** Iteration 5 = `trust` only. `trust` is Layer 1 (blueprint
  §4.1); `secrets` (Layer 3, blueprint §8.6) is postponed and still precedes
  `context` (Iteration 8), preserving Risk #9's mitigation. Blueprint §2 module
  set `trust/{__init__,classes,sanitize,hostile}.py` is unchanged.
- **Ownership (DN-36, DN-37).** `trust` owns RFC-0007. No name whose meaning
  belongs to RFC-0009/0011 is defined here (RFC-0004 §3 one-owner rule). The
  allowed `trust → schema` edge stays latent (DN-28 precedent); no new edge.
- **Promotion (Q4).** No upgrade operation in `trust`; the only upward moves are
  Observation→Fact (RFC-0005), Post-condition confirmation (RFC-0006), and
  authenticated skill metadata (RFC-0011) — all owned elsewhere (RFC-0007 §3,
  §5.1, §8, T6). Enforced as an invariant test.
- **Sanitizer (DN-38) and result contract (Q6).** The sanitizer is containment,
  not a trust grant (S1, T9); the result carries class + provenance (T8);
  failure → Hostile (S6, T11). No redaction mechanism (RFC-0009) and no exact
  catalogue (RFC-0012) are anticipated.
- **Hostile (DN-39, Q8).** Fail-closed production paths only; quarantine is
  in-memory; durable recording is RFC-0013's (Iteration 7). No detection
  heuristics.
- **Authority.** `trust` holds no authority from the RFC-0004 §7 matrix (no F
  cell granted; it is an information-handling layer). It cannot "grant" trust —
  it records the class a datum already has per RFC-0007's rules.
- **Gates.** No production behavior is introduced at C0; the package-tree and
  dependency-rule tests remain green.

**Residual open items (reported, not resolved):** none of Q1–Q8. Draft rework
risk on RFC-0007 (and RFC-0009/RFC-0011/RFC-0012, which own deferred parts of
its §16 surface) remains a recorded risk (blueprint §9 #2), not a blocker. The
pre-existing validator error (RFC-0004 §470 `'S1'`) is unchanged and unrelated.

### Commit C0 status

Commit C0 (this commit) is the Iteration 5 docs-ratification: decision notes
DN-35…DN-39 and the Q1–Q8 resolution table above. **Iteration 5 implementation
is unblocked** and proceeds with Commit C1 (`classes.py`: lattice +
classification) once C0 is ratified, per the design review §6/§7 plan.

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
