# Iteration 12 — Design Review (CLI / Presentation Layer)

> **Document type:** Implementation design review, at the same rigor as
> Iterations 2–11. **Not an RFC, not code.**
> **Read this first:** This document **defines no new architecture, modifies no
> RFC, invents no behavior, and writes no production code.** It translates the
> frozen corpus (RFC-0000–0013, RFC-0021, the decision traceability matrix,
> `docs/architecture-implementation-blueprint.md`, and the ratified
> `docs/implementation-decision-notes.md` DN-1…DN-95) into an implementation
> plan for the **Presentation layer — the `cli` package** (blueprint §2, §4.1,
> §4.2, §5; RFC-0001 §5). Where the corpus does not decide something, this
> document **reports** it as an ambiguity or a question; it does not resolve it.
>
> **Status of sources.** Only RFC-0000, RFC-0001, RFC-0002, RFC-0003, RFC-0004
> are **Accepted**. RFC-0005 through RFC-0013 and RFC-0021 remain **Draft**
> (verified against every header, 2026-08-11), exactly as they were for
> Iterations 9–11. RFC-0015 (the Operator Interface & Interaction Contract) is
> **Planned** — it does not exist (RFC-0000 §3 row 0015, "Planned"), and the
> blueprint §5 defers the CLI's interface details to it. The Iteration-10/11
> posture therefore applies: conformance to the invariants, the scaffold
> posture, the concrete interaction contract rework risk recorded, none of the
> Drafts re-opened here. Blueprint §8.0's gate stands — production code begins
> only after RFC-0015/0019/0020 and the Drafts are Accepted; this iteration
> keeps the scaffold posture of Iterations 1–11 (I/O-free, injected primitives,
> conformance-enforced).
>
> **Scope decision (reported — Q1).** Blueprint §8.12 still reads "Iteration 11
> — the MVP gate" and §8.13 "Iteration 12 — production MVP", while DN-45
> re-ordered the build and the Iterations 9–11 closeouts place `cli` (Layer 7)
> at Iteration 12; the consistency report records that "The next iteration is
> `cli` (Layer 7; blueprint §8.12) — the only importer of `core`." Iterations
> 10–11 executed the identical supersession for §8.10/§8.11; this task does the
> same for §8.12/§8.13 (Q1). The re-order is dependency-safe: `cli` imports
> `core`, `audit`, `context`, `schema` only (blueprint §4.1) and nothing imports
> `cli`.

---

## 1. Architectural consistency review

### 1.1 Scope (blueprint §2, §5, §8.13; RFC-0001 §5, transcribed)

| Item | Value |
|---|---|
| Goal | The only interface: render conversation/state, present evidence and proposals, collect approvals/refusals/input, expose the audit log and the context view (RFC-0001 §5 Presentation) |
| Work | The presentation model (`render`), operator decision collection (`collect`), audit/context exposure (`expose`) |
| Definition of Done | Presentation-only: risk tone is presentation, never policy (RFC-0001 §5); decisions are collected and returned to `core`, never decided (RFC-0004 §7: Presentation not an actor in the matrix); the session is driven only through `core`'s `advance`/`pump` seam (blueprint §5 — "the only entry point the `cli` uses"); audit/context exposure is read-only and secret-free (RFC-0009 SC-series); no production I/O in any `cli` file (DN-55/DN-94 posture) |
| RFC basis | RFC-0001 §5; RFC-0002 §4.1 (operator events); RFC-0004 §7 (not an actor); RFC-0013 §7/§8 (records, transcript); RFC-0012 §13 (Provider View); RFC-0009 SC2/SC3/SC4/SC16 (secrets) |

Blueprint §3 (responsibilities): "*Presentation collects decisions and renders
state; it never classifies, executes, or holds secrets* (RFC-0001 §5; RFC-0004
§7: Presentation not an actor in the matrix)." Blueprint §5 (public contract):
"*Render, collect Operator decisions/input, expose audit/context view* —
RFC-0001 §5 Presentation; interface details deferred to RFC-0015." Blueprint §2
module set: `cli` = `render.py`, `collect.py`, `expose.py`. Blueprint §4.1:
`cli` = {`core`, `audit`, `context`, `schema`}; blueprint §4.2: `cli` never
{classify, execute, hold secrets}.

**The enforcement halves this layer inherits (DoD of this iteration, never
deferred again).** Iterations 5–11 recorded, not dropped, every presentation
half that binds `cli`; each becomes a Definition of Done item here:

1. **Presentation-only tone.** Risk levels translate into *presentation* tone
   and layout only, never into policy (RFC-0001 §5); the CLI never classifies,
   never gates, never blocks, never overrides (RFC-0004 §7).
2. **Decision collection, not decision.** The Operator approves/refuses/refines;
   the CLI *collects* the decision and returns it to `core` as the
   RFC-0002 §4.1 operator event. The CLI is not an actor in the matrix; every
   decision cell is the Operator's or `core`'s routing, never the CLI's.
3. **The single `core` seam.** The CLI drives the session only through the
   `core` surface (`Session`, `advance`/`pump`, `LoopStep`, `Refusal`); it never
   re-implements routing, state transitions, classification, or recovery.
