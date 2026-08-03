# RFC-0009 — Secrets, Privacy & Sensitive Data

**Status:** Draft
**Date:** 2026-08-02
**Scope:** The single canonical model for secrets, personal data, and sensitive
data: what is and is not a secret; secret lifecycle, ownership, authority,
visibility, boundaries, trust, classification, origin, consumption, and
destruction; the persistence, sharing, redaction, failure, recovery, and audit
philosophies that govern them; interaction with Providers, Skills, Diagnostics,
Context, Audit, Verification, and the Approval Engine; retention defaults; the
telemetry and privacy posture; and the secret invariants SC1–SC16.
**Audience:** Future maintainers
**Supersedes:** Nothing
**Depends on:** RFC-0001, RFC-0002, RFC-0003, RFC-0004, RFC-0005, RFC-0006,
RFC-0007, RFC-0008 (accepted in this series). RFC-0010 and RFC-0011 are
referenced for the no-secrets boundaries they already state; both are Drafts
and are not dependencies.

**Roadmap note:** This is RFC-0000's "RFC-0009 — Secrets, Privacy & Sensitive
Data" (Security, Required), the safety-spine document that fixes secret
handling before the Provider Contract (RFC-0010) can state that no secrets
travel to a provider, and before Context & Memory (RFC-0012) enforces the same
rules (RFC-0000 §4). Its core scope is Required; its telemetry half is deferred
to the post-MVP phase, with the deferred parts recorded here so nothing is
silently dropped (RFC-0000 §5). It answers the coverage rows RFC-0000 §8
assigns to it: RFC-0001 Q14 (which redaction approach is sufficient given
arbitrary formats) and Q15 (whether any telemetry or crash reports are stored,
and under what opt-in). It also answers the deferred mechanics of RFC-0007 §16
OQ3 (redaction sufficiency), RFC-0010 §15 OQ2 (the mechanism keeping secrets
out of Provider Views), and RFC-0011 §30 OQ5 (secret handling specifics).

**BREAKING:** No. This RFC specifies the secret model that RFC-0001, RFC-0002,
RFC-0004, RFC-0005, RFC-0006, RFC-0007, RFC-0008, RFC-0010, and RFC-0011
already assume and cite — secrets are segregated and never enter prompt context
(RFC-0001 §8.7); secrets cross boundaries one way only (RFC-0001 §7.6); the LLM
never receives secrets (RFC-0002 invariant 4); the Context Manager assembles
Provider Views with no secrets (RFC-0004 §4.11); suspected exposure is
compromise (RFC-0007 §6.10); no Action carries a secret into a Provider View
(RFC-0008 §3); no secret enters a Provider View (RFC-0010 §11); no Skill
receives or stores secrets (RFC-0011 §15). It does not weaken any Principle,
Boundary, Invariant, or canonical Definition in an accepted RFC.

---

## 0. Purpose

> **What is a secret, and how does the system guarantee that a secret never
> reaches a Provider, a Skill, the Audit, or any other component that must not
> hold it?**

A **secret** is a value whose compromise grants a capability the Operator did
not intend to grant. The no-secrets boundary is the core privacy guarantee
(RFC-0004 §9.11), and this RFC is its specification. Three binary guarantees
fix everything below:

1. A secret value exists only where it must and only when it must.
2. A secret value never enters Context, a Provider View, machine output
   summaries, the Audit, telemetry, or any extension.
3. When secrecy cannot be guaranteed, the boundary holds closed.

---

## 1. What is a Secret

A **Secret** is a value whose disclosure, possession, or inference would grant
or reveal a capability, identity, or authorization the Operator did not intend
to expose. Secrets by construction:

1. **Credentials** — passwords, passphrases, login material.
2. **Tokens and API keys** — provider keys; bearer, session, refresh, signing
   tokens; bring-your-own keys the Operator provisions.
3. **Private keys and derived secrets** — asymmetric private keys, seeds, and
   anything that reconstructs one of the above.
4. **Secret-shaped values in captured data** — machine output or configuration
   matching a secret's shape. Secrets *in effect*, with the same boundaries.
5. **Personal data whose compromise harms the Operator** — identity documents,
   Operator-bound account identifiers, private content (RFC-0001 §9).

Two parts of a secret are distinct. **Secret Value** — the material itself:
never derived, reconstructed, copied into a derived artifact, or displayed
except at its provisioning boundary. **Secret Metadata** — what can be said
without revealing the value (existence, provider, provisioning/use/invalidation
dates); private to the Operator by default.

A value is a secret because of what holding it would let someone do, never
because of where it was typed. Hence classification (RFC-0009 §3) is
deterministic, and the LLM never decides what is secret.

---

## 2. What is not a Secret

Fixed non-secrets, not judgment calls:

1. **Public machine facts** — distro, kernel, package lists, service states:
   the high-signal facts RFC-0001 §9 permits (Facts, RFC-0005 §3).
2. **Aggregates that reveal no capability** — a derived value that cannot
   become a credential or authorization. One that could is secret-shaped
   (RFC-0009 §1 rule 4).
3. **The mechanism itself** — the fact that secrets are stored, and the names
   of the boundaries, grant nothing.
4. **Sanitized or redacted text** — a log line with its secret fields removed
   is a redacted artifact, not a secret (RFC-0009 §11), so long as no value
   survived.
5. **Operator preferences** — verbosity, provider choice, skill selection
   (RFC-0001 §9).
