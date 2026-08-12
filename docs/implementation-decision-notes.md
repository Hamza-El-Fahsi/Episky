# Implementation Decision Notes

> **Document type:** Implementation decision log, not an RFC.
> **Read this first:** These notes record implementation decisions ratified
> during Iteration 1 (the `schema` package), Iteration 2 (the `systemmodel`
> layer), Iteration 3 (the `factlayer` + `collectors` pipeline), Iteration 4
> (the `verification` layer), Iteration 5 (the `trust` layer), and Iteration 6
> (the `secrets` layer). They define no new architecture, modify no RFC, and
> change no ownership (blueprint §10; RFC-0004 §3). They fix the *reading* of
> ambiguities reported by the iteration design reviews
> (`docs/iteration-1-design-review.md`,
> `docs/iteration-2-design-review.md` §16, `docs/iteration-3-design-review.md`
> §11, `docs/iteration-4-design-review.md` §8,
> `docs/iteration-5-design-review.md` §5,
> `docs/iteration-6-design-review.md` §5) so that a reported ambiguity
> cannot reappear in a later iteration. Each note names the ambiguity it
> resolves, its RFC grounding, and the commit that embodies it. Amending a note
> here amends no RFC; it is a re-ratified implementation record, subject to the
> same review that ratified it. Iteration 1 notes are DN-1…DN-6; Iteration 2
> notes are DN-7…DN-12; Iteration 3 notes are DN-13…DN-24; Iteration 4 notes are
> DN-25…DN-34; Iteration 5 notes are DN-35…DN-39; Iteration 6 notes are
> DN-40…DN-44 (see the iteration sections below).

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
edge. **Iteration 5 implementation is unblocked** (design review §10 readiness)
and is now **complete**: the planned commits shipped as `70ff815` (C1, trust
classes), `7864f65` (C2, sanitization), `fb5bcb9` (C3, hostile quarantine),
`2cf85d8` (C4, Layer-1 conformance and invariant tests), with this closeout
commit (C5) recorded in `docs/implementation-consistency-report.md` (Iteration
5 section).

### DN-35 … DN-39 completion status

| Note | Decision | Status | Embodied in | Validated by |
|---|---|---|---|---|
| DN-35 | Iteration 5 = `trust` layer only; `secrets` postponed | **Implemented** | C0 (scope); C1–C4 | `trust` layer complete; `secrets` untouched |
| DN-36 | Category/domain vocabulary: enumerate RFC-0007-owned (§6.1–§6.9); defer owned-elsewhere | **Implemented** | C1 (`classes.py` vocabulary) | `test_trust_classes.py`; S5 boundary test |
| DN-37 | Classification over an internal abstract datum; origin required; `schema` edge latent | **Implemented** | C1 (`Datum`, `classify`) | `test_trust_conformance.py` (latent edge) |
| DN-38 | S3 neutralization primitives + S4/S8 now; exact mechanics remain RFC-0012's | **Implemented** | C2 (`sanitize.py`) | `test_trust_sanitize.py`; S1/S6/S7/S8 tests |
| DN-39 | Hostile produced only by the fail-closed paths; no detection heuristics | **Implemented** | C2/C3 (fail-closed sanitize; quarantine/contagion) | `test_trust_invariants.py` DN-39 enumeration |

**Iteration 5 completion note.** All ratified Trust-layer decisions
(DN-35…DN-39) are implemented and validated: the full suite is green (1049
tests), the Layer-1 conformance and invariant suites (`test_trust_conformance.py`,
`test_trust_invariants.py`) enforce the ratified readings, and the next
iteration is the `secrets` package (RFC-0009) that DN-35 postponed. No new
decision note is required for this closeout.

---

# Iteration 6 decision notes (Secrets layer)

The notes below record the Iteration 6 ratification (Operator, 2026-08-06) of
the five questions posed by `docs/iteration-6-design-review.md` §5 (Q1–Q5).
They fix the reading of the reported ambiguities so that a reported ambiguity
cannot reappear in a later iteration, and they **unblock Iteration 6
implementation** (design review §6–§10 readiness). All five questions are
recorded as decision notes DN-40…DN-44: each fixes an iteration-scope reading
that the frozen corpus leaves open (the corpus supplies the grounding, never
the iteration boundary itself). No question requires an RFC amendment, a
`schema`/`systemmodel`/`trust`/`factlayer`/`verification`/`policy` change, a
new module, or a new dependency edge. The notes define no new architecture,
modify no RFC, and change no ownership the corpus did not already assign
(blueprint §10).

## DN-40 — Iteration 6 scope is the `secrets` layer; the blueprint §8.6/§8.7 numbering is superseded by DN-35

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 6 ratification) |
| Date | 2026-08-06 |
| Resolves | design review §5 Q1 |
| Grounding | DN-35 (secrets postponed to the iteration after `trust`); blueprint §8.6 (`secrets`), §8.7 (`policy`, original numbering); RFC-0000 §4 (RFC-0009 entry: core scope Required, telemetry deferred to post-MVP), §7 (writing order); RFC-0009 roadmap note; consistency report Iteration 5 §Readiness for Iteration 6 |
| Embodied in | Iteration 6 implementation plan (docs-ratification commit C0) |

**Decision.** Iteration 6 executes as the **Secrets Layer (`secrets` only)**
(RFC-0009; blueprint §8.6, re-ordered by DN-35 to follow `trust`). The blueprint
§8.6/§8.7 numbering is **superseded by DN-35's re-order**: `secrets` is Iteration
6, `policy` (blueprint §8.7) shifts to the following iteration, and `secrets`
still precedes `context` (RFC-0012, Iteration 8 per the closeout's label). The
blueprint text itself is **left unchanged** — the re-numbering is recorded here
and in the consistency report as a reported tension, and the blueprint stands
until RFC-0020 (the authoritative build order) lands. No RFC is modified.

**Effect.** Iteration 6's Definition of Done and commit plan contain `secrets`
work only (classifier, redactor, Secure Store abstraction; SC2–SC5
layer-boundary tests, SC14, SC15). The blueprint §8.7 `policy` DoD (I-7, I-11,
P8–P13) is not part of Iteration 6 and is renumbered to the following iteration.
This note executes DN-35's promise and mirrors DN-13/DN-35's scope-fixing
pattern.

## DN-41 — The Secure Store abstraction now; the OS secret store mechanics are RFC-0020's

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 6 ratification) |
| Date | 2026-08-06 |
| Resolves | design review §5 Q2 |
| Grounding | RFC-0009 §9 (persistence philosophy: a value is never durable anywhere but the Secure Store), §30 OQ1 (which OS store / how its interface is presented — RFC-0020); RFC-0001 §8.7 (OS secret store); blueprint §6.2 (`secrets` = "Secure Store adapter interface (mechanics per RFC-0020)"); DN-1 (in-memory types only), DN-19 (in-memory current set), DN-34 (in-memory evidence record) |
| Embodied in | Iteration 6 implementation plan, Commit C3 |

**Decision.** `secrets/store.py` implements the Secure Store **abstraction /
interface contract** — `provision`, `consume`-at-named-boundary (purpose-scoped,
SC6/SC7), `invalidate`, `destroy` (SC12), the owner/custody split (SC8), and the
exposure = compromise invalidation (SC15) — over **in-memory, metadata-only
records** (DN-19/DN-34 precedent). In this iteration a secret value exists only
at the `consume` boundary and is destroyed when the call completes (SC12); the
abstraction never holds a value durably, never re-displays one, and records
metadata only (RFC-0009 §15). The real OS-secret-store mechanics — which store,
its interface, encryption, key management — are **RFC-0020's** (RFC-0009 §30
OQ1) and are not built here. Nothing durable is written.

**Effect.** C3 builds the contract, not a real store; tests assert the
metadata-only, value-at-boundary-only behavior; no persistence beyond in-memory
metadata (SC11 honored by never retaining without consent). Mirrors DN-19/DN-34.

## DN-42 — The redaction framework now; the exact catalogue remains RFC-0020/RFC-0012's

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 6 ratification) |
| Date | 2026-08-06 |
| Resolves | design review §5 Q3 |
| Grounding | RFC-0009 §11 (layered redaction), §13 (SC13 deterministic/testable, SC14 fails closed), §30 OQ2 (exact deterministic rule catalogue — RFC-0020 and RFC-0012); RFC-0007 S5 (redaction is a sanitization), S8 (containment/bounding), §16 OQ3 (redaction mechanics delegated to RFC-0009); DN-38 precedent (Iteration 5 built the S3 primitives now; exact mechanics deferred) |
| Embodied in | Iteration 6 implementation plan, Commit C2 |

**Decision.** `secrets/redact.py` implements the deterministic redaction
**framework now** (RFC-0009 §11): a secret-classifier-gated transformation that
replaces secret-shaped spans at the boundary and fails closed to **WITHHELD**
when the no-secret property cannot be established (SC14), with a minimal,
explicitly **non-exhaustive** mechanical catalogue covering the §1
secret-shaped classes (bearer tokens, API keys, private-key blocks,
secret-shaped configuration). It consumes `trust.sanitize` for the containment
layer (bound/quote, RFC-0007 S8/S4) and `TrustClass` for the never-upgrade
guarantee (RFC-0007 S1, T9) — redaction is not trust, and it never upgrades.
It implements no summarization algorithms and no exhaustive pattern catalogue:
those remain RFC-0012's and RFC-0020's (RFC-0009 §30 OQ2). Redaction transforms
derived artifacts, never the machine's source files (RFC-0009 §11.5).

**Effect.** C2 is the invariant-bearing redactor satisfying SC13/SC14 now
(blueprint §8.6 DoD); the exact per-pattern catalogue is RFC-0020's/RFC-0012's
enforcement point. Mirrors DN-38.

## DN-43 — SC2–SC5 are satisfied as layer-boundary tests now; cross-component enforcement is the owning packages' DoD

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 6 ratification) |
| Date | 2026-08-06 |
| Resolves | design review §5 Q4 |
| Grounding | blueprint §8.6 DoD (SC2–SC5, SC14, SC15 tests pass); RFC-0009 §19–§22 (interactions), §28 (SC2–SC5); RFC-0004 §4.11 (the Context Manager is the enforcement point and may never decide to include a secret); RFC-0012 §32 (context interaction with secrets); RFC-0013 §31 (audit interaction); RFC-0010 §11 (no secret enters a Provider View); RFC-0011 §15 (no secrets to Skills); RFC-0002 invariant 4; Iteration 5 precedent (RFC-0002 invariants 4/5 made testable at the sanitize/containment layer; runtime enforcement is `core`'s) |
| Embodied in | Iteration 6 implementation plan, Commit C4 |

**Decision.** The blueprint §8.6 DoD's **SC2–SC5 half is satisfied at the
secrets layer as layer-boundary tests**: property tests proving the package's
own public surface never exports a value, never offers a path from a public
function to a value-bearing artifact outside `store.consume`, never constructs
Context/Provider/Audit/Skill material, and that SC2–SC5 hold "by construction"
of the surface — the facade re-exports only owned, value-free vocabulary, and
the surface honors blueprint §4.2's "`context` may import `secrets` classifier
types only". The **cross-component enforcement** of SC2 (Context), SC3
(Provider View), SC4 (Audit), and SC5 (extensions) is the Definition of Done of
`context` (Iteration 8), `audit` (Iteration 7), and `providers`/`skills`
(Iteration 9) respectively, and is **recorded, not dropped**, in the
consistency-report deferred-items table. End-to-end SC2–SC5 conformance
completes at those iterations.

**Effect.** C4's SC2–SC5 tests are boundary tests on this package; the deferred
cross-component conformance is named against its owning package. Mirrors the
Iteration 5 pattern for RFC-0002 invariants 4/5.

## DN-44 — `classify.py` operates on an internal abstract input; the `schema` edge stays latent

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 6 ratification) |
| Date | 2026-08-06 |
| Resolves | design review §5 Q5 |
| Grounding | RFC-0009 §1 (value/metadata split), §3 (six classification rules — value-shaped), §21 (a secret value is never a Fact); blueprint §4.1 (`secrets → schema` edge allowed, not required); DN-1 (in-memory types); DN-37 precedent (`trust → schema` edge latent), DN-28 precedent (`verification → systemmodel` edge latent) |
| Embodied in | Iteration 6 implementation plan, Commit C1 |

**Decision.** The secrecy classifier entry in `secrets/classify.py` operates on
an **internal abstract input record** (content + provenance/origin context), not
on a `schema` canonical type and not on a bare string. The declared
`secrets → schema` import edge is left **latent** this iteration (DN-37
precedent). The classifier carries the §1 **value/metadata distinction as
separate result kinds**: a `SecretMetadata` record (existence, provider, dates)
and a value-bearing classification that is never re-displayed or exported
beyond its boundary. A `schema`-bound adapter, if ever needed, is RFC-0020's
(DN-1). A `schema.Fact` is never the classifier's input — Facts are secret-free
by construction (RFC-0009 §21).

**Effect.** `classify` is type-free over the canonical `schema` vocabulary; the
declared edge is authorized but unused; no new dependency is introduced. Mirrors
DN-37/DN-28.

### Q1–Q5 question status

| §5 Q | Subject | Status | Where resolved |
|---|---|---|---|
| Q1 | Iteration scope / renumbering vs blueprint §8.7 | **Ratified** | DN-40 (this file) |
| Q2 | Secure Store abstraction vs real store | **Ratified** | DN-41 (this file) |
| Q3 | Redaction framework scope vs RFC-0020 catalogue | **Ratified** | DN-42 (this file) |
| Q4 | SC2–SC5 DoD without their enforcement points | **Ratified** | DN-43 (this file) |
| Q5 | Classifier input / `schema` edge | **Ratified** | DN-44 (this file) |

All five §5 questions are resolved as decision notes; none requires an RFC
amendment, a `schema`/`systemmodel`/`trust`/`factlayer`/`verification`/`policy`
change, a new module, or a new dependency edge. **Iteration 6 implementation is
unblocked** (design review §10 readiness) and is now **complete**: the planned
commits shipped as `0281e13` (C1, classification), `9ac2ebf` (C2, redaction),
`fae6dcb` (C3, Secure Store abstraction), `ca3f3cb` (C4, Layer-3 conformance and
SC-invariant tests), with this closeout commit (C5) recorded in
`docs/implementation-consistency-report.md` (Iteration 6 section).

### DN-40 … DN-44 completion status

| Note | Decision | Status | Embodied in | Validated by |
|---|---|---|---|---|
| DN-40 | Iteration 6 = `secrets` layer only; blueprint §8.6/§8.7 numbering superseded by DN-35's re-order; `policy` shifts; blueprint text stands until RFC-0020 | **Implemented** | C0 (scope); C1–C4 | `secrets` layer complete; `policy` untouched |
| DN-41 | Secure Store abstraction over in-memory metadata-only records; a value exists only at the consume boundary; OS-store mechanics RFC-0020's | **Implemented** | C3 (`store.py`) | `test_secrets_store.py`; SC1/SC6/SC7/SC8/SC12/SC15 tests |
| DN-42 | Redaction framework + minimal non-exhaustive catalogue now, consuming `trust.sanitize`; exact catalogue RFC-0020/RFC-0012's | **Implemented** | C2 (`redact.py`) | `test_secrets_redact.py`; SC13/SC14, S1/T9 tests |
| DN-43 | SC2–SC5 satisfied as layer-boundary tests now; cross-component enforcement is the owning packages' DoD | **Implemented** | C4 (conformance + invariant boundary tests) | `test_secrets_conformance.py`/`test_secrets_invariants.py` SC2–SC5 |
| DN-44 | Classifier on an internal abstract input; value/metadata split; `schema` edge latent | **Implemented** | C1 (`classify.py`) | `test_secrets_classes.py`; latent-edge conformance test |

**Iteration 6 completion note.** All ratified Secrets-layer decisions
(DN-40…DN-44) are implemented and validated: the full suite is green (1333
tests), the Layer-3 conformance and invariant suites (`test_secrets_conformance.py`,
`test_secrets_invariants.py`) enforce the ratified readings, and the next
iteration is the `policy` package (RFC-0008) that DN-40 shifted to follow
`secrets`. No new decision note is required for this closeout.

---

# Iteration 7 decision notes (Policy layer)

The notes below record the Iteration 7 ratification (Operator, 2026-08-06) of
the ten questions posed by `docs/iteration-7-design-review.md` §10 (Q1–Q10).
They fix the reading of the reported ambiguities so that a reported ambiguity
cannot reappear in a later iteration, and they **unblock Iteration 7
implementation** (design review §16–§17 readiness). All ten questions are
recorded as decision notes DN-45…DN-54: each fixes an iteration-scope or
layer-mechanics reading that the frozen corpus leaves open. RFC-0008 §2 is
architecture-only ("no APIs, no pseudocode, no algorithms, no data formats"),
so each question resolves an *implementation interpretation*, never an
architectural expansion; the corpus supplies the grounding. No question
requires an RFC amendment, a `schema`/`systemmodel`/`trust`/`factlayer`/
`verification`/`secrets` change, a new module (the four `policy` modules are
already scaffolded per blueprint §2), or a new dependency edge beyond the
declared `policy → {schema, trust, factlayer}` set (blueprint §4.1). The
grounding RFCs cited below are Accepted where marked; RFC-0008 and RFC-0021 are
Draft, whose rework risk is accepted per blueprint §9 #2 (the DN posture of
Iterations 1–6).

## DN-45 — Iteration 7 scope is the `policy` layer; the blueprint §8.7/§8.8 numbering is superseded by DN-35/DN-40

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 7 ratification) |
| Date | 2026-08-06 |
| Resolves | design review §10 Q1 |
| Grounding | DN-35 (secrets postponed to the iteration after `trust`), DN-40 (Iteration 6 = `secrets`; `policy` shifts to the following iteration); blueprint §8.7 (`policy`, original numbering "Iteration 6"), §8.8 (`executor` + `audit`, original numbering "Iteration 7"); RFC-0000 §4 (RFC-0008 entry: Security, Required), §7 (writing order); consistency report §Readiness for Iteration 7 ("Iteration 7 is the `policy` package ... with `executor` + `audit` following") |
| Embodied in | Iteration 7 implementation plan (docs-ratification commit C0) |

