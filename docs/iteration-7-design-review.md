# Iteration 7 — Design Review (Policy Layer)

> **Document type:** Implementation design review, at the same rigor as
> Iterations 2–6. **Not an RFC, not code.**
> **Read this first:** This document **defines no new architecture, modifies no
> RFC, invents no behavior, and writes no production code.** It translates the
> frozen corpus (RFC-0000–0013, RFC-0021, the decision traceability matrix,
> `docs/architecture-implementation-blueprint.md`, and the ratified
> `docs/implementation-decision-notes.md` DN-1…DN-44) into an implementation
> plan for the **Policy Layer — the `policy` package** (blueprint §8.7,
> re-ordered to Iteration 7 by DN-35/DN-40). Where the corpus does not decide
> something, this document **reports** it as an ambiguity or a question; it does
> not resolve it.
>
> **Status of sources.** RFC-0008 is **Draft** (not Accepted; dated 2026-08-02).
> Per RFC-0003 Part II §1.1 Draft RFCs are not normative and must not be relied
> upon by implementation; yet the blueprint (a translation, §0) targets the
> Drafts' *invariants* as the conformance oracle (blueprint §9 #2). Iteration 7
> inherits Iterations 1–6's posture: it conforms to RFC-0008's Draft wording
> knowingly, accepting the rework risk that a Draft change carries. Blueprint
> §8.0 gate stands — production code begins only after RFC-0015/0019/0020 and
> the Drafts are Accepted; this iteration builds the translation scaffold. The
> load-bearing dependencies this layer rests on — RFC-0001 §8.1–§8.12
> (principles 2 default-deny, 3 human-is-the-authorization-service, 5
> deterministic risk, 6 elevation, 12 fail-closed); RFC-0002 §6.2, §2.7, §4.7,
> §9 invariants 1, 6, 7, 10, 11, 12, 13, 15; RFC-0004 §4.7, §4.8, §7, §8
> (A2/A6/A8/A9/A10), §9.7; RFC-0007 §4.4, §5.1, T2 — are **Accepted**, which
> bounds the rework risk. RFC-0021 (the State-Domain vocabulary RFC-0008 §6
> cites) is Draft and its edge is kept **latent** here (Q3); RFC-0015 (override
> presentation), RFC-0019 (MVP), and RFC-0020 (policy *content*) are explicitly
> not built here (Q6/Q7).
>
> **Scope decision (reported — Q1).** DN-35/DN-40 re-ordered the build so that
> `policy` (blueprint §8.7) follows `secrets`, and the Iteration 6 closeout
> (`docs/implementation-consistency-report.md` §Readiness for Iteration 7)
> records that Iteration 7 is the `policy` package, with `executor` + `audit`
> following. Blueprint §8.7/§8.8 were never renumbered: §8.7 still reads
> "Iteration 6 — `policy`" and §8.8 "Iteration 7 — `executor` + `audit`". This
> task's scope implements `policy` at Iteration 7, which requires recorded
> supersession of the numbering before C0 (Q1). The re-order is
> dependency-safe — `secrets` (Layer 3) precedes `policy` (Layer 3), and
> `policy` still precedes `executor` + `audit` (Layer 4), preserving the safety
> spine (RFC-0000 §6 items 1, 3) and blueprint Risk #9's mitigation (the
> blast-radius RFCs' packages built first).

---

## 1. Architectural consistency review

### 1.1 Scope (blueprint §8.7, transcribed)

| Item | Value |
|---|---|
| Goal | The gate, before any execution |
| Work | Deterministic risk classification; gate table; Approval Token mint/validate; default-deny policy loading |
| Definition of Done | I-7 (never LLM self-report), I-11 (token scoped/consumable/invalidated), RFC-0001 §8.2 (default-deny) tests pass; P8/P9/P10/P13 conformance |
| RFC basis | RFC-0008 §6–§8, §10, §13; RFC-0002 §9; RFC-0001 §8 |

Blueprint §7 (test oracle) carries a `policy` row: "Classification deterministic,
never LLM self-report (I-7); token scoped/consumable/invalidated (I-11);
default-deny (RFC-0001 §8.2); blocked action only via audited override (I-12,
P10)" — oracle RFC-0008 §6–§8, §13; RFC-0002 §9. Blueprint §8.3's coverage
table adds the package's invariant suite: `policy/*` → RFC-0008 §6, §7, §8, §10;
P1–P14; RFC-0002 invariants 7, 11, 12, 13. Blueprint §5 exposes the package
contract: "Classify an Action into a risk class; return the gate; mint/validate
an Approval Token; apply Operator policy (default-deny)" — RFC-0008 §6, §7, §8;
P1–P14; RFC-0002 invariant 7.

**Layer-enforceable now vs. cross-component.** The §8.7 DoD conformance set is
P8/P9/P10/P13. The blueprint's *test* oracle is P1–P14. The layer can satisfy
the DoD set and most of the P set **at its own surface** (P2–P10, P13, P14) as
deterministic mechanics plus layer-boundary tests; the parts whose enforcement
points do not exist yet — P1 (the gate is the only path to *machine mutation*),
P11 (standing approvals as shipped policy), P12 (elevation *use*), and the
durable half of P13 (the Audit write) — are recorded as the owning packages'
DoD (RFC-0004 A2/§4.9 → `executor`; RFC-0013 → `audit`; RFC-0002 §6.2 → `core`),
mirroring how Iteration 5 made RFC-0002 invariants 4/5 testable at the
sanitize/containment layer and Iteration 6 made SC2–SC5 testable as
layer-boundary obligations (DN-43).

**Two faces, one engine.** RFC-0002 §6.2 and RFC-0008 §7 fix that the Approval
concern (risk classification) and the Policy concern (default-deny, elevation,
scope, standing approvals) are two faces of one deterministic engine, always
applied together at the same two edges. This layer implements the engine as a
single `policy` package; the two §6.2 consultation edges (Planning → Awaiting
Approval; Awaiting Approval → Executing; startup/reload; CONFIG_CHANGED) are
`core`'s to invoke, exactly as RFC-0002 §6.2's "Never consulted to design a plan
or to interpret evidence" prescribes.

### 1.2 Out of scope (recorded, not dropped)

Each of these is owned elsewhere and is **not** built in Iteration 7:

| Item | Owned by | Blueprint gate |
|---|---|---|
| The §6.2 consultation edges themselves (classify at Planning→Awaiting Approval; re-validate at Awaiting Approval→Executing; startup/reload; CONFIG_CHANGED) | RFC-0002 §6.2; `core`, Iteration 11 | RFC-0002 §6.2 |
| Independent executor-side token enforcement (Executor refuses anything not carrying a valid token) | RFC-0004 A2, §4.9; `executor`, Iteration 8 | RFC-0008 §10 |
| The durable Audit write for issuance/override/auto-permit/rejection records | RFC-0002 invariant 13; RFC-0013; `audit`, Iteration 8 | RFC-0008 §8, §13 P13 |
| The mandatory presentation content (§12) and override presentation form | RFC-0008 §12; RFC-0015 (future); `cli` | RFC-0008 §16 |
| The shipped policy *content* — default allowlist contents, standing-approval defaults, expiry windows, retry ceilings, the absolute-block list | RFC-0020 (future); RFC-0008 §16 | RFC-0008 §16 |
| Whether any block is hard-coded | RFC-0019 (MVP scope) | RFC-0008 §16 |
| The machine's elevation mechanism (sudo/polkit, revocation plumbing) | RFC-0021 §3.3; `executor.elevation`, Iteration 8 | RFC-0008 §3, §8 |
| Plan re-presentation after deviation/failure/partial execution | RFC-0002 §7, §2.8–§2.10; `core` | RFC-0008 §11 |
| The RFC-0021 §6 State-Domain diff used for state-change detection | RFC-0021 (Draft); runtime (`executor`/`core`) | RFC-0008 §9; Q3/Q4 |
| RFC-0008 §18 vocabulary additions to RFC-0003 (additive amendment) | RFC-0003 Part II amendment; on RFC-0008 acceptance | not this iteration |
| Signatures / package naming | RFC-0020 (future) | DN-1 |

