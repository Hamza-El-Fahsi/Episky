# Implementation Decision Notes

> **Document type:** Implementation decision log, not an RFC.
> **Read this first:** These notes record implementation decisions ratified
> during Iteration 1 (the `schema` package), Iteration 2 (the `systemmodel`
> layer), Iteration 3 (the `factlayer` + `collectors` pipeline), Iteration 4
> (the `verification` layer), and Iteration 5 (the `trust` layer). They define
> no new architecture, modify no RFC, and change no ownership (blueprint §10;
> RFC-0004 §3). They fix the *reading* of ambiguities reported by the iteration
> design reviews (`docs/iteration-1-design-review.md`,
> `docs/iteration-2-design-review.md` §16, `docs/iteration-3-design-review.md`
> §11, `docs/iteration-4-design-review.md` §8,
> `docs/iteration-5-design-review.md` §5) so that a reported ambiguity
> cannot reappear in a later iteration. Each note names the ambiguity it
> resolves, its RFC grounding, and the commit that embodies it. Amending a note
> here amends no RFC; it is a re-ratified implementation record, subject to the
> same review that ratified it. Iteration 1 notes are DN-1…DN-6; Iteration 2
> notes are DN-7…DN-12; Iteration 3 notes are DN-13…DN-24; Iteration 4 notes are
> DN-25…DN-34; Iteration 5 notes are DN-35…DN-39 (see the iteration sections
> below).

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

## DN-24 — Scenario 30 status: Unsupported is reached at normalization for "not supported" family/ecosystem cases

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 3 implementation review) |
| Date | 2026-08-05 |
| Resolves | design review §9.3 (Failure → status); RFC-0005 §4 (Unsupported, "how it is reached"); failure-injection Scenario 30 |
| Grounding | RFC-0005 §4; RFC-0021 §2.1, §2.2; RFC-0005 §13 F11; DN-17, DN-22 |
| Embodied in | `5061d59` (Scenario 30 / F11 tests) and the `normalize` Unsupported path |

**Decision.** Normalization reaches **Unsupported** (RFC-0005 §4) exactly when it
matches a "not supported" family/ecosystem case, per the C7 realization of
Scenario 30:

- A `distro` identity naming a recognized family **with a Family Profile**
  (Supported or Planned) is **Observed**; a recognized family **without a
  profile** (Experimental, Unsupported, Out of Scope) is **Unsupported** and
  carries the family name as its value (the machine *is* an unsupported
  family); an **unrecognized** family output is **Unknown** (fail closed, never
  guessed, never Observed).
- `package-state` requires a promised Native ecosystem in the Family Profile:
  present → **Observed**; absent → **Unsupported**; no Family Profile at all
  (`None` — an unsupported family) → **Unsupported**, fail closed; the runtime
  never fabricates a Family Profile for an unknown family (Scenario 30;
  RFC-0021 §2.3).
- Unsupported, Unknown, and Unavailable stay distinct and are never collapsed
  (F11); an Unsupported Fact flows through the store as a valid current status
  and is never degraded by a later Unknown or Unavailable claim.

**Effect.** `normalize()` emits `FactStatus.UNSUPPORTED` for these cases — the
C7 suite exposed that the scaffold could not reach Unsupported at all, and
closed the gap (RFC-0005 §4 "how it is reached"). The fail-closed
disclose/ask *decision* remains `core`'s (DN-22; RFC-0002 §2.3).

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

---

# Iteration 4 decision notes (Verification layer)

The notes below record the Iteration 4 ratification (Operator, 2026-08-05) of
the ten questions posed by `docs/iteration-4-design-review.md` §8 (Q1–Q10).
They fix the reading of the reported ambiguities so that a reported ambiguity
cannot reappear in a later iteration, and they **unblock Iteration 4
implementation** (design review §10–§12 readiness): none of Q1–Q10 requires an
RFC amendment, a `schema`/`systemmodel`/`factlayer`/`collectors` change, a new
module, or a new dependency edge. They define no new architecture, modify no
RFC, and change no ownership the corpus did not already assign (blueprint §10).

