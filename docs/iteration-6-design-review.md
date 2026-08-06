# Iteration 6 — Design Review (Secrets Layer)

> **Document type:** Implementation design review, at the same rigor as
> Iterations 2–5. **Not an RFC, not code.**
> **Read this first:** This document **defines no new architecture, modifies no
> RFC, invents no behavior, and writes no production code.** It translates the
> frozen corpus (RFC-0000–0013, RFC-0021, the decision traceability matrix,
> `docs/architecture-implementation-blueprint.md`, and the ratified
> `docs/implementation-decision-notes.md` DN-1…DN-39) into an implementation
> plan for the **Secrets Layer — the `secrets` package** (blueprint §8.6,
> re-ordered to Iteration 6 by DN-35). Where the corpus does not decide
> something, this document **reports** it as an ambiguity or a question; it does
> not resolve it.
>
> **Status of sources.** RFC-0009 is **Draft** (not Accepted). Per RFC-0003 Part
> II §1.1 Draft RFCs are not normative and must not be relied upon by
> implementation; yet the blueprint (a translation, §0) targets the Drafts'
> *invariants* as the conformance oracle (blueprint §9 #2). Iteration 6 inherits
> Iterations 1–5's posture: it conforms to RFC-0009's Draft wording knowingly,
> accepting the rework risk that a Draft change carries. Blueprint §8.0 gate
> stands — production code begins only after RFC-0015/0019/0020 and the Drafts
> are Accepted; this iteration builds the translation scaffold. The load-bearing
> dependencies this layer rests on — RFC-0001 §7.6, §8.7, §8.12, §9; RFC-0002
> invariants 4 and 13; RFC-0004 §3 and §4.11; RFC-0007 S5, T7, T10, §15.5 — are
> **Accepted**, which bounds the rework risk. RFC-0010/RFC-0011/RFC-0012/RFC-0013
> (which own the no-secrets boundaries this RFC cites) are Draft and are
> explicitly not built here (Q4).
>
> **Scope decision (reported — Q1).** DN-35 postponed `secrets` (blueprint §8.6)
> to the iteration after `trust`, and the Iteration 5 closeout
> (`docs/implementation-consistency-report.md` §Readiness for Iteration 6)
> records that Iteration 6 is the `secrets` package. Blueprint §8.6/§8.7 were
> never renumbered: §8.7 still reads "Iteration 6 — `policy`". This task's scope
> implements `secrets` at Iteration 6, which requires ratification of the
> renumbering before C0 (Q1). The re-order is dependency-safe — `trust` (Layer 1)
> precedes `secrets` (Layer 3), and `secrets` still precedes `context`
> (RFC-0012), preserving blueprint Risk #9's mitigation (the no-secrets boundary
> established before the Context/Provider join).

---

## 1. Scope

### 1.1 Scope (blueprint §8.6, transcribed)

| Item | Value |
|---|---|
| Goal | The no-secrets boundary, testable |
| Work | Classifier (secret/non-secret/secret-adjacent/Hostile), redactor (fail-closed), Secure Store interface |
| Definition of Done | SC2–SC5 (never in Context/View/Audit/extensions), SC14 (fail closed), SC15 (exposure = compromise) tests pass |
| RFC basis | RFC-0009 §0, §3, §11, §13, §15, §28 |

Blueprint §7 (test oracle) carries a `secrets` row (RFC-0009 §0, §13, §28:
"no value enters Context/View/Audit (SC2–SC5); redaction fails closed (SC14);
exposure is compromise (SC15); retention is consent-based (SC11)"). Blueprint
§5 exposes the package contract: "Classify a datum (secret/non-secret/
secret-adjacent/Hostile); redact with fail-closed; Secure Store interface
(provision, consume-at-boundary, destroy)" — RFC-0009 §3, §11, §13, §14;
SC1–SC16. The SC2–SC5 half of the §8.6 DoD cannot be exercised end-to-end yet
(Context, Audit, Providers, Skills do not exist); how it is satisfied at this
layer is a ratification matter (Q4), mirroring how Iteration 5 made RFC-0002
invariants 4/5 testable at the sanitize/containment layer with runtime
enforcement deferred to `core`.

### 1.2 Out of scope (recorded, not dropped)

Each of these is owned elsewhere and is **not** built in Iteration 6:

