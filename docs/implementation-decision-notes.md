# Implementation Decision Notes

> **Document type:** Implementation decision log, not an RFC.
> **Read this first:** These notes record implementation decisions ratified
> during Iteration 1 (the `schema` package) and Iteration 2 (the `systemmodel`
> layer). They define no new architecture, modify no RFC, and change no
> ownership (blueprint §10; RFC-0004 §3). They fix the *reading* of ambiguities
> reported by the iteration design reviews (`docs/iteration-1-design-review.md`
> and `docs/iteration-2-design-review.md` §16, `docs/iteration-3-design-review.md`
> §11) so that a reported ambiguity cannot reappear in a later iteration. Each
> note names the ambiguity it resolves, its RFC grounding, and the commit that
> embodies it. Amending a note here amends no RFC; it is a re-ratified
> implementation record, subject to the same review that ratified it. Iteration
> 1 notes are DN-1…DN-6; Iteration 2 notes are DN-7…DN-12; Iteration 3 notes are
> DN-13…DN-23 (see the iteration sections below).

---

## DN-1 — In-memory domain types only; RFC-0020 owns formats and APIs

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 1 review) |
| Date | 2026-08-03 |
| Resolves | design review §16 #1; answers §17 #7 |
| Grounding | RFC-0005 §3 ("no schemas and no data formats… in whatever form implementation chooses"); blueprint §5, §6.2, §8.2, §11.2 #4 |
| Embodied in | `880bd47` (the composed `Fact` type) |

**Decision.** Iteration 1 defines concrete canonical **in-memory domain types
only**. These types are **not**: serialization schemas, wire formats,
persistence formats, public APIs, or construction protocols. Language-generated
constructors (for example dataclass constructors) are implementation artifacts,
not architectural interfaces. RFC-0020 exclusively owns: serialization, parsing,
validation, builders, factories, public API signatures, persistence formats,
and wire formats.

**Effect.** A type's concrete in-memory form — its fields, frozen dataclass
shape, and enum members — is the type surface and may be defined in Iteration 1.
Anything in the RFC-0020-owned list must be absent from Iteration 1's types, and
later iterations must not read these types as a format or API contract.

---

## DN-2 — F1 enforced structurally in Iteration 1, behaviorally in Iteration 3

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 1 review) |
| Date | 2026-08-03 |
| Resolves | design review §16 #10; answers §17 #6 |
| Grounding | RFC-0005 §2, §13 (F1); RFC-0004 A1; blueprint §7 (`schema` row) |
| Embodied in | `880bd47` (type-level F1 test in `tests/test_schema_fact.py`) |

**Decision.** Iteration 1 enforces RFC-0005 F1 **structurally**: a Fact has no
raw-text field and no untrusted-text constructor; the only construction path
takes typed canonical components. Iteration 3 enforces F1 **behaviorally**
through the normalization pipeline: only a normalized Observation produces a
Fact's components. The two forms are **complementary, never substitutes** — the
type-level test does not satisfy the behavioral requirement, and the behavioral
pipeline does not make the structural test unnecessary.

**Effect.** F1 conformance at Iteration 1 is the type-level test; passing it is
not a claim that F1 is fully enforced. Iteration 3 must add the
normalization-gate enforcement and the behavioral reading of the RFC-0005 §13
F1 test.

---

## DN-3 — FactCategory stays out of Iteration 1; RFC-0021 owns it

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 1 review); **amended by DN-9 (Iteration 2)** |
| Date | 2026-08-03 |
| Resolves | design review §16 #4; answers §17 #3 |
| Grounding | RFC-0005 §10; RFC-0021 (Draft); blueprint §8.2 (DoD stdlib-only); design review §3, §16 #4 |
| Embodied in | Commit 5 of the plan is **cancelled** (no code) |

