# RFC reference validator

`tools/validate_rfc_refs.py` is the dev-only validator for the Episky RFC
corpus. It checks cross-references between RFC documents so that normative
documents stay internally consistent and unambiguous.

It is part of the governance workflow described here. **The RFCs themselves are
the source of truth; this tool only helps keep them honest.**

## What it checks

1. **Inter-RFC references** — every `RFC-XXXX` token names an RFC that exists
   (0000–0021). References to planned RFCs (0005–0020) are legal forward refs.
2. **Section references** — every `§N` / `§N.M` / `§N.M.K` resolves to a real
   heading, implicit subsection, numbered-list item, or table row in the
   target RFC. Bare `§N.M` references inherit the scope of a preceding
   `RFC-XXXX §` mention in the same block.
3. **Invariant and principle references** — invariant identifiers (RFC-0002
    invariants 1–15, RFC-0004 A1–A10, RFC-0007 T1–T12, RFC-0008 P1–P14, RFC-0005
    F1–F16, RFC-0006 V1–V16, RFC-0010 PR1–PR16, RFC-0011 SK1–SK16, RFC-0009
    SC1–SC16, RFC-0012 CM1–CM16, RFC-0013 AU1–AU16) and RFC-0007
   sanitization principles S1–S8 resolve to known identifiers. A lettered id
   used with the word "invariant" is only valid as an invariant, not as a
   principle.
4. **Open questions** — every RFC-0001 / RFC-0002 question has an owner in the
   RFC-0000 §8 coverage tables, and every coverage entry maps to a question
   that is actually asked. Open questions in RFC-0004 / RFC-0007 / RFC-0021
   name an owning RFC (or a delegation marker) inline. RFC-0003's questions are
   deliberately delegated and exempt.
5. **Open-question references** — `Qnn` references to RFC-0001 (1–27) and
   RFC-0002 (1–17) are in range.

Fenced code blocks are excluded from reference scanning.

## When to run it

Run from the repository root:

```
python3 tools/validate_rfc_refs.py
```

The validator is **mandatory** at these points, not optional:

- **Before accepting an RFC.** A Draft cannot be accepted (RFC-0003 §3) while
  the validator reports blocking findings.
- **Before opening an RFC pull request.** The branch must validate clean before
  a pull request is opened for review.
- **Before merging an RFC branch.** The final merge must validate clean, after
  any review-driven edits.

It should also be run locally on every commit that touches `rfc/` or `tools/`,
so that problems surface at author time rather than at review time.

> Note: the RFCs must be left correct; do not edit an **Accepted** RFC to make
> the validator pass. Fixing an Accepted RFC requires an amendment per
> RFC-0003 §4 (see [How to fix validator failures](#how-to-fix-validator-failures)).

## Exit-code convention (machine-readable)

The validator's exit code is stable and meant to be consumed by scripts and CI:

| Code | Meaning |
| ---- | ------- |
| `0`  | Valid. No blocking findings (WARNING / INFO may be present). |
| `1`  | Blocking. At least one `ERROR` was found. |

`2` is reserved for a tool-internal failure (e.g. unreadable input) and is not
currently returned. Exit `0` with no output means the corpus is clean.

## Severity levels

| Severity | Meaning | Blocks? |
| -------- | ------- | ------- |
| `ERROR`  | A reference is broken or a governance rule is violated: dangling section/invariant/principle reference, reference to a nonexistent RFC, an open question with no owner, or an out-of-range question reference. | **Yes** |
| `WARNING` | A deviation that is suspicious but not provably wrong (e.g. a reference resolved only by fallback). Advisory; the author should review it. | No |
| `INFO`   | Informational output only (e.g. which files were checked). Never blocks. | No |

Findings are printed one per line in the machine-readable form:

```
<filename>:<line>: <SEVERITY>  <message>
```

## Which severities block acceptance

Only `ERROR` blocks acceptance. A document with any `ERROR` cannot be
accepted, its pull request cannot be opened, and its branch cannot be merged.

`WARNING` and `INFO` findings do **not** block acceptance. A `WARNING` should
still be reviewed and, where reasonable, resolved before acceptance; leaving an
unexplained `WARNING` requires a note in the pull request explaining why.

## How to fix validator failures

1. **Read the finding.** Each line names the file, the line number (raw file
   line, not a display artifact), the severity, and the problem.
2. **Find the reference.** Open the RFC at that line and look at the cited
   `§N.M`, invariant/principle id, or open-question reference.
3. **Decide what the text should say.** The RFC is the source of truth. If the
   reference is wrong, fix the RFC's text — do not weaken the check.
4. **Re-run.** `python3 tools/validate_rfc_refs.py` must exit `0`.

Common cases:

- **Unknown section** (`§N.M does not exist in RFC-XXXX`) — the section number
  is mistyped, or the section was removed/reworded. Correct the reference.
- **Unknown invariant/principle id** — the id is mistyped, or the id was never
  registered in the target RFC. Correct the reference.
- **`invariant S1` style errors** — the id is only valid with the word
  "invariant" if it is registered as an invariant; principles (e.g. RFC-0007's
  S1–S8) must not be called invariants. Rephrase to "principle S1".
- **Open question without an owner** — in Draft RFCs, name the RFC that owns
  the question inline (or mark it `Delegated` / `Future work` / `future
  amendment`).
- **No owner in RFC-0000 §8** — add the question to the correct coverage table
  in RFC-0000 §8. Editing RFC-0000 for a not-yet-accepted RFC is the normal
  mechanism; it is an Accepted document, so changes go through a pull request
  per CONTRIBUTING.md.

**If the finding is in an Accepted RFC (e.g. RFC-0004):** do not edit it to
force a pass. Record the finding, open an issue, and resolve it via an
amendment per RFC-0003 §4. The validator reports the problem so it stays
visible until the amendment lands.

## Proposed GitHub Actions integration

Not yet implemented. Once the repository's CI setup is decided, the following
is proposed so that **every RFC pull request automatically runs the validator**:

- A workflow triggered on `pull_request` (and `push` to RFC branches) that
  checks out the branch, runs `python3 tools/validate_rfc_refs.py`, and fails
  the check when the exit code is `1`.
- The check is a required status check on RFC branches so a red result blocks
  merge.
- Output is consumed via the exit-code convention above (no log parsing
  needed).

A concrete `.github/workflows/rfc-validation.yml` should be added when GitHub
Actions is adopted for the repository. Until then, contributors run the
validator locally per the gates above.
