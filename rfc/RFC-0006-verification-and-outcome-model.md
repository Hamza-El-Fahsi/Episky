# RFC-0006 — Verification & Outcome Model

**Status:** Draft
**Date:** 2026-08-02
**Scope:** How the Assistant determines whether a proposed repair actually
succeeded: what verification means, what success and failure mean, what
uncertainty means, when re-inspection is mandatory, and how Outcomes are
determined from Facts
**Audience:** Future maintainers
**Supersedes:** Nothing
**Depends on:** RFC-0001, RFC-0002, RFC-0003, RFC-0004, RFC-0005, RFC-0007,
RFC-0008 (accepted in this series). RFC-0021 is referenced for the machine's
subsystem and state-domain vocabulary but is itself a Draft and is not a
dependency.

**Roadmap note:** This is RFC-0000's "RFC-0006 — Verification & Rollback
Semantics" (Domain, Required), the document that fixes what "verified" means —
RFC-0001 names weak verification as a top risk and this RFC is that risk's
answer (RFC-0000 §5, §6). It answers the coverage rows RFC-0000 §8 assigns to
it: RFC-0001 Q10–Q11 (verification definition, rollback promises), Q12
(catastrophic failure surfacing); RFC-0002 Q16 (diagnostic-only goals evidence
bar). It also answers RFC-0005 §15 OQ3 (how before/after Fact sets are compared
to decide "verified").

**BREAKING:** No. This RFC specifies the verification semantics RFC-0001,
RFC-0002, RFC-0004, and RFC-0005 already assume — that a fix is not complete
until verified with deterministic, state-based evidence (RFC-0001 §10.5), that
Verification always follows Execution (RFC-0002 invariant 2), that verification
never assumes success (RFC-0004 A5), and that Facts are what state-based
verification compares (RFC-0005). It does not weaken any Principle, Boundary,
Invariant, or canonical Definition in an accepted RFC.

---

## 0. Purpose

This RFC answers one question:

> **How does the Assistant know that a proposed repair actually worked?**

The answer: **by comparing Facts.** Verification is the deterministic,
state-based determination, from the Assistant's own Facts, of whether an
executed action produced its expected Post-condition. Nothing else counts as
proof.

Three sentences of this RFC's philosophy, each load-bearing:

1. **Execution is not evidence.** The fact that an action ran tells you only
   that the action ran. It says nothing about whether the machine now has the
   state the action was supposed to create. Running an installer is not the
   same as a working installation.
2. **Exit codes are not proof.** A command's exit status is produced by the
   same tool that the Assistant asked to change the machine; it reports what
   that tool decided to report. It is raw output — distro-specific, tool-shaped,
   and un-normalized — and per RFC-0005 raw output is never internal knowledge.
3. **The machine must testify through Facts.** The only trustworthy statement
   that the machine changed is a fresh, provenance-carrying Fact describing the
   machine's actual state *after* the action, produced by an independent
   inspection, compared against the state the action was supposed to produce.

Verification is therefore always *comparison of Facts against expected
Post-conditions*. It is never a guess, never a provider's claim, and never a
re-run of the command that just ran.

This RFC defines verification and Outcomes only. Execution is defined by
RFC-0008. Facts are defined by RFC-0005. Authority is defined by RFC-0004.

---

## 1. Principles

Verification is governed by the following principles. They are not
implementation details; they are normative commitments. Each is operationalized
as an invariant in §13.

1. **Verify after every state-changing action.** Every action that may change
   the machine is followed by a verification attempt before any success is
   claimed (RFC-0002 invariant 2; RFC-0008).
2. **Never infer success.** Success is a determination made from observed
   Facts, never from the plan's intent, the command's report, or the absence of
   an error. No "it probably worked."
3. **Evidence over assumptions.** When expected evidence and assumption
   disagree, the evidence wins. When evidence is missing, the outcome is
   Unknown — never success by default.
4. **Verification is deterministic.** The same Facts produce the same Outcome
   every time. Verification never consults the LLM for judgment; it is a
   mechanical comparison. LLM judgment belongs to planning and diagnosis, not
   to verification.
5. **Unknown is acceptable.** "I could not verify this" is a first-class,
   honest outcome (RFC-0001 §10.1). Unknown is always preferable to false
   success.
6. **Partial success exists.** A multi-step plan may leave some Post-conditions
   met and others not. That is a distinct Outcome, never collapsed into a
   binary success/failure.