**Decision.** Do **not** introduce `FactCategory` in Iteration 1. RFC-0021 is the
sole owner of `FactCategory`. `Scope` remains category-free. Iteration 2
(`systemmodel`) will add `FactCategory` additively. Do not create placeholders.

**Effect.** The plan's Commit 5 (a placeholder `FactCategory` enum) produces no
code; `Scope` keeps its three fields (Subject, Property, Value); the RFC-0021
binding is deferred to Iteration 2, never duplicated inside `schema`.

**Amended by DN-9 (Iteration 2, 2026-08-04).** "Iteration 2 (`systemmodel`)
will add `FactCategory` additively" is fulfilled by DN-9: the `FactCategory`
**type** is added to `schema` (canonical vocabulary, Layer 0), while
RFC-0021/`systemmodel` keeps sole ownership of FactCategory **semantics** — the
category→subsystem and category→state-domain mappings and the architectural
meaning. `Scope` remains category-free. DN-9 supersedes the "never duplicated
inside `schema`" reading for the *type* and preserves it for the *meaning*.

---

## DN-4 — PostCondition is a `schema` pure data type

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 1 review) |
| Date | 2026-08-03 |
| Resolves | design review §16 #5; answers §17 #4 |
| Grounding | RFC-0003 §2.6 (Post-condition); RFC-0006 §5 (Postconditions) |
| Embodied in | Commit 6 (`Action`/`Step`/`Proposal`/`Plan` + `PostCondition`) |

**Decision.** `PostCondition` belongs to `schema` as a pure data type.
Verification owns semantics only: no evaluation, comparison, execution logic,
validation, parsing, serialization, builders, factories, or APIs. Schema owns
only the in-memory type.

**Effect.** `PostCondition` lives in `schema/action.py` as `Step`'s expected
Post-condition, expressed in the same vocabulary as Facts (Subject, Property,
Value). Whether it evaluates, compares, or confirms anything is
Verification's (RFC-0006), never this type's.

---

## DN-5 — VerificationOutcome carries all eight RFC-0006 §7 values

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 1 review) |
| Date | 2026-08-03 |
| Resolves | design review §16 #2; answers §17 #1 |
| Grounding | RFC-0006 §7 (normative oracle); blueprint §8.5 (superseded wording) |
| Embodied in | Commit 7 (`VerificationOutcome`) |

**Decision.** RFC-0006 is authoritative. Implement all eight
`VerificationOutcome` values exactly as defined by RFC-0006 §7. Ignore the older
five-value blueprint wording.

**Effect.** Commit 7's `VerificationOutcome` carries the eight RFC-0006 §7
values; the blueprint §8.5 five-value list (Verified Success / Partial / Unknown
/ Contradicted / Expired) is superseded.

---

## DN-6 — Only VerificationOutcome in Iteration 1; no GoalOutcome

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 1 review) |
| Date | 2026-08-03 |
| Resolves | design review §16 #3; answers §17 #2 |
| Grounding | RFC-0006 §7 (verification Outcome); RFC-0003 §2.3 (Goal terminal result) |
| Embodied in | Commit 7 (`VerificationOutcome`) |

**Decision.** Implement only `VerificationOutcome` in Iteration 1. Do **not**
introduce `GoalOutcome`. `GoalOutcome` is a future type outside this iteration.

**Effect.** `schema/outcome.py` exports only `VerificationOutcome` (RFC-0006
§7). The RFC-0003 §2.3 Goal-level Outcome (Completed / Failed / Cancelled) is
deferred to `core` in a later iteration; the two senses are distinguished by
naming.

---

## Design review §17 question status

Iteration 1's design review posed seven questions. Status is tracked here so a
later iteration can see what was ratified and what still awaits ratification.