## DN-25 — Iteration 4 scope is `verification` Compare + Outcome semantics only

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 4 ratification) |
| Date | 2026-08-05 |
| Resolves | design review §8 Q1 |
| Grounding | RFC-0006 §6 (process), §4 (Preconditions); blueprint §2 (module set), §8.5 (RFC basis §5–§8); RFC-0005 §2 (Collect/Normalize); RFC-0002 §2.9 (Verification state), invariant 2 |
| Embodied in | Iteration 4 implementation plan (docs-ratification commit) |

**Decision.** Iteration 4 implements only the **Compare → Outcome** steps of the
RFC-0006 §6 process, as semantics over already-normalized Facts. `verification`
never invokes Collect, never models Preconditions (RFC-0006 §4), and never
orchestrates. The runtime obligation (every executed action followed by a
verification attempt; RFC-0002 invariant 2; V2) and Precondition revalidation
(RFC-0006 §4; RFC-0008 P9/P10/P14) are `core`'s / RFC-0008's.

**Effect.** `verification` stays within the blueprint §8.5 basis (§5–§8); no
Collect invocation, no Precondition modeling, no orchestrator in this package.
This mirrors the DN-13/DN-22 pattern (a decision owned by a later iteration).

## DN-26 — Comparable Fact status gate

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 4 ratification) |
| Date | 2026-08-05 |
| Resolves | design review §8 Q2 |
| Grounding | RFC-0006 §3 (evidence = Facts with known provenance and freshness), §9, §13 V9/V14; RFC-0005 §4 (FactStatus), §13 F11/F16 |
| Embodied in | Iteration 4 implementation plan (docs-ratification commit) |

**Decision.** A Fact is comparable evidence only when its status is **Observed**
(RFC-0005 §4) or **Verified** (a runtime-assigned status, DN-27). An
**Unknown/Unavailable/Unsupported** Fact is missing evidence → outcome
**Unknown** (RFC-0006 V9/V14); a **Contradicted** Fact → **Contradicted** (V7);
a **Stale** Fact → excluded (V4); an **Invalid** Fact → excluded, fail-closed
(F16). The eight statuses stay distinct (F11).

**Effect.** Compare applies this status gate on input; the verdict for each
Postcondition follows from the gate plus the value comparison (RFC-0006 §9.2).

## DN-27 — No store write in Iteration 4; the Verified-status write is a runtime obligation

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 4 ratification) |
| Date | 2026-08-05 |
| Resolves | design review §8 Q3 |
| Grounding | RFC-0005 §4 (FactStatus.Verified); RFC-0006 V8, §6 (Compare read-only); RFC-0002 §2.9 (Verification state), invariant 2 (V2) |
| Embodied in | Iteration 4 implementation plan (docs-ratification commit) |

**Decision.** Iteration 4 writes **nothing** to the `factlayer` store. Compare
and Outcome are pure functions. V8's "verification changes nothing but the
Assistant's Fact store" is a *permission*, not an obligation; writing a
`Verified` status or an Outcome into the store is a runtime obligation
exercised by `core` (RFC-0002 §2.9) once it exists.

**Effect.** `verification` never imports the store for writing; the store is
read-only from Compare's perspective; `FactStatus.Verified` has no writer in
this iteration (recorded, not invented).

## DN-28 — Verification Scope is implicit via the Postconditions

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 4 ratification) |
| Date | 2026-08-05 |
| Resolves | design review §8 Q4 |
| Grounding | RFC-0006 §9.7 (scope follows the Postcondition), §11 (scope in RFC-0021 vocabulary), §14 (RFC-0021 referenced, not a dependency); RFC-0021 §11/§12; DN-9/DN-14 precedent |
| Embodied in | Iteration 4 implementation plan (docs-ratification commit) |

**Decision.** No explicit Verification Scope type in Iteration 4. Scope is the
Subjects and Properties named by the declared Postconditions (RFC-0006 V10,
§9.7). A scope type, if ever needed, is RFC-0020's.

**Effect.** Compare covers exactly the Postcondition Subjects/Properties; no
`systemmodel`-bound scope type is introduced (mirrors DN-9/DN-14: a binding,
not a type).

## DN-29 — Compare consumes after-Facts + Postconditions; before/after delta deferred

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 4 ratification) |
| Date | 2026-08-05 |
| Resolves | design review §8 Q5 |
| Grounding | RFC-0006 §9.1 (three Fact sets), §7 (Partially Successful, No Observable Change); RFC-0005 §15 OQ3 (before/after comparison) |
| Embodied in | Iteration 4 implementation plan (docs-ratification commit) |

