# RFC-0001 — Architecture and Design Foundations

**Status:** Accepted
**Date:** 2026-08-01
**Scope:** Whole-project architecture
**Audience:** Future maintainers
**Supersedes:** Nothing

---

## 0. Preamble

This is the first architecture document of the project and the foundation every
later RFC builds on. It deliberately specifies **what** the system is and **why**,
and explicitly avoids *how* — no APIs, no data schemas, no implementation
details, no code.

If a future decision contradicts anything in this document, that decision must
be discussed and this document amended through the same RFC process. Silently
violating a boundary here is considered a design defect.

Two terms recur throughout and are defined once:

- **The Assistant** — the whole product as the user experiences it.
- **The Operator** — the human running the Assistant on their machine.

---

## 1. Project Goals

1. Provide an open-source, terminal-based assistant that helps Linux beginners
   diagnose and repair their own systems, with guidance they can understand.
2. Keep the human in the loop at all times: the Assistant proposes, the Operator
   disposes.
3. Let the Operator use any LLM they prefer — OpenAI, Anthropic, Gemini, local
   models — through a uniform provider abstraction, with no vendor lock-in.
4. Give the AI *controlled and audited* access to inspect the machine and to run
   only those commands the Operator has explicitly approved.
5. Grow a community skill ecosystem so that experts can package reusable,
   reviewable troubleshooting procedures for beginners.
6. Deliver an interaction experience comparable to Claude Code or OpenCode in
   quality, but specialized for Linux system care rather than software
   development.

Success is measurable, not aspirational. The project is on track when:

- A beginner can describe a symptom in plain language and be walked from
  diagnosis to a *verified* fix, without ever being told to "just trust the AI."
- Every consequential action is explained before it happens, in terms a beginner
  can grasp.
- The Assistant remains usable, honestly degraded, when the preferred provider
  is unavailable.
- A skill authored by a community member works reproducibly across the supported
  distro families.

---

## 2. Explicit Non-Goals

Non-goals are as binding as goals. They exist to protect the project from the
scope creep that destroys focused tools.

The project deliberately does **not** attempt to be:

1. **An unattended remediation agent.** No mode exists in which the machine is
   modified without a human having approved the modification. Autonomy is never
   a design goal.
2. **A general-purpose coding assistant.** The UX is inspired by Claude Code /
   OpenCode; the mission is not. The Assistant edits system configuration, not
   application source code.
3. **A configuration management / fleet tool.** It is not an Ansible, Puppet,
   or Terraform replacement, and will not manage groups of machines.
4. **A monitoring or observability platform.** It reads machine state on demand
   during a troubleshooting session; it does not watch systems 24/7 or keep
   time-series data.
5. **A security scanner, malware hunter, or forensics tool.** A tool that can
   run approved commands must never be mistaken for a trusted evidence or
   intrusion-analysis instrument.
6. **A remote-administration platform.** Managing machines over SSH from a
   central seat is explicitly out of scope for the initial design. A local
   process acting on the machine it runs on is the only model.
7. **A commercial LLM gateway or proxy.** No bundling of API keys, no paid
   tiers, no account system, no telemetry-for-revenue. Bring-your-own-key is a
   feature, not an upsell.
8. **An authoritative source of Linux truth.** The Assistant explains and
   guides; it does not *define* how Linux works. Authority belongs to the
   distro, the documentation, and the machine itself.
9. **A distributor or maintainer of OS packages, kernels, or systemd units.**
   It invokes the system's own package manager and init system; it does not
   ship its own.
10. **A root wrapper or privilege-escalation utility.** It will use the
    system's existing elevation mechanisms under policy, but providing
    "sudo for beginners" is not its purpose.
11. **A cross-platform tool.** Linux only, initially. Supporting macOS or
    Windows would dilute every safety mechanism in this document.
12. **A replacement for `man`, distro wikis, or the Operator's own judgement.**
    It augments understanding; it never substitutes for it.