| §17 Q | Subject | Status | Where resolved |
|---|---|---|---|
| 7 | Type/signature boundary | **Ratified** | DN-1 (this file) |
| 6 | F1 test scope | **Ratified** | DN-2 (this file) |
| 5 | Observation reference form | **Ratified** | `ObservationReference` placeholder in `552f77d` (reference, never the pipeline's Observation model) |
| 1 | Outcome cardinality (8 vs 5) | **Ratified** | DN-5 (this file) |
| 2 | Goal-level Outcome sense | **Ratified** | DN-6 (this file) |
| 3 | Category binding / `FactCategory` | **Ratified** | DN-3 (this file) |
| 4 | Postcondition ownership | **Ratified** | DN-4 (this file) |

All seven §17 questions are resolved. Deferred without a question: §16 #7
(`MachineIdentity` opaque placeholder, RFC-0014), §16 #8 (freshness-bound
representation, RFC-0020), §16 #9 (Fact Identifier format, RFC-0020).

---

# Iteration 2 decision notes (System Model layer)

The notes below record the Iteration 2 ratification (Operator, 2026-08-04) of
the six questions posed by `docs/iteration-2-design-review.md` §17. They fix
the reading of the ambiguities reported in §16 so that a reported ambiguity
cannot reappear in a later iteration, and they amend DN-3 where Iteration 2
fulfils it. They define no new architecture, modify no RFC, and change no
ownership that the corpus did not already assign (blueprint §10).

## DN-7 — Iteration 2 scope is `systemmodel` only; `trust` is deferred

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 2 ratification) |
| Date | 2026-08-04 |
| Resolves | design review §16 A10; answers §17 Q1 |
| Grounding | blueprint §8.3 (iteration pairing); RFC-0007; task scope |
| Embodied in | Iteration 2 implementation plan (docs-ratification commit) |

**Decision.** Iteration 2 executes as the **System Model layer (`systemmodel`)
only**. The `trust` package (RFC-0007: trust classes T1–T12, sanitizer S1–S8,
Hostile quarantine) is **explicitly deferred** to its own design review and
iteration. Scope is not expanded to include `trust`. Blueprint §8.3's DoD line
naming trust tests (T9, T11/T12) is not part of Iteration 2's DoD.

**Effect.** Iteration 2's Definition of Done and commit plan contain no `trust`
work. When `trust` is implemented, it is first reviewed in its own design review
against RFC-0007 §10, §11, §15.

---

## DN-8 — FamilyStatus is five-valued, including Experimental

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 2 ratification) |
| Date | 2026-08-04 |
| Resolves | design review §16 A1; answers §17 Q2 |
| Grounding | RFC-0021 §2.1 (four status words), §2.2 (Immutable row: Experimental), §2.4 (Experimental as a class), §5.1 (Experimental ecosystem status) |
| Embodied in | Commit 1 (family and status vocabulary) |

**Decision.** `FamilyStatus` has **five** values: Supported, Planned,
Experimental, Unsupported, Out of Scope. RFC-0021's use of **Experimental**
(§2.2 Immutable/atomic row, §2.4, §5.1) is canonical and resolves the internal
inconsistency: §2.1's four-word table is read as supplemented by the status
word the rest of the RFC already uses.

**Effect.** `DistributionFamily` data assigns Experimental to the Immutable /
atomic systems row; every §2.2 row has exactly one of the five statuses. No
family is invented and no RFC is modified; this fixes the reading of a Draft
RFC's internal inconsistency (RFC-0021 remains Draft).

---

## DN-9 — FactCategory type in `schema`; RFC-0021/`systemmodel` owns its semantics (amends DN-3)

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 2 ratification) |
| Date | 2026-08-04 |
| Resolves | design review §16 A4; answers §17 Q3; amends DN-3 |
| Grounding | RFC-0005 §10 (categories; "category membership follows RFC-0021"); RFC-0021 §4, §6, §6.10; blueprint §4.1 (Layer 0/1, `systemmodel`→`schema` edge) |
| Embodied in | Commit 7 (`schema.FactCategory`) and Commit 7b (`systemmodel` mappings) |