6. **Personal data the Operator explicitly marks public** — the only demotion
   path, always Operator-initiated for a stated purpose (RFC-0009 §14).

A datum that cannot be classified is Hostile and quarantined (RFC-0007 §15.5),
never "probably not a secret."

---

## 3. Secret Classification

Classification decides deterministically whether a datum is a secret,
non-secret, or secret-adjacent. It answers RFC-0001 Q14's premise honestly: no
pattern catalogue is complete, so classification is layered and fails closed.

1. **Provisioned values are secrets.** Anything the Operator enters into the
   Secure Store is secret by definition.
2. **Operator-marked values are secrets.** Anything the Operator marks private,
   including content from which private data is inferable (RFC-0001 §9).
3. **Secret-shaped values are secrets in effect.** Values in captured data
   matching a secret's shape are classified secret-adjacent until proven
   otherwise; the shape catalogue is mechanical and never exhaustive.
4. **Unclassified values fail closed.** Unclassifiable data is Hostile:
   quarantined, excluded from Context and Provider Views, disclosed (RFC-0007
   §15.5).
5. **The LLM never classifies.** Classification is local and deterministic,
   never the LLM's characterization (RFC-0001 §8.5 applied by analogy).
6. **Classification is testable.** Every class rule is a deterministic,
   testable rule (RFC-0007 S7).

The secret class is exactly the set RFC-0010 excludes from Provider Views as
"anything RFC-0009 classifies as secret" (RFC-0010 §11).

---

## 4. Secret Ownership

Every secret has **exactly one owner** (RFC-0004 §3). This RFC assigns the
Secrets ownership row RFC-0004 §3's table does not yet carry, under the same
rules — one owner per row, no delegation into self-extension (RFC-0004 §3,
RFC-0004 A8).

| Thing | Owner | Delegated through | Never owned by |
|---|---|---|---|
| Secrets | Operator | Secure Store (custody); Provider adapter (scoped consumption) | Provider, Skills, Diagnostics, Fact Layer, Context Manager, Orchestrator, Approval Engine, Executor, Audit System |

- **The Operator owns every secret**, because secrets are credentials and
  permissions and the Operator owns Machine and Permissions (RFC-0004 §3);
  bring-your-own-key is the only origin (RFC-0001 §2), so the owner is always
  the provisioner.
- **The Secure Store holds custody.** Custody is not ownership: it may hold a
  value under the Operator's grant and release it only at a named consumption
  boundary, but never decide what it is for or who may use it.
- **The Provider adapter is a scoped consumer.** It receives a value at its
  boundary for the single provisioned purpose and nothing else (RFC-0009 §5,
  §8).
- **No other component owns, holds, or decides about secrets.** The Context
  Manager may never decide to include one (RFC-0004 §4.11); the Orchestrator
  may carry a secret *handle* but never a value; everything else has no secret
  surface.

Ownership carries three duties (RFC-0004 §3): accountability for the lifecycle,
the authority to act on it (RFC-0009 §5), and the sole right to demote or
destroy it (RFC-0009 §12, §14).

---

## 5. Secret Authority

Authority is the tool that lets an owner discharge responsibility; it flows
downward from the Operator (RFC-0004 §6).

1. **Provision** — enter a secret into the Secure Store. Operator alone; the
   system never provisions for itself.
2. **Consume** — receive a value at a named boundary for a named purpose.
   Operator, delegated scoped to the Provider adapter (RFC-0004 A8: authority
   flows downward and no actor may extend its own grant).
3. **View and export metadata** — what is stored, when used, when destroyed.
   Operator (RFC-0001 §9.2).
4. **View values** — the Operator may re-view a value only at the provisioning
   boundary, on explicit request.
5. **Invalidate and destroy** — Operator; on suspected exposure, exercised by
   the system as a fail-closed duty (RFC-0009 §15).

No component holds authority to include a secret in Context, a Provider View,
machine output summaries, the Audit, or telemetry — not a privilege withheld
from most components, but one held by none (RFC-0004 §4.11).

---

## 6. Secret Lifecycle

The lifecycle is owned by this RFC (RFC-0007 §6.10) and has exactly six steps:

1. **Provision** — the Operator enters a secret at its boundary of need; the
   only origin (RFC-0009 §7). It is bound to a stated purpose (RFC-0009 §7, §9)
   and stored in the Secure Store.
2. **Store** — the value lives only in the Secure Store, scoped to its purpose
   (RFC-0001 §8.7).
3. **Bound** — the purpose is fixed at provisioning and never silently widened;
   a wider use is a new Operator decision.
4. **Consume** — at a consumption boundary the value is materialized for the
   named consumer for the named purpose; use is recorded as metadata
   (RFC-0009 §15). Consumption never changes Context, Plans, or anything the
   LLM can see.
5. **Invalidate** — the Operator revokes, or the system does as a fail-closed
   duty on suspected exposure (RFC-0009 §15). An invalidated secret is refused
   at every boundary.
6. **Destroy** — the value and every materialization are destroyed (RFC-0009
   §12). Nothing is retained.

Any step after *Provision* may jump to *Invalidate* on suspected exposure; the
lifecycle is never paused in a "probably fine" state (RFC-0007 §15.6).

---

## 7. Secret Origin

Secrets enter at exactly three points, and never elsewhere:

1. **Operator provisioning** — the Operator brings a key or token into the
   Secure Store for a stated purpose. The only intended origin, and the only
   one producing a governed secret with an owner, purpose, and lifecycle.