**Decision.** Iteration 7 executes as the **Policy Layer (`policy` only)**
(RFC-0008; blueprint §8.7, re-ordered by DN-35/DN-40 to follow `secrets`). The
blueprint §8.7/§8.8 numbering is **superseded by DN-35/DN-40's re-order**:
`policy` is Iteration 7, `executor` + `audit` (blueprint §8.8) shift to
Iteration 8, `context` to Iteration 9, `providers` + `skills` to Iteration 10,
and `core` to Iteration 11. The blueprint text itself is **left unchanged** —
the renumbering is recorded here and in the consistency report as a reported
tension, and the blueprint stands until RFC-0020 (the authoritative build
order) lands. No RFC is modified.

**Effect.** Iteration 7's Definition of Done and commit plan contain `policy`
work only (classification, gate table, token mint/validate, default-deny policy
loading; I-7, I-11, RFC-0001 §8.2, P8/P9/P10/P13). The blueprint §8.8
`executor`+`audit` DoD is not part of Iteration 7. This note executes DN-35/
DN-40's promise and mirrors the DN-13/DN-35/DN-40 scope-fixing pattern.

## DN-46 — `classify` consumes `schema.Action` + a referenced-Fact set; the `schema` edge is exercised

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 7 ratification) |
| Date | 2026-08-06 |
| Resolves | design review §10 Q2 |
| Grounding | RFC-0008 §5 (the Action is the atomic approval unit — "a structured object with a description, risk-relevant properties, and verification criteria", RFC-0003 §2.6), §6 (classification reads "the Action's structured description and the Facts it is built on"); blueprint §4.1 (`policy → schema` edge allowed); RFC-0005 §3 (canonical Fact types); DN-1 (final signatures RFC-0020's); DN-37/DN-44 precedent (internal abstract inputs were used for the `trust`/`secrets` classifiers because no canonical object was the subject — the inverse holds here) |
| Embodied in | Iteration 7 implementation plan, Commit C1 |

**Decision.** The classifier entry in `policy/classify.py` consumes the
canonical **`schema.Action`** (RFC-0003 §2.6) together with a **referenced-Fact
set passed at the entry** — the Facts the classification is built on (RFC-0008
§6). This deliberately departs from the `secrets`/`trust` internal-abstract-input
pattern (DN-37/DN-44), which applied where no canonical object existed; here the
Action *is* the object the RFC classifies (RFC-0008 §5) and the `schema` edge is
declared in blueprint §4.1. "Referenced Facts" is read as: the Facts passed at
the classification entry by the caller (`core`, Iteration 11, invokes it per
RFC-0002 §6.2); Step preconditions are the Plan view and are not re-derived by
`policy`. No new input type is invented beyond the canonical `schema` types.

**Effect.** `classify` operates over the canonical vocabulary; the declared
`policy → schema` edge is exercised (unlike the `systemmodel` edge, which stays
latent per DN-47); no new dependency is introduced.

## DN-47 — Internal canonical risk-property vocabulary in `classify.py`; the `systemmodel`/State-Domain edge stays latent

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 7 ratification) |
| Date | 2026-08-06 |
| Resolves | design review §10 Q3 |
| Grounding | RFC-0008 §6 (classification reads "deterministic properties of the Action" — mutates-or-reads a State Domain, subsystems touched, elevation, reversibility, boot/auth risk — "using RFC-0021 §6's State Domains as the vocabulary"; "No rule uses a percentage, a probability, a severity score, or the proposer's words"), §3 non-scope (machine subsystem and state-domain modeling is RFC-0021's); blueprint §4.1 (Layer 3 allowed imports: `schema`, `trust`, `factlayer` — **no `systemmodel`**); `schema.Action.risk_properties` ("Canonical risk-relevant property names (RFC-0008 §6)", `tuple[str, ...]`, built Iteration 1); RFC-0021 (Draft) §6; DN-9 (type in `schema`, semantics owned elsewhere), DN-37/DN-28/DN-44 (latent-edge precedent) |
| Embodied in | Iteration 7 implementation plan, Commit C1 |

**Decision.** The State-Domain vocabulary RFC-0008 §6 references is carried as
**canonical property names** on `schema.Action.risk_properties`; the
name→State-Domain semantics belongs to RFC-0021 (Draft) and is **latent** this
iteration. `policy/classify.py` owns an **internal canonical risk-property
vocabulary** — the deterministic property set §6 lists (mutates-a-State-Domain,
reads-a-State-Domain, touches-packages/services/configuration/network/users/
storage/security-state, uses-elevation, reversible, boot/auth-affecting) —
keyed by the names the Action declares. Classification is a membership test over
these properties. No `policy → systemmodel` import is introduced (blueprint
§4.1 forbids the edge); the `systemmodel` edge stays authorized-but-unused.

**Effect.** The `systemmodel` edge remains latent (DN-9/DN-37/DN-44 pattern);
the conformance test allows the edge's absence; no new dependency edge is
introduced, and no RFC-0021 type is consumed while it is Draft.

## DN-48 — The token carries an opaque in-memory machine-state snapshot reference; the State-Domain diff is runtime-owned

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 7 ratification) |
| Date | 2026-08-06 |
| Resolves | design review §10 Q4 |
| Grounding | RFC-0008 §8 (token bound to "the Machine State it was approved against"; invalidation on a change to "any State Domain it depends on (RFC-0021 §6)"), §9 (re-validation compares "State Domains the Action touches against the snapshot the token was approved against"), §2 (architecture only — "no data formats"), §3 non-scope (state-domain modeling is RFC-0021's); RFC-0002 invariant 11 (token bound to its action, its time, and the machine state it was approved against); RFC-0021 (Draft) §6; DN-19/DN-34/DN-41 (in-memory records precedent) |
| Embodied in | Iteration 7 implementation plan, Commit C3 |

**Decision.** The machine-state snapshot a token is bound to (RFC-0008 §8;
RFC-0002 invariant 11) is represented this iteration as an **opaque in-memory
snapshot reference**: the snapshot's identity plus the Facts it was approved
against (a metadata record, DN-19/DN-34/DN-41 precedent). Boundary re-validation
(RFC-0008 §9) is the deterministic combination of (a) Action-identity match
(§9.3), (b) referenced-Fact staleness via `factlayer` freshness (§9.1), and (c)
the machine-state check (§9.2) as a **runtime-supplied state-change signal** —
the concrete State-Domain diff is RFC-0021's vocabulary and the runtime's
mechanism (RFC-0008 §2, §3), exercised at `executor`/`core` in later
iterations. Any uncertainty fails closed: refuse, disclose, re-present
(RFC-0008 §9; RFC-0002 §2.8; RFC-0007 T11).

**Effect.** C3 builds the re-validation mechanics over an in-memory snapshot
reference; the RFC-0021 State-Domain diff is recorded as a deferred,
runtime-owned item, not built here.

## DN-49 — `mint` requires an explicit decision input; no input or rejection mints nothing

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 7 ratification) |
| Date | 2026-08-06 |
| Resolves | design review §10 Q5 |
| Grounding | RFC-0008 §8 Creation ("mints the token only after (a) classified and gated and (b) the Operator has made an explicit decision — approve, auto-permit, or override"), §12 ("Nothing is approved by silence... no 'accept after timeout'"), §13 P5 (explicit; nothing proceeds on silence), P10 (a Blocked Action proceeds only by an explicit, audited override); RFC-0004 §4.8 (the Approval Engine is the Operator's instrument, matrix C11; "May never decide: whether to approve"); RFC-0002 §2.7 (approve / override a block / reject); RFC-0008 §2 (architecture only — the interface is not fixed here) |
| Embodied in | Iteration 7 implementation plan, Commit C3 |

**Decision.** `mint` in `policy/tokens.py` takes an **explicit decision input**
— APPROVE, AUTO_PERMIT, or OVERRIDE (RFC-0008 §8), plus REJECT (RFC-0002
§2.7) — as an argument, never by inference and never on silence. An absent
decision, a rejection, or a timeout yields **no token and consumes nothing**
(P5; RFC-0008 §12 "no 'accept after timeout'"). AUTO_PERMIT is accepted only
for an allowlisted read-only Action (RFC-0008 §6; RFC-0001 §8.3);
auto-permission is per-Action, never a reusable pass. OVERRIDE is accepted only
for a Blocked Action and produces an override-scoped token plus an override
record (P10; RFC-0002 invariant 12). The decision's delivery path (`core`/`cli`)
is a later iteration; this layer only defines and consumes the input.

**Effect.** P5/P10/I-12 are testable at the layer now; `mint` never decides
whether to approve (RFC-0004 §4.8 C11) and never mints on its own authority (A6).

## DN-50 — P13/I-13 satisfied as in-memory issuance records now; the durable Audit write is `audit`'s DoD

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 7 ratification) |
| Date | 2026-08-06 |
| Resolves | design review §10 Q6 |
| Grounding | RFC-0008 §8 ("Issuance is written to the Audit before execution may proceed (RFC-0002 invariant 13; RFC-0004 A10)"), §13 P13 (approval is recorded before it is spent), §15 ("if the Audit cannot record, the consequence it precedes is blocked"), §3 non-scope (Audit and transcript mechanics is RFC-0013's); RFC-0002 invariant 13; RFC-0004 A10; RFC-0013 (Draft; `audit`, Iteration 8); DN-34 (in-memory evidence-bearing OutcomeRecord), DN-41 (in-memory metadata-only records), DN-43 (layer-boundary tests now; cross-component enforcement is the owning package's DoD) |
| Embodied in | Iteration 7 implementation plan, Commit C3 |

**Decision.** The blueprint §8.7 DoD's **P13 is satisfied at the policy layer as
layer-boundary records**: every mint (approve/auto-permit/override) and every
rejection produces an in-memory metadata record held by the layer, and a
**layer-boundary test** proves no token is spendable without a prior
issuance/override/auto-permit/rejection record (P13; RFC-0002 invariant 13;
RFC-0004 A10). The **durable Audit write** of these records is the Definition of
Done of `audit` (Iteration 8, RFC-0013), recorded not dropped, per the DN-43
layer-boundary precedent. A consequence never proceeds unrecorded or unpresented
(RFC-0008 §15).

**Effect.** C3's P13 tests are boundary tests on this package; the durable
write is named against `audit` in the consistency-report deferred-items table.

## DN-51 — Default-deny policy-loading mechanism now; the shipped contents are RFC-0020's

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 7 ratification) |
| Date | 2026-08-06 |
| Resolves | design review §10 Q7 |
| Grounding | blueprint §8.7 (work: "default-deny policy loading"); RFC-0008 §7 (Policy evaluation: "the deterministic rules the project ships and the Operator sets within their authority" — default-deny, allowlists, elevation limits, standing-approval bounds; "Where no rule matches, the decision is blocked — default deny and fail closed"), §13 P3, §16 ("The specific default contents of the read-only allowlist, standing-approval defaults, and expiry windows are policy content for RFC-0020"); RFC-0001 §8.2 (default deny, explicit allow), §8.12 (fail closed); RFC-0004 §4.7; DN-1 (no production content before RFC-0020) |
| Embodied in | Iteration 7 implementation plan, Commit C2 |

**Decision.** `policy/policy.py` builds the deterministic **policy mechanism**
(RFC-0008 §7) this iteration: the rule set, a **structural default-deny rule** —
no rule matches → blocked (P3; RFC-0001 §8.2) — the read-only-allowlist
membership function (empty by default), elevation bounds (DN-53), per-class
retry ceilings (RFC-0008 §8), and a **fail-closed `load`** that blocks and
discloses on an unparseable rule (P3; RFC-0001 §8.12). The **specific shipped
contents** — which Actions are allowlisted, the expiry windows, the
standing-approval defaults, the absolute-block list — are **RFC-0020's**
(RFC-0008 §16) and are not invented here (DN-1; blueprint §8.0).

**Effect.** C2 implements the mechanism, not the content; the allowlist is empty
until RFC-0020, and default-deny is enforced by construction.

## DN-52 — Standing approvals: representation + evaluation mechanism now; no shipped defaults

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 7 ratification) |
| Date | 2026-08-06 |
| Resolves | design review §10 Q8 |
| Grounding | RFC-0008 §7 (Policy evaluation: "whether a standing approval applies and is in scope and unexpired"), §8 (a standing approval is a Policy construct that pre-mints a "narrowly scoped, expiring authorization" for a class of Actions within a defined scope and a risk-class ceiling; "never covers a Blocked Action", "never raises a class ceiling", always visible), §13 P11 (scoped, bounded, expiring, never blanket); RFC-0001 §8.3 (standing approvals expire; no "always yes"); RFC-0008 §16 (standing-approval defaults — RFC-0020) |
| Embodied in | Iteration 7 implementation plan, Commits C2/C3 |

**Decision.** The standing-approval **construct** (RFC-0008 §8) is represented and
evaluated this iteration: a Policy record with a defined scope, a risk-class
ceiling, and an expiry; evaluation answers "does it apply, is it in scope, is it
unexpired" (RFC-0008 §7, Policy-evaluation row) and never covers a Blocked
Action and never raises a ceiling (P11; RFC-0001 §8.3). No **shipped defaults**
are invented — which standing approvals the project ships is RFC-0020's
(RFC-0008 §16). Any pre-minting is exercised through the same `mint` machinery
(DN-49) and stays per-Action at execution; the construct itself never becomes
blanket authority.

**Effect.** P11 is testable at the mechanism level (scope/ceiling/expiry/
Blocked-exclusion) with no policy content invented.