7. **Contradiction always wins.** If observed Facts contradict the expected
   Post-condition, or contradict each other, the outcome is Contradicted and
   the current path stops (RFC-0001 §10.4). A contradiction is never papered
   over by choosing the friendlier interpretation.
8. **Verification never mutates.** Verification only observes and compares. It
   must not itself change the machine, or its evidence would be self-produced.
9. **Re-verify when trust lapses.** Freshness, machine change, reboot, operator
   intervention, and provenance loss all make previous verification results
   inapplicable; the affected Facts must be re-collected (§10).
10. **Rollback is not a promise; it is a new action.** The project promises
    careful, verified recovery, not that every action can be undone. Reverting
    anything is itself a state-changing action requiring its own approval and
    its own verification (RFC-0002 §10).

---

## 2. Execution vs Verification

Execution and verification are two different acts with two different
authorities, and confusing them is the root of verification theater.

```
Proposal
   ↓
Approval
   ↓
Execution
   ↓
Verification
   ↓
Outcome
```

Each stage is independent:

| Stage | Owner | Decides | Produces |
|---|---|---|---|
| Proposal | Planning | What the Assistant proposes to do | A proposed Action with a declared expected effect |
| Approval | RFC-0008 / RFC-0004 | Whether the Operator permits it | An Approval Token; authorization to execute |
| Execution | RFC-0008 | Whether the action runs and with what result | An execution record; the machine's state changed (or not) |
| Verification | This RFC | Whether the machine's actual state matches the expected effect | An Outcome, from fresh Facts |
| Outcome | This RFC | The final determination for the goal | The reported result (§7) |

**Why they are independent:**

- **Approval is not execution.** An approved action can fail to run, run
  partially, or run and fail. Approval authorizes a *risk*, not a *result*.
- **Execution is not verification.** The act of running the action and the act
  of determining its effect are performed by different concerns for exactly
  this reason: an actor who reports on its own change is its own witness.
  RFC-0004 A5 and A1 keep the observer separate from the executor.
- **Verification is not approval.** An action can be approved and correctly
  executed and still not produce its expected Post-condition. Verification
  does not ask "was I allowed to?"; it asks "is the machine in the expected
  state?"
- **Verification is not planning.** Planning decides *what to change*; 
  verification decides *whether it changed*. The LLM may participate in
  planning; it never participates in verification (§1.4).

Because the stages are independent, failure in any one stage is a distinct,
reportable event. A rejected approval, a failed execution, and a failed
verification are three different stories, and the Assistant must never conflate
them in what it tells the Operator (RFC-0002 §2.9, §2.14).

---

## 3. Verification Sources

Verification consumes Facts. Facts are produced by the Observation-to-Fact
pipeline of RFC-0005 (Raw Output → Observation → Normalization → Fact). The
list of acceptable sources of verification evidence is therefore the list of
Fact sources:

| Source | What it contributes | Example shape |
|---|---|---|
| **Fresh inspection** | A newly collected Observation of the machine's state at verification time | A Fact carrying a current Timestamp |
| **Fact comparison** | The before/after delta between Facts collected before and after execution | Two Facts over the same Subject and Property |
| **Service status** | Whether a service is in its expected run state | A Fact over the service's State Domain |
| **Configuration state** | Whether a configuration value matches the expected value | A Fact over a configuration Property |
| **Filesystem state** | Whether a file, directory, or mount is present and in the expected form | A Fact over a filesystem Property |
| **Package state** | Whether a package is installed at the expected version, or absent | A Fact over the package's State Domain |
| **Kernel state** | Whether a kernel module, parameter, or boot entry is active | A Fact over a kernel Property |

**Never raw command output.** A tool's raw output is not a verification source.
Raw output is distro-specific text that must first pass through RFC-0005
normalization to become Facts. Verification compares Facts; it never compares
text (RFC-0004 A5, RFC-0005).

**One rule unifies the table:** a verification source is acceptable if and
only if it is a Fact produced by independent inspection with known provenance
and known freshness. Anything else — a provider's sentence, a skill's
recollection, a logged claim — is not evidence.

---

## 4. Preconditions

A Precondition is a Fact that must be true *before* execution may begin. It is
declared as part of the proposed Action (RFC-0008 §9) and verified at approval
time. Because the machine is not frozen between planning and execution, a
Precondition that was true at approval time may be false at execution time.

**What must be true before execution:**

1. The Precondition Facts are fresh (within their freshness bound) at the
   moment execution begins.
2. The Precondition Facts match the declared expected state.
3. No state change has occurred, between approval and execution, that would
   invalidate the Precondition Facts (RFC-0002 invariant 8; RFC-0008 TOCTOU
   rules).