**Decision.** In Iteration 4, `compare` takes the **after-execution Facts** and
the declared **Postconditions**. The before-state Facts (RFC-0006 §9.1 set 1)
and the before/after delta analysis are deferred to the runtime that passes
before-state (`core`). Consequences (recorded, not implemented): Partially
Successful is producible from after-Facts when multiple Postconditions partly
hold (§7); **No Observable Change** requires before/after delta and is therefore
not producible by Iteration 4's single-snapshot Compare.

**Effect.** No before-Facts input in this iteration; the consequence for No
Observable Change is recorded in the design review §10/§11 commit plan.

## DN-30 — Verification Confidence computation deferred to RFC-0020

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 4 ratification) |
| Date | 2026-08-05 |
| Resolves | design review §8 Q6 |
| Grounding | RFC-0006 §12 (confidence levels), §15 OQ1 (comparison algorithms owned by RFC-0020), V15 |
| Embodied in | Iteration 4 implementation plan (docs-ratification commit) |

**Decision.** Iteration 4 does **not** compute verification confidence
(RFC-0006 §12). V15 is honored by never upgrading an Outcome from insufficient
or contradictory evidence. Confidence levels are derived mechanically (§12 rule
4) as part of the comparison algorithms owned by RFC-0020 (RFC-0006 §15 OQ1).

**Effect.** No confidence type is introduced; outcome determination is
confidence-free (V15).

## DN-31 — Produciable Outcomes; Interrupted/Expired are not Compare outputs

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 4 ratification) |
| Date | 2026-08-05 |
| Resolves | design review §8 Q7 |
| Grounding | RFC-0006 §7 (Outcome table), V3 (determinism), §9.6, V4; RFC-0002 §2.9 (Verification state) |
| Embodied in | Iteration 4 implementation plan (docs-ratification commit) |

**Decision.** Iteration 4's `compare`/`outcome` produce exactly the Outcomes
determinable from the Facts compared: **Verified Success, Verified Failure,
Partially Successful, Unknown, Contradicted** (and No Observable Change once
before-state exists, DN-29). **Interrupted** arises from process cut-off
(operator/reboot/watchdog) — orchestration (RFC-0002 §2.9); it is a value only
(DN-5) with no producer here. **Expired** (freshness bound lapsed during
verification) maps to re-collect-or-Unknown (V4), never a Compare output.

**Effect.** The eight-value `VerificationOutcome` stays complete (DN-5); two
members have no producer in this iteration, recorded.

## DN-32 — Staleness trusted from the Facts; PostCondition.freshness is the declared bound

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 4 ratification) |
| Date | 2026-08-05 |
| Resolves | design review §8 Q8 |
| Grounding | RFC-0006 V4, §9.6, §5 (PostCondition freshness); RFC-0005 §12 (F14/F15, FreshnessState); DN-4 (verification owns semantics only) |
| Embodied in | Iteration 4 implementation plan (docs-ratification commit) |

**Decision.** Compare **reads** the Freshness state carried by each Fact
(RFC-0005 §12) and does not re-derive staleness. A Fact whose freshness state is
not Current is excluded (V4; F14/F15). `PostCondition.freshness` is the declared
bound the comparison checks against (RFC-0006 §5).

**Effect.** No staleness recomputation in `verification`; F14/F15 remain
`factlayer`'s; the DN-4 ownership split is preserved.

## DN-33 — Contradiction is a comparison-level rule; RFC-0005 §8 stays deferred

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 4 ratification) |
| Date | 2026-08-05 |
| Resolves | design review §8 Q9 |
| Grounding | RFC-0006 §7 rule 2, §8 (runtime response), V7; RFC-0005 §8 (deferred by Iteration 3) |
| Embodied in | Iteration 4 implementation plan (docs-ratification commit) |

**Decision.** In Iteration 4, **Contradicted** is produced by a
comparison-level rule in `compare.py`: two comparable Facts over the same
Subject and Property with differing values at the same freshness →
Contradicted (RFC-0006 V7, §7 rule 2). RFC-0005 §8 Fact-relationship mechanics
(the representation side) stay deferred. Reported, not amended: this narrows
RFC-0006 §8's stated dependency on RFC-0005 §8 to the runtime response.