2. **Operator marking** — the Operator marks content private, promoting it into
   the secret class for the stated purpose.
3. **Discovery in captured data** — machine output or configuration contains a
   secret-shaped value (RFC-0009 §3 rule 3). Secrets *in effect*, handled by
   containment and redaction (RFC-0009 §11); never adopted into the Secure
   Store, never Facts (RFC-0009 §21), never given a lifecycle — contained and
   discarded.

The system **never creates a secret** — never derives, guesses, rotates, or
regenerates one; a lost secret is a provisioning decision again (RFC-0009 §14).
The LLM and Provider therefore can never be a secret's origin: their output is
untrusted data (RFC-0004 A1) and can only leak, never provision.

---

## 8. Secret Consumption

A secret is consumed at the boundary where it is needed, and only there
(RFC-0001 §7.6). The complete consumer set is **the Provider adapter, at the
provider boundary, for the secret's stated purpose** — e.g., authenticating the
API request that carries a Provider View; the value never becomes View content
(RFC-0009 §16). Nothing else consumes secret values: not Skills (RFC-0011 §15),
not Diagnostics, not the Fact Layer, Context Manager, Verification, Approval
Engine, or Audit System.

1. Consumption is single-purpose and scoped (RFC-0009 §5, §6).
2. Consumption places the value in no derived artifact — not Context, Plans,
   summaries, Audit, or telemetry.
3. Consumption is recorded as metadata only (RFC-0009 §15).
4. The materialization is destroyed when the call completes (RFC-0009 §12).
5. The LLM is never consulted with a secret (RFC-0002 §6, invariant 4).

Because the consumer set is closed and small, the secret surface is small and
the blast radius of any boundary is bounded.

---

## 9. Secret Persistence Philosophy

Persistence is where privacy guarantees live or die; the philosophy is maximally
strict: **a secret value is never durable anywhere but the Secure Store**
(RFC-0001 §8.7).

1. **In the Secure Store only.** The value persists only under custody
   (RFC-0009 §4), purpose-scoped and consent-based.
2. **Nowhere derived.** Never in Facts, Context, Memory, Plans, transcripts,
   skill content, configuration logs, or crash reports. The default is: a secret
   is never in context (RFC-0001 §8.7; RFC-0007 T10).
3. **Nothing to clean up later.** Redaction happens before anything leaves the
   session (RFC-0001 §5), so no durable artifact ever holds a value needing
   post-hoc scrubbing.
4. **Session-scoped by default.** Materializations live for one consumption
   call and die with it (RFC-0001 §9.5).
5. **Metadata persists, values do not.** Secret metadata may persist under the
   visibility and retention rules of RFC-0009 §15 and §27.

This turns RFC-0001 §9's "What should never persist" list into invariants
(SC1, SC2, SC11).

---

## 10. Secret Sharing Philosophy

Secrets are never *shared*; they are *consumed at a closed boundary*.

- **Sharing** would be a value flowing between components, held by more than
  one holder, or re-derivable from a common artifact. All forbidden.
- **Consumption** is one named consumer receiving the value once, at one
  boundary, for one purpose, after which it is destroyed (RFC-0009 §8).

1. **No forwarding.** No holder — the Secure Store or the adapter — relays a
   value to any other component.
2. **No copies in transit.** A value exists in exactly one place at a time: the
   Secure Store or the consuming boundary during a call.
3. **No shared derivation.** No two components derive the same value from a
   third artifact, because no third artifact exists.
4. **Extensions share nothing.** Skills have no secret surface (RFC-0011 §15,
   SK8).
5. **The Operator is the only multiplier.** Every new consumer is a separate,
   explicit provisioning decision.

This is why the "no secrets to providers" boundary (RFC-0010 §11) is
enforceable: with no sharing layer, no value is ever in two places to leak.

---

## 11. Secret Redaction Philosophy

Redaction keeps machine output and derived artifacts free of secrets. It is a
sanitization (RFC-0007 S5) whose mechanics are owned here (RFC-0007 §16 OQ3).

1. **Redaction is not trust.** Removing a value makes text unable to carry it;
   it does not make text true, safe, or upgraded (RFC-0007 S1).
2. **Redaction happens at the boundary, before anything leaves the session**
   (RFC-0001 §5, §9).
3. **Redaction is layered, because patterns are incomplete.** No catalogue is
   exhaustive, so:
   - **Exclusion at collection** — deterministic tools do not capture
     secret-bearing sources in the first place.
   - **Detection at the boundary** — secret-shaped values in captured data are
     classified (RFC-0009 §3) and removed before Context or Provider Views are
     assembled.
   - **Containment for the unprovable** — data that cannot be proven
     secret-free is summarized, truncated, or withheld rather than carried
     verbatim (RFC-0007 S8).
4. **Redaction is deterministic and testable** (RFC-0007 S7): given this input,
   the output contains no secret value.
5. **Redaction transforms derived artifacts, never the source.** The machine's
   files and raw captures are unaltered; only what the session carries onward
   is transformed.
6. **Redaction fails closed.** If the no-secret property cannot be established,
   content does not cross (RFC-0007 §15.6) and the Operator is told why
   (RFC-0001 §8.12; SC14).

Answer to RFC-0001 Q14: **no pattern approach is sufficient alone; the binary
property (never carry a secret outward) plus layered containment is** — exactly
the property RFC-0007 T7 fixes, with the mechanics specified here.

---

## 12. Secret Destruction Philosophy