**Decision.** The `FactCategory` **enumeration is defined in `schema`** as part
of the canonical vocabulary — the type only. RFC-0021 / `systemmodel` remains
the **sole owner of the category semantics**: the category→subsystem mapping,
the category→state-domain mapping, and the architectural meaning. `schema` owns
only the type, never the meaning. `schema.Scope` remains category-free; the
RFC-0005 §10 statement that the category is part of the Fact's Scope is a
*binding*, not a type, and is deferred to the fact-model binding (Iteration 3+).

**Effect.** `schema/fact.py` gains a `FactCategory` enum (Layer 0, stdlib-only;
no meaning). `systemmodel` carries the category→subsystem and
category→state-domain mapping data, referencing `schema.FactCategory`. DN-3's
"never duplicated inside `schema`" is superseded for the type and preserved for
the meaning. Amending this note amends no RFC (RFC-0005 and RFC-0021 are both
Draft).

---

## DN-10 — FactCategory source set is RFC-0005 §10's 12 categories

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 2 ratification) |
| Date | 2026-08-04 |
| Resolves | design review §16 A2; answers §17 Q5 |
| Grounding | RFC-0005 §10 (normative enumeration for this implementation); RFC-0021 §4 (subsystem set) |
| Embodied in | Commit 7 (`FactCategory` enum) |

**Decision.** The `FactCategory` set is **RFC-0005 §10's 12 categories**
(Hardware, Kernel, Packages, Filesystem, Services, Networking, Storage, Boot,
Logs, Security, Configuration, Applications) — including **Configuration** and
with **no Users** category. The difference vs RFC-0021 §4's 12 subsystems
(Users↔Configuration; Filesystem(s) naming) is **reconciled by the mapping data**
owned by `systemmodel`, never by changing either RFC.

**Effect.** `schema.FactCategory` has exactly the 12 members from RFC-0005 §10.
The category→subsystem and category→state-domain mappings express how a
category that is a domain (Configuration), not a subsystem, maps to its State
Domain and to no subsystem.

---

## DN-11 — `systemmodel` uses the `schema` import edge for FactCategory

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 2 ratification) |
| Date | 2026-08-04 |
| Resolves | design review §16 A5; answers §17 Q4 |
| Grounding | blueprint §4.1 (allowed edge `systemmodel` → `schema`); DN-9 |
| Embodied in | Commit 7b (mapping data) |

**Decision.** The allowed `systemmodel`→`schema` import edge is **used**, not
left latent: `systemmodel` imports `schema.FactCategory` for its
category→subsystem and category→state-domain mapping data. The edge was already
authorized by blueprint §4.1; using it is a consequence of DN-9, not a new
dependency.

**Effect.** The mapping data in `systemmodel/subsystems.py` is keyed by
`schema.FactCategory`. Layer-1 conformance (plan Commit 8) allows exactly
stdlib + `schema` imports for `systemmodel` modules.

---

## DN-12 — FamilyProfile carries the full §2.3 five-dimension descriptive set

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 2 ratification) |
| Date | 2026-08-04 |
| Resolves | design review §16 A3; answers §17 Q6 |
| Grounding | RFC-0021 §2.3 (the five profile elements); §3.1 (init contract); §5 (package ecosystems); §6.2/§6.4 (release model, configuration conventions); §7 (verification conventions) |
| Embodied in | Commit 3 (`FamilyProfile`, `FAMILY_PROFILES`) |

**Decision.** `FamilyProfile` carries the **full §2.3 five-dimension descriptive
set** as structured, descriptive data: package ecosystems (per-family
status), init contract, configuration conventions, release model, and
verification conventions. The profile is **descriptive, not prescriptive**
(RFC-0021 §2.3): it states expectations as data and is never behavior, never a
configuration file, and never code.

**Effect.** Configuration-conventions and verification-conventions fields are
expressed in RFC-0021's own vocabulary (§6.4, §7 capability terms) and are data
only; they do not duplicate State-Domain or Capability *behavior*. Only
Supported and Planned families have a profile (blueprint §7; RFC-0021 §2.1).