**Effect.** Contradicted is reachable from within the layer; no RFC-0005 §8
relationships are implemented.

## DN-34 — Outcome evidence record is in-memory; durable recording deferred to RFC-0013

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 4 ratification) |
| Date | 2026-08-05 |
| Resolves | design review §8 Q10 |
| Grounding | RFC-0006 V11/V12, §7 rule 4; RFC-0013 (verification records); RFC-0012 (Outcomes as Context material); RFC-0006 §15 OQ5 |
| Embodied in | Iteration 4 implementation plan (docs-ratification commit) |

**Decision.** Iteration 4 carries an **in-memory OutcomeRecord** — the Outcome
plus the Facts that determined it (RFC-0006 §7 rule 4) — as the `outcome`
module's result. Durable recording, retention, and audit wiring are RFC-0013's
(Iteration 7).

**Effect.** V11/V12 are satisfied at the layer level (a verification attempt
records its evidence and Outcome in memory); persistence is deferred.

### Q1–Q10 question status

| §8 Q | Subject | Status | Where resolved |
|---|---|---|---|
| Q1 | Iteration scope / process | **Ratified** | DN-25 (this file) |
| Q2 | Comparable Fact status | **Ratified** | DN-26 (this file) |
| Q3 | Verified-status writer / store write | **Ratified** | DN-27 (this file) |
| Q4 | Verification Scope representation | **Ratified** | DN-28 (this file) |
| Q5 | Before/after Fact sets | **Ratified** | DN-29 (this file) |
| Q6 | Verification Confidence computation | **Ratified** | DN-30 (this file) |
| Q7 | Interrupted/Expired producers | **Ratified** | DN-31 (this file) |
| Q8 | Staleness boundary | **Ratified** | DN-32 (this file) |
| Q9 | Contradiction representation | **Ratified** | DN-33 (this file) |
| Q10 | Evidence record home | **Ratified** | DN-34 (this file) |

All ten §8 questions are resolved as decision notes; none required an RFC
amendment, a `schema`/`systemmodel`/`factlayer`/`collectors` change, a new
module, or a new dependency edge. **Iteration 4 implementation is unblocked**
(design review §10–§12 readiness) and is now **complete**: the planned commits
shipped as `bc3c4dd` (compare), `ac6da1d` (outcome), `a5fdf1a` (Layer-2
conformance and V-invariant tests), and the Iteration 4 consistency-report
commit — see `docs/implementation-consistency-report.md` (Iteration 4 section)
and the implementation mapping in `docs/iteration-4-design-review.md` §10.

---

# Iteration 5 decision notes (Trust layer)

The notes below record the Iteration 5 ratification (Operator, 2026-08-05) of
the eight questions posed by `docs/iteration-5-design-review.md` §5 (Q1–Q8).
They fix the reading of the reported ambiguities so that a reported ambiguity
cannot reappear in a later iteration, and they **unblock Iteration 5
implementation** (design review §6–§10 readiness). Three questions — Q4
(promotion, T6), Q6 (sanitize result contract), Q8 (quarantine container
scope) — are **resolved by the frozen corpus itself** and need no decision note;
the remaining five are recorded as DN-35…DN-39. No question requires an RFC
amendment, a `schema`/`systemmodel`/`factlayer`/`verification`/`secrets` change,
a new module, or a new dependency edge. The notes define no new architecture,
modify no RFC, and change no ownership the corpus did not already assign
(blueprint §10).

## DN-35 — Iteration 5 scope is the `trust` layer; `secrets` is postponed

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 5 ratification) |
| Date | 2026-08-05 |
| Resolves | design review §5 Q1 |
| Grounding | blueprint §8.3 (trust half), §8.6 (`secrets`); DN-7; RFC-0009 §16.3 (redaction consumes RFC-0007 sanitization); blueprint §4.1 (`trust` Layer 1; `secrets`→`trust` edge) |
| Embodied in | Iteration 5 implementation plan (docs-ratification commit) |