Destruction is a first-class lifecycle step, not cleanup afterthought
(RFC-0001 §9.1: context is deleted when the purpose lapses).

1. **Destroy when the purpose lapses** — session end, rotation, abandoned goal.
2. **Destroy on Operator request** — anytime, immediately (RFC-0001 §9.2's wipe
   applies to secrets by extension).
3. **Destroy on exposure** — suspected exposure invalidates and destroys
   immediately (RFC-0009 §15).
4. **Destroy materializations, not just the stored value** — any value
   materialized at a boundary is destroyed when the call completes.
5. **Destruction is recorded, never the value** (RFC-0009 §15).
6. **Destruction is not undoable, and that is correct.** Recovery is
   re-provisioning by the Operator (RFC-0009 §14); there is no trash can for
   secrets.

---

## 13. Secret Failure Philosophy

When secrecy cannot be guaranteed, the system follows RFC-0002 §10's ordering —
determinism first, then disclosure:

1. **Redaction cannot be guaranteed.** Content is withheld; it does not cross
   into Context or the Provider View, and the Operator is told (RFC-0007
   §15.6). There is no "probably fine."
2. **Redaction is unavailable.** The boundary holds closed until redaction
   returns; nothing passes raw untrusted text into a Provider View because "the
   sanitizer was unavailable" (RFC-0007 §15.7; RFC-0001 §8.12).
3. **A secret-shaped value is unclassifiable.** It is Hostile: quarantined,
   excluded, disclosed (RFC-0007 §15.5).
4. **Exposure is suspected.** The secret is treated as compromised (RFC-0007
   §6.10): invalidated, destroyed, disclosed, recorded; everything derived from
   the exposed source is re-verified before further use (RFC-0007 §15.10).
5. **The store fails.** If the Secure Store cannot establish whether a value is
   safe to release, it is not released.
6. **A consumer misbehaves.** If a consumer attempts to persist or relay a
   value, that is a security incident: recorded, the secret invalidated, the
   consumer treated as compromised until proven otherwise (RFC-0007 §6.10).

---

## 14. Secret Recovery Philosophy

Two distinct promises:

1. **Recovery of access.** A lost, invalidated, or destroyed secret is
   recovered only by the Operator re-provisioning it (RFC-0009 §7). The system
   never guesses, regenerates, or derives a replacement — a feature: a secret
   the system cannot recreate is a secret it cannot leak from storage.
2. **Recovery of secrecy.** Suspected exposure is an incident, not an undo:
   invalidate and destroy, disclose, record (RFC-0009 §15), re-verify
   everything derived from the source (RFC-0007 §15.10). Re-establishing
   secrecy means fresh provisioning, not restoring the old value.

The one demotion path is Operator-initiated: the Operator may explicitly mark a
datum as no longer private for a stated purpose (RFC-0009 §2 rule 6). No
automatic process ever demotes a secret, because demotion widens the capability
surface and widening requires the owner (RFC-0004 A8).

---

## 15. Secret Audit Philosophy

The Audit System (RFC-0001 §5, RFC-0013) records the honest account of what was
done. For secrets it records **metadata, never values** (RFC-0001 §7.6;
RFC-0002 invariant 4).

**Recorded:** provisioning (which secret, purpose, by the Operator);
consumption (which credential, which consumer, when, outcome); invalidation and
destruction (which, when, why); suspected exposure and incident response;
Operator visibility requests.

**Never recorded:** secret values in any form, or enough secret-shaped material
to reconstruct one.

1. **Record before the consequence** — matching RFC-0002 invariant 13.
2. **Append-only and honest** (RFC-0001 §8.10).
3. **Auditable by the Operator** — "what secret was stored, when used, was it
   destroyed" is answerable from the Audit alone.
4. **Transparency, not forensics** (RFC-0001 risk 8) — and the secret guarantee
   is that values were never there to begin with.
5. **Audit retention is RFC-0013's**; this RFC fixes only that no retention
   rule may preserve a secret value.

---

## 16. Secret Interaction with Providers

This section specifies the boundary RFC-0010 already states and cites
(RFC-0010 §11; §15 OQ2): **no secret ever enters a Provider View.**

1. **The Provider View is secret-free by construction** — assembled from
   sanitized, purpose-limited material (RFC-0002 §6; RFC-0007 §12) containing
   nothing RFC-0009 classifies as secret (RFC-0010 §11).
2. **Provider authentication is not View content.** The credential that
   authenticates a call is consumed at the adapter boundary and never appears
   in the View. This is what "no secrets to providers" means: the model's input
   is secret-free, and the transport credential is never a message.
3. **The provider never receives a secret it could retain** and never persists
   what it did receive (RFC-0010 PR8); an attempt is a consumer incident
   (RFC-0009 §13 rule 6).
4. **The Provider View is the only channel.** Audit, secrets, and raw machine
   output never cross the provider boundary by any other path (RFC-0010 PR14).
5. **No fallback, outage, or retry path widens the boundary** (RFC-0007 §15.7);
   the boundary is not mode-dependent.

The Provider sees exactly the sanitized, bounded view the system decides it may
see (RFC-0001 §7), and nothing else.

---

## 17. Secret Interaction with Skills

This section supplies the mechanics RFC-0011 §30 OQ5 delegates here. RFC-0011
§15 fixes the boundary — no secrets in Skill content, no secrets to Skills, no
path to the Operator's secret store — and this RFC makes it hold.