---

# Iteration 3 decision notes (Fact Layer + Collectors)

The notes below record the Iteration 3 ratification (Operator, 2026-08-05) of
the eleven questions posed by `docs/iteration-3-design-review.md` §11 (Q1–Q12).
They fix the reading of the reported ambiguities so that a reported ambiguity
cannot reappear in a later iteration, and they **unblock Iteration 3
implementation**: none of Q1–Q12 requires an RFC amendment, a `schema` public
surface change, a new module, or a new dependency edge. They define no new
architecture, modify no RFC, and change no ownership the corpus did not already
assign (blueprint §10).

## DN-13 — Iteration 3 scope is `factlayer` + `collectors`; `verification` and `trust` are not in scope

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 3 ratification) |
| Date | 2026-08-05 |
| Resolves | design review §11 Q1 |
| Grounding | blueprint §8.4 (Iteration 3), §8.5 (Iteration 4); RFC-0005 §2; RFC-0006; RFC-0007 T6; DN-7 |
| Embodied in | Iteration 3 implementation plan (docs-ratification commit) |

**Decision.** Iteration 3 executes as the **`factlayer` + `collectors` pipeline
for the baseline only** (blueprint §8.4). `verification` (RFC-0006) is blueprint
§8.5 (Iteration 4) and is **strictly excluded**. The `trust` package is **not
imported** (DN-7); the Observation→Fact trust-upgrade (RFC-0007 T6) is
*consumed* by normalization as the pipeline's only trust-upgrade step, without
any `trust` code.

**Effect.** No commit builds `verification` or `trust`; both packages stay out
of the import graph until their own iterations.

## DN-14 — FactCategory stays out of Scope; the §10 binding and freshness-per-category defer to RFC-0020

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 3 ratification) |
| Date | 2026-08-05 |
| Resolves | design review §11 Q2 |
| Grounding | RFC-0005 §10, §12, §15 OQ6; DN-9; RFC-0020 |
| Embodied in | Iteration 3 implementation plan (docs-ratification commit) |

**Decision.** `schema.Scope` **remains category-free** (DN-9). Iteration 3 does
**not** bind the RFC-0005 §10 category into the Fact/Scope; the "category is
part of Scope" statement is a binding, not a type (DN-9), and the binding is
deferred **beyond Iteration 3**. Freshness-per-category *bound values* are
RFC-0020 policy (RFC-0005 §12, §15 OQ6); Iteration 3 implements the freshness
*state* mechanism without a category.

**Effect.** No change to `schema.Scope`; freshness bookkeeping is
category-independent; freshness-per-category values are RFC-0020's.

## DN-15 — `schema.ObservationReference` stays the reference-only marker; the Observation model is `factlayer`-internal

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 3 ratification) |
| Date | 2026-08-05 |
| Resolves | design review §11 Q3; fulfils Iteration 1 §17 #5 |
| Grounding | RFC-0005 §2, §5; blueprint §4.1 (Layer 0); DN-1; RFC-0020 |
| Embodied in | Iteration 3 implementation plan (docs-ratification commit) |

**Decision.** `schema.Provenance.observation` keeps the `schema`
`ObservationReference` **reference-only marker**. The real `Observation` model
lives in `factlayer` (Layer 2) and is **not** imported by `schema` (Layer 0) —
no Layer-0→2 import is created (blueprint §4.1). `factlayer` instantiates the
marker as the reference to the Observation a Fact was normalized from, and
resolves it internally. The marker stays out of `schema.__all__`; no `schema`
public surface changes. This honours the Iteration 1 placeholder's contract: the
"zero semantic changes to Provenance" promise is satisfied by the reference-only
marker under the Layer-0 rule.

**Effect.** `Provenance.observation` remains typed to the schema marker (zero
semantic change to Provenance); `Observation` is a `factlayer`-internal type;
`tests/test_schema_conformance.py` is unchanged.

