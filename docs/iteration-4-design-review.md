# Iteration 4 — Design Review (Verification Layer)

> **Document type:** Implementation design review, at the same rigor as
> Iterations 2–3. **Not an RFC, not code.**
> **Read this first:** This document **defines no new architecture, modifies no
> RFC, invents no behavior, and writes no production code.** It translates the
> frozen corpus (RFC-0000–0013, RFC-0021, the two walkthroughs, the decision
> traceability matrix, `docs/architecture-implementation-blueprint.md`, and the
> ratified `docs/implementation-decision-notes.md` DN-1…DN-24) into an
> implementation plan for the **Verification Layer — the `verification`
> package** (blueprint §8.5). Where the corpus does not decide something, this
> document **reports** it as an ambiguity or a question; it does not resolve it.
>
> **Status of sources.** RFC-0006 is **Draft** (not Accepted). Per RFC-0003 Part
> II §1.1 Draft RFCs are not normative and must not be relied upon by
> implementation; yet the blueprint (a translation, §0) targets the Drafts'
> *invariants* as the conformance oracle (blueprint §9 #2). Iteration 4 inherits
> Iterations 1–3's posture: it conforms to RFC-0006's Draft wording knowingly,
> accepting the rework risk that a Draft change carries. Blueprint §8.0 gate
> stands — production code begins only after RFC-0015/0019/0020 and the Drafts
> are Accepted; this iteration builds the translation scaffold.
>
> **Scope decision (reported — Q1).** Blueprint §2 fixes the module set
> `verification/{__init__,compare,outcome}.py`. The RFC-0006 §6 verification
> *process* (Execute → Collect → Normalize → Facts → Compare → Outcome) names
> steps owned outside this package: Collect and Normalize are `factlayer`'s
> (RFC-0005), Execute is RFC-0008/`executor`'s, and the runtime obligation
> "every executed action is followed by a verification attempt" (RFC-0002
> invariant 2, V2) is `core`'s. Iteration 4 therefore builds **Compare + Outcome
> semantics over already-normalized Facts**; the process *invocation* is
> orchestration, deferred. This mirrors Iteration 3's Q1.

---

## 1. Architectural review

### 1.1 Scope (blueprint §8.5, transcribed)

| Item | Value |
|---|---|
| Goal | Deterministic Compare and Outcome |
| Work | Compare Facts against declared Postconditions; Outcome mapping |
| Definition of Done | V3 (deterministic), V4 (no stale), V7 (contradiction wins), V10 (Postconditions fixed), V14 (never skip) all pass |
| RFC basis | RFC-0006 §5–§8; RFC-0002 invariant 2 |

Blueprint §7 (test oracle, adds a constraint beyond the DoD row): `verification`
— "Compare is deterministic (V3), read-only (V8), never stale (V4), Postconditions
fixed before Compare (V10), contradiction wins (V7), never skips (V14)".

The §8.5 *Work* wording names five outcomes. Per DN-5, RFC-0006 §7 is
authoritative: **eight** values. The five-value wording (here and in the current
`verification/outcome.py` stub docstring) is superseded; see §6.

### 1.2 Module set (fixed)

One package, three modules — **fixed** by blueprint §2 and
`tests/test_packages.py::test_tree_matches_blueprint_exactly`. Adding a module
breaks the tree test.

| Module | Blueprint responsibility |
|---|---|
| `verification/__init__.py` | package surface |
| `verification/compare.py` | deterministic Compare |
| `verification/outcome.py` | Outcome mapping |

### 1.3 RFC sections implemented (translation surface)

| RFC | Section | Implemented as |
|---|---|---|
| RFC-0006 | §5 Postconditions | Consumes `schema.PostCondition` (DN-4) as the fixed expected state; never invents expectations (V10) |
| RFC-0006 | §6 Verification Process | The Compare→Outcome steps, as pure functions over Facts; Collect/Normalize consumed via `factlayer` results (Q1) |
| RFC-0006 | §7 Outcome Model | Deterministic mapping to the eight `VerificationOutcome` values; strictest-wins (§7 rule 2); verbatim, no silent upgrade (§7 rule 3) |
| RFC-0006 | §8 Contradictions | Comparison-level conflict rule (Q9); Contradicted stops the path (V7) |
| RFC-0006 | §9 Evidence Comparison | Principles 1–7: compare Facts not text; expected delta drives; unexpected delta surfaced; missing ≠ success; conflict → Contradicted; freshness precondition; scope follows Postcondition |
| RFC-0006 | §13 V1–V16 | V3, V4, V5, V6, V7, V8, V9, V10, V14, V15 enforced here; V2/V12/V13/V16 owned by the runtime (`core`) and flagged |
| RFC-0002 | invariant 2 | Made *possible* (Compare exists); the runtime obligation is `core`'s |

### 1.4 Explicit exclusions

None is silently dropped; each is recorded with its owner.

| Item | Why excluded | Owner |
|---|---|---|
| Collect/Normalize invocation | `factlayer` owns them (RFC-0005 §2); re-running them after execution is orchestration | RFC-0005; `core` (Q1) |
| "Every action → verification attempt" obligation | Runtime state-machine behavior | RFC-0002 invariant 2; V2; `core` (Iteration 10) |
| Verification Scope type | RFC-0006 §11 uses RFC-0021 vocabulary (referenced, not a dependency); §9.7 "scope follows the Postcondition" | RFC-0021 §11/§12; RFC-0020 (Q4) |
| Before/after delta analysis | Needs runtime-passed before-state Facts | RFC-0006 §9; `core` (Q5) |
| Verification Confidence computation | RFC-0006 §12 levels need a new type; §15 OQ1; V15 honored by never upgrading | RFC-0006 §12; RFC-0020 (Q6) |
| Interrupted production | Trigger is process cut-off (operator/reboot/watchdog) — orchestration | RFC-0002 §2.9; `core` (Q7) |
| Evidence record persistence / audit | RFC-0013 (Iteration 7); RFC-0012 (Iteration 8) | RFC-0013/0012 (Q10) |
| RFC-0005 §8 Fact relationships | Deferred by Iteration 3; contradiction here is a narrow comparison rule (Q9) | RFC-0005 §8 |
| Rollback catalogue, presentation, resume mechanics, freshness-bound values | RFC-0006 §15 OQs 2/3/4/6 | RFC-0017/0015/0014/0020 |
| Goal-level Outcome | DN-6; RFC-0003 §2.3 sense owned by `core` | RFC-0003 §2.3 |
| Secret handling in evidence | RFC-0009 (Iteration 5); no secret material in Outcomes (stub docstring) | RFC-0009 |

---

## 2. Ownership review

### 2.1 Package owner

| Package | Owning RFC | Responsibility |
|---|---|---|
| `verification` | RFC-0006 | Deterministic Compare of Facts against declared Postconditions; Outcome determination (blueprint §3; consistency report: `verification` → RFC-0006 → `compare`, `outcome`) |

### 2.2 Type owners (one owner each)

| Type | Module | Owning RFC / section | Protected by |
|---|---|---|---|
| Compare function | `verification/compare.py` | RFC-0006 §6, §9 | V3, V4, V7, V8, V10 |
| Outcome determination | `verification/outcome.py` | RFC-0006 §7 | V5, V6, V9, V14, V15 |
| CompareResult / per-Postcondition verdict (in-memory) | `verification/compare.py` | RFC-0006 §9 | V6 (exact held/not-held), V7 |
| OutcomeRecord (in-memory, evidence-carrying) | `verification/outcome.py` | RFC-0006 V11/V12 | V11 (evidence + Outcome), Q10 |
| `schema.PostCondition` (reused) | `schema/action.py` | RFC-0006 §5; DN-4 | V10 (fixed before Compare) |
| `schema.VerificationOutcome` (reused) | `schema/outcome.py` | RFC-0006 §7; DN-5 | exhaustive + exclusive |
| `schema.Fact`/`Provenance`/`Freshness`/`FactStatus` (reused) | `schema/fact.py` | RFC-0005 | F1–F16; V4 input |
| `factlayer` store/collect/normalize (reused) | `factlayer/*` | RFC-0005 | Facts are the only evidence (V1) |

**The two-owner check.** DN-4 splits `PostCondition`: `schema` owns the type,
`verification` owns evaluation/comparison semantics. Freshness has two faces
(F14/F15 in `factlayer`, V4 in `verification`) — the boundary is Q8, reported,
not resolved. No property has two owners otherwise.

**Authority (RFC-0004 §4.6, §4.9, §7; traceability D-01/D-04).** `verification`
holds **Verify** — the re-observation arm, consuming Facts the Diagnostics Layer
produced. It never holds Propose, Infer, Approve, Execute, Refuse, or Persist.
The Executor never verifies itself (RFC-0004 §4.9; RFC-0011 SK6); verification
is never the LLM's or a Skill's assessment (V3). **No authority leak:**
compare/outcome are pure, mutate nothing (V8), create no Facts.

---

## 3. Dependency review

### 3.1 Allowed imports (blueprint §4.1; already asserted by `tests/test_dependency_rules.py:24`)

| From | To | Why allowed |
|---|---|---|
| `verification` | `factlayer` | Compare consumes normalized Facts (V1); re-observation arm of Verify |
| `verification` | `schema` | PostConditions, VerificationOutcome, Fact/Freshness types |
| `verification` | `systemmodel` | PostCondition Subject vocabulary (RFC-0021; Q4) |

Layer 2, after `factlayer` (blueprint §8.3→§8.4→§8.5; RFC-0000 §7). The
`verification→factlayer` edge was declared latent in Iteration 3 (§3.3) and is
now used.

### 3.2 Forbidden imports (blueprint §4.2; already asserted by `tests/test_dependency_rules.py:67`)

| Package | Must NOT import | Reason |
|---|---|---|
| `verification` | `providers`, `policy`, `executor`, `skills`, `context`, `audit`, `secrets`, `trust`, `core`, `cli` | Verification is deterministic Fact comparison (V1/V3); never execution, never secret handling (RFC-0009 §1), never policy or orchestration |

### 3.3 Acyclicity

Edges point strictly downward; no cycle; `tests/test_dependency_rules.py` asserts
declared and observed acyclicity. No type is defined in two modules (§2).

---

## 4. Layer review

```
Layer 0  schema
Layer 1  systemmodel
Layer 2  factlayer ─► verification
```

- `verification` is Layer 2, after `factlayer` (blueprint §8.3→§8.4→§8.5;
  RFC-0000 §7).
- No reverse edge: `schema` (Layer 0) and `systemmodel` (Layer 1) never import
  `verification`.
- The allowed-edge set and the tree are already enforced by the conformance
  harness before any `verification` code exists (the edges are latent until the
  implementation imports them).

---

## 5. Public API review

Signatures are RFC-0020's (blueprint §5; DN-1). This review records the planned
*surface* only. Types it consumes (already built, unchanged):

| Type | Module | Field/notes | RFC basis |
|---|---|---|---|
| `PostCondition` | `schema/action.py` | `subject: Subject`, `property: Property`, `expected_value: Value`, `freshness: Freshness`; frozen | RFC-0006 §5; DN-4 |
| `Action.verification_criteria` | `schema/action.py` | `tuple[PostCondition, ...]` — the fixed expectations (V10) | RFC-0006 §5; RFC-0008 §5 |
| `Step.preconditions` / `postcondition` / `verification_method` | `schema/action.py` | before-Facts home (Q5); `verification_method: str` is a placeholder (RFC-0020) | RFC-0006 §4/§5 |
| `VerificationOutcome` | `schema/outcome.py` | 8 members, exhaustive + exclusive; `INTERRUPTED`/`EXPIRED` present (DN-5) | RFC-0006 §7 |
| `Fact`/`Freshness`/`FactStatus` | `schema/fact.py` | the evidence and its status/freshness (Q2, Q8) | RFC-0005 §3/§4/§12 |

Planned surface to be introduced:

| Module | Planned public surface | RFC source |
|---|---|---|
| `verification/compare.py` | deterministic Compare (after-Facts + PostConditions → per-Postcondition verdicts + contradiction/Unknown signals) | RFC-0006 §6, §9 |
| `verification/outcome.py` | Outcome determination (verdicts → one of eight, strictest-wins; in-memory evidence-bearing OutcomeRecord) | RFC-0006 §7, V11/V12 |
| `verification/__init__.py` | package surface exposing `compare`/`outcome`; process contract | RFC-0006 §6 |

No new public type is *required* by the corpus before the questions are answered
(Q4 scope type, Q6 confidence type are conditional on ratification).
`Step.verification_method: str` is a free-form placeholder — never consumed by
Compare (Compare consumes PostConditions), noted for RFC-0020.

---

## 6. RFC consistency review

**Consistent (passes):**

- V1–V16 have exactly one normative home (RFC-0006 §13; traceability §3).
  RFC-0006 uses F13/F15 (RFC-0005) and A1/A5 (RFC-0004) — no cross-ownership.
- Outcome model (RFC-0006 §7): exhaustive (rule 1); strictest-wins
  **Contradicted > Verified Failure > Unknown > rest** (rule 2); verbatim, no
  silent upgrade (rule 3); evidence-carrying (rule 4, V11/V12); rollback = new
  action (rule 5). Matches `schema.VerificationOutcome` (DN-5) and
  `test_schema_outcome.py`.
- §8 split: RFC-0005 §8 = what a contradiction *is*; RFC-0006 §8 = what the
  Assistant *does*. Clean split; representation side deferred → Q9.
- Verify authority and determinism consistent with RFC-0004 §4.6/§7 and
  traceability D-01/D-04; invariant 2 / §2.9 bind the runtime (`core`), not
  this layer.

**Inconsistent / wording tensions (reported, not resolved):**

1. RFC-0006 header (line 11–12): claims dependencies are "accepted in this
   series" — RFC-0005/0007/0008 are **Draft**. Reporting only.
2. RFC-0006 §7 "Verified Failure … When it occurs: An expected Fact is missing
   or contradicts" — collides with V9 (missing → Unknown, §9.4) and V7
   (contradicts → Contradicted); partially reconciled by rule 2. Reported.
3. Five-value Outcome wording persists in blueprint §8.5 *Work*, traceability
   D-11, and the `verification/outcome.py` stub docstring — **superseded by
   DN-5** (eight values). Cosmetic.
4. RFC-0006 §7 Expired (time-dependent) vs V3 determinism → Q7.
5. RFC-0006 §5 "an expected Status" maps to `expected_value: Value` per DN-4 —
   already settled.
6. Pre-existing, unrelated: `rfc/RFC-0004-trust-and-authority-model.md:470`
   unknown invariant `S1` (family is A1–A10) — requires RFC amendment, out of
   scope, unchanged.

---

## 7. Ambiguity analysis

Every ambiguity found, classified per the established rule (already-answered /
needs-DN / requires-RFC-amendment). None is silently resolved.

| # | Ambiguity | Class | Why |
|---|---|---|---|
| A1 | Collect/Normalize in §6 process but not in the module set | **needs-DN** (Q1) | Blueprint §2 fixes modules; process invocation owner is `core` |
| A2 | Comparable `FactStatus` values unspecified | **needs-DN** (Q2) | RFC-0006 §3/§9 silent; RFC-0005 §4 enumerates 8 statuses |
| A3 | `FactStatus.Verified` writer + V8 store-write | **needs-DN** (Q3) | RFC-0005 §4 defines the status; V8 permits-but-ambiguates the write |
| A4 | Verification Scope: type vs implicit | **needs-DN** (Q4) | RFC-0021 referenced, not a dependency (RFC-0006 §14); §9.7 says scope follows Postcondition |
| A5 | Before/after three-set Compare (§9.1) vs module scope | **needs-DN** (Q5) | Partially Successful / No Observable Change need before-state |
| A6 | Confidence computation (§12) | **needs-DN** (Q6) | §15 OQ1 defers algorithms to RFC-0020 |
| A7 | Interrupted/Expired producers | **needs-DN** (Q7) | Interrupted is orchestration (RFC-0002 §2.9); Expired conflicts with V3 |
| A8 | V4 vs F14/F15 staleness boundary | **needs-DN** (Q8) | DN-4 says verification owns semantics only |
| A9 | Contradiction without deferred RFC-0005 §8 | **needs-DN** (Q9) | Representation deferred by Iteration 3 |
| A10 | V11/V12 evidence-record home | **needs-DN** (Q10) | Durable records are RFC-0013's |
| A11 | RFC-0006 header "accepted in this series" | **requires-RFC-amendment / reporting** | Factually wrong statuses; draft-rfc wording fix |
| A12 | §7 Verified-Failure "occurs when" wording | **reporting (may need amendment)** | Collides with V9/V7; rule 2 partially reconciles |
| A13 | Five-value Outcome wording (blueprint/D-11/stub) | **already-answered** | DN-5 |
| A14 | §5 "expected Status" → `expected_value` | **already-answered** | DN-4 |
| A15 | `Step.verification_method: str` free-form | **already-answered / RFC-0020** | DN-1; placeholder |

---

## 8. Blocking questions

| Q | Question | Owner (RFC §) | Blocks | Sev. | Recommended resolution |
|---|---|---|---|---|---|
| Q1 | Scope: Compare+Outcome semantics only; never invoke Collect; never model Preconditions (§4 out of the §5–§8 basis)? | RFC-0006 §6; blueprint §2/§8.5; RFC-0002 §2.9 | all commits | Med | **Yes** — semantics only; process invocation + Precondition revalidation + "every action → attempt" are `core`/RFC-0008 obligations (mirrors DN-13/DN-22) |
| Q2 | Which `FactStatus` values are comparable evidence? | RFC-0006 §3/§9; RFC-0005 §4 | C1 | Med | Status gate: Observed/Verified → compare; Unknown/Unavailable/Unsupported → Unknown (V9/V14); Contradicted → Contradicted (V7); Stale → excluded (V4); Invalid → excluded (F16) |
| Q3 | Does Iteration 4 write `Verified`/Outcome into the `factlayer` store, or is the store read-only here? | RFC-0005 §4; RFC-0006 V8/§6 | C2, C3 | High | **Defer** — Compare/Outcome pure; V8's store phrase is permission, not obligation; Verified-write + Outcome recording are runtime (V2) obligations |
| Q4 | Verification Scope: type bound to `systemmodel`, or implicit? | RFC-0006 §11/§9.7; RFC-0021 §11/§12 | C1 | Med | **Implicit** — scope = Postcondition Subjects/Properties (V10, §9.7); no Scope type (mirrors DN-9/DN-14) |
| Q5 | Does `compare` take before-Facts as input this iteration, or after-Facts + Postconditions only? | RFC-0006 §9.1/§7; RFC-0005 §15 OQ3 | C1 | High | **After + Postconditions first**; before/after delta deferred to the runtime; consequence: Partial/No-Observable-Change not producible from one snapshot |
| Q6 | Confidence (§12) computed here or deferred? | RFC-0006 §12/§15 OQ1; RFC-0020 | C2 | Low | **Defer** computation to RFC-0020; honor V15 by never-upgrading |
| Q7 | Which of the eight Outcomes can the semantics-only layer produce? | RFC-0006 §7, V3; RFC-0002 §2.9 | C2 | Med | Fact-determined values produced; **Interrupted** = orchestrator's; **Expired** → re-collect-or-Unknown (V4), not a Compare output |
| Q8 | Staleness: re-derive or trust `factlayer` freshness state; role of `PostCondition.freshness`? | RFC-0006 V4/§9.6/§5; RFC-0005 §12 (F14/F15); DN-4 | C1 | High | **Trust** the freshness state carried by Facts; `PostCondition.freshness` is the declared bound to check against |
| Q9 | Contradiction: comparison-level rule in `compare.py`, leaving RFC-0005 §8 deferred? | RFC-0006 §7/§8; RFC-0005 §8 | C1 | High | **Yes** — narrow rule (same Subject+Property, differing values, same freshness → Contradicted, §7 rule 2, V7); RFC-0005 §8 stays deferred; reported deviation |
| Q10 | V11/V12 evidence record: in-memory here, durable in RFC-0013? | RFC-0006 V11/V12/§7 rule 4; RFC-0013; RFC-0012 | C2 | Low | **In-memory** OutcomeRecord (Outcome + determining Facts); durable record/retention → RFC-0013 (Iteration 7) |

---

## 9. Proposed decision notes (DN-25…DN-34)

Proposals for Operator ratification; none takes effect by this review. Each maps
to exactly one question. **Ratified as DN-25…DN-34 in
`docs/implementation-decision-notes.md`.**

| DN | Resolves | Proposal |
|---|---|---|
| DN-25 | Q1 | Iteration 4 = Compare+Outcome semantics over normalized Facts; no Collect invocation; no Precondition modeling |
| DN-26 | Q2 | Comparable-FactStatus gate (see Q2 recommendation) |
| DN-27 | Q3 | No store write in `verification`; Verified-status write + Outcome recording are runtime obligations |
| DN-28 | Q4 | Verification Scope implicit via PostCondition; no Scope type |
| DN-29 | Q5 | `compare` consumes after-Facts + Postconditions; before/after delta deferred to runtime |
| DN-30 | Q6 | Confidence computation deferred to RFC-0020; V15 honored by never-upgrade |
| DN-31 | Q7 | Produciable Outcomes = the Fact-determined five*; Interrupted owned by orchestrator; Expired = re-collect-or-Unknown (*Verified Success/Failure, Partially Successful, Unknown, Contradicted — plus No Observable Change once before-state exists, DN-29) |
| DN-32 | Q8 | `verification` trusts Fact freshness state; `PostCondition.freshness` is the declared bound |
| DN-33 | Q9 | Contradiction is a comparison-level rule in `compare.py`; RFC-0005 §8 relationship mechanics stay deferred |
| DN-34 | Q10 | In-memory evidence-bearing OutcomeRecord; durable record/retention deferred to RFC-0013 |

---

## 10. Atomic commit plan

Recorded only; nothing is executed. Each commit: purpose, est. LOC, ownership,
RFC sections, dependencies, Definition of Done. All keep CI green (ruff,
pytest, dependency rules, package-tree test) and add conformance tests.

**C0 — `docs: ratify Iteration 4 design review decisions (DN-25..DN-34)`**
*(precedes C1; mirrors Iterations 1–3)*
- Purpose: record ratified Q1–Q10 readings; add the Iteration 4 design review;
  update the consistency report.
- Est. LOC: ~790 (docs) · Ownership: process (docs) · RFC sections: n/a ·
  Depends: Q1–Q10 answers · DoD: every question has a DN; report reflects
  Iteration 4; suite green.

**C1 — `feat(verification): deterministic Compare against declared Postconditions (RFC-0006 §6, §9; V3, V7, V10)`**
- Purpose: pure `compare` — per-Postcondition verdicts over normalized Facts;
  scope follows Postcondition (§9.7); contradiction rule (DN-33); freshness gate
  (DN-32); status gate (DN-26).
- Est. LOC: ~180 · Ownership: RFC-0006 §6/§9 · RFC sections: §5 (PostConditions
  consumed), §6, §8, §9, §13 (V3/V4/V7/V10/V14) · Depends: `schema.PostCondition`
  (DN-4), `schema.VerificationOutcome` (DN-5), `schema.Fact/Freshness/FactStatus`;
  DN-25, DN-26, DN-28, DN-29, DN-32, DN-33 · DoD: V3 deterministic, V7
  contradiction wins, V10 Postconditions fixed/immutable, read-only (V8), never
  stale (V4), scope declared not assumed (§9.7).

**C2 — `feat(verification): Outcome determination (RFC-0006 §7; V5, V6, V9, V14, V15)`**
- Purpose: pure `outcome` — strictest-wins classification (§7 rule 2) to the
  eight-value enum; verbatim report (§7 rule 3); in-memory evidence-bearing
  OutcomeRecord (DN-34); never-upgrade (V5/V15); missing→Unknown (V9); partial
  exactness (V6); never-skip (V14).
- Est. LOC: ~160 · Ownership: RFC-0006 §7 · RFC sections: §7 (rules 1–5), §13
  (V5/V6/V9/V14/V15/V16) · Depends: C1 verdicts, `schema.VerificationOutcome`
  (DN-5); DN-27, DN-30, DN-31, DN-34 · DoD: exhaustive + mutually exclusive;
  strictest-wins precedence; no silent upgrading; outcomes carry evidence (V11);
  no store write (V8, DN-27).

**C3 — `test(verification): Layer-2 conformance and V-invariant suite`**
- Purpose: conformance (imports, no I/O at import, forbidden edges) + V3/V4/V5/
  V6/V7/V8/V9/V10/V14/V15 + §7 precedence + scenario mapping.
- Est. LOC: ~200 · Ownership: RFC-0006 (conformance oracle) · RFC sections: §6,
  §7, §8, §13 · Depends: C1, C2 · DoD: every mapped invariant has a test;
  `test_packages.py` and `test_dependency_rules.py` pass unchanged (edges already
  asserted); no new module.

**C4 — `docs: record Iteration 4 conformance mapping`**
- Purpose: type→owner map, ratified answers, deferred items in the consistency
  report.
- Est. LOC: ~120 · Ownership: process (docs) · RFC sections: n/a · Depends: C3 ·
  DoD: report reflects ratified plan and deferrals.

---

## 11. Estimated LOC

| Commit | Est. LOC |
|---|---|
| C0 | ~790 (docs) |
| C1 | ~180 |
| C2 | ~160 |
| C3 | ~200 |
| C4 | ~120 |
| **Total pipeline (C1–C4)** | **~660** |
| **Total incl. ratification (C0)** | **~790** |

Each commit <300 LOC; total pipeline LOC ≈ 660 over 4 commits.

---

## 12. Readiness table

Design-review-only; no code is written. **Process note:** the tree is on
`iteration/3-fact-layer` (HEAD `b1f4116`, clean); branch `iteration/4-verification`
does **not** exist and is required before any C-commit (AGENTS.md /
CONTRIBUTING.md). No commits are made in this review.

| Commit | Status | Blocked by |
|---|---|---|
| C0 | **Blocked** | Q1–Q10 ratification |
| C1 | **Blocked** | DN-25…DN-34 ratification (Q2, Q4, Q5, Q8, Q9) |
| C2 | **Blocked** | DN-25…DN-34 ratification (Q3, Q6, Q7, Q10) |
| C3 | **Blocked** | DN-25…DN-34 ratification (Q1), plus all of C1–C2 |
| C4 | **Blocked** | C3 |

**Overall: BLOCKED** pending ratification of Q1–Q10 (DN-25…DN-34). Highest-
leverage: Q9 (contradiction without RFC-0005 §8), Q8 (staleness boundary), Q5
(before/after surface), Q3 (store-write/Verified status). Nothing invented; all
reported to their owning documents.

---

# Consistency review against the Blueprint and governing RFCs

This review was checked against the blueprint, RFC-0000–0013, RFC-0021, the two
walkthroughs, the decision traceability matrix, and DN-1…DN-24.

**Consistent (passes):**

- **Module set.** `verification/{__init__,compare,outcome}.py` matches blueprint
  §2/§10 exactly; `test_packages.py:24` enforces it. No new module.
- **Dependency rules.** `verification` imports only `factlayer`/`schema`/
  `systemmodel` (+ stdlib); no forbidden edge; acyclic —
  `test_dependency_rules.py:24,67`.
- **Iteration scope and RFC basis.** Scope, work, DoD, and RFC basis are
  transcribed from blueprint §8.5.
- **Ownership.** Exactly one owner per artifact (§2); DN-4 (PostCondition type
  in `schema`, semantics here) honored.
- **Gate.** Iteration 4 produces the verification scaffold + conformance tests;
  production code begins only after RFC-0015/0019/0020 and the Drafts are
  Accepted (blueprint §8.0; RFC-0000 §5).
- **Decision notes.** DN-1 (in-memory types), DN-5 (eight Outcomes), DN-6 (no
  GoalOutcome) honored; the five-value wording is superseded by DN-5.
- **Walkthroughs.** Verification failure scenarios of the failure-injection
  walkthrough map to tests at `verification`; the core-execution Stage 10/13/14
  sequence is the integration oracle once `core` exists.

**Inconsistent / required attention (reported, not resolved):**

1. **Contradiction dependency on deferred RFC-0005 §8** (RFC-0006 §8 vs Iteration
   3's exclusion) — Q9.
2. **Collect/Normalize named in the RFC-0006 §6 process** but not in this
   package — Q1.
3. **§12 confidence and V11/V12 evidence records** have no home until the
   audit/context iterations — Q6/Q10.
4. **RFC-0006 header dependency-status claim** ("accepted in this series") is
   factually wrong for RFC-0005/0007/0008 — reported.
5. **Blueprint §8.5 basis (§5–§8) is narrower than its own DoD and §7 oracle**
   (V4/V10/V14 live in §13) — reported.

**Ownership conflicts found:** none beyond the reported Q6 (staleness) and Q9
(contradiction). **Circular dependencies found:** none. **Authority leaks
found:** none — `verification` holds Verify only (RFC-0004 §4.6). **Hidden
implementation decisions detected and surfaced:** Q1–Q10.

**Verdict.** The design review **passes as a translation**: it adds no
architecture, invents no behavior, respects the gate, and reports every
ambiguity to its owning document (blueprint §0, §11). Implementation of
Iteration 4 is **blocked** until Q1–Q10 are answered and recorded as decision
notes, exactly as Iterations 1–3 were ratified before implementation.