**Decision.** Iteration 5 executes as the **Trust Layer (`trust`) only** — the
half of blueprint §8.3 that DN-7 deferred "to its own design review and
iteration". The `secrets` package (RFC-0009, blueprint §8.6) is **postponed to
the next iteration**; its scope is not dropped, and its dependency on `trust` is
preserved (blueprint §4.1: `secrets → {schema, trust}`). The re-order is
dependency-safe: `trust` is Layer 1, `secrets` is Layer 3, and `secrets` still
precedes `context` (Iteration 8), so blueprint Risk #9's mitigation (the
no-secrets boundary established before the Context/Provider join) is preserved.

**Effect.** Iteration 5's Definition of Done and commit plan contain `trust`
work (T9, T11/T12); the blueprint §8.6 `secrets` DoD (SC2–SC5, SC14, SC15) is
not part of Iteration 5 and is renumbered to the following iteration. This note
executes DN-7's promise and mirrors DN-13's scope-fixing pattern.

## DN-36 — Category/domain vocabulary: enumerate RFC-0007's own; defer owned-elsewhere mechanics

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 5 ratification) |
| Date | 2026-08-05 |
| Resolves | design review §5 Q2 |
| Grounding | RFC-0007 §4 (trust domains, normative), §6 (information categories, normative), §6.10/§6.11/§6.12 (owned-elsewhere mechanics), §16.2 (output-size bounds → RFC-0005); DN-3/DN-9/DN-14 pattern (a binding deferred, never a placeholder; no duplicate naming) |
| Embodied in | Iteration 5 implementation plan, Commit C1 |

**Decision.** `trust/classes.py` enumerates as **vocabulary + default-posture
data** the categories and domains whose *semantics* RFC-0007 owns outright — the
categories classification needs: **Observation, Fact, Evidence, Hypothesis,
Provider Output, User Input, Configuration, Logs, Metadata** (§6.1–§6.9) with
the §4 trust domains that originate them, each carrying the §6 default class and
the §4 default posture. The categories whose promotion/demotion **mechanics**
belong to later RFCs are **deferred to their owning iterations**, never stubbed
and never duplicated: **Secrets** (§6.10 → RFC-0009), **Skill Manifest**
(§6.11 → RFC-0011), **Skill Code** (§6.12 → RFC-0011). Output-size bounds are
RFC-0005's (§16.2) and are not data here.

**Effect.** The data surface of `classes.py` carries exactly the
RFC-0007-owned categories/domains and their defaults; no name whose meaning
belongs to RFC-0009/0011 is defined here (one owner per name, RFC-0004 §3).
Mirrors DN-3/DN-9/DN-10/DN-14.

## DN-37 — Classification operates on an internal abstract datum; the `schema` edge stays latent

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 5 ratification) |
| Date | 2026-08-05 |
| Resolves | design review §5 Q3 |
| Grounding | RFC-0007 §4 (every datum originates in exactly one domain), §5 (held at a class), §6 (every datum categorized), §2 (architecture only; no APIs), §11 S7 (deterministic classification); DN-1 (in-memory types are implementation's); blueprint §4.1 (`trust`→`schema` edge allowed, not required); DN-28 precedent (`verification`→`systemmodel` edge latent) |
| Embodied in | Iteration 5 implementation plan, Commit C1 |

**Decision.** The classification entry in `trust/classes.py` operates on an
**internal abstract datum record** — category + content + provenance state +
origin `TrustDomain` — not on `schema.Fact` and not on a bare string. The origin
domain is a **required input** (RFC-0007 §4: every datum originates in exactly
one domain); the category determines the default class (§6). The allowed
`trust → schema` import edge is **left latent** this iteration, mirroring DN-28
(`verification`→`systemmodel`). A `schema.Fact`-bound adapter, if ever needed,
is RFC-0020's (DN-1).

**Effect.** `classify()` is type-free over the canonical `schema` vocabulary; the
declared edge is authorized but unused; RFC-0007's determinism (S7) and
one-origin rule are honored structurally. No new dependency is introduced.

## DN-38 — Sanitizer scope: S3 neutralization primitives now; exact mechanics remain RFC-0012's

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 5 ratification) |
| Date | 2026-08-05 |
| Resolves | design review §5 Q5 |
| Grounding | RFC-0007 §11 (S1–S8 principles), §16.1 (exact mechanics → RFC-0012), §16.6 (detection → RFC-0012); blueprint §8.3 DoD (T9, T11/T12 tests now); RFC-0009 §16.3 (redaction mechanics) |
| Embodied in | Iteration 5 implementation plan, Commit C2 |