## DN-53 — Elevation: an elevation risk-property makes the class at least Consequential and the token records bounds; the mechanism is `executor`'s

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 7 ratification) |
| Date | 2026-08-06 |
| Resolves | design review §10 Q9 |
| Grounding | RFC-0008 §8 (Elevation: "an elevated Action is at least Consequential (§6), its elevation bounds are part of the token"), §13 P12 (explicit, per-action, scoped, and revoked; "an elevated Action's token carries its elevation bound"), §6 (Consequential includes "anything requiring elevation"); RFC-0001 §8.6 (explicit, scoped, re-authenticated); RFC-0008 §3 non-scope (the elevation mechanism is the machine's own, RFC-0021 §3.3); blueprint §2 (`executor/elevation.py`), §8.8 (`executor`, Iteration 8) |
| Embodied in | Iteration 7 implementation plan, Commits C1/C3 |

**Decision.** Classification reads an **elevation** risk-property from the
Action's canonical properties (RFC-0008 §6; DN-47) and maps an elevated Action
to **at least Consequential** (RFC-0008 §8). The token records the **elevation
bounds** the approved Action declared (§8 scope list), so P12's "the token
carries its elevation bound" is testable now. The **mechanism** — how the
machine's own privilege-escalation is invoked and revoked — is the
`executor.elevation` module's (blueprint §2, §8.8; RFC-0021 §3.3; RFC-0001
§8.6) and is not built here (P12's execution half). Elevation never persists and
never covers unapproved work (RFC-0008 §8).

**Effect.** The at-least-Consequential rule and the token's elevation field are
testable at C1/C3; invocation and revocation are `executor`'s DoD (Iteration 8).

## DN-54 — Plan envelope: meet rule + envelope-scoped token now; re-presentation is `core`'s

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 7 ratification) |
| Date | 2026-08-06 |
| Resolves | design review §10 Q10 |
| Grounding | RFC-0008 §6 (a Plan's class is the meet of its Steps' classes — "the most restrictive among them", RFC-0007 §5.1), §8 Scope ("for a plan envelope — the set of Steps as presented (§11)"), §11 (envelope approval; "the envelope approves exactly the Steps that were shown"), §13 P6/P7 (envelope scoped to the shown Steps; consumed as Steps run); RFC-0002 §7 (a changed plan is re-normalized, re-classified, re-presented); blueprint §8.7 (DoD names no plan item; the §8.7 RFC basis is §6–§8, §10, §13, which includes §6's meet rule and §8's envelope scope but not §11's runtime re-presentation) |
| Embodied in | Iteration 7 implementation plan, Commits C1/C3 |

**Decision.** The **meet rule** (RFC-0008 §6) is implemented in `classify` — a
Plan's class is the most restrictive of its Steps' classes — and the **envelope
token** carries the presented Step set (RFC-0008 §8) so P6/P7 hold for an
envelope: a deviation, or a Step whose token was consumed by a failed attempt,
is re-approved, never inherited (RFC-0008 §8 single-use; RFC-0002 §7). **Plan
re-presentation** after deviation, failure, or partial execution is a runtime
(`core`) obligation (RFC-0002 §7, §2.8–§2.10; RFC-0008 §11) and is not built
here; the layer provides the classification and the envelope token the runtime
consumes.

**Effect.** The meet rule and the envelope-scoped token are testable at C1/C3;
deviation handling is recorded as `core`'s deferred item.

### Q1–Q10 question status

| §10 Q | Subject | Status | Where resolved |
|---|---|---|---|
| Q1 | Iteration scope / renumbering vs blueprint §8.7/§8.8 | **Ratified** | DN-45 (this file) |
| Q2 | `classify` input: `schema.Action` + referenced Facts vs internal input | **Ratified** | DN-46 (this file) |
| Q3 | Risk-property / State-Domain vocabulary without a `systemmodel` edge | **Ratified** | DN-47 (this file) |
| Q4 | Machine-state snapshot representation / state-change detection | **Ratified** | DN-48 (this file) |
| Q5 | Decision-input abstraction for `mint` (P5/P10 testable) | **Ratified** | DN-49 (this file) |
| Q6 | P13/I-13 records without the Audit package | **Ratified** | DN-50 (this file) |
| Q7 | Default-deny policy loading: mechanism vs RFC-0020 content | **Ratified** | DN-51 (this file) |
| Q8 | Standing-approval construct in scope vs deferred | **Ratified** | DN-52 (this file) |
| Q9 | Elevation representation (at-least-Consequential; bounds on token) | **Ratified** | DN-53 (this file) |
| Q10 | Plan envelope: meet rule + envelope token vs deferred | **Ratified** | DN-54 (this file) |

All ten §10 questions are resolved as decision notes; none requires an RFC
amendment, a `schema`/`systemmodel`/`trust`/`factlayer`/`verification`/`secrets`
change, a new module, or a new dependency edge. **Iteration 7 implementation is
unblocked** (design review §16 readiness) and is now **complete**: the planned
commits shipped as `76f6476` (C1, risk classification), `b3e4b20` (C2, policy
gates and evaluation), `3abe96c` (C3, policy token machinery), `720a20a` (C4,
Layer-3 conformance and P-invariant tests), with this closeout commit (C5)
recorded in `docs/implementation-consistency-report.md` (Iteration 7 section).

### DN-45 … DN-54 completion status

| Note | Decision | Status | Embodied in | Validated by |
|---|---|---|---|---|
| DN-45 | Iteration 7 = `policy` layer only; blueprint §8.7/§8.8 numbering superseded by DN-35/DN-40's re-order; blueprint text stands until RFC-0020 | **Implemented** | C0 (scope); C1–C4 | `policy` layer complete; `executor`/`audit` untouched |
| DN-46 | `classify` consumes `schema.Action` + a referenced-Fact set; the `schema` edge is exercised | **Implemented** | C1 (`classify.py`) | `test_policy_classify.py`; exercised-edge conformance test |
| DN-47 | Internal canonical risk-property vocabulary in `classify.py`; the `systemmodel`/State-Domain edge stays latent | **Implemented** | C1 (`RISK_PROPERTIES`) | `test_policy_classify.py`; latent-edge conformance test |
| DN-48 | Token carries an opaque in-memory machine-state snapshot reference; the State-Domain diff is runtime-owned | **Implemented** | C3 (`tokens.py`) | `test_policy_tokens.py`; P8/P9 boundary tests |
| DN-49 | `mint` requires an explicit decision input; no input or rejection mints nothing (P5); override only for Blocked (P10) | **Implemented** | C3 (`mint`) | `test_policy_tokens.py`; P5/P10 tests |
| DN-50 | P13/I-13 satisfied as in-memory issuance records now; the durable Audit write is `audit`'s DoD | **Implemented** | C3 (`TokenRecord`) | `test_policy_tokens.py`; P13/I-13 tests |
| DN-51 | Default-deny policy-loading mechanism now; the shipped contents are RFC-0020's | **Implemented** | C2 (`load`, `gates.py`) | `test_policy_gates.py`; `test_policy_evaluation.py` |
| DN-52 | Standing approvals: representation + evaluation mechanism now; no shipped defaults | **Implemented** | C2 (`StandingApproval`) | `test_policy_evaluation.py`; P11 boundary tests |
| DN-53 | Elevation risk-property → at least Consequential; token records bounds; mechanism is `executor`'s | **Implemented** | C1/C3 (`classify`, `Token`) | `test_policy_classify.py`; `test_policy_invariants.py` elevation tests |
| DN-54 | Plan envelope: meet rule + envelope-scoped token now; re-presentation is `core`'s | **Implemented** | C1/C3 (`classify_plan`, `meet`, `mint`) | `test_policy_classify.py`; `test_policy_tokens.py`; `test_policy_invariants.py` meet tests |

**Iteration 7 completion note.** All ratified Policy-layer decisions
(DN-45…DN-54) are implemented and validated: the full suite is green (1722
tests), the Layer-3 conformance and invariant suites
(`test_policy_conformance.py`, `test_policy_invariants.py`) enforce the ratified
readings, and the next iteration is the `executor` + `audit` layer (RFC-0004
§4.8–§4.10; RFC-0013) that DN-45 shifted to follow `policy`. No new decision
note is required for this closeout.

# Iteration 8 decision notes (Executor + Audit layer)

The notes below record the Iteration 8 ratification (Operator, 2026-08-07) of
the ten questions posed by `docs/iteration-8-design-review.md` §10 (Q1–Q10).
They fix the reading of the reported ambiguities so that a reported ambiguity
cannot reappear in a later iteration, and they **unblock Iteration 8
implementation** (design review §16–§17 readiness). All ten questions are
recorded as decision notes DN-55…DN-64: each fixes an iteration-scope or
layer-mechanics reading that the frozen corpus leaves open. RFC-0013 is
architecture-only ("no schemas, no APIs"; RFC-0005 §3; RFC-0013 §0), so each
question resolves an *implementation interpretation*, never an architectural
expansion; the corpus supplies the grounding. No question requires an RFC
amendment, a `schema`/`systemmodel`/`trust`/`factlayer`/`verification`/
`secrets`/`policy` change, a new module (the six `executor`/`audit` modules are
already scaffolded per blueprint §2), or a new dependency edge beyond the
declared `executor → {schema, audit, secrets}` and `audit → {schema, secrets}`
sets (blueprint §4.1). The grounding RFCs cited below are Accepted where
marked; RFC-0013 and RFC-0021 are Draft, whose rework risk is accepted per
blueprint §9 #2 (the DN posture of Iterations 1–7).

## DN-55 — The runner consumes an injected run primitive; the `executor` package performs no I/O and no subprocess spawn

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 8 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q1 |
| Grounding | RFC-0004 §4.9 (the Executor "runs approved Actions against the Machine" — the sanctioned Action runner, the sole Execute cell); RFC-0002 §2.8 (the approved action runs "under the executor's guardrails: scoping, timeouts, output capture, secret-free handling, elevation per action"); RFC-0002 §6.2 (the Executor is "consulted only in Executing, and only with a valid, re-validated approval token"); RFC-0001 §5 (Action Execution responsibilities); RFC-0002 §6 (deterministic tools are the only subsystem that reads the machine); blueprint §3/§5 (executor public contract: "Run one token-bound Action under guardrails; report start/end and sanitized output; scoped elevation"), §8.8 (scaffold iteration) |
| Embodied in | Iteration 8 implementation plan, Commit C3 |

**Decision.** The runner takes an **injected run primitive**
(`run(action, argv) -> RunResult`) supplied at the boundary. The `executor`
package itself performs **no I/O and no subprocess spawn** — it validates the
token, constructs the argv-structured descriptor, applies the guardrails,
writes the execution records through `audit`, and hands the sanctioned
descriptor to the injected primitive; the primitive's real machine interaction
is `core`'s wiring at Iteration 10. This makes I-1/I-5/I-11 and the guardrails
testable deterministically against a test primitive now, without a real
subprocess and without `executor` reading the machine itself (RFC-0002 §6.2:
the runner is not a deterministic-tools consumer). The package stays
import-safe and conformance-testable at Layer 4.

**Effect.** The run boundary is an injectable seam, not a subprocess call; the
Layer-4 conformance suite can assert "no I/O, no subprocess, no forbidden
stdlib" inside `executor`.

## DN-56 — The token crosses as a structural handoff value; the runner re-validates it locally without importing `policy`

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 8 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q2 |
| Grounding | RFC-0008 §8 (the Approval Token is "the only thing that carries permission to the Executor"; its scope list), §10 layer 3 (Independent enforcement: "the Executor does not trust the re-validation by word; it independently refuses to run anything not carrying a valid, unexpired, state-consistent token"); RFC-0004 A2 (Executor never invents; runs only token-bound Actions), §4.9 (Depends on: Approval Engine tokens); RFC-0002 I-11; blueprint §4.2 (`executor` must not import `policy`); Iteration 7 review §3 ("the token is the handoff value, not a call") |
| Embodied in | Iteration 8 implementation plan, Commit C3 |

**Decision.** The token crosses the boundary as a **structural handoff value**:
its public fields (approved Action identity, class, gate, machine-state
snapshot reference, session identity, expiry, consumed flag, elevation bounds)
are read as a plain schema-shaped record. The runner **re-validates it locally
and deterministically** — valid / unexpired / not-consumed / Action-identity
match / session match (RFC-0008 §8 scope; RFC-0002 I-11) — without importing
`policy`. This is RFC-0008 §10 layer 3's independent enforcement: the gate is
enforced in two components (the Approval Engine's re-validation at `policy` and
the Executor's own check here) so that a compromise of either still leaves the
other refusing (RFC-0004 §9.7/§9.8). The token remains a `policy`-owned type at
its mint site; only its *fields* cross, mirroring how the gate was carried as a
field at `policy` (DN-46's carried-value precedent).

**Effect.** Independent enforcement (P1's execution half, DN-45) is testable at
the runner's surface; the `policy` import edge stays forbidden and the Layer-4
conformance suite enforces it.

## DN-57 — The runner re-validates locally and consumes the machine-state + precondition verdict as an explicit boundary input

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 8 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q3 |
| Grounding | RFC-0008 §9 (preconditions re-checked at the execution boundary: assumptions/staleness, machine-state domains, Action identity), §10 layer 2 (re-validation at Awaiting Approval → Executing); RFC-0002 §6.2 edge (b) (the token "is re-validated against current policy, elevation, and machine state" at the Awaiting Approval → Executing edge); RFC-0002 I-11; RFC-0021 (Draft) §6 (State Domains); DN-48 (token carries an opaque machine-state snapshot reference; the State-Domain diff is RFC-0021's/runtime's); blueprint §4.2 (`executor` may not import `factlayer`/`policy`) |
| Embodied in | Iteration 8 implementation plan, Commit C3 |

**Decision.** The runner re-validates **what it can locally** (valid /
unexpired / consumed / Action-identity / session, per DN-56) and consumes the
**machine-state + precondition re-validation as an explicit boundary input** —
a verdict computed by the §6.2 edge-(b) handler / runtime at the Awaiting
Approval → Executing edge (RFC-0002 §6.2; RFC-0008 §9). Any uncertainty in
either the local check or the consumed verdict → **refused** (fail closed,
RFC-0008 §9 "If any precondition is uncertain, the gate treats it as not
holding"; RFC-0002 §2.8). The runner never re-derives the State-Domain compare
itself (that requires the Draft vocabulary and forbidden imports); the compare
is the runtime's, exactly as DN-48 recorded.

**Effect.** P9's boundary re-validation is satisfied as local-check +
consumed-verdict, keeping `executor` free of `factlayer`/`policy` imports while
making the refusal behavior (fail closed on uncertainty) testable now.

## DN-58 — Execution uses an argv-structured descriptor built from the sanctioned Action structure only; no shell string is ever constructed

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 8 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q4 |
| Grounding | RFC-0002 I-5 ("No untrusted text is ever interpolated into a command. Nothing from the LLM, from machine output, or from a skill is executed as a shell string. Actions are built from sanctioned structures only"); RFC-0001 §8.4 rule 4 ("No shell interpolation of untrusted text. Ever."); RFC-0007 §4.4 (classification/execution reads structured Action descriptions, never raw untrusted text); RFC-0003 §2.6 (Action is a structured canonical type) |
| Embodied in | Iteration 8 implementation plan, Commit C3/C5 |

**Decision.** The runner derives an **argv-structured execution descriptor**
(`[executable, *args]`) from the sanctioned `schema.Action` structure only —
never from free text, never from machine output, never from a skill — and
**no shell string is ever constructed** at the executor boundary. The run
primitive receives the descriptor as structured values. I-5 is enforced
structurally and asserted by a boundary test that feeds LLM/machine/skill-shaped
text and proves no shell string results (RFC-0002 I-5; RFC-0001 §8.4 rule 4).

**Effect.** I-5 becomes a structural, testable guarantee of the runner, not an
admonition; the argv boundary is what the injected run primitive (DN-55)
consumes.

## DN-59 — Guardrail mechanism now (timeout with placeholder bound; bounded, redacted output capture); concrete values are RFC-0020's

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 8 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q5 |
| Grounding | RFC-0001 §5 (Action Execution: "Apply the technical guardrails of a sanctioned action (scoping, timeouts, output capture, no secret leakage)"), §8.8 (output is limited — bounded, redacted, truncated rather than dumped), §8.12 (fail closed); RFC-0002 §11 Q3 (per-phase time budgets are an open question); RFC-0009 SC8/SC10 (no secret in output summaries / elevation exposes nothing); DN-18 (truncation mechanism with a placeholder default bound; the value is RFC-0020) |
| Embodied in | Iteration 8 implementation plan, Commit C4 |

**Decision.** The **mechanism** is built now: scoping to the one approved
Action; a deterministic timeout over the injected run primitive with a
**placeholder default bound** (DN-18 precedent — a bounded, configurable
default whose concrete value is RFC-0020's, per RFC-0002 §11 Q3); bounded
output capture that **truncates rather than dumps** (RFC-0001 §8.8); output
**redacted via `secrets`** before it enters the record or any display
(SC8/SC10); and fail-closed behavior on any guardrail error (RFC-0001 §8.12).
A timed-out run yields an outcome-unknown result (RFC-0002 §2.8 → Interrupted
at `core`), recorded as such. Concrete budgets and ceilings are RFC-0020's.

**Effect.** The guardrails are testable deterministically now; no RFC-0020
value is invented — the mechanism exists with an explicit placeholder bound.

## DN-60 — `elevation.py` implements the deterministic elevation lifecycle; the machine mechanism is injected at the boundary

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 8 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q6 |
| Grounding | RFC-0008 §8 Elevation (explicit, per-action, scoped, re-authenticated; an elevated Action is at least Consequential; bounds on the token; revoked at the end of that Action or on any invalidation; never persists, never covers unapproved work, never a standing root session); RFC-0001 §8.6 (explicit, scoped, re-authenticated; only for the approved action; Operator present); RFC-0021 (Draft) §3.3 (the machine's own elevation mechanism — not named here); DN-53 (elevation risk-property → at least Consequential; token records bounds; mechanism/revocation is `executor.elevation`'s) |
| Embodied in | Iteration 8 implementation plan, Commit C4 |

**Decision.** `elevation.py` implements the **deterministic elevation
lifecycle** RFC-0008 §8 fixes: a per-Action elevation request carrying its
bounds (which `policy` already enforced as at-least-Consequential, DN-53), and
a **revocation** that fires at the end of that Action or on any invalidation.
Elevation never persists, never covers unapproved work, and never forms a
standing root session. The **machine's own mechanism** (RFC-0021 §3.3, Draft —
sudo/polkit invocation and revocation plumbing) is **injected at the boundary**,
not built here (§1.2). The module owns the request/revoke contract and the SC10
no-exposure boundary (elevation never displays or records a value).

**Effect.** P12 (explicit/per-action/scoped/revoked) and SC10 are testable at
the executor surface now; the machine-specific mechanism stays deferred to
RFC-0021 acceptance, exactly as RFC-0008 §8 fixes semantics but not mechanism.

## DN-61 — The runner writes execution start/end records through `audit`; a failed pre-write blocks the run and is disclosed (AU8)

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 8 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q7 |
| Grounding | RFC-0002 I-13 ("The audit trail is written before the consequence… recorded at the boundary, not after the fact, and never silently edited"); RFC-0013 §23 (execution start/end are audited before their consequences; "the write points are runtime boundaries"), §21 (fail closed: a failed audit write blocks the consequence it precedes); RFC-0004 A10 (Approval recorded before spent); RFC-0008 P13; blueprint §5's note ("every record is written *at a boundary* by the component whose consequence it precedes — RFC-0002 invariant 13; RFC-0013 §7"); DN-50 (the durable Audit write is `audit`'s DoD) |
| Embodied in | Iteration 8 implementation plan, Commit C1/C3 |

**Decision.** The **runner writes** the execution-start record through `audit`
**before** the run and the execution-end record **after**, because the write
point is the boundary of the component whose consequence it precedes (RFC-0013
§23; blueprint §5's non-hub note). A **failed pre-write blocks the run and is
disclosed** (AU8; RFC-0013 §21; RFC-0004 §9.12): no consequence proceeds
unrecorded. This makes I-13/AU8 testable at this layer now, without `core`
(Iteration 10). The other §7 write points (goal adoption, proposal,
classification, verification, outcome) belong to their owning components
(RFC-0013 §23; design review §1.2).

**Effect.** I-13 and AU8 — the audit half of the §8.8 DoD — are enforced at the
runner's surface: the execution record exists before any machine interaction
is attempted, and a degraded store stops the run.

## DN-62 — `store.py` is an in-memory append-only store with tamper-evidence, the §11 lifecycle, AU8 fail-closed, and §22 reconciliation; durable backing is deferred to RFC-0020

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 8 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q8 |
| Grounding | RFC-0013 §1 (durable, append-only, tamper-evident record), §11 (lifecycle: Empty → Recording → Degraded → Recovering → …), §12 (legal transitions; anything not listed is illegal; Degraded → consequence proceeds is illegal), §21 (fail closed; fail loud; a gap is never patched by invention), §22 (reconciliation, never rewrite); RFC-0002 I-13; RFC-0004 A7; RFC-0001 §8.10 (append-only and honest); DN-19/DN-27/DN-34/DN-50 (in-memory mechanics now, durable mechanics deferred); RFC-0020 (storage mechanics, retention, deletion, export) |
| Embodied in | Iteration 8 implementation plan, Commit C1 |

**Decision.** `store.py` is an **in-memory append-only store** now: an ordered
record list that can only be appended to; prior records immutable (A7/AU4); a
**hash-chain** binds each record to its predecessor so any silent edit is
detectable (RFC-0001 §8.10 tamper-evidence); the **§11 lifecycle state machine**
(Empty → Recording → Degraded → Recovering) with the §12 legal transitions —
Degraded → consequence proceeds is illegal (RFC-0004 §9.12); **AU8 fail-closed**
(a failed or refused write moves the store to Degraded and is disclosed); and
**§22 reconciliation** (a genuinely lost write is recorded as failed-to-record,
never invented; deleted records never return — AU13). The durable backing
(filesystem/database), retention (§19), deletion (§20), and export (§18)
mechanics are RFC-0020's, recorded at design review §1.2.

**Effect.** Append-only, tamper-evidence, the lifecycle, AU8, and reconciliation
are testable now; no storage or retention mechanic is invented before RFC-0020.

## DN-63 — `records.py` implements this layer's boundaries' categories; the remaining §7 categories arrive with their owning write points

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 8 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q9 |
| Grounding | RFC-0013 §7 (the twelve record categories, each "written at its boundary before the consequence"), §16 (completeness: no actor exempt), §23 (the write points are runtime boundaries); RFC-0004 §4.12 (the Audit System owns the record format); DN-50 (the durable write of the issuance/override/auto-permit/rejection records is `audit`'s); blueprint §8.8 (this iteration's work: "record writers") |
| Embodied in | Iteration 8 implementation plan, Commit C1 |

**Decision.** `records.py` implements the canonical record types for **this
layer's boundaries**: the execution record (cat. 6: action start/end, commands
in sanitized form, machine state at the boundary), the secret-metadata record
(cat. 10, built on `secrets` *metadata types* only — SC4; no value-shaped field
exists by construction), and the approval / override / auto-permit / rejection
records (cat. 4/5) whose durable write DN-50 assigned to audit. The remaining §7
categories (proposal, classification, verification, fact-lifecycle,
context-boundary, skill-event, operator-visibility) **arrive with their owning
write points** — they are recorded, not dropped, and no category type is
orphaned before its boundary exists (RFC-0013 §23: each is written at *its*
boundary).

**Effect.** The record vocabulary for the boundaries that exist in this layer is
canonical and testable; the rest are deferred with their owners, not invented
here.

## DN-64 — `transcript.py` implements derivation from the record only; the presentation form is RFC-0015's

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 8 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q10 |
| Grounding | RFC-0013 §8 (Transcript Record Categories; "The Transcript is always renderable from the record; it never holds material the record does not"), §2 (derived, not primary; for the Operator; never evidence), §5 (RFC-0015 owns the presentation form); AU2 (Transcript is never evidence; Facts remain the only evidence model); RFC-0003 §2.8 (Transcript is the Operator-facing account derived from the record) |
| Embodied in | Iteration 8 implementation plan, Commit C2 |

**Decision.** `transcript.py` implements the **deterministic derivation**:
transcript = render(record), producing exactly the §8 categories (dialogue,
actions/outcomes, decisions/grounds, disclosures, recovery context) from the
record **only** — never holding material the record does not (AU2; RFC-0013 §8;
the §8.8 DoD). The **presentation form** (how the derived account is shown to a
beginner) is RFC-0015's (RFC-0013 §5), recorded at design review §1.2. No
verification or reasoning path consumes a transcript rendering (AU2).

**Effect.** The "transcript derives from the record only" half of the §8.8 DoD
is testable now; the form stays with RFC-0015.

### Q1–Q10 question status

| §10 Q | Subject | Status | Where resolved |
|---|---|---|---|
| Q1 | Run primitive: injected boundary vs real subprocess | **Ratified** | DN-55 (this file) |
| Q2 | Token handoff type / independent re-validation without `policy` | **Ratified** | DN-56 (this file) |
| Q3 | State-consistency/precondition verdict at the boundary | **Ratified** | DN-57 (this file) |
| Q4 | Execution command construction (I-5, no shell) | **Ratified** | DN-58 (this file) |
| Q5 | Guardrail mechanism vs RFC-0020 values | **Ratified** | DN-59 (this file) |
| Q6 | Elevation module: lifecycle now vs deferred | **Ratified** | DN-60 (this file) |
| Q7 | Record-before-consequence at the runner | **Ratified** | DN-61 (this file) |
| Q8 | Audit store durability | **Ratified** | DN-62 (this file) |
| Q9 | Record categories in scope | **Ratified** | DN-63 (this file) |
| Q10 | Transcript derivation scope | **Ratified** | DN-64 (this file) |

All ten §10 questions are resolved as decision notes; none requires an RFC
amendment, a `schema`/`systemmodel`/`trust`/`factlayer`/`verification`/`secrets`/
`policy` change, a new module (the six `executor`/`audit` modules are already
scaffolded per blueprint §2), or a new dependency edge beyond the declared
`executor → {schema, audit, secrets}` and `audit → {schema, secrets}` sets
(blueprint §4.1). **Iteration 8 implementation is unblocked** (design review
§16 readiness). The planned commits (design review §12) will be recorded in
`docs/implementation-consistency-report.md` (Iteration 8 section) as they land.

### DN-55 … DN-64 completion status

| Note | Decision | Status | Embodied in | Validated by |
|---|---|---|---|---|
| DN-55 | Injected run primitive; `executor` performs no I/O/subprocess | **Implemented** | C3 (`runner.py` `RunPrimitive`) | `test_executor_runner.py`; AST conformance |
| DN-56 | Token as structural handoff; local re-validation, no `policy` import | **Implemented** | C3 (`runner.py` `TokenHandoff`, `validate_handoff`) | `test_executor_runner.py`; AST conformance |
| DN-57 | Local re-validation + consumed machine-state/precondition verdict | **Implemented** | C3 (`BoundaryVerdict`) | `test_executor_runner.py` refusals |
| DN-58 | argv-structured descriptor; no shell string (I-5) | **Implemented** | C3 (`runner.py` descriptor) | `test_executor_runner.py` I-5 tests |
| DN-59 | Guardrail mechanism now (timeout placeholder bound; bounded/redacted capture) | **Implemented** | C4 (`guards.py`) | `test_executor_guards.py` |
| DN-60 | Deterministic elevation lifecycle; machine mechanism injected | **Implemented** | C4 (`elevation.py`) | `test_executor_elevation.py` |
| DN-61 | Runner writes execution records through `audit`; failed pre-write blocks run (AU8) | **Implemented** | C1/C3 (`store.py`, `runner.py`) | `test_audit_store.py`; `test_executor_runner.py` |
| DN-62 | In-memory append-only store, hash-chain, §11 lifecycle, §22 reconciliation | **Implemented** | C1 (`store.py`) | `test_audit_store.py`; `test_audit_conformance.py` |
| DN-63 | This layer's boundaries' categories | **Implemented** | C1 (`records.py`) | `test_audit_records.py`; `test_audit_conformance.py` |
| DN-64 | Transcript derivation from the record only; form is RFC-0015's | **Implemented** | C2 (`transcript.py`) | `test_audit_transcript.py` |

**Iteration 8 completion note.** All ratified Executor + Audit layer decisions
(DN-55…DN-64) are implemented and validated: the full suite is green (1965
tests), the Layer-4 conformance and invariant suites
(`test_audit_conformance.py` plus the AST-conformance sections of
`test_executor_runner.py`/`test_executor_guards.py`/`test_executor_elevation.py`)
enforce the ratified readings, and the next iteration is the `context` layer
(RFC-0012) that owns the runtime `core`-side wiring recorded as deferred in the
consistency report. No new decision note is required for this closeout.

# Iteration 9 decision notes (Context & Memory layer)

The notes below record the Iteration 9 ratification (Operator, 2026-08-07) of
the ten questions posed by `docs/iteration-9-design-review.md` §10 (Q1–Q10).
They fix the reading of the reported ambiguities so that a reported ambiguity
cannot reappear in a later iteration, and they **unblock Iteration 9
implementation** (design review §16–§17 readiness). All ten questions are
recorded as decision notes DN-65…DN-74: each fixes an iteration-scope or
layer-mechanics reading that the frozen corpus leaves open. RFC-0012 is
architecture-only ("no schemas, no APIs"; RFC-0005 §3; RFC-0012 §0), so each
question resolves an *implementation interpretation*, never an architectural
expansion; the corpus supplies the grounding. No question requires an RFC
amendment, a `schema`/`systemmodel`/`trust`/`factlayer`/`verification`/
`secrets`/`policy`/`executor`/`audit` change, a new module (the four `context`
modules are already scaffolded per blueprint §2), or a new dependency edge
beyond the declared `context → {schema, factlayer, trust, secrets, systemmodel}`
set with `secrets` restricted to classifier types (blueprint §4.1/§4.2). The
grounding RFCs cited below are Accepted where marked; RFC-0012, RFC-0013, and
RFC-0021 are Draft, whose rework risk is accepted per blueprint §9 #2 (the DN
posture of Iterations 1–8).

## DN-65 — Iteration 9 scope is the `context` layer; the blueprint §8.9 numbering is superseded by DN-45's re-order

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 9 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q1 |
| Grounding | DN-45 (re-order: `policy` = Iteration 7, `executor` + `audit` = Iteration 8, `context` = Iteration 9, `providers` + `skills` = Iteration 10, `core` = Iteration 11); blueprint §8.9 (the `context` iteration, original numbering "Iteration 8"); Iteration 8 closeout (`docs/iteration-8-design-review.md` §16: "The next iteration is the `context` layer (RFC-0012)") |
| Embodied in | Iteration 9 implementation plan (docs-ratification commit C0) |

**Decision.** Iteration 9 executes as the **Context & Memory Layer (`context`
only)** (RFC-0012; blueprint §8.9, re-ordered by DN-45 to follow `executor` +
`audit`). The blueprint §8.9 numbering is **superseded by DN-45's re-order**:
`context` is Iteration 9, not the §8.9 label's "Iteration 8". The blueprint text
itself is **left unchanged** — the renumbering is recorded here and in the
consistency report as a reported tension, and the blueprint stands until
RFC-0020 (the authoritative build order). The re-order is dependency-safe:
`context` (Layer 4) precedes `providers` (Layer 5, imports `context`), `core`
(Layer 6, imports `context`), and `cli` (Layer 7, imports `context`), preserving
the safety spine and blueprint Risk #9's mitigation (secrets, Layer 2, precedes
context and providers). No architecture is added; the §8.9 DoD
(CM1–CM16; PR14; SC2; CM13) is the conformance oracle.

**Effect.** The Iteration 9 plan in `docs/iteration-9-design-review.md` §12–§14
is ratified; the blueprint §8.9 label stays recorded as a reported tension until
RFC-0020.

## DN-66 — The assembly function consumes explicit boundary inputs; the runtime wiring is `core`'s

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 9 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q2 (and the A11 Goal-shape part) |
| Grounding | RFC-0012 §8 (what enters Context; "only through the Context Manager"), §12 (deterministic, ordered composition); RFC-0002 §2.4 (Context Building is "the *only* place LLM input is assembled" and is a runtime state); RFC-0003 §2.3 (the Goal is a Session concept, one active Goal; the Goal is the Core's per `schema/action.py`); RFC-0004 §4.11 (Context Manager trusts Fact Layer and Operator consent; does not trust raw Observations/Provider output/Skill material); Iteration 8 DN-55/DN-56 (injected boundary + structural-handoff precedent); DN-44 (latent edge precedent); blueprint §4.2 (forbidden `context → providers`/`skills` edges) |
| Embodied in | Iteration 9 implementation plan, Commit C1 |

**Decision.** `assemble.py` consumes **explicit boundary inputs**: a plain
schema-shaped Goal value (statement + scope; a canonical Goal schema is
RFC-0020's, DN-1), the Fact current set read from `factlayer` (filtered to
relevance + freshness at its trust class, RFC-0012 §8/§12), a bounded,
already-labeled history turn record, sanitized skill material, and the
routing-state marker. The package performs **no I/O and no provider call** and
holds no live session state; assembly is a pure, deterministic function, testable
now against supplied material (RFC-0007 S7). The producers of history, skill
material, the Goal, and routing state are `core`/`providers`/`skills`
(Iterations 10–11) and remain recorded at design review §1.2; the Context
Building *state wiring* (entry/exit conditions, the → Diagnosis/Planning exits)
is `core`'s. No architecture is added; the composition order of RFC-0012 §12 is
the normative rule.

**Effect.** The assembly input contract is fixed and testable at Layer 4 without
`core`; the `context → providers`/`skills` edges stay forbidden and the Layer-4
conformance suite enforces it.

## DN-67 — The sanitization enforcement point is built now (mechanism), with the per-source catalogue deferred to RFC-0020

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 9 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q3 |
| Grounding | RFC-0012 §5 authority 2 ("Filter and sanitize — apply purpose-limits, size bounds, and sanitization (RFC-0007 S1–S8) before material enters Context or a View"), §32 ("The rule is RFC-0009's; the mechanics are this RFC's"), §37 OQ3 (the sanitization catalogue at the enforcement point is RFC-0020's); RFC-0004 §4.11 (the Context Manager "is the enforcement point and may never decide to include a secret"); RFC-0009 SC2/SC16; RFC-0007 S1–S8; DN-18 (placeholder-default precedent); DN-43 (SC2–SC5 are satisfied as layer-boundary tests now; cross-component enforcement is the owning packages' DoD) |
| Embodied in | Iteration 9 implementation plan, Commit C2 |

**Decision.** `boundaries.py` implements the **enforcement point mechanism now**:
it applies `trust`'s RFC-0007 S1–S8 (neutralize, contain, bound, label) and the
`secrets` classifier (fail-closed on secret-shaped values, SC2) before any
material enters Context or a View, with a placeholder-default policy (DN-18).
Personal data is treated as secret until an explicit Operator demotion (SC16).
The **concrete per-source catalogue** (which treatment for which source, per
RFC-0012 §37 OQ3) is RFC-0020's; the mechanism is this layer's. No architecture
is added; the rule stays RFC-0009's, the mechanics are RFC-0012 §32's, and the
enforcement point is RFC-0004 §4.11's.

**Effect.** SC2/CM4/T10 are testable at their enforcement point now (DN-43's
assignment); the catalogue values stay with RFC-0020.

## DN-68 — `provider_view.py` derives the View now; the presentation form is RFC-0015's and final signatures are RFC-0020's

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 9 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q4 |
| Grounding | RFC-0010 §3 (the Provider View's elements; "This RFC does not define its shape — no schemas — but defines its boundary"), §11 (the Context Boundary; assembled, not forwarded; minimal by default), §15 OQ3 (assembly mechanics are RFC-0012's and RFC-0015's); RFC-0012 §13 (Context → Provider View boundary), §27 (the View is the only channel, PR14); RFC-0007 §12 (built, labeled, size-bounded, purpose-limited, disposable); RFC-0002 §2.4 (the View is built at the Context Building exit); DN-1 (signatures are RFC-0020's); Iteration 8 DN-64 (derivation-now precedent) |
| Embodied in | Iteration 9 implementation plan, Commit C4 |

**Decision.** `provider_view.py` implements the **deterministic View derivation
now**: `build_view` derives a schema-shaped, secret-free View from the assembled
Context carrying exactly the RFC-0010 §3 elements (Operator Goal, the selected
evidence/Allowed Context, Conversation State including the routing-state marker
per RFC-0012 §33, and the Capability Declaration echoed back) and nothing else
(no Audit, no secrets, no raw output, no provider identity), so PR14/SC3/CM10
are testable here. The **presentation form** (how the View is rendered to the
Operator or consumed by the provider) is RFC-0015's (RFC-0010 §15 OQ3) and the
**final signatures** are RFC-0020's (DN-1). No architecture is added; the View's
boundary is RFC-0010 §3/§11's, and the shape is reported, not invented.

**Effect.** PR14/SC3/CM10 and RFC-0002 invariant 4 are testable at this layer
now; the form stays with RFC-0015.

## DN-69 — `memory.py` is an in-memory consented store now; durable backing is RFC-0014/RFC-0020's

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 9 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q5 |
| Grounding | RFC-0012 §7 (Memory Categories: exactly three), §22 (Persistence Philosophy; "Durable only by explicit, reversible consent"; "Retention is by consent, not by default"), §37 OQ4/OQ5 (what survives a resume and multi-goal separation are RFC-0014's); RFC-0001 §9.5 (retention by consent); RFC-0004 §4.11 (Persist under consent); DN-19/DN-27/DN-34/DN-50/DN-62 (in-memory-now, durable-later precedent); RFC-0020 (storage mechanics) |
| Embodied in | Iteration 9 implementation plan, Commit C3 |

**Decision.** `memory.py` builds the **in-memory consented store now**: the
promotion gate (Context material moves to Memory only with an explicit consent
carrying a stated purpose, CM11), exactly the three §7 categories (Preference
Memory, Machine Memory, Durable Context; never secret values, raw output, the
Audit record, or private content without demotion, SC16), list/export/wipe
(CM14), complete and irreversible wipe with no restore path (CM12/CM13), and no
decision surface (CM2). The **durable backing** (storage mechanics, retention,
deletion, export, and what survives a resume) is RFC-0014/RFC-0020's, exactly as
DN-62 deferred the audit store's durable backing. No architecture is added; the
consent gate is RFC-0012 §22's, and the in-memory posture is the established
scaffold precedent.

**Effect.** CM11/CM13/CM14 are testable now; the durable half stays recorded
against RFC-0014/RFC-0020.

## DN-70 — The context package emits context-boundary events; `core` writes them as RFC-0013 category-9 records

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 9 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q6 |
| Grounding | RFC-0013 §7 cat. 9 (Context-boundary records — "material entered Context or Memory, never the material itself"), §23 ("The write points are runtime boundaries"); RFC-0004 §9.11 (the Context Manager "the Audit records what entered Context"); RFC-0002 I-13 (recorded before the consequence); blueprint §4.2 (forbidden `context → audit` edge; CM15); RFC-0012 §31 (Audit records that material entered Context, never the material) |
| Embodied in | Iteration 9 implementation plan, Commits C1/C3 (event emission) |

**Decision.** The `context` package emits **deterministic context-boundary
events** — category, size, identity, entered/destroyed, and never the material
itself (SC4-compatible, value-free) — as outputs of assembly, promotion, and
destruction. **`core` writes them** as RFC-0013 §7 cat. 9 records at the runtime
boundary, before the material's use (RFC-0013 §23; RFC-0002 I-13). The package
never imports `audit` (blueprint §4.2; CM15) and never holds records itself. No
architecture is added; the record format is RFC-0013's, the write point is the
runtime's, and the event generation is this layer's, mirroring how Iteration 8
recorded the cat-9 write point at its owning runtime boundary.

**Effect.** CM15 and RFC-0002 I-13 both hold; the cat-9 record is testable as an
event-before-use boundary test now and written by `core` at Iteration 11.

## DN-71 — Routing-state is a Context category now; routing decisions are `core`'s and persistence is RFC-0014's

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 9 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q7 |
| Grounding | RFC-0012 §6 cat. 6 (Routing state: "the minimal state to route the next input: the outstanding-question marker and the current decision pointer"), §33 (the answer to RFC-0002 Q12: a new question supersedes the marker; the superseded question is disclosed, never silently dropped); RFC-0002 §2.5/§2.6 (routing decisions in Diagnosis/Planning), §10 Q12; RFC-0012 §37 OQ4 (routing-state persistence across interrupts is RFC-0014's) |
| Embodied in | Iteration 9 implementation plan, Commit C1 |

**Decision.** `assemble.py` carries the **routing-state marker** as a Context
category and implements the RFC-0012 §33 **supersede-disclose semantics**
deterministically (a new Operator question supersedes the outstanding-question
marker; the superseded question is disclosed, never silently dropped), so the
RFC-0002 Q12 answer is testable at the category now. The **routing decisions**
(which state to enter) are `core`'s (RFC-0002 §2.5/§2.6, Iteration 11), and
**cross-interrupt persistence** of the marker is RFC-0014's (§37 OQ4). No
architecture is added; routing state is exactly RFC-0012 §6 category 6's.

**Effect.** The §33 Q12 answer is testable here; the runtime routing and the
persistence half stay recorded against `core`/RFC-0014.

## DN-72 — Assembly enforces freshness gates and a mark-stale function now; the event emission and re-inspection are `core`'s

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 9 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q8 |
| Grounding | RFC-0012 §16 (Context inherits Fact freshness; "Stale Context is rebuilt, never patched"), §17 (invalidation is deterministic and precedes use; state change, freshness lapse, interruption, contradiction), §35 CM7/CM8; RFC-0005 §12 (freshness states; stale truth is not truth); RFC-0002 §4.2 (STATE_CHANGED_DETECTED marks the set stale and forces re-inspection) |
| Embodied in | Iteration 9 implementation plan, Commit C1 |

**Decision.** Assembly enforces the **deterministic freshness gates now**:
Stale/Expired/Unknown-freshness Facts are excluded or mark the working set
Stale (CM7), and a **mark-stale function** consumes the state-change/freshness
event as an explicit input and records the invalidation before any use (CM8).
The **event emission** (STATE_CHANGED_DETECTED) and the **re-inspection
trigger** are `core`'s (RFC-0002 §4.2, Iteration 11), exactly as Iteration 8
recorded the I-8 re-assessment trigger against `core`. No architecture is added;
freshness belongs to RFC-0005 §12 and the invalidation rule to RFC-0012 §17.

**Effect.** CM7/CM8 are testable at the layer's surface now; the runtime event
and re-inspection stay with `core`.

## DN-73 — All six Context categories are implemented as explicit types now; producers arrive with their owning iterations

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 9 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q9 |
| Grounding | RFC-0012 §6 (Context has "exactly six categories of material for reasoning"), §8 (what enters), §34 rule 2 ("New Context categories are additive amendments"); RFC-0006 §14 (Evidence is a forward reference); Iteration 8 DN-63 (categories-in-scope precedent: implement the category types now, writers arrive with their write points) |
| Embodied in | Iteration 9 implementation plan, Commit C1 |

**Decision.** All six §6 categories — **Goal, Facts, History, Evidence, Skill
material, and Routing state** — are implemented as explicit types now, fixing
the §6 closure before the producers land. Categories whose live producers do not
exist yet (History from `core`/`providers`, Skill material from `skills`,
Routing state from `core`) are tested at the boundary with supplied material
(DN-66). Adding a category later is an amendment (RFC-0012 §34 rule 2; RFC-0003
Part II), so the closure is fixed in this iteration. No architecture is added;
the six categories are RFC-0012 §6's exactly.

**Effect.** The §6 category set is closed and testable; later iterations fill
producers without amending the category set.

## DN-74 — Evidence enters Context as labeled material built on `schema.VerificationOutcome`, never as verification power

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 9 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q10 |
| Grounding | RFC-0012 §6 cat. 4 (Evidence: "verification Outcomes and their evidence… enter as Facts or labeled evidence, never as verification power"), §26 (Outcomes and evidence are Context material; Verification never reads Context); RFC-0006 §14 (Evidence as Context material is a forward reference; Verification consumes Facts, never Context, RFC-0006 §3); RFC-0005 §3 (canonical Fact/Outcome vocabulary); schema.VerificationOutcome (Iteration 4) |
| Embodied in | Iteration 9 implementation plan, Commit C1 |

**Decision.** Evidence enters Context as **labeled material built on the
`schema.VerificationOutcome` type** (its canonical form), never as verification
power, never as a decision input, and never through Context as a Fact — Facts
remain the only source of truth (CM1). The RFC-0006 §14 forward reference's
*write boundary* (how verification produces that material) stays `verification`'s
(Iteration 4) and is recorded as such. No architecture is added; the category is
RFC-0012 §6 category 4's, and the schema type is Iteration 4's.

**Effect.** The Evidence category is closed and labeled now; RFC-0006's author
resolves the §14 forward reference against this reading.

### Q1–Q10 question status

| §10 Q | Subject | Status | Where resolved |
|---|---|---|---|
| Q1 | Iteration scope / renumbering vs blueprint §8.9 | **Ratified** | DN-65 (this file) |
| Q2 | Context assembly input contract | **Ratified** | DN-66 (this file) |
| Q3 | Sanitization enforcement point | **Ratified** | DN-67 (this file) |
| Q4 | Provider View representation | **Ratified** | DN-68 (this file) |
| Q5 | In-memory Memory abstraction | **Ratified** | DN-69 (this file) |
| Q6 | Context-boundary audit write | **Ratified** | DN-70 (this file) |
| Q7 | Routing state ownership | **Ratified** | DN-71 (this file) |
| Q8 | Freshness event model | **Ratified** | DN-72 (this file) |
| Q9 | Six context categories as explicit types | **Ratified** | DN-73 (this file) |
| Q10 | Evidence basis | **Ratified** | DN-74 (this file) |

All ten §10 questions are resolved as decision notes; none requires an RFC
amendment, a `schema`/`systemmodel`/`trust`/`factlayer`/`verification`/`secrets`/
`policy`/`executor`/`audit` change, a new module (the four `context` modules are
already scaffolded per blueprint §2), or a new dependency edge beyond the
declared `context → {schema, factlayer, trust, secrets, systemmodel}` set with
`secrets` restricted to classifier types (blueprint §4.1/§4.2). **Iteration 9
implementation is unblocked** (design review §16 readiness). The planned commits
(design review §12) will be recorded in `docs/implementation-consistency-report.md`
(Iteration 9 section) as they land.

### DN-65 … DN-74 completion status

| Note | Decision | Status | Embodied in | Validated by |
|---|---|---|---|---|
| DN-65 | `context` executes at Iteration 9 per DN-45's re-order; blueprint §8.9 label superseded and stands until RFC-0020 | **Ratified** | C0 (docs-ratification) | design review §10 Q1 |
| DN-66 | `assemble()` consumes explicit boundary inputs (Goal value, Fact set, labeled history, sanitized skill material, routing-state marker); no I/O; `core` wires the runtime | **Ratified** | C1 (planned, `assemble.py`) | pending C1 |
| DN-67 | `boundaries.py` builds the enforcement point mechanism now (S1–S8 + secrets classifier, fail-closed SC2/SC16); per-source catalogue is RFC-0020's | **Ratified** | C2 (planned, `boundaries.py`) | pending C2 |
| DN-68 | `provider_view.py` derives the View now (RFC-0010 §3 elements, secret-free); form is RFC-0015's, signatures RFC-0020's | **Ratified** | C4 (planned, `provider_view.py`) | pending C4 |
| DN-69 | `memory.py` is an in-memory consented store now (promotion gate, three §7 categories, list/export/wipe, no-restore); durable backing RFC-0014/RFC-0020's | **Ratified** | C3 (planned, `memory.py`) | pending C3 |
| DN-70 | `context` emits deterministic context-boundary events; `core` writes them as RFC-0013 §7 cat. 9 records before use (I-13) | **Ratified** | C1/C3 (planned, event emission) | pending C1/C3 |
| DN-71 | `assemble.py` carries the routing-state marker + §33 supersede-disclose semantics; routing decisions `core`'s, persistence RFC-0014's | **Ratified** | C1 (planned, `assemble.py`) | pending C1 |
| DN-72 | Assembly enforces freshness gates + mark-stale function now; event emission and re-inspection are `core`'s | **Ratified** | C1 (planned, `assemble.py`) | pending C1 |
| DN-73 | All six §6 categories are explicit types now; producers arrive with their owning iterations | **Ratified** | C1 (planned, `assemble.py`) | pending C1 |
| DN-74 | Evidence enters as labeled material on `schema.VerificationOutcome`, never verification power; §14 write boundary stays `verification`'s | **Ratified** | C1 (planned, `assemble.py`) | pending C1 |

**Iteration 9 ratification note.** All ten Context & Memory layer decisions
(DN-65…DN-74) are ratified before C0, the docs-ratification commit; none is yet
implemented (C1–C6 remain, per design review §12). The four `context` modules
are scaffolded stubs (blueprint §2) and the `context` dependency row is already
declared in `tests/test_dependency_rules.py`, so the tree test stays green
throughout. The next iteration after `context` is `providers` + `skills`
(blueprint §8.10, re-ordered by DN-45 to Iteration 10).

### DN-65 … DN-74 completion block (Iteration 9 closeout)

| Note | Status | Embodiment | Validation |
|---|---|---|---|
| DN-65 … DN-74 | **Implemented** | C1–C5 | corresponding suites |

**Iteration 9 completion note.** All ratified Context & Memory layer decisions
(DN-65…DN-74) are implemented and validated: the full suite is green (2285
tests), the Layer-4 conformance and invariant suites (`test_context_conformance.py`
and `test_context_invariants.py`) enforce the ratified readings, and the next
iteration is the `providers` + `skills` layer (blueprint §8.10, re-ordered by
DN-45 to Iteration 10) that owns the runtime `core`-side wiring recorded as
deferred in the consistency report. No new decision note is required for this
closeout.

---

## Iteration 10 ratification — Providers & Skills layer (RFC-0010; RFC-0011)

This section ratifies the ten blocking questions Q1–Q10 of
`docs/iteration-10-design-review.md` §10 as **DN-75…DN-84**, exactly as
Iterations 1–9 ratified theirs before C0. Each question resolves an
implementation interpretation that the frozen corpus leaves open; no question
requires an RFC amendment, a `schema`/`systemmodel`/`trust`/`factlayer`/
`verification`/`secrets`/`policy`/`executor`/`audit` change, a new module (the
five `providers`/`skills` modules are already scaffolded per blueprint §2), or
a new dependency edge beyond the declared `providers → {schema, trust, context}`
and `skills → {schema, collectors, trust, policy, factlayer}` sets (blueprint
§4.1/§4.2). RFC-0010 and RFC-0011 are Draft; the layer conforms to their
wording knowingly, accepting the rework risk a Draft change carries, exactly as
Iterations 1–9 conformed to the Draft sections they translated. The grounding
RFCs cited below are Accepted where marked; RFC-0012, RFC-0013, and RFC-0021
are Draft.

## DN-75 — Iteration 10 executes the `providers` + `skills` layer; the blueprint §8.10 numbering is superseded by DN-45's re-order

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 10 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q1 |
| Grounding | DN-45 (re-order: `policy` = Iteration 7, `executor` + `audit` = Iteration 8, `context` = Iteration 9, `providers` + `skills` = Iteration 10, `core` = Iteration 11); blueprint §8.10 (the `providers` + `skills` iteration, original numbering "Iteration 9"); Iteration 9 closeout (consistency report "Readiness for Iteration 10": "The next iteration is the `providers` + `skills` layer (blueprint §8.10, re-ordered by DN-45 to Iteration 10)") |
| Embodied in | Iteration 10 implementation plan (C0, docs-ratification) |

**Decision.** Iteration 10 executes as the **Providers & Skills layer
(`providers` + `skills`)** (RFC-0010; RFC-0011; blueprint §8.10, re-ordered by
DN-45 to follow `context`). The blueprint §8.10 numbering is **superseded by
DN-45's re-order**: the layer is Iteration 10, not the §8.10 label's "Iteration
9". The blueprint text itself is **left unchanged** — the renumbering is
recorded here and in the consistency report as a reported tension, and the
blueprint stands until RFC-0020 (the authoritative build order). The re-order
is dependency-safe: `providers` (Layer 5, imports `context`) and `skills`
(Layer 5) precede `core`/`cli` (Layers 6–7), preserving the safety spine and
blueprint Risk #9's mitigation (secrets, Layer 2, precedes context and
providers). No architecture is added; the §8.10 DoD (PR11, PR14, F6; SK4, SK5,
SC5) and the blueprint §7 oracle rows (PR1–PR16; SK1–SK16) are the conformance
oracle.

**Effect.** The Iteration 10 plan in `docs/iteration-10-design-review.md`
§12–§14 is ratified; the blueprint §8.10 label stays recorded as a reported
tension until RFC-0020.

## DN-76 — `contract.py` validates the finite RFC-0010 §4 structured outputs now; the per-vendor adapters are RFC-0020's

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 10 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q2 |
| Grounding | RFC-0010 §0 (architecture only: "no HTTP, no REST, no SDKs, no vendor APIs, no JSON schemas, no implementation"), §4 (the finite structured outputs; rule 2, a Proposal carries its expected effect; "The Core validates the result against the contract; anything that does not conform is malformed"), §8 (malformed output rejected, never interpreted, PR13), §13 PR11 (provider failure never crashes), §15 OQ6 (the adapter implementation is RFC-0020's); RFC-0008 §5 (the gate's input is the Proposal; an incomplete Proposal is rejected; the expected Post-condition); DN-1 (final signatures are RFC-0020's); blueprint §8.10 DoD (PR11, PR13, F6) |
| Embodied in | Iteration 10 implementation plan, Commit C1 |

**Decision.** `contract.py` implements the **structured-output validation
mechanics now**: the finite RFC-0010 §4 outputs (Proposal, Explanation,
Questions, Clarifications, Alternative Plans, Refusal, Failure, Need More
Evidence) as deterministic validators over the `schema` types, with the
**expected-effect rule** (a Proposal is incomplete without its expected
Post-condition → rejected; RFC-0010 §4 rule 2, RFC-0008 §5, PR13) — never
interpreted into validity (PR13), never a Fact (F6), never authority
(PR2/PR3/PR6), never executed (PR1), degrading never crashing (PR11). The
**per-vendor adapters are RFC-0020's** (RFC-0010 §15 OQ6) and `adapters/` stays
a scaffold (DN-1). No architecture is added; the finite output set is RFC-0010
§4's and the expected-effect rule RFC-0008 §5's.

**Effect.** PR13/PR11/F6 and the expected-effect rule are testable at
`contract.py` now; the vendor-facing translation stays with RFC-0020.

## DN-77 — `view.py` implements the lifecycle mechanics and the capability vocabulary now; selection and fallback are RFC-0016's

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 10 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q3 |
| Grounding | RFC-0010 §5 (the capability model; "no capability implies permission", §5.4, PR12), §6 (the deterministic negotiation adaptation), §7 (the provider lifecycle: registration, activation, removal), §9/§15 OQ1 (provider selection, profiles, and wiring are RFC-0016's, Post-MVP); RFC-0002 §5/§6 (the consultation use is the runtime's); DN-1 |
| Embodied in | Iteration 10 implementation plan, Commit C2 |

**Decision.** `view.py` implements the §7 **lifecycle mechanics now** —
registration (the capability declaration stored as facts), activation
(usable-check), and removal — plus the §5 capability vocabulary and the
deterministic §6 negotiation adaptation. Provider **selection, profiles,
fallback chains, and cost controls are RFC-0016's** (RFC-0010 §15 OQ1) and the
consultation use is `core`'s (RFC-0002 §5/§6). No architecture is added; the
capability model is RFC-0010 §5's and the lifecycle §7's.

**Effect.** §5/§7 mechanics are testable at `view.py` now; selection/fallback
is recorded against RFC-0016 and the consultation use against `core`.

## DN-78 — The provider package validates and returns contract-shaped §4 outputs; routing to the deterministic consumers is `core`'s

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 10 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q4 |
| Grounding | RFC-0010 §4 ("The Core validates the result against the contract" and routes each output to its deterministic consumer, rule 3), §8 (malformed rejected, never interpreted, PR13); RFC-0008 §5 (the gate's input is the Proposal); RFC-0002 §6 (component consultation rules: each output reaches its consumer through the runtime) |
| Embodied in | Iteration 10 implementation plan, Commit C1 |

**Decision.** The provider package **validates and returns contract-shaped §4
results**; routing each output to its deterministic consumer (classification,
Planning, Awaiting Input) is **`core`'s** (RFC-0002 §6); nothing is interpreted
into validity here (PR13). No architecture is added; the validation half is
RFC-0010 §4's and the routing half RFC-0002 §6's.

**Effect.** PR13 is testable at the package now; the routing wiring is recorded
against `core` (Iteration 11).

## DN-79 — The provider package classifies the §8 failure modes into the §4.3 events deterministically; the recovery reaction is `core`'s

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 10 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q5 |
| Grounding | RFC-0010 §8 (the seven failure modes; "never interpret it into validity"; PR11), §13 PR11/PR16; RFC-0002 §4.3 (the provider-event vocabulary: PROVIDER_RESPONSE/REFUSAL/UNAVAILABLE/TIMEOUT/FALLBACK_OK/FALLBACK_FAILED), §10 (the recovery order: retry with backoff → fallback chain → degraded mode); RFC-0002 Q3 (bounded retry) |
| Embodied in | Iteration 10 implementation plan, Commit C2 |

**Decision.** The provider package translates the §8 failure modes into the
RFC-0002 §4.3 event vocabulary **deterministically** (Timeout →
PROVIDER_TIMEOUT, unavailable → PROVIDER_UNAVAILABLE, malformed →
PROVIDER_REFUSAL, and so on; PR11/PR16). **Retry with backoff, the fallback
chain, and degraded mode are `core`'s** (RFC-0002 §10), and provider selection
is RFC-0016's. No architecture is added; the classification is RFC-0010 §8's
and the reaction RFC-0002 §10's.

**Effect.** PR11/PR16 are testable as the failure→event classification now; the
reaction is recorded against `core` (Iteration 11).

## DN-80 — `loader.py` is the Skill Registry's load-and-authenticate boundary; the packaging and signing scheme is RFC-0017/RFC-0020's

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 10 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q6 |
| Grounding | RFC-0011 §3 (the Skill Registry's authentication role), §22 (the load steps: read the declared surface, authenticate signature and provenance, validate the declaration, check Policy before activation, register), §19 (version and signature carried on the manifest), §30 OQ1 (the concrete packaging/signing scheme is RFC-0017/RFC-0020's); RFC-0002 §4.7 (an unauthenticated Skill is refused, never substituted; SKILL_UNAVAILABLE); RFC-0001 §11.2 (the Core enumerates what is registered); blueprint §2 (no `registry` module in the scaffolded `skills` package) |
| Embodied in | Iteration 10 implementation plan, Commit C3 |

**Decision.** `loader.py` plays the **Skill Registry's load-and-authenticate
boundary now** — read the declared surface, authenticate signature and
provenance (an unauthenticated Skill is never loaded, RFC-0002 §4.7; SK5),
validate the declaration (targets, privileges, risk, capabilities,
dependencies, Pre/Postconditions, verification approach), check Policy before
activation (RFC-0008), register with the Core — with no side effects and no LLM
judgment (RFC-0011 §22). The version and signature ride the manifest now; the
concrete packaging/signing scheme is RFC-0017/RFC-0020's (§19/§30 OQ1). No
architecture is added.

**Effect.** SK5/SK15 and RFC-0011 §22 are testable at the loader now; the
packaging/signing mechanics stay recorded against RFC-0017/RFC-0020.

## DN-81 — `activation.py` implements the per-session, reversible, Policy-gated, audited lifecycle; the consultation and session scope are `core`'s

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 10 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q7 |
| Grounding | RFC-0011 §23 (activation: per-session, reversible, Policy-gated, audited; grants no authority; unauthenticated never substituted), §24 (Skill Actions pass the exact same gate; no unit approval), §25/§13 (verification is never the Skill's, SK6; declared Pre/Postconditions, SK11/SK12); RFC-0002 §6/§2.2 (the consultation of a Skill in Diagnosis/Planning/Machine Inspection and the session scope are the runtime's); RFC-0008 §5 (gate participation; incomplete Proposals rejected) |
| Embodied in | Iteration 10 implementation plan, Commits C3/C4 |

**Decision.** `activation.py` implements the §23 lifecycle mechanics now
(per-session, reversible, Policy-gated, audited-event emitting, no
unauthenticated substitution, no authority grant); `runtime.py` implements §24
**gate participation** (SK4, no unit approval, no skill-based shortcut; declared
Preconditions and Postconditions ride the Action, SK11/SK12; verification never
the Skill's, SK6). The consultation/invocation (Diagnosis/Planning/Machine
Inspection) and the session scope are `core`'s (RFC-0002 §6/§2.2). No
architecture is added.

**Effect.** SK4/SK11/SK12 are testable at the gate-surface mechanics now; the
consultation wiring is recorded against `core` (Iteration 11).

## DN-82 — RFC-0011 §20's provider↔skill interaction is `core`'s obligation with no direct package edge

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 10 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q8 (and RFC-0010 §15 OQ5) |
| Grounding | RFC-0011 §20 (a Skill consumes the Provider Contract, never a vendor; a deterministic Skill needs no Provider; Skill code never enters the LLM path except sanitized; no bidirectional trust), §13/SK13 (Skill content never enters the View/LLM path unsanitized); RFC-0010 §15 OQ5 (skill-provider interaction is RFC-0011's); RFC-0001 §11.2 (the two extension axes); blueprint §4.1 (no `providers ↔ skills` edge; `providers` allowed = {schema, trust, context}, `skills` allowed = {schema, collectors, trust, policy, factlayer}) |
| Embodied in | Iteration 10 implementation plan, Commit C4 (recorded obligation) |

**Decision.** RFC-0011 §20's provider↔skill interaction is realized as **`core`'s
obligation** through `schema`/`context`, never by an import: a Skill consumes
the Provider Contract, never a vendor; deterministic Skills run without a
Provider in degraded mode; Skill code never enters the LLM path except
sanitized (SK13). The §20 rules become boundary obligations asserted at the
layer — SK13 sanitization asserted at the boundary, no `skills → providers`
edge (blueprint §4.1). No architecture is added; the interaction is RFC-0011
§20's and the wiring `core`'s.

**Effect.** The forbidden-edge rule and SK13 are conformance-asserted; the
interaction wiring is recorded against `core` (Iteration 11).

## DN-83 — Both packages are I/O-free; all external surfaces are injected and belong to RFC-0020/RFC-0017

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 10 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q9 |
| Grounding | RFC-0010 §0 (architecture only — no HTTP, no REST, no SDKs, no vendor APIs), §15 OQ6 (the adapter is RFC-0020's); RFC-0011 §17/§30 OQ2 (sandboxing mechanics are RFC-0020's); DN-1 (final signatures are RFC-0020's); DN-55 (the injected-primitive / run-primitive precedent of Iteration 8); blueprint §8.10 DoD (PR11, PR14, SK5, SC5 testable without a live vendor or a real skill fetch) |
| Embodied in | Iteration 10 implementation plan, Commits C1–C4 |

**Decision.** Neither package performs **network, subprocess, filesystem,
vendor, or skill-fetch I/O** — everything external is injected at the boundary
(the DN-55 run-primitive precedent); vendor calls, skill fetch, and sandbox
execution are RFC-0020's/RFC-0017's. No architecture is added; the layer builds
the contract and the mechanics those external surfaces must serve.

**Effect.** The layer is deterministic and I/O-free (RFC-0007 S7); the absence
of I/O is conformance-enforced.

## DN-84 — The provider package is the sole vendor-facing surface (PR10/PR15), enforced by conformance; SC3/SC5 are asserted by boundary injection without a `secrets` import

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 10 ratification) |
| Date | 2026-08-07 |
| Resolves | design review §10 Q10 |
| Grounding | RFC-0010 §12 (replacement changes only the adapter, PR15), §13 PR10 (the Core knows no vendor); RFC-0002 §1 (keep the provider world separate from the machine world); RFC-0009 SC3 (no secret in the Provider View), SC5 (no secret reaches a Skill); blueprint §4.2 (neither package may import `secrets`); DN-43 (the boundary-test precedent of RFC-0009 §0) |
| Embodied in | Iteration 10 implementation plan, Commit C5 (conformance) |

**Decision.** The provider package is the **sole vendor-facing surface**
(PR10/PR15), enforced by a vendor-scan test (no vendor name or branch anywhere
else); SC3/SC5 are asserted by **injecting secret-shaped values** at the
View-consumption and Skill-loading boundaries and verifying none cross, with no
`secrets` import (blueprint §4.2; DN-43). The runtime provider-world /
machine-world separation is `core`'s (Iteration 11). No architecture is added;
the no-secrets property is RFC-0009's, asserted by injection.

**Effect.** PR10/PR15 and SC3/SC5 are testable at the layer now; the runtime
separation is recorded against `core`.

### Q1–Q10 question status

| §10 Q | Subject | Status | Where resolved |
|---|---|---|---|
| Q1 | Iteration scope / renumbering vs blueprint §8.10 | **Ratified** | DN-75 (this file) |
| Q2 | Provider contract surface | **Ratified** | DN-76 (this file) |
| Q3 | Provider request lifecycle | **Ratified** | DN-77 (this file) |
| Q4 | Provider response ownership | **Ratified** | DN-78 (this file) |
| Q5 | Provider error handling | **Ratified** | DN-79 (this file) |
| Q6 | Skill registry ownership | **Ratified** | DN-80 (this file) |
| Q7 | Skill invocation boundary | **Ratified** | DN-81 (this file) |
| Q8 | Provider↔skill interaction | **Ratified** | DN-82 (this file) |
| Q9 | External API boundaries | **Ratified** | DN-83 (this file) |
| Q10 | Runtime ownership / no-vendor-knowledge | **Ratified** | DN-84 (this file) |

All ten §10 questions are resolved as decision notes; none requires an RFC
amendment, a `schema`/`systemmodel`/`trust`/`factlayer`/`verification`/`secrets`/
`policy`/`executor`/`audit` change, a new module (the five `providers`/`skills`
modules are already scaffolded per blueprint §2), or a new dependency edge
beyond the declared `providers → {schema, trust, context}` and
`skills → {schema, collectors, trust, policy, factlayer}` sets (blueprint
§4.1/§4.2). **Iteration 10 implementation is unblocked** (design review §16
readiness). The planned commits (design review §12) will be recorded in
`docs/implementation-consistency-report.md` (Iteration 10 section) as they land.

### DN-75 … DN-84 completion status

| Note | Decision | Status | Embodied in | Validated by |
|---|---|---|---|---|
| DN-75 | `providers` + `skills` execute at Iteration 10 per DN-45's re-order; blueprint §8.10 label superseded and stands until RFC-0020 | **Ratified** | C0 (docs-ratification) | design review §10 Q1 |
| DN-76 | `contract.py` validates the finite RFC-0010 §4 outputs over `schema` types + the expected-effect rule (incomplete → reject, PR13); adapters RFC-0020's, `adapters/` stays a scaffold | **Ratified** | C1 (planned, `contract.py`) | pending C1 |
| DN-77 | `view.py` implements §7 lifecycle mechanics + §5 capability vocabulary + deterministic §6 negotiation now; selection/fallback RFC-0016's, consultation `core`'s | **Ratified** | C2 (planned, `view.py`) | pending C2 |
| DN-78 | The provider package validates and returns contract-shaped §4 outputs; routing to deterministic consumers is `core`'s; nothing interpreted into validity (PR13) | **Ratified** | C1 (planned, `contract.py`) | pending C1 |
| DN-79 | The provider package classifies §8 failures into the §4.3 events deterministically (PR11/PR16); retry/fallback/degraded are `core`'s | **Ratified** | C2 (planned, `view.py`) | pending C2 |
| DN-80 | `loader.py` is the Skill Registry's load-and-authenticate boundary (SK5/SK15, §22); version + signature ride the manifest, scheme RFC-0017/0020's | **Ratified** | C3 (planned, `loader.py`) | pending C3 |
| DN-81 | `activation.py` §23 lifecycle + `runtime.py` §24 gate participation (SK4/SK11/SK12); consultation and session scope `core`'s | **Ratified** | C3/C4 (planned, `activation.py`/`runtime.py`) | pending C3/C4 |
| DN-82 | RFC-0011 §20 provider↔skill interaction is `core`'s obligation, no direct edge (blueprint §4.1); SK13 asserted at the boundary | **Ratified** | C4 (recorded obligation) | pending C4 |
| DN-83 | Both packages are I/O-free — no network/subprocess/filesystem/vendor/fetch I/O; everything injected (DN-55); vendor/sandbox mechanics RFC-0020/0017's | **Ratified** | C1–C4 (I/O-free mechanics) | pending C1–C4 |
| DN-84 | The provider package is the sole vendor-facing surface (PR10/PR15) enforced by conformance; SC3/SC5 asserted by boundary injection, no `secrets` import | **Ratified** | C5 (conformance) | pending C5 |

**Iteration 10 ratification note.** All ten Providers & Skills layer decisions
(DN-75…DN-84) are ratified **before Commit C1**, the first implementation
commit, exactly as Iterations 1–9 ratified their ten decisions before C0; none
is yet implemented (C1–C6 remain, per design review §12). The five
`providers`/`skills` modules are scaffolded stubs (blueprint §2) and the
`providers` and `skills` dependency rows are already declared in
`tests/test_dependency_rules.py`, so the tree test stays green throughout.
Because Iteration 10's C0 (the design-review record) was committed first, the
ratification record in this file travels with Commit C1; the design review §16
readiness flips to READY and Commit C1 (`contract.py`, structured-output
validation) satisfies the design review §14 C1 DoD.

### DN-75 … DN-84 completion block (Iteration 10 closeout)

| Note | Status | Embodiment | Validation |
|---|---|---|---|
| DN-75 … DN-84 | **Implemented** | C1–C5 | corresponding suites |

**Iteration 10 completion note.** All ratified Providers & Skills layer
decisions (DN-75…DN-84) are implemented and validated: the full suite is green
(2530 tests, 2285 baseline + 245 new), the Layer-5 per-module conformance and
boundary suites (`test_providers_contract.py`, `test_providers_view.py`,
`test_skills_loader.py`, `test_skills_activation.py`, `test_skills_runtime.py`
plus the cross-cutting `tests/test_dependency_rules.py` and
`tests/test_packages.py`) enforce the ratified readings, and the next iteration
is the `core` layer (blueprint §8.11, re-ordered by DN-45 to Iteration 11) that
owns the runtime wiring recorded as deferred in the consistency report
(consultation, gate routing, audit writes, failure reaction, provider-world/
machine-world separation). No new decision note is required for this closeout.

---

## Iteration 11 ratification — Orchestration Core layer (RFC-0002; RFC-0004)

This section ratifies the ten blocking questions Q1–Q10 of
`docs/iteration-11-design-review.md` §10 as **DN-85…DN-94**, exactly as
Iterations 1–10 ratified theirs before C0. Each question resolves an
implementation interpretation that the frozen corpus leaves open; no question
requires an RFC amendment, a `schema`/`systemmodel`/`trust`/`factlayer`/
`verification`/`secrets`/`policy`/`executor`/`audit` change, a new module (the
seven `core` modules are already scaffolded per blueprint §2), or a new
dependency edge beyond the declared `core → {all packages}` set with `cli` the
only importer (blueprint §4.1/§4.2). RFC-0005 through RFC-0013 and RFC-0021
are Draft; the layer conforms to their wording knowingly, accepting the rework
risk a Draft change carries, exactly as Iterations 1–10 conformed to the Draft
sections they translated. The grounding RFCs cited below are Accepted where
marked; RFC-0008, RFC-0013, and RFC-0021 are Draft.

## DN-85 — Iteration 11 executes the `core` layer; the blueprint §8.11 numbering is superseded by DN-45's re-order

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 11 ratification) |
| Date | 2026-08-10 |
| Resolves | design review §10 Q1 |
| Grounding | DN-45 (re-order: `policy` = Iteration 7, `executor` + `audit` = Iteration 8, `context` = Iteration 9, `providers` + `skills` = Iteration 10, `core` = Iteration 11); blueprint §8.11 (the `core` iteration, original numbering "Iteration 10"); Iteration 10 closeout (consistency report "Readiness for Iteration 11": "The next iteration is `core` (Layer 6; blueprint §8.11, re-ordered by DN-45), followed by `cli`") |
| Embodied in | Iteration 11 implementation plan (docs-ratification commit C0) |

**Decision.** Iteration 11 executes as the **Orchestration Core layer (`core`
only)** (RFC-0002; RFC-0004; blueprint §8.11, re-ordered by DN-45 to follow
`providers` + `skills`). The blueprint §8.11 numbering is **superseded by
DN-45's re-order**: `core` is Iteration 11, not the §8.11 label's "Iteration
10". The blueprint text itself is **left unchanged** — the renumbering is
recorded here and in the consistency report as a reported tension, and the
blueprint stands until RFC-0020 (the authoritative build order). The re-order
is dependency-safe: `core` (Layer 6) imports all lower layers (blueprint §4.1)
and is imported only by `cli` (Layer 7), preserving the safety spine. No
architecture is added; the §8.11 DoD (state-machine conformance, invariants
1–15, recovery ordering determinism→disclosure→decision→action) and the
blueprint §7 oracle rows (RFC-0002 §1–§10) are the conformance oracle.

**Effect.** The Iteration 11 plan in `docs/iteration-11-design-review.md`
§12–§14 is ratified; the blueprint §8.11 label stays recorded as a reported
tension until RFC-0020.

## DN-86 — The reachable transition set is exactly the §2.1–§2.15 "Allowed transitions" lists plus the §3 shortcut edges and the §2.9 next-step edge; the diagram defers to §§2/4

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 11 ratification) |
| Date | 2026-08-10 |
| Resolves | design review §10 Q2 |
| Grounding | RFC-0002 §0 ("the drawing is ambiguous, the written definitions in §2 and the event rules in §4 win"), §2.1–§2.15 (each state's Allowed transitions), §3 (the state-machine diagram, normative only where it matches §§2/4), §2.9 (Verification "Passed, but approved steps remain → Executing (the next step)"), §4 (the events that move between states) |
| Embodied in | Iteration 11 implementation plan, Commit C1 (`state_machine.py`) |

**Decision.** The conformance transition set is exactly: (a) the §2.1–§2.15
**"Allowed transitions"** lists; (b) the **§3 shortcut edges** (OP_CANCEL →
Cancelled from any active state; OP_INTERRUPT → Interrupted / second press →
END; ACTION_TIMEOUT / ACTION_INTERRUPTED → Interrupted; provider loss with no
fallback → degraded mode → Awaiting Input; approved REBOOT → write resume
marker → END; STATE_CHANGED_DETECTED → invalidate facts → Machine Inspection);
(c) the §2.9 **Verification → Executing (next approved step)** edge. Nothing
else is reachable; any other transition is refused. The diagram defers to §§2/4
where it is ambiguous or drawn-only. No architecture is added.

**Effect.** The reachable set is a testable, closed oracle for
`test_core_state_machine` (the impossible-transition table of the walkthrough
§6.1); any invented move fails conformance.

## DN-87 — All §4.1–§4.7 events exist as typed events; the informational ones (OP_VIEW, ACTION_STARTED, ACTION_CLASSIFIED) are audited notes with no state change

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 11 ratification) |
| Date | 2026-08-10 |
| Resolves | design review §10 Q3 |
| Grounding | RFC-0002 §4.1 (OP_VIEW "informational only … no state change"), §4.5 (ACTION_STARTED "internal; audited"), §4.4 (ACTION_CLASSIFIED — the classification event), §4.1–§4.7 (the full event vocabulary), §6 (the Audit is "written at every consequential boundary"); RFC-0013 §23 (the write points are runtime boundaries, before the consequence); RFC-0002 I-13 (audit written before the consequence) |
| Embodied in | Iteration 11 implementation plan, Commit C1 (`events.py`) |

**Decision.** The full §4.1–§4.7 event catalog exists as typed events with a
per-event dispatch (event → transition relation declared once). The
transition-less, information-only events — **OP_VIEW, ACTION_STARTED,
ACTION_CLASSIFIED** — emit audited notes and change no state; every
consequential event is audited before its effect (I-13). No architecture is
added; the catalog is RFC-0002 §4's.

**Effect.** Q3's uniform-type-set reading is testable at `events.py` now; the
informational events' no-state-change property is conformance-asserted.

## DN-88 — `core` is the single runtime writer at every boundary, invoking `audit` before the consequence, metadata-only, fail-closed (AU8)

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 11 ratification) |
| Date | 2026-08-10 |
| Resolves | design review §10 Q4 |
| Grounding | RFC-0013 §23 (the write points are runtime boundaries — goal adoption, proposal, classification, approval, override, execution start/end, verification, outcome — all audited before their consequences), §7 cat. 9 (context-boundary records: "material entered Context or Memory, never the material itself"), §21 (AU8: a failed write blocks and is disclosed); RFC-0002 §6 (the Audit is written before the consequence is allowed to proceed), §9 I-13; DN-70 (the `context` package emits deterministic boundary events; `core` writes them as RFC-0013 §7 cat. 9 records before use (I-13)) |
| Embodied in | Iteration 11 implementation plan, Commits C3/C5 (`loop.py` + `consultation.py`; the C5 boundary suites) |

**Decision.** `core` — the session owner — is the **single runtime writer at
every boundary**: the lower packages emit deterministic boundary events and
never write; `core` invokes `audit` before the consequence, metadata-only
(SC4), fail-closed (AU8; a failed write blocks the consequence and is
disclosed). This satisfies the recorded Iteration-9 obligation that the cat-9
context-boundary write is `core`'s (DN-70). No architecture is added; the write
points are RFC-0013 §23's and the writer placement RFC-0002 §6's.

**Effect.** I-13 and the cat-9 write are testable at `core` now; the lower
packages' never-write property is preserved.

## DN-89 — At the Awaiting Approval → Executing edge the token is re-validated against its declared preconditions and the injected current machine state plus current policy (P9; I-11)

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 11 ratification) |
| Date | 2026-08-10 |
| Resolves | design review §10 Q5 |
| Grounding | RFC-0002 §6 (the Approval & Policy Engine is consulted at the Awaiting Approval → Executing edge — "the token is re-validated against current policy, elevation, and machine state (the approval-to-execution gap is the classic time-of-check/time-of-use hazard)"), §2.8 (Executing runs the approved action under a re-validated token); RFC-0008 §8 (the Approval Token is the only thing that carries permission; scoped, consumable, never reused), §10 (independent enforcement at the boundary); RFC-0002 I-11 (tokens scoped and consumable) |
| Embodied in | Iteration 11 implementation plan, Commit C3 (`loop.py` + `consultation.py`) |

**Decision.** At the Awaiting Approval → Executing edge, `core` re-validates
the token against its **declared preconditions** and the **injected current
machine snapshot plus current policy** (P9; I-11); the token is scoped,
consumable, and never reused (RFC-0008 §8). `core` re-validates, it never
re-decides approval — classification and gate remain `policy`'s (I-7). No
architecture is added; the TOCTOU rule is RFC-0002 §6's and RFC-0008 §10's.

**Effect.** The boundary re-validation is testable at `core` now; the
approval-to-execution gap closes deterministically.

## DN-90 — Provider retry/backoff/fallback is a pure bounded reducer over injected events; back-off is data, never a sleep; the fallback-chain selection is RFC-0016's

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 11 ratification) |
| Date | 2026-08-10 |
| Resolves | design review §10 Q6 |
| Grounding | RFC-0002 §4.3 (PROVIDER_REFUSAL "Bounded retry with the provider, then fallback"; PROVIDER_UNAVAILABLE "Retry with backoff (bounded), then the fallback provider chain"; PROVIDER_TIMEOUT "Treated as PROVIDER_UNAVAILABLE after backoff"), §10 (Provider failure: "Retry with backoff (bounded) → fallback provider chain → degraded mode"); DN-55 (the injected-primitive / no-I/O precedent of Iteration 8); RFC-0010 §15 OQ1 (provider selection and profiles are RFC-0016's, Post-MVP); DN-77 (selection/fallback recorded as RFC-0016's) |
| Embodied in | Iteration 11 implementation plan, Commit C4 (`recovery.py`) |

**Decision.** Retry-with-backoff and the fallback chain are a **pure, bounded
reducer** over injected failure/time events: back-off is data, never a sleep,
and `core` imports no clock. The **selection** of the fallback chain is
**RFC-0016's** (RFC-0010 §15 OQ1; DN-77); `core` runs the reaction only. No
architecture is added; the recovery order is RFC-0002 §4.3/§10's.

**Effect.** The reducer is deterministic and testable at `recovery.py` now; the
I/O-free posture of `core` is preserved (DN-55).

## DN-91 — Degraded mode is facts-only with deterministic (non-LLM) Skills and no recommendations; the product-vs-fallback scope is RFC-0019's

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 11 ratification) |
| Date | 2026-08-10 |
| Resolves | design review §10 Q7 |
| Grounding | RFC-0002 §4.3 (PROVIDER_FALLBACK_FAILED "→ degraded mode → Awaiting Input (facts-only presentation; no recommendations)"), §10 (Provider failure: "the runtime never fabricates a reply"), §11 OQ 11 (degraded-mode scope: "run baseline inspections, present raw facts, run skills that are fully deterministic?"), §9 I-9 (the runtime never fabricates); RFC-0011 §20.2 ("A deterministic Skill does not need a Provider — it runs in degraded mode"); RFC-0019 (MVP: the product-vs-fallback scope is RFC-0019's) |
| Embodied in | Iteration 11 implementation plan, Commit C3 (`loop.py` + `consultation.py`) |

**Decision.** Degraded mode (no usable Provider) is **facts-only**: baseline
inspection, raw Facts presentation, and deterministic (non-LLM) Skills run —
RFC-0011 §20.2; there are **no recommendations** and the runtime never
fabricates (I-9; PROVIDER_FALLBACK_FAILED → Awaiting Input). Whether degraded
mode is a product feature or a graceful-failure path — and how much it may do —
is **RFC-0019's** (RFC-0002 §11 OQ 11). No architecture is added.

**Effect.** The facts-only, no-recommendations reaction is testable at `core`
now; the product scope stays with RFC-0019.

## DN-92 — Timeouts are injected-deadline primitives; TIMEOUT is a core event with the §4.7 reaction; numeric budgets are RFC-0020's

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 11 ratification) |
| Date | 2026-08-10 |
| Resolves | design review §10 Q8 |
| Grounding | RFC-0002 §4.7 (TIMEOUT "a generic phase watchdog fired (stalled phase). If cognitive → Awaiting Input (disclose). If machine-touching → Interrupted"), §11 OQ 2/3 (the per-phase time budget and the grace window are open questions); DN-55 (the injected-primitive / no-clock precedent); RFC-0020 (numeric budgets are RFC-0020's) |
| Embodied in | Iteration 11 implementation plan, Commits C1/C3/C4 (`events.py`; `loop.py`; `recovery.py`) |

**Decision.** A deadline is an **injected primitive**; a phase expiry raises
**TIMEOUT**, a core event with the §4.7 reaction — cognitive → Awaiting Input
(disclose); machine-touching → Interrupted. `core` imports no clock and holds
no numeric budget; the concrete per-phase budgets and grace windows are
**RFC-0020's** (RFC-0002 §11 OQ 2/3). No architecture is added.

**Effect.** Timeouts are deterministic and testable now; the budget values stay
with RFC-0020.

## DN-93 — Every cognitive consultation requires a fresh Provider View over the current facts; otherwise Context Building is re-entered first

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 11 ratification) |
| Date | 2026-08-10 |
| Resolves | design review §10 Q9 |
| Grounding | RFC-0002 §6 (the LLM is "Consulted in Diagnosis, Planning, and Replanning — and only after a fresh Context Building has produced a provider view"; the LLM is never consulted with raw, unbounded machine output or with secrets), §4.3 (PROVIDER_FALLBACK_OK "→ continue the cognitive phase with a fresh Context Building"), §9 I-4 (the LLM is only ever consulted through a Provider View); RFC-0010 §3/PR14 (the Provider View is the only channel); RFC-0012 §13 (the View is re-assembled, never restored) |
| Embodied in | Iteration 11 implementation plan, Commit C3 (`consultation.py`) |

**Decision.** A cognitive consultation (Diagnosis, Planning, Replanning) is
allowed only when the **current Provider View covers the current facts**;
otherwise **Context Building is re-entered first** (RFC-0002 §6). The LLM is
never consulted with raw output or secrets, and only through the View (I-4;
PR14). No architecture is added; the fresh-View rule is RFC-0002 §6's.

**Effect.** I-4 and the fresh-View rule are testable at `consultation.py` now.

## DN-94 — The loop's integration tests inject deterministic fake provider/skill/executor responders; production `core` files perform no I/O

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 11 ratification) |
| Date | 2026-08-10 |
| Resolves | design review §10 Q10 |
| Grounding | blueprint §7 (the `core` test-oracle row: state-machine conformance, invariants 1–15, interruption → re-assessment, no terminal outcome while work is in flight, no approval survives a boundary, recovery ordering), §8.11 DoD (a full-loop integration test mirrors `docs/core-execution-walkthrough.md` §2/§3; all 31 failure scenarios mirror `docs/failure-injection-walkthrough.md` §3); DN-55 (the injected-primitive / no-I/O precedent of Iteration 8); RFC-0002 §5 (the loop is the conductor with deterministic subsystem participation); RFC-0007 S7 (determinism is asserted) |
| Embodied in | Iteration 11 implementation plan, Commit C5 (conformance + integration) |

