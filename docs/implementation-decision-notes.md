# Implementation Decision Notes

> **Document type:** Implementation decision log, not an RFC.
> **Read this first:** These notes record implementation decisions ratified
> during Iteration 1 (the `schema` package). They define no new architecture,
> modify no RFC, and change no ownership (blueprint §10; RFC-0004 §3). They fix
> the *reading* of ambiguities reported by `docs/iteration-1-design-review.md`
> §16 so that a reported ambiguity cannot reappear in a later iteration. Each
> note names the ambiguity it resolves, its RFC grounding, and the commit that
> embodies it. Amending a note here amends no RFC; it is a re-ratified
> implementation record, subject to the same review that ratified it.

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
| Status | Ratified (Operator, Iteration 1 review) |
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
