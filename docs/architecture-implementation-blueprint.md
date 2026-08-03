# Architecture Implementation Blueprint

> **Document type:** Implementation translation, not an RFC.
> **Read this first:** This document **defines no new architecture, modifies no
> RFC, and invents no behavior**. It translates the architecture already fixed by
> RFC-0000 through RFC-0013 and RFC-0021 into a package layout, a dependency
> discipline, a testing strategy, and an implementation order. Every package,
> responsibility, dependency, and iteration below is derived from an existing
> RFC section, section invariant, or the roadmap's own dependency ordering. Where
> the corpus does not yet decide something, this document reports it as a **Gap**
> or **Unknown** — it does not fill it.
>
> **Normative status.** The RFCs are normative; this document is a plan that
> must be ratified. RFC-0020 (Implementation Blueprint & Build Order) is the
> architectural owner of "how to build the thing the prior RFCs define"
> (RFC-0000 §4, RFC-0020 entry) and does not yet exist. This document is a
> translation *for review*; it is not, and does not claim to be, RFC-0020.

---

## 0. Purpose

1. **This document introduces no architecture.** It maps the accepted RFCs onto
   build units and borrows the roadmap's own category and dependency reasoning
   (RFC-0000 §2, §4, §7) as the skeleton of the build order.
2. **Every implementation artifact traces to exactly one architectural owner.**
   §10 proves this mapping; no artifact has two owners (RFC-0004 §3).
3. **Gaps are reported, not invented.** Where the corpus is silent — most
   importantly the MVP boundary and the Operator interface contract — this
   document says so and defers to the RFC that owns the decision.
4. **The implementation gate is respected.** RFC-0000 §5 names the RFCs that
   must be **Accepted** before a single line of production code:
   RFC-0001–0013, RFC-0015, RFC-0019, RFC-0020, RFC-0021. Of these,
   RFC-0015, RFC-0019, and RFC-0020 **do not exist yet**, and RFC-0005–0013
   are currently **Draft** (not Accepted). Production code is therefore
   **blocked** by the corpus itself. The iterations in §8 build the non-
   production translation and conformance scaffold up to that gate.

---

## 1. Constraints the Corpus Imposes

The blueprint is bounded by the following, each cited:

1. **No production code before the gates.** RFC-0000 §5: RFC-0015, RFC-0019,
   RFC-0020 must be Accepted before production code; without them "the MVP
   cannot be specified, or it would be built against undecided safety or domain
   semantics."
2. **RFC-0020 owns the authoritative build order.** RFC-0000 §4 (RFC-0020
   entry): it specifies "the mapping from accepted architecture to build units,
   the runtime's concurrency model, the architectural testing philosophy, and
   the build order in which each stage is demonstrable and verifiable."
   This document's §8 order is a *translation* of RFC-0000 §7's writing order;
   it is subject to RFC-0020.
3. **RFC-0019 owns the MVP boundary.** RFC-0000 §4 (RFC-0019 entry): "Define
   the minimum viable product precisely… the smallest safe core loop." Until
   RFC-0019 exists, the MVP boundary is **Unknown** (§11) and this document
   defines iterations, not an MVP claim.
4. **RFC-0015 owns the Operator interface contract.** The Presentation
   component exists in RFC-0001 §5, but its interaction contract is RFC-0015's
   (RFC-0000 §4). The `cli` package (§2) is therefore scoped to the RFC-0001
   §5 responsibilities only until RFC-0015 lands.
5. **Authorities are fixed.** No package may grant an actor an authority the
   RFC-0004 §7 matrix forbids. The dependency rules (§4) encode this matrix.
6. **Invariants are without exception.** RFC-0002 §9: invariants hold "in every
   state, without exception." Tests (§7) are conformance tests against these.
7. **Single-goal, serial execution.** RFC-0002 §1: the lifecycle is
   single-goal and serial; state-changing actions never run in parallel.
   RFC-0002 §11 item 15 leaves concurrent read-only collection open; the
   blueprint marks it Unknown until RFC-0020.

---

## 2. Complete Project Directory Tree

The tree is a *translation* of RFC-0001 §5's components into packages, one
package per architectural component (plus cross-cutting packages for the
fact/trust/secret/system models). Names are implementation detail; ownership is
architectural and is fixed in §3.