**Decision.** The full-loop integration test and the 31-scenario mirror inject
**deterministic fake provider/skill/executor responders** (the DN-55
precedent); production `core` files perform **no I/O** — no clock, no network,
no filesystem, no subprocess. The walkthroughs are the conformance oracle for
the loop. No architecture is added; the loop is RFC-0002 §5's and the
testability is blueprint §7's.

**Effect.** The §8.11 DoD's integration half is testable deterministically now;
the I/O-free posture of `core` is conformance-enforced.

### Q1–Q10 question status

| §10 Q | Subject | Status | Where resolved |
|---|---|---|---|
| Q1 | Iteration scope / renumbering vs blueprint §8.11 | **Ratified** | DN-85 (this file) |
| Q2 | The reachable transition set | **Ratified** | DN-86 (this file) |
| Q3 | The event-set fidelity | **Ratified** | DN-87 (this file) |
| Q4 | The audit writer at the runtime boundary | **Ratified** | DN-88 (this file) |
| Q5 | Token re-validation input | **Ratified** | DN-89 (this file) |
| Q6 | No-I/O retry/fallback | **Ratified** | DN-90 (this file) |
| Q7 | Degraded-mode scope | **Ratified** | DN-91 (this file) |
| Q8 | Timeout/budget events | **Ratified** | DN-92 (this file) |
| Q9 | Fresh Context Building rule | **Ratified** | DN-93 (this file) |
| Q10 | Loop testability at zero I/O | **Ratified** | DN-94 (this file) |