## DN-16 — Failure Facts name the Collector as their confidence source

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 3 ratification) |
| Date | 2026-08-05 |
| Resolves | design review §11 Q4 |
| Grounding | RFC-0005 §3, §5; RFC-0004 A1 |
| Embodied in | Iteration 3 implementation plan (docs-ratification commit) |

**Decision.** An Unknown, Unavailable, or Unsupported Fact's `ConfidenceSource`
names the **Collector/check that was attempted** — the Collector identity
(RFC-0005 §5: the "who" is always a Collector). It is never a percentage and
never an LLM estimate (RFC-0005 §3; RFC-0004 A1).

**Effect.** Failure Facts carry `ConfidenceSource(name = the Collector that ran
or failed)`; no numeric confidence exists.

## DN-17 — Baseline set = distro, kernel, package-state over the Native ecosystems; one question per Collector

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 3 ratification) |
| Date | 2026-08-05 |
| Resolves | design review §11 Q5, Q6 |
| Grounding | RFC-0021 §5.1, §5.2, §5.3; RFC-0003 §2.4; RFC-0005 §2; blueprint §8.4 |
| Embodied in | Iteration 3 implementation plan (docs-ratification commit) |

**Decision.** The baseline Collector set is **distro, kernel, package-state**
(blueprint §8.4). The package-state baseline covers **only the two Native
ecosystems** (apt/dpkg, dnf/rpm; RFC-0021 §5.2, §5.3.1). Secondary (flatpak,
snap, appimage) and Experimental (pacman, zypper, nix) ecosystems are **not**
baseline Collectors; a machine that only offers them yields Unsupported /
Out-of-baseline status, never Unavailable (F11). Granularity: **one
`CollectorSpec` per baseline question** (RFC-0003 §2.4: a Collector "answers one
specific question"), with per-ecosystem declarations allowed under one question.

**Effect.** `collectors/registry.py` declares exactly three baseline
`CollectorSpec`s; the package-state Collector declares Native-ecosystem scope.

## DN-18 — Truncation mechanism with a placeholder default bound; the value is RFC-0020

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 3 ratification) |
| Date | 2026-08-05 |
| Resolves | design review §11 Q7 |
| Grounding | RFC-0005 §2, §15 OQ6; RFC-0020 |
| Embodied in | Iteration 3 implementation plan (docs-ratification commit) |

**Decision.** The truncation **mechanism** — bounded output with
truncation-with-marker, never silently dropped (RFC-0005 §2) — is implemented.
The concrete per-Collector size bound is a **placeholder default constant**; the
authoritative bound value is RFC-0020 policy.

**Effect.** `collect.py` enforces a default bound and records truncation in the
Observation; the bound value remains RFC-0020's.

## DN-19 — Fact store is the in-memory current set; no persistence

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 3 ratification) |
| Date | 2026-08-05 |
| Resolves | design review §11 Q8 |
| Grounding | RFC-0005 §7, §15 OQ2; RFC-0012; RFC-0013 |
| Embodied in | Iteration 3 implementation plan (docs-ratification commit) |

**Decision.** The Fact store is the **in-memory current set** only, with no
durability and no persistence format. RFC-0005 §7 fixes lifecycle *meaning*,
not storage; storage belongs to RFC-0012 (Context/Memory) and RFC-0013 (Audit).

**Effect.** `store.py` implements lifecycle, status, and invalidation in memory;
persistence is deferred.

## DN-20 — Supersession on RFC-0005 §6 component identity; no Identifier format

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 3 ratification) |
| Date | 2026-08-05 |
| Resolves | design review §11 Q9 |
| Grounding | RFC-0005 §6, §7; RFC-0020 (Identifier) |
| Embodied in | Iteration 3 implementation plan (docs-ratification commit) |