**Decision.** `trust/sanitize.py` implements the **deterministic S3
neutralization primitives** — control-character neutralization, ANSI-escape
stripping, and Unicode taming — plus quoting/labeling of the contained form (S4)
and bounding/truncation (S8), as the invariant-bearing core that makes T9/T11/T12
testable now (blueprint §8.3 DoD). It implements **no summarization algorithms,
no Provider View assembly, no detection heuristics, and no redaction catalogue**:
those remain RFC-0012's (exact sanitization mechanics, §16.1) and RFC-0009's
(redaction, §16.3). The primitives satisfy S7 (deterministic and testable) at
the principle level; the *exact* per-character catalogue is RFC-0012's
enforcement point, not this layer's.

**Effect.** The sanitizer exists and is testable per blueprint §8.3 DoD without
pre-empting RFC-0012's catalogue or RFC-0009's redaction. The layer's tests
assert S1 (no upgrade), S6 (fail to Hostile), S7 (determinism), S8 (bounding),
and the S5 no-secret boundary as an invariant, never a mechanism.

## DN-39 — Hostile production paths: the fail-closed set only; detection is not this layer's

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 5 ratification) |
| Date | 2026-08-05 |
| Resolves | design review §5 Q7 |
| Grounding | RFC-0007 §5 (Hostile = Untrusted plus positive signal), §9.6 (provenance loss → Untrusted or Hostile), §15.5–§15.8 (failure behaviour), §13 T11/T12, §16.6 (detection-vs-containment → RFC-0012); RFC-0002 invariant 13 (recording) |
| Embodied in | Iteration 5 implementation plan, Commits C2/C3 |

**Decision.** Within the trust layer, **Hostile is produced only by the
deterministic fail-closed paths**: (1) a datum whose trust class cannot be
established (no origin, no provenance, unparseable) → Hostile (T11, §15.5); (2)
sanitization failure → Hostile (S6, T9); (3) provenance loss the layer must
treat as suspicious → Hostile (§9.6) — otherwise provenance loss → Untrusted.
The layer implements **no detection heuristics**: a *positive adversarial
signal* is RFC-0012's detection stance (§16.6), a defense-in-depth bonus
(RFC-0007 §10, §15.8), and no detector exists this iteration. This mirrors
DN-31's pattern: the layer's *producible* Hostile set is fixed; detection-driven
Hostile has no producer here.

**Effect.** C2/C3 produce Hostile only via the three fail-closed paths; T11/T12
are enforced as tests. No "recognition" code exists; §15.8's *recording* of a
recognized attempt is the Audit's (RFC-0013, Iteration 7), and "recognition"
itself is RFC-0012's.

### Q1–Q8 question status

| §5 Q | Subject | Status | Where resolved |
|---|---|---|---|
| Q1 | Iteration scope / roadmap re-order | **Ratified** | DN-35 (this file) |
| Q2 | Category/domain enumeration scope | **Ratified** | DN-36 (this file) |
| Q3 | Classification input / `schema` edge | **Ratified** | DN-37 (this file) |
| Q4 | Promotion (T6): absent vs declared | **Resolved by corpus** | RFC-0007 §2, §3, §5.1, §8, §13 T6 — no `promote()` in `trust` |
| Q5 | Sanitizer scope vs RFC-0012 | **Ratified** | DN-38 (this file) |
| Q6 | Sanitize result contract | **Resolved by corpus** | RFC-0007 §11 S1/S6, §13 T8/T9, §15.6; RFC-0002 invariant 10; DN-1 |
| Q7 | Hostile production paths | **Ratified** | DN-39 (this file) |
| Q8 | Quarantine container scope | **Resolved by corpus** | RFC-0007 §15.5–§15.8; RFC-0002 invariant 13; RFC-0013; DN-19/DN-34 |

All eight §5 questions are resolved — five as decision notes, three by the
frozen corpus; none requires an RFC amendment, a `schema`/`systemmodel`/
`factlayer`/`verification`/`secrets` change, a new module, or a new dependency
edge. **Iteration 5 implementation is unblocked** (design review §10 readiness),
pending only the implementation commits that follow.