**How Preconditions are revalidated.** Between approval and execution, the
Preconditions are re-observed. The Assistant does not trust the Fact set from
planning time; it re-collects the Precondition Facts at the execution boundary
and compares them to the declared expected state. If any Precondition no longer
holds, the action does not run; the plan is re-opened and the Operator is
informed (RFC-0002 §2.10 Replanning).

**TOCTOU relationship with RFC-0008.** The time-of-check to time-of-use gap is
an execution concern: RFC-0008 defines how Preconditions are held against
execution (RFC-0008 §10, invariants P9/P10/P14). This RFC's contribution is the
verification side of that gap: the Assistant must *re-observe* before acting,
and any action executed without a fresh Precondition Fact set is
unverifiable-by-construction and must be labeled as such (§7 Unknown). The two
documents together close the gap from both sides: RFC-0008 refuses to execute
on stale Preconditions, and this RFC refuses to verify outcomes that were
reached without fresh Preconditions.

---

## 5. Postconditions

A Postcondition is the expected machine state after an action, expressed as
Facts. It is the target that verification compares observed state against.

**Postconditions are state, not implementation.** A Postcondition says *what
the machine should be like* — the service running, the package at version X,
the configuration value set — not *what steps were taken* or *how it was
achieved*. "The file contains the new value" is a Postcondition; "we ran the
edit command" is an execution record. Verification cares only about the former.

**Every state-changing Action declares its Postconditions up front.** An
Action is not a complete Proposal without a declared expected effect (RFC-0008;
RFC-0001 §11.3). The Postconditions are expressed in the same vocabulary as
Facts: a Subject, a Property, an expected Status, and a freshness bound for the
check (§11, §12).

**Architecture only.** This RFC does not prescribe how Postconditions are
stated syntactically — no schemas, no data formats (RFC-0005 §3). It prescribes
that they *are* stated, that they are stated *before* execution, and that
verification is a comparison of Facts against them (§6, §9).

**Postconditions are not a wish list.** The Assistant must not invent
Postconditions after the fact to fit whatever state it observes. The expected
state is declared with the Proposal; an Outcome that matches a
retrospectively-invented expectation is not verification, it is rationalization
(§9, invariant V10).

---

## 6. Verification Process

Verification is a defined process. It is normative; every step is mandatory and
their order is fixed.

```
Execute
   ↓
Collect
   ↓
Normalize
   ↓
Facts
   ↓
Compare
   ↓
Outcome
```

| Step | What happens | Normative requirement |
|---|---|---|
| **Execute** | The action runs under RFC-0008 | Produces an execution record; the machine's state has changed (or not) |
| **Collect** | Independent, read-only inspection of the machine's current state | Fresh Observations over the Postcondition's Subjects and Properties |
| **Normalize** | Raw output becomes Facts through RFC-0005 | Deterministic per-Observation normalization; no raw text retained |
| **Facts** | A Fact set describing the state after execution | Every Fact carries provenance, Status, and a Timestamp |
| **Compare** | Before/after Facts and expected Postconditions are compared | Comparison follows §9; deterministic; contradiction wins |
| **Outcome** | The comparison resolves to one of the §7 Outcomes | Reported verbatim; no silent upgrading |

**Normative requirements of the process:**

1. **Verification follows execution.** Every executed action is followed by a
   verification attempt before any success is claimed (RFC-0002 invariant 2).
2. **Verification is read-only.** The Collect step never mutates the machine
   (invariant V8). Its only effect is the creation of Facts.
3. **Verification is deterministic.** The Compare step has no LLM, no policy
   interpretation, no judgment call (invariant V3). The same Facts produce the
   same Outcome.
4. **The expected state is fixed before Compare.** The Postconditions compared
   against are those declared with the Proposal, not those implied by the
   observed state (invariant V10).
5. **A diagnostic-only goal uses a different bar.** When the goal was to
   understand, not to act (RFC-0002 Q16), no state-changing action ran and no
   Postcondition applies. The "verification" for such a goal is completeness of
   evidence: the goal is Complete when the diagnostic evidence bar is met —
   the relevant Facts were collected, are fresh, and the interpretation was
   completed (RFC-0002 §2.5, §2.13). There is nothing to compare, and none is
   invented.
6. **Verification never skips.** If Collect cannot produce the needed Facts,
   the outcome is Unknown (§7) — the absence of a verification result is a
   result, not a reason to skip the step (invariant V14).

---

## 7. Outcome Model