**Decision.** A newer Fact supersedes an older one on the **RFC-0005 §6
component identity** — same Machine Identity + Subject + Property — when it is
fresher and its evidence is at least as strong; the older is retired with the
newer recorded as successor. **No Identifier format or generation is invented**;
the Identifier component remains RFC-0020's (Iteration 1 deferred item).

**Effect.** `store.py` supersedes on component identity; no Identifier format.

## DN-21 — Run timing is not a separate field; provenance keeps `collected_at`

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 3 ratification) |
| Date | 2026-08-05 |
| Resolves | design review §11 Q10 |
| Grounding | RFC-0005 §2; DN-1 |
| Embodied in | Iteration 3 implementation plan (docs-ratification commit) |

**Decision.** RFC-0005 §2 lists timing as Raw Output *content*; it is **not** a
separate `Observation`/`RawOutput` field in Iteration 3 (omitted/None).
Provenance keeps `collected_at`. The concrete in-memory type surface is
implementation's per DN-1.

**Effect.** `collect.py` records `collected_at` via provenance; no timing field.

## DN-22 — Critical-failure status is recorded here; the disclose/ask decision is `core`'s

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 3 ratification) |
| Date | 2026-08-05 |
| Resolves | design review §11 Q11 |
| Grounding | RFC-0002 §2.3; RFC-0004 §3, §4.3; blueprint §8.4 |
| Embodied in | Iteration 3 implementation plan (docs-ratification commit) |

**Decision.** On a critical collector failure (e.g., cannot establish the
distro), Iteration 3 records the **Unavailable** status only (RFC-0005 §4; F11).
The disclose + ask-the-Operator *decision* is `core`'s (RFC-0002 §2.3; RFC-0004
§4.3 owns Failure/Recovery), Iteration 10.

**Effect.** `store.py` records the status; no disclose/ask wiring exists in
Iteration 3.

## DN-23 — DoD "F10 conformance" = provenance attached at normalization + loss → Invalid

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 3 ratification) |
| Date | 2026-08-05 |
| Resolves | design review §11 Q12 |
| Grounding | RFC-0005 §5, §13 F10; blueprint §8.4 DoD |
| Embodied in | Iteration 3 implementation plan (docs-ratification commit) |

**Decision.** The blueprint §8.4 DoD phrase "F5/F6/F7/F8/F10 conformance" reads
F10 as **provenance attached at normalization, never added later** (RFC-0005
§5), with loss of provenance → Invalid, not re-attribution (§13 F10 test).

**Effect.** `provenance.py` attaches provenance at normalization; a Fact with
lost provenance is invalidated, not re-attributed.

### Q1–Q12 question status

| §11 Q | Subject | Status | Where resolved |
|---|---|---|---|
| Q1 | Iteration scope (`verification`/`trust`) | **Ratified** | DN-13 (this file) |
| Q2 | FactCategory/Scope binding | **Ratified** | DN-14 (this file) |
| Q3 | ObservationReference replacement | **Ratified** | DN-15 (this file) |
| Q4 | ConfidenceSource on failure | **Ratified** | DN-16 (this file) |
| Q5 | Baseline set contents | **Ratified** | DN-17 (this file) |
| Q6 | Collector granularity | **Ratified** | DN-17 (this file) |
| Q7 | Output-bound value | **Ratified** | DN-18 (this file) |
| Q8 | Store persistence | **Ratified** | DN-19 (this file) |
| Q9 | Supersession identity | **Ratified** | DN-20 (this file) |
| Q10 | Timing in Observation | **Ratified** | DN-21 (this file) |
| Q11 | Critical collector failure | **Ratified** | DN-22 (this file) |
| Q12 | DoD F10 conformance reading | **Ratified** | DN-23 (this file) |

All eleven §11 questions are resolved as decision notes; none requires an RFC
amendment. **Iteration 3 implementation is unblocked** (design review §12, §13
readiness), pending only the implementation commits that follow.