```
episky/
├── pyproject.toml                     # packaging: implementation (RFC-0020)
├── README.md
├── LICENSE
├── AGENTS.md
├── CONTRIBUTING.md
├── .github/                           # CI, issue templates, PR template (RFC-0020)
├── rfc/                               # normative documents (RFC-0000..0021)
├── docs/                              # architecture + review documents (this doc)
├── tools/                             # existing validation tooling
│   ├── README.md
│   └── validate_rfc_refs.py           # invariant/reference validator (existing)
└── src/
    └── episky/
        ├── __init__.py
        ├── schema/                    # canonical fact/action/plan types   → RFC-0005 §3, RFC-0003 §2
        │   ├── __init__.py
        │   ├── fact.py                #   canonical Fact model (RFC-0005 §3, §4, §5, §12)
        │   ├── action.py              #   Action / Step / Proposal / Plan types (RFC-0003 §2.6)
        │   └── outcome.py             #   Outcome vocabulary (RFC-0006 §7)
        ├── systemmodel/               # Family Profiles, subsystem vocabulary → RFC-0021
        │   ├── __init__.py
        │   ├── profiles.py            #   Family Profile (§2.3), supported families (§2.2)
        │   └── subsystems.py          #   subsystem / State-Domain vocabulary (§4, §6, §11)
        ├── trust/                     # trust classes + sanitization        → RFC-0007
        │   ├── __init__.py
        │   ├── classes.py             #   trust classes T1–T12 (§10)
        │   ├── sanitize.py            #   sanitization S1–S8 (§11)
        │   └── hostile.py             #   Hostile quarantine / fail-closed (§15)
        ├── collectors/                # built-in diagnostics                → RFC-0005, RFC-0021
        │   ├── __init__.py
        │   └── registry.py            #   Collector registry (RFC-0003 §2.4 Collector)
        ├── factlayer/                 # Diagnostics & Fact Layer            → RFC-0005
        │   ├── __init__.py
        │   ├── collect.py             #   run Collectors (RFC-0005 §2; RFC-0004 §4.5)
        │   ├── normalize.py           #   Observation → Fact (RFC-0005 §2; F5)
        │   ├── provenance.py          #   provenance + freshness (RFC-0005 §5, §12)
        │   └── store.py               #   Fact storage, status, invalidation (RFC-0005 §4, §7)
        ├── verification/              # Collect/Compare/Outcome             → RFC-0006
        │   ├── __init__.py
        │   ├── compare.py             #   deterministic Compare (V3, V7, V10)
        │   └── outcome.py             #   Outcome determination (V5–V7, V9, V14–V16)
        ├── secrets/                   # secret classification/boundaries    → RFC-0009
        │   ├── __init__.py
        │   ├── classify.py            #   deterministic classification (§3)
        │   ├── redact.py              #   redaction, fail-closed (SC13, SC14)
        │   └── store.py               #   Secure Store abstraction (SC1, SC8, SC12)
        ├── policy/                    # Approval & Policy Engine            → RFC-0008
        │   ├── __init__.py
        │   ├── classify.py            #   deterministic risk classification (§6)
        │   ├── gates.py               #   gate per class (§7)
        │   ├── tokens.py              #   Approval Token mint/validate (§8)
        │   └── policy.py              #   Operator-owned policy (default-deny) (§7)
        ├── executor/                  # Action Execution                    → RFC-0004 §4.9, RFC-0002 §2.8
        │   ├── __init__.py
        │   ├── runner.py              #   run one approved Action (§2.8; I-1)
        │   ├── guards.py              #   scoping, timeouts, output capture (§5 Action Execution)
        │   └── elevation.py           #   explicit scoped elevation (§8.6; P12)
        ├── audit/                     # Audit & Transcript                  → RFC-0013
        │   ├── __init__.py
        │   ├── records.py             #   record categories (§7, §9)
        │   ├── store.py               #   append-only durable store (§1, §11, §21)
        │   └── transcript.py          #   derive transcript from record (§8)
        ├── context/                   # Context & Memory                    → RFC-0012
        │   ├── __init__.py
        │   ├── assemble.py            #   deterministic composition (§12)
        │   ├── boundaries.py          #   boundary rules, secret-free (§13, SC2)
        │   ├── memory.py              #   consented Memory (§7, §18–§22)
        │   └── provider_view.py       #   the Provider View (§13; RFC-0010 §3)
        ├── providers/                 # Provider adapters                   → RFC-0010
        │   ├── __init__.py
        │   ├── contract.py            #   structured output validation (§4, §8)
        │   ├── view.py                #   consume the Provider View (§3)
        │   └── adapters/              #   per-vendor adapters (§1 uniform interface)
        │       └── __init__.py
        ├── skills/                    # Skill Runtime                       → RFC-0011
        │   ├── __init__.py
        │   ├── loader.py              #   load/authenticate (§22)
        │   ├── activation.py          #   activation lifecycle (§23)
        │   └── runtime.py             #   gate participation (SK4; §4)
        ├── core/                      # Orchestration Core                  → RFC-0002
        │   ├── __init__.py
        │   ├── session.py             #   session lifecycle (§1, §2)
        │   ├── state_machine.py       #   states + transitions (§2, §3)
        │   ├── events.py              #   event model (§4)
        │   ├── loop.py                #   the goal loop (§5)
        │   ├── consultation.py        #   component consultation rules (§6)
        │   ├── replan.py              #   Replanning (§2.10, §7)
        │   └── recovery.py            #   failure ordering (§10)
        └── cli/                       # Presentation (TUI)                  → RFC-0001 §5 (interface: RFC-0015)
            ├── __init__.py
            ├── render.py              #   render conversation/state (§5 Presentation)
            ├── collect.py             #   collect approvals/refusals/input (§5 Presentation)
            └── expose.py              #   expose audit log / context view (§5 Presentation)
```

---

## 3. Package Responsibilities and Owners