1. **No secrets in Skill content.** Skill packages contain no embedded
   credentials or personal data (RFC-0011 §15 rule 1); a package that requires
   one is invalid, not provisioned.
2. **No secrets to Skills.** The no-secrets boundary applies to Skills exactly
   as to Providers (RFC-0011 §15 rule 2): no values at activation, execution,
   or input.
3. **No path to the Secure Store.** Skills have no access to the Secure Store
   and no mechanism to request a value (RFC-0011 §15 rule 3); secret lifecycle
   is this RFC's.
4. **A Skill never persists what it saw**, even sanitized material (RFC-0011
   SK8).
5. **A Skill cannot consume.** The consumer set is closed (RFC-0009 §8); Skills
   are not in it. Untrusted-until-reviewed material (RFC-0007 §6.12) never gets
   secret surface.

---

## 18. Secret Interaction with Diagnostics

Diagnostics (Collectors) are the deterministic subsystem that reads the machine
(RFC-0002 §6). Two facts govern their secret interaction:

1. **Diagnostics never consume secrets.** They run read-only inspections
   (RFC-0001 §5) and need no protected credential. A diagnostic that requests
   one is misbehaving, and the request is a security incident (RFC-0009 §13
   rule 6).
2. **Diagnostics may discover secrets.** Reading the machine can surface
   secret-shaped values. Those values are Observations (RFC-0005 §2), untrusted
   machine data, handled by containment:
   - They never become Facts: the Fact Layer normalizes safe Observations into
     Facts (RFC-0005 §2); secret-adjacent material is quarantined before the
     pipeline, and a Fact never carries a secret value (RFC-0009 §21).
   - They are redacted at the session boundary before Context or Provider View
     assembly (RFC-0009 §11), testably (RFC-0007 S7).
   - They are never adopted into the Secure Store (RFC-0009 §7 rule 3);
     discovered secrets are contained and discarded, not governed.

Diagnostics are the *source* of the redaction problem (arbitrary secret formats
in machine output), never the *solution*; the solution is the boundary, owned
here (RFC-0009 §11), enforced by the Context Manager (RFC-0004 §4.11).

---

## 19. Secret Interaction with Context

Context is the material the session carries; it is secret-free (RFC-0001 §9;
RFC-0007 T10).

1. **Context never contains a secret value** — not durable, session, or derived
   (RFC-0001 §8.7).
2. **The Context Manager is the enforcement point.** It assembles Provider
   Views with no secrets and may never decide to include one (RFC-0004 §4.11).
   The mechanical enforcement is RFC-0012's; the rule is this RFC's.
3. **Memory never persists secrets.** Durable Memory exists only under consent
   (RFC-0004 §4.11) and persists none of RFC-0001 §9's "never persist" list; a
   secret is never consumed into long-term context (RFC-0001 §5).
4. **Context is a cache of evidence, not a claim** (RFC-0001 §9.4), and secret
   material cannot enter even as evidence. A suspected secret relevant to a
   task is surfaced to the Operator in contained, redacted form; the value is
   never carried.
5. **Truncation and consolidation** (RFC-0001 §9.3; RFC-0012) cannot reveal a
   secret because they operate on already-secret-free material.

---

## 20. Secret Interaction with Audit

The Audit and the secret model share one rule from both sides:

- From the Audit's side (RFC-0001 §5; RFC-0013): the transcript records what
  was proposed, approved, executed, and verified, never a secret value
  (RFC-0001 §7.6; RFC-0002 invariant 4).
- From the secret's side (RFC-0009 §15): the only trace a secret leaves is
  metadata — existence, purpose, use, destruction, exposure — which is exactly
  what the Audit holds.

The interaction is unidirectional and safe: the Audit answers "what did we do
and why" about secrets without ever holding one. Its retention rules (RFC-0013)
are bounded by RFC-0009 §27: no retention rule may preserve a value.

---

## 21. Secret Interaction with Verification

Verification (RFC-0006) compares Facts against machine state deterministically.
Its secret interaction is minimal and strict:

1. **A secret value is never a Fact.** Facts are normalized, deterministic,
   provenance-carrying, and enter Context and Provider Views (RFC-0005 §3, §13)
   — all secret-free. A Fact cannot carry a value without breaking RFC-0001 §9
   and RFC-0007 T10.
2. **Verification never consumes secrets.** It runs deterministic tools
   (RFC-0002 §6) and has no credential surface (RFC-0009 §8).
3. **Verifying a secret is verifying an outcome, never a value.** Whether a
   credential still works is checked at the consumer's boundary; the result is
   a Fact about the outcome ("authentication failed"), never the credential.
4. **Exposure re-verification** follows RFC-0007 §15.10: everything derived
   from a suspected-compromised source is re-verified; the secret itself is
   already invalidated (RFC-0009 §15), so there is no "check whether it leaked"
   step that could carry a value.

---

## 22. Secret Interaction with the Approval Engine

The Approval Engine (RFC-0008) gates every state-changing Action. RFC-0008 §3
fixes two boundaries this RFC makes enforceable:

1. **No Action carries a secret into a Provider View.** Proposals and Plans are
   normalized structures (RFC-0003 §2.8) and the material through the gate is
   secret-free; an Action whose construction needs a secret value is not a valid
   Action, so the gate has nothing secret to inspect.
2. **Elevation never exposes secrets.** Elevation executes the approved Action
   with the approved scope (RFC-0001 §8.6); it never reveals values to the
   Approval Engine, the screen beyond the provisioning boundary, or any
   transcript.