**Why this matters:** the single greatest risk to a project like this is being
pulled into being "a general agent that can also fix your computer." Each
non-goal above is a statement of what we are willing to *not* ship in order to
ship the thing we do well: safe, explainable Linux care for beginners.

---

## 3. Core Design Principles

These are ranked; when principles conflict, the earlier one wins unless a
later one is explicitly invoked with justification.

1. **Safety before convenience.** Any feature that increases power over the
   machine must carry its own safety cost. We never trade safety for a smoother
   demo.
2. **Human approval before risky actions.** Read-only inspection may proceed
   under policy; anything that changes system state requires explicit Operator
   approval first. There is no standing authorization to "do whatever is
   needed."
3. **Explain every important action.** Before an action, the Operator sees what
   will happen, why, and what could go wrong — in language proportionate to the
   risk. An action that cannot be explained is an action that cannot be taken.
4. **Never assume — verify.** The Assistant's beliefs about the machine must be
   grounded in evidence gathered from the machine, never in what "probably" is
   the case. State must be confirmed before acting and after acting.
5. **Prefer deterministic information over AI guesses.** The LLM may form
   hypotheses; it may never fabricate facts. When a deterministic check exists
   for a piece of information, the Assistant must use it.
6. **The AI is an assistant, not an authority.** The LLM proposes and explains;
   it does not command. Its output is advisory by construction and is treated
   as untrusted input by the rest of the system (see Trust Boundaries).
7. **Least privilege.** The Assistant runs with the minimum authority needed for
   the task at hand, and only as high as a single action requires.
8. **Default deny.** Everything is disallowed until an explicit, explainable
   permission says otherwise.
9. **Everything consequential is audited.** What was asked, what was run, what
   it returned, and who approved it — recorded durably and shown to the
   Operator.
10. **Fail safe and fail loud.** When uncertain, the Assistant must stop and ask,
    never guess-and-continue. When something goes wrong, it must say so clearly
    and stop escalating.
11. **The Operator owns the machine.** The Assistant is a guest with delegated
    powers. The Operator can revoke, refuse, or override at any point, and can
    see and export everything the Assistant knows.
12. **A model the beginner can hold in their head.** The product's behavior
    should be simple enough that a user can predict it: *the AI talks, the tool
    gathers facts, the user approves actions.* If a feature can't be explained
    in that frame, it doesn't belong in the core.

---

## 4. High-Level Architecture

The system is a set of cooperating subsystems with strict, one-way dependency
intentions. No subsystem reaches into another's internals.

```
                 ┌──────────────────────────────────────────────┐
                 │  Presentation (TUI)                          │
                 │  the Operator's whole world                  │
                 └───────────────┬──────────────────────────────┘
                                 │
                                 ▼
                 ┌──────────────────────────────────────────────┐
                 │  Conversation / Orchestration Core           │
                 │  owns the session loop and the rules         │
                 └──┬──────────────┬───────────────┬────────────┘
                    │              │               │
         ┌──────────▼───┐  ┌───────▼────────┐  ┌───▼────────────┐
         │ Providers    │  │ Diagnostics &  │  │ Action         │
         │ (LLM adapters)│ │ Fact Layer     │  │ Execution      │
         │ untrusted    │  │ deterministic  │  │ gated, audited │
         └──────────┬───┘  │ read-only      │  └───┬────────────┘
                    │      └────────┬───────┘      │
                    │               │              │
                    │      ┌────────▼───────┐      │
                    └──────▶│ Approval &    │◀─────┘
                           │ Policy Engine │
                           │ (the gate)    │
                           └────────┬──────┘
                                    │
                 ┌──────────────────▼──────────────────┐
                 │  Skills (registry + runtime)        │
                 │  Context & Memory                   │
                 │  Audit & Transcript                 │
                 │  (supporting layers, see below)     │
                 └─────────────────────────────────────┘
```

The architecture has four layers:

**A. Presentation.** The TUI is the only interface. It renders conversation,
presents evidence, asks for approval, and exposes the audit trail. It knows
nothing about Linux; it is a rendering and input surface.