An Outcome is the final determination of whether the goal's expected machine
state was achieved. Outcomes are conceptual and finite; every verification
attempt, and every goal, resolves to exactly one of the following.

| Outcome | Meaning | When it occurs | What the Assistant must do |
|---|---|---|---|
| **Verified Success** | The machine's observed state matches the expected Postconditions, on fresh Facts | All expected Facts present, current, and matching | Report success; proceed to Completed (RFC-0002 §2.13) |
| **Verified Failure** | The machine's observed state does not match the expected Postconditions, and the Facts are trustworthy | An expected Fact is missing or contradicts the observed state | Report failure; the failure evidence is new Fact; Replanning (RFC-0002 §2.9) |
| **Partially Successful** | Some expected Postconditions are met, others are not | A multi-step plan left part of the expected state in place | Report exactly which Postconditions hold and which do not; never call it success or failure |
| **No Observable Change** | The machine's state after execution is indistinguishable from its state before | The action ran but produced no change, or produced an idempotent state | Report that no change was observed; the goal may be complete if no change was required |
| **Unknown** | Verification could not be completed — evidence is missing, stale, or unobtainable | Collect failed, Facts went stale mid-check, or the state cannot be observed | Report "unverified"; never claim success (RFC-0002 §2.9, VERIFICATION_INCONCLUSIVE) |
| **Contradicted** | Observed Facts contradict the expected Postconditions, or each other | Conflicting evidence (§8) | Stop the current path; surface the contradiction; re-evaluate with the Operator (RFC-0001 §10.4) |
| **Interrupted** | Verification was halted — by the Operator, a reboot, or a watchdog — before Compare | The process was cut off between Execute and Outcome | Report Interrupted; the actual state is re-established on resume (RFC-0002 §2.9) |
| **Expired** | The window for trusting the Facts closed before Compare | The freshness bound lapsed during verification | Re-collect, or report Unknown; never report against expired Facts (invariant V4) |

**Rules over the model:**

1. **Outcomes are exhaustive.** Any verification attempt resolves to exactly
   one of the eight. "No outcome" is not an option; a failed attempt is
   Unknown or Contradicted, never nothing.
2. **Outcomes are mutually exclusive.** The eight are defined so that a single
   comparison has a single answer. Where two rules would apply, the strictest
   wins: Contradicted > Verified Failure > Unknown > the rest.
3. **No silent upgrading.** A partially successful result is never reported as
   success; an Unknown result is never reported as success; an Interrupted
   result is never reported as success. The Outcome reported is the Outcome
   determined (RFC-0002 §2.13 Completed-with-caveat).
4. **Outcomes carry their evidence.** Every Outcome is reported with the Facts
   that determined it, so the Operator can see why it was reached (invariant
   V12).
5. **Rollback promises.** The project's promise about rollback is: *careful,
   verified recovery*, never automatic undo. A Verified Failure or Partially
   Successful outcome may lead to a *proposal* to revert, but reverting is
   itself a state-changing Action needing its own approval (RFC-0008) and its
   own verification (this RFC). Some Actions are inherently not undoable
   (e.g., editing a boot configuration); the Assistant must say so up front
   when proposing them (RFC-0001 Q11).

---

## 8. Contradictions

A contradiction exists when two Facts that should agree do not, or when the
observed state cannot be reconciled with the expected Postconditions.

**How contradictions are represented.** Contradiction is a Fact-level
condition, not a prose conclusion. RFC-0005 defines the Contradicted Fact
status and the conflict rules between Facts (§8, relationships). Two Facts
over the same Subject and Property with different values at the same freshness
are in contradiction; a Fact whose expected Postcondition is not met is a
contradiction between the Fact and the plan.

**How they stop planning.** Contradiction is a hard stop, per RFC-0001 §10.4:
the Assistant stops the current path, surfaces the contradiction to the
Operator, and re-evaluates. A contradiction is not resolved by trusting the
friendlier Fact, by re-running the verification until it passes, or by asking
the LLM which side to believe. The outcome is Contradicted (§7), the plan is
re-opened, and the Operator decides with the evidence visible (RFC-0002 §2.10).

**Relationship with RFC-0005 Facts.** The detection and representation of
contradiction belong to the Fact model (RFC-0005 §8). This RFC specifies the
*runtime response*: when RFC-0005 reports a contradiction, this RFC's Outcome
is Contradicted, the current plan stops, and no further step in the plan
executes until the Operator re-evaluates. The two documents do not overlap:
RFC-0005 defines what a contradiction *is*; this RFC defines what the Assistant
*does* about it.