4. **The provider-world/machine-world separation.** The CLI presents what the
   owned surfaces expose — the `LoopStep` boundary trace, the audit transcript,
   the Provider View — never raw provider/skill output (I-4, I-5, I-7) and never
   a command construction.
5. **Read-only, secret-free exposure.** The audit log is presented through the
   RFC-0013 §8 transcript (metadata only, SC4); the context view through the
   RFC-0012 §13 Provider View (SC3); no secret value ever leaves (SC2/SC3/SC4/
   SC16).

**Constraint (dependency).** `cli` may import `core`, `audit`, `context`,
`schema` (blueprint §4.1) and is imported by nothing. Its C1–C3 *fill* the three
Iteration-0 scaffolds (`render`, `collect`, `expose`) with **no new module** and
**no change to the allowed/forbidden graph** — the dependency test already
sanctions `ALLOWED["cli"] = {core, audit, context, schema}`,
`FORBIDDEN["cli"] = {policy, executor, factlayer, providers, skills, secrets}`,
and the acyclicity test already passes. Because `policy` is forbidden, the risk
class/gate arrive at the CLI as **data** inside the audit records
(`ApprovalRecord.risk_class`/`gate`, RFC-0013 §7 cat. 4) — the RFC-0004 §3
consume-as-values doctrine — never via a `policy` import.

### 1.2 Out of scope (recorded, not dropped)

| Item | Owned by | Gate |
|---|---|---|
| The TUI's semantic interaction contract (how states/evidence/approvals are presented *semantically*, the approval experience, degraded-mode presentation, progress/status) | RFC-0001 §5; blueprint §5 | RFC-0015 |
| The visual/terminal surface — widgets, keybindings, layout, colors, async I/O loop | RFC-0001 §5 | RFC-0015 / RFC-0020 |
| Public API signatures, serialization, wire/display formats | blueprint §5 | RFC-0020 (DN-1 precedent) |
| User-facing configuration and defaults UI | RFC-0000 §3 (0016) | RFC-0016 |
| Anything policy, execution, fact, provider, skill, or secret logic | RFC-0004 §7 | Forbidden to `cli` (§4.2) |

### 1.3 What exists already

The `cli` package (`{__init__,render,collect,expose}.py`) was scaffolded in
Iteration 0 with ownership docstrings only (blueprint §2). `tests/test_packages.py`
already imports and docstring-checks it; `tests/test_dependency_rules.py` already
carries the `cli` allowed/forbidden rows with no violation and the acyclicity
test already passes — so the tree/edge tests stay green from C1's first import
onward. The runtime surfaces `cli` consumes are complete and conformance-tested:
`core` (`Session`, `Step`, `Prerequisites`, the §4.1 operator events, `Loop`,
`LoopStep`, `advance`, `pump`, `Refusal`, `Workstate`, `Consultation` — Iteration
11), `audit` (`AuditRecord` family, `RecordCategory`, `ApprovalRecord` with
`risk_class`/`gate`, `transcript.render`, `TranscriptCategory`, `TranscriptEntry`,
`AuditStore`, `StoreStatus` — Iteration 8), `context` (`ProviderView`,
`ProviderViewOutcome`, `derive` — Iteration 9), `schema` (`Action`, `Plan`,
`Step`, `Proposal`, `PostCondition`, `VerificationOutcome` — Iteration 1).
`tests/test_core_imports.py` already asserts the "only `cli` imports `core`" AST
edge. Baseline: **3404 tests, green**, branch `iteration/11-core`, HEAD
`c86b7b6` (Iteration 11 closeout), working tree clean except the two pre-existing
untracked files `HANDOFF.md` and `uv.lock`; branch `iteration/12-cli` derives
from `c86b7b6`.

---

## 2. RFC consistency review

| RFC | Section | Implemented as | Status in layer |
|---|---|---|---|
| RFC-0001 | §5 Presentation | The layer's charter: render, present evidence/proposals, collect approvals/refusals/input, expose audit/context, tone-only risk translation | Transcribed (charter) |
| RFC-0002 | §4.1 (operator events) | `collect` maps an Operator decision to the corresponding operator event; `core` refuses the inapplicable | Implemented (C2) |
| RFC-0004 | §7 authority matrix | Presentation is **not an actor**; no cell is granted; the CLI only renders and collects | Conformance (C4) |
| RFC-0013 | §7 (record categories), §8 (transcript) | `expose` presents the audit log through the transcript's five §8 categories, derived from the record only (AU2), metadata-only (SC4) | Implemented (C3) |
| RFC-0012 | §13 Provider View | `expose` presents the context view through the Provider View (SC3); the CLI never assembles a View itself | Implemented (C3) |
| RFC-0009 | SC2, SC3, SC4, SC16 | No secret value in the presented state, the exposed context, or the audit exposure; privacy parity | Conformance (C4) |
| RFC-0003 | §2 vocabulary | The CLI presents owned vocabulary only; it never invents presentation names for corpus concepts | Consumed |
| RFC-0015 | (Planned) | The semantic interaction contract; this iteration records the semantic model and defers the contract | Deferred (§1.2) |
| Walkthroughs | execution/failure | The session surface the CLI presents is the `core` oracle's boundary trace; `cli` itself has no walkthrough oracle (the runtime's) | Consumed |

**Resolved by the corpus (not re-opened here):**