**B. Core orchestration.** The Conversation/Orchestration Core is the only
subsystem that composes the others. It runs the session loop (gather → plan →
propose → approve → act → verify), enforces the principles in Section 3, and
decides *when* each other subsystem is consulted. It is deliberately thin: it
orchestrates and enforces rules; it contains no domain logic about distros,
packages, or services.

**C. Capability subsystems.** Three capabilities sit behind the Core:
- **Providers** translate between a single internal, provider-agnostic
  representation and each vendor's API. The Core speaks one dialect; vendors
  speak their own.
- **Diagnostics & Fact Layer** runs *read-only* inspection and normalizes
  machine output into structured, deterministic facts. This is the only source
  of factual claims about the machine.
- **Action Execution** runs approved, state-changing commands under policy,
  captures their results, and reports success/failure deterministically.

**D. Guardrails and supporting layers.**
- **Approval & Policy Engine** classifies proposed actions by risk and decides
  what must happen before execution (confirmation, warning, or block).
- **Skills** are packaged, versioned troubleshooting procedures that bundle
  diagnostics, explanations, and approved-safe action sequences.
- **Context & Memory** holds what the session is allowed to remember.
- **Audit & Transcript** durably records everything consequential.

The single most important architectural invariant:

> **No path from the LLM to the machine is direct.** Providers produce
> *proposals*. Proposals become reality only through Diagnostics (read-only),
> the Approval engine, Action Execution, and an explicit Operator decision.
> The LLM cannot execute; the machine cannot execute the LLM.

---

## 5. Component Responsibilities

Responsibilities only. Interfaces and APIs are the subject of later RFCs.

### Presentation (TUI)
- Render the conversation and current state to the Operator.
- Present evidence and proposed actions in a legible, inspectable form.
- Collect approvals, refusals, and free-text Operator input.
- Expose the audit log and context view to the Operator on demand.
- Translate risk levels into *presentation* tone and layout (never into policy).

### Conversation / Orchestration Core
- Own the session loop and its state transitions.
- Enforce the decision rules of this RFC (approval gates, verification-before-
  claim, fail-safe stops).
- Decide which capability subsystem to consult and in what order.
- Keep the Provider's world (a text stream) separate from the machine's world
  (deterministic facts and gated actions).
- Degrade gracefully: define what the session looks like when a provider is
  missing, offline, or unresponsive.

### Providers (LLM adapters)
- Expose one uniform interface to the Core for all supported vendors.
- Translate internal representations to and from each vendor's API and
  prompting conventions.
- Normalize and validate provider output into the internal form.
- Treat provider output as **untrusted data** and never as instructions.
- Report provider errors and refusals honestly to the Core.

### Diagnostics & Fact Layer
- Enumerate and run read-only inspections appropriate to the task.
- Normalize distro-specific output into a stable, structured fact model.
- Attach provenance (which command, when, exit status) to every fact.
- Never mutate state; never consume secrets into long-term context.
- Distinguish "fact unknown," "fact verified," and "fact failed to collect" —
  these are different and must stay different.

### Action Execution
- Execute only actions that have cleared the Approval & Policy Engine *and*
  the Operator.
- Apply the technical guardrails of a sanctioned action (scoping, timeouts,
  output capture, no secret leakage).
- Report exit status, output, and state-delta before/after, deterministically.
- Never guess whether an action succeeded; verify or state it as unverified.

### Approval & Policy Engine
- Classify each proposed action into a risk class (e.g., read-only / benign /
  consequential / destructive) using deterministic rules, never the LLM's
  self-assessment.
- Decide the required gate per class: silent (read-only), notify, confirm,
  confirm-with-warning, or block.
- Enforce default-deny and least-privilege for elevation.
- Remain local and deterministic; it is the part that must never be surprised.

### Skills
- Define the packaging format for troubleshooting procedures.
- Validate, version, and (for trusted sources) authenticate skill packages
  before their content is loaded or executed.
- Isolate skill-provided instructions from the core's own decision rules.
- Enforce that skills declare their risk profile and privilege needs up front
  and are evaluated under the same Approval engine as everything else.