3. **Approval decisions never require a secret.** The Operator approves on
   structured descriptions (RFC-0001 §8.5), never hidden material; the gate is
   more trustworthy for being secret-free.

The Approval Engine's tokens (RFC-0008 §8) are authorization tokens, not
secrets under this RFC — consumed internally at the gate; if compromised, they
fall under the same invalidation rule (RFC-0009 §15).

---

## 23. Secret Visibility

Visibility is the Operator's window into the secret model: generous to the
Operator, closed to everyone else (RFC-0001 §9.2).

1. **Metadata is always visible to the Operator** — what secrets exist, for
   what purpose, when used, when destroyed — via the Accountability View
   derived from the Audit (RFC-0009 §15).
2. **Values are visible only at the provisioning boundary**, on explicit
   request; never re-displayed in Context, transcripts, or general TUI flow.
3. **No component sees a value it does not consume.** The consumer set
   (RFC-0009 §8) is the visibility set.
4. **Wipe is always available.** The Operator can wipe any or all secrets and
   materializations immediately (RFC-0001 §9.2; RFC-0009 §12).
5. **Maintainers see nothing.** Secrets are not debuggable from a transcript,
   log, or crash report, because the values were never in them (RFC-0009 §9,
   §15, §26).

---

## 24. Secret Boundaries

A boundary is a point where data changes holder, purpose, or form. Each secret
boundary has a known enforcement point and failure mode:

| Boundary | What may cross | What never crosses | Enforcement |
|---|---|---|---|
| Machine output → session | Read-only Observations (RFC-0005 §2) | Secret values; unprovable dumps | Redaction at collection and at the session boundary (RFC-0009 §11; RFC-0007 §4) |
| Session → Context | Sanitized, bounded, purpose-limited material | Secret values (RFC-0001 §9) | Context Manager (RFC-0004 §4.11; RFC-0012) |
| Context → Provider View | Sanitized, secret-free material (RFC-0002 §6) | Secret values (RFC-0010 §11) | Context Manager assembly (RFC-0004 §4.11) |
| Adapter → provider transport | The authenticated request | The credential as message content | Adapter consumes at boundary, never forwards (RFC-0009 §16) |
| Session → Audit | Metadata only (RFC-0009 §15) | Secret values (RFC-0002 invariant 4) | Audit writer (RFC-0001 §5; RFC-0013) |
| Session → telemetry | Opt-in, non-secret, non-personal diagnostics (RFC-0009 §26) | Secret values; personal data (RFC-0009 §26) | Telemetry path, absent by default |
| Core → Skill | Sanitized Skill input, no secrets (RFC-0011 §15) | Secret values; Secure Store access (RFC-0011 §15) | No Skill secret surface (RFC-0009 §17) |

Every boundary is one-way outward toward consumption; nothing flows a secret
back in (RFC-0001 §7.6). Each fails closed (RFC-0009 §13).

---

## 25. Secret Trust

Trust is a property of information; authority is a property of actors
(RFC-0004 §2). For secrets this distinction is the safety mechanism:

1. **Possession of a secret grants no authority in this model.** Authority
   comes from the Operator's decisions, recorded and gated (RFC-0004 §3). A
   leaked credential grants capability only at the specific boundary where it
   is consumed — the narrowest possible surface (RFC-0009 §8).
2. **Secrets are information held under custody** (RFC-0009 §4). Their
   trustworthiness is exactly the custody contract and the releasing
   boundaries; there is no "trust the holder" beyond it.
3. **Suspected exposure is compromise** (RFC-0007 §6.10). Trust in a secret
   does not degrade gracefully; it is revoked (RFC-0009 §15).
4. **Redaction does not promote data.** Removing a value does not upgrade its
   source's trust class (RFC-0007 S1).
5. **The boundary, not the secret, is the security boundary.** The invariant is
   that a value cannot reach where it must not be; the secret's own secrecy is
   a second, weaker line. The architecture relies on the former.

---

## 26. Telemetry and Privacy Posture

RFC-0001 Q15 asks whether any telemetry or crash reports are stored, and under
what opt-in. The posture, fixed here:

1. **No telemetry for revenue; no account system** (RFC-0001 §2). No business
   reason to collect, so no collection by default.
2. **Telemetry is opt-in and minimal** — if it exists at all, crash reports and
   basic error diagnostics only; no secret values, no personal data, nothing
   the Operator did not explicitly include.
3. **The no-secret and no-personal-data boundaries apply to telemetry
   unchanged** (RFC-0009 §1, §24); a telemetry path is just another boundary
   that fails closed.
4. **The telemetry *architecture* is deferred to post-MVP** per RFC-0000 §5;
   the deferred questions are recorded in RFC-0009 §30. The default is that no
   telemetry is sent and nothing is collected until the Operator opts in.
5. **Crash reports, if opted into, carry no secrets structurally**: a report
   cannot contain a value that was never written anywhere durable (RFC-0009 §9).

---

## 27. Retention Defaults

Retention is persistence philosophy applied over time (RFC-0001 §9.5: retention
by consent, not by default).

1. **Session-scoped by default.** Everything the session materializes — Context,
   materializations, working copies — is gone when the session ends.
2. **Secret values: never durable.** The Secure Store is the only place a value
   may exist, and even there persistence is purpose-scoped and consent-based
   (RFC-0009 §9). No durable secret artifact exists anywhere else.
3. **Durable material is explicit.** Anything retained beyond the session
   exists only under consent (RFC-0001 §9.5) and none of it may hold a value
   (RFC-0009 §9, §15).
