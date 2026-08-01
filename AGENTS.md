# AGENTS.md — Repository guide for contributors and tooling

This file helps both human contributors and AI coding agents work correctly in
this repository. Read it before making changes.

## What this project is

Episky is an open-source TUI assistant that helps Linux beginners diagnose and
repair their own systems with human-approved, LLM-driven troubleshooting.

**Current phase: architecture.** There is no product code yet. The design is
defined by an accepted RFC series, and those documents are normative. Do not
write product code until RFC-0019 (MVP definition) and RFC-0020 (implementation
blueprint) are accepted — see the roadmap.

## Repository layout

- `rfc/` — architecture documents. `RFC-0000-architectural-roadmap.md` is the
  index of what exists and what comes next.

## Hard rules

1. **Accepted RFCs (RFC-0000 through RFC-0003) are normative.** Do not modify
   them. Changing their meaning requires an amendment per RFC-0003.
2. **Never commit to `main`.** Every change goes on a branch tied to an issue,
   through a reviewed pull request. See `CONTRIBUTING.md`.
3. **Use Conventional Commits** and keep commits small and atomic.
4. **The canonical vocabulary is binding.** Terms like *fact*, *action*,
   *approval*, and *verification* have precise meanings in RFC-0003. Use them
   exactly.
5. **The security principles are not negotiable in passing.** Anything involving
   execution, approvals, or untrusted input must stay within RFC-0001 §7–§8 and
   RFC-0002 §9 invariants.

## Getting context

- Start with `rfc/RFC-0000-architectural-roadmap.md` to see what is planned and
  in what order.
- Read `rfc/RFC-0001-architecture.md` for goals, non-goals, and principles.
- Read `rfc/RFC-0002-runtime.md` for the session state machine and invariants.
- Read `rfc/RFC-0003-vocabulary-and-governance.md` for the dictionary and the
  rules for changing documents.

## Working in this repository

1. Open (or find) a GitHub Issue for the task.
2. Create a branch `feat/<n>-<slug>` (or `fix/`, `docs/`, `rfc/`) from `main`.
3. Do the work; commit atomically with Conventional Commits.
4. Run applicable checks/tests before committing.
5. Push, open a pull request referencing the issue, and get it reviewed.