### Context & Memory
- Hold only what Section 9 permits.
- Track session history and the "facts known about this machine" that are
  legitimately needed.
- Provide the Operator a complete, exportable view of what is remembered.
- Enforce redaction of secrets before anything leaves a session.

### Audit & Transcript
- Record every consequential event: proposals, approvals, refusals, commands,
  outputs (policy-limited), and outcomes.
- Write to durable, append-only storage; resist tampering after the fact.
- Be the mechanism by which the Operator can answer "what did we do and why."

---

## 6. System Boundaries

### Inside the project
- The session loop and orchestration rules.
- The TUI and all Operator-facing interaction.
- Provider adapters and the provider-agnostic internal representation.
- Diagnostic tooling, fact normalization, and fact models.
- The approval and risk-classification engine.
- The skill format, registry, loader, and runtime guardrails.
- Context and memory policy, and its implementation.
- The audit/transcript mechanism.
- User-facing configuration of all of the above.

### Outside the project (by design)
- **The LLM vendors and local model runtimes.** They are external services we
  call. Their reliability, safety, and data handling are outside our control —
  which is exactly why they sit behind an untrusted boundary.
- **The distro, its package manager, init system, kernel, and hardware.** We
  invoke them; we never own them.
- **The Operator's system policy.** The machine's own security policy (users,
  sudo rules, AppArmor/SELinux, firewalls) is defined by the distro and the
  Operator. We operate *under* it and must never try to override it.
- **Community skill hosting.** A marketplace or central skill repository is an
  ecosystem concern, not a core feature. Distribution and trust evaluation of
  skills is separate from the runtime that executes them.
- **Backup systems and rollback infrastructure.** We may call them, but we do
  not implement them.
- **Notifications, messaging, and remote interfaces.** Anything that lets the
  Assistant be invoked or observed from outside the local terminal.

Boundary test — a feature is **inside** only if it supports the core loop
(*the AI talks, the tool gathers facts, the user approves actions*) or the
supporting layers around it. If a feature could live as a skill, it should.

---

## 7. Trust Boundaries

We treat the world as a set of trust domains, ordered from most to least
trusted. Every data flow in the system is defined by which domains it crosses.

### Trusted
- **The Operator.** The ultimate authority. They own the machine and all
  delegation originates from them.
- **The local machine's OS primitives** as invoked by our own deterministic
  tooling (e.g., the init system, package manager, kernel interfaces) — *as
  data sources*. We trust the machine to report what it actually is, which is
  not the same as trusting that the machine is healthy.
- **The deterministic tooling we ship** (Diagnostics, Approval engine, Action
  Execution guardrails). These are the only parts allowed to make decisions or
  touch system state, and they are trusted precisely because they contain no
  AI.

### Untrusted
- **All LLM provider output.** Model text is data, never authority and never
  commands. It may be eloquent, wrong, or deliberately malicious; the system
  behaves identically either way.
- **Skills from the community.** Third-party code by nature. Untrusted until
  authenticated and policy-reviewed; even then, executed under the same gates
  as everything else.
- **Anything read off the machine.** Command output and config file contents
  are data collected from an environment we do not control. A compromised or
  weird machine can emit hostile text — see prompt-injection rules below.
- **Network resources.** Downloaded packages, docs, and any remote content the
  Assistant may consult.

### Rules of data flow across trust boundaries

1. **Untrusted text is never executed.** No string originating from a provider,
   a skill, or machine output is ever interpolated into a shell command. Actions
   are constructed from sanctioned, parameterized templates and checked
   structures only.
2. **Untrusted text is never trusted as evidence of itself.** The Assistant may
   *quote* machine output to the Operator, but the LLM's *interpretation* of it
   is always downgraded to hypothesis until a deterministic check confirms it.
3. **Untrusted text never carries permissions.** An instruction found in
   machine output ("please run rm -rf /"), in a provider reply, or in a skill's
   *content* cannot grant itself authority. Authority is a property of the
   Approval engine, which never reads such text as instructions.