---

## 9. Evidence Comparison

Evidence comparison is the Compare step of §6. This RFC defines the
principles; it deliberately does not define algorithms, thresholds, or code.

**What is compared.** Three sets of Facts:

1. **State before** — the Precondition Facts and any baseline Facts collected
   before execution (§4).
2. **State after** — the Facts collected after execution (§6, Collect).
3. **Expected delta** — the Postconditions declared with the Proposal (§5).

**Comparison principles:**

1. **Compare Facts, never text.** Before/after comparison is over normalized
   Facts with the same Subject and Property, never over raw output (RFC-0005).
2. **Expected delta drives the comparison.** The check is "did the expected
   delta occur?" — the state after execution matches the expected
   Postconditions, given the state before. The expected delta is the only
   standard; nothing else counts as success (invariant V10).
3. **Unexpected delta is evidence, not noise.** A difference between state
   before and after that the Proposal did not declare is itself a Fact and must
   be reported. An unexpected delta does not make a match invalid by itself,
   but it must be surfaced; a large or safety-relevant unexpected delta
   warrants a re-check or a stop (RFC-0002 invariant 2).
4. **Missing evidence is not evidence of success.** If an expected Fact cannot
   be collected, the outcome is Unknown, never success (invariant V9). Absence
   of an error message is not the same as presence of the expected state.
5. **Conflicting evidence resolves to Contradicted.** Where Facts conflict
   (§8), the comparison does not pick a winner; the outcome is Contradicted and
   the path stops (invariant V7).
6. **Freshness is a precondition of comparison.** Facts with unknown or lapsed
   freshness are not comparable; they are treated as stale and re-collected or
   excluded (invariant V4).
7. **Scope is declared, not assumed.** The comparison covers exactly the
   Subjects and Properties in the Postconditions. It never silently generalizes
   ("the package is installed, therefore the service works") beyond what was
   declared (§11).

**Not algorithms.** This RFC does not fix comparison thresholds, matching
algorithms, or normalization specifics. Those are implementation and belong to
RFC-0020 (implementation blueprint). The principles here are binding on any
implementation.

---

## 10. Re-verification

A verification result is true of a moment, not of a machine forever. Re-
verification is mandatory when any of the following occurs:

| Trigger | Why re-verification is required |
|---|---|
| **Time elapsed** | The Facts behind the last verification exceed their freshness bound; they no longer describe the current state (RFC-0005 §12) |
| **Machine changed** | Any state change — even an unrelated one — may have disturbed the verified state; the Postcondition Facts must be re-observed |
| **Reboot** | A reboot invalidates in-memory assumptions wholesale; the machine's state is re-established by inspection (RFC-0002 §8, REBOOT_DETECTED) |
| **Operator intervention** | The Operator may have changed something between steps; their action is a state change and re-establishes the baseline |
| **Unknown freshness** | If the Facts' freshness cannot be established, they are treated as stale (RFC-0005 §12 F15) |

**Rules:**

1. **Re-verification is a fresh collect.** Re-verification re-runs the
   Observation-to-Fact pipeline; it never reuses stored Facts whose freshness
   has lapsed (invariant V4).
2. **Verification results do not outlive their Facts.** An Outcome stays valid
   only while the Facts it was determined from stay current. Once they go
   stale, the Outcome's claim is unsupported (RFC-0007 §9, trust demotion on
   staleness).
3. **Reboot-resume is a re-verification, not a replay.** On resume, the
   Assistant re-establishes actual state and compares it to the expected
   Postconditions again; it does not assume that what was verified before the
   reboot still holds (RFC-0002 §8; RFC-0014 owns the resume mechanics).
4. **Catastrophic surfacing.** If the machine cannot be inspected at all after
   a change — e.g., the system fails to boot, or the diagnostics cannot run —
   the Assistant must surface this as a catastrophic case (RFC-0001 Q12): it
   reports that the change's outcome is *unverifiable*, does not claim success,
   and hands the Operator the clearest possible framing — what was attempted,
   what is unknown, and what safe next options exist, including the distro's
   own recovery tools. This surfacing is itself mandatory even when the
   Operator may be outside the TUI (RFC-0001 §10.9).

---

## 11. Verification Scope

Verification is always scoped to a part of the machine. Scope is expressed in
the subsystem and State-Domain vocabulary of RFC-0021.