All ten §10 questions are resolved as decision notes; none requires an RFC
amendment, a `schema`/`systemmodel`/`trust`/`factlayer`/`verification`/`secrets`/
`policy`/`executor`/`audit` change, a new module (the seven `core` modules are
already scaffolded per blueprint §2), or a new dependency edge beyond the
declared `core → {all packages}` set with `cli` the only importer (blueprint
§4.1/§4.2). **Iteration 11 implementation is unblocked** (design review §16
readiness). The planned commits (design review §12) will be recorded in
`docs/implementation-consistency-report.md` (Iteration 11 section) as they land.

### DN-85 … DN-94 completion status

| Note | Decision | Status | Embodied in | Validated by |
|---|---|---|---|---|
| DN-85 | `core` executes at Iteration 11 per DN-45's re-order; blueprint §8.11 label superseded and stands until RFC-0020 | **Ratified** | C0 (docs-ratification) | design review §10 Q1 |
| DN-86 | The reachable transition set is exactly the §2.1–§2.15 "Allowed transitions" + the §3 shortcut edges + the §2.9 next-step edge; the diagram defers to §§2/4 | **Ratified** | C1 (planned, `state_machine.py`) | pending C1 |
| DN-87 | All §4.1–§4.7 events exist as typed events; the informational ones (OP_VIEW, ACTION_STARTED, ACTION_CLASSIFIED) are audited notes with no state change | **Ratified** | C1 (planned, `events.py`) | pending C1 |
| DN-88 | `core` is the single runtime writer at every boundary, invoking `audit` before the consequence, metadata-only, fail-closed (AU8) | **Ratified** | C3/C5 (planned, `loop.py` + `consultation.py`; C5 suites) | pending C3/C5 |
| DN-89 | At the Awaiting Approval → Executing edge the token is re-validated against its declared preconditions and the injected current machine state and policy (P9; I-11) | **Ratified** | C3 (planned, `loop.py` + `consultation.py`) | pending C3 |
| DN-90 | Provider retry/backoff/fallback is a pure bounded reducer over injected events; back-off is data, never a sleep; the chain's selection is RFC-0016's | **Ratified** | C4 (planned, `recovery.py`) | pending C4 |
| DN-91 | Degraded mode is facts-only with deterministic (non-LLM) Skills and no recommendations (I-9); the product-vs-fallback scope is RFC-0019's | **Ratified** | C3 (planned, `loop.py` + `consultation.py`) | pending C3 |
| DN-92 | Timeouts are injected-deadline primitives; TIMEOUT is a core event with the §4.7 reaction; numeric budgets are RFC-0020's | **Ratified** | C1/C3/C4 (planned, `events.py`/`loop.py`/`recovery.py`) | pending C1/C3/C4 |
| DN-93 | Every cognitive consultation requires a fresh Provider View over the current facts; otherwise Context Building is re-entered first | **Ratified** | C3 (planned, `consultation.py`) | pending C3 |
| DN-94 | The loop's integration tests inject deterministic fake provider/skill/executor responders (DN-55); production `core` files perform no I/O | **Ratified** | C5 (planned, conformance + integration) | pending C5 |