Every package, its owning RFC(s), and its responsibility (each clause cited to
the RFC's own wording). Internal-only modules are named per package.

| Package | Owning RFC(s) | Responsibility | Internal-only modules |
|---|---|---|---|
| `schema` | RFC-0005 §3, §4, §5, §12; RFC-0003 §2 | The canonical fact/action/plan/outcome types — the shared vocabulary every package consumes. No behavior. | `fact.py`, `action.py`, `outcome.py` |
| `systemmodel` | RFC-0021 | The Family Profile (§2.3), supported families (§2.2), and subsystem/State-Domain vocabulary (§4, §6, §11) that Facts and Verification Scopes reference. | `profiles.py`, `subsystems.py` |
| `trust` | RFC-0007 | Trust classes T1–T12 (§10), sanitization S1–S8 (§11), Hostile quarantine and fail-closed failure behavior (§15). Consumed by every boundary toward the LLM, the Operator terminal, and any interpreter. | `classes.py`, `sanitize.py`, `hostile.py` |
| `collectors` | RFC-0005 §2; RFC-0003 §2.4 (Collector); RFC-0021 (vocabulary) | The registry of deterministic, read-only inspection procedures; each Collector answers one question and carries declared inputs and provenance behavior. | `registry.py` |
| `factlayer` | RFC-0005 §2, §3, §4, §5, §7, §12 | Normalize Observations into canonical Facts; carry status, provenance, freshness; own Fact storage and invalidation. Never mutates; never consumes secrets into long-term context (RFC-0001 §5 Diagnostics & Fact Layer). | `collect.py`, `normalize.py`, `provenance.py`, `store.py` |
| `verification` | RFC-0006 §6, §7, §8 | The deterministic Collect→Normalize→Facts→Compare→Outcome process; comparison against declared Postconditions (V10); contradiction always wins (V7). Realizes the Fact Layer's Verify authority (RFC-0004 §4.6). | `compare.py`, `outcome.py` |
| `secrets` | RFC-0009 | Deterministic secret classification (§3), redaction with fail-closed (§11, §13, SC13/SC14), and the Secure Store abstraction (SC1, SC8, SC12). Never lets a value enter Context/View/Audit/extensions (SC2–SC5). | `classify.py`, `redact.py`, `store.py` |
| `policy` | RFC-0008 §6, §7, §8; RFC-0004 §4.7, §4.8 | Deterministic risk classification (never the LLM's self-report, RFC-0002 invariant 7); the gate per class (§7); Approval Token mint/validate (§8); Operator-owned default-deny policy. | `classify.py`, `gates.py`, `tokens.py`, `policy.py` |
| `executor` | RFC-0004 §4.9; RFC-0002 §2.8; RFC-0001 §8.6 | Run the one approved Action under a valid, unexpired, state-consistent token; scoping, timeouts, output capture, no secret leakage (RFC-0001 §5 Action Execution); explicit scoped elevation (§8.6, P12). May decide only *how*, never *what*. | `runner.py`, `guards.py`, `elevation.py` |
| `audit` | RFC-0013 §7–§22 | Append-only, tamper-evident record of the categories in §7; written before the consequence (RFC-0002 invariant 13, AU8); transcript derived from the record (§8); reconciliation on failure (§22). | `records.py`, `store.py`, `transcript.py` |
| `context` | RFC-0012 §12, §13, §7, §21 | Deterministic Context composition from Facts, Goal, bounded history, Skill material; boundary rules and secret-free assembly (SC2); consented Memory; the Provider View as the only outward channel (§13, PR14). | `assemble.py`, `boundaries.py`, `memory.py`, `provider_view.py` |
| `providers` | RFC-0010 §2–§8 | One uniform interface to all vendors (RFC-0001 §5 Providers); structured output validation (§4, §8); consume exactly the Provider View (§3, PR14); output is untrusted data, never instructions. | `contract.py`, `view.py`, `adapters/` |
| `skills` | RFC-0011 §4, §22, §23 | Load/authenticate Skill packages (§22), activation lifecycle (§23), and gate participation — every Skill Action passes the full gate, never approved as a unit (SK4). Skill holds Propose/Infer only (RFC-0004 §4.10). | `loader.py`, `activation.py`, `runtime.py` |
| `core` | RFC-0002 §1–§10 | Own the session loop and state transitions; enforce the decision rules (RFC-0001 §5 Orchestration Core); keep the provider world separate from the machine world; degrade gracefully; consult components per §6; run failure recovery per §10. | `session.py`, `state_machine.py`, `events.py`, `loop.py`, `consultation.py`, `replan.py`, `recovery.py` |
| `cli` | RFC-0001 §5 (Presentation); interface per RFC-0015 (future) | Render conversation/state; present evidence and proposals legibly; collect approvals/refusals/input; expose the audit log and context view on demand. Risk tone is presentation only, never policy (RFC-0001 §5). | `render.py`, `collect.py`, `expose.py` |

---

## 4. Allowed and Forbidden Dependencies

### 4.1 Allowed import graph

Edges are "package imports package"; the graph is layered so that every edge
points from a later layer to an earlier one (mirroring RFC-0000 §7's writing
order and RFC-0002 §5's consultation order). `core` is the only package allowed
to import across all layers — it is the conductor (RFC-0002 §5).

```
Layer 0  schema
Layer 1  systemmodel, trust
Layer 2  collectors ─► factlayer ─► verification
Layer 3  secrets, policy
Layer 4  executor, audit, context
Layer 5  providers, skills
Layer 6  core  ◄── imports all above
Layer 7  cli   ◄── imports core, audit, context, schema
```

**Allowed edges (each derived from the owning RFC):**

| From | To | Why allowed (RFC basis) |
|---|---|---|
| `systemmodel` | `schema` | Vocabulary is expressed in the canonical types (RFC-0021 §2.3, §4; RFC-0005 §3) |
| `trust` | `schema` | Trust classes attach to data of the canonical types (RFC-0007 §10) |
| `collectors` | `schema`, `systemmodel`, `trust` | A Collector's output is Observation material (RFC-0005 §2), expressed over subsystem vocabulary (RFC-0021) |
| `factlayer` | `collectors`, `schema`, `systemmodel`, `trust` | Normalizes Observations into Facts (RFC-0005 §2); consumes the trust-upgrade path (RFC-0007 T6) |
| `verification` | `factlayer`, `schema`, `systemmodel` | Compares Facts (RFC-0006 §6); Verification Scope uses subsystem vocabulary (RFC-0021 §11) |
| `secrets` | `schema`, `trust` | Classification is local and deterministic over data (RFC-0009 §3); redaction is a sanitization (RFC-0007 §11) |
| `policy` | `schema`, `trust`, `factlayer` | Consumes Facts for classification and preconditions (RFC-0008 §6, §9); never the LLM's self-report (RFC-0002 invariant 7) |
| `executor` | `schema`, `audit`, `secrets` | Runs a sanctioned Action (RFC-0004 §4.9); records before/after (RFC-0002 invariant 13); scoped elevation touches the secret boundary (RFC-0001 §8.6) |
| `audit` | `schema`, `secrets` | Records categories in canonical form (RFC-0013 §7); secret interaction is metadata-only (SC4) |
| `context` | `schema`, `factlayer`, `trust`, `secrets`, `systemmodel` | Assembles Facts into Context (RFC-0012 §12); secret-free by construction (SC2); sanitizes via RFC-0007 |
| `providers` | `schema`, `trust`, `context` | Consumes the Provider View type (RFC-0010 §3); validates structured output (RFC-0010 §4, §8); output is untrusted (RFC-0007 T4) |
| `skills` | `schema`, `collectors`, `trust`, `policy`, `factlayer` | Bundles Collectors (RFC-0011 §2); its Actions pass the gate (SK4); conditional trust (RFC-0007 §4.8) |
| `core` | all above | The conductor (RFC-0002 §5); owns the loop, states, and recovery |
| `cli` | `core`, `audit`, `context`, `schema` | Renders state, exposes audit/context on demand (RFC-0001 §5 Presentation) |

### 4.2 Forbidden dependencies

Each forbidden edge encodes a cell of the RFC-0004 §7 authority matrix (F =
forbidden) or a consultation rule in RFC-0002 §6. A package that *imports* a
forbidden package is a design defect before it is a bug (RFC-0004 §7).

| Package | Must NOT import | Reason (RFC basis) |
|---|---|---|
| `providers` | `factlayer`, `executor`, `policy`, `verification`, `audit`, `secrets` | Provider may not create Facts (F1, F6), may not execute/verify/approve (RFC-0010 §2), never receives secrets (SC3), never receives the Audit (PR14); never consulted in Inspection/Executing/Verification (RFC-0002 §6) |
| `skills` | `executor`, `verification`, `policy` (decision), `audit`, `secrets`, `factlayer` (create) | Skill may not execute/verify/approve/escalate (RFC-0011 §4; A8); never receives a secret (SC5); may not modify the Audit (SK14). May reference `factlayer` *types* for Collectors, never to author Facts |
| `executor` | `policy` (classify), `verification` (decide), `factlayer` (normalize), `providers`, `skills` | Executor may decide only *how* within declared bounds, never *what* (RFC-0004 §4.9); never verifies its own work (V1; RFC-0006); the gate is upstream (RFC-0008) |
| `verification` | `providers`, `skills`, `executor`, `policy` | Verification is deterministic and never the LLM's or Skill's assessment (V3; RFC-0004 §1.1); the Executor may not verify itself (RFC-0004 §4.9) |
| `factlayer` | `providers`, `policy`, `executor`, `skills`, `context`, `audit`, `secrets` | Facts are provider-independent (F6), never contain permissions (F2), never execute (F3); the Fact Layer has no secret surface (RFC-0009 §1, SC6) |
| `context` | `providers` (assembly), `policy`, `executor`, `audit`, `secrets` (values) | Context assembly is owned by the Context Manager, not providers (RFC-0012 §12); the gate consumes Facts, never Context (RFC-0008 §2); Context is never the Audit (CM15); secret-free by construction (SC2). May import `secrets` *classifier* types only |
| `audit` | `factlayer`, `providers`, `context`, `policy`, `executor`, `secrets` (values) | The Audit holds records, never the material (RFC-0013 §7 category 9, §10); metadata-only for secrets (SC4); no decision authority (RFC-0004 §4.12) |
| `core` | *(none structurally)* — but must never *re-implement* a forbidden authority (e.g., classify, verify, approve); it routes (RFC-0002 §5; RFC-0004 §4.3) | Core owns Propose/Refuse/Explain (RFC-0004 §4.3), not Observe/Verify/Approve/Execute |
| `cli` | `policy`, `executor`, `factlayer`, `providers`, `skills`, `secrets` | Presentation collects decisions and renders state; it never classifies, executes, or holds secrets (RFC-0001 §5; RFC-0004 §7: Presentation not an actor in the matrix) |

### 4.3 The import graph, drawn

```
                          ┌──────────┐
                          │  schema  │
                          └────┬─────┘
                 ┌─────────────┼──────────────┐
                 ▼             ▼              ▼
           ┌───────────┐ ┌───────────┐ ┌───────────┐
           │systemmodel│ │   trust   │ │  schema   │
           └─────┬─────┘ └─────┬─────┘ └───────────┘
                 │             │
                 ▼             ▼
           ┌────────────────────────┐
           │ collectors ─► factlayer │────► verification
           └────────────┬───────────┘
                        │
        ┌───────────────┼───────────────┐
        ▼               ▼               ▼
  ┌─────────┐    ┌───────────┐    ┌───────────┐
  │ secrets │    │  policy   │    │  context  │
  └────┬────┘    └─────┬─────┘    └─────┬─────┘
       │               │               │
       ▼               ▼               ▼
  ┌─────────┐    ┌───────────┐    ┌───────────┐
  │ executor│    │  skills   │    │ providers │
  └────┬────┘    └───────────┘    └─────┬─────┘
       │                               │
       ▼                               ▼
  ┌────────────────────────────────────────┐
  │                  core                  │
  └────────────────────┬───────────────────┘
                       ▼
                ┌───────────┐
                │    cli    │
                └───────────┘
```

`audit` is deliberately *not* drawn as a fan-out hub: only `core`, `executor`,
`context`, `secrets`, `policy`, and `skills` write records through `core`'s
boundary handling, because every record is written *at a boundary* by the
component whose consequence it precedes (RFC-0002 invariant 13; RFC-0013 §7).
`audit` itself imports only `schema` and `secrets` (metadata types).

---

## 5. Public Interfaces Exposed by Each Package

The RFCs explicitly specify **behavior, not schemas or APIs** (RFC-0005 §3:
"no schemas, no data formats"; RFC-0010 §3: "This RFC does not define its
shape — no schemas — but defines its boundary"). Therefore the "public
interface" of each package is the *architectural contract* it must honor. Exact
signatures are implementation detail, owned by RFC-0020, and are **not**
specified here.

| Package | Public contract (what it must expose to its allowed importers) | Boundary statement in the RFC |
|---|---|---|
| `schema` | Canonical Fact (status, provenance, freshness, machine identity, scope); Action/Step/Proposal/Plan types; Outcome vocabulary | RFC-0005 §3–§5, §12; RFC-0003 §2.6; RFC-0006 §7 |
| `systemmodel` | Family Profile access (supported families, descriptive profile); subsystem and State-Domain vocabulary | RFC-0021 §2.2, §2.3, §4, §6, §11 |
| `trust` | Trust-class classifier over data; sanitize (neutralize control, preserve content); Hostile quarantine, fail-closed on trust failure | RFC-0007 §10 (T1–T12), §11 (S1–S3), §15.5 |
| `collectors` | A read-only inspection procedure: one question, declared inputs, provenance behavior, declared output (Observation) | RFC-0003 §2.4 Collector; RFC-0005 §2 |
| `factlayer` | Run Collectors; normalize Observation→Fact (deterministic); store/status/invalidate Facts; expose fresh Facts with provenance | RFC-0005 §2, §4, §5, §7, §12; RFC-0004 §4.5/§4.6 |
| `verification` | Compare Facts against declared Postconditions; return an Outcome (never success without fresh Facts) | RFC-0006 §6, §7; V1–V16 |
| `secrets` | Classify a datum (secret/non-secret/secret-adjacent/Hostile); redact with fail-closed; Secure Store interface (provision, consume-at-boundary, destroy) | RFC-0009 §3, §11, §13, §14; SC1–SC16 |
| `policy` | Classify an Action into a risk class; return the gate; mint/validate an Approval Token; apply Operator policy (default-deny) | RFC-0008 §6, §7, §8; P1–P14; RFC-0002 invariant 7 |
| `executor` | Run one token-bound Action under guardrails; report start/end and sanitized output; scoped elevation | RFC-0004 §4.9; RFC-0002 §2.8; RFC-0001 §5, §8.6 |
| `audit` | Append a record (append-only, before-consequence); render the transcript from the record; reconcile failed writes | RFC-0013 §7, §8, §21, §22; AU1–AU16; RFC-0002 invariant 13 |
| `context` | Assemble a bounded, secret-free Context from Facts/Goal/history/Skill material; produce the Provider View (the only outward channel) | RFC-0012 §12, §13; RFC-0010 §3; SC2 |
| `providers` | Consume a Provider View; return one of the finite structured outputs; validate and route them; never accept secrets | RFC-0010 §3, §4, §8; PR1–PR16 |
| `skills` | Load/authenticate a Skill package; activate; expose its bundled Collectors and candidate Plans through the gate | RFC-0011 §22, §23, §4; SK1–SK16 |
| `core` | The session: start/stop, goal loop, state transitions, events, recovery — the only entry point the `cli` uses | RFC-0002 §1–§10 |
| `cli` | Render, collect Operator decisions/input, expose audit/context view | RFC-0001 §5 Presentation; interface details deferred to RFC-0015 |

**Interface discipline.** Because RFC-0005, RFC-0008, RFC-0010, RFC-0011,
RFC-0012, RFC-0013 all declare "no schemas here," this blueprint exposes
*contracts*, not signatures. Defining the concrete interfaces is RFC-0020's
job. Any signature invented before RFC-0020 is a **Gap** (§11), not a design
decision.

---

## 6. Mapping: RFC → Package → Components → Future Implementation

### 6.1 RFC → Package

| RFC | Primary package(s) |
|---|---|
| RFC-0001 (architecture, principles) | `core` (enforces decision rules); `cli` (Presentation); cross-cutting principles enforced in every package |
| RFC-0002 (runtime) | `core` |
| RFC-0003 (vocabulary/governance) | `schema` (canonical terms); governance in `tools/` + repo process |
| RFC-0004 (authority) | enforcement across `policy`, `executor`, `factlayer`, `verification`, `audit`, `context` (the matrix is per-component) |
| RFC-0005 (facts) | `factlayer`, `collectors`, `schema` |
| RFC-0006 (verification) | `verification`, `schema` |
| RFC-0007 (trust) | `trust` |
| RFC-0008 (approval) | `policy`, `executor` |
| RFC-0009 (secrets) | `secrets`, `context`, `audit` (boundary enforcement) |
| RFC-0010 (provider) | `providers`, `context` (View) |
| RFC-0011 (skills) | `skills`, `collectors` |
| RFC-0012 (context/memory) | `context` |
| RFC-0013 (audit/transcript) | `audit` |
| RFC-0021 (system model) | `systemmodel` |

### 6.2 Package → Component → Future implementation

| Package | Component (RFC-0001 §5 / RFC-0004 §4) | Future implementation (translation, not new architecture) |
|---|---|---|
| `schema` | — (types layer) | Concrete canonical types; serialization bounded by RFC-0005 §3's "no schemas" until RFC-0020 |
| `systemmodel` | RFC-0021 §2–§6, §11 | Family Profile data for Supported families (RFC-0021 §2.2), subsystem vocabulary, State-Domain listing |
| `trust` | RFC-0007 | Trust-class table, sanitizer primitives, Hostile quarantine path |
| `collectors` | Diagnostics (RFC-0005 §2) | One Collector per baseline question (distro, kernel, package state) for Supported families |
| `factlayer` | Diagnostics & Fact Layer (RFC-0001 §5) | Normalizer per Family Profile, provenance/freshness bookkeeping, Fact store |
| `verification` | Fact Layer Verify authority (RFC-0004 §4.6) | Compare implementation against declared Postconditions; Outcome mapping per RFC-0006 §7 |
| `secrets` | RFC-0009 | Classifier, redactor, Secure Store adapter interface (mechanics per RFC-0020) |
| `policy` | Approval & Policy Engine (RFC-0001 §5; RFC-0004 §4.7/§4.8) | Risk rules per RFC-0008 §6; gate table §7; token mint/validate §8; default-deny policy loading |
| `executor` | Action Execution (RFC-0001 §5; RFC-0004 §4.9) | Sanctioned Action runner; guardrails; scoped elevation |
| `audit` | Audit & Transcript (RFC-0001 §5; RFC-0004 §4.12) | Append-only store, record writers per RFC-0013 §7, transcript derivation §8, reconciliation §22 |
| `context` | Context & Memory (RFC-0001 §5; RFC-0004 §4.11) | Assembly rules §12, boundary enforcement §13, consented Memory, Provider View builder |
| `providers` | Providers (RFC-0001 §5; RFC-0004 §4.4) | Uniform adapter interface, structured output validation, first vendor adapter |
| `skills` | Skills (RFC-0001 §5; RFC-0004 §4.10) | Loader/authenticator, activation, gate wiring |
| `core` | Orchestration Core (RFC-0001 §5; RFC-0004 §4.3) | State machine, event loop, consultation router, recovery |
| `cli` | Presentation (RFC-0001 §5) | TUI renderer, decision collector, audit/context exposure (interface per RFC-0015) |

---

## 7. Testing Strategy Per Package

The corpus fixes the *testing philosophy* (RFC-0000 §4 RFC-0020 entry:
"architectural testing philosophy (state-machine conformance, invariant
checks)"), and RFC-0002 §9 fixes that invariants hold "in every state, without
exception." Each package's tests are therefore **conformance tests** against its
owning RFC's invariants, plus the mandatory validator gate
(`tools/validate_rfc_refs.py`, per `AGENTS.md` and `tools/README.md`) when any
RFC or tooling changes.

| Package | Test focus | Normative oracle |
|---|---|---|
| `schema` | Type invariants: Fact can't be LLM-authored by construction (F1), Facts never carry permissions (F2), never execute (F3) | RFC-0005 §13 (F1–F16); RFC-0006 §7 vocabulary |
| `systemmodel` | Only Supported/Planned families have a Family Profile; unsupported families promise no Facts | RFC-0021 §2.1, §2.2 |
| `trust` | Sanitize removes instruction-capability without changing trust class (S1–S3); trust never upgrades via sanitize (T9); failure degrades to Hostile (T11/T12) | RFC-0007 §10, §11, §13 |
| `collectors` | Read-only (no mutation); each Collector carries declared inputs and provenance; per-family behavior | RFC-0003 §2.4; RFC-0005 §2 |
| `factlayer` | Normalization is deterministic (F5), provider-independent (F6), distro-independent (F7); Observations immutable (F8); provenance mandatory (F10); failed collection → Unknown/Unavailable status (F11, §4) | RFC-0005 §2, §4, §5, §13 |
| `verification` | Compare is deterministic (V3), read-only (V8), never stale (V4), Postconditions fixed before Compare (V10), contradiction wins (V7), never skips (V14) | RFC-0006 §6, §7, §8, V1–V16 |
| `secrets` | No value enters Context/View/Audit (SC2–SC5); redaction fails closed (SC14); exposure is compromise (SC15); retention is consent-based (SC11) | RFC-0009 §0, §13, §28 |
| `policy` | Classification deterministic, never LLM self-report (I-7); token scoped/consumable/invalidated (I-11); default-deny (RFC-0001 §8.2); blocked action only via audited override (I-12, P10) | RFC-0008 §6–§8, §13; RFC-0002 §9 |
| `executor` | Never starts without approval (I-1); token-bound and re-validated at boundary (I-11, P9); no untrusted text interpolated (I-5); elevation scoped and revoked (P12); no secret exposed (SC10) | RFC-0004 §4.9; RFC-0002 §2.8; RFC-0008 §10 |
| `audit` | Recorded before consequence (I-13); append-only, tamper-evident (A7); failed write blocks consequence and is disclosed (AU8); transcript derives from record only (RFC-0013 §8); no secret value recorded (SC4) | RFC-0013 §21, §22, §33; RFC-0002 invariant 13 |
| `context` | Assembly deterministic and bounded (§12); secret-free (SC2); Provider View is the only outward channel (PR14); re-assembly never restore (CM13) | RFC-0012 §12, §13, §21; RFC-0002 §2.4 |
| `providers` | View is the only input (PR14); structured outputs only (RFC-0010 §4); malformed → degrade, never crash (PR11); output never a Fact (F6); provider never executes (RFC-0010 §2) | RFC-0010 §2–§4, §8, PR1–PR16 |
| `skills` | Every Skill Action passes the gate (SK4); no unit approval; Skill cannot execute/verify/approve (RFC-0011 §4); no secret reaches a Skill (SC5); untrusted until authenticated (SK5) | RFC-0011 §4, §28; SC5 |
| `core` | **State-machine conformance**: only the transitions of RFC-0002 §3 are reachable; invariants 1–15 hold in every state; interruption → re-assessment (I-8); no terminal outcome while work is in flight (I-14); no approval survives a boundary (I-15); recovery ordering is determinism→disclosure→decision→action (§10) | RFC-0002 §2, §3, §4, §9, §10 |
| `cli` | Renders state without policy authority; collects decisions and returns them to `core`; exposes audit/context on demand (RFC-0001 §5) | RFC-0001 §5 Presentation; RFC-0015 (future) |
| Whole-repo | `tools/validate_rfc_refs.py` exits 0 after any `rfc/` or `tools/` change | `tools/README.md`; `AGENTS.md` |

**Cross-cutting test policy** (from the corpus, not invented):
- Invariant-conformance tests run at every layer boundary; a failing invariant
  is a blocking defect (RFC-0002 §9 preamble).
- Failure tests mirror `docs/failure-injection-walkthrough.md` §3: each of the
  31 scenarios has a conformance test at its responsible package.
- The happy-path composition mirrors `docs/core-execution-walkthrough.md` §3:
  one integration test walks the full loop end to end.

---

## 8. GitHub Implementation Roadmap

### 8.0 Gate statement

Per RFC-0000 §5, **no production code is written until RFC-0015, RFC-0019,
RFC-0020 are Accepted** and RFC-0005–0013, RFC-0021 are Accepted (not Draft).
Iterations 0–10 below build the *translation scaffold, conformance tests, and
tooling* — not the product. Iteration 11 (the "gate" iteration, §8.12) is where the MVP
boundary is ratified by RFC-0019 and the build order by RFC-0020; only after
those land does production implementation begin. The blueprint defines
iterations; it does not define the MVP (that is RFC-0019's, per RFC-0000 §4).

### 8.1 Iteration 0 — Repository bootstrap

| Item | Value |
|---|---|
| Goal | Establish the repo skeleton, tooling, and the conformance harness |
| Work | `pyproject.toml`, package skeleton, CI, issue/PR templates, import `rfc/` and `docs/`, wire `tools/validate_rfc_refs.py` into CI |
| Definition of Done | Repo builds; validator runs and exits 0 on the current corpus; no production code; CI green on an empty `src/` tree |
| RFC basis | RFC-0000 §4 (build units, build order); `AGENTS.md`; `tools/README.md` |

### 8.2 Iteration 1 — `schema`

| Item | Value |
|---|---|
| Goal | Canonical types as the shared vocabulary |
| Work | Fact/Action/Step/Proposal/Plan/Outcome types; conformance tests for F1–F3, F10 |
| Definition of Done | Type-level invariant tests pass; `schema` has zero imports beyond stdlib |
| RFC basis | RFC-0005 §3–§5, §12; RFC-0003 §2; RFC-0006 §7 |

### 8.3 Iteration 2 — `systemmodel` + `trust`

| Item | Value |
|---|---|
| Goal | The thing facts describe, and the trust spine |
| Work | Family Profile access for Supported families; subsystem/State-Domain vocabulary; trust classes T1–T12, sanitizer S1–S8, Hostile quarantine |
| Definition of Done | Profile lookup tests (RFC-0021 §2.2); sanitize-never-upgrades tests (T9); fail-to-Hostile tests (T11/T12) |
| RFC basis | RFC-0021 §2, §4, §6, §11; RFC-0007 §10, §11, §15 |

### 8.4 Iteration 3 — `factlayer` + `collectors`

| Item | Value |
|---|---|
| Goal | Observation→Fact pipeline for the baseline |
| Work | Baseline Collectors (distro, kernel, package state); deterministic normalization; provenance/freshness; Fact status store |
| Definition of Done | F5/F6/F7/F8/F10 conformance; a failed collection yields Unknown/Unavailable status (F11, §4); no mutation in any Collect |
| RFC basis | RFC-0005 §2, §4, §5, §12; RFC-0002 §4.2 (COLLECTOR_FAILED) |

### 8.5 Iteration 4 — `verification`

| Item | Value |
|---|---|
| Goal | Deterministic Compare and Outcome |
| Work | Compare Facts against declared Postconditions; Outcome mapping (Verified Success/Partial/Unknown/Contradicted/Expired) |
| Definition of Done | V3 (deterministic), V4 (no stale), V7 (contradiction wins), V10 (Postconditions fixed), V14 (never skip) all pass |
| RFC basis | RFC-0006 §5–§8; RFC-0002 invariant 2 |

### 8.6 Iteration 5 — `secrets`

| Item | Value |
|---|---|
| Goal | The no-secrets boundary, testable |
| Work | Classifier (secret/non-secret/secret-adjacent/Hostile), redactor (fail-closed), Secure Store interface |
| Definition of Done | SC2–SC5 (never in Context/View/Audit/extensions), SC14 (fail closed), SC15 (exposure = compromise) tests pass |
| RFC basis | RFC-0009 §0, §3, §11, §13, §15, §28 |

### 8.7 Iteration 6 — `policy`

| Item | Value |
|---|---|
| Goal | The gate, before any execution |
| Work | Deterministic risk classification; gate table; Approval Token mint/validate; default-deny policy loading |
| Definition of Done | I-7 (never LLM self-report), I-11 (token scoped/consumable/invalidated), RFC-0001 §8.2 (default-deny) tests pass; P8/P9/P10/P13 conformance |
| RFC basis | RFC-0008 §6–§8, §10, §13; RFC-0002 §9; RFC-0001 §8 |

### 8.8 Iteration 7 — `executor` + `audit`

| Item | Value |
|---|---|
| Goal | Execution under a token, recorded before its consequence |
| Work | Sanctioned Action runner with guardrails and scoped elevation; append-only Audit store, record writers, transcript derivation |
| Definition of Done | I-1/I-5/I-11 (executor) and I-13/AU8 (audit) conformance; a consequence with a failed audit write is blocked and disclosed (AU8); transcript derives from the record only (RFC-0013 §8) |
| RFC basis | RFC-0004 §4.9; RFC-0002 §2.8, invariant 13; RFC-0013 §7–§22; RFC-0001 §8.6 |

### 8.9 Iteration 8 — `context`

| Item | Value |
|---|---|
| Goal | Bounded, secret-free reasoning material and the Provider View |
| Work | Deterministic assembly (§12); boundary enforcement (§13); consented Memory; Provider View builder |
| Definition of Done | CM1–CM16 conformance; the Provider View is the only outward channel (PR14); no secret in Context (SC2); re-assembly on loss (CM13) |
| RFC basis | RFC-0012 §12, §13, §21; RFC-0010 §3 |

### 8.10 Iteration 9 — `providers` + `skills`

| Item | Value |
|---|---|
| Goal | The extension axes, gated |
| Work | Uniform provider interface, structured-output validation, one vendor adapter; Skill loader/authenticator/activator wired to the gate |
| Definition of Done | PR11 (malformed degrades, never crashes), PR14 (View is only channel), F6 (never a Fact); SK4 (every Skill Action passes the gate), SK5 (untrusted until authenticated), SC5 (no secret) — all pass |
| RFC basis | RFC-0010 §2–§8; RFC-0011 §4, §22, §23 |

### 8.11 Iteration 10 — `core` (the loop)

| Item | Value |
|---|---|
| Goal | The runtime that composes every package |
| Work | State machine, event loop, consultation router, replanning, recovery |
| Definition of Done | **State-machine conformance**: only RFC-0002 §3 transitions reachable; invariants 1–15 hold in every state; recovery ordering is determinism→disclosure→decision→action (§10); a full-loop integration test mirrors `docs/core-execution-walkthrough.md` §3 and all 31 failure scenarios mirror `docs/failure-injection-walkthrough.md` §3 |
| RFC basis | RFC-0002 §1–§10 |

### 8.12 Iteration 11 — the MVP gate (deferred, not decided here)

| Item | Value |
|---|---|
| Goal | Ratify the MVP boundary and the build order |
| Work | **None of this blueprint's**: RFC-0019 must define the MVP ("the smallest safe core loop… and, just as explicitly, everything it excludes", RFC-0000 §4); RFC-0020 must ratify the build order and concurrency model; RFC-0015 must fix the interaction contract |
| Definition of Done | RFC-0015, RFC-0019, RFC-0020 Accepted; RFC-0005–0013 and RFC-0021 Accepted; only then does Iteration 12 begin |
| RFC basis | RFC-0000 §4 (RFC-0019, RFC-0020 entries), §5 |

### 8.13 Iteration 12 — production MVP

| Item | Value |
|---|---|
| Goal | The smallest safe core loop, as RFC-0019 defines it |
| Work | Production `cli` per RFC-0015; hardening each package per RFC-0020's build order; release gates |
| Definition of Done | RFC-0019's MVP definition met; all Required-RFC invariants conformance-clean; validator exits 0 |
| RFC basis | RFC-0019 (future), RFC-0020 (future), RFC-0015 (future); every package per §3 |

---

## 9. Risk Analysis for Implementation Order

Risks are ranked; each is grounded in the corpus, not invented.

| # | Risk | Grounding | Severity | Mitigation |
|---|---|---|---|---|
| 1 | **Production code blocked on missing RFCs** — RFC-0015/0019/0020 do not exist | RFC-0000 §5 requires them Accepted before code | Critical | Iterations 0–10 are scaffold + conformance only; the gate is explicit (§8.12); nothing production-facing is merged before it |
| 2 | **RFC-0005–0013 and RFC-0021 are Draft, not Accepted** — implementation against them risks rework | Status headers of the files; RFC-0000 §3 status column | High | Iterations target Draft documents' *invariants* (which are Draft-specific and may change); conformance tests are re-run at each Draft revision; no production code depends on Draft wording until acceptance |
| 3 | **RFC-0014 amending RFC-0002** — the one deferred RFC most likely to amend an accepted one | RFC-0000 §6 item 8; RFC-0000 §9 item 2 | High | `core`'s interruption/recovery (I-8, I-15) is written against RFC-0002 as-is; a decision record for RFC-0014's core semantics should be agreed early (RFC-0000 §6 item 8) |
| 4 | **Blast-radius RFCs written too late** — RFC-0008 and RFC-0005 are the top two | RFC-0000 §6 items 1, 3 | High | Their packages (`policy`, `factlayer`) are built first in the scaffold (Iterations 1–7), mirroring the writing order |
| 5 | **The gate becoming a bottleneck** — RFC-0000 as "a committee" | RFC-0000 §9 item 4 | Medium | The roadmap is meant to be amended mechanically; iterations do not wait on RFC-0000 approval, only on the RFCs themselves |
| 6 | **Authority-matrix violations in wiring** — a package importing a forbidden authority | RFC-0004 §7 (F cells); §4.2 here | High | The import-lint (forbidden edges, §4.2) runs in CI from Iteration 1 onward |
| 7 | **Verification theater** — executor built before verification semantics | RFC-0000 §5 domain-spine rationale | High | `verification` (Iteration 4) precedes `executor` (Iteration 7); the executor is never allowed to verify itself (V1) |
| 8 | **Concurrency mistakes** — the single-goal serial lifecycle violated | RFC-0002 §1; RFC-0002 §11 item 15 (open) | Medium | Serial execution is enforced in `core`'s state machine; concurrent read-only collection remains Unknown until RFC-0020 |
| 9 | **Secret leakage at a boundary** during the Context/Provider join | RFC-0009 §0; RFC-0010 §3 | Critical | `secrets` (Iteration 5) precedes `context` (Iteration 8) and `providers` (Iteration 9); SC2–SC5 are boundary tests, not unit tests |

**Ordering rationale.** The iteration order mirrors RFC-0000 §7's writing order
(foundations → safety spine → domain spine → providers/secrets → extension →
runtime support → gate), because the roadmap already reasoned that this is the
order in which decisions are safe to depend on. This blueprint borrows that
reasoning; RFC-0020 retains the authoritative final word.

---

## 10. Proof of Traceability: Every Artifact Has Exactly One Owner

**Claim.** Every implementation artifact in §2–§7 traces to exactly one
architectural owner (RFC, section, and invariant family). No artifact has two
normative owners (RFC-0004 §3: "one owner per row, no delegation into
self-extension").

| Artifact | Owning RFC | Owning section(s) | Protected by |
|---|---|---|---|
| `schema/fact.py` | RFC-0005 | §3, §4, §5, §12 | F1–F16 |
| `schema/action.py` | RFC-0003 | §2.6 (Action/Step/Proposal/Plan) | (vocabulary) |
| `schema/outcome.py` | RFC-0006 | §7 | V5–V7, V9, V15 |
| `systemmodel/*` | RFC-0021 | §2, §4, §6, §11 | (supported-platform promise) |
| `trust/*` | RFC-0007 | §10, §11, §15 | T1–T12; S1–S8 |
| `collectors/*` | RFC-0005 | §2; RFC-0003 §2.4 | (Collector definition) |
| `factlayer/*` | RFC-0005 | §2, §4, §5, §7, §12 | F1–F16; RFC-0004 A4 |
| `verification/*` | RFC-0006 | §6, §7, §8 | V1–V16; RFC-0002 invariant 2 |
| `secrets/*` | RFC-0009 | §0, §3, §11, §13, §15, §27 | SC1–SC16 |
| `policy/*` | RFC-0008 | §6, §7, §8, §10 | P1–P14; RFC-0002 invariants 7, 11, 12, 13 |
| `executor/*` | RFC-0004 §4.9 / RFC-0002 §2.8 | §4.9; §2.8 | I-1, I-5, I-11; P12; SC10 |
| `audit/*` | RFC-0013 | §7–§22 | AU1–AU16; RFC-0002 invariant 13; SC4 |
| `context/*` | RFC-0012 | §12, §13, §21 | CM1–CM16; SC2; PR14 |
| `providers/*` | RFC-0010 | §2–§8 | PR1–PR16; F6; SC3 |
| `skills/*` | RFC-0011 | §4, §22, §23 | SK1–SK16; SC5 |
| `core/*` | RFC-0002 | §1–§10 | invariants 1–15 |
| `cli/*` | RFC-0001 §5 | §5 Presentation | (presentation; interface per RFC-0015) |

**The two-owner check.** Where an artifact is touched by two RFCs (for example
`executor` = RFC-0004 profile + RFC-0002 state), the *authority* is owned by
RFC-0004 §4.9 and the *state behavior* by RFC-0002 §2.8 — two distinct
properties of one package, each with one owner, never one property with two
owners. The same split holds for `factlayer` (truth: RFC-0004 §4.6; pipeline:
RFC-0005), `context` (profile: RFC-0004 §4.11; assembly: RFC-0012), and
`audit` (profile: RFC-0004 §4.12; records: RFC-0013). This is exactly the
"no two RFCs would own the same question" rule of RFC-0000 §9 item 6: the
earlier-accepted document wins the shared question and the later references it.

---

## 11. Consistency Review and Ambiguity Report

This document was reviewed against RFC-0000–RFC-0013, RFC-0021, the Core
Execution Walkthrough, the Failure Injection Walkthrough, and the Decision
Traceability Matrix. Findings:

### 11.1 Status finding (blocks production)

- **RFC-0000 §5** requires RFC-0015, RFC-0019, RFC-0020 Accepted before
  production code. **None of the three exists.** This is the single binding
  constraint on §8; the blueprint honors it by ending at the gate (§8.12).
- **RFC-0005–0013 and RFC-0021 are Draft**, not Accepted. Their invariants are
  used as the conformance oracle; if a Draft changes, conformance tests change
  with it. This is a risk (§9 #2), not a contradiction.

### 11.2 Ambiguities reported (not invented)

| # | Ambiguity | Why it cannot be resolved here | Owning RFC |
|---|---|---|---|
| 1 | **The MVP boundary** ("smallest safe core loop… everything it excludes") | RFC-0000 §4 names RFC-0019 as the only document that may define it | RFC-0019 (does not exist) |
| 2 | **The Operator interface contract** (presentation form, disconnect semantics, approval UX) | RFC-0000 §4 names RFC-0015 | RFC-0015 (does not exist) |
| 3 | **The authoritative build order and concurrency model** | RFC-0000 §4 names RFC-0020; this blueprint's §8 is a translation, not the owner | RFC-0020 (does not exist) |
| 4 | **Concrete API/schema signatures** | RFC-0005 §3, RFC-0008, RFC-0010 §3, RFC-0011, RFC-0012, RFC-0013 all explicitly declare "no schemas here" | RFC-0020 |
| 5 | **Phase budgets, retry counts, per-phase timeouts** | RFC-0002 §11 items 2–3 are open; RFC-0010 §8 references them | RFC-0002 / RFC-0020 |
| 6 | **Degraded-mode scope** (how much a facts-only session can do) | RFC-0002 §11 item 11 is open | RFC-0002 / RFC-0010 |
| 7 | **Concurrent read-only collection** | RFC-0002 §11 item 15 is open | RFC-0002 / RFC-0020 |
| 8 | **Resume/persistence semantics** (what survives a reboot beyond the resume marker) | RFC-0000 §4, RFC-0012 §21 defer to RFC-0014 | RFC-0014 (does not exist) |
| 9 | **Whether the current Draft RFCs will change before acceptance** | Cannot be proven from the corpus; depends on the review process (RFC-0003 Part II) | RFC-0003 process |

### 11.3 Consistency confirmations

- The package map (§2) is a bijection onto RFC-0001 §5's component list plus the
  cross-cutting model RFCs; no component is duplicated, none is missing.
- The dependency rules (§4.2) are the RFC-0004 §7 matrix rendered as imports;
  no allowed edge violates a matrix cell, and no forbidden edge is permitted in
  the allowed graph.
- The invariant-coverage claims (§7) match the Decision Traceability Matrix §3:
  each family is defined exactly once and consumed by its dependents.
- The iteration order (§8) is RFC-0000 §7's writing order mirrored onto
  packages; the roadmap's own rationale (§9 of that document) is preserved.
- The failure scenarios of the Failure Injection Walkthrough (§3) map to
  conformance tests at the responsible packages (§7), so the 31 scenarios are
  testable without inventing behavior.

---

## End State

This blueprint translates RFC-0000–RFC-0013 and RFC-0021 into a package layout,
a dependency discipline that encodes the authority matrix, a per-package
conformance-test strategy, and an iteration plan that respects the corpus's own
gate: **no production code until RFC-0015, RFC-0019, and RFC-0020 are Accepted
and the Drafts are ratified** (RFC-0000 §5). It adds no architecture, modifies
no RFC, and reports every ambiguity to its owning document instead of resolving
it. The proof in §10 shows every artifact has exactly one owner. When RFC-0019
and RFC-0020 land, this document becomes a draft of the content they must
ratify — not a substitute for them.