### 1.3 What exists already

The `policy` package and its four modules were scaffolded in Iteration 0 with
ownership docstrings only (blueprint §2); `tests/test_packages.py` already
imports and docstring-checks them, so the tree test stays green throughout —
C1–C3 **fill** the stubs, they do not create modules. `tests/test_dependency_rules.py`
already declares `ALLOWED["policy"] = {"schema", "trust", "factlayer"}` and the
forbidden-source rows (no package may import `policy` except `skills`, `core`,
`cli` per blueprint §4.1/§4.2). Baseline suite: **1333 tests, green**, branch
`iteration/6-secrets`, HEAD `0b0ca07` (Iteration 6 closeout), working tree clean.

---

## 2. RFC consistency review

| RFC | Section | Implemented as | Status in layer |
|---|---|---|---|
| RFC-0008 | §0 Preamble, §1 Purpose | The constitutional sentence — *the human decides what changes the machine; the engine makes that decision meaningful, scoped, and honest* — as invariant tests (P1–P14) | Oracle (C4) |
| RFC-0008 | §4 Approval Philosophy | The six theses as testable properties: explicit (P5), contextual (P8/P9), revocable (P8), consumable (P7), never implies trust (P2 — approval confers no trust on the proposer) | Implemented (C1–C3) |
| RFC-0008 | §5 Approval Unit | The Action is the atomic approval unit; a command is never an approval unit; the Plan is the envelope unit | Implemented (C1/C3; consumes `schema.Action`/`Plan`/`Step`, Q2/Q10) |
| RFC-0008 | §6 Risk Classification | Four classes + four gates, deterministic, never the proposer's self-report (I-7); the meet rule for Plans; the read-only allowlist membership; the override distinction vs absolute block | Implemented (C1/C2); override semantics C3 (P10) |
| RFC-0008 | §7 Policy Engine | Three responsibilities (evaluation, decision, enforcement); default-deny and fail-closed (P3); the two faces applied together; the engine never loosens bounds | Implemented (C2; enforcement edges recorded as `core`'s, §1.2) |
| RFC-0008 | §8 Approval Tokens | Creation on classification + explicit decision; ownership (Operator issues, engine administers); scope; lifetime/expiry; invalidation; single-use; retries; standing approvals (P11); elevation (P12) | Implemented (C3); standing-approval/elevation mechanics per Q8/Q9 |
| RFC-0008 | §9 Preconditions | The three families re-checked at the execution boundary (assumptions/staleness, state, identity) | Implemented (C3, the deterministic re-validation function; boundary enforcement is `executor`/`core`'s, Q4) |
| RFC-0008 | §10 TOCTOU | Four layers: binding, boundary re-validation, independent enforcement, consumption/invalidation | Implemented (C3); independent enforcement = `executor`, Iteration 8 |
| RFC-0008 | §11 Plan Approval | Envelope = one judgment over a fully shown, ordered, classified set; meet class shown; deviations void the envelope | Boundary (C1/C3: meet rule + envelope-scoped token); re-presentation is `core`'s (§1.2) |
| RFC-0008 | §12 Human Interaction | Six mandatory elements + three presentation rules; nothing approved by silence (P5); friction proportional to risk | Contract (C3: the decision-input surface and mint guards); rendering is `cli`/RFC-0015 |
| RFC-0008 | §13 Approval Invariants P1–P14 | Conformance oracle — layer-enforceable subset enumerated in §8 below | Oracle (C4) |
| RFC-0008 | §15 Failure Behaviour | Approval expires / policy unavailable / gate unreachable → deterministic, disclosed, fail-closed outcomes | Implemented (C3/C4); full failure ordering at `core`, Iteration 11 |
| RFC-0008 | §16 Open Questions | Shipped policy content → RFC-0020; absolute-block list → RFC-0020; override presentation → RFC-0015; hard-coded block → RFC-0019; attended mechanics → RFC-0014 | Recorded (C5); Q6/Q7 |
| RFC-0008 | §18 New Terms | Approval Unit, Approval Gate, Plan Envelope, Standing Approval, Read-Only Allowlist, Override, Elevation, Precondition — flagged for RFC-0003 Part I | Recorded (C5); amendment on acceptance |
| RFC-0002 | §2.7 Awaiting Approval | Every action classified and audited, including auto-permitted; blocked still enters the state; state change invalidates | Boundary (C3/C4); state transitions are `core`'s |
| RFC-0002 | §6.2 Approval & Policy Engine | Consulted at the two edges + startup/reload + CONFIG_CHANGED; never to design a plan or interpret evidence | Boundary (C4); invocation at `core`, Iteration 11 |
| RFC-0002 | §4.7 CONFIG_CHANGED | Outstanding approvals re-validated against the new policy | Implemented (C3: revalidate-on-reload, P14) |
| RFC-0002 | §9 invariants 1, 6, 7, 10, 11, 12, 13, 15 | Gate-only path (P1); scoped-to-shown (P6); deterministic never self-report (I-7); freshness (P9); token scoped/consumable (I-11); audited override (I-12); record-before-consequence (I-13); no standing authorization across boundary (I-15) | Implemented (C1–C4); runtime enforcement at `core` |
| RFC-0001 | §5 Approval & Policy Engine | Deterministic classification; gate per class; default-deny and least-privilege for elevation; "the part that must never be surprised" | Implemented (C1–C3) |
| RFC-0001 | §8.1–§8.12 | Principle 2 default-deny (DoD), 3 human-is-authz (P5/P11), 5 deterministic risk (I-7), 6 elevation (P12), 12 fail-closed (P3) | Implemented (C1–C4) |
| RFC-0004 | §4.7 Policy Engine | Classify; apply default-deny/allowlists/elevation limits/standing-approval bounds; fail closed; Refuse + procedural Propose only | Implemented (C1/C2) |
| RFC-0004 | §4.8 Approval Engine | Present/capture the decision; mint the token; re-validate at the gate; invalidate on boundary events; the Operator's instrument only | Implemented (C3) |
| RFC-0004 | §7 matrix (C9, C10, C11, C12, C13; F cells) | Policy Engine: Refuse A, Propose C9, Explain C10; Approval Engine: Approve C11 (instrument), Refuse C12, Explain C13; never Approve/Execute/Observe | Implemented (C1–C4, structural) |
| RFC-0004 | §8 A2, A6, A8, A9, A10 | Executor never invents (A2); Policy never executes (A6); authority flows downward (A8); gate is the only path (A9); recorded before spent (A10) | Boundary (C3/C4); A2 at `executor`, Iteration 8 |
| RFC-0004 | §9.7 Policy Engine abuse | A malicious/loosened Policy still cannot bypass the Operator's Approval or the Executor's token validation; reloads invalidate; fail closed (A6) | Implemented (C3/C4: token independent of policy loosening; reload invalidation) |
| RFC-0007 | §4.4, T2 | Classification reads structured Action descriptions and Facts, never raw untrusted text; the gate decided before presentation (P4) | Implemented (C1/C4) |
| RFC-0007 | §5.1 meet | A Plan's class is the meet of its Steps' classes — the most restrictive among them | Implemented (C1, Q10) |
| RFC-0021 | §6 State Domains | The vocabulary (packages, services, configuration, network, users, storage, security state) that risk-relevant Action properties describe | Latent (Q3); `systemmodel` edge unauthorized and unused (DN-9/DN-37 precedent) |
| RFC-0009 | §22 SC9, SC10 (via DN-43) | No Action carries a secret (boundary test at `policy`); elevation never exposes secrets (`executor`) | Boundary (C4, SC9 at this layer; SC10 at `executor`, Iteration 8) |

**Already resolved by the corpus (not re-opened here):**

- The **gate set is closed**: exactly auto-permitted, confirm, confirm-with-warning,
  blocked (RFC-0008 §6; RFC-0000/RFC-0002/RFC-0004 name the same four). Not a
  question.
- **The class is never the proposer's self-report**; a class is a membership
  test over deterministic properties; no percentage, probability, or score
  (RFC-0008 §6; RFC-0002 invariant 7; RFC-0001 §8.5). Not a question.
- **Default deny and fail closed**: an unclassified, unparseable, or unknown
  Action is blocked and disclosed, never auto-permitted (RFC-0008 §7, §13 P3;
  RFC-0001 §8.2, §8.12; RFC-0004 §9.7). Not a question.
- **Nothing proceeds on silence**; no timeout yields a "yes" (RFC-0008 §4, §13
  P5; RFC-0001 §8.3; RFC-0002 §2.7). Not a question.
- **Tokens are single-use, expiring, and invalidated by any boundary** — state
  change, interrupt, reboot, session restart, policy reload, revocation; never
  resurrected (RFC-0008 §8, §13 P7/P8; RFC-0002 invariants 11, 15). Not a
  question.
- **Approval is scoped to what was shown**; any deviation is a fresh approval
  (RFC-0008 §13 P6; RFC-0002 invariant 6). Not a question.
- **The override is an explicit, warned, recorded, scoped decision**, never a
  habit-forming default; an absolute block is Policy content (RFC-0008 §6, §13
  P10; RFC-0002 invariant 12). Not a question.
- **The Operator owns the machine; only the Operator approves**; the engine is
  the instrument, never the decision-maker (RFC-0004 §4.8, C11). Not a
  question.
- **Elevation is at least Consequential**, explicit, per-action, scoped, and
  revoked; the *mechanism* is the machine's own (RFC-0008 §8, §13 P12; RFC-0001
  §8.6). Not a question.
- **The engine never loosens bounds on its own** (RFC-0008 §7; RFC-0004 §9.7).
  Not a question.
- **Auto-permission is per-Action, never a reusable pass** (RFC-0008 §8; RFC-0001
  §8.3). Not a question.

---

## 3. Layer placement

`policy` sits at **Layer 3** (blueprint §4.1), beside `secrets`. Its imports
reach only downward to Layers 0–2 (`schema`, `trust`, `factlayer`); nothing at
Layers 0–2 may import it. `factlayer` (Layer 2) is the one upward-reachable edge
the engine legitimately consumes: classification and precondition re-validation
read Facts (RFC-0008 §6, §9). Its future consumers are `skills` (Layer 5, SK4:
its Actions pass the gate — allowed), `core` (Layer 6, the conductor that invokes
the §6.2 edges), and `cli` (Layer 7, renders decisions — allowed), plus `audit`
and `context` (Layer 4) only through the qualifiers in blueprint §4.2 (`audit`
imports `policy`; `context` does **not** — "the gate consumes Facts, never
Context", RFC-0008 §2). `executor` (Layer 4) must **not** import `policy`
(blueprint §4.2): independent token enforcement is the Executor's own check
(RFC-0004 A2; RFC-0008 §10), and the token is the handoff value, not a call.

`secrets` is a Layer-3 sibling, not a dependency: no `policy → secrets` edge
exists. The SC9 "no Action carries a secret" boundary (DN-43) is satisfied here
by construction — the engine's inputs are the structured `schema.Action`
description and `schema.Fact`s, never raw text (RFC-0007 T2) — and is asserted
as a boundary test (C4).

---

## 4. Ownership map

`policy` is owned by **RFC-0008** — one owner per row, no delegation (RFC-0004
§3; blueprint §10). Module-level ownership:

| Module | Owning RFC sections | Protected by |
|---|---|---|
| `policy/classify.py` | RFC-0008 §6 | P2 (deterministic, never self-report; I-7), P4 (gate carried, never re-derived); RFC-0001 §8.5 |
| `policy/gates.py` | RFC-0008 §6, §7 | P4 (gate per class fixed before presentation); RFC-0004 C9 (procedural Propose only) |
| `policy/tokens.py` | RFC-0008 §8, §10 | I-11 (scoped/consumable/invalidated), P5–P10, P13, P14; RFC-0004 §4.8 (C11 instrument), §8 A6 |
| `policy/policy.py` | RFC-0008 §7 | P3 (default-deny, fail-closed); RFC-0001 §8.2, §8.12; RFC-0004 §4.7 |

**Two-owner checks.** (a) *Classification vs. trust:* the risk-class meet
(RFC-0008 §6) and the trust-lattice meet (RFC-0007 §5.1) share a word but are
distinct lattices over distinct objects (Actions vs. information), never merged;
`trust` answers "how trustworthy is this datum?", `policy` answers "what is the
gate for this Action?" — the precedent is Iteration 6's Q5 split. (b)
*Classification vs. presentation:* the gate is the engine's (P4); the *form* of
the override and its warning belongs to RFC-0015 (RFC-0008 §16) — `policy`
produces the decision and its grounds, never a rendering. (c) *Policy vs.
Approval engine:* RFC-0004 §4.7 and §4.8 are two actors with two matrix rows; in
one package the split is module-level — `classify`/`gates`/`policy` are the
Policy Engine (Refuse A, Propose C9, Explain C10), `tokens` is the Approval
Engine face (Approve C11 as the Operator's instrument, Refuse C12, Explain C13).
`tokens` must never decide whether to approve (RFC-0004 §4.8 "May never decide:
whether to approve") — minting is driven by an explicit decision *input* (Q5).

**Authority boundaries.** This layer holds Refuse and procedural Propose only
(RFC-0004 §4.7): it never Approves, never Executes, never Observes (A6), and
never decides policy content — the Operator sets Policy bounds within their
authority (RFC-0004 §3). It holds no authority over values' *use* (no secret
surface); its token records are metadata only (RFC-0009 SC4 boundary, DN-43).

---

## 5. Dependency analysis

**Allowed** (blueprint §4.1; already enforced by `tests/test_dependency_rules.py`):

| Edge | Why allowed |
|---|---|
| `policy → schema` | The Action/Plan/Step are the approval units (RFC-0008 §5); the structured description and `risk_properties` are the classification input (§6) |
| `policy → trust` | Classification never reads raw untrusted text (RFC-0007 T2); the engine operates within the trusted/untrusted frame (RFC-0007 §4.4); the meet-rule precedent (§5.1) |
| `policy → factlayer` | Consumes Facts for classification and preconditions (RFC-0008 §6, §9); the engine never reads the machine itself (RFC-0002 §6.2: only Diagnostics reads the machine) |

**Forbidden** (blueprint §4.2): `systemmodel`, `collectors`, `verification`,
`secrets`, `executor`, `audit`, `context`, `providers`, `skills`, `core`, `cli`.
Notably: no `systemmodel` edge (the State-Domain vocabulary stays latent — Q3);
no `verification` edge (the engine never verifies — RFC-0004 A6, the Policy
Engine has no Observe); no `audit` edge (records are in-memory metadata here,
the durable write is `audit`'s — Q6); no `secrets` edge (SC9 by construction).

**Latent edges.** `systemmodel` (Q3) is the declared-but-unused case, mirroring
DN-9/DN-37/DN-44: the vocabulary is referenced by canonical *names* carried on
`schema.Action.risk_properties` ("Canonical risk-relevant property names
(RFC-0008 §6)"), and the name→State-Domain semantics is owned elsewhere (RFC-0021,
Draft) and left unused. The conformance test must allow this edge to be absent
while the architecture declares it permitted for other packages.

---

## 6. Public surface analysis

The planned public surface is **reported**, not ratified; final signatures are
RFC-0020's (DN-1). The shape below is what C1–C3 will build. The package is
value-free and import-safe beyond its own surface (no I/O, no forbidden stdlib),
mirroring the `secrets`/`trust` precedent.

`policy/classify.py`

- `RiskClass` enum with exactly the four §6 classes — **Read-only (Inspection),
  Benign, Consequential, Destructive** (RFC-0008 §6 table; RFC-0001 §5).
- `Gate` enum with exactly the four gates — **auto-permitted, confirm,
  confirm-with-warning, blocked** (RFC-0008 §6; the §6 "silent/notify" words are
  presentation faces of auto-permitted, owned by `cli`/RFC-0015).
- A classification result record: risk class + gate + warning grounds
  (confirm-with-warning) or reason (blocked) + the deterministic inputs it was
  computed from. The gate is a **carried field** of the result, never re-derived
  (P4).
- The deterministic classifier entry operating on the Action's structured
  description and its referenced Facts (exact input type per Q2), the §6
  membership test over the canonical risk-property vocabulary (Q3), and the
  **meet rule** for Plans — a Plan's class is the most restrictive of its Steps'
  classes (RFC-0008 §6; RFC-0007 §5.1; Q10).
- Fail-closed: unclassifiable, unknown property, or classification error →
  **blocked** with reason (P3; RFC-0001 §8.12).

`policy/gates.py`

- The §6 class→gate table as data, transcribed exactly: Read-only →
  auto-permitted iff allowlisted else confirm; Benign → confirm;
  Consequential → confirm-with-warning; Destructive → blocked (RFC-0008 §6).
- The gate-lookup entry (class, allowlist membership, override) → gate;
  deterministic, never the proposer's words (P2/P4).

`policy/tokens.py`

- The Approval Token record: the approved Action's identity, its class and gate,
  the machine-state snapshot it was approved against (Q4), elevation bounds if
  any (Q9), the identity of the session that produced it (RFC-0008 §8 scope
  list), an expiry fixed per risk class, a consumed flag, and — for a plan
  envelope — the set of Steps as presented (Q10).
- `mint`: requires (a) a prior classification and (b) an **explicit decision
  input** — approve, auto-permit (allowlisted read-only), or override (blocked) —
  and refuses on silence/rejection (P5; Q5). Override requires the Action be
  Blocked and records an override (P10). Nothing else mints (A6; RFC-0004 C11).
- `validate`/`revalidate`: the deterministic boundary re-validation — token
  valid/consumed/expired; Action-identity match (P6/P9 §9.3); referenced-Fact
  staleness via `factlayer` (P9 §9.1); machine-state snapshot consistency (P9
  §9.2; Q4); policy-reload and state-change invalidation (P14). Any uncertainty
  → refused (fail closed, RFC-0008 §9; RFC-0002 §2.8).
- Invalidation: single-use consumption (P7), the boundary events (state change,
  interrupt, reboot, session restart, policy reload, revocation) (P8, I-15),
  never resurrected (P8).
- Records: issuance/override/auto-permit/rejection as in-memory metadata
  records (Q6; DN-34/DN-41 precedent), so that P13/I-13 is satisfiable as a
  layer-boundary test now and the durable Audit write is `audit`'s.

`policy/policy.py`

- The Operator-owned, default-deny policy *mechanism*: the deterministic rule
  set (the class→gate table, elevation bounds, standing-approval bounds, retry
  ceilings per class), a structural default-deny rule (no match → blocked, P3),
  the read-only-allowlist membership function (empty by default; contents are
  RFC-0020's), and a policy-`load` that fails closed on unparseable rules (P3,
  RFC-0001 §8.12). The shipped *contents* are RFC-0020's (Q7).

Nothing else is exported. The facade re-exports only the owned vocabulary
(blueprint §3), and the public surface carries no secret-bearing artifact and no
execution path (A6).

---

## 7. Boundary analysis

- **Upstream of the Executor.** The gate is decided before the Executor exists
  (RFC-0008 §7; RFC-0004 §4.9: the Executor may decide only *how*, never
  *what*). The handoff to execution is the token, and the Executor independently
  refuses anything not carrying a valid, unexpired, state-consistent token
  without importing `policy` (RFC-0004 A2; RFC-0008 §10) — an Iteration 8
  obligation recorded here (Q5/§1.2).
- **The §6.2 consultation edges are `core`'s.** RFC-0002 §6.2 fixes *when* the
  engine is consulted; the layer provides the classify/re-validate functions and
  the revalidate-on-reload entry (P14), `core` (Iteration 11) invokes them. The
  layer is never consulted to design a plan or interpret evidence.
- **Presentation is `cli`/RFC-0015.** The layer produces the class, gate, and
  grounds; it never renders, and the presented gate must equal the engine's
  decision (P4; RFC-0008 §12, §16).
- **The Audit is Iteration 8.** Records are in-memory metadata now (Q6); the
  durable, record-before-consequence write (I-13/A10, P13) is `audit`'s. A
  consequence never proceeds unrecorded or unpresented (RFC-0008 §15 "the gate
  cannot be reached") — this layer's boundary test proves no path from mint to a
  spendable token without a prior issuance record.
- **Facts, never raw text.** Classification reads the Action's structured
  description and Facts (RFC-0007 T2; RFC-0008 §7). The SC9 "no Action carries a
  secret" boundary (DN-43) is asserted as: the classify entry accepts only
  structured types, and no secret-shaped value can be smuggled through it
  (RFC-0009 §22).
- **The `systemmodel`/State-Domain boundary.** The vocabulary is referenced by
  canonical names only; the State-Domain diff that detects machine-state change
  is RFC-0021's (Draft) and the runtime's, not this layer's (Q3/Q4).

---

## 8. Required invariants

Each P invariant's normative source, whether the layer can make it hold at its
own surface now, and where the remainder is enforced (mirroring the
layer-boundary precedent of Iterations 5–6).

| Invariant | Normative source | Layer-enforceable now | Enforcement point for the rest |
|---|---|---|---|
| P1 — the gate is the only path to machine mutation | RFC-0008 §13; RFC-0002 I-1; RFC-0004 A9 | Structural (mint is the only path to a spendable token); the *execution* half is not | `executor` (A2), `audit` (I-13), `core` (state machine), Iteration 8/11 |
| P2 — deterministic, never self-report | RFC-0008 §13; RFC-0002 I-7; RFC-0001 §8.5 | **Yes** (C1: membership test, no proposer words/scores) | — |
| P3 — default deny, fail closed | RFC-0008 §13; RFC-0001 §8.2, §8.12; RFC-0004 §9.7 | **Yes** (C1/C2: unknown/unparseable → blocked) | — |
| P4 — classification precedes presentation, never re-derived | RFC-0008 §13; RFC-0007 §4.4 | **Yes** (C1/C2: gate is a carried field; presented gate == engine's) | `cli` rendering, RFC-0015 |
| P5 — explicit decision, nothing on silence | RFC-0008 §13; RFC-0001 §8.3 | **Yes** (C3: mint requires a decision input; no decision → no token) | `cli` collection, RFC-0015 |
| P6 — scoped to what was shown | RFC-0008 §13; RFC-0002 I-6 | **Yes** (C3: Action-identity binding; deviation fails re-validation) | — |
| P7 — single-use, never reused | RFC-0008 §13; RFC-0002 I-11 | **Yes** (C3: consumed/expired dead; replay refused) | — |
| P8 — bound to action/time/state, invalidated by any boundary | RFC-0008 §13; RFC-0002 I-11, I-15 | **Yes** (C3: expiry per class; invalidation on boundary events; never resurrected) | runtime boundary events via `core` |
| P9 — preconditions re-validated at the execution boundary | RFC-0008 §13; RFC-0002 §2.8 | **Yes, as the deterministic re-validation function** (C3: identity + freshness + state); the *boundary* is `executor`/`core` | `executor`, Iteration 8 |
| P10 — blocked only by explicit, audited override | RFC-0008 §13; RFC-0002 I-12; RFC-0004 A10 | **Yes** (C3: override decision input, override-scoped token, in-memory override record); durable audit write | `audit`, Iteration 8 |
| P11 — standing approvals scoped/bounded/expiring, never blanket | RFC-0008 §13; RFC-0001 §8.3 | Per Q8: representation + evaluation mechanism at C2/C3; shipped defaults are RFC-0020's | RFC-0020; `audit` visibility |
| P12 — elevation explicit/per-action/scoped/revoked | RFC-0008 §13; RFC-0001 §8.6 | Per Q9: elevated → at least Consequential; elevation bounds on the token; the *mechanism* and revocation | `executor.elevation`, Iteration 8 |
| P13 — recorded before spent | RFC-0008 §13; RFC-0002 I-13; RFC-0004 A10 | **Yes, as layer-boundary records** (C3: in-memory issuance records precede a spendable token); durable write | `audit`, Iteration 8 |
| P14 — reload/state change re-validates outstanding | RFC-0008 §13; RFC-0002 §4.7, I-15 | **Yes** (C3: revalidate-on-reload/state-change; nothing approved under older policy runs without re-check) | `core` CONFIG_CHANGED wiring |

DoD subset (blueprint §8.7): **I-7, I-11, RFC-0001 §8.2, P8/P9/P10/P13** — all
layer-enforceable per the table. The package's blueprint §8.3 oracle (P1–P14;
RFC-0002 invariants 7, 11, 12, 13) is satisfied across the layer + the recorded
cross-component obligations (§1.2).

---

## 9. Ambiguities

Each is **reported, not resolved** here; each names the corpus silence that
forces the report and the RFC/decision that owns the answer. Column "Blocking?"
marks whether it elevates to a blocking question in §10.

| # | Subject scope | RFC §/location | Open question | Alternative readings | Governing RFC / note | Blocking? |
|---|---|---|---|---|---|---|
| A1 | Iteration identity / numbering | blueprint §8.7 ("Iteration 6 — `policy`"), §8.8 ("Iteration 7 — `executor` + `audit`"); DN-40 | Blueprint §8.7/§8.8 were never renumbered; DN-40 says `policy` shifts "to the following iteration" and the Iteration 6 closeout labels it Iteration 7. How is the renumbering recorded (supersession note vs blueprint edit), and what are the subsequent numeric labels (executor+audit, context, providers+skills, core)? | (a) Iteration 7 = `policy`, renumbering recorded as a reported tension, blueprint text stands until RFC-0020; (b) stop and amend the blueprint | DN-40; blueprint §8.7/§8.8; consistency report §Readiness for Iteration 7 | **Yes (Q1)** |
| A2 | `classify` input type | RFC-0008 §5, §6 | Classification reads "the Action's structured description and the Facts it is built on". Does the entry consume `schema.Action` (+ referenced Facts), an internal abstract input (DN-37/DN-44 precedent), or a bare description? And which Facts are "referenced" — Step preconditions, PostCondition subjects, or a passed-in Fact set? | (a) `schema.Action` + a referenced-Fact set (the Action is the approval unit; the `schema` edge is declared and natural); (b) internal abstract input, `schema` edge latent | RFC-0008 §5/§6; DN-37, DN-44; blueprint §4.1 | **Yes (Q2)** |
| A3 | Risk-property / State-Domain vocabulary | RFC-0008 §6; RFC-0021 §6 | §6 says the class is read "using RFC-0021 §6's State Domains as the vocabulary" — packages, services, configuration, network, users, storage, security state, elevation. But `policy` may not import `systemmodel` (Layer 3 allowed = schema/trust/factlayer), and `schema.Action.risk_properties` carries only canonical *names* (`tuple[str, ...]`, docstring "Canonical risk-relevant property names (RFC-0008 §6)"). Where does the name→semantics registry live, and is the State-Domain mapping latent? | (a) internal canonical risk-property vocabulary in `classify.py`, the `systemmodel` edge latent (DN-9/DN-37/DN-44 pattern); (b) bind to `systemmodel` types (requires a new, forbidden edge) | RFC-0008 §6, §3 (non-scope → RFC-0021); DN-9, DN-37, DN-44; blueprint §4.1 | **Yes (Q3)** |
| A4 | Machine-state snapshot representation | RFC-0008 §8, §9, §10 | A token is bound to "the Machine State it was approved against"; re-validation compares "State Domains the Action touches against the snapshot". RFC-0021 (the State-Domain vocabulary) is Draft and its diffing is runtime-owned. What is the snapshot on a token now, and how does the layer detect "state changed" without importing RFC-0021? | (a) an opaque in-memory snapshot reference (identity + the Facts it was approved against); re-validation checks factlayer freshness + Action identity, and treats a runtime-supplied state-change signal as invalidation (P8/P9/P14); (b) build a State-Domain compare now (needs the forbidden edge + Draft vocabulary) | RFC-0008 §8/§9/§10; RFC-0021 (Draft) §6; RFC-0002 I-11 | **Yes (Q4)** |
| A5 | Decision-input abstraction | RFC-0008 §8; RFC-0004 §4.8 | Minting requires an explicit Operator decision (approve / auto-permit / override), but there is no `core`, no `cli`, and no Audit in this iteration. Does the layer define the decision-input type (approve/auto-permit/override/reject) that `mint` requires — making P5/P10 testable — and how does an unanswered request behave? | (a) `mint` requires a decision input enum; rejection/no-input mints nothing and consumes nothing (P5); override allowed only for Blocked and records an override (P10); (b) defer minting until `core`/`cli` exist (would make P5/P10 untestable this iteration) | RFC-0008 §8/§13 P5/P10; RFC-0004 §4.8 (C11), A6; RFC-0002 §2.7 | **Yes (Q5)** |
| A6 | P13/I-13 records without the Audit package | RFC-0008 §8, §13 P13; RFC-0002 I-13 | "Issuance is written to the Audit before execution may proceed." `audit` is Iteration 8. How is P13/I-13 satisfied at the policy layer now? | (a) in-memory issuance/override/auto-permit/rejection metadata records + a layer-boundary test that no token is spendable without a prior record; the durable write is `audit`'s DoD (DN-43 pattern); (b) declare P13 deferred wholesale | RFC-0008 §8/§13; RFC-0002 I-13; RFC-0004 A10; DN-34, DN-41, DN-43 | **Yes (Q6)** |
| A7 | Default-deny policy loading: mechanism vs content | blueprint §8.7 (work: "default-deny policy loading"); RFC-0008 §7, §16 | The blueprint's work item and `policy.py` ("Operator-owned policy (default-deny)") vs RFC-0008 §16, which defers the *specific default contents* (allowlist contents, standing-approval defaults, expiry windows, retry ceilings, absolute-block list) to RFC-0020. What does "policy loading" build now? | (a) the deterministic policy *mechanism* — the rule set, default-deny structural rule, allowlist membership function (empty by default), elevation bounds, retry ceilings, a fail-closed `load`; contents RFC-0020's; (b) an interface-only stub, all mechanics deferred | blueprint §8.7; RFC-0008 §7, §16; RFC-0004 §4.7 | **Yes (Q7)** |
| A8 | Standing approvals in scope | RFC-0008 §7, §8, §13 P11 | §7 lists "whether a standing approval applies and is in scope and unexpired" as Policy evaluation; §8 defines the construct; but P11 is not in the §8.7 DoD and RFC-0008 §16 defers standing-approval *defaults* to RFC-0020. Is the standing-approval construct (scope/ceiling/expiry) part of this iteration's mechanism, or deferred? | (a) representation + evaluation mechanism at C2/C3 (P11 testable), no shipped defaults; (b) deferred wholesale to RFC-0020/RFC-0016 | RFC-0008 §7/§8/§13 P11; RFC-0001 §8.3; RFC-0020 | **Yes (Q8)** |
| A9 | Elevation representation | RFC-0008 §8; RFC-0001 §8.6 | Tokens carry "elevation bounds (if any)"; an elevated Action is at least Consequential. P12 is not in the DoD, the mechanism is the machine's own (RFC-0021 §3.3), and `executor.elevation` is Iteration 8. Does the token carry elevation bounds and does classification enforce at-least-Consequential now? | (a) yes — a risk-property "elevation" makes the class at least Consequential and the token records bounds; the mechanism/revocation is `executor`'s (P12 deferred); (b) no elevation surface until `executor` | RFC-0008 §8/§13 P12; RFC-0001 §8.6; RFC-0021 §3.3 | **Yes (Q9)** |
| A10 | Plan envelope scope | RFC-0008 §6, §8, §11 | §6's meet rule and §8's "for a plan envelope — the set of Steps as presented" vs §11's full envelope approval + deviation rules and the fact that the DoD names no plan item. Does the layer implement Plan classification (meet rule) and an envelope-scoped token, or defer? | (a) meet rule at C1 + envelope-scoped token at C3 (the presented Step set); plan re-presentation after deviation is `core`'s (RFC-0002 §7); (b) defer plans entirely to `core` | RFC-0008 §6/§8/§11; RFC-0002 §7; schema.Plan/Step (Iteration 1) | **Yes (Q10)** |
| A11 | Retry ceiling | RFC-0008 §8 | Retries are bounded "by Policy per risk class"; a state-changing retry is re-presented. Is the per-class retry ceiling part of the policy mechanism (C2/C3), or RFC-0020 content? | (a) a per-class retry-ceiling field in the policy mechanism + re-presentation rule (token consumed → no auto-retry), values RFC-0020's; (b) deferred with the other content | RFC-0008 §8, §16; RFC-0002 Q2 | **Part of Q7** |

---

## 10. Blocking questions

| Q | Question | Owner (RFC §) | Blocks | Sev. | Recommended resolution |
|---|---|---|---|---|---|
| Q1 | Iteration identity / renumbering (A1) | blueprint §8.7/§8.8; DN-40 | all commits | Low | **Proceed as `policy` = Iteration 7**; record the supersession in this review + consistency report, leave the blueprint text until RFC-0020 (mirrors DN-40) |
| Q2 | `classify` input: `schema.Action` + referenced Facts vs internal abstract input (A2) | RFC-0008 §5/§6; DN-37, DN-44 | C1 | High | **`schema.Action` + a referenced-Fact set** — the Action is the approval unit and the `schema` edge is declared; referenced Facts = the Facts passed at the entry (Step preconditions are `core`'s view) |
| Q3 | Risk-property / State-Domain vocabulary without a `systemmodel` edge (A3) | RFC-0008 §6, §3; RFC-0021 (Draft); DN-9, DN-37, DN-44 | C1 | High | **Internal canonical risk-property vocabulary in `classify.py`** (mutates-a-domain / reads-a-domain, subsystems touched, elevation, reversibility, boot/auth), `systemmodel` edge latent; the name→State-Domain mapping is RFC-0021's on acceptance |
| Q4 | Machine-state snapshot + state-change detection (A4) | RFC-0008 §8/§9/§10; RFC-0021 (Draft); RFC-0002 I-11 | C3 | High | **Opaque in-memory snapshot reference** (identity + the Facts it was approved against); re-validation = Action identity + `factlayer` freshness + a runtime-supplied state-change signal; the State-Domain diff is RFC-0021's/runtime's |
| Q5 | Decision-input abstraction for `mint` (A5) | RFC-0008 §8/§13 P5/P10; RFC-0004 §4.8 | C3 | High | **`mint` requires an explicit decision input** (approve/auto-permit/override/reject); no input or rejection mints nothing and consumes nothing (P5); override allowed only for Blocked and records an override (P10) |
| Q6 | P13/I-13 records at the layer (A6) | RFC-0008 §8/§13; RFC-0002 I-13; DN-34, DN-41, DN-43 | C3 | Med | **In-memory issuance/override/auto-permit/rejection records + layer-boundary test** that no token is spendable without a prior record; the durable write is `audit`'s DoD |
| Q7 | Policy-loading scope: mechanism vs RFC-0020 content (A7) | blueprint §8.7; RFC-0008 §7/§16 | C2 | High | **Mechanism now** — default-deny rule set, allowlist membership (empty by default), elevation bounds, retry ceilings, fail-closed `load`; the shipped contents and expiry/absolute-block values are RFC-0020's |
| Q8 | Standing approvals: construct in scope vs deferred (A8) | RFC-0008 §7/§8/§13 P11; RFC-0001 §8.3 | C2/C3 | Med | **Representation + evaluation mechanism** (scope/ceiling/expiry; never covers a Blocked Action; never raises a ceiling) so P11 is testable; no shipped defaults (RFC-0020's) |
| Q9 | Elevation: bounds on the token, at-least-Consequential (A9) | RFC-0008 §8/§13 P12; RFC-0001 §8.6 | C1/C3 | Med | **Yes** — an elevation risk-property makes the class at least Consequential and the token records bounds; the mechanism/revocation is `executor.elevation`'s (P12) |
| Q10 | Plan envelope: meet rule + envelope token (A10) | RFC-0008 §6/§8/§11; RFC-0002 §7 | C1/C3 | Med | **Meet rule at C1 + envelope-scoped token at C3** (the presented Step set); deviation/failure re-presentation is `core`'s |

**Status: Ratified.** Q1–Q10 were ratified by the Operator (2026-08-06) and
recorded as **DN-45…DN-54** in `docs/implementation-decision-notes.md` before
C0. Each recommended resolution was adopted as a decision note; the design
review §16 readiness flips to READY.

---

## 11. Proposed Decision Notes (DN-45…DN-54)

Proposals for Operator ratification; none took effect by this review. **Ratified
as DN-45…DN-54 in `docs/implementation-decision-notes.md`** in the established
table form — Status (Ratified, Operator, Iteration 7 ratification) / Date
(2026-08-06) / Resolves (design review §10 Qn) / Grounding (RFC sections + DN
precedents) / Embodied in (commit) / Decision — mirroring DN-40…DN-44.

| DN | Resolves | Proposal |
|---|---|---|
| DN-45 | Q1 | Iteration 7 = `policy` only; blueprint §8.7/§8.8 numbering superseded by DN-35/DN-40's re-order (`executor`+`audit` → Iteration 8); blueprint text stands until RFC-0020 |
| DN-46 | Q2 | `classify` consumes `schema.Action` + a referenced-Fact set; the `schema` edge is exercised; referenced Facts = the Facts passed at the entry |
| DN-47 | Q3 | Internal canonical risk-property vocabulary in `classify.py`; the `systemmodel`/State-Domain edge stays latent (DN-9/DN-37/DN-44 pattern) |
| DN-48 | Q4 | Token carries an opaque in-memory machine-state snapshot reference (identity + Facts); re-validation = Action identity + `factlayer` freshness + runtime-supplied state-change signal; the State-Domain diff is RFC-0021's/runtime's |
| DN-49 | Q5 | `mint` requires an explicit decision input (approve/auto-permit/override/reject); no input/rejection mints nothing (P5); override only for Blocked and recorded (P10) |
| DN-50 | Q6 | P13/I-13 as in-memory issuance/override/auto-permit/rejection records + layer-boundary test now; the durable Audit write is `audit`'s DoD (DN-43 pattern) |
| DN-51 | Q7 | Default-deny policy-loading mechanism now (rule set, allowlist membership empty-by-default, elevation bounds, retry ceilings, fail-closed `load`); shipped contents RFC-0020's |
| DN-52 | Q8 | Standing-approval representation + evaluation mechanism (scope/ceiling/expiry, never covers Blocked, never raises a ceiling); no shipped defaults |
| DN-53 | Q9 | Elevation risk-property → at least Consequential; token records elevation bounds; mechanism/revocation deferred to `executor.elevation` (P12) |
| DN-54 | Q10 | Plan meet rule + envelope-scoped token (presented Step set); deviation/failure re-presentation is `core`'s |

---

## 12. Atomic implementation plan

Each commit is <300 production LOC, single responsibility, test-visible, on a
branch derived from `iteration/6-secrets` (e.g. `iteration/7-policy`). Commit
order follows ratification of the questions it depends on. Est. = estimated LOC
(impl / test / docs). C1–C3 **fill the Iteration 0 scaffold stubs** (`classify.py`,
`gates.py`, `tokens.py`, `policy.py` already exist with ownership docstrings; the
tree test stays green).

| Commit | Message | Content | Est. (impl/test) | Depends on | Deliverable |
|---|---|---|---|---|---|
| C0 | `docs: ratify Iteration 7 questions Q1–Q10 and policy scope` | Decision notes for Q1–Q10 (DN-45…DN-54), design review record, renumbering note (Q1), consistency-report note | — / — / ~800 | Q1–Q10 ratified | Ratified plan; all questions answered |
| C1 | `feat(policy): deterministic risk classification (RFC-0008 §6; RFC-0002 invariant 7; P2, P3, P4)` | The four `RiskClass` + four `Gate` enums; deterministic classification over `schema.Action` + referenced Facts (Q2); the internal canonical risk-property membership test (Q3); meet rule for Plans (Q10); elevation → at least Consequential (Q9); unknown/unparseable → blocked (P3); the gate carried, never re-derived (P4); never the proposer's self-report (I-7) | ~230 / ~330 | Q1, Q2, Q3, Q9, Q10 | Classifier |
| C2 | `feat(policy): gate table and default-deny policy loading (RFC-0008 §7; RFC-0001 §8.2; P3)` | `gates.py`: the §6 class→gate table (auto-permitted iff allowlisted else confirm / confirm / confirm-with-warning / blocked); `policy.py`: the Operator-owned default-deny mechanism — rule set, allowlist membership (empty by default, Q7), elevation bounds, standing-approval bounds (scope/ceiling/expiry, Q8), retry ceilings (Q7); fail-closed `load` (P3); never loosens bounds (RFC-0004 §9.7) | ~190 / ~290 | Q1, Q7, Q8 | Gate table + policy mechanism |
| C3 | `feat(policy): Approval Token mint/validate (RFC-0008 §8, §10; RFC-0002 invariant 11; P5–P10, P13, P14)` | Token record (Action identity, class, gate, state-snapshot ref (Q4), elevation bounds (Q9), session identity, per-class expiry, consumed, presented Step set (Q10)); `mint` on classification + explicit decision input (Q5); override path (P10); `validate`/`revalidate` (identity + freshness + state, P9; Q4); single-use consumption (P7); boundary-event invalidation + reload re-validation (P8, P14, I-15); in-memory issuance/override/auto-permit/rejection records (P13, Q6) | ~270 / ~340 | Q1, Q4, Q5, Q6, Q9, Q10 | Approval Token lifecycle |
| C4 | `test(policy): Layer-3 conformance and P-invariant suite` | Conformance (allowed imports schema/trust/factlayer only, no I/O, no forbidden stdlib, public surface == owned vocabulary, frozen/slotted, no top-level logic, package tree, lower layers never import policy); invariant tests I-7, I-11, RFC-0001 §8.2, P2–P10, P13, P14; boundary tests: P5 no-silence, P10 override-record, P13 record-before-spend, P9 re-validation refusals, SC9 structured-inputs-only; cross-component obligations (P1, P11, P12, durable P13, §6.2 edges) recorded | 0 / ~480 | C1–C3 | Conformance oracle |
| C5 | `docs: record Iteration 7 completion and policy conformance` | Consistency report + decision notes completion + deferred-items table | — / — / ~220 | C4 | Completion record |

---

## 13. Validation strategy

Same gates as Iterations 1–6: `pytest` (baseline **1333 tests**), `ruff check`,
`ruff format --check`, `python -m build`, and `pre-commit run --all-files`.
Conformance is enforced by the existing `tests/test_dependency_rules.py` (the
`policy` row is already declared: `ALLOWED["policy"] = {"schema", "trust",
"factlayer"}` and its forbidden-source rows) and `tests/test_packages.py`
(already green — the four `policy` modules exist as stubs), extended by C4's new
`test_policy_conformance.py` and `test_policy_invariants.py`. Because C0–C5
touch neither `rfc/` nor `tools/`, the RFC-reference validator is not a gate for
this iteration (CI still runs it; the known pre-existing RFC-0004 §470 `'S1'`
error is unrelated and unchanged). Determinism (P2) is asserted by
property-style tests: identical Actions + identical Facts → identical class and
gate, regardless of description.

---

## 14. Definition of Done (per commit)

| Commit | Definition of Done |
|---|---|
| C0 | Q1–Q10 each answered and recorded as decision notes (DN-45…DN-54); the renumbering tension (Q1) recorded; this review's readiness flips to READY |
| C1 | The four classes are exhaustive and mutually exclusive; one gate per class; classification is a membership test over the canonical risk-property vocabulary — no percentage, probability, score, or proposer words (P2/I-7); unknown/unparseable/classification-error → blocked with reason (P3); the gate is a carried field, never re-derived (P4); a Plan's class is the meet of its Steps' classes (Q10); an elevation risk-property makes the class at least Consequential (Q9); the `systemmodel` edge is latent (Q3) |
| C2 | The gate table is exactly the four §6 gates (auto-permitted iff allowlisted else confirm / confirm / confirm-with-warning / blocked); default-deny is structural — no rule matches → blocked (P3, RFC-0001 §8.2); allowlist membership deterministic and empty by default (Q7); policy-`load` fails closed on unparseable rules (P3, §8.12); elevation and standing-approval bounds are represented without shipped defaults (Q7/Q8); the engine never loosens bounds (RFC-0004 §9.7); no Approve/Execute/Observe surface (A6) |
| C3 | Mint requires a prior classification + an explicit decision input; no input or rejection mints nothing and consumes nothing (P5); AUTO_PERMIT only for an allowlisted read-only Action; OVERRIDE only for a Blocked Action and produces an override-scoped token + override record (P10); the token is bound to Action identity + time + state snapshot and carries class, gate, elevation bounds, session identity, expiry, presented Step set (P8, I-11; Q4/Q9/Q10); expiry is deterministic per class (P8); single-use — consumed/expired dead, replay refused (P7); invalidation on state change / interrupt / reboot / session restart / policy reload / revocation, never resurrected (P8, I-15); re-validation checks Action identity + Fact freshness + state snapshot and refuses on any uncertainty (P9; RFC-0002 §2.8); reload/state-change re-validates outstanding tokens (P14); no token is spendable without a prior issuance/override/auto-permit/rejection record (P13, I-13, layer-boundary) |
| C4 | Blueprint §7 policy row and §8.7 DoD (I-7, I-11, RFC-0001 §8.2, P8/P9/P10/P13) pass; every layer-enforceable P has a test; conformance: imports limited to `schema`/`trust`/`factlayer` + sanctioned stdlib, no I/O, no forbidden stdlib, public surface == owned vocabulary, package tree unchanged; the SC9 structured-inputs-only boundary test passes; cross-component obligations (P1, P11, P12, durable P13, the §6.2 edges) recorded against `executor`/`audit`/`core`; full suite green |
| C5 | Consistency report reflects Iteration 7; no orphaned decision notes; the deferred-items table names every §1.2 owner |

**Overall DoD (blueprint §8.7):** I-7 (never LLM self-report), I-11 (token
scoped/consumable/invalidated), RFC-0001 §8.2 (default-deny) tests pass;
P8/P9/P10/P13 conformance; `pytest` full suite, `ruff check`, `ruff format
--check`, `python -m build` all green; `tests/test_dependency_rules.py` and
`tests/test_packages.py` still green (tree and edges unchanged).

---

## 15. LOC estimates

| Commit | impl | test | docs | Notes |
|---|---|---|---|---|
| C0 | — | — | ~800 | Ratification |
| C1 | ~230 | ~330 | — | Classifier |
| C2 | ~190 | ~290 | — | Gate table + policy |
| C3 | ~270 | ~340 | — | Tokens |
| C4 | 0 | ~480 | — | Conformance + invariants |
| C5 | — | — | ~220 | Closeout |
| **Total** | **~690** | **~1,440** | ~1,020 | |

Production total ≈ **690**; test total ≈ **1,440**. Test LOC may exceed the
300-LOC cap per-commit, as in Iterations 4–6 (the cap applies to implementation
lines). C3 (tokens) is the largest implementation commit — the token lifecycle
carries the DoD's conformance weight (P8/P9/P10/P13, I-11).

---

## 16. Readiness assessment

**Status: BLOCKED** pending ratification of Q1–Q10 (recorded as decision notes
DN-45…DN-54 before C0), exactly as Iterations 1–6 began. The highest-leverage
questions are **Q2** (`classify` input binding), **Q3** (the risk-property /
State-Domain vocabulary without a `systemmodel` edge), **Q4** (the machine-state
snapshot representation), **Q5** (the decision-input abstraction that makes
P5/P10 testable), and **Q7** (how "default-deny policy loading" differs from
RFC-0020's policy *content*). Once Q1–Q10 are ratified, the layer is **READY**
and commits execute in order C0→C5, each satisfying its §14 DoD before the next
begins. The dominant residual risk is the Draft status of RFC-0008 itself (§17
risk 1); the layer's load-bearing dependencies are all Accepted, which bounds it.

**Post-ratification status (Iteration 7, Commit C0).** Q1–Q10 were ratified and
recorded as **DN-45…DN-54** (`docs/implementation-decision-notes.md`) before C0,
the docs-ratification commit: all ten questions answered as decision notes, the
renumbering tension (Q1) recorded as a supersession note, and the consistency
report updated. **Status: Ratified.** The layer is now **READY for
implementation** — commits execute in order C0→C5, each satisfying its §14 DoD
before the next begins. C1–C5 (the `policy` package: `classify.py`, `gates.py`,
`policy.py`, `tokens.py`, the conformance suite, and the closeout) remain to be
implemented per §12/§14.

---

## 17. Final verdict

This plan is a faithful translation of the frozen corpus into a policy-layer
scaffold: **no new architecture is proposed**, every ambiguity is reported and
elevated to a blocking question, no RFC is modified, no module is invented
beyond the scaffolded four, the allowed/forbidden dependency graph is honored,
and every layer-enforceable invariant (I-7, I-11, RFC-0001 §8.2, P2–P10, P13,
P14) maps to a deterministic mechanism and a test. The cross-component
obligations (P1, P11, P12, the durable half of P13, the §6.2 enforcement edges,
and the SC9/SC10 boundaries recorded by DN-43) are named against
`executor`/`audit`/`core` rather than dropped. **Ratified: Q1–Q10 are recorded
as DN-45…DN-54; the layer is READY for C1.**

---

## Consistency review against the Blueprint and governing RFCs

**Consistent.** Module set `policy/{__init__,classify,gates,tokens,policy}.py`
fixed by blueprint §2 (scaffold already present); dependency rules
(`ALLOWED["policy"] = {"schema", "trust", "factlayer"}` + stdlib, Layer 3)
honored by §3/§5; one-owner discipline (RFC-0004 §3) honored by §4 and the
two-owner checks; the scaffold gate (blueprint §8.0) stands; DN-40's re-order is
now executed (policy = Iteration 7, `executor`+`audit` = Iteration 8); DN-1
(signatures) honored; DN-9/DN-37/DN-44's latent-edge precedent is the Q3
recommendation; DN-34/DN-41's in-memory precedent is the Q6 recommendation;
DN-43's layer-boundary precedent is the P13/SC9 reading; RFC-0002 §6.2's
consultation edges are recorded as `core`'s obligation (§1.2), never invoked
here.

**Reported tensions (not violations):**

1. Blueprint §8.7/§8.8 numbering vs DN-35/DN-40's re-order — §8.7 still reads
   "Iteration 6 — `policy`" and §8.8 "Iteration 7 — `executor` + `audit`" while
   this iteration (and the Iteration 6 closeout) implement `policy` at Iteration
   7 (Q1). Needs ratification as a recorded supersession.
2. Blueprint §8.7 DoD requires P8/P9/P10/P13 "conformance" while P9's boundary,
   the durable half of P10/P13, and P1/P11/P12 live at Iteration 8/11 packages
   (Q4/Q5/Q6) — needs ratification of the layer-boundary reading (DN-49/DN-50).
3. RFC-0008 §6 requires RFC-0021 §6 State Domains as the classification
   vocabulary while `policy` may not import `systemmodel` and RFC-0021 is Draft
   (Q3) — needs ratification of the internal-vocabulary reading (DN-47).
4. RFC-0008 §7/§8 name standing approvals and elevation as Policy evaluation,
   while the §8.7 DoD omits P11/P12 (Q8/Q9) — needs ratification of the
   mechanism-only reading (DN-52/DN-53).
5. RFC-0008 §16 defers all shipped policy content to RFC-0020 while blueprint
   §8.7's work item is "default-deny policy loading" (Q7) — needs ratification
   of the mechanism-now reading (DN-51).
6. The Iteration 6 review's out-of-scope table labels `audit` as "Iteration 7"
   in three rows (RFC-0009 §15 wiring, RFC-0013 retention/records); under
   DN-40's re-order `audit` is Iteration 8 with `policy` — recorded here so the
   label is not carried forward.
7. RFC-0008 is Draft (2026-08-02); its normative sections 4–13, 15 may change
   before acceptance — the rework risk is accepted (DN posture of Iterations
   1–6) and the layer's Accepted-RFC dependencies bound it.

**Verdict.** This plan is a faithful translation of the frozen corpus into a
policy-layer scaffold; no new architecture is proposed, and every ambiguity is
elevated to a blocking question. Proceed to ratification.