- **The CLI is not an actor.** RFC-0004 §7 lists no Presentation row; blueprint
  §4.2 states "Presentation not an actor in the matrix." The CLI presents the
  Operator's view and collects the Operator's decisions; the decision authority
  is the Operator's, the routing is `core`'s. Not a question.
- **Tone is presentation, never policy.** RFC-0001 §5: "Translate risk levels
  into *presentation* tone and layout (never into policy)." The tone is derived
  from the risk-class/gate *names* the records carry; it never alters a gate,
  never classifies, never blocks. Not a question.
- **The session entry point is `core`'s alone.** Blueprint §5: `core` is "the
  only entry point the `cli` uses." The CLI drives the session through
  `advance`/`pump` and emits operator events; it never constructs internal
  session/state/recovery logic. Not a question.
- **No secret crosses the presentation boundary.** RFC-0009 SC2/SC3/SC4: secret-
  free Context, secret-free Provider View, metadata-only Audit. The CLI presents
  metadata and records, never values. Not a question.
- **The audit log is the transcript's.** RFC-0013 §8: the Transcript presents
  exactly the five categories, each derived from the record only (AU2). The CLI
  presents the transcript, not the raw store internals. Not a question.

---

## 3. Layer placement

`cli` is **Layer 7** (blueprint §4.1), the top of the stack: it imports `core`
(Layer 6), `audit`/`context` (Layer 4), and `schema` (Layer 0), and is imported
by nothing. Blueprint §4.2's `cli` row forbids `policy`, `executor`, `factlayer`,
`providers`, `skills`, `secrets` outright (import-level). This is the first
layer with a genuine import-ban list (§5), enforced by the C4 conformance test.

- **`cli → core`**: the session seam. The CLI renders the `LoopStep` boundary
  trace (`session`, `writes`, `consultations`, `disclosures`) and emits
  operator events (RFC-0002 §4.1) through `advance`. This is the *only* live
  conductor edge the CLI sees.