| Item | Owned by | Blueprint gate |
|---|---|---|
| The real Secure Store mechanics — which OS secret store, its interface, encryption, key management | RFC-0009 §30 OQ1; RFC-0020 (implementation) | RFC-0001 §8.7; Q2 |
| The exhaustive redaction rule catalogue (all secret-shaped patterns, collection exclusion) | RFC-0009 §30 OQ2; RFC-0020, RFC-0012 | Q3 |
| The telemetry architecture (opt-in flow, crash-report format) | RFC-0009 §26, §30 OQ3; post-MVP (RFC-0000 §5) | RFC-0009 §26; recorded |
| Audit retention limits for secret metadata | RFC-0013; `audit`, Iteration 7 | RFC-0009 §15 rule 5, §27 rule 4 |
| Credential provisioning UX (how the Operator enters/re-views keys) | RFC-0015, RFC-0016 | RFC-0009 §7, §23 |
| Personal-data detection heuristics (beyond the explicit classes) | RFC-0009 §30 OQ6; post-MVP | RFC-0000 §5; recorded |
| The Context-side enforcement of the secret-free boundary (SC2/SC3) | RFC-0012 §32, §13; `context` | RFC-0004 §4.11; blueprint §4.2 (`context` imports `secrets` *classifier types* only) |
| The Audit-side metadata-only records (SC4) | RFC-0013 §31; `audit`, Iteration 7 | RFC-0009 §15; blueprint §4.2 |
| The Provider-adapter consumption boundary (the only secret consumer, RFC-0009 §8) | RFC-0010 §11; `providers`, Iteration 9 | RFC-0009 §8, §16 |
| The Skill no-secrets boundary (SC5) | RFC-0011 §15; `skills`, Iteration 9 | RFC-0009 §17 |
| The "no Action carries a secret" gate (SC9) and elevation (SC10) | RFC-0008 §3; `policy`/`executor` | RFC-0009 §22 |
| RFC-0009 §32 vocabulary additions to RFC-0003 (additive amendment) | RFC-0003 Part II amendment; on RFC-0009 acceptance | not this iteration |
| Signatures / package naming | RFC-0020 (future) | DN-1 |

### 1.3 Ownership (package owner)

`secrets` is owned by RFC-0009 — one owner per row, no delegation (RFC-0004 §3;
blueprint §10). Module-level ownership:

| Module | Owning RFC sections | Protected by |
|---|---|---|
| `secrets/classify.py` | RFC-0009 §1, §2, §3 | SC13 (testable classification rules), S7 (deterministic); RFC-0001 §8.5 (never the LLM's characterization) |
| `secrets/redact.py` | RFC-0009 §11, §13 | SC13, SC14; RFC-0007 S1, S5, T7 |
| `secrets/store.py` | RFC-0009 §4–§12 | SC1, SC6, SC7, SC8, SC11, SC12, SC15 |

**Two-owner check.** The classifier *produces* `TrustClass.HOSTILE` as an outcome
of its own secret classification (RFC-0009 §3 rule 4 → RFC-0007 §15.5) and
redaction is "a sanitization (RFC-0007 S5)" — but the *trust class and
quarantine semantics* are RFC-0007's and the *secrecy predicate* is RFC-0009's;
the `trust` package's S5 boundary test already asserts `trust` never classifies
secrets. The blueprint's precedent: `executor` = RFC-0004 profile + RFC-0002
state — two distinct properties, two owners. The trust-layer's `Datum`/`classify`
answer "how trustworthy is this datum?"; the secrets classifier answers "is this
a secret value?" They are distinct predicates and are never merged (Q5).

### 1.4 Authority boundaries

RFC-0004 §4.11 and §9.11 fix this layer's authority posture: **no component may
include a secret in Context, a Provider View, machine output summaries, the
Audit, or telemetry — not a privilege withheld from most components, but one
held by none.** The `secrets` package therefore holds no authority over values'
*use*; it holds the deterministic mechanics only: classification, redaction, and
the custody abstraction. It must never decide what a secret is *for* or who may
use it (custody is not ownership, RFC-0009 §4). Ownership stays with the
Operator; authority to Provision/Consume/View/Destroy flows per RFC-0009 §5. This
layer implements none of Provision/Consume/View in an acting sense — it defines
the contracts the Operator (provisioner), the Secure Store (custodian), and the
Provider adapter (the single scoped consumer, RFC-0009 §8) will discharge in
later iterations.

---

## 2. Architectural review

### 2.1 Package ownership (blueprint §3, transcribed)

| Package | Owner | Responsibility |
|---|---|---|
| `secrets` | RFC-0009 | Deterministic secret classification (§3), redaction with fail-closed (§11, §13, SC13/SC14), and the Secure Store abstraction (SC1, SC8, SC12). Never lets a value enter Context/View/Audit/extensions (SC2–SC5). |

Consumed (eventually) by `executor`, `audit`, and `context` (blueprint §4.1,
§4.2); it is built with no consumers today, exactly like `trust` in Iteration 5.

### 2.2 Module set (fixed)

One package, three modules — **fixed** by blueprint §2 and
`tests/test_packages.py::test_tree_matches_blueprint_exactly`:

| Module | Responsibility |
|---|---|
| `secrets/__init__.py` | Package facade; re-exports only the owned vocabulary |
| `secrets/classify.py` | Deterministic secret classification (RFC-0009 §1, §2, §3) |
| `secrets/redact.py` | Fail-closed redaction (RFC-0009 §11, §13; SC13, SC14) |
| `secrets/store.py` | Secure Store abstraction (RFC-0009 §4–§12; SC1, SC8, SC12) |

Adding or renaming a module breaks the tree test.

### 2.3 Allowed imports

`ALLOWED["secrets"] = {"schema", "trust"}` (blueprint §4.1) plus the sanctioned
stdlib subset. The `secrets → trust` edge is the *reason this iteration follows
Iteration 5*: redaction is a sanitization (RFC-0009 §11; RFC-0007 S5) and
unclassifiable data is Hostile (RFC-0009 §3 rule 4; RFC-0007 §15.5), so `redact`
and `classify` are expected to consume `trust` primitives (`sanitize`,
`TrustClass`). Whether the `secrets → schema` edge is exercised (classifier over
canonical types) or kept **latent** (classifier over an internal abstract input,
the DN-37 precedent) is a ratification matter (Q5), not an architecture change:
the edge is already declared.

### 2.4 Forbidden imports

Everything not in `ALLOWED["secrets"]`: `systemmodel`, `collectors`, `factlayer`,
`verification`, `policy`, `executor`, `audit`, `context`, `providers`, `skills`,
`core`, `cli`. The layer must not anticipate `factlayer`/`verification` data
types, must not reach for the Audit, and must not touch Provider/Skill surface.
It is the *source* of the no-secrets boundary, never a consumer of the
components that enforce it. Enforced by `tests/test_dependency_rules.py` (the
allowed-graph test covers the secrets row transitively; no FORBIDDEN row is
needed). Additionally the §4.2 authority qualifier "`context`: ... `secrets`
(values)" is a *use* restriction on `context`, not an import ban — `context`
may import `secrets` *classifier types only*, which constrains this layer's
public surface (Q4/Q5: classifier types must be value-free and import-safe).

### 2.5 Layer placement

Layer 3 (blueprint §4.1), beside `policy`. Its imports reach only downward to
Layers 0–1 (`schema`, `trust`); nothing at Layers 0–2 may import it, and nothing
it may import exists at Layer 2 (no `factlayer`/`verification` edge — the
redaction problem arrives from *their* output, but the seam is RFC-0005 §2's
collection boundary, not an import). `secrets` is a leaf whose future consumers
(`executor`, `audit`, `context` at Layer 4; `core` at Layer 6) do not yet exist.

### 2.6 Acyclicity and single-typing

No cycle: all edges point downward (`secrets` → `schema`, `trust` → stdlib).
Each type is defined in exactly one module: classification types in
`classify.py`, redaction results in `redact.py`, store/ownership records in
`store.py`. No type is shared or re-defined across modules; `redact.py` carries
the trust class as a *value* from `trust` rather than re-declaring it (Q6-in-
Iteration-5 precedent; S1's never-upgrades is asserted, not reimplemented).

---

## 3. RFC traceability

| RFC | Section | Implemented as | Status in layer |
|---|---|---|---|
| RFC-0009 | §0 Purpose | The three binary guarantees as invariant tests: value exists only where/when it must; never in Context/View/output/Audit/telemetry/extensions; boundary holds closed | Oracle (C4) |
| RFC-0009 | §1 What is a Secret | The value/metadata split; the five by-construction secret classes; "secret because of what holding it lets someone do" | Implemented (C1) |
| RFC-0009 | §2 What is not a Secret | The fixed non-secret list as classifier outputs; unclassifiable → Hostile, never "probably not a secret" | Implemented (C1) |
| RFC-0009 | §3 Secret Classification | Deterministic classification — provisioned, Operator-marked, secret-shaped (mechanical, never exhaustive), fail-closed to Hostile, never the LLM's, testable | Implemented (C1) |
| RFC-0009 | §4 Secret Ownership | Owner/custody/consumer records; one owner per secret; the "never owned by" list as a boundary test | Implemented (C3) |
| RFC-0009 | §5 Secret Authority | Provision/Consume/View/Invalidate/Destroy as the store's contract; no component may include a secret anywhere (SC2–SC5) | Implemented (C3/C4) |
| RFC-0009 | §6 Lifecycle | Provision → Store → Bound → Consume → Invalidate → Destroy; any step may jump to Invalidate on suspected exposure | Implemented (C3) |
| RFC-0009 | §7 Secret Origin | The three origins; discovery in captured data → contained and discarded, never adopted | Implemented (C1/C3) |
| RFC-0009 | §8 Consumption | The closed consumer set: the Provider adapter only; nothing else consumes values | Implemented (C3, contract); exercised at providers (Iteration 9) |
| RFC-0009 | §9 Persistence | "Value never durable anywhere but the Secure Store" as the store contract; no derived artifacts; session-scoped materializations | Implemented (C3, abstraction); real store RFC-0020 (Q2) |
| RFC-0009 | §10 Sharing | No forwarding, no copies in transit, no shared derivation — the store contract | Implemented (C3) |
| RFC-0009 | §11 Redaction | Layered redaction: detection at the boundary + containment for the unprovable; deterministic and testable; fails closed | Implemented (C2) |
| RFC-0009 | §12 Destruction | Destroy on purpose lapse / request / exposure; destroy materializations; recorded, never the value; not undoable | Implemented (C3) |
| RFC-0009 | §13 Failure | Determinism first, then disclosure; redaction cannot be guaranteed → withheld; store fails → not released; consumer misbehaves → incident | Implemented (C2/C3/C4) |
| RFC-0009 | §14 Recovery | Re-provisioning only; the one Operator-initiated demotion path; no automatic demotion | Implemented (C3, contract) |
| RFC-0009 | §15 Audit | Metadata-only records (existence, purpose, use, destruction); never a value; record-before-consequence | Contract (C3); wiring to RFC-0013, Iteration 7 |
| RFC-0009 | §16–§25 Interactions | Boundary tests on the layer's own surface (SC2–SC5); cross-component enforcement in `context`/`audit`/`providers`/`skills`/`policy` | Boundary (C4); deferred per Q4 |
| RFC-0009 | §26 Telemetry | Out of scope: post-MVP per RFC-0000 §5; posture recorded, nothing built | Recorded (C5) |
| RFC-0009 | §27 Retention | Session-scoped default; values never durable; metadata retention RFC-0013's | Implemented (C3, contract) |
| RFC-0009 | §28 SC1–SC16 | Conformance oracle — layer-enforceable set enumerated in §7 below | Oracle (C4) |
| RFC-0001 | §7.6, §8.7, §8.12, §9 | One-way crossing; segregation in the OS secret store; fail-closed disclosure; "what never persists" | Made *testable*; runtime enforcement later |
| RFC-0002 | invariants 4, 13 | Never with secrets (LLM); audit before consequence | Boundary (C4); runtime at `core` |
| RFC-0004 | §3, §4.11 | One owner per row; Context Manager may never decide to include a secret | Boundary (C4) |
| RFC-0007 | §6.10, S5, T7, T10, §15.5 | The Secrets category (never exported); no secret through sanitization; the binary no-secret property; secret-free Context; unclassifiable → Hostile | Boundary (C4); consumes `trust` |
| RFC-0010 | §11 | No secret enters a Provider View | Boundary (C4); enforced at `context`, Iteration 8 |
| RFC-0011 | §15 | No secrets to Skills | Boundary (C4); enforced at `skills`, Iteration 9 |
| RFC-0013 | §31 | Audit interaction with secrets — metadata, never substance | Boundary (C4); enforced at `audit`, Iteration 7 |
| RFC-0021 | §4.11 | Passwords/secrets are this RFC's subject, not the machine abstraction's | Consistency (C4) |

**Already resolved by the corpus (not re-opened here):**

- The **consumer set is closed**: the Provider adapter, at the provider boundary,
  for the stated purpose, alone (RFC-0009 §8). Not a question.
- **The LLM never classifies** — classification is local and deterministic
  (RFC-0009 §3 rule 5; RFC-0001 §8.5 by analogy). Not a question.
- **Unclassifiable data fails closed to Hostile**, quarantined and excluded
  (RFC-0009 §3 rule 4; RFC-0007 §15.5). Not a question.
- **Redaction is not trust** — removing a value never upgrades its source's
  trust class (RFC-0009 §11.1, §25.4; RFC-0007 S1). Not a question.
- **Exposure is compromise** — suspected exposure invalidates and destroys
  (RFC-0009 §13.4, §15; RFC-0007 §6.10). Not a question.
- **A secret value is never a Fact**, never enters Context or the Provider View,
  never a Skill input (RFC-0009 §21, §19, §17; RFC-0005 §3/§13). Not a question.
- **Discovery-in-captured-data is containment, not adoption** — never into the
  Secure Store, never Facts (RFC-0009 §7 rule 3). Not a question.
- **Signatures**: RFC-0020's, not invented here (DN-1). Not a question.

---

## 4. Public surface

The planned public surface is **reported**, not ratified; final signatures are
RFC-0020's (DN-1). The shape below is what C1–C3 will build.

`secrets/classify.py`

- A classification enum with exactly the four blueprint §5 outputs —
  **secret / non-secret / secret-adjacent / Hostile** (RFC-0009 §3; blueprint
  §5). HOSTILE is the outcome class mapping to `TrustClass.HOSTILE` (RFC-0007
  §15.5) as an outcome of the *secrecy* predicate — distinct from trust
  classification (Q5).
- The value/metadata split (RFC-0009 §1): a `SecretMetadata` record (existence,
  provider, dates) and a value-bearing classification that is never
  re-displayed or exported beyond its boundary.
- The deterministic classifier entry operating on a content/provenance input
  (exact input type per Q5), the §3 six rules, and a **mechanical, explicitly
  non-exhaustive** shape catalogue for §3 rule 3 (RFC-0009 §3; exact catalogue
  RFC-0020's, RFC-0009 §30 OQ2).

`secrets/redact.py`

- The redaction entry → a result record: redacted text + status + reason +
  trust class (unchanged or Hostile — S1, T9), deterministic (SC13), fail-closed
  to **WITHHELD** when the no-secret property cannot be established (SC14).
- The layered strategy of RFC-0009 §11.3: detection at the boundary (secret-
  shaped spans replaced) + containment for the unprovable (bounded/quoted via
  `trust.sanitize`, S8/S4). Never emits a secret value (SC14).

`secrets/store.py`

- The **Secure Store abstraction** (RFC-0009 §4–§12): `provision`,
  `consume`-at-named-boundary (purpose-scoped, SC6/SC7), `invalidate`,
  `destroy` (SC12), with the owner/custody split (SC8) and the
  exposure = compromise invalidation (SC15). In-memory, metadata-only records
  (DN-19/DN-34 precedent); the real OS-secret-store mechanics are RFC-0020's
  (Q2; RFC-0009 §30 OQ1).

Nothing else is exported. The facade re-exports only the owned vocabulary, and
the public surface carries **no value-bearing artifact** beyond the store's
`consume` boundary (the constraint `context`'s import of classifier types relies
on, blueprint §4.2).

---

## 5. Ambiguities and blocking questions

Per Iterations 2–5, ambiguities are **reported**, never resolved here; each is
ratified as a decision note before its commit begins. Each question names its
owning RFC, why it blocks, and the possible interpretations. The recommended
reading is marked, mirroring how DN-8–DN-39 were settled.

**Q1 — Iteration-6 identity and the blueprint §8.6/§8.7 numbering.** DN-35
postponed `secrets` (blueprint §8.6, originally "Iteration 5") to the iteration
after `trust`, and the Iteration 5 closeout records Iteration 6 = the `secrets`
package. But blueprint §8.6/§8.7 were never renumbered: §8.7 still reads
"Iteration 6 — `policy`". Does this iteration proceed as `secrets` (per DN-35
and the closeout), and how is the renumbering recorded — as a supersession note
in this review and the consistency report, leaving the blueprint text until
RFC-0020 lands, or as a blueprint edit? Also unrecorded: the numeric labels of
the *subsequent* iterations after the trust/secrets re-order (policy,
executor+audit, context, providers+skills); only "secrets precedes `context`"
is fixed (DN-35; RFC-0000's safety-spine ordering §4). Owning documents:
blueprint §8.6/§8.7; DN-35; RFC-0000 §4, §7; RFC-0009 roadmap note. **Blocks:
every commit.** Interpretations: (a) Iteration 6 = `secrets`, renumbering
recorded in the review + consistency report as a reported tension (blueprint
text stands until RFC-0020); (b) stop and amend the blueprint first. **Recommended: (a)** —
DN-35 already ratified the re-order; this review records its execution.

**Q2 — `store.py` scope: abstraction vs real store.** RFC-0009 §9 says the value
lives only in the Secure Store; RFC-0001 §8.7 names the OS secret store;
RFC-0009 §30 OQ1 defers "which OS secret store and how its interface is
presented" to RFC-0020. Does `store.py` implement the **abstraction/interface
contract** (provision/consume-at-boundary/invalidate/destroy + lifecycle + the
owner/custody split + purpose-scoping) with in-memory, metadata-only records
(DN-1/DN-19/DN-34 precedent), or attempt a real keyring-backed store now? A
related sub-question: does this iteration's store hold any value in memory at
all, or is it a pure contract over metadata such that a value materializes only
inside `consume`'s boundary and is destroyed when the call completes (SC12)?
Owning documents: RFC-0009 §4–§12, §30 OQ1; RFC-0001 §8.7; DN-1, DN-19, DN-34.
**Blocks: C3.** Interpretations: (a) abstraction + in-memory metadata records,
value only at the consume boundary, mechanics RFC-0020's; (b) minimal real
store (would violate no-persistence-before-RFC-0020 and DN-1). **Recommended: (a)**.

**Q3 — `redact.py` scope: framework now vs full catalogue; relationship to
`trust.sanitize`.** RFC-0009 §11 fixes the layered philosophy and that
redaction "is a sanitization (RFC-0007 S5)"; RFC-0009 §30 OQ2 defers the *exact
deterministic rule catalogue* to RFC-0020 and RFC-0012. Does `redact.py`
implement the **deterministic redaction framework now** — a secret-classifier-
gated transformation that replaces secret-shaped spans and fails closed to
WITHHELD — plus a minimal, explicitly non-exhaustive mechanical catalogue (the
§1 classes: bearer tokens, API keys, private-key blocks, secret-shaped
configuration), consuming `trust.sanitize` for the containment layer (bound/
quote, S8/S4) and `TrustClass` for the never-upgrade guarantee (S1, T9) — or
only an interface + tests with all mechanics deferred? The DN-38 precedent
(Iteration 5 built the S3 primitives now, exact catalogue RFC-0012's) suggests
the framework is this iteration's invariant-bearing core (SC13/SC14 are the
§8.6 DoD's own test oracle). Owning documents: RFC-0009 §11, §13, §30 OQ2;
RFC-0007 S5, S8, §16 OQ3; DN-38. **Blocks: C2.** Interpretations: (a) framework
+ minimal mechanical catalogue + fail-closed, consuming `trust`; (b)
interface-only, all mechanics deferred. **Recommended: (a)**.

**Q4 — Blueprint §8.6 DoD SC2–SC5 without their enforcement points.** The §8.6
Definition of Done requires "SC2–SC5 (never in Context/View/Audit/extensions)
tests pass", but Context (Iteration 8), Audit (Iteration 7), Providers and
Skills (Iteration 9) do not exist, and the enforcement points live there
(RFC-0004 §4.11; RFC-0012 §32; RFC-0013 §31; RFC-0010 §11; RFC-0011 §15). How is
that half of the DoD satisfied at the secrets layer now? Iteration 5's precedent
holds: RFC-0002 invariants 4/5 were "made testable at the sanitize/containment
layer; runtime enforcement is `core`'s". Does this iteration implement
**layer-boundary tests** — property tests proving the secrets package's own
public surface never exports a value, never offers a path from a public function
to a value-bearing artifact outside `store.consume`, never constructs Context/
Provider/Audit/Skill material, and that SC2–SC5 hold "by construction" of the
surface — and record the cross-component conformance as the owning packages'
DoD? Or are SC2–SC5 declared deferred wholesale? Owning documents: blueprint
§8.6; RFC-0009 §19–§22, §28; RFC-0004 §4.11; RFC-0002 invariant 4; RFC-0007
T7/T10. **Blocks: C4 (and constrains the C1–C3 surfaces).** Interpretations:
(a) layer-boundary tests now + cross-component enforcement recorded as
`context`/`audit`/`providers`/`skills` obligations; (b) defer SC2–SC5 entirely,
relying only on the future components' tests. **Recommended: (a)** — it is the
§8.6 DoD's only satisfiable reading this iteration and mirrors Iteration 5.

**Q5 — `classify.py` input and the `schema` edge.** What does the secrecy
classifier operate on — a raw content/provenance input (an internal abstract
secret-classification record), a `schema` canonical type (exercising the
declared `secrets → schema` edge), or a bare string? RFC-0009 §3 rules are
value-shaped (a token, a line of machine output), and Facts are never secrets
(RFC-0009 §21), so a `schema.Fact` input is semantically wrong at the classifier
entry. Does `classify.py` keep the `schema` edge **latent** (DN-37 precedent —
`verification → systemmodel` and `trust → schema` both stayed latent), operating
on an internal abstract input record (content + provenance/origin context) that
`context` (Iteration 8) can adapt to? Also: does the classifier carry the §1
value/metadata distinction as separate result kinds? Owning documents: RFC-0009
§1, §3, §21; blueprint §4.1 (`secrets → schema` edge allowed, not required);
DN-1, DN-37. **Blocks: C1, C4.** Interpretations: (a) internal abstract input,
`schema` edge latent, value/metadata split explicit; (b) classifier bound to
`schema` types (edge used). **Recommended: (a)** — keeps the layer type-free and
the edge authorized-but-unused, the established pattern since Iteration 4.

---

## 6. Atomic implementation plan

Each commit is <300 production LOC, single responsibility, test-visible, on
`iteration/6-secrets`. Commit order follows ratification of the questions it
depends on. EST. = estimated LOC (impl / test / docs).

| Commit | Message | Content | Est. (impl/test) | Depends on | Deliverable |
|---|---|---|---|---|---|
| C0 | `docs: ratify Iteration 6 questions Q1–Q5 and secrets scope` | Decision notes for Q1–Q5 (DN-40…DN-44), design review record, renumbering note (Q1), consistency-report note | — / — / ~800 | Q1–Q5 ratified | Ratified plan; all questions answered |
| C1 | `feat(secrets): deterministic secret classification (RFC-0009 §1, §2, §3)` | Secret/non-secret/secret-adjacent/Hostile enum; value/metadata split; the six §3 rules; the mechanical non-exhaustive shape catalogue; fail-closed to Hostile; deterministic-only (never the LLM's) | ~220 / ~320 | Q1, Q5 | Classifier |
| C2 | `feat(secrets): fail-closed redaction (RFC-0009 §11, §13, SC13/SC14)` | Secret-shaped span replacement at the boundary + containment via `trust.sanitize` (bound/quote, S8/S4); result record carrying class + status + reason; never upgrades (S1, T9); WITHHELD on failure (SC14); deterministic (SC13) | ~180 / ~280 | Q1, Q3 | Redactor |
| C3 | `feat(secrets): Secure Store abstraction (RFC-0009 §4–§12, SC1, SC8, SC12, SC15)` | The contract: provision, bound (purpose-scope, SC7), consume-at-boundary (SC6, SC8), invalidate, destroy (SC12); exposure = compromise invalidation (SC15); metadata-only records; value exists only at the consume boundary and dies with the call | ~200 / ~260 | Q1, Q2 | Secure Store abstraction |
| C4 | `test(secrets): Layer-3 conformance and SC-invariant suite` | Conformance (allowed imports only stdlib+schema+trust, no I/O, no forbidden stdlib, public surface == owned vocabulary, frozen/slotted, no top-level logic, package tree, lower layers never import secrets); invariant tests SC13/SC14/SC1/SC8/SC12/SC15; SC2–SC5 layer-boundary tests per Q4; determinism; never-upgrade (S1 via trust) | 0 / ~450 | C1–C3 | Conformance oracle |
| C5 | `docs: record Iteration 6 completion and secrets conformance` | Consistency report + decision notes completion + deferred-items table | — / — / ~220 | C4 | Completion record |

Production total ≈ **600**; test total ≈ **1,310**. Test LOC may exceed the
300-LOC cap per-commit, as in Iterations 4–5 (cap applies to implementation
lines).

---

## 7. Definition of Done (per commit)

| Commit | Definition of Done |
|---|---|
| C0 | Q1–Q5 each answered and recorded as decision notes (DN-40…DN-44); the renumbering tension (Q1) recorded; this review's readiness flips to READY |
| C1 | The four-class secrecy predicate is exhaustive and mutually exclusive; §3 rules 1–6 each have a deterministic, testable rule (rule 5 = no LLM/statistical path — enforced as a property); unclassifiable → Hostile (rule 4); the shape catalogue is mechanical and explicitly non-exhaustive (never claims completeness); the value/metadata split is structural |
| C2 | SC13: redaction is deterministic (same input, same output); SC14: no-secret cannot be established → WITHHELD, nothing crosses, a non-empty reason is produced; S1/T9: the trust class never upgrades; no secret value ever appears in the output (the SC14 boundary test); containment via `trust.sanitize` is used, not re-implemented |
| C3 | SC1: a value exists only in the store's custody and only at its consume boundary; SC8: exactly one owner + one custody holder per record; SC12: destroy removes the value and every materialization; SC15: suspected exposure invalidates and destroys immediately and is recorded as metadata; SC6/SC7: consumption is one-way, single-purpose, scoped; nothing is persisted beyond in-memory metadata (DN-19/DN-34) |
| C4 | Blueprint §5 secrets row and §8.6 DoD (SC2–SC5 layer-boundary, SC14, SC15) pass; every layer-enforceable SC has a test; the SC2–SC5 cross-component obligations are recorded against `context`/`audit`/`providers`/`skills`; full suite green |
| C5 | Consistency report reflects Iteration 6; no orphaned decision notes; the deferred-items table names every §1.2 owner |

**Overall DoD (blueprint §8.6):** SC2–SC5 (layer-boundary), SC14 (fail closed),
SC15 (exposure = compromise) tests pass; `pytest` full suite, `ruff check`, `ruff
format --check`, `python -m build` all green; `tests/test_dependency_rules.py`
and `tests/test_packages.py` still green (tree and edges unchanged).

---

## 8. Validation strategy

Same gates as Iterations 1–5: `pytest` (baseline 1049 tests), `ruff check`,
`ruff format --check`, `python -m build`, and `pre-commit run --all-files`.
Conformance is enforced by the existing `tests/test_dependency_rules.py` (the
`secrets` row is already declared: `ALLOWED["secrets"] = {"schema", "trust"}`)
and `tests/test_packages.py`, extended by C4's new `test_secrets_conformance.py`
and `test_secrets_invariants.py`. Because C0–C5 touch neither `rfc/` nor
`tools/`, the RFC-reference validator is not a gate for this iteration (CI still
runs it; the known pre-existing RFC-0004 §470 `'S1'` error is unrelated and
unchanged).

---

## 9. Risk assessment

| # | Risk | Grounding | Severity | Mitigation |
|---|---|---|---|---|
| 1 | RFC-0009 is Draft; SC rules may change → rework | RFC-0003 Part II §1.1; blueprint §9 #2 | High | This layer rests on Accepted RFC-0001 §7.6/§8.7/§8.12, RFC-0002 invariants 4/13, RFC-0004 §3/§4.11, RFC-0007 S5/T7/T10; conformance re-run at each Draft revision; no production dependence on Draft wording until acceptance |
| 2 | The in-memory abstraction mistaken for the real Secure Store (RFC-0001 §8.7's OS secret store) | RFC-0009 §30 OQ1; DN-19/DN-34 | High | Q2: the store is explicitly an abstraction over metadata; docs and tests state the value lives only at the consume boundary and the real store is RFC-0020's |
| 3 | Classification over/under-blocking (false positives/negatives) | RFC-0009 §31 risks 6–7 | High | Layered redaction (exclusion + detection + containment); fail-closed on unclassifiable (rule 4); SC14 withholds rather than guesses; SC15 treats exposure as compromise |
| 4 | Redaction theatre — the redactor mistaken for the safety boundary itself | RFC-0009 §25.5, §11; RFC-0007 S1 | Medium | Docs/tests state redaction removes capability to carry a value, never upgrades trust; the boundary, not the redactor, is the security boundary |
| 5 | Real credentials leaking into tests/docs | RFC-0009 §1 | Medium | Synthetic token fixtures only; the shape catalogue uses obviously-fake patterns; no real secret material anywhere in the repo |
| 6 | SC2–SC5 silently gapped because their enforcement points don't exist yet | blueprint §8.6; Q4 | Medium | Layer-boundary tests now + cross-component obligations named against `context`/`audit`/`providers`/`skills` in the deferred table (Iteration 5 pattern) |
| 7 | Signature invention before RFC-0020 | DN-1 | Medium | Surface reported in §4 is provisional; final naming is RFC-0020's |
| 8 | Boundary creep toward `context`/`audit` mechanics (summarization, durable records) | RFC-0009 §30; RFC-0012; RFC-0013 | Medium | §1.2 out-of-scope table; C2/C3 implement only the framework; RFC-0012's summarization and RFC-0013's durable records deferred by name |
| 9 | Telemetry half dropped | RFC-0009 §26, §30 OQ3; RFC-0000 §5 | Low | Recorded, never built: posture fixed, architecture deferred to post-MVP |

---

## 10. Readiness verdict

**Status: BLOCKED** pending ratification of Q1–Q5 (recorded as decision notes
before C0), exactly as Iterations 1–5 began. The highest-leverage questions are
**Q2** (store scope vs the real OS secret store), **Q3** (redaction framework
scope vs RFC-0020's catalogue), and **Q4** (how the §8.6 DoD's SC2–SC5 half is
satisfied without its enforcement points). Once Q1–Q5 are ratified, the layer is
**READY** and commits execute in order C0→C5, each satisfying its §7 DoD before
the next begins.

**Post-ratification status (Iteration 6, Commit C0).** Q1–Q5 were ratified and
recorded as **DN-40…DN-44** (`docs/implementation-decision-notes.md`) before C0,
the docs-ratification commit: all five questions answered as decision notes, the
renumbering tension (Q1) recorded as a supersession note, and the consistency
report updated. The layer is now **READY for implementation** — commits execute
in order C0→C5, each satisfying its §7 DoD before the next begins. C1–C5 (the
`secrets` package: `classify.py`, `redact.py`, `store.py`, the conformance
suite, and the closeout) remain to be implemented per §6/§7.

---

## Consistency review against the Blueprint and governing RFCs

**Consistent.** Module set `secrets/{__init__,classify,redact,store}.py` fixed by
blueprint §2; dependency rules (`ALLOWED["secrets"] = {"schema", "trust"}`
+ stdlib, Layer 3) honored by §2.3–§2.5; one-owner discipline (RFC-0004 §3)
honored by §1.3 and the two-owner check; the scaffold gate (blueprint §8.0)
stands; DN-35's postponement is now executed; DN-1 (signatures) honored; DN-37's
latent-edge precedent is the Q5 recommendation; DN-19/DN-34's in-memory precedent
is the Q2 recommendation; the `context` import restriction ("`secrets` classifier
types only", blueprint §4.2) is honored by §4's value-free surface constraint.

**Reported tensions (not violations):**

1. Blueprint §8.6/§8.7 numbering vs DN-35's re-order — §8.7 still reads
   "Iteration 6 — `policy`" while this iteration (and the Iteration 5 closeout)
   implement `secrets` at Iteration 6 (Q1). Needs ratification as a recorded
   renumbering.
2. Blueprint §8.6 DoD requires "SC2–SC5 tests pass" while their enforcement
   points are Iterations 7–9 packages (Q4) — needs ratification of the
   layer-boundary reading.
3. RFC-0009 §9/§30 OQ1 name a real OS secret store (RFC-0001 §8.7) while the
   iteration is a pre-RFC-0020 scaffold bound by DN-1/DN-19/DN-34 (Q2) — needs
   ratification of the abstraction scope.
4. RFC-0009 §11 requires redaction mechanics "owned here", while §30 OQ2 defers
   the exact catalogue to RFC-0020/RFC-0012 (Q3) — needs ratification of the
   framework-now reading.

**Verdict.** This plan is a faithful translation of the frozen corpus into a
secrets-layer scaffold; no new architecture is proposed, and every ambiguity is
elevated to a blocking question. Proceed to ratification.