**Iteration 11 ratification note.** All ten Orchestration Core layer decisions
(DN-85…DN-94) are ratified **before Commit C1**, the first implementation
commit, exactly as Iterations 1–10 ratified their ten decisions before C0; none
is yet implemented (C1–C6 remain, per design review §12). The seven `core`
modules are scaffolded stubs (blueprint §2) and the `core` dependency row is
already declared in `tests/test_dependency_rules.py`, so the tree test stays
green throughout. Because Iteration 11's C0 (the design-review record) was
committed first, the ratification record in this file travels with Commit C1;
the design review §16 readiness flips to READY and Commit C1 (`state_machine.py`
+ `events.py`, the state/event model) satisfies the design review §14 C1 DoD.

## DN-95 — C1's verified implementation exceeds the §12 <300-LOC cap and the §15 ~270-LOC estimate; the deviation is reconciled and ratified as inherent to the DN-87 explicit per-event dispatch

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 11 Commit C1 reconciliation) |
| Date | 2026-08-11 |
| Resolves | design review §12 (the <300 production LOC per-commit cap), §15 (C1 estimated at ~270 impl LOC) |
| Grounding | DN-87 (the full §4.1–§4.7 catalog as one explicit typed event per kind); RFC-0002 §4 (the 39-event catalog); RFC-0013 §7 (record categories), AU3/AU6 (the audit mapping complete by construction); RFC-0007 S7 (determinism); the Q1 renumbering precedent (design review §10 — the plan-vs-record tension is reconciled by a decision note, never by editing the ratified review) |
| Embodied in | Commit C1 (`state_machine.py` + `events.py`) |