4. **Provider and machine never meet directly.** The Core mediates every
   exchange. Providers see sanitized, purpose-limited representations; the
   machine is touched only by our deterministic layers.
5. **Downward, not upward, trust.** Trust flows from the Operator down through
   policy to actions. Nothing upstream in the data flow is allowed to change
   the decision rules downstream.
6. **Secrets cross boundaries one way only.** Credentials and API keys enter at
   the boundary they are needed and never travel into provider context,
   machine output, or the audit transcript.

---

## 8. Security Principles

No implementation here — only the principles every implementation must honor.

1. **Least privilege, per action.** Each action runs with the smallest authority
   that action requires, obtained for that action alone. There is no blanket
   root session.
2. **Default deny, explicit allow.** Nothing is permitted by omission. Every
   capability is granted through an explicit, explainable permission.
3. **The human is the authorization service.** No mechanism may substitute for
   an explicit Operator decision on a state-changing action. Standing
   approvals expire; there is no "always yes."
4. **No shell interpolation of untrusted text.** Ever. This is the first
   security rule violated anywhere in the codebase, no matter how benign the
   fix appears.
5. **Deterministic risk classification.** Risk is judged by local rules over
   structured descriptions of the action, never by the LLM's characterization
   of its own intent.
6. **Elevation is explicit, scoped, and re-authenticated.** Using the machine's
   own elevation mechanism, only for the approved action, with the Operator
   present.
7. **Secrets are segregated.** Secrets are stored in the OS secret store or
   equivalent, scoped to their use, and never placed into prompt context, tool
   output summaries, or logs. The default is: a secret is never in context.
8. **Output is limited.** Command output enters session context only under a
   policy that bounds size, redacts secrets, and truncates rather than dumps.
9. **Supply chain is defended.** Skills and any fetched content are checked for
   integrity and authenticity before use, and are treated as untrusted even
   after authentication.
10. **The audit trail is append-only and honest.** It must be difficult to
    tamper with silently, and easy for the Operator to read. Its value is
    accountability, not forensics; see Architectural Risks.
11. **Minimal attack surface.** The Assistant ships the smallest set of
    capabilities needed. Capabilities the user doesn't use are off by default.
12. **Fail closed.** Any error in a safety mechanism (unparseable policy,
    unknown risk class, failed verification) results in blocking the action and
    telling the Operator, never in proceeding.

---

## 9. Context Philosophy

Context is power. We are deliberately miserly about what we keep, and generous
about what the Operator can see and delete.

### What should persist
- What the Operator explicitly asked and explicitly authorized.
- High-signal facts about the machine that were *collected, not guessed*:
  distro, kernel, key services, relevant configuration snapshots — limited to
  what current and reasonably foreseeable tasks need.
- The history of approved actions and their verified outcomes (via the audit
  layer).
- Operator preferences for how the Assistant behaves (verbosity, provider
  choice, skill set) — these are the Operator's own decisions about the tool.

### What should never persist
- **Secrets, credentials, and API keys.** Under any condition. These exist only
  inside the secure store and only when needed.
- **Raw, unbounded command output.** Output is summarized, truncated, and
  redacted. Full dumps are ephemeral by default and never stored by default.
- **Content the Operator marks as private**, or content from which private data
  is inferable.
- **Anything without a stated purpose.** If the Assistant cannot say why a
  piece of information is being kept, it must not be kept.
- **Provider conversation dumps that predate our redaction.** Redaction happens
  before anything leaves the session, so there is nothing to clean up later.
- **Personal data not required for the troubleshooting task** (e.g., browsing
  history, unrelated user documents discovered incidentally).

### Governing rules
1. **Purpose-limited.** Context is retained only in service of the session or a
   stated future need, and is deleted when that purpose lapses.
2. **Visible and exportable.** The Operator can always see exactly what the
   Assistant remembers about their machine, in plain form, and can wipe it.
3. **Bounded.** There is a ceiling on how much context is carried forward; when
   it fills, the Assistant consolidates or drops, transparently, rather than
   silently growing.