- **`cli → audit`**: the record/transcript edge. The CLI exposes the audit log
  through `audit.transcript.render` (RFC-0013 §8) — read-only, metadata-only
  (SC4). The CLI never writes a record (the write is `core`'s, DN-88).
- **`cli → context`**: the Provider View edge. The CLI exposes the context view
  through the `ProviderView` type (RFC-0012 §13; SC3). The CLI never assembles a
  View (that is `context`'s, Iteration 9).
- **`cli → schema`**: the vocabulary edge. The CLI presents `schema` types
  (`Action`, `Plan`, `Step`, `Proposal`, `VerificationOutcome`) as owned values.
- **No `cli →` lower authority.** `policy`, `executor`, `factlayer`, `providers`,
  `skills`, `secrets` are forbidden (§4.2); risk-class/gate arrive as record
  data (RFC-0004 §3), never via import.

**Behavioral conformance surface (C4).** `cli`'s non-actor cells are tested by
`test_cli_conformance`: the CLI never invokes classification, verification,
approval, or execution logic; it presents the tone derived from record data, not
a gate decision; and it returns decisions to `core` as events, never as an
internal state change.

---

## 4. Ownership map

The Presentation *responsibility* (RFC-0001 §5) and the *non-actor* doctrine
(RFC-0004 §7) are two properties of one package, each with one owner (blueprint
§10's two-owner check). Module ownership:

| Module | Owning RFC sections | Protected by |
|---|---|---|
| `cli/render.py` | RFC-0001 §5 | the presentable-state model (session state, disclosures, evidence/proposals); the risk-class/gate → presentation-tone map; never a policy decision |
| `cli/collect.py` | RFC-0001 §5; RFC-0002 §4.1 | the Operator-decision → operator-event mapping; free-text payloads; inapplicable events are refused by `core` (a `Refusal` is presented, not swallowed) |
| `cli/expose.py` | RFC-0001 §5; RFC-0013 §8; RFC-0012 §13 | read-only exposure: the audit transcript's five categories and the Provider View; secret-free (SC-series); no write path |
| `audit` (invoked) | RFC-0013 §7/§8/§21 | the record's integrity; the transcript's derivation (AU2) |
| `context` (invoked) | RFC-0012 §13 | the Provider View's secret-free assembly (SC3) |

**Authority table (RFC-0004 §7).** Presentation appears in **no** row: every
cell is F-by-absence. The CLI renders and collects; the Operator decides, `core`
routes, the CLI presents the outcome. The only "decision" the CLI models is
*which operator event to emit from the collected decision* — a deterministic
transcription of RFC-0002 §4.1, never a policy/approval/execution judgment.

**Two-owner checks.** (a) *Tone vs policy:* RFC-0001 §5 owns the presentation
tone; RFC-0008 owns the risk classes and gates — the CLI consumes the class/gate
*names* as data and never re-implements their meaning. (b) *The audit exposure
vs the record:* the CLI *presents* (RFC-0013 §8), `audit` owns the record and its
integrity (RFC-0013 §21) — Q5. (c) *The collection vs the decision:* the CLI
collects (RFC-0001 §5), `core` routes the resulting event (RFC-0002 §4.1/§5) —
Q4.

---

## 5. Dependency analysis

`ALLOWED["cli"] = {core, audit, context, schema}` and `FORBIDDEN["cli"] =
{policy, executor, factlayer, providers, skills, secrets}` are already declared
in `tests/test_dependency_rules.py` and the graph is acyclic. The C4 conformance
test adds the exact-rules AST enforcement (`test_cli_imports.py`): each `cli`
file imports only the four sanctioned packages, the closed stdlib allowlist
(types only), and carries no banned I/O/clock/random/network token (DN-55/DN-94;
RFC-0007 S7).

**The one edge to keep on purpose.** `core` is consumed by `cli` alone (blueprint
§5; the C5 "only `cli` imports `core`" AST edge in `tests/test_core_imports.py`).
Iteration 12 adds **no** new edge anywhere: `cli`'s edges were declared in
Iteration 0 and are merely *filled* by C1–C3.

**Data, not imports.** The forbidden packages' *values* still reach the CLI as
data: risk-class/gate names in `ApprovalRecord` (RFC-0013 §7 cat. 4), the
Provider View built by `context` (RFC-0012 §13), the transcripts derived by
`audit` (RFC-0013 §8). This is the RFC-0004 §3 consume-as-values doctrine — the
same posture `core` uses for its routed values.

---

## 6. Public surface analysis

Reported, not ratified — final signatures are RFC-0015/RFC-0020's (DN-1). The
C1–C3 shapes:

- `cli/render.py` — the presentable-state model. Pure functions over the owned
  surfaces: a presented session state (the RFC-0002 state + goal + a disclosure
  trace + a presentation tone) derived from `LoopStep`; presented evidence and
  proposals from the boundary records (`AuditRecord`) and `schema` types; the
  closed risk-class/gate → tone mapping. No I/O; the source values are injected.
- `cli/collect.py` — the decision collection. A closed `Decision` vocabulary
  (approve, reject, override, refine, reply, cancel, interrupt, exit, view) with
  an optional free-text payload; a deterministic mapping to the RFC-0002 §4.1
  operator events; the inapplicable event surfaces as `core`'s `Refusal`,
  re-presented (I-9: never fabricated).
- `cli/expose.py` — the read-only exposure. The audit log as the transcript's
  five categories (RFC-0013 §8) via `audit.transcript.render`; the context view
  as the `ProviderView` (RFC-0012 §13); both secret-free by construction
  (SC2/SC3/SC4). No write path; no raw store internals.

The surface is deterministic, I/O-free (sources injected), read-only, and
authority-free; it adds no authority cell to the matrix (RFC-0004 §7).

---

## 7. Boundary analysis

- **The `core` seam.** The CLI's only interaction with the runtime is
  `advance`/`pump` → `LoopStep`/`Refusal` and the operator events it emits. It
  never holds a `Session` and mutates it, never builds a `Workstate`, never runs
  a recovery reaction, never classifies (I-7). A `Refusal` from `core` is
  presented honestly (I-9), never swallowed.
- **The tone seam.** The risk-class/gate *names* from the records map to a
  closed presentation-tone vocabulary. The mapping is total, deterministic, and
  one-directional: a tone can never change a gate, mint a token, or block
  (RFC-0001 §5 "never into policy"; RFC-0004 §7).
- **The secret seam.** SC2/SC3/SC4/SC16: the presented state, the exposed
  context View, and the audit exposure are all secret-free by construction; the
  CLI presents metadata and records, never values, and never re-redacts (the
  redaction is `secrets`'/`context`'s, and `secrets` is forbidden to `cli`).
- **The read-only exposure.** `expose` presents the transcript and the View; it
  never appends to the audit store (the write is `core`'s, DN-88) and never
  alters Context or Memory. The `AuditStore`'s durable lifecycle (Export/
  Retained/Deleted) is RFC-0020's (§1.2).
- **No command construction.** The CLI renders, it never composes a command
  string or passes free text into anything executable (I-5); free text collected
  in `collect` travels only as the payload of the RFC-0002 §4.1 reply/refine
  events.

---

## 8. Required invariants

| Invariant | Normative source | `cli`'s method | Machinery owner |
|---|---|---|---|
| I-4 — LLM only through a Provider View | RFC-0002 §9; RFC-0010 PR14 | presents the View; never raw provider text | `context` |
| I-5 — No untrusted text interpolated into a command | RFC-0002 §9 | renders; never composes a command | all |
| I-7 — Risk classification deterministic, never LLM self-report | RFC-0002 §9 | tone is derived from record data; never classifies | `policy` |
| I-9 — The runtime never fabricates | RFC-0002 §9 | a `Refusal`/gap is presented honestly, never filled | `audit` |
| I-13 — Audit written before the consequence | RFC-0002 §9; RFC-0013 §23 | the CLI never writes; it presents the record after | `core` (DN-88) |
| SC2 — The default is secret-free | RFC-0009 | the presented state is secret-free by construction | `context` |
| SC3 — No secret enters a Provider View | RFC-0009; RFC-0010 §11 | `expose` presents the already-secret-free View | `context` |
| SC4 — No secret enters the Audit | RFC-0009; RFC-0002 I-4 | `expose` presents metadata only | `audit` |
| SC16 — Privacy parity | RFC-0009 | personal data treated as secret until demotion | `context` |
| RFC-0004 §7 — not an actor | RFC-0004 §7 | no authority cell; render + collect only | C4 conformance |

The C4 conformance suite asserts the presentation boundary in every presentable
state where the invariant applies, and the banned-import/token oracles assert
the "never" halves structurally (no `policy`/`executor`/`secrets` import, no
I/O token).

---

## 9. Ambiguities

Each is reported, not resolved; each names the corpus silence that forces the
report and the owner that answers it. "Blocking?" marks whether it elevates to a
blocking question in §10.

| # | Subject | RFC §/location | Open question | Alternative readings | Owner | Blocking? |
|---|---|---|---|---|---|---|
| A1 | Iteration scope / renumbering + the MVP gate | blueprint §8.12/§8.13; DN-45 | §8.12 reads "Iteration 11 — the MVP gate" (DoD: production begins only after RFC-0015/0019/0020 Accepted) and §8.13 "Iteration 12 — production MVP", while the closeouts place `cli` at Iteration 12. | (a) implement `cli` at Iteration 12 under the scaffold posture, recording the supersession (b) stop and renumber the blueprint / wait for RFC-0015 | DN-45; blueprint §8.12/§8.13 | **Yes (Q1)** |
| A2 | The semantic-vs-visual split | RFC-0000 §3 (0015); blueprint §5 | RFC-0015 (the *semantic* interaction contract) is Planned; what does this iteration build without it? | (a) the I/O-free semantic model (in-memory types per DN-1), visual/interaction to RFC-0015 (b) nothing until RFC-0015 is accepted | RFC-0015; RFC-0000 §3 | **Yes (Q2)** |
| A3 | The presentable-state source | RFC-0001 §5; RFC-0002 §4; RFC-0013 §7/§8; RFC-0012 §13 | Which surfaces may the CLI render, and as what model? | (a) the owned surfaces only (`LoopStep` trace, the §8 transcript, the §13 View, `schema` types), derived deterministically (b) also raw provider/skill/machine data | RFC-0001 §5; I-4/I-5/I-7 | **Yes (Q3)** |
| A4 | The decision-collection model | RFC-0002 §4.1; RFC-0001 §5 | How is a collected Operator decision modeled and returned to `core`? | (a) a closed decision vocabulary mapped to the §4.1 operator events; inapplicable events refused by `core` (b) a free-form input pass-through | RFC-0002 §4.1 | **Yes (Q4)** |
| A5 | The audit/context exposure | RFC-0013 §8; RFC-0012 §13; RFC-0009 | What exactly does "expose the audit log and context view on demand" present? | (a) the five §8 transcript categories + the §13 Provider View, read-only and secret-free (b) raw store/view internals | RFC-0013 §8; RFC-0012 §13; SC-series | **Yes (Q5)** |
| A6 | The risk-tone translation surface | RFC-0001 §5; RFC-0008; RFC-0013 §7 | "Translate risk levels into presentation tone" — what is the concrete closed tone vocabulary, and its input? | (a) a closed tone enum mapped from the record-carried risk-class/gate *names*; presentation-only (b) a free-form rendering of policy internals | RFC-0001 §5; RFC-0004 §7 | **Yes (Q6)** |
| A7 | The `core` seam | blueprint §5; RFC-0002 §4.1/§5 | Exactly how does the CLI drive the session and emit operator events? | (a) through `advance`/`pump` only, emitting §4.1 events; inapplicable events surface as `Refusal` (b) direct state/event construction | blueprint §5 | **Yes (Q7)** |
| A8 | Testability at zero I/O | blueprint §7; DN-55/DN-94 | A presentation layer is an I/O surface; how is it tested deterministically? | (a) inject the sources (LoopStep, records, View) and assert pure presentable outputs (DN-55 precedent) (b) build a real terminal I/O loop now | DN-55/DN-94; RFC-0007 S7 | **Yes (Q8)** |

---

## 10. Blocking questions

| Q | Question | Owner (RFC §) | Blocks | Sev. | Recommended resolution |
|---|---|---|---|---|---|
| Q1 | Iteration scope / renumbering + the MVP gate (A1) | DN-45; blueprint §8.12/§8.13 | C0 | Med | **`cli` is Iteration 12.** Implement per DN-45 and the Iteration 11 closeout; record the supersession of the §8.12/§8.13 labels (as §8.10/§8.11 were); the scaffold posture keeps the gate's *production* meaning standing until RFC-0015/0019/0020 |
| Q2 | The semantic-vs-visual split (A2) | RFC-0000 §3 (0015); DN-1 | C1 | High | **Semantic model now, contract deferred.** Build the I/O-free in-memory presentation model (DN-1 precedent: types, not formats/APIs); RFC-0015 owns the semantic interaction contract, RFC-0020 the signatures/formats |
| Q3 | The presentable-state source (A3) | RFC-0001 §5; I-4/I-5/I-7 | C1 | High | **Owned surfaces only.** Render from the `LoopStep` boundary trace, the RFC-0013 §8 transcript, the RFC-0012 §13 Provider View, and `schema` types — never raw provider/skill/machine data |
| Q4 | The decision-collection model (A4) | RFC-0002 §4.1 | C2 | High | **Closed vocabulary → §4.1 events.** A decision (approve/reject/override/refine/reply/cancel/interrupt/exit/view) maps to its operator event with free-text payloads; inapplicable events are refused by `core` and the `Refusal` is presented |
| Q5 | The audit/context exposure (A5) | RFC-0013 §8; RFC-0012 §13; RFC-0009 | C3 | Med | **Transcript + View, read-only.** Expose the five §8 categories via `audit.transcript.render` and the §13 View via `context`; secret-free (SC2/SC3/SC4); no write path |
| Q6 | The risk-tone translation surface (A6) | RFC-0001 §5; RFC-0004 §7 | C1 | Med | **Closed tone from record data.** A tone enum mapped from the `risk_class`/`gate` names the records carry; presentation-only — never a gate change, a mint, or a block |
| Q7 | The `core` seam (A7) | blueprint §5; RFC-0002 §4.1 | C2 | Med | **`advance`/`pump` only.** Drive via `advance`/`pump`, emit §4.1 operator events, present `LoopStep`/`Refusal`; never construct session/state/recovery logic |
| Q8 | Testability at zero I/O (A8) | blueprint §7; DN-55/DN-94 | C4 | Low | **Injected sources, asserted outputs.** The C1–C3 tests inject `LoopStep`/records/`ProviderView` and assert the pure presentable outputs; the C4 conformance suite enforces imports, authority, tone-only, and the banned-token oracle |

**Status: BLOCKED.** Q1–Q8 await Operator ratification. Once ratified each is
recorded as **DN-96…DN-103** in `docs/implementation-decision-notes.md` before
C0, exactly as Iterations 1–11; the design review §16 readiness flips to READY.

---

## 11. Proposed Decision Notes (DN-96…DN-103)

Proposals for Operator ratification; none took effect by this review. To be
ratified in the established table form (Status / Date / Resolves / Grounding /
Embodied in / Decision), mirroring DN-1…DN-95.

| DN | Resolves | Proposal |
|---|---|---|
| DN-96 | Q1 | `cli` executes at Iteration 12 per DN-45's re-order and the Iteration 11 closeout; the blueprint §8.12/§8.13 labels are superseded and stand until RFC-0020; the scaffold posture keeps the MVP-gate's production meaning standing |
| DN-97 | Q2 | Iteration 12 builds the I/O-free in-memory presentation model (the DN-1 precedent); the semantic interaction contract is RFC-0015's, the public signatures/formats RFC-0020's |
| DN-98 | Q3 | The presentable state is derived from the owned surfaces only — the `LoopStep` boundary trace, the RFC-0013 §8 transcript, the RFC-0012 §13 Provider View, and `schema` types; never raw provider/skill/machine data |
| DN-99 | Q4 | `collect` maps a closed Operator-decision vocabulary to the RFC-0002 §4.1 operator events, carrying free-text payloads; inapplicable events are refused by `core` and the `Refusal` is presented (I-9) |
| DN-100 | Q5 | `expose` presents the audit log through the RFC-0013 §8 transcript (five categories, metadata-only) and the context through the RFC-0012 §13 Provider View; read-only, secret-free (SC2/SC3/SC4/SC16) |
| DN-101 | Q6 | The risk-class/gate *names* carried by the records map to a closed presentation-tone vocabulary; presentation-only — never a gate change, a mint, or a block (RFC-0001 §5; RFC-0004 §7) |
| DN-102 | Q7 | The CLI drives the session only through `core.advance`/`core.pump`, emitting §4.1 operator events and presenting `LoopStep`/`Refusal`; it never constructs session/state/recovery logic (blueprint §5) |
| DN-103 | Q8 | The CLI's logic is I/O-free and deterministic; the C1–C3 tests inject `LoopStep`/records/`ProviderView` sources (DN-55 precedent); the C4 conformance suite enforces imports, authority, tone-only, and the banned-token oracle |

---

## 12. Atomic implementation plan

Each commit is <300 production LOC, single responsibility, test-visible, on a
branch derived from `c86b7b6` (`iteration/12-cli`). Commit order follows
ratification of the questions it depends on. C1–C3 **fill** the three
Iteration-0 scaffolds (`render`, `collect`, `expose` — already present with
ownership docstrings; the tree test stays green); C4 enforces the layer's
conformance; C5 closes the record.

| Commit | Message | Content | Est. (impl/test) | Depends on | Deliverable |
|---|---|---|---|---|---|
| C0 | `docs: ratify Iteration 12 questions Q1–Q8 and cli scope` | Decision notes for Q1–Q8 (DN-96…DN-103), design review record, renumbering note (Q1), consistency-report note | — / — / ~500 | Q1–Q8 ratified | Ratified plan; all questions answered |
| C1 | `feat(cli): the presentation model and render surface (RFC-0001 §5)` | `render.py`: the presentable-state model derived from `LoopStep` (session state, goal, disclosure trace), the risk-class/gate → tone map (Q6), evidence/proposal presentation from the boundary records and `schema` types (Q3) | ~260 / ~320 | Q2, Q3, Q6 | Presentation model |
| C2 | `feat(cli): operator decision collection (RFC-0001 §5; RFC-0002 §4.1)` | `collect.py`: the closed decision vocabulary, the deterministic mapping to the §4.1 operator events, free-text payloads, the inapplicable-event `Refusal` re-presentation (Q4); the `core` seam (Q7) | ~200 / ~280 | Q4, Q7 | Decision collection |
| C3 | `feat(cli): audit and context exposure (RFC-0001 §5; RFC-0013 §8; RFC-0012 §13)` | `expose.py`: the audit log as the five §8 transcript categories via `audit.transcript.render`, the context view as the §13 Provider View, read-only and secret-free (Q5) | ~180 / ~240 | Q5 | Exposure seam |
| C4 | `test(cli): Layer-7 conformance — imports, authority, tone, I/O-free` | `test_cli_imports.py` (exact §4.1/§4.2 edges + closed stdlib + banned tokens), `test_cli_conformance.py` (RFC-0004 §7 non-actor, tone-only, secret-free, only-`cli`-imports-`core` AST) | 0 / ~280 | C1–C3 | Conformance oracle |
| C5 | `docs: record Iteration 12 completion and cli conformance` | Consistency report + decision notes completion + deferred-items table | — / — / ~200 | C4 | Completion record |

---

## 13. Validation strategy

Same gates as Iterations 1–11: `pytest` (baseline **3404 tests**), `ruff check`,
`ruff format --check`, `python -m build`, `pre-commit run --all-files`. The new
conformance tests add:

- `test_cli_imports.py` — each `cli` file imports only `core`/`audit`/`context`/
  `schema` (and own modules), only the closed stdlib type set, and carries no
  banned I/O/clock/random/network token; the AST "only `cli` imports `core`"
  edge (already asserted in `test_core_imports.py`) is re-asserted here.
- `test_cli_render.py` (C1) — the presentable-state derivation from a `LoopStep`
  trace and the tone mapping from record-carried `risk_class`/`gate` names.
- `test_cli_collect.py` (C2) — the decision → §4.1 operator-event mapping and
  the `Refusal` re-presentation.
- `test_cli_expose.py` (C3) — the transcript and View exposure, read-only and
  secret-free (a token never appears in any presented output).
- `test_cli_conformance.py` (C4) — RFC-0004 §7 non-actor cells; tone-only (a
  tone never changes a gate/mints/blocks); no write path; the only-`cli`-imports-
  `core` AST edge.

Determinism is asserted by property-style tests (same inputs → same presented
outputs, RFC-0007 S7); the I/O-free posture is conformance-enforced (no clock,
no network, no filesystem, no subprocess imports in `cli`; DN-55/DN-94). Because
C0–C5 touch neither `rfc/` nor `tools/`, the RFC-reference validator is not a
gate for this iteration (CI still runs it; the pre-existing RFC-0004 §470 `'S1'`
error is unrelated and unchanged).

---

## 14. Definition of Done (per commit)

| Commit | Definition of Done |
|---|---|
| C0 | Q1–Q8 each answered and recorded as decision notes (DN-96…DN-103); the renumbering tension (Q1) recorded; this review's readiness flips to READY |
| C1 | `render.py` derives the presentable state from the owned surfaces only (Q3); the risk-class/gate → tone map is closed, total, deterministic, and presentation-only (Q6); no raw provider/skill/machine data is rendered; the presented output never carries a secret (SC2) |
| C2 | `collect.py` maps each closed decision to its RFC-0002 §4.1 operator event (Q4); free-text payloads travel only as reply/refine payloads (I-5); an inapplicable event surfaces `core`'s `Refusal`, presented honestly (I-9); no decision logic and no state construction (Q7) |
| C3 | `expose.py` presents the audit log as the five §8 transcript categories via `audit.transcript.render` and the context as the §13 Provider View (Q5); read-only (no write path); secret-free (SC2/SC3/SC4/SC16); no raw store internals |
| C4 | Every banned edge and banned token is asserted structurally; the RFC-0004 §7 non-actor cells hold (no classify/verify/approve/execute/persist); tone-only (a tone never changes a gate); the only-`cli`-imports-`core` edge holds; full suite green |
| C5 | Consistency report reflects Iteration 12; no orphaned decision notes; the deferred-items table names every owner |

**Overall DoD (RFC-0001 §5; blueprint §2/§4.1/§4.2):** Presentation-only (tone
never policy); decisions collected and returned to `core`, never decided
(RFC-0004 §7); the session driven only through `core`'s `advance`/`pump` seam
(blueprint §5); audit/context exposure read-only and secret-free (SC-series);
`pytest`, `ruff check`, `ruff format --check`, `python -m build`, and
`pre-commit` all green; the tree and edges unchanged.

---

## 15. LOC estimates

| Commit | impl | test | docs | Notes |
|---|---|---|---|---|
| C0 | — | — | ~500 | Ratification |
| C1 | ~260 | ~320 | — | Presentation model + tone |
| C2 | ~200 | ~280 | — | Decision collection |
| C3 | ~180 | ~240 | — | Exposure seam |
| C4 | 0 | ~280 | — | Conformance oracle |
| C5 | — | — | ~200 | Closeout |
| **Total** | **~640** | **~1,120** | ~700 | |

Production total ≈ **640**; test total ≈ **1,120**. Test LOC exceeds the
300-LOC cap per-commit, as in Iterations 3–11 (the cap applies to implementation
lines). C1 (the presentation model) carries the tone/secret-seam weight
(Q3/Q6/SC2); C2 carries the collection seam (Q4/Q7/I-5/I-9); C3 the exposure seam
(Q5/SC3/SC4). The estimates are advisory; as at C1 of Iteration 11 (DN-95), a
verified overshoot is reconciled by a decision note, never by editing this
review.

---

## 16. Readiness assessment

**Status: BLOCKED** pending ratification of Q1–Q8 (to be recorded as decision
notes DN-96…DN-103 before C0), exactly as Iterations 1–11 began. The
highest-leverage questions are **Q2** (the semantic-vs-visual split that fixes
the iteration's deliverable), **Q3** (the presentable-state source that fixes
the render surface), and **Q4** (the collection model that fixes the `core`
seam). Once Q1–Q8 are ratified, the layer is **READY** and commits execute in
order C0→C5, each satisfying its §14 DoD before the next begins. The dominant
residual risk is broader but unchanged in kind from Iterations 10–11 — the Draft
status of RFC-0005…RFC-0013 and RFC-0021 and the Planned status of RFC-0015 —
and is bounded by the scaffold posture and by the fact that `cli`'s load-bearing
spine is Accepted (RFC-0001 §5; RFC-0002 §4.1; RFC-0004 §7).

---

## 17. Final verdict

This plan is a faithful translation of the frozen corpus into the presentation
scaffold: **no new architecture is proposed** — no new state, no new event, no
new authority, no new interface contract. Every piece it builds is the corpus's
own: RFC-0001 §5's Presentation responsibilities (render, present, collect,
expose, tone); RFC-0002 §4.1's operator events; RFC-0013 §7/§8's records and
transcript; RFC-0012 §13's Provider View; RFC-0009's secret-free doctrine;
RFC-0004 §7's non-actor status. Every ambiguity the corpus leaves — the
renumbering/gate posture, the semantic-vs-visual split, the presentable-state
source, the collection model, the exposure seam, the tone surface, the `core`
seam, and the testability of an I/O-free presentation layer — is elevated to a
blocking question (Q1–Q8) for ratification rather than resolved here. The
inherited Iteration 5–11 `cli`-ward obligations (the presentation-only tone, the
decision collection returned to `core`, the read-only secret-free exposure, the
single `core` seam) are now Definition of Done items, not deferred again. The
parts whose concrete surface does not exist yet — the semantic interaction
contract, the visual TUI, the public signatures/formats, configuration UI — are
named against RFC-0015/RFC-0016/RFC-0020 in §1.2, never dropped. **Pending
ratification: Q1–Q8 are to be recorded as DN-96…DN-103; the layer is READY for
C1.**

---

## Consistency review against the Blueprint and governing RFCs

**Consistent.** Module set `cli/{__init__,render,collect,expose}.py` fixed by
blueprint §2 (scaffolds already present); the dependency rule
`ALLOWED["cli"] = {core, audit, context, schema}` and
`FORBIDDEN["cli"] = {policy, executor, factlayer, providers, skills, secrets}`
honored (§3/§5); RFC-0004 §7's absence of a Presentation actor honored by §4 and
the C4 authority suite; one-owner discipline honored by the two-owner checks
(tone vs policy; the exposure vs the record; the collection vs the decision);
blueprint §8.0's scaffold gate stands; DN-45's re-order is continued (`cli` =
Iteration 12); DN-55/DN-94's injected-primitive / I/O-free precedent is the
Q8 reading; DN-1's in-memory-types precedent is the Q2 reading; DN-88's
"`core` is the single runtime writer" is preserved — `cli` never writes;
RFC-0013 §8's transcript is the exposure channel (AU2); RFC-0012 §13's Provider
View is the context channel (SC3); RFC-0009 SC2/SC3/SC4/SC16 hold at the
presentation boundary; the two walkthroughs' session surface is consumed, not
re-oracled, by `cli`.

**Reported tensions (not violations):**

1. Blueprint §8.12/§8.13 numbering vs DN-45's re-order — §8.12 still reads
   "Iteration 11 — the MVP gate" and §8.13 "Iteration 12 — production MVP" while
   this iteration implements `cli` at Iteration 12 (Q1), exactly as §8.10/§8.11's
   labels were superseded at Iterations 10–11.
2. RFC-0005…0013 and RFC-0021 are Draft and RFC-0015 is Planned — `cli` presents
   the Draft-owned transcript (RFC-0013 §8) and View (RFC-0012 §13), so the
   rework risk is wider than in Iterations 10–11 in the interaction half; it is
   accepted under the same posture and bounded by the Accepted spine (RFC-0001
   §5; RFC-0002 §4.1; RFC-0004 §7).
3. RFC-0001 §5's "the TUI is the only interface" vs the I/O-free scaffold
   posture — reconciled by Q2: the CLI's *logic* is the semantic presentation
   model (deterministic, injected), the *TUI* (real terminal I/O, the visual
   surface) is RFC-0015/RFC-0020's.
4. "Expose the audit log" (RFC-0001 §5) vs "audit written before the consequence
   by the owning component" (RFC-0013 §23) — reconciled by Q5/DN-88: `cli`
   *reads* the transcript (`audit` owns the record; `core` writes it); `cli`
   never writes.

**Verdict.** This plan is a faithful translation of the frozen corpus into the
presentation scaffold; no new architecture is proposed, and every ambiguity the
corpus does not decide is elevated to a blocking question for ratification rather
than resolved here.

*End of design review. To be ratified as DN-96…DN-103 before C0.*