**Decision.** The verified C1 implementation is **1,027 production LOC** —
`state_machine.py` 233, `events.py` 794 — against the §15 ~270 estimate and the
§12 <300 per-commit cap. The overshoot is **inherent to the ratified design**,
not scope creep: DN-87 declares each of the 39 §4.1–§4.7 events as an explicit
typed dataclass carrying its `kind`, its RFC-0013 §7 record `category`, and its
per-event dispatch, so the audit mapping is complete by construction (AU3/AU6)
and no transition or routing logic lives outside the two C1 files. The
data-carrying events (OP_REPLY's routing constraint, COLLECTOR_FAILED's
critical/hopeless, ACTION_PARTIAL's halt, VERIFICATION_PASSED's steps-remaining,
TIMEOUT's injected `Deadline`) need per-event validation that a table-driven
dispatch would push into a central switch, and the estimate did not anticipate
the per-event docstrings. The cap is a governance target, not an RFC invariant
(the RFC-0002 §9 invariants and the design-review §14 C1 DoD are all met).
**The reconciled figure is recorded and ratified so Commit C1 lands complete
and unambiguous.**

**Effect.** C1's actual scope is on the record; later commits re-estimate from
the C1 experience (`events.py` is the whole §4 catalog, not a template for
other files). No RFC, no design decision (DN-86/DN-87), and no architecture
change; the §12 cap continues to apply to subsequent commits from their §15
estimates.

### DN-85 … DN-95 completion block (Iteration 11 closeout)

| Note | Status | Embodiment | Validation |
|---|---|---|---|
| DN-85 … DN-95 | **Implemented** | C1–C5 | corresponding suites + C5 conformance oracle |

**Iteration 11 completion note.** All ratified Orchestration Core layer
decisions (DN-85…DN-95) are implemented and validated: the full suite is green
(3404 tests, 2530 baseline + 874 new across the nine `test_core_*` modules),
the C5 conformance oracle (`test_core_imports.py`, `test_core_invariants.py`,
`test_core_authority.py`, plus the walkthrough mirrors in `test_core_loop.py`)
enforces the ratified readings — the reachable transition set (DN-86), the
typed §4 catalog (DN-87), the single boundary writer (DN-88), the token
re-validation edge (DN-89), the pure provider-failure reducer (DN-90), the
facts-only degraded mode (DN-91), the injected-deadline timeouts (DN-92), the
fresh-Provider-View rule (DN-93), and the zero-I/O injected-responder loop
(DN-94) — and the C1 production-LOC reconciliation (DN-95) stands as ratified.
The next iteration is the `cli` layer (blueprint §8.12), the only importer of
`core`, which consumes the `core` session/loop surface as its sole entry point.
No new decision note is required for this closeout.

---

## Iteration 12 ratification — Presentation layer (RFC-0001 §5)

This section ratifies the eight blocking questions Q1–Q8 of
`docs/iteration-12-design-review.md` §10 as **DN-96…DN-103**, exactly as
Iterations 1–11 ratified theirs before C0. Each question resolves an
implementation interpretation that the frozen corpus leaves open; no question
requires an RFC amendment, a `core`/`audit`/`context`/`schema` change, a new
module (the three `cli` modules are already scaffolded per blueprint §2), or a
new dependency edge beyond the declared `cli → {core, audit, context, schema}`
set with nothing importing `cli` (blueprint §4.1/§4.2). RFC-0005 through
RFC-0013 and RFC-0021 are Draft and RFC-0015 is Planned; the layer conforms to
the Draft wording it transcribes knowingly (RFC-0013 §8, RFC-0012 §13),
accepting the rework risk a Draft change carries, exactly as Iterations 1–11
conformed to the Draft sections they translated. The grounding RFCs cited below
are Accepted where marked; RFC-0012, RFC-0013, and RFC-0009 are Draft, RFC-0015
is Planned.

## DN-96 — Iteration 12 executes the `cli` layer; the blueprint §8.12/§8.13 numbering is superseded by DN-45's re-order and the MVP gate keeps its production meaning

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 12 ratification) |
| Date | 2026-08-11 |
| Resolves | design review §10 Q1 |
| Grounding | DN-45 (re-order: `core` = Iteration 11, `cli` = Iteration 12); blueprint §8.12 ("Iteration 11 — the MVP gate": DoD is RFC-0015/0019/0020 and the Drafts Accepted before production), §8.13 ("Iteration 12 — production MVP"); Iteration 11 closeout (consistency report "Readiness for Iteration 12": "The next iteration is `cli` (Layer 7; blueprint §8.12) — the only importer of `core`") |
| Embodied in | Iteration 12 implementation plan (docs-ratification commit C0) |