| Scope | What is verified | Example Postcondition |
|---|---|---|
| **Service** | A service's run state and health | The service is running and enabled |
| **Package** | A package's presence and version | The package is installed at version X |
| **Filesystem** | Files, directories, mounts, and their properties | The file contains the expected value; the mount is present |
| **Kernel** | Kernel modules, parameters, and boot entries | The module is loaded |
| **Configuration** | Configuration values under their owning subsystem | The setting has the expected value |
| **Boot** | The boot state after a change that affects startup | The system boots; the entry is selected |
| **Network** | Network interfaces, links, and reachability | The interface is up |
| **Hardware** | Devices and their observable state | The device is detected |
| **Application** | Application-level state that maps to Facts | The application's database is in the expected state |

**Scope inheritance.** Scopes are not independent islands; they nest through the
machine model (RFC-0021 §4 subsystems, §6 State Domains). Verifying a service
often requires verifying a configuration value that the service reads, which
may require verifying a file. Scope inheritance means:

1. **A verification at a narrower scope depends on the wider scopes it
   touches.** "The service works" cannot be verified without the Facts that
   the service's configuration and dependencies are in their expected state.
2. **Scope follows the Postcondition.** The verification covers exactly the
   scopes the declared Postconditions name (§9.7). A Postcondition about a
   package does not by itself verify the service that consumes the package.
3. **Unverifiable scopes are declared.** Some states cannot be observed as
   Facts — e.g., "user perception of an app" (RFC-0021). Where a Postcondition
   touches an unverifiable scope, the outcome must say so: the verifiable
   parts are compared, and the unverifiable parts are labeled Unknown
   (RFC-0021 "Can verify"; RFC-0005 F13).

---

## 12. Verification Confidence

Verification Confidence is a qualitative statement about how much the evidence
supports the Outcome. It is **never a percentage**. Percentages imply a
measurement the Assistant cannot make, and they invite false precision — a
"90% sure" that turns out wrong is still wrong.

| Level | Meaning | When it applies |
|---|---|---|
| **Direct evidence** | The expected Postcondition was directly observed in a fresh Fact | The exact Subject/Property named by the Postcondition was re-observed and matched |
| **Strong evidence** | The Postcondition is supported by closely-related fresh Facts with consistent values | The exact Fact could not be observed, but its proximate Facts all agree and are current |
| **Supporting evidence** | The Postcondition is consistent with fresh Facts, but the connection is indirect | The Facts observed are compatible with the expected state but do not uniquely establish it |
| **Insufficient evidence** | The Facts collected cannot establish the Postcondition | Evidence missing, stale, or too coarse to compare (§9.4) |
| **Contradictory evidence** | Fresh Facts conflict with the Postcondition or each other | Contradiction detected (§8) |

**Rules:**

1. **Confidence qualifies the Outcome, it does not change it.** The Outcome is
   whatever §7 says it is. Confidence describes how well-supported that Outcome
   is. "Verified Success with Strong evidence" and "Verified Success with
   Direct evidence" are the same Outcome with different confidence, and the
   Assistant must say both honestly.
2. **Direct evidence is the target.** Verification should aim for Direct
   evidence of the Postcondition. The other levels exist because some states
   cannot be observed directly (RFC-0021 "Can verify"); they are honest
   fallbacks, not substitutes.
3. **Confidence never inflates the Outcome.** Insufficient or Contradictory
   evidence never yields Verified Success (invariant V5). If evidence is
   insufficient, the Outcome is Unknown; if contradictory, Contradicted.
4. **Confidence is derived, not asserted.** The level is computed from the
   freshness and specificity of the Facts, mechanically, in the Compare step —
   never chosen by the LLM to make a story sound better (invariant V3).

---

## 13. Verification Rules (Normative)

The following invariants are normative for the entire project. They are stated
so that each is testable: a reviewer can check the described behaviour against
the rule. They extend, and never weaken, RFC-0002's §9 invariants and RFC-0001's
principles.