4. **Audit retention is RFC-0013's**, bounded by RFC-0009 §15 rule 5: no
   retention rule may preserve a value.
5. **Retention lapses are destruction events** (RFC-0009 §12). Retention never
   outlives purpose.

---

## 28. Secret Rules (Normative)

| ID | Statement | Rationale | Test |
|---|---|---|---|
| SC1 | **Secrets are segregated.** Every secret value is stored only in the Secure Store and materialized only at the boundary where it is consumed. | RFC-0001 §8.7: secrets are stored in the OS secret store, scoped to their use. | Store a credential; verify no other component holds the value and only the consuming boundary can materialize it. |
| SC2 | **The default is secret-free.** By default a secret is never in Context; no exception exists for any derived artifact. | RFC-0001 §8.7: the default is a secret is never in context. | Build Context from material containing a known token; verify the token appears nowhere in Context or its summaries. |
| SC3 | **No secret enters a Provider View.** No secret value crosses the provider boundary. | RFC-0001 §7.6; RFC-0010 §11: the no-secrets boundary. | Attach a token to input; verify it never appears in the Provider View. |
| SC4 | **No secret enters the Audit.** The Audit records metadata, never values. | RFC-0001 §7.6; RFC-0002 invariant 4. | Run the full lifecycle; grep the transcript for the value; verify it is absent. |
| SC5 | **No secret reaches an extension.** No Skill or other extension receives or stores a secret value. | RFC-0011 §15 and SK8. | Offer a secret-adjacent token to a Skill; verify it never arrives and nothing is persisted. |
| SC6 | **Secrets cross boundaries one way only.** A value crosses a boundary only at its point of consumption and never propagates outward. | RFC-0001 §7.6. | Trace every boundary crossing of a value; verify each is a single scoped consumption with no onward hop. |
| SC7 | **Every secret is purpose-scoped.** A secret is bound to the purpose for which it was provisioned and the scope is never widened silently. | RFC-0001 §9.1: purpose-limited. | Use a credential for a second, unstated purpose; verify refusal and an Audit record. |
| SC8 | **Every secret has exactly one owner.** The Operator owns; the Secure Store holds custody; the Provider adapter consumes under a scoped grant. | RFC-0004 §3: exactly one owner per row; RFC-0004 A8: no actor extends its own grant. | Enumerate every secret; verify each maps to exactly one owner and one custody holder. |
| SC9 | **No Action carries a secret.** No Proposal, Plan, or Action carries a secret value. | RFC-0008 §3: no Action may carry a secret into a provider view. | Construct a proposal containing a token; verify it cannot reach the gate or the executor. |
| SC10 | **Elevation exposes nothing.** Elevation never reveals a secret value to any screen, transcript, or component. | RFC-0008 §3: elevation never exposes secrets. | Elevate and execute an approved Action; verify no value is displayed, logged, or forwarded. |
| SC11 | **Retention is by consent, not by default.** Anything retained beyond the session is explicit and reversible; secret values are never durable. | RFC-0001 §9.5. | End a session; verify no secret value or unconsented material persists anywhere. |
| SC12 | **Destruction is timely and complete.** When a purpose lapses, the value and every materialization are destroyed. | RFC-0001 §9.1. | Rotate a credential; verify the old value and all materializations are gone from storage and memory. |
| SC13 | **Redaction is deterministic and testable.** Redaction is applied before anything leaves the session and is checkable by a deterministic rule. | RFC-0007 S7. | Feed hostile secret-shaped inputs through the boundary; verify the output contains no secret value. |
| SC14 | **Redaction fails closed.** If the no-secret property cannot be established, the boundary holds closed and the Operator is told. | RFC-0001 §8.12; RFC-0007 §15.6 and §15.7. | Disable the redactor; verify no raw untrusted text reaches a Provider View and the Operator is informed. |
| SC15 | **Exposure is compromise.** Suspected exposure invalidates and destroys the secret and everything derived from it, and is disclosed and recorded. | RFC-0007 §6.10: suspected exposure = compromised. | Simulate a leaked token; verify immediate invalidation, destruction, disclosure, and an Audit record. |
| SC16 | **Privacy parity.** Personal data is governed by the same boundaries as secret values unless the Operator explicitly demotes it for a stated purpose. | RFC-0001 §9: personal data never persists by default. | Mark content private; verify it is treated as secret across every boundary until an explicit demotion. |

---

## 29. Interaction with other RFCs

- **RFC-0001.** Supplies the principles this RFC realizes (RFC-0001 §8.7,
  §8.8, §8.12), the one-way rule (RFC-0001 §7.6), the context philosophy
  (RFC-0001 §9, §5), and Q14/Q15.
- **RFC-0002.** The LLM is never consulted with secrets (RFC-0002 §6, invariant
  4); the Audit records before the consequence (invariant 13); failure ordering
  (RFC-0002 §10).
- **RFC-0003.** Canonical vocabulary; the Provider View definition (RFC-0003
  §2.8); Part II amendment process for the RFC-0009 §32 additions.
- **RFC-0004.** Ownership and authority rules (RFC-0004 §3, §6, §8 A8); the
  Context Manager's "may never decide to include a secret" (RFC-0004 §4.11).
  This RFC assigns the Secrets ownership row (RFC-0009 §4), which RFC-0004 §3's
  table should gain by additive amendment when this RFC is accepted; the row
  alters no existing row and weakens no invariant.