**Decision.** Iteration 12 executes as the **Presentation layer (`cli` only)**
(RFC-0001 §5; blueprint §2, §4.1, §4.2, §5). The blueprint §8.12/§8.13 numbering
is **superseded by DN-45's re-order and the Iteration 11 closeout**: `cli` is
Iteration 12, not the §8.13 label's "production MVP". The blueprint text itself
is **left unchanged** — the renumbering is recorded here and in the consistency
report as a reported tension, and the blueprint stands until RFC-0020 (the
authoritative build order). The MVP gate (§8.12 DoD) keeps its **production**
meaning: the real terminal/visual TUI and the semantic interaction contract
begin only after RFC-0015/0019/0020 and the Drafts are Accepted; this iteration
implements the CLI's **logic** under the scaffold posture (I/O-free, injected
primitives), exactly as Iterations 1–11 did. The re-order is dependency-safe:
`cli` (Layer 7) imports `core`, `audit`, `context`, `schema` only (blueprint
§4.1) and is imported by nothing. No architecture is added.

**Effect.** The Iteration 12 plan in `docs/iteration-12-design-review.md`
§12–§14 is ratified; the blueprint §8.12/§8.13 labels stay recorded as a
reported tension until RFC-0020.

## DN-97 — Iteration 12 builds the in-memory semantic presentation model; the interaction contract is RFC-0015's and the public signatures RFC-0020's

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 12 ratification) |
| Date | 2026-08-11 |
| Resolves | design review §10 Q2 |
| Grounding | RFC-0000 §3 row 0015 (Planned: "Define the interaction architecture of the TUI: how states, evidence, and approvals are presented *semantically* (not visually)… the contract between the runtime and any presentation surface"); blueprint §5 ("interface details deferred to RFC-0015"); DN-1 (in-memory domain types only; RFC-0020 owns serialization, parsing, validation, public API signatures, persistence and wire formats) |
| Embodied in | Iteration 12 implementation plan, Commit C1 (planned, `render.py`) |

**Decision.** Iteration 12 defines concrete canonical **in-memory presentation
types and pure mapping functions only** (the DN-1 precedent). These are **not**:
the TUI's semantic interaction contract, visual/layout definitions,
keybindings, or wire/display formats. RFC-0015 exclusively owns the semantic
interaction contract (how states, evidence, and approvals are presented
*semantically*); RFC-0020 owns the public API signatures, serialization, and
formats. The CLI's production files perform **no I/O** — rendering, collection,
and exposure are pure functions over injected sources (DN-55/DN-94).

**Effect.** The iteration's deliverable is the deterministic, I/O-free semantic
presentation model; the interaction-contract rework risk (RFC-0015 is Planned)
is accepted and bounded by the scaffold posture.

## DN-98 — The presentable state is derived from the owned surfaces only — the `LoopStep` trace, the §8 transcript, the §13 Provider View, and `schema` types; never raw provider/skill/machine data

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 12 ratification) |
| Date | 2026-08-11 |
| Resolves | design review §10 Q3 |
| Grounding | RFC-0001 §5 (render conversation/state; present evidence and proposed actions legibly); RFC-0002 I-4 (the LLM is consulted only through a Provider View), I-5 (no untrusted text into a command), I-7 (classification deterministic, never LLM self-report); RFC-0013 §7/§8 (the record categories and the transcript); RFC-0012 §13 (the Provider View); blueprint §5 (`core` is "the only entry point the `cli` uses") |
| Embodied in | Iteration 12 implementation plan, Commit C1 (planned, `render.py`) |

**Decision.** `cli/render.py` derives its presentable state deterministically
from the **owned surfaces**: the `core` `LoopStep` boundary trace (`session`,
`writes`, `consultations`, `disclosures`), the RFC-0013 §8 transcript, the
RFC-0012 §13 Provider View, and the `schema` types (`Action`, `Plan`, `Step`,
`Proposal`, `VerificationOutcome`). It **never** renders raw provider/skill/
machine data (I-4/I-5/I-7) and never constructs a command. The
provider-world/machine-world separation (RFC-0002 §1) is preserved at the
presentation boundary.

**Effect.** The render surface is fixed by the owned boundary trace; no new data
path from the runtime to the Operator exists outside the seam `core` already
exposes.

## DN-99 — `collect` maps a closed Operator-decision vocabulary to the RFC-0002 §4.1 operator events; inapplicable events are refused by `core` and presented honestly

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 12 ratification) |
| Date | 2026-08-11 |
| Resolves | design review §10 Q4 |
| Grounding | RFC-0001 §5 (collect approvals, refusals, and free-text Operator input); RFC-0002 §4.1 (the operator event catalog: OP_GOAL, OP_REPLY, OP_APPROVE, OP_OVERRIDE, OP_REJECT, OP_REFINE, OP_CANCEL, OP_INTERRUPT, OP_EXIT, OP_VIEW), I-9 (the runtime never fabricates); RFC-0004 §7 (Presentation not an actor) |
| Embodied in | Iteration 12 implementation plan, Commit C2 (planned, `collect.py`) |

**Decision.** `cli/collect.py` models a collected Operator decision as a closed
vocabulary (approve, reject, override, refine, reply, cancel, interrupt, exit,
view) with an optional free-text payload, mapped deterministically to the
RFC-0002 §4.1 operator event of the same intent. The CLI **decides nothing**: an
inapplicable decision yields `core`'s `Refusal`, which is presented honestly
(I-9), never swallowed and never re-mapped. Free text travels only as the
OP_REPLY/OP_REFINE payload (I-5: never into a command).

**Effect.** The `core` seam is one-way (events out, `LoopStep`/`Refusal` in);
the collection is deterministic and testable.

## DN-100 — `expose` presents the audit log through the RFC-0013 §8 transcript and the context through the RFC-0012 §13 Provider View; read-only and secret-free

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 12 ratification) |
| Date | 2026-08-11 |
| Resolves | design review §10 Q5 |
| Grounding | RFC-0001 §5 (expose the audit log and context view on demand); RFC-0013 §8 (the transcript's five categories, derived from the record only, AU2), §21 (the record's integrity is `audit`'s); RFC-0012 §13 (the Provider View); RFC-0009 SC2/SC3/SC4/SC16; DN-88 (`core` is the single runtime writer — `cli` never writes) |
| Embodied in | Iteration 12 implementation plan, Commit C3 (planned, `expose.py`) |

**Decision.** `cli/expose.py` exposes the audit log as the **five §8 transcript
categories** via `audit.transcript.render` (metadata only, SC4) and the context
view as the **§13 Provider View** (SC3). Exposure is **read-only**: `cli` never
appends a record (the write is `core`'s, DN-88), never mutates Context/Memory,
and never re-derives a record. No secret value ever leaves (SC2/SC3/SC4/SC16);
the `AuditStore`'s durable lifecycle (Exported/Retained/Deleted) is RFC-0020's.

**Effect.** The exposure seam is a pure read over the transcript and View; the
secret-free guarantee holds by construction, not by re-redaction (which would
need a `secrets` import, forbidden to `cli`).

## DN-101 — The risk-class/gate names carried by the records map to a closed presentation-tone vocabulary; presentation-only, never a gate change

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 12 ratification) |
| Date | 2026-08-11 |
| Resolves | design review §10 Q6 |
| Grounding | RFC-0001 §5 ("Translate risk levels into *presentation* tone and layout (never into policy)"); RFC-0004 §7 (Presentation not an actor); RFC-0008 (the risk classes and gates are `policy`'s); RFC-0013 §7 cat. 4 (`ApprovalRecord.risk_class`/`gate` names as record data); RFC-0004 §3 (consume-as-values) |
| Embodied in | Iteration 12 implementation plan, Commit C1 (planned, `render.py`) |

**Decision.** The presentation tone is a **closed enum**, mapped deterministically
from the `risk_class`/`gate` **names** the records carry (RFC-0004 §3
consume-as-values — `policy` is forbidden to `cli`). The mapping is total,
one-directional, and **presentation-only**: a tone never changes a gate, never
mints an approval token, never blocks, never classifies (RFC-0001 §5; RFC-0004
§7).

**Effect.** The tone is derived from record data without a `policy` import; the
"never into policy" doctrine is conformance-enforced (C4).

## DN-102 — The CLI drives the session only through `core.advance`/`core.pump`, emitting §4.1 operator events and presenting `LoopStep`/`Refusal`; it never constructs session/state/recovery logic

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 12 ratification) |
| Date | 2026-08-11 |
| Resolves | design review §10 Q7 |
| Grounding | blueprint §5 (`core` is "the only entry point the `cli` uses"); RFC-0002 §4.1/§5 (the session loop and the operator events); RFC-0004 §7 (Presentation not an actor); DN-88 (`core` is the single runtime writer) |
| Embodied in | Iteration 12 implementation plan, Commits C2/C3 (planned, `collect.py`/`expose.py`) |

**Decision.** The CLI's only interaction with the runtime is the `core` surface:
`Session`, `Prerequisites`, the §4.1 operator events, `Loop`, `LoopStep`,
`advance`, `pump`, `Refusal`. It never holds and mutates a `Session`, never
builds a `Workstate`, never runs a recovery reaction, never classifies, never
writes a record. An inapplicable event is refused by `core`; the `Refusal` is
presented, not worked around.

**Effect.** The runtime half of the loop stays `core`'s alone; the CLI's role is
strictly presentation and collection.

## DN-103 — The CLI's logic is I/O-free and deterministic; tests inject the `LoopStep`/record/View sources and the C4 conformance suite enforces imports, authority, tone-only, and the banned-token oracle

| Field | Value |
|---|---|
| Status | Ratified (Operator, Iteration 12 ratification) |
| Date | 2026-08-11 |
| Resolves | design review §10 Q8 |
| Grounding | blueprint §7 (the `cli` test-oracle row: RFC-0001 §5 Presentation); DN-55 (the injected-primitive precedent), DN-94 (the no-I/O posture); RFC-0007 S7 (determinism is asserted) |
| Embodied in | Iteration 12 implementation plan, Commits C1–C4 |

**Decision.** The CLI's production files perform **no I/O** — no clock, no
network, no filesystem, no subprocess (DN-55/DN-94). The C1–C3 tests inject the
sources (`LoopStep`, records, `ProviderView`) and assert the pure presentable
outputs. The C4 conformance suite asserts the exact §4.1/§4.2 import edges, the
closed stdlib allowlist, the banned-token oracle, the RFC-0004 §7 non-actor
cells, tone-only (a tone never changes a gate), secret-free outputs, and the
only-`cli`-imports-`core` AST edge.

**Effect.** The presentation layer is testable deterministically now; the real
terminal I/O loop is RFC-0015/RFC-0020's.

### Q1–Q8 question status

| §10 Q | Subject | Status | Where resolved |
|---|---|---|---|
| Q1 | Iteration scope / renumbering vs blueprint §8.12/§8.13 + the MVP gate | **Ratified** | DN-96 (this file) |
| Q2 | The semantic-vs-visual split | **Ratified** | DN-97 (this file) |
| Q3 | The presentable-state source | **Ratified** | DN-98 (this file) |
| Q4 | The decision-collection model | **Ratified** | DN-99 (this file) |
| Q5 | The audit/context exposure | **Ratified** | DN-100 (this file) |
| Q6 | The risk-tone translation surface | **Ratified** | DN-101 (this file) |
| Q7 | The `core` seam | **Ratified** | DN-102 (this file) |
| Q8 | Testability at zero I/O | **Ratified** | DN-103 (this file) |

All eight §10 questions are resolved as decision notes; none requires an RFC
amendment, a `core`/`audit`/`context`/`schema` change, a new module (the three
`cli` modules are already scaffolded per blueprint §2), or a new dependency edge
beyond the declared `cli → {core, audit, context, schema}` set with nothing
importing `cli` (blueprint §4.1/§4.2). **Iteration 12 implementation is
unblocked** (design review §16 readiness). The planned commits (design review
§12) will be recorded in `docs/implementation-consistency-report.md` (Iteration
12 section) as they land.

### DN-96 … DN-103 completion status

| Note | Decision | Status | Embodied in | Validated by |
|---|---|---|---|---|
| DN-96 | `cli` executes at Iteration 12; blueprint §8.12/§8.13 labels superseded and stand until RFC-0020; the MVP gate keeps its production meaning | **Ratified** | C0 (docs-ratification) | design review §10 Q1 |
| DN-97 | In-memory semantic presentation model only; the interaction contract is RFC-0015's, the public signatures RFC-0020's | **Ratified** | C1 (planned, `render.py`) | pending C1 |
| DN-98 | The presentable state is derived from the owned surfaces only — the `LoopStep` trace, the §8 transcript, the §13 View, `schema` types | **Ratified** | C1 (planned, `render.py`) | pending C1 |
| DN-99 | `collect` maps a closed decision vocabulary to the §4.1 operator events; inapplicable events are refused by `core` and presented honestly | **Ratified** | C2 (planned, `collect.py`) | pending C2 |
| DN-100 | `expose` presents the §8 transcript and the §13 View; read-only and secret-free (SC-series) | **Ratified** | C3 (planned, `expose.py`) | pending C3 |
| DN-101 | The record-carried risk-class/gate names map to a closed presentation-tone vocabulary; presentation-only | **Ratified** | C1 (planned, `render.py`) | pending C1 |
| DN-102 | The CLI drives the session only through `core.advance`/`core.pump`; never constructs session/state/recovery logic | **Ratified** | C2/C3 (planned, `collect.py`/`expose.py`) | pending C2/C3 |
| DN-103 | The CLI's logic is I/O-free and deterministic; injected sources; C4 conformance suite | **Ratified** | C1–C4 (planned) | pending C4 |

**Iteration 12 ratification note.** All eight Presentation layer decisions
(DN-96…DN-103) are ratified **before Commit C1**, the first implementation
commit, exactly as Iterations 1–11 ratified their decisions before C0; none is
yet implemented (C1–C5 remain, per design review §12). The three `cli` modules
are scaffolded stubs (blueprint §2) and the `cli` dependency rows are already
declared in `tests/test_dependency_rules.py`, so the tree test stays green
throughout. Because Iteration 12's C0 (the design-review record) is committed
first, the ratification record in this file travels with Commit C0; the design
review §16 readiness flips to READY and Commit C1 (`render.py`, the presentation
model) satisfies the design review §14 C1 DoD.

## DN-104 — The core `OpReply` route validation is fixed to its intended fail-loud contract

**Situation.** Iteration 12, Commit C2. The `collect` path constructs
`OpReply(routes_to=...)`; when the caller supplied a missing route
(``routes_to=None``), `OpReply.__post_init__` crashed with an
``AttributeError`` (`'NoneType' object has no attribute 'name'`) — the
f-string interpolated ``self.routes_to.name`` **before** the guard could raise
the intended ``ValueError``. The guard text existed; the crash hid it.

**Decision.** Fix the core event so the *authoritative* validation always fires
the fail-loud ``ValueError`` it declares: interpolate the route by ``!r``
(``{self.routes_to!r}``) so a ``None`` or any non-``State`` value renders as
data inside the message instead of dereferencing ``.name``. The CLI keeps the
design-review Q7 rule — it does **not** pre-validate routes itself; it hands the
decision to `core`'s event type and lets the authoritative rule refuse (the
Ratified reading of DN-99: inapplicable decisions are refused by `core`, and the
refusal surfaces, never a silent CLI swallow).

**Effect.** `to_event(Collected(decision), routes_to=None)` (or an out-of-set
route) now raises the clean, deterministic `ValueError` it documents
(RFC-0007 S7); the CLI collection tests assert both the accepted routes
(Diagnosis/Planning) and the refused ones. One line changed in
`core/events.py`; no RFC, no other `core` behavior, no design change.

### DN-96 … DN-104 completion block (Iteration 12 closeout)

| Note | Status | Embodiment | Validation |
|---|---|---|---|
| DN-96 … DN-103 | **Implemented** | C1–C4 | corresponding suites + C4 conformance oracle |
| DN-104 | **Implemented** | C2 (`core/events.py`, one line) | `test_cli_collect.py` (valid/refused REPLY routes) |

**Iteration 12 completion note.** All ratified Presentation layer decisions
(DN-96…DN-103) are implemented and validated, and the C2-surfaced core defect is
fixed (DN-104): the full suite is **3486 collected — 3484 passed** (the two
failures, `test_trust_hostile.py::test_no_non_excluded_quarantine_can_exist` and
`test_trust_invariants.py::test_quarantine_exclusion_is_unconditional`, are
pre-existing on a clean tree and unrelated to Layer 7), with the C4 conformance
oracle (`test_cli_imports.py`, `test_cli_conformance.py`) enforcing the ratified
edges — the in-memory semantic model (DN-97), the owned-surface derivation
(DN-98), the closed decision → §4.1 event map (DN-99), the transcript/View
exposure (DN-100), the presentation-only tone map (DN-101), the `advance`/`pump`
seam (DN-102), and the zero-I/O injected-source tests (DN-103). The next
iteration's work gates on RFC-0015/0019/0020 (the TUI contract, the MVP
definition, and the implementation blueprint) per the design review §1.2
deferred table; the `cli` layer itself is complete.
