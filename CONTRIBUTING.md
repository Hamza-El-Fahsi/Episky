# Contributing to Episky

Thanks for wanting to contribute. Episky is designed as a project many
contributors will live in for years, so the workflow below is **mandatory**, not
suggested. It exists to keep the repository reviewable and the history clean.

## Where contributions happen

- **Issues** — bug reports, feature requests, and task tracking.
- **Pull requests** — every change lands here, reviewed. Nothing is pushed
  directly to `main`.
- **RFCs** — architectural change happens as documents first, never as code
  first. See [the RFC process](#the-rfc-process).

## Development workflow (mandatory)

1. **Every logical task has a GitHub Issue.** If none exists, open one before
   starting work. One issue = one task.
2. **Never work directly on `main`.** Create a dedicated branch per task, named
   `<type>/<issue-number>-<slug>` (for example `feat/12-provider-contract`).
3. **One issue per branch.** Never combine unrelated work in one branch or one
   pull request.
4. **Keep commits small, focused, and atomic.** Each commit is one logical
   change. Never mix unrelated changes in the same commit.
5. **Use Conventional Commits** (see below).
6. **Run the tests before every commit** whenever applicable. If a change has no
   applicable tests, say so in the pull request.
7. **Run the RFC validator before committing RFC or tooling changes.**
   `python3 tools/validate_rfc_refs.py` must exit `0` before accepting an RFC,
   opening an RFC pull request, or merging an RFC branch. See
   [`tools/README.md`](tools/README.md) for the full workflow.
8. **Update documentation when behavior changes.** The RFCs are normative;
   documentation that disagrees with them is a defect.
9. **Push the branch and open a pull request** that references its issue
   (`Fixes #N`). Never merge your own pull request without review.
10. **Milestones get tagged.** Every completed milestone receives a Git tag and a
    GitHub Release.

## Conventional Commits

Commit messages follow [Conventional Commits]:

```
<type>(<scope>): <subject>

<body, why the change is needed>
```

Common types: `feat`, `fix`, `docs`, `chore`, `refactor`, `test`, `perf`,
`build`, `ci`, `style`.

Examples:

- `feat(provider): add support for local OpenAI-compatible endpoints`
- `fix(executor): stop orphaned processes after an interrupted action`
- `docs: clarify approval-token expiry in RFC-0002`
- `chore: add .gitignore for editor artifacts`

## The RFC process

Architecture is written, not decided in code. The full constitution is
[RFC-0003](rfc/RFC-0003-vocabulary-and-governance.md). In short:

- New architectural work is a **new RFC**; the roadmap
  ([RFC-0000](rfc/RFC-0000-architectural-roadmap.md)) defines what comes next.
- Accepted RFCs are **normative**. Changing one requires an amendment.
- **Breaking changes** are labeled `BREAKING`, enumerate their impact, and are
  rejected by default.

If you are proposing a feature, expect to be asked "what does the RFC say?"
That is the process working, not friction.

RFC pull requests must also validate clean before they can be accepted, opened,
or merged. See [`tools/README.md`](tools/README.md).

## Testing and documentation

- Tests are run before each commit. When the project has a test suite, it must
  pass before a pull request merges.
- The RFCs are the source of truth. Code or documentation that contradicts an
  accepted RFC should be corrected, or the RFC amended.

## Code of conduct

All participation is governed by our
[Code of Conduct](CODE_OF_CONDUCT.md).

[Conventional Commits]: https://www.conventionalcommits.org