- **RFC-0005.** The Fact model, secret-free by construction (RFC-0005 §3,
  §13); the Observation pipeline whose secret-adjacent inputs this RFC
  quarantines (RFC-0005 §2).
- **RFC-0006.** Verification consumes Facts (RFC-0006 §3); secrets are never
  Facts and verification never consumes them (RFC-0006 V1, V8).
- **RFC-0007.** Sanitization principles (S1–S8), trust classes and failure
  behavior (RFC-0007 §11, §15), the secrets category (RFC-0007 §6.10), the
  binary no-secret property (T7, T10); redaction mechanics delegated here
  (RFC-0007 §16 OQ3).
- **RFC-0008.** The approval gate and elevation rules; the "no Action carries a
  secret" and "elevation exposes nothing" boundaries (RFC-0008 §3).
- **RFC-0010.** The no-secrets-to-providers boundary (RFC-0010 §11, §15 OQ2,
  PR8, PR14).
- **RFC-0011.** The no-secrets boundary for Skills (RFC-0011 §15, §30 OQ5,
  SK8).
- **RFC-0021.** Passwords and secrets are this RFC's subject, not the machine
  abstraction's (RFC-0021 §4.11).

Forward references (planned RFCs this model constrains): RFC-0012 (Context &
Memory enforce the secret-free boundary); RFC-0013 (Audit format and
retention); RFC-0015 (presentation of redaction); RFC-0016 (provisioning and
opt-in configuration); RFC-0017 (compatibility); RFC-0020 (Secure Store
mechanics, redaction catalogue, telemetry implementation).

---

## 30. Open Questions

Each names its owner. None blocks the secret model's guarantees.

1. **Secure Store mechanics.** Which OS secret store (or equivalent) is used and
   how its interface is presented (RFC-0001 §8.7) — RFC-0020 (implementation).
2. **Redaction rule catalogue.** The exact deterministic rules for secret-shaped
   patterns and where collection exclusion applies — RFC-0020 and RFC-0012.
3. **Full telemetry architecture.** The concrete opt-in flow, crash-report
   format, and diagnostics collected (RFC-0001 Q15) — the telemetry half, which
   RFC-0000 §5 defers to post-MVP. This RFC fixes the posture (§26).
4. **Audit retention limits.** Concrete retention periods for secret metadata —
   RFC-0013.
5. **Credential provisioning UX.** How the Operator enters and re-views keys at
   the provisioning boundary (RFC-0009 §7, §23) — RFC-0015 and RFC-0016.
6. **Personal-data detection.** Deterministic heuristics for recognizing
   personal data beyond the explicit classes — the post-MVP half of this RFC's
   privacy scope, recorded here so it is not dropped (RFC-0000 §5).

---

## 31. Risks

| Risk | Mitigation |
|---|---|
| **Credential in machine output** | Exclusion at collection + redaction at the session boundary + containment (SC13, SC14; RFC-0007 S8) |
| **Secret reaching the Provider View** | Secret-free construction, adapter-boundary consumption, fail-closed redaction (SC3, SC6; RFC-0010 PR8, PR14) |
| **Secret in the Audit/transcript** | Metadata-only audit, record-before-consequence ordering (SC4; RFC-0002 invariant 4) |
| **Skill or extension exfiltrating** | Closed consumer set, no Skill secret surface, consumer incidents (SC5; RFC-0011 §15) |
| **Elevation leaking a secret** | Elevation executes approved scope, never displays values (SC10; RFC-0008 §3) |
| **Over-broad classification blocking tasks** | Layered redaction; Operator can see what was withheld (SC13, SC14; RFC-0007 §15.6) |
| **Under-classification (false negative)** | Fail-closed on unclassifiable data; exposure is compromise (SC14, SC15; RFC-0007 §6.10) |
| **Retention outliving purpose** | Session-scoped default, consent-based durability, timely destruction (SC11, SC12; RFC-0001 §9.5) |
| **Provider attempting to persist** | PR8 treated as a consumer incident, immediate invalidation (SC15; RFC-0010 PR8) |
| **Telemetry collecting secrets** | No telemetry by default; opt-in, non-secret posture; structural absence of values (§26; RFC-0001 §2) |

---

## 32. Vocabulary Additions for RFC-0003

The following terms are defined in this RFC and must be added to RFC-0003 Part
I by additive amendment: **Secret**, **Secret Value**, **Secret Metadata**,
**Secret Classification**, **Secret-Shaped Value**, **Secure Store**,
**No-Secrets Boundary**, **Consumption Boundary**, **Suspected Exposure**,
**Redaction**, **Telemetry Posture** — defined at first use in §1, §3, §4, §5,
§8, §11, §15, and §26. Secret, Fact, Observation, Action, Proposal, Plan,
Approval, Policy, Context, Provider View, Verification, and Audit already exist
in RFC-0003 Part I and are used here with their canonical meanings. This RFC
also proposes RFC-0004 §3's table gain a **Secrets** row by amendment (§29).

---

*End of RFC-0009. Normative: sections 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
13, 14, 15, 16, 17, 18, 19, 20, 21, 22, 23, 24, 25, 26, 27, 28. Explanatory and
load-bearing: sections 0, 29, 30, 31, 32. Any change to a secret
responsibility, boundary, lifecycle step, classification rule, failure rule,
retention rule, consumer set, or an invariant SC1–SC16 is a BREAKING change
and must be made by amendment (RFC-0003 Part II).*