4. **Never authoritative.** Context is a cache of evidence, not a claim. If the
   current session contradicts stored context, the machine is re-checked and the
   fresh fact wins.
5. **Retention by consent, not by default.** The default is session-scoped
   memory; durable memory is an explicit, reversible choice.

---

## 10. Failure Philosophy

The Assistant's behavior when it does not know, cannot verify, or is contradicted
is a feature, not a bug. These rules describe how it must behave.

1. **Uncertainty is disclosed, not hidden.** "I don't know" and "I couldn't
   verify this" are first-class outputs, with a suggested next step (run a
   diagnostic, consult a doc, ask the Operator).
2. **The LLM hypothesizes; the machine testifies.** When the LLM is unsure of a
   fact, it must propose a diagnostic that would produce that fact
   deterministically, not assert the fact.
3. **Failed diagnostics are facts too.** If a command fails or times out, the
   Assistant reports the failure and treats the state as *unknown*, never as
   "assume it was fine."
4. **Stop on contradiction.** If evidence contradicts a belief, the Assistant
   must stop the current path, surface the contradiction, and re-evaluate with
   the Operator. It must never proceed on the belief.
5. **Verification before victory.** A fix is not complete until it is verified
   with deterministic evidence (exit status, changed state, or a confirmatory
   diagnostic). Unverified work is labeled unverified.
6. **Fail safe, fail loud, fail small.** On error, stop escalating, make the
   error visible and understandable, and keep the machine in a state no worse
   than before (see also rollback expectations in Open Questions).
7. **Provider loss is an event, not a crash.** If the preferred provider is
   unavailable, the Assistant should offer the configured fallback (another
   provider or a local model) and, if none exists, present the diagnostic facts
   it already gathered in a plain, useful form.
8. **Do not guess the answer to save face.** Fabricated diagnostics, invented
   exit codes, and confident wrongness are the cardinal sins. The safest reply
   is often: "here is what we know for certain, and here is what I could not
   determine."
9. **The last resort is the human.** When the Assistant is out of its depth —
   filesystem corruption, boot failures, potential data loss — its job is to
   frame the situation clearly, list safe options, and hand over to the
   Operator or the distro's own recovery tools. Escalating to a human is a
   success condition, not a failure mode.

---

## 11. Extensibility Philosophy

The product must grow — new skills, new providers, new diagnostic domains —
without modification to the Core. The Core is the constitution; extensions are
the amendments. Amendments must not rewrite the constitution.

### General rules
1. **The Core defines contracts, not specifics.** New functionality attaches at
   defined extension points (provider interface, skill format, fact model,
   risk-classification hooks) and never edits Core code.
2. **Extension by registry, not by branching.** New providers, skills, and
   diagnostic domains register themselves. The Core enumerates what is
   registered and knows each entry only through its declared contract.
3. **Every extension declares its surface up front.** A skill states: what
   distro families and versions it targets, what privileges it requires, what
   risk class its actions fall in, what it reads, what it changes, and how its
   success is verified. Declared, reviewable intent is what makes a third-party
   thing safe to consider.
4. **Additive means non-destructive.** A new skill must not alter how existing
   skills or Core behavior work. Versioning and compatibility guarantees live
   with the Core's contracts.
5. **Ships unsafe by default.** Anything loaded from outside the Core is
   treated as untrusted until its declared intent passes policy, and even then
   it is executed under the same Approval engine as everything else.
6. **The ecosystem is separate from the runtime.** Skill distribution, review,
   and trust rating are ecosystem concerns that must not couple to how skills
   are executed. The runtime must not care where a skill came from, only
   whether it is authenticated and within policy.

### The two primary extension axes
- **Skills** extend *what the Assistant can do*. They are the mechanism by
  which the community contributes knowledge and procedures. A skill packages
  diagnostics, explanations, and gated action sequences, and is bound by the
  same failure and approval rules as Core behavior.
- **Providers** extend *how the Assistant thinks*. New providers implement the
  one internal representation with a new adapter. The Core holds no knowledge
  of any vendor's API, prompt format, or pricing; a vendor's quirks are the
  adapter's problem.