| ID | Invariant | Test |
|---|---|---|
| V1 | **Verification never trusts raw output or exit status alone.** Only Facts, produced by independent inspection and normalized per RFC-0005, are verification evidence. | Remove all Fact evidence; any outcome other than Unknown or Contradicted is a violation. |
| V2 | **Every executed state-changing action produces a verification attempt.** Success is never claimed for an action that ran without a following Compare. | Record an action that ran with no verification attempt; report success — violation. |
| V3 | **Verification is deterministic.** The Compare step has no LLM, no policy judgment, and no randomness; identical Facts produce identical Outcomes. | Run the same Fact set through Compare twice; differing Outcomes are a violation. |
| V4 | **Verification never consumes stale Facts.** Facts with lapsed or unknown freshness are treated as stale and re-collected or excluded; Outcomes are never determined from them. | Feed a stale Fact into Compare; any Outcome other than a re-collect-then-compare or Unknown is a violation. |
| V5 | **Unknown is preferable to false success.** Unverifiable work is labeled unverified; no claim of success is made without supporting fresh Facts. | A goal whose evidence was missing is reported as success — violation. |
| V6 | **Partial success is a distinct Outcome.** It is reported as exactly which Postconditions held and which did not; never collapsed into success or failure. | A plan with one unmet Postcondition is reported as success — violation. |
| V7 | **Contradiction always wins.** Conflicting Facts resolve to Contradicted and stop the current path; no friendlier interpretation is chosen. | Two Facts conflict; a non-Contradicted outcome that proceeds is a violation. |
| V8 | **Verification never mutates the machine.** Collect and Compare are read-only; verification changes nothing but the Assistant's Fact store. | A verification step writes to the machine — violation. |
| V9 | **Missing evidence is not evidence of success.** Absent expected Facts yield Unknown, never success. | A missing expected Fact is treated as confirmation — violation. |
| V10 | **Postconditions are fixed before Compare.** The expected state is the declared Proposal's expected state, never invented after the fact. | A Postcondition changed between Proposal and Compare to fit the observed state — violation. |
| V11 | **Every verification attempt records its evidence and Outcome.** The Facts compared, the confidence level, and the resulting Outcome are all recorded with provenance. | A verification attempt with no evidence record — violation. |
| V12 | **Re-verification follows every trust-lapse trigger.** A fresh Collect replaces stored Facts after time, state change, reboot, operator intervention, or unknown freshness. | An Outcome is reused after a reboot without re-collect — violation. |
| V13 | **A diagnostic-only goal verifies completeness of evidence, not a change.** No Postcondition comparison is invented where no state-changing action ran. | A diagnostic-only goal is reported via a Postcondition comparison — violation. |
| V14 | **Verification never silently skips.** If Collect cannot produce the needed Facts, the Outcome is Unknown (or Contradicted), never absent or assumed. | A Collect failure yields no Outcome and the goal is reported Complete — violation. |
| V15 | **Confidence never changes the Outcome.** Confidence qualifies the report; it never upgrades Unknown or Contradicted to Verified Success. | Insufficient evidence produces Verified Success with any confidence — violation. |
| V16 | **Catastrophic cases are surfaced, never silenced.** A machine that cannot be inspected after a change is reported as unverifiable, with safe options, never as success. | A boot failure after a change is reported as success or omitted — violation. |

---

## 14. Interaction with other RFCs

This RFC specifies verification and Outcomes for the whole project. Only
references follow; no duplication (RFC-0003 Part II §1). The referenced
documents define what this RFC consumes; this RFC defines what they assume.

| RFC | Relationship | What RFC-0006 says here |
|---|---|---|
| **RFC-0001** | Architecture and principles | Operationalizes RFC-0001 §10.5 (verification before victory), §10.1 (uncertainty disclosed), §10.4 (stop on contradiction), §10.9 (last resort is the human); answers Q10–Q12. |
| **RFC-0002** | Runtime states and invariants | Implements the Verification state (RFC-0002 §2.9), the Verifying→Replanning/Awaiting Input exits, invariant 2 (verification always follows execution), Completed-with-caveat (RFC-0002 §2.13); answers Q16. |
| **RFC-0003** | Vocabulary and governance | Uses Verification, Outcome, Fact, Observation, Action, Proposal, Post-condition canonically; §17 flags new terms for Part I. |
| **RFC-0004** | Authority model | Implements A5 (verification never assumes success) and the observer/executor separation; verification consumes Facts the Diagnostics Layer produces (RFC-0004 §4.5). |
| **RFC-0005** | Canonical Fact Model | Defines the Facts verification compares, their statuses and freshness, and contradiction representation (RFC-0005 §8); answers RFC-0005 §15 OQ3. |
| **RFC-0007** | Trust and sanitization | Verification consumes Facts at their trusted level; demotion on staleness or contradiction (RFC-0007 §9) is what forces re-verification (§10). |
| **RFC-0008** | Approval and policy | Execution, Preconditions, and TOCTOU belong to RFC-0008; this RFC covers the outcome side of the same gap (RFC-0008 §4). No duplication. |
| **RFC-0021** | System model and platforms | Supplies the subsystem and State-Domain vocabulary for Verification Scope (RFC-0021 §11) and for which states can be verified (RFC-0021 §12, "Can verify"). Referenced, not a dependency. |

