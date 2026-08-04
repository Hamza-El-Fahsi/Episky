# Iteration 2 — Design Review (System Model layer)

> **Document type:** Implementation design review, not an RFC.
> **Read this first:** This document **defines no new architecture, modifies no
> RFC, invents no behavior, and writes no production code.** It translates the
> frozen corpus (RFC-0000–0013, RFC-0021, the two walkthroughs, the decision
> traceability matrix, `docs/architecture-implementation-blueprint.md`, and the
> ratified `docs/implementation-decision-notes.md` DN-1…DN-6) into an
> implementation plan for the **System Model layer — the `systemmodel`
> package** (RFC-0021). Where the corpus does not decide something, this
> document **reports** it as an ambiguity or a question; it does not resolve it.
>
> **Status of sources.** RFC-0021 is **Draft** (not Accepted), and RFC-0005 and
> RFC-0006 — the RFCs that reference its vocabulary — are Draft too. Per
> RFC-0003 Part II §1.1 Draft RFCs are not normative and must not be relied
> upon by implementation; yet the blueprint (a translation, §0) targets the
> Drafts' *invariants* as the conformance oracle (blueprint §9 #2). Iteration 2
> inherits Iteration 1's posture: it conforms to RFC-0021's Draft wording
> knowingly, accepting the rework risk that a Draft change carries (blueprint
> §9 #2; RFC-0003 Part II §1).
>
> **Scope decision (ratified — Q1).** Blueprint §8.3 defines Iteration 2 as
> **`systemmodel` + `trust`** in one iteration. Ratified: this iteration is
> scoped to the **System Model layer (`systemmodel`) only**. The `trust` half
> (RFC-0007, blueprint §8.3 work item "trust classes T1–T12, sanitizer S1–S8,
> Hostile quarantine") is a distinct package, a distinct RFC, and is **explicitly
> deferred to its own design review and iteration** (DN-7; §17 Q1). Scope is not
> expanded. Nothing in this review covers or depends on `trust`.

> **Ratification record (Operator, 2026-08-04).** All six §17 questions are
> ratified. Each answer is recorded in a decision note (DN-7…DN-12); the notes
> are authoritative for implementation and this review is updated to match.
> A1, A2, A4, A5, and A10 are resolved by ratification; A3, A6, A7, A8, and A9
> remain reported, not resolved.
>
> | Q | Subject | Ratified answer | Note |
> |---|---|---|---|
> | Q1 | Scope / `trust` pairing | Iteration 2 = `systemmodel` only; `trust` deferred to its own review and iteration; scope not expanded | DN-7 |
> | Q2 | FamilyStatus cardinality | Five values, including Experimental; RFC-0021's usage is canonical | DN-8 |
> | Q3 | FactCategory placement | Type in `schema` (canonical vocabulary); RFC-0021/`systemmodel` sole owner of semantics (category→subsystem and category→state-domain mappings, architectural meaning); `schema` owns only the type, never the meaning | DN-9 (amends DN-3) |
> | Q4 | `schema` import edge | Used: `systemmodel` imports `schema.FactCategory` for the mapping data | DN-11 |
> | Q5 | Category source set | RFC-0005 §10's 12 categories; Users↔Configuration reconciliation lives in the mapping | DN-10 |
> | Q6 | FamilyProfile fields | Full §2.3 five-dimension descriptive set, as data | DN-12 |

---

## 1. Scope of Iteration 2

Blueprint §8.3 defines Iteration 2 (systemmodel half) as:

| Item | Value |
|---|---|
| Goal | The thing facts describe (the machine model) |
| Work | Family Profile access for Supported families; subsystem / State-Domain vocabulary |
| Definition of Done (systemmodel half) | Profile lookup tests (RFC-0021 §2.2); unsupported families promise no Facts (RFC-0021 §2.1) |
| RFC basis | RFC-0021 §2, §4, §6, §11 |

Scope boundary: Iteration 2 produces **vocabulary and profile data types and
their type-level conformance tests only**. It produces no machine inspection,
no distro detection, no normalization, no Facts, no verification, no runtime
behavior, and no serialization. `systemmodel` is the *description of a class of
machines*, not a tool that reads a machine (RFC-0021 §0: "It defines the world,
not the code").

**Gate posture.** Like Iteration 1, this is scaffold: vocabulary + data +
conformance tests. Production code begins only after RFC-0015/0019/0020 and the
Draft RFCs are Accepted (blueprint §8.0, §8.12; RFC-0000 §5).

**The `trust` exclusion (ratified — Q1, DN-7).** Blueprint §8.3's DoD line names
two trust tests ("sanitize-never-upgrades tests (T9); fail-to-Hostile tests
(T11/T12)"). Those belong to the `trust` half and are **not** part of this
iteration's Definition of Done. `trust` is deferred to its own design review and
iteration; its implementation, when it comes, is reviewed against RFC-0007
§10, §11, §15 before any `trust` code is written.

---

## 2. Which RFC sections are implemented

Iteration 2 implements the *type/data surfaces* named here. **Type surface**
means the canonical types and enumerations that express the section's
vocabulary; **data surface** means the descriptive profile and mapping data
expressed as constant tables. No behavior is implemented. Exact constructor and
method signatures are RFC-0020's to define (blueprint §5, §11.2 #4; DN-1) and
are **not** specified by this review.

| RFC | Section | Implemented as (type / data surface) |
|---|---|---|
| RFC-0021 | §2.1 Status words | The `FamilyStatus` enumeration (see §16 A1 for the "Experimental" gap) |
| RFC-0021 | §2.2 Family table | The `DistributionFamily` enumeration + the family→status data table |
| RFC-0021 | §2.3 Family Profile | The `FamilyProfile` type (descriptive) + the `FAMILY_PROFILES` data table for Supported/Planned families |
| RFC-0021 | §4 Machine Subsystems | The `MachineSubsystem` enumeration (12 members) + the subsystem→depends-on graph |
| RFC-0021 | §5 Package Ecosystems | The `PackageEcosystem` and `EcosystemStatus` enumerations (used by the Family Profile) |
| RFC-0021 | §6 State Domains | The `StateDomain` enumeration (7 members) + the subsystem→state-representation mapping (normative §6.10) |
| RFC-0021 | §11 Future Expansion | The additive, data-driven profile mechanism (a new family = a new profile row, never new architecture) |
| RFC-0005 | §10 Fact Categories (data) | `FactCategory` vocabulary — **type in `schema`, semantics in `systemmodel` (DN-9/DN-10, Q3/Q5)** |

Supporting data needed to express the above: the subsystem dependency graph
(§4.2–§4.13 per-subsystem "Depends on", summarized in §4.14), the subsystem→
State-Domain mapping (§6.10, normative), and the per-family ecosystem
classification (§5.2).

---

## 3. Which RFC sections are intentionally NOT implemented

None is silently dropped; each is recorded with its owner.

| RFC | Section | Why not implemented now | Deferred to |
|---|---|---|---|
| RFC-0021 | §3 System Assumptions | Behavior: confirming a machine satisfies the assumptions happens at session start / collection, not in vocabulary | Iteration 3 (`factlayer`/`collectors`), `core` (RFC-0002 §2.1) |
| RFC-0021 | §7 Capability matrix | Conceptual ("what the model believes is possible"); refined by RFC-0006/RFC-0011, not a type surface | Iteration 4 (`verification`), RFC-0006 |
| RFC-0021 | §8 Unsupported environments | Behavioral classification ("treat as unknown"); the type surface here is only the vocabulary the behavior reads | `core` (session init), Iteration 3 |
| RFC-0021 | §9 Architectural assumptions | Model-level invariants about one machine / one operator / local execution; enforced by runtime | RFC-0002 invariants; `core` |
| RFC-0021 | §12 Risks | Analysis, not a type | — |
| RFC-0021 | §13 New terms for RFC-0003 | A governance action (additive amendment to RFC-0003 Part I), not code | RFC-0003 amendment process |
| RFC-0021 | §14 Open questions | Owned by the RFC's future amendment | RFC-0021 amendment |
| RFC-0005 | §2 normalization (uses the Family Profile) | Behavior; needs Collectors | Iteration 3 |
| RFC-0005 | §3 Subject vocabulary binding | Whether `schema.Subject` references `systemmodel` vocabulary — Layer-0 constraint; reported §16 A4 | RFC-0020 / decision note |
| RFC-0006 | §11 Verification Scope (uses subsystem vocabulary) | Behavior | Iteration 4 |

The **capability matrix (§7)** and **unknown-environment handling (§8)** are the
two largest deferrals. They are referenced by RFC-0006's "Can verify" and the
failure-injection walkthrough Scenario 30 ("unknown environment"), but both are
*behavior over vocabulary*, and the vocabulary comes first in Iteration 2.

---

## 4. Complete package list affected

| Package | Change in Iteration 2 |
|---|---|
| `systemmodel` | **The package implemented.** `profiles.py` gains family/profile/ecosystem types + data; `subsystems.py` gains subsystem/state-domain types + mappings. |
| `schema` | **Additive change (Q3/DN-9):** `FactCategory` enum added to `fact.py` — the type only, no meaning. `Scope` stays category-free; no existing type changes. |
| `trust`, `collectors`, `factlayer`, `verification`, `secrets`, `policy`, `executor`, `audit`, `context`, `providers`, `skills`, `core`, `cli` | **No change.** `trust` is Iteration 2's paired package in blueprint §8.3 but is explicitly deferred to its own review (Q1, DN-7). |

No new package or module is created. The module set
`systemmodel/{__init__,profiles,subsystems}` already exists from Iteration 0 and
is **fixed** by blueprint §2 and `tests/test_packages.py` — every piece of
Iteration 2 vocabulary fits into exactly two modules (plus `__init__.py`). This
is a hard constraint: adding a third module would break
`test_tree_matches_blueprint_exactly`.

---

## 5. Public interfaces to be introduced

Blueprint §5: the RFC specifies **behavior, not schemas or APIs**; exact
signatures are RFC-0020's. Iteration 2 therefore introduces a *type/data
surface* — the exported names and their invariants.

| Module | Public type surface (exported) | Normative source |
|---|---|---|
| `systemmodel/profiles.py` | `FamilyStatus`, `DistributionFamily`, `PackageEcosystem`, `EcosystemStatus`, `FamilyProfile`, `FAMILY_PROFILES` (data) | RFC-0021 §2.1, §2.2, §2.3, §5 |
| `systemmodel/subsystems.py` | `MachineSubsystem`, `StateDomain`, `SUBSYSTEM_STATE_REPRESENTATION` (data), `SUBSYSTEM_DEPENDENCIES` (data), `CATEGORY_SUBSYSTEMS` (data), `CATEGORY_STATE_DOMAINS` (data) | RFC-0021 §4, §6, §6.10; RFC-0005 §10 (DN-9/DN-10/DN-11) |
| `systemmodel/__init__.py` | Re-exports the two modules' surfaces | blueprint §2 |

Invariants of the surface (the *architectural* contract; exact APIs are
RFC-0020's):

- `DistributionFamily` carries the exact 8 rows of §2.2; its status data is
  exactly §2.2 (Supported / Planned / Unsupported / Out of Scope; see §16 A1
  for "Experimental").
- Only **Supported and Planned** families have a `FamilyProfile`; Unsupported
  and Out-of-Scope families have **no** profile and promise **no Facts**
  (blueprint §7 systemmodel row; RFC-0021 §2.1).
- `MachineSubsystem` has exactly the 12 members of §4.1; `StateDomain` exactly
  the 7 members of §6.2–§6.8.
- `SUBSYSTEM_STATE_REPRESENTATION` matches §6.10 exactly; **no individual fact
  or state item is owned by more than one representation** (§6.10 rule 2).
- `SUBSYSTEM_DEPENDENCIES` matches the per-subsystem "Depends on" clauses of
  §4.2–§4.13 and is a DAG (§4.14).
- Profile data is **descriptive, not prescriptive** (RFC-0021 §2.3); it is not
  a configuration file and not code.
- No module performs I/O, reads the environment, or detects the machine
  (blueprint §2 systemmodel: "profile data only").

---

## 6. Internal interfaces

Within `systemmodel` there is one intra-package relationship:

- `profiles.py` and `subsystems.py` are **independent** in Iteration 2: profile
  data (§2.3) mentions package ecosystems (§5) and init contract (§3.1) — both
  owned by `profiles.py` — while subsystem vocabulary (§4) and State-Domain
  vocabulary (§6) live in `subsystems.py`. No module imports the other unless a
  data need arises (e.g., a profile referencing a State Domain — see §16 A5).

Whether `systemmodel` imports `schema` in Iteration 2 — **ratified (Q4/DN-11):
the edge is used**. Blueprint §4.1 allows the edge ("Vocabulary is expressed in
the canonical types"); the category mapping data (DN-9) references
`schema.FactCategory`, so the edge is used, not latent. It exists for later
Fact/Subject binding (RFC-0005 §3) as well.

The DoD "Layer 1" constraint is: `systemmodel` imports **only stdlib and
`schema`** — never `trust`, `collectors`, `factlayer`, or any other package
(blueprint §4.1 `ALLOWED["systemmodel"] = {"schema"}`; enforced by
`tests/test_dependency_rules.py`).

---

## 7. Data types to be created

Conceptual types (name and normative content; representation is RFC-0020's):

| Type | Normative content |
|---|---|
| `FamilyStatus` | The five status words (DN-8): Supported, Planned, Experimental, Unsupported, Out of Scope (§2.1 with Experimental canonical from §2.2/§2.4/§5.1) |
| `DistributionFamily` | The 8 family rows of §2.2: Debian, Red Hat, Arch, openSUSE, Immutable/atomic, Other distros, Non-Linux, Android |
| `PackageEcosystem` | The 8 ecosystems of §5.2: apt/dpkg, dnf/rpm, pacman, zypper, nix, flatpak, snap, appimage |
| `EcosystemStatus` | Native, Secondary, Experimental, Unsupported (§5.1) |
| `FamilyProfile` | The descriptive profile of §2.3: package ecosystem(s), init contract, configuration conventions, release model, verification conventions |
| `MachineSubsystem` | The 12 subsystems of §4.1: Hardware, Boot, Kernel, Users, Services, Storage, Filesystems, Packages, Networking, Security, Logs, Applications |
| `StateDomain` | The 7 domains of §6.2–§6.8: Package, Service, Configuration, Filesystem, Network, User, Security |
| `FactCategory` | **Ratified (DN-9/DN-10).** The 12 RFC-0005 §10 categories, defined as a canonical type in `schema`; RFC-0021/`systemmodel` owns its semantics (category→subsystem and category→state-domain mappings) via DN-9/DN-10/DN-11. |

---

## 8. System Model responsibilities

The responsibility of `systemmodel` (blueprint §3, transcribed): **the Family
Profile (§2.3), supported families (§2.2), and subsystem/State-Domain
vocabulary (§4, §6, §11) that Facts and Verification Scopes reference.**

Its **forbidden responsibilities** (blueprint §2, §3, and the Iteration-0
docstring): no Facts, no behavior, no profile for unsupported families, no
machine detection, no normalization, no serialization, no I/O.

Put another way, `systemmodel` answers, as data:
1. *What kind of machine is this?* — `DistributionFamily` + `FamilyStatus`
   (§2.2).
2. *What do we expect about this family?* — `FamilyProfile` (§2.3) + ecosystem
   classification (§5).
3. *What are the parts of a machine?* — `MachineSubsystem` (§4).
4. *What machine state changes together?* — `StateDomain` (§6).
5. *Where does each subsystem's state live?* — `SUBSYSTEM_STATE_REPRESENTATION`
   (§6.10).
6. *How do subsystems relate?* — `SUBSYSTEM_DEPENDENCIES` (§4.2–§4.14).
7. *How is this extensible?* — the profile mechanism is additive (§11).

The systemmodel **does not** decide whether a real machine matches a profile;
that is Facts and Inspection (RFC-0005 §2, RFC-0002 §2.3), Iteration 3+.

---

## 9. State Domain ownership

RFC-0021 §6.10 is the **normative** subsystem→state mapping. It fixes where
each subsystem's mutable state lives (a State Domain, Facts-only, or domain
+ Facts). The `systemmodel` package encodes exactly this table.

| Subsystem | State representation (RFC-0021 §6.10) |
|---|---|
| Hardware | Facts only |
| Boot | Configuration State + Facts |
| Kernel | Configuration State + Facts |
| Users | User State |
| Services | Service State |
| Storage | Filesystem State + Facts |
| Filesystems | Filesystem State |
| Packages | Package State |
| Networking | Network State |
| Security | Security State |
| Logs | Facts only |
| Applications | Filesystem State + User State + Facts |

Two normative rules (§6.10) that the mapping data must satisfy:
1. **Every Fact about the machine belongs to exactly one subsystem** and is
   expressed in that subsystem's representation.
2. **No fact or state item is owned by more than one representation.** Where a
   subsystem's state spans a domain *and* Facts (Boot, Kernel, Storage,
   Applications), the table fixes which items are domain-owned and which are
   Facts.

Independence/influence (the §6.9 summary) is **explanatory**, not normative;
§6.10 is the owner. Iteration 2 may encode §6.9 as data for future
verification but must mark it explanatory (§16 A6), never normative.

---

## 10. The 12 subsystem mapping (RFC-0021 §4)

`MachineSubsystem` enumerates the 12 members of §4.1 exactly:

```
Hardware, Boot, Kernel, Users, Services, Storage,
Filesystems, Packages, Networking, Security, Logs, Applications
```

Each subsystem's "Depends on" clause (§4.2–§4.13) is normative and forms the
dependency data (`SUBSYSTEM_DEPENDENCIES`):

| Subsystem | Depends on (§4.2–§4.13) |
|---|---|
| Hardware | nothing (bottom of the stack) |
| Boot | Hardware |
| Kernel | Hardware, Boot |
| Users | Filesystems, Kernel |
| Services | Boot, Users, Filesystems, Networking |
| Storage | Hardware, Kernel |
| Filesystems | Storage, Kernel |
| Packages | Filesystems, Networking, Kernel |
| Networking | Hardware, Kernel, Services |
| Security | Kernel, Packages, Services, Users |
| Logs | Services, Boot, Kernel |
| Applications | Filesystems, Users, Packages, Networking |

The §4.14 summary graph is a **condensed** rendering of these clauses and must
be **consistent** with them (every §4.14 edge appears in the data; the data is
acyclic). Whether §4.14 is a strict subset or a re-drawing is a minor
consistency item (§16 A7) to confirm against the RFC text at implementation
time; the per-subsystem clauses are the normative source.

---

## 11. RFC ownership mapping (every artifact has exactly one owner)

Blueprint §10 fixes ownership; this review transcribes it and adds none. No
type or data item has two owners.

| Artifact | Owning RFC | Owning section(s) | Protected by |
|---|---|---|---|
| `systemmodel/*` | RFC-0021 | §2, §4, §6, §11 | (supported-platform promise) |
| `FamilyStatus`, `DistributionFamily`, `FamilyProfile`, `FAMILY_PROFILES` | RFC-0021 | §2.1, §2.2, §2.3 | supported-platform promise (§1.3) |
| `PackageEcosystem`, `EcosystemStatus` | RFC-0021 | §5.1, §5.2 | ecosystem statuses |
| `MachineSubsystem`, `SUBSYSTEM_DEPENDENCIES` | RFC-0021 | §4.1–§4.14 | subsystem boundaries |
| `StateDomain`, `SUBSYSTEM_STATE_REPRESENTATION` | RFC-0021 | §6, §6.10 | no two-owner representation rule |
| `FactCategory` (type) | `schema` (type only, DN-9) | RFC-0005 §10 | category set per DN-10 |
| `FactCategory` (semantics: category→subsystem, category→state-domain mappings, meaning) | RFC-0021 (`systemmodel`) — sole owner (DN-9) | RFC-0021 §4/§6; RFC-0005 §10 | category membership follows RFC-0021 |

**Two-owner check (blueprint §10) — resolved (Q3, DN-9).** `FactCategory` was
the only artifact where two RFCs touch the same property: RFC-0005 §10 *defines
the category set* ("concepts, not implementations; the categories map to
RFC-0021's subsystems and State Domains") while DN-3 declared RFC-0021 the
*sole owner*. The split is resolved by separating **type** from **meaning**: the
enumeration (RFC-0005 §10's 12 categories) is a canonical **type in `schema`** —
Layer 0, stdlib-only, owning the type and nothing else — while the **semantics**
(category→subsystem and category→state-domain mappings and the architectural
meaning) are owned by **RFC-0021/`systemmodel`** ("Category membership follows
RFC-0021"). The RFC-0005 §10 statement that the category is part of the Fact's
Scope is a binding, not a type, and is deferred; `Scope` stays category-free
(DN-9). This was the single most consequential ownership decision of Iteration 2
and it is now ratified.

---

## 12. Dependency graph

**Package-level (import graph).** Per blueprint §4.1/§4.3 (Layer 0 → higher):

```
systemmodel   ← imports: schema (allowed; may remain unused in Iteration 2)
                 importers: collectors (3), factlayer (3), verification (4),
                 context (8), core (10) — none built in Iteration 2
```

- `systemmodel` is Layer 1; its only allowed import is `schema`
  (`ALLOWED["systemmodel"] = {"schema"}` in `tests/test_dependency_rules.py`).
- `schema` is Layer 0 and may **never** import `systemmodel`. This is the hard
  constraint behind the FactCategory question (Q3).
- The dependency-rule tests stay green; Iteration 2 must not add any edge.

**Machine-level (subsystem graph).** `SUBSYSTEM_DEPENDENCIES` is a *data*
encoding of RFC-0021 §4.2–§4.13 and is a **DAG** (Hardware is the bottom; Logs
and Applications are near the top). This is a model graph, not a package graph;
it is never imported. A conformance test asserts acyclicity.

No circular dependency exists at either level.

---

## 13. Import rules

- `systemmodel` imports only stdlib and `schema` (blueprint §4.1). Any other
  `episky.*` import is a defect (blueprint §4.2).
- No import-time side effects; module load performs no I/O and reads no
  environment (blueprint §2 systemmodel: "profile data only").
- Import order is definitional only: `subsystems.py` and `profiles.py` are
  independent; data tables are module-level constants (DN-1 permits in-memory
  types; constant tables are data, not behavior).
- CI gates that must remain green: `tests/test_dependency_rules.py` (allowed
  graph, forbidden edges, acyclicity), `tests/test_packages.py` (tree matches
  blueprint §2 exactly), plus a new Layer-1 conformance test for `systemmodel`
  (see §16, plan Commit 8).

---

## 14. Layer boundaries

```
Layer 0  schema
Layer 1  systemmodel, trust          ← Iteration 2 adds vocabulary here
Layer 2  collectors ─► factlayer ─► verification
...      (blueprint §4.1)
```

- `systemmodel` sits at Layer 1 beside `trust`; neither imports the other
  (they are independent packages; blueprint §4.1 gives `trust` no dependency on
  `systemmodel` and vice versa). `trust` is deferred (DN-7).
- `collectors` (Iteration 3), `factlayer` (3), `verification` (4), `context`
  (8), and `core` (10) are the future *importers* of `systemmodel`; none exists
  yet.
- The Layer-0 boundary (`schema` imports nothing beyond stdlib) is what drives
  the FactCategory split (Q3/DN-9): a type that must later appear on a `schema`
  type cannot be defined in a Layer-1 package, so `schema` defines the type and
  `systemmodel` owns the meaning.

---

## 15. Initialization order

- **Build order (iteration level):** `systemmodel` is built after `schema`
  (blueprint §8.2 → §8.3) and before `factlayer`/`collectors` (blueprint §8.3 →
  §8.4), because RFC-0005's normalization and Subject/Category vocabulary
  reference it (RFC-0005 §1, §3, §10). This review does not change the
  iteration order; RFC-0020 retains the final word (blueprint §1).
- **Within Iteration 2:** no runtime initialization. Import order is
  irrelevant because no module executes code at import time; data tables are
  constants.
- **No module imports, loads, or reads any external resource.** No
  configuration, no I/O, no environment access in `systemmodel`.

---

## 16. Ambiguities discovered

Each is **reported, not resolved** in the review itself. Each names the corpus
silence that forces the report and the RFC/decision that owns the answer. A1,
A2, A4, A5, and A10 have since been **ratified** (see §17; DN-7…DN-11). A3, A6,
A7, A8, and A9 remain **open** — reported, not resolved.

| # | Ambiguity | Why it cannot be resolved here | Owning RFC / decision |
|---|---|---|---|
| A1 | **"Experimental" is a family status not defined in §2.1.** §2.1 defines four status words (Supported, Planned, Unsupported, Out of Scope); §2.2's Immutable row and §2.4 use "Experimental" for a *class* of systems, and §5.1 defines Experimental as an *ecosystem* status. Is `FamilyStatus` four-valued, or five with Experimental? | §2.1's status table is normative but omits Experimental; §2.4 introduces it without a §2.1 entry | **RATIFIED: five-valued (DN-8, Q2)** |
| A2 | **RFC-0005 §10 categories ≠ RFC-0021 §4 subsystems.** RFC-0005 lists 12 categories (Hardware, Kernel, Packages, Filesystem, Services, Networking, Storage, Boot, Logs, Security, Configuration, Applications) — no **Users**, and a **Configuration** category that is a State Domain, not a subsystem — while RFC-0021 §4.1 lists 12 subsystems including **Users** and no Configuration. Two sets of 12 that differ in exactly Users↔Configuration (plus Filesystem/Filesystems naming). | RFC-0005 §10 says categories "map to" RFC-0021 subsystems and State Domains, but defines a distinct set; RFC-0021 §4 is a different 12 | **RATIFIED: RFC-0005 §10 is the source set; mapping reconciles (DN-10, Q5)** |
| A3 | **Where does the Family Profile live vs. the State Domains?** §2.3's profile covers "configuration conventions" (§6.4) and "verification conventions" (§7) — concepts owned by subsystems/domains. Does `FamilyProfile` duplicate state-domain vocabulary or reference it? | §2.3 is descriptive; §6 is a different cut | RFC-0021 (Draft) |
| A4 | **`FactCategory` ownership vs. Layer-0.** RFC-0005 §10 says the category is part of `Scope` (a `schema` type); DN-3 says RFC-0021/`systemmodel` owns FactCategory; `schema` may not import `systemmodel`. The enum cannot both live in `systemmodel` and be referenced by `schema.Scope`. | DN-3 (ratified) vs RFC-0005 §10 vs blueprint §4.1/§8.2 DoD | **RATIFIED: type in `schema`, semantics in `systemmodel` (DN-9, Q3)** |
| A5 | **Does `systemmodel` import `schema` in Iteration 2?** Blueprint §4.1 allows the edge but nothing in RFC-0021's vocabulary requires `schema` types yet. An unused allowed edge is legal but the conformance test must allow both states. | Blueprint §4.1 is permissive, not mandatory | **RATIFIED: edge used for `schema.FactCategory` (DN-11, Q4)** |
| A6 | **Is the §6.9 independence/influence summary encoded?** §6.9 says it is "explanatory; §6.10 is the normative owner." Encoding it as data risks treating it as normative. | RFC-0021 §6.9's own disclaimer | RFC-0021 (Draft) |
| A7 | **§4.14 graph vs §4.2–§4.13 clauses.** The summary graph is condensed; the per-subsystem "Depends on" clauses are the normative source. The two must be consistent but the RFC does not reconcile them line-by-line. | RFC-0021 §4.14 is a rendering, not a second normative list | RFC-0021 (Draft) |
| A8 | **Family name semantics.** "Immutable / atomic systems" is a *class*, not a distro; "Other distros" is a catch-all. Are these first-class `DistributionFamily` members or special markers? | RFC-0021 §2.2 mixes families and classes in one table | RFC-0021 (Draft) |
| A9 | **Draft rework risk.** RFC-0021 is Draft; RFC-0005/0006 that reference it are Draft; §13 terms await RFC-0003 amendment. Every type in this review is against Draft wording. | RFC-0021 status; RFC-0003 Part II §1.1 | RFC-0021 acceptance / amendment |
| A10 | **Blueprint §8.3 pairs `trust` with `systemmodel`.** This review is scoped to `systemmodel`. The DoD line in §8.3 names trust tests. | Task scope vs blueprint iteration boundary | **RATIFIED: `trust` deferred to its own review (DN-7, Q1)** |

---

## 17. Questions that require explicit ratification — all ratified

The six questions posed at review time were ratified by the Operator
(2026-08-04). Each is recorded as a decision note (DN-7…DN-12); the answer is
authoritative for implementation.

1. **Q1 (Scope — DN-7, §16 A10):** Iteration 2 executes as `systemmodel` only.
   `trust` (RFC-0007) is **deferred** to its own design review and iteration.
   Scope is not expanded. The blueprint §8.3 DoD line naming trust tests
   (T9, T11/T12) is not part of this iteration's DoD.
2. **Q2 (FamilyStatus — DN-8, §16 A1):** `FamilyStatus` is **five-valued**,
   including Experimental. RFC-0021's use of Experimental (§2.2 Immutable row,
   §2.4, §5.1) is canonical; the §2.1 four-word table is read as supplemented
   by it.
3. **Q3 (FactCategory — DN-9, §16 A4):** `FactCategory` is **defined in `schema`**
   as part of the canonical vocabulary — the type only. RFC-0021/`systemmodel`
   remains the **sole owner of the semantics**: the category→subsystem mapping,
   the category→state-domain mapping, and the architectural meaning. `schema`
   owns only the type, never the meaning. `schema.Scope` stays category-free;
   the RFC-0005 §10 "part of Scope" binding is deferred.
4. **Q4 (schema import — DN-11, §16 A5):** `systemmodel` **uses** the allowed
   edge: it imports `schema.FactCategory` for the category mapping data
   (a consequence of Q3).
5. **Q5 (category set — DN-10, §16 A2):** The source set is **RFC-0005 §10's 12
   categories** (including Configuration; no Users). The Users↔Configuration
   difference vs RFC-0021 §4 is reconciled by the mapping data owned by
   `systemmodel`, never by changing either RFC.
6. **Q6 (profile fields — DN-12, §16 A3):** `FamilyProfile` carries the **full
   §2.3 five-dimension descriptive set** (package ecosystems, init contract,
   configuration conventions, release model, verification conventions) as
   structured, descriptive data — never as behavior or prescription.

---

## 18. Mapping: RFC section → Type → Interface → Future implementation

| RFC section | Type | Interface (surface) | Future implementation |
|---|---|---|---|
| RFC-0021 §2.1/§2.2 | `FamilyStatus`, `DistributionFamily` | Enums + family→status table | Profile lookup at session init (Scenario 30); collectors target families |
| RFC-0021 §2.3, §5 | `FamilyProfile`, `PackageEcosystem`, `EcosystemStatus`, `FAMILY_PROFILES` | Data table for Supported/Planned families | Iteration 3 normalization uses the profile (RFC-0005 §2, F7); skills target distros (RFC-0011 §2) |
| RFC-0021 §4 | `MachineSubsystem`, `SUBSYSTEM_DEPENDENCIES` | Enum + DAG data | Fact Subject vocabulary (RFC-0005 §3); Verification Scope (RFC-0006 §11) |
| RFC-0021 §6, §6.10 | `StateDomain`, `SUBSYSTEM_STATE_REPRESENTATION` | Enum + mapping data | Verification before/after comparison; Postconditions (RFC-0006 §5) |
| RFC-0021 §11 | additive profile mechanism | Data-driven (new row = new family) | Arch/openSUSE promotion; immutable systems (amendment) |
| RFC-0005 §10 | `FactCategory` (DN-9/DN-10) | Type in `schema`; mapping in `systemmodel` | Fact category on `Scope` (deferred binding); uniform staleness/scope presentation |

---

## 19. Definition of Done for Iteration 2 (systemmodel half)

Per blueprint §8.3 (systemmodel DoD), transcribed and made testable:

- **Profile lookup tests pass:** `DistributionFamily`/`FamilyStatus` data
  matches RFC-0021 §2.2; **only Supported/Planned families have a
  `FamilyProfile`**; unsupported families promise no Facts (blueprint §7
  systemmodel row; RFC-0021 §2.1).
- **Subsystem/State-Domain vocabulary tests pass:** `MachineSubsystem` = the 12
  members of §4.1; `StateDomain` = the 7 members of §6; the
  subsystem→state-representation mapping matches §6.10 exactly and obeys the
  no-two-owners rule (§6.10 rule 2).
- **`systemmodel` is Layer 1:** imports only stdlib and `schema`; no behavior
  beyond data; no I/O; no machine detection.
- **Dependency rules hold:** no forbidden edge; allowed graph and observed graph
  acyclic; package tree still matches blueprint §2 exactly.
- **Full suite green:** pytest, ruff, format, build, pre-commit.
- **`trust` DoD (T9, T11/T12) is NOT part of this iteration's DoD** (Q1, DN-7).

---

# Consistency review against the Blueprint and governing RFCs

This review was checked against the blueprint, RFC-0000–0013, RFC-0021, the two
walkthroughs, the decision traceability matrix, and DN-1…DN-6.

**Consistent (passes):**

- **Module set.** `systemmodel/{profiles,subsystems}` matches blueprint §2 and
  §10 exactly; `tests/test_packages.py` enforces it.
- **Dependency rules.** `systemmodel` stays at Layer 1 with
  `ALLOWED["systemmodel"] = {"schema"}`; no forbidden edge concerns it
  (blueprint §4.2 lists none); the allowed graph is acyclic.
- **Iteration scope and RFC basis.** Scope, work, DoD, and RFC basis are
  transcribed from blueprint §8.3 (systemmodel half).
- **Test focus.** "Only Supported/Planned families have a Family Profile;
  unsupported families promise no Facts" matches blueprint §7 systemmodel row.
- **Ownership.** Every artifact in §11 has exactly one owner except the
  reported `FactCategory` split (A4).
- **Gate.** Iteration 2 produces no production code; vocabulary + data are
  scaffold (blueprint §8.0), consistent with RFC-0000 §5.
- **Walkthroughs.** Failure-injection Scenario 30 ("unknown environment")
  consumes the Family Profile *lookup* (RFC-0021 §2.3) at session init — the
  lookup data is provided here, the fail-closed *behavior* is `core`'s.
  Core-execution Stage 9 normalization consumes the Family Profile — behavior
  is Iteration 3's. No contradiction.
- **Initialization order.** `systemmodel`-after-`schema`, before-`collectors`
  matches blueprint §8.2→§8.3→§8.4 and RFC-0000 §7 (Phase 2, domain spine).
- **Decision notes.** DN-1 (in-memory types only, no formats/APIs) is honored;
  DN-3 is fulfilled and amended by DN-9 (FactCategory type in `schema`,
  `Scope` stays category-free); DN-4/DN-5/DN-6 do not concern `systemmodel`.

**Inconsistent / required attention — all four resolved by ratification:**

1. **`FactCategory` ownership split (DN-3 vs RFC-0005 §10 vs Layer-0)** — the
   central inconsistency. Resolved: type in `schema`, semantics in
   `systemmodel` (DN-9; amends DN-3, Q3).
2. **Category set mismatch (RFC-0005 §10 vs RFC-0021 §4):** Users↔Configuration
   and Filesystem(s) naming. Resolved: RFC-0005 §10 is the source set; the
   mapping reconciles (DN-10, Q5).
3. **"Experimental" status gap in §2.1.** Resolved: five-valued `FamilyStatus`
   (DN-8, Q2).
4. **Blueprint §8.3 iteration pairing (`systemmodel` + `trust`) vs this review's
   task scope.** Resolved: `systemmodel` only; `trust` deferred (DN-7, Q1).

**Ownership conflicts found:** exactly one — the `FactCategory` type/semantics
split (A4); resolved by DN-9. After ratification, no artifact has two owners:
`schema` owns the type, `systemmodel` owns the meaning.
**Circular dependencies found:** none — package graph and subsystem graph are
both DAGs.
**Authority leaks found:** none — `systemmodel` is not an actor in the RFC-0004
§7 matrix; it holds no Observe/Propose/Infer/Verify/Approve/Execute/Refuse/
Persist/Explain authority; it imports only vocabulary.
**Hidden implementation decisions detected and surfaced:** A1 (Experimental),
A2 (category set), A4 (FactCategory placement), A6 (encoding §6.9), A7 (§4.14
vs clauses), A8 (class-vs-family), Q1 (trust pairing), Q3, Q5, Q6. A1, A2, A4,
Q1, Q3, Q5, and Q6 are **ratified** (DN-7…DN-12); A6 (encoding §6.9), A7
(§4.14 vs clauses), and A8 (class-vs-family) remain **open** and are reported
to RFC-0021.

**Verdict.** The design review **passes as a translation**: it adds no
architecture, invents no behavior, respects the gate, and reports every
ambiguity to its owning document (blueprint §0, §11). All six questions are
**ratified** (DN-7…DN-12): Q1 (scope/trust), Q2 (FamilyStatus), and Q3
(FactCategory) were the gating decisions and are resolved. Implementation may
proceed on the revised plan below.

---

# Iteration 2 implementation plan (atomic commits, <300 LOC each)

Precondition (satisfied): the design review passed and Q1–Q6 were ratified
(DN-7…DN-12). The plan below is the revised, ratified plan. Each commit keeps CI
green (ruff, pytest, dependency rules, package-tree test) and adds its
conformance tests. Execution proceeds one atomic commit at a time, with an
architectural review, RFC consistency review, test report, and LOC summary after
each commit. This section records the plan; it does not perform it.

1. **`feat(systemmodel): add distribution family and status vocabulary (RFC-0021 §2)`**
   — `FamilyStatus` (five values, DN-8) and `DistributionFamily` (8 members) in
   `profiles.py`; family→status data matching §2.2. Tests: member sets match
   §2.2 exactly; every §2.2 row present; Immutable row is Experimental. ~120 LOC.
2. **`feat(systemmodel): add package ecosystem vocabulary (RFC-0021 §5)`**
   — `PackageEcosystem` (8) and `EcosystemStatus` (4) in `profiles.py`. Tests:
   §5.2 table transcribed exactly; Debian→apt/dpkg and RedHat→dnf/rpm native
   statuses. ~90 LOC.
3. **`feat(systemmodel): add Family Profile type and profile data (RFC-0021 §2.3)`**
   — `FamilyProfile` (full §2.3 five-dimension descriptive set, DN-12) +
   `FAMILY_PROFILES` for Supported/Planned families only. Tests: only
   Supported/Planned have a profile (DoD); Unsupported/Out-of-Scope families
   promise no Facts; profile is data, not callable behavior. ~180 LOC.
4. **`feat(systemmodel): add machine subsystem vocabulary (RFC-0021 §4)`**
   — `MachineSubsystem` (12 members) in `subsystems.py`. Tests: member set
   equals §4.1 exactly; naming matches §4.2–§4.13. ~80 LOC.
5. **`feat(systemmodel): add subsystem dependency graph (RFC-0021 §4.2–§4.14)`**
   — `SUBSYSTEM_DEPENDENCIES` constant table; acyclicity. Tests: DAG; every
   per-subsystem clause present; §4.14 edges ⊆ data (A7, still open). ~100 LOC.
6. **`feat(systemmodel): add State Domain vocabulary and subsystem mapping (RFC-0021 §6, §6.10)`**
   — `StateDomain` (7 members) + `SUBSYSTEM_STATE_REPRESENTATION` matching
   §6.10; no-two-owners rule. Tests: 7 members; mapping exact; every subsystem
   maps to exactly one representation. ~140 LOC.
7. **`feat(schema): add FactCategory enum (RFC-0005 §10)`** — the 12 categories
   as the canonical type in `schema/fact.py` (Layer 0, stdlib-only; type only,
   no meaning, DN-9/DN-10). Update `tests/test_schema_conformance.py` public
   surface. Tests: exactly the 12 RFC-0005 §10 categories. ~60 LOC.
7b. **`feat(systemmodel): add category→subsystem and category→state-domain mapping (RFC-0005 §10, RFC-0021 §4/§6)`**
   — `CATEGORY_SUBSYSTEMS` and `CATEGORY_STATE_DOMAINS` data referencing
   `schema.FactCategory`, per DN-9/DN-10/DN-11. Tests: each category maps to a
   §6.10 representation; Configuration maps to StateDomain.Configuration; a
   category that is a domain maps to no subsystem; Facts-only categories carry
   no domain. ~90 LOC.
8. **`test(systemmodel): enforce Layer-1 conformance (imports, no behavior, public surface)`**
   — a conformance test mirroring `tests/test_schema_conformance.py`: every
   `systemmodel` module imports only stdlib/schema; no logic beyond data tables;
   `__all__` equals the owned vocabulary; public names defined by their owning
   module; dependency rules + tree still green. ~130 LOC.
9. **`docs: record Iteration 2 clarifications and conformance mapping`**
   — update `docs/implementation-consistency-report.md` with the systemmodel
   type→owner map, ratified answers (Q1–Q6 / DN-7…DN-12), and remaining open
   items. ~130 LOC.

Suggested atomic order: docs-ratification → 1 → 2 → 3 → 4 → 5 → 6 → 7 → 7b → 8
→ 9. All ratification gates (Q1–Q6) are satisfied (DN-7…DN-12), so no commit is
blocked. A **docs-ratification commit** records the updated design review,
decision notes (DN-7…DN-12), and consistency report before any implementation
commit. Q3's answer splits FactCategory into 7 (`schema` type) + 7b
(`systemmodel` mapping), each additive and <300 LOC.

**Execution is gated and proceeds one commit at a time.** Ratification (Q1–Q6)
is complete; the implementation commits proceed under the review protocol
(architectural review, RFC consistency review, test report, LOC summary after
each commit). Nothing is pushed and no PR is opened without explicit request.