### Future modules
New subsystems (e.g., a new diagnostic domain, an output-channel, an
additional safety mechanism) must be introducible the same way: define a
contract, register an implementation, and leave the Core's decision rules
intact. Any proposed change that requires editing the Core's rules to ship a
feature should be treated as a Core change, requiring its own RFC — not slipped
in as an extension.

---

## 12. Open Questions

These are the architectural questions that must be answered — by design and
investigation, and ideally with dedicated RFCs — before implementation begins.

### Trust and authorization
1. What is the precise taxonomy of action risk classes, and where are the
   boundaries between "notify", "confirm", "confirm-with-warning", and "block"?
   Is the taxonomy per-command, per-action, or per-intent?
2. What granularity of approval is right: per individual command, per logical
   action (possibly several commands), per session, or a mix? How are
   multi-command "fix plans" approved without becoming a rubber stamp?
3. How does elevation work end to end — which mechanism (e.g., `sudo`,
   `pkexec`), how is it scoped to a single action, and how is it revoked?
4. What does "default deny" mean for read-only commands? Is there a
   pre-approved read-only set, and who defines it?
5. How are standing approvals represented, how do they expire, and how do we
   prevent "approve all" habits?

### Diagnostics and facts
6. What is the canonical fact model, and how do we normalize across distro
   families (apt/dnf/pacman/zypper/Nix, systemd/sysv, etc.) without drowning
   in distro-specific code?
7. How do we handle immutable and atomic systems (e.g., ostree/Flatpak
   designs) where "change the file" is the wrong model?
8. What is the maximum bound on diagnostic output entering context, and how is
   truncation/redaction done safely?
9. How are facts about the machine kept current within a session, and how is
   staleness detected?

### Verification and rollback
10. What counts as deterministic verification that a fix worked? Exit codes?
    State diffs? Re-running diagnostics? Which is authoritative?
11. What, if anything, does the project promise about rollback? Which actions
    are inherently rollback-safe (package install/uninstall) and which are not
    (editing boot config)? How is that communicated to the Operator?
12. How are catastrophic cases (system fails to boot after a change) surfaced
    to a beginner who is now, possibly, outside the TUI?

### Context and privacy
13. What is the exact persistence model — what is session-only, what is
    durable, and what consent flow gates durable memory?
14. Which secret-redaction approach is sufficient given that machine output
    can contain secrets in arbitrary formats?
15. Do we store any telemetry or crash reports, and under what opt-in model?

### Providers
16. How much provider variance in tool-calling reliability are we willing to
    absorb, and what is the minimum capability a provider must have to be a
    supported backend? (e.g., local models with weak tool-calling.)
17. What is the provider-agnostic internal representation, and can it
    faithfully represent multi-step plans, evidence, and approval requests to
    both strong and weak models?
18. How are provider outages and refusals handled without a crash, and what is
    the degraded-mode UX?

### Skills and the ecosystem
19. What is the skill packaging format, and how are skills versioned and
    signed? Who are the initial trusted signers, and what is the trust
    lifecycle?
20. What is the skill review process for anything shipped or recommended as
    trusted?
21. How are skills sandboxed at runtime — isolated environments, capability
    declarations, or both?
22. Who audits skills for the risk classes they *declare* vs. the commands they
    *actually* contain, and can that audit be automated?