Forward references (planned RFCs this model constrains): RFC-0009 (verification
evidence never carries secrets into Context); RFC-0012 (Outcomes and evidence
are part of what Context/Memory holds); RFC-0013 (verification attempts are
audit records); RFC-0014 (reboot-resume re-verification mechanics, and
interrupted-action reconciliation); RFC-0015 (how Outcomes and confidence are
presented); RFC-0017 (verification and rollback compatibility promises);
RFC-0020 (comparison algorithms and freshness-bound policy as implementation).

---

## 15. Open Questions

Questions this RFC deliberately leaves open; each names its owner. None blocks
the verification guarantees above.

1. **Comparison algorithms and thresholds.** How the Compare step is
   implemented — matching rules, normalization specifics, delta detection —
   is owned by RFC-0020 (implementation blueprint). The principles of §9 are
   binding; the mechanics are not.
2. **Rollback catalogue.** Which Action kinds are inherently undoable and which
   are not, as a maintainable catalogue communicated to the Operator, is owned
   by RFC-0017 (compatibility policy) and the skill contracts that declare
   Postconditions.
3. **Presentation of Outcomes.** How Outcomes, confidence levels, and
   contradictory evidence are shown to a beginner, and how catastrophic
   surfacing is rendered when the Operator may be outside the TUI, is owned by
   RFC-0015 (interface).
4. **Resume-time re-verification mechanics.** How re-verification is scheduled
   and sequenced across a reboot and an interrupted session is owned by
   RFC-0014.
5. **Evidence retention.** How long verification evidence and Outcomes are
   retained, and how they feed audit, is owned by RFC-0013.
6. **Freshness-bound values.** The concrete freshness bounds that drive the
   "time elapsed" re-verification trigger are policy values owned by RFC-0020.
7. **Skill-declared Postconditions.** The contract by which a skill declares
   its Postconditions and its verifiable scope is owned by the extension
   contract work (RFC-0011, and RFC-0001 §11.3).

---

## 16. Risks

| Risk | Mitigation |
|---|---|
| **False success** | The cardinal sin: reporting success without fresh Fact evidence. Blocked by V1, V5, V14, V15 and the rule that only a Compare can produce Verified Success. |
| **False failure** | Reporting failure from stale or mis-scoped evidence. Blocked by V4 (freshness), V9 (missing evidence ≠ failure), and scope discipline (§11). |
| **Stale evidence** | Reusing verification results after their Facts lapsed. Blocked by V4 and V12 (re-verification triggers). |
| **Verification loops** | Re-collecting and re-comparing indefinitely when the machine will not settle. Blocked by bounded retry (RFC-0002 §2.10, RFC-0008) and by Unknown being an acceptable terminal outcome (V5). |
| **Missing observations** | Expected Facts that cannot be collected being silently treated as success. Blocked by V9 and V14 (a Collect failure is a reportable Outcome, never an omission). |
| **Contradictory facts** | The temptation to pick the friendlier Fact when evidence conflicts. Blocked by V7 and §8 (Contradicted stops the path). |
| **Race conditions** | The machine changing between Collect and Compare, or between approval and execution. Blocked by TOCTOU revalidation (§4, RFC-0008) and freshness-aware comparison (§9.6). |

---

## 17. Vocabulary Additions for RFC-0003

The following terms are defined in this RFC and must be added to RFC-0003 Part I
by additive amendment: **Outcome**, **Verified Success**, **Verified Failure**,
**Partially Successful**, **No Observable Change**, **Unknown** (verification
sense), **Contradicted** (verification sense), **Interrupted** (verification
sense), **Expired** (verification sense), **Postcondition**, **Evidence
Comparison**, **Verification Confidence**, **Direct Evidence**, **Strong
Evidence**, **Supporting Evidence**, **Insufficient Evidence**, **Contradictory
Evidence**, **Re-verification**, **Verification Scope**. The definitions appear
at first use in §7, §5, §9, §12, §10, and §11. Verification, Fact, Observation,
Action, Proposal, Approval, and Plan already exist in RFC-0003 Part I and are
used here with their canonical meanings.

---

*End of RFC-0006. Normative: sections 1, 2, 3, 4, 5, 6, 7, 8, 9, 10, 11, 12,
13. Explanatory and load-bearing: sections 0, 14, 15, 16, 17. Any change to an
Outcome, a verification-process step, a comparison principle, a re-verification
trigger, a confidence level, or an invariant V1–V16 is a BREAKING change and
must be made by amendment (RFC-0003 Part II).*