### Operational
23. How should the Assistant handle networks and remote resources (downloading
    docs, checking a skill's repository) under default-deny?
24. How are concurrent or long-running diagnostics handled without blocking the
    session?
25. What is the expected initial scope of "supported distro families," and how
    is that communicated so skills can target it?
26. How are cost controls handled for bring-your-own-key providers (token
    budgets, spend warnings)?
27. What is the compatibility policy for the skill format and the fact model
    across versions?

---

## 13. Architectural Risks

The biggest design risks visible today, roughly ordered by severity. These are
the things most likely to sink the project, and they are named so that future
RFCs can attack them explicitly.

1. **Safety theater — approval as a rubber stamp.** If approvals are so
   frequent, fast, or uninformative that Operators click "yes" without reading,
   every safety mechanism in this document becomes decoration. This is the
   single most likely path to a harmful outcome. Mitigation direction: tiered
   approval UX, meaningful default-deny, friction proportional to risk, and
   plan-level approval so a "fix" is judged once, as a whole.

2. **Prompt injection via the machine itself.** The system's own inputs —
   command output, config files, the environment — are untrusted text, and an
   adversarial or compromised machine can emit instructions aimed at the LLM
   and at the Operator. If untrusted text ever influences an approved action
   without deterministic confirmation, the entire model is broken. This risk
   is binary: either no untrusted text ever flows into action construction, or
   the project does not work.

3. **The beginner-with-root-power contradiction.** The least experienced users
   are exactly the ones who will be asked to authorize the most destructive
   actions. If the approval UI is simple enough for a beginner to use
   confidently, it may also be simple enough to approve a catastrophic command;
   if it is informative enough to be safe, it may be too complex for the target
   user. Designing the approval experience for this specific contradiction is
   the core UX problem and is unsolved in this RFC.

4. **Ecosystem trust problem for skills.** Skills are the community feature and
   the community hazard: they are arbitrary code by design. There is a real
   tension between a low-friction ecosystem (unreviewed, open) and a safe one
   (signed, reviewed, slow to grow). This RFC takes the conservative position —
   untrusted until authenticated and policy-checked — but that position may
   strangle the ecosystem if the friction is too high, and a lax position may
   produce a malware delivery channel. The trade-off is not yet resolved.

5. **Fact-layer fragmentation or dilution.** The Diagnostics & Fact Layer is the
   only source of truth, and it must normalize across many distros. Too thick,
   and it becomes an unmaintainable matrix of distro-specific cases; too thin,
   and it degrades into "the LLM reading raw command output," which collapses
   the deterministic-facts principle. Finding the stable, minimal fact model is
   a research problem, and getting it wrong either direction undermines the
   architecture.

6. **Provider lowest-common-denominator trap.** Supporting any preferred LLM —
   including weak, local models with unreliable tool-calling — may force the
   provider abstraction so thin that it can't represent evidence, plans, and
   approval flows faithfully, weakening the whole design. Alternatively,
   requiring strong tool-calling excludes the local-model users the project
   explicitly wants. The capability floor for a supported provider is
   undecided (Open Question 16) and is a strategic decision, not a
   technical detail.

7. **Scope creep into a general agent platform.** Every instinct that made this
   tool attractive ("it's like Claude Code but for computers!") is also the
   vector for absorbing general-purpose agent features, remote control, fleet
   management, and monitoring — each of which is an explicit non-goal. Without
   disciplined gatekeeping at every RFC, the project becomes a mediocre general
   agent instead of an excellent Linux care tool. The boundary tests in Section
   6 exist for this, but enforcement is a process risk.

8. **Audit trail honesty vs. security.** The audit log provides accountability,
   not security: the Operator is also the entity with full control of the
   machine, so the log cannot be genuinely tamper-proof against the person it
   is meant to protect. If the project markets the audit as a security control,
   it will overpromise; if it fails to surface the log clearly, it underdelivers
   on transparency. The honest position — audit as transparency for the
   Operator, not evidence for adversaries — must be held consistently.

9. **Context creep eroding privacy and focus.** The more the Assistant
   remembers, the more useful it is and the more dangerous it is. If context
   grows toward "collect everything about the machine," it violates the
   purpose-limited rule and the trust of the very users it targets. Enforcing
   minimalism against the perpetual temptation to "just keep the whole config
   tree in context" requires ongoing architectural discipline, not just a rule
   in this document.

10. **Verification theater.** The design insists on deterministic verification
    of fixes, but "the command exited 0" is not always "the problem is solved."
    If the project ships with a weak notion of verification, it will display
    confident false successes — the exact failure mode this RFC forbids in
    principle but must also forbid in practice. Defining honest verification
    (Open Questions 10–11) is therefore not a nicety but a prerequisite.
